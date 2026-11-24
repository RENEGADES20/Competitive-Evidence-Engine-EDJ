"""#292 (plans/0292-reduce-synthesis.md): reduce prompt v7, a direct answer plus a short cited synthesis; window /
all-recency questions keep v5.2's list form. 0 real calls."""
import json

import pytest

from cee.answer import prompt as P
from cee.answer import reduce as R
from cee.app.views import ask_page as AP
from cee.retrieve.fts import Query
from cee.retrieve.planner import Aspect
from tests.test_reduce import H, cell, item, matrix, plan_of, q24_shaped, run_finish  # noqa: F401 (fixture)
from tests.test_reduce import _one_population  # noqa: F401  (autouse fixture)

WINDOW = ("2026-08-19", "2026-11-17")


def two_firm():
    """Two fact aspects over MS and RJF, plus a recency aspect (the shape of Q5's plan: one recency among facts)."""
    a1, a2, a3 = Aspect("a1", "Technology investment."), Aspect("a2", "Advisor tools."), Aspect("a3", "What is new.",
                                                                                                    kind="recency")
    hits = [H("MS-TR#1", "MS", text="MS invests in AI for advisors."), H("RJF-TR#1", "RJF", text="RJF invests in CRM."),
            H("MS-TR#2", "MS", text="MS rolled out a new workstation."), H("RJF-PR#3", "RJF", text="RJF opened a hub.")]
    cells = [cell("a1.MS", "fact", [item("MS-TR#1", "MS invests in AI for advisors.")]),
             cell("a1.RJF", "fact", [item("RJF-TR#1", "RJF invests in CRM.")]),
             cell("a2.MS", "fact", [item("MS-TR#2", "MS rolled out a new workstation.")]),
             cell("a2.RJF", "not_found"),
             cell("a3.MS", "not_found"),
             cell("a3.RJF", "fact", [item("RJF-PR#3", "RJF opened a hub.")])]
    return matrix("Where are Morgan Stanley and Raymond James investing in advisor technology?", [a1, a2, a3], cells,
                  hits)


def query_of(m, window=None):
    return Query(question=m.question, entities=[r for r in m.rows if r not in ("research", "all")], window=window)


@pytest.fixture
def v7(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v7")


# --- the one form rule ------------------------------------------------------------------------------

def test_form_rule_per_version(monkeypatch):
    fact, rec = Aspect("a1", "x"), Aspect("a2", "y", kind="recency")
    plain, windowed = Query(question="q"), Query(question="q", window=WINDOW)
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")   # v5.2: #291's rule, unchanged
    assert R.list_form([fact, rec], plain) and R.list_form([fact], windowed) and not R.list_form([fact], plain)
    monkeypatch.setenv("REDUCE_PROMPT", "v7")
    assert not R.list_form([fact, rec], plain)           # one recency aspect among facts: synthesis
    assert R.list_form([rec, rec], plain) and R.list_form([fact], windowed)
    assert not R.list_form([], plain)


def test_ask_page_uses_the_same_rule_for_the_streamed_and_the_final_answer(v7):
    """The streamed answer reads the plan's aspects, the final one the matrix's: one helper, the same form."""
    m = two_firm()
    for q in (query_of(m), query_of(m, WINDOW)):
        streamed = AP.list_form(q, list(plan_of(m).aspects))
        final = AP.list_form(q, list(m.aspects))
        assert streamed == final == R.list_form(m.aspects, q) == (not R.synthesis(m, q))


# --- version, prompt and message --------------------------------------------------------------------

def test_v52_request_is_unchanged_and_the_default_is_v8(monkeypatch):
    monkeypatch.delenv("REDUCE_PROMPT", raising=False)
    assert R.prompt_version() == "v8"   # #292: v8 passed the plan rule at reduce effort low
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    m = two_firm()
    assert R.prompt_version(m, query_of(m)) == "v5.2" and R.system_prompt(m, query_of(m)) == P.SYSTEM_PROMPT_V5
    assert "every item needs a why-line" in R.reduce_message(m.question, m, query_of(m))


def test_v7_synthesis_prompt_and_message(v7):
    m = two_firm()
    q = query_of(m)
    assert R.prompt_version() == "v7" and R.prompt_version(m, q) == "v7"
    assert R.system_prompt(m, q) == P.SYSTEM_PROMPT_V7 and "Prompt version: v7." in P.SYSTEM_PROMPT_V7
    msg = R.reduce_message(m.question, m, q)
    assert "why-line" not in msg and "      context:" not in msg and "      related:" not in msg
    req = R.requests(m.question, m, q, "deepseek")
    assert req["messages"][0]["content"] == P.SYSTEM_PROMPT_V7


def test_v7_list_form_question_is_v52_byte_for_byte(monkeypatch):
    m = two_firm()
    q = query_of(m, WINDOW)
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    old = (R.prompt_version(m, q), json.dumps(R.requests(m.question, m, q, "deepseek"), sort_keys=True),
           json.dumps(R.mock_reduce(m, q), sort_keys=True))
    monkeypatch.setenv("REDUCE_PROMPT", "v7")
    new = (R.prompt_version(m, q), json.dumps(R.requests(m.question, m, q, "deepseek"), sort_keys=True),
           json.dumps(R.mock_reduce(m, q), sort_keys=True))
    assert old == new and new[0] == "v5.2"


# --- mock and checks in the synthesis form ----------------------------------------------------------

def test_mock_v7_direct_sentence_then_one_sentence_per_aspect_and_no_part_gap(v7):
    m = two_firm()
    raw = R.mock_reduce(m, query_of(m))
    claims = raw["claims"]
    assert claims[0]["text"].startswith("In short: ") and claims[0]["part_id"] == "a1"
    assert {c["part_id"] for c in claims} <= {"a1", "a2", "a3"} and "Why it might matter" not in json.dumps(raw)
    assert any(set(c["chunk_ids"]) == {"MS-TR#1", "RJF-TR#1"} for c in claims)   # one sentence, two cells
    a, info = run_finish(m, raw, query=query_of(m))
    assert info["version"] == "v7" and info["part_gaps"] == 0 and info["why_line_missing"] == 0
    assert a.claims[0].text.startswith("In short: ")
    assert all(not c.flags for c in a.claims)


def test_aspect_sentence_covers_each_cell_it_cites_and_only_those(v7):
    m = two_firm()
    raw = {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "Both firms invest in advisor technology.", "chunk_ids": ["MS-TR#1", "RJF-TR#1"], "part_id": "a1"},
        {"text": "RJF opened a hub.", "chunk_ids": ["RJF-PR#3"], "part_id": "a3"}]}
    a, info = run_finish(m, raw, query=query_of(m))
    gaps = {g.part_id for g in a.gaps if "part_gap" in g.flags}
    assert gaps == {"a2.MS"}   # a holding cell no sentence cites still gets its part gap
    assert info["why_line_missing"] == 0 and info["reordered"] == 0


def test_dedupe_keeps_the_direct_sentence(v7):
    m = two_firm()
    raw = {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "MS invests in AI.", "chunk_ids": ["MS-TR#1"], "part_id": "a1"},
        {"text": "MS invests in AI for its advisors.", "chunk_ids": ["MS-TR#1"], "part_id": "a1.MS"}]}
    a, info = run_finish(m, raw, query=query_of(m))
    assert a.claims[0].text == "MS invests in AI." and len(info["duplicates_removed"]) == 1


def test_computation_claim_with_the_aspect_id_counts(v7):
    m = q24_shaped()
    need = sorted(set(m.cells["a1.EDJ"].derivation["input_chunk_ids"])
                  | set(m.cells["a1.EDJ"].derivation.get("population_chunk_ids") or []))
    q = Query(question=m.question, entities=["EDJ", "SCHW", "MS"])
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "Edward Jones: client assets per advisor is computable on this evidence.", "chunk_ids": need,
         "part_id": "a1"},
        {"text": "Comparison is valid only for Edward Jones.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]}
    a, info = run_finish(m, raw, query=q)
    assert info["code_computability"] == []


def test_aspect_sentence_on_adjacent_only_cells_is_flagged(v7):
    m = q24_shaped()
    q = Query(question=m.question, entities=["EDJ", "SCHW", "MS"])
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "Schwab serves 16,000 RIA client firms.", "chunk_ids": ["SCHW-TR#10"], "part_id": "a3"}]}
    a, _ = run_finish(m, raw, query=q)
    assert "claim_from_adjacent" in next(c for c in a.claims if "SCHW-TR#10" in c.chunk_ids).flags


# --- v8: brief answer, no full coverage, computability box (#292 v8 amendment) ----------------------

@pytest.fixture
def v8(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v8")


def test_v8_is_a_brief_synthesis_version_and_list_form_stays_v52(v8):
    m = two_firm()
    assert R.brief(m, query_of(m)) and R.prompt_version(m, query_of(m)) == "v8"
    assert R.system_prompt(m, query_of(m)) == P.SYSTEM_PROMPT_V8 and "Prompt version: v8." in P.SYSTEM_PROMPT_V8
    assert not R.brief(m, query_of(m, WINDOW)) and R.prompt_version(m, query_of(m, WINDOW)) == "v5.2"


def test_mock_v8_is_at_most_five_cited_sentences_and_uncited_holding_cells_get_no_part_gap(v8):
    m = two_firm()
    raw = R.mock_reduce(m, query_of(m))
    assert 1 <= len(raw["claims"]) <= P.BRIEF_MAX_SENTENCES and all(c["chunk_ids"] for c in raw["claims"])
    only_first = {**raw, "claims": raw["claims"][:1]}
    a, info = run_finish(m, only_first, query=query_of(m))
    assert info["version"] == "v8" and info["part_gaps"] == 0   # a1.RJF, a2.MS, a3.RJF: in the evidence list
    assert {g.part_id for g in a.gaps if "part_gap" in g.flags} == set()


def test_every_uncited_holding_cell_is_in_the_evidence_list(v8):
    from types import SimpleNamespace
    from cee.ask import evidence_lines
    from cee.answer.matrix import holds
    m = two_firm()
    raw = R.mock_reduce(m, query_of(m))
    a, _ = run_finish(m, {**raw, "claims": raw["claims"][:1]}, query=query_of(m))
    cited = {k for c in a.claims for k in c.chunk_ids}
    lines = evidence_lines(SimpleNamespace(hits=list(m.hits.values())), list(m.cells.values()))
    listed = {k for line in lines for k in line["chunk_ids"]}
    for c in m.cells.values():
        if holds(c) and not ({k for i in c.counting_items for k in i.chunk_ids} & cited):
            assert {k for i in c.counting_items for k in i.chunk_ids} <= listed, c.id


def test_v8_computability_goes_to_the_box_with_inputs_and_population_sources(v8):
    m = q24_shaped()
    q = Query(question=m.question, entities=["EDJ", "SCHW", "MS"])
    d = m.cells["a1.EDJ"].derivation
    need = set(d["input_chunk_ids"]) | set(d.get("population_chunk_ids") or [])
    # the model's own sentence already states the verdict, citing every input: the box is still added
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "Client assets per advisor cannot be compared across the five.", "chunk_ids": sorted(need),
         "part_id": "a1"},
        {"text": "Comparison is valid only for Edward Jones.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]}
    a, info = run_finish(m, raw, query=q)
    assert info["code_computability"] == ["a1.EDJ"] and len(a.claims) == 2
    box = a.computations[0]
    assert box.text.startswith("Edward Jones: ") and ("computed by code" in box.text or "not computed" in box.text)
    assert need <= set(box.chunk_ids) and "code_computability" in box.flags
    assert not any("code_computability" in c.flags for c in a.claims)


def test_mock_v8_q24_shape_keeps_the_box(v8):
    m = q24_shaped()
    q = Query(question=m.question, entities=["EDJ", "SCHW", "MS"])
    a, info = run_finish(m, R.mock_reduce(m, q), query=q)
    assert a.computations and info["comparison_missing"] == [] and len(a.claims) <= P.BRIEF_MAX_SENTENCES


def test_computations_default_empty_so_old_records_load():
    from cee.answer.schema import Answer
    old = {"answerable": True, "behavior": "answer", "claims": [{"text": "x", "chunk_ids": ["a#1"]}],
           "adjacent": [], "gaps": [], "caveats": []}
    a = Answer(**old)
    assert a.computations == [] and Answer(**a.model_dump()).computations == []


def test_ask_page_draws_the_box_outside_the_paragraph_with_footnotes(v8):
    from cee.app import components as ui
    from cee.answer.schema import Claim
    h = H("EDJ-10Q#60")
    cards, items = AP.evidence_cards([], [Claim(text="A.", chunk_ids=["EDJ-10Q#60"])], [h],
                                     [Claim(text="Edward Jones: not computed.", chunk_ids=["EDJ-10Q#60"],
                                            flags=["code_computability"])])
    assert [i.get("box", False) for i in items] == [False, True] and len(cards) == 1
    html = ui.computability_html(items[1])
    assert "Computability:" in html and 'href="#cee-ev-1"' in html and "code_computability" not in html
