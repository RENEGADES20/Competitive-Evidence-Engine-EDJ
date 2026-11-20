"""Sub-question search of a question plan (#245, ADR-021 rule 6; was the per-part search of #214) on
fixture rows in a throwaway schema of the local Postgres (skipped if it is down): every hard filter
in every sub-question, research once, a budget per sub-question, no chunk twice, competitors on the
theme only with the floor across them, the `search_fn` seam and the corrective re-search hook."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts, planner
from cee.retrieve.fts import resolve, search
from cee.retrieve.planner import Aspect, Part, Plan, rules_plan, search_subquestions, subquestions

SCHEMA = "test_subquestions"
TODAY = date(2026, 6, 1)
IN, OUT = date(2026, 5, 1), date(2025, 12, 1)
WORDS = "younger investors prefer digital advice and advisor recruiting"
Q19 = "How should the preferences of younger investors shape Edward Jones's offerings?"
DOCS = [  # doc_id, entity_id, doc_type, tier, published, basis, topic, chunks, segment, words
    *[(f"{e}-10K-{i}", e, "10-K", 2, IN, "source", None, 3, None, WORDS)
      for e in ("MS", "RJF", "EDJ", "SCHW", "MER") for i in range(2)],
    *[(f"{e}-PR-OLD", e, "press", 2, OUT, "source", None, 2, None, WORDS) for e in ("MS", "RJF")],
    *[(f"{e}-WEB", e, "web", 3, IN, "retrieved", None, 2, None, WORDS) for e in ("MS", "RJF")],
    ("BAC-10K-GWIM", "BAC", "10-K", 2, IN, "source", None, 3, "GWIM", WORDS),
    ("BAC-10K-CONS", "BAC", "10-K", 2, IN, "source", None, 3, "Consumer Banking", WORDS),
    ("BAC-10K-NOSEG", "BAC", "10-K", 2, IN, "source", None, 3, None, WORDS),
    # research on the theme, long chunks
    ("SURVEY-A", None, "research", 5, IN, "source", "younger_investors", 4, None, WORDS + " survey" * 60),
    ("SURVEY-B", None, "research", 5, IN, "source", "younger_investors", 4, None, WORDS + " study" * 60),
    # benchmark question: trade press is left out in every sub-question
    *[(f"{e}-TRADE", e, "trade", 4, IN, "source", None, 2, None, "advisor headcount rose") for e in ("MS", "RJF")],
    *[(f"{e}-10Q-HC", e, "10-Q", 2, IN, "source", None, 2, None, "advisor headcount rose") for e in ("MS", "RJF")],
    # a competitor chunk off the theme (no younger-investor keyword) that matches Q19's words
    ("MS-10K-OFF", "MS", "10-K", 2, IN, "source", None, 2, None, "new offerings shape the platform offerings"),
]
TURNS = [  # a call: analyst question turn, management answer turn (#203)
    ("RJF-TR-1", 0, "Jane Analyst, Example Securities\n\nHow do younger investors pick an advisor?"),
    ("RJF-TR-1", 1, "Paul Example - Chief Executive Officer\n\nThey want digital tools and a human advisor."),
]


@pytest.fixture(scope="module")
def sub_db():
    url = settings().database_url
    try:
        conn = psycopg.connect(url, connect_timeout=2, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not reachable")
    with conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.execute(f"CREATE SCHEMA {SCHEMA}")
        conn.execute(f"""CREATE TABLE {SCHEMA}.documents (
            doc_id text PRIMARY KEY, entity_id text, doc_type text NOT NULL, source_tier int NOT NULL,
            published_at date NOT NULL, date_basis text NOT NULL, period_end date)""")
        conn.execute(f"""CREATE TABLE {SCHEMA}.chunks (
            chunk_id text PRIMARY KEY, doc_id text NOT NULL, seq int NOT NULL, section text,
            segment text, page int, prefix text NOT NULL, text text NOT NULL,
            tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', prefix || ' ' || text)) STORED)""")
        conn.execute(f"CREATE TABLE {SCHEMA}.chunk_topics (chunk_id text, topic_id text)")
        for doc_id, entity, doc_type, tier, published, basis, topic, n, segment, words in DOCS:
            conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES (%s, %s, %s, %s, %s, %s, NULL)",
                         (doc_id, entity, doc_type, tier, published, basis))
            for i in range(n):
                cid = f"{doc_id}#{i}"
                conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, %s, 'Document', %s, NULL, '', %s)",
                             (cid, doc_id, i, segment,
                              words + " " + " ".join(f"{cid.lower()}w{j}" for j in range(12))))
                if topic:
                    conn.execute(f"INSERT INTO {SCHEMA}.chunk_topics VALUES (%s, %s)", (cid, topic))
        conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES ('RJF-TR-1', 'RJF', 'transcript', 1, %s, 'source', NULL)",
                     (IN,))
        for doc_id, seq, text in TURNS:
            conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, %s, 'Q&A', NULL, NULL, '', %s)",
                         (f"{doc_id}#{seq}", doc_id, seq, text))
        yield lambda: psycopg.connect(url, row_factory=dict_row, options=f"-c search_path={SCHEMA}")
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


@pytest.fixture
def db(sub_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", sub_db)
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 40000)


def ids(hits):
    return [h.chunk_id for h in hits]


def merrill_ok(h) -> bool:
    return h.entity_id == "MER" or (h.entity_id == "BAC" and h.segment in ("GWIM", "Merrill"))


def test_merrill_subquestion_only_mer_or_gwim_bac(db):
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    plan = rules_plan(q)
    assert [s.id for s in plan.subquestions] == ["a1.MER", "a1.RJF"]
    hits = search_subquestions(q, plan)
    mer = [h for h in hits if h.part_id == "a1.MER"]
    assert mer and all(merrill_ok(h) for h in mer)
    assert any(h.entity_id == "BAC" for h in mer)                        # GWIM chunks do come in
    assert all(h.entity_id == "RJF" for h in hits if h.part_id == "a1.RJF")


def test_window_applies_in_every_subquestion(db):
    q = resolve("What's new on Raymond James and Morgan Stanley in the last 90 days?", TODAY)
    plan = Plan.from_parts([Part("p1", "t", ["RJF"], "digital advice"), Part("p2", "t", ["MS"], "advisor recruiting"),
                            Part("p3", "t", ["MS", "RJF"], "younger investors")])
    hits = search_subquestions(q, plan)
    assert hits and {h.part_id for h in hits} >= {"p1", "p2"}
    for h in hits:
        assert q.window[0].isoformat() <= h.published_at <= q.window[1].isoformat()
        assert h.date_basis == "source"
    assert not any(h.doc_id.endswith(("-PR-OLD", "-WEB")) for h in hits)


def test_benchmark_scope_holds_in_one_firm_subquestions(db):
    q = resolve("Advisor headcount at Morgan Stanley and Raymond James", TODAY)
    hits = search_subquestions(q, rules_plan(q))
    assert {h.part_id for h in hits} == {"a1.MS", "a1.RJF"} and all(h.source_tier != 4 for h in hits)
    # a one-firm question is no benchmark: there the trade press does come back
    assert any(h.source_tier == 4 for h in search(resolve("Advisor headcount at Morgan Stanley", TODAY)))


def test_every_subquestion_query_keeps_the_hard_filters(db):
    """Captured search_fn: every sub-question query is the resolved query with one firm and its
    words; window, date range, keywords, firm filter, mode, themes and the doc-type scope unchanged."""
    q = fts.apply_filters(resolve("Advisor headcount at Morgan Stanley and Raymond James in the last 90 days", TODAY),
                          date_range=(date(2026, 1, 1), date(2026, 6, 1)), keywords=["advisor"])
    a = [Aspect("a1", "count", "advisor headcount"), Aspect("a2", "definition", "definition includes")]
    plan = Plan(aspects=a, subquestions=subquestions(q, a))
    seen = []

    def fake(sq, **kw):
        seen.append((sq, kw))
        return []
    search_subquestions(q, plan, search_fn=fake, research_fn=lambda q, trace=None: [])
    assert [s.entities for s, _ in seen] == [["MS"], ["MS"], ["RJF"], ["RJF"]]
    for sq, kw in seen:
        assert (sq.window, sq.date_range, sq.keywords, sq.firm_filter, sq.mode, sq.themes) == \
               (q.window, q.date_range, q.keywords, q.firm_filter, q.mode, q.themes)
        assert sq.scope == fts.doc_type_scope(q) and 4 in sq.scope[1]           # benchmark: no trade
        assert kw["tokens"] == settings().subquestion_tokens and kw["research"] is False and kw["peers"] is False
        assert kw["text"] and isinstance(kw["exclude"], set)
    assert [s.terms for s, _ in seen] == ["advisor headcount", "definition includes"] * 2


def test_research_once_and_a_budget_per_subquestion(db, monkeypatch):
    monkeypatch.setenv("SUBQUESTION_TOKENS", "300")
    q = resolve("How are Morgan Stanley, Raymond James, Merrill and Edward Jones serving younger investors?", TODAY)
    assert q.mode == "entity+theme"
    calls = []

    def research_fn(q, trace=None):
        calls.append(q)
        return fts.research_pass(q, trace=trace)
    plan = rules_plan(q)
    assert len(plan.subquestions) == 4
    hits = search_subquestions(q, plan, research_fn=research_fn)
    assert len(calls) == 1
    research = [h for h in hits if h.entity_id is None]
    assert 0 < len(research) <= fts.THEME_K and all(h.part_id == "research" for h in research)
    assert not any(h.entity_id is None for h in hits if h.part_id != "research")
    for s in plan.searched:   # each sub-question its own budget, at most one chunk past it
        own = [h for h in hits if h.part_id == s["id"]]
        assert s["budget"] == 300 and s["tokens"] == round(sum(fts.hit_tokens(h) for h in own))
        assert not own or sum(fts.hit_tokens(h) for h in own) <= 300 + max(fts.hit_tokens(h) for h in own)
    assert len(ids(hits)) == len(set(ids(hits)))


def test_total_grows_with_the_decomposition(db, monkeypatch):
    monkeypatch.setenv("SUBQUESTION_TOKENS", "200")
    q = resolve("How is Raymond James reaching younger investors?", TODAY)
    one = rules_plan(q)
    a = [Aspect("a1", "a", "younger investors advisor"), Aspect("a2", "b", "younger investors digital advice")]
    two = Plan(aspects=a, subquestions=subquestions(q, a))
    search_subquestions(q, one)
    t1 = sum(s["tokens"] for s in one.searched)
    hits = search_subquestions(q, two)
    t2 = sum(s["tokens"] for s in two.searched)
    assert t2 > t1 and len(ids(hits)) == len(set(ids(hits)))                 # no chunk in two


def test_exclude_filters_answer_turns(db):
    q = resolve("How do younger investors pick an advisor at Raymond James?", TODAY)
    assert "RJF-TR-1#1" in ids(search(q))                                # the answer turn is attached
    hits = search(q, exclude={"RJF-TR-1#1"})
    assert "RJF-TR-1#0" in ids(hits) and "RJF-TR-1#1" not in ids(hits)
    hits = search(q, exclude={"RJF-TR-1#0"})
    assert "RJF-TR-1#0" not in ids(hits)


def test_subquestion_ids_and_trace(db):
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    trace, pools = fts.PoolTrace(), {}
    hits = search_subquestions(q, rules_plan(q), trace=trace, part_pools=pools)
    assert {h.part_id for h in hits} <= {"a1.MER", "a1.RJF", "research"}
    assert set(ids(hits)) <= trace.ids() and set(pools) == {"a1.MER", "a1.RJF"}
    assert {h.chunk_id for h in hits if h.part_id == "a1.MER"} <= pools["a1.MER"]


def test_passage_mode_is_one_whole_search(db, monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    plan = planner.plan_question(q, "mock")
    assert len(plan.parts) == 1 and ids(search_subquestions(q, plan)) == ids(search(q))


# --- competitors on a home-firm market question (Q19) -------------------------------------------

def test_competitors_are_subquestions_on_the_theme_only(db):
    q = resolve(Q19, TODAY)
    assert q.entities == ["EDJ"] and q.theme_peers == ["MS", "SCHW", "MER", "RJF"]
    plan = rules_plan(q)
    assert [(s.id, s.role) for s in plan.subquestions] == [
        ("a1.EDJ", "named"), ("a1.MS", "competitor"), ("a1.SCHW", "competitor"),
        ("a1.MER", "competitor"), ("a1.RJF", "competitor")]
    hits = search_subquestions(q, plan)
    comp = [h for h in hits if h.part_id in {"a1.MS", "a1.SCHW", "a1.MER", "a1.RJF"}]
    assert comp and all(h.on_theme for h in comp)
    assert not any(h.doc_id == "MS-10K-OFF" for h in hits)                 # off the theme: never
    assert all(merrill_ok(h) for h in hits if h.part_id == "a1.MER")
    assert not any(h.chunk_id.startswith("RJF-TR-1#1") for h in comp)       # no answer turn attached
    assert not any(h.part_id == "peers" for h in hits)                     # peer_pass not run
    assert "a1" in plan.competitor_floor


def test_floor_across_competitors_drops_the_low_firm(db):
    q = resolve(Q19, TODAY)
    plan = rules_plan(q)
    by_sub = {s.id: [] for s in plan.subquestions}
    mk = lambda cid, rank: fts.Hit(cid, cid.split("#")[0], cid[:3], None, "10-K", 2, "2026-05-01", None,  # noqa: E731
                                   None, None, rank, "younger investors")
    by_sub["a1.MS"] = [mk("MS-A#0", 10.0), mk("MS-A#1", 9.0)]
    by_sub["a1.MER"] = [mk("MER-A#0", 1.0)]                                  # its best < 0.3 x 9.0
    plan.searched = [{"id": s.id, "floor_dropped": [], "floor_emptied": False} for s in plan.subquestions]
    planner._competitor_floor(plan, by_sub)
    entry = {e["id"]: e for e in plan.searched}
    assert by_sub["a1.MER"] == [] and entry["a1.MER"]["floor_emptied"] is True
    assert entry["a1.MER"]["floor_dropped"] == ["MER-A#0"] and len(by_sub["a1.MS"]) == 2
    assert plan.competitor_floor["a1"] == pytest.approx(fts.FLOOR * 9.0)


def test_floor_emptied_subquestion_reads_as_nothing_found():
    from cee.answer.llm import KEPT_ELSEWHERE, NO_PASSAGES, build_user_message
    from cee.answer.validate import _part_pools
    q = resolve(Q19, TODAY)
    plan = rules_plan(q)
    plan.searched = [{"id": s.id, "pool": 7, "floor_emptied": s.id == "a1.MER"} for s in plan.subquestions]
    msg = build_user_message(q.question, [], plan)
    mer = msg.split("Part a1.MER")[1].splitlines()[1]
    assert mer == NO_PASSAGES and KEPT_ELSEWHERE in msg                       # MS etc.: pool 7
    assert _part_pools(plan)["a1.MER"] == 0 and _part_pools(plan)["a1.MS"] == 7


# --- search_fn seam and the corrective re-search hook ------------------------------------------

def test_search_fn_is_used_for_every_subquestion(db):
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    plan = rules_plan(q)
    used = []

    def wrapped(sq, **kw):
        used.append(kw["text"])
        return search(sq, **{k: v for k, v in kw.items() if k != "text"})
    hits = search_subquestions(q, plan, search_fn=wrapped)
    assert used == [s.text for s in plan.subquestions] and hits


def test_corrective_search_keeps_filters_and_the_exclude_set(db):
    q = resolve("What's new on Merrill in the last 90 days?", TODAY)
    plan = rules_plan(q)
    first = search_subquestions(q, plan)
    used = {h.chunk_id for h in first}
    again = planner.corrective_search(q, plan, "a1.MER", "digital advice payout grid", used)
    assert not used & set(ids(again))
    for h in again:
        assert merrill_ok(h) and q.window[0].isoformat() <= h.published_at <= q.window[1].isoformat()
        assert h.part_id == "a1.MER"
    seen = []
    planner.corrective_search(q, plan, "a1.MER", "payout ratio", used,
                              search_fn=lambda sq, **kw: seen.append((sq, kw)) or [])
    sq, kw = seen[0]
    assert q.question in sq.terms and "payout ratio" not in sq.terms        # rule-plan words + guard
    assert kw["exclude"] == used and sq.window == q.window and sq.entities == ["MER"]
    assert sq.scope == fts.doc_type_scope(q)
    with pytest.raises(ValueError):
        planner.corrective_search(q, plan, "a9.XX", "w", set())


def test_corrective_search_on_a_competitor_keeps_the_theme_and_floor(db):
    q = resolve(Q19, TODAY)
    plan = rules_plan(q)
    search_subquestions(q, plan)
    seen = []
    planner.corrective_search(q, plan, "a1.MS", "next-gen clients", set(),
                              search_fn=lambda sq, **kw: seen.append(sq) or [])
    assert seen[0].on_theme_only is True and seen[0].entities == ["MS"]
    plan.competitor_floor["a1"] = 1e9                                           # nothing passes
    assert planner.corrective_search(q, plan, "a1.MS", "younger", set()) == []


def test_neighbour_guard_keeps_dividend_payout_out_of_a_pay_subquestion(db, sub_db):
    """#224: #214's Q25 Schwab + RJF part searched "payout ratio" and pulled Schwab's "dividend
    payout range" deck chunks in. With the guarded words the chunk is no candidate at all."""
    with sub_db() as conn:
        conn.execute("INSERT INTO documents VALUES ('SCHW-DECK-DIV', 'SCHW', 'deck', 2, %s, 'source', NULL)", (IN,))
        conn.execute("INSERT INTO chunks VALUES ('SCHW-DECK-DIV#0', 'SCHW-DECK-DIV', 0, 'Document', NULL, NULL, '', "
                     "'Support ongoing business growth. Common dividend payout range. Our capital ratios remained strong.')")
        conn.commit()
    try:
        q = resolve("What has Schwab disclosed about advisor compensation structures?", TODAY)
        words = ("advisor compensation payout ratio affiliation transition assistance compensation and "
                 "benefits expense salary bonus commissions independent advisors employee advisors")
        guarded, dropped = planner.strip_neighbours(words, q.question)
        assert dropped == ["payout ratio"]
        pools = {}
        for pid, w in (("raw", words), ("guarded", guarded)):
            part_pools = {}
            search_subquestions(q, Plan.from_parts([Part("p1", "t", ["SCHW"], w)]), part_pools=part_pools)
            pools[pid] = part_pools["p1"]
        assert "SCHW-DECK-DIV#0" in pools["raw"]
        assert "SCHW-DECK-DIV#0" not in pools["guarded"]
    finally:
        with sub_db() as conn:
            conn.execute("DELETE FROM chunks WHERE doc_id = 'SCHW-DECK-DIV'")
            conn.execute("DELETE FROM documents WHERE doc_id = 'SCHW-DECK-DIV'")
            conn.commit()
