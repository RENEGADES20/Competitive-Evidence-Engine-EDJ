"""Coverage page: what the corpus holds per firm and document type (#41)."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.db import connect

THIN_MAX = 1  # a combination with this many documents or fewer (but not 0) is "thin"

# (entity_id, label shown, note). Merrill's parent filings sit under BAC (CLAUDE.md invariants).
ROWS = [("EDJ", "EDJ", ""), ("MS", "MS", ""), ("SCHW", "SCHW", ""), ("RJF", "RJF", ""),
        ("MER", "MER", "Merrill's own documents"),
        ("BAC", "BAC filings", "parent of Merrill; segment tags come with #37")]
TYPE_ORDER = ["10-K", "10-Q", "8-K", "DEF 14A", "press", "transcript", "supplement", "deck", "monthly",
              "adv", "trade"]


def cell_state(n: int) -> str:
    return "empty" if n == 0 else "thin" if n <= THIN_MAX else "covered"


def cell_text(n: int, first, last) -> str:
    if n == 0:
        return "0 docs"
    span = str(first) if first == last else f"{first}\nto {last}"
    return f"{n} doc{'' if n == 1 else 's'}\n{span}"


def build_grid(docs: list[dict], expected: list[dict]):
    """docs: entity_id, doc_type, n, first, last. expected: entity_id, doc_type (source_registry).
    Returns (columns, rows); a cell is (state, text), or None when the row does not expect the type."""
    ids = {r[0] for r in ROWS}
    want = {(e["entity_id"], e["doc_type"]) for e in expected if e["entity_id"] in ids}
    have = {(d["entity_id"], d["doc_type"]): d for d in docs if d["entity_id"] in ids}
    types = {t for _, t in want | set(have)}
    columns = [t for t in TYPE_ORDER if t in types] + sorted(types - set(TYPE_ORDER))
    rows = []
    for ent, label, note in ROWS:
        cells = []
        for t in columns:
            d = have.get((ent, t))
            if d is None and (ent, t) not in want:
                cells.append(None)
            else:
                n = d["n"] if d else 0
                cells.append((cell_state(n), cell_text(n, d["first"] if d else None, d["last"] if d else None)))
        rows.append((label, note, cells))
    return columns, rows


def load() -> tuple[list[dict], list[dict]]:
    with connect() as c:
        docs = c.execute("SELECT entity_id, doc_type, count(*) AS n, min(published_at) AS first, "
                         "max(published_at) AS last FROM documents GROUP BY 1, 2").fetchall()
        expected = c.execute("SELECT DISTINCT entity_id, doc_type FROM source_registry").fetchall()
    return docs, expected


def render() -> None:
    ui.eyebrow("What the corpus covers")
    st.title("Coverage")
    st.caption("Stored documents by firm and document type, with earliest and latest published date. "
               f"Thin = {THIN_MAX} document or fewer; empty = nothing stored. "
               "Columns are the types the source registry expects for these firms.")
    docs, expected = load()
    columns, rows = build_grid(docs, expected)
    ui.coverage_grid(columns, rows)
    st.caption("Themes (tier 5 research) are not shown yet: the topics taxonomy (#6) is not merged. "
               "Dates are published_at, which for some sources is the retrieval date.")
