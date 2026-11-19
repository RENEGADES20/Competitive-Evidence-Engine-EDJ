"""Hybrid retrieval (#125, experimental branch exp/hybrid): keyword + vector candidates, RRF, local
rerank, then the same quotas as fts mode. Owner: TL (Yueyang Du); fts.py stays S1's and equals `main`.

Part of the optional vectors module (ADR-009): it needs CEE_VECTORS=on, the table
chunk_embeddings (db/optional/vectors.sql) and both models in the cache. Nothing here downloads a
model at query time; `--fetch` is the only path that does. The mode switch is cee.retrieve.modes.

Every hard filter of fts mode, in every SQL pass (#211): firm and segment (fts.entity_filter), time
window (fts.window_filter), Ask filters (fts.filters_sql) and the document-type scope
(fts.doc_type_scope_sql: Form ADV only for fee questions and never in a window, no trade press for
benchmark questions; ADR-015). Each part of a question runs both legs:
  1. keyword leg: the fts words, synonyms and rank, top LEG_K per quota firm;
  2. vector leg: cosine distance to the embedded text (the question, or a plan part's text), top
     LEG_K per quota firm (exact);
  3. RRF per quota firm: score = sum over legs of 1 / (RRF_K + rank in that firm). The quota firm
     (fts.quota_firms, ADR-013) puts Merrill's MER and BAC GWIM chunks in one ranked list;
  4. the pool (#240, ADR-019's rule): the best fts.POOL_PER_GROUP (30) fused chunks per
     (entity_id, document type), as fts's pool SQL partitions.
Parts, as in fts.search(): the named firms; entity+theme also the firms' own chunks on the theme
(fts.on_theme_filter, #117), tier 5 research on the theme, and the home firm's theme peers on the
theme (#205, ADR-018). Question turns get their answer turn (fts.answer_turns, PAIR_TURNS, ADR-017).
Budget and plan (#240): the token budget (fts.budget_tokens, ADR-019) as fts.search, and
search_parts() searches a question plan (planner parts, ADR-020) exactly as planner.search_parts.

`hybrid-norerank` (rerank=False): Hit.rank = RRF score, and fts.select() does the rest exactly as in
fts mode: relative floor FLOOR[mode] from the firm's FLOOR_BASE-th best (ADR-014; research base 1;
none in a window), theme slot below the floor (#190), Merrill counted once, slot order (trade press
last, new document first; ADR-016), answer turns, near-duplicates (fts.DUP_JACCARD). The peers pass
fts.peer_floor() at FLOOR[mode]. `hybrid` (reference): the same floor is applied to the RRF score
before the cross-encoder (a gate, so fewer passages are scored); the theme part is exempt; then
Hit.rank = sigmoid(cross-encoder score) and select() runs with floor 0 (a sigmoid is not a ratio).

Scores where parts merge (#211): a chunk in the firm part and the on-theme part keeps its firm-part
RRF score; an on-theme-only chunk gets ON_THEME_SCALE x m x s / s_max (s its on-theme RRF score, s_max
the best on-theme-only score of its quota firm, m the firm's lowest firm-part score), so it ranks
strictly below every firm-part chunk of its firm and never moves the floor base.

  python -m cee.retrieve.hybrid --fetch      download the reranker into the cache (once)
  python -m cee.retrieve.hybrid --check      load both models from the cache, score one pair
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

from cee.retrieve import fts
from cee.retrieve.fts import K, Hit, PoolTrace, Query  # noqa: F401 (re-exported)
from cee.retrieve.modes import HybridUnavailable  # noqa: F401 (re-exported)

LEG_K = 100          # candidates per leg and quota firm
RRF_K = 60           # reciprocal rank fusion constant
RERANK_FLOOR = 0.0   # sigmoid score below which a hit is a weak match (outside time windows)
# 0 = no rerank floor: every grid value lost evidence on corpus-2026-10-29 (#125 plan Progress log).
# Per mode (#126; values chosen by the selection rule in plans/0126-hybrid-eval.md, report in
# evals/hybrid-eval/corpus-2026-10-29/report.md). Not retuned in #211.
FLOOR = {"hybrid": 0.4, "hybrid-norerank": 0.4}        # relative RRF floor
MAX_PER_DOC = {"hybrid": 4, "hybrid-norerank": 3}      # firm part; window / research caps unchanged
ON_THEME_SCALE = 0.99  # < 1: an on-theme-only chunk ranks strictly below its firm's firm-part chunks
DEFAULT_RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"
# Rerankers this module knows: name -> size. Cache folder: models--<org>--<name>/snapshots/*/onnx/model.onnx
RERANKERS = {"Xenova/ms-marco-MiniLM-L-12-v2": "about 120 MB", "BAAI/bge-reranker-base": "about 1 GB"}

Scorer = Callable[[str, Sequence[str]], list[float]]


class MissingVectors(RuntimeError):
    pass


class RerankerNotCached(RuntimeError):
    """The reranker is not in the cache; nothing is downloaded by itself."""


# --- reranker (cache only) ------------------------------------------------------------------

def rerank_model_name() -> str:
    name = os.getenv("RERANK_MODEL", "").strip() or DEFAULT_RERANK_MODEL
    if name not in RERANKERS:
        raise ValueError(f"RERANK_MODEL={name!r} is not known; use one of {', '.join(RERANKERS)}")
    return name


def model_folder(name: str) -> str:
    return "models--" + name.replace("/", "--")


def reranker_cached(name: str, path: Path | None = None) -> bool:
    """True when the model file is in the cache (checked without fastembed, which would create
    folders)."""
    from cee.retrieve.embed import cache_dir
    folder = (path or cache_dir()) / model_folder(name) / "snapshots"
    return folder.is_dir() and any(folder.glob("*/onnx/model.onnx"))


@lru_cache(maxsize=2)
def reranker(name: str):
    """The cached cross-encoder, loaded with local_files_only=True. Missing -> RerankerNotCached."""
    from cee.retrieve.embed import cache_dir
    path = cache_dir()
    if not reranker_cached(name, path):
        raise RerankerNotCached(
            f"Reranker {name} is not in {path} (FASTEMBED_CACHE_PATH). It is never downloaded by "
            "itself. Get it once with `python -m cee.retrieve.hybrid --fetch`, or copy the models/ "
            "folder from the shared corpus folder into that folder (docs/RUN.md).")
    from fastembed.rerank.cross_encoder import TextCrossEncoder  # imported late: core never needs it
    return TextCrossEncoder(model_name=name, cache_dir=str(path), local_files_only=True)


def fetch_reranker(name: str) -> Path:
    """Download the reranker into the cache (the only path that uses the network)."""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    from cee.retrieve.embed import cache_dir
    path = cache_dir()
    path.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {name} ({RERANKERS[name]}) into {path}...", file=sys.stderr, flush=True)
    TextCrossEncoder(model_name=name, cache_dir=str(path))
    return path


def cross_encoder_scores(question: str, passages: Sequence[str]) -> list[float]:
    """Raw cross-encoder scores (logits), one per passage, in order."""
    if not passages:
        return []
    return [float(x) for x in reranker(rerank_model_name()).rerank(question, list(passages), batch_size=16)]


# --- fusion, pool, floor ---------------------------------------------------------------------

def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x)) if x >= 0 else math.exp(x) / (1 + math.exp(x))


def rrf(legs: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal rank fusion. Each leg is a ranked list of chunk_ids (best first, rank 1).
    Returns (chunk_id, score) best first; ties broken by chunk_id."""
    scores: dict[str, float] = {}
    for leg in legs:
        for rank, cid in enumerate(leg, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


def gate(ids: Sequence[str], rrf_score: dict[str, float], group_of: dict[str, object], floor: float,
         floor_base: int = 1, exempt: set[str] | frozenset = frozenset()) -> list[str]:
    """Candidates whose RRF score is at least floor x the floor_base-th best RRF score of their quota
    firm (its lowest when it has fewer), order kept; `exempt` ids (the theme part) always stay and
    do not count for the base. floor 0 keeps everything. group_of: chunk_id -> (quota firm, type).
    Used by `hybrid` before the cross-encoder; `hybrid-norerank` leaves the floor to fts.select()."""
    if floor <= 0:
        return list(ids)
    firm = {c: (group_of.get(c) or (None,))[0] for c in ids}
    scores: dict[object, list[float]] = {}
    for c in ids:
        if c not in exempt:
            scores.setdefault(firm[c], []).append(rrf_score[c])
    base = {f: sorted(v, reverse=True)[min(floor_base, len(v)) - 1] for f, v in scores.items()}
    return [c for c in ids if c in exempt or rrf_score[c] >= floor * base.get(firm[c], 0.0)]


def apply_floor(pool: list[Hit], floor: float) -> list[Hit]:
    """Pool sorted by score (best first, ties by chunk_id), hits below an absolute floor dropped."""
    ranked = sorted(pool, key=lambda h: (-h.rank, h.chunk_id))
    return [h for h in ranked if h.rank >= floor]


def merge_theme(firm_ids: list[str], firm_rrf: dict[str, float], theme_ids: list[str],
                theme_rrf: dict[str, float], group_of: dict[str, object]) -> tuple[list[str], dict[str, float]]:
    """The firm part plus the on-theme part (#117) on one score scale per quota firm (#211):
    a chunk in both keeps its firm-part score; an on-theme-only chunk gets
    ON_THEME_SCALE x m x s / s_max (s: its on-theme RRF score; s_max: the best on-theme-only score of
    its quota firm; m: the firm's lowest firm-part score, 1 / (RRF_K + LEG_K) when it has none).
    So it ranks strictly below every firm-part chunk of its firm, keeps its on-theme order and
    never moves the firm's floor base. Returns (ids, score)."""
    firm_set = set(firm_ids)
    score = {c: firm_rrf[c] for c in firm_ids}
    only = [c for c in theme_ids if c not in firm_set]
    lowest: dict[object, float] = {}
    for c in firm_ids:
        f = (group_of.get(c) or (None,))[0]
        lowest[f] = min(lowest.get(f, math.inf), firm_rrf[c])
    best: dict[object, float] = {}
    for c in only:
        f = (group_of.get(c) or (None,))[0]
        best[f] = max(best.get(f, 0.0), theme_rrf[c])
    for c in only:
        f = (group_of.get(c) or (None,))[0]
        m = lowest.get(f, 1.0 / (RRF_K + LEG_K))
        score[c] = ON_THEME_SCALE * m * theme_rrf[c] / best[f]
    return firm_ids + only, score


# --- SQL ---------------------------------------------------------------------------------------

KEYWORD_SQL = """
WITH q AS (
  SELECT {tsquery} AS tsq
), scored AS (
  SELECT c.chunk_id, d.entity_id, d.doc_type, {quota_key} AS qfirm, {rank} AS rank
  FROM chunks c JOIN documents d USING (doc_id), q
  WHERE {match}
    AND {entity_filter}
    AND {window_filter}
    AND {filters}
), ranked AS (
  SELECT chunk_id, entity_id, doc_type, qfirm,
         row_number() OVER (PARTITION BY qfirm ORDER BY rank DESC, chunk_id) AS rn
  FROM scored
)
SELECT chunk_id, entity_id, doc_type, qfirm, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

VECTOR_SQL = """
WITH ranked AS (
  SELECT c.chunk_id, d.entity_id, d.doc_type, {quota_key} AS qfirm,
         row_number() OVER (PARTITION BY {quota_key} ORDER BY e.embedding <=> %(qvec)s::vector, c.chunk_id) AS rn
  FROM chunks c JOIN documents d USING (doc_id) JOIN chunk_embeddings e USING (chunk_id)
  WHERE {entity_filter}
    AND {window_filter}
    AND {filters}
)
SELECT chunk_id, entity_id, doc_type, qfirm, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

ROWS_SQL = """
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, c.text, d.date_basis, c.prefix
FROM chunks c JOIN documents d USING (doc_id)
WHERE c.chunk_id = ANY(%(ids)s)
"""

PARTS = ("firm", "on_theme", "research", "peers")


def quota_key_sql(firm_of: dict[str, str]) -> tuple[str, dict]:
    """SQL for a chunk's quota firm (fts.quota_firms, ADR-013): BAC -> MER when the question names
    Merrill and not BAC, so the legs rank MER and BAC GWIM chunks in one list."""
    if not firm_of:
        return "d.entity_id", {}
    whens, params = [], {}
    for i, (entity, firm) in enumerate(sorted(firm_of.items())):
        whens.append(f"WHEN d.entity_id = %(qf_entity{i})s THEN %(qf_firm{i})s")
        params |= {f"qf_entity{i}": entity, f"qf_firm{i}": firm}
    return f"(CASE {' '.join(whens)} ELSE d.entity_id END)", params


def hard_filters(q: Query) -> tuple[str, str, dict]:
    """(window, filters, params): the time window, the Ask filters and the document-type scope
    (ADR-015), exactly as fts.search builds them."""
    window, params = fts.window_filter(q.window)
    filters, filter_params = fts.filters_sql(q)
    scope, scope_params = fts.doc_type_scope_sql(q)
    if scope != "TRUE":
        filters = f"{filters} AND {scope}"
    return window, filters, {**params, **filter_params, **scope_params}


def part_where(q: Query, part: str = "firm") -> tuple[str, dict, dict[str, str]]:
    """(where, params, firm_of) of one part: the named firms; their chunks on the theme; tier 5
    research on the theme (no firm); the home firm's theme peers on the theme (#205)."""
    if part == "research":
        where, params = fts.theme_filter(q.themes)
        return where, params, {}
    if part == "peers":
        where, params = fts.entity_filter(q.theme_peers, prefix="peer_")
        firm_of = fts.quota_firms(q.theme_peers)
    else:
        where, params = fts.entity_filter(q.entities)
        firm_of = fts.quota_firms(q.entities)
    if part in ("on_theme", "peers"):
        on_theme, on_params = fts.on_theme_filter(q.themes)
        where, params = f"{where} AND {on_theme}", {**params, **on_params}
    return where, params, firm_of


def part_filters(q: Query, part: str = "firm") -> tuple[str, str, str, str, dict]:
    """(where, window, filters, quota key, params) of one part: every hard filter of fts mode."""
    where, params, firm_of = part_where(q, part)
    window, filters, filter_params = hard_filters(q)
    key, key_params = quota_key_sql(firm_of)
    return where, window, filters, key, {**params, **filter_params, **key_params}


def keyword_leg_sql(conn, q: Query, research: bool = False, part: str | None = None,
                    rank: tuple[str, dict] | None = None) -> tuple[str, dict]:
    part = part or ("research" if research else "firm")
    where, window, filters, key, params = part_filters(q, part)
    terms, synonyms = fts.keyword_terms(q)
    fragments, syn_params = fts._tsquery_sql(terms, synonyms)
    if rank is None:
        rank = fts.rank_sql(conn, terms, syn_params) if conn is not None else ("0", {})
    rank_expr, rank_params = rank
    match = "TRUE" if q.window else "c.tsv @@ q.tsq"  # as in fts mode
    sql = KEYWORD_SQL.format(**fragments, rank=rank_expr, match=match, entity_filter=where,
                             window_filter=window, filters=filters, quota_key=key)
    return sql, {**params, **syn_params, **rank_params, "terms": terms, "leg_k": LEG_K}


def vector_leg_sql(q: Query, qvec: str, research: bool = False, part: str | None = None) -> tuple[str, dict]:
    part = part or ("research" if research else "firm")
    where, window, filters, key, params = part_filters(q, part)
    return (VECTOR_SQL.format(entity_filter=where, window_filter=window, filters=filters, quota_key=key),
            {**params, "qvec": qvec, "leg_k": LEG_K})


def check_vectors(conn) -> None:
    """Hybrid needs a vector for every chunk; never a silent fallback to fts."""
    if conn.execute("SELECT to_regclass('chunk_embeddings') IS NOT NULL AS ok").fetchone()["ok"] is not True:
        raise MissingVectors(
            "Hybrid retrieval needs the table chunk_embeddings (optional vectors module, ADR-009). "
            "With CEE_VECTORS=on, run `python -m cee.retrieve.embed --missing` (applies "
            "db/optional/vectors.sql and fills the vectors), or set RETRIEVAL_MODE=fts.")
    n = conn.execute("SELECT count(*) AS n FROM chunks c WHERE NOT EXISTS "
                     "(SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id)").fetchone()["n"]
    if n:
        raise MissingVectors(
            f"Hybrid retrieval needs a vector for every chunk; {n} chunks have none. With CEE_VECTORS=on, "
            "run `python -m cee.retrieve.embed --missing`, or set RETRIEVAL_MODE=fts.")


# --- search --------------------------------------------------------------------------------------

Part = tuple[list[str], dict[str, float], dict[str, object]]
EMPTY: Part = ([], {}, {})


def pool_cut(fused: Sequence[tuple[str, float]], entity_of: dict[str, object], doc_type_of: dict[str, object],
             per_group: int | None = None) -> list[str]:
    """The pool of one part (#240, ADR-019's rule): the best `per_group` (fts.POOL_PER_GROUP) chunks
    of the fused list per (entity_id, doc_type), in fused order, as fts's pool SQL partitions
    (`PARTITION BY entity_id, doc_type`): MER and BAC GWIM chunks each keep their own groups here,
    while the RRF lists and select() count them as one quota firm (ADR-013)."""
    per_group = fts.POOL_PER_GROUP if per_group is None else per_group
    counts: dict[tuple, int] = {}
    out: list[str] = []
    for cid, _ in fused:
        g = (entity_of.get(cid), doc_type_of.get(cid))
        if counts.get(g, 0) < per_group:
            counts[g] = counts.get(g, 0) + 1
            out.append(cid)
    return out


def candidates(conn, q: Query, qvec: str, research: bool = False, part: str | None = None,
               rank: tuple[str, dict] | None = None) -> Part:
    """Both legs of one part, RRF per quota firm, then the pool cut (pool_cut: POOL_PER_GROUP per
    (entity, document type)). Returns (candidates in fused order, RRF score per chunk,
    (quota firm, type) per chunk)."""
    part = part or ("research" if research else "firm")
    sql, params = keyword_leg_sql(conn, q, part=part, rank=rank)
    kw = conn.execute(sql, params).fetchall()
    sql, params = vector_leg_sql(q, qvec, part=part)
    vec = conn.execute(sql, params).fetchall()
    group_of = {r["chunk_id"]: (r["qfirm"], r["doc_type"]) for r in [*kw, *vec]}
    entity_of = {r["chunk_id"]: r["entity_id"] for r in [*kw, *vec]}
    doc_type_of = {r["chunk_id"]: r["doc_type"] for r in [*kw, *vec]}
    fused = rrf([*_per_firm(kw), *_per_firm(vec)])
    return pool_cut(fused, entity_of, doc_type_of), dict(fused), group_of


def _per_firm(rows: list[dict]) -> list[list[str]]:
    """Split a leg into one ranked list per quota firm (rows come in per-firm rank order), so a
    chunk's RRF rank is its rank inside its quota firm: firms are not ranked against each other,
    and Merrill's MER and BAC GWIM chunks share one list (ADR-013)."""
    lists: dict[str | None, list[str]] = {}
    for r in rows:
        lists.setdefault(r["qfirm"], []).append(r["chunk_id"])
    return list(lists.values())


def search(q: Query, k: int | None = None, scorer: Scorer | None = None, timings: dict | None = None,
           rerank: bool = True, trace: PoolTrace | None = None, tokens: float | None = None,
           exclude: set[str] | None = None, research: bool = True, peers: bool = True,
           text: str | None = None, checked: bool = False, firm: bool = True,
           kept: set[str] | None = None) -> list[Hit]:
    """rerank=True: mode `hybrid` (cross-encoder order); False: `hybrid-norerank` (RRF order).
    k, tokens, exclude, research, peers as fts.search (#240): k None and tokens None = the app
    default, the token budget budget_tokens(q) (ADR-019; research first, its tokens off the firm
    part; peers on top), or budget(q) - peer_slots(q) passages in passage mode; an explicit k is the
    passage rule; `tokens` is a part's share; `exclude` (chunk ids kept earlier) leaves the firm and
    on-theme pools after the pool cut, and the answer-turn map. text: what the vector leg embeds and
    the cross-encoder scores against (a plan part's text; None = the question). checked: the
    vectors check already ran for this question (search_parts runs it once). firm=False runs only
    the research and peer parts (research_pass / peer_pass); kept: chunk ids the peers never take.
    trace (#210): the candidate pools before any floor or select(); recording only."""
    mode = "hybrid" if rerank else "hybrid-norerank"
    if tokens is None and k is None:
        tokens = fts.budget_tokens(q)
    k = fts.budget(q) - fts.peer_slots(q) if k is None else k
    if not fts.searchable(q):
        return []  # unmapped firm only, or the firm filter leaves none: no model, no SQL
    from cee.db import connect
    from cee.retrieve.embed import embed_query, vector_literal

    scorer = scorer or cross_encoder_scores
    text = text or q.question
    exclude = exclude or set()
    floor = 0.0 if q.window else FLOOR[mode]  # inside a window every document is on topic
    theme_q = q.mode == "entity+theme"
    firm_of = fts.quota_firms(q.entities)
    t0 = time.perf_counter()
    with connect() as conn:
        if not checked:
            check_vectors(conn)
        qvec = vector_literal(embed_query(text))
        terms, synonyms = fts.keyword_terms(q)
        _, syn_params = fts._tsquery_sql(terms, synonyms)
        rank = fts.rank_sql(conn, terms, syn_params)  # once per search, shared by every part
        firm_ids, firm_rrf, groups = (candidates(conn, q, qvec, part="firm", rank=rank) if firm else EMPTY)
        theme_ids, theme_rrf, theme_groups = (candidates(conn, q, qvec, part="on_theme", rank=rank)
                                              if firm and theme_q else EMPTY)
        research_ids, research_rrf, research_groups = (
            candidates(conn, q, qvec, part="research", rank=rank) if theme_q and research else EMPTY)
        peer_ids, peer_rrf, _ = (candidates(conn, q, qvec, part="peers", rank=rank)
                                 if theme_q and q.theme_peers and peers else EMPTY)
        groups = {**theme_groups, **groups}
        # as fts.search: the pool cut first, then the chunks kept earlier leave the pools (#240)
        pooled_firm = [c for c in firm_ids if c not in exclude]
        pooled_theme = [c for c in theme_ids if c not in exclude]
        ids, score = merge_theme(pooled_firm, firm_rrf, pooled_theme, theme_rrf, groups)
        on_theme = set(pooled_theme)
        every = list(dict.fromkeys([*ids, *research_ids, *peer_ids]))
        rows = {r["chunk_id"]: dict(r) for r in conn.execute(ROWS_SQL, {"ids": every}).fetchall()}

        def hit(c: str, rank_: float, theme: bool = False) -> Hit:
            return Hit(**{key: v for key, v in rows[c].items() if key != "prefix"}, rank=rank_, on_theme=theme)

        pool = [hit(c, score[c], c in on_theme) for c in ids if c in rows]
        answers = {}
        if fts.PAIR_TURNS and firm:  # answer turns of the pooled question turns (#203), every hard filter
            where, window, filters, _, params = part_filters(q, "firm")
            answers = fts.answer_turns(conn, [h for h in pool if fts.is_question_turn(h)], where, window,
                                       filters, params)
            answers = {qid: a for qid, a in answers.items() if a.chunk_id not in exclude}
    if trace is not None:
        trace.firm += firm_ids
        trace.on_theme += theme_ids
        trace.research += research_ids
        trace.peers += peer_ids
        trace.answers += [a.chunk_id for a in answers.values()]
    t1 = time.perf_counter()
    research_pool = [hit(c, research_rrf[c]) for c in research_ids if c in rows]
    peer_pool = [hit(c, peer_rrf[c], True) for c in peer_ids if c in rows]
    if rerank:
        # the RRF floor as a gate before the cross-encoder (fewer passages to score); theme part exempt
        keep = set(gate(ids, score, groups, floor, fts.FLOOR_BASE, exempt=on_theme))
        keep |= set(gate(research_ids, research_rrf, research_groups, floor, 1))
        peer_pool = fts.peer_floor(peer_pool, FLOOR[mode])
        keep |= {h.chunk_id for h in peer_pool}
        found = [c for c in every if c in keep and c in rows]
        scores = dict(zip(found, scorer(text, [f"{rows[c]['prefix']} {rows[c]['text']}" for c in found])))
        rerank_floor = 0.0 if q.window else RERANK_FLOOR

        def rescored(hits: list[Hit]) -> list[Hit]:
            return apply_floor([replace(h, rank=sigmoid(scores[h.chunk_id]))
                                for h in hits if h.chunk_id in scores], rerank_floor)
        pool, research_pool, peer_pool = rescored(pool), rescored(research_pool), rescored(peer_pool)
        select_floor = 0.0
    else:
        pool, research_pool = apply_floor(pool, 0.0), apply_floor(research_pool, 0.0)  # sort by RRF
        peer_pool = fts.peer_floor(apply_floor(peer_pool, 0.0), FLOOR[mode])
        select_floor = floor
    t2 = time.perf_counter()
    if timings is not None:
        timings.update(retrieve_s=t1 - t0, rerank_s=t2 - t1)

    # As fts.search: no floor, the window cap and no trade-last inside a window; research as before
    # #166 (base 1, no slot-order rules); answer turns; Merrill counted once; the token budget (#240).
    opts = ({"floor": 0, "max_per_doc": fts.WINDOW_MAX_PER_DOC, "trade_last": False} if q.window
            else {"floor": select_floor, "max_per_doc": MAX_PER_DOC[mode]})
    research_hits = fts.select(research_pool, min(fts.THEME_K, k),
                               **{**opts, "max_per_doc": fts.THEME_MAX_PER_DOC, "trade_last": False,
                                  "new_doc_first": False}, floor_base=1) if research_pool else []
    hits: list[Hit] = []
    if firm:
        firm_tokens = None if tokens is None else max(0.0, tokens - sum(fts.hit_tokens(h) for h in research_hits))
        hits = fts.select(pool, k - len(research_hits), **opts, firm_of=firm_of, answers=answers,
                          tokens=firm_tokens, unattached=trace.unattached if trace is not None else None)
    hits += research_hits
    if peer_pool:
        # the peers' best chunks on the theme, at most PEER_THEME_PER_FIRM each, never a chunk already kept
        peer_firm_of = fts.quota_firms(q.theme_peers)
        taken = {h.chunk_id for h in hits} | (kept or set())
        peer_hits = fts.select([h for h in peer_pool if h.chunk_id not in taken],
                               fts.PEER_THEME_PER_FIRM * len({peer_firm_of.get(h.entity_id, h.entity_id)
                                                              for h in peer_pool}),
                               floor=0, firm_of=peer_firm_of, trade_last=not q.window)
        per_firm: dict = {}
        for h in peer_hits:
            f = peer_firm_of.get(h.entity_id, h.entity_id)
            if per_firm.get(f, 0) < fts.PEER_THEME_PER_FIRM:
                per_firm[f] = per_firm.get(f, 0) + 1
                hits.append(h)
    if q.window and firm:  # recency questions read newest first (Q26)
        hits.sort(key=lambda h: h.published_at, reverse=True)
    return hits


def research_pass(q: Query, rerank: bool = True, trace: PoolTrace | None = None, scorer: Scorer | None = None,
                  checked: bool = False) -> list[Hit]:
    """The research part of search() on its own (#240, as fts.research_pass): run once per question
    before the plan's parts, from the whole question (its words, its embedding)."""
    if q.mode != "entity+theme" or not fts.searchable(q):
        return []
    return search(q, rerank=rerank, trace=trace, scorer=scorer, peers=False, firm=False, checked=checked)


def peer_pass(q: Query, kept: set[str], rerank: bool = True, trace: PoolTrace | None = None,
              scorer: Scorer | None = None, checked: bool = False) -> list[Hit]:
    """The theme peers of search() on their own (#240, as fts.peer_pass): run once per question after
    the plan's parts, never a chunk in `kept`, on top of the token budget."""
    if q.mode != "entity+theme" or not q.theme_peers or not fts.searchable(q):
        return []
    return search(q, rerank=rerank, trace=trace, scorer=scorer, research=False, firm=False, kept=kept,
                  checked=checked)


def search_parts(q: Query, plan, rerank: bool = True, trace: PoolTrace | None = None,
                 part_pools: dict[str, set[str]] | None = None, scorer: Scorer | None = None) -> list[Hit]:
    """Retrieve a plan in hybrid mode (#240): the same loop as planner.search_parts (ADR-020), which
    stays byte-equal to main (tests pin its source hash): research once, the parts in order with
    equal shares of the token budget left (T - research - used so far, divided by the parts left),
    earlier chunks excluded, the theme peers once. Each part searches planner.part_query(q, part)
    (its firms and words, every hard filter of the question) and embeds the part's text. Passage
    mode (TOKEN_BUDGET None) is one whole-question search. `part_pools` (eval) gets each part's
    candidate ids; `plan.searched` also records each part's `vector_text`."""
    from cee.retrieve import planner

    total = fts.budget_tokens(q)
    if total is None or not fts.searchable(q):
        hits = search(q, rerank=rerank, trace=trace, scorer=scorer)
        for h in hits:
            h.part_id = "p1"
        return hits
    from cee.db import connect
    with connect() as conn:
        check_vectors(conn)  # once per question (#240), not once per part
    research = research_pass(q, rerank, trace=trace, scorer=scorer, checked=True)
    for h in research:
        h.part_id = "research"
    plan.research_tokens = sum(fts.hit_tokens(h) for h in research)
    kept = {h.chunk_id for h in research}
    used = 0.0
    out: list[Hit] = []
    plan.searched = []
    n = len(plan.parts)
    for i, part in enumerate(plan.parts):
        share = max(0.0, total - plan.research_tokens - used) / (n - i)
        part_trace = PoolTrace()
        hits = search(planner.part_query(q, part), trace=part_trace, tokens=share, exclude=kept,
                      research=False, peers=False, text=part.text, rerank=rerank, scorer=scorer, checked=True)
        for h in hits:
            h.part_id = part.id
        size = sum(fts.hit_tokens(h) for h in hits)
        used += size
        kept |= {h.chunk_id for h in hits}
        out += hits
        if trace is not None:
            for name in ("firm", "on_theme", "answers", "unattached"):
                getattr(trace, name).extend(getattr(part_trace, name))
        if part_pools is not None:
            part_pools[part.id] = part_trace.ids()
        plan.searched.append({"id": part.id, "share": round(share), "passages": len(hits),
                              "tokens": round(size), "pool": len(part_trace.ids()),
                              "chunk_ids": [h.chunk_id for h in hits], "vector_text": part.text})
    out += research
    peers = peer_pass(q, kept, rerank, trace=trace, scorer=scorer, checked=True)
    for h in peers:
        h.part_id = "peers"
    out += peers
    if q.window:  # recency questions read newest first (Q26)
        out.sort(key=lambda h: h.published_at, reverse=True)
    return out

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="load the embedding model and the reranker, score one pair")
    g.add_argument("--fetch", action="store_true", help="download the reranker into the cache (once)")
    args = ap.parse_args(argv)
    from cee.retrieve.embed import ModelNotCached, embed_query
    try:
        name = rerank_model_name()
        if args.fetch:
            print(f"Reranker {name} is in {fetch_reranker(name)}")
            return 0
        t = time.perf_counter()
        n = len(embed_query("advisor payout"))
        s = cross_encoder_scores("What does the firm pay its financial advisors?",
                                 ["Advisor compensation is a formulaic payout tied to revenue.",
                                  "The Firm guarantees the prompt payment of its clients' obligations."])
        print(f"embedding {n} dims; reranker {name} scores {[round(x, 3) for x in s]} "
              f"({time.perf_counter() - t:.1f} s)")
        return 0 if n and len(s) == 2 else 1
    except (ModelNotCached, RerankerNotCached, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"ERROR: {e}. The vectors extra is not installed: pip install -r requirements-vectors.txt",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
