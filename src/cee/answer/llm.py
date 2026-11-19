"""One answer call per question; the question planner (#214, ADR-020) may make one more before
search, so a question uses at most 2 calls (ADR-012 allows 5). Providers: mock | anthropic | openai.

Skeleton placeholder, owner: S2 (Jiapeng Liu).
mock is offline and free: it cites the top hits verbatim. Use it for development and tests.
"""
from __future__ import annotations

import json
import time

from cee.answer.prompt import SYSTEM_PROMPT
from cee.answer.schema import Answer, llm_output_schema
from cee.config import settings
from cee.retrieve.fts import Hit

TOOL_NAME = "submit_answer"
# Output cap of the answer call. 8000 covers 20-30 passages (#181), grid answers with a gap per
# empty cell (#204) and the token budget of the retrieved set (#213, ADR-019); the eval's cache key
# includes it when it differs from 8000, so a run with another cap never reuses an older output.
MAX_TOKENS = 8000


class ModelOutputError(RuntimeError):
    """A paid model call returned something that is not a valid Answer (#187).

    `raw` is the provider payload, always JSON-safe, so the caller can save what was paid for
    (CLAUDE.md "Paid API calls" step 3) instead of losing it with the exception."""

    def __init__(self, message: str, raw, provider: str, stop_reason: str | None = None):
        super().__init__(message)
        self.raw, self.provider, self.stop_reason = raw, provider, stop_reason


def _block_dict(b) -> dict:
    """One Anthropic content block as plain JSON data (SDK objects have model_dump; fakes may not)."""
    if hasattr(b, "model_dump"):
        return b.model_dump(mode="json")
    return {k: getattr(b, k) for k in ("type", "text", "name", "input") if hasattr(b, k)}


def build_user_message(question: str, hits: list[Hit]) -> str:
    parts = [f"Question: {question}", "", "Evidence chunks:"]
    for h in hits:
        seg = f", segment {h.segment}" if h.segment else ""
        dated = (f"period n/a, page content as of {h.published_at} (undated web page)"  # ADR-007 T-09
                 if getattr(h, "date_basis", "source") == "retrieved"
                 else f"period {h.period_end or 'n/a'}, published {h.published_at}")
        where = f"{h.entity_id or 'Research'} {h.doc_type}{seg}, {dated}, {h.section or ''}"
        if h.page:
            where += f", p.{h.page}"
        parts.append(f'<chunk id="{h.chunk_id}" source="{where}">\n{h.text}\n</chunk>')
    return "\n".join(parts)


def generate(question: str, hits: list[Hit], provider: str | None = None) -> Answer:
    provider = provider or settings().llm_provider
    if provider == "mock":
        return _mock(hits)
    if provider == "anthropic":
        return _anthropic(question, hits)
    if provider == "openai":
        return _openai(question, hits)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _clip(text: str, n: int = 300) -> str:
    """Cut at a word boundary, so a figure or its unit is never cut in half (#52)."""
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0]


def _mock(hits: list[Hit]) -> Answer:
    time.sleep(settings().mock_delay_s)  # 0 unless MOCK_DELAY_S is set (verify-cee, #80)
    claims = [{"text": _clip(" ".join(h.text.split())), "chunk_ids": [h.chunk_id]} for h in hits[:3]]
    return Answer(answerable=True, behavior="answer", claims=claims, llm_called=False)


def anthropic_request(question: str, hits: list[Hit]) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT + "\nYou MUST return the result by calling the submit_answer tool;"
                                  " do not answer in plain text.",
        "tools": [{"name": TOOL_NAME, "description": "Submit the cited answer.",
                   "input_schema": llm_output_schema()}],
        # Current Claude models reject forced tool_choice; the prompt requires the tool instead.
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": build_user_message(question, hits)}],
    }


def anthropic_client():
    """The Anthropic client for the answer and the planner call (#214)."""
    import os

    import anthropic

    # Keys not scoped to a workspace must name one in a header.
    ws = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()
    return anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)


def openai_client():
    """The OpenAI client for the answer and the planner call (#214)."""
    import openai

    return openai.OpenAI()


def _anthropic(question: str, hits: list[Hit], client=None) -> Answer:
    if client is None:
        client = anthropic_client()
    resp = client.messages.create(**anthropic_request(question, hits))
    block = next((b for b in resp.content if b.type == "tool_use" and b.name == TOOL_NAME), None)
    if block is None:
        raise ModelOutputError(f"Model did not call {TOOL_NAME} (stop_reason={getattr(resp, 'stop_reason', '?')})",
                               [_block_dict(b) for b in resp.content], "anthropic",
                               getattr(resp, "stop_reason", None))
    raw = block.input
    try:
        return Answer(**raw, llm_called=True)
    except (ValueError, TypeError) as e:  # pydantic ValidationError is a ValueError
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", raw, "anthropic",
                               getattr(resp, "stop_reason", None)) from e


def openai_request(question: str, hits: list[Hit]) -> dict:
    return {
        "model": settings().openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + "\nReturn JSON matching the schema."},
            {"role": "user", "content": build_user_message(question, hits)},
        ],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "answer", "strict": True,
                                            "schema": llm_output_schema()}},
    }


def _openai(question: str, hits: list[Hit], client=None) -> Answer:
    if client is None:
        client = openai_client()
    resp = client.chat.completions.create(**openai_request(question, hits))
    content = resp.choices[0].message.content
    try:
        return Answer(**json.loads(content), llm_called=True)
    except (ValueError, TypeError) as e:  # None, not JSON, not an object, or not a valid Answer
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", content, "openai") from e
