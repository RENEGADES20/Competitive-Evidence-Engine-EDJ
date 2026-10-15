"""Source page, opened from ?chunk=<id>: stored passage, metadata and the stored file."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.config import FileNotAvailable, resolve_path
from cee.db import connect


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
    meta = [f"Section: {row['section']}"] + ([f"Page {row['page']}"] if row["page"] else []) + \
           [f"Chunk: {row['chunk_id']}", f"Filed: {row['published_at']}"]
    ui.source_header(f"{row['entity_id']} {row['doc_type']} {row['period_end'] or row['published_at']}",
                     row["source_tier"], meta)
    st.markdown("**Stored passage**")
    ui.passage(row["text"])
    with ui.placeholder("context", 53, "Passage in context"):
        st.markdown('<div class="cee-meta">Surrounding passages and the PDF opened at this page.</div>',
                    unsafe_allow_html=True)
    try:
        path = resolve_path(row["storage_path"])
        st.download_button("Download stored document", path.read_bytes(), file_name=path.name)
    except FileNotAvailable as e:
        st.info(str(e))
    if row["url"]:
        st.caption(f"Original filing (as recorded at ingestion): {row['url']}")
