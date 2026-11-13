"""Ask page: question box, answer with citation chips, caveats and gaps (always visible)."""
from __future__ import annotations

import time
from html import escape

import streamlit as st

from cee.app import components as ui
from cee.answer.validate import WITHHELD_NOTICE, source_label
from cee.ask import STAGES, Result, ask
from cee.config import entities_config, settings
from cee.feedback import HELPFUL, NOT_HELPFUL, save_feedback

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


def filters_sidebar() -> dict:
    """Optional filters (#63). They reach retrieval as SQL WHERE clauses, never the prompt."""
    names = {e["id"]: e["name"] for e in entities_config()["entities"]}
    with st.sidebar:
        st.markdown("**Filters**")
        st.caption("Optional. Only passages that match every filter are searched.")
        firms = st.multiselect("Firms", list(names), format_func=lambda i: f"{i} · {names[i]}", key="f_firms")
        dates = st.date_input("Date range", value=(), key="f_dates", format="YYYY-MM-DD",
                              help="Published date, both ends included. Pick a start and an end.")
        words = st.text_input("Keywords", key="f_keywords", placeholder="e.g. advisor, net new assets",
                              help="Comma-separated. Every keyword must appear in the passage.")
    date_range = tuple(dates) if isinstance(dates, (list, tuple)) and len(dates) == 2 else None
    if isinstance(dates, (list, tuple)) and len(dates) == 1:
        st.sidebar.caption("Pick an end date too; the date range is not applied yet.")
    return {"firms": firms, "date_range": date_range,
            "keywords": [w.strip() for w in words.split(",") if w.strip()]}


def filters_text(f: dict) -> str:
    parts = []
    if f.get("firms"):
        parts.append("firms " + ", ".join(f["firms"]))
    if f.get("date_range"):
        parts.append(f"dates {f['date_range'][0]} to {f['date_range'][1]}")
    if f.get("keywords"):
        parts.append("keywords " + ", ".join(f["keywords"]))
    return "; ".join(parts) or "none"


def ask_with_trace(question: str, filters: dict | None = None) -> Result | None:
    """Progress bar + one line per stage while the answer is built (#80). The trace stays on the
    page, collapsed, once the answer is ready; a failed stage is marked and its error shown."""
    bar = st.progress(0.0, text="Reading the question")
    box = st.status("Building the answer", expanded=True)
    slot = box.empty()
    steps: dict[str, tuple[str, str]] = {}

    def progress(stage: str, state: str, text: str) -> None:
        steps[stage] = (state, text)
        finished = sum(s != "running" for s, _ in steps.values())
        bar.progress(finished / len(STAGES), text=text)
        ui.trace_lines(list(steps.values()), slot)

    start = time.perf_counter()
    try:
        r = ask(question, progress=progress, filters=filters)
    except Exception as e:
        bar.empty()
        failed = next((t for s, t in steps.values() if s == "failed"), "A step failed")
        box.update(label=failed, state="error", expanded=True)
        st.error(f"The answer could not be built. {type(e).__name__}: {e}")
        return None
    bar.empty()
    box.update(label=f"How this answer was built: {len(steps)} steps in {time.perf_counter() - start:.1f} s",
               state="complete", expanded=False)
    return r


def render() -> None:
    _ticker()
    filters = filters_sidebar()
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

    if asked and question.strip():
        r = ask_with_trace(question, filters)
        # Kept for reruns: clicking a feedback control reruns the page, the answer must stay.
        st.session_state["last_answer"] = (r, filters) if r else None
        if r is None:
            return
    last = st.session_state.get("last_answer")
    if not last:
        ui.empty_state("No question asked yet. Answers appear here, with a citation for every claim.")
        return
    show_answer(*last)


def show_answer(r: Result, filters: dict) -> None:
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
    if a.withheld:
        ui.withheld_box(WITHHELD_NOTICE)
    for cav in a.caveats:
        ui.caveat_box(cav)
    for g in a.gaps:
        ui.gap_box(g.what, g.suggested_source)
    if a.coverage_note:
        ui.coverage_box(a.coverage_note)
    st.markdown(f'<div class="cee-meta">Query #{r.query_id} | firms: {footer_firms(r.query)} | '
                f'filters: {escape(filters_text(filters))} | {len(r.hits)} chunks retrieved | LLM called: {a.llm_called}</div>', unsafe_allow_html=True)
    feedback_form(r.query_id)


RATINGS = {"Helpful": HELPFUL, "Not helpful": NOT_HELPFUL}


def feedback_form(query_id: int | None) -> None:
    """Rating + optional comment, stored against the query (#62). Sending again for the same
    query replaces the earlier feedback (src/cee/feedback.py)."""
    if query_id is None:
        return
    with st.form(key=f"feedback-{query_id}", border=True):
        st.markdown("**Feedback on this answer**")
        rating = st.radio("Rating", list(RATINGS), index=None, horizontal=True)
        comment = st.text_area("Comment (optional)", placeholder="What was wrong or missing?", height=80)
        sent = st.form_submit_button("Send feedback")
    if sent:
        if rating is None:
            st.warning("Pick Helpful or Not helpful first.")
        else:
            how = save_feedback(query_id, RATINGS[rating], comment)
            st.success(f"Feedback {how} for query #{query_id}"
                       + (" (replaces the earlier one)." if how == "updated" else "."))
