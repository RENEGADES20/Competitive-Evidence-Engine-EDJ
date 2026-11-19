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


NO_PASSAGES = "(no passages were found for this part)"
KEPT_ELSEWHERE = ("(no further passages; the passages found for this part are listed under another part "
                  "or the research passages)")
RESEARCH_HEADING = "Research passages (found for the whole question):"
PEERS_HEADING = "Peer firms on the question's theme:"


def _chunk(h: Hit) -> str:
    seg = f", segment {h.segment}" if h.segment else ""
    dated = (f"period n/a, page content as of {h.published_at} (undated web page)"  # ADR-007 T-09
             if getattr(h, "date_basis", "source") == "retrieved"
             else f"period {h.period_end or 'n/a'}, published {h.published_at}")
    where = f"{h.entity_id or 'Research'} {h.doc_type}{seg}, {dated}, {h.section or ''}"
    if h.page:
        where += f", p.{h.page}"
    return f'<chunk id="{h.chunk_id}" source="{where}">\n{h.text}\n</chunk>'


def _part_head(part) -> str:
    from cee.answer.validate import _short_name
    firms = ", ".join(_short_name(f) for f in part.firms)
    return f"{part.id}" + (f" [{firms}]" if firms else "") + f": {' '.join(part.text.split())}"


def build_user_message(question: str, hits: list[Hit], plan=None) -> str:
    """Prompt v4 (#215): the plan's parts, then the evidence grouped under the part it was found
    for (hits keep their order inside a group), then research and peer passages. A part with no
    passages of its own says why, from its candidate pool before exclusion (plan.searched): pool
    0 -> nothing found; otherwise its passages sit under another part or the research passages.
    No plan: one part p1, the whole question, holding every hit that is not research or peers."""
    parts = list(getattr(plan, "parts", None) or [])
    if not parts:
        from cee.retrieve.planner import Part
        parts = [Part("p1", question, [])]
    single = len(parts) == 1
    pools = {s["id"]: s.get("pool") for s in getattr(plan, "searched", None) or []}

    def part_of(h: Hit) -> str | None:
        pid = getattr(h, "part_id", None)
        if pid in ("research", "peers"):
            return pid
        if single:
            return parts[0].id
        return pid if any(p.id == pid for p in parts) else "other"

    lines = [f"Question: {question}", "",
             "Parts of the question (from the search plan; every claim, adjacent item and gap gives the "
             "part_id it answers):"]
    lines += [f"- {_part_head(p)}" for p in parts]
    lines += ["", "Evidence chunks, grouped by the part they were found for:"]
    for p in parts:
        own = [h for h in hits if part_of(h) == p.id]
        lines.append(f"Part {_part_head(p)}")
        if own:
            lines += [_chunk(h) for h in own]
        else:
            lines.append(NO_PASSAGES if pools.get(p.id) == 0 else KEPT_ELSEWHERE)
    for heading, kind in ((RESEARCH_HEADING, "research"), (PEERS_HEADING, "peers"),
                          ("Other passages:", "other")):   # "other": a part not in the plan, never left out
        group = [h for h in hits if part_of(h) == kind]
        if group:
            lines.append(heading)
            lines += [_chunk(h) for h in group]
    return "\n".join(lines)


def generate(question: str, hits: list[Hit], provider: str | None = None, plan=None) -> Answer:
    provider = provider or settings().llm_provider
    if provider == "mock":
        return _mock(hits, plan)
    if provider == "anthropic":
        return _anthropic(question, hits, plan=plan)
    if provider == "openai":
        return _openai(question, hits, plan=plan)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _clip(text: str, n: int = 300) -> str:
    """Cut at a word boundary, so a figure or its unit is never cut in half (#52)."""
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0]


def _mock(hits: list[Hit], plan=None) -> Answer:
    """The top 3 hits verbatim; each claim carries its hit's plan part (#215), so the part check
    runs on mock answers too (a part the mock does not cite gets a code gap)."""
    time.sleep(settings().mock_delay_s)  # 0 unless MOCK_DELAY_S is set (verify-cee, #80)
    ids = {p.id for p in getattr(plan, "parts", None) or []}
    claims = [{"text": _clip(" ".join(h.text.split())), "chunk_ids": [h.chunk_id],
               "part_id": h.part_id if getattr(h, "part_id", None) in ids else ""} for h in hits[:3]]
    return Answer(answerable=True, behavior="answer", claims=claims, llm_called=False)


def anthropic_request(question: str, hits: list[Hit], plan=None) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": MAX_TOKENS,
        "system": SYSTEM_PROMPT + "\nYou MUST return the result by calling the submit_answer tool;"
                                  " do not answer in plain text.",
        "tools": [{"name": TOOL_NAME, "description": "Submit the cited answer.",
                   "input_schema": llm_output_schema()}],
        # Current Claude models reject forced tool_choice; the prompt requires the tool instead.
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": build_user_message(question, hits, plan)}],
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


def _anthropic(question: str, hits: list[Hit], client=None, plan=None) -> Answer:
    if client is None:
        client = anthropic_client()
    resp = client.messages.create(**anthropic_request(question, hits, plan))
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


def openai_request(question: str, hits: list[Hit], plan=None) -> dict:
    return {
        "model": settings().openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT + "\nReturn JSON matching the schema."},
            {"role": "user", "content": build_user_message(question, hits, plan)},
        ],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "answer", "strict": True,
                                            "schema": llm_output_schema()}},
    }


def _openai(question: str, hits: list[Hit], client=None, plan=None) -> Answer:
    if client is None:
        client = openai_client()
    resp = client.chat.completions.create(**openai_request(question, hits, plan))
    content = resp.choices[0].message.content
    try:
        return Answer(**json.loads(content), llm_called=True)
    except (ValueError, TypeError) as e:  # None, not JSON, not an object, or not a valid Answer
        raise ModelOutputError(f"Model output is not a valid Answer: {e}", content, "openai") from e
