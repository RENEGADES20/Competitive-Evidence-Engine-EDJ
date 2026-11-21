"""Map step (#246, ADR-021 rules 1, 3, 6, 7): per-firm structured extraction, corrective re-search,
evidence matrix.

- Round 1: one extraction call per firm (its sub-questions' passages) plus one for the research
  passages, in parallel (MAP_CONCURRENCY). Prompt extract-v1, a strict tool / schema on every
  provider. Each output is checked by code: chunk ids against the cell's retrieved set (rejected ids
  flagged, never dropped silently), quotes, figures, periods.
- Corrective re-search (CRAG): every not_found sub-question once, through
  planner.corrective_search, with widened words (the firm's metric definition entry, adjacent
  periods), every chunk already retrieved excluded.
- Round 2: one re-extraction call per firm, over only the re-searched sub-questions that found new
  chunks, and only those chunks. A re-extracted cell is final.
- An invalid output or a failed call makes that call's cells `failed`: saved, never re-rolled.
- cee.answer.matrix then applies the code rules (behavior, comparability, gaps, caveats).
The mock provider extracts deterministically (0 calls). Tests and CI make 0 real calls.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, Literal

from pydantic import BaseModel, Field

from cee.answer.matrix import Cell, EvidenceMatrix, Item, LABELS, OPERATIONS, finish, metric_definition
from cee.config import settings
from cee.retrieve import fts
from cee.retrieve.fts import Hit, Query

EXTRACT_VERSION = "extract-v1.1"   # #247: the asked quantity for other periods is a fact (ADR-021 rule 3)
EXTRACT_TOOL = "submit_extraction"

# Approval condition 1 (plan review 2): one proxy text, used verbatim in the firm and research prompts.
PROXY_RULE = """Only the quantity a sub-question names is a fact for it; a figure that only resembles it is never a
fact. A sub-question marked [proxy] names a stand-in figure (a numerator, a denominator or the
closest measure to what the question asks, such as total client assets or the firm's count of
financial advisors): that named figure, as the firm reports it, is a fact. A figure of a different
measure than the one named (all employees, full-time equivalents, compensation expense, client
firms on a platform) is different_quantity, with differs_because. When unsure between fact and
different_quantity, choose different_quantity and say why."""

SYSTEM_PROMPT = """You extract evidence about one firm from passages of its documents, for a question about
wealth-management firms. Code has split the question into sub-questions; return exactly one cell
for each sub-question listed. You do not answer the question and you do not compare firms: code
and a later step do that.

Use only the passages below. Never use what you know from elsewhere, never estimate, never compute
a figure.

Label each cell:
- fact: a passage states what the sub-question asks for this firm, in full or in part. Partial is
  still a fact (some periods, a narrower group or sample, one of several figures); the item says
  what it covers (period, scope). The asked quantity for periods other than those asked (older or
  later) is also a fact, for the periods it covers: the item's period says which; it is never
  different_quantity.
- different_quantity: no passage states the asked quantity, but one states a different, related
  quantity: a wider unit that contains the asked one (a parent company, a segment that also holds
  other businesses), a different measure (all employees or full-time equivalents for advisors,
  compensation expense for a payout grid or a headcount, client firms on a platform for the firm's
  own advisors, a regulatory form's label for a business metric), or an industry figure for a firm's
  own figure. A different period of the asked quantity is not a different quantity. Put it in items
  and say in differs_because how it differs from what is asked.
- not_disclosed: the passages show the firm does not report it (they say so, or they report the
  surrounding figures without it).
- not_found: the passages say nothing about it.
{proxy_rule}

Items (fact and different_quantity only), one per figure or statement; a series is one item per
period:
- text: one sentence stating what the passage says, attributed to the firm, in the passage's terms;
- quote: the exact words of the passage that support it, copied, at most about 300 characters;
- chunk_ids: the ids of the passages quoted, only ids listed below;
- value: the figure as printed ("20,425", "$1.2 billion"), "" when the item states no figure;
- unit: what is counted or measured ("financial advisors", "USD"), "" when no figure;
- period: "YYYY-MM-DD" for a point in time, "YYYYQn" for a calendar quarter, "FYYYYY" for a fiscal
  year, "YYYY" for a calendar year; "" when not stated or no figure;
- scope: the part of the firm the figure covers as the passage says (a segment, a country), "" for
  the whole firm;
- definition: the firm's own definition of the quantity when a passage gives one, quoted; else "".
The firm's own definition of a metric, quoted from a passage, is a fact for a sub-question that asks
how the firm defines or reports it.

Derivation: when a sub-question asks for a quantity the firm does not report but which follows from
figures in your other cells (a ratio, a sum or a difference) for the same period and scope, label it
not_disclosed and set derivation to the operation and its inputs (sub-question id and item number,
counting from 0; numerator first). Do not compute it: code checks and computes it. Otherwise the
operation is "" and inputs is empty.

reason: one short sentence on why you chose the label.
Positions others hold about the future (executives, analysts, surveys) are facts when the passage
attributes and dates them; never add a forecast of your own. Write nothing about what any firm
should do.
Return the cells by calling the {tool} tool."""

RESEARCH_NOTE = """These passages are industry research, not one firm's documents; the cell ids end in .research. A
research figure is a fact for an aspect about the industry, clients or advisors in general; for an
aspect about a named firm's own figure it is a different_quantity (an industry figure, not the
firm's disclosure)."""


def system_prompt(research: bool = False) -> str:
    text = SYSTEM_PROMPT.format(proxy_rule=PROXY_RULE, tool=EXTRACT_TOOL)
    return text + ("\n\n" + RESEARCH_NOTE if research else "")


# --- call specs -------------------------------------------------------------------------------

@dataclass
class CellSpec:
    id: str
    entity: str | None
    aspect: object          # planner.Aspect
    role: str
    text: str


@dataclass
class MapSpec:
    """One extraction call: its cells, the passages listed under each, and each cell's retrieved set."""
    id: str                 # map.EDJ | map.research | map.all | remap.EDJ
    round: int
    entity: str | None
    research: bool
    cells: list[CellSpec]
    groups: dict[str, list[Hit]]          # cell id -> passages listed under it (input order)
    allowed: dict[str, set[str]]          # cell id -> chunk ids it may cite (section 6)
    pools: dict[str, int | None] = field(default_factory=dict)   # for the "no passages" line

    @property
    def hits(self) -> list[Hit]:
        seen, out = set(), []
        for hs in self.groups.values():
            for h in hs:
                if h.chunk_id not in seen:
                    seen.add(h.chunk_id)
                    out.append(h)
        return out

    @property
    def cell_ids(self) -> list[str]:
        return [c.id for c in self.cells]


def _row_key(entity: str | None) -> str:
    return entity or "all"


def map_specs(q: Query, plan, hits: list[Hit]) -> tuple[list[MapSpec], list[Cell]]:
    """Round-1 calls (one per firm with passages, plus research) and the code cells of firms that
    kept no passage (not_found, no call)."""
    by_sub: dict[str, list[Hit]] = {}
    for h in hits:
        by_sub.setdefault(h.part_id or "", []).append(h)
    pools = {s["id"]: (0 if s.get("floor_emptied") else s.get("pool")) for s in getattr(plan, "searched", []) or []}
    groups: dict[str, list] = {}
    for sq in plan.subquestions:
        groups.setdefault(_row_key(sq.entity), []).append(sq)
    single = len(plan.subquestions) == 1
    specs, code_cells = [], []
    for key, sqs in groups.items():
        own = {sq.id: list(by_sub.get(sq.id, [])) for sq in sqs}
        if single and not own[sqs[0].id]:   # passage mode / one part: every non-research hit
            own[sqs[0].id] = [h for h in hits if h.part_id not in ("research", "peers")]
        input_ids = {h.chunk_id for hs in own.values() for h in hs}
        if not input_ids:
            for sq in sqs:
                code_cells.append(Cell(sq.id, sq.entity, sq.aspect.id, sq.role, "not_found", source="code",
                                       reason="no passages retrieved", flags=["no_passages"]))
            continue
        allowed = {sq.id: {h.chunk_id for h in own[sq.id]}
                   | (set(getattr(plan, "pools", {}).get(sq.id, set())) & input_ids) for sq in sqs}
        specs.append(MapSpec(f"map.{key}", 1, sqs[0].entity, False,
                             [CellSpec(sq.id, sq.entity, sq.aspect, sq.role, sq.text) for sq in sqs],
                             own, allowed, {sq.id: pools.get(sq.id) for sq in sqs}))
    research = [h for h in hits if h.part_id == "research"]
    if research:
        cells = [CellSpec(f"{a.id}.research", None, a, "research", a.text) for a in plan.aspects]
        ids = {h.chunk_id for h in research}
        specs.append(MapSpec("map.research", 1, None, True, cells,
                             {cells[0].id: research, **{c.id: [] for c in cells[1:]}},
                             {c.id: set(ids) for c in cells}))
    return specs, code_cells


# --- schema and messages ----------------------------------------------------------------------

def extraction_schema(spec: MapSpec, strict: bool = False) -> dict:
    """strict=True: the OpenAI and DeepSeek schema (no array limits); strict=False: the Anthropic
    tool's schema (strict tool since #232; minItems 1 on cells). Every property required, no extra
    properties, "" for none (no nullable types)."""
    ids = spec.cell_ids
    item = {"type": "object", "additionalProperties": False,
            "properties": {k: {"type": "string"} for k in
                           ("text", "quote", "value", "unit", "period", "scope", "definition")}
            | {"chunk_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["text", "quote", "chunk_ids", "value", "unit", "period", "scope", "definition"]}
    ref = {"type": "object", "additionalProperties": False,
           "properties": {"subquestion_id": {"type": "string", "enum": ids}, "item": {"type": "integer"}},
           "required": ["subquestion_id", "item"]}
    derivation = {"type": "object", "additionalProperties": False,
                  "properties": {"operation": {"type": "string", "enum": list(OPERATIONS)},
                                 "inputs": {"type": "array", "items": ref}},
                  "required": ["operation", "inputs"]}
    cell = {"type": "object", "additionalProperties": False,
            "properties": {"subquestion_id": {"type": "string", "enum": ids},
                           "label": {"type": "string", "enum": list(LABELS)},
                           "items": {"type": "array", "items": item},
                           "differs_because": {"type": "string"}, "reason": {"type": "string"},
                           "derivation": derivation},
            "required": ["subquestion_id", "label", "items", "differs_because", "reason", "derivation"]}
    cells = {"type": "array", "items": cell}
    if not strict:
        cells |= {"minItems": 1}
    return {"type": "object", "additionalProperties": False, "properties": {"cells": cells},
            "required": ["cells"]}


def query_window(q: Query):
    """The question's window and the Ask page date range, their overlap (as ask.answer_window)."""
    spans = [s for s in (getattr(q, "window", None), getattr(q, "date_range", None)) if s]
    if not spans:
        return None
    return (max(s[0] for s in spans), min(s[1] for s in spans))


def extract_message(question: str, spec: MapSpec, window=None, firms: list[str] | None = None) -> str:
    from cee.answer.llm import KEPT_ELSEWHERE, NO_PASSAGES, _chunk
    from cee.answer.matrix import row_name
    if spec.research:
        named = ", ".join(row_name(f) for f in (firms or [])) or "none"
        head = f"Industry research (no firm; firms in the question: {named})"
    elif spec.entity:
        from cee.retrieve.planner import firm_name
        head = f"{firm_name(spec.entity)} ({spec.entity})"
    else:
        head = "All sources (no firm named)"
    lines = [f"Question: {question}", f"Firm: {head}"]
    if window:
        lines.append(f"Time window: {window[0]} to {window[1]} (only passages dated in it were searched).")
    lines += ["", "Sub-questions (return one cell for each, with this id):"]
    for c in spec.cells:
        tags = [c.aspect.kind] + ([f"metric {c.aspect.metric}"] if c.aspect.metric else []) \
            + (["proxy"] if getattr(c.aspect, "proxy", False) else [])
        lines.append(f"- {c.id} [{', '.join(tags)}]: {' '.join(c.aspect.text.split())}")
    lines += ["", "Passages, grouped by the sub-question they were found for:"]
    for c in spec.cells:
        own = spec.groups.get(c.id) or []
        lines.append(f"Sub-question {c.id}")
        if own:
            lines += [_chunk(h) for h in own]
        elif spec.research:
            lines.append("(the research passages are listed under the first sub-question; they apply to every one)")
        else:
            lines.append(NO_PASSAGES if spec.pools.get(c.id) == 0 else KEPT_ELSEWHERE)
    return "\n".join(lines)


def extract_max_tokens(provider: str) -> int:
    """The map call's output cap: deepseek by the map stage's effort (#272: off 20000, thinking 128000),
    else llm.MAX_TOKENS. It joins the map cache key directly."""
    from cee.answer import llm
    if provider == "deepseek":
        return llm.stage_max_tokens("map")
    return llm.MAX_TOKENS


def anthropic_extract_request(question: str, spec: MapSpec, window=None, firms=None) -> dict:
    return {"model": settings().llm_model, "max_tokens": extract_max_tokens("anthropic"),
            "system": system_prompt(spec.research),
            "tools": [{"name": EXTRACT_TOOL, "description": "Submit the extracted cells.", "strict": True,
                       "input_schema": extraction_schema(spec)}],
            "tool_choice": {"type": "auto"},
            "messages": [{"role": "user", "content": extract_message(question, spec, window, firms)}]}


def openai_extract_request(question: str, spec: MapSpec, window=None, firms=None) -> dict:
    return {"model": settings().openai_model,
            "messages": [{"role": "system", "content": system_prompt(spec.research) + "\nReturn JSON matching the schema."},
                         {"role": "user", "content": extract_message(question, spec, window, firms)}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "extraction", "strict": True,
                                                "schema": extraction_schema(spec, strict=True)}}}


def deepseek_extract_request(question: str, spec: MapSpec, window=None, firms=None) -> dict:
    from cee.answer.llm import deepseek_tool_request
    return deepseek_tool_request(EXTRACT_TOOL, "Submit the extracted cells.", extraction_schema(spec, strict=True),
                                 system_prompt(spec.research), extract_message(question, spec, window, firms),
                                 extract_max_tokens("deepseek"), stage="map")


def input_tokens(question: str, spec: MapSpec, window=None, firms=None) -> int:
    """Estimated input tokens of one map call (characters / 4)."""
    chars = (len(system_prompt(spec.research)) + len(json.dumps(extraction_schema(spec)))
             + len(extract_message(question, spec, window, firms)))
    return round(chars / 4)


# --- output -----------------------------------------------------------------------------------

class ItemOut(BaseModel):
    text: str
    quote: str = ""
    chunk_ids: list[str] = Field(default_factory=list)
    value: str = ""
    unit: str = ""
    period: str = ""
    scope: str = ""
    definition: str = ""


class RefOut(BaseModel):
    subquestion_id: str
    item: int


class DerivationOut(BaseModel):
    operation: Literal["", "ratio", "sum", "difference"] = ""
    inputs: list[RefOut] = Field(default_factory=list)


class CellOut(BaseModel):
    subquestion_id: str
    label: Literal["fact", "not_disclosed", "not_found", "different_quantity"]
    items: list[ItemOut] = Field(default_factory=list)
    differs_because: str = ""
    reason: str = ""
    derivation: DerivationOut = Field(default_factory=DerivationOut)


class MapOutput(BaseModel):
    cells: list[CellOut]


def validate_output(raw, provider: str, stop=None, usage=None) -> MapOutput:
    """The tool input as a MapOutput, else ModelOutputError (invalid: saved, never re-rolled)."""
    from cee.answer.llm import ModelOutputError
    try:
        out = MapOutput(**raw) if isinstance(raw, dict) else None
    except (ValueError, TypeError) as e:
        raise ModelOutputError(f"Map output is not a valid extraction: {e}", raw, provider, stop, usage) from e
    if out is None:
        raise ModelOutputError("Map output is not a JSON object", raw, provider, stop, usage)
    if not out.cells:
        raise ModelOutputError("Map output has no cells", raw, provider, stop, usage)
    return out


def call_extract(question: str, spec: MapSpec, provider: str, window=None, firms=None, client=None,
                 meta: dict | None = None) -> dict:
    """One extraction call; the raw tool input (a dict), or ModelOutputError when the output cannot
    be trusted (no tool call, cut at the cap, refusal, a DeepSeek finish_reason other than
    tool_calls / stop, not JSON, not a valid extraction, no cells). `meta` gets stop_reason, usage
    and (deepseek) reasoning_content. ProviderStop and any other exception propagate."""
    from cee.answer import llm
    meta = {} if meta is None else meta
    if provider == "anthropic":
        client = client or llm.anthropic_client()
        resp = client.messages.create(**anthropic_extract_request(question, spec, window, firms))
        stop = getattr(resp, "stop_reason", None)
        usage = {**llm._usage(resp, "input_tokens", "output_tokens"),
                 "blocks": [getattr(b, "type", "?") for b in resp.content]}
        meta["stop_reason"], meta["usage"] = stop, usage
        blocks = [llm._block_dict(b) for b in resp.content]
        block = next((b for b in resp.content if b.type == "tool_use" and b.name == EXTRACT_TOOL), None)
        if block is None:
            raise llm.ModelOutputError(f"Model did not call {EXTRACT_TOOL} (stop_reason={stop or '?'})",
                                       blocks, provider, stop, usage)
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Map output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       blocks, provider, stop, usage)
        if stop == llm.REFUSAL:
            raise llm.ModelOutputError("Map output stopped by refusal", blocks, provider, stop, usage)
        raw = block.input
    elif provider == "openai":
        client = client or llm.openai_client()
        resp = client.chat.completions.create(**openai_extract_request(question, spec, window, firms))
        content = resp.choices[0].message.content
        stop = getattr(resp.choices[0], "finish_reason", None)
        usage = llm._usage(resp, "prompt_tokens", "completion_tokens")
        meta["stop_reason"], meta["usage"] = stop, usage
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Map output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       content, provider, stop, usage)
        flags: list = []
        try:
            raw = llm.loads_object(content, flags)
        except (TypeError, ValueError) as e:
            raise llm.ModelOutputError(f"Map output is not JSON: {e}", content, provider, stop, usage) from e
        if flags:
            meta["parse_flags"] = flags
    elif provider == "deepseek":
        client = client or llm.deepseek_client()
        req = deepseek_extract_request(question, spec, window, firms)
        resp = llm.deepseek_create(client, req)
        call, stop, usage, payload = llm.deepseek_tool_call(resp, EXTRACT_TOOL, req)
        msg = payload if isinstance(payload, dict) else {}
        meta["stop_reason"], meta["usage"] = stop, usage
        meta["reasoning_content"] = msg.get("reasoning_content")
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Map output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       payload, provider, stop, usage)
        if stop not in llm.DEEPSEEK_OK:
            raise llm.ModelOutputError(f"Map output stopped by finish_reason {stop}", payload, provider, stop, usage)
        if call is None:
            raise llm.ModelOutputError(f"Model did not call {EXTRACT_TOOL} (finish_reason={stop or '?'})",
                                       payload, provider, stop, usage)
        flags: list = []
        try:
            raw = llm.deepseek_arguments(call, flags)   # #246 TL: stray closing braces accepted, flagged
        except (TypeError, ValueError) as e:
            raise llm.ModelOutputError(f"Map arguments are not a JSON object: {e}", call.function.arguments,
                                       provider, stop, usage) from e
        if flags:
            meta["parse_flags"] = flags
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
    validate_output(raw, provider, meta.get("stop_reason"), meta.get("usage"))
    return raw


# --- code checks on an output (plan section 6) --------------------------------------------------

_PERIOD = re.compile(r"^(?:\d{4}-\d{2}-\d{2}|\d{4}Q[1-4]|FY\d{4}|\d{4})$")


def _squash(text: str) -> str:
    return " ".join(str(text or "").split())


def _value_found(value: str, texts: list[str]) -> bool:
    """The item's figure is in one of its cited chunks (the answer's number check rules, #52)."""
    from cee.answer.validate import _chunk_values, figures, number_matches
    fs = figures(value or "")
    if not fs:
        return True
    scaled = [v for t in texts for v in _chunk_values(t)]
    bare = [v for t in texts for v in _chunk_values(t, unscaled=True)]
    unitless = [float(f.shown) for t in texts for f in figures(t) if f.scale == 1.0]

    def found(f) -> bool:
        values = bare if f.scale == 1.0 else scaled + [v * f.scale for v in unitless]
        return any(number_matches(f, v) for v in values)

    return all(found(f) for f in fs)


def parse_output(raw: dict, spec: MapSpec, by_id: dict[str, Hit], source: str = "model") -> list[Cell]:
    """Cells of one valid output, checked by code: chunk ids outside the cell's retrieved set are
    rejected (flag unmatched_citation, kept in rejected_ids); the quote must be in a cited chunk
    (quote_not_found); the figure must be in a cited chunk (number_not_found); periods normalised
    (period_unparsed). A missing cell is not_found (missing_cell); a duplicate is dropped (flag on
    the kept one)."""
    out = MapOutput(**raw)
    specs = {c.id: c for c in spec.cells}
    cells: dict[str, Cell] = {}
    for co in out.cells:
        cs = specs.get(co.subquestion_id)
        if cs is None:
            continue
        if cs.id in cells:
            if "duplicate_cell" not in cells[cs.id].flags:
                cells[cs.id].flags.append("duplicate_cell")
            continue
        allowed = spec.allowed.get(cs.id, set())
        items = []
        for io in co.items:
            ok = [c for c in io.chunk_ids if c in allowed]
            bad = [c for c in io.chunk_ids if c not in allowed]
            item = Item(io.text, io.quote, list(dict.fromkeys(ok)), io.value, io.unit, "", io.scope,
                        io.definition, rejected_ids=bad)
            if bad:
                item.flags.append("unmatched_citation")
            period = io.period.strip()
            if period and not _PERIOD.match(period):
                item.flags.append("period_unparsed")
                period = ""
            item.period = period
            texts = [by_id[c].text for c in item.chunk_ids if c in by_id]
            if texts and io.quote.strip() and not any(_squash(io.quote) in _squash(t) for t in texts):
                item.flags.append("quote_not_found")
            if texts and io.value.strip() and not _value_found(io.value, texts):
                item.flags.append("number_not_found")
            items.append(item)
        derivation = None
        if co.derivation.operation:
            derivation = {"operation": co.derivation.operation,
                          "inputs": [r.model_dump() for r in co.derivation.inputs]}
        cells[cs.id] = Cell(cs.id, cs.entity, cs.aspect.id, cs.role, co.label, source=source, items=items,
                            differs_because=co.differs_because, reason=co.reason, derivation=derivation)
    for cs in spec.cells:
        if cs.id not in cells:
            cells[cs.id] = Cell(cs.id, cs.entity, cs.aspect.id, cs.role, "not_found", source=source,
                                reason="the output had no cell for this sub-question", flags=["missing_cell"])
    return [cells[c.id] for c in spec.cells]


def failed_cells(spec: MapSpec, error: str) -> list[Cell]:
    return [Cell(c.id, c.entity, c.aspect.id, c.role, "failed", source="code", reason=error, error=error)
            for c in spec.cells]


# --- mock -------------------------------------------------------------------------------------

def mock_extract(spec: MapSpec) -> dict:
    """Deterministic, 0 calls: each cell with passages listed under it is a fact with one item from
    its top passage (the quote verbatim, so the quote check passes); none -> not_found. Research:
    every aspect reads the research passages."""
    time.sleep(settings().mock_delay_s)
    research = spec.groups.get(spec.cells[0].id, []) if spec.research else []
    cells = []
    for c in spec.cells:
        own = research if spec.research else spec.groups.get(c.id) or []
        if not own:
            cells.append({"subquestion_id": c.id, "label": "not_found", "items": [], "differs_because": "",
                          "reason": "no passages", "derivation": {"operation": "", "inputs": []}})
            continue
        h = own[0]
        text = _squash(h.text)
        text = text if len(text) <= 200 else text[:200].rsplit(" ", 1)[0]
        cells.append({"subquestion_id": c.id, "label": "fact",
                      "items": [{"text": text, "quote": text, "chunk_ids": [h.chunk_id], "value": "", "unit": "",
                                 "period": "", "scope": "", "definition": ""}],
                      "differs_because": "", "reason": "mock: the top passage",
                      "derivation": {"operation": "", "inputs": []}})
    return {"cells": cells}


# --- corrective re-search words (plan section 7) -------------------------------------------------

_ORDINAL = {1: "first", 2: "second", 3: "third", 4: "fourth"}
_FULLTEXT = re.compile(r"full-text search[^:]*:\s*(.+)$", re.I)


def _quarter(d: dt.date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def _quarter_words(year: int, quarter: int) -> list[str]:
    return [f"{_ORDINAL[quarter]} quarter {year}", f"{quarter}Q{str(year)[2:]}"]


def _shift(year: int, quarter: int, n: int) -> tuple[int, int]:
    k = year * 4 + (quarter - 1) + n
    return k // 4, k % 4 + 1


def widen_words(q: Query, sq, as_of: dt.date | None = None) -> str:
    """Extra words for one corrective re-search (deterministic): the firm's metric definition entry
    (quote, includes, the phrases its looked_in names as full-text searches) for a registered
    metric, and adjacent periods as words (with a window: the quarter before its start and the
    quarter of its end; a series without a window: the four quarters before the as-of date). Config
    synonyms of these words are added by fts itself. The SQL window is never widened."""
    words: list[str] = []
    entry = metric_definition(sq.entity, sq.aspect.metric)
    if entry:
        words.append(str(entry.get("quote") or ""))
        words += [str(x) for x in entry.get("includes") or []]
        for place in entry.get("looked_in") or []:
            m = _FULLTEXT.search(str(place))
            if m:
                words += [w.strip() for w in m.group(1).split(",")]
    if q.window:
        y, n = _quarter(q.window[0])
        words += _quarter_words(*_shift(y, n, -1))
        words += _quarter_words(*_quarter(q.window[1]))
    elif sq.aspect.kind == "series":
        y, n = _quarter(as_of or dt.date.today())
        for k in range(1, 5):
            words += _quarter_words(*_shift(y, n, -k))
    out = " ".join(dict.fromkeys(w for w in (" ".join(x.split()) for x in words) if w))
    return out[:1200].rsplit(" ", 1)[0] if len(out) > 1200 else out


# --- running the map --------------------------------------------------------------------------

@dataclass
class CallResult:
    raw: dict | None = None
    invalid: bool = False        # the output came back but cannot be trusted
    failed_call: bool = False    # the call raised (timeout, 5xx, 401 / 429 outside ProviderStop, 400)
    skipped: bool = False        # not made: over --max-calls, or input over the model's limit
    error: str | None = None
    stop_reason: str | None = None
    usage: dict | None = None
    wall_s: float | None = None
    cached: bool = False
    bad_request: bool = False
    flags: list = field(default_factory=list)   # e.g. trailing_braces (#246 TL decision on Q24)
    finished_at: str | None = None   # #248: when this call ended, offset-aware, stamped in the worker


CallFn = Callable[[MapSpec, str, object, list], CallResult]


def provider_call(provider: str) -> CallFn:
    """The default call: the mock (0 calls) or one real provider call. An invalid output is a
    CallResult with invalid; any other error except ProviderStop is a failed call (B3)."""
    from cee.answer.llm import ModelOutputError, ProviderStop

    def call(spec: MapSpec, question: str, window, firms) -> CallResult:
        if provider == "mock":
            return CallResult(raw=mock_extract(spec))
        meta: dict = {}
        t0 = time.monotonic()
        try:
            raw = call_extract(question, spec, provider, window, firms, meta=meta)
        except ProviderStop:
            raise
        except ModelOutputError as e:
            return CallResult(invalid=True, error=str(e), stop_reason=e.stop_reason, usage=e.usage,
                              wall_s=round(time.monotonic() - t0, 2))
        except Exception as e:   # B3: the call's cells become failed; the round goes on
            return CallResult(failed_call=True, error=f"{type(e).__name__}: {e}",
                              bad_request=getattr(e, "status_code", None) == 400,
                              wall_s=round(time.monotonic() - t0, 2))
        return CallResult(raw=raw, stop_reason=meta.get("stop_reason"), usage=meta.get("usage"),
                          wall_s=round(time.monotonic() - t0, 2), flags=list(meta.get("parse_flags") or []))

    return call


ARGUMENT_ERRORS = ("Map arguments are not a JSON object", "Map output is not JSON")


def recheck_invalid(saved: dict, provider: str) -> CallResult | None:
    """#246 TL decision (Q24): a saved invalid map record whose arguments failed only to parse is
    parsed again with llm.loads_object (0 calls). A complete object followed only by stray closing
    braces is accepted with the flags trailing_braces and rechecked, then validated like any output;
    anything else stays invalid (None)."""
    from cee.answer import llm
    payload, error = saved.get("raw_payload"), str(saved.get("error") or "")
    if saved.get("failed_call") or not isinstance(payload, str) or not error.startswith(ARGUMENT_ERRORS):
        return None
    flags: list = []
    try:
        raw = llm.loads_object(payload, flags)
        validate_output(raw, provider)
    except (TypeError, ValueError, llm.ModelOutputError):
        return None
    return CallResult(raw=raw, stop_reason=saved.get("stop_reason"), usage=saved.get("usage"), cached=True,
                      flags=[*flags, "rechecked"])


def input_limit(provider: str) -> int | None:
    from cee.answer import llm
    window = llm.CONTEXT_WINDOW.get(provider)
    return None if window is None else window - extract_max_tokens(provider)


def run_round(specs: list[MapSpec], call: CallFn, question: str, window, firms, concurrency: int,
              allow: Callable[[MapSpec], bool] | None = None, provider: str = "mock") -> list[CallResult]:
    """One round in parallel; results in spec order. Specs over the input limit or refused by
    `allow` (the eval's --max-calls reservation, made here in the calling thread) are skipped.
    A ProviderStop cancels the calls not yet started, lets running ones finish, then propagates."""
    from cee.answer.llm import ProviderStop
    results: list[CallResult | None] = [None] * len(specs)
    todo = []
    limit = input_limit(provider) if provider != "mock" else None
    for i, s in enumerate(specs):
        if limit is not None and input_tokens(question, s, window, firms) > limit:
            results[i] = CallResult(skipped=True, error="input over the model's limit")
        else:
            ok = True if allow is None else allow(s)
            if ok is True:
                todo.append(i)
            else:   # #247: allow() returns True, or False / a reason string (e.g. the run stopped after a 400)
                results[i] = CallResult(skipped=True, error=ok if isinstance(ok, str) and ok
                                        else "not run: --max-calls reached")
    stop: Exception | None = None
    if todo:
        def timed(spec, *args) -> CallResult:
            # #248: each call's own completion time (pricing by period), not one time for the round
            r = call(spec, *args)
            if r is not None and r.finished_at is None and not r.cached:
                r.finished_at = dt.datetime.now().astimezone().isoformat()
            return r

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            futures = {ex.submit(timed, specs[i], question, window, firms): i for i in todo}
            for f in as_completed(futures):
                i = futures[f]
                try:
                    results[i] = f.result()
                except CancelledError:
                    results[i] = CallResult(skipped=True, error="cancelled after the provider stopped the run")
                except ProviderStop as e:
                    stop = stop or e
                    results[i] = CallResult(skipped=True, error=str(e))
                    for g in futures:
                        g.cancel()
    if stop is not None:
        raise stop
    return [r for r in results]   # type: ignore[misc]


def _call_log(spec: MapSpec, r: CallResult, provider: str, est: int | None = None) -> dict:
    from cee.retrieve.planner import model_for
    return {"id": spec.id, "round": spec.round, "entity": spec.entity, "cells": spec.cell_ids,
            "chunk_ids": [h.chunk_id for h in spec.hits], "provider": provider,
            "model": "mock" if provider == "mock" else model_for(provider, "map"), "version": EXTRACT_VERSION,
            "stop_reason": r.stop_reason, "usage": r.usage, "wall_s": r.wall_s, "error": r.error,
            "invalid": r.invalid, "failed_call": r.failed_call, "skipped": r.skipped, "cached": r.cached,
            "bad_request": r.bad_request, "flags": list(r.flags), "finished_at": r.finished_at,
            "passages": len(spec.hits), "input_tokens_est": est}   # #247 part 2: per-call size before the run


def _cells_of(spec: MapSpec, r: CallResult, by_id: dict[str, Hit], source: str) -> list[Cell]:
    if r.raw is not None and not (r.invalid or r.failed_call or r.skipped):
        try:
            return parse_output(r.raw, spec, by_id, source)
        except (ValueError, TypeError) as e:   # a saved record that no longer validates
            return failed_cells(spec, f"Map output is not a valid extraction: {e}")
    return failed_cells(spec, r.error or "no output")


def eligible_for_research(cell: Cell, aspect) -> bool:
    return (cell.role != "research" and cell.label != "failed" and cell.effective_label == "not_found"
            and aspect.kind != "comparison")


def run_map(q: Query, plan, hits: list[Hit], provider: str | None = None, call: CallFn | None = None,
            concurrency: int | None = None, search_fn=None, as_of: dt.date | None = None,
            allow: Callable[[MapSpec], bool] | None = None, sources=None,
            on_research: Callable[[], None] | None = None) -> EvidenceMatrix:
    """The map step: round 1, corrective re-search, round 2, then the code rules (matrix.finish).
    `on_research` (#248, the app's progress): called once, after round 1 and before the corrective
    re-search, so the trace can show round 1 done while the re-search runs."""
    from cee.retrieve import planner
    provider = provider or settings().llm_provider
    call = call or provider_call(provider)
    concurrency = concurrency or settings().map_concurrency
    window = query_window(q)
    firms = [e for e, _ in planner.firm_scope(q) if e]
    by_id = {h.chunk_id: h for h in hits}
    specs, code_cells = map_specs(q, plan, hits)
    results = run_round(specs, call, q.question, window, firms, concurrency, allow, provider)
    cells: dict[str, Cell] = {c.id: c for c in code_cells}
    calls = []
    for spec, r in zip(specs, results):
        calls.append(_call_log(spec, r, provider, input_tokens(q.question, spec, window, firms)))
        for c in _cells_of(spec, r, by_id, "mock" if provider == "mock" else "model"):
            cells[c.id] = c
    order = [sq.id for sq in plan.subquestions] + [f"{a.id}.research" for a in plan.aspects]
    aspects = {a.id: a for a in plan.aspects}
    # Corrective re-search (CRAG): once per not_found sub-question, every used chunk excluded.
    research_log: list[dict] = []
    new_hits: dict[str, list[Hit]] = {}
    if on_research is not None:
        on_research()
    if fts.searchable(q) and fts.budget_tokens(q) is not None:
        used = {h.chunk_id for h in hits}
        for sq in plan.subquestions:
            cell = cells.get(sq.id)
            if cell is None or not eligible_for_research(cell, aspects[cell.aspect_id]):
                continue
            words = widen_words(q, sq, as_of)
            found = planner.corrective_search(q, plan, sq.id, words, exclude=set(used), search_fn=search_fn)
            used |= {h.chunk_id for h in found}
            cell.researched, cell.research_hits = True, len(found)
            research_log.append({"id": sq.id, "words": words, "hits": len(found),
                                 "chunk_ids": [h.chunk_id for h in found]})
            if found:
                new_hits[sq.id] = found
    # Round 2: one re-extraction per firm over only the re-searched sub-questions with new chunks.
    remaps: list[MapSpec] = []
    groups: dict[str, list] = {}
    for sq in plan.subquestions:
        if sq.id in new_hits:
            groups.setdefault(_row_key(sq.entity), []).append(sq)
    for key, sqs in groups.items():
        own = {sq.id: new_hits[sq.id] for sq in sqs}
        remaps.append(MapSpec(f"remap.{key}", 2, sqs[0].entity, False,
                              [CellSpec(sq.id, sq.entity, sq.aspect, sq.role, sq.text) for sq in sqs],
                              own, {sq.id: {h.chunk_id for h in own[sq.id]} for sq in sqs}))
    extra = []
    for sq_id, hs in new_hits.items():   # #247 B1: corrective hits keep their sub-question, origin tagged
        for h in hs:
            if h.chunk_id not in by_id and all(h.chunk_id != e.chunk_id for e in extra):
                extra.append(replace(h, part_id=h.part_id or sq_id, origin="corrective"))
    by_id.update({h.chunk_id: h for h in extra})
    if remaps:
        results2 = run_round(remaps, call, q.question, window, firms, concurrency, allow, provider)
        for spec, r in zip(remaps, results2):
            calls.append(_call_log(spec, r, provider, input_tokens(q.question, spec, window, firms)))
            for c in _cells_of(spec, r, by_id, "reextract"):
                old = cells[c.id]
                c.first = asdict(old)
                c.researched, c.research_hits = True, old.research_hits
                cells[c.id] = c
    m = EvidenceMatrix(q.question, rows=[], aspects=list(plan.aspects),
                       cells={k: cells[k] for k in order if k in cells}, calls=calls, research=research_log,
                       version=EXTRACT_VERSION)
    rows = []
    for c in m.cells.values():
        key = "research" if c.role == "research" else _row_key(c.entity)
        if key not in rows:
            rows.append(key)
    m.rows = rows
    m.hits, m.corrective = dict(by_id), list(extra)
    # #247 part 2: each sub-question's retrieved set (its pool, its hits, its re-search hits), for the
    # population rule "a population source counts only when it is in the input cell's pool"
    pools = getattr(plan, "pools", {}) or {}
    m.pools = {sq.id: set(pools.get(sq.id, set())) | {h.chunk_id for h in hits if h.part_id == sq.id}
               | {h.chunk_id for h in new_hits.get(sq.id, [])} for sq in plan.subquestions}
    return finish(m, q, hits + extra, sources, as_of=as_of)
