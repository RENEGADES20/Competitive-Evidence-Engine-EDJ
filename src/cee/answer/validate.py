"""Code-side checks on every answer (specs/answer-citations.md).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
Here: citation check (flag, never drop), code-built source labels, caveat insertion,
coverage note, empty-retrieval gap/refuse.
Not yet: number check (#52).
"""
from __future__ import annotations

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


def suggested_sources(entity_id: str) -> str:
    e = _entry(entity_id)
    return f"{e['name']}: " + ", ".join(SOURCE_NAMES.get(t, t) for t in e.get("expected_sources", []))


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
