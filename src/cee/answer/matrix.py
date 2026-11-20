"""Evidence matrix and the code rules of the map step (#246; ADR-021 rules 1, 2, 3).

The map extraction calls (cee.answer.extract, prompt extract-v1) label every firm x aspect cell
`fact`, `not_disclosed`, `not_found` or `different_quantity`, with items that cite retrieved chunks.
Code, not the model, then:
- verifies the within-firm derivations the model proposes (rule 1d, rule 2 within-firm) and computes
  their value;
- marks comparability per aspect from config/metric_definitions.yaml (rule 2): same basis, a
  different basis (the comparability caveat), or an unregistered metric (the "unverified" mark);
- decides the answer behavior (rule 1, with its precedence: forecast -> refuse, normative ->
  answer_with_boundary, then (a)-(c)); a proxy aspect (plan-v3.1: the closest disclosed figure, a
  numerator or denominator) never fires rule (a), it feeds the adjacent side; no fact plus a failed
  extraction leaves the behavior undecided, shown as incomplete, never as refuse (TL decision D5);
- builds the gap texts and the caveats (comparability and config/entities.yaml caveats).
The reduce step (#247) writes the answer from this matrix and cannot change the behavior.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import yaml

from cee.config import entities_config

LABELS = ("fact", "not_disclosed", "not_found", "different_quantity")   # the model's labels
CODE_LABELS = ("derived", "failed")                                     # set only by code
OPERATIONS = ("", "ratio", "sum", "difference")
HOLDS = ("fact", "derived")
CAVEAT_DEF_CHARS = 160   # TL decision D10: the entry's quote, cut at a word boundary

GAP_TEXT = {
    "not_disclosed": "{firm} - {aspect}: not disclosed in the documents searched.",
    "not_found": "{firm} - {aspect}: not found in the documents searched.",
    "different_quantity": "{firm} - {aspect}: not disclosed; a different quantity is listed as adjacent.",
    # #247 part 2 R6b: the closest figure named
    "closest": "{firm} - {aspect}: not published in the documents searched; the closest disclosed figure is {closest} (adjacent).",
    "failed": "{firm} - {aspect}: not extracted (the model output for this firm was invalid or the call failed).",
}
RESEARCHED_NOTHING = " A second search with wider words found nothing new."
NOT_SUPPORTED = "The database does not support this today: {aspect} ({firms})."
COMPARABILITY_CAVEAT = ("{metric}: the firms define it differently ({definitions}); figures are listed side "
                        "by side and not compared or combined (reporting risk).")
UNVERIFIED_MARK = "{metric} is not in the metric definitions file; its definition is unverified."
INCOMPLETE_NOTE = ("This answer is incomplete: the evidence for {firms} could not be extracted (the model "
                   "output was invalid or the call failed). Nothing is concluded about what {firms} disclose.")


@dataclass
class Item:
    text: str
    quote: str = ""
    chunk_ids: list[str] = field(default_factory=list)   # valid ids only (section 6 of the plan)
    value: str = ""
    unit: str = ""
    period: str = ""
    scope: str = ""
    definition: str = ""
    rejected_ids: list[str] = field(default_factory=list)   # outside the cell's retrieved set
    flags: list[str] = field(default_factory=list)   # unmatched_citation, quote_not_found, number_not_found, period_unparsed
    # #247 part 2 (code-set, tag_populations): the population key of a ratio input and the chunk that
    # states it (config/metric_definitions.yaml `populations`); "" = not registered for this item
    population: str = ""
    population_source: str = ""

    @property
    def counts(self) -> bool:
        return bool(self.chunk_ids)


@dataclass
class Cell:
    id: str                      # sub-question id ("a2.EDJ") or "<aspect>.research"
    entity: str | None           # None: research row or theme mode
    aspect_id: str
    role: str                    # named | competitor | all | research
    label: str                   # a model label, or derived / failed (code)
    source: str = "model"        # model | code | mock | reextract
    items: list[Item] = field(default_factory=list)
    differs_because: str = ""
    reason: str = ""
    flags: list[str] = field(default_factory=list)   # missing_cell, duplicate_cell, no_passages, definition_unverified
    derivation: dict | None = None   # the model's proposal; after derive(): + ok, why, value, formula, input_chunk_ids
    researched: bool = False
    research_hits: int = 0
    first: dict | None = None    # the round-1 cell when re-extracted
    error: str | None = None     # failed cells: why

    @property
    def counting_items(self) -> list[Item]:
        return [i for i in self.items if i.counts]

    @property
    def effective_label(self) -> str:
        """The label the rules read: a fact or a different quantity with no item left that cites a
        retrieved chunk reads as not_found (its rejected citations are flagged on the items)."""
        if self.label in ("fact", "different_quantity") and not self.counting_items:
            return "not_found"
        return self.label


@dataclass
class AspectMark:
    aspect_id: str
    metric: str | None
    status: str = "none"         # same_basis | different_basis | unverified | none
    firms: list[str] = field(default_factory=list)
    caveat: str | None = None
    mark: str | None = None
    shared_periods: list[str] = field(default_factory=list)


@dataclass
class EvidenceMatrix:
    question: str
    rows: list[str]
    aspects: list = field(default_factory=list)          # planner.Aspect, plan order
    cells: dict[str, Cell] = field(default_factory=dict)
    marks: dict[str, AspectMark] = field(default_factory=dict)
    behavior: str | None = None
    behavior_reason: str = ""
    incomplete_note: str | None = None
    gaps: list[dict] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    research: list[dict] = field(default_factory=list)
    version: str = "extract-v1"
    # #247 (B1): every passage the matrix may cite, retrieval and corrective re-search hits, by chunk
    # id (not logged: the ids are in cells and research). `corrective` = the re-search hits, in order.
    hits: dict = field(default_factory=dict, repr=False)
    corrective: list = field(default_factory=list, repr=False)
    # #247 part 2: each sub-question's retrieved set (plan.pools plus its hits), for the population
    # tagging rule "only a population chunk in the input cell's pool"; not logged
    pools: dict = field(default_factory=dict, repr=False)
    breaks: list[dict] = field(default_factory=list)   # basis breaks inside one firm's series (code)

    def aspect(self, aspect_id: str):
        return next(a for a in self.aspects if a.id == aspect_id)

    def chunk_ids(self) -> list[str]:
        """Every valid cited chunk id (items, derivation inputs and, #247 part 2, the population source
        chunks of every derivation proposal): what the reduce may cite (#247)."""
        out: list[str] = []
        for c in self.cells.values():
            for i in c.items:
                out += [x for x in i.chunk_ids if x not in out]
        for c in self.cells.values():
            out += [x for x in (c.derivation or {}).get("population_chunk_ids") or [] if x not in out]
        return out

    def counts(self) -> dict:
        labels: dict[str, int] = {}
        for c in self.cells.values():
            labels[c.effective_label] = labels.get(c.effective_label, 0) + 1
        rounds: dict[str, int] = {}
        for call in self.calls:
            if call.get("skipped"):
                continue
            key = "remap" if call.get("round") == 2 else "map"
            rounds[key] = rounds.get(key, 0) + 1
        return {"cells": len(self.cells), "labels": labels, "calls": rounds}

    def grid(self) -> list[str]:
        """One line per row: 'EDJ: a1 fact, a2 not_disclosed, ...' (logs, reports)."""
        lines = []
        for row in self.rows:
            cells = [c for c in self.cells.values() if (c.entity or ("research" if c.role == "research" else "all")) == row]
            lines.append(f"{row}: " + ", ".join(f"{c.aspect_id} {c.effective_label}" for c in cells))
        return lines

    def to_log(self) -> dict:
        return {"version": self.version, "question": self.question, "rows": self.rows,
                "aspects": [asdict(a) for a in self.aspects],
                "cells": {k: {**asdict(c), "effective_label": c.effective_label} for k, c in self.cells.items()},
                "marks": {k: asdict(m) for k, m in self.marks.items()},
                "behavior": self.behavior, "behavior_reason": self.behavior_reason,
                "incomplete_note": self.incomplete_note, "gaps": self.gaps, "caveats": self.caveats,
                "breaks": self.breaks,
                "calls": self.calls, "research": self.research, "counts": self.counts(), "grid": self.grid()}


# --- config -----------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _definitions() -> dict[tuple[str, str], dict]:
    from cee.retrieve.planner import METRIC_DEFINITIONS
    data = yaml.safe_load(METRIC_DEFINITIONS.read_text(encoding="utf-8")) or {}
    return {(d["entity"], d["metric"]): d for d in data.get("definitions") or []}


def metric_definition(entity: str | None, metric: str | None) -> dict | None:
    """The firm's entry in config/metric_definitions.yaml; a firm reported inside a parent (MER ->
    BAC, `parent` in config/entities.yaml) reads its parent's entry."""
    if not entity or not metric:
        return None
    defs = _definitions()
    if (entity, metric) in defs:
        return defs[(entity, metric)]
    parent = next((e.get("parent") for e in entities_config()["entities"] if e["id"] == entity), None)
    return defs.get((parent, metric)) if parent else None


# --- populations of ratio inputs (#247 part 2, TL conditions 1-3) -----------------------------------

POPULATION_INPUTS = ("client_assets", "advisor_headcount")
# The proxy-to-input rule (TL condition 2): a proxy aspect without a metric takes the inputs whose
# words are in its text or keyword query; none matched -> every input.
INPUT_WORDS = {"client_assets": ("client assets", "assets under", "aua", "aum", "client balances"),
               "advisor_headcount": ("advisor", "headcount", "representatives")}


@lru_cache(maxsize=1)
def _populations() -> tuple[dict, ...]:
    from cee.retrieve.planner import METRIC_DEFINITIONS
    data = yaml.safe_load(METRIC_DEFINITIONS.read_text(encoding="utf-8")) or {}
    return tuple(data.get("populations") or [])


def _config_entity(entity: str | None) -> str | None:
    """The entity whose config entries apply (MER -> BAC, `parent` in config/entities.yaml)."""
    if not entity:
        return None
    parent = next((e.get("parent") for e in entities_config()["entities"] if e["id"] == entity), None)
    return parent or entity


def population_inputs(aspect) -> list[str]:
    """The ratio inputs an aspect can hold (TL condition 2): its metric when that is an input; a proxy
    aspect: its metric's input, else the inputs named in its words, else every input; else none."""
    metric = getattr(aspect, "metric", None)
    if metric in POPULATION_INPUTS:
        return [metric]
    if not getattr(aspect, "proxy", False):
        return []
    if metric:
        return []
    words = f"{getattr(aspect, 'text', '')} {getattr(aspect, 'keyword_query', '') or ''}".lower()
    named = [k for k, ws in INPUT_WORDS.items() if any(re.search(rf"\b{re.escape(w)}", words) for w in ws)]
    return named or list(POPULATION_INPUTS)


def population_entries(entity: str | None, aspect) -> list[dict]:
    """The `populations` entries of a firm for the inputs this aspect can hold."""
    ent, inputs = _config_entity(entity), population_inputs(aspect)
    if not ent or not inputs:
        return []
    own = [p for p in _populations() if p.get("entity") in (entity, ent)]
    return [p for p in own if p.get("input") in inputs]


_DASHES = re.compile(r"[‐‑‒–—]")
_APPROX_BEFORE = re.compile(r"(?:approximately|about|around|nearly|close\s+to|more\s+than|over|at\s+least|roughly|"
                            r"almost|upwards\s+of|~|>|<|≈)\s*(?:US)?\$?\s*$", re.I)
_APPROX_AFTER = re.compile(r"^\s*(?:\+|[kK]\b|\s*plus\b)")
_CORE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _flat(text: str) -> str:
    return " ".join(_DASHES.sub("-", str(text or "")).split())


def _value_pos(item: Item) -> tuple[str, int, str]:
    """(the quote, the index of the item's figure in it or -1, the figure's digits)."""
    m = _CORE.search(item.value or "")
    core = m.group(0) if m else ""
    quote = _flat(item.quote)
    return quote, (quote.find(core) if core else -1), core


def approximate(item: Item) -> bool:
    """A figure given as an estimate or a bound, matched next to the figure only (round-1 note 1): the
    value field itself, or the words directly before the figure in its quote, or "+" / "K" right after."""
    v = _flat(item.value)
    m = _CORE.search(v)
    if m and (_APPROX_BEFORE.search(v[:m.start()]) or _APPROX_AFTER.match(v[m.end():])):
        return True
    quote, pos, core = _value_pos(item)
    if pos < 0:
        return False
    return bool(_APPROX_BEFORE.search(quote[:pos]) or _APPROX_AFTER.match(quote[pos + len(core):]))


def _match_entry(item: Item, entries: list[dict]) -> dict | None:
    """The entry whose match phrase stands nearest before the item's figure in its quote; when no phrase
    stands before it (or the figure is not in the quote) the whole quote and the item text are read
    (#247 part 2 R2: "We had 8,943 ... financial advisors"); a scope set on the entry must equal; two
    keys at the same distance -> none."""
    quote, pos, _ = _value_pos(item)
    whole = f"{quote} {_flat(item.text)}".lower()
    hay = quote[:pos].lower() if pos >= 0 else whole
    found = _match_in(hay, item, entries)
    if found is None and pos >= 0:
        found = _match_in(whole, item, entries)
    return found


def _match_in(hay: str, item: Item, entries: list[dict]) -> dict | None:
    best: list[tuple[int, dict]] = []
    for e in entries:
        if "scope" in e and normalize_scope(e.get("scope") or "") != normalize_scope(item.scope):
            continue
        at = max((hay.rfind(_flat(w).lower()) for w in e.get("match") or []), default=-1)
        if at >= 0:
            best.append((at, e))
    if not best:
        return None
    top = max(a for a, _ in best)
    keys = {e["key"] for a, e in best if a == top}
    return next(e for a, e in best if a == top) if len(keys) == 1 else None


def tag_populations(m: EvidenceMatrix) -> None:
    """Each counting item of a firm cell on a ratio-input aspect gets the population key of its matched
    entry, only when that entry's chunk is in the cell's retrieved set (m.pools; TL condition 1)."""
    for c in m.cells.values():
        if c.role == "research" or not c.entity:
            continue
        entries = population_entries(c.entity, m.aspect(c.aspect_id))
        pool = set(m.pools.get(c.id) or ())
        for i in c.items:
            i.population, i.population_source = "", ""
            if not entries or not i.counts:
                continue
            e = _match_entry(i, entries)
            if e is not None and e.get("chunk_id") in pool:
                i.population, i.population_source = e["key"], e["chunk_id"]


def population_entry(entity: str | None, key: str, chunk_id: str) -> dict | None:
    ent = _config_entity(entity)
    return next((p for p in _populations() if p.get("entity") in (entity, ent) and p.get("key") == key
                 and p.get("chunk_id") == chunk_id), None)


def row_name(cell_or_entity) -> str:
    entity = cell_or_entity.entity if isinstance(cell_or_entity, Cell) else cell_or_entity
    role = cell_or_entity.role if isinstance(cell_or_entity, Cell) else None
    if role == "research":
        return "Industry research"
    if not entity:
        return "All sources"
    from cee.answer.validate import _short_name
    return _short_name(entity)


def _clip(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."


# --- the question's own asks (rule 1e) ------------------------------------------------------------

_FORECAST = [
    re.compile(r"^\s*(?:please\s+)?(?:forecast|predict|project|estimate)\b", re.I),
    re.compile(r"\byour\s+(?:own\s+)?(?:forecast|prediction|projection|estimate)s?\b", re.I),
    re.compile(r"\bwhat\s+will\b.*\b(?:be|reach|grow|total)\b.*\b(?:in\s+20\d\d|by\s+20\d\d|next\s+(?:year|quarter))\b",
               re.I),
]


def forecast_request(question: str) -> bool:
    """The question asks the system for its own forecast (rule 1e -> refuse). Narrow on purpose:
    positions others hold ("what will advice look like", Q16) are facts, not a forecast request."""
    return any(p.search(question) for p in _FORECAST)


@lru_cache(maxsize=1)
def _normative_question_patterns() -> list[re.Pattern]:
    from cee.answer.validate import _alternation, _entry
    home = entities_config().get("home_firm", {}).get("id", "EDJ")
    e = _entry(home)
    names = [e["name"].split(" (")[0], *e.get("aliases", []), "EJ", "EDJ", "the home firm"]
    firm = _alternation(names)
    return [re.compile(rf"\b(?:should|could|can|ought to|must)\s+{firm}\s+\w+", re.I),
            re.compile(rf"\bhow\s+should\b.{{0,160}}?\b(?:shape|change|influence|guide|inform|drive|affect)\s+{firm}",
                       re.I)]


def normative_question(question: str) -> bool:
    """The question asks what the home firm should or could do (rule 1e -> answer_with_boundary):
    a modal with the home firm as its subject ("how could Edward Jones replicate", Q12), or "how
    should <x> shape <home firm>" (Q19). validate.is_normative is for answer sentences."""
    return any(p.search(question) for p in _normative_question_patterns())


# --- derivation (rule 1d, rule 2 within-firm) ---------------------------------------------------

def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


_SCOPE_TAIL = re.compile(r"\s+(?:reportable\s+segment|business\s+segment|segment|business|division)$")


def normalize_scope(text: str) -> str:
    """A scope label for comparison (#247, PR #256 review note 4): lower case, punctuation stripped,
    whitespace collapsed, a leading "the" and a trailing "segment" / "business segment" / "reportable
    segment" / "business" / "division" removed. "Wealth Management segment" == "Wealth Management";
    "Private Client Group" stays different from "" (the whole firm)."""
    t = re.sub(r"[^\w\s&]", " ", str(text or "").lower())
    t = " ".join(t.split())
    t = re.sub(r"^the\s+", "", t)
    return _SCOPE_TAIL.sub("", t).strip()


_SCALE_WORD = re.compile(r"\b(thousands?|millions?|billions?|trillions?)\b", re.I)


def _value(text: str, unit: str = "") -> float | None:
    """The item's figure; a scale word in its unit ("USD billions") applies when the value itself
    has none ("$2,647" in a "($ in billions)" table)."""
    from cee.answer.validate import SCALES, figures
    fs = figures(text or "")
    if not fs:
        return None
    m = _SCALE_WORD.search(unit or "")
    if fs[0].scale == 1.0 and m:
        return fs[0].value * SCALES[m.group(1).lower().rstrip("s")]
    return fs[0].value


def _base_unit(unit: str) -> str:
    """The unit without its scale word ("USD billions" -> "USD")."""
    return " ".join(_SCALE_WORD.sub(" ", unit or "").split())


def _fmt(x: float) -> str:
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.4g}"


def _q1(text: str) -> str:
    return " ".join(str(text or "").split())


def _input_label(m: EvidenceMatrix, ref: str) -> str:
    """'client assets ($2,647, 2026Q2)' style label of a derivation input reference 'a2.EDJ#0'."""
    cid, _, idx = ref.partition("#")
    c = m.cells.get(cid)
    if c is None:
        return ref
    i = c.items[int(idx)]
    a = m.aspect(c.aspect_id)
    what = (a.metric or "").replace("_", " ") or _aspect_text(a)
    return f"{what} ({_q1(i.value)}{', ' + i.period if i.period else ''})"


def _input_populations(cell: Cell, items) -> list[dict]:
    """The population source of each input whose source chunk is in the input cell's pool (tagging
    only sets a key when it is): {ref, key, chunk_id, quote, valid_from, period}. TL condition 1."""
    out = []
    for ref, i in items:
        if not i.population or not i.population_source:
            continue
        e = population_entry(cell.entity, i.population, i.population_source) or {}
        out.append({"ref": ref, "key": i.population, "chunk_id": i.population_source,
                    "quote": e.get("quote", ""), "valid_from": str(e.get("valid_from") or ""),
                    "period": i.period, "value": i.value})
    return out


def derive(m: EvidenceMatrix) -> None:
    """Check every derivation the model proposed: inputs are counting items of fact cells (proxy
    aspects allowed) of the same firm, no input flagged number_not_found, the same non-empty period
    and scope, the same unit for a sum or difference, values that parse. Accepted: code computes the
    value and the cell becomes `derived`; else the proposal stays with ok false and why."""
    for cell in m.cells.values():
        d = cell.derivation
        if not d or d.get("operation") not in OPERATIONS[1:]:
            cell.derivation = None
            continue
        op, inputs = d["operation"], d.get("inputs") or []
        why, items = None, []
        if len(inputs) < 2 or (op != "sum" and len(inputs) != 2):
            why = f"{op} needs {'two or more' if op == 'sum' else 'two'} inputs"
        for ref in inputs if why is None else []:
            src = m.cells.get(str(ref.get("subquestion_id")))
            idx = ref.get("item")
            if src is None:
                why = f"input {ref.get('subquestion_id')} is not a cell"
            elif src.entity != cell.entity or src.role == "research":
                why = f"input {src.id} is not the same firm"
            elif src.effective_label != "fact":
                why = f"input {src.id} is not a fact"
            elif not isinstance(idx, int) or not 0 <= idx < len(src.items) or not src.items[idx].counts:
                why = f"input {src.id} item {idx} is not a cited item"
            elif "number_not_found" in src.items[idx].flags:
                why = f"input {src.id} item {idx}: figure not found in its cited chunk"
            if why:
                break
            items.append((f"{src.id}#{idx}", src.items[idx]))
        if why is None:
            periods = {i.period for _, i in items}
            scopes = {normalize_scope(i.scope) for _, i in items}
            units = {_norm(i.unit) for _, i in items}
            values = [_value(i.value, i.unit) for _, i in items]
            if "" in periods or len(periods) != 1:
                why = "periods differ or are not stated: " + ", ".join(i.period or "(none)" for _, i in items)
            elif len(scopes) != 1:
                why = "scopes differ: " + ", ".join(i.scope or "(whole firm)" for _, i in items)
            elif op in ("sum", "difference") and len(units) != 1:
                why = "units differ: " + ", ".join(i.unit or "(none)" for _, i in items)
            elif any(v is None for v in values):
                why = "a value does not parse"
            elif op == "ratio" and values[1] == 0:
                why = "division by zero"
        # #247 part 2 (rule 2, populations): both inputs exact, both on one registered population
        pops = _input_populations(cell, items)
        if why is None:
            approx = [ref for ref, i in items if approximate(i)]
            keys = {i.population for _, i in items}
            if approx:
                why = "approximate: " + ", ".join(f"{_input_label(m, ref)} is approximate ({_q1(i.value)})"
                                                  for ref, i in items if ref in approx)
            elif "" in keys:
                missing = [ref for ref, i in items if not i.population]
                why = "population not stated: " + ", ".join(_input_label(m, r) for r in missing)
            elif len(keys) != 1:
                why = "populations differ"
        if why is not None:
            cell.derivation = {**d, "ok": False, "why": why, "populations": pops,
                               "population_chunk_ids": sorted({p["chunk_id"] for p in pops}),
                               "input_chunk_ids": sorted({c for _, i in items for c in i.chunk_ids})}
            continue
        if op == "ratio":
            result, sign = values[0] / values[1], " / "
            num, den = _base_unit(items[0][1].unit), _base_unit(items[1][1].unit)
            unit = f"{num} per {den}" if num and den else ""
        elif op == "sum":
            result, sign = sum(values), " + "
            unit = _base_unit(items[0][1].unit)
        else:
            result, sign = values[0] - values[1], " - "
            unit = _base_unit(items[0][1].unit)
        shown = [f"{i.value} ({i.unit})" if i.unit else i.value for _, i in items]
        formula = (sign.join(ref for ref, _ in items) + " = " + sign.join(shown) + f" = {_fmt(result)}"
                   + (f" {unit}" if unit else ""))
        # #247 (review note 2): the user-facing formula, with no cell ids, for the reduce and the mock
        formula_text = sign.join(shown) + f" = {_fmt(result)}" + (f" {unit}" if unit else "")
        cell.derivation = {**d, "ok": True, "why": "", "value": result, "value_text": _fmt(result), "unit": unit,
                           "formula": formula, "formula_text": formula_text,
                           "period": items[0][1].period, "scope": items[0][1].scope,
                           "input_chunk_ids": sorted({c for _, i in items for c in i.chunk_ids}),
                           "populations": pops, "population_chunk_ids": sorted({p["chunk_id"] for p in pops})}
        if cell.label != "fact":
            cell.label = "derived"
        registered = len(pops) == len(items) and all(p.get("key") for p in pops)   # #247 part 2 R2
        if m.aspect(cell.aspect_id).metric is None and not registered and "definition_unverified" not in cell.flags:
            cell.flags.append("definition_unverified")


def holds(cell: Cell) -> bool:
    """The cell holds its aspect's quantity: a counting fact, or an accepted derivation."""
    if cell.effective_label == "fact":
        return True
    return cell.label == "derived" and bool(cell.derivation and cell.derivation.get("ok"))


# --- comparability (rule 2) ---------------------------------------------------------------------

def _registered_ratio(a, cells) -> bool:
    """#247 part 2 R2: an aspect whose holding cells are all derivations over registered populations (their
    computation claims quote both population sources): no "definition unverified" mark."""
    derived = [c for c in cells if c.label == "derived"]
    return bool(derived) and len(derived) == len(cells) and all(
        "definition_unverified" not in c.flags for c in derived)


def metric_aspect(a, cells) -> bool:
    """An aspect that asks for a quantity (#247, TL D6): kind series, a proxy, or one holding a derived
    cell. Recency and comparison aspects never are."""
    if a.kind in ("recency", "comparison"):
        return False
    return a.kind == "series" or bool(getattr(a, "proxy", False)) or any(c.label == "derived" for c in cells)


def mark_comparability(m: EvidenceMatrix) -> None:
    m.marks = {}
    for a in m.aspects:
        cells = [c for c in m.cells.values() if c.aspect_id == a.id and c.role != "research" and holds(c)]
        firms = list(dict.fromkeys(c.entity for c in cells if c.entity))
        mark = AspectMark(a.id, a.metric, firms=firms)
        if a.metric:
            if len(firms) >= 2:
                defs = {f: metric_definition(f, a.metric) for f in firms}
                bases = {(d or {}).get("basis") for d in defs.values()}
                units = {(d or {}).get("unit") for d in defs.values()}
                if all(defs.values()) and len(bases) == 1 and len(units) == 1:
                    mark.status = "same_basis"
                    periods = [{i.period for i in c.counting_items if i.period} for c in cells if c.entity]
                    mark.shared_periods = sorted(set.intersection(*periods)) if periods else []
                else:
                    mark.status = "different_basis"
                    parts = []
                    for f, d in defs.items():
                        text = (f"{_clip(d['quote'], CAVEAT_DEF_CHARS)} ({d['chunk_id']})" if d and d.get("quote")
                                else "no registered definition")
                        parts.append(f"{row_name(f)}: {text}")
                    mark.caveat = COMPARABILITY_CAVEAT.format(metric=a.metric.replace("_", " ").capitalize(),
                                                              definitions="; ".join(parts))
        elif metric_aspect(a, cells) and (any(i.value for c in cells for i in c.counting_items)
                                          or any(c.label == "derived" for c in cells)) \
                and not _registered_ratio(a, cells):
            # #247 (#246 finding 5): the mark only on metric aspects (series, proxy, or holding a
            # derived cell); qualitative, recency and comparison aspects that carry a figure get none
            mark.status = "unverified"
            mark.mark = UNVERIFIED_MARK.format(metric=_aspect_text(a))
        m.marks[a.id] = mark


# --- behavior (rule 1) and gaps -----------------------------------------------------------------

def _aspect_text(a) -> str:
    from cee.answer.validate import is_normative
    text = " ".join(a.text.split()).rstrip(".")
    return a.id if is_normative(text) else text


def _decides(m: EvidenceMatrix, c: Cell) -> bool:
    """Cells that can decide rule (a): not a comparison aspect (rule 4), not a proxy (plan-v3.1)."""
    a = m.aspect(c.aspect_id)
    return a.kind != "comparison" and not getattr(a, "proxy", False)


def decide_behavior(m: EvidenceMatrix) -> None:
    q = m.question
    failed = [c for c in m.cells.values() if c.label == "failed"]
    fact_cells = [c for c in m.cells.values() if _decides(m, c) and holds(c)]
    related = [c for c in m.cells.values() if m.aspect(c.aspect_id).kind != "comparison"
               and (c.effective_label == "different_quantity"
                    or (getattr(m.aspect(c.aspect_id), "proxy", False) and holds(c)))]
    m.incomplete_note = None
    if forecast_request(q):
        m.behavior, m.behavior_reason = "refuse", "1e: the question asks for the system's own forecast"
    elif normative_question(q):
        m.behavior, m.behavior_reason = "answer_with_boundary", "1e: the question has a normative part"
        if failed and not fact_cells:   # #247 B2: a failed extraction is shown, not hidden by 1e
            m.incomplete_note = INCOMPLETE_NOTE.format(firms=", ".join(dict.fromkeys(row_name(c) for c in failed)))
    elif fact_cells:
        m.behavior = "answer"
        m.behavior_reason = "1a: the asked quantity in " + ", ".join(c.id for c in fact_cells)
    elif failed:
        firms = ", ".join(dict.fromkeys(row_name(c) for c in failed))
        m.behavior, m.behavior_reason = None, f"undecided: no fact, extraction failed for {firms}"
        m.incomplete_note = INCOMPLETE_NOTE.format(firms=firms)
    elif related:
        m.behavior = "gap_with_adjacent"
        m.behavior_reason = "1b: no fact; a related quantity in " + ", ".join(c.id for c in related)
    else:
        m.behavior, m.behavior_reason = "refuse", "1c: no fact and no related quantity"


# --- asked periods and uncovered-period gaps (#247 B4, TL approval conditions 1-4) ----------------

_NUMBER_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
_ASKED = re.compile(r"\b(?:last|past|previous|prior|most\s+recent)\s+(\d{1,2}|[a-z]+)\s+(quarters|years)\b", re.I)
PERIOD_GAP = "{firm} - {aspect}: not found for {periods} in the documents searched."
PERIOD_GAP_ALL = ("{firm} - {aspect}: not found for the asked periods ({span}) in the documents searched; "
                  "figures for other periods are listed.")


def asked_periods(question: str, as_of) -> tuple[str, list[str]] | None:
    """The periods the question itself asks for: ("quarter", ["2024Q4", ...]) for "last N quarters"
    (the N most recent calendar quarters that ended before as_of), ("year", ["2023", ...]) for
    "last N years" (complete years only, the unfinished current year never counts). A time window
    (a publication-date filter) gives none (TL condition 1); no stated range gives none."""
    if as_of is None:
        return None
    m = _ASKED.search(question or "")
    if not m:
        return None
    raw = m.group(1).lower()
    n = int(raw) if raw.isdigit() else _NUMBER_WORDS.get(raw)
    if not n:
        return None
    if m.group(2).lower() == "years":
        last = as_of.year - 1   # the current year is unfinished on any as_of inside it
        return "year", [str(y) for y in range(last - n + 1, last + 1)]
    y, q = as_of.year, (as_of.month - 1) // 3 + 1
    import datetime as _dt
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    if _dt.date(y, *ends[q]) >= as_of:   # the current quarter has not ended before as_of
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    out = []
    for _ in range(n):
        out.append(f"{y}Q{q}")
        y, q = (y, q - 1) if q > 1 else (y - 1, 4)
    return "quarter", list(reversed(out))


def _covers(period: str, unit: str) -> str | None:
    """The asked period an item period covers: a quarter ("2025Q3") or a year ("2025"). In a quarters
    ask a YYYY or FYYYYY item covers no quarter (TL condition 4d)."""
    p = str(period or "")
    m = re.fullmatch(r"(\d{4})-(\d{2})-\d{2}", p)
    if m:
        return m.group(1) if unit == "year" else f"{m.group(1)}Q{(int(m.group(2)) - 1) // 3 + 1}"
    m = re.fullmatch(r"(\d{4})Q([1-4])", p)
    if m:
        return m.group(1) if unit == "year" else p
    m = re.fullmatch(r"(?:FY)?(\d{4})", p)
    if m and unit == "year":
        return m.group(1)
    return None


def _period_gaps_apply(a) -> bool:
    return a.kind == "series" or (a.kind == "fact" and bool(a.metric) and not getattr(a, "proxy", False))


def period_gaps(m: EvidenceMatrix, as_of, source) -> list[dict]:
    """A gap naming the asked periods a holding cell does not cover (series aspects and registered-
    metric fact aspects; never recency, comparison or proxy aspects; research excluded)."""
    asked = asked_periods(m.question, as_of)
    if not asked:
        return []
    unit, periods = asked
    out = []
    for a in m.aspects:
        if not _period_gaps_apply(a):
            continue
        for c in m.cells.values():
            if c.aspect_id != a.id or c.role == "research" or not holds(c):
                continue
            covered = {_covers(i.period, unit) for i in c.counting_items}
            if c.label == "derived" and c.derivation:
                covered.add(_covers(c.derivation.get("period", ""), unit))
            missing = [p for p in periods if p not in covered]
            if not missing:
                continue
            if len(missing) == len(periods):
                what = PERIOD_GAP_ALL.format(firm=row_name(c), aspect=_aspect_text(a),
                                             span=f"{periods[0]}-{periods[-1]}")
            else:
                what = PERIOD_GAP.format(firm=row_name(c), aspect=_aspect_text(a), periods=", ".join(missing))
            out.append({"id": c.id, "what": what, "suggested_source": source(c.entity), "label": "period_gap",
                        "periods": missing})
    return out


COMPETITORS_GAP = "Competitors ({firms}) - {aspect}: not found in the documents searched."
BASIS_BREAK = ("{firm} - {aspect}: the figures cover different bases and are not one series: {groups}. "
               "The break is flagged, not smoothed.")


def in_gap_scope(a, c: Cell) -> bool:
    """#247 part 2 (Q19): a cell gets a gap only inside its aspect's own firm scope: with a planned
    subset (`asked_firms`, before the home-firm widening) only those firms' cells; research cells only
    for aspects without a subset."""
    asked = list(getattr(a, "asked_firms", None) or [])
    if not asked:
        return True
    return c.role != "research" and c.entity in asked


def _breaks_apply(a) -> bool:
    return a.kind == "series" or (a.kind == "fact" and bool(a.metric) and not getattr(a, "proxy", False))


def basis_breaks(m: EvidenceMatrix) -> None:
    """#247 part 2 (TL item 3): a holding cell of a series aspect (or a registered-metric fact aspect)
    whose counting items cover more than one basis (normalised scope, population key) gets the flag
    basis_break and a code caveat listing each basis with its periods. A flow series has no population
    keys, so only the scope splits it."""
    m.breaks = []
    for a in m.aspects:
        if not _breaks_apply(a):
            continue
        for c in m.cells.values():
            if c.aspect_id != a.id or c.role == "research" or not holds(c):
                continue
            groups: dict[tuple[str, str], list[str]] = {}
            labels: dict[tuple[str, str], str] = {}
            valued = [i for i in c.counting_items if i.value]
            keyed = {normalize_scope(i.scope): i.population for i in valued if i.population}
            for i in valued:
                k = (normalize_scope(i.scope), i.population)
                if keyed and not i.population:   # R3: an item without a population ...
                    if k[0] in keyed:
                        k = (k[0], keyed[k[0]])   # ... joins its scope's group
                    elif not i.period:
                        continue                  # ... and an undated one makes no basis
                groups.setdefault(k, [])
                if i.period and i.period not in groups[k]:
                    groups[k].append(i.period)
                labels.setdefault(k, _q1(i.scope) or "whole firm")
            if len(groups) < 2:
                continue
            parts = [f"{labels[k]}{' (' + k[1] + ')' if k[1] else ''}: {', '.join(sorted(v)) or 'period not stated'}"
                     for k, v in groups.items()]
            text = BASIS_BREAK.format(firm=row_name(c), aspect=_aspect_text(a), groups="; ".join(parts))
            if "basis_break" not in c.flags:
                c.flags.append("basis_break")
            m.breaks.append({"id": c.id, "caveat": text, "groups": parts})


def build_gaps(m: EvidenceMatrix, sources=None, as_of=None) -> None:
    """Code-built gaps (#247 places them): one per cell that does not hold its quantity, and the
    'does not support' gap per aspect no row holds; comparison and proxy aspects get none. #247 B4:
    plus a gap naming the asked periods (last N quarters / years) a holding cell does not cover."""
    from cee.answer.validate import suggested_sources
    sources = sources or suggested_sources
    memo: dict[str, str] = {}

    def source(entity):
        if not entity:
            return ""
        if entity not in memo:
            try:
                memo[entity] = sources(entity)
            except Exception:
                memo[entity] = ""
        return memo[entity]

    m.gaps = []
    for a in m.aspects:
        if a.kind == "comparison" or getattr(a, "proxy", False):
            continue
        cells = [c for c in m.cells.values() if c.aspect_id == a.id]
        scoped = [c for c in cells if in_gap_scope(a, c)]
        folded = []
        for c in scoped:
            if holds(c):
                continue
            label = c.effective_label if c.label != "failed" else "failed"
            label = label if label in GAP_TEXT else "not_found"
            if c.role == "competitor" and label in ("not_found", "not_disclosed"):
                folded.append(c)   # TL D3: one gap per aspect for the empty competitor cells
                continue
            what = GAP_TEXT[label].format(firm=row_name(c), aspect=_aspect_text(a))
            if label == "different_quantity" and c.counting_items:   # R6b
                what = GAP_TEXT["closest"].format(firm=row_name(c), aspect=_aspect_text(a),
                                                  closest=_clip(c.counting_items[0].text, CAVEAT_DEF_CHARS).rstrip("."))
            if label == "not_found" and c.researched and c.research_hits == 0:
                what += RESEARCHED_NOTHING
            m.gaps.append({"id": c.id, "what": what, "suggested_source": source(c.entity), "label": label})
        if folded:
            names = ", ".join(dict.fromkeys(row_name(c) for c in folded))
            m.gaps.append({"id": a.id, "what": COMPETITORS_GAP.format(firms=names, aspect=_aspect_text(a)),
                           "suggested_source": "; ".join(dict.fromkeys(s for s in (source(c.entity) for c in folded) if s)),
                           "label": "competitors_not_found", "cells": [c.id for c in folded]})
        # A failed extraction cannot show an absence (D5): no "does not support" gap for that aspect.
        if scoped and not any(holds(c) for c in cells) and not any(c.label == "failed" for c in cells):
            firms = ", ".join(dict.fromkeys(row_name(c) for c in scoped))
            m.gaps.append({"id": a.id, "what": NOT_SUPPORTED.format(aspect=_aspect_text(a), firms=firms),
                           "suggested_source": "", "label": "not_supported"})
    m.gaps += period_gaps(m, as_of, source)


DEFINITIONS_BY_FIRM = "{metric} as each firm defines it: {parts}."
DEFINITION_CHANGED = ("{firm} - {metric}: the definition wording differs between {a} ('{qa}') and {b} ('{qb}'); "
                      "figures are listed as each document states them.")
SERIES_SPAN = ("{firm} - {aspect}: the series in the documents searched runs from {first} to {last} ({n} points); "
               "no figure after {last} was found.")


def _list(xs) -> str:
    return ", ".join(str(x) for x in xs or [])


def definitions_by_firm(m: EvidenceMatrix) -> dict[str, str]:
    """#247 part 2 R6a: per registered metric of the question's aspects, when the firms in the matrix do not
    all share one quoted basis, one caveat naming each firm's definition (config/metric_definitions.yaml:
    its own words, includes / excludes / not stated, or that it publishes none)."""
    out: dict[str, str] = {}
    firms = [r for r in m.rows if r not in ("research", "all")]
    for metric in dict.fromkeys(a.metric for a in m.aspects if a.metric):
        defs = {f: metric_definition(f, metric) for f in firms}
        bases = {(d or {}).get("basis") for d in defs.values()}
        if len(firms) < 2 or (len(bases) == 1 and all(d and d.get("status") == "quoted" for d in defs.values())):
            continue
        parts = []
        for f, d in defs.items():
            if not d:
                parts.append(f"{row_name(f)}: no registered definition")
                continue
            st = d.get("status")
            head = {"quoted": "", "closest_metric": "publishes no definition of this metric; closest metric ",
                    "not_disclosed": "publishes no definition or count; nearest text "}.get(st, "")
            bits = [f"{head}'{_clip(d.get('quote', ''), CAVEAT_DEF_CHARS)}' ({d.get('chunk_id', '')})"]
            for k, w in (("includes", "includes"), ("excludes", "excludes"), ("not_stated", "not stated")):
                if d.get(k):
                    bits.append(f"{w} {_clip(_list(d[k]), 120)}")
            parts.append(f"{row_name(f)}: " + "; ".join(bits))
        out[metric] = DEFINITIONS_BY_FIRM.format(metric=metric.replace("_", " ").capitalize(), parts=" | ".join(parts))
    return out


def definition_changes(m: EvidenceMatrix) -> list[str]:
    """#247 part 2 R5: one firm's items quoting definitions that differ (normalised) from different
    documents, on a registered-metric aspect -> a caveat naming both documents and their wording."""
    out = []
    for a in m.aspects:
        if not a.metric:
            continue
        for c in m.cells.values():
            if c.aspect_id != a.id or c.role == "research" or not c.entity:
                continue
            seen: dict[str, tuple[str, str]] = {}
            for i in c.counting_items:
                if not i.definition:
                    continue
                norm = re.sub(r"[^a-z0-9 ]", "", _norm(i.definition))
                doc = i.chunk_ids[0].split("#")[0]
                seen.setdefault(norm, (doc, i.definition))
            docs = list(seen.values())
            if len(docs) >= 2 and docs[0][0] != docs[1][0]:
                text = DEFINITION_CHANGED.format(firm=row_name(c), metric=a.metric.replace("_", " "), a=docs[0][0],
                                                 qa=_clip(docs[0][1], CAVEAT_DEF_CHARS), b=docs[1][0],
                                                 qb=_clip(docs[1][1], CAVEAT_DEF_CHARS))
                if text not in out:
                    out.append(text)
    return out


def _period_key(p: str):
    s = str(p or "")
    m_ = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m_:
        return (int(m_.group(1)), int(m_.group(2)), int(m_.group(3)))
    m_ = re.fullmatch(r"(\d{4})Q([1-4])", s)
    if m_:
        return (int(m_.group(1)), 3 * int(m_.group(2)), 31)
    m_ = re.fullmatch(r"(?:FY)?(\d{4})", s)
    if m_:
        return (int(m_.group(1)), 12, 31)
    return None


def series_spans(m: EvidenceMatrix) -> list[str]:
    """#247 part 2 R6c: for a series aspect, each holding firm cell: where its disclosed series starts
    and stops in the documents searched (the items' own periods; undated items not counted)."""
    out = []
    for a in m.aspects:
        if a.kind != "series":
            continue
        for c in m.cells.values():
            if c.aspect_id != a.id or c.role == "research" or not c.entity or not holds(c):
                continue
            periods = sorted({i.period for i in c.counting_items if i.value and _period_key(i.period)},
                             key=_period_key)
            if not periods:
                continue
            out.append(SERIES_SPAN.format(firm=row_name(c), aspect=_aspect_text(a), first=periods[0],
                                          last=periods[-1], n=len(periods)))
    return out


def build_caveats(m: EvidenceMatrix, query=None, hits=None) -> None:
    """Comparability caveats (rule 2) and the config caveats of cited substitutes (entities.yaml)."""
    by_firm = definitions_by_firm(m)   # #247 part 2 R6a: replaces the comparability caveat of that metric
    replaced = {mk.metric for mk in m.marks.values() if mk.caveat and mk.metric in by_firm}
    m.caveats = [mk.caveat for mk in m.marks.values() if mk.caveat and mk.metric not in replaced]
    m.caveats += [c for c in by_firm.values() if c not in m.caveats]
    m.caveats += [b["caveat"] for b in m.breaks if b["caveat"] not in m.caveats]   # #247 part 2
    m.caveats += [c for c in definition_changes(m) + series_spans(m) if c not in m.caveats]   # R5, R6c
    if query is None or not hits:
        return
    from cee.answer.schema import Answer, Claim
    from cee.answer.validate import insert_caveats
    cited = m.chunk_ids()
    if not cited:
        return
    probe = insert_caveats(Answer(answerable=True, behavior="answer", claims=[Claim(text="", chunk_ids=cited)]),
                           query, hits)
    m.caveats += [c for c in probe.caveats if c not in m.caveats]


def finish(m: EvidenceMatrix, query=None, hits=None, sources=None, as_of=None) -> EvidenceMatrix:
    """Run every code rule on a filled matrix, in order."""
    tag_populations(m)
    derive(m)
    mark_comparability(m)
    decide_behavior(m)
    basis_breaks(m)
    build_gaps(m, sources, as_of)
    build_caveats(m, query, hits)
    return m
