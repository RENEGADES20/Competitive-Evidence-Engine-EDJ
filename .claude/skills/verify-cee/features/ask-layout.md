# Answer above the evidence

The answer sits on top (#291): while the reduce streams, its checked claims fade in above the first evidence
card, sentence by sentence; the final answer replaces them in the same place. The claims read as one paragraph
with footnotes `[n]` (a numbered list, each item with its why-line, when the question has its own time window or
a recency aspect). Footnote `[n]` links to evidence card `n` below (`#cee-ev-n`); the card flashes when reached.
After the run, and on every rerun (a page switch, a feedback click), the page draws answer -> adjacent / withheld /
caveats / gaps / coverage -> the full evidence list -> footer and feedback from session state: no new run.

## Sub-features

- `answer-on-top`: the answer block (or, with no claims, the answer heading) is above the first evidence card.
- `footnotes`: every footnote `#cee-ev-n` in the answer has its card. A claim's chunk id maps to the first card
  that cites it; a cited chunk no card cites gets a `SOURCE` card at the end of the list (ground rule 1); an id
  outside the retrieved set stays a flagged, unlinked chip (no card, no footnote). Mapping and the extra card are
  proven by `tests/test_answer_footnotes.py` (the mock cites only chunks of its evidence lines).
- `list-form`: a window / recency answer (Q26) is a numbered list (`.cee-answer ol`); any other a paragraph.
- `rerun-keeps-evidence`: after Coverage -> Ask (top navigation, same session) the answer and the same evidence
  cards and footnotes are shown, and `query_log` has no new row.
- `no-reserved-space`: the answer slot is a zero-height `st.empty()` (display none) until the first claim; the
  driver does not measure it (checked by hand in the PR for #291).
- The stopped view never shows an answer block: [ask-stop-retry](ask-stop-retry.md). The streamed sentences:
  [ask-progress](ask-progress.md).

## How to get to it (user POV)

- Open the app, type a question into "Question", press "Ask"; click a footnote; switch to Coverage and back.

## Driving it

Preconditions: baseline. Questions read from `evals/questions.yaml`: Q5, Q8, Q24, Q26 (`LAYOUT_QS`).

- **Layout.** For each question: Ask; `.cee-answer` (or `.cee-behavior h2` when no claim) is above the first
  `.cee-claim[id^=cee-ev-]`; every `.cee-answer a[href^="#cee-ev-"]` has its element; Q26 is a list, the others
  a paragraph; no "Answer (in progress" left (screenshot).
- **Footnote click.** On Q5, click the first footnote: `:target` is that card.
- **Round trip.** Click "Coverage" in the top navigation, wait for the Coverage page, click "Ask": the same
  layout checks pass, with the same card and footnote counts, and `query_log` count unchanged (screenshot).

## Gotchas

- Use the top navigation, not `page.goto`: a new URL load starts a new session, and session state (the answer)
  is gone by design.
- The mock's Q24 answer is `answer` (the mock always answers when retrieval finds something), not the expected
  `gap_with_adjacent`; the layout check is the same.
- The mock says nothing about answer quality.
