"""Code-side checks on every answer (specs/answer-citations.md).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
Here: citation check (flag, never drop), code-built source labels, empty-retrieval gap/refuse.
Not yet (S2, W3+): number check, caveat insertion, coverage note.
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
