"""Hybrid retrieval (#125, experimental branch exp/hybrid): keyword + vector candidates, RRF, local
rerank, then the same quotas as fts mode. Owner: TL (Yueyang Du); fts.py stays S1's.

Part of the optional vectors module (ADR-009): it needs CEE_VECTORS=on, the table
chunk_embeddings (db/optional/vectors.sql) and both models in the cache. Nothing here downloads a
model at query time; `--fetch` is the only path that does.

Inside the same SQL filters as fts mode (fts.entity_filter, fts.window_filter, fts.filters_sql;
entity+theme questions also get a research part with fts.theme_filter, as in fts mode):
  1. keyword leg: the fts words, synonyms and rank, top LEG_K per firm (every mode: research with
     no firm is its own group);
  2. vector leg: cosine distance to the question's embedding, top LEG_K per firm; the window
     function reads every eligible row, so it is exact (no approximate index);
  3. RRF per firm: score = sum over legs of 1 / (RRF_K + rank in that firm);
  4. rerank pool: (firm, document type) groups take turns down the fused list until RERANK_N
     candidates (the groups fts mode pools by); a local cross-encoder scores (question, passage);
     Hit.rank = sigmoid(score) in 0..1;
  5. floor: hits below the absolute RERANK_FLOOR are dropped (not inside a time window); then
     fts.select() with floor=0. select()'s relative FLOOR (share of the firm's best) is meant for
     ts_rank, where 0 means "no match"; on sigmoid scores it dropped most of the pool (#125 plan).
No LLM call (ADR-003): the reranker is a local ONNX model, retrieval stays deterministic.

Two modes share steps 1-4 (#126): `hybrid` orders the pool by the cross-encoder score;
`hybrid-norerank` (search(..., rerank=False)) orders it by the RRF score and loads no reranker.
In both, FLOOR[mode] is a relative floor on the RRF score, applied to the pool before any rerank:
a candidate below FLOOR x its firm's best RRF score in the pool is dropped (not inside a time
window). RRF is a ratio-like scale (0 = found by no leg; 2/(RRF_K+1) = first in both legs), so
"share of the firm's best" means "how much the two legs agree"; the cross-encoder sigmoid is not.
MAX_PER_DOC[mode] and DUP_JACCARD[mode] go to select() for the firm part; the window cap
(fts.WINDOW_MAX_PER_DOC) and the research cap (fts.THEME_MAX_PER_DOC) are not per mode.

  python -m cee.retrieve.hybrid --fetch      download the reranker into the cache (once)
  python -m cee.retrieve.hybrid --check      load both models from the cache, score one pair
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

from cee.retrieve import fts
from cee.retrieve.fts import K, Hit, HybridUnavailable, Query  # noqa: F401 (re-exported)

LEG_K = 100          # candidates per leg and firm
RRF_K = 60           # reciprocal rank fusion constant
RERANK_N = 50        # candidates the cross-encoder scores (firm part)
THEME_RERANK_N = 20  # candidates for the research part of entity+theme questions (#116)
RERANK_FLOOR = 0.0   # sigmoid score below which a hit is a weak match (outside time windows)
# 0 = no rerank floor: every grid value lost evidence on corpus-2026-10-29 (tier-1 passages 0.373 at 0,
# 0.339 / 0.323 / 0.310 at 0.01 / 0.05 / 0.1; #125 plan Progress log). Tuning is #126.
# Per mode (#126; values chosen by the selection rule in plans/0126-hybrid-eval.md, report in
# evals/hybrid-eval/corpus-2026-10-29/report.md).
FLOOR = {"hybrid": 0.0, "hybrid-norerank": 0.0}        # relative RRF floor on the pool
MAX_PER_DOC = {"hybrid": 3, "hybrid-norerank": 3}      # firm part; window / research caps unchanged
DUP_JACCARD = {"hybrid": 0.6, "hybrid-norerank": 0.6}  # word 5-gram overlap that counts as a repeat
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


def take_turns(fused: Sequence[tuple[str, float]], group_of: dict[str, object], n: int) -> list[str]:
    """The first n chunk_ids, groups taking turns: each group in its own fused order, the group
    with the best chunk first. Groups are (firm, document type), as fts mode pools them, so every
    firm and document type with candidates reaches the reranker."""
    queues: dict[object, list[str]] = {}
    for cid, _ in fused:
        queues.setdefault(group_of.get(cid), []).append(cid)
    out: list[str] = []
    while len(out) < n and any(queues.values()):
        for g in queues:
            if queues[g] and len(out) < n:
                out.append(queues[g].pop(0))
    return out


def gate(ids: Sequence[str], rrf_score: dict[str, float], group_of: dict[str, object], floor: float) -> list[str]:
    """Pool candidates whose RRF score is at least floor x the best RRF score of their firm in the
    pool, order kept. floor 0 keeps everything. group_of maps chunk_id -> (firm, doc type)."""
    if floor <= 0:
        return list(ids)
    firm = {c: (group_of.get(c) or (None,))[0] for c in ids}
    best: dict[object, float] = {}
    for c in ids:
        best[firm[c]] = max(best.get(firm[c], 0.0), rrf_score[c])
    return [c for c in ids if rrf_score[c] >= floor * best[firm[c]]]


def apply_floor(pool: list[Hit], floor: float) -> list[Hit]:
    """Pool sorted by rerank score (best first, ties by chunk_id), weak matches dropped."""
    ranked = sorted(pool, key=lambda h: (-h.rank, h.chunk_id))
    return [h for h in ranked if h.rank >= floor]


# --- SQL ---------------------------------------------------------------------------------------

KEYWORD_SQL = """
WITH q AS (
  SELECT {tsquery} AS tsq
), scored AS (
  SELECT c.chunk_id, d.entity_id, d.doc_type, {rank} AS rank
  FROM chunks c JOIN documents d USING (doc_id), q
  WHERE {match}
    AND {entity_filter}
    AND {window_filter}
    AND {filters}
), ranked AS (
  SELECT chunk_id, entity_id, doc_type,
         row_number() OVER (PARTITION BY entity_id ORDER BY rank DESC, chunk_id) AS rn
  FROM scored
)
SELECT chunk_id, entity_id, doc_type, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

VECTOR_SQL = """
WITH ranked AS (
  SELECT c.chunk_id, d.entity_id, d.doc_type,
         row_number() OVER (PARTITION BY d.entity_id ORDER BY e.embedding <=> %(qvec)s::vector, c.chunk_id) AS rn
  FROM chunks c JOIN documents d USING (doc_id) JOIN chunk_embeddings e USING (chunk_id)
  WHERE {entity_filter}
    AND {window_filter}
    AND {filters}
)
SELECT chunk_id, entity_id, doc_type, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

ROWS_SQL = """
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, c.text, c.prefix
FROM chunks c JOIN documents d USING (doc_id)
WHERE c.chunk_id = ANY(%(ids)s)
"""


def part_filters(q: Query, research: bool = False) -> tuple[str, str, str, dict]:
    """The hard filters, exactly as fts mode builds them: firm (or, for the research part of an
    entity+theme question, the theme filter), time window, Ask filters (#63)."""
    where, params = fts.theme_filter(q.themes) if research else fts.entity_filter(q.entities)
    window, window_params = fts.window_filter(q.window)
    filters, filter_params = fts.filters_sql(q)
    return where, window, filters, {**params, **window_params, **filter_params}


def keyword_leg_sql(conn, q: Query, research: bool = False) -> tuple[str, dict]:
    where, window, filters, params = part_filters(q, research)
    terms, synonyms = fts.keyword_terms(q)
    fragments, syn_params = fts._tsquery_sql(terms, synonyms)
    rank, rank_params = fts.rank_sql(conn, terms, syn_params) if conn is not None else ("0", {})
    match = "TRUE" if q.window else "c.tsv @@ q.tsq"  # as in fts mode
    sql = KEYWORD_SQL.format(**fragments, rank=rank, match=match, entity_filter=where,
                             window_filter=window, filters=filters)
    return sql, {**params, **syn_params, **rank_params, "terms": terms, "leg_k": LEG_K}


def vector_leg_sql(q: Query, qvec: str, research: bool = False) -> tuple[str, dict]:
    where, window, filters, params = part_filters(q, research)
    return (VECTOR_SQL.format(entity_filter=where, window_filter=window, filters=filters),
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

def candidates(conn, q: Query, qvec: str, n: int,
               research: bool = False) -> tuple[list[str], dict[str, float], dict[str, object]]:
    """Both legs, RRF per firm, then (firm, document type) groups take turns into n candidates.
    Returns (candidates, RRF score per chunk, (firm, doc type) per chunk)."""
    sql, params = keyword_leg_sql(conn, q, research)
    kw = conn.execute(sql, params).fetchall()
    sql, params = vector_leg_sql(q, qvec, research)
    vec = conn.execute(sql, params).fetchall()
    group_of = {r["chunk_id"]: (r["entity_id"], r["doc_type"]) for r in [*kw, *vec]}
    fused = rrf([*_per_firm(kw), *_per_firm(vec)])
    return take_turns(fused, group_of, n), dict(fused), group_of


def _per_firm(rows: list[dict]) -> list[list[str]]:
    """Split a leg into one ranked list per firm (rows come in per-firm rank order), so a
    chunk's RRF rank is its rank inside its firm: firms are not ranked against each other."""
    lists: dict[str | None, list[str]] = {}
    for r in rows:
        lists.setdefault(r["entity_id"], []).append(r["chunk_id"])
    return list(lists.values())


def search(q: Query, k: int = K, scorer: Scorer | None = None, timings: dict | None = None,
           rerank: bool = True) -> list[Hit]:
    """rerank=True: mode `hybrid` (cross-encoder order); False: `hybrid-norerank` (RRF order)."""
    mode = "hybrid" if rerank else "hybrid-norerank"
    if q.unmapped and not q.entities:
        return []  # firm is known but not in the corpus: nothing is eligible (no model, no SQL)
    if q.firm_filter and not q.entities:
        return []  # the firm filter leaves none of the firms the question names
    from cee.db import connect
    from cee.retrieve.embed import embed_query, vector_literal

    scorer = scorer or cross_encoder_scores
    floor = 0.0 if q.window else FLOOR[mode]  # inside a window every document is on topic
    t0 = time.perf_counter()
    with connect() as conn:
        check_vectors(conn)
        qvec = vector_literal(embed_query(q.question))
        firm_ids, firm_rrf, firm_groups = candidates(conn, q, qvec, RERANK_N)
        firm_ids = gate(firm_ids, firm_rrf, firm_groups, floor)
        research_ids, research_rrf = [], {}
        if q.mode == "entity+theme":
            research_ids, research_rrf, research_groups = candidates(conn, q, qvec, THEME_RERANK_N, research=True)
            research_ids = gate(research_ids, research_rrf, research_groups, floor)
        ids = firm_ids + [c for c in research_ids if c not in firm_ids]
        rows = {r["chunk_id"]: r for r in conn.execute(ROWS_SQL, {"ids": ids}).fetchall()}
    t1 = time.perf_counter()
    found = [cid for cid in ids if cid in rows]
    scores = dict(zip(found, scorer(q.question, [f"{rows[c]['prefix']} {rows[c]['text']}" for c in found]))) \
        if rerank else {}
    t2 = time.perf_counter()
    if timings is not None:
        timings.update(retrieve_s=t1 - t0, rerank_s=t2 - t1)

    def pool(cids: list[str], rrf_score: dict[str, float]) -> list[Hit]:
        """Hits in final order: cross-encoder sigmoid (hybrid) or RRF score (hybrid-norerank)."""
        if rerank:
            hits = [Hit(**{key: rows[c][key] for key in rows[c] if key != "prefix"}, rank=sigmoid(scores[c]))
                    for c in cids if c in scores]
            return apply_floor(hits, 0.0 if q.window else RERANK_FLOOR)
        hits = [Hit(**{key: rows[c][key] for key in rows[c] if key != "prefix"}, rank=rrf_score[c])
                for c in cids if c in rows]
        return apply_floor(hits, 0.0)  # sorts by RRF score, ties by chunk_id; the gate was the floor

    # Inside a window every document is on topic: no floor, one filing may be all there is (as fts).
    opts = {"floor": 0, "max_per_doc": fts.WINDOW_MAX_PER_DOC if q.window else MAX_PER_DOC[mode],
            "dup_jaccard": DUP_JACCARD[mode]}
    research = fts.select(pool(research_ids, research_rrf), min(fts.THEME_K, k),
                          **{**opts, "max_per_doc": fts.THEME_MAX_PER_DOC}) if research_ids else []
    hits = fts.select(pool(firm_ids, firm_rrf), k - len(research), **opts) + research
    if q.window:  # recency questions read newest first (Q26)
        hits.sort(key=lambda h: h.published_at, reverse=True)
    return hits


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
