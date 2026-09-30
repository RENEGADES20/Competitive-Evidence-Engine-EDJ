"""Streamlit UI: ask a question, read the cited answer, open the stored source.

Skeleton placeholder, owner: U1 (Yiqi Zhang).
Run: streamlit run src/cee/app/streamlit_app.py
Not yet (U1, W3+): filters, coverage page, PDF page view, feedback buttons.
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

from cee.answer.validate import TIER_LABELS
from cee.ask import ask
from cee.config import FileNotAvailable, resolve_path, settings
from cee.db import connect

st.set_page_config(page_title="Competitive Evidence Engine", layout="wide")

BEHAVIOR_TEXT = {
    "answer": "Answer",
    "answer_with_boundary": "Answer (evidence only; the judgement is yours)",
    "gap_with_adjacent": "Not in the corpus",
    "refuse": "No evidence",
}


def chunk_link(chunk_id: str) -> str:
    return f"?chunk={quote(chunk_id)}"


def source_page(chunk_id: str) -> None:
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
    st.subheader(f"{row['entity_id']} {row['doc_type']} {row['period_end'] or row['published_at']}")
    st.caption(f"Tier: {TIER_LABELS.get(row['source_tier'])} | Section: {row['section']}"
               + (f" | Page {row['page']}" if row["page"] else "")
               + f" | Chunk: {row['chunk_id']} | Filed: {row['published_at']}")
    st.markdown("**Stored passage**")
    st.text(row["text"])
    try:
        path = resolve_path(row["storage_path"])
        st.download_button("Download stored document", path.read_bytes(), file_name=path.name)
    except FileNotAvailable as e:
        st.info(str(e))
    if row["url"]:
        st.caption(f"Original filing (as recorded at ingestion): {row['url']}")


def ask_page() -> None:
    st.title("Competitive Evidence Engine")
    st.caption(f"Skeleton build. LLM provider: {settings().llm_provider}")
    question = st.text_input("Question", placeholder="What does Edward Jones's 10-K say about its number of financial advisors?")
    if not st.button("Ask", type="primary") or not question.strip():
        return
    r = ask(question)
    a = r.answer
    st.subheader(BEHAVIOR_TEXT[a.behavior])
    for i, c in enumerate(a.claims, start=1):
        cites = " ".join(f"[{cid}]({chunk_link(cid)})" for cid in c.chunk_ids)
        flags = f"  \n:warning: {', '.join(c.flags)}" if c.flags else ""
        st.markdown(f"**{i}.** {c.text}  \n{cites}  \n*{c.source_label}*{flags}")
    for c in a.adjacent:
        cites = " ".join(f"[{cid}]({chunk_link(cid)})" for cid in c.chunk_ids)
        st.markdown(f"*Adjacent:* {c.text} {cites}  \n*Differs because:* {c.differs_because}")
    for cav in a.caveats:
        st.warning(cav)
    for g in a.gaps:
        st.error(f"**Gap:** {g.what}" + (f"  \n**Would be filled by:** {g.suggested_source}" if g.suggested_source else ""))
    st.caption(f"Query #{r.query_id} | firms: {', '.join(r.query.entities) or 'none'} | "
               f"{len(r.hits)} chunks retrieved | LLM called: {a.llm_called}")


chunk = st.query_params.get("chunk")
if chunk:
    source_page(chunk)
else:
    ask_page()
