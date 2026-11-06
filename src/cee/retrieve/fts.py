"""Full-text retrieval with hard entity/segment filters in SQL (ADR-001, ADR-004).

Skeleton placeholder, owner: S1 (Yi-chen Wu).
Synonyms and peer sets ("the five") come from config/entities.yaml (#89).
Time windows ("last 90 days", "since the start of the year") are filtered in SQL (#49). The pool is over-fetched per firm and document type, then
near-duplicates are dropped and firms, document types and documents take turns (quotas), so
one filing's boilerplate repeated across four 10-Qs cannot fill the list (Q1: the NNA
definition took all 8 places; the earnings-call strategy commentary took none).
Themes (#116): a question that names one firm and a topic from config/topics.yaml also gets a
few tier 5 research chunks tagged with that topic (Q19: the EDJ filter dropped every survey on
younger investors). Several firms + a topic stay in entity mode until per-firm theme quotas (#117):
research slots pushed Q23's headcount figures out of the list.
Three retrieval modes (experimental branch exp/hybrid; #125, #126):
`search(q, mode="fts" | "hybrid" | "hybrid-norerank")`, default RETRIEVAL_MODE (fts). Both hybrid
modes (src/cee/retrieve/hybrid.py) need CEE_VECTORS=on and reuse this module's filters, keyword
terms and select().
"""
from __future__ import annotations

import calendar
import math
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, timedelta

from cee.config import entities_config, settings, vectors_enabled
from cee.db import connect
from cee.ingest.topics import load_topics, tag_text


@dataclass
class Query:
    question: str
    entities: list[str] = field(default_factory=list)   # covered firms named in the question
    unmapped: list[str] = field(default_factory=list)   # known firms we hold no documents for
    themes: list[str] = field(default_factory=list)     # top-level topics named (config/topics.yaml)
    mode: str = "entity"
    window: tuple[date, date] | None = None              # published_at from..to, both inclusive
    # Ask page filters (#63), all hard SQL filters; set them with apply_filters
    firm_filter: list[str] = field(default_factory=list)  # only these firms; empty = no firm filter
    date_range: tuple[date, date] | None = None          # published_at from..to, both inclusive
    keywords: list[str] = field(default_factory=list)     # every keyword must be in the passage

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
    date_basis: str = "source"   # "retrieved": dated by the stored copy, not the page (ADR-007 T-09)


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
_START_OF_YEAR = [re.compile(r"\bsince\s+the\s+(?:start|beginning)\s+of\s+(?:the|this)\s+year\b", re.IGNORECASE),
                  re.compile(r"\byear[\s-]to[\s-]date\b", re.IGNORECASE),
                  re.compile(r"\bso\s+far\s+this\s+year\b", re.IGNORECASE),
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
    topics = load_topics()
    named = tag_text(question, topics)
    q.themes = [t.topic_id for t in topics if t.parent is None and t.topic_id in named]
    q.mode = ("entity+theme" if q.themes and len(q.firms) == 1 else "entity") if q.entities else "theme"
    q.window = _window(question, today or date.today())
    return q


def apply_filters(q: Query, firms: list[str] | None = None, date_range: tuple[date, date] | None = None,
                  keywords: list[str] | None = None) -> Query:
    """Narrow a resolved question with the Ask page filters (#63). Firms intersect with the
    firms the question names (none named: the chosen firms); an empty intersection means
    nothing is eligible, never "every firm"."""
    if firms:
        q.firm_filter = list(firms)
        q.entities = [e for e in q.entities if e in firms] if q.entities else list(firms)
        q.unmapped = [u for u in q.unmapped if u in firms]
        q.mode = "entity"  # a firm filter means only these firms: no firm-less research (#116)
    q.date_range = date_range
    q.keywords = [k.strip() for k in keywords or [] if k.strip()]
    return q


def filters_sql(q: Query) -> tuple[str, dict]:
    """Date range and keywords as SQL WHERE clauses (the firm filter is entity_filter). A range
    counts only documents dated by the source, the same rule as a time window."""
    clauses, params = [], {}
    if q.date_range:
        clauses.append("(d.date_basis = 'source' AND d.published_at BETWEEN %(r_from)s AND %(r_to)s)")
        params |= {"r_from": q.date_range[0], "r_to": q.date_range[1]}
    for i, kw in enumerate(q.keywords):
        clauses.append(f"c.tsv @@ phraseto_tsquery('english', %(kw{i})s)")
        params[f"kw{i}"] = kw
    return " AND ".join(clauses) or "TRUE", params


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
    text = QUESTION_WORDS.sub(" ", text)
    return re.sub(r"['’]s\b", "", text)


# Words that say what to do with the evidence, not what it is about (Q8 "Compare how ... describe"
# matched a stock-plan note that "describes" the plan).
QUESTION_WORDS = re.compile(r"\b(?:compare[sd]?|comparison|describe[sd]?|explain|discuss|tell|say|says|"
                            r"said|summari[sz]e|list|versus|vs|itself|themselves|their|its)\b", re.IGNORECASE)


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


def synonym_only_words() -> list[str]:
    """Ambiguous words searched only through their synonyms (config `synonym_only`). In filings
    the bare verb "pay" almost always means paying an obligation, not advisor pay (Q29: a
    clearing-guarantee note outranked the payout passage)."""
    return list(entities_config().get("synonym_only") or [])


def keyword_terms(q: Query) -> tuple[str, list[str]]:
    """(words for the FTS query, synonym phrases). Synonyms are read from the whole question;
    `synonym_only` words are then left out of the words."""
    terms = _search_terms(q)
    if q.window:
        terms += " " + RECENCY_TERMS
    synonyms = expand_synonyms(terms)
    for word in synonym_only_words():
        terms = _synonym_pattern(word).sub(" ", terms)
    return terms, synonyms


def _tsquery_sql(terms: str, synonyms: list[str] | None = None) -> tuple[dict, dict]:
    """SQL fragments for SQL: the question's words OR'ed, plus each synonym as a phrase."""
    words = ("to_tsquery('english',\n"
             "           coalesce(nullif(replace(plainto_tsquery('english', %(terms)s)::text, '&', '|'), ''),\n"
             "                    'zzznomatch'))")
    synonyms = expand_synonyms(terms) if synonyms is None else synonyms
    params = {f"syn{i}": s for i, s in enumerate(synonyms)}
    if not params:
        return {"tsquery": words}, params
    phrases = " || ".join(f"phraseto_tsquery('english', %({name})s)" for name in params)
    return {"tsquery": f"{words}\n         || {phrases}"}, params


DENSITY_WEIGHT = 0.1  # ts_rank_cd only breaks ties between chunks covering the same words


def rank_sql(conn, terms: str, synonyms: dict[str, str]) -> tuple[str, dict]:
    """Rank = sum of the IDF of every question word and synonym phrase the chunk contains,
    plus a little term density. ts_rank_cd alone counts "net", "new" and "assets" (in
    thousands of chunks) like "strategy", so a footnote that defines NNA three times beat the
    earnings-call passage on NNA strategy (Q1). IDF is counted over the loaded corpus."""
    lexemes = [r["lexeme"] for r in conn.execute(
        "SELECT lexeme FROM unnest(to_tsvector('english', %(terms)s))", {"terms": terms}).fetchall()]
    probes = {f"w{i}": ("%({0})s::tsquery", "'" + lx.replace("'", "''") + "'") for i, lx in enumerate(lexemes)}
    probes |= {f"p{name}": (f"phraseto_tsquery('english', %({{0}})s)", phrase)
               for name, phrase in synonyms.items()}
    if not probes:
        return f"{DENSITY_WEIGHT} * ts_rank_cd(c.tsv, q.tsq)", {}
    values = {name: value for name, (_, value) in probes.items()}
    counts = ", ".join(f"count(*) FILTER (WHERE tsv @@ {tmpl.format(name)}) AS {name}"
                       for name, (tmpl, _) in probes.items())
    row = conn.execute(f"SELECT count(*) AS n_all, {counts} FROM chunks", values).fetchone()
    parts, params = [], {}
    for name, (tmpl, value) in probes.items():
        if not row[name]:
            continue
        params[name], params[f"{name}_idf"] = value, math.log(row["n_all"] / row[name])
        parts.append(f"(c.tsv @@ {tmpl.format(name)})::int * %({name}_idf)s")
    parts.append(f"{DENSITY_WEIGHT} * ts_rank_cd(c.tsv, q.tsq)")
    params["boilerplate"] = BOILERPLATE
    return (f"({' + '.join(parts)})\n"
            f"         * CASE WHEN c.text ~* ANY(%(boilerplate)s) THEN {BOILERPLATE_WEIGHT} ELSE 1 END"), params


# Safe-harbor and legend paragraphs name every strategy word and are never evidence
# (Q12: the "forward-looking statements" slide of every SCHW deck outranked the strategy slides).
BOILERPLATE = [r"forward-looking statements", r"safe harbor"]
BOILERPLATE_WEIGHT = 0.2


SQL = """
WITH q AS (
  SELECT {tsquery} AS tsq
), scored AS (
  SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
         d.published_at::text AS published_at, d.period_end::text AS period_end,
         c.section, c.page, {rank} AS rank, c.text, d.date_basis
  FROM chunks c JOIN documents d USING (doc_id), q
  WHERE {match}
    AND {entity_filter}
    AND {window_filter}
    AND {filters}
), pooled AS (
  SELECT *, row_number() OVER (PARTITION BY entity_id, doc_type ORDER BY rank DESC, chunk_id) AS rn
  FROM scored
)
SELECT chunk_id, doc_id, entity_id, segment, doc_type, source_tier, published_at, period_end,
       section, page, rank, text, date_basis
FROM pooled
WHERE rn <= %(per_group)s
ORDER BY rank DESC, chunk_id
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


def theme_filter(themes: list[str]) -> tuple[str, dict]:
    """Hard filter for the research part of entity+theme: no firm, and the chunk tagged with a
    topic the question names (a sub-topic tag always carries its parent, so top-level is enough)."""
    return ("(d.entity_id IS NULL AND EXISTS (SELECT 1 FROM chunk_topics t\n"
            "                                       WHERE t.chunk_id = c.chunk_id AND t.topic_id = ANY(%(themes)s)))",
            {"themes": themes})


def window_filter(window: tuple[date, date] | None) -> tuple[str, dict]:
    """Hard filter. Inside a window only documents dated by the source count: a page dated
    by its download (date_basis = 'retrieved', ADR-007 T-09) is never "recent"."""
    if window is None:
        return "TRUE", {}
    return ("(d.date_basis = 'source' AND d.published_at BETWEEN %(w_from)s AND %(w_to)s)",
            {"w_from": window[0], "w_to": window[1]})


K = 20              # chunks handed to the model (specs/retrieval.md)
POOL_PER_GROUP = 15  # over-fetch: best chunks per (firm, document type) before quotas
MAX_PER_DOC = 3      # no single document fills the list
DUP_JACCARD = 0.6    # word 5-gram overlap above which a chunk repeats a kept one (boilerplate)
FLOOR = 0.3          # share of the firm's best rank a chunk needs to take a slot
WINDOW_MAX_PER_DOC = 8
THEME_K = 4          # research slots in entity+theme; the firm keeps the rest (#116)
THEME_MAX_PER_DOC = 2
# Window questions name no topic ("What's new on Raymond James in the last 90 days?"), so these
# rank news-like passages (headlines, launches, records) above tables of contents.
RECENCY_TERMS = "announced launched introduced new record acquisition agreement completed increased hired"


def _shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}


def _similar(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def select(pool: list[Hit], k: int = K, floor: float | None = None,
           max_per_doc: int | None = None, dup_jaccard: float | None = None) -> list[Hit]:
    """Quotas over a rank-ordered pool: firms take turns; within a firm, document types take
    turns (best-ranked type first); a document gives at most MAX_PER_DOC chunks; a chunk that
    repeats a kept one (the same definition in every 10-Q) is dropped. A chunk ranked below
    FLOOR x its firm's best chunk gets no slot: quotas spread relevant evidence, they do not
    pad the list with a document type that has nothing on the question.
    floor / max_per_doc / dup_jaccard: None -> FLOOR / MAX_PER_DOC / DUP_JACCARD (hybrid modes pass
    their own values, #126; fts mode never does)."""
    floor = FLOOR if floor is None else floor
    dup_jaccard = DUP_JACCARD if dup_jaccard is None else dup_jaccard
    max_per_doc = MAX_PER_DOC if max_per_doc is None else max_per_doc
    firms: OrderedDict[str | None, OrderedDict[str, list[Hit]]] = OrderedDict()
    best: dict[str | None, float] = {}
    for h in pool:  # first seen = best ranked
        best.setdefault(h.entity_id, h.rank)
        if h.rank >= floor * best[h.entity_id]:
            firms.setdefault(h.entity_id, OrderedDict()).setdefault(h.doc_type, []).append(h)
    turn = dict.fromkeys(firms, 0)
    kept: list[Hit] = []
    kept_shingles: list[set] = []
    per_doc: dict[str, int] = {}

    def take(firm) -> bool:
        types = firms[firm]
        names = [t for t in types if types[t]]
        for i in range(len(names)):
            t = names[(turn[firm] + i) % len(names)]
            while types[t]:
                h = types[t].pop(0)
                if per_doc.get(h.doc_id, 0) >= max_per_doc:
                    continue
                sh = _shingles(h.text)
                if any(_similar(sh, other) > dup_jaccard for other in kept_shingles):
                    continue
                kept.append(h)
                kept_shingles.append(sh)
                per_doc[h.doc_id] = per_doc.get(h.doc_id, 0) + 1
                turn[firm] = (turn[firm] + i + 1) % len(names)
                return True
        return False

    while len(kept) < k:
        progressed = False
        for firm in firms:
            if len(kept) >= k:
                break
            progressed |= take(firm)
        if not progressed:
            break
    return kept


MODES = ("fts", "hybrid", "hybrid-norerank")


class HybridUnavailable(RuntimeError):
    """Hybrid mode asked for while the optional vectors module is off (ADR-009)."""


HYBRID_NEEDS_VECTORS = (
    "Hybrid retrieval needs the optional vectors module: set CEE_VECTORS=on, install "
    "requirements-vectors.txt and fill the vectors (docs/RUN.md, 'Hybrid retrieval'), or use "
    "RETRIEVAL_MODE=fts.")


def search(q: Query, k: int = K, mode: str | None = None) -> list[Hit]:
    """Retrieve for one request. mode: "fts" | "hybrid" | "hybrid-norerank"; None -> RETRIEVAL_MODE
    (default fts). hybrid-norerank (#126): the same candidates as hybrid, final order by RRF score."""
    mode = (mode or settings().retrieval_mode).strip().lower()
    if mode == "fts":
        return fts_search(q, k)
    if mode in ("hybrid", "hybrid-norerank"):
        if not vectors_enabled():  # checked before the import: vectors off never loads hybrid
            raise HybridUnavailable(HYBRID_NEEDS_VECTORS)
        from cee.retrieve import hybrid  # imported late: fts mode never loads a model
        return hybrid.search(q, k) if mode == "hybrid" else hybrid.search(q, k, rerank=False)
    raise ValueError(f"unknown retrieval mode {mode!r}; use one of {', '.join(MODES)}")


def fts_search(q: Query, k: int = K) -> list[Hit]:
    if q.unmapped and not q.entities:
        return []  # firm is known but not in the corpus: nothing is eligible
    if q.firm_filter and not q.entities:
        return []  # the firm filter leaves none of the firms the question names
    where, params = entity_filter(q.entities)
    filters, filter_params = filters_sql(q)
    params.update(filter_params)
    window, window_params = window_filter(q.window)
    terms, synonyms = keyword_terms(q)
    fragments, syn_params = _tsquery_sql(terms, synonyms)
    # A window question ("what's new ... in the last 90 days") asks about everything inside the
    # window, so there the words only rank; outside a window they must match.
    match = "TRUE" if q.window else "c.tsv @@ q.tsq"
    params.update(syn_params)
    params.update(window_params, terms=terms, per_group=POOL_PER_GROUP)
    research_rows = []
    with connect() as conn:
        rank, rank_params = rank_sql(conn, terms, syn_params)
        params.update(rank_params)
        sql = SQL.format(**fragments, rank=rank, match=match, entity_filter=where, window_filter=window,
                         filters=filters)
        rows = conn.execute(sql, params).fetchall()
        if q.mode == "entity+theme":
            themes, theme_params = theme_filter(q.themes)
            sql = SQL.format(**fragments, rank=rank, match=match, entity_filter=themes, window_filter=window,
                             filters=filters)
            research_rows = conn.execute(sql, params | theme_params).fetchall()
    pool = [Hit(**r) for r in rows]
    # Inside a window every document is on topic, so no floor; one filing may be all there is.
    opts = {"floor": 0, "max_per_doc": WINDOW_MAX_PER_DOC} if q.window else {}
    research = select([Hit(**r) for r in research_rows], min(THEME_K, k),
                      **{**opts, "max_per_doc": THEME_MAX_PER_DOC})
    hits = select(pool, k - len(research), **opts) + research
    if q.window:  # recency questions read newest first (Q26)
        hits.sort(key=lambda h: h.published_at, reverse=True)
    return hits
