"""Ask page: question box, answer with citation chips, caveats and gaps (always visible)."""
from __future__ import annotations

import streamlit as st

from cee.app import components as ui
from cee.answer.validate import source_label
from cee.ask import ask
from cee.config import settings

BEHAVIOR_TEXT = {
    "answer": "Answer",
    "answer_with_boundary": "Answer (evidence only; the judgement is yours)",
    "gap_with_adjacent": "Not in the corpus",
    "refuse": "No evidence",
}


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def footer_firms(query) -> str:
    """Same firms the gap box names (#50); firms we hold nothing for are marked."""
    return ", ".join(f if f in query.entities else f"{f} (no documents)" for f in query.firms) or "none"


def _ticker() -> None:
    s = ui.corpus_stats()
    firms = _plural(s["firms"], "firm")
    ui.ticker([f"Snapshot {s['snapshot']}", f"{firms} in corpus", _plural(s["docs"], "stored document"),
               _plural(s["chunks"], "indexed passage"), f"Latest filing {s['latest']}",
               "Every claim cites a stored document", "No evidence is a valid answer"])


def render() -> None:
    _ticker()
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.eyebrow("Evidence, not opinion")
        ui.hero("What is known, and", "where", "it was said.")
        st.caption("Ask a plain-language question about the peer set. Every claim links to a stored document; "
                   f"if nothing is stored, the answer says so. LLM provider: {settings().llm_provider}")
        question = st.text_input("Question", placeholder="What does Edward Jones's 10-K say about its number of financial advisors?")
        asked = st.button("Ask", type="primary")
    with right:
        s = ui.corpus_stats()
        ui.snapshot_card(s["snapshot"], [("DOCUMENTS", f"{s['docs']:,}"), ("PASSAGES", f"{s['chunks']:,}"),
                                         ("FIRMS", str(s["firms"]))])

    if not asked or not question.strip():
        ui.empty_state("No question asked yet. Answers appear here, with a citation for every claim.")
        return
    r = ask(question)
    a = r.answer
    by_id = {h.chunk_id: h for h in r.hits}

    def chips(chunk_ids):
        """One chip per citation: its own source label and tier. An id that is not in the
        retrieved set is shown, flagged, and not linked (no composed source)."""
        out = []
        for cid in chunk_ids:
            h = by_id.get(cid)
            out.append((cid, h.source_tier, source_label(h), True) if h
                       else (cid, None, "not in the retrieved set", False))
        return out

    ui.behavior_header(BEHAVIOR_TEXT[a.behavior], a.behavior)
    for i, c in enumerate(a.claims, start=1):
        ui.claim_card(i, c.text, chips(c.chunk_ids), "", c.flags)
    for i, c in enumerate(a.adjacent, start=1):
        ui.claim_card(i, c.text, chips(c.chunk_ids), "", c.flags,
                      label="ADJACENT EVIDENCE", note=c.differs_because)
    for cav in a.caveats:
        ui.caveat_box(cav)
    for g in a.gaps:
        ui.gap_box(g.what, g.suggested_source)
    st.markdown(f'<div class="cee-meta">Query #{r.query_id} | firms: {footer_firms(r.query)} | '
                f'{len(r.hits)} chunks retrieved | LLM called: {a.llm_called}</div>', unsafe_allow_html=True)
    with ui.placeholder("feedback", 62, "Feedback on this answer"):
        c1, c2, c3 = st.columns([1, 1, 4])
        c1.button("Helpful", disabled=True, key="fb_up")
        c2.button("Not helpful", disabled=True, key="fb_down")
        c3.text_input("Comment", disabled=True, key="fb_comment", label_visibility="collapsed",
                      placeholder="Comment")
