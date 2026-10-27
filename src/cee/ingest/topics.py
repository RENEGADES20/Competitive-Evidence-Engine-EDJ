"""Topic tags for thematic (tier 5) chunks: config/topics.yaml -> topics, chunk_topics.

Owner: C3 (Jieyu Hu). Spec: specs/thematic.md; ExecPlan: plans/0081-institutional-research.md.
Rules (keyword tagging, no LLM):
  1. Keywords match as whole words, case-insensitively ("ai" never matches inside "said").
  2. A sub-topic is tagged only when its parent also matches in the same chunk, so generic
     sub-topic words ("trillion", "deployed") never tag on their own.
  3. A chunk tagged with a sub-topic also carries its parent.
  4. Fallback: a chunk with no match gets the document's most frequent top-level topic, so every
     chunk has at least one topic (spec acceptance). Fallback chunks are counted and reported.
Tags do not change retrieval: src/cee/retrieve does not read chunk_topics.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from cee.config import REPO_ROOT

TOPICS_PATH = REPO_ROOT / "config" / "topics.yaml"


@dataclass(frozen=True)
class Topic:
    topic_id: str
    label: str
    parent: str | None
    pattern: re.Pattern


def _pattern(keywords: list[str]) -> re.Pattern:
    # \b fails next to non-word characters ("reg bi", "12b-1"), so use explicit look-arounds.
    alts = sorted((re.escape(k.lower()) for k in keywords), key=len, reverse=True)
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(alts) + r")(?![a-z0-9])", re.IGNORECASE)


@lru_cache(maxsize=4)
def load_topics(path: Path = TOPICS_PATH) -> tuple[Topic, ...]:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)["topics"]
    return tuple(Topic(t["id"], t["label"], t.get("parent"), _pattern(t["keywords"])) for t in raw)


def tag_text(text: str, topics: tuple[Topic, ...] | None = None) -> set[str]:
    """Rules 1-3 for one chunk. Empty set when nothing matches (the fallback is per document)."""
    topics = topics or load_topics()
    hits = {t.topic_id for t in topics if t.pattern.search(text)}
    by_id = {t.topic_id: t for t in topics}
    return {tid for tid in hits if by_id[tid].parent is None or by_id[tid].parent in hits}


def tag_chunks(texts: list[str], topics: tuple[Topic, ...] | None = None) -> tuple[list[set[str]], int]:
    """Tags for every chunk of one document, with the rule-4 fallback. Returns (tags, n_fallback)."""
    topics = topics or load_topics()
    top_level = {t.topic_id for t in topics if t.parent is None}
    tags = [tag_text(t, topics) for t in texts]
    counts = Counter(tid for s in tags for tid in s if tid in top_level)
    if not counts:
        # No chunk matched at all: nothing to fall back on. Callers report this as a failure.
        return tags, 0
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    n_fallback = 0
    for s in tags:
        if not s:
            s.add(best)
            n_fallback += 1
    return tags, n_fallback


def seed_topics(conn, path: Path = TOPICS_PATH) -> int:
    """Upsert every topic; parents first (topics.parent_id is informative, not a foreign key)."""
    topics = load_topics(path)
    for t in sorted(topics, key=lambda t: t.parent is not None):
        conn.execute(
            """INSERT INTO topics (topic_id, label, parent_id) VALUES (%s, %s, %s)
               ON CONFLICT (topic_id) DO UPDATE SET label = EXCLUDED.label, parent_id = EXCLUDED.parent_id""",
            (t.topic_id, t.label, t.parent))
    return len(topics)


def tag_document(conn, doc_id: str) -> tuple[int, int]:
    """Replace chunk_topics for one document. Returns (chunks, fallback chunks)."""
    rows = conn.execute("SELECT chunk_id, text FROM chunks WHERE doc_id = %s ORDER BY seq",
                        (doc_id,)).fetchall()
    tags, n_fallback = tag_chunks([r["text"] for r in rows])
    conn.execute("DELETE FROM chunk_topics WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = %s)",
                 (doc_id,))
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO chunk_topics (chunk_id, topic_id) VALUES (%s, %s)",
                        [(r["chunk_id"], tid) for r, s in zip(rows, tags) for tid in sorted(s)])
    return len(rows), n_fallback
