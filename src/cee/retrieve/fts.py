"""Full-text retrieval with hard entity/segment filters in SQL (ADR-001, ADR-004).

Skeleton placeholder, owner: S1 (Yi-chen Wu).
Not yet here (S1, W3+): synonyms, themes, time windows, quotas, dedupe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from cee.config import entities_config
from cee.db import connect


@dataclass
class Query:
    question: str
    entities: list[str] = field(default_factory=list)   # covered firms named in the question
    unmapped: list[str] = field(default_factory=list)   # known firms we hold no documents for
    mode: str = "entity"


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    entity_id: str | None
    segment: str | None
    doc_type: str
    source_tier: int
    published_at: str
    period_end: str | None
    section: str | None
    page: int | None
    rank: float
    text: str


def _alias_pattern(alias: str) -> re.Pattern:
    flags = 0 if alias.isupper() and len(alias) <= 5 else re.IGNORECASE  # tickers: exact case
    return re.compile(rf"(?<![\w.]){re.escape(alias)}(?![\w])", flags)


def _mentions(question: str, entry: dict) -> bool:
    names = [entry["name"], *entry.get("aliases", [])]
    return any(_alias_pattern(a).search(question) for a in names)


def resolve(question: str) -> Query:
    cfg = entities_config()
    q = Query(question=question)
    q.entities = [e["id"] for e in cfg["entities"] if _mentions(question, e)]
    q.unmapped = [e["id"] for e in cfg.get("expansion", []) if _mentions(question, e)]
    q.mode = "entity" if q.entities else "theme"
    return q


def _search_terms(q: Query) -> str:
    """Question minus firm names, as an OR query (ranking does the rest)."""
    text = q.question
    cfg = entities_config()
    for e in cfg["entities"] + cfg.get("expansion", []):
        for a in [e["name"], *e.get("aliases", [])]:
            text = _alias_pattern(a).sub(" ", text)
    return re.sub(r"['’]s\b", "", text)


SQL = """
WITH q AS (
  SELECT to_tsquery('english',
           coalesce(nullif(replace(plainto_tsquery('english', %(terms)s)::text, '&', '|'), ''),
                    'zzznomatch')) AS tsq
)
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, ts_rank_cd(c.tsv, q.tsq) AS rank, c.text
FROM chunks c JOIN documents d USING (doc_id), q
WHERE c.tsv @@ q.tsq
  AND {entity_filter}
ORDER BY rank DESC, c.chunk_id
LIMIT %(k)s
"""


def entity_filter(entity_ids: list[str]) -> tuple[str, dict]:
    """Hard filter. An entity reported inside a parent segment (MER -> BAC GWIM) only sees
    parent chunks tagged with that segment."""
    if not entity_ids:
        return "TRUE", {}
    clauses, params = [], {}
    by_id = {e["id"]: e for e in entities_config()["entities"]}
    for i, eid in enumerate(entity_ids):
        params[f"e{i}"] = eid
        clause = f"d.entity_id = %(e{i})s"
        e = by_id.get(eid, {})
        if e.get("parent") and e.get("reported_as"):
            params[f"p{i}"] = e["parent"]
            params[f"s{i}"] = [e["reported_as"], e["name"]]
            clause = f"({clause} OR (d.entity_id = %(p{i})s AND c.segment = ANY(%(s{i})s)))"
        clauses.append(clause)
    return "(" + " OR ".join(clauses) + ")", params


def search(q: Query, k: int = 8) -> list[Hit]:
    if q.unmapped and not q.entities:
        return []  # firm is known but not in the corpus: nothing is eligible
    where, params = entity_filter(q.entities)
    params.update(terms=_search_terms(q), k=k)
    with connect() as conn:
        rows = conn.execute(SQL.format(entity_filter=where), params).fetchall()
    return [Hit(**r) for r in rows]
