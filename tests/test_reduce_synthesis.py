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


# --- #295: comparison verdict re-filed in the v8 brief form; reduce effort per form -------------------

VERDICT_OFF = ("A valid side-by-side client-assets-per-advisor figure across the three firms cannot be computed, "
               "because each firm measures client assets and advisor headcount on a different basis.")
VERDICT_LOW = ("Client assets per advisor cannot be validly compared across the three firms, because their "
               "advisor-headcount and client-asset measures are each defined differently.")


def q24_off_shape():
    """The #292 Q24 v8-off shape: fact aspects a1 (client assets) and a2 (headcount), comparison aspect a4 holding a
    definition item for every firm."""
    a1, a2 = Aspect("a1", "Client assets for the firm."), Aspect("a2", "Advisor headcount for the firm.")
    a4 = Aspect("a4", "Whether client assets per advisor can be compared side by side.", kind="comparison")
    hits, cells = [], []
    for f in ("MS", "SCHW", "RJF"):
        hits += [H(f"{f}-TR#1", f, text=f"{f} client assets."), H(f"{f}-10K#2", f, text=f"{f} advisors."),
                 H(f"{f}-SUPP#3", f, text=f"{f} defines client assets its own way.")]
        cells += [cell(f"a1.{f}", "fact", [item(f"{f}-TR#1", f"{f} client assets.")]),
                  cell(f"a2.{f}", "fact", [item(f"{f}-10K#2", f"{f} advisors.")]),
                  cell(f"a4.{f}", "fact", [item(f"{f}-SUPP#3", f"{f} defines client assets its own way.")])]
    return matrix("Client assets per advisor across the three -- and is that comparison even valid?", [a1, a2, a4],
                  cells, hits)


def _raw(*claims):
    return {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [],
            "claims": [{"text": t, "chunk_ids": ids, "part_id": p} for t, ids, p in claims]}


def test_v8_verdict_under_another_part_id_is_refiled_not_written(v8):
    m = q24_off_shape()
    ids = ["MS-SUPP#3", "SCHW-10K#2", "RJF-SUPP#3"]   # a4 cells of MS and RJF (2 firms), SCHW's headcount cell
    a, info = run_finish(m, _raw((VERDICT_OFF, ids, "a1"), ("MS reported client assets.", ["MS-TR#1"], "a1.MS")),
                         query=query_of(m))
    assert info["comparison_missing"] == [] and not any("comparison_missing" in g.flags for g in a.gaps)
    assert info["comparison_refiled"] == [{"claim": 0, "old_part_id": "a1", "aspect": "a4"}]
    assert a.claims[0].part_id == "a4" and a.claims[0].text == VERDICT_OFF and a.claims[0].chunk_ids == ids
    assert a.claims[1].part_id == "a1.MS" and len(a.claims) == 2


@pytest.mark.parametrize("text, ids, why", [
    ("MS, Schwab and Raymond James each report client assets and advisors.", ["MS-SUPP#3", "RJF-SUPP#3"], "no verdict"),
    (VERDICT_LOW, ["MS-SUPP#3", "MS-10K#2"], "one firm's a4 cell"),
    (VERDICT_LOW, ["MS-TR#1", "RJF-TR#1"], "no a4 cell"),
])
def test_v8_sentence_without_verdict_or_cited_a4_cells_is_not_refiled(v8, text, ids, why):
    m = q24_off_shape()
    a, info = run_finish(m, _raw((text, ids, "a1")), query=query_of(m))
    assert info["comparison_refiled"] == [] and info["comparison_missing"] == ["a4"], why
    assert a.claims[0].part_id == "a1"


def test_v8_flagged_verdict_is_not_refiled(v8):
    m = q24_off_shape()
    a, info = run_finish(m, _raw((VERDICT_LOW, ["MS-SUPP#3", "RJF-SUPP#3", "XX-NOT#9"], "a1")), query=query_of(m))
    assert "unmatched_citation" in a.claims[0].flags or "outside_matrix" in a.claims[0].flags
    assert info["comparison_refiled"] == [] and info["comparison_missing"] == ["a4"]


def test_v8_verdict_already_under_the_aspect_needs_no_refile(v8):
    m = q24_off_shape()
    _, info = run_finish(m, _raw((VERDICT_LOW, ["MS-SUPP#3", "RJF-SUPP#3"], "a4")), query=query_of(m))
    assert info["comparison_refiled"] == [] and info["comparison_missing"] == []


def test_v52_answer_is_never_refiled(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    m = q24_off_shape()
    a, info = run_finish(m, _raw((VERDICT_OFF, ["MS-SUPP#3", "RJF-SUPP#3"], "a1")), query=query_of(m))
    assert info["comparison_refiled"] == [] and info["comparison_missing"] == ["a4"] and a.claims[0].part_id == "a1"


@pytest.mark.parametrize("text, verdict", [
    (VERDICT_OFF, True), (VERDICT_LOW, True),
    ("The firms' advisor counts are not comparable.", True),
    ("A like-for-like comparison is not possible.", True),
    ("Schwab's client assets rose 12% compared with 2025.", False),
    ("Edward Jones reports its advisor count on a quarterly basis.", False),
    ("Morgan Stanley reported $10.5 trillion in total client assets as of September 30, 2026.", False),
    ("Raymond James compared favorably on recruiting, the CEO said.", False),
])
def test_verdict_pattern(text, verdict):
    import re
    assert bool(re.search(P.COMPARISON_VERDICT, text, re.I)) is verdict


def test_reduce_effort_per_form(monkeypatch):
    from cee.answer import llm
    monkeypatch.setenv("REDUCE_PROMPT", "v8")
    for v in ("DEEPSEEK_EFFORT_REDUCE", "DEEPSEEK_EFFORT_REDUCE_BRIEF", "DEEPSEEK_STREAM"):
        monkeypatch.delenv(v, raising=False)
    m = two_firm()
    brief_q, list_q = query_of(m), query_of(m, WINDOW)
    assert R.effort(m, brief_q) == "off" and R.effort(m, list_q) == "low"
    assert R.max_tokens("deepseek", m, brief_q) == 64000 and R.max_tokens("deepseek", m, list_q) == 128000
    assert R.request_version("deepseek", m, brief_q) == "ds-strict-2-reduce-off-c64000-s1"
    assert R.request_version("deepseek", m, list_q) == "ds-strict-2-reduce-low-c128000-s1" \
        == llm.request_version("deepseek", "reduce")
    off, low = R.requests("q", m, brief_q, "deepseek"), R.requests("q", m, list_q, "deepseek")
    assert off["extra_body"] == {"thinking": {"type": "disabled"}} and off["max_tokens"] == 64000
    assert low["extra_body"]["reasoning_effort"] == "low" and low["max_tokens"] == 128000
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE_BRIEF", "low")
    assert R.request_version("deepseek", m, brief_q) == "ds-strict-2-reduce-low-c128000-s1"
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")   # no brief form: the stage setting for every question
    assert R.effort(m, brief_q) == "low"


def test_app_run_cache_reduce_key_follows_the_form_effort(monkeypatch):
    from cee.answer import runcache
    monkeypatch.setenv("REDUCE_PROMPT", "v8")
    monkeypatch.delenv("DEEPSEEK_EFFORT_REDUCE_BRIEF", raising=False)
    m = two_firm()
    k_off = runcache.reduce_key(m.question, m, query_of(m), "deepseek")
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE_BRIEF", "low")
    assert runcache.reduce_key(m.question, m, query_of(m), "deepseek") != k_off
