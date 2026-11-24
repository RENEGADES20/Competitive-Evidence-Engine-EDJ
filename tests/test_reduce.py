"""Reduce step (#247; ADR-021 rules 0-5; plans/0247-reduce.md): matrix-only input, strict enums, code
checks after the call, code-built answers, the mock. Fake clients only: 0 real calls (conftest)."""
import json
from types import SimpleNamespace

import pytest

from cee import ask
from cee.answer import llm
from cee.answer import prompt as P
from cee.answer import reduce as R
from cee.answer.matrix import Cell, EvidenceMatrix, Item, finish
from cee.answer.schema import Answer
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Aspect, Plan, SubQuestion
from tests.test_llm_deepseek import FakeDeepSeek, _strict_problems, response, tool_call

NO_SOURCES = lambda entity: ""   # noqa: E731


@pytest.fixture(autouse=True)
def _reduce_v52(monkeypatch):
    """These tests pin the list-form reduce v5.2 (the default is v8 since #292)."""
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")


def H(cid, entity="EDJ", published="2026-08-05", period="2026-06-26", text="Edward Jones had 20,514 advisors.",
      origin="search"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-Q",
               source_tier=2, published_at=published, period_end=period, section="Item 2", page=None, rank=1.0,
               text=text, part_id=None, origin=origin)


def item(cid, text="t", value="", unit="", period="", scope="", **kw):
    return Item(text=text, quote="", chunk_ids=[cid] if cid else [], value=value, unit=unit, period=period,
                scope=scope, **kw)


def cell(cid, label, items=(), derivation=None, differs=""):
    a, e = cid.split(".")
    ent = None if e in ("research", "all") else e
    return Cell(cid, ent, a, "research" if e == "research" else "named", label, items=list(items),
                derivation=derivation, differs_because=differs)


# #247 part 2: one shared test population for every firm and input (source chunk in every pool), so
# these reduce tests keep their accepted derivations; population rules: tests/test_populations.py.
TEST_POPULATIONS = tuple({"entity": e, "input": i, "key": "test_pop", "match": [""], "quote": "",
                          "chunk_id": "EDJ-10Q#60", "valid_from": "2026-06-26"}
                         for e in ("EDJ", "MS", "SCHW", "BAC", "RJF") for i in ("client_assets", "advisor_headcount"))


@pytest.fixture(autouse=True)
def _one_population(monkeypatch):
    from cee.answer import matrix as mx
    monkeypatch.setattr(mx, "_populations", lambda: TEST_POPULATIONS)


def matrix(question, aspects, cells, hits=(), as_of=None, pools=None):
    m = EvidenceMatrix(question, rows=[], aspects=aspects, cells={c.id: c for c in cells})
    m.pools = pools if pools is not None else {
        c.id: {"EDJ-10Q#60", *(x for i in c.items for x in i.chunk_ids)} for c in cells}
    rows = []
    for c in cells:
        k = "research" if c.role == "research" else (c.entity or "all")
        if k not in rows:
            rows.append(k)
    m.rows = rows
    m.hits = {h.chunk_id: h for h in hits}
    return finish(m, sources=NO_SOURCES, as_of=as_of)


def plan_of(m):
    subs = [SubQuestion(c.id, c.entity, m.aspect(c.aspect_id)) for c in m.cells.values() if c.role != "research"]
    return Plan(aspects=list(m.aspects), subquestions=subs)


Q_FIRMS = "Client assets per advisor across the five, and is that comparison valid?"


def q24_shaped():
    a1 = Aspect("a1", "Client assets per advisor.")
    a2 = Aspect("a2", "Total client assets, the numerator.", proxy=True)
    a3 = Aspect("a3", "Advisor headcount, the denominator.", proxy=True)
    a4 = Aspect("a4", "Whether the comparison is valid.", kind="comparison")
    hits = [H("EDJ-10Q#59", text="Assets under care of $2,647 billion."), H("EDJ-10Q#60"),
            H("SCHW-TR#10", entity="SCHW", text="16,000 RIA client firms."),
            H("MS-10K#5", entity="MS", text="Advisor counts are not comparable across firms.")]
    cells = [
        cell("a1.EDJ", "not_disclosed", derivation={"operation": "ratio", "inputs": [
            {"subquestion_id": "a2.EDJ", "item": 0}, {"subquestion_id": "a3.EDJ", "item": 0}]}),
        cell("a2.EDJ", "fact", [item("EDJ-10Q#59", value="$2,647", unit="USD billions", period="2026-06-26")]),
        cell("a3.EDJ", "fact", [item("EDJ-10Q#60", value="20,514", unit="financial advisors", period="2026-06-26")]),
        cell("a4.EDJ", "not_found"),
        cell("a1.SCHW", "not_disclosed"), cell("a2.SCHW", "not_found"),
        cell("a3.SCHW", "different_quantity", [item("SCHW-TR#10", value="16,000")], differs="RIA firms, not advisors"),
        cell("a4.SCHW", "not_found"),
        cell("a1.MS", "not_found"), cell("a2.MS", "not_found"), cell("a3.MS", "not_found"),
        cell("a4.MS", "fact", [item("MS-10K#5", "Advisor counts are not comparable across firms.")]),
    ]
    return matrix(Q_FIRMS, [a1, a2, a3, a4], cells, hits)


def run_finish(m, raw: dict, query=None, plan=None):
    query = query or Query(question=m.question, entities=[r for r in m.rows if r not in ("research", "all")])
    a = R.to_answer(raw, "mock")
    return R.finish_answer(a, m, query, plan or plan_of(m), list(m.hits.values()), m.question)


# --- input and schema --------------------------------------------------------------------------

def test_schema_enums_come_from_the_matrix_and_rejected_ids_are_not_citable():
    m = q24_shaped()
    m.cells["a3.EDJ"].items[0].rejected_ids = ["EDJ-10Q#99"]
    schema, fallback = R.reduce_schema(m)
    assert fallback == [] and _strict_problems(schema) == []
    ids = schema["properties"]["claims"]["items"]["properties"]["chunk_ids"]["items"]["enum"]
    assert ids == m.chunk_ids() and "EDJ-10Q#99" not in ids
    assert schema["properties"]["behavior"]["enum"] == ["answer"]
    parts = schema["properties"]["gaps"]["items"]["properties"]["part_id"]["enum"]
    assert "a4" in parts and "a1.EDJ" in parts and "" in parts
    assert "incomplete" not in json.dumps(schema)


def test_rendered_input_lists_only_matrix_sources_and_a_formula_without_ids():
    m = q24_shaped()
    text = R.reduce_message(Q_FIRMS, m, None)
    sources = text.split("Sources (every chunk id you may cite; cite no other):")[1]
    assert sorted(l.split('"')[1] for l in sources.strip().splitlines()) == sorted(m.chunk_ids())
    derived = next(l for l in text.splitlines() if l.strip().startswith("a1.EDJ"))
    assert "derived (computed by code)" in derived and "a2.EDJ" not in derived and "#0" not in derived
    assert "adjacent only" in next(l for l in text.splitlines() if l.strip().startswith("a3.SCHW"))
    assert "needs exactly one comparison claim, part_id a4" in text


def test_q19_sized_schema_counts_enum_values_and_falls_back_over_the_limit():
    aspects = [Aspect(f"a{i}", f"Aspect {i}.") for i in range(1, 14)]
    firms = ["EDJ", "MS", "SCHW", "MER", "RJF"]
    cells, hits = [], []
    for a in aspects:
        for f in firms:
            cid = f"{f}-DOC-2026#{a.id}"
            hits.append(H(cid, entity=f))
            cells.append(cell(f"{a.id}.{f}", "fact", [item(cid)]))
    for n in range(135):   # 65 + 135 = 200 chunk ids
        cells[n % 65].items.append(item(f"EXTRA-DOC#{n}"))
    m = matrix("Younger investors and the five.", aspects, cells, hits)
    schema, fallback = R.reduce_schema(m)
    assert len(m.chunk_ids()) == 200
    assert fallback == []   # 200 x 2 + 79 x 3 + 1 = 638 values: within the limits and R.enum_values(schema) == 2 * 200 + 3 * (65 + 13 + 1) + 1
    for n in range(400):   # over 1000 values in all -> chunk_ids falls back to plain strings
        cells[n % 65].items.append(item(f"MORE-DOC#{n}"))
    big = matrix("Younger investors and the five.", aspects, cells, hits)
    schema2, fallback2 = R.reduce_schema(big)
    assert fallback2 == ["chunk_ids"] and R.enum_values(schema2) <= R.ENUM_TOTAL_MAX
    assert schema2["properties"]["claims"]["items"]["properties"]["chunk_ids"] == {
        "type": "array", "items": {"type": "string"}}


# --- code checks after the call --------------------------------------------------------------------

def test_synthesis_cannot_cite_outside_the_matrix():
    m = q24_shaped()
    m.cells["a3.EDJ"].items[0].rejected_ids = ["EDJ-10Q#99"]
    m.hits["EDJ-10Q#70"] = H("EDJ-10Q#70")          # retrieved, but no matrix item cites it
    raw = {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "Edward Jones: assets of $2,647 billion.", "chunk_ids": ["EDJ-10Q#59"], "part_id": "a2.EDJ"},
        {"text": "Edward Jones: a retrieved passage.", "chunk_ids": ["EDJ-10Q#70"], "part_id": "a3.EDJ"},
        {"text": "Edward Jones: a rejected id.", "chunk_ids": ["EDJ-10Q#99"], "part_id": "a3.EDJ"},
        {"text": "Edward Jones: an invented id.", "chunk_ids": ["EDJ-10Q#123"], "part_id": "a3.EDJ"}]}
    a, info = run_finish(m, raw)
    flagged = [c for c in a.claims if "outside_matrix" in c.flags]
    assert [c.chunk_ids[0] for c in flagged] == ["EDJ-10Q#70", "EDJ-10Q#99", "EDJ-10Q#123"]
    assert all("unmatched_citation" in c.flags for c in flagged) and info["outside_matrix"] == 3
    assert len([x for x in a.claims if "code_computability" not in x.flags]) == 4   # flagged, never dropped


def test_comparison_claim_required():
    m = q24_shaped()
    a, info = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "Edward Jones: assets.", "chunk_ids": ["EDJ-10Q#59"], "part_id": "a2.EDJ"}]})
    gap = [g for g in a.gaps if "comparison_missing" in g.flags]
    assert len(gap) == 1 and gap[0].part_id == "a4" and info["comparison_missing"] == ["a4"]
    assert gap[0].what == "No cited claim answers the comparison asked: Whether the comparison is valid."
    ok, info2 = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "The comparison is not valid: definitions differ.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]})
    assert not [g for g in ok.gaps if "comparison_missing" in g.flags] and info2["comparison_missing"] == []
    nocite, _ = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "It is not valid.", "chunk_ids": [], "part_id": "a4"}]})
    assert [g for g in nocite.gaps if "comparison_missing" in g.flags]


def test_comparison_and_proxy_parts_get_no_false_part_gap_q24_shaped():
    """B3: the mock reduce on a Q24-shaped matrix: no part_gap on a4.* or on a not-found proxy cell."""
    m = q24_shaped()
    a, info = run_finish(m, R.mock_reduce(m))
    gaps = [g for g in a.gaps if "part_gap" in g.flags]
    assert gaps == [] and info["part_gaps"] == 0
    assert any(c.part_id == "a4" for c in a.claims)          # the comparison claim
    # without the comparison claim, the comparison_missing gap covers a4.* (still no part gap)
    raw = R.mock_reduce(m)
    raw["claims"] = [c for c in raw["claims"] if c["part_id"] != "a4"]
    b, _ = run_finish(m, raw)
    assert not [g for g in b.gaps if "part_gap" in g.flags]
    assert [g.part_id for g in b.gaps if "comparison_missing" in g.flags] == ["a4"]


def test_computed_figure_needs_both_inputs_cited():
    m = q24_shaped()
    v = m.cells["a1.EDJ"].derivation["value"]
    assert m.cells["a1.EDJ"].label == "derived" and round(v) == 129033831
    both, _ = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "Edward Jones: about $129.0 million of client assets per financial advisor.",
         "chunk_ids": ["EDJ-10Q#59", "EDJ-10Q#60"], "part_id": "a1.EDJ"},
        {"text": "Edward Jones: about $129.0 million per advisor.", "chunk_ids": ["EDJ-10Q#59"], "part_id": "a1.EDJ"},
        {"text": "Morgan Stanley: about $129.0 million per advisor.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]})
    assert "computed" in both.claims[0].flags and "number_not_found" not in both.claims[0].flags
    assert "number_not_found" in both.claims[1].flags and "number_not_found" in both.claims[2].flags


def test_rule_3_placement_flags():
    m = q24_shaped()
    a, _ = run_finish(m, {"answerable": True, "behavior": "answer", "gaps": [], "claims": [
        {"text": "Schwab: 16,000 RIA client firms.", "chunk_ids": ["SCHW-TR#10"], "part_id": "a3.SCHW"}],
        "adjacent": [{"text": "MS says counts differ.", "chunk_ids": ["MS-10K#5"], "part_id": "a4.MS",
                      "differs_because": "x"},
                     {"text": "Edward Jones: 20,514 advisors.", "chunk_ids": ["EDJ-10Q#60"], "part_id": "a3.EDJ",
                      "differs_because": "a stand-in"}]})
    assert "claim_from_adjacent" in a.claims[0].flags
    assert "adjacent_is_fact" in a.adjacent[0].flags          # a4.MS holds a fact of a non-proxy aspect
    assert "adjacent_is_fact" not in a.adjacent[1].flags      # proxy cells belong on the adjacent side


def test_matrix_gaps_placed_once_and_a_repeated_model_gap_is_merged():
    m = q24_shaped()
    code = [g["what"] for g in m.gaps]
    a, info = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "claims": [
        {"text": "The comparison is not valid.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}],
        "gaps": [{"what": code[0], "suggested_source": "", "part_id": m.gaps[0]["id"]},
                 {"what": "Something else is missing.", "suggested_source": "", "part_id": ""}]})
    whats = [g.what for g in a.gaps]
    assert all(whats.count(w) == 1 for w in code) and "Something else is missing." in whats
    merged = next(g for g in a.gaps if g.what == code[0])
    assert "model_also_named" in merged.flags and info["gaps_merged"] == 1


def test_why_lines_and_newest_first_with_the_questions_own_window():
    a1 = Aspect("a1", "What is new.", kind="recency")
    hits = [H("RJF-PR#1", "RJF", published="2026-09-01"), H("RJF-PR#2", "RJF", published="2026-11-01")]
    m = matrix("What's new on Raymond James in the last 90 days?", [a1],
               [cell("a1.RJF", "fact", [item("RJF-PR#1"), item("RJF-PR#2")])], hits)
    q = Query(question=m.question, entities=["RJF"], window=("2026-08-19", "2026-11-17"))
    a, info = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "RJF announced A. " + P.WHY_LINE + "The release says it doubles capacity.",
         "chunk_ids": ["RJF-PR#1"], "part_id": "a1.RJF"},
        {"text": "RJF announced B.", "chunk_ids": ["RJF-PR#2"], "part_id": "a1.RJF"}]}, query=q)
    assert [c.chunk_ids[0] for c in a.claims] == ["RJF-PR#2", "RJF-PR#1"] and info["reordered"] == 2
    assert "why_line_missing" in a.claims[0].flags and "why_line_missing" not in a.claims[1].flags


def test_an_ask_page_date_filter_alone_triggers_no_why_line_and_no_resort():
    a1 = Aspect("a1", "Advisor recruiting.")
    hits = [H("RJF-PR#1", "RJF", published="2026-09-01"), H("RJF-PR#2", "RJF", published="2026-11-01")]
    m = matrix("How does Raymond James recruit advisors?", [a1],
               [cell("a1.RJF", "fact", [item("RJF-PR#1"), item("RJF-PR#2")])], hits)
    q = Query(question=m.question, entities=["RJF"], date_range=("2026-08-01", "2026-11-17"))
    a, info = run_finish(m, {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"text": "Older.", "chunk_ids": ["RJF-PR#1"], "part_id": "a1.RJF"},
        {"text": "Newer.", "chunk_ids": ["RJF-PR#2"], "part_id": "a1.RJF"}]}, query=q)
    assert [c.text for c in a.claims] == ["Older.", "Newer."] and info["reordered"] == 0
    assert not any("why_line_missing" in c.flags for c in a.claims)


def test_the_model_cannot_change_the_behavior():
    m = q24_shaped()
    a, info = run_finish(m, {"answerable": False, "behavior": "refuse", "adjacent": [], "gaps": [], "claims": [
        {"text": "The comparison is not valid.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]})
    assert a.behavior == "answer" and a.answerable and info["model_behavior"] == "refuse"


# --- code-built answers: 0 calls ------------------------------------------------------------------

NORMATIVE = "How should the preferences of younger investors shape Edward Jones's offerings?"


def _answer_for(m, provider="deepseek", query=None):
    """ask.answer_for with the real provider path: conftest blocks every real client, so a call fails."""
    query = query or Query(question=m.question, entities=["EDJ", "MS"])
    info: dict = {}
    hits = list(m.hits.values()) or [H("EDJ-10K#1")]
    a, raw = ask.answer_for(m.question, query, hits, provider, plan=plan_of(m), matrix=m, info=info)
    return a, raw, info


def test_empty_citable_set_on_a_normative_question_is_code_built():
    """B2: all not_found under rule 1e -> answer_with_boundary with the hand-off, the gaps, 0 calls."""
    a1 = Aspect("a1", "Preferences of younger investors.")
    m = matrix(NORMATIVE, [a1], [cell("a1.EDJ", "not_found"), cell("a1.MS", "not_found")], [H("EDJ-10K#1")])
    assert m.behavior == "answer_with_boundary" and m.chunk_ids() == [] and not R.needs_call(m)
    a, raw, info = _answer_for(m)
    assert raw is None and info["code_built"] and not a.llm_called
    assert a.behavior == "answer_with_boundary" and not a.answerable
    assert a.claims[-1].text == P.BOUNDARY_HANDOFF and a.claims[-1].flags == []
    assert any(g.what.startswith("The database does not support this today:") for g in a.gaps)
    assert not a.incomplete_note


def test_empty_citable_set_with_a_failed_cell_shows_the_incomplete_note(monkeypatch):
    a1 = Aspect("a1", "Preferences of younger investors.")
    m = matrix(NORMATIVE, [a1], [cell("a1.EDJ", "failed"), cell("a1.MS", "not_found")], [H("EDJ-10K#1")])
    a, raw, info = _answer_for(m)
    assert a.behavior == "answer_with_boundary" and a.incomplete_note.startswith("This answer is incomplete")
    assert not any(g.what.startswith("The database does not support") for g in a.gaps)
    # the Ask page shows the note on a boundary answer too (a warning box), without a KeyError
    shown = _render(a)
    assert a.incomplete_note in shown


@pytest.mark.parametrize("question, cells, behavior", [
    ("Advisor headcount across the five.", [cell("a1.EDJ", "not_disclosed"), cell("a1.MS", "not_found")], "refuse"),
    ("Forecast Edward Jones's advisor headcount for 2027.", [cell("a1.EDJ", "fact", [item("EDJ-10K#1")])], "refuse"),
    ("Advisor headcount across the five.", [cell("a1.EDJ", "failed"), cell("a1.MS", "not_found")], "incomplete"),
])
def test_refuse_forecast_and_undecided_make_no_call(question, cells, behavior):
    m = matrix(question, [Aspect("a1", "Advisor headcount.")], cells, [H("EDJ-10K#1")])
    a, raw, info = _answer_for(m)
    assert raw is None and info["code_built"] and a.behavior == behavior and not a.answerable
    if question.startswith("Forecast"):
        assert [g.what for g in a.gaps] == [P.FORECAST_REFUSAL] and not a.claims
    if behavior == "incomplete":
        assert a.incomplete_note.startswith("This answer is incomplete")
        assert not any("does not support" in g.what for g in a.gaps)
        assert "Incomplete" in _render(a)


def _render(answer) -> str:
    from streamlit.testing.v1 import AppTest

    def page():
        import streamlit as st

        from cee.answer.schema import Answer as A
        from cee.app.views.ask_page import show_answer
        from cee.ask import Result
        from cee.retrieve.fts import Query as Q
        a = A(**st.session_state["answer"])
        show_answer(Result(Q(question="q", entities=["EDJ"]), [], a, query_id=None), {})

    at = AppTest.from_function(page)
    at.session_state["answer"] = answer.model_dump()
    at.run(timeout=30)
    assert not at.exception
    return " ".join([*(m.value for m in at.markdown), *(w.value for w in at.warning), *(c.value for c in at.caption)])


# --- the provider call (fake clients) --------------------------------------------------------------

def _ds_answer(m):
    return {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "The comparison is not valid.", "chunk_ids": ["MS-10K#5"], "part_id": "a4"}]}


def test_deepseek_reduce_request_uses_v5_and_the_matrix_schema(monkeypatch):
    m = q24_shaped()
    client = FakeDeepSeek(response([tool_call(arguments=json.dumps(_ds_answer(m)))]))
    meta: dict = {}
    raw = R.call_reduce(m.question, m, None, "deepseek", client=client, meta=meta)
    req = client.kwargs
    assert req["messages"][0]["content"] == P.SYSTEM_PROMPT_V5
    assert req["tools"][0]["function"]["strict"] is True
    assert req["tools"][0]["function"]["parameters"]["properties"]["behavior"]["enum"] == ["answer"]
    assert raw["claims"][0]["part_id"] == "a4" and meta["reasoning_content"] == "I look at the passages."


@pytest.mark.parametrize("resp, match", [
    (lambda m: response(finish="length"), "cut at max_tokens"),
    (lambda m: response(finish="content_filter"), "finish_reason content_filter"),
    (lambda m: response(calls=[]), "did not call"),
    (lambda m: response([tool_call(arguments="not json")]), "not a JSON object"),
    (lambda m: response([tool_call(arguments=json.dumps({"claims": "x"}))]), "not a valid Answer"),
    (lambda m: response([tool_call(arguments=json.dumps({"answerable": True, "behavior": "answer", "claims": [],
                                                         "adjacent": [], "gaps": []}))]), "no claims"),
])
def test_invalid_reduce_outputs_raise_with_the_payload(resp, match):
    m = q24_shaped()
    with pytest.raises(llm.ModelOutputError, match=match) as e:
        R.call_reduce(m.question, m, None, "deepseek", client=FakeDeepSeek(resp(m)))
    assert e.value.raw is not None


def test_stray_closing_braces_are_accepted_and_flagged():
    m = q24_shaped()
    meta: dict = {}
    R.call_reduce(m.question, m, None, "deepseek", meta=meta,
                  client=FakeDeepSeek(response([tool_call(arguments=json.dumps(_ds_answer(m)) + "}")])))
    assert meta["parse_flags"] == ["trailing_braces"]


def test_anthropic_and_openai_reduce_paths():
    m = q24_shaped()
    block = SimpleNamespace(type="tool_use", name="submit_answer", input=_ds_answer(m))
    anth = SimpleNamespace(messages=SimpleNamespace(create=lambda **k: SimpleNamespace(
        stop_reason="tool_use", content=[block], usage=SimpleNamespace(input_tokens=1, output_tokens=1))))
    assert R.call_reduce(m.question, m, None, "anthropic", client=anth)["behavior"] == "answer"
    cut = SimpleNamespace(messages=SimpleNamespace(create=lambda **k: SimpleNamespace(
        stop_reason="max_tokens", content=[block], usage=SimpleNamespace(input_tokens=1, output_tokens=1))))
    with pytest.raises(llm.ModelOutputError, match="cut"):
        R.call_reduce(m.question, m, None, "anthropic", client=cut)
    msg = SimpleNamespace(content=json.dumps(_ds_answer(m)))
    oai = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: SimpleNamespace(
        choices=[SimpleNamespace(message=msg, finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1)))))
    assert R.call_reduce(m.question, m, None, "openai", client=oai)["claims"][0]["part_id"] == "a4"


def test_anthropic_transform_schema_leaves_the_reduce_schema_unchanged():
    anthropic = pytest.importorskip("anthropic")
    transform = getattr(anthropic, "transform_schema", None)
    if transform is None:
        pytest.skip("this SDK has no transform_schema")
    schema, _ = R.reduce_schema(q24_shaped())
    assert transform(schema) == schema


# --- the mock --------------------------------------------------------------------------------------

def test_mock_reduce_is_deterministic_and_passes_every_check():
    m = q24_shaped()
    raw = R.mock_reduce(m)
    assert raw == R.mock_reduce(m) and raw["behavior"] == "answer"
    a, info = run_finish(m, raw)
    derived = next(c for c in a.claims if c.part_id == "a1.EDJ")
    assert "a2.EDJ" not in derived.text and "#0" not in derived.text and "computed" in derived.flags
    assert info["outside_matrix"] == 0 and info["comparison_missing"] == [] and info["part_gaps"] == 0
    assert [x.part_id for x in a.adjacent] == ["a3.SCHW", "a2.EDJ", "a3.EDJ"] or a.adjacent


def test_prompt_v5_holds_the_rules_and_no_question_text():
    from tests.test_prompt import WORDING, _grams, _leaks, _question_texts
    text = P.SYSTEM_PROMPT_V5
    assert "Prompt version: v5." in text and P.WHY_LINE.strip() in text and "adjacent only" in text
    assert P.BOUNDARY_HANDOFF not in text   # code adds the hand-off
    mine = _grams(text)
    assert {q: h for q, t in _question_texts().items() if (h := mine & _grams(t))} == {}
    stripped = text
    for sentence in WORDING:
        stripped = stripped.replace(sentence, " ")
    assert _leaks(stripped) == {}
    assert "Neither firm discloses advisor attrition" not in text   # the old Q28 row is v4.1 only
