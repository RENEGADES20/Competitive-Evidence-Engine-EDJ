"""Request building for the paid providers, with fake clients. Never calls a real API."""
import json
from types import SimpleNamespace

import pytest

from cee.answer import llm
from tests.test_validate import hit

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
