"""Chunk and query embeddings: part of the optional vectors module (ADR-009). Owner: TL (Yueyang Du).

Vectors are off by default (CEE_VECTORS). The core (schema, build, app, eval in fts mode) never
imports this module's model code and needs no extension, no model and no network.

Model: BAAI/bge-small-en-v1.5 through fastembed (ONNX Runtime, no torch), 384 dims, the size of
`chunk_embeddings.embedding` in db/optional/vectors.sql. Install the extra first:
`pip install -r requirements-vectors.txt` (or `pip install -e .[vectors]`).

Model cache: FASTEMBED_CACHE_PATH (environment or .env), else <repo>/.cache/fastembed. The model
loads from the cache only (no network request); it is never downloaded by itself. Get it once
with `--fetch`, or copy the `models/` folder from the shared corpus folder (docs/RUN.md).

  python -m cee.retrieve.embed --fetch            download the model into the cache (once)
  python -m cee.retrieve.embed --query "text"     embed one question (offline check)
  python -m cee.retrieve.embed --missing          CEE_VECTORS=on: apply db/optional/vectors.sql,
                                                  embed every chunk without a chunk_embeddings row
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from cee.config import REPO_ROOT, vectors_enabled  # also loads .env

MODEL = "BAAI/bge-small-en-v1.5"
MODEL_FOLDER = "models--Qdrant--bge-small-en-v1.5-onnx-Q"  # fastembed's cache folder for MODEL
DIM = 384
BATCH = 256        # rows per database commit
# Texts per model call. One at a time is fastest on CPU (no padding; measured on this corpus:
# 1 -> 15.6, 8 -> 9.7, 32 -> 5.9 chunks/s) and needs little memory (256 per call needed 3 GB).
EMBED_BATCH = 1
DEFAULT_CACHE = REPO_ROOT / ".cache" / "fastembed"
VECTORS_SQL = REPO_ROOT / "db" / "optional" / "vectors.sql"

SELECT_MISSING = ("SELECT c.chunk_id, c.prefix || ' ' || c.text AS body FROM chunks c "
                  "WHERE NOT EXISTS (SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id) "
                  "ORDER BY length(c.prefix) + length(c.text), c.chunk_id")
# Stable order (shortest first), so progress lines are comparable between runs.
INSERT_ONE = ("INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (%s, %s::vector) "
              "ON CONFLICT (chunk_id) DO UPDATE SET embedding = EXCLUDED.embedding")
COUNT_MISSING = ("SELECT count(*) AS n FROM chunks c "
                 "WHERE NOT EXISTS (SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id)")


class ModelNotCached(RuntimeError):
    """The model is not in the cache; nothing is downloaded by itself."""


def cache_dir() -> Path:
    """Where the model lives: FASTEMBED_CACHE_PATH, else <repo>/.cache/fastembed.

    Never the fastembed default (<system temp>/fastembed_cache). HF_HOME (HuggingFace's own
    small files) is pointed next to it only when it is not set already. Creates no folder.
    """
    raw = os.getenv("FASTEMBED_CACHE_PATH", "").strip().strip('"')
    path = Path(raw) if raw else DEFAULT_CACHE
    os.environ.setdefault("HF_HOME", str(path.parent / "huggingface"))
    return path


def model_cached(path: Path | None = None) -> bool:
    """True when the model files are in the cache (checked without fastembed, which would
    create the folder)."""
    folder = (path or cache_dir()) / MODEL_FOLDER / "snapshots"
    return folder.is_dir() and any(folder.glob("*/model_optimized.onnx"))


@lru_cache(maxsize=1)
def model():
    """The cached model, loaded with local_files_only=True. Missing -> ModelNotCached."""
    path = cache_dir()
    if not model_cached(path):
        raise ModelNotCached(
            f"Embedding model {MODEL} is not in {path} (FASTEMBED_CACHE_PATH). It is never "
            "downloaded by itself. Get it once with `python -m cee.retrieve.embed --fetch`, or "
            "copy the models/ folder from the shared corpus folder into that folder (docs/RUN.md).")
    from fastembed import TextEmbedding  # imported late: the core never needs it
    return TextEmbedding(model_name=MODEL, cache_dir=str(path), local_files_only=True)


def fetch() -> Path:
    """Download the model into the cache (the only path that uses the network)."""
    from fastembed import TextEmbedding
    path = cache_dir()
    path.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {MODEL} (about 70 MB) into {path}...", file=sys.stderr, flush=True)
    TextEmbedding(model_name=MODEL, cache_dir=str(path))
    return path


def embed_texts(texts: Sequence[str], batch_size: int = EMBED_BATCH) -> list[list[float]]:
    return [v.tolist() for v in model().embed(list(texts), batch_size=batch_size)]


def embed_query(question: str) -> list[float]:
    return next(iter(model().query_embed(question))).tolist()


def vector_literal(vec: Iterable[float]) -> str:
    """pgvector text form '[0.1,0.2,...]', cast with ::vector (no pgvector Python package)."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def apply_vectors_sql(conn) -> None:
    """Run db/optional/vectors.sql (idempotent; it has its own BEGIN/COMMIT)."""
    conn.commit()
    conn.autocommit = True
    try:
        conn.execute(VECTORS_SQL.read_text(encoding="utf-8"))
    finally:
        conn.autocommit = False


def fill_missing(conn, batch: int = BATCH, embed=embed_texts, log=print) -> int:
    """Embed every chunk without a chunk_embeddings row; rows that have one are never touched.

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
            cur.executemany(INSERT_ONE, [(r["chunk_id"], vector_literal(v)) for v, r in zip(vecs, part)])
        conn.commit()
        log(f"   {min(i + batch, total)}/{total} chunks embedded ({time.monotonic() - start:.0f} s)")
    return total


def count_missing(conn) -> int:
    return conn.execute(COUNT_MISSING).fetchone()["n"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--missing", action="store_true",
                   help="CEE_VECTORS=on: apply db/optional/vectors.sql, embed every chunk without a vector")
    g.add_argument("--query", help="embed one question and print its size")
    g.add_argument("--fetch", action="store_true", help="download the model into the cache (once)")
    args = ap.parse_args(argv)

    try:
        if args.fetch:
            print(f"Model {MODEL} is in {fetch()}")
            return 0

        if args.query is not None:
            v = embed_query(args.query)
            print(f"{len(v)} dims, first values {[round(x, 4) for x in v[:3]]}")
            return 0 if len(v) == DIM else 1

        if not vectors_enabled():
            print("Vectors are off (CEE_VECTORS). Set CEE_VECTORS=on to embed chunks (docs/RUN.md).",
                  file=sys.stderr)
            return 2
        from cee.db import connect
        start = time.monotonic()
        with connect() as conn:
            apply_vectors_sql(conn)
            n = fill_missing(conn)
            left = count_missing(conn)
        print(f"{n} embedded, {left} still missing ({time.monotonic() - start:.0f} s, model {MODEL}, cache {cache_dir()})")
        return 0 if left == 0 else 1
    except (ModelNotCached, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"ERROR: {e}. The vectors extra is not installed: pip install -r requirements-vectors.txt",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
