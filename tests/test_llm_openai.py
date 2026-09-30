"""Request building for the paid providers, with fake clients. Never calls a real API."""
import json
from types import SimpleNamespace

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
