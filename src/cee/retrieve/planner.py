"""Question planner: sub-question decomposition (#245, ADR-021 rule 6; ADR-020 as amended).

One planner call (the configured provider, the answer model; prompt plan-v3) lists every aspect the
question asks about, literally: no merging and no cap. Code, not the model, decides the firms
(firm_scope): the firms resolve() found and, for a home-firm market question (ADR-018's home-firm
theme rule, Q19), the competitors on the theme as real entities. An aspect may carry a subset of
those firms when the question itself asks it of some of them (TL decision D3, Q12, Q15); code
validates the subset. Code expands each aspect over its firms into SubQuestion(entity, aspect).
The window, themes and Ask page filters are not in the planner's schema; code removes configured
neighbour phrases from the search words (strip_neighbours, #224). The mock provider, PLANNER=off,
an unsearchable question and an unusable output use the rule plan: one whole-question aspect for
every scoped firm. Tests and CI make 0 calls.

Retrieval (search_subquestions): research once (<= THEME_K passages, outside the sub-question
budgets), then every sub-question with its own token budget (SUBQUESTION_TOKENS) through
`search_fn` (default fts.search; exp/hybrid passes its own), each a copy of the resolved query with
its firm and words, so entity / segment, window, date range, keywords and the doc-type scope stay
SQL filters. Chunks kept earlier are excluded later. Competitor sub-questions search on the theme
only, and a floor across the competitors of one aspect drops their low chunks (ADR-018 safeguards).
corrective_search is the re-search hook of #246 (CRAG): one sub-question with extra words and an
exclude set, every filter kept.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache

import yaml

from cee.config import REPO_ROOT, entities_config, settings
from cee.retrieve import fts
from cee.retrieve.fts import Hit, PoolTrace, Query

PLANNER_VERSION = "plan-v3.1"   # #246: + proxy per aspect; v3 #245: aspects, literal, no cap (v2: #224, v1: #214)
PLANNER_MAX_TOKENS = 8000     # #245: no aspect cap, so a long plan needs room (was 2000)
PLAN_TOOL = "submit_plan"
MAX_QUERY_CHARS = 400
KINDS = ("fact", "comparison", "recency", "series")
METRIC_DEFINITIONS = REPO_ROOT / "config" / "metric_definitions.yaml"

PLANNER_PROMPT = """You plan the document search for a question about wealth-management firms.
The search engine runs one full-text search per aspect and firm, over filings, earnings calls,
investor decks, press releases, Form ADV brochures, trade press and research reports. Code chooses
the firms (listed below, each with how code found it), searches every aspect you list once for each
of its firms, and applies the firm filters, the time window and every other filter. You only list
the aspects, their search words and, when the question restricts an aspect, its firms.

List the aspects literally. An aspect is one thing the question asks about. List every one, in the
order the question asks them:
- each item of a list, each "and" joining two asks, each metric or dimension the question names;
- what the question asks without naming it. Example: "What is Firm X's plan for its
  retirement-plan unit?" also asks how management describes the unit, the priorities it states,
  the competition it names, and where it says it is losing ground or pulling back. Example: "How do
  Firm X and Firm Y each handle branch staffing?" asks whom they hire, how they pay them, how they
  train them, and the results they report (staff numbers, departures);
- a figure that may not be disclosed also asks for the closest figure that is disclosed, as its
  own aspect, marked proxy;
- a judgement the question asks for across firms or periods (whether figures can be set side by
  side, which firm says the most) is its own aspect of kind comparison.
Never merge two aspects into one, never drop one, and do not stop at any number: a question with
twelve asks has twelve aspects. Do not add an aspect the question does not ask. Write no firm
names in an aspect's text or words.

Firms of an aspect. Leave firms empty when the question asks the aspect of every listed firm; code
then searches it for all of them. Fill firms with IDs from the list only when the question itself
asks the aspect of some of them. Example: "Firm X's fee levels and the hiring plans of the firms
found through a group phrase" asks the fee levels of Firm X only and the hiring plans of those
group firms only. Competitors on the theme are searched for every aspect unless the question
itself restricts it.

Same concept only. Search words name the asked concept: the words filings and calls use for it and
its exact synonyms. Never add a different figure that shares a word with it, even as context (a
ratio paid to shareholders is not staff pay; company-wide staff turnover is not one unit's
turnover; deposits are not client assets). The closest disclosed figure for an undisclosed one is
its own aspect, never words in the asked figure's aspect.

For each aspect give:
- id: a short label (code renumbers);
- text: what the aspect asks, in one sentence, without firm names;
- keyword_query: 5 to 25 words the documents themselves would use for this aspect (filing and
  earnings-call vocabulary, synonyms, the names of the metrics and disclosures), with no firm names
  and no dates;
- firms: firm IDs from the list when the question restricts the aspect to them, else an empty list;
- metric: one of {metrics} when the aspect asks for exactly that registered metric, else "";
- kind: fact (a disclosed fact or figure), series (a figure over several periods), recency (what is
  new inside the time window), comparison (a judgement across firms or periods);
- proxy: true when the aspect asks for a stand-in for what the question asks (the closest disclosed
  figure, a numerator or denominator to compute it, the nearest measure); false for everything the
  question asks itself.
Return the plan by calling the {tool} tool; do not answer the question."""


class PlannerOutputError(RuntimeError):
    """The planner's output is not a usable plan (no tool call, wrong shape, cut off)."""

    def __init__(self, message: str, raw=None, stop_reason: str | None = None):
        super().__init__(message)
        self.raw, self.stop_reason = raw, stop_reason


@dataclass
class Part:
    """The answer side's view of one sub-question (prompt v4.1 grouping, check_parts, eval keys)."""
    id: str
    text: str
    firms: list[str] = field(default_factory=list)
    keyword_query: str | None = None   # None = the question's own words (fts.keyword_terms)


@dataclass
class Aspect:
    """One thing the question asks (planner v3 or the rule plan)."""
    id: str                            # a1..aM, set by code in order
    text: str
    keyword_query: str | None = None   # None = the question's own words
    metric: str | None = None          # a key of config/metric_definitions.yaml
    kind: str = "fact"                 # fact | comparison | recency | series
    firms: list[str] = field(default_factory=list)   # D3: subset of firm_scope(q); empty = all
    proxy: bool = False                # #246 plan-v3.1: a stand-in for the asked quantity (never rule 1a)
    # #247 part 2: the planner's validated firm subset before the home-firm "competitors kept"
    # widening (Q19): code gaps only inside it. Not in any cache key.
    asked_firms: list[str] = field(default_factory=list)


@dataclass
class SubQuestion:
    """SubQuestion(entity, aspect): one firm (None in theme mode) x one aspect (ADR-021 rule 6)."""
    id: str                            # "<aspect id>.<entity>", e.g. "a2.EDJ"; theme mode "a1.all"
    entity: str | None
    aspect: Aspect
    role: str = "named"                # named | competitor | all
    part_firms: list[str] | None = None   # Plan.from_parts only: the Part's firms as given
    part_text: str | None = None          # Plan.from_parts only: the Part's text as given

    @property
    def firms(self) -> list[str]:
        if self.part_firms is not None:
            return list(self.part_firms)
        return [self.entity] if self.entity else []

    @property
    def text(self) -> str:
        if self.part_text is not None:
            return self.part_text
        if not self.entity:
            return self.aspect.text
        return f"{firm_name(self.entity)}: {self.aspect.text}"

    def to_log(self) -> dict:
        return {"id": self.id, "entity": self.entity, "aspect": self.aspect.id, "role": self.role}


@dataclass
class Plan:
    aspects: list[Aspect] = field(default_factory=list)
    subquestions: list[SubQuestion] = field(default_factory=list)
    source: str = "rules"           # rules | model | fallback
    provider: str = "rules"
    model: str | None = None
    version: str = PLANNER_VERSION
    corrections: list[str] = field(default_factory=list)
    error: str | None = None
    raw: object = None              # the model's output (or payload), JSON-safe
    calls: int = 0                  # paid planner calls (0 or 1)
    usage: dict | None = None       # #248: the planner call's usage (app path), for the cost
    finished_at: str | None = None  # #248: when the planner call ended, offset-aware
    searched: list[dict] = field(default_factory=list)   # per sub-question (search_subquestions)
    research_tokens: float = 0.0
    competitor_floor: dict[str, float] = field(default_factory=dict)   # aspect id -> rank floor
    # #246: each sub-question's candidate pool ids (PoolTrace.ids(), the value part_pools gets), for
    # the map's retrieved-set check; not in to_log() (the pool size is logged in `searched`)
    pools: dict[str, set[str]] = field(default_factory=dict)

    @property
    def parts(self) -> list[Part]:
        """One Part per sub-question: what the interim answer call (prompt v4.1) and its checks read."""
        return [Part(s.id, s.text, s.firms, s.aspect.keyword_query) for s in self.subquestions]

    @classmethod
    def from_parts(cls, parts: list[Part], **kw) -> "Plan":
        """A plan from Parts as given (tests, passage mode): one aspect and one sub-question per
        Part, ids, texts and firms kept."""
        aspects, subs = [], []
        for p in parts:
            a = Aspect(p.id, p.text, p.keyword_query, firms=list(p.firms))
            aspects.append(a)
            subs.append(SubQuestion(p.id, p.firms[0] if len(p.firms) == 1 else None, a,
                                    "named" if p.firms else "all", part_firms=list(p.firms), part_text=p.text))
        return cls(aspects=aspects, subquestions=subs, **kw)

    def to_log(self) -> dict:
        return {"source": self.source, "provider": self.provider, "model": self.model,
                "version": self.version, "aspects": [asdict(a) for a in self.aspects],
                "subquestions": [s.to_log() for s in self.subquestions],
                "parts": [asdict(p) for p in self.parts],
                "corrections": self.corrections, "error": self.error, "calls": self.calls,
                "usage": self.usage, "finished_at": self.finished_at,
                "searched": self.searched, "research_tokens": round(self.research_tokens),
                "competitor_floor": {k: round(v, 4) for k, v in self.competitor_floor.items()},
                "raw": self.raw}


# --- firms, decided by code --------------------------------------------------------------------

def firm_name(entity: str) -> str:
    return next((e["name"] for e in entities_config()["entities"] if e["id"] == entity), entity)


def firm_scope(q: Query) -> list[tuple[str | None, str]]:
    """[(entity, role)]: the resolved firms (role named) in resolve order, then, for a home-firm
    market question (q.theme_peers set: ADR-018's home-firm theme rule, Q19), the competitors on
    the theme (role competitor). Theme mode (no firm named): [(None, "all")]. Firms we hold no
    documents for are not searched (the gap path names them)."""
    scope: list[tuple[str | None, str]] = [(e, "named") for e in q.entities]
    scope += [(e, "competitor") for e in q.theme_peers if e not in q.entities]
    return scope or [(None, "all")]


def firm_origins(q: Query) -> list[tuple[str, str]]:
    """[(entity, how code found it)] for the planner message (D3): named; through "<phrase>" (a
    peer phrase, e.g. "an advisor-led model" in Q15, "the five" in Q22); competitor on the theme
    (Q19); chosen by the firm filter."""
    cfg = entities_config()
    by_id = {e["id"]: e for e in cfg["entities"]}
    out = []
    for entity, role in firm_scope(q):
        if entity is None:
            continue
        if role == "competitor":
            out.append((entity, "competitor on the theme"))
            continue
        if fts._mentions(q.question, by_id[entity]):
            out.append((entity, "named"))
            continue
        phrase = next((m.group(0) for s in cfg.get("peer_sets", []) if entity in s["members"]
                       for p in sorted(s["phrases"], key=len, reverse=True)
                       if (m := fts._phrase_pattern(p).search(q.question))), None)
        out.append((entity, f'through "{phrase}"' if phrase else "chosen by the firm filter"))
    return out


def subquestions(q: Query, aspects: list[Aspect]) -> list[SubQuestion]:
    """Each aspect over its own firm set (aspect.firms, or every scoped firm), firm-major order:
    each scoped firm, then the aspects that include it. No cap."""
    out = []
    for entity, role in firm_scope(q):
        for a in aspects:
            if a.firms and entity not in a.firms:
                continue
            out.append(SubQuestion(f"{a.id}.{entity or 'all'}", entity, a, role))
    return out


# --- rule plan ---------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def metric_keys() -> tuple[str, ...]:
    """The registered metrics of config/metric_definitions.yaml (the schema's `metric` enum)."""
    data = yaml.safe_load(METRIC_DEFINITIONS.read_text(encoding="utf-8")) or {}
    return tuple(sorted({d["metric"] for d in data.get("definitions") or [] if d.get("metric")}))


def rule_metric(question: str) -> str | None:
    """The registered metric whose words (underscores as spaces) the question contains."""
    return next((k for k in metric_keys() if fts._phrase_pattern(k.replace("_", " ")).search(question)), None)


def rules_plan(q: Query) -> Plan:
    """The deterministic plan: one aspect a1 = the whole question (its own words), kind recency
    with a time window else fact, the metric the question names; for every scoped firm."""
    a = Aspect("a1", q.question, None, rule_metric(q.question), "recency" if q.window else "fact")
    return Plan(aspects=[a], subquestions=subquestions(q, [a]))


# --- validation of a model plan ----------------------------------------------------------------

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


def _aspect_firms(item_firms, q: Query, n: int, notes: list[str], asked: list[str] | None = None) -> list[str]:
    """The aspect's firm subset (D3), validated: IDs, names or aliases mapped; firms outside the
    scope dropped; nothing left -> all; on a home-firm market question a list equal to the named
    firms counts as empty, so the competitors stay (Q19)."""
    if not isinstance(item_firms, list) or not item_firms:
        return []
    scoped = [e for e, _ in firm_scope(q) if e]
    firms: list[str] = []
    for f in item_firms:
        fid, _ = _firm_id(f)
        if fid is None or fid not in scoped:
            notes.append(f"aspect {n}: firm {f} not in scope")
        elif fid not in firms:
            firms.append(fid)
    if not firms:
        notes.append(f"aspect {n}: no firm in scope, all firms")
        return []
    if q.theme_peers and set(firms) == set(q.entities):
        notes.append(f"aspect {n}: named firms only on a home-firm market question, competitors kept")
        if asked is not None:
            asked[:] = [e for e in scoped if e in firms]
        return []
    if set(firms) == set(scoped):
        return []
    out = [e for e in scoped if e in firms]   # scope order
    if asked is not None:
        asked[:] = out
    return out


def validate_plan(raw, q: Query) -> tuple[list[Aspect], list[str]]:
    """The model's aspects corrected by code (ADR-021 rule 6); PlannerOutputError when not usable.
    No cap, no merge, no dedupe: 100 aspects stay 100."""
    if not isinstance(raw, dict) or not isinstance(raw.get("aspects"), list) or not raw["aspects"]:
        raise PlannerOutputError("planner output has no aspects", raw)
    notes: list[str] = []
    aspects: list[Aspect] = []
    metrics = set(metric_keys())
    for n, item in enumerate(raw["aspects"], 1):
        if not isinstance(item, dict):
            raise PlannerOutputError("an aspect is not an object", raw)
        text = str(item.get("text") or "").strip()
        if not text:
            text = q.question
            notes.append(f"aspect {n}: no text, the question")
        words = str(item.get("keyword_query") or "").strip()
        if not words:
            words = text
            notes.append(f"aspect {n}: no search words")
        elif len(words) > MAX_QUERY_CHARS:
            words = _cut(words)
            notes.append(f"aspect {n}: search words cut")
        words, dropped = strip_neighbours(words, q.question)
        notes += [f"aspect {n}: dropped neighbour phrase {d}" for d in dropped]
        if dropped and not words:
            words = None
            notes.append(f"aspect {n}: no search words left")
        metric = str(item.get("metric") or "").strip() or None
        if metric is not None and metric not in metrics:
            notes.append(f"aspect {n}: unknown metric {metric}")
            metric = None
        kind = str(item.get("kind") or "").strip()
        if kind not in KINDS:
            notes.append(f"aspect {n}: unknown kind {kind or '(none)'}, fact")
            kind = "fact"
        asked: list[str] = []
        firms = _aspect_firms(item.get("firms"), q, n, notes, asked)
        proxy = item.get("proxy")
        if not isinstance(proxy, bool):   # #246: strict prevents it; covers replays and fallbacks
            notes.append(f"aspect {n}: proxy missing or not a boolean, false")
            proxy = False
        aspects.append(Aspect(f"a{n}", text, words, metric, kind, firms, proxy, asked_firms=asked))
    return aspects, notes


# --- requests ----------------------------------------------------------------------------------

def plan_schema(strict: bool = False) -> dict:
    """strict=True: the OpenAI and DeepSeek (#242) schema (no array limits). strict=False: the
    Anthropic tool's schema, also sent with strict: true since #232 (minItems 0 or 1, no maxItems).
    `metric` is an enum with "" for none, so no nullable type is needed on any path."""
    aspect = {"type": "object",
              "properties": {"id": {"type": "string"}, "text": {"type": "string"},
                             "keyword_query": {"type": "string"},
                             "firms": {"type": "array", "items": {"type": "string"}},
                             "metric": {"type": "string", "enum": ["", *metric_keys()]},
                             "kind": {"type": "string", "enum": list(KINDS)},
                             "proxy": {"type": "boolean"}},   # #246 plan-v3.1
              "required": ["id", "text", "keyword_query", "firms", "metric", "kind", "proxy"],
              "additionalProperties": False}
    aspects = {"type": "array", "items": aspect}
    if not strict:
        aspects |= {"minItems": 1}
    return {"type": "object", "properties": {"aspects": aspects}, "required": ["aspects"],
            "additionalProperties": False}


def planner_message(q: Query) -> str:
    origins = firm_origins(q)
    firms = "; ".join(f"{f} ({firm_name(f)}): {how}" for f, how in origins) or "none named (all sources)"
    lines = [f"Question: {q.question}", f"Firms (chosen by code; IDs to use in firms): {firms}"]
    if q.window:
        lines.append(f"Time window (applied by code): {q.window[0]} to {q.window[1]}")
    if q.themes:
        lines.append(f"Themes: {fts.theme_label(q)}")
    return "\n".join(lines)


def system_prompt() -> str:
    return PLANNER_PROMPT.format(metrics=", ".join(metric_keys()), tool=PLAN_TOOL)


def anthropic_plan_request(q: Query) -> dict:
    return {
        "model": settings().llm_model,
        "max_tokens": PLANNER_MAX_TOKENS,
        "system": system_prompt(),
        "tools": [{"name": PLAN_TOOL, "description": "Submit the search plan.", "strict": True,   # #232
                   "input_schema": plan_schema()}],
        "tool_choice": {"type": "auto"},
        "messages": [{"role": "user", "content": planner_message(q)}],
    }


def openai_plan_request(q: Query) -> dict:
    return {
        "model": settings().openai_model,
        "messages": [{"role": "system", "content": system_prompt() + "\nReturn JSON matching the schema."},
                     {"role": "user", "content": planner_message(q)}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "plan", "strict": True, "schema": plan_schema(strict=True)}},
    }


def planner_max_tokens(provider: str) -> int:
    """The planner call's output cap (#242): by thinking mode for deepseek, else PLANNER_MAX_TOKENS."""
    if provider == "deepseek":
        from cee.answer.llm import DEEPSEEK_PLANNER_MAX_TOKENS
        return DEEPSEEK_PLANNER_MAX_TOKENS[settings().deepseek_thinking]
    return PLANNER_MAX_TOKENS


def deepseek_plan_request(q: Query) -> dict:
    """#242: strict function submit_plan (OpenAI strict schema: no array limits), explicit max_tokens."""
    from cee.answer.llm import deepseek_tool_request
    return deepseek_tool_request(PLAN_TOOL, "Submit the search plan.", plan_schema(strict=True),
                                 system_prompt(), planner_message(q), planner_max_tokens("deepseek"))


def _block_dict(b) -> dict:
    from cee.answer.llm import _block_dict as block
    return block(b)


def call_planner(q: Query, provider: str, client=None, meta: dict | None = None):
    """The raw plan from one provider call; PlannerOutputError when the output is not a plan.
    `meta` (#230, bookkeeping only): when a dict is passed, it gets the call's stop_reason and usage,
    so the eval saves why every real output stopped."""
    from cee.answer import llm

    meta = {} if meta is None else meta
    if provider == "anthropic":
        client = client or llm.anthropic_client()
        resp = client.messages.create(**anthropic_plan_request(q))
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
        resp = client.chat.completions.create(**openai_plan_request(q))
        content = resp.choices[0].message.content
        stop = getattr(resp.choices[0], "finish_reason", None)
        meta["stop_reason"] = stop
        meta["usage"] = llm._usage(resp, "prompt_tokens", "completion_tokens")
        if stop in llm.CUT_REASONS:   # #242: a cut plan is never trusted, even when it parses
            raise PlannerOutputError("planner output cut at max_tokens", content, stop)
        flags: list = []
        try:
            out = llm.loads_object(content, flags)   # #246: stray closing braces accepted, flagged
        except (TypeError, ValueError) as e:
            raise PlannerOutputError(f"planner output is not JSON: {e}", content) from e
        if flags:
            meta["parse_flags"] = flags
        return out
    if provider == "deepseek":   # #242: same checks and order as llm._deepseek
        client = client or llm.deepseek_client()
        resp = llm.deepseek_create(client, deepseek_plan_request(q))
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
        flags: list = []
        try:
            out = llm.deepseek_arguments(call, flags)   # #246: stray closing braces accepted, flagged
        except (TypeError, ValueError) as e:
            raise PlannerOutputError(f"planner arguments are not a JSON object: {e}",
                                     call.function.arguments, stop) from e
        if flags:
            meta["parse_flags"] = flags
        return out
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def model_for(provider: str) -> str:
    s = settings()
    return {"anthropic": s.llm_model, "openai": s.openai_model,
            "deepseek": s.deepseek_model}.get(provider, provider)


def from_output(q: Query, raw, provider: str, error: str | None = None) -> Plan:
    """A Plan from a saved or fresh planner output (raw), or the fallback when it is not usable
    (`error` set: the call failed or its output was rejected before validation)."""
    model = model_for(provider)
    if error is None:
        try:
            aspects, notes = validate_plan(raw, q)
            return Plan(aspects=aspects, subquestions=subquestions(q, aspects), source="model",
                        provider=provider, model=model, corrections=notes, raw=raw, calls=1)
        except PlannerOutputError as e:
            error = str(e)
    plan = rules_plan(q)
    plan.source, plan.provider, plan.model, plan.error, plan.raw, plan.calls = \
        "fallback", provider, model, error, raw, 1
    return plan


def passage_plan(q: Query) -> Plan:
    """Passage mode (TOKEN_BUDGET None, an explicit k): one whole-question part, no planner call."""
    return Plan.from_parts([Part("p1", q.question, list(q.entities))])


def plan_question(q: Query, provider: str | None = None, client=None) -> Plan:
    """The plan for a resolved question. The rule plan (0 calls) on the mock provider, with
    PLANNER=off, or when code skips search; else one planner call, validated, with the rule plan
    as fallback when the output is not usable or the call fails (the call still counts)."""
    provider = provider or settings().llm_provider
    if fts.budget_tokens(q) is None:
        return passage_plan(q)
    if provider == "mock" or not settings().planner or not fts.searchable(q):
        return rules_plan(q)
    from cee.answer.llm import ProviderStop

    meta: dict = {}

    def stamped(plan: Plan) -> Plan:   # #248: usage and completion time, for the logged cost
        plan.usage, plan.finished_at = meta.get("usage"), dt.datetime.now().astimezone().isoformat()
        return plan

    try:
        raw = call_planner(q, provider, client, meta=meta)
    except PlannerOutputError as e:
        return stamped(from_output(q, e.raw, provider, error=str(e)))
    except ProviderStop:   # #242: 401 / 402 / 429 stop the question, never a silent rule plan
        raise
    except Exception as e:   # API / network error: the rule plan; the call still counts (ADR-020)
        return stamped(from_output(q, None, provider, error=f"{type(e).__name__}: {e}"))
    return stamped(from_output(q, raw, provider))


# --- retrieval ---------------------------------------------------------------------------------

def subquestion_query(q: Query, sq: SubQuestion) -> Query:
    """The resolved query for one sub-question: its firm and words; every other field (window,
    themes, mode, firm filter, date range, keywords) from the question, and the question's doc-type
    scope; competitors on the theme only."""
    return replace(q, entities=sq.firms, terms=sq.aspect.keyword_query, scope=fts.doc_type_scope(q),
                   theme_peers=[], on_theme_only=sq.role == "competitor")


def _floor_value(hits: list[Hit]) -> float | None:
    """fts.peer_floor's cut as a value: FLOOR x the FLOOR_BASE-th best rank (its lowest with fewer)."""
    ranks = sorted((h.rank for h in hits), reverse=True)
    if not ranks:
        return None
    return fts.FLOOR * ranks[min(fts.FLOOR_BASE, len(ranks)) - 1]


PERIOD_K = 3   # #247 part 2: passages per asked period in the per-period sub-search
PIN_MAX = 8    # #247 part 2: pinned ids per sub-question (population sources first)


def pinned_ids(entity: str | None, aspect: Aspect) -> tuple[list[str], list[str]]:
    """(ids to pin, ids cut at PIN_MAX) for one sub-question (#247 part 2, TL conditions 2-3): the
    firm's population sources for the ratio inputs this aspect can hold, then its registered definition
    chunk and see_also for a registered metric. Ids are not filtered here (fetch_pinned applies the
    sub-question's SQL filters, so "same firm" = passes the entity filter)."""
    from cee.answer.matrix import metric_definition, population_entries
    if not entity:
        return [], []
    ids = [p["chunk_id"] for p in population_entries(entity, aspect) if p.get("chunk_id")]
    d = metric_definition(entity, aspect.metric) if aspect.metric else None
    if d:
        ids += [d.get("chunk_id")] if d.get("chunk_id") else []
        ids += list(d.get("see_also") or [])
        if aspect.kind == "series":   # #247 part 4 item 10: dated counts in undated documents (Q23 RJF)
            ids += list(d.get("series_pins") or [])
    ids = list(dict.fromkeys(ids))
    return ids[:PIN_MAX], ids[PIN_MAX:]


def _period_bounds(period: str):
    """An asked period ("2025Q4" or "2025") as (first day, last day)."""
    import datetime as dt
    if "Q" in period:
        y, n = int(period[:4]), int(period[-1])
        start = dt.date(y, 3 * n - 2, 1)
        end = dt.date(y + (n == 4), (3 * n) % 12 + 1, 1) - dt.timedelta(days=1)
        return start, end
    y = int(period)
    return dt.date(y, 1, 1), dt.date(y, 12, 31)


def _extra_passes(q: Query, plan: Plan, kept: set[str], as_of, period_fn, pin_fn) -> dict[str, list[Hit]]:
    """#247 part 2: after every main search, per sub-question the per-period sub-search (series
    aspects with asked periods) and the pinned registered chunks; every chunk kept so far excluded
    (in the SQL pool for the period search), added on top of the budget."""
    from cee.answer.matrix import asked_periods
    asked = asked_periods(q.question, as_of)
    out: dict[str, list[Hit]] = {}
    for sq in plan.subquestions:
        sub = subquestion_query(q, sq)
        added: list[Hit] = []
        entry = next(e for e in plan.searched if e["id"] == sq.id)
        entry["period_hits"], entry["pinned"], entry["pins_cut"] = [], [], []
        if sq.aspect.kind == "series" and asked and not q.window and sq.entity:
            for period in asked[1]:
                hits = period_fn(replace(sub, period_range=_period_bounds(period), exclude_ids=sorted(kept)),
                                 k=PERIOD_K, research=False, peers=False, text=sq.text)
                for h in hits:
                    if h.chunk_id in kept:
                        continue
                    h.part_id, h.origin = sq.id, "period"
                    kept.add(h.chunk_id)
                    added.append(h)
                    entry["period_hits"].append(f"{period}:{h.chunk_id}")
        ids, cut = pinned_ids(sq.entity, sq.aspect)
        entry["pins_cut"] = cut
        shared: set[str] = set()
        if ids:
            # every registered id passing this sub-question's filters joins its pool; a chunk another
            # sub-question already kept is not repeated as a hit, but still counts as retrieved here
            for h in pin_fn(sub, ids):
                entry["pinned"].append(h.chunk_id)
                if h.chunk_id in kept:
                    shared.add(h.chunk_id)
                    continue
                h.part_id, h.origin = sq.id, "pinned"
                kept.add(h.chunk_id)
                added.append(h)
        if added:
            out[sq.id] = added
        if added or shared:
            plan.pools[sq.id] = set(plan.pools.get(sq.id, set())) | {h.chunk_id for h in added} | shared
    return out


def search_subquestions(q: Query, plan: Plan, search_fn=None, research_fn=None,
                        trace: PoolTrace | None = None, part_pools: dict[str, set[str]] | None = None,
                        tokens: float | None = None, as_of=None, period_fn=None, pin_fn=None) -> list[Hit]:
    """Retrieve a plan (#245, ADR-021 rule 6): research once (outside the sub-question budgets), then
    every sub-question in plan order through `search_fn` with its own budget (`tokens`, default
    SUBQUESTION_TOKENS) and every SQL filter; chunks kept earlier excluded; competitor sub-questions
    on the theme only, then cut at a floor across the competitors of each aspect. Passage mode
    (TOKEN_BUDGET None) and unsearchable questions: one whole-question search. `part_pools` (eval)
    gets each sub-question's candidate ids. Hits carry part_id = the sub-question id or "research"."""
    search_fn = search_fn or fts.search
    research_fn = research_fn or fts.research_pass
    if fts.budget_tokens(q) is None or not fts.searchable(q):
        hits = search_fn(q, trace=trace)
        for h in hits:
            h.part_id = plan.subquestions[0].id if len(plan.subquestions) == 1 else "p1"
        return hits
    budget = settings().subquestion_tokens if tokens is None else tokens
    research = research_fn(q, trace=trace)
    for h in research:
        h.part_id = "research"
    plan.research_tokens = sum(fts.hit_tokens(h) for h in research)
    kept = {h.chunk_id for h in research}
    by_sub: dict[str, list[Hit]] = {}
    plan.searched, plan.competitor_floor, plan.pools = [], {}, {}
    for sq in plan.subquestions:
        sub_trace = PoolTrace()
        hits = search_fn(subquestion_query(q, sq), trace=sub_trace, tokens=budget, exclude=kept,
                         research=False, peers=False, text=sq.text)
        for h in hits:
            h.part_id = sq.id
        by_sub[sq.id] = hits
        kept |= {h.chunk_id for h in hits}
        if trace is not None:
            for name in ("firm", "on_theme", "answers", "unattached"):
                getattr(trace, name).extend(getattr(sub_trace, name))
        plan.pools[sq.id] = sub_trace.ids()
        if part_pools is not None:
            part_pools[sq.id] = plan.pools[sq.id]
        plan.searched.append({"id": sq.id, "entity": sq.entity, "aspect": sq.aspect.id, "role": sq.role,
                              "budget": round(budget), "pool": len(sub_trace.ids()),
                              "floor_dropped": [], "floor_emptied": False})
    _competitor_floor(plan, by_sub)
    kept = {h.chunk_id for hs in by_sub.values() for h in hs} | {h.chunk_id for h in research}
    # A fake search (tests) gets no database pin fetch unless one is given
    pin_fn = pin_fn or (fts.fetch_pinned if search_fn is fts.search else (lambda _q, _ids: []))
    extra = _extra_passes(q, plan, kept, as_of, period_fn or search_fn, pin_fn)
    for sq_id, hs in extra.items():
        by_sub[sq_id] = by_sub[sq_id] + hs
        if part_pools is not None:
            part_pools[sq_id] = plan.pools[sq_id]
    out: list[Hit] = []
    for entry in plan.searched:
        hits = by_sub[entry["id"]]
        entry |= {"passages": len(hits), "tokens": round(sum(fts.hit_tokens(h) for h in hits)),
                  "chunk_ids": [h.chunk_id for h in hits]}
        out += hits
    out += research
    if q.window:  # recency questions read newest first (Q26)
        out.sort(key=lambda h: h.published_at, reverse=True)
    return out


def _competitor_floor(plan: Plan, by_sub: dict[str, list[Hit]]) -> None:
    """ADR-018's floor across the theme peers, per aspect: the competitor sub-questions' hits of one
    aspect are cut at FLOOR x their 2nd-best rank across all competitors (a firm whose only text on
    the theme is an advisor ranking keeps no slot). Dropped hits leave the list; a sub-question left
    with none is marked floor_emptied (its pool reads as 0 for the prompt and the gap wording)."""
    entries = {e["id"]: e for e in plan.searched}
    for a in plan.aspects:
        subs = [s for s in plan.subquestions if s.aspect.id == a.id and s.role == "competitor"]
        pool = [h for s in subs for h in by_sub.get(s.id, [])]
        floor = _floor_value(pool)
        if floor is None:
            continue
        plan.competitor_floor[a.id] = floor
        for s in subs:
            keep = [h for h in by_sub[s.id] if h.rank >= floor]
            dropped = [h.chunk_id for h in by_sub[s.id] if h.rank < floor]
            by_sub[s.id] = keep
            entries[s.id]["floor_dropped"] = dropped
            entries[s.id]["floor_emptied"] = bool(dropped) and not keep


def corrective_search(q: Query, plan: Plan, sq_id: str, extra_words: str, exclude: set[str],
                      search_fn=None, tokens: float | None = None) -> list[Hit]:
    """Re-search hook (#246, CRAG; ADR-021 rule 6): one sub-question again with its words (the
    question's own words for a rule-plan aspect) plus `extra_words`, neighbour phrases the question
    does not name removed, never a chunk in `exclude`, budget `tokens` (default SUBQUESTION_TOKENS).
    Every SQL filter of the sub-question is kept (entity / segment, window, date range, keywords,
    doc-type scope; competitors on the theme only and cut at the aspect's competitor floor); the
    window is never widened (adjacent periods enter as words). 0 model calls."""
    sq = next((s for s in plan.subquestions if s.id == sq_id), None)
    if sq is None:
        raise ValueError(f"no sub-question {sq_id} in the plan")
    search_fn = search_fn or fts.search
    base = sq.aspect.keyword_query or q.question
    words, _ = strip_neighbours(" ".join(f"{base} {extra_words or ''}".split()), q.question)
    sub_q = replace(subquestion_query(q, sq), terms=words or None)
    budget = settings().subquestion_tokens if tokens is None else tokens
    hits = search_fn(sub_q, tokens=budget, exclude=set(exclude), research=False, peers=False, text=sq.text)
    floor = plan.competitor_floor.get(sq.aspect.id) if sq.role == "competitor" else None
    hits = [h for h in hits if h.chunk_id not in exclude and (floor is None or h.rank >= floor)]
    for h in hits:
        h.part_id = sq.id
    return hits


def describe_plan(plan: Plan) -> str:
    """'1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.RJF' for the Ask page trace."""
    def n(k: int, word: str) -> str:
        return f"{k} {word}" + ("" if k == 1 else "s")
    ids = "; ".join(s.id if s.part_text is None else f"{s.id} {', '.join(s.firms) or 'all sources'}"
                    for s in plan.subquestions)
    firms = [s.entity for s in plan.subquestions if s.entity]
    scope = n(len(dict.fromkeys(firms)), "firm") if firms else "all sources"
    return f"{n(len(plan.aspects), 'aspect')} x {scope} = {n(len(plan.subquestions), 'sub-question')}: {ids}"
