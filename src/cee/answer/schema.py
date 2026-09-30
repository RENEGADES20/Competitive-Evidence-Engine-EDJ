"""Answer JSON (docs/ARCHITECTURE.md, ADR-002).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
The LLM fills claims/adjacent/gaps/behavior; code fills source_label, flags and caveats.
"""
from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

Behavior = Literal["answer", "answer_with_boundary", "gap_with_adjacent", "refuse"]


class Claim(BaseModel):
    text: str
    chunk_ids: list[str] = Field(default_factory=list)
    source_label: str = ""                            # built by code, never by the model
    flags: list[str] = Field(default_factory=list)    # e.g. unmatched_citation


class Adjacent(Claim):
    differs_because: str = ""


class Gap(BaseModel):
    what: str
    suggested_source: str = ""


class Answer(BaseModel):
    answerable: bool
    behavior: Behavior
    claims: list[Claim] = Field(default_factory=list)
    adjacent: list[Adjacent] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)  # inserted by code
    llm_called: bool = False


def llm_output_schema() -> dict:
    """JSON schema of the part the model writes (no code-owned fields)."""
    claim = {"type": "object", "additionalProperties": False,
             "properties": {"text": {"type": "string"},
                            "chunk_ids": {"type": "array", "items": {"type": "string"}}},
             "required": ["text", "chunk_ids"]}
    adjacent = {"type": "object", "additionalProperties": False,
                "properties": {**claim["properties"], "differs_because": {"type": "string"}},
                "required": ["text", "chunk_ids", "differs_because"]}
    gap = {"type": "object", "additionalProperties": False,
           "properties": {"what": {"type": "string"}, "suggested_source": {"type": "string"}},
           "required": ["what", "suggested_source"]}
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
