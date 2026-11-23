"""#272: DeepSeek effort per stage, caps, model per stage, streaming and the stage request versions.
Fake clients only; never a real call (tests/conftest.py)."""
import json
from types import SimpleNamespace as NS

import pytest

from cee import config
from cee.answer import llm
from tests.test_llm_deepseek import FakeDeepSeek, response, tool_call


def _req(stage):
    return llm.deepseek_tool_request("t", "d", {"type": "object"}, "sys", "user", 999, stage=stage)


@pytest.mark.parametrize("effort", ["off", "low", "high", "max"])
@pytest.mark.parametrize("stage, var", [("plan", "DEEPSEEK_EFFORT_PLAN"), ("map", "DEEPSEEK_EFFORT_MAP"),
                                        ("reduce", "DEEPSEEK_EFFORT_REDUCE")])
def test_each_stage_sends_its_own_effort_and_cap(monkeypatch, stage, var, effort):
    monkeypatch.setenv(var, effort)
    req = _req(stage)
    body = req["extra_body"]
    if effort == "off":
        assert body == {"thinking": {"type": "disabled"}}
        assert req["tool_choice"] == {"type": "function", "function": {"name": "t"}}
        # #275: a streamed off reduce gets 64000 (it writes the whole answer); the other off caps are unchanged
        assert req["max_tokens"] == (64000 if stage == "reduce" else llm.DEEPSEEK_OFF_CAPS[stage])
    else:
        assert body == {"thinking": {"type": "enabled"}, "reasoning_effort": effort}
        assert req["tool_choice"] == "auto" and req["max_tokens"] == 128000
    assert req["stream"] is True and req["stream_options"] == {"include_usage": True}


def test_stages_are_independent(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_PLAN", "off")
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "low")
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE", "max")
    assert _req("plan")["extra_body"]["thinking"]["type"] == "disabled"
    assert _req("map")["extra_body"]["reasoning_effort"] == "low"
    assert _req("reduce")["extra_body"]["reasoning_effort"] == "max"


def test_legacy_request_without_stage_is_unchanged(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_THINKING", "on")
    req = llm.deepseek_tool_request("t", "d", {}, "s", "u", 64000)
    assert req["extra_body"] == {"thinking": {"type": "enabled"}} and "stream" not in req
    assert req["max_tokens"] == 64000 and llm.request_version("deepseek") == "ds-strict-1-think-on-a64000-p64000"


def test_map_model_only_for_the_map(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL_MAP", "deepseek-flash")
    assert _req("map")["model"] == "deepseek-flash"
    assert _req("plan")["model"] == _req("reduce")["model"] == "deepseek-v4-pro"


def test_stream_modes(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_PLAN", "off")
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "low")
    monkeypatch.setenv("DEEPSEEK_STREAM", "nothink")
    assert _req("plan").get("stream") is True and "stream" not in _req("map")
    monkeypatch.setenv("DEEPSEEK_STREAM", "off")
    assert "stream" not in _req("plan") and "stream" not in _req("map")


def test_bad_settings_stop_with_a_clear_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "medium")
    with pytest.raises(ValueError, match="DEEPSEEK_EFFORT_MAP"):
        config.settings()
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "low")
    monkeypatch.setenv("DEEPSEEK_STREAM", "yes")
    with pytest.raises(ValueError, match="DEEPSEEK_STREAM"):
        config.settings()


def test_request_version_names_only_its_own_stage(monkeypatch):
    for v in ("DEEPSEEK_EFFORT_PLAN", "DEEPSEEK_EFFORT_MAP", "DEEPSEEK_EFFORT_REDUCE", "DEEPSEEK_STREAM"):
        monkeypatch.delenv(v, raising=False)
    base = {s: llm.request_version("deepseek", s) for s in llm.DEEPSEEK_STAGES}
    # the #272 defaults: plan off, map low, reduce low; #283: the map names its shared-prefix ceiling
    assert base["map"] == "ds-strict-2-map-low-c128000-s1-pf150000"
    assert base["plan"] == "ds-strict-2-plan-off-c8000-s1" and base["reduce"] == "ds-strict-2-reduce-low-c128000-s1"
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "max")
    assert llm.request_version("deepseek", "map") == "ds-strict-2-map-max-c128000-s1-pf150000"
    assert llm.request_version("deepseek", "plan") == base["plan"]
    assert llm.request_version("deepseek", "reduce") == base["reduce"]
    monkeypatch.setenv("DEEPSEEK_EFFORT_PLAN", "high")
    assert llm.request_version("deepseek", "plan") == "ds-strict-2-plan-high-c128000-s1"
    monkeypatch.setenv("DEEPSEEK_EFFORT_PLAN", "off")
    monkeypatch.setenv("DEEPSEEK_STREAM", "nothink")
    assert llm.request_version("deepseek", "map").endswith("-s0-pf150000")
    assert llm.request_version("deepseek", "plan").endswith("-s1")


def test_stage_versions_join_every_cache_key(monkeypatch, tmp_path):
    from scripts import eval_run as er
    runner = er.RealRunner("deepseek", 0, "snap", tmp_path / "run", cache_dir=tmp_path / "c")
    first = (runner.plan_version, runner.map_version, runner.reduce_version, runner.map_model)
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE", "high")
    monkeypatch.setenv("DEEPSEEK_MODEL_MAP", "deepseek-flash")
    again = er.RealRunner("deepseek", 0, "snap", tmp_path / "run", cache_dir=tmp_path / "c")
    assert again.plan_version == first[0] and again.map_version == first[1]
    assert again.reduce_version != first[2] and again.map_model == "deepseek-flash" != first[3]


# --- streaming --------------------------------------------------------------------------------

def chunk(content=None, reasoning=None, calls=None, finish=None, usage=None, choices=True):
    delta = NS(content=content, reasoning_content=reasoning, tool_calls=calls)
    return NS(choices=[NS(delta=delta, finish_reason=finish)] if choices else [], usage=usage)


def tc(index, args, name=None, id_=None):
    return NS(index=index, id=id_, function=NS(name=name, arguments=args))


USAGE = NS(prompt_tokens=100, completion_tokens=50, prompt_cache_hit_tokens=60, prompt_cache_miss_tokens=40,
           completion_tokens_details=NS(reasoning_tokens=20))


class FakeStream(FakeDeepSeek):
    def __init__(self, chunks):
        super().__init__()
        self.chunks = chunks

    def _create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return iter(self.chunks)


def test_a_stream_is_assembled_into_the_usual_response():
    args = json.dumps({"a": 1})
    chunks = [chunk(reasoning="I th"), chunk(reasoning="ink."),
              chunk(calls=[tc(0, args[:4], name="submit_answer", id_="c1")]), chunk(calls=[tc(0, args[4:])]),
              chunk(finish="tool_calls"), chunk(usage=USAGE, choices=False)]
    req = {**_req("map"), "model": "m"}
    resp = llm.deepseek_create(FakeStream(chunks), req)
    call, stop, usage, payload = llm.deepseek_tool_call(resp, "submit_answer", req)
    assert call.function.arguments == args and stop == "tool_calls"
    assert payload["reasoning_content"] == "I think." and payload["content"] is None
    assert usage["output_tokens"] == 50 and usage["reasoning_tokens"] == 20 and usage["streamed"] is True
    assert usage["ttft_s"] is not None and usage["ttft_s"] >= 0
    assert usage["thinking"] == "on" and usage["effort"] == "low" and usage["model"] == "m"


def test_a_cut_stream_keeps_finish_reason_length():
    chunks = [chunk(calls=[tc(0, '{"a": ', name="t")]), chunk(finish="length"), chunk(usage=USAGE, choices=False)]
    resp = llm.assemble_stream(chunks)
    call, stop, usage, _ = llm.deepseek_tool_call(resp, "t")
    assert stop == "length" and call.function.arguments == '{"a": '


def test_a_stream_without_usage_or_text():
    resp = llm.assemble_stream([chunk(finish="stop")])
    call, stop, usage, _ = llm.deepseek_tool_call(resp, "t")
    assert call is None and stop == "stop" and usage["output_tokens"] is None and usage["ttft_s"] is None


def test_two_tool_calls_are_kept_apart_by_index():
    resp = llm.assemble_stream([chunk(calls=[tc(0, "{}", name="a"), tc(1, '{"x"', name="b")]),
                                chunk(calls=[tc(1, ": 1}")]), chunk(finish="tool_calls")])
    calls = resp.choices[0].message.tool_calls
    assert [(c.function.name, c.function.arguments) for c in calls] == [("a", "{}"), ("b", '{"x": 1}')]


def test_a_whole_response_to_a_streamed_request_is_used_as_is():
    resp = llm.deepseek_create(FakeDeepSeek(response([tool_call()])), _req("reduce"))
    call, stop, _, _ = llm.deepseek_tool_call(resp, llm.TOOL_NAME)
    assert call is not None and stop == "tool_calls"


def test_streaming_read_timeout_is_per_chunk(monkeypatch):
    """#272 review note 6: a 128000-token output at 18 tokens/s is about 7100 s, above the 3600 s timeout;
    the SDK's read timeout applies to each read, and a stream sends chunks throughout, so it is not hit."""
    import openai
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    from tests.test_llm_deepseek import REAL_DEEPSEEK_CLIENT
    c = REAL_DEEPSEEK_CLIENT()
    assert isinstance(c.timeout, openai.Timeout) and c.timeout.read == llm.DEEPSEEK_TIMEOUT_S == 3600
    assert llm.DEEPSEEK_THINKING_CAP / 18 > llm.DEEPSEEK_TIMEOUT_S   # why only a per-read timeout is safe
