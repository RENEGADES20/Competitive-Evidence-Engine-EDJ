# Demo mode: replay prepared answers

With the muted "Demo" toggle on (bottom of the sidebar; on from the start with `?demo=1` or `CEE_DEMO=1`), the Ask
page answers only the 30 prepared eval questions. A dropdown fills the question box; Ask replays the prepared run in
the live layout and order: progress bar and step trace, the plan line, the evidence cards one by one, then a
narrative answer above the evidence whose `[n]` footnotes jump to the cards, with the code's caveat and gap boxes.
The replay takes 5 s or less. No model is called, nothing is searched and no `query_log` row is written. A question
that is not prepared gets "... prepared question set only ...". Spec: `specs/ui.md` "Demo mode (#299)".

## Sub-features

- `demo-toggle`: the toggle sits below the filters, muted (opacity < 1), on with `?demo=1`.
- `demo-pick`: choosing "Q4 · ..." in the "Prepared question" dropdown puts its text in the question box.
- `demo-progress`: during the replay the progress bar and the plan line show before any answer; the evidence cards
  ("Evidence so far") land before the answer.
- `demo-answer`: the final answer's `[n]` links (`.st-key-cee-demo-answer a[href^="#cee-ev-"]`) each have their
  card (`id="cee-ev-n"`); clicking one jumps to it; the card count equals the fixture's.
- `demo-timing`: Ask to the full answer (the footer "model calls now: 0") in 5 s or less, measured in the browser.
- `demo-trap`: Q4 (trap) keeps to Merrill and shows the "GWIM is not Merrill" caveat; Q30 is "Not in the corpus"
  and opens by saying Merrill's standalone profitability is not reported.
- `demo-no-match`: an unprepared question gets the polite message and no answer.
- `demo-off`: toggling Demo off gives the live Ask page; the live flow itself is covered by `ask-progress`.
- `demo-no-calls`: `query_log` has no new row after the whole feature (the answer flow never ran).

## How to get to it (user POV)

- Open the app with `?demo=1` (or start it with `scripts/run_demo.ps1` / `scripts/run_demo.sh`), or switch on the
  "Demo" toggle at the bottom of the sidebar. Pick a question from "Prepared question" and click Ask.

## Driving it

Preconditions: baseline; `src/cee/app/demo/fixture.json` present (it is committed).

- Open `<base>?demo=1`, wait for "Demo mode: a prepared answer is replayed". The toggle (`.st-key-cee-demo`) is
  checked, its opacity below 1 and its top below the Keywords box (screenshot).
- Pick Q4 in the dropdown: the box holds Q4's text.
- Click Ask (the driver stores `performance.now()` just before). As soon as the progress bar and "Plan:" show: no
  `.cee-behavior` heading yet (screenshot mid-progress). As soon as a `.cee-claim` card shows: "Evidence so far" and
  still no answer heading (screenshot: evidence before the answer).
- Wait for "model calls now: 0": the seconds since the click are 5 or less; every footnote link has its card; the
  card count matches the fixture (screenshot of the answer). Click the first footnote: `:target` is that card.
- Q4's page shows the caveat "GWIM is not Merrill" (screenshot).
- Pick Q30, Ask: heading "Not in the corpus", the first paragraph says the figure is not reported, 5 s or less
  (screenshot: the decline).
- Type "What is the weather in Paris tomorrow?", Ask: the "prepared question set only" message, no answer heading.
- Click the toggle off: "No question yet" and no dropdown (the live page).
- `query_log` row count in `cee_verify` is unchanged since the start.

## Gotchas

- The verify app runs the mock provider; demo mode never calls it either way.
- The replay draws with short sleeps (about 3.6 s in all), so the driver catches the progress and the evidence
  mid-run without any MOCK_DELAY_S; poll with `wait_for_function`, never a fixed sleep.
- Citation chips on the cards open the stored passage in a new tab (`?chunk=`); `open-citation` covers that page.
- The answers were written once, offline, by Claude Opus (`scripts/build_demo_fixture.py`, raw outputs in
  `.eval-runs/demo-fixture/`); this recipe checks the replay, not the answers' quality.
