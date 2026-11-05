"""Code-side checks on every answer (specs/answer-citations.md).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
Here: citation check (flag, never drop), code-built source labels, caveat insertion,
coverage note, registry-based suggested sources, number check, empty-retrieval gap/refuse.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from cee.answer.schema import Answer, Gap
from cee.config import entities_config
from cee.retrieve.fts import Hit, Query

TIER_LABELS = {1: "licensed", 2: "filing", 3: "IR", 4: "trade press (indicative only)",
               5: "research", 6: "signal"}

SOURCE_NAMES = {
    "10-K": "Form 10-K annual report (SEC EDGAR)", "10-Q": "Form 10-Q quarterly report (SEC EDGAR)",
    "8-K": "Form 8-K current report (SEC EDGAR)", "DEF 14A": "Proxy statement (SEC EDGAR)",
    "20-F": "Form 20-F annual report (SEC EDGAR)", "40-F": "Form 40-F annual report (SEC EDGAR)",
    "6-K": "Form 6-K report (SEC EDGAR)", "adv": "Form ADV (SEC IAPD)",
    "transcript": "earnings-call transcripts", "supplement": "quarterly financial supplement",
    "monthly": "monthly activity reports", "deck": "investor-day presentations",
    "press": "company press releases", "trade": "trade press", "research": "industry research",
}


def source_label(hit: Hit) -> str:
    seg = f" - {hit.segment} segment" if hit.segment else ""
    page = f", p.{hit.page}" if hit.page else ""
    tier = TIER_LABELS.get(hit.source_tier, "?")
    return f"{hit.entity_id or 'Research'} {hit.doc_type}{seg} {hit.period_end or hit.published_at}{page} [{tier}]"


def check_citations(answer: Answer, hits: list[Hit]) -> Answer:
    by_id = {h.chunk_id: h for h in hits}
    for claim in [*answer.claims, *answer.adjacent]:
        known = [c for c in claim.chunk_ids if c in by_id]
        if not claim.chunk_ids:
            claim.flags.append("no_citation")
        elif len(known) < len(claim.chunk_ids):
            claim.flags.append("unmatched_citation")
        claim.source_label = "; ".join(dict.fromkeys(source_label(by_id[c]) for c in known))
    return check_numbers(answer, hits)


# Number check (#52). Rule in specs/answer-citations.md, "Number check".
SCALES = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "trillion": 1e12}
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_NUMBER = re.compile(
    r"(?<![\w.#/-])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w-]|\.\d)"
    r"(?:\s*(%|percent\b|thousand\b|million\b|billion\b|trillion\b|bn\b|mn\b|k\b))?", re.I)
_TABLE_SCALE = re.compile(r"in (thousands|millions|billions)\b", re.I)
_DAY_AFTER_MONTH = re.compile(rf"\b{_MONTHS}\s+\d{{1,2}}\b")


@dataclass
class Figure:
    shown: Decimal      # as written, before scale ("20.4" in "20.4 thousand")
    scale: float        # 1, 1e3, 1e6, ...
    decimals: int       # digits after the point as written

    @property
    def value(self) -> float:
        return float(self.shown) * self.scale


def figures(text: str) -> list[Figure]:
    """Numbers in the text, skipping years, quarter/form labels and day of month."""
    text = _DAY_AFTER_MONTH.sub(lambda m: m.group(0).rsplit(" ", 1)[0], text)
    out = []
    for m in _NUMBER.finditer(text):
        whole, frac, unit = m.group(1), m.group(2), (m.group(3) or "").lower()
        if not frac and not unit and "," not in whole and 1990 <= int(whole) <= 2099:
            continue                                            # a year
        shown = Decimal(whole.replace(",", "") + (f".{frac}" if frac else ""))
        out.append(Figure(shown, SCALES.get(unit.strip(), 1.0), len(frac or "")))
    return out


def _chunk_values(text: str, unscaled: bool = False) -> list[float]:
    """Every number in a cited chunk; a "(in millions)" table header also offers bare numbers at that
    scale. unscaled: a claim figure written without a unit may match the digits shown ("21" vs "21 million")."""
    values = [f.value for f in figures(text)]
    if unscaled:
        values += [float(f.shown) for f in figures(text) if f.scale != 1.0]
    for word in {m.group(1).lower() for m in _TABLE_SCALE.finditer(text)}:
        scale = SCALES[word[:-1]]
        values += [f.value * scale for f in figures(text) if f.scale == 1.0]
    return values


def number_matches(f: Figure, value: float) -> bool:
    """1) within 0.1% of the chunk number, or 2) shows a decimal and is the chunk number rounded half up."""
    if abs(f.value - value) <= 0.001 * abs(value):
        return True
    if f.decimals >= 1:
        q = Decimal(1).scaleb(-f.decimals)
        return Decimal(repr(value / f.scale)).quantize(q, rounding=ROUND_HALF_UP) == f.shown
    return False


def check_numbers(answer: Answer, hits: list[Hit]) -> Answer:
    """Flag (never drop) a claim with a number not found in any chunk it cites (rule 4)."""
    by_id = {h.chunk_id: h for h in hits}
    for claim in [*answer.claims, *answer.adjacent]:
        cited = [by_id[c].text for c in claim.chunk_ids if c in by_id]
        if not cited:
            continue                                            # already flagged by the citation check
        scaled = [v for text in cited for v in _chunk_values(text)]
        bare = [v for text in cited for v in _chunk_values(text, unscaled=True)]
        if any(not any(number_matches(f, v) for v in (bare if f.scale == 1.0 else scaled))
               for f in figures(claim.text))                 and "number_not_found" not in claim.flags:
            claim.flags.append("number_not_found")
    return answer


def insert_caveats(answer: Answer, query: Query, hits: list[Hit]) -> Answer:
    """Code, not prompt (specs/answer-citations.md): when the answer cites a substitute for a
    firm the question names (BAC GWIM chunks for MER, equivalence: partial), append that firm's
    caveat from config/entities.yaml."""
    by_id = {h.chunk_id: h for h in hits}
    cited = [by_id[c] for claim in [*answer.claims, *answer.adjacent] for c in claim.chunk_ids if c in by_id]
    for e in entities_config()["entities"]:
        if e["id"] not in query.entities or not e.get("caveat") or not e.get("parent"):
            continue
        segments = {e.get("reported_as"), e["name"]}
        if any(h.entity_id == e["parent"] and h.segment in segments for h in cited) \
                and e["caveat"] not in answer.caveats:
            answer.caveats.append(e["caveat"])
    return answer


def _short_name(entity_id: str) -> str:
    return _entry(entity_id)["name"].split(" (")[0]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def coverage_note(query: Query, hits: list[Hit]) -> str:
    """What this answer rests on, built by code from the retrieved hits (#40): firms searched,
    then per entity / document type / segment the period covered. Same note for every behavior.
    Describes this question's retrieval only, not the whole corpus."""
    searched = ", ".join(_short_name(e) for e in query.entities) or "all documents (no covered firm named)"
    parts = [f"Coverage: searched {searched}."]
    window = getattr(query, "window", None)  # dates below are periods; the window is on publication date (#49)
    if window:
        parts.append(f"Published {window[0]} to {window[1]} only.")
    if query.unmapped:
        parts.append("No documents in the corpus for "
                     + ", ".join(_short_name(e) for e in query.unmapped) + ".")
    if not hits:
        if query.entities or not query.unmapped:
            parts.append("No stored passage matched this question.")
        return " ".join(parts)
    groups: dict[tuple, dict] = {}
    for h in hits:
        g = groups.setdefault((h.entity_id or "Research", h.doc_type, h.segment), {"docs": set(), "dates": set()})
        g["docs"].add(h.doc_id)
        g["dates"].add(h.period_end or h.published_at)
    sources = []
    for (entity, doc_type, segment), g in groups.items():
        lo, hi = min(g["dates"]), max(g["dates"])
        seg = f", {segment} segment" if segment else ""
        label = doc_type if entity == "Research" and doc_type == "research" else f"{entity} {doc_type}"
        sources.append(f"{label}{seg} ({lo if lo == hi else f'{lo} to {hi}'})")
    docs = len({h.doc_id for h in hits})
    parts.append(f"{_plural(len(hits), 'passage')} from {_plural(docs, 'document')}: " + "; ".join(sources) + ".")
    hit_entities = {h.entity_id for h in hits}
    missing = [e for e in query.entities
               if e not in hit_entities and _entry(e).get("parent") not in hit_entities]
    if missing:
        parts.append("No passages for " + ", ".join(_short_name(e) for e in missing) + ".")
    return " ".join(parts)


def _entry(entity_id: str) -> dict:
    cfg = entities_config()
    return next(e for e in cfg["entities"] + cfg.get("expansion", []) if e["id"] == entity_id)


def _registry_lookup(entity_id: str) -> tuple[list[tuple[str, str]], set[str]]:
    """(doc_type, source_name) rows in source_registry, and the doc types already ingested."""
    from cee.db import connect

    with connect() as conn:
        rows = conn.execute("SELECT doc_type, source_name FROM source_registry WHERE entity_id = %s "
                            "ORDER BY doc_type, source_name", (entity_id,)).fetchall()
        have = conn.execute("SELECT DISTINCT doc_type FROM documents WHERE entity_id = %s",
                            (entity_id,)).fetchall()
    return [(r["doc_type"], r["source_name"]) for r in rows], {r["doc_type"] for r in have}


registry_lookup = _registry_lookup   # tests swap in a fake; no database needed


def _config_sources(entity_id: str) -> str:
    e = _entry(entity_id)
    return f"{e['name']}: " + ", ".join(SOURCE_NAMES.get(t, t) for t in e.get("expected_sources", []))


def suggested_sources(entity_id: str) -> str:
    """Registry sources expected for the firm minus doc types already in the corpus (#51).
    Firm not in the registry, or the registry unreadable: the config list, as before."""
    try:
        rows, have = registry_lookup(entity_id)
    except Exception:
        rows, have = [], set()
    if not rows:
        return _config_sources(entity_id)
    missing = [name for doc_type, name in rows if doc_type not in have]
    return "Not yet in the corpus: " + "; ".join(missing) if missing else ""


def fill_suggested_sources(answer: Answer, query: Query) -> Answer:
    """Fill only gaps whose suggested_source is empty; text the model wrote is kept (#51)."""
    empty = [g for g in answer.gaps if not g.suggested_source.strip()]
    if empty and query.entities:
        prefix = "Not yet in the corpus: "
        parts = [t for t in (suggested_sources(e) for e in query.entities) if t]
        registry = [t[len(prefix):] for t in parts if t.startswith(prefix)]
        text = "; ".join(([prefix + "; ".join(registry)] if registry else [])
                         + [t for t in parts if not t.startswith(prefix)])
        for g in empty:
            g.suggested_source = text
    return answer


def empty_retrieval_answer(query: Query) -> Answer:
    """No eligible chunks: answer in code, without calling the LLM."""
    if query.unmapped and not query.entities:
        return Answer(answerable=False, behavior="refuse", gaps=[
            Gap(what=f"The corpus holds no documents for {_entry(e)['name']}.",
                suggested_source=suggested_sources(e)) for e in query.unmapped])
    if query.entities:
        return Answer(answerable=False, behavior="gap_with_adjacent", gaps=[
            Gap(what=f"No stored {_entry(e)['name']} passage matches this question.",
                suggested_source=suggested_sources(e)) for e in query.entities])
    return Answer(answerable=False, behavior="refuse", gaps=[
        Gap(what="No stored document matches this question and no covered firm is named.")])
