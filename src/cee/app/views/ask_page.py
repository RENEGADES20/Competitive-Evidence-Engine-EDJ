"""Ask page: question box, answer with citation chips, caveats and gaps (always visible)."""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from html import escape

import streamlit as st

from cee.app import components as ui
from cee.answer.cancel import CancelToken
from cee.answer.runcache import RunCache
from cee.answer.validate import WITHHELD_NOTICE, source_label
from cee.ask import STAGES, Result, ask
from cee.config import entities_config, settings
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
    "answer": "Each point ends with footnotes [n]: click one to jump to the evidence card it comes from; "
              "the card links to the stored passage.",
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


def filters_text(f: dict) -> str:
    parts = []
    if f.get("firms"):
        parts.append("firms " + ", ".join(f["firms"]))
    if f.get("date_range"):
        parts.append(f"dates {f['date_range'][0]} to {f['date_range'][1]}")
    if f.get("keywords"):
        parts.append("keywords " + ", ".join(f["keywords"]))
    return "; ".join(parts) or "none"


PLAN_HEADING = "Plan"
EVIDENCE_HEADING = "Evidence so far"
EVIDENCE_HELP = ("Cited passages found while the answer is written; each comes from a stored document. "
                 "The answer appears above them once its checks are done.")
# #291: after the run (and on every rerun) the full evidence list sits under the answer; footnote [n] -> card n
EVIDENCE_FINAL_HEADING = "Evidence"
EVIDENCE_FINAL_HELP = ("Every passage the answer cites, each from a stored document; footnote [n] in the answer "
                       "opens card n. A SOURCE card is a cited passage with no extracted evidence line.")
SOURCE_LABEL = "SOURCE"
EXCERPT_CHARS = 240
# #275: the reduce's claims as they stream, each after the per-claim checks (citation in the matrix, figures,
# dates); replaced by the final answer once every check, gap and caveat is done. #291: drawn above the evidence.
EARLY_HEADING = "Answer (in progress: checks running)"
EARLY_HELP = ("Each point has passed its citation, figure and date checks. The order may change and "
              "duplicates may be removed when the remaining checks finish; gaps and caveats come with the full answer.")
STALL_TEXT = ("The model stopped sending the answer (no output for {idle:g} s), so this answer was not built. "
              "Nothing partial is shown.")
# #277: Stop while the answer is built; Retry after a stop or any failure (replaces #275's stall-only "Try again",
# same key and flag). One click = one attempt; finished calls are reused from the run cache.
STOP_LABEL = "Stop"
RETRY_LABEL = "Retry"
RETRY_FAILED_LABEL = "Retry the failed calls"
STOPPED_HEADING = "Stopped while {stage}"
STOPPED_TEXT = ("The answer was not built. The evidence found before the stop is below; each item cites a stored "
                "passage. Retry asks again with the same question and filters; calls that finished are reused.")
PAGE_CHANGED_TEXT = "The run stopped because the page changed while the answer was being built."
WAITING_TEXT = "The previous call is still finishing; Retry is available once it has ended."
FAILED_RETRY_HELP = "Retry asks again with the same question and filters; calls that finished are reused."
ASK_BUSY_TEXT = ("Finishing the stopped call; Ask is available again once it has ended "
                 "(so no call runs twice and nothing is paid twice).")
RUNNING_TEXT = "Working for {s:.0f} s. Stop ends the run; the evidence found so far stays on the page."
STAGE_WORDS = {"resolve": "reading the question", "decompose": "planning the search", "search": "searching",
               "extract": "extracting evidence", "research": "re-searching", "synthesize": "writing the answer",
               "check": "checking citations", "caveats": "adding caveats and gaps", "log": "saving the query"}
PUMP_S = 0.2   # #277: how often the script thread draws the worker's messages (and yields to a click)
GRACE_S = 2.0  # #277: how long the Stopped view waits for the stopped worker before showing "still finishing"


def evidence_label(line: dict) -> str:
    """'EVIDENCE - Edward Jones - a1' style label of one evidence line (firm, aspect)."""
    from cee.retrieve.planner import firm_name
    firm = firm_name(line["entity"]) if line.get("entity") else "Research"
    return f"EVIDENCE - {firm} - {line.get('aspect', '')}"


def list_form(query, aspects) -> bool:
    """#291: a list-form answer (one item per claim, with why-lines) is drawn as a numbered list; any other answer as
    one paragraph. #292: the rule is reduce.list_form, the one the reduce wrote the answer by (streamed and final)."""
    from cee.answer.reduce import list_form as form
    return form(aspects, query)


def answer_aspects(r: Result) -> list:
    if r.matrix is not None:
        return list(getattr(r.matrix, "aspects", []) or [])
    return list(r.plan.aspects) if r.plan is not None else []


def _excerpt(h) -> str:
    text = " ".join(str(getattr(h, "text", "") or "").split())
    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + " ..."


def line_card(line: dict) -> dict:
    return {"label": evidence_label(line), "text": line["text"], "hits": list(line["hits"])}


def footnote_items(cards: list[dict], claims, by_id: dict) -> list[dict]:
    """#291: one answer item per claim with its footnotes: for each cited chunk id in the retrieved set (by_id), the
    first card that cites it; a cited chunk no card cites gets a SOURCE card appended to `cards` (so every footnote
    resolves, ground rule 1). An id outside the retrieved set gets no footnote and no card: it stays a flagged,
    unlinked chip (never a composed source). Mutates `cards`."""
    first: dict[str, int] = {}
    for n, c in enumerate(cards, start=1):
        for h in c["hits"]:
            first.setdefault(h.chunk_id, n)
    items = []
    for c in claims:
        notes: list[int] = []
        unlinked: list[str] = []
        for cid in c.chunk_ids:
            h = by_id.get(cid)
            if h is None:
                unlinked.append(cid)
                continue
            if cid not in first:
                cards.append({"label": SOURCE_LABEL, "text": _excerpt(h), "hits": [h]})
                first[cid] = len(cards)
            if first[cid] not in notes:
                notes.append(first[cid])
        items.append({"text": c.text, "footnotes": notes, "unlinked": unlinked, "flags": list(c.flags)})
    return items


def evidence_cards(lines: list[dict], claims, hits) -> tuple[list[dict], list[dict]]:
    """#291: (cards, items): the evidence cards (the run's evidence lines in order, then the extra SOURCE cards) and
    the answer items with footnotes into them. No evidence lines (MAP=off, a code-built answer, an answer from the
    run cache): the cards are the answer's cited chunks."""
    cards = [line_card(line) for line in lines]
    return cards, footnote_items(cards, claims, {h.chunk_id: h for h in hits})


@dataclass
class Run:
    """#277: one attempt of the Ask page, held in st.session_state["ask_run"]. The worker thread never touches
    Streamlit; it writes only to the queue and the run cache. The script thread (the pump) fills the rest."""
    question: str
    filters: dict
    cache: RunCache
    token: CancelToken = field(default_factory=CancelToken)
    thread: threading.Thread | None = None
    status: str = "running"   # running | done | stopped | failed
    stage: str | None = None
    stop_clicked: bool = False
    plan_text: str | None = None
    evidence: list[dict] = field(default_factory=list)
    steps: dict = field(default_factory=dict)
    error: str | None = None
    idle_s: float | None = None
    result: Result | None = None

    def alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


STOP_KEY = "stop-ask"


def stop_clicked(e: BaseException) -> bool:
    """#277: whether the rerun that interrupted the pump was caused by the Stop button: Streamlit's rerun exception
    carries the new widget states, and the clicked button's state holds trigger_value true (its id ends with the
    user key). Any other interruption (a filter, a new Ask, the tab closed) reads False ("page")."""
    states = getattr(getattr(e, "rerun_data", None), "widget_states", None)
    for w in getattr(states, "widgets", None) or []:
        try:
            fired = w.WhichOneof("value") == "trigger_value" and bool(w.trigger_value)
        except (AttributeError, ValueError):
            fired = bool(getattr(w, "trigger_value", False))
        if fired and str(getattr(w, "id", "")).endswith(STOP_KEY):
            return True
    return False


def _on_stop() -> None:   # runs at the start of the rerun the Stop click causes (the pump already set the token)
    run = st.session_state.get("ask_run")
    if run is not None:
        run.stop_clicked = True
        run.token.set("stop", run.stage)


def _on_retry() -> None:
    st.session_state["retry_ask"] = True


def _running_stage(steps: dict) -> str | None:
    return next((s for s, (state, _) in reversed(list(steps.items())) if state == "running"), None)


def _start_worker(run: Run, q: queue.Queue) -> None:
    """The answer flow in a worker thread (#277): every progress line and event goes on the queue; the end is
    ("done", result) or ("error", exception). Never touches st."""
    def work() -> None:
        try:
            r = ask(run.question, progress=lambda *a: q.put(("progress", a)), filters=run.filters,
                    on_event=lambda kind, data: q.put(("event", (kind, data))), token=run.token, cache=run.cache)
            q.put(("done", r))
        except BaseException as e:   # noqa: BLE001 - cancel.Cancelled included; the pump decides what to show
            q.put(("error", e))

    run.thread = threading.Thread(target=work, daemon=True, name="cee-ask")
    run.thread.start()


def ask_with_trace(question: str, filters: dict | None = None, cache: RunCache | None = None) -> Result | None:
    """Progress bar + one line per stage while the answer is built (#80). The trace stays on the
    page, collapsed, once the answer is ready; a failed stage is marked and its error shown.
    #272: the plan shows first, then each map call's cited evidence as it lands, then the answer.
    #277: the flow runs in a worker thread; this (script) thread pumps its messages onto the page and shows a
    Stop button. A click (Stop, or any widget) makes Streamlit raise its rerun exception at the pump's next draw:
    the pump sets the run's cancel token, marks the run stopped and lets the rerun draw the Stopped view.
    `cache`: Retry passes the earlier attempt's run cache (finished calls reused); None starts a new one."""
    filters = dict(filters or {})
    run = Run(question, filters, cache if cache is not None else RunCache(question, filters))
    st.session_state["ask_run"] = run   # replaced before the new worker starts
    bar = st.progress(0.0, text="Reading the question")
    plan_slot = st.empty()
    # #291: the answer's slot sits between the plan line and the evidence; st.empty() takes no height until the
    # first checked claim streams in, so nothing is reserved. The final answer replaces the streamed claims there.
    answer_slot = st.empty()
    ev_slot = st.empty()
    evidence = ev_slot.container()
    stream: dict = {"cards": [], "claims": [], "by_id": {}, "query": None, "aspects": []}
    stop_slot = st.empty()
    elapsed = st.empty()
    box = st.status("Building the answer", expanded=True)
    slot = box.empty()
    steps = run.steps

    def on_event(kind: str, data: dict) -> None:
        if kind == "plan":
            run.plan_text = data["text"]
            stream["query"], stream["aspects"] = data.get("query"), list(getattr(data.get("plan"), "aspects", []))
            plan_slot.markdown(f"**{PLAN_HEADING}:** {escape(data['text'])}", unsafe_allow_html=True)
            return
        if kind == "claim":   # #291: sentence by sentence into the answer slot; only the new one fades in
            stream["claims"].append(data["claim"])
            stream["by_id"].update({h.chunk_id: h for h in data["hits"]})
            cards = stream["cards"]
            drawn = len(cards)
            items = footnote_items(cards, stream["claims"], stream["by_id"])
            _draw_cards(evidence, cards, drawn)
            with answer_slot.container():
                st.markdown(f"**{EARLY_HEADING}**")
                st.caption(EARLY_HELP)
                ui.answer_block(items, list_form(stream["query"], stream["aspects"]), fade_from=len(items) - 1)
            return
        if kind != "evidence":
            return
        drawn = len(stream["cards"])
        for line in data["lines"]:
            run.evidence.append(line)
            stream["cards"].append(line_card(line))
            stream["by_id"].update({h.chunk_id: h for h in line["hits"]})
        _draw_cards(evidence, stream["cards"], drawn)

    def progress(stage: str, state: str, text: str) -> None:
        steps[stage] = (state, text)
        run.stage = _running_stage(steps) or run.stage
        finished = sum(s != "running" for s, _ in steps.values())
        bar.progress(min(1.0, finished / len(STAGES)), text=text)
        ui.trace_lines(list(steps.values()), slot)

    start = time.perf_counter()
    stop_slot.button(STOP_LABEL, key=STOP_KEY, on_click=_on_stop)
    q: queue.Queue = queue.Queue()
    _start_worker(run, q)
    end: tuple | None = None
    try:
        tick = 0.0
        while end is None:
            try:
                kind, payload = q.get(timeout=PUMP_S)
            except queue.Empty:
                kind, payload = None, None
            if kind == "progress":
                progress(*payload)
            elif kind == "event":
                on_event(*payload)
            elif kind in ("done", "error"):
                end = (kind, payload)
            now = time.perf_counter()
            if end is None and now - tick >= 1.0:   # a draw each second: Streamlit's yield point for a click
                tick = now
                elapsed.caption(RUNNING_TEXT.format(s=now - start))
                st.session_state.get("ask_run")   # a session-state read is a yield point too
    except BaseException as e:   # Streamlit's rerun / stop exception: Stop or another click interrupted the script
        stop = stop_clicked(e)
        run.stop_clicked = run.stop_clicked or stop
        run.token.set("stop" if stop else "page", run.stage)
        run.status = "stopped"
        raise
    bar.empty()
    stop_slot.empty()
    elapsed.empty()
    kind, payload = end
    if kind == "done" and not run.token.is_set():
        run.status, run.result = "done", payload
        # #291: the final answer replaces the streamed claims in the same slot; the evidence slot becomes the full
        # list (with the SOURCE cards the final answer needs); the footer and feedback follow (render).
        cards, items = evidence_cards(run.evidence, payload.answer.claims, payload.hits)
        with answer_slot.container():
            answer_body(payload, filters, items, fade=not stream["claims"])
        with ev_slot.container():
            evidence_list(cards)
        box.update(label=f"How this answer was built: {len(steps)} steps in {time.perf_counter() - start:.1f} s",
                   state="complete", expanded=False)
        return payload
    answer_slot.empty()   # #275 / #277 rule 1: no streamed claim stays on screen without a final answer
    from cee.answer.cancel import Cancelled
    from cee.answer.llm import StreamIdle
    if kind == "done" or isinstance(payload, Cancelled):   # stopped (a late result is never shown)
        run.status = "stopped"
        box.update(label=STOPPED_HEADING.format(stage=STAGE_WORDS.get(run.stage or "", "building the answer")),
                   state="error", expanded=False)
        _stopped_note(run)
        _retry_button(run)
        return None
    run.status = "failed"
    failed = next((t for s, t in steps.values() if s == "failed"), "A step failed")
    box.update(label=failed, state="error", expanded=True)
    if isinstance(payload, StreamIdle):   # #275: a stalled stream; the user may ask again (no automatic retry)
        run.idle_s = payload.idle_s
        run.error = STALL_TEXT.format(idle=payload.idle_s)
    else:
        run.error = f"The answer could not be built. {type(payload).__name__}: {payload}"
    st.error(run.error)
    _retry_button(run)
    return None


def _card(n: int, card: dict) -> None:
    chips = [(h.chunk_id, h.source_tier, source_label(h), True) for h in card["hits"]]
    ui.claim_card(n, card["text"], chips, label=card["label"], anchor=True)


def _evidence_card(n: int, line: dict) -> None:
    _card(n, line_card(line))


def _draw_cards(where, cards: list[dict], drawn: int) -> None:
    """Append cards[drawn:] to the running page's evidence container (the heading before the first card)."""
    with where:
        if drawn == 0 and cards:
            st.markdown(f"**{EVIDENCE_HEADING}**")
            st.caption(EVIDENCE_HELP)
        for n in range(drawn + 1, len(cards) + 1):
            _card(n, cards[n - 1])


def evidence_list(cards: list[dict]) -> None:
    """#291: the full evidence list under a finished answer (first draw and every rerun)."""
    if not cards:
        return
    st.markdown(f"**{EVIDENCE_FINAL_HEADING}**")
    st.caption(EVIDENCE_FINAL_HELP)
    for n, card in enumerate(cards, start=1):
        _card(n, card)


def _stopped_note(run: Run) -> None:
    st.warning(f"**{STOPPED_HEADING.format(stage=STAGE_WORDS.get(run.stage or '', 'building the answer'))}.** "
               + STOPPED_TEXT + ("" if run.stop_clicked or run.token.reason == "stop" else " " + PAGE_CHANGED_TEXT))


def _retry_button(run: Run, label: str = RETRY_LABEL) -> None:
    """#277: Retry (key "retry-ask", sets session_state.retry_ask; one click = one attempt). While the previous
    worker is still finishing (a call that cannot be cut), a disabled button and a note, refreshed each second
    by a fragment; it reruns the page once the worker has ended. Never starts a run and draws no Stop button.
    The usual case first waits up to GRACE_S for the worker: a cut call and the stopped row's log end in ~1 s."""
    if run.alive():
        run.thread.join(GRACE_S)
    if run.alive():
        _wait_for_worker()
        return
    st.button(label, key="retry-ask", on_click=_on_retry, help=FAILED_RETRY_HELP)


@st.fragment(run_every=1.0)
def _wait_for_worker() -> None:
    run = st.session_state.get("ask_run")
    if run is None or not run.alive():
        st.rerun()
    st.button(RETRY_LABEL, key="retry-wait", disabled=True)
    st.caption(WAITING_TEXT)


def show_halted(run: Run) -> None:
    """#277: the page of a stopped or failed run, on any later rerun (the Stop click's rerun included): the plan
    line, the note, the evidence cards (each code-checked and cited), the trace and Retry. Rule 1: never the
    streamed claims, never a final answer."""
    if run.plan_text:
        st.markdown(f"**{PLAN_HEADING}:** {escape(run.plan_text)}", unsafe_allow_html=True)
    if run.status == "stopped":
        _stopped_note(run)
    else:
        st.error(run.error or "The answer could not be built.")
    _retry_button(run)
    if run.evidence:
        st.markdown(f"**{EVIDENCE_HEADING}**")
        st.caption("Cited passages found before the run ended; each comes from a stored document. "
                   "They are not an answer.")
        for i, line in enumerate(run.evidence, start=1):
            _evidence_card(i, line)
    if run.steps:
        label = (STOPPED_HEADING.format(stage=STAGE_WORDS.get(run.stage or "", "building the answer"))
                 if run.status == "stopped" else "How far the answer got")
        with st.status(label, state="error", expanded=False):
            ui.trace_lines(list(run.steps.values()))


def has_failed_calls(r: Result | None) -> bool:
    """#277: a finished answer with a failed or invalid call (a map cell, or the planner's rule-plan fallback after
    a failed call): Retry the failed calls is offered under it."""
    if r is None:
        return False
    calls = getattr(r.matrix, "calls", None) or []
    plan_failed = r.plan is not None and r.plan.source == "fallback" and bool(r.plan.calls)
    return plan_failed or any(c.get("failed_call") or c.get("invalid") for c in calls)


def render() -> None:
    _ticker()
    filters = filters_sidebar()
    run: Run | None = st.session_state.get("ask_run")
    if run is not None and run.status != "running" and run.alive():
        run.thread.join(GRACE_S)   # the usual case: the stopped worker ends within a second
    # #277: while a stopped run's worker still finishes a call that cannot be cut, Ask (like Retry) starts nothing
    busy = run is not None and run.status != "running" and run.alive()
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.eyebrow("Evidence, not opinion")
        ui.hero("What is known, and", "where", "it was said.")
        st.caption("Ask a question in plain English about Morgan Stanley, Schwab, Edward Jones, Merrill or "
                   "Raymond James. Every point in the answer links to the stored document it comes from; "
                   "if nothing is stored, the answer says so.")
        question = st.text_input("Question", placeholder="What does Edward Jones's 10-K say about its number of financial advisors?")
        asked = st.button("Ask", type="primary", disabled=busy) and not busy
        if busy:
            st.caption(ASK_BUSY_TEXT)
    retry = bool(st.session_state.pop("retry_ask", False))   # #277: Retry (was #275's "Try again")
    with right:
        s = ui.corpus_stats()
        ui.snapshot_card(s["snapshot"], [("DOCUMENTS", f"{s['docs']:,}"), ("PASSAGES", f"{s['chunks']:,}"),
                                         ("FIRMS", str(s["firms"]))])

    fresh = None   # #291: a run that just finished has drawn its answer and evidence already
    if asked and question.strip():
        fresh = ask_with_trace(question, filters)   # a new run and a new run cache
        # Kept for reruns: clicking a feedback control reruns the page, the answer must stay.
        st.session_state["last_answer"] = (fresh, filters) if fresh else None
        if fresh is None:
            return
    elif retry and run is not None and run.status != "running" and not run.alive():
        # #277: one attempt with the saved question and filters; finished calls come from the run cache
        fresh = ask_with_trace(run.question, run.filters, cache=run.cache)
        st.session_state["last_answer"] = (fresh, run.filters) if fresh else None
        if fresh is None:
            return
    elif run is not None and run.status in ("stopped", "failed"):
        show_halted(run)   # the Stop click's rerun included: never starts a run
        return
    last = st.session_state.get("last_answer")
    if not last:
        ui.empty_state("No question yet. Type one above and click Ask; the answer appears here, "
                       "with a link to the source of every point.")
        return
    run = st.session_state.get("ask_run")
    if fresh is not None:
        answer_footer(*last)
    else:   # #291: any rerun draws answer, boxes, the run's evidence list, footer and feedback from session state
        show_answer(*last, evidence=run.evidence if run is not None and run.result is last[0] else None)
    if run is not None and run.status == "done" and run.result is last[0] and has_failed_calls(run.result):
        _retry_button(run, RETRY_FAILED_LABEL)


def _chips(r: Result, chunk_ids) -> list[tuple]:
    """One chip per citation: its own source label and tier. An id that is not in the
    retrieved set is shown, flagged, and not linked (no composed source)."""
    by_id = {h.chunk_id: h for h in r.hits}
    out = []
    for cid in chunk_ids:
        h = by_id.get(cid)
        out.append((cid, h.source_tier, source_label(h), True) if h
                   else (cid, None, "not in the retrieved set", False))
    return out


def answer_body(r: Result, filters: dict, items: list[dict], fade: bool = False) -> None:
    """#291: the answer (a paragraph with footnotes, or a numbered list for a window / recency answer), then the
    adjacent items, withheld notice, caveats, gaps and coverage note (never collapsed)."""
    a = r.answer
    ui.behavior_header(BEHAVIOR_TEXT[a.behavior], a.behavior)
    st.caption(BEHAVIOR_HELP[a.behavior])
    if a.incomplete_note:   # #247: shown on any behavior (incomplete, or a boundary answer with a failed extraction)
        st.warning(a.incomplete_note)
    if a.behavior in ("refuse", "gap_with_adjacent") and filters_text(filters) != "none":
        st.info(FILTERS_HINT)
    if items:
        ui.answer_block(items, list_form(r.query, answer_aspects(r)), fade_from=None, block_fade=fade)
    for i, c in enumerate(a.adjacent, start=1):
        ui.claim_card(i, c.text, _chips(r, c.chunk_ids), "", c.flags,
                      label="ADJACENT EVIDENCE", note=c.differs_because)
    if a.withheld:
        ui.withheld_box(WITHHELD_NOTICE)
    for cav in a.caveats:
        ui.caveat_box(cav)
    for g in a.gaps:
        ui.gap_box(g.what, g.suggested_source, g.flags)
    if a.coverage_note:
        ui.coverage_box(a.coverage_note)


def answer_footer(r: Result, filters: dict) -> None:
    a = r.answer
    st.markdown(f'<div class="cee-meta">Query #{r.query_id} | firms: {footer_firms(r.query)} | '
                f'filters: {escape(filters_text(filters))} | {len(r.hits)} passages found | model: {settings().llm_provider} | LLM called: {a.llm_called}</div>', unsafe_allow_html=True)
    feedback_form(r.query_id)


def show_answer(r: Result, filters: dict, evidence: list[dict] | None = None) -> None:
    """#291: a finished answer from session state: answer, boxes, the full evidence list (the run's evidence lines
    plus SOURCE cards; without evidence lines, the answer's cited chunks), footer and feedback. No run, no call."""
    cards, items = evidence_cards(evidence or [], r.answer.claims, r.hits)
    answer_body(r, filters, items)
    evidence_list(cards)
    answer_footer(r, filters)


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
