"""One LLM call per answer (ADR-003). Providers: mock | anthropic | openai.

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


def build_user_message(question: str, hits: list[Hit]) -> str:
    parts = [f"Question: {question}", "", "Evidence chunks:"]
    for h in hits:
        seg = f", segment {h.segment}" if h.segment else ""
        where = (f"{h.entity_id or 'Research'} {h.doc_type}{seg}, period {h.period_end or 'n/a'}, "
                 f"published {h.published_at}, {h.section or ''}")
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


def _mock(hits: list[Hit]) -> Answer:
    time.sleep(settings().mock_delay_s)  # 0 unless MOCK_DELAY_S is set (verify-cee, #80)
    claims = [{"text": " ".join(h.text.split())[:300], "chunk_ids": [h.chunk_id]} for h in hits[:3]]
    return Answer(answerable=True, behavior="answer", claims=claims, llm_called=False)


def anthropic_request(question: str, hits: list[Hit]) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": 4000,  # 20 chunks (fts.K) give longer answers than the 8 of v0
        "system": SYSTEM_PROMPT + "\nYou MUST return the result by calling the submit_answer tool;"
                                  " do not answer in plain text.",
        "tools": [{"name": TOOL_NAME, "description": "Submit the cited answer.",
                   "input_schema": llm_output_schema()}],
        # Current Claude models reject forced tool_choice; the prompt requires the tool instead.
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": build_user_message(question, hits)}],
    }


def _anthropic(question: str, hits: list[Hit], client=None) -> Answer:
    if client is None:
        import os

        import anthropic

        # Keys not scoped to a workspace must name one in a header.
        ws = os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip()
        client = anthropic.Anthropic(default_headers={"anthropic-workspace-id": ws} if ws else None)
    resp = client.messages.create(**anthropic_request(question, hits))
    block = next((b for b in resp.content if b.type == "tool_use" and b.name == TOOL_NAME), None)
    if block is None:
        raise RuntimeError(f"Model did not call {TOOL_NAME} (stop_reason={getattr(resp, 'stop_reason', '?')})")
    return Answer(**block.input, llm_called=True)


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
        import openai

        client = openai.OpenAI()
    resp = client.chat.completions.create(**openai_request(question, hits))
    return Answer(**json.loads(resp.choices[0].message.content), llm_called=True)
