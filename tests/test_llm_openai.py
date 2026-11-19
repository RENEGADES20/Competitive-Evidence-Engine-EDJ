"""Request building for the paid providers, with fake clients. Never calls a real API."""
import json
from types import SimpleNamespace

import pytest

from cee.answer import llm
from tests.test_validate import hit

# The real client builders, captured before conftest's autouse fixture replaces them (#230 test).
REAL_ANTHROPIC_CLIENT, REAL_OPENAI_CLIENT = llm.anthropic_client, llm.openai_client

OUTPUT = {"answerable": True, "behavior": "answer",
          "claims": [{"text": "c", "chunk_ids": ["EDJ-10K-2025#1"]}], "adjacent": [], "gaps": []}


class FakeOpenAI:
    def __init__(self):
        self.kwargs = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        msg = SimpleNamespace(content=json.dumps(OUTPUT))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class FakeAnthropic:
    def __init__(self):
        self.kwargs = None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name=llm.TOOL_NAME, input=OUTPUT)])


def test_openai_request_uses_strict_structured_outputs():
    client = FakeOpenAI()
    a = llm._openai("q?", [hit()], client=client)
    rf = client.kwargs["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert "EDJ-10K-2025#1" in client.kwargs["messages"][1]["content"]
    assert a.llm_called and a.claims[0].chunk_ids == ["EDJ-10K-2025#1"]


def test_anthropic_request_offers_the_answer_tool():
    client = FakeAnthropic()
    a = llm._anthropic("q?", [hit()], client=client)
    assert client.kwargs["tools"][0]["name"] == llm.TOOL_NAME
    assert "MUST" in client.kwargs["system"]
    assert client.kwargs["tools"][0]["input_schema"]["required"][0] == "answerable"
    assert a.llm_called


def test_mock_is_offline_and_cites_hits():
    a = llm.generate("q?", [hit()], provider="mock")
    assert not a.llm_called and a.claims[0].chunk_ids == ["EDJ-10K-2025#1"]


# --- #187: an invalid paid output raises ModelOutputError with a JSON-safe raw payload --------

class TextBlock:
    """Like the SDK's TextBlock: an object with model_dump, not a dict."""
    type = "text"

    def __init__(self, text):
        self.text = text

    def model_dump(self, mode="python"):
        return {"type": self.type, "text": self.text}


def anthropic_returning(content):
    client = FakeAnthropic()
    client.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(content=content, stop_reason="end_turn"))
    return client


def openai_returning(content):
    client = FakeOpenAI()
    msg = SimpleNamespace(content=content)
    client.chat = SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(choices=[SimpleNamespace(message=msg)])))
    return client


def test_anthropic_invalid_tool_input_keeps_the_payload():
    bad = {"answer": "yes", "behavior": "answer", "claims": []}   # "answer" not a boolean: no alias
    client = anthropic_returning([SimpleNamespace(type="tool_use", name=llm.TOOL_NAME, input=bad)])
    with pytest.raises(llm.ModelOutputError) as e:
        llm._anthropic("q?", [hit()], client=client)
    assert e.value.raw == bad and e.value.provider == "anthropic"
    assert json.loads(json.dumps(e.value.raw)) == bad


def test_anthropic_no_tool_call_keeps_the_text_blocks():
    client = anthropic_returning([TextBlock("I think the answer is yes.")])
    with pytest.raises(llm.ModelOutputError, match="did not call") as e:
        llm._anthropic("q?", [hit()], client=client)
    assert e.value.raw == [{"type": "text", "text": "I think the answer is yes."}]
    json.dumps(e.value.raw)   # JSON-safe without default=


def test_anthropic_no_tool_call_without_model_dump():
    client = anthropic_returning([SimpleNamespace(type="text", text="plain")])
    with pytest.raises(llm.ModelOutputError) as e:
        llm._anthropic("q?", [hit()], client=client)
    assert e.value.raw == [{"type": "text", "text": "plain"}]


@pytest.mark.parametrize("content", [None, "not json", "[1, 2]", json.dumps({"behavior": "answer"})])
def test_openai_invalid_content_keeps_the_payload(content):
    with pytest.raises(llm.ModelOutputError) as e:
        llm._openai("q?", [hit()], client=openai_returning(content))
    assert e.value.raw == content and e.value.provider == "openai"
    json.dumps(e.value.raw)


# --- #230: cut or empty outputs are invalid; every output records why it stopped ----------------

def anthropic_response(content, stop_reason, output_tokens=1234):
    usage = SimpleNamespace(input_tokens=60000, output_tokens=output_tokens)
    client = FakeAnthropic()
    client.messages = SimpleNamespace(create=lambda **kw: SimpleNamespace(content=content, stop_reason=stop_reason,
                                                                          usage=usage))
    return client


def tool(payload):
    return SimpleNamespace(type="tool_use", name=llm.TOOL_NAME, input=payload)


def test_anthropic_cut_at_max_tokens_is_invalid_even_when_it_validates():
    thinking = SimpleNamespace(type="thinking", thinking="")
    client = anthropic_response([thinking, tool(OUTPUT)], "max_tokens", 20000)
    with pytest.raises(llm.ModelOutputError, match="cut at max_tokens") as e:
        llm._anthropic("q?", [hit()], client=client)
    assert e.value.stop_reason == "max_tokens"
    assert e.value.usage == {"input_tokens": 60000, "output_tokens": 20000, "blocks": ["thinking", "tool_use"]}
    assert e.value.raw[1]["input"] == OUTPUT and e.value.raw[0]["type"] == "thinking"   # every block kept
    json.dumps(e.value.raw)


@pytest.mark.parametrize("payload", [
    {"answerable": True, "behavior": "answer"},                                    # the #229 Q22 shape
    {"answerable": True, "behavior": "answer", "items": [{"text": "c", "chunk_ids": ["EDJ-10K-2025#1"]}]},
    {"answerable": True, "behavior": "refuse"},                                    # refuse must be answerable false
])
def test_anthropic_empty_answer_is_invalid_with_the_input_as_sent(payload):
    with pytest.raises(llm.ModelOutputError, match="no claims, adjacent items or gaps") as e:
        llm._anthropic("q?", [hit()], client=anthropic_response([tool(payload)], "tool_use"))
    assert e.value.raw == payload and e.value.stop_reason == "tool_use"
    assert e.value.usage["output_tokens"] == 1234


def test_refusal_with_no_claims_stays_valid():
    a = llm._anthropic("q?", [hit()], client=anthropic_response(
        [tool({"answerable": False, "behavior": "refuse"})], "tool_use"))
    assert a.behavior == "refuse" and a.stop_reason == "tool_use"


def test_valid_output_records_stop_reason_and_usage():
    a = llm._anthropic("q?", [hit()], client=anthropic_response([tool(OUTPUT)], "tool_use", 4321))
    assert a.stop_reason == "tool_use"
    assert a.usage == {"input_tokens": 60000, "output_tokens": 4321, "blocks": ["tool_use"]}
    saved = a.model_dump()
    assert saved["stop_reason"] == "tool_use" and saved["usage"]["output_tokens"] == 4321
    assert "stop_reason" not in json.dumps(llm.llm_output_schema())   # code-owned, never asked of the model


def test_fake_without_usage_still_works():
    a = llm._anthropic("q?", [hit()], client=FakeAnthropic())
    assert a.stop_reason == "" and a.usage == {"input_tokens": None, "output_tokens": None, "blocks": ["tool_use"]}


def openai_finishing(content, finish_reason):
    client = FakeOpenAI()
    usage = SimpleNamespace(prompt_tokens=50000, completion_tokens=777)
    msg = SimpleNamespace(content=content)
    client.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        choices=[SimpleNamespace(message=msg, finish_reason=finish_reason)], usage=usage)))
    return client


def test_openai_length_is_invalid_and_stop_saved():
    with pytest.raises(llm.ModelOutputError, match="cut at max_tokens") as e:
        llm._openai("q?", [hit()], client=openai_finishing(json.dumps(OUTPUT), "length"))
    assert e.value.stop_reason == "length" and e.value.usage["output_tokens"] == 777
    a = llm._openai("q?", [hit()], client=openai_finishing(json.dumps(OUTPUT), "stop"))
    assert a.stop_reason == "stop" and a.usage == {"input_tokens": 50000, "output_tokens": 777}
    with pytest.raises(llm.ModelOutputError, match="no claims"):
        llm._openai("q?", [hit()], client=openai_finishing(json.dumps({"answerable": True, "behavior": "answer"}), "stop"))


def test_check_output_on_a_saved_answer():
    from cee.answer.schema import Answer
    with pytest.raises(llm.ModelOutputError):
        llm.check_output(Answer(answerable=True, behavior="answer"))
    with pytest.raises(llm.ModelOutputError, match="cut"):
        llm.check_output(Answer(answerable=True, behavior="answer", claims=[{"text": "c"}], stop_reason="max_tokens"))
    ok = Answer(answerable=False, behavior="gap_with_adjacent", gaps=[{"what": "x"}])
    assert llm.check_output(ok) is ok


# --- #230: output cap and client settings ---------------------------------------------------------

def test_max_tokens_is_20000():
    assert llm.MAX_TOKENS == 20000 and llm.anthropic_request("q?", [hit()])["max_tokens"] == 20000


def test_sdk_accepts_the_cap_without_streaming():
    anthropic = pytest.importorskip("anthropic")
    from anthropic._constants import MODEL_NONSTREAMING_TOKENS
    client = anthropic.Anthropic(api_key="test-key-not-used")
    client._calculate_nonstreaming_timeout(llm.MAX_TOKENS, MODEL_NONSTREAMING_TOKENS.get("claude-sonnet-5-5"))
    with pytest.raises(ValueError):          # the limit the cap stays under (600 s x 128000 / 3600)
        client._calculate_nonstreaming_timeout(21334, None)


def test_real_clients_never_retry(monkeypatch):
    # TL (#230): a timeout or transport error is a reported failure, never a second paid request.
    # The builders are the originals captured at import (conftest replaces them for every test);
    # fake SDK modules record the constructor arguments, so this needs no SDK and no credentials.
    import sys
    seen = {}

    def recorder(name):
        return lambda **kw: seen.setdefault(name, kw)

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=recorder("anthropic")))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=recorder("openai")))
    REAL_ANTHROPIC_CLIENT()
    REAL_OPENAI_CLIENT()
    assert seen["anthropic"]["max_retries"] == 0 and seen["openai"]["max_retries"] == 0


def test_real_anthropic_client_has_max_retries_0(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")   # constructing makes no request
    client = REAL_ANTHROPIC_CLIENT()
    assert isinstance(client, anthropic.Anthropic) and client.max_retries == 0