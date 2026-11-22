"""Ask page: question box, answer with citation chips, caveats and gaps (always visible)."""
from __future__ import annotations

import time
from html import escape

import streamlit as st

from cee.app import components as ui
from cee.answer.validate import WITHHELD_NOTICE, source_label
from cee.ask import STAGES, Result, ask
from cee.config import entities_config, settings, vectors_enabled
from cee.feedback import HELPFUL, NOT_HELPFUL, save_feedback

BEHAVIOR_TEXT = {
    "answer": "Answer",
    "answer_with_boundary": "Answer (evidence only; the judgement is yours)",
    "gap_with_adjacent": "Not in the corpus",
    "refuse": "No evidence",
    "incomplete": "Incomplete",   # #247: an extraction failed and no firm holds the asked figure (code-built)
}


# One plain sentence under the heading, so a first-time reader knows what kind of answer this is.
BEHAVIOR_HELP = {
    "answer": "Each numbered point below comes from a stored document; click its code to read the passage.",
    "answer_with_boundary": "These are the facts on record. Deciding what they mean for your firm is left to you.",
    "gap_with_adjacent": "The stored documents do not answer this directly. Anything close is shown "
                         "below and marked as adjacent; the box says what is missing.",
    "refuse": "Nothing in the stored documents answers this. That is a valid result, not an error: "
              "the box below says what is missing and where it could come from.",
    "incomplete": "Part of the evidence could not be extracted, so nothing is concluded about it. "
                  "The warning below names the firms; anything close is marked as adjacent.",
}
FILTERS_HINT = "Filters are on in the sidebar; they may be hiding the evidence. Clear them and ask again."


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}" + ("" if n == 1 else "s")


def footer_firms(query) -> str:
    """Same firms the gap box names (#50); firms we hold nothing for are marked; firms searched
    only on the theme (home-firm theme rule, #205) are marked too."""
    firms = [f if f in query.entities else f"{f} (no documents)" for f in query.firms]
    firms += [f"{f} (on the theme)" for f in getattr(query, "theme_peers", [])]
    return ", ".join(firms) or "none"


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


# The two search modes a user can pick (#128). Plain names only: the UI never says how the
# search works inside. hybrid-norerank is for comparison runs and is not offered.
MODE_LABELS = {"fts": "Exact match", "hybrid": "Smart search"}
MODE_HELP = {"fts": "Finds passages that use the words of your question. Predictable.",
             "hybrid": "Also finds passages that say the same thing in other words. A few seconds slower."}
SMART_OFF = "Smart search is not set up on this computer, so Exact match is used."


def default_mode() -> str:
    mode = settings().retrieval_mode
    return "hybrid" if mode.startswith("hybrid") else "fts"


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, MODE_LABELS["hybrid"] if mode.startswith("hybrid") else mode)


def search_mode_sidebar() -> str:
    """Exact match / Smart search switch (#128); default from RETRIEVAL_MODE. With the optional
    vectors module off, Smart search cannot run: the switch is locked on Exact match."""
    smart_ok = vectors_enabled()
    with st.sidebar:
        st.markdown("**Search mode**")
        modes = list(MODE_LABELS)
        mode = st.radio("Search mode", modes, index=modes.index(default_mode() if smart_ok else "fts"),
                        format_func=MODE_LABELS.get, key="search_mode", disabled=not smart_ok,
                        label_visibility="collapsed")
        mode = mode if smart_ok else "fts"
        st.caption(MODE_HELP[mode] if smart_ok else SMART_OFF)
    return mode


def filters_text(f: dict) -> str:
    parts = []
    if f.get("firms"):
        parts.append("firms " + ", ".join(f["firms"]))
    if f.get("date_range"):
        parts.append(f"dates {f['date_range'][0]} to {f['date_range'][1]}")
    if f.get("keywords"):
        parts.append("keywords " + ", ".join(f["keywords"]))
    return "; ".join(parts) or "none"


# Raised by the meaning search when its setup is missing (cee.retrieve.modes / hybrid); matched by
# name so fts mode never imports the hybrid module.
SMART_SETUP_ERRORS = {"HybridUnavailable", "MissingVectors", "RerankerNotCached"}
PLAN_HEADING = "Plan"
EVIDENCE_HEADING = "Evidence so far"
EVIDENCE_HELP = ("Cited passages found while the answer is written; each comes from a stored document. "
                 "The answer below is the complete result.")
# #275: the reduce's claims as they stream, each after the per-claim checks (citation in the matrix, figures,
# dates); replaced by the final answer once every check, gap and caveat is done.
EARLY_HEADING = "Answer (in progress: checks running)"
EARLY_HELP = ("Each point below has passed its citation, figure and date checks. The order may change and "
              "duplicates may be removed when the remaining checks finish; gaps and caveats come with the full answer.")
STALL_TEXT = ("The model stopped sending the answer (no output for {idle:g} s), so this answer was not built. "
              "Nothing partial is shown.")
RETRY_LABEL = "Try again"


def evidence_label(line: dict) -> str:
    """'EVIDENCE - Edward Jones - a1' style label of one evidence line (firm, aspect)."""
    from cee.retrieve.planner import firm_name
    firm = firm_name(line["entity"]) if line.get("entity") else "Research"
    return f"EVIDENCE - {firm} - {line.get('aspect', '')}"


def ask_with_trace(question: str, filters: dict | None = None, mode: str = "fts") -> Result | None:
    """Progress bar + one line per stage while the answer is built (#80). The trace stays on the
    page, collapsed, once the answer is ready; a failed stage is marked and its error shown.
    #272: the plan shows first, then each map call's cited evidence as it lands, then the answer."""
    bar = st.progress(0.0, text="Reading the question")
    plan_slot = st.empty()
    evidence = st.container()
    early = st.empty()   # #275: the streamed claims; emptied when the final answer or a failure is shown
    early_box = {"c": None}
    shown = {"n": 0}
    box = st.status("Building the answer", expanded=True)
    slot = box.empty()
    steps: dict[str, tuple[str, str]] = {}

    def on_event(kind: str, data: dict) -> None:
        if kind == "plan":
            plan_slot.markdown(f"**{PLAN_HEADING}:** {escape(data['text'])}", unsafe_allow_html=True)
            return
        if kind == "claim":
            if early_box["c"] is None:
                early_box["c"] = early.container()
                with early_box["c"]:
                    st.markdown(f"**{EARLY_HEADING}**")
                    st.caption(EARLY_HELP)
            c = data["claim"]
            chips = [(h.chunk_id, h.source_tier, source_label(h), True) for h in data["hits"]]
            with early_box["c"]:
                ui.claim_card(data["n"], c.text, chips, label="CLAIM (CHECKING)")
            return
        if kind != "evidence":
            return
        with evidence:
            if shown["n"] == 0:
                st.markdown(f"**{EVIDENCE_HEADING}**")
                st.caption(EVIDENCE_HELP)
            for line in data["lines"]:
                shown["n"] += 1
                chips = [(h.chunk_id, h.source_tier, source_label(h), True) for h in line["hits"]]
                ui.claim_card(shown["n"], line["text"], chips, label=evidence_label(line))

    def progress(stage: str, state: str, text: str) -> None:
        for internal in ("hybrid-norerank", "hybrid"):  # the trace names the mode the user picked
            text = text.replace(f"({internal})", f"({mode_label(internal)})")
        steps[stage] = (state, text)
        finished = sum(s != "running" for s, _ in steps.values())
        bar.progress(finished / len(STAGES), text=text)
        ui.trace_lines(list(steps.values()), slot)

    start = time.perf_counter()
    try:
        r = ask(question, progress=progress, filters=filters, mode=mode, on_event=on_event)
    except Exception as e:
        bar.empty()
        early.empty()   # #275: no early claim stays on screen without a final answer
        failed = next((t for s, t in steps.values() if s == "failed"), "A step failed")
        box.update(label=failed, state="error", expanded=True)
        from cee.answer.llm import StreamIdle
        if mode != "fts" and type(e).__name__ in SMART_SETUP_ERRORS:
            st.error("Smart search is not fully set up on this computer. Switch to Exact match in the "
                     "sidebar and ask again.")
        elif isinstance(e, StreamIdle):   # #275: a stalled stream; the user may ask again (no automatic retry)
            st.error(STALL_TEXT.format(idle=e.idle_s))
            st.button(RETRY_LABEL, key="retry-ask", on_click=lambda: st.session_state.update(retry_ask=True))
        else:
            st.error(f"The answer could not be built. {type(e).__name__}: {e}")
        return None
    bar.empty()
    early.empty()
    box.update(label=f"How this answer was built: {len(steps)} steps in {time.perf_counter() - start:.1f} s",
               state="complete", expanded=False)
    return r


def render() -> None:
    _ticker()
    mode = search_mode_sidebar()
    filters = filters_sidebar()
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.eyebrow("Evidence, not opinion")
        ui.hero("What is known, and", "where", "it was said.")
        st.caption("Ask a question in plain English about Morgan Stanley, Schwab, Edward Jones, Merrill or "
                   "Raymond James. Every point in the answer links to the stored document it comes from; "
                   "if nothing is stored, the answer says so.")
        question = st.text_input("Question", placeholder="What does Edward Jones's 10-K say about its number of financial advisors?")
        asked = st.button("Ask", type="primary")
        asked = asked or bool(st.session_state.pop("retry_ask", False))   # #275: "Try again" after a stall
    with right:
        s = ui.corpus_stats()
        ui.snapshot_card(s["snapshot"], [("DOCUMENTS", f"{s['docs']:,}"), ("PASSAGES", f"{s['chunks']:,}"),
                                         ("FIRMS", str(s["firms"]))])

    if asked and question.strip():
        r = ask_with_trace(question, filters, mode)
        # Kept for reruns: clicking a feedback control reruns the page, the answer must stay.
        st.session_state["last_answer"] = (r, filters) if r else None
        if r is None:
            return
    last = st.session_state.get("last_answer")
    if not last:
        ui.empty_state("No question yet. Type one above and click Ask; the answer appears here, "
                       "with a link to the source of every point.")
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
    st.markdown(f'<div class="cee-meta">Found with: {mode_label(r.retrieval_mode)}</div>', unsafe_allow_html=True)
    st.caption(BEHAVIOR_HELP[a.behavior])
    if a.incomplete_note:   # #247: shown on any behavior (incomplete, or a boundary answer with a failed extraction)
        st.warning(a.incomplete_note)
    if a.behavior in ("refuse", "gap_with_adjacent") and filters_text(filters) != "none":
        st.info(FILTERS_HINT)
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
        ui.gap_box(g.what, g.suggested_source, g.flags)
    if a.coverage_note:
        ui.coverage_box(a.coverage_note)
    st.markdown(f'<div class="cee-meta">Query #{r.query_id} | search: {mode_label(r.retrieval_mode)} | firms: {footer_firms(r.query)} | '
                f'filters: {escape(filters_text(filters))} | {len(r.hits)} passages found | model: {settings().llm_provider} | LLM called: {a.llm_called}</div>', unsafe_allow_html=True)
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
