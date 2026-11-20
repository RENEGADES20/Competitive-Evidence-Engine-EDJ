"""#247 part 3 (plans/0247-reduce-3.md): the code-built contrast of the definitions, the unit-aware
related-metric wording, quarter holes and span segments, years in the dedupe, per-firm gap sources and
the basis-break rules (undated items, same-date splits). Fakes and the registry; the verbatim check uses
the database and skips without one. 0 paid calls."""
import datetime as dt
import re
import unittest.mock as um

import psycopg
import pytest
import yaml

from cee.answer import matrix as mx
from cee.answer import reduce as R
from cee.answer import validate
from cee.answer.matrix import Cell, EvidenceMatrix, Item
from cee.answer.schema import Answer, Claim
from cee.config import REPO_ROOT, settings
from cee.retrieve.fts import Query
from cee.retrieve.planner import Aspect

NO_SOURCES = lambda entity: ""   # noqa: E731
AS_OF = dt.date(2026, 11, 17)
FIVE = ["MS", "SCHW", "EDJ", "MER", "RJF"]
Q11 = "How does each of the five define and report advisor headcount -- and what does each definition include or exclude?"
Q22 = "Net new assets by quarter for each of the five, with each firm's own definition of the metric."
Q23 = "Advisor headcount over the last eight quarters across the five."


def C(cid, label, role="named", items=()):
    a, e = cid.split(".")
    return Cell(cid, e, a, role, label, items=list(items))


def it(value, period, scope="", population=""):
    return Item(text="t", quote="q", chunk_ids=["X#1"], value=value, period=period, scope=scope, population=population)


# --- item 1: contrast of the definitions -----------------------------------------------------------------

Q11_ASPECTS = [Aspect("a1", "How each firm defines advisor headcount.", metric="advisor_headcount"),
               Aspect("a2", "How each firm reports advisor headcount.", metric="advisor_headcount"),
               Aspect("a3", "What each firm's advisor headcount definition includes.", metric="advisor_headcount"),
               Aspect("a4", "What each firm's advisor headcount definition excludes.", metric="advisor_headcount")]


def _matrix(question, aspects, rows=FIVE):
    cells = [C(f"{a.id}.{f}", "fact", items=[Item(text="t", chunk_ids=[f"{f}#1"])]) for a in aspects for f in rows]
    return mx.finish(EvidenceMatrix(question, rows=list(rows), aspects=aspects, cells={c.id: c for c in cells}),
                     sources=NO_SOURCES)


def _contrast(m):
    return [x for x in m.caveats if x.startswith("Advisor headcount, how the definitions differ - ")]


def test_contrast_one_caveat_per_dimension_every_firm_placed_one_block():
    cav = _contrast(_matrix(Q11, Q11_ASPECTS))
    labels = [c.split(" - ", 1)[1].split(":", 1)[0] for c in cav]
    assert labels == ["Written definition", "Independent contractor advisors",
                      "Business lines in the count", "Date of the registered count"]   # one block, in order;
    # trainees: every firm not stated (RJF #228 explains a change in the count, not who is counted) -> skipped
    for c in cav:
        for name in ("Morgan Stanley", "The Charles Schwab Corporation", "Edward Jones",
                     "Merrill (Bank of America Corporation)", "Raymond James Financial"):
            assert c.count(name) == 1, (name, c)
        assert "last" not in c.lower() and "wider" not in c.lower()
    ind = cav[1]
    assert ("stated by Edward Jones ('The Partnership’s financial advisors are employees or partners of the "
            "Partnership.', EDJ-10K-2025#35)") in ind
    assert "counted by Raymond James Financial ('Independent contractors 5,065', RJF-10K-2025#227)" in ind
    assert "not stated by Morgan Stanley, Merrill (Bank of America Corporation)" in ind
    assert "publishes no count of this metric; reports a related figure instead at The Charles Schwab" in cav[0]
    assert "dated for Morgan Stanley (2020-12-31, 'Wealth Management representatives 15,950', MS-SUPP-2020Q4#1)" in cav[3]


@pytest.mark.parametrize("question, aspect, rows", [
    (Q23, Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series"), FIVE),
    ("Client assets per advisor across the five -- and is that comparison even valid?",
     Aspect("a3", "Number of financial advisors (headcount) for each firm.", metric="advisor_headcount", proxy=True), FIVE),
    ("Client assets per advisor across the five -- and is that comparison even valid?",
     Aspect("a4", "Whether it is valid given how each defines client assets and advisor headcount.",
            kind="comparison"), FIVE),
    (Q11, Aspect("a1", "How each firm defines advisor headcount.", metric="advisor_headcount"), ["RJF"]),
])
def test_contrast_only_on_definition_asks_with_two_firms(question, aspect, rows):
    assert _contrast(_matrix(question, [aspect], rows)) == []


# --- item 2 and review nb 1: unit-aware wording, parent named --------------------------------------------

def test_by_firm_caveat_names_the_parent_and_schwab_headcount_reports_a_related_figure():
    m = _matrix(Q11, Q11_ASPECTS[:1])
    cav = next(x for x in m.caveats if x.startswith("Advisor headcount as each firm defines it:"))
    assert "Merrill (Bank of America Corporation): '(3) Includes advisors" in cav
    assert ("The Charles Schwab Corporation: publishes no count of this metric; reports a related figure instead: "
            "'perform investment advisory functions") in cav
    assert "publishes no definition of this metric" not in cav
    edj = cav.split("Edward Jones:")[1].split(" | ")[0]
    assert "independents" not in edj and "none: all advisors are employees" not in cav


def test_closest_metric_in_the_asked_unit_defines_a_related_metric():
    a = Aspect("a1", "Net new assets by quarter, as each firm reports the metric.", metric="net_new_assets", kind="series")
    m = _matrix(Q22, [a])
    cav = next(x for x in m.caveats if x.startswith("Net new assets as each firm defines it:"))
    assert "The Charles Schwab Corporation: defines a related metric instead: 'Core net new client assets" in cav
    assert "Merrill (Bank of America Corporation): defines a related metric instead: 'The net client AUM flows" in cav
    assert "publishes no definition" not in cav and "related figure" not in cav
    assert _contrast(m) == []   # net_new_assets has no contrast dimensions


# --- item 3: quarter holes and span segments --------------------------------------------------------------

NNA = Aspect("a1", "Net new assets by quarter, as each firm reports the metric.", metric="net_new_assets", kind="series")
ALLQ = ["2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]


def _q22(cells, question=Q22, aspect=NNA):
    return mx.finish(EvidenceMatrix(question, rows=[c.entity for c in cells], aspects=[aspect],
                                    cells={c.id: c for c in cells}), sources=NO_SOURCES, as_of=AS_OF)


def _qs(*qs):
    return [it("$1", q) for q in qs]


def _holes(m):
    return [g for g in m.gaps if "other firms report these quarters" in g["what"]]


def test_q22_edj_fourth_quarters_named_no_ms_false_gap_ms_span_by_segment():
    edj = C("a1.EDJ", "fact", items=_qs("2024Q2", "2024Q3", "2025Q1", "2025Q2", "2025Q3", "2026Q1", "2026Q2"))
    ms = C("a1.MS", "fact", items=_qs("2019Q4", "2020Q3", "2020Q4", *ALLQ[1:]))
    rjf = C("a1.RJF", "fact", items=_qs(*ALLQ[:-1]))
    m = _q22([ms, edj, rjf])
    holes = _holes(m)
    assert [g["id"] for g in holes] == ["a1.EDJ"] and holes[0]["periods"] == ["2024Q4", "2025Q4"]
    assert holes[0]["what"] == ("Edward Jones - Net new assets by quarter, as each firm reports the metric: not found for "
                                "2024Q4, 2025Q4 in the documents searched (inside its series 2024Q2-2026Q2; other firms "
                                "report these quarters).") and holes[0]["label"] == "period_gap"
    span = next(x for x in m.caveats if x.startswith("Morgan Stanley - Net new assets by quarter"))
    assert ("runs from 2024Q3 to 2026Q3 (9 points; earlier points 2019Q4 to 2020Q4, 3 points, are a separate segment); "
            "no figure after 2026Q3 was found.") in span


@pytest.mark.parametrize("own, other, expected", [
    (["2024Q1", "2025Q3"], ALLQ, []),                               # a 5-quarter run: two segments, no hole
    (["2024Q2", "2024Q3"], ALLQ, []),                               # missing after the end: not inside
    (["2024Q2", "2024Q4"], ["2024Q2", "2024Q4"], []),               # nobody else reports 2024Q3
    (["2024Q2", "2025Q2"], ALLQ, ["2024Q3", "2024Q4", "2025Q1"]),   # a 3-quarter hole
])
def test_quarter_hole_rule(own, other, expected):
    m = _q22([C("a1.EDJ", "fact", items=_qs(*own)), C("a1.RJF", "fact", items=_qs(*other))])
    assert [g["periods"] for g in _holes(m) if g["id"] == "a1.EDJ"] == ([expected] if expected else [])


def test_no_quarter_holes_with_asked_periods_a_fact_aspect_or_years():
    edj = C("a1.EDJ", "fact", items=_qs("2024Q2", "2025Q1"))
    rjf = C("a1.RJF", "fact", items=_qs(*ALLQ))
    assert _holes(_q22([edj, rjf], question="Net new assets over the last eight quarters across the five.")) == []
    assert _holes(_q22([edj, rjf], aspect=Aspect("a1", "Net new assets by quarter.", metric="net_new_assets"))) == []
    years = C("a1.EDJ", "fact", items=[it("$1", "2024"), it("$1", "FY2026")])
    assert _holes(_q22([years, rjf])) == []


def test_q23_rjf_fiscal_year_ends_stay_one_span_segment():
    a = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
    rjf = C("a1.RJF", "fact", items=[it("8,712", "2023-09-30"), it("8,787", "2024-09-30"), it("8,943", "2025-09-30")])
    m = mx.finish(EvidenceMatrix(Q23, rows=["RJF"], aspects=[a], cells={rjf.id: rjf}), sources=NO_SOURCES, as_of=AS_OF)
    span = next(x for x in m.caveats if "the series in the documents searched" in x)
    assert "runs from 2023-09-30 to 2025-09-30 (3 points); no figure after 2025-09-30 was found." in span


# --- item 6: basis breaks ---------------------------------------------------------------------------------

def _breaks(items):
    a = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
    c = C("a1.RJF", "fact", items=items)
    with um.patch.object(mx, "tag_populations", lambda m: None):   # keep the hand-set keys
        return mx.finish(EvidenceMatrix(Q23, rows=[], aspects=[a], cells={c.id: c}), sources=NO_SOURCES).breaks


def test_q23_rjf_undated_keyed_items_make_no_basis():
    k = "rjf_advisors_excl_rcs"
    assert _breaks([it("8,712", "2023-09-30", population=k), it("8,787", "2024-09-30", population=k),
                    it("8,943", "2025-09-30", population=k),
                    it("approximately 9,000", "", "domestic wealth management businesses", k),
                    it("about 400", "", "Financial Institutions Division", k)]) == []


def test_q11_edj_same_date_split_is_not_a_break():
    assert _breaks([it("20,514", "2026Q2", population="edj_firm"), it("19,639", "2026Q2", "U.S."),
                    it("875", "2026Q2", "Canada")]) == []


def test_split_rule_edges():
    assert _breaks([it("1", "2026Q2", "U.S."), it("2", "2026Q2", "Canada")]) == []          # no whole firm: split
    assert _breaks([it("3", "2026-06-30"), it("1", "2026Q2", "U.S.")]) == []                # periods normalised
    assert len(_breaks([it("1", "2025Q4", population="k1"), it("2", "2026Q2", population="k2")])) == 1   # two keys
    assert len(_breaks([it("3", "2026Q2", population="k1"), it("1", "2026Q2", "U.S.", "k2")])) == 1      # no merge
    assert len(_breaks([it("3", "2025Q3"), it("3", "2026Q2"), it("1", "2026Q1", "U.S.")])) == 1          # Q23 EDJ shape


# --- item 4: years in the dedupe --------------------------------------------------------------------------

def cl(text, ids=("T#1",)):
    return Claim(text=text, chunk_ids=list(ids), part_id="a1.X")


@pytest.mark.parametrize("a, b", [
    ("X reported $17 billion for fiscal 2024.", "X reported $17 billion for fiscal 2025, the table shows."),
    ("In 2024, net new assets were $5 billion.", "In 2025, net new assets were $5 billion, the table shows."),
])
def test_dedupe_keeps_claims_for_different_years(a, b):
    ans = Answer(answerable=True, behavior="answer", claims=[cl(a), cl(b)])
    assert R.dedupe_claims(ans) == [] and len(ans.claims) == 2


def test_dedupe_exact_repeat_with_a_year_still_removed():
    ans = Answer(answerable=True, behavior="answer", claims=[cl("X had 8,943 advisors in fiscal 2025."),
                                                            cl("X had 8,943 advisors in fiscal 2025.")])
    assert len(R.dedupe_claims(ans)) == 1


def test_figures_are_not_years():
    assert R._stated_periods("$2,024 million and 2,024 advisors, ratio 2024.5") == set()
    assert R._stated_periods("fiscal 2024, FY2025, FY 2023, fiscal year 2022, in 2021, x") == \
        {"fy2024", "fy2025", "fy2023", "fy2022", "2021"}


# --- item 5: per-firm gap sources ------------------------------------------------------------------------

REG = {"MER": ([("adv", "Merrill Form ADV"), ("press", "Merrill press")], {"adv", "press"}),
       "BAC": ([("8-K", "Bank of America Form 8-K"), ("10-K", "Bank of America 10-K")], {"10-K"}),
       "MS": ([("8-K", "Morgan Stanley Form 8-K")], set()),
       "RJF": ([("adv", "Raymond James Form ADV")], {"adv"})}


@pytest.fixture
def reg(monkeypatch):
    monkeypatch.setattr(validate, "registry_lookup", lambda e: REG.get(e, ([], set())))


def test_merrill_with_nothing_missing_names_its_parents_sources(reg):
    assert validate.suggested_sources("MER") == ("Not yet in the corpus (parent Bank of America Corporation): "
                                                 "Bank of America Form 8-K")
    assert validate.suggested_sources("RJF") == ""   # nothing missing, no parent


def test_firm_gap_gets_only_its_firm_aspect_gap_the_joined_list(reg):
    a = Answer(answerable=True, behavior="answer", gaps=[
        {"what": "Merrill - x", "suggested_source": "", "part_id": "a1.MER"},
        {"what": "RJF - x", "suggested_source": "", "part_id": "a1.RJF"},
        {"what": "x", "suggested_source": "", "part_id": "a4"},
        {"what": "research - x", "suggested_source": "", "part_id": "a3.research"}])
    out = validate.fill_suggested_sources(a, Query(question="q", entities=["MS", "MER", "RJF"])).gaps
    assert out[0].suggested_source.startswith("Not yet in the corpus (parent Bank of America Corporation)")
    assert "Morgan Stanley" not in out[0].suggested_source
    assert out[1].suggested_source == ""
    joined = ("Not yet in the corpus: Morgan Stanley Form 8-K; (parent Bank of America Corporation) "
              "Bank of America Form 8-K")
    assert out[2].suggested_source == joined and out[3].suggested_source == joined


def test_empty_retrieval_for_merrill_names_the_parents_sources(reg):
    a = validate.empty_retrieval_answer(Query(question="q", entities=["MER"]))
    assert a.gaps[0].suggested_source.startswith("Not yet in the corpus (parent Bank of America Corporation): ")


# --- item 1: registry rules (TL conditions 1-2) ----------------------------------------------------------

def _registry():
    return yaml.safe_load((REPO_ROOT / "config" / "metric_definitions.yaml").read_text(encoding="utf-8"))


def _contrast_entries():
    return [d for d in _registry()["definitions"] if d.get("contrast")]


def test_registry_contrast_shape():
    reg = _registry()
    dims = {d["key"] for d in reg["contrast_dimensions"]["advisor_headcount"]}
    entries = _contrast_entries()
    assert {d["entity"] for d in entries} == {"MS", "SCHW", "EDJ", "BAC", "RJF"}
    for d in entries:
        assert d["metric"] == "advisor_headcount" and set(d["contrast"]) <= dims
        allowed = {d["chunk_id"], *d.get("see_also", []), *d.get("contrast_ids", [])}
        assert not set(d.get("contrast_ids", [])) & set(d.get("see_also", []))   # never pinned
        for key, cell in d["contrast"].items():
            assert cell["value"] in mx.CONTRAST_VALUES, (d["entity"], key)
            assert isinstance(cell.get("text", ""), str)
            if cell["value"] not in ("not_stated", "none") or cell.get("text"):
                assert cell.get("chunk_id") in allowed, (d["entity"], key)
            if key == "count_date" and cell["value"] == "counted":
                assert isinstance(cell["date"], dt.date)
        assert d["contrast"].get("business_lines", {}).get("value") in mx.CONTRAST_VALUES
    by = {d["entity"]: d for d in entries}
    assert by["MS"]["contrast"]["business_lines"]["text"] == "Wealth Management representatives"
    assert by["EDJ"]["contrast"]["independents"] == {
        "value": "stated", "chunk_id": "EDJ-10K-2025#35",
        "text": "The Partnership’s financial advisors are employees or partners of the Partnership."}
    assert not any("independents" in str(x) for x in by["EDJ"]["not_stated"])
    assert by["SCHW"]["contrast"]["independents"]["text"].startswith("Through the Advisor Services segment, Schwab")


def test_registry_contrast_texts_are_verbatim_in_their_chunks():
    ids = {c["chunk_id"] for d in _contrast_entries() for c in d["contrast"].values() if c.get("chunk_id")}
    ids |= {i for d in _contrast_entries() for i in d.get("contrast_ids", [])}
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            rows = dict(conn.execute("SELECT chunk_id, text FROM chunks WHERE chunk_id = ANY(%s)", (list(ids),)).fetchall())
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not rows:
        pytest.skip("no corpus loaded")
    assert ids - rows.keys() == set()
    squash = lambda t: re.sub(r"\s+", " ", t).strip()   # noqa: E731
    for d in _contrast_entries():
        for key, cell in d["contrast"].items():
            if cell.get("text"):
                assert squash(cell["text"]) in squash(rows[cell["chunk_id"]]), (d["entity"], key)


# --- TL (after the EDJ #148 finding): the per-firm definitions caveat is verbatim or fixed phrases -------

_QUOTED_CITED = re.compile(r"'(.+?)' \(([A-Z0-9][\w.-]*#\d+)\)")
FIXED_WORDS = set("""as each firm defines it publishes no count of this metric reports a related figure instead
defines a related metric definition or nearest text not stated registered independent contractor advisors trainees
business lines in the count excludes advisor headcount net new assets""".split())


def _by_firm_caveats():
    out = []
    for metric, aspect in (("advisor_headcount", Aspect("a1", "Advisor headcount over the last eight quarters.",
                                                        metric="advisor_headcount", kind="series")),
                           ("net_new_assets", NNA)):
        m = _matrix(Q23 if metric == "advisor_headcount" else Q22, [aspect])
        out += [x for x in m.caveats if " as each firm defines it: " in x]
    assert len(out) == 2
    return out


def test_by_firm_caveat_outside_quotes_is_only_fixed_phrases_and_names():
    names = set(" ".join(["Morgan Stanley", "The Charles Schwab Corporation", "Edward Jones", "Merrill",
                          "Bank of America Corporation", "Raymond James Financial"]).lower().split())
    for cav in _by_firm_caveats():
        rest = _QUOTED_CITED.sub(" ", cav)
        words = set(re.findall(r"[a-z]+", rest.lower()))
        assert words <= FIXED_WORDS | names, words - FIXED_WORDS - names
        assert "#148" not in cav


def test_by_firm_caveat_quotes_are_verbatim_in_the_chunk_they_cite():
    pairs = [(q, cid) for cav in _by_firm_caveats() for q, cid in _QUOTED_CITED.findall(cav)]
    assert len(pairs) >= 15
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            rows = dict(conn.execute("SELECT chunk_id, text FROM chunks WHERE chunk_id = ANY(%s)",
                                     ([c for _, c in pairs],)).fetchall())
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not rows:
        pytest.skip("no corpus loaded")
    squash = lambda t: re.sub(r"\s+", " ", t).strip()   # noqa: E731
    for q, cid in pairs:
        q = q[:-3] if q.endswith("...") else q          # a quote clipped at a word boundary (TL D10)
        assert squash(q) in squash(rows[cid]), (cid, q)
