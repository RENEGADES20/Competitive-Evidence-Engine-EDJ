"""Full-text retrieval with hard entity/segment filters in SQL (ADR-001, ADR-004).

Skeleton placeholder, owner: S1 (Yi-chen Wu).
Synonyms and peer sets ("the five") come from config/entities.yaml (#89).
Time windows ("last 90 days", "since the start of the year") are filtered in SQL (#49).
Not yet here (S1, W3+): themes, quotas, dedupe.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from cee.config import entities_config
from cee.db import connect


@dataclass
class Query:
    question: str
    entities: list[str] = field(default_factory=list)   # covered firms named in the question
    unmapped: list[str] = field(default_factory=list)   # known firms we hold no documents for
    mode: str = "entity"
    window: tuple[date, date] | None = None              # published_at from..to, both inclusive

    @property
    def firms(self) -> list[str]:
        """Every firm the question names, covered first. Footer and gap path both read this."""
        return [*self.entities, *self.unmapped]


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


def _phrase_pattern(phrase: str) -> re.Pattern:
    return re.compile(rf"(?<![\w]){re.escape(phrase)}(?![\w])", re.IGNORECASE)


def _peer_phrases() -> list[str]:
    """Every peer-set phrase, longest first so "each of the five" is stripped whole."""
    phrases = [p for s in entities_config().get("peer_sets", []) for p in s["phrases"]]
    return sorted(phrases, key=len, reverse=True)


def _peer_members(question: str) -> set[str]:
    return {m for s in entities_config().get("peer_sets", [])
            if any(_phrase_pattern(p).search(question) for p in s["phrases"])
            for m in s["members"]}


_LAST_N = re.compile(r"\b(?:last|past)\s+(\d+)\s+(day|week|month)s?\b", re.IGNORECASE)
_START_OF_YEAR = [re.compile(r"\bsince\s+the\s+(?:start|beginning)\s+of\s+the\s+year\b", re.IGNORECASE),
                  re.compile(r"\byear[\s-]to[\s-]date\b", re.IGNORECASE),
                  re.compile(r"\bYTD\b")]   # "start of the year" = calendar year (specs/retrieval.md)


def _months_back(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    return date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


def _window(question: str, today: date) -> tuple[date, date] | None:
    if m := _LAST_N.search(question):
        n, unit = int(m.group(1)), m.group(2).lower()
        start = _months_back(today, n) if unit == "month" else today - timedelta(days=n * (7 if unit == "week" else 1))
        return start, today
    if any(p.search(question) for p in _START_OF_YEAR):
        return date(today.year, 1, 1), today
    return None


def resolve(question: str, today: date | None = None) -> Query:
    cfg = entities_config()
    q = Query(question=question)
    peers = _peer_members(question)
    q.entities = [e["id"] for e in cfg["entities"] if e["id"] in peers or _mentions(question, e)]
    q.unmapped = [e["id"] for e in cfg.get("expansion", []) if _mentions(question, e)]
    q.mode = "entity" if q.entities else "theme"
    q.window = _window(question, today or date.today())
    return q


def _search_terms(q: Query) -> str:
    """Question minus firm names, peer phrases and time phrases, as an OR query (ranking does
    the rest)."""
    text = q.question
    cfg = entities_config()
    for e in cfg["entities"] + cfg.get("expansion", []):
        for a in [e["name"], *e.get("aliases", [])]:
            text = _alias_pattern(a).sub(" ", text)
    for p in _peer_phrases():
        text = _phrase_pattern(p).sub(" ", text)
    for p in [_LAST_N, *_START_OF_YEAR]:
        text = p.sub(" ", text)
    return re.sub(r"['’]s\b", "", text)


def _synonym_pattern(key: str) -> re.Pattern:
    flags = 0 if key.removesuffix("s").isupper() else re.IGNORECASE  # NNA, FA, FAs, AI: exact case
    return re.compile(rf"(?<![\w]){re.escape(key)}(?![\w])", flags)


def expand_synonyms(terms: str) -> list[str]:
    """Synonyms of every config key found in the terms (key -> values only), in config order."""
    out: list[str] = []
    for key, values in (entities_config().get("synonyms") or {}).items():
        if _synonym_pattern(key).search(terms):
            out += [v for v in values if v not in out]
    return out


SYNONYM_BONUS = 2  # a synonym phrase match ranks 2x on top of the words (#89: Q22 gets NNA from 3 of the five)


def _tsquery_sql(terms: str) -> tuple[dict, dict]:
    """SQL fragments for SQL: the question's words OR'ed, plus each synonym as a phrase, and
    a rank bonus for synonym matches. No synonym -> words only, rank unchanged."""
    words = ("to_tsquery('english',\n"
             "           coalesce(nullif(replace(plainto_tsquery('english', %(terms)s)::text, '&', '|'), ''),\n"
             "                    'zzznomatch'))")
    params = {f"syn{i}": s for i, s in enumerate(expand_synonyms(terms))}
    if not params:
        return {"tsquery": words, "syn": "", "bonus": ""}, params
    phrases = " || ".join(f"phraseto_tsquery('english', %({name})s)" for name in params)
    return {"tsquery": f"{words}\n         || {phrases}",
            "syn": f",\n         {phrases} AS syn",
            "bonus": f" + {SYNONYM_BONUS} * ts_rank_cd(c.tsv, q.syn)"}, params


SQL = """
WITH q AS (
  SELECT {tsquery} AS tsq{syn}
)
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, ts_rank_cd(c.tsv, q.tsq){bonus} AS rank, c.text
FROM chunks c JOIN documents d USING (doc_id), q
WHERE c.tsv @@ q.tsq
  AND {entity_filter}
  AND {window_filter}
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


def window_filter(window: tuple[date, date] | None) -> tuple[str, dict]:
    """Hard filter. Inside a window only documents dated by the source count: a page dated
    by its download (date_basis = 'retrieved', ADR-007 T-09) is never "recent"."""
    if window is None:
        return "TRUE", {}
    return ("(d.date_basis = 'source' AND d.published_at BETWEEN %(w_from)s AND %(w_to)s)",
            {"w_from": window[0], "w_to": window[1]})


def search(q: Query, k: int = 8) -> list[Hit]:
    if q.unmapped and not q.entities:
        return []  # firm is known but not in the corpus: nothing is eligible
    where, params = entity_filter(q.entities)
    when, window_params = window_filter(q.window)
    terms = _search_terms(q)
    fragments, syn_params = _tsquery_sql(terms)
    params.update(window_params)
    params.update(syn_params, terms=terms, k=k)
    with connect() as conn:
        rows = conn.execute(SQL.format(**fragments, entity_filter=where, window_filter=when),
                            params).fetchall()
    return [Hit(**r) for r in rows]
