"""Demo mode (#299): replay a prepared answer for one of the 30 eval questions in the live Ask layout.

The fixture (src/cee/app/demo/fixture.json) is built once, offline, by scripts/build_demo_fixture.py: evidence cards
from the W12 fts run (docs/results/w12-latency/b-fts/) with the stored chunk text, and one narrative answer per
question. Nothing here calls a model, the retrieval layer or cee.ask.ask: the replay only draws what the fixture holds,
with short waits so the progress bar, the plan, the evidence cards and the answer appear in the live order.
"""
from __future__ import annotations

import difflib
import functools
import json
import os
import re
import time
from html import escape
from pathlib import Path

FIXTURE_PATH = Path(__file__).with_name("fixture.json")
MAX_REPLAY_S = 5.0          # the whole replay, Ask to the full answer (issue #299)
STAGE_BUDGET_S = 3.6        # the fixture's stage seconds add up to this (typical 3-4 s)
MATCH_CUTOFF = 0.6
NO_MATCH_TEXT = ("Demo mode answers the prepared question set only: the 30 evaluation questions. "
                 "Pick one from the list, or type one of them (close wording is matched).")
DEMO_CAPTION = ("Demo mode: a prepared answer is replayed. No model is called and nothing is searched; "
                "every citation still opens the stored passage.")
EVIDENCE_HEADING = "Evidence so far"
EVIDENCE_FINAL_HEADING = "Evidence"
PLAN_HEADING = "Plan"
STOPWORDS = {"the", "and", "for", "what", "how", "has", "have", "its", "their", "with", "about", "does", "did", "each",
             "are", "is", "of", "in", "on", "to", "a", "an", "do", "these", "five", "this", "that", "who", "which"}

CITE_RE = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
QUARTER_RE = re.compile(r"(?<![\w.])[1-4]Q\s?(\d{4}|\d{2})(?!\d)")
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")


# ---------- switch ----------

def demo_default(query_params=None) -> bool:
    """On when the URL has ?demo=1 or the environment has CEE_DEMO=1 (the launch scripts set it)."""
    on = ("1", "true", "on", "yes")
    qp = query_params.get("demo") if query_params is not None else None
    return str(qp or "").strip().lower() in on or os.getenv("CEE_DEMO", "").strip().lower() in on


# ---------- fixture ----------

@functools.lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_fixture(path: Path | str | None = None) -> dict:
    """The fixture, cached by path and modification time (a rebuilt fixture is picked up without a restart)."""
    p = Path(path or FIXTURE_PATH)
    return _load(str(p), p.stat().st_mtime)


def entries(fixture: dict | None = None) -> list[dict]:
    return list((fixture or load_fixture())["questions"])


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", str(text).casefold()).split())


def _words(text: str) -> set[str]:
    return {w for w in _norm(text).split() if len(w) > 2 and w not in STOPWORDS}


def match(question: str, fixture: dict | None = None, cutoff: float = MATCH_CUTOFF) -> dict | None:
    """The prepared entry for a typed question: an id ("Q4"), the exact text, else the closest text. Close means a
    difflib ratio >= cutoff, or (two or more content words typed) at least that share of the typed words in the
    question. None when nothing is close (the page then says the demo answers the prepared set only)."""
    text = (question or "").strip()
    if not text:
        return None
    qs = entries(fixture)
    by_id = {e["id"].casefold(): e for e in qs}
    if text.casefold() in by_id:
        return by_id[text.casefold()]
    norm = _norm(text)
    for e in qs:
        if _norm(e["text"]) == norm:
            return e
    typed = _words(text)
    best, best_score = None, 0.0
    for e in qs:
        ratio = difflib.SequenceMatcher(None, norm, _norm(e["text"])).ratio()
        overlap = len(typed & _words(e["text"])) / len(typed) if len(typed) >= 2 else 0.0
        score = max(ratio, overlap) + ratio / 100   # the ratio breaks ties between full overlaps
        if score > best_score:
            best, best_score = e, score
    return best if best_score >= cutoff else None


# ---------- checks (the builder and the tests use the same ones) ----------

def cited_numbers(answer_md: str) -> list[int]:
    """Every card number cited as [n] or [n, m] in the answer, in order."""
    out: list[int] = []
    for m in CITE_RE.finditer(answer_md or ""):
        out += [int(x) for x in re.split(r"\s*[,;]\s*", m.group(1))]
    return out


def bad_citations(entry: dict) -> list[int]:
    """Cited numbers that are not a card of this entry."""
    n = len(entry.get("cards") or [])
    return [k for k in cited_numbers(entry.get("answer_md", "")) if not 1 <= k <= n]


def _numbers(text: str) -> set[str]:
    out = set()
    for m in NUMBER_RE.finditer(text or ""):
        v = m.group(0).replace(",", "").rstrip(".")
        if "." in v:
            v = v.rstrip("0").rstrip(".")
        out.add(v.lstrip("0") or "0")
    return out


def card_text(entry: dict) -> str:
    """Everything the answer may take a figure from: the question, the cards (evidence line, quote, passage, source
    label) and the code's caveats and gaps."""
    parts = [entry.get("text", "")]
    for c in entry.get("cards") or []:
        parts += [c.get("label", ""), c.get("text", ""), c.get("quote", ""), c.get("passage", ""),
                  c.get("source_label", ""), c.get("differs_because", "")]
    parts += list(entry.get("caveats") or [])
    parts += [g.get("what", "") for g in entry.get("gaps") or []]
    return "\n".join(parts)


def unmatched_numbers(entry: dict) -> list[str]:
    """Numbers in the answer (citation markers left out) that appear nowhere in the question's cards (ground rule 4:
    no figure that is not traceable). A cheap code check: a figure must be copied, never computed or recalled."""
    body = CITE_RE.sub(" ", entry.get("answer_md", ""))
    body = re.sub(r"(?m)^#+.*$", " ", body)   # headings carry no figures of their own
    # "3Q25" / "3Q 2025": a quarter named from the source's date; its year must still be in the cards
    body = QUARTER_RE.sub(lambda m: " " + (m.group(1) if len(m.group(1)) == 4 else "20" + m.group(1)), body)
    allowed = _numbers(card_text(entry))
    return sorted(_numbers(body) - allowed, key=lambda v: (len(v), v))


# ---------- drawing ----------

_sleep = time.sleep

def answer_html(answer_md: str) -> str:
    """The answer's markdown with each [n] turned into a footnote link to evidence card n (#cee-ev-n), as live.
    Model text is escaped first; $ would start LaTeX in st.markdown (#99), so it becomes an entity."""
    from cee.app.components import EVIDENCE_ANCHOR
    text = escape(answer_md or "", quote=False).replace("$", "&#36;")

    def link(m: re.Match) -> str:
        nums = [int(x) for x in re.split(r"\s*[,;]\s*", m.group(1))]
        links = "".join(f'<a href="#{EVIDENCE_ANCHOR}{n}" title="Evidence card {n}">[{n}]</a>' for n in nums)
        return f'<sup class="cee-fn">{links}</sup>'
    return CITE_RE.sub(link, text)


def _hits(card: dict) -> list:
    from cee.retrieve.fts import Hit
    out = []
    for h in card.get("hits") or []:
        out.append(Hit(chunk_id=h["chunk_id"], doc_id=h.get("doc_id", ""), entity_id=h.get("entity_id"),
                       segment=h.get("segment"), doc_type=h.get("doc_type", ""), source_tier=h.get("source_tier") or 0,
                       published_at=h.get("published_at") or "", period_end=h.get("period_end"),
                       section=h.get("section"), page=h.get("page"), rank=0.0, text="",
                       date_basis=h.get("date_basis") or "source"))
    return out


def live_card(card: dict) -> dict:
    """A fixture card in the shape the live page draws ({label, text, hits})."""
    return {"label": card["label"], "text": card["text"], "hits": _hits(card)}


def evidence_list(entry: dict) -> None:
    import streamlit as st
    cards = entry.get("cards") or []
    if not cards:
        return
    st.markdown(f"**{EVIDENCE_FINAL_HEADING}**")
    st.caption("Every passage the answer cites, each from a stored document; footnote [n] in the answer opens card n.")
    from cee.answer.validate import source_label

    from cee.app import components as ui
    for n, card in enumerate(cards, start=1):   # as the live card, plus why an adjacent card differs
        chips = [(h.chunk_id, h.source_tier, source_label(h), True) for h in _hits(card)]
        ui.claim_card(n, card["text"], chips, label=card["label"], note=card.get("differs_because") or "",
                      anchor=True)


def answer_body(entry: dict) -> None:
    """The prepared answer: behavior heading, the narrative with [n] footnotes, then the code's caveats and gaps."""
    import streamlit as st

    from cee.app import components as ui
    from cee.app.views.ask_page import BEHAVIOR_HELP, BEHAVIOR_TEXT
    behavior = entry.get("behavior") or "answer"
    ui.behavior_header(BEHAVIOR_TEXT.get(behavior, "Answer"), behavior)
    st.caption(BEHAVIOR_HELP.get(behavior, ""))
    with st.container(key="cee-demo-answer"):   # styled like the live answer (components.CSS, .st-key-cee-demo-answer)
        st.markdown(answer_html(entry.get("answer_md", "")), unsafe_allow_html=True)
    for cav in entry.get("caveats") or []:
        ui.caveat_box(cav)
    for g in entry.get("gaps") or []:
        ui.gap_box(g.get("what", ""), g.get("suggested_source", ""), [])


def footer(entry: dict, fixture: dict | None = None, seconds: float | None = None) -> None:
    import streamlit as st
    fx = fixture or {}
    took = f" | replayed in {seconds:.1f} s" if seconds is not None else ""
    st.markdown(f'<div class="cee-meta">Demo mode: prepared answer {escape(entry["id"])} | '
                f'{len(entry.get("cards") or [])} evidence cards | written by {escape(str(fx.get("model", "")))} '
                f'on {escape(str(fx.get("built_at", ""))[:10])} from snapshot {escape(str(fx.get("snapshot", "")))}'
                f'{took} | model calls now: 0</div>', unsafe_allow_html=True)


def show(entry: dict, fixture: dict | None = None, seconds: float | None = None) -> None:
    """A replayed answer on a later rerun: answer, boxes, evidence list and footer. No waiting, no call."""
    if entry.get("plan_text"):
        import streamlit as st
        st.markdown(f"**{PLAN_HEADING}:** {escape(entry['plan_text'])}", unsafe_allow_html=True)
    answer_body(entry)
    evidence_list(entry)
    footer(entry, fixture, seconds)


def replay(entry: dict, fixture: dict | None = None, sleep=None) -> float:
    """Draw the prepared run in the slots the live flow uses: progress bar and step trace, the plan, the evidence
    cards one by one (during the extract stage), then the answer above them and the full evidence list. Returns the
    seconds from start to the full answer. `sleep` is injectable (default: _sleep, which tests may patch)."""
    sleep = sleep or _sleep
    import streamlit as st

    from cee.app import components as ui
    from cee.app.views.ask_page import _draw_cards
    start = time.perf_counter()
    stages = entry.get("stages") or []
    cards = [live_card(c) for c in entry.get("cards") or []]
    bar = st.progress(0.0, text="Reading the question")
    plan_slot = st.empty()
    answer_slot = st.empty()
    ev_slot = st.empty()
    evidence = ev_slot.container()
    box = st.status("Building the answer (demo replay)", expanded=True)
    slot = box.empty()
    steps: dict[str, tuple[str, str]] = {}
    total = len(stages) or 1
    for i, s in enumerate(stages):
        steps[s["stage"]] = ("running", s["text"])
        bar.progress(min(1.0, i / total), text=s["text"])
        ui.trace_lines(list(steps.values()), slot)
        wait = float(s.get("seconds") or 0.0)
        if s["stage"] == "extract" and cards:   # the cards land one by one while the extract stage runs
            step = wait / len(cards)
            for k in range(len(cards)):
                sleep(step)
                _draw_cards(evidence, cards[:k + 1], k)
        else:
            sleep(wait)
        steps[s["stage"]] = ("done", s["text"])
        if s["stage"] == "decompose" and entry.get("plan_text"):
            plan_slot.markdown(f"**{PLAN_HEADING}:** {escape(entry['plan_text'])}", unsafe_allow_html=True)
        if s["stage"] == "synthesize":   # the answer shows once, above the evidence (live layout, #291)
            with answer_slot.container():
                answer_body(entry)
        ui.trace_lines(list(steps.values()), slot)
    if not any(s["stage"] == "extract" for s in stages):
        _draw_cards(evidence, cards, 0)
    if not any(s["stage"] == "synthesize" for s in stages):
        with answer_slot.container():
            answer_body(entry)
    with ev_slot.container():
        evidence_list(entry)
    bar.empty()
    took = time.perf_counter() - start
    box.update(label=f"How this answer was built: {len(steps)} steps in {took:.1f} s (demo replay, prepared answer)",
               state="complete", expanded=False)
    footer(entry, fixture, took)
    return took
