"""DeepSeek provider (#242) with fake clients. Never calls a real API (tests/conftest.py)."""
import json
from types import SimpleNamespace

import httpx2
import openai
import pytest

from cee import ask, config
from cee.answer import llm
from cee.answer.schema import Answer, llm_output_schema
from cee.retrieve import planner
from tests.test_validate import hit

REAL_DEEPSEEK_CLIENT = llm.deepseek_client   # captured before conftest's autouse stub

OUTPUT = {"answerable": True, "behavior": "answer",
          "claims": [{"text": "c", "chunk_ids": ["EDJ-10K-2025#1"], "part_id": "p1"}],
          "adjacent": [], "gaps": []}


def tool_call(name=llm.TOOL_NAME, arguments=None):
    args = json.dumps(OUTPUT) if arguments is None else arguments
    return SimpleNamespace(id="call_1", type="function", function=SimpleNamespace(name=name, arguments=args))


def response(calls=None, finish="tool_calls", content=None, reasoning="I look at the passages."):
    calls = [tool_call()] if calls is None else calls
    msg = SimpleNamespace(role="assistant", content=content, reasoning_content=reasoning, tool_calls=calls)
    usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_cache_hit_tokens=60,
                            prompt_cache_miss_tokens=40,
                            completion_tokens_details=SimpleNamespace(reasoning_tokens=20))
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish)], usage=usage)


class FakeDeepSeek:
    def __init__(self, resp=None, error=None):
        self.kwargs, self.calls, self.resp, self.error = None, 0, resp or response(), error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.resp


def status_error(code: int) -> openai.APIStatusError:
    req = httpx2.Request("POST", "http://127.0.0.1:9/chat/completions")
    return openai.APIStatusError(f"error {code}", response=httpx2.Response(code, request=req), body=None)


@pytest.fixture
def thinking(monkeypatch):
    def set_mode(on: bool):
        monkeypatch.setenv("DEEPSEEK_THINKING", "on" if on else "off")
    return set_mode


# --- D1 schema --------------------------------------------------------------------------------

def _strict_problems(node, path="$") -> list[str]:
    out = []
    if isinstance(node, dict):
        for bad in ("minItems", "maxItems", "minLength", "maxLength"):
            if bad in node:
                out.append(f"{path}: {bad}")
        if node.get("type") == "object":
            if node.get("additionalProperties") is not False:
                out.append(f"{path}: additionalProperties")
            if set(node.get("required", [])) != set(node.get("properties", {})):
                out.append(f"{path}: required")
        for k, v in node.items():
            out += _strict_problems(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _strict_problems(v, f"{path}[{i}]")
    return out


def test_both_schemas_meet_deepseek_strict_rules():
    assert _strict_problems(llm_output_schema()) == []
    assert _strict_problems(planner.plan_schema(strict=True)) == []


# --- D2 answer request ------------------------------------------------------------------------

def test_answer_request_thinking_off(thinking):
    thinking(False)
    client = FakeDeepSeek()
    llm._deepseek("q?", [hit()], client=client)
    req = client.kwargs
    fn = req["tools"][0]["function"]
    assert req["tools"][0]["type"] == "function" and fn["name"] == llm.TOOL_NAME and fn["strict"] is True
    assert fn["parameters"] == llm_output_schema()
    assert req["max_tokens"] == 20000 and req["model"] == "deepseek-v4-pro"
    assert req["tool_choice"] == {"type": "function", "function": {"name": llm.TOOL_NAME}}
    assert req["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "MUST" in req["messages"][0]["content"] and "EDJ-10K-2025#1" in req["messages"][1]["content"]
    assert "temperature" not in req


def test_answer_request_thinking_on(thinking):
    thinking(True)
    client = FakeDeepSeek()
    llm._deepseek("q?", [hit()], client=client)
    req = client.kwargs
    assert req["tool_choice"] == "auto" and req["extra_body"] == {"thinking": {"type": "enabled"}}
    assert req["max_tokens"] == 64000 and req["tools"][0]["function"]["strict"] is True


# --- D4 valid output --------------------------------------------------------------------------

def test_valid_tool_call_gives_an_answer_with_usage(thinking):
    thinking(False)
    a = llm._deepseek("q?", [hit()], client=FakeDeepSeek())
    assert a.llm_called and a.claims[0].chunk_ids == ["EDJ-10K-2025#1"] and a.stop_reason == "tool_calls"
    assert a.usage == {"input_tokens": 100, "output_tokens": 50, "cache_hit_tokens": 60, "cache_miss_tokens": 40,
                       "reasoning_tokens": 20, "tool_calls": 1, "thinking": "off"}
    # the reasoning text rides along for the eval record, never in the dump (query_log, UI)
    assert a._provider_payload["reasoning_content"] == "I look at the passages."
    assert "reasoning_content" not in json.dumps(a.model_dump()) and "passages." not in a.model_dump_json()


def test_forced_choice_may_stop_with_stop():
    a = llm._deepseek("q?", [hit()], client=FakeDeepSeek(response(finish="stop")))
    assert a.stop_reason == "stop"


# --- D5 invalid outputs -----------------------------------------------------------------------

@pytest.mark.parametrize("resp, match, raw_check", [
    (response(finish="length"), "cut at max_tokens", lambda r: r["tool_calls"]),
    (response(finish="content_filter"), "finish_reason content_filter", lambda r: r["tool_calls"]),
    (response(finish="insufficient_system_resource"), "insufficient_system_resource", lambda r: True),
    (response(calls=[], finish="stop", content="Here is the answer"), "did not call",
     lambda r: r["content"] == "Here is the answer" and r["reasoning_content"]),
    (response(calls=[tool_call(arguments="{not json")]), "not a JSON object", lambda r: r == "{not json"),
    (response(calls=[tool_call(arguments="[1, 2]")]), "not a JSON object", lambda r: r == "[1, 2]"),
    (response(calls=[tool_call(arguments=json.dumps({**OUTPUT, "behavior": "maybe"}))]), "not a valid Answer",
     lambda r: r["behavior"] == "maybe"),
    (response(calls=[tool_call(arguments=json.dumps({**OUTPUT, "claims": []}))]), "no claims",
     lambda r: r["claims"] == []),
])
def test_invalid_outputs_raise_with_raw(resp, match, raw_check):
    with pytest.raises(llm.ModelOutputError, match=match) as e:
        llm._deepseek("q?", [hit()], client=FakeDeepSeek(resp))
    assert e.value.provider == "deepseek" and raw_check(e.value.raw)
    assert e.value.usage["output_tokens"] == 50
    json.dumps(e.value.raw)   # JSON-safe, so the eval can save it


def test_another_tool_name_is_no_answer():
    with pytest.raises(llm.ModelOutputError, match="did not call"):
        llm._deepseek("q?", [hit()], client=FakeDeepSeek(response(calls=[tool_call(name="other")])))


# --- D6 errors --------------------------------------------------------------------------------

@pytest.mark.parametrize("code, words", [(402, "insufficient balance"), (429, "rate limit"), (401, "key")])
def test_provider_refusals_stop_with_a_plain_message(code, words):
    with pytest.raises(llm.ProviderStop, match=words):
        llm._deepseek("q?", [hit()], client=FakeDeepSeek(error=status_error(code)))


def test_other_api_errors_propagate_unchanged():
    with pytest.raises(openai.APIStatusError):
        llm._deepseek("q?", [hit()], client=FakeDeepSeek(error=status_error(500)))


# --- D9 versions and names --------------------------------------------------------------------

def test_request_version_and_model_names(thinking):
    assert llm.request_version("anthropic") == "strict-1" and llm.request_version("openai") is None
    thinking(False)
    off = llm.request_version("deepseek")
    thinking(True)
    on = llm.request_version("deepseek")
    assert (off, on) == ("ds-strict-1-think-off-a20000-p8000", "ds-strict-1-think-on-a64000-p64000")
    assert llm.answer_max_tokens("deepseek") == 64000 and llm.answer_max_tokens("anthropic") == llm.MAX_TOKENS
    assert ask.model_name("deepseek") == planner.model_for("deepseek") == "deepseek-v4-pro"


# --- D10 settings -----------------------------------------------------------------------------

def test_deepseek_settings(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    s = config.settings()
    assert s.deepseek_model == "deepseek-v4-pro" and s.deepseek_base_url == "https://api.deepseek.com/beta"
    assert s.deepseek_thinking is config.DEEPSEEK_THINKING_DEFAULT is True   # chosen by the #242 real check
    for raw, want in (("on", True), ("TRUE", True), ("off", False), ("0", False), ("", config.DEEPSEEK_THINKING_DEFAULT)):
        monkeypatch.setenv("DEEPSEEK_THINKING", raw)
        assert config.settings().deepseek_thinking is want
    monkeypatch.setenv("DEEPSEEK_THINKING", "maybe")
    with pytest.raises(ValueError, match="DEEPSEEK_THINKING"):
        config.settings()


# --- D11 client -------------------------------------------------------------------------------

def test_real_client_settings(monkeypatch):
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        REAL_DEEPSEEK_CLIENT()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    c = REAL_DEEPSEEK_CLIENT()
    assert c.max_retries == 0 and c.timeout.read == 3600 and c.timeout.connect == 30
    assert str(c.base_url) == "https://api.deepseek.com/beta/" and c.api_key == "dummy"


# --- D13 several tool calls -------------------------------------------------------------------

def test_first_answer_tool_call_wins():
    second = tool_call(arguments=json.dumps({**OUTPUT, "claims": [{"text": "second", "chunk_ids": ["x"],
                                                                   "part_id": ""}]}))
    a = llm._deepseek("q?", [hit()], client=FakeDeepSeek(response(calls=[tool_call(), second])))
    assert a.claims[0].text == "c" and a.usage["tool_calls"] == 2


def test_generate_routes_to_deepseek(monkeypatch):
    monkeypatch.setattr(llm, "deepseek_client", lambda: FakeDeepSeek())
    a = llm.generate("q?", [hit()], provider="deepseek")
    assert isinstance(a, Answer) and a.llm_called
