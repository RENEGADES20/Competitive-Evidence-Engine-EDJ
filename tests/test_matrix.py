"""Evidence matrix code rules (#246; ADR-021 rules 1, 2, 3): behavior, proxy aspects, gaps,
derivations, comparability and caveats. No database, 0 calls."""
import pytest
import yaml

from cee.answer import matrix as mx
from cee.answer.matrix import Cell, EvidenceMatrix, Item
from cee.config import REPO_ROOT
from cee.retrieve.planner import Aspect

NO_SOURCES = lambda entity: ""   # noqa: E731  (no registry lookup in these tests)


def item(cid="X#1", value="", unit="", period="", scope="", **kw):
    return Item(text="t", quote="q", chunk_ids=[cid] if cid else [], value=value, unit=unit, period=period,
                scope=scope, **kw)


def cell(cid, label, items=(), entity=None, role="named", derivation=None):
    aspect, ent = cid.split(".")
    entity = entity if entity is not None else (None if ent in ("research", "all") else ent)
    role = "research" if ent == "research" else role
    return Cell(cid, entity, aspect, role, label, items=list(items), derivation=derivation)


def build(question, aspects, cells):
    m = EvidenceMatrix(question, rows=[], aspects=aspects, cells={c.id: c for c in cells})
    return mx.finish(m, sources=NO_SOURCES)


A1 = Aspect("a1", "Advisor headcount as reported.", metric="advisor_headcount")
PLAIN = "Advisor headcount across the five."


# --- behavior rule table (rule 1, with its precedence) ------------------------------------------

@pytest.mark.parametrize("question, aspects, cells, behavior", [
    ("Forecast Edward Jones's net new assets for 2027.", [A1], [cell("a1.EDJ", "fact", [item()])], "refuse"),
    ("How should the preferences of younger investors shape Edward Jones's offerings?", [A1],
     [cell("a1.EDJ", "not_found")], "answer_with_boundary"),
    (PLAIN, [A1], [cell("a1.EDJ", "fact", [item()]), cell("a1.MS", "not_disclosed")], "answer"),
    (PLAIN, [A1], [cell("a1.EDJ", "not_found"), cell("a1.research", "fact", [item("R#1")])], "answer"),
    (PLAIN, [A1], [cell("a1.EDJ", "not_disclosed"), cell("a1.MS", "different_quantity", [item()])],
     "gap_with_adjacent"),
    (PLAIN, [A1], [cell("a1.EDJ", "not_disclosed"), cell("a1.MS", "not_found")], "refuse"),
    (PLAIN, [A1], [cell("a1.EDJ", "failed"), cell("a1.MS", "not_found")], None),
    (PLAIN, [A1], [cell("a1.EDJ", "failed"), cell("a1.MS", "fact", [item()])], "answer"),
    (PLAIN, [A1, Aspect("a2", "Whether the figures compare.", kind="comparison")],
     [cell("a1.EDJ", "not_found"), cell("a2.EDJ", "fact", [item()])], "refuse"),
    (PLAIN, [A1], [cell("a1.EDJ", "fact", [item(cid=None)])], "refuse"),   # fact citing nothing retrieved
])
def test_behavior_rule_table(question, aspects, cells, behavior):
    assert build(question, aspects, cells).behavior == behavior


def test_undecided_is_incomplete_never_refuse():
    m = build(PLAIN, [A1], [cell("a1.EDJ", "failed"), cell("a1.MS", "not_found")])
    assert m.behavior is None and m.behavior_reason.startswith("undecided")
    assert m.incomplete_note.startswith("This answer is incomplete: the evidence for Edward Jones")
    assert not any("does not support" in g["what"] for g in m.gaps)   # an absence is never asserted


# --- proxy aspects (B2) -------------------------------------------------------------------------

def test_q29_shaped_proxy_fact_gives_gap_with_adjacent():
    a1 = Aspect("a1", "The payout grid the firm pays its advisors.")
    a2 = Aspect("a2", "The closest disclosed figure on advisor pay.", proxy=True)
    m = build("What does Morgan Stanley pay its financial advisors?", [a1, a2],
              [cell("a1.MS", "not_disclosed"), cell("a2.MS", "fact", [item(value="$1,875 million")])])
    assert m.behavior == "gap_with_adjacent"
    assert not any(g["id"].startswith("a2") for g in m.gaps)             # no gap for the proxy aspect
    assert any(g["what"].startswith("The database does not support this today: The payout grid") for g in m.gaps)


def test_proxy_fact_alone_never_answers():
    a1 = Aspect("a1", "Client assets per advisor.", proxy=True)
    assert build(PLAIN, [a1], [cell("a1.EDJ", "fact", [item()])]).behavior == "gap_with_adjacent"


def test_q24_shaped_derived_ratio_answers_and_fte_stays_different_quantity():
    a1 = Aspect("a1", "Client assets per advisor as reported.")
    a2 = Aspect("a2", "Total client assets, as the closest disclosed numerator.", proxy=True)
    a3 = Aspect("a3", "Advisor headcount, as the closest disclosed denominator.", metric="advisor_headcount",
                proxy=True)
    edj_assets = item("EDJ-10Q-2026Q2#1", value="$2.3 trillion", unit="USD", period="2026-06-30")
    edj_fas = item("EDJ-10Q-2026Q2#2", value="20,425", unit="financial advisors", period="2026-06-30")
    fte = item("SCHW-PR-2026-07-21-01#24", value="33.7 thousand", unit="full-time equivalent employees",
               period="2026-06-30")
    m = build("Client assets per advisor across the five -- and is that comparison even valid?", [a1, a2, a3], [
        cell("a1.EDJ", "not_disclosed", derivation={"operation": "ratio", "inputs": [
            {"subquestion_id": "a2.EDJ", "item": 0}, {"subquestion_id": "a3.EDJ", "item": 0}]}),
        cell("a2.EDJ", "fact", [edj_assets]), cell("a3.EDJ", "fact", [edj_fas]),
        cell("a1.SCHW", "not_disclosed", derivation={"operation": "ratio", "inputs": [
            {"subquestion_id": "a2.SCHW", "item": 0}, {"subquestion_id": "a3.SCHW", "item": 0}]}),
        cell("a2.SCHW", "fact", [item("SCHW-10Q#1", value="$11 trillion", unit="USD", period="2026-06-30")]),
        cell("a3.SCHW", "different_quantity", [fte])])
    assert m.behavior == "answer" and m.behavior_reason == "1a: the asked quantity in a1.EDJ"
    edj = m.cells["a1.EDJ"]
    assert edj.label == "derived" and edj.derivation["ok"]
    assert edj.derivation["value_text"] == "112,607,099"
    assert edj.derivation["input_chunk_ids"] == ["EDJ-10Q-2026Q2#1", "EDJ-10Q-2026Q2#2"]
    assert "definition_unverified" in edj.flags                                  # client assets: unregistered
    assert m.cells["a3.SCHW"].effective_label == "different_quantity"             # never a derivation input
    assert not m.cells["a1.SCHW"].derivation["ok"] and "not a fact" in m.cells["a1.SCHW"].derivation["why"]
    assert m.marks["a1"].status == "unverified" and "definition is unverified" in m.marks["a1"].mark


# --- the question's own asks --------------------------------------------------------------------

def bank():
    return yaml.safe_load((REPO_ROOT / "evals" / "questions.yaml").read_text(encoding="utf-8"))["questions"]


def test_normative_question_matches_exactly_q12_and_q19_of_the_bank():
    assert [q["id"] for q in bank() if mx.normative_question(q["text"])] == ["Q12", "Q19"]


@pytest.mark.parametrize("text, expected", [
    ("What should investors know about Edward Jones's fees?", False),
    ("How should clients compare Edward Jones with Morgan Stanley?", False),
    ("What could slow Edward Jones's advisor growth?", False),
    ("Edward Jones says advisors should meet clients yearly.", False),
    ("Should Edward Jones launch a robo-advisor?", True),
    ("How can Edward Jones win younger clients?", True),
])
def test_normative_question_synthetic_cases(text, expected):
    assert mx.normative_question(text) is expected


def test_forecast_request_matches_no_bank_question_and_three_synthetic_ones():
    assert [q["id"] for q in bank() if mx.forecast_request(q["text"])] == []
    for text in ("Forecast Edward Jones's net new assets for 2027.",
                 "Predict which of the five will have the most advisors next year.",
                 "What will Schwab's client assets be in 2028?"):
        assert mx.forecast_request(text), text


# --- gaps -------------------------------------------------------------------------------------

def test_gap_wording_per_label_and_not_supported():
    m = build(PLAIN, [A1], [cell("a1.EDJ", "not_disclosed"), cell("a1.MS", "not_found"),
                            cell("a1.SCHW", "different_quantity", [item()]), cell("a1.RJF", "not_found")])
    whats = {g["id"]: g["what"] for g in m.gaps}
    failed = build(PLAIN, [A1], [cell("a1.RJF", "failed"), cell("a1.MS", "fact", [item()])])
    assert "not extracted" in {g["id"]: g["what"] for g in failed.gaps}["a1.RJF"]
    assert whats["a1.EDJ"] == "Edward Jones - Advisor headcount as reported: not disclosed in the documents searched."
    assert whats["a1.MS"] == "Morgan Stanley - Advisor headcount as reported: not found in the documents searched."
    assert whats["a1.SCHW"].endswith("not disclosed; a different quantity is listed as adjacent.")
    assert whats["a1"] == ("The database does not support this today: Advisor headcount as reported "
                           "(Edward Jones, Morgan Stanley, The Charles Schwab Corporation, Raymond James Financial).")


def test_researched_not_found_says_so_and_comparison_aspects_get_no_gap():
    c = cell("a1.EDJ", "not_found")
    c.researched, c.research_hits = True, 0
    comp = Aspect("a2", "Whether the figures compare.", kind="comparison")
    m = build(PLAIN, [A1, comp], [c, cell("a2.EDJ", "not_found")])
    whats = {g["id"]: g["what"] for g in m.gaps}
    assert whats["a1.EDJ"].endswith("A second search with wider words found nothing new.")
    assert not any(g["id"].startswith("a2") for g in m.gaps)


# --- derivation -------------------------------------------------------------------------------

def _derive(a_item, b_item, op="ratio", other_entity=False):
    a1 = Aspect("a1", "Assets per advisor.")
    a2, a3 = Aspect("a2", "Assets.", proxy=True), Aspect("a3", "Advisors.", proxy=True)
    b_cell = cell("a3.MS" if other_entity else "a3.EDJ", "fact", [b_item])
    return build(PLAIN, [a1, a2, a3], [
        cell("a1.EDJ", "not_disclosed", derivation={"operation": op, "inputs": [
            {"subquestion_id": "a2.EDJ", "item": 0}, {"subquestion_id": b_cell.id, "item": 0}]}),
        cell("a2.EDJ", "fact", [a_item]), b_cell]).cells["a1.EDJ"]


@pytest.mark.parametrize("a, b, op, other, why", [
    (item(value="100", period="2026-06-30"), item(value="4", period="2025-12-31"), "ratio", False, "periods differ"),
    (item(value="100", period="2026-06-30", scope="PCG"), item(value="4", period="2026-06-30"), "ratio", False,
     "scopes differ"),
    (item(value="100", unit="USD", period="2026Q2"), item(value="4", unit="advisors", period="2026Q2"), "sum", False,
     "units differ"),
    (item(value="n/a", period="2026Q2"), item(value="4", period="2026Q2"), "ratio", False, "does not parse"),
    (item(value="100", period="2026Q2", flags=["number_not_found"]), item(value="4", period="2026Q2"), "ratio",
     False, "figure not found"),
    (item(value="100", period="2026Q2"), item(value="4", period="2026Q2"), "ratio", True, "not the same firm"),
])
def test_derivation_rejected_with_why(a, b, op, other, why):
    c = _derive(a, b, op, other)
    assert c.label == "not_disclosed" and not c.derivation["ok"] and why in c.derivation["why"]


def test_derivation_applies_the_scale_word_of_the_unit():
    """Found in the #246 re-check (Q24 EDJ): "$2,647" with unit "USD billions" is 2.647e12, so the
    per-advisor value is in dollars, not billions."""
    c = _derive(item("A#1", value="$2,647", unit="USD billions", period="2026-06-26"),
                item("B#1", value="20,514", unit="financial advisors", period="2026-06-26"))
    assert c.derivation["value_text"] == "129,033,831" and c.derivation["unit"] == "USD per financial advisors"
    assert c.derivation["formula"] == ("a2.EDJ#0 / a3.EDJ#0 = $2,647 (USD billions) / 20,514 (financial advisors)"
                                       " = 129,033,831 USD per financial advisors")


def test_derivation_accepted_computes_value_and_formula():
    c = _derive(item("A#1", value="100", period="2026Q2"), item("B#1", value="4", period="2026Q2"))
    assert c.label == "derived" and c.derivation["value"] == 25
    assert c.derivation["formula"] == "a2.EDJ#0 / a3.EDJ#0 = 100 / 4 = 25"


# --- comparability (rule 2) -----------------------------------------------------------------------

def test_different_basis_caveat_exact_and_mer_reads_bac():
    m = build(PLAIN, [A1], [cell("a1.EDJ", "fact", [item()]), cell("a1.MER", "fact", [item("BAC#1")])])
    mark = m.marks["a1"]
    assert mark.status == "different_basis"
    edj = mx.metric_definition("EDJ", "advisor_headcount")
    bac = mx.metric_definition("BAC", "advisor_headcount")
    assert mx.metric_definition("MER", "advisor_headcount") is bac
    assert mark.caveat == ("Advisor headcount: the firms define it differently (Edward Jones: "
                           f"{mx._clip(edj['quote'], 160)} ({edj['chunk_id']}); Merrill: "
                           f"{mx._clip(bac['quote'], 160)} ({bac['chunk_id']})); figures are listed side by side "
                           "and not compared or combined (reporting risk).")
    assert mark.caveat in m.caveats


def test_same_basis_marks_shared_periods(monkeypatch):
    same = {"basis": "b", "unit": "advisors", "quote": "q", "chunk_id": "c"}
    monkeypatch.setattr(mx, "metric_definition", lambda e, m: same)
    m = build(PLAIN, [A1], [cell("a1.EDJ", "fact", [item(period="2026Q1"), item(period="2026Q2")]),
                            cell("a1.MS", "fact", [item(period="2026Q2")])])
    assert m.marks["a1"].status == "same_basis" and m.marks["a1"].shared_periods == ["2026Q2"]
    assert m.caveats == []


def test_unregistered_metric_with_value_is_unverified_and_qualitative_is_none():
    a = Aspect("a1", "Total client assets.", kind="series")   # #247 D6: metric aspects only
    m = build(PLAIN, [a], [cell("a1.EDJ", "fact", [item(value="$2 trillion")])])
    assert m.marks["a1"].status == "unverified"
    assert m.marks["a1"].mark == "Total client assets is not in the metric definitions file; its definition is unverified."
    q = build(PLAIN, [Aspect("a1", "Strategy.")], [cell("a1.EDJ", "fact", [item()])])
    assert q.marks["a1"].status == "none"


@pytest.mark.parametrize("aspect, status", [
    (Aspect("a1", "What management says about younger clients."), "none"),          # Q19 a1-shaped fact
    (Aspect("a1", "New hires announced.", kind="recency"), "none"),                 # Q26-shaped recency
    (Aspect("a1", "Whether the figures compare.", kind="comparison"), "none"),
    (Aspect("a1", "Total client assets, the numerator.", proxy=True), "unverified"),  # Q24 a2-shaped
    (Aspect("a1", "Client assets over the last quarters.", kind="series"), "unverified"),
])
def test_unverified_mark_only_on_metric_aspects(aspect, status):
    m = build(PLAIN, [aspect], [cell("a1.EDJ", "fact", [item(value="1,200")]),
                                cell("a1.MS", "fact", [item(value="900")])])
    assert m.marks["a1"].status == status


@pytest.mark.parametrize("a, b, same", [
    ("Wealth Management segment", "Wealth Management", True),
    ("the Wealth Management Segment.", "wealth management", True),
    ("Global Wealth & Investment Management business segment", "Global Wealth & Investment Management", True),
    ("Private Client Group", "", False),
    ("Private Client Group", "Asset Management", False),
])
def test_normalize_scope(a, b, same):
    assert (mx.normalize_scope(a) == mx.normalize_scope(b)) is same


def test_derivation_accepts_scopes_that_differ_only_by_segment_word():
    a1 = Aspect("a1", "Client assets per advisor.")
    a2 = Aspect("a2", "Client assets.", proxy=True)
    a3 = Aspect("a3", "Advisors.", proxy=True)
    m = build(PLAIN, [a1, a2, a3], [
        cell("a1.MS", "not_disclosed", derivation={"operation": "ratio", "inputs": [
            {"subquestion_id": "a2.MS", "item": 0}, {"subquestion_id": "a3.MS", "item": 0}]}),
        cell("a2.MS", "fact", [item("M#1", value="$6,000", unit="USD billions", period="2026-09-30",
                                    scope="Wealth Management segment")]),
        cell("a3.MS", "fact", [item("M#2", value="15,000", unit="representatives", period="2026-09-30",
                                    scope="Wealth Management")])])
    d = m.cells["a1.MS"].derivation
    assert d["ok"] and m.cells["a1.MS"].label == "derived"
    assert "a2.MS" not in d["formula_text"] and d["formula_text"].endswith("USD per representatives")


def test_normative_question_with_a_failed_cell_shows_the_incomplete_note():
    m = build("How should the preferences of younger investors shape Edward Jones's offerings?", [A1],
              [cell("a1.EDJ", "failed"), cell("a1.MS", "not_found")])
    assert m.behavior == "answer_with_boundary"
    assert m.incomplete_note.startswith("This answer is incomplete: the evidence for Edward Jones")


# --- uncovered asked periods (#247 B4, TL approval conditions 1-4) ---------------------------------

import datetime as dt  # noqa: E402

AS_OF = dt.date(2026, 11, 17)


def test_asked_periods():
    assert mx.asked_periods("Advisor headcount over the last eight quarters across the five.", AS_OF) == (
        "quarter", ["2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"])
    assert mx.asked_periods("Net new assets over the past 3 years.", AS_OF) == ("year", ["2023", "2024", "2025"])
    assert mx.asked_periods("What's new on Raymond James in the last 90 days?", AS_OF) is None   # a window: none
    assert mx.asked_periods("Net new assets by quarter for each of the five.", AS_OF) is None


def _series(question, cells, kind="series"):
    a = Aspect("a1", "Advisor headcount.", kind=kind, metric="advisor_headcount")
    return build_at(question, [a], cells)


def build_at(question, aspects, cells):
    m = EvidenceMatrix(question, rows=[], aspects=aspects, cells={c.id: c for c in cells})
    return mx.finish(m, sources=NO_SOURCES, as_of=AS_OF)


def test_q23_shaped_period_gaps_name_the_uncovered_quarters():
    q = "Advisor headcount over the last eight quarters across the five."
    edj = [item("E#1", "19,413", period="2025-03-28"), item("E#2", "20,309", period="2025-06-27"),
           item("E#3", "20,429", period="2025-09-26"), item("E#4", "19,674", period="2026-03-27"),
           item("E#5", "20,514", period="2026-06-26"), item("E#6", "20,000", period="2025")]   # YYYY: no quarter
    ms = [item("M#1", "15,950", period="2020-12-31")]
    m = _series(q, [cell("a1.EDJ", "fact", edj), cell("a1.MS", "fact", ms)])
    gaps = {g["id"]: g["what"] for g in m.gaps if g["label"] == "period_gap"}
    assert gaps["a1.EDJ"] == ("Edward Jones - Advisor headcount: not found for 2024Q4, 2025Q4, 2026Q3 in the "
                              "documents searched.")
    assert gaps["a1.MS"].startswith("Morgan Stanley - Advisor headcount: not found for the asked periods "
                                    "(2024Q4-2026Q3)")


def test_q26_shaped_window_gives_no_period_gap():
    q = "What's new on Raymond James in the last 90 days?"
    m = _series(q, [cell("a1.RJF", "fact", [item("R#1", "8,943", period="2026-06-30")])])   # 10-Q in window
    assert not [g for g in m.gaps if g["label"] == "period_gap"]
    r = build_at(q, [Aspect("a1", "Recent news.", kind="recency")],
                 [cell("a1.RJF", "fact", [item("R#1", period="2026-06-30")])])
    assert not [g for g in r.gaps if g["label"] == "period_gap"]


def test_years_shaped_year_end_reporter_has_no_quarter_gaps_and_no_current_year():
    q = "Advisor headcount over the past 3 years for Morgan Stanley."
    items = [item(f"M#{y}", "15,000", period=f"{y}-12-31") for y in (2023, 2024, 2025)]
    m = _series(q, [cell("a1.MS", "fact", items + [item("M#9", "15,100", period="2026-06-30")])])
    assert not [g for g in m.gaps if g["label"] == "period_gap"]
    m2 = _series(q, [cell("a1.MS", "fact", items[1:])])
    assert [g["what"] for g in m2.gaps if g["label"] == "period_gap"] == [
        "Morgan Stanley - Advisor headcount: not found for 2023 in the documents searched."]


def test_gwim_caveat_when_a_merrill_cell_cites_a_bac_gwim_chunk():
    from cee.retrieve.fts import Hit, Query
    h = Hit(chunk_id="BAC-10K-2025#246", doc_id="BAC-10K-2025", entity_id="BAC", segment="GWIM", doc_type="10-K",
            source_tier=2, published_at="2026-02-25", period_end="2025-12-31", section=None, page=None, rank=1.0,
            text="t")
    m = EvidenceMatrix(PLAIN, rows=[], aspects=[A1],
                       cells={"a1.MER": cell("a1.MER", "fact", [item("BAC-10K-2025#246")])})
    mx.finish(m, Query(question=PLAIN, entities=["MER"]), [h], NO_SOURCES)
    assert "GWIM is not Merrill: the segment also includes Bank of America Private Bank." in m.caveats
