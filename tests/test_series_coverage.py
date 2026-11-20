"""#247 part 2 (plans/0247-reduce-2.md sections 2-4): per-period sub-search, pinned registered chunks,
basis breaks, gap scope (Q19), `asked_firms`. Fakes only; the fetch_pinned tests use the database and
skip without one. 0 paid calls."""
import datetime as dt

import psycopg
import pytest

from cee.answer import matrix as mx
from cee.answer.matrix import Cell, EvidenceMatrix, Item
from cee.config import settings
from cee.retrieve import fts, planner
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Aspect, Plan, SubQuestion

NO_SOURCES = lambda entity: ""   # noqa: E731
AS_OF = dt.date(2026, 11, 17)
Q23 = "Advisor headcount over the last eight quarters across the five."


def H(cid, entity="EDJ", origin="search"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-03-13", period_end="2025-12-31", section=None, page=None,
               rank=1.0, text="t", origin=origin)


# --- per-period sub-search -------------------------------------------------------------------------

def test_period_pass_one_call_per_asked_period_excluding_kept_chunks_main_lists_unchanged(monkeypatch):
    series = Aspect("a1", "Advisor headcount over the last eight quarters.", "advisor headcount",
                    metric=None, kind="series")
    plan = Plan(aspects=[series], subquestions=[SubQuestion("a1.EDJ", "EDJ", series)])
    calls = []

    def fake(q, trace=None, tokens=None, exclude=None, research=True, peers=True, text=None, k=None):
        if q.period_range is None:
            return [H("EDJ-10K-2025#58"), H("EDJ-10K-2025#70"), H("EDJ-10K-2025#202")]
        calls.append((q.period_range, tuple(q.exclude_ids), k, q.entities))
        if q.period_range == (dt.date(2025, 10, 1), dt.date(2025, 12, 31)):
            # the pool already lost the kept chunks in SQL: the next three are new
            return [H("EDJ-10K-2025#130"), H("EDJ-10K-2025#142"), H("EDJ-10K-2025#148")]
        return []
    monkeypatch.setattr(fts, "budget_tokens", lambda q: 40000)
    q = Query(question=Q23, entities=["EDJ"])
    hits = planner.search_subquestions(q, plan, search_fn=fake, research_fn=lambda q, trace=None: [], as_of=AS_OF)
    assert len(calls) == 8 and all(c[2] == planner.PERIOD_K and c[3] == ["EDJ"] for c in calls)
    assert all({"EDJ-10K-2025#58", "EDJ-10K-2025#70", "EDJ-10K-2025#202"} <= set(c[1]) for c in calls)
    assert [h.chunk_id for h in hits if h.origin == "search"] == ["EDJ-10K-2025#58", "EDJ-10K-2025#70",
                                                                  "EDJ-10K-2025#202"]
    assert [h.chunk_id for h in hits if h.origin == "period"] == ["EDJ-10K-2025#130", "EDJ-10K-2025#142",
                                                                  "EDJ-10K-2025#148"]
    assert {"EDJ-10K-2025#130"} <= plan.pools["a1.EDJ"]
    assert plan.searched[0]["period_hits"][0] == "2025Q4:EDJ-10K-2025#130"


@pytest.mark.parametrize("question, kind", [
    ("Net new assets by quarter across the five.", "series"),        # no asked periods (Q22)
    ("Advisor headcount over the last eight quarters across the five.", "fact"),   # not a series
])
def test_no_period_pass_without_asked_periods_or_series(monkeypatch, question, kind):
    a = Aspect("a1", "x", kind=kind)
    plan = Plan(aspects=[a], subquestions=[SubQuestion("a1.EDJ", "EDJ", a)])
    seen = []

    def fake(q, **kw):
        seen.append(q.period_range)
        return []
    monkeypatch.setattr(fts, "budget_tokens", lambda q: 40000)
    planner.search_subquestions(Query(question=question, entities=["EDJ"]), plan, search_fn=fake,
                                research_fn=lambda q, trace=None: [], as_of=AS_OF)
    assert seen == [None]


def test_window_question_gets_no_period_pass(monkeypatch):
    a = Aspect("a1", "x", kind="series")
    plan = Plan(aspects=[a], subquestions=[SubQuestion("a1.RJF", "RJF", a)])
    seen = []
    monkeypatch.setattr(fts, "budget_tokens", lambda q: 40000)
    q = Query(question="Advisor headcount over the last eight quarters?", entities=["RJF"],
              window=(dt.date(2026, 8, 19), dt.date(2026, 11, 17)))
    planner.search_subquestions(q, plan, search_fn=lambda q, **kw: seen.append(q.period_range) or [],
                                research_fn=lambda q, trace=None: [], as_of=AS_OF)
    assert seen == [None]


def test_filters_sql_period_end_and_exclusion_clauses():
    sql, params = fts.filters_sql(Query(question="x", period_range=(dt.date(2025, 10, 1), dt.date(2025, 12, 31)),
                                        exclude_ids=["A#1"]))
    assert "d.period_end BETWEEN %(pr_from)s AND %(pr_to)s" in sql and "c.chunk_id <> ALL(%(excl_ids)s)" in sql
    assert params["pr_to"] == dt.date(2025, 12, 31) and params["excl_ids"] == ["A#1"]
    assert fts.filters_sql(Query(question="x"))[0] == "TRUE"


def test_period_bounds():
    assert planner._period_bounds("2025Q4") == (dt.date(2025, 10, 1), dt.date(2025, 12, 31))
    assert planner._period_bounds("2026Q1") == (dt.date(2026, 1, 1), dt.date(2026, 3, 31))
    assert planner._period_bounds("2024") == (dt.date(2024, 1, 1), dt.date(2024, 12, 31))


# --- pinned registered chunks (database) ---------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            n = conn.execute("SELECT count(*) FROM chunks WHERE chunk_id = 'BAC-SUPP-2023Q4#2'").fetchone()[0]
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not n:
        pytest.skip("no corpus loaded")


def test_fetch_pinned_entity_filter_adv_allowed_tier4_and_window_applied(db):
    bench = Query(question=Q23, entities=["MER"], scope=(["adv"], [4]))
    got = [h.chunk_id for h in fts.fetch_pinned(bench, ["BAC-SUPP-2023Q4#2", "BAC-DECK-2025-investor-day#13",
                                                        "MER-ADV1A-2026#1", "MS-SUPP-2020Q4#1"])]
    assert got == ["BAC-SUPP-2023Q4#2", "MER-ADV1A-2026#1"]   # GWIM segment yes, NULL segment no, other firm no
    trade = Query(question=Q23, entities=["MS"], scope=(["adv"], [4]))
    assert [h.chunk_id for h in fts.fetch_pinned(trade, ["MS-TRADE-2026-09-16-IN-01#0", "MS-ADV1A-2026#1"])] \
        == ["MS-ADV1A-2026#1"]   # tier 4 stays excluded, adv allowed (D1 narrowed)
    window = Query(question="What's new on Raymond James in the last 90 days?", entities=["RJF"],
                   window=(dt.date(2026, 8, 19), dt.date(2026, 11, 17)))
    assert fts.fetch_pinned(window, ["RJF-10K-2025#228"]) == []
    assert all(h.origin == "pinned" for h in fts.fetch_pinned(bench, ["BAC-SUPP-2023Q4#2"]))


# --- asked_firms and the gap scope (Q19) ------------------------------------------------------------------

def test_validate_plan_records_asked_firms_before_the_home_firm_widening():
    q = Query(question="How should the preferences of younger investors shape Edward Jones's offerings?",
              entities=["EDJ"], theme_peers=["MS", "SCHW"], mode="entity+theme", themes=["clients"])
    aspects, notes = planner.validate_plan({"aspects": [
        {"text": "EDJ priorities", "keyword_query": "priorities", "firms": ["EDJ"], "metric": "", "kind": "fact",
         "proxy": False},
        {"text": "Preferences", "keyword_query": "preferences", "firms": [], "metric": "", "kind": "fact",
         "proxy": False}]}, q)
    assert aspects[0].firms == [] and aspects[0].asked_firms == ["EDJ"]
    assert aspects[1].firms == [] and aspects[1].asked_firms == []


def C(cid, label, role="named", items=()):
    a, e = cid.split(".")
    return Cell(cid, None if e == "research" else e, a, "research" if e == "research" else role, label,
                items=list(items))


def test_q19_shaped_gaps_only_inside_the_aspect_scope_and_competitors_folded():
    own = Aspect("a7", "How does Edward Jones management describe younger investors?", asked_firms=["EDJ"])
    pref = Aspect("a1", "What preferences do younger investors state?")
    cells = [C("a7.EDJ", "not_found"), C("a7.MS", "not_found", "competitor"), C("a7.SCHW", "not_found", "competitor"),
             C("a7.research", "not_found"),
             C("a1.EDJ", "not_found"), C("a1.MS", "not_found", "competitor"), C("a1.RJF", "not_disclosed", "competitor"),
             C("a1.SCHW", "different_quantity", "competitor", [Item("t", chunk_ids=["S#1"])]),
             C("a1.research", "fact", items=[Item("t", chunk_ids=["R#1"])])]
    m = EvidenceMatrix("How should the preferences of younger investors shape Edward Jones's offerings?", rows=[],
                       aspects=[pref, own], cells={c.id: c for c in cells})
    mx.finish(m, sources=NO_SOURCES)
    ids = [g["id"] for g in m.gaps]
    assert "a7.EDJ" in ids and not {"a7.MS", "a7.SCHW", "a7.research"} & set(ids)
    assert "a1.EDJ" in ids and "a1.SCHW" in ids and not {"a1.MS", "a1.RJF"} & set(ids)
    fold = next(g for g in m.gaps if g["label"] == "competitors_not_found")
    assert fold["id"] == "a1" and fold["what"].startswith("Competitors (Morgan Stanley, Raymond James")
    assert fold["cells"] == ["a1.MS", "a1.RJF"]


def test_benchmark_named_cells_keep_one_gap_per_firm():
    a = Aspect("a1", "How each firm defines advisor headcount.", metric="advisor_headcount")
    cells = [C(f"a1.{f}", "not_found") for f in ("MS", "SCHW", "EDJ")] + [C("a1.RJF", "fact", items=[Item("t", chunk_ids=["R#1"])])]
    m = mx.finish(EvidenceMatrix("How does each of the five define advisor headcount?", rows=[], aspects=[a],
                                 cells={c.id: c for c in cells}), sources=NO_SOURCES)
    assert [g["id"] for g in m.gaps if g["label"] == "not_found"] == ["a1.MS", "a1.SCHW", "a1.EDJ"]
    assert not any(g["label"] == "competitors_not_found" for g in m.gaps)


# --- basis breaks ---------------------------------------------------------------------------------------

def it(value, period, scope=""):
    return Item(text="t", quote="q", chunk_ids=["X#1"], value=value, period=period, scope=scope)


def test_q23_edj_shaped_basis_break_lists_each_basis_with_its_periods():
    a = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
    c = C("a1.EDJ", "fact", items=[it("20,514", "2026Q2"), it("19,674", "2026Q1", "U.S."), it("876", "2026Q1", "Canada"),
                             it("20,429", "2025Q3")])
    m = mx.finish(EvidenceMatrix(Q23, rows=[], aspects=[a], cells={c.id: c}), sources=NO_SOURCES)
    assert "basis_break" in m.cells["a1.EDJ"].flags and len(m.breaks) == 1
    cav = m.breaks[0]["caveat"]
    assert cav.startswith("Edward Jones - Advisor headcount over the last eight quarters: the figures cover different "
                          "bases") and "whole firm: 2025Q3, 2026Q2" in cav and "U.S.: 2026Q1" in cav
    assert cav in m.caveats


@pytest.mark.parametrize("items, kind, expected", [
    ([it("100", "2025Q3"), it("120", "2025Q4")], "series", 0),                         # one basis
    ([it("$66", "2025Q3", "Wealth Management"), it("$70", "2025Q4", "Wealth Management")], "series", 0),   # Q22 flow
    ([it("$66", "2025Q3", "Wealth Management"), it("$70", "2025Q4", "Firm")], "series", 1),
    ([it("100", "2025Q3"), it("90", "2025Q4", "U.S.")], "recency", 0),
])
def test_basis_break_cases(items, kind, expected):
    a = Aspect("a1", "Net new assets by quarter.", metric="net_new_assets", kind=kind)
    c = C("a1.MS", "fact", items=items)
    m = mx.finish(EvidenceMatrix("Net new assets by quarter across the five.", rows=[], aspects=[a],
                                 cells={c.id: c}), sources=NO_SOURCES)
    assert len(m.breaks) == expected


# --- #247 part 2 revision (R3, R5, R6) -----------------------------------------------------------------

def test_r3_unkeyed_items_join_their_scope_and_undated_ones_make_no_basis(monkeypatch):
    a = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
    keyed = Item(text="t", quote="q", chunk_ids=["X#1"], value="8,943", period="2025-09-30", population="rjf_x")
    split = Item(text="t", quote="q", chunk_ids=["X#2"], value="3,878", period="2025-09-30")
    pcg = Item(text="t", quote="q", chunk_ids=["X#3"], value="approximately 9,000", scope="domestic wealth management")
    c = C("a1.RJF", "fact", items=[keyed, split, pcg])
    monkeypatch.setattr(mx, "tag_populations", lambda m: None)   # keep the hand-set keys
    m = mx.finish(EvidenceMatrix(Q23, rows=[], aspects=[a], cells={c.id: c}), sources=NO_SOURCES)
    assert m.breaks == []
    us = Item(text="t", quote="q", chunk_ids=["X#4"], value="19,674", period="2026Q1", scope="U.S.")
    c2 = C("a1.EDJ", "fact", items=[Item(text="t", quote="q", chunk_ids=["X#5"], value="20,514", period="2026Q2",
                                         population="edj_firm"), us])
    m2 = mx.finish(EvidenceMatrix(Q23, rows=[], aspects=[a], cells={c2.id: c2}), sources=NO_SOURCES)
    assert len(m2.breaks) == 1   # a dated U.S. point under another scope keeps the EDJ break


def test_r5_definition_wording_change_across_documents():
    a = Aspect("a1", "Net new assets by quarter.", metric="net_new_assets", kind="series")
    c = C("a1.EDJ", "fact", items=[
        Item(text="t", chunk_ids=["EDJ-10K-2025#130"], value="$74", period="2025", definition="Net new assets represents "
             "cash and securities inflows and outflows, excluding mutual fund capital gain distributions."),
        Item(text="t", chunk_ids=["EDJ-10Q-2026Q2#60"], value="$20", period="2026Q2", definition="Net new assets "
             "represents cash and securities inflows and outflows, including fees and commissions and excluding ...")])
    m = mx.finish(EvidenceMatrix("Net new assets by quarter for each of the five.", rows=["EDJ"], aspects=[a],
                                 cells={c.id: c}), sources=NO_SOURCES)
    cav = [x for x in m.caveats if "definition wording differs" in x]
    assert len(cav) == 1 and "EDJ-10K-2025" in cav[0] and "EDJ-10Q-2026Q2" in cav[0]


def test_r6a_definitions_by_firm_named_without_a_comparison_aspect():
    a = Aspect("a1", "How each firm defines advisor headcount.", metric="advisor_headcount")
    cells = [C(f"a1.{f}", "fact", items=[Item(text="t", chunk_ids=[f"{f}#1"])]) for f in ("MS", "EDJ", "RJF")] \
        + [C("a1.SCHW", "different_quantity", items=[Item(text="Form ADV: 4,127 employees perform advisory functions",
                                                          chunk_ids=["SCHW#1"])])]
    m = mx.finish(EvidenceMatrix("How does each of the five define advisor headcount?", rows=["MS", "EDJ", "RJF", "SCHW"],
                                 aspects=[a], cells={c.id: c for c in cells}), sources=NO_SOURCES)
    cav = [x for x in m.caveats if x.startswith("Advisor headcount as each firm defines it:")]
    assert len(cav) == 1
    for name in ("Morgan Stanley:", "Edward Jones:", "Raymond James Financial:", "The Charles Schwab Corporation:"):
        assert name in cav[0]
    assert "excludes advisors in the RCS division" in cav[0]
    assert "publishes no count of this metric; reports a related figure instead" in cav[0]   # #247 part 3 item 2
    assert "publishes no definition of this metric" not in cav[0]
    assert not any(x.startswith("Advisor headcount: the firms define it differently") for x in m.caveats)
    gap = next(g for g in m.gaps if g["id"] == "a1.SCHW")
    assert "the closest disclosed figure is Form ADV: 4,127 employees perform advisory functions (adjacent)" in gap["what"]


def test_r6c_series_span_per_holding_firm():
    a = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
    ms = C("a1.MS", "fact", items=[it("15,950", "2020-12-31"), it("15,469", "2020-09-30"), it("15,468", "2019-12-31")])
    edj = C("a1.EDJ", "fact", items=[it("20,514", "2026Q2"), it("20,425", "2025-12-31"), it("x", "")])
    m = mx.finish(EvidenceMatrix(Q23, rows=["MS", "EDJ"], aspects=[a], cells={"a1.MS": ms, "a1.EDJ": edj}),
                  sources=NO_SOURCES)
    spans = [x for x in m.caveats if "the series in the documents searched runs from" in x]
    assert ("Morgan Stanley - Advisor headcount over the last eight quarters: the series in the documents searched "
            "runs from 2019-12-31 to 2020-12-31 (3 points); no figure after 2020-12-31 was found.") in spans
    assert any(s.startswith("Edward Jones") and "from 2025-12-31 to 2026Q2 (2 points)" in s for s in spans)


# --- PR #261 review round 1 (fixes 1, 2) ---------------------------------------------------------------

def test_registry_list_items_are_plain_text():
    import yaml

    from cee.config import REPO_ROOT
    defs = yaml.safe_load((REPO_ROOT / "config" / "metric_definitions.yaml").read_text(encoding="utf-8"))["definitions"]
    for d in defs:
        for k in ("includes", "excludes", "not_stated", "see_also", "looked_in"):
            for x in d.get(k) or []:
                assert isinstance(x, str), (d["entity"], d["metric"], k, x)
                assert x.count("(") == x.count(")"), (d["entity"], d["metric"], k, x)   # not split at a comma


def _hit(cid, doc_type):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id="EDJ", segment=None, doc_type=doc_type,
               source_tier=2, published_at="2026-08-07", period_end="2026-06-26", section=None, page=None, rank=1.0,
               text="t")


def test_r5_q22_shaped_definition_aspect_fires_across_10k_and_10q():
    series = Aspect("a1", "Net new assets by quarter, as each firm reports the metric.", metric="net_new_assets",
                    kind="series")
    defs = Aspect("a2", "Each firm's own definition of its net new assets metric.")
    c1 = C("a1.EDJ", "fact", items=[Item(text="t", chunk_ids=["EDJ-10Q-2026Q2#60"], value="18", period="2026Q2")])
    c2 = C("a2.EDJ", "fact", items=[
        Item(text="t", chunk_ids=["EDJ-10Q-2026Q2#60"], definition="Net new assets represents cash and securities "
             "inflows and outflows, including fees and commissions and excluding mutual fund distributions."),
        Item(text="t", chunk_ids=["EDJ-10K-2025#130"], definition="Net new assets represents cash and securities "
             "inflows and outflows, excluding mutual fund capital gain distributions.")])
    m = EvidenceMatrix("Net new assets by quarter for each of the five, with each firm's own definition.",
                       rows=["EDJ"], aspects=[series, defs], cells={c1.id: c1, c2.id: c2})
    m.hits = {"EDJ-10Q-2026Q2#60": _hit("EDJ-10Q-2026Q2#60", "10-Q"), "EDJ-10K-2025#130": _hit("EDJ-10K-2025#130", "10-K")}
    mx.finish(m, sources=NO_SOURCES)
    assert len([x for x in m.caveats if "definition wording differs" in x]) == 1


def test_r5_no_merrill_false_positive_from_a_different_quantity_cell_or_another_doc_family():
    a = Aspect("a3", "Number of financial advisors.", metric="advisor_headcount", proxy=True)
    dq = C("a3.MER", "different_quantity", items=[
        Item(text="t", chunk_ids=["BAC-SUPP-2023Q4#2"], definition="Includes advisors across all wealth management "
             "businesses in GWIM and Consumer Banking."),
        Item(text="t", chunk_ids=["MER-ADV1A-2026#1"], definition="full- and part-time employees, excluding clerical")])
    m = EvidenceMatrix("Client assets per advisor across the five?", rows=["MER"], aspects=[a], cells={dq.id: dq})
    m.hits = {"BAC-SUPP-2023Q4#2": _hit("BAC-SUPP-2023Q4#2", "supplement"), "MER-ADV1A-2026#1": _hit("MER-ADV1A-2026#1", "adv")}
    mx.finish(m, sources=NO_SOURCES)
    assert not any("definition wording differs" in x for x in m.caveats)
    dq.label = "fact"   # even as facts: a supplement footnote and Form ADV wording are not like-for-like
    mx.finish(m, sources=NO_SOURCES)
    assert not any("definition wording differs" in x for x in m.caveats)
