"""Coverage page: what the corpus holds per firm and document type (#41)."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.config import entities_config
from cee.db import connect

# Fewest documents that cover one expected period, by the source registry's expected_cadence:
# one 10-K is a full year, but one transcript of four quarters is thin. Other cadences: 2.
COVERED_MIN = {"annual": 1, "annual amendment": 1, "quarterly": 4, "monthly": 3}
DEFAULT_MIN = 2

# Columns in reading order; a type not listed here comes after, alphabetically.
TYPE_ORDER = ["10-K", "10-Q", "8-K", "DEF 14A", "press", "transcript", "supplement", "deck", "monthly",
              "adv", "trade"]


def rows_from_config(entities: list[dict]) -> list[tuple[str, str, str]]:
    """(entity_id, label, note) for every firm in config/entities.yaml, in config order, so a new
    firm is a config change. A firm reported inside a parent (MER in BAC GWIM) and its parent say so."""
    children = {e["parent"]: e for e in entities if e.get("parent")}
    rows = []
    for e in entities:
        if e.get("parent"):
            note = f"own documents; also {e['parent']} chunks tagged {e.get('reported_as') or e['name']}"
        elif e["id"] in children:
            child = children[e["id"]]
            note = f"filings; parent of {child['name']}"
        else:
            note = ""
        rows.append((e["id"], e["id"], note))
    return rows


def cell_state(n: int, cadence: str | None = None) -> str:
    if n == 0:
        return "empty"
    return "covered" if n >= COVERED_MIN.get(cadence or "", DEFAULT_MIN) else "thin"


def cell_text(n: int, first, last) -> str:
    if n == 0:
        return "0 docs"
    span = str(first) if first == last else f"{first}\nto {last}"
    return f"{n} doc{'' if n == 1 else 's'}\n{span}"


def build_grid(docs: list[dict], expected: list[dict], firms: list[tuple[str, str, str]],
               segment_chunks: dict[str, int] | None = None):
    """docs: entity_id, doc_type, n, first, last. expected: entity_id, doc_type, expected_cadence
    (source_registry). firms: rows_from_config(). segment_chunks: entity_id -> parent chunks tagged
    with its segment (MER -> BAC GWIM). Returns (columns, rows); a cell is (state, text), or None
    when the row does not expect the type."""
    ids = {r[0] for r in firms}
    cadence = {(e["entity_id"], e["doc_type"]): e.get("expected_cadence") for e in expected}
    want = {(e["entity_id"], e["doc_type"]) for e in expected if e["entity_id"] in ids}
    have = {(d["entity_id"], d["doc_type"]): d for d in docs if d["entity_id"] in ids}
    types = {t for _, t in want | set(have)}
    columns = [t for t in TYPE_ORDER if t in types] + sorted(types - set(TYPE_ORDER))
    rows = []
    for ent, label, note in firms:
        if segment_chunks and ent in segment_chunks:
            note += f": {segment_chunks[ent]} chunks"
        cells = []
        for t in columns:
            d = have.get((ent, t))
            if d is None and (ent, t) not in want:
                cells.append(None)
            else:
                n = d["n"] if d else 0
                cells.append((cell_state(n, cadence.get((ent, t))), cell_text(n, d["first"] if d else None, d["last"] if d else None)))
        rows.append((label, note, cells))
    return columns, rows


def load(entities: list[dict]) -> tuple[list[dict], list[dict], dict[str, int]]:
    with connect() as c:
        docs = c.execute("SELECT entity_id, doc_type, count(*) AS n, min(published_at) AS first, "
                         "max(published_at) AS last FROM documents GROUP BY 1, 2").fetchall()
        expected = c.execute("SELECT DISTINCT entity_id, doc_type, expected_cadence FROM source_registry").fetchall()
        # the same rule as the retrieval filter (fts.entity_filter): parent chunks tagged with the segment
        segment_chunks = {
            e["id"]: c.execute("SELECT count(*) AS n FROM chunks JOIN documents USING (doc_id) "
                               "WHERE entity_id = %s AND segment = ANY(%s)",
                               (e["parent"], [e["reported_as"], e["name"]])).fetchone()["n"]
            for e in entities if e.get("parent") and e.get("reported_as")}
    return docs, expected, segment_chunks


def render() -> None:
    ui.eyebrow("What the corpus covers")
    st.title("Coverage")
    st.caption("Stored documents by firm and document type, with earliest and latest published date. "
               "Thin = fewer documents than one period of the type's expected cadence (4 for quarterly, "
               "1 for annual); empty = nothing stored. "
               "Columns are the types the source registry expects for these firms.")
    entities = entities_config()["entities"]
    docs, expected, segment_chunks = load(entities)
    columns, rows = build_grid(docs, expected, rows_from_config(entities), segment_chunks)
    ui.coverage_grid(columns, rows)
    st.caption("Themes (tier 5 research) are not shown yet; they come with topic tags (#81). "
               "Dates are published_at, which for some sources is the retrieval date.")
