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

    def aspect(self, aspect_id: str):
        return next(a for a in self.aspects if a.id == aspect_id)

    def chunk_ids(self) -> list[str]:
        """Every valid cited chunk id (items and derivation inputs): what the reduce may cite (#247)."""
        out: list[str] = []
        for c in self.cells.values():
            for i in c.items:
                out += [x for x in i.chunk_ids if x not in out]
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


def _value(text: str) -> float | None:
    from cee.answer.validate import figures
    fs = figures(text or "")
    return fs[0].value if fs else None


def _fmt(x: float) -> str:
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.4g}"


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
            scopes = {_norm(i.scope) for _, i in items}
            units = {_norm(i.unit) for _, i in items}
            values = [_value(i.value) for _, i in items]
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
        if why is not None:
            cell.derivation = {**d, "ok": False, "why": why}
            continue
        if op == "ratio":
            result, sign = values[0] / values[1], " / "
        elif op == "sum":
            result, sign = sum(values), " + "
        else:
            result, sign = values[0] - values[1], " - "
        formula = (sign.join(ref for ref, _ in items) + " = " + sign.join(i.value for _, i in items)
                   + f" = {_fmt(result)}")
        cell.derivation = {**d, "ok": True, "why": "", "value": result, "value_text": _fmt(result),
                           "formula": formula, "period": items[0][1].period, "scope": items[0][1].scope,
                           "input_chunk_ids": sorted({c for _, i in items for c in i.chunk_ids})}
        if cell.label != "fact":
            cell.label = "derived"
        if m.aspect(cell.aspect_id).metric is None and "definition_unverified" not in cell.flags:
            cell.flags.append("definition_unverified")


def holds(cell: Cell) -> bool:
    """The cell holds its aspect's quantity: a counting fact, or an accepted derivation."""
    if cell.effective_label == "fact":
        return True
    return cell.label == "derived" and bool(cell.derivation and cell.derivation.get("ok"))


# --- comparability (rule 2) ---------------------------------------------------------------------

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
        elif any(i.value for c in cells for i in c.counting_items) or any(c.label == "derived" for c in cells):
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


def build_gaps(m: EvidenceMatrix, sources=None) -> None:
    """Code-built gaps (#247 places them): one per cell that does not hold its quantity, and the
    'does not support' gap per aspect no row holds; comparison and proxy aspects get none."""
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
        for c in cells:
            if holds(c):
                continue
            label = c.effective_label if c.label != "failed" else "failed"
            label = label if label in GAP_TEXT else "not_found"
            what = GAP_TEXT[label].format(firm=row_name(c), aspect=_aspect_text(a))
            if label == "not_found" and c.researched and c.research_hits == 0:
                what += RESEARCHED_NOTHING
            m.gaps.append({"id": c.id, "what": what, "suggested_source": source(c.entity), "label": label})
        # A failed extraction cannot show an absence (D5): no "does not support" gap for that aspect.
        if cells and not any(holds(c) for c in cells) and not any(c.label == "failed" for c in cells):
            firms = ", ".join(dict.fromkeys(row_name(c) for c in cells))
            m.gaps.append({"id": a.id, "what": NOT_SUPPORTED.format(aspect=_aspect_text(a), firms=firms),
                           "suggested_source": "", "label": "not_supported"})


def build_caveats(m: EvidenceMatrix, query=None, hits=None) -> None:
    """Comparability caveats (rule 2) and the config caveats of cited substitutes (entities.yaml)."""
    m.caveats = [mk.caveat for mk in m.marks.values() if mk.caveat]
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


def finish(m: EvidenceMatrix, query=None, hits=None, sources=None) -> EvidenceMatrix:
    """Run every code rule on a filled matrix, in order."""
    derive(m)
    mark_comparability(m)
    decide_behavior(m)
    build_gaps(m, sources)
    build_caveats(m, query, hits)
    return m
