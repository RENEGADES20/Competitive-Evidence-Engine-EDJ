"""Hybrid retrieval (#125, ADR-008): keyword + vector candidates, RRF, local rerank, then the
same quotas as fts mode. Owner: TL (Yueyang Du); fts.py stays S1's.

Inside the same SQL entity / segment / window filters as fts mode (fts.entity_filter,
fts.window_filter):
  1. keyword leg: the fts words, synonyms and rank (fts.keyword_terms, fts.rank_sql), top LEG_K
     per named firm (theme questions: top LEG_K overall);
  2. vector leg: cosine distance to the question's embedding (embed.embed_query), top LEG_K per
     named firm (theme questions: top LEG_K overall, through the HNSW index);
  3. RRF: score = sum over legs of 1 / (RRF_K + rank);
  4. rerank: firms take turns down the RRF list until RERANK_N candidates; a local cross-encoder
     scores (question, passage); Hit.rank = sigmoid(score) in 0..1;
  5. floor: hits below RERANK_FLOOR are dropped (not inside a time window: "what's new" names no
     topic, as fts mode uses no floor there); then fts.select() with the fts constants.
No LLM call (ADR-003): the reranker is a local ONNX model, retrieval stays deterministic.

  python -m cee.retrieve.hybrid --check      load both models and score one pair (offline check)
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from functools import lru_cache
from typing import Callable, Sequence

from cee.retrieve import fts
from cee.retrieve.fts import K, Hit, Query

LEG_K = 100        # candidates per leg (per named firm)
RRF_K = 60         # reciprocal rank fusion constant
RERANK_N = 50      # candidates the cross-encoder scores
RERANK_FLOOR = 0.05  # sigmoid score below which a hit is a weak match (outside time windows)
DEFAULT_RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-12-v2"
RERANK_SIZES = {"Xenova/ms-marco-MiniLM-L-12-v2": "about 120 MB", "BAAI/bge-reranker-base": "about 1 GB"}
EF_SEARCH = 100    # HNSW candidates for the theme leg; iterative scan fills up to LEG_K under filters

Scorer = Callable[[str, Sequence[str]], list[float]]


class MissingVectors(RuntimeError):
    pass


def rerank_model_name() -> str:
    return os.getenv("RERANK_MODEL", "").strip() or DEFAULT_RERANK_MODEL


@lru_cache(maxsize=4)
def _cross_encoder(name: str):
    from fastembed.rerank.cross_encoder import TextCrossEncoder  # imported late: tests need no model

    from cee.retrieve.embed import load_cached
    return load_cached(TextCrossEncoder, name, RERANK_SIZES.get(name, "size unknown"))


def cross_encoder_scores(question: str, passages: Sequence[str]) -> list[float]:
    """Raw cross-encoder scores (logits), one per passage, in order."""
    if not passages:
        return []
    return [float(x) for x in _cross_encoder(rerank_model_name()).rerank(question, list(passages), batch_size=16)]


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


def take_turns(fused: Sequence[tuple[str, float]], firm_of: dict[str, str | None], n: int,
               by_firm: bool) -> list[str]:
    """The first n chunk_ids of the fused list; with by_firm, firms take turns (each in its own
    fused order, the firm with the best chunk first), so every named firm reaches the reranker."""
    if not by_firm:
        return [cid for cid, _ in fused[:n]]
    queues: dict[str | None, list[str]] = {}
    for cid, _ in fused:
        queues.setdefault(firm_of.get(cid), []).append(cid)
    out: list[str] = []
    while len(out) < n and any(queues.values()):
        for firm in queues:
            if queues[firm] and len(out) < n:
                out.append(queues[firm].pop(0))
    return out


def apply_floor(pool: list[Hit], floor: float) -> list[Hit]:
    """Pool sorted by rerank score (best first, ties by chunk_id), weak matches dropped."""
    ranked = sorted(pool, key=lambda h: (-h.rank, h.chunk_id))
    return [h for h in ranked if h.rank >= floor]


# --- SQL ---------------------------------------------------------------------------------

KEYWORD_SQL = """
WITH q AS (
  SELECT {tsquery} AS tsq
), scored AS (
  SELECT c.chunk_id, d.entity_id, {rank} AS rank
  FROM chunks c JOIN documents d USING (doc_id), q
  WHERE {match}
    AND {entity_filter}
    AND {window_filter}
), ranked AS (
  SELECT chunk_id, entity_id, row_number() OVER (PARTITION BY {partition} ORDER BY rank DESC, chunk_id) AS rn
  FROM scored
)
SELECT chunk_id, entity_id, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

VECTOR_SQL_PER_FIRM = """
WITH ranked AS (
  SELECT c.chunk_id, d.entity_id,
         row_number() OVER (PARTITION BY d.entity_id ORDER BY c.embedding <=> %(qvec)s::vector, c.chunk_id) AS rn
  FROM chunks c JOIN documents d USING (doc_id)
  WHERE {entity_filter}
    AND {window_filter}
)
SELECT chunk_id, entity_id, rn FROM ranked WHERE rn <= %(leg_k)s ORDER BY rn, chunk_id
"""

VECTOR_SQL_THEME = """
SELECT c.chunk_id, d.entity_id
FROM chunks c JOIN documents d USING (doc_id)
WHERE {entity_filter}
  AND {window_filter}
ORDER BY c.embedding <=> %(qvec)s::vector
LIMIT %(leg_k)s
"""

ROWS_SQL = """
SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, c.text, c.prefix
FROM chunks c JOIN documents d USING (doc_id)
WHERE c.chunk_id = ANY(%(ids)s)
"""

HNSW_SETTINGS = ("SET LOCAL hnsw.iterative_scan = strict_order", f"SET LOCAL hnsw.ef_search = {EF_SEARCH}")


def filters(q: Query) -> tuple[str, str, dict]:
    """The hard filters, exactly as fts mode builds them (entity / segment, time window)."""
    where, params = fts.entity_filter(q.entities)
    window, window_params = fts.window_filter(q.window)
    return where, window, {**params, **window_params}


def keyword_leg_sql(conn, q: Query) -> tuple[str, dict]:
    where, window, params = filters(q)
    terms, synonyms = fts.keyword_terms(q)
    fragments, syn_params = fts._tsquery_sql(terms, synonyms)
    rank, rank_params = fts.rank_sql(conn, terms, syn_params) if conn is not None else ("0", {})
    match = "TRUE" if q.window else "c.tsv @@ q.tsq"  # as in fts mode
    partition = "entity_id" if q.entities else "1"
    sql = KEYWORD_SQL.format(**fragments, rank=rank, match=match, entity_filter=where,
                             window_filter=window, partition=partition)
    return sql, {**params, **syn_params, **rank_params, "terms": terms, "leg_k": LEG_K}


def vector_leg_sql(q: Query, qvec: str) -> tuple[str, dict]:
    where, window, params = filters(q)
    template = VECTOR_SQL_PER_FIRM if q.entities else VECTOR_SQL_THEME
    return template.format(entity_filter=where, window_filter=window), {**params, "qvec": qvec, "leg_k": LEG_K}


def vector_leg(conn, q: Query, qvec: str, exact: bool = False) -> list[dict]:
    sql, params = vector_leg_sql(q, qvec)
    for s in HNSW_SETTINGS:
        conn.execute(s)
    if exact:
        conn.execute("SET LOCAL enable_indexscan = off")
    return conn.execute(sql, params).fetchall()


def check_vectors(conn) -> None:
    if conn.execute("SELECT EXISTS (SELECT 1 FROM chunks WHERE embedding IS NULL) AS e").fetchone()["e"]:
        raise MissingVectors(
            "Hybrid retrieval needs a vector for every chunk, and this database has chunks without one. "
            "Run `python -m cee.retrieve.embed --missing` (about 20 min) or restore a snapshot built after "
            "#124, or set RETRIEVAL_MODE=fts.")


# --- search ------------------------------------------------------------------------------

def search(q: Query, k: int = K, scorer: Scorer | None = None, timings: dict | None = None) -> list[Hit]:
    if q.unmapped and not q.entities:
        return []  # firm is known but not in the corpus: nothing is eligible (no model, no SQL)
    from cee.db import connect
    from cee.retrieve.embed import embed_query, vector_literal

    scorer = scorer or cross_encoder_scores
    t0 = time.perf_counter()
    qvec = vector_literal(embed_query(q.question))
    with connect() as conn:
        check_vectors(conn)
        sql, params = keyword_leg_sql(conn, q)
        kw = conn.execute(sql, params).fetchall()
        vec = vector_leg(conn, q, qvec)
        firm_of = {r["chunk_id"]: r["entity_id"] for r in [*kw, *vec]}
        if q.entities:
            fused = rrf([*_per_firm(kw), *_per_firm(vec)])
        else:  # theme question: one ranking over every firm
            fused = rrf([[r["chunk_id"] for r in kw], [r["chunk_id"] for r in vec]])
        ids = take_turns(fused, firm_of, RERANK_N, by_firm=bool(q.entities))
        rows = {r["chunk_id"]: r for r in conn.execute(ROWS_SQL, {"ids": ids}).fetchall()}
    t1 = time.perf_counter()
    candidates = [rows[cid] for cid in ids if cid in rows]
    scores = scorer(q.question, [f"{r['prefix']} {r['text']}" for r in candidates])
    pool = [Hit(**{key: r[key] for key in r if key != "prefix"}, rank=sigmoid(s)) for r, s in zip(candidates, scores)]
    t2 = time.perf_counter()
    if timings is not None:
        timings.update(retrieve_s=t1 - t0, rerank_s=t2 - t1)
    if q.window:  # inside a window every document is on topic: no floor, newest first (Q26)
        hits = fts.select(apply_floor(pool, 0.0), k, floor=0, max_per_doc=fts.WINDOW_MAX_PER_DOC)
        hits.sort(key=lambda h: h.published_at, reverse=True)
        return hits
    return fts.select(apply_floor(pool, RERANK_FLOOR), k)


def _per_firm(rows: list[dict]) -> list[list[str]]:
    """Split a leg into one ranked list per firm (rows come in per-firm rank order), so a
    chunk's RRF rank is its rank inside its firm: firms are not ranked against each other."""
    lists: dict[str | None, list[str]] = {}
    for r in rows:
        lists.setdefault(r["entity_id"], []).append(r["chunk_id"])
    return list(lists.values())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="load the embedding model and the reranker, score one pair")
    args = ap.parse_args(argv)
    if not args.check:
        ap.print_help()
        return 0
    from cee.retrieve.embed import embed_query
    t = time.perf_counter()
    n = len(embed_query("advisor payout"))
    s = cross_encoder_scores("What does the firm pay its financial advisors?",
                             ["Advisor compensation is a formulaic payout tied to revenue.",
                              "The Firm guarantees the prompt payment of its clients' obligations."])
    print(f"embedding {n} dims; reranker {rerank_model_name()} scores {[round(x, 3) for x in s]} "
          f"({time.perf_counter() - t:.1f} s)")
    return 0 if n and len(s) == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
