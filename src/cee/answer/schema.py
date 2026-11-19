"""Answer JSON (docs/ARCHITECTURE.md, ADR-002).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
The LLM fills claims/adjacent/gaps/behavior; code fills source_label, flags and caveats.
"""
from __future__ import annotations

import json
from typing import Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

Behavior = Literal["answer", "answer_with_boundary", "gap_with_adjacent", "refuse"]


class Claim(BaseModel):
    text: str
    chunk_ids: list[str] = Field(default_factory=list)
    part_id: str = ""                                 # the plan part it answers (prompt v4, #215); "" in v3 outputs
    source_label: str = ""                            # built by code, never by the model
    flags: list[str] = Field(default_factory=list)    # e.g. unmatched_citation


class Adjacent(Claim):
    differs_because: str = ""


class Gap(BaseModel):
    what: str
    suggested_source: str = ""
    part_id: str = ""                                 # the plan part it names (prompt v4, #215)
    flags: list[str] = Field(default_factory=list)    # code-owned: part_gap, uncited_cell (#215)
    claim_text: str = ""                              # code-owned: an uncited grid cell's model text, not shown


class Withheld(BaseModel):
    """A claim kept out of the shown answer by code (#118, ground rule 6); kept here for review."""
    text: str
    chunk_ids: list[str] = Field(default_factory=list)
    reason: str = "normative"


class Answer(BaseModel):
    answerable: bool
    behavior: Behavior
    claims: list[Claim] = Field(default_factory=list)
    adjacent: list[Adjacent] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)  # inserted by code
    coverage_note: str = ""                            # built by code from the retrieved hits
    withheld: list[Withheld] = Field(default_factory=list)  # normative claims, not shown (#118)
    llm_called: bool = False
    # Code-owned, from the provider response (#230): why the output stopped (Anthropic stop_reason,
    # OpenAI finish_reason; "" for the mock and outputs saved before #230) and its token usage
    # (input_tokens, output_tokens; Anthropic also the content block types, e.g. thinking, tool_use).
    stop_reason: str = ""
    usage: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _answer_sent_for_answerable(cls, data):
        """The model once sent the boolean as "answer" instead of "answerable" (Q25, real run
        2026-11-16, #167); the eval run crashed and the paid output was lost. Accept that one
        alias for a boolean; anything else still fails validation."""
        if isinstance(data, dict) and "answerable" not in data and isinstance(data.get("answer"), bool):
            data = {**data, "answerable": data["answer"]}
            data.pop("answer")
        return data

    @field_validator("claims", "adjacent", "gaps", "caveats", mode="before")
    @classmethod
    def _list_sent_as_string(cls, v):
        """The model sometimes sends a list field as "" or as a JSON-encoded string (Q20, real run
        2026-10-30); a bare "" crashed the whole eval run. Empty -> [], JSON list -> parsed.
        Any other string is left alone so validation still fails loudly."""
        if not isinstance(v, str):
            return v
        if not v.strip():
            return []
        try:
            parsed = json.loads(v)
        except ValueError:
            return v
        return parsed if isinstance(parsed, list) else v


def llm_output_schema() -> dict:
    """JSON schema of the part the model writes (no code-owned fields)."""
    # part_id (#215): required for OpenAI strict mode; "" when the item answers no listed part.
    claim = {"type": "object", "additionalProperties": False,
             "properties": {"text": {"type": "string"},
                            "chunk_ids": {"type": "array", "items": {"type": "string"}},
                            "part_id": {"type": "string"}},
             "required": ["text", "chunk_ids", "part_id"]}
    adjacent = {"type": "object", "additionalProperties": False,
                "properties": {**claim["properties"], "differs_because": {"type": "string"}},
                "required": ["text", "chunk_ids", "part_id", "differs_because"]}
    gap = {"type": "object", "additionalProperties": False,
           "properties": {"what": {"type": "string"}, "suggested_source": {"type": "string"},
                          "part_id": {"type": "string"}},
           "required": ["what", "suggested_source", "part_id"]}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "answerable": {"type": "boolean"},
            "behavior": {"type": "string", "enum": list(get_args(Behavior))},
            "claims": {"type": "array", "items": claim},
            "adjacent": {"type": "array", "items": adjacent},
            "gaps": {"type": "array", "items": gap},
        },
        "required": ["answerable", "behavior", "claims", "adjacent", "gaps"],
    }
