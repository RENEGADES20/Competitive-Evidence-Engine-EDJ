"""Chunk and query embeddings for hybrid retrieval (#124). Owner: TL (Yueyang Du).

Model: BAAI/bge-small-en-v1.5 through fastembed (ONNX Runtime, no torch), 384 dims, the
size of `chunks.embedding` in db/upgrade.sql. Vectors are computed once, at snapshot build
(scripts/build-snapshot.*), and travel inside the snapshot; teammates only embed questions.
Hybrid retrieval (#125, src/cee/retrieve/hybrid.py) embeds the question with `embed_query`.

Model cache: FASTEMBED_CACHE_PATH (environment or .env), else <repo>/.cache/fastembed.
A cached model loads with `local_files_only=True`, so no network request is made; the model
is downloaded (about 70 MB) only when it is not in the cache. Offline teammates copy the
Box `models/` folder into the cache folder (docs/RUN.md).

  python -m cee.retrieve.embed --missing          embed every chunk whose embedding is NULL
  python -m cee.retrieve.embed --query "text"     embed one question (offline check)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from cee.config import REPO_ROOT  # also loads .env

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
BATCH = 256        # rows per database commit
# Texts per model call. One at a time is fastest on CPU (no padding; measured on this corpus:
# 1 -> 15.6, 8 -> 9.7, 32 -> 5.9 chunks/s) and needs little memory (256 per call needed 3 GB).
EMBED_BATCH = 1
DEFAULT_CACHE = REPO_ROOT / ".cache" / "fastembed"

SELECT_MISSING = ("SELECT chunk_id, prefix || ' ' || text AS body FROM chunks "
                  "WHERE embedding IS NULL ORDER BY length(prefix) + length(text), chunk_id")
# Stable order (shortest first), so progress lines are comparable between runs.
UPDATE_ONE = "UPDATE chunks SET embedding = %s::vector WHERE chunk_id = %s"
COUNT_MISSING = "SELECT count(*) AS n FROM chunks WHERE embedding IS NULL"


def cache_dir() -> Path:
    """Where the model lives: FASTEMBED_CACHE_PATH, else <repo>/.cache/fastembed.

    Never the fastembed default (<system temp>/fastembed_cache). HF_HOME (HuggingFace's own
    small files) is pointed next to it only when it is not set already.
    """
    raw = os.getenv("FASTEMBED_CACHE_PATH", "").strip().strip('"')
    path = Path(raw) if raw else DEFAULT_CACHE
    os.environ.setdefault("HF_HOME", str(path.parent / "huggingface"))
    return path


def load_cached(cls, name: str, size: str):
    """Load a fastembed model class (TextEmbedding, TextCrossEncoder) from the cache, without any
    network request; download it only when the cached load fails.

    The cached load's error is printed first, so a broken install (e.g. an onnxruntime wheel that
    does not load) is not hidden behind a download error, and it stays chained if the download
    fails too (PR #140 review)."""
    path = cache_dir()
    path.mkdir(parents=True, exist_ok=True)
    try:  # cached model: no network request at all
        return cls(model_name=name, cache_dir=str(path), local_files_only=True)
    except Exception as first:  # not cached yet, incomplete, or the runtime does not load
        print(f"Could not load {name} from {path}: {type(first).__name__}: {first}", file=sys.stderr, flush=True)
        print(f"Downloading {name} ({size})...", file=sys.stderr, flush=True)
        try:
            return cls(model_name=name, cache_dir=str(path))
        except Exception as second:
            raise second from first


@lru_cache(maxsize=1)
def model():
    from fastembed import TextEmbedding  # imported late: tests and --help need no model

    return load_cached(TextEmbedding, MODEL, "about 70 MB")


def embed_texts(texts: Sequence[str], batch_size: int = EMBED_BATCH) -> list[list[float]]:
    return [v.tolist() for v in model().embed(list(texts), batch_size=batch_size)]


def embed_query(question: str) -> list[float]:
    return next(iter(model().query_embed(question))).tolist()


def vector_literal(vec: Iterable[float]) -> str:
    """pgvector text form '[0.1,0.2,...]', cast with ::vector (no pgvector Python package)."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def fill_missing(conn, batch: int = BATCH, embed=embed_texts, log=print) -> int:
    """Embed every chunk whose embedding is NULL; rows that have one are never touched.

    Commits after each batch, so a stopped run resumes where it left off.
    """
    rows = conn.execute(SELECT_MISSING).fetchall()
    conn.commit()
    total, start = len(rows), time.monotonic()
    for i in range(0, total, batch):
        part = rows[i:i + batch]
        vecs = embed([r["body"] for r in part])
        if any(len(v) != DIM for v in vecs):
            raise ValueError(f"model returned a vector that is not {DIM} long")
        with conn.cursor() as cur:
            cur.executemany(UPDATE_ONE, [(vector_literal(v), r["chunk_id"]) for v, r in zip(vecs, part)])
        conn.commit()
        log(f"   {min(i + batch, total)}/{total} chunks embedded ({time.monotonic() - start:.0f} s)")
    return total


def count_missing(conn) -> int:
    return conn.execute(COUNT_MISSING).fetchone()["n"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--missing", action="store_true", help="embed every chunk whose embedding is NULL")
    g.add_argument("--query", help="embed one question and print its size")
    args = ap.parse_args(argv)

    if args.query is not None:
        v = embed_query(args.query)
        print(f"{len(v)} dims, first values {[round(x, 4) for x in v[:3]]}")
        return 0 if len(v) == DIM else 1

    from cee.db import connect
    start = time.monotonic()
    with connect() as conn:
        n = fill_missing(conn)
        left = count_missing(conn)
    print(f"{n} embedded, {left} still NULL ({time.monotonic() - start:.0f} s, model {MODEL}, cache {cache_dir()})")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
