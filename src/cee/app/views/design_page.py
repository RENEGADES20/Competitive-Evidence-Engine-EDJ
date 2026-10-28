"""Design page: every component with sample data (never real firm figures)."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui

SAMPLE_ID = "SAMPLE-DOC-2025#1"


def _section(title: str) -> None:
    st.markdown(f"#### {title}")


def render() -> None:
    ui.eyebrow("Design language")
    st.title("Design")
    ui.sample_banner()
    st.caption("Every component used in the app, filled with made-up sample data. See docs/DESIGN.md.")

    _section("Citation chip")
    st.markdown(ui.citation_chip_html(SAMPLE_ID, 2, link=False), unsafe_allow_html=True)

    _section("Tier badges (all five)")
    st.markdown(" ".join(ui.tier_badge_html(t) for t in range(1, 6)), unsafe_allow_html=True)

    _section("Answer behavior headers")
    for text, code in [("Answer", "answer"), ("Answer (evidence only; the judgement is yours)", "answer_with_boundary"),
                       ("Not in the corpus", "gap_with_adjacent"), ("No evidence", "refuse")]:
        ui.behavior_header(text, code)

    _section("Claim card")
    ui.claim_card(1, "Sample Co. describes its advisor network in the annual report.",
                  [(SAMPLE_ID, 2, "Sample Co. 10-K 2025-12-31, p.12 [filing]"),
                   ("SAMPLE-PRESS-2025#4", 4, "Sample Co. trade 2025-11-03 [trade press (indicative only)]")],
                  link=False)
    ui.claim_card(1, "Sample Co. reports a related segment, not the unit asked about.", [(SAMPLE_ID, 2)],
                  label="ADJACENT EVIDENCE", note="the segment includes a second business line", link=False)

    _section("Caveat box and gap box")
    ui.caveat_box("Sample segment is not the same as the sample brand: it also includes another business.")
    ui.gap_box("No stored passage for Sample Co. matches this question.", "Sample Co. Form ADV")

    _section("Source page header")
    ui.source_header("Sample Co. 10-K 2025-12-31", 2, ["Section: Item 1", "Page 4", f"Chunk: {SAMPLE_ID}"])

    _section("Passage in context")
    ui.context_passages([
        {"chunk_id": "SAMPLE-DOC-2025#0", "text": "A sample paragraph before the cited one.", "page": None, "cited": False},
        {"chunk_id": SAMPLE_ID, "text": "The sample paragraph that a citation points to.", "page": None, "cited": True},
        {"chunk_id": "SAMPLE-DOC-2025#2", "text": "A sample paragraph after the cited one.", "page": None, "cited": False}])
    st.caption("PDF chunks add the page number to each tag, and the stored PDF page is shown below the passages.")

    _section("Coverage cells")
    st.markdown("".join(ui.coverage_cell_html(state, text) for state, text in
                        [("covered", "12 docs"), ("thin", "1 doc"), ("empty", "0 docs")]), unsafe_allow_html=True)

    _section("Placeholder")
    with ui.placeholder("design-demo", "N", "Sample placeholder"):
        st.button("Disabled control", disabled=True, key="design_demo_btn")

    _section("Empty state")
    ui.empty_state("No question asked yet. Answers appear here, with a citation for every claim.")

    _section("Ticker and snapshot card")
    ui.ticker(["Snapshot corpus-2025-01-01", "3 firms in corpus", "Every claim cites a stored document"])
    ui.snapshot_card("corpus-2025-01-01", [("DOCUMENTS", "10"), ("PASSAGES", "200"), ("FIRMS", "3")])

    _section("Footer")
    st.caption("The footer at the bottom of every page shows the snapshot name read from the database.")
