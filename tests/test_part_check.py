"""Every planned part answered or named as a gap; uncited grid cells move to gaps (#215).
No database (fake registry_lookup), no API."""
import json
from pathlib import Path

import pytest

from cee.answer import validate
from cee.answer.prompt import BOUNDARY_HANDOFF
from cee.answer.schema import Answer
from cee.answer.validate import check_citations, check_parts, move_uncited_cells, part_coverage
from cee.retrieve.fts import Hit
from cee.retrieve.planner import Part, Plan

DATA = Path(__file__).parent / "data"
Q = "How do Morgan Stanley and Raymond James approach advisor recruiting?"


@pytest.fixture(autouse=True)
def fake_registry(monkeypatch):
    """No database: every firm has a 10-Q missing from the corpus."""
    monkeypatch.setattr(validate, "registry_lookup",
                        lambda e: ([("10-Q", f"{e} 10-Q")], {"10-K"}))


def hit(cid, part="p1", entity="MS"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-02-19", period_end="2025-12-31", section="Item 1",
               page=None, rank=1.0, text="x", part_id=part)


def plan(*parts, pools=None):
    p = Plan(parts=[Part(pid, text, firms) for pid, text, firms in parts])
    if pools is not None:
        p.searched = [{"id": pid, "pool": n} for pid, n in pools.items()]
    return p


TWO = plan(("p1", Q, ["MS"]), ("p2", Q, ["RJF"]), pools={"p1": 5, "p2": 0})


def answer(claims=(), gaps=(), adjacent=(), behavior="answer"):
    return Answer(answerable=True, behavior=behavior, claims=list(claims), gaps=list(gaps), adjacent=list(adjacent))


# --- check_parts -----------------------------------------------------------------------------

def test_part_with_no_claim_and_no_gap_gets_the_code_gap_pool_zero():
    hits = [hit("MS-10K-2025#1")]
    a = check_parts(answer([{"text": "t", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]), TWO, hits, Q)
    assert len(a.gaps) == 1
    g = a.gaps[0]
    assert g.what == f"No evidence retrieved for: {Q} (Raymond James Financial)"
    assert g.part_id == "p2" and g.flags == ["part_gap"]
    assert g.suggested_source == "Not yet in the corpus: RJF 10-Q"
    assert a.behavior == "answer" and len(a.claims) == 1


def test_part_with_passages_but_no_claim_gets_not_answered_wording():
    p = plan(("p1", "MS recruiting", ["MS"]), ("p2", "RJF recruiting", ["RJF"]), pools={"p1": 5, "p2": 3})
    hits = [hit("MS-10K-2025#1"), hit("RJF-10K-2025#1", "p2", "RJF")]
    a = check_parts(answer([{"text": "t", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]), p, hits, Q)
    assert [g.what for g in a.gaps] == ["Not answered from the evidence retrieved for: RJF recruiting"]


def test_two_parts_sharing_a_chunk_never_say_no_evidence():
    # p2's only candidate was kept by p1 (exclude=kept): p2 has no hits of its own, but pool 1.
    p = plan(("p1", "MS recruiting", ["MS"]), ("p2", "MS retention", ["MS"]), pools={"p1": 1, "p2": 1})
    hits = [hit("MS-10K-2025#1", "p1")]
    a = check_parts(answer([{"text": "t", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]), p, hits, Q)
    assert [g.what for g in a.gaps] == ["Not answered from the evidence retrieved for: MS retention"]
    assert not any(g.what.startswith("No evidence retrieved") for g in a.gaps)


def test_unknown_pool_uses_not_answered():
    p = plan(("p1", "a", ["MS"]), ("p2", "b", ["RJF"]))     # no searched record
    a = check_parts(answer([{"text": "t", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]), p, [hit("MS-10K-2025#1")])
    assert [g.what for g in a.gaps] == ["Not answered from the evidence retrieved for: b"]


@pytest.mark.parametrize("item", [
    {"claims": [{"text": "t", "chunk_ids": ["RJF-10K-2025#1"], "part_id": "p2"}]},                       # part id
    {"claims": [{"text": "t", "chunk_ids": ["RJF-10K-2025#1"]}]},                                         # citation
    {"claims": [{"text": "t", "chunk_ids": ["RJF-10K-2025#1"], "part_id": "rjf"}]},                       # bad id
    {"gaps": [{"what": "Raymond James: nothing", "part_id": "p2"}]},                                      # gap
    {"adjacent": [{"text": "t", "chunk_ids": ["RJF-10K-2025#1"], "part_id": "p2", "differs_because": "d"}]},
])
def test_covered_parts_get_no_code_gap(item):
    hits = [hit("MS-10K-2025#1"), hit("RJF-10K-2025#1", "p2", "RJF")]
    base = {"claims": [{"text": "m", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]}
    a = answer(**{k: base.get(k, []) + item.get(k, []) for k in ("claims", "gaps", "adjacent")})
    before = a.model_copy(deep=True)
    out = check_parts(a, TWO, hits, Q)
    assert not any("part_gap" in g.flags for g in out.gaps)
    assert out.model_dump() == before.model_dump()


def test_unmatched_citation_does_not_cover_a_part():
    hits = [hit("MS-10K-2025#1")]
    a = answer([{"text": "m", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"},
                {"text": "x", "chunk_ids": ["RJF-10K-2025#999"], "part_id": "p2"}])
    assert part_coverage(check_parts(a, TWO, hits, Q), TWO, hits)["p2"] == "code_gap"


def test_one_part_plan_any_gap_covers_it():
    p = plan(("p1", "q", ["MS"]), pools={"p1": 0})
    a = check_parts(answer(gaps=[{"what": "Morgan Stanley: Payout grids are not public."}],
                           behavior="gap_with_adjacent"), p, [])
    assert len(a.gaps) == 1 and part_coverage(a, p, [])["p1"] == "citation"


def test_one_part_refusal_with_nothing_gets_a_gap():
    p = plan(("p1", "q", ["MS"]), pools={"p1": 0})
    a = check_parts(answer(behavior="refuse"), p, [], "q")
    assert [g.what for g in a.gaps] == ["No evidence retrieved for: q (Morgan Stanley)"]


def test_boundary_normative_part_is_covered_by_the_handoff_and_label_is_never_normative():
    text = "How Edward Jones could replicate a scale-driven low-cost acquisition strategy"
    p = plan(("p1", "Schwab acquisition", ["SCHW"]), ("p2", text, ["EDJ"]), pools={"p1": 2, "p2": 2})
    hits = [hit("SCHW-10K-2025#1", "p1", "SCHW"), hit("EDJ-10K-2025#1", "p2", "EDJ")]
    a = answer([{"text": "s", "chunk_ids": ["SCHW-10K-2025#1"], "part_id": "p1"}], behavior="answer_with_boundary")
    a = check_citations(a, hits)                         # code adds the hand-off (cites every chunk)
    assert a.claims[-1].text == BOUNDARY_HANDOFF
    assert part_coverage(a, p, hits)["p2"] == "handoff"
    # Without the boundary behavior the part is not covered, and its label is not printed as a "should".
    b = check_parts(answer([{"text": "s", "chunk_ids": ["SCHW-10K-2025#1"], "part_id": "p1"}]), p, hits)
    assert [g.what for g in b.gaps] == ["Not answered from the evidence retrieved for: part p2 (Edward Jones)"]


def test_code_added_handoff_does_not_cover_parts_by_citation():
    p = plan(("p1", "Schwab acquisition", ["SCHW"]), ("p2", "Edward Jones costs", ["EDJ"]), pools={"p1": 2, "p2": 2})
    hits = [hit("SCHW-10K-2025#1", "p1", "SCHW"), hit("EDJ-10K-2025#1", "p2", "EDJ")]
    a = check_citations(answer([{"text": "s", "chunk_ids": ["SCHW-10K-2025#1", "EDJ-10K-2025#1"], "part_id": "p1"}],
                               behavior="answer_with_boundary"), hits)
    a = check_parts(a, p, hits)
    assert [g.what for g in a.gaps] == ["Not answered from the evidence retrieved for: Edward Jones costs"]


def test_no_plan_no_check():
    a = answer()
    assert check_parts(a, None, []).gaps == []


# --- move_uncited_cells ----------------------------------------------------------------------

def test_uncited_grid_cell_becomes_a_true_gap():
    a = move_uncited_cells(answer([{"text": "Training - Raymond James: a two-year program for new advisors.",
                                    "chunk_ids": [], "part_id": "p3"}]))
    assert a.claims == []
    g = a.gaps[0]
    assert g.what == "Raymond James - Training: no cited evidence in this answer."
    assert g.flags == ["uncited_cell"] and g.part_id == "p3"
    assert g.claim_text.startswith("Training - Raymond James: a two-year")


def test_cited_or_unmatched_or_non_grid_claims_stay():
    hits = [hit("MS-10K-2025#1")]
    a = check_citations(answer([
        {"text": "Training - Morgan Stanley: x", "chunk_ids": ["MS-10K-2025#999"]},   # unmatched: flagged, kept
        {"text": "Morgan Stanley says it hires.", "chunk_ids": []},                      # not a cell
        {"text": "Training - something else: y", "chunk_ids": []},                       # not a firm
    ]), hits)
    assert [c.text for c in a.claims] == ["Training - Morgan Stanley: x", "Morgan Stanley says it hires.",
                                          "Training - something else: y"]
    assert "unmatched_citation" in a.claims[0].flags
    assert "no_citation" in a.claims[1].flags and "no_citation" in a.claims[2].flags
    assert a.gaps == []


def test_gate4_q7_uncited_cells_join_their_model_gaps():
    saved = json.loads((DATA / "answer_v3_q7_gate4.json").read_text(encoding="utf-8"))
    raw = Answer(**saved["raw"])
    raw.gaps = [g.model_copy(update={"flags": [], "claim_text": ""}) for g in raw.gaps]
    for c in raw.claims:
        c.flags = []
    model_gaps = [g.what for g in raw.gaps]
    uncited = [c.text for c in raw.claims if not c.chunk_ids]
    assert len(uncited) == 3
    out = move_uncited_cells(raw.model_copy(deep=True))
    assert all(c.chunk_ids for c in out.claims)
    assert [g.what for g in out.gaps] == model_gaps                     # no duplicate, own text kept
    flagged = [g for g in out.gaps if "uncited_cell" in g.flags]
    assert len(flagged) == 3
    assert sorted(g.claim_text for g in flagged) == sorted(uncited)


def test_saved_v3_answers_parse():
    for name in ("answer_v3_q7_gate4.json", "answer_v3_q25_0224.json"):
        raw = json.loads((DATA / name).read_text(encoding="utf-8"))["raw"]
        for k in ("caveats", "coverage_note", "withheld", "llm_called"):
            raw.pop(k, None)
        a = Answer(**raw)
        assert all(c.part_id == "" for c in a.claims) and all(g.part_id == "" for g in a.gaps)


# --- prompt v4 user message and the mock -----------------------------------------------------

def test_user_message_groups_evidence_by_part_with_pool_chosen_empty_lines():
    from cee.answer.llm import KEPT_ELSEWHERE, NO_PASSAGES, PEERS_HEADING, RESEARCH_HEADING, build_user_message
    p = plan(("p1", "MS recruiting", ["MS"]), ("p2", "RJF recruiting", ["RJF"]), ("p3", "MER recruiting", ["MER"]),
             ("p4", "EDJ recruiting", ["EDJ"]), pools={"p1": 4, "p2": 3, "p3": 0, "p4": 2})
    hits = [hit("MS-10K-2025#2"), hit("RJF-10K-2025#1", "p2", "RJF"), hit("MS-10K-2025#1"),
            hit("R-1#1", "research", None), hit("SCHW-1#1", "peers", "SCHW")]
    msg = build_user_message("q", hits, p)
    assert "- p1 [Morgan Stanley]: MS recruiting" in msg
    order = [msg.index(s) for s in ("Part p1 [Morgan Stanley]", 'id="MS-10K-2025#2"', 'id="MS-10K-2025#1"',
                                    "Part p2 [Raymond James Financial]", 'id="RJF-10K-2025#1"', "Part p3 [Merrill",
                                    NO_PASSAGES, "Part p4 [Edward Jones]", KEPT_ELSEWHERE,
                                    RESEARCH_HEADING, 'id="R-1#1"', PEERS_HEADING, 'id="SCHW-1#1"')]
    assert order == sorted(order)                       # grouped, hit order kept inside a group
    assert msg.count("<chunk ") == len(hits)            # nothing dropped


def test_user_message_without_plan_is_one_part():
    from cee.answer.llm import build_user_message
    msg = build_user_message("What is X?", [hit("MS-10K-2025#1", None)])
    assert "- p1: What is X?" in msg and "Part p1: What is X?" in msg and 'id="MS-10K-2025#1"' in msg


def test_mock_claims_carry_their_hits_part():
    from cee.answer.llm import generate
    hits = [hit("MS-10K-2025#1"), hit("R-1#1", "research", None), hit("RJF-10K-2025#1", "p2", "RJF")]
    a = generate("q", hits, "mock", TWO)
    assert [c.part_id for c in a.claims] == ["p1", "", "p2"]
    assert generate("q", hits, "mock").claims[0].part_id == ""     # no plan: no part ids


def test_schema_requires_part_id_for_the_model():
    from cee.answer.schema import llm_output_schema
    s = llm_output_schema()["properties"]
    for field in ("claims", "adjacent", "gaps"):
        item = s[field]["items"]
        assert "part_id" in item["properties"] and "part_id" in item["required"]
        assert "flags" not in item["properties"] and "claim_text" not in item["properties"]


# --- wiring: Ask page gap chips, trace, eval cache key ---------------------------------------

def test_gap_box_shows_code_flags_as_chips(monkeypatch):
    from cee.app import components as ui
    out = []
    monkeypatch.setattr(ui.st, "markdown", lambda s, **kw: out.append(s))
    ui.gap_box("No evidence retrieved for: x", "10-Q", ["part_gap"])
    html = "".join(out)
    assert html.startswith('<div class="cee-box cee-gap"><b class="l">Gap:</b> No evidence retrieved for: x')
    assert '<span class="cee-flag">part_gap</span>' in html


def test_answer_for_with_plan_checks_parts_and_reports_them(monkeypatch):
    from cee import ask as pipeline
    from cee.retrieve.fts import Query
    events = []
    t = pipeline._Trace(lambda *e: events.append(e))
    hits = [hit("MS-10K-2025#1")]
    raw = Answer(answerable=True, behavior="answer", claims=[
        {"text": "m", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"},
        {"text": "Training - Raymond James: unknown", "chunk_ids": [], "part_id": "p2"}])
    a, _ = pipeline.answer_for(Q, Query(question=Q, entities=["MS", "RJF"]), hits, "mock", raw=raw, trace=t,
                               plan=TWO)
    done = {s: x for s, st, x in events if st == "done"}
    assert done["check"].endswith(", 1 empty cell moved to gaps")
    assert [g.flags for g in a.gaps] == [["uncited_cell"]]     # the moved cell names p2: p2 covered
    a2, _ = pipeline.answer_for(Q, Query(question=Q, entities=["MS", "RJF"]), hits, "mock", raw=Answer(
        answerable=True, behavior="answer", claims=[{"text": "m", "chunk_ids": ["MS-10K-2025#1"], "part_id": "p1"}]),
        trace=t, plan=TWO)
    assert [g.flags for g in a2.gaps] == [["part_gap"]]
    assert events[-1][2].endswith("(1 added by code for unanswered parts)")


def test_answer_cache_key_takes_parts_only_when_given():
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("eval_run_215", Path(__file__).parents[1] / "scripts" / "eval_run.py")
    er = importlib.util.module_from_spec(spec)
    sys.modules["eval_run_215"] = er
    spec.loader.exec_module(er)
    qq = {"id": "Q7", "text": "t"}
    args = ("v4", "snap", "anthropic", "m", ["a#1"])
    assert er.cache_key(qq, *args) == er.cache_key(qq, *args, 8000, None)
    with_parts = er.cache_key(qq, *args, 8000, er.parts_of(TWO))
    assert with_parts != er.cache_key(qq, *args)
    assert with_parts != er.cache_key(qq, *args, 8000, er.parts_of(plan(("p1", Q, ["MS"]))))
    assert er.parts_of(None) is None and er.parts_of(TWO)[1] == ["p2", Q, ["RJF"]]
