"""Map step (#246): extraction schema, requests, invalid outputs, code checks, mock, parallel
calls, failed calls, corrective re-search. Fake clients and a fake search; 0 real calls."""
import json
import threading
import time
from types import SimpleNamespace

import anthropic
import pytest

from cee.answer import extract, llm
from cee.answer.extract import CallResult, MapSpec
from cee.retrieve import planner
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Aspect, Plan, SubQuestion
from tests.test_llm_deepseek import FakeDeepSeek, _strict_problems, response, status_error, tool_call


def hit(cid, entity="EDJ", part=None, text=None, rank=1.0):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-03-13", period_end="2025-12-31", section="Item 7", page=None,
               rank=rank, text=text or f"Financial advisors at year end 20,425 in {cid}.", part_id=part)


A1 = Aspect("a1", "Advisor headcount as reported.", metric="advisor_headcount")
A2 = Aspect("a2", "How the firm defines advisor headcount.")
Q = Query(question="How does each firm define and report advisor headcount?", entities=["EDJ", "MS"])


def plan_for(aspects=(A1, A2), firms=("EDJ", "MS")):
    subs = [SubQuestion(f"{a.id}.{f}", f, a, "named") for f in firms for a in aspects]
    return Plan(aspects=list(aspects), subquestions=subs)


def spec_edj(plan=None, hits=None):
    plan = plan or plan_for()
    hits = hits if hits is not None else [hit("EDJ-10K-2025#130", part="a1.EDJ"), hit("EDJ-10K-2025#131", part="a2.EDJ")]
    specs, code = extract.map_specs(Q, plan, hits)
    return next(s for s in specs if s.id == "map.EDJ"), specs, code


def cell_out(sid, label="fact", chunk_ids=("EDJ-10K-2025#130",), value="20,425", quote="Financial advisors at year end 20,425"):
    items = [{"text": "t", "quote": quote, "chunk_ids": list(chunk_ids), "value": value, "unit": "advisors",
              "period": "2025-12-31", "scope": "", "definition": ""}] if label in ("fact", "different_quantity") else []
    return {"subquestion_id": sid, "label": label, "items": items, "differs_because": "", "reason": "r",
            "derivation": {"operation": "", "inputs": []}}


OUT = {"cells": [cell_out("a1.EDJ"), cell_out("a2.EDJ", "not_disclosed")]}


# --- specs ------------------------------------------------------------------------------------

def test_one_call_per_firm_with_passages_research_call_and_code_cells():
    plan = plan_for()
    hits = [hit("EDJ#1", part="a1.EDJ"), hit("R#1", entity=None, part="research")]
    specs, code = extract.map_specs(Q, plan, hits)
    assert [s.id for s in specs] == ["map.EDJ", "map.research"]
    assert specs[1].cell_ids == ["a1.research", "a2.research"] and specs[1].research
    assert [(c.id, c.label, c.source) for c in code] == [("a1.MS", "not_found", "code"), ("a2.MS", "not_found", "code")]


def test_allowed_set_is_own_passages_plus_pooled_sibling_chunks():
    plan = plan_for()
    plan.pools = {"a2.EDJ": {"EDJ-10K-2025#130", "EDJ-NEVER-SEEN#9"}}
    spec, _, _ = spec_edj(plan)
    assert spec.allowed["a1.EDJ"] == {"EDJ-10K-2025#130"}
    assert spec.allowed["a2.EDJ"] == {"EDJ-10K-2025#131", "EDJ-10K-2025#130"}   # pooled + in the input


# --- schema and requests ----------------------------------------------------------------------

def test_schemas_meet_strict_rules_on_every_provider():
    spec, specs, _ = spec_edj()
    assert _strict_problems(extract.extraction_schema(spec, strict=True)) == []
    loose = extract.extraction_schema(spec)
    assert loose["properties"]["cells"]["minItems"] == 1
    assert anthropic.transform_schema(loose) == loose
    enum = loose["properties"]["cells"]["items"]["properties"]["subquestion_id"]["enum"]
    assert enum == ["a1.EDJ", "a2.EDJ"]


def test_plan_v31_schema_has_required_boolean_proxy():
    for schema in (planner.plan_schema(), planner.plan_schema(strict=True)):
        aspect = schema["properties"]["aspects"]["items"]
        assert aspect["properties"]["proxy"] == {"type": "boolean"} and "proxy" in aspect["required"]
    assert _strict_problems(planner.plan_schema(strict=True)) == []
    assert planner.PLANNER_VERSION == "plan-v3.1"


def test_one_proxy_text_in_both_prompts():
    assert extract.PROXY_RULE in extract.system_prompt() and extract.PROXY_RULE in extract.system_prompt(True)
    assert extract.system_prompt().count(extract.PROXY_RULE) == 1


def test_message_marks_proxy_and_lists_passages_per_sub_question():
    a = Aspect("a3", "Advisor headcount, as the closest denominator.", proxy=True)
    plan = plan_for((a,), ("EDJ",))
    spec, _, _ = spec_edj(plan, [hit("EDJ#1", part="a3.EDJ")])
    msg = extract.extract_message(Q.question, spec)
    assert "- a3.EDJ [fact, proxy]: Advisor headcount" in msg and '<chunk id="EDJ#1"' in msg
    assert "Firm: Edward Jones" in msg


def test_deepseek_request_and_output(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_THINKING", "on")
    spec, _, _ = spec_edj()
    client = FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, json.dumps(OUT))]))
    meta = {}
    raw = extract.call_extract(Q.question, spec, "deepseek", client=client, meta=meta)
    fn = client.kwargs["tools"][0]["function"]
    assert fn["name"] == extract.EXTRACT_TOOL and fn["strict"] is True
    assert fn["parameters"] == extract.extraction_schema(spec, strict=True)
    assert client.kwargs["max_tokens"] == 64000 and client.kwargs["tool_choice"] == "auto"
    assert raw == OUT and meta["reasoning_content"] == "I look at the passages."


class FakeAnthropic:
    def __init__(self, blocks, stop="tool_use"):
        self.kwargs = None
        self.messages = SimpleNamespace(create=self._create)
        self.resp = SimpleNamespace(content=blocks, stop_reason=stop,
                                    usage=SimpleNamespace(input_tokens=10, output_tokens=5))

    def _create(self, **kw):
        self.kwargs = kw
        return self.resp


def tool_use(inp):
    return SimpleNamespace(type="tool_use", name=extract.EXTRACT_TOOL, input=inp)


def test_anthropic_and_openai_requests_are_strict():
    spec, _, _ = spec_edj()
    a = FakeAnthropic([tool_use(OUT)])
    assert extract.call_extract(Q.question, spec, "anthropic", client=a) == OUT
    tool = a.kwargs["tools"][0]
    assert tool["strict"] is True and tool["input_schema"] == extract.extraction_schema(spec)
    req = extract.openai_extract_request(Q.question, spec)
    assert req["response_format"]["json_schema"]["strict"] is True


# --- invalid outputs: saved by the caller, never re-rolled ----------------------------------------

@pytest.mark.parametrize("client, provider, why", [
    (lambda: FakeAnthropic([SimpleNamespace(type="text", text="no tool")]), "anthropic", "did not call"),
    (lambda: FakeAnthropic([tool_use(OUT)], stop="max_tokens"), "anthropic", "cut at max_tokens"),
    (lambda: FakeAnthropic([tool_use(OUT)], stop="refusal"), "anthropic", "refusal"),
    (lambda: FakeAnthropic([tool_use({"cells": []})]), "anthropic", "no cells"),
    (lambda: FakeAnthropic([tool_use({"cells": [{"subquestion_id": "a1.EDJ", "label": "maybe"}]})]), "anthropic",
     "not a valid extraction"),
    (lambda: FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, json.dumps(OUT))], finish="length")),
     "deepseek", "cut at max_tokens"),
    (lambda: FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, json.dumps(OUT))], finish="content_filter")),
     "deepseek", "finish_reason content_filter"),
    (lambda: FakeDeepSeek(response([])), "deepseek", "did not call"),
    (lambda: FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, "{not json")])), "deepseek", "not a JSON object"),
])
def test_invalid_outputs_raise_model_output_error_with_payload(client, provider, why):
    spec, _, _ = spec_edj()
    with pytest.raises(llm.ModelOutputError) as e:
        extract.call_extract(Q.question, spec, provider, client=client())
    assert why in str(e.value)


def test_invalid_output_cells_are_failed_and_not_researched():
    plan = plan_for()
    hits = [hit("EDJ-10K-2025#130", part="a1.EDJ"), hit("MS#1", entity="MS", part="a1.MS")]
    searched = []

    def call(spec, *a):
        return CallResult(invalid=True, error="Model output cut") if spec.entity == "EDJ" else \
            CallResult(raw={"cells": [cell_out("a1.MS", "not_found"), cell_out("a2.MS", "not_found")]})

    m = extract.run_map(Q, plan, hits, "anthropic", call=call, search_fn=lambda *a, **k: searched.append(a) or [],
                        sources=lambda e: "")
    assert m.cells["a1.EDJ"].label == "failed" and m.cells["a2.EDJ"].label == "failed"
    assert {r["id"] for r in m.research} == {"a1.MS", "a2.MS"}   # only the not_found cells, never failed ones


# --- code checks on a valid output ----------------------------------------------------------------

def test_chunk_ids_outside_the_retrieved_set_are_rejected_and_flagged():
    spec, _, _ = spec_edj()
    by_id = {h.chunk_id: h for h in spec.hits}
    raw = {"cells": [cell_out("a1.EDJ", chunk_ids=("EDJ-10K-2025#130", "MS#1", "INVENTED#7")),
                     cell_out("a2.EDJ", chunk_ids=("EDJ-10K-2025#130",))]}   # sibling chunk, not in a2's pool
    cells = extract.parse_output(raw, spec, by_id)
    it = cells[0].items[0]
    assert it.chunk_ids == ["EDJ-10K-2025#130"] and it.rejected_ids == ["MS#1", "INVENTED#7"]
    assert "unmatched_citation" in it.flags and cells[0].effective_label == "fact"
    assert cells[1].items[0].chunk_ids == [] and cells[1].effective_label == "not_found"


def test_quote_number_period_checks_and_missing_cell():
    spec, _, _ = spec_edj()
    by_id = {h.chunk_id: h for h in spec.hits}
    bad = cell_out("a1.EDJ", value="21,000", quote="a sentence that is not there")
    bad["items"][0]["period"] = "end of 2025"
    cells = extract.parse_output({"cells": [bad]}, spec, by_id)
    flags = cells[0].items[0].flags
    assert {"quote_not_found", "number_not_found", "period_unparsed"} <= set(flags)
    assert cells[1].label == "not_found" and "missing_cell" in cells[1].flags


def test_mock_extract_is_deterministic_and_verbatim():
    spec, _, _ = spec_edj()
    a, b = extract.mock_extract(spec), extract.mock_extract(spec)
    assert a == b
    cells = extract.parse_output(a, spec, {h.chunk_id: h for h in spec.hits}, "mock")
    assert [c.effective_label for c in cells] == ["fact", "fact"] and not cells[0].items[0].flags


# --- parallel calls, ProviderStop, failed calls ---------------------------------------------------

def five_firm_setup():
    firms = ("MS", "SCHW", "EDJ", "MER", "RJF")
    plan = plan_for((A1,), firms)
    hits = [hit(f"{f}#1", entity=f, part=f"a1.{f}") for f in firms]
    return Query(question=Q.question, entities=list(firms)), plan, hits


def test_parallel_calls_respect_concurrency_and_keep_spec_order(monkeypatch):
    q, plan, hits = five_firm_setup()
    live, peak, lock = [0], [0], threading.Lock()

    def call(spec, *a):
        with lock:
            live[0] += 1
            peak[0] = max(peak[0], live[0])
        order = ["map.MS", "map.SCHW", "map.EDJ", "map.MER", "map.RJF"]
        time.sleep(0.02 * (5 - order.index(spec.id)))   # finish in reverse order
        with lock:
            live[0] -= 1
        return CallResult(raw=extract.mock_extract(spec))

    par = extract.run_map(q, plan, hits, "anthropic", call=call, concurrency=2, sources=lambda e: "")
    seq = extract.run_map(q, plan, hits, "anthropic", call=call, concurrency=1, sources=lambda e: "")
    assert peak[0] <= 2
    assert [c["id"] for c in par.calls] == ["map.MS", "map.SCHW", "map.EDJ", "map.MER", "map.RJF"]
    assert par.to_log()["cells"] == seq.to_log()["cells"] and par.behavior == "answer"


def test_provider_stop_stops_the_question_and_cancels_the_rest():
    q, plan, hits = five_firm_setup()
    started = []

    def call(spec, *a):
        started.append(spec.id)
        if spec.id == "map.MS":
            raise llm.ProviderStop("DeepSeek: rate limit reached (429)")
        time.sleep(0.2)
        return CallResult(raw=extract.mock_extract(spec))

    with pytest.raises(llm.ProviderStop):
        extract.run_map(q, plan, hits, "anthropic", call=call, concurrency=1, sources=lambda e: "")
    assert started == ["map.MS"]


def test_failed_call_marks_only_its_cells_and_the_round_goes_on(monkeypatch):
    q, plan, hits = five_firm_setup()
    errors = {"map.MS": TimeoutError("read timed out"), "map.SCHW": status_error(500),
              "map.EDJ": status_error(429)}

    def fake_call_extract(question, spec, provider, window=None, firms=None, client=None, meta=None):
        if spec.id in errors:
            raise errors[spec.id]
        return extract.mock_extract(spec)

    monkeypatch.setattr(extract, "call_extract", fake_call_extract)
    m = extract.run_map(q, plan, hits, "openai", sources=lambda e: "")
    assert [m.cells[f"a1.{f}"].label for f in ("MS", "SCHW", "EDJ")] == ["failed"] * 3
    assert m.cells["a1.MER"].label == "fact" and m.cells["a1.RJF"].label == "fact"
    assert m.cells["a1.MS"].error.startswith("TimeoutError") and m.behavior == "answer"
    logged = {c["id"]: c for c in m.calls}
    assert logged["map.SCHW"]["failed_call"] and not logged["map.MER"]["failed_call"]


def test_over_the_cap_is_skipped_without_a_call():
    q, plan, hits = five_firm_setup()
    calls = []
    allowed = iter([True, True, True, False, False])
    m = extract.run_map(q, plan, hits, "anthropic",
                        call=lambda spec, *a: calls.append(spec.id) or CallResult(raw=extract.mock_extract(spec)),
                        allow=lambda spec: next(allowed), sources=lambda e: "")
    assert sorted(calls) == ["map.EDJ", "map.MS", "map.SCHW"]
    assert m.cells["a1.MER"].label == "failed" and "--max-calls" in m.cells["a1.MER"].error


# --- corrective re-search (CRAG) --------------------------------------------------------------------

def test_research_runs_once_per_not_found_with_the_exclude_set_then_one_reextraction():
    plan = plan_for((A1, A2, Aspect("a3", "Whether the counts compare.", kind="comparison")), ("EDJ", "MS"))
    hits = [hit("EDJ-10K-2025#130", part="a1.EDJ"), hit("MS#1", entity="MS", part="a1.MS")]
    searches, calls = [], []

    def search_fn(sq_q, tokens=None, exclude=None, research=False, peers=False, text=None):
        searches.append((sq_q.entities, sq_q.terms, set(exclude)))
        return [hit(f"NEW-{sq_q.entities[0]}#{len(searches)}", entity=sq_q.entities[0])] \
            if sq_q.entities == ["MS"] else []

    def call(spec, *a):
        calls.append((spec.id, spec.cell_ids, [h.chunk_id for h in spec.hits]))
        out = {"cells": [cell_out(c, "not_found") for c in spec.cell_ids]}
        if spec.id == "map.EDJ":
            out["cells"][0] = cell_out("a1.EDJ")
        return CallResult(raw=out)

    m = extract.run_map(Q, plan, hits, "anthropic", call=call, search_fn=search_fn, sources=lambda e: "")
    researched = [r["id"] for r in m.research]
    assert researched == ["a2.EDJ", "a1.MS", "a2.MS"]             # not a1.EDJ (fact), never a3 (comparison)
    assert all(ex >= {"EDJ-10K-2025#130", "MS#1"} for _, _, ex in searches)
    assert "NEW-MS#2" in searches[2][2]                            # earlier re-search hits excluded too
    ms =next(r for r in m.research if r["id"] == "a1.MS")
    assert "Wealth Management representatives" in ms["words"]       # the definition quote
    assert calls[-1][0] == "remap.MS" and calls[-1][1] == ["a1.MS", "a2.MS"]
    assert calls[-1][2] == ["NEW-MS#2", "NEW-MS#3"]
    assert sum(c[0].startswith("remap") for c in calls) == 1        # one per firm, only with new hits
    assert m.cells["a1.MS"].source == "reextract" and m.cells["a1.MS"].first["label"] == "not_found"
    assert len(m.research) == 3                                     # a re-extracted not_found is final


def test_widen_words_adds_definition_phrases_and_adjacent_quarters():
    import datetime as dt
    sq = SubQuestion("a1.SCHW", "SCHW", Aspect("a1", "Advisor headcount over eight quarters.",
                                                metric="advisor_headcount", kind="series"), "named")
    words = extract.widen_words(Query(question="q", entities=["SCHW"]), sq, dt.date(2026, 11, 17))
    assert "financial consultants" in words and "wealth consultants" in words
    assert "third quarter 2026 3Q26" in words and "fourth quarter 2025 4Q25" in words
    win = Query(question="q", entities=["RJF"], window=(dt.date(2026, 8, 19), dt.date(2026, 11, 17)))
    sq2 = SubQuestion("a1.RJF", "RJF", Aspect("a1", "What is new.", kind="recency"), "named")
    assert extract.widen_words(win, sq2) == "second quarter 2026 2Q26 fourth quarter 2026 4Q26"


# --- #246 TL decision (Q24): stray closing braces after a complete JSON object -------------------

def test_loads_object_accepts_stray_closing_braces_and_flags_them():
    flags = []
    assert llm.loads_object('{"cells": [1]}}', flags) == {"cells": [1]} and flags == ["trailing_braces"]
    flags = []
    assert llm.loads_object('{"a": 1}\n ]} ', flags) == {"a": 1} and flags == ["trailing_braces"]


@pytest.mark.parametrize("text", ['{"a": 1} extra', '{"a": 1}{"b": 2}', '{"a": 1},', '[1, 2]', 'not json', '{"a": '])
def test_loads_object_rejects_other_trailing_text_and_non_objects(text):
    with pytest.raises(ValueError):
        llm.loads_object(text, [])


def test_loads_object_unchanged_without_trailing_text():
    flags = []
    assert llm.loads_object('  {"a": [1, {"b": "}"}]}  ', flags) == {"a": [1, {"b": "}"}]} and flags == []


def test_map_output_with_stray_brace_is_accepted_flagged_and_still_checked():
    spec, _, _ = spec_edj()
    bad_id = {"cells": [cell_out("a1.EDJ", chunk_ids=("INVENTED#1",)), cell_out("a2.EDJ", "not_disclosed")]}
    client = FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, json.dumps(bad_id) + "}")]))
    meta = {}
    raw = extract.call_extract(Q.question, spec, "deepseek", client=client, meta=meta)
    assert meta["parse_flags"] == ["trailing_braces"]
    cells = extract.parse_output(raw, spec, {h.chunk_id: h for h in spec.hits})
    assert cells[0].items[0].rejected_ids == ["INVENTED#1"] and cells[0].effective_label == "not_found"
    junk = FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, json.dumps(OUT) + " trailing words")]))
    with pytest.raises(llm.ModelOutputError, match="not a JSON object"):
        extract.call_extract(Q.question, spec, "deepseek", client=junk)
    schema_bad = FakeDeepSeek(response([tool_call(extract.EXTRACT_TOOL, '{"cells": []}}')]))
    with pytest.raises(llm.ModelOutputError, match="no cells"):
        extract.call_extract(Q.question, spec, "deepseek", client=schema_bad)


def test_saved_invalid_record_is_rechecked_at_zero_calls():
    good = {"invalid": True, "error": "Map arguments are not a JSON object: Extra data: line 1 column 9",
            "raw_payload": json.dumps(OUT) + "}"}
    r = extract.recheck_invalid(good, "deepseek")
    assert r.raw == OUT and r.flags == ["trailing_braces", "rechecked"] and r.cached
    assert extract.recheck_invalid({**good, "raw_payload": json.dumps(OUT) + " x"}, "deepseek") is None
    assert extract.recheck_invalid({**good, "error": "Map output cut at max_tokens"}, "deepseek") is None
    assert extract.recheck_invalid({**good, "failed_call": True}, "deepseek") is None


def test_answer_and_planner_paths_use_the_same_rule(monkeypatch):
    from tests.test_llm_deepseek import OUTPUT
    from tests.test_validate import hit as vhit
    a = llm._deepseek("q?", [vhit()], client=FakeDeepSeek(response([tool_call(llm.TOOL_NAME, json.dumps(OUTPUT) + "}")])))
    assert a.usage["parse_flags"] == ["trailing_braces"]
    with pytest.raises(llm.ModelOutputError):
        llm._deepseek("q?", [vhit()], client=FakeDeepSeek(response([tool_call(llm.TOOL_NAME, json.dumps(OUTPUT) + "x")])))
    plan = {"aspects": [{"id": "a", "text": "t", "keyword_query": "w", "firms": [], "metric": "", "kind": "fact",
                         "proxy": False}]}
    meta = {}
    out = planner.call_planner(Q, "deepseek", FakeDeepSeek(response([tool_call(planner.PLAN_TOOL, json.dumps(plan) + "}}")])), meta)
    assert out == plan and meta["parse_flags"] == ["trailing_braces"]