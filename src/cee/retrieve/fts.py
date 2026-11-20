"""Full-text retrieval with hard entity/segment filters in SQL (ADR-001, ADR-004).

Skeleton placeholder, owner: S1 (Yi-chen Wu).
Synonyms and peer sets ("the five") come from config/entities.yaml (#89).
Time windows ("last 90 days", "since the start of the year") are filtered in SQL (#49). The pool is over-fetched per firm and document type, then
near-duplicates are dropped and firms, document types and documents take turns (quotas), so
one filing's boilerplate repeated across four 10-Qs cannot fill the list (Q1: the NNA
definition took all 8 places; the earnings-call strategy commentary took none).
Themes (#116): a question that names one firm and a topic from config/topics.yaml also gets a
few tier 5 research chunks tagged with that topic (Q19: the EDJ filter dropped every survey on
younger investors).
Per-firm theme quotas (#117): with several firms + a theme, every firm's chunks on the theme take
its turns first and a firm with none is reported as a gap (Q21: "these five" and the wealth
transfer; Q12: Schwab, Edward Jones and client acquisition, a firm theme from config/entities.yaml).
Budget (#181, ADR-013): the number of passages grows with the number of firms the question names
(budget()), and Merrill's own documents plus BAC's GWIM chunks share one firm's quota
(quota_firms()), so five firms do not each drop to 3 passages when Merrill fills two groups (Q22, Q24).
Token budget (#213, ADR-019): the retrieved set is filled up to an estimated token budget
(characters / 4, budget_tokens(): 40k, five firms 60k) instead of a passage count, from a pool of
the best 30 chunks per firm and document type (POOL_PER_GROUP); both chosen from a grid.
Document-type scope (#179, ADR-015): Form ADV brochures only for fee and pricing questions and
never inside a time window; no trade press (tier 4) for benchmark questions (doc_type_scope()).
Slot order inside a firm (#198, #199, ADR-016): trade press takes a turn only when the firm's other
document types have nothing left (a full list still keeps one trade chunk in place of a repeat), and
a document type gives a new document, the newest among near-equal ranks, before a second chunk of a
used one (speaker-turn transcripts of one call crowded out the firm's other calls).
Answer turns and key matching (#203, ADR-017): an analyst's question turn brings management's next
turn (same hard filters); synonym keys fire hyphenated and inflected, and a multi-word key is also
searched as a phrase.
Firm scope (#205, ADR-018): "an advisor-led model" is a peer phrase (MS, EDJ, Merrill, RJF; Q15),
and a theme question naming only the home firm (config `home_firm`) also gets the other covered
firms' chunks on the theme (theme_peers, Q19), filtered in SQL and cut at a floor across them.
"""
from __future__ import annotations

import calendar
import math
import re
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from cee.config import entities_config
from cee.db import connect
from cee.ingest.topics import Topic, _pattern, load_topics, tag_text
from cee.ingest.transcript import HEADINGS as TRANSCRIPT_HEADINGS


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
    # Home-firm theme rule (#205, ADR-018): other covered firms searched only on the theme
    theme_peers: list[str] = field(default_factory=list)
    # Question planner (#214, ADR-020): one part of a question searches its own words (None = the
    # question's) and keeps the whole question's doc-type scope (None = computed from this query).
    terms: str | None = None
    scope: tuple[list[str], list[int]] | None = None
    # Sub-question decomposition (#245, ADR-021 rule 6): a competitor sub-question of a home-firm
    # market question (Q19) searches its firm on the theme only (SQL AND of the theme's keywords on
    # the firm pass, no answer-turn attachment), the ADR-018 safeguard of the theme peers.
    on_theme_only: bool = False
    # #247 part 2: a per-period sub-search (series aspects) keeps documents whose period_end falls in
    # this range (both inclusive); a hard SQL filter like the window. Chunk ids in exclude_ids leave the
    # SQL pool before any cut (only the per-period pass sets it, so the main searches are unchanged).
    period_range: tuple[date, date] | None = None
    exclude_ids: list[str] = field(default_factory=list)

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
    on_theme: bool = False       # entity+theme: a firm chunk with the theme's keywords (#117)
    part_id: str | None = None   # #214: the plan part that kept it (p1.., "research", "peers")
    origin: str = "search"       # #247: "corrective" (map re-search), "period" (per-period pass), "pinned (registered definition / population chunk)


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


def firm_themes() -> tuple[Topic, ...]:
    """Themes firms talk about that tier 5 research is not indexed by (config `firm_themes`, #117)."""
    return tuple(Topic(t["id"], t["label"], None, _pattern(t["keywords"]))
                 for t in entities_config().get("firm_themes") or [])


def _themes() -> dict[str, Topic]:
    """Every theme a question can name: top-level topics, then firm themes."""
    return {t.topic_id: t for t in [*load_topics(), *firm_themes()] if t.parent is None}


def theme_label(q: Query) -> str:
    themes = _themes()
    return " / ".join(themes[t].label for t in q.themes if t in themes)


def home_theme_peers(firms: list[str], mode: str) -> list[str]:
    """Covered firms whose chunks on the theme join a theme question that names only the home
    firm (config `home_firm`, #205, ADR-018): the members of its `theme_peers` peer set minus the
    home firm (Q19: MS, SCHW, MER, RJF). Empty for any other question, including one that also
    names a firm we hold no documents for ("Edward Jones and Vanguard on fees")."""
    cfg = entities_config()
    home = cfg.get("home_firm") or {}
    if mode != "entity+theme" or not home.get("id") or firms != [home["id"]]:
        return []
    sets = {s["id"]: s["members"] for s in cfg.get("peer_sets", [])}
    return [m for m in sets.get(home.get("theme_peers"), []) if m != home["id"]]


def resolve(question: str, today: date | None = None) -> Query:
    cfg = entities_config()
    q = Query(question=question)
    peers = _peer_members(question)
    q.entities = [e["id"] for e in cfg["entities"] if e["id"] in peers or _mentions(question, e)]
    q.unmapped = [e["id"] for e in cfg.get("expansion", []) if _mentions(question, e)]
    topics = load_topics()
    themed = question
    for phrase in entities_config().get("metric_phrases") or []:  # a figure, not a theme (Q23)
        themed = _phrase_pattern(phrase).sub(" ", themed)
    named = tag_text(themed, topics) | tag_text(themed, firm_themes())
    q.themes = [t for t in _themes() if t in named]
    q.mode = ("entity+theme" if q.themes else "entity") if q.entities else "theme"
    q.theme_peers = home_theme_peers(q.firms, q.mode)
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
        q.theme_peers = []  # ... and no other firms on the theme (#205)
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
    if q.period_range:   # #247 part 2: per-period sub-search, by the document's period end
        clauses.append("d.period_end BETWEEN %(pr_from)s AND %(pr_to)s")
        params |= {"pr_from": q.period_range[0], "pr_to": q.period_range[1]}
    if q.exclude_ids:    # #247 part 2: kept chunks leave the SQL pool before the cut
        clauses.append("c.chunk_id <> ALL(%(excl_ids)s)")
        params["excl_ids"] = list(q.exclude_ids)
    return " AND ".join(clauses) or "TRUE", params


def doc_type_scope(q: Query) -> tuple[list[str], list[int]]:
    """(document types, source tiers) this question does not search (config `doc_type_scope`,
    #179, ADR-015). Form ADV brochures (`adv`) answer fee and pricing questions; elsewhere their
    1,156 chunks crowded out filings, supplements and press releases (Q23, Q24), and a brochure
    revision is not news, so they are never searched inside a time window (Q26, Q27). They open on
    the fees_pricing theme or a term: "Form ADV", "ADV", "brochure(s)", "compensation" (Q25).
    Benchmark questions (a reported metric across firms: "advisor headcount", "net new assets",
    "assets per advisor", "attrition rate"; Q11, Q22-Q24, Q28) do not search trade press (tier 4)."""
    cfg = entities_config().get("doc_type_scope") or {}
    types: list[str] = []
    tiers: list[int] = []
    adv = cfg.get("adv")
    if adv is not None:
        opens = (any(t in q.themes for t in adv.get("themes") or [])
                 or any(_alias_pattern(t).search(q.question) for t in adv.get("terms") or []))
        if not opens or (adv.get("never_in_window") and q.window):
            types.append("adv")
    bench = cfg.get("benchmark")
    if (bench and len(q.entities) >= bench.get("min_firms", 2)
            and any(_phrase_pattern(p).search(q.question) for p in bench.get("phrases") or [])):
        tiers += [t for t in bench.get("exclude_tiers") or [] if t not in tiers]
    return types, tiers


def pinned_scope(q: Query) -> tuple[list[str], list[int]]:
    """The doc-type scope for pinned ids (#247 part 2, TL D1 narrowed): every exclusion except `adv`
    (a registered Form ADV Part 1A figure is curated, one chunk, and crowds nothing out); tier 4 stays."""
    types, tiers = q.scope if q.scope is not None else doc_type_scope(q)
    return [t for t in types if t != "adv"], list(tiers)


def doc_type_scope_sql(q: Query) -> tuple[str, dict]:
    """doc_type_scope() as a hard SQL filter; TRUE when nothing is left out. A plan part (#214)
    carries the whole question's scope in q.scope, so a one-firm part of a benchmark question
    keeps the tier 4 exclusion."""
    types, tiers = q.scope if q.scope is not None else doc_type_scope(q)
    clauses, params = [], {}
    if types:
        clauses.append("d.doc_type <> ALL(%(scope_types)s)")
        params["scope_types"] = types
    if tiers:
        clauses.append("d.source_tier <> ALL(%(scope_tiers)s)")
        params["scope_tiers"] = tiers
    return " AND ".join(clauses) or "TRUE", params


def _search_terms(q: Query) -> str:
    """Question minus firm names, peer phrases and time phrases, as an OR query (ranking does
    the rest). A plan part (#214) searches its own words (q.terms) through the same clean-up."""
    text = q.question if q.terms is None else q.terms
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


INFLECTION = r"(?:s|es|ed|ing)?"  # a lower-case key's last word also fires inflected (#203)


def _synonym_pattern(key: str) -> re.Pattern:
    """All-caps keys (NNA, FA, FAs, AI) match whole word in exact case. Other keys match in any
    case, with a hyphen or spaces between their words ("stock-plan" fires `stock plan`, Q13) and
    an inflected last word (`recruit` fires on "recruiting", Q2/Q7; #203). Keys in config
    `synonym_exact` keep the plain whole-phrase match (gap questions, see config)."""
    if key.removesuffix("s").isupper():
        return re.compile(rf"(?<![\w]){re.escape(key)}(?![\w])")
    words = re.split(r"[\s-]+", key.strip())
    body = r"[\s-]+".join(re.escape(w) for w in words)
    if key not in (entities_config().get("synonym_exact") or []):
        body += INFLECTION
    return re.compile(rf"(?<![\w]){body}(?![\w])", re.IGNORECASE)


def expand_synonyms(terms: str) -> list[str]:
    """Synonyms of every config key found in the terms (key -> values only), in config order.
    A multi-word key is searched as a phrase too, ahead of its values (#203: "net new assets"
    in Q22 scored only its three common words, so the table row "Net new assets for the period"
    lost to prose that repeats "definition" and "metric")."""
    out: list[str] = []
    for key, values in (entities_config().get("synonyms") or {}).items():
        if _synonym_pattern(key).search(terms):
            phrase = [key] if len(re.split(r"[\s-]+", key.strip())) > 1 else []
            out += [v for v in [*phrase, *values] if v not in out]
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


def entity_filter(entity_ids: list[str], prefix: str = "") -> tuple[str, dict]:
    """Hard filter. An entity reported inside a parent segment (MER -> BAC GWIM) only sees
    parent chunks tagged with that segment. prefix keeps the parameter names apart when two
    entity filters share one query (the theme peers, #205)."""
    if not entity_ids:
        return "TRUE", {}
    clauses, params = [], {}
    by_id = {e["id"]: e for e in entities_config()["entities"]}
    for i, eid in enumerate(entity_ids):
        e_, p_, s_ = f"{prefix}e{i}", f"{prefix}p{i}", f"{prefix}s{i}"
        params[e_] = eid
        clause = f"d.entity_id = %({e_})s"
        e = by_id.get(eid, {})
        if e.get("parent") and e.get("reported_as"):
            params[p_] = e["parent"]
            params[s_] = [e["reported_as"], e["name"]]
            clause = f"({clause} OR (d.entity_id = %({p_})s AND c.segment = ANY(%({s_})s)))"
        clauses.append(clause)
    return "(" + " OR ".join(clauses) + ")", params


def theme_filter(themes: list[str]) -> tuple[str, dict]:
    """Hard filter for the research part of entity+theme: no firm, and the chunk tagged with a
    topic the question names (a sub-topic tag always carries its parent, so top-level is enough)."""
    return ("(d.entity_id IS NULL AND EXISTS (SELECT 1 FROM chunk_topics t\n"
            "                                       WHERE t.chunk_id = c.chunk_id AND t.topic_id = ANY(%(themes)s)))",
            {"themes": themes})


def on_theme_filter(themes: list[str]) -> tuple[str, dict]:
    """The firm chunks on the theme: the text has one of the theme's keywords, matched with the
    topic tagger's own pattern (Postgres regex, same look-arounds, any case)."""
    by_id = _themes()
    pattern = "|".join(f"(?:{by_id[t].pattern.pattern})" for t in themes if t in by_id)
    return "c.text ~* %(on_theme)s", {"on_theme": pattern or "(?!)"}


def window_filter(window: tuple[date, date] | None) -> tuple[str, dict]:
    """Hard filter. Inside a window only documents dated by the source count: a page dated
    by its download (date_basis = 'retrieved', ADR-007 T-09) is never "recent"."""
    if window is None:
        return "TRUE", {}
    return ("(d.date_basis = 'source' AND d.published_at BETWEEN %(w_from)s AND %(w_to)s)",
            {"w_from": window[0], "w_to": window[1]})


K = 20              # chunks handed to the model for a question naming 0 or 1 firm (specs/retrieval.md)
POOL_PER_GROUP = 30  # over-fetch: best chunks per (firm, document type) before quotas (#213: 15 -> 30)
MAX_PER_DOC = 3      # no single document fills the list
DUP_JACCARD = 0.6    # word 5-gram overlap above which a chunk repeats a kept one (boilerplate)
FLOOR = 0.3          # share of the firm's FLOOR_BASE-th best rank a chunk needs to take a slot
FLOOR_BASE = 2       # the floor is measured from a firm's 2nd-best chunk, so one outlier does not
                     # lift it for the whole firm (#166, ADR-014: the Merrill answer BAC-TR-2026Q2#63
                     # at 10.65 dropped BAC-10K-2025#246 at 2.77 from Q28)
WINDOW_MAX_PER_DOC = 8
THEME_K = 4          # research slots in entity+theme; the firm keeps the rest (#116)
THEME_MAX_PER_DOC = 2
THEME_FIRST = 1      # entity+theme: each firm's best chunk on the theme is sure of a slot (#117)
# Window questions name no topic ("What's new on Raymond James in the last 90 days?"), so these
# rank news-like passages (headlines, launches, records) above tables of contents.
RECENCY_TERMS = "announced launched introduced new record acquisition agreement completed increased hired"


PER_FIRM = 6         # passages per named firm once the firms outgrow K (#181, ADR-013)
# Token budget (#213, ADR-019): None = the passage rule above (budget()); an int B = estimated
# tokens (characters / 4) of the retrieved set for a question naming 0 or 1 firm, growing per firm
# like the passage rule (budget_tokens()). Module-level so the eval grid can swap it.
TOKEN_BUDGET: int | None = 40000  # chosen from the #213 grid (ADR-019); five firms get 60000
CHARS_PER_TOKEN = 4

# Slot order inside a firm's turn (#198, #199, ADR-016); trade press last is off inside a time
# window, both are off for the tier 5 research part. Module-level so the eval grid can swap them.
TIER_LAST = 0        # tier 4 trade press: the first TIER_LAST trade chunks of a firm take turns
                     # like any document type; after that trade takes a turn only when no other
                     # document type of the firm can give a chunk; None = no rule
LAST_TIERS = (4,)
TRADE_KEEP = True    # with TIER_LAST: a firm whose trade chunks all waited and found the list full
                     # gets its best one in place of a repeated document's chunk (Q7, Q29 keep *:trade)
NEW_DOC_FIRST = True  # a document type gives a document not yet in the list before a second
                      # chunk of a used one (speaker-turn transcripts of one call, #199)
NEWEST_BAND = 0.9     # among unused documents ranked within this share of the type's best, the
                      # newest wins (Q11: a later call 5% below an older one); None = rank order


# Answer turn with its question turn (#203, ADR-017): an analyst's question turn on a call is kept
# for the question's words, but the answer is in management's next turn (Q6: RJF-TR-2026Q1 #45
# kept, the CEO's answer #46 a second chunk of the same call and left out). "attach": the answer
# turn is kept right after its question turn; "replace": in its place; None: no rule.
PAIR_TURNS: str | None = "attach"
_HANDOFF = re.compile(r"^(?:Operator|Moderator)$|^Q - [A-Z]")
# A speaker label with an executive title is management, whose "?" hands over to a colleague
# ("... Alastair?"), not an analyst's question (#203: BAC-TR-2026Q2 #6, SCHW-TR-2026Q1 #49).
_EXECUTIVE = re.compile(r"\b(?:CEO|CFO|COO|CIO|CTO|President|Director|Officer|Chair(?:man|woman)?|VP|"
                        r"Vice President|Executive|Treasurer|Investor Relations|Head of|"
                        r"Company Representative)\b|^A - [A-Z]")


def is_question_turn(h: Hit) -> bool:
    """A transcript chunk that asks: it carries the operator hand-off ("Operator" / "Moderator"
    paragraph, Bloomberg "Q - " label) that leads an analyst's turn, or its last paragraph ends
    with "?" and its speaker label has no executive title."""
    if h.doc_type != "transcript":
        return False
    paras = [p.strip() for p in re.split(r"\n\s*\n", h.text) if p.strip()]
    if not paras:
        return False
    if any(_HANDOFF.match(p) for p in paras):
        return True
    label = next((p for p in paras if p not in TRANSCRIPT_HEADINGS), "")
    return paras[-1].endswith("?") and not _EXECUTIVE.search(label)


ANSWER_SQL = """
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, c.text, d.date_basis, qt.chunk_id AS question_id
FROM chunks qt JOIN chunks c ON c.doc_id = qt.doc_id AND c.seq = qt.seq + 1
     JOIN documents d ON d.doc_id = c.doc_id
WHERE qt.chunk_id = ANY(%(question_ids)s)
  AND {entity_filter}
  AND {window_filter}
  AND {filters}
"""


def answer_turns(conn, questions: list[Hit], entity_where: str, window: str, filters: str,
                 params: dict) -> dict[str, Hit]:
    """{question chunk_id: its answer turn}: the next chunk of the same call, fetched with every
    hard filter of the main pass (entity/segment, window, date range, keywords, doc-type scope) but
    no word match, so a turn the filters exclude (a BAC consumer turn in a Merrill question) never
    comes in. A next chunk that is itself a question turn is not an answer."""
    if not questions:
        return {}
    by_id = {h.chunk_id: h for h in questions}
    sql = ANSWER_SQL.format(entity_filter=entity_where, window_filter=window, filters=filters)
    out: dict[str, Hit] = {}
    for r in conn.execute(sql, params | {"question_ids": list(by_id)}).fetchall():
        r = dict(r)
        q = by_id[r.pop("question_id")]
        a = Hit(**r, rank=q.rank, on_theme=q.on_theme)
        if not is_question_turn(a):
            out[q.chunk_id] = a
    return out


def per_firm_budget(n_firms: int) -> int:
    """k for a question naming n >= 2 firms: max(K, PER_FIRM x n), so 2-3 firms keep 20 and the
    five get 30. Chosen from a grid (6, 7, 8 per firm; 20 + 5 per extra firm) as the smallest
    rule that brought Q22 and Q24 back with no question worse (#181)."""
    return max(K, PER_FIRM * n_firms)


# Module-level so the eval grid can swap the rule (#181).
BUDGET_RULE = per_firm_budget


def budget(q: Query) -> int:
    """Passages handed to the model for this question: K for 0 or 1 named firm, more for several
    firms so each keeps its best evidence (#181). Merrill is one firm (q.entities lists MER once);
    firms we hold no documents for do not count. The theme peers' slots (#205) come on top."""
    n = len(q.entities)
    return (K if n <= 1 else max(K, BUDGET_RULE(n))) + peer_slots(q)


def budget_tokens(q: Query) -> int | None:
    """Estimated tokens of the retrieved set (#213, ADR-019), None in passage mode (TOKEN_BUDGET
    None). ADR-013's growth in tokens: B for 0 or 1 named firm, max(B, B x PER_FIRM x n // K) for
    n firms (the same 6-of-20 share per firm: 2-3 firms keep B, the five get 1.5 x B). The theme
    peers' passages (#205) are outside it."""
    if TOKEN_BUDGET is None:
        return None
    n = len(q.entities)
    return TOKEN_BUDGET if n <= 1 else max(TOKEN_BUDGET, TOKEN_BUDGET * PER_FIRM * n // K)


def hit_tokens(h: Hit) -> float:
    """Estimated tokens of one passage: characters / 4, unrounded (#213)."""
    return len(h.text) / CHARS_PER_TOKEN


PEER_THEME_PER_FIRM = 2  # home-firm theme rule (#205): slots per peer firm, on the theme only


def peer_slots(q: Query) -> int:
    """Most passages the theme peers can add (#205); 0 without peers."""
    return PEER_THEME_PER_FIRM * len(getattr(q, "theme_peers", None) or [])


def peer_floor(pool: list[Hit], floor: float | None = None) -> list[Hit]:
    """The peers' pool cut at FLOOR x its FLOOR_BASE-th best rank across all peers as one group
    (its lowest with fewer chunks): a firm whose only text on the theme is a footnote (Merrill's
    "Top 40 Advisors Under 40" rankings at 3.3 vs Schwab's 29.5 in Q19) takes no slot, which a
    per-firm floor would not do. Kept inside a time window too (#205)."""
    floor = FLOOR if floor is None else floor
    ranks = sorted((h.rank for h in pool), reverse=True)
    if not ranks:
        return []
    base = ranks[min(FLOOR_BASE, len(ranks)) - 1]
    return [h for h in pool if h.rank >= floor * base]


def _shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i:i + n]) for i in range(max(1, len(words) - n + 1))}


def _similar(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def quota_firms(entity_ids: list[str]) -> dict[str, str]:
    """{parent: child} for a named firm reported inside a parent's segment whose parent is not
    named itself (MER -> BAC GWIM/Merrill, #181). The entity filter lets only the child's segment
    of the parent through, so those parent chunks are the child's evidence and share its quota:
    the question names one firm, so it takes one firm's slots."""
    by_id = {e["id"]: e for e in entities_config()["entities"]}
    return {e["parent"]: eid for eid in entity_ids
            if (e := by_id.get(eid, {})).get("parent") and e.get("reported_as") and e["parent"] not in entity_ids}


def select(pool: list[Hit], k: int = K, floor: float | None = None,
           max_per_doc: int | None = None, firm_of: dict[str, str] | None = None,
           floor_base: int | None = None, trade_last: bool = True, new_doc_first: bool = True,
           answers: dict[str, Hit] | None = None, tokens: float | None = None,
           unattached: list[str] | None = None) -> list[Hit]:
    """Quotas over a rank-ordered pool: firms take turns; within a firm, document types take
    turns (best-ranked type first); a document gives at most MAX_PER_DOC chunks; a chunk that
    repeats a kept one (the same definition in every 10-Q) is dropped. A chunk ranked below
    FLOOR x its firm's FLOOR_BASE-th best chunk (its lowest when it has fewer) gets no slot:
    quotas spread relevant evidence, they do not pad the list with a document type that has
    nothing on the question. In entity+theme (#117) a firm's first THEME_FIRST turns go to its
    best chunks on the theme, below the floor too (#190), then rank order again.
    firm_of maps an entity to the firm whose quota it shares (quota_firms: BAC GWIM -> MER).
    Slot order (#198, #199, ADR-016), in theme and rank turns alike: with trade_last, tier 4 trade
    press takes a firm's turn only when no other document type of the firm can give a chunk
    (TIER_LAST; Q2, Q5, Q30 lost filings and transcripts to trade articles), and a full list then
    gives the firm's best trade chunk the place of a repeated document (TRADE_KEEP); with
    new_doc_first, a document type gives a document not yet in the list, the newest among
    near-equal ranks (NEWEST_BAND), before a second chunk of a used one (NEW_DOC_FIRST;
    speaker-turn chunks of one call pushed the firm's other calls out of Q6, Q11, Q13, Q27).
    answers maps a question turn to its answer turn (answer_turns, #203): with PAIR_TURNS "attach"
    the answer is kept right after its question (same firm, MAX_PER_DOC, near-duplicates and k
    still apply), with "replace" in its place.
    tokens (#213, ADR-019): when set, the list is full once its estimated tokens (hit_tokens) reach
    `tokens` instead of k passages; an answer turn is attached only while the list is not full (a
    question turn that fills it is recorded in `unattached`), and TRADE_KEEP swaps only for a trade
    chunk no longer than the pick it replaces, so the list ends at most one chunk past `tokens`."""
    floor = FLOOR if floor is None else floor
    answers = answers or {}
    max_per_doc = MAX_PER_DOC if max_per_doc is None else max_per_doc
    floor_base = FLOOR_BASE if floor_base is None else floor_base
    # tiers[0]: on the theme, tiers[1]: every chunk; each firm -> document type -> rank-ordered hits
    tiers: tuple[dict, dict] = ({}, {})
    firm_of = firm_of or {}
    ranks: dict[str | None, list[float]] = {}
    for h in pool:  # rank-ordered: first seen = best ranked
        ranks.setdefault(firm_of.get(h.entity_id, h.entity_id), []).append(h.rank)
    best = {f: r[min(floor_base, len(r)) - 1] for f, r in ranks.items()}  # the floor base
    for h in pool:
        firm = firm_of.get(h.entity_id, h.entity_id)
        above = h.rank >= floor * best[firm]
        # The theme slot ignores the floor (#190): a firm's best chunk on the theme is its
        # evidence on the theme even when an off-theme chunk ranks far higher.
        if h.on_theme:
            tiers[0].setdefault(firm, OrderedDict()).setdefault(h.doc_type, []).append(h)
        if above:
            tiers[1].setdefault(firm, OrderedDict()).setdefault(h.doc_type, []).append(h)
    firms = [f for f in best if f in tiers[0] or f in tiers[1]]
    turn = {(n, f): 0 for n in (0, 1) for f in firms}
    kept: list[Hit] = []
    kept_ids: set[str] = set()
    kept_shingles: list[set] = []
    per_doc: dict[str, int] = {}
    on_theme_kept = dict.fromkeys(firms, 0)
    last_kept = dict.fromkeys(firms, 0)
    tier_last = TIER_LAST if trade_last else None
    kept_firm: list = []  # firm of each kept chunk, same order as kept
    new_doc_first = NEW_DOC_FIRST and new_doc_first
    size = [0.0]          # estimated tokens of kept (#213)

    def full() -> bool:
        return len(kept) >= k if tokens is None else size[0] >= tokens

    def eligible(h: Hit) -> set | None:
        """The chunk's shingles when it may still take a slot, else None (never again: being
        kept, a full document and a kept near-duplicate only grow)."""
        if h.chunk_id in kept_ids or per_doc.get(h.doc_id, 0) >= max_per_doc:
            return None
        sh = _shingles(h.text)
        return None if any(_similar(sh, other) > DUP_JACCARD for other in kept_shingles) else sh

    def keep(h: Hit, sh: set, firm) -> None:
        a = answers.get(h.chunk_id) if PAIR_TURNS else None
        if a is not None and PAIR_TURNS == "replace" and (a_sh := eligible(a)) is not None:
            h, sh = a, a_sh
            a = None
        add(h, sh, firm)
        if a is not None and PAIR_TURNS == "attach":
            if full():
                if unattached is not None:
                    unattached.append(h.chunk_id)
            elif (a_sh := eligible(a)) is not None:
                add(a, a_sh, firm)

    def add(h: Hit, sh: set, firm) -> None:
        size[0] += hit_tokens(h)
        kept_firm.append(firm)
        kept.append(h)
        kept_ids.add(h.chunk_id)
        on_theme_kept[firm] += h.on_theme
        last_kept[firm] += h.source_tier in LAST_TIERS
        kept_shingles.append(sh)
        per_doc[h.doc_id] = per_doc.get(h.doc_id, 0) + 1

    def pick(hits: list[Hit]) -> tuple[Hit, set] | None:
        """Next chunk of one document type, removed from its list."""
        if new_doc_first:
            fresh: list[tuple[int, Hit, set]] = []
            for j, h in enumerate(hits):
                if h.doc_id in per_doc:
                    continue
                if fresh and (NEWEST_BAND is None or h.rank < NEWEST_BAND * fresh[0][1].rank):
                    break
                if (sh := eligible(h)) is not None:
                    fresh.append((j, h, sh))
            if fresh:
                j, h, sh = max(fresh, key=lambda c: (c[1].published_at, c[1].rank)) if NEWEST_BAND else fresh[0]
                hits.pop(j)
                return h, sh
        while hits:
            h = hits.pop(0)
            if (sh := eligible(h)) is not None:
                return h, sh
        return None

    def take_types(n: int, firm, types: dict, names: list[str]) -> bool:
        for i in range(len(names)):
            t = names[(turn[n, firm] + i) % len(names)]
            if (got := pick(types[t])) is not None:
                keep(*got, firm)
                turn[n, firm] = (turn[n, firm] + i + 1) % len(names)
                return True
        return False

    def take_from(n: int, firm) -> bool:
        types = tiers[n].get(firm, {})
        names = [t for t in types if types[t]]
        if tier_last is not None:
            last = [t for t in names if types[t][0].source_tier in LAST_TIERS]
            rest = [t for t in names if t not in last]
            if last_kept[firm] >= tier_last:
                return take_types(n, firm, types, rest) or take_types(n, firm, types, last)
        return take_types(n, firm, types, names)

    def keep_one_trade() -> None:
        """TRADE_KEEP: a firm whose trade press all waited for the other types and found the list
        full gets its best trade chunk in place of one pick (Q7, Q29 keep a *:trade source)."""
        for firm in firms:
            if last_kept[firm] or not (types := tiers[1].get(firm)):
                continue
            mine = [i for i, f in enumerate(kept_firm) if f == firm and kept[i].source_tier not in LAST_TIERS]
            if not mine:
                continue
            # The pick to give up: the last second chunk of a document, else the last chunk of a
            # type with several; none -> no swap: a firm's only chunk of a type stays (Q30's
            # release, Q18's brochure).
            n_type = {}
            for j in mine:
                n_type[kept[j].doc_type] = n_type.get(kept[j].doc_type, 0) + 1
            # An answer turn kept with its question is half of a pair, not a repeat (#203).
            paired = {a.chunk_id for qid, a in answers.items() if qid in kept_ids}
            mine = [j for j in mine if kept[j].chunk_id not in paired]
            i = next((j for j in reversed(mine) if per_doc[kept[j].doc_id] > 1), None)
            if i is None:
                i = next((j for j in reversed(mine) if n_type[kept[j].doc_type] > 1), None)
            if i is None:
                continue
            out = kept.pop(i)
            kept_firm.pop(i)
            kept_ids.discard(out.chunk_id)
            kept_shingles.pop(i)
            size[0] -= hit_tokens(out)
            per_doc[out.doc_id] -= 1
            if not per_doc[out.doc_id]:
                del per_doc[out.doc_id]  # "in per_doc" means the document is in the list
            got = next((g for t in types if types[t] and types[t][0].source_tier in LAST_TIERS
                        if (g := pick(types[t])) is not None), None)
            # Token budget (#213): the swap never makes the list longer.
            if got is None or (tokens is not None and hit_tokens(got[0]) > hit_tokens(out)):
                # nothing usable: put the pick back where it was
                size[0] += hit_tokens(out)
                kept.insert(i, out)
                kept_firm.insert(i, firm)
                kept_ids.add(out.chunk_id)
                kept_shingles.insert(i, _shingles(out.text))
                per_doc[out.doc_id] = per_doc.get(out.doc_id, 0) + 1
                continue
            keep(*got, firm)

    def take(firm) -> bool:
        return (on_theme_kept[firm] < THEME_FIRST and take_from(0, firm)) or take_from(1, firm)

    while not full():
        progressed = False
        for firm in firms:
            if full():
                break
            progressed |= take(firm)
        if not progressed:
            break
    if tier_last is not None and TRADE_KEEP and full():
        keep_one_trade()
    return kept


@dataclass
class PoolTrace:
    """Chunk ids of every candidate pool search() fetches before select() (#210), so the eval can
    tell a passage that was never a candidate (recall) from one lost in select() (selection).
    Recording only: search() returns the same hits with or without a trace."""
    firm: list[str] = field(default_factory=list)       # main pass (named firms, or all in theme mode)
    research: list[str] = field(default_factory=list)   # tier 5 research on the theme (entity+theme)
    on_theme: list[str] = field(default_factory=list)   # the firms' own chunks on the theme (#117)
    peers: list[str] = field(default_factory=list)      # theme peers (#205), before peer_floor()
    answers: list[str] = field(default_factory=list)    # answer turns of pooled question turns (#203)
    # Not a pool (#213): kept question turns whose answer turn was left out because the token
    # budget was full; not part of ids().
    unattached: list[str] = field(default_factory=list)

    def ids(self) -> set[str]:
        return {*self.firm, *self.research, *self.on_theme, *self.peers, *self.answers}


def searchable(q: Query) -> bool:
    """False when code knows nothing is eligible without searching: every named firm is one we
    hold no documents for, or the Ask page firm filter leaves none of the named firms."""
    if q.unmapped and not q.entities:
        return False  # firm is known but not in the corpus: nothing is eligible
    if q.firm_filter and not q.entities:
        return False  # the firm filter leaves none of the firms the question names
    return True


@dataclass
class _Ctx:
    """The SQL pieces every pass of one question shares: hard filters, words, ranking."""
    where: str
    filters: str
    window: str
    fragments: dict
    match: str
    params: dict
    rank: str


def _context(conn, q: Query) -> _Ctx:
    where, params = entity_filter(q.entities)
    filters, filter_params = filters_sql(q)
    params.update(filter_params)
    scope, scope_params = doc_type_scope_sql(q)  # #179: adv only for fee questions, no tier 4 for benchmarks
    if scope != "TRUE":
        filters = f"{filters} AND {scope}"
        params.update(scope_params)
    window, window_params = window_filter(q.window)
    terms, synonyms = keyword_terms(q)
    fragments, syn_params = _tsquery_sql(terms, synonyms)
    # A window question ("what's new ... in the last 90 days") asks about everything inside the
    # window, so there the words only rank; outside a window they must match.
    match = "TRUE" if q.window else "c.tsv @@ q.tsq"
    params.update(syn_params)
    params.update(window_params, terms=terms, per_group=POOL_PER_GROUP)
    rank, rank_params = rank_sql(conn, terms, syn_params)
    params.update(rank_params)
    return _Ctx(where, filters, window, fragments, match, params, rank)


def _rows(conn, ctx: _Ctx, entity_where: str, extra: dict | None = None) -> list:
    sql = SQL.format(**ctx.fragments, rank=ctx.rank, match=ctx.match, entity_filter=entity_where,
                     window_filter=ctx.window, filters=ctx.filters)
    return conn.execute(sql, ctx.params | (extra or {})).fetchall()


def _research_rows(conn, ctx: _Ctx, q: Query) -> list:
    """Tier 5 research on the theme (entity+theme only; no firm, tagged with a named topic)."""
    if q.mode != "entity+theme":
        return []
    themes, theme_params = theme_filter(q.themes)
    return _rows(conn, ctx, themes, theme_params)


def _peer_rows(conn, ctx: _Ctx, q: Query) -> list:
    """Home-firm theme rule (#205): the other firms' chunks, on the theme only."""
    if q.mode != "entity+theme" or not q.theme_peers:
        return []
    on_theme, on_theme_params = on_theme_filter(q.themes)
    peers, peer_params = entity_filter(q.theme_peers, prefix="peer_")
    return _rows(conn, ctx, f"{peers} AND {on_theme}", on_theme_params | peer_params)


def _window_opts(q: Query) -> dict:
    # Inside a window every document is on topic, so no floor; one filing may be all there is.
    # Trade press is not put last there (#198): Q26 reads its 90 days of news as they rank; a new
    # document still comes before a second chunk of a used one (#199, Q27: Merrill since January).
    return {"floor": 0, "max_per_doc": WINDOW_MAX_PER_DOC, "trade_last": False} if q.window else {}


def _select_research(rows: list, k: int, q: Query) -> list[Hit]:
    return select([Hit(**r) for r in rows], min(THEME_K, k),  # research: as before #166
                  **{**_window_opts(q), "max_per_doc": THEME_MAX_PER_DOC, "trade_last": False,
                     "new_doc_first": False},
                  floor_base=1)


def _select_peers(rows: list, q: Query, kept: set[str]) -> list[Hit]:
    """The peers' best chunks on the theme, after the floor across them (kept in a window too);
    at most PEER_THEME_PER_FIRM each, never a chunk already in the list."""
    if not rows:
        return []
    peer_pool = peer_floor([Hit(**r, on_theme=True) for r in rows])
    firm_of = quota_firms(q.theme_peers)
    peer_hits = select([h for h in peer_pool if h.chunk_id not in kept],
                       PEER_THEME_PER_FIRM * len({firm_of.get(h.entity_id, h.entity_id) for h in peer_pool}),
                       floor=0, firm_of=firm_of, trade_last=not q.window)
    out, per_firm = [], {}
    for h in peer_hits:
        f = firm_of.get(h.entity_id, h.entity_id)
        if per_firm.get(f, 0) < PEER_THEME_PER_FIRM:
            per_firm[f] = per_firm.get(f, 0) + 1
            out.append(h)
    return out


def research_pass(q: Query, k: int | None = None, trace: PoolTrace | None = None) -> list[Hit]:
    """The research part of search() on its own (#214, ADR-020): run once per question before the
    plan's parts, from the whole question's query (same filters, scope, window and ranking as
    search()), so a question keeps at most THEME_K research passages whatever its parts."""
    if q.mode != "entity+theme" or not searchable(q):
        return []
    k = budget(q) - peer_slots(q) if k is None else k
    with connect() as conn:
        ctx = _context(conn, q)
        rows = _research_rows(conn, ctx, q)
    if trace is not None:
        trace.research += [r["chunk_id"] for r in rows]
    return _select_research(rows, k, q)


def peer_pass(q: Query, kept: set[str], trace: PoolTrace | None = None) -> list[Hit]:
    """The theme peers of search() on their own (#214, ADR-020): run once per question after the
    plan's parts, never a chunk in `kept`, on top of the token budget as before."""
    if q.mode != "entity+theme" or not q.theme_peers or not searchable(q):
        return []
    with connect() as conn:
        ctx = _context(conn, q)
        rows = _peer_rows(conn, ctx, q)
    if trace is not None:
        trace.peers += [r["chunk_id"] for r in rows]
    return _select_peers(rows, q, kept)


def search(q: Query, k: int | None = None, trace: PoolTrace | None = None, tokens: float | None = None,
           exclude: set[str] | None = None, research: bool = True, peers: bool = True,
           text: str | None = None) -> list[Hit]:
    """k: passages to return; None = the app default: budget(q) passages in passage mode
    (TOKEN_BUDGET None), budget_tokens(q) estimated tokens in token mode. The theme peers' slots (#205)
    are part of budget(q) and come on top of an explicit k, so the named firms and the research
    part get the same k with or without peers. trace (#210): filled with the candidate pools'
    chunk ids; it changes nothing else.
    Token budget (#213, ADR-019): with k None and TOKEN_BUDGET set, the firm and research parts
    share budget_tokens(q) (research first, its tokens off the firm part); the peers' passages
    stay on top. An explicit k is always the passage rule.
    Plan parts (#214, ADR-020): `tokens` is an explicit token budget (a part's share); `exclude`
    holds chunk ids already kept (earlier parts, the research pass): they leave the pools and the
    answer-turn map, so they are never kept twice; research=False / peers=False leave out the
    research part and the theme peers (run once per question by research_pass / peer_pass).
    Sub-questions (#245): `text` (the sub-question's text) is accepted and ignored: FTS ranks on
    words; the hybrid search on exp/hybrid embeds it, so both fit planner.search_subquestions'
    `search_fn`. `q.on_theme_only` (a competitor sub-question, entity+theme): the firm pass keeps
    only chunks with the theme's keywords and no answer turn is attached (an answer turn is fetched
    without the word match and may be off the theme)."""
    if tokens is None and k is None:
        tokens = budget_tokens(q)
    k = budget(q) - peer_slots(q) if k is None else k
    if not searchable(q):
        return []
    exclude = exclude or set()
    with connect() as conn:
        ctx = _context(conn, q)
        theme_only = q.on_theme_only and q.mode == "entity+theme" and bool(q.themes)
        if theme_only:   # #245: competitor sub-question, on the theme only (ADR-018 safeguard)
            on_theme, on_theme_params = on_theme_filter(q.themes)
            rows = _rows(conn, ctx, f"{ctx.where} AND {on_theme}", on_theme_params)
        else:
            rows = _rows(conn, ctx, ctx.where)
        research_rows = _research_rows(conn, ctx, q) if research else []
        on_theme_rows = []
        if theme_only:
            on_theme_rows = rows
        elif q.mode == "entity+theme":
            # The firms' own chunks on the theme, pooled on their own so a firm's best on-theme
            # chunks are there even when off-theme chunks fill its usual pool (#117).
            on_theme, on_theme_params = on_theme_filter(q.themes)
            on_theme_rows = _rows(conn, ctx, f"{ctx.where} AND {on_theme}", on_theme_params)
        peer_rows = _peer_rows(conn, ctx, q) if peers else []
        on_ids = {r["chunk_id"] for r in on_theme_rows}
        merged = {r["chunk_id"]: r for r in [*rows, *on_theme_rows]}
        pool = sorted((Hit(**r, on_theme=r["chunk_id"] in on_ids) for r in merged.values()
                       if r["chunk_id"] not in exclude),
                      key=lambda h: (-h.rank, h.chunk_id))
        answers = answer_turns(conn, [h for h in pool if is_question_turn(h)], ctx.where, ctx.window,
                               ctx.filters, ctx.params) if PAIR_TURNS and not theme_only else {}
        answers = {qid: a for qid, a in answers.items() if a.chunk_id not in exclude}
    if trace is not None:
        trace.firm += [r["chunk_id"] for r in rows]
        trace.research += [r["chunk_id"] for r in research_rows]
        trace.on_theme += [r["chunk_id"] for r in on_theme_rows]
        trace.peers += [r["chunk_id"] for r in peer_rows]
        trace.answers += [a.chunk_id for a in answers.values()]
    opts = _window_opts(q)
    research_hits = _select_research(research_rows, k, q) if research_rows else []
    firm_tokens = None if tokens is None else max(0.0, tokens - sum(hit_tokens(h) for h in research_hits))
    hits = select(pool, k - len(research_hits), **opts, firm_of=quota_firms(q.entities), answers=answers,
                  tokens=firm_tokens, unattached=trace.unattached if trace is not None else None) + research_hits
    if peer_rows:
        hits += _select_peers(peer_rows, q, {h.chunk_id for h in hits})
    if q.window:  # recency questions read newest first (Q26)
        hits.sort(key=lambda h: h.published_at, reverse=True)
    return hits


PIN_SQL = """
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, 0.0::float AS rank, c.text, d.date_basis
FROM chunks c JOIN documents d USING (doc_id)
WHERE c.chunk_id = ANY(%(pin_ids)s)
  AND {entity_filter}
  AND {window_filter}
  AND {filters}
"""


def fetch_pinned(q: Query, ids: list[str]) -> list[Hit]:
    """Registered chunks by ID (#247 part 2): definition and population sources from
    config/metric_definitions.yaml. Every hard filter of the sub-question applies (entity / segment,
    window, date range, keywords) and the doc-type scope except the `adv` exclusion (pinned_scope);
    returned in the order of `ids`."""
    if not ids or not searchable(q):
        return []
    where, params = entity_filter(q.entities)
    filters, filter_params = filters_sql(replace(q, exclude_ids=[], period_range=None))
    params.update(filter_params)
    types, tiers = pinned_scope(q)
    scope, scope_params = doc_type_scope_sql(replace(q, scope=(types, tiers)))
    if scope != "TRUE":
        filters = f"{filters} AND {scope}"
        params.update(scope_params)
    window, window_params = window_filter(q.window)
    params.update(window_params, pin_ids=list(ids))
    with connect() as conn:
        rows = conn.execute(PIN_SQL.format(entity_filter=where, window_filter=window, filters=filters),
                            params).fetchall()
    by_id = {r["chunk_id"]: r for r in rows}
    return [Hit(**by_id[i], origin="pinned") for i in ids if i in by_id]


def theme_gaps(q: Query, hits: list[Hit]) -> list[str]:
    """Named firms with no retrieved chunk on the theme (entity+theme, #117). Code reports them as
    gaps; the model is never left to notice. Merrill counts through BAC GWIM chunks (the entity
    filter only lets those through)."""
    if q.mode != "entity+theme":
        return []
    covered = {h.entity_id for h in hits if h.on_theme}
    by_id = {e["id"]: e for e in entities_config()["entities"]}
    return [e for e in q.entities if e not in covered and by_id.get(e, {}).get("parent") not in covered]
