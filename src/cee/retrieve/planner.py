"""Question planner (#214, ADR-020): split a question into parts and search each part.

One planner call (the configured provider, the answer model) splits the question into at most
PLANNER_MAX_PARTS parts, each with its firms and its own search words. Code validates the plan:
firms must be ones resolve() found (unknown or unasked firms are dropped, a dropped resolved firm
is added back), the window, themes and Ask page filters are not in the planner's schema at all, and
every part is searched with every hard SQL filter (fts.search on a copy of the resolved query).
Prompt plan-v2 (#224) asks for a part, or its own search words, for every asked part and keeps
the words on the asked concept; code then removes any configured neighbour phrase (a different
figure that shares a word, e.g. "payout ratio") the question does not name (strip_neighbours).
The mock provider, PLANNER=off and an unusable model output use the rule plan: one part per named
firm (2 to PLANNER_MAX_PARTS firms), else one part for the whole question. Tests and CI make 0 calls.

Retrieval of a plan (search_parts): the research part (<= THEME_K passages) once per question, then
the parts in order, sharing the question's ADR-019 token budget minus the research tokens (equal
shares; what a part leaves flows to the parts after it; chunks kept earlier are excluded), then the
theme peers once. A one-part plan returns exactly fts.search(q). Unused share is not handed back
to earlier parts (#224: "not now", see ADR-020).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace

from cee.config import entities_config, settings
from cee.retrieve import fts
from cee.retrieve.fts import Hit, PoolTrace, Query

PLANNER_VERSION = "plan-v2"   # #224: asked-parts and same-concept rules (v1: #214)
PLANNER_MAX_TOKENS = 2000
PLAN_TOOL = "submit_plan"
MAX_QUERY_CHARS = 400

PLANNER_PROMPT = """You plan the document search for a question about wealth-management firms.
The search engine runs one full-text search per part you write, over filings, earnings calls,
investor decks, press releases, Form ADV brochures, trade press and research reports. Code applies
the firm filters, the time window and every other filter; you only choose the parts and the words.

List the asks first. Before writing parts, list for yourself everything the question asks for:
- each named firm or group of firms whose evidence must be found separately;
- each "and" joining two asks, each item of a list, each metric or dimension it names;
- what the question asks without naming it. Example: "What is Firm X's plan for its
  retirement-plan unit?" also asks how management describes the unit, the priorities it states,
  the competition it names, and where it says it is losing ground or pulling back. Example: "How do
  Firm X and Firm Y each handle branch staffing?" asks, for each firm, whom it hires, how it pays
  them, how it trains them, and the results it reports (staff numbers, departures). A figure that
  may not be disclosed also asks for the closest figure that is disclosed, as its own part. A firm
  set against the home firm also asks for the home firm's own comparable figures.

Cover every ask, in at most {max_parts} parts. Every ask gets its own part. With more asks than
parts, merge asks into one part and give each merged ask its own words in that part's
keyword_query; no ask is left without words. With several firms and several dimensions, write one
part per firm with words for every dimension, or one part per dimension with every firm; either way
every firm gets words for every dimension. Do not spend a part on something the question does not
ask. A short question with one ask is one part.

Same concept only. Search words name the asked concept: the words filings and calls use for it and
its exact synonyms. Never add a different figure that shares a word with it, even as context (a
ratio paid to shareholders is not staff pay; company-wide staff turnover is not one unit's
turnover; deposits are not client assets). The closest disclosed figure for an undisclosed one goes
in its own part, never into the words of the asked figure's part.

For each part give:
- id: a short label;
- text: what the part asks, in one sentence;
- firms: firm IDs from the list given, only those; an empty list when no firm is named;
- keyword_query: 5 to 25 words the documents themselves would use for this part (filing and
  earnings-call vocabulary, synonyms, the names of the metrics and disclosures), with no firm names
  and no dates.
Return the plan by calling the {tool} tool; do not answer the question."""


class PlannerOutputError(RuntimeError):
    """The planner's output is not a usable plan (no tool call, wrong shape, cut off)."""

    def __init__(self, message: str, raw=None, stop_reason: str | None = None):
        super().__init__(message)
        self.raw, self.stop_reason = raw, stop_reason


@dataclass
class Part:
    id: str
    text: str
    firms: list[str] = field(default_factory=list)
    keyword_query: str | None = None   # None = the question's own words (fts.keyword_terms)


@dataclass
class Plan:
    parts: list[Part]
    source: str = "rules"           # rules | model | fallback
    provider: str = "rules"
    model: str | None = None
    version: str = PLANNER_VERSION
    corrections: list[str] = field(default_factory=list)
    error: str | None = None
    raw: object = None              # the model's output (or payload), JSON-safe
    calls: int = 0                  # paid planner calls (0 or 1)
    searched: list[dict] = field(default_factory=list)   # per part: share, passages, tokens (search_parts)
    research_tokens: float = 0.0

    def to_log(self) -> dict:
        return {"source": self.source, "provider": self.provider, "model": self.model,
                "version": self.version, "parts": [asdict(p) for p in self.parts],
                "corrections": self.corrections, "error": self.error, "calls": self.calls,
                "searched": self.searched, "research_tokens": round(self.research_tokens),
                "raw": self.raw}


def max_parts() -> int:
    return settings().planner_max_parts


def rules_plan(q: Query, cap: int | None = None) -> Plan:
    """The deterministic plan: one part per named covered firm when there are 2 to `cap` of them,
    else one part for the whole question (five firms exceed the default cap of 4)."""
    cap = max_parts() if cap is None else cap
    firms = list(q.entities)
    if 2 <= len(firms) <= cap:
        parts = [Part(f"p{i}", q.question, [f]) for i, f in enumerate(firms, 1)]
    else:
        parts = [Part("p1", q.question, firms)]
    return Plan(parts=parts)


def _firm_id(name: str) -> tuple[str | None, bool]:
    """(config id, covered) for a firm string the planner wrote: an ID, a name or an alias."""
    cfg = entities_config()
    s = str(name).strip()
    for covered, entries in ((True, cfg["entities"]), (False, cfg.get("expansion") or [])):
        for e in entries:
            if s.upper() == e["id"].upper() or fts._mentions(s, e):
                return e["id"], covered
    return None, False


def _cut(text: str, n: int = MAX_QUERY_CHARS) -> str:
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0]


def neighbour_phrases() -> list[str]:
    """Phrases naming a different figure than the asked one (config `neighbour_phrases`, #224)."""
    return [str(p) for p in entities_config().get("neighbour_phrases") or []]


def strip_neighbours(words: str, question: str) -> tuple[str, list[str]]:
    """The planner's search words without every configured neighbour phrase the question itself
    does not name (#224, ADR-020): "payout ratio" in a part about advisor pay brought dividend
    payout chunks into #214's Q25. Matched like a synonym key (any case, hyphen or spaces between
    words, inflected last word). Returns (words, dropped phrases)."""
    dropped: list[str] = []
    for phrase in neighbour_phrases():
        pattern = fts._synonym_pattern(phrase)
        if pattern.search(words) and not pattern.search(question):
            words = pattern.sub(" ", words)
            dropped.append(phrase)
    return (" ".join(words.split()) if dropped else words), dropped


def validate_plan(raw, q: Query, cap: int | None = None) -> tuple[list[Part], list[str]]:
    """The model's plan corrected by code (ADR-020); raises PlannerOutputError when not usable."""
    cap = max_parts() if cap is None else cap
    if not isinstance(raw, dict) or not isinstance(raw.get("parts"), list) or not raw["parts"]:
        raise PlannerOutputError("planner output has no parts", raw)
    notes: list[str] = []
    parts: list[Part] = []
    for item in raw["parts"]:
        if not isinstance(item, dict):
            raise PlannerOutputError("a part is not an object", raw)
        text = str(item.get("text") or "").strip()
        firms: list[str] = []
        for f in item.get("firms") or []:
            fid, covered = _firm_id(f)
            if fid is None:
                notes.append(f"unknown firm {f}")
            elif fid not in q.entities:
                notes.append(f"not asked: {fid}" if covered else f"no documents: {fid}")
            elif fid not in firms:
                firms.append(fid)
        if not firms and q.entities:
            firms = list(q.entities)
            notes.append(f"part {len(parts) + 1}: no asked firm, all firms")
        words = str(item.get("keyword_query") or "").strip()
        if not words:
            words = text or q.question
            notes.append(f"part {len(parts) + 1}: no search words")
        elif len(words) > MAX_QUERY_CHARS:
            words = _cut(words)
            notes.append(f"part {len(parts) + 1}: search words cut")
        words, dropped = strip_neighbours(words, q.question)
        notes += [f"part {len(parts) + 1}: dropped neighbour phrase {d}" for d in dropped]
        if dropped and not words:
            words = None
            notes.append(f"part {len(parts) + 1}: no search words left")
        parts.append(Part("", text or q.question, firms, words))
    if len(parts) > cap:
        parts = parts[:cap]
        notes.append(f"cut to {cap} parts")
    missing = [f for f in q.entities if not any(f in p.firms for p in parts)]
    if missing:
        if len(parts) < cap:
            parts.append(Part("", q.question, missing, None))
        else:
            fewest = min(parts, key=lambda p: len(p.firms))
            fewest.firms += missing
        notes.append("added firm " + ", ".join(missing))
    for i, p in enumerate(parts, 1):
        p.id = f"p{i}"
    return parts, notes


def plan_schema(strict: bool = False) -> dict:
    """strict=True: the OpenAI and DeepSeek (#242) schema (no array limits). strict=False: the Anthropic tool's schema,
    also sent with strict: true since #232; Anthropic strict mode accepts minItems 0 or 1 and no
    maxItems, so the part cap is in the prompt and code cuts extra parts (validate_plan)."""
    part = {"type": "object",
            "properties": {"id": {"type": "string"}, "text": {"type": "string"},
                           "firms": {"type": "array", "items": {"type": "string"}},
                           "keyword_query": {"type": "string"}},
            "required": ["id", "text", "firms", "keyword_query"], "additionalProperties": False}
    parts = {"type": "array", "items": part}
    if not strict:
        parts |= {"minItems": 1}
    return {"type": "object", "properties": {"parts": parts}, "required": ["parts"],
            "additionalProperties": False}


def planner_message(q: Query, cap: int) -> str:
    by_id = {e["id"]: e["name"] for e in entities_config()["entities"]}
    firms = "; ".join(f"{f} ({by_id.get(f, f)})" for f in q.entities) or "none named"
    lines = [f"Question: {q.question}", f"Firms (IDs to use): {firms}"]
    if q.window:
        lines.append(f"Time window (applied by code): {q.window[0]} to {q.window[1]}")
    if q.themes:
        lines.append(f"Themes: {fts.theme_label(q)}")
    lines.append(f"Most parts: {cap}")
    return "\n".join(lines)


def system_prompt(cap: int) -> str:
    return PLANNER_PROMPT.format(max_parts=cap, tool=PLAN_TOOL)


def anthropic_plan_request(q: Query, cap: int) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": PLANNER_MAX_TOKENS,
        "system": system_prompt(cap),
        "tools": [{"name": PLAN_TOOL, "description": "Submit the search plan.", "strict": True,   # #232
                   "input_schema": plan_schema()}],
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": planner_message(q, cap)}],
    }


def openai_plan_request(q: Query, cap: int) -> dict:
    return {
        "model": settings().openai_model,
        "messages": [{"role": "system", "content": system_prompt(cap) + "\nReturn JSON matching the schema."},
                     {"role": "user", "content": planner_message(q, cap)}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "plan", "strict": True, "schema": plan_schema(strict=True)}},
    }


def planner_max_tokens(provider: str) -> int:
    """The planner call's output cap (#242): by thinking mode for deepseek, else PLANNER_MAX_TOKENS."""
    if provider == "deepseek":
        from cee.answer.llm import DEEPSEEK_PLANNER_MAX_TOKENS
        return DEEPSEEK_PLANNER_MAX_TOKENS[settings().deepseek_thinking]
    return PLANNER_MAX_TOKENS


def deepseek_plan_request(q: Query, cap: int) -> dict:
    """#242: strict function submit_plan (OpenAI strict schema: no array limits), explicit max_tokens."""
    from cee.answer.llm import deepseek_tool_request
    return deepseek_tool_request(PLAN_TOOL, "Submit the search plan.", plan_schema(strict=True),
                                 system_prompt(cap), planner_message(q, cap), planner_max_tokens("deepseek"))


def _block_dict(b) -> dict:
    from cee.answer.llm import _block_dict as block
    return block(b)


def call_planner(q: Query, provider: str, cap: int, client=None, meta: dict | None = None):
    """The raw plan from one provider call; PlannerOutputError when the output is not a plan.
    `meta` (#230, bookkeeping only): when a dict is passed, it gets the call's stop_reason and usage,
    so the eval saves why every real output stopped."""
    from cee.answer import llm

    meta = {} if meta is None else meta
    if provider == "anthropic":
        client = client or llm.anthropic_client()
        resp = client.messages.create(**anthropic_plan_request(q, cap))
        stop = getattr(resp, "stop_reason", None)
        meta["stop_reason"] = stop
        meta["usage"] = {**llm._usage(resp, "input_tokens", "output_tokens"),
                         "blocks": [getattr(b, "type", "?") for b in resp.content]}
        block = next((b for b in resp.content if b.type == "tool_use" and b.name == PLAN_TOOL), None)
        if block is None:
            raise PlannerOutputError(f"planner did not call {PLAN_TOOL} (stop_reason={stop})",
                                     [_block_dict(b) for b in resp.content], stop)
        if stop == "max_tokens":
            raise PlannerOutputError("planner output cut at max_tokens", block.input, stop)
        if stop == llm.REFUSAL:   # #232: strict's schema guarantee does not hold after a refusal
            raise PlannerOutputError("planner output stopped by refusal",
                                     [_block_dict(b) for b in resp.content], stop)
        return block.input
    if provider == "openai":
        client = client or llm.openai_client()
        resp = client.chat.completions.create(**openai_plan_request(q, cap))
        content = resp.choices[0].message.content
        stop = getattr(resp.choices[0], "finish_reason", None)
        meta["stop_reason"] = stop
        meta["usage"] = llm._usage(resp, "prompt_tokens", "completion_tokens")
        if stop in llm.CUT_REASONS:   # #242: a cut plan is never trusted, even when it parses
            raise PlannerOutputError("planner output cut at max_tokens", content, stop)
        try:
            return json.loads(content)
        except (TypeError, ValueError) as e:
            raise PlannerOutputError(f"planner output is not JSON: {e}", content) from e
    if provider == "deepseek":   # #242: same checks and order as llm._deepseek
        client = client or llm.deepseek_client()
        resp = llm.deepseek_create(client, deepseek_plan_request(q, cap))
        call, stop, usage, payload = llm.deepseek_tool_call(resp, PLAN_TOOL)
        msg = payload if isinstance(payload, dict) else {}
        meta["stop_reason"], meta["usage"] = stop, usage
        meta["reasoning_content"] = msg.get("reasoning_content")
        if stop in llm.CUT_REASONS:
            raise PlannerOutputError("planner output cut at max_tokens", payload, stop)
        if stop not in llm.DEEPSEEK_OK:
            raise PlannerOutputError(f"planner output stopped by finish_reason {stop}", payload, stop)
        if call is None:
            raise PlannerOutputError(f"planner did not call {PLAN_TOOL} (finish_reason={stop})", payload, stop)
        try:
            return llm.deepseek_arguments(call)
        except (TypeError, ValueError) as e:
            raise PlannerOutputError(f"planner arguments are not a JSON object: {e}",
                                     call.function.arguments, stop) from e
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def model_for(provider: str) -> str:
    s = settings()
    return {"anthropic": s.llm_model, "openai": s.openai_model,
            "deepseek": s.deepseek_model}.get(provider, provider)


def from_output(q: Query, raw, provider: str, cap: int, error: str | None = None) -> Plan:
    """A Plan from a saved or fresh planner output (raw), or the fallback when it is not usable
    (`error` set: the call failed or its output was rejected before validation)."""
    model = model_for(provider)
    if error is None:
        try:
            parts, notes = validate_plan(raw, q, cap)
            return Plan(parts=parts, source="model", provider=provider, model=model, corrections=notes,
                        raw=raw, calls=1)
        except PlannerOutputError as e:
            error = str(e)
    plan = rules_plan(q, cap)
    plan.source, plan.provider, plan.model, plan.error, plan.raw, plan.calls = \
        "fallback", provider, model, error, raw, 1
    return plan


def plan_question(q: Query, provider: str | None = None, client=None, cap: int | None = None) -> Plan:
    """The plan for a resolved question. The rule plan (0 calls) on the mock provider, with
    PLANNER=off, or when code skips search; else one planner call, validated, with the rule plan
    as fallback when the output is not usable or the call fails (the call still counts)."""
    provider = provider or settings().llm_provider
    cap = max_parts() if cap is None else cap
    if fts.budget_tokens(q) is None:   # passage mode: no shares, one whole-question part
        return Plan(parts=[Part("p1", q.question, list(q.entities))])
    if provider == "mock" or not settings().planner or not fts.searchable(q):
        return rules_plan(q, cap)
    from cee.answer.llm import ProviderStop

    try:
        raw = call_planner(q, provider, cap, client)
    except PlannerOutputError as e:
        return from_output(q, e.raw, provider, cap, error=str(e))
    except ProviderStop:   # #242: 401 / 402 / 429 stop the question, never a silent rule plan
        raise
    except Exception as e:   # API / network error: the rule plan; the call still counts (ADR-020)
        return from_output(q, None, provider, cap, error=f"{type(e).__name__}: {e}")
    return from_output(q, raw, provider, cap)


def part_query(q: Query, part: Part) -> Query:
    """The resolved query for one part: its firms and words; every other field (window, themes,
    mode, firm filter, date range, keywords) from the question, and the question's doc-type scope."""
    return replace(q, entities=list(part.firms), terms=part.keyword_query, scope=fts.doc_type_scope(q),
                   theme_peers=[])


def search_parts(q: Query, plan: Plan, trace: PoolTrace | None = None,
                 part_pools: dict[str, set[str]] | None = None) -> list[Hit]:
    """Retrieve a plan (ADR-020): research once, the parts in order with equal shares of the token
    budget left (T - research - used so far, divided by the parts left), the theme peers once.
    Passage mode (TOKEN_BUDGET None) is one whole-question search. `part_pools` (eval) gets each
    part's candidate ids."""
    total = fts.budget_tokens(q)
    if total is None or not fts.searchable(q):
        hits = fts.search(q, trace=trace)
        for h in hits:
            h.part_id = "p1"
        return hits
    research = fts.research_pass(q, trace=trace)
    for h in research:
        h.part_id = "research"
    plan.research_tokens = sum(fts.hit_tokens(h) for h in research)
    kept = {h.chunk_id for h in research}
    used = 0.0
    out: list[Hit] = []
    plan.searched = []
    n = len(plan.parts)
    for i, part in enumerate(plan.parts):
        share = max(0.0, total - plan.research_tokens - used) / (n - i)
        part_trace = PoolTrace()
        hits = fts.search(part_query(q, part), trace=part_trace, tokens=share, exclude=kept,
                          research=False, peers=False)
        for h in hits:
            h.part_id = part.id
        size = sum(fts.hit_tokens(h) for h in hits)
        used += size
        kept |= {h.chunk_id for h in hits}
        out += hits
        if trace is not None:
            for name in ("firm", "on_theme", "answers", "unattached"):
                getattr(trace, name).extend(getattr(part_trace, name))
        if part_pools is not None:
            part_pools[part.id] = part_trace.ids()
        plan.searched.append({"id": part.id, "share": round(share), "passages": len(hits),
                              "tokens": round(size), "pool": len(part_trace.ids()),
                              "chunk_ids": [h.chunk_id for h in hits]})
    out += research
    peers = fts.peer_pass(q, kept, trace=trace)
    for h in peers:
        h.part_id = "peers"
    out += peers
    if q.window:  # recency questions read newest first (Q26)
        out.sort(key=lambda h: h.published_at, reverse=True)
    return out


def describe_plan(plan: Plan) -> str:
    """'2 parts: p1 MS; p2 RJF' for the Ask page trace."""
    def part(p: Part) -> str:
        return f"{p.id} {', '.join(p.firms) or 'all sources'}"
    n = len(plan.parts)
    return f"{n} part{'' if n == 1 else 's'}: " + "; ".join(part(p) for p in plan.parts)
