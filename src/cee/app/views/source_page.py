"""Source page, opened from ?chunk=<id>: stored passage in its section, PDF page, metadata, file."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.config import FileNotAvailable, resolve_path
from cee.db import connect

CONTEXT_CHUNKS = 2  # neighbours shown on each side of the cited chunk


def neighbours(conn, row: dict) -> list[dict]:
    """The cited chunk and up to CONTEXT_CHUNKS chunks on each side, same document and section."""
    rows = conn.execute(
        """SELECT chunk_id, seq, page, text FROM chunks
           WHERE doc_id = %s AND section IS NOT DISTINCT FROM %s AND seq BETWEEN %s AND %s
           ORDER BY seq""",
        (row["doc_id"], row["section"], row["seq"] - CONTEXT_CHUNKS, row["seq"] + CONTEXT_CHUNKS)).fetchall()
    return [{"chunk_id": r["chunk_id"], "text": r["text"], "page": r["page"],
             "cited": r["chunk_id"] == row["chunk_id"]} for r in rows]


@st.cache_data(show_spinner=False)
def render_pdf_page(path: str, page: int) -> tuple[bytes, int] | None:
    """PNG of one 1-based page and the page count; None when the page is not in the file."""
    import pymupdf

    with pymupdf.open(path) as doc:
        if not 1 <= page <= doc.page_count:
            return None
        return doc[page - 1].get_pixmap(dpi=110).tobytes("png"), doc.page_count


def render(chunk_id: str) -> None:
    st.markdown("[&larr; Back to question](./)")
    with connect() as conn:
        row = conn.execute(
            """SELECT c.*, d.entity_id, d.doc_type, d.source_tier, d.published_at, d.period_end,
                      d.url, d.storage_path, d.sha256
               FROM chunks c JOIN documents d USING (doc_id) WHERE c.chunk_id = %s""",
            (chunk_id,)).fetchone()
        if not row:
            st.error(f"Chunk {chunk_id} is not in the stored corpus.")
            return
        context = neighbours(conn, row)
    meta = [f"Section: {row['section']}"] + ([f"Page {row['page']}"] if row["page"] else []) + \
           [f"Chunk: {row['chunk_id']}", f"Filed: {row['published_at']}"]
    ui.source_header(f"{row['entity_id']} {row['doc_type']} {row['period_end'] or row['published_at']}",
                     row["source_tier"], meta)
    st.markdown("**Stored passage**")
    ui.context_passages(context)

    try:
        path = resolve_path(row["storage_path"])
    except FileNotAvailable as e:
        st.info(str(e))
        path = None
    if path and row["page"] and path.suffix.lower() == ".pdf":
        st.markdown(f"**Page {row['page']} of the stored PDF**")
        try:
            shown = render_pdf_page(str(path), row["page"])
        except Exception as e:  # unreadable file: the passage above is still the evidence
            shown = None
            st.info(f"Could not open the PDF page ({type(e).__name__}); the stored passage above is unaffected.")
        else:
            if shown:
                ui.pdf_page(shown[0], row["page"], shown[1])
            else:
                st.info(f"Page {row['page']} is not in the stored PDF.")
    if path:
        st.download_button("Download stored document", path.read_bytes(), file_name=path.name)
    if row["url"]:
        st.caption(f"Original filing (as recorded at ingestion): {row['url']}")
