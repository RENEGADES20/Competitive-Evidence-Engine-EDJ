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
import re
import time

from cee.answer import prompt as P
from cee.answer.matrix import EvidenceMatrix, holds, row_name
from cee.answer.schema import Adjacent, Answer, Gap, llm_output_schema
from cee.config import settings

REDUCE_VERSION = P.REDUCE_VERSION   # v5.2; the version a call uses is prompt_version() (REDUCE_PROMPT, #275)


def prompt_version() -> str:
    """The reduce prompt version in use (REDUCE_PROMPT: v5.2 | v5.3, #275)."""
    return P.reduce_prompt()[0]


def system_prompt() -> str:
    return P.reduce_prompt()[1]


def v6() -> bool:
    """#284: prompt v6 (item refs rendered by code) is in use."""
    return prompt_version() == "v6"
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


def _item_line(n: int, i, ref: str | None = None) -> str:
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
    return f"    item {ref or n + 1}: " + " | ".join(parts) + (f" [{'; '.join(flags)}]" if flags else "")


def _cell_head(m: EvidenceMatrix, c) -> str:
    a = m.aspect(c.aspect_id)
    firm = row_name(c)
    d = c.derivation or {}
    if c.label == "derived" and d.get("ok"):
        unver = "; definition unverified" if "definition_unverified" in c.flags else ""
        ref = f"; ref {c.id}/derived" if v6() else ""   # #284
        return (f"  {c.id} {firm}: derived (computed by code): {d.get('formula_text') or d.get('value_text')}; "
                f"period {d.get('period') or 'n/a'}; scope {d.get('scope') or 'whole firm'}{unver}; "
                f"cite {', '.join(d.get('input_chunk_ids') or [])}{ref}")
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


CONTEXT_CHARS = 600   # #247 part 2: the cited passage around a recency / window item's quote
RELATED_MAX = 3       # #247 part 2 R1: related matrix items offered as cited background for a why-line


def related_items(m: EvidenceMatrix, cell, item) -> list:
    """Up to RELATED_MAX other counting items of the same row (firm, or the research row) citing other
    chunks and sharing content words with the item, most shared first (#247 part 2 R1)."""
    mine = _content(item.text)
    scored = []
    for c in m.cells.values():
        if (c.role == "research") != (cell.role == "research") or c.entity != cell.entity:
            continue
        for j in c.counting_items:
            if j is item or set(j.chunk_ids) <= set(item.chunk_ids):
                continue
            shared = len(mine & _content(j.text))
            if shared:
                scored.append((-shared, j.chunk_ids[0], j))
    out, seen = [], set()
    for _, _, j in sorted(scored, key=lambda s: (s[0], s[1])):
        key = tuple(j.chunk_ids)
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
        if len(out) == RELATED_MAX:
            break
    return out


def _flat(text) -> str:
    return " ".join(str(text or "").split())


def item_context(m: EvidenceMatrix, i) -> str:
    """The cited passage around the item's quote (up to CONTEXT_CHARS, cut at word boundaries), so the
    why-line can give what the source says about why the item matters (#247 part 2)."""
    h = next((m.hits.get(c) for c in i.chunk_ids if m.hits.get(c) is not None), None)
    if h is None:
        return ""
    text = _flat(h.text)
    if len(text) <= CONTEXT_CHARS:
        return text
    probe = _flat(i.quote)[:40]
    at = text.find(probe) if probe else -1
    start = max(0, (at if at >= 0 else 0) - CONTEXT_CHARS // 3)
    piece = text[start:start + CONTEXT_CHARS]
    if start > 0:
        piece = piece.split(" ", 1)[-1]
    if start + CONTEXT_CHARS < len(text):
        piece = piece.rsplit(" ", 1)[0]
    return ("... " if start > 0 else "") + piece + (" ..." if start + CONTEXT_CHARS < len(text) else "")


def _date_words(iso: str) -> str:
    import datetime as dt
    try:
        d = dt.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{d:%B} {d.day}, {d.year}"


def _quarter(period: str) -> str | None:
    import re
    p = str(period or "")
    m_ = re.fullmatch(r"(\d{4})-(\d{2})-\d{2}", p)
    if m_:
        return f"{m_.group(1)}Q{(int(m_.group(2)) - 1) // 3 + 1}"
    m_ = re.fullmatch(r"(\d{4})Q([1-4])", p)
    return p if m_ else None


def population_sources(m: EvidenceMatrix, d: dict) -> list[dict]:
    """One entry per distinct population source chunk of a derivation: chunk id, its own words, a
    label from its source line and, when an input's period falls in another quarter than the
    statement's valid_from (either direction), the date (TL condition 3.4)."""
    from cee.answer.validate import source_label
    out: dict[str, dict] = {}
    for p in d.get("populations") or []:
        h = m.hits.get(p["chunk_id"])
        e = out.setdefault(p["chunk_id"], {"chunk_id": p["chunk_id"], "quote": p.get("quote", ""),
                                           "label": source_label(h).rsplit(" [", 1)[0] if h else p["chunk_id"],
                                           "valid_from": p.get("valid_from", ""), "dated": False})
        if _quarter(p.get("period", "")) and _quarter(p.get("valid_from", "")) != _quarter(p.get("period", "")):
            e["dated"] = True
    return list(out.values())


def _sources_text(srcs: list[dict]) -> str:
    out = []
    for s in srcs:
        dated = f", dated {_date_words(s['valid_from'])}" if s["dated"] and s["valid_from"] else ""
        out.append(f' Population per the {s["label"]}{dated}: "{s["quote"]}"')
    return "".join(out)


def computation_proposal(c) -> bool:
    """A derivation proposal whose inputs are all cited items (so its claim can cite them)."""
    d = c.derivation or {}
    return bool(d) and bool(d.get("input_chunk_ids")) and "populations" in d and bool(
        d.get("ok") or not str(d.get("why", "")).startswith("input "))


def _why_words(why: str) -> str:
    why = str(why or "")
    if why == "populations differ":
        return "the two figures cover different populations"
    if why.startswith("population not stated: "):
        return "the population of " + why.split(": ", 1)[1] + " is not stated in the documents searched"
    if why.startswith("approximate: "):
        return why.split(": ", 1)[1]
    return why


def _computation_line(m: EvidenceMatrix, c) -> str:
    d = c.derivation or {}
    srcs = population_sources(m, d)
    verdict = (f"computable: {d.get('formula_text')} (period {d.get('period') or 'n/a'})" if d.get("ok")
               else f"not computable: {_why_words(d.get('why', ''))}")
    src = "; ".join(f'"{_q(s["quote"])}" ({s["chunk_id"]}'
                    + (f", population statement dated {s['valid_from']}" if s["dated"] else "") + ")" for s in srcs)
    return (f"    computation (code): {verdict}; inputs cite {', '.join(d.get('input_chunk_ids') or [])}"
            + (f"; population sources: {src}" if src else "; population sources: none registered"))


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
    seen: dict = {}
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
        why_items = bool(w) or a.kind == "recency"
        for c in m.cells.values():
            if c.aspect_id != a.id:
                continue
            lines.append(_cell_head(m, c))
            if computation_proposal(c):
                lines.append(_computation_line(m, c))
            for b in m.breaks:
                if b["id"] == c.id:
                    lines.append("    basis break (code): " + "; ".join(b["groups"])
                                 + " -> state each basis with its own periods; never join them")
            for n, i in enumerate(c.items):
                if i.counts:
                    ref = None
                    if v6():   # #284: the item's ref; an item whose figure was not found in its passage has none
                        ref = f"{c.id}/{n + 1}" + (" (no ref)" if "number_not_found" in i.flags else "")
                    line = _item_line(n, i, ref)
                    first = seen.setdefault((_flat(i.text).lower(), tuple(sorted(i.chunk_ids))), c.aspect_id)
                    if first != c.aspect_id:
                        line += f" [also under {first}: write it once]"
                    lines.append(line)
                    if why_items:
                        ctx = item_context(m, i)
                        if ctx:
                            lines.append(f'      context: "{_q(ctx)}"')
                        for r_ in related_items(m, c, i):   # #247 part 2 R1: background another passage gives
                            lines.append(f"      related: cite {', '.join(r_.chunk_ids)} | {_q(r_.text)[:160]}")
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
    if v6():
        return reduce_schema_v6(m)
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


def output_schema_v6() -> dict:
    """#284: the v6 tool schema without enums: claims and adjacent items name matrix items by ref (`items`), with a
    short `text`, extra `chunk_ids` and a `why` sentence; gaps as before."""
    base = llm_output_schema()
    claim = {"type": "object", "additionalProperties": False,
             "properties": {"part_id": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}},
                            "text": {"type": "string"}, "chunk_ids": {"type": "array", "items": {"type": "string"}},
                            "why": {"type": "string"}},
             "required": ["part_id", "items", "text", "chunk_ids", "why"]}
    adjacent = copy.deepcopy(claim)
    adjacent["properties"]["differs_because"] = {"type": "string"}
    adjacent["required"].append("differs_because")
    s = copy.deepcopy(base)
    s["properties"]["claims"]["items"] = claim
    s["properties"]["adjacent"]["items"] = adjacent
    return s


def reduce_schema_v6(m: EvidenceMatrix) -> tuple[dict, list[str]]:
    """#284: the v6 schema with enums from the matrix (behavior, part ids, chunk ids, refs), under the same limits
    as v5.2; over them a field falls back to a plain string, chunk ids first, then refs, then part ids (the code
    checks are the guard there: unknown_ref, ref_part_mismatch, unmatched_citation)."""
    s = output_schema_v6()
    ids, parts, refs = citable(m), part_ids(m), list(item_refs(m))
    behavior = [m.behavior] if m.behavior in CALLING else list(CALLING)
    on = {"chunk_ids": bool(ids), "items": bool(refs), "part_id": True}
    size = {"chunk_ids": (2, ids), "items": (2, refs), "part_id": (3, parts)}

    def total() -> int:
        return len(behavior) + sum(k * len(v) for f, (k, v) in size.items() if on[f])

    def too_long(values: list[str]) -> bool:
        return len(values) > ENUM_BIG and sum(len(v) for v in values) > ENUM_BIG_CHARS

    fallback: list[str] = []
    for f in ("chunk_ids", "items", "part_id"):
        if on[f] and (too_long(size[f][1]) or total() > ENUM_TOTAL_MAX):
            on[f] = False
            fallback.append(f)
    s["properties"]["behavior"]["enum"] = behavior
    for key in ("claims", "adjacent", "gaps"):
        props = s["properties"][key]["items"]["properties"]
        if on["part_id"]:
            props["part_id"] = {"type": "string", "enum": parts}
        if key != "gaps":
            if on["chunk_ids"]:
                props["chunk_ids"] = {"type": "array", "items": {"type": "string", "enum": ids}}
            if on["items"]:
                props["items"] = {"type": "array", "items": {"type": "string", "enum": refs}}
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
    """#272: deepseek by the reduce stage's effort (off 20000, thinking 128000); else the answer cap."""
    from cee.answer import llm
    if provider == "deepseek":
        return llm.stage_max_tokens("reduce")
    return llm.answer_max_tokens(provider)


def requests(question: str, m: EvidenceMatrix, query, provider: str) -> dict:
    """The provider request (and its parts, for the eval's cache key)."""
    from cee.answer import llm
    schema, _ = reduce_schema(m)
    user = reduce_message(question, m, query)
    if provider == "anthropic":
        return {"model": settings().llm_model, "max_tokens": max_tokens(provider), "system": system_prompt(),
                "tools": [{"name": TOOL, "description": "Submit the cited answer.", "strict": True,
                           "input_schema": schema}],
                "tool_choice": {"type": "auto"}, "messages": [{"role": "user", "content": user}]}
    if provider == "openai":
        return {"model": settings().openai_model,
                "messages": [{"role": "system", "content": system_prompt() + "\nReturn JSON matching the schema."},
                             {"role": "user", "content": user}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": "answer", "strict": True, "schema": schema}}}
    if provider == "deepseek":
        return llm.deepseek_tool_request(TOOL, "Submit the cited answer.", schema, system_prompt(), user,
                                         max_tokens(provider), stage="reduce")
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def input_tokens(question: str, m: EvidenceMatrix, query=None) -> int:
    schema, _ = reduce_schema(m)
    return round((len(system_prompt()) + len(json.dumps(schema)) + len(reduce_message(question, m, query))) / 4)


def input_limit(provider: str) -> int | None:
    from cee.answer import llm
    window = llm.CONTEXT_WINDOW.get(provider)
    return None if window is None else window - max_tokens(provider)


# --- v6: item refs rendered by code (#284, plans/0284-reduce-short.md) ----------------------------------------

def item_refs(m: EvidenceMatrix) -> dict:
    """#284: ref -> (cell, item); "<cell id>/<n>" for each counting item without number_not_found, n as numbered in
    the message (index in c.items + 1), and "<cell id>/derived" -> (cell, None) for an accepted derivation."""
    out: dict = {}
    for c in m.cells.values():
        if c.label == "derived" and (c.derivation or {}).get("ok"):
            out[f"{c.id}/derived"] = (c, None)
        for n, i in enumerate(c.items):
            if i.counts and "number_not_found" not in i.flags:
                out[f"{c.id}/{n + 1}"] = (c, i)
    return out


def is_v6(raw) -> bool:
    """A v6 output: a claim or adjacent item carries `items` (refs)."""
    if not isinstance(raw, dict):
        return False
    return any(isinstance(x, dict) and "items" in x
               for f in STREAMED if isinstance(raw.get(f), list) for x in raw[f])


def render_source(h) -> str:
    """#284: "Per the <source label without tier>, published <date>: " (a retrieved web page's label already says
    "page content as of ...")."""
    from cee.answer.validate import _retrieved, source_label
    label = source_label(h).rsplit(" [", 1)[0]
    pub = "" if _retrieved(h) or not h.published_at else f", published {_date_words(h.published_at)}"
    return f"Per the {label}{pub}: "


def render_item(m: EvidenceMatrix, c, i) -> str:
    """#284: one ref's text: the source of the item's first chunk id, the item's own text, then scope, period and
    value when the text lacks them (TL NB1); a derived ref -> the cell's formula, as mock_reduce writes it."""
    if i is None:
        a = m.aspect(c.aspect_id)
        return f"{_q(a.text).rstrip('.')}: {(c.derivation or {}).get('formula_text')}."
    h = next((m.hits.get(x) for x in i.chunk_ids[:1] if m.hits.get(x) is not None), None)
    body = _q(i.text).rstrip().rstrip(".")
    low = body.lower()
    extra = []
    if i.scope and _q(i.scope).lower() not in low:
        extra.append(f"scope: {_q(i.scope)}")
    if i.period and _q(i.period).lower() not in low:
        extra.append(f"period {_q(i.period)}")
    if i.value and _q(i.value) not in body:
        extra.append(f"value {_q(i.value)}" + (f" {_q(i.unit)}" if i.unit else ""))
    tail = f" ({'; '.join(extra)})" if extra else ""
    return (render_source(h) if h is not None else "") + body + tail + "."


def _figure_values(texts: list[str]) -> list[float]:
    from cee.answer.validate import _chunk_values
    return [v for t in texts if t for v in _chunk_values(t) + _chunk_values(t, unscaled=True)]


def _matrix_texts(m: EvidenceMatrix, ids: set) -> tuple[list[str], list[float]]:
    """#284 (TL B3): the matrix strings a figure may come from for a claim citing `ids`: value / text / quote /
    definition of every item citing one of them, and every accepted derived value whose inputs it all cites."""
    texts = [s for c in m.cells.values() for i in c.items if set(i.chunk_ids) & ids
             for s in (f"{i.value} {i.unit}".strip(), i.text, i.quote, i.definition)]
    derived = [v for v, inputs in derived_values(m) if inputs and inputs <= ids]
    return texts, derived


def outside_figures(text: str, m: EvidenceMatrix, ids: set) -> list[str]:
    """#284 (TL B3): figures of `text` (validate.figures) found in no matrix string of the cited cells nor in a
    derived value whose inputs are cited (matrix provenance; rule 4)."""
    from cee.answer.validate import figures, number_matches
    texts, derived = _matrix_texts(m, ids)
    values = _figure_values(texts) + derived
    return [str(f.shown) for f in figures(text) if not any(number_matches(f, v) for v in values)]


def number_missing(text: str, m: EvidenceMatrix, ids) -> bool:
    """#284 (TL B1): validate.check_numbers on `text` alone, citing `ids` (the matrix's hits and derived values):
    True when a figure of it is in none of the cited chunks (number_not_found)."""
    from cee.answer.schema import Claim
    from cee.answer.validate import check_numbers
    if not text or not ids:
        return False
    a = Answer(answerable=True, behavior="answer", claims=[Claim(text=text, chunk_ids=list(ids))])
    check_numbers(a, [h for h in m.hits.values()], derived=derived_values(m))
    return "number_not_found" in a.claims[0].flags


def _ref_ok(c, part_id: str) -> bool:
    return c.id == part_id or c.aspect_id == part_id


def _ref_ids(c, i) -> list[str]:
    return list((c.derivation or {}).get("input_chunk_ids") or []) if i is None else list(i.chunk_ids)


def render_one(x: dict, m: EvidenceMatrix, refs: dict | None = None, log: dict | None = None) -> dict:
    """#284: one v6 claim or adjacent item -> the v5 shape (text, chunk_ids, part_id [, differs_because], flags).
    Text = [<Firm>: ][<lead>: ]<rendered refs> (the firm prefix from the ref's own cell: once when every ref has one
    cell, else before each ref) + " Why it might matter: <why>"; a claim with no ref keeps its text. Chunk ids = the
    refs' ids + `chunk_ids`. An unknown ref is dropped (flag unknown_ref); a ref outside the part (not its cell, not a
    cell of its aspect) is dropped (flag ref_part_mismatch). A claim left with no ids keeps today's uncited path
    (no_citation); render_output drops a claim whose refs were all dropped (logged under `dropped`), so the part
    check names the cell as a gap. `log` collects the counts (render_output)."""
    refs = item_refs(m) if refs is None else refs
    log = {} if log is None else log
    part = str(x.get("part_id") or "")
    flags: list[str] = []
    picked = []
    for r in x.get("items") or []:
        got = refs.get(str(r))
        if got is None:
            flags.append("unknown_ref")
            log.setdefault("unknown_ref", []).append({"part_id": part, "ref": r})
        elif not _ref_ok(got[0], part):
            flags.append("ref_part_mismatch")
            log.setdefault("ref_part_mismatch", []).append({"part_id": part, "ref": r})
        else:
            picked.append(got)
    lead = " ".join(str(x.get("text") or "").split())
    why = " ".join(str(x.get("why") or "").split())
    if why.startswith(P.WHY_LINE.strip()):
        why = why[len(P.WHY_LINE.strip()):].strip()
    ids = list(dict.fromkeys([*(k for c, i in picked for k in _ref_ids(c, i)),
                              *(str(k) for k in x.get("chunk_ids") or [])]))
    segs = [(c, i, render_item(m, c, i)) for c, i in picked]
    head = f"{lead.rstrip(':.')}: " if lead else ""
    if not segs:
        text = lead
    elif len({c.id for c, _, _ in segs}) == 1:
        text = _firm_prefix(m, segs[0][0]) + head + " ".join(s for _, _, s in segs)
    else:
        text = head + " ".join(_firm_prefix(m, c) + s for c, _, s in segs)
    if why:
        text = f"{text} {P.WHY_LINE}{why}" if text else f"{P.WHY_LINE}{why}"
    out = {"text": text, "chunk_ids": ids, "part_id": part, "flags": list(dict.fromkeys(flags))}
    if "differs_because" in x:
        out["differs_because"] = str(x.get("differs_because") or "")
    if x.get("items") and not segs:   # every ref dropped: not a claim (its extra ids alone carry no text)
        out["dropped"] = True
        log.setdefault("dropped", []).append({"part_id": part, "refs": list(x.get("items") or []), "text": lead})
    log["refs"] = log.get("refs", 0) + len(x.get("items") or [])
    if not segs:
        log["text_claims"] = log.get("text_claims", 0) + 1
    if not ids and not out.get("dropped") and text.strip() != P.BOUNDARY_HANDOFF:
        log["uncited"] = log.get("uncited", 0) + 1
    for c, i, s in segs:   # TL B3: rendered text only from the matrix (0 required); TL B1: and from its chunks
        for f in outside_figures(s, m, set(_ref_ids(c, i))):
            log.setdefault("rendered_outside", []).append({"part_id": part, "figure": f})
        if number_missing(s, m, _ref_ids(c, i)):
            log.setdefault("rendered_number_not_found", []).append({"part_id": part, "text": s[:200]})
    model_text = " ".join(t for t in (lead, why) if t)
    for f in (outside_figures(model_text, m, set(ids)) if model_text else []):
        log.setdefault("model_outside", []).append({"part_id": part, "figure": f, "text": model_text[:200]})
    if model_text and number_missing(model_text, m, ids):
        log.setdefault("model_number_not_found", []).append({"part_id": part, "text": model_text[:200]})
    return out


RENDER_COUNTS = ("refs", "unknown_ref", "ref_part_mismatch", "dropped", "uncited", "text_claims",
                 "rendered_outside", "model_outside", "rendered_number_not_found", "model_number_not_found")


def render_output(raw: dict, m: EvidenceMatrix) -> tuple[dict, dict]:
    """#284: a v6 tool output -> the v5 Answer shape (claims / adjacent rendered by render_one; gaps and the rest
    unchanged) and the render log: counts, plus the lists behind unknown_ref, ref_part_mismatch and the figures
    outside the matrix (rendered vs model text). Runs in to_answer, so every check after it is the same as v5.2's."""
    refs, log = item_refs(m), {}
    out = dict(raw)
    for f in STREAMED:
        if isinstance(raw.get(f), list):
            done = [render_one(x, m, refs, log) if isinstance(x, dict) else x for x in raw[f]]
            out[f] = [x for x in done if not (isinstance(x, dict) and x.pop("dropped", False))]
    counts = {k: (len(v) if isinstance(v, list) else v) for k, v in log.items()}
    return out, {**{k: 0 for k in RENDER_COUNTS}, **counts,
                 "lists": {k: v for k, v in log.items() if isinstance(v, list)}}


# --- the call ------------------------------------------------------------------------------------

def call_reduce(question: str, m: EvidenceMatrix, query, provider: str, client=None,
                meta: dict | None = None, on_item=None) -> dict:
    """One reduce call; the raw tool input (a dict), or ModelOutputError when the output cannot be
    trusted (no tool call, cut at the cap, refusal, a DeepSeek finish_reason other than tool_calls /
    stop, not JSON, not a valid Answer, empty). `meta` gets stop_reason, usage, parse_flags and
    (deepseek) reasoning_content. ProviderStop and any other exception propagate. No trim: an input
    over the model's limit is not sent (RuntimeError). #275: `on_item(kind, item)` (DeepSeek, streamed) gets each
    claim / adjacent item as soon as its JSON object is complete (StreamItems), in this thread; see EarlyClaims.
    #277: not sent after Stop (cancel.Cancelled); a streamed call is cut by Stop (llm.read_stream)."""
    from cee.answer import cancel, llm
    cancel.check()
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
        if on_item is None:
            resp = llm.deepseek_create(client, req)
        else:
            items = StreamItems()

            def on_delta(index, name, text):
                if name == TOOL:
                    for kind, obj in items.feed(text):
                        on_item(kind, obj)
            resp = llm.deepseek_create(client, req, on_delta=on_delta)
        call, stop, usage, payload = llm.deepseek_tool_call(resp, TOOL, req)
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
    to_answer(raw, provider, meta, m)   # validates (ModelOutputError when not a valid, non-empty Answer)
    return raw


ARGUMENT_ERRORS = ("Model arguments are not a JSON object", "Model output is not JSON")


def to_answer(raw, provider: str, meta: dict | None = None, m: EvidenceMatrix | None = None) -> Answer:
    """A raw tool input as a checked Answer (llm.check_output), else ModelOutputError. #284: a v6 output (refs) is
    rendered first (render_output, needs the matrix `m`); the render log rides on the Answer (`_render`)."""
    from cee.answer import llm
    meta = meta or {}
    stop, usage = meta.get("stop_reason"), dict(meta.get("usage") or {})
    if meta.get("parse_flags"):
        usage["parse_flags"] = list(meta["parse_flags"])
    render = None
    if is_v6(raw):
        if m is None:
            raise llm.ModelOutputError("A v6 output (item refs) needs the matrix to render", raw, provider, stop, usage)
        raw, render = render_output(raw, m)
    try:
        answer = Answer(**raw) if isinstance(raw, dict) else None
    except (ValueError, TypeError) as e:
        raise llm.ModelOutputError(f"Model output is not a valid Answer: {e}", raw, provider, stop, usage) from e
    if answer is None:
        raise llm.ModelOutputError("Model output is not a JSON object", raw, provider, stop, usage)
    answer.llm_called = provider != "mock"
    answer.stop_reason, answer.usage = stop or "", usage
    answer._render = render
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
    the code gap fires); recency items end with the why-line. Behavior = the matrix's. #277: waits through
    cancel.sleep (a Stop cuts it)."""
    from cee.answer import cancel
    cancel.sleep(settings().mock_delay_s)
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


def mock_reduce_v6(m: EvidenceMatrix, query=None) -> dict:
    """#284: mock_reduce's output as v6 refs (0 calls): an item claim -> its first counting item's ref (a text claim
    with that item's text when it has no ref), a derived claim -> "<cell>/derived", the comparison claim -> a text
    claim, recency items -> why "the source does not say."; the same chunk ids as v5.2's mock."""
    base = mock_reduce(m, query)
    refs = {id(i): r for r, (c, i) in item_refs(m).items() if i is not None}
    unsaid = P.WHY_UNSAID[len(P.WHY_LINE):]

    def conv(x: dict, adjacent: bool) -> dict:
        c = m.cells.get(x["part_id"])
        why = unsaid if x["text"].endswith(P.WHY_UNSAID) else ""
        out = {"part_id": x["part_id"], "items": [], "text": "", "chunk_ids": [], "why": why}
        d = (c.derivation or {}) if c is not None else {}
        if c is not None and c.label == "derived" and d.get("ok") and not adjacent:
            out["items"] = [f"{c.id}/derived"]
        elif c is not None and c.counting_items:
            i = c.counting_items[0]
            if id(i) in refs:
                out["items"] = [refs[id(i)]]
            else:
                out.update(text=x["text"].split(P.WHY_LINE, 1)[0].rstrip(), chunk_ids=list(x["chunk_ids"]))
        else:
            out.update(text=x["text"], chunk_ids=list(x["chunk_ids"]))
        if adjacent:
            out["differs_because"] = x["differs_because"]
        return out
    return {**base, "claims": [conv(x, False) for x in base["claims"]],
            "adjacent": [conv(x, True) for x in base["adjacent"]]}


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
        if any(g.part_id == a.id and "comparison_missing" in g.flags for g in answer.gaps):
            missing.append(a.id)   # #247 part 2 R4: added once
            continue
        if _normative_handoff(answer, a):
            continue
        missing.append(a.id)
        answer.gaps.append(Gap(what=P.COMPARISON_MISSING.format(aspect=_aspect_text(a)), part_id=a.id,
                               flags=["comparison_missing"]))
    return missing


def _normative_handoff(answer: Answer, a) -> bool:
    """R4: a normative comparison aspect ("how should ...") is answered by the hand-off sentence."""
    from cee.answer.matrix import normative_question
    from cee.answer.validate import is_normative
    return answer.behavior == "answer_with_boundary" and (is_normative(a.text) or normative_question(a.text)) and any(
        c.text.strip() == P.BOUNDARY_HANDOFF for c in answer.claims)


def _why_scope(m: EvidenceMatrix, query, x) -> bool:
    c = m.cells.get(x.part_id)
    aspect = c.aspect_id if c is not None else x.part_id
    return bool(own_window(query)) or aspect in _recency_aspects(m)


_STOP = set("""a an the and or of to in on at for by with from as is are was were be been it its this that these those
which who what why how it's their his her our we they he she not no but also than then so such into about over
after before more most per may might matter source sources says said report reports reported states stated
according firm company total totals amount amounts figure figures show shows showing same table include
includes including""".split())


def _content(text: str) -> set[str]:
    import re
    from cee.answer.validate import _firm_names
    t = text.lower()
    for n in sorted(_firm_names(), key=len, reverse=True):
        t = t.replace(n.lower(), " ")
    return {w for w in re.findall(r"[a-z][a-z'-]+", t) if w not in _STOP and len(w) > 2}


def restates(body: str, why: str) -> bool:
    """The why sentence adds nothing beyond its claim (#247 part 2, TL D4): every figure it states is in
    the claim and >= 80% of its content words (stop words and firm names removed) are too."""
    from cee.answer.validate import figures
    why = why.strip()
    if not why or why == P.WHY_UNSAID[len(P.WHY_LINE):]:
        return False
    body_figs = {str(f.value) for f in figures(body)}
    if any(str(f.value) not in body_figs for f in figures(why)):
        return False
    words, have = _content(why), _content(body)
    if not words:
        return True

    def known(w: str) -> bool:   # "addition" is in a body that says "add"
        return any(w.startswith(b) or b.startswith(w) for b in have)
    return sum(known(w) for w in words) >= 0.8 * len(words)


def clean_why_lines(answer: Answer, m: EvidenceMatrix, query) -> dict:
    """#247 part 2: a why-line outside recency / window items is removed (why_line_removed); a why-line
    that restates its claim is replaced with WHY_UNSAID (why_line_restated). The model's text is kept
    in the log (returned)."""
    log: dict = {"removed": [], "restated": [], "unsaid": []}
    for x in [*answer.claims, *answer.adjacent]:
        if P.WHY_LINE not in x.text:
            continue
        body, why = x.text.split(P.WHY_LINE, 1)
        if not _why_scope(m, query, x):
            x.text = body.rstrip()
            x.flags.append("why_line_removed")
            log["removed"].append({"part_id": x.part_id, "why": why.strip()})
        elif why.strip() == P.WHY_UNSAID[len(P.WHY_LINE):]:
            log["unsaid"].append({"part_id": x.part_id})   # written by the model (R1: never by default)
        elif restates(body, why) and not _cites_background(m, x):
            x.text = body.rstrip() + " " + P.WHY_UNSAID
            x.flags.append("why_line_restated")
            log["restated"].append({"part_id": x.part_id, "why": why.strip()})
    return log


def _cites_background(m: EvidenceMatrix, x) -> bool:
    """R1: the claim cites more than any one item's chunks (factual background from another passage)."""
    c = m.cells.get(x.part_id)
    items = c.counting_items if c is not None else []
    cited = set(x.chunk_ids)
    return bool(items) and not any(cited <= set(i.chunk_ids) for i in items)


def check_computability(answer: Answer, m: EvidenceMatrix) -> list[str]:
    """TL D5 / condition 1: for each derivation proposal with cited inputs, a claim on that cell citing
    every input and population source chunk; missing -> code adds it (COMPUTED / NOT_COMPUTED, the
    sources quoted), flag code_computability. Returns the cells it added a claim for."""
    from cee.answer.matrix import _aspect_text
    from cee.answer.schema import Claim
    added = []
    for c in m.cells.values():
        if not computation_proposal(c):
            continue
        d = c.derivation
        need = set(d.get("input_chunk_ids") or []) | set(d.get("population_chunk_ids") or [])
        if any(x.part_id == c.id and need <= set(x.chunk_ids) for x in answer.claims):
            continue
        a = m.aspect(c.aspect_id)
        firm = f"{row_name(c)}: "
        srcs = _sources_text(population_sources(m, d))
        if d.get("ok"):
            text = P.COMPUTED.format(firm=firm, aspect=_aspect_text(a).rstrip("."), formula=d.get("formula_text"),
                                     period=f" ({d.get('period')})" if d.get("period") else "", sources=srcs)
        else:
            text = P.NOT_COMPUTED.format(firm=firm, aspect=_aspect_text(a).rstrip("."),
                                         why=_why_words(d.get("why", "")), sources=srcs)
        ids = list(dict.fromkeys([*(d.get("input_chunk_ids") or []), *(d.get("population_chunk_ids") or [])]))
        claim = Claim(text=text, chunk_ids=ids, part_id=c.id, flags=["code_computability"])
        same = [n for n, x in enumerate(answer.claims)
                if x.part_id in m.cells and m.cells[x.part_id].aspect_id == c.aspect_id]
        answer.claims.insert((max(same) + 1) if same else len(answer.claims), claim)
        added.append(c.id)
    return added


def _dup_text(x) -> str:
    import re
    body = x.text.split(P.WHY_LINE, 1)[0]
    body = re.sub(r"^[^:]{1,60}:\s+", "", body.strip())
    return " ".join(re.sub(r"[^\w\s.,%$]", " ", body.lower()).split()).rstrip(".")


SUBSUMED = 0.85   # share of the shorter claim's content words found in the longer one
_QUOTED = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d|(?<![\w])\'[^\']{6,}\'(?![\w])')
_QUARTER_LABEL = re.compile(r"\b(?:[1-4]Q\d{2}|\d{4}Q[1-4]|(?:first|second|third|fourth) quarter(?: of)? \d{4})\b", re.I)


def _outside_quotes(text: str) -> str:
    """A claim's own words: quoted passage text removed (PR #261 review blocking 1: a quoted table row
    carries every period's figure, so figures are compared outside the quotes)."""
    return _QUOTED.sub(" ", text)


# #247 part 3 item 4: bare and fiscal years are stated periods too; "$2,024" / "2,024 advisors" / "2024.5" are
# not years, "in 2024, ..." is (TL condition 3: lookahead (?!\d|,\d|\.\d))
_YEAR = re.compile(r"(?:\b(fiscal(?:\s+year)?\s+|FY\s?))?(?<![\d$.,])((?:19|20)\d{2})(?!\d|,\d|\.\d)", re.I)


def _stated_periods(text: str) -> set:
    from cee.answer.validate import _ANY_DATE
    return ({m.group(0).lower() for m in _ANY_DATE.finditer(text)}
            | {m.group(0).lower() for m in _QUARTER_LABEL.finditer(text)}
            | {("fy" if m.group(1) else "") + m.group(2) for m in _YEAR.finditer(text)})


def dedupe_claims(answer: Answer) -> list[dict]:
    """#247 part 2: claims citing the same chunk set are duplicates when their texts (no why-line, no
    "<Firm>: " prefix) are equal, or when the shorter is held in the longer: outside quoted text, every
    figure and every stated period (dates, quarter labels) of it in the longer (PR #261 review blocking 1:
    one table row quoted by claims about different periods), and >= SUBSUMED of its content words (stop
    words and firm names removed) too. The longer is kept (ties: the first). Returns the removed."""
    from cee.answer.validate import figures
    claims = answer.claims
    drop: dict[int, int] = {}
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            if i in drop or j in drop:
                continue
            a, b = claims[i], claims[j]
            if not a.chunk_ids or set(a.chunk_ids) != set(b.chunk_ids) \
                    or P.BOUNDARY_HANDOFF in (a.text.strip(), b.text.strip()):
                continue
            ta, tb = _dup_text(a), _dup_text(b)
            if ta == tb:
                drop[j] = i
                continue
            short, long_, si, li = (ta, tb, i, j) if len(ta) < len(tb) else (tb, ta, j, i)
            rs, rl = (a.text, b.text) if si == i else (b.text, a.text)
            os_, ol = _outside_quotes(rs.split(P.WHY_LINE, 1)[0]), _outside_quotes(rl.split(P.WHY_LINE, 1)[0])
            fs, fl = {str(f.value) for f in figures(os_)}, {str(f.value) for f in figures(ol)}
            ws, wl = _content(short), _content(long_)
            if fs <= fl and _stated_periods(os_) <= _stated_periods(ol) and ws and len(ws & wl) >= SUBSUMED * len(ws):
                drop[si] = li
    removed = [{"text": claims[k].text, "part_id": claims[k].part_id, "kept": v} for k, v in sorted(drop.items())]
    answer.claims = [x for n, x in enumerate(claims) if n not in drop]
    return removed


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
    rec = _recency_aspects(m)

    def key(x):
        dates = [str(by_id[c].published_at) for c in x.chunk_ids if c in by_id and by_id[c].published_at]
        return max(dates) if dates else ""

    def recency_item(x) -> bool:
        c = m.cells.get(x.part_id)
        return (c.aspect_id if c is not None else x.part_id) in rec

    moved = 0
    for field in ("claims", "adjacent"):
        items = getattr(answer, field)
        handoff = [x for x in items if x.text.strip() == P.BOUNDARY_HANDOFF]
        rest = [x for x in items if x.text.strip() != P.BOUNDARY_HANDOFF]
        if own_window(query):
            new = sorted(rest, key=key, reverse=True) + handoff
        else:   # #247 part 2 (review note, Q19): only the recency items move, inside their own slots
            slots = [n for n, x in enumerate(rest) if recency_item(x)]
            ordered = iter(sorted((rest[n] for n in slots), key=key, reverse=True))
            new = list(rest)
            for n in slots:
                new[n] = next(ordered)
            new += handoff
        moved += sum(a is not b for a, b in zip(items, new))
        setattr(answer, field, new)
    return moved


def _gap_norm(text: str) -> str:
    return " ".join(str(text or "").lower().split()).rstrip(".")


def contradicts(m: EvidenceMatrix, g) -> bool:
    """R4: a model gap on a cell that holds, or on an aspect with a planned firm subset whose firms' cells
    all hold (Q19: "Morgan Stanley, ... - how Edward Jones management describes ...: not found")."""
    from cee.answer.matrix import holds
    c = m.cells.get(g.part_id)
    if c is not None:
        return holds(c)
    a = next((x for x in m.aspects if x.id == g.part_id), None)
    asked = list(getattr(a, "asked_firms", None) or []) if a is not None else []
    if not asked or a.kind == "comparison":
        return False
    cells = [c for c in m.cells.values() if c.aspect_id == a.id and c.entity in asked]
    return bool(cells) and all(holds(c) for c in cells)


def place_gaps(answer: Answer, m: EvidenceMatrix, log: list | None = None) -> int:
    """The matrix gaps after the model's; a model gap repeating a code gap (same text, or the same
    "<Firm> - <aspect>:" head for the same part) is merged into it: the code gap kept with the flag
    model_also_named, the model's text in claim_text (review note 9). Returns the merged count."""
    model = list(answer.gaps)
    code = [Gap(what=g["what"], suggested_source=g.get("suggested_source", ""), part_id=g["id"],
                flags=[f"matrix_{g.get('label', 'gap')}"]) for g in m.gaps]
    kept, merged = [], 0
    contradicted = log if log is not None else []
    from cee.answer.matrix import in_gap_scope
    folds = {cid: c for g, c in zip(m.gaps, code) for cid in g.get("cells") or []}
    from cee.answer.matrix import holds
    for g in model:
        cell = m.cells.get(g.part_id)
        if contradicts(m, g):   # #247 part 2 R4: a gap where the matrix holds the evidence
            contradicted.append(g.what)
            merged += 1
            continue
        if cell is not None:   # #247 part 2 (Q19): no gap outside the aspect's firm scope, folded cells merged
            if not in_gap_scope(m.aspect(cell.aspect_id), cell):
                merged += 1
                continue
            if cell.id in folds:
                f = folds[cell.id]
                if "model_also_named" not in f.flags:
                    f.flags.append("model_also_named")
                f.claim_text = "\n".join(x for x in (f.claim_text, g.what) if x)
                merged += 1
                continue
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
    info: dict = {"version": prompt_version(), "code_built": code_built, "model_behavior": answer.behavior}
    if getattr(answer, "_render", None) is not None:   # #284: the v6 render log (counts and lists)
        info["render"] = answer._render
    decided = m.behavior if m.behavior is not None else "incomplete"
    answer.behavior = decided
    answer.answerable = decided in ("answer", "answer_with_boundary") and bool(citable(m))
    answer.incomplete_note = m.incomplete_note or ""
    by_id = _hits_for(m, hits)
    allowed = [by_id[c] for c in citable(m) if c in by_id]
    # #247 part 2: code computability claims and the why-line clean-up come before the citation check,
    # so the citation, number and date checks run on them like on the model's claims (TL condition 1)
    info["code_computability"] = check_computability(answer, m)
    why_log = clean_why_lines(answer, m, query)
    info["why_line_removed"], info["why_line_restated"] = len(why_log["removed"]), len(why_log["restated"])
    info["why_line_unsaid"] = len(why_log["unsaid"])
    info["why_lines_log"] = why_log
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
        info["gaps_contradicting"] = []
        info["gaps_merged"] = place_gaps(answer, m, info["gaps_contradicting"])
    answer.caveats = list(dict.fromkeys([*answer.caveats, *m.caveats]))
    union = list(by_id.values())
    answer = check_parts(answer, plan, union, question, matrix=m)
    # #247 part 2: duplicates removed after the part check; then the comparison and computability
    # checks run again on the reduced list (round-1 note 6), new code claims citation-checked
    info["duplicates_removed"] = dedupe_claims(answer)
    if info["duplicates_removed"]:
        info["comparison_missing"] = sorted(set(info["comparison_missing"]) | set(check_comparisons(answer, m)))
        before = {id(x) for x in answer.claims}
        late = check_computability(answer, m)
        if late:
            fresh = Answer(answerable=answer.answerable, behavior=answer.behavior,
                           claims=[x for x in answer.claims if id(x) not in before])
            check_citations(fresh, allowed, derived=derived_values(m))
            info["code_computability"] = info["code_computability"] + late
    info["basis_breaks"] = [b["id"] for b in m.breaks]
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


def raw_answer(m: EvidenceMatrix, query, provider: str, on_item=None) -> Answer:
    """The mock reduce as a checked Answer (0 calls). #275: with `on_item`, its output is fed as tool JSON through
    StreamItems in pieces (MOCK_DELAY_S spread over the items), so the mock exercises the streamed path.
    #277: a Stop cuts the waits (cancel.Cancelled); MOCK_FAIL_FILE naming `reduce` makes it fail (verify-cee)."""
    from cee.answer import cancel
    from cee.answer.extract import mock_failure
    cancel.check()
    out = mock_reduce_v6(m, query) if v6() else mock_reduce(m, query)
    injected = mock_failure("reduce")
    if injected:
        raise RuntimeError(injected.split(": ", 1)[1])
    if on_item is not None:
        text = json.dumps(out)
        pause = settings().mock_delay_s / max(1, len(out["claims"]) + len(out["adjacent"]))
        items = StreamItems()
        for k in range(0, len(text), 40):
            for kind, obj in items.feed(text[k:k + 40]):
                on_item(kind, obj)
                if pause:
                    cancel.sleep(pause)
    return to_answer(out, "mock", m=m)


# --- streamed claims (#275) ------------------------------------------------------------------------

STREAMED = ("claims", "adjacent")


class StreamItems:
    """#275: incremental parse of the reduce's streamed tool arguments. feed(delta) returns [(kind, item)] for each
    object of the top-level `claims` or `adjacent` array completed by this delta (json.loads of its text). A
    character scanner tracks string / escape state and the bracket stack, so deltas may split anywhere and key
    order does not matter; an incomplete object (a cut or stalled stream) is never returned."""

    def __init__(self):
        self.text = ""
        self.stack: list[str] = []
        self.in_str = self.esc = False
        self.str_start = 0
        self.last_str = self.key = self.array_key = None
        self.item_start = None

    def feed(self, delta: str) -> list[tuple[str, dict]]:
        out = []
        base = len(self.text)
        self.text += delta or ""
        for k, ch in enumerate(delta or ""):
            pos = base + k
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif ch == "\\":
                    self.esc = True
                elif ch == '"':
                    self.in_str = False
                    if len(self.stack) == 1:
                        self.last_str = self.text[self.str_start + 1:pos]
                continue
            if ch == '"':
                self.in_str, self.str_start = True, pos
            elif ch == ":" and len(self.stack) == 1:
                self.key = self.last_str
            elif ch in "{[":
                if ch == "[" and len(self.stack) == 1:
                    self.array_key = self.key
                self.stack.append(ch)
                if ch == "{" and len(self.stack) == 3 and self.stack[1] == "[" and self.array_key in STREAMED:
                    self.item_start = pos
            elif ch in "}]":
                if ch == "}" and len(self.stack) == 3 and self.item_start is not None:
                    try:
                        obj = json.loads(self.text[self.item_start:pos + 1])
                    except ValueError:
                        obj = None
                    if isinstance(obj, dict):
                        out.append((self.array_key, obj))
                    self.item_start = None
                if self.stack:
                    self.stack.pop()
                if ch == "]" and len(self.stack) == 1:
                    self.array_key = None
        return out


def check_item(raw: dict, m: EvidenceMatrix, query):
    """#275 (TL condition 2): the per-item checks of finish_answer on a one-item Answer (behavior answer, hits =
    the matrix's citable hits from m.hits): why-line clean-up, check_citations (with withhold_normative,
    move_uncited_cells, ensure_handoff, the number and date checks), outside_matrix, rule 3, the why-line check.
    Returns the checked Claim when it may be shown before the final answer: still in `claims` with the same
    text, nothing withheld, no gap, no hand-off appended, cited, and `flags == []`; else None (held back)."""
    from cee.answer.schema import Claim
    from cee.answer.validate import check_citations
    if not isinstance(raw, dict):
        return None
    if "items" in raw:   # #284: a v6 claim is rendered first; an unknown or out-of-part ref holds it (flags)
        raw = render_one(raw, m)
    try:
        a = Answer(answerable=True, behavior="answer", claims=[Claim(**raw)])
    except (ValueError, TypeError):
        return None
    x = a.claims[0]
    text = x.text
    clean_why_lines(a, m, query)
    a = check_citations(a, [m.hits[c] for c in citable(m) if c in m.hits], derived=derived_values(m))
    ok_ids = set(citable(m))
    if any(c not in ok_ids for c in x.chunk_ids) and "outside_matrix" not in x.flags:
        x.flags.append("outside_matrix")
    check_adjacent(a, m)
    check_why_lines(a, m, query)
    shown = (len(a.claims) == 1 and a.claims[0] is x and x.text == text and not a.withheld and not a.gaps
             and bool(x.chunk_ids) and x.text.strip() != P.BOUNDARY_HANDOFF and x.flags == [])
    return x if shown else None


class EarlyClaims:
    """#275: on_item for call_reduce / raw_answer. A claim that passes check_item is shown at once (`show(claim)`);
    adjacent items are held until the final answer (TL condition 1), as is every claim check_item holds back.
    Keeps the time from the reduce start to the first shown claim (first_claim_s) and the counts."""

    def __init__(self, m: EvidenceMatrix, query, show=None):
        self.m, self.query, self.show = m, query, show
        self.t0 = time.monotonic()
        self.first_claim_s = None
        self.shown: list = []
        self.held = 0

    def __call__(self, kind: str, raw: dict) -> None:
        claim = check_item(raw, self.m, self.query) if kind == "claims" else None
        if claim is None:
            self.held += 1
            return
        self.shown.append(claim)
        if self.first_claim_s is None:
            self.first_claim_s = round(time.monotonic() - self.t0, 2)
        if self.show is not None:
            self.show(claim)

    def stats(self, final: Answer | None = None) -> dict:
        """first_claim_s, shown, held and (with the final answer) shown_not_final: early claims whose text is not
        in the final answer's claims (only dedupe_claims may remove one)."""
        out = {"first_claim_s": self.first_claim_s, "shown": len(self.shown), "held": self.held}
        if final is not None:
            texts = {c.text for c in final.claims}
            out["shown_not_final"] = sum(c.text not in texts for c in self.shown)
        return out
