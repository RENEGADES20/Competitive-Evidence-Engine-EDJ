"""Feedback on an answer (#62): one rating and an optional comment per query.

Rule for a second submit on the same query: it replaces the first (one row per query, the
latest wins), so a corrected rating never leaves two rows that disagree.
"""
from __future__ import annotations

from cee.db import connect

HELPFUL, NOT_HELPFUL = 1, -1


def save_feedback(query_id: int, rating: int, comment: str = "") -> str:
    """Write the feedback row for query_id. Returns "saved" (first time) or "updated"."""
    if rating not in (HELPFUL, NOT_HELPFUL):
        raise ValueError(f"rating must be {HELPFUL} or {NOT_HELPFUL}, got {rating}")
    with connect() as conn:
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(62, %s)", (query_id,))
            old = conn.execute("DELETE FROM query_feedback WHERE query_id = %s", (query_id,)).rowcount
            conn.execute("INSERT INTO query_feedback (query_id, rating, comment) VALUES (%s, %s, %s)",
                         (query_id, rating, comment.strip() or None))
    return "updated" if old else "saved"
