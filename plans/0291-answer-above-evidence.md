# 0291 - Ask page: answer above the evidence, footnotes, evidence kept on rerun

Issue: #291    Role: TL    Spec: specs/ui.md, specs/answer-citations.md    Design: none (the issue)

## Goal
The Ask page shows the answer on top: while the reduce streams, its checked claims fade in above the first
evidence card (no reserved blank space before); the final answer replaces them in the same place, as one
paragraph with footnotes `[n]` into the evidence cards below (a numbered list for window / recency answers).
After the run and on every rerun the page draws answer -> boxes -> full evidence list -> footer / feedback
from session state. Page only: Answer JSON, prompts and calls unchanged.

## Files to change
- `src/cee/app/views/ask_page.py` - a zero-height `st.empty()` answer slot between the plan line and the
  evidence; streamed claims go there; the final answer is drawn there; `evidence_cards()` (footnote mapping
  by chunk id, extra `SOURCE` cards); `list_form()`; `show_answer` draws answer, boxes, evidence, footer;
  `render` passes the run's evidence on rerun. #277 stop / retry unchanged.
- `src/cee/app/components.py` - answer paragraph / list HTML with footnote links, card anchors
  (`id="cee-ev-n"`), `:target` highlight, fade-in keyframes with `prefers-reduced-motion`.
- `src/cee/ask.py` - the "plan" event also carries the resolved query (for the list-form choice while
  streaming); nothing else.
- `tests/test_answer_footnotes.py` (new), `tests/test_reduce_stream.py`, `tests/test_stop_retry.py` - mapping,
  list choice, rerun keeps evidence, stopped run shows no answer.
- `.claude/skills/verify-cee/features/ask-answer.md`, `ask-progress.md`, `scripts/verify_cee.py` - recipe and
  driver: answer above the first evidence card, every footnote target exists, Coverage -> Ask round trip.
- `specs/ui.md` - the new answer layout.

## Steps
1. `evidence_cards(lines, answer, hits)`: cards from the run's evidence lines (in order), then one `SOURCE` card
   per cited chunk (claims, in order) that no card cites and that is in the retrieved set; footnotes per claim =
   the first card citing each chunk id. An id outside the retrieved set gets no footnote, only today's flagged,
   unlinked chip. No evidence lines (MAP=off, code-built) -> every cited chunk becomes a SOURCE card.
2. `list_form(query, aspects)`: the question's own window or a recency aspect (`reduce.own_window`, aspect kind).
3. Components: `answer_html(items, list_form, new_index)`; `claim_card(..., anchor=)`; CSS.
4. Ask page: answer slot; streamed claims re-rendered sentence by sentence into the slot (only the new one fades
   in), with the "checks running" caption; stop / failure empties it; final answer into the slot, evidence slot
   redrawn as the full list; footer and feedback after. Rerun: `show_answer(r, filters, evidence)`.
5. Tests, then verify-cee on mock (Q5, Q8, Q24, Q26 + the driver features), recipe, driver, spec.

## Acceptance
- [x] pytest green (CI), with tests for the footnote mapping (card found, extra card added, id outside the
      retrieved set) and the window / recency list choice.
- [x] verify-cee on mock, with screenshots: Q5 (single firm), Q8 (comparison), Q24 (gap_with_adjacent),
      Q26 (window: list form). Each: answer above the first evidence card; every footnote target exists; after
      Coverage -> Ask, answer and evidence both shown.
- [x] A stopped run still shows the evidence and no answer (#277 behaviour unchanged).
- [x] Mock eval fts Q1-Q30 answer JSON identical to main (page-only change).
- [x] 0 paid calls.

## Paid calls
0. Everything runs on `LLM_PROVIDER=mock`; the change is the page layout only.

## Progress log
- 2026-11-23 16:58 - plan written; plan review skipped (no risk item: 0 paid calls, no ADR / schema / corpus change)
- 2026-11-23 17:04 - ask_page / components / ask.py done (the "plan" event also carries the query, for the list form
  while streaming); tests/test_answer_footnotes.py added; local pytest 1200 passed
- 2026-11-23 17:20 - verify-cee ask-layout (new), ask-progress, ask-stop-retry PASS on mock (run
  20261123-170548-47186a3). The empty answer slot is display:none, height 0 (measured in the browser: the gap
  plan line -> "Evidence so far" is the normal 16 px). Mock Q24 answers `answer`, not `gap_with_adjacent` (mock)
- 2026-11-23 17:40 - mock eval (fts, all 35) on the branch and on main: identical answer JSON for Q1-Q30 (and
  Q31-Q35), 33 PASS / 2 FAIL on both; 0 real calls. Full verify-cee run on 46ce139: 12 features PASS (20261123-171554-46ce139)
