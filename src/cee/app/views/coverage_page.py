"""Coverage page: shell only. The entity x doc_type table arrives with #41."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui


def render() -> None:
    ui.eyebrow("What the corpus covers")
    st.title("Coverage")
    st.caption("Stored documents by firm and document type, with earliest and latest dates.")
    with ui.placeholder("coverage", 41, "Coverage table"):
        st.markdown('<div class="cee-meta">Firm x document type grid: count, earliest and latest '
                    'published date; thin and empty cells highlighted.</div>', unsafe_allow_html=True)
