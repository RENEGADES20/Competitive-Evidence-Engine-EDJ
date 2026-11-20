"""Reduce step (#247, ADR-021 rules 0-5; plans/0247-reduce.md): one synthesis call writes the cited
Answer from the evidence matrix only, for the behavior code decided.

- Input: the matrix rendered (cells, items with their valid chunk ids, flags in words, derived cells
  with a formula without ids, comparability marks, registered definitions, the code gaps and caveats,
  one source line per citable chunk). No raw passages.
- Output: the existing Answer schema, strict, with enums: `behavior` = the one decided value,
  `part_id` = the matrix's cell and aspect ids, `chunk_ids` = the matrix's citable ids (never empty: an
  empty citable set is answered by code with no call).
- Code then sets the behavior, checks citations against the matrix only (`outside_matrix`), accepts
  a computed figure only with both cited inputs (`computed`), flags rule-3 misplacements, requires a
  comparison claim per comparison aspect, a why-line per recency item, re-sorts newest first in a
  question with its own window, places the matrix gaps (deduped) and caveats, and checks every part.
- Refuse, a forecast request, an undecided matrix (`incomplete`) and an empty citable set are built
  by code with 0 calls; the mock reduce is deterministic (0 calls).
"""
from __future__ import annotations

import copy
import json
import time

from cee.answer import prompt as P
from cee.answer.matrix import EvidenceMatrix, holds, row_name
from cee.answer.schema import Adjacent, Answer, Gap, llm_output_schema
from cee.config import settings

REDUCE_VERSION = P.REDUCE_VERSION
TOOL = "submit_answer"
CALLING = ("answer", "answer_with_boundary", "gap_with_adjacent")
# Enum limits (review note 5): OpenAI structured outputs allow at most 1000 enum values across the
# schema and 15,000 characters in total for an enum with more than 250 values. DeepSeek's tool-call
# guide (read 2026-11-20) states no numeric limit; Anthropic's are not stated for enums either. The
# OpenAI numbers are applied to every provider (conservative); over them a field falls back to a plain
# string (TL D7) and the code check is the guard there.
ENUM_TOTAL_MAX, ENUM_BIG, ENUM_BIG_CHARS = 1000, 250, 15000
FLAG_WORDS = {"number_not_found": "figure not found in its passage: do not state this figure",
              "quote_not_found": "quote not verbatim: never put it in quotation marks",
              "period_unparsed": "period not stated in a usable form",
              "unmatched_citation": "some cited ids were rejected (not shown)"}


# --- which answers call the model ------------------------------------------------------------------

def citable(m: EvidenceMatrix) -> list[str]:
    return m.chunk_ids()


def needs_call(m: EvidenceMatrix) -> bool:
    """A reduce call only for answer / answer_with_boundary / gap_with_adjacent with a citable item."""
    return m.behavior in CALLING and bool(citable(m))


def own_window(query):
    """The question's own time window (a SQL filter on publication date), not the Ask page date filter:
    only it triggers the why-line check and the newest-first re-sort (review note 4)."""
    return getattr(query, "window", None)


def _recency_aspects(m: EvidenceMatrix) -> set[str]:
    return {a.id for a in m.aspects if a.kind == "recency"}


def _proxy(m: EvidenceMatrix, aspect_id: str) -> bool:
    return bool(getattr(m.aspect(aspect_id), "proxy", False))


# --- input rendering ---------------------------------------------------------------------------------

def source_line(h) -> str:
    """The chunk's source line without its text (dates, doc type, segment, section, page)."""
    seg = f", segment {h.segment}" if h.segment else ""
    dated = (f"period n/a, page content as of {h.published_at} (undated web page)"
             if getattr(h, "date_basis", "source") == "retrieved"
             else f"period {h.period_end or 'n/a'}, published {h.published_at}")
    where = f"{h.entity_id or 'Research'} {h.doc_type}{seg}, {dated}, {h.section or ''}"
    if h.page:
        where += f", p.{h.page}"
    return f'<source id="{h.chunk_id}" from="{where}"/>'


def _q(text: str) -> str:
    return " ".join(str(text or "").split()).replace('"', "'")


def _item_line(n: int, i) -> str:
    parts = [_q(i.text)]
    for k in ("value", "unit", "period", "scope"):
        v = getattr(i, k)
        if v:
            parts.append(f"{k} {_q(v)}")
    if i.definition:
        parts.append(f'definition "{_q(i.definition)}"')
    if i.quote:
        parts.append(f'quote "{_q(i.quote)}"')
    parts.append("cite " + ", ".join(i.chunk_ids))
    flags = [FLAG_WORDS[f] for f in i.flags if f in FLAG_WORDS]
    return f"    item {n + 1}: " + " | ".join(parts) + (f" [{'; '.join(flags)}]" if flags else "")


def _cell_head(m: EvidenceMatrix, c) -> str:
    a = m.aspect(c.aspect_id)
    firm = row_name(c)
    d = c.derivation or {}
    if c.label == "derived" and d.get("ok"):
        unver = "; definition unverified" if "definition_unverified" in c.flags else ""
        return (f"  {c.id} {firm}: derived (computed by code): {d.get('formula_text') or d.get('value_text')}; "
                f"period {d.get('period') or 'n/a'}; scope {d.get('scope') or 'whole firm'}{unver}; "
                f"cite {', '.join(d.get('input_chunk_ids') or [])}")
    label = c.effective_label if c.label != "failed" else "failed"
    if label == "fact" and getattr(a, "proxy", False):
        head = "stand-in figure (adjacent only)"
    elif label == "fact":
        head = "fact"
    elif label == "different_quantity":
        head = f"different quantity (adjacent only): differs because '{_q(c.differs_because)}'"
    else:
        head = f"{label.replace('_', ' ')} (code gap)"
    if d and d.get("ok") is False:
        head += f"; a computation was proposed and rejected by code: {d.get('why')}"
    return f"  {c.id} {firm}: {head}"


def reduce_message(question: str, m: EvidenceMatrix, query=None) -> str:
    from cee.answer.matrix import metric_definition
    lines = [f"Question: {question}",
             f"Behavior (decided by code; write the answer for it): {m.behavior}",
             f"  Why: {m.behavior_reason}"]
    w = own_window(query)
    if w:
        lines.append(f"Time window: {w[0]} to {w[1]} (only passages published in it were searched). "
                     "Order newest first.")
    dr = getattr(query, "date_range", None)
    if dr and not w:
        lines.append(f"Date filter: {dr[0]} to {dr[1]} (only passages published in it were searched).")
    firms = [r for r in m.rows if r not in ("research", "all")]
    if firms:
        lines.append("Firms (row order): " + ", ".join(f"{row_name(f)} ({f})" for f in firms))
    lines += ["", "Aspects (their ids are part ids for claims that span firms):"]
    for a in m.aspects:
        tags = [a.kind] + ([f"metric {a.metric}"] if a.metric else [])
        if getattr(a, "proxy", False):
            tags.append("proxy: a stand-in figure, adjacent only")
        note = {"comparison": " -> needs exactly one comparison claim, part_id " + a.id,
                "recency": " -> every item needs a why-line"}.get(a.kind, "")
        lines.append(f"- {a.id} [{', '.join(tags)}]: {_q(a.text)}{note}")
    lines += ["", "Evidence matrix, aspect by aspect (a cell id is the part_id of what you write from it):"]
    for a in m.aspects:
        lines.append(f"Aspect {a.id}: {_q(a.text)}")
        mk = m.marks.get(a.id)
        if mk and mk.status == "same_basis":
            lines.append(f"  Comparability (code): same_basis; shared periods {', '.join(mk.shared_periods) or 'none'}")
        elif mk and mk.status == "different_basis":
            lines.append("  Comparability (code): different_basis: the firms define it differently; "
                         "not compared or combined (caveat added by code)")
        elif mk and mk.status == "unverified":
            lines.append("  Comparability (code): unverified: not in the metric definitions file; "
                         "never compared across firms")
        if a.metric:
            for f in firms:
                d = metric_definition(f, a.metric)
                if d and d.get("quote"):
                    lines.append(f"  Registered definition, {row_name(f)}: \"{_q(d['quote'])[:160]}\" "
                                 f"({d.get('chunk_id', '')}; context, cite only if under Sources)")
        for c in m.cells.values():
            if c.aspect_id != a.id:
                continue
            lines.append(_cell_head(m, c))
            for n, i in enumerate(c.items):
                if i.counts:
                    lines.append(_item_line(n, i))
    lines += ["", "Gaps added by code (do not repeat them):"]
    lines += [f"- [{g['id']}] {g['what']}" for g in m.gaps] or ["- none"]
    lines += ["", "Caveats added by code (do not repeat them):"]
    lines += [f"- {c}" for c in m.caveats] or ["- none"]
    lines += ["", "Sources (every chunk id you may cite; cite no other):"]
    for cid in citable(m):
        h = m.hits.get(cid)
        lines.append(source_line(h) if h is not None else f'<source id="{cid}"/>')
    return "\n".join(lines)


# --- output schema ---------------------------------------------------------------------------------

def part_ids(m: EvidenceMatrix) -> list[str]:
    return [*m.cells.keys(), *[a.id for a in m.aspects], ""]


def reduce_schema(m: EvidenceMatrix) -> tuple[dict, list[str]]:
    """(schema, fields that fell back to plain strings). Strict on every provider (every property
    required, no extra properties, no array limits), with enums from the matrix."""
    s = copy.deepcopy(llm_output_schema())
    ids, parts = citable(m), part_ids(m)
    behavior = [m.behavior] if m.behavior in CALLING else list(CALLING)
    fallback: list[str] = []
    use_ids = bool(ids)   # never an empty enum (B2)
    use_parts = True

    def total(ids_on: bool, parts_on: bool) -> int:
        return len(behavior) + (2 * len(ids) if ids_on else 0) + (3 * len(parts) if parts_on else 0)

    def too_long(values: list[str]) -> bool:
        return len(values) > ENUM_BIG and sum(len(v) for v in values) > ENUM_BIG_CHARS

    if use_ids and (too_long(ids) or total(True, True) > ENUM_TOTAL_MAX):
        use_ids = False
        fallback.append("chunk_ids")
    if too_long(parts) or total(use_ids, True) > ENUM_TOTAL_MAX:
        use_parts = False
        fallback.append("part_id")
    s["properties"]["behavior"]["enum"] = behavior
    for key in ("claims", "adjacent", "gaps"):
        props = s["properties"][key]["items"]["properties"]
        if use_parts:
            props["part_id"] = {"type": "string", "enum": parts}
        if key != "gaps" and use_ids:
            props["chunk_ids"] = {"type": "array", "items": {"type": "string", "enum": ids}}
    return s, fallback


def enum_values(schema: dict) -> int:
    n = 0
    if isinstance(schema, dict):
        n += len(schema.get("enum") or [])
        n += sum(enum_values(v) for v in schema.values() if isinstance(v, (dict, list)))
    elif isinstance(schema, list):
        n += sum(enum_values(v) for v in schema)
    return n


def max_tokens(provider: str) -> int:
    from cee.answer import llm
    return llm.answer_max_tokens(provider)


def requests(question: str, m: EvidenceMatrix, query, provider: str) -> dict:
    """The provider request (and its parts, for the eval's cache key)."""
    from cee.answer import llm
    schema, _ = reduce_schema(m)
    user = reduce_message(question, m, query)
    if provider == "anthropic":
        return {"model": settings().llm_model, "max_tokens": max_tokens(provider), "system": P.SYSTEM_PROMPT_V5,
                "tools": [{"name": TOOL, "description": "Submit the cited answer.", "strict": True,
                           "input_schema": schema}],
                "tool_choice": {"type": "auto"}, "messages": [{"role": "user", "content": user}]}
    if provider == "openai":
        return {"model": settings().openai_model,
                "messages": [{"role": "system", "content": P.SYSTEM_PROMPT_V5 + "\nReturn JSON matching the schema."},
                             {"role": "user", "content": user}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "answer", "strict": True, "schema": schema}}}
    if provider == "deepseek":
        return llm.deepseek_tool_request(TOOL, "Submit the cited answer.", schema, P.SYSTEM_PROMPT_V5, user,
                                         max_tokens(provider))
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def input_tokens(question: str, m: EvidenceMatrix, query=None) -> int:
    schema, _ = reduce_schema(m)
    return round((len(P.SYSTEM_PROMPT_V5) + len(json.dumps(schema)) + len(reduce_message(question, m, query))) / 4)


def input_limit(provider: str) -> int | None:
    from cee.answer import llm
    window = llm.CONTEXT_WINDOW.get(provider)
    return None if window is None else window - max_tokens(provider)


# --- the call ------------------------------------------------------------------------------------

def call_reduce(question: str, m: EvidenceMatrix, query, provider: str, client=None,
                meta: dict | None = None) -> dict:
    """One reduce call; the raw tool input (a dict), or ModelOutputError when the output cannot be
    trusted (no tool call, cut at the cap, refusal, a DeepSeek finish_reason other than tool_calls /
    stop, not JSON, not a valid Answer, empty). `meta` gets stop_reason, usage, parse_flags and
    (deepseek) reasoning_content. ProviderStop and any other exception propagate. No trim: an input
    over the model's limit is not sent (RuntimeError)."""
    from cee.answer import llm
    meta = {} if meta is None else meta
    limit = input_limit(provider)
    if limit is not None and input_tokens(question, m, query) > limit:
        raise RuntimeError("input over the model's limit: the reduce call was not sent")
    req = requests(question, m, query, provider)
    if provider == "anthropic":
        client = client or llm.anthropic_client()
        resp = client.messages.create(**req)
        stop = getattr(resp, "stop_reason", None)
        usage = {**llm._usage(resp, "input_tokens", "output_tokens"),
                 "blocks": [getattr(b, "type", "?") for b in resp.content]}
        meta["stop_reason"], meta["usage"] = stop, usage
        blocks = [llm._block_dict(b) for b in resp.content]
        block = next((b for b in resp.content if b.type == "tool_use" and b.name == TOOL), None)
        if block is None:
            raise llm.ModelOutputError(f"Model did not call {TOOL} (stop_reason={stop or '?'})", blocks, provider,
                                       stop, usage)
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       blocks, provider, stop, usage)
        if stop == llm.REFUSAL:
            raise llm.ModelOutputError("Model output stopped by refusal (stop_reason refusal)", blocks, provider,
                                       stop, usage)
        raw = block.input
    elif provider == "openai":
        client = client or llm.openai_client()
        resp = client.chat.completions.create(**req)
        content = resp.choices[0].message.content
        stop = getattr(resp.choices[0], "finish_reason", None)
        usage = llm._usage(resp, "prompt_tokens", "completion_tokens")
        meta["stop_reason"], meta["usage"] = stop, usage
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       content, provider, stop, usage)
        flags: list = []
        try:
            raw = llm.loads_object(content, flags)
        except (TypeError, ValueError) as e:
            raise llm.ModelOutputError(f"Model output is not JSON: {e}", content, provider, stop, usage) from e
        if flags:
            meta["parse_flags"] = flags
    elif provider == "deepseek":
        client = client or llm.deepseek_client()
        resp = llm.deepseek_create(client, req)
        call, stop, usage, payload = llm.deepseek_tool_call(resp, TOOL)
        msg = payload if isinstance(payload, dict) else {}
        meta["stop_reason"], meta["usage"] = stop, usage
        meta["reasoning_content"] = msg.get("reasoning_content")
        if stop in llm.CUT_REASONS:
            raise llm.ModelOutputError(f"Model output cut at max_tokens ({usage['output_tokens']} output tokens)",
                                       payload, provider, stop, usage)
        if stop not in llm.DEEPSEEK_OK:
            raise llm.ModelOutputError(f"Model output stopped by finish_reason {stop}", payload, provider, stop, usage)
        if call is None:
            raise llm.ModelOutputError(f"Model did not call {TOOL} (finish_reason={stop or '?'})", payload,
                                       provider, stop, usage)
        flags = []
        try:
            raw = llm.deepseek_arguments(call, flags)
        except (TypeError, ValueError) as e:
            raise llm.ModelOutputError(f"Model arguments are not a JSON object: {e}", call.function.arguments,
                                       provider, stop, usage) from e
        if flags:
            meta["parse_flags"] = flags
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
    to_answer(raw, provider, meta)   # validates (ModelOutputError when not a valid, non-empty Answer)
    return raw


ARGUMENT_ERRORS = ("Model arguments are not a JSON object", "Model output is not JSON")


def to_answer(raw, provider: str, meta: dict | None = None) -> Answer:
    """A raw tool input as a checked Answer (llm.check_output), else ModelOutputError."""
    from cee.answer import llm
    meta = meta or {}
    stop, usage = meta.get("stop_reason"), dict(meta.get("usage") or {})
    if meta.get("parse_flags"):
        usage["parse_flags"] = list(meta["parse_flags"])
    try:
        answer = Answer(**raw) if isinstance(raw, dict) else None
    except (ValueError, TypeError) as e:
        raise llm.ModelOutputError(f"Model output is not a valid Answer: {e}", raw, provider, stop, usage) from e
    if answer is None:
        raise llm.ModelOutputError("Model output is not a JSON object", raw, provider, stop, usage)
    answer.llm_called = provider != "mock"
    answer.stop_reason, answer.usage = stop or "", usage
    if meta.get("reasoning_content") is not None:
        answer._provider_payload = {"reasoning_content": meta.get("reasoning_content")}
    return llm.check_output(answer, raw, provider)


# --- mock and code-built answers -------------------------------------------------------------------

def _firm_prefix(m: EvidenceMatrix, c) -> str:
    firms = [r for r in m.rows if r not in ("research", "all")]
    return f"{row_name(c)}: " if len(firms) > 1 or c.role == "research" else ""


def _why(m: EvidenceMatrix, query, aspect_id: str) -> str:
    return (" " + P.WHY_UNSAID) if (own_window(query) or aspect_id in _recency_aspects(m)) else ""


def _adjacent_items(m: EvidenceMatrix, query=None) -> list[dict]:
    out = []
    for c in m.cells.values():
        a = m.aspect(c.aspect_id)
        if a.kind == "comparison":
            continue
        if c.effective_label == "different_quantity" or (getattr(a, "proxy", False) and holds(c)):
            i = c.counting_items[0] if c.counting_items else None
            if i is None:
                continue
            out.append({"text": _firm_prefix(m, c) + _q(i.text) + _why(m, query, a.id), "chunk_ids": list(i.chunk_ids),
                        "part_id": c.id, "differs_because": _q(c.differs_because) or "a different quantity"})
    return out


def mock_reduce(m: EvidenceMatrix, query=None) -> dict:
    """Deterministic, 0 calls: per aspect and row, a holding fact cell -> one claim from its first
    counting item; a derived cell -> one claim with the formula (no ids); a different-quantity or proxy
    cell -> one adjacent item; a comparison aspect -> one claim citing its holding cells (else none, so
    the code gap fires); recency items end with the why-line. Behavior = the matrix's."""
    time.sleep(settings().mock_delay_s)
    claims = []
    for a in m.aspects:
        cells = [c for c in m.cells.values() if c.aspect_id == a.id]
        if a.kind == "comparison":
            ids = list(dict.fromkeys(x for c in cells if holds(c) for i in c.counting_items for x in i.chunk_ids))
            if ids:
                mk = m.marks.get(a.id)
                claims.append({"text": f"{_q(a.text).rstrip('.')}: compared only on the same basis; code marks it "
                                       f"{mk.status if mk else 'none'}.", "chunk_ids": ids, "part_id": a.id})
            continue
        if getattr(a, "proxy", False):
            continue
        for c in cells:
            if not holds(c):
                continue
            d = c.derivation or {}
            if c.label == "derived" and d.get("ok"):
                claims.append({"text": f"{_firm_prefix(m, c)}{_q(a.text).rstrip('.')}: {d.get('formula_text')}.",
                               "chunk_ids": list(d.get("input_chunk_ids") or []), "part_id": c.id})
                continue
            i = c.counting_items[0]
            claims.append({"text": _firm_prefix(m, c) + _q(i.text) + _why(m, query, a.id),
                           "chunk_ids": list(i.chunk_ids), "part_id": c.id})
    return {"answerable": m.behavior in ("answer", "answer_with_boundary"), "behavior": m.behavior,
            "claims": claims, "adjacent": _adjacent_items(m, query), "gaps": []}


def code_answer(m: EvidenceMatrix, query=None) -> Answer:
    """0 calls: refuse (1c), a forecast request, an undecided matrix (`incomplete`), and any matrix with
    an empty citable set (in practice a normative question with no fact: answer_with_boundary, the
    hand-off added by code). The matrix gaps, caveats and checks are added by finish_answer."""
    if m.behavior == "refuse" and m.behavior_reason.startswith("1e"):
        return Answer(answerable=False, behavior="refuse", gaps=[Gap(what=P.FORECAST_REFUSAL)])
    if m.behavior == "refuse":
        return Answer(answerable=False, behavior="refuse")
    if m.behavior is None:
        return Answer(answerable=False, behavior="incomplete", adjacent=[Adjacent(**x) for x in _adjacent_items(m, query)],
                      incomplete_note=m.incomplete_note or "")
    return Answer(answerable=False, behavior=m.behavior, adjacent=[Adjacent(**x) for x in _adjacent_items(m, query)])


# --- code after the reduce -------------------------------------------------------------------------

def _hits_for(m: EvidenceMatrix, hits) -> dict:
    out = {h.chunk_id: h for h in hits or []}
    out.update(m.hits or {})
    return out


def derived_values(m: EvidenceMatrix) -> list[tuple[float, set[str]]]:
    return [(c.derivation["value"], set(c.derivation.get("input_chunk_ids") or []))
            for c in m.cells.values() if c.label == "derived" and (c.derivation or {}).get("ok")]


def check_adjacent(answer: Answer, m: EvidenceMatrix) -> None:
    """Rule 3: an adjacent item on a holding cell of a non-proxy aspect -> adjacent_is_fact; a claim on
    a different-quantity or proxy cell -> claim_from_adjacent (flagged, never moved)."""
    for x in answer.adjacent:
        c = m.cells.get(x.part_id)
        if c is not None and holds(c) and not _proxy(m, c.aspect_id) and "adjacent_is_fact" not in x.flags:
            x.flags.append("adjacent_is_fact")
    for x in answer.claims:
        c = m.cells.get(x.part_id)
        if c is not None and (c.effective_label == "different_quantity" or _proxy(m, c.aspect_id)) \
                and "claim_from_adjacent" not in x.flags:
            x.flags.append("claim_from_adjacent")


def _aspect_ids(m: EvidenceMatrix, aspect_id: str) -> set[str]:
    return {aspect_id} | {c.id for c in m.cells.values() if c.aspect_id == aspect_id}


def check_comparisons(answer: Answer, m: EvidenceMatrix) -> list[str]:
    """Rule 4: each comparison aspect needs a claim (part_id the aspect or one of its cells) citing a
    matrix chunk; else the gap COMPARISON_MISSING, flag comparison_missing. Returns the missing ids."""
    from cee.answer.matrix import _aspect_text
    ids_ok = set(citable(m))
    missing = []
    for a in m.aspects:
        if a.kind != "comparison":
            continue
        own = _aspect_ids(m, a.id)
        if any(c.part_id in own and any(k in ids_ok for k in c.chunk_ids) for c in answer.claims):
            continue
        missing.append(a.id)
        answer.gaps.append(Gap(what=P.COMPARISON_MISSING.format(aspect=_aspect_text(a)), part_id=a.id,
                               flags=["comparison_missing"]))
    return missing


def check_why_lines(answer: Answer, m: EvidenceMatrix, query) -> int:
    """Rule 5: with the question's own window every item, else every item of a recency aspect, needs
    "Why it might matter: " and text after it; missing -> why_line_missing. Returns the count."""
    rec = _recency_aspects(m)
    every = bool(own_window(query))
    n = 0
    for x in [*answer.claims, *answer.adjacent]:
        if x.text.strip() == P.BOUNDARY_HANDOFF:
            continue
        c = m.cells.get(x.part_id)
        aspect = c.aspect_id if c is not None else x.part_id
        if not (every or aspect in rec):
            continue
        tail = x.text.split(P.WHY_LINE, 1)
        if len(tail) < 2 or not tail[1].strip():
            if "why_line_missing" not in x.flags:
                x.flags.append("why_line_missing")
            n += 1
    return n


def order_newest_first(answer: Answer, m: EvidenceMatrix, query, by_id: dict) -> int:
    """D4: with the question's own window or a recency aspect, claims and adjacent items are re-sorted
    newest first by the latest published date of their cited documents (stable; the hand-off last).
    Returns how many items moved."""
    if not (own_window(query) or _recency_aspects(m)):
        return 0

    def key(x):
        dates = [str(by_id[c].published_at) for c in x.chunk_ids if c in by_id and by_id[c].published_at]
        return max(dates) if dates else ""

    moved = 0
    for field in ("claims", "adjacent"):
        items = getattr(answer, field)
        handoff = [x for x in items if x.text.strip() == P.BOUNDARY_HANDOFF]
        rest = [x for x in items if x.text.strip() != P.BOUNDARY_HANDOFF]
        new = sorted(rest, key=key, reverse=True) + handoff
        moved += sum(a is not b for a, b in zip(items, new))
        setattr(answer, field, new)
    return moved


def _gap_norm(text: str) -> str:
    return " ".join(str(text or "").lower().split()).rstrip(".")


def place_gaps(answer: Answer, m: EvidenceMatrix) -> int:
    """The matrix gaps after the model's; a model gap repeating a code gap (same text, or the same
    "<Firm> - <aspect>:" head for the same part) is merged into it: the code gap kept with the flag
    model_also_named, the model's text in claim_text (review note 9). Returns the merged count."""
    model = list(answer.gaps)
    code = [Gap(what=g["what"], suggested_source=g.get("suggested_source", ""), part_id=g["id"],
                flags=[f"matrix_{g.get('label', 'gap')}"]) for g in m.gaps]
    kept, merged = [], 0
    for g in model:
        twin = next((c for c in code if _gap_norm(c.what) == _gap_norm(g.what)
                     or (c.part_id == g.part_id and ":" in c.what
                         and _gap_norm(g.what).startswith(_gap_norm(c.what.split(":", 1)[0]) + ":"))), None)
        if twin is not None:
            if "model_also_named" not in twin.flags:
                twin.flags.append("model_also_named")
            twin.claim_text = "\n".join(t for t in (twin.claim_text, g.what) if t)
            merged += 1
        else:
            kept.append(g)
    answer.gaps = kept + code
    return merged


def finish_answer(answer: Answer, m: EvidenceMatrix, query, plan, hits, question: str,
                  code_built: bool = False) -> tuple[Answer, dict]:
    """Every code step after the reduce (plan section 4), in order. Returns (answer, info for the log)."""
    from cee.answer.validate import (check_citations, check_parts, coverage_note, fill_suggested_sources,
                                     insert_caveats)
    info: dict = {"version": REDUCE_VERSION, "code_built": code_built, "model_behavior": answer.behavior}
    decided = m.behavior if m.behavior is not None else "incomplete"
    answer.behavior = decided
    answer.answerable = decided in ("answer", "answer_with_boundary") and bool(citable(m))
    answer.incomplete_note = m.incomplete_note or ""
    by_id = _hits_for(m, hits)
    allowed = [by_id[c] for c in citable(m) if c in by_id]
    answer = check_citations(answer, allowed, derived=derived_values(m))
    info["behavior_rejudged"] = answer.behavior != decided
    ok_ids = set(citable(m))
    outside = 0
    for x in [*answer.claims, *answer.adjacent]:
        if any(c not in ok_ids for c in x.chunk_ids):
            outside += 1
            if "outside_matrix" not in x.flags:
                x.flags.append("outside_matrix")
    info["outside_matrix"] = outside
    check_adjacent(answer, m)
    info["comparison_missing"] = check_comparisons(answer, m)
    info["why_line_missing"] = check_why_lines(answer, m, query)
    info["reordered"] = order_newest_first(answer, m, query, by_id)
    if not (m.behavior == "refuse" and m.behavior_reason.startswith("1e")):
        info["gaps_merged"] = place_gaps(answer, m)
    answer.caveats = list(dict.fromkeys([*answer.caveats, *m.caveats]))
    union = list(by_id.values())
    answer = check_parts(answer, plan, union, question, matrix=m)
    answer = insert_caveats(answer, query, union)
    answer = fill_suggested_sources(answer, query)
    answer.coverage_note = coverage_note(query, list(hits or []))
    flags: dict[str, int] = {}
    for x in [*answer.claims, *answer.adjacent, *answer.gaps]:
        for f in x.flags:
            flags[f] = flags.get(f, 0) + 1
    info["flags"] = flags
    info["part_gaps"] = sum("part_gap" in g.flags for g in answer.gaps)
    info["stop_reason"], info["usage"] = answer.stop_reason, answer.usage
    return answer, info


def raw_answer(m: EvidenceMatrix, query, provider: str) -> Answer:
    """The mock reduce as a checked Answer (0 calls)."""
    return to_answer(mock_reduce(m, query), "mock")
