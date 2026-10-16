"""Streamlit UI: page shell for Ask, Coverage and Design; the source page opens from ?chunk=<id>.

Owner: U1 (Yiqi Zhang). Look and components: docs/DESIGN.md, src/cee/app/components.py.
Run: streamlit run src/cee/app/streamlit_app.py
"""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.app.views import ask_page, coverage_page, design_page, source_page

st.set_page_config(page_title="Competitive Evidence Engine", layout="wide")
ui.inject_css()

with st.sidebar:
    st.markdown("**Filters**")
    with ui.placeholder("filters", 63, "Filters"):
        st.multiselect("Firms", [], disabled=True)
        st.date_input("Date range", value=[], disabled=True)
        st.text_input("Keywords", disabled=True)

pages = [st.Page(ask_page.render, title="Ask", url_path="ask", default=True),
         st.Page(coverage_page.render, title="Coverage", url_path="coverage"),
         st.Page(design_page.render, title="Design", url_path="design")]
nav = st.navigation(pages, position="top")

chunk = st.query_params.get("chunk")
if chunk:
    source_page.render(chunk)
else:
    nav.run()
ui.footer()
