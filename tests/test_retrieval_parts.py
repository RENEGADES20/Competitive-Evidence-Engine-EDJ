"""Per-part search of a question plan (#214, ADR-020) on fixture rows in a throwaway schema of the
local Postgres (skipped if it is down): every hard filter in every part, research and theme peers
once per question, the token budget split, no chunk twice, and a one-part plan = search(q)."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts, planner
from cee.retrieve.fts import resolve, search
from cee.retrieve.planner import Part, Plan, rules_plan, search_parts

SCHEMA = "test_retrieval_parts"
TODAY = date(2026, 6, 1)
IN, OUT = date(2026, 5, 1), date(2025, 12, 1)
WORDS = "younger investors prefer digital advice and advisor recruiting"
DOCS = [  # doc_id, entity_id, doc_type, tier, published, basis, topic, chunks, segment, words
    *[(f"{e}-10K-{i}", e, "10-K", 2, IN, "source", None, 3, None, WORDS)
      for e in ("MS", "RJF", "EDJ", "SCHW", "MER") for i in range(2)],
    *[(f"{e}-PR-OLD", e, "press", 2, OUT, "source", None, 2, None, WORDS) for e in ("MS", "RJF")],
    *[(f"{e}-WEB", e, "web", 3, IN, "retrieved", None, 2, None, WORDS) for e in ("MS", "RJF")],
    ("BAC-10K-GWIM", "BAC", "10-K", 2, IN, "source", None, 3, "GWIM", WORDS),
    ("BAC-10K-CONS", "BAC", "10-K", 2, IN, "source", None, 3, "Consumer Banking", WORDS),
    ("BAC-10K-NOSEG", "BAC", "10-K", 2, IN, "source", None, 3, None, WORDS),
    # research on the theme, long chunks: 4 of them (THEME_K) outweigh a part's share below
    ("SURVEY-A", None, "research", 5, IN, "source", "younger_investors", 4, None, WORDS + " survey" * 60),
    ("SURVEY-B", None, "research", 5, IN, "source", "younger_investors", 4, None, WORDS + " study" * 60),
    # benchmark question: trade press is left out in every part
    *[(f"{e}-TRADE", e, "trade", 4, IN, "source", None, 2, None, "advisor headcount rose") for e in ("MS", "RJF")],
    *[(f"{e}-10Q-HC", e, "10-Q", 2, IN, "source", None, 2, None, "advisor headcount rose") for e in ("MS", "RJF")],
]
TURNS = [  # a call: analyst question turn, management answer turn (#203)
    ("RJF-TR-1", 0, "Jane Analyst, Example Securities\n\nHow do younger investors pick an advisor?"),
    ("RJF-TR-1", 1, "Paul Example - Chief Executive Officer\n\nThey want digital tools and a human advisor."),
]


@pytest.fixture(scope="module")
def parts_db():
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
def db(parts_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", parts_db)
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 40000)


def ids(hits):
    return [h.chunk_id for h in hits]


def merrill_ok(h) -> bool:
    return h.entity_id == "MER" or (h.entity_id == "BAC" and h.segment in ("GWIM", "Merrill"))


def test_merrill_part_only_mer_or_gwim_bac(db):
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    plan = rules_plan(q, cap=4)
    assert [p.firms for p in plan.parts] == [["MER"], ["RJF"]]
    hits = search_parts(q, plan)
    mer = [h for h in hits if h.part_id == "p1"]
    assert mer and all(merrill_ok(h) for h in mer)
    assert any(h.entity_id == "BAC" for h in mer)                        # GWIM chunks do come in
    assert all(h.entity_id == "RJF" for h in hits if h.part_id == "p2")


def test_window_applies_in_every_part(db):
    q = resolve("What's new on Raymond James and Morgan Stanley in the last 90 days?", TODAY)
    plan = Plan(parts=[Part("p1", "t", ["RJF"], "digital advice"), Part("p2", "t", ["MS"], "advisor recruiting"),
                       Part("p3", "t", ["MS", "RJF"], "younger investors")])
    hits = search_parts(q, plan)
    assert hits and {h.part_id for h in hits} >= {"p1", "p2"}
    for h in hits:
        assert q.window[0].isoformat() <= h.published_at <= q.window[1].isoformat()
        assert h.date_basis == "source"
    assert not any(h.doc_id.endswith(("-PR-OLD", "-WEB")) for h in hits)


def test_benchmark_scope_holds_in_one_firm_parts(db):
    q = resolve("Advisor headcount at Morgan Stanley and Raymond James", TODAY)
    hits = search_parts(q, rules_plan(q, cap=4))
    assert {h.part_id for h in hits} == {"p1", "p2"} and all(h.source_tier != 4 for h in hits)
    # a one-firm question is no benchmark: there the trade press does come back
    assert any(h.source_tier == 4 for h in search(resolve("Advisor headcount at Morgan Stanley", TODAY)))


@pytest.mark.parametrize("question", [
    "How should the preferences of younger investors shape Edward Jones's offerings?",   # peers (Q19-like)
    "How are these five reaching younger investors?",                                   # five firms > cap
    "What is Raymond James saying about younger investors?",                             # one firm
    "What's new on Raymond James in the last 90 days?",                                  # window
])
def test_one_part_plan_is_search(db, question):
    q = resolve(question, TODAY)
    plan = rules_plan(q, cap=4)
    assert len(plan.parts) == 1
    hits = search_parts(q, plan)
    assert ids(hits) == ids(search(resolve(question, TODAY)))


def test_passage_mode_is_one_whole_search(db, monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    plan = planner.plan_question(q, "mock")
    assert len(plan.parts) == 1 and ids(search_parts(q, plan)) == ids(search(q))


def test_research_once_and_budget_bound(db, monkeypatch):
    # 4 parts, a small budget: each part's share is below the THEME_K research chunks' tokens
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 500)
    q = resolve("How are Morgan Stanley, Raymond James, Merrill and Edward Jones serving younger investors?", TODAY)
    assert q.mode == "entity+theme"
    plan = rules_plan(q, cap=4)
    assert len(plan.parts) == 4
    hits = search_parts(q, plan)
    research = [h for h in hits if h.entity_id is None]
    tok = fts.hit_tokens
    r_tokens = sum(tok(h) for h in research)
    total = fts.budget_tokens(q)
    assert 0 < len(research) <= fts.THEME_K and all(h.part_id == "research" for h in research)
    assert all(s["share"] < r_tokens for s in plan.searched)               # shares below the research
    assert not any(h.entity_id is None for h in hits if h.part_id not in ("research", "peers"))
    budgeted = [h for h in hits if h.part_id != "peers"]
    assert sum(tok(h) for h in budgeted) <= max(total, r_tokens) + max(tok(h) for h in budgeted)
    assert len(ids(hits)) == len(set(ids(hits)))


def test_no_chunk_in_two_parts_even_with_the_same_firm(db):
    q = resolve("How is Raymond James reaching younger investors?", TODAY)
    plan = Plan(parts=[Part("p1", "a", ["RJF"], "younger investors advisor"),
                       Part("p2", "b", ["RJF"], "younger investors digital advice")])
    hits = search_parts(q, plan)
    assert {h.part_id for h in hits} >= {"p1"} and len(ids(hits)) == len(set(ids(hits)))


def test_exclude_filters_answer_turns(db):
    q = resolve("How do younger investors pick an advisor at Raymond James?", TODAY)
    assert "RJF-TR-1#1" in ids(search(q))                                # the answer turn is attached
    hits = search(q, exclude={"RJF-TR-1#1"})
    assert "RJF-TR-1#0" in ids(hits) and "RJF-TR-1#1" not in ids(hits)
    hits = search(q, exclude={"RJF-TR-1#0"})
    assert "RJF-TR-1#0" not in ids(hits)


def test_part_ids_and_trace(db):
    q = resolve("How do Merrill and Raymond James approach younger investors?", TODAY)
    trace, pools = fts.PoolTrace(), {}
    hits = search_parts(q, rules_plan(q, cap=4), trace=trace, part_pools=pools)
    assert {h.part_id for h in hits} <= {"p1", "p2", "research", "peers"}
    assert set(ids(hits)) <= trace.ids() and set(pools) == {"p1", "p2"}
    assert {h.chunk_id for h in hits if h.part_id == "p1"} <= pools["p1"]
