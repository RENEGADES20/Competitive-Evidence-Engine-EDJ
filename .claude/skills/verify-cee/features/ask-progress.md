# Answer progress and step trace

From the moment "Ask" is clicked, a progress bar and one line per pipeline stage show what
the system is doing (reading the question, planning the search, searching, asking the model or
skipping it, checking citations, caveats and gaps, saving the query). Each line states the stage's
real output. Once the answer shows, the trace stays on the page, collapsed under "How this answer
was built".

## Sub-features

- `progress-early`: the progress bar and the first step line appear before the answer.
- `progress-facts`: the search line's passage count equals the footer's chunk count; the
  model line names the provider and "one call"; the citation line gives matched/flagged.
- `progress-collapsed`: after the answer the trace is collapsed and opens on click.
- `progress-skip`: on a question with no passages the model step reads "no model call".
- `progress-failed`: a failing stage is marked failed and its error shown (pytest
  `tests/test_ask_page_trace.py`; the driver cannot break a stage in the running app).
- `plan-parts` (#214, ADR-020; sub-questions since #245, ADR-021): the plan line says who planned
  the search and how many calls ("rules, no model call" on the mock) and lists the decomposition,
  "<M> aspects x <N> firms = <K> sub-questions: a1.MS; ..." (sub-question ids `<aspect>.<firm>`); a
  two-firm question is one sub-question per firm ("in 2 sub-questions" on the search line), and its
  `query_log` row holds the plan (aspects, sub-questions, parts) and the call count
  (`filters->'plan'`, `filters->'llm_calls'`). A real planner
  call ("anthropic, one call") and its fallback line are covered by pytest
  (`tests/test_ask_progress.py`); the verify app runs the mock.

## How to get to it (user POV)

- Open the app, type a question, press "Ask"; watch above the answer.

## Driving it

Preconditions: baseline.

- **Early.** Ask the answerable question. As soon as "Asking the model" shows, the progress
  bar (`stProgress`) and the line "Reading the question: ..." are on the page and the meta
  line "LLM called:" is not (screenshot of the trace mid-run).
- **Collapsed.** A status box labelled "How this answer was built: 7 steps ..." is present
  and the trace lines are hidden; click the label and the seven lines show.
- **Plan.** The line "Planning the search (rules, no model call): 1 aspect x 1 firm = 1
  sub-question: a1.EDJ" is there (the answerable question names Edward Jones only).
- **Facts.** "Searching the corpus: N passages" equals "N passages found" in the meta line;
  the model line contains "(mock, one call)"; a "Checking citations: ... matched" line exists.
- **Skip.** Ask the no-evidence question, open the trace: "No passages found: no model call",
  and the meta line says "LLM called: False".
- **Parts.** Ask "How do Morgan Stanley and Raymond James approach advisor recruiting?", open
  the trace: "Planning the search (rules, no model call): 1 aspect x 2 firms = 2 sub-questions:
  a1.MS; a1.RJF" and the search line ends "in 2 sub-questions". The newest `query_log` row in
  `cee_verify` has plan source `rules`, 2 parts (one per sub-question) and `llm_calls`
  `{"answer": 0, "planner": 0}` (the mock makes no paid call).

## Gotchas

- The mock answers in milliseconds, and Streamlit merges a bar that is shown and removed
  within one update, so the bar would never be drawn. The verify app sets `MOCK_DELAY_S=1.5`
  (the mock waits like a model would); without it, do not expect to see the bar.
- Streamlit renders `st.status` as an expander; open it by clicking its label.
- `llm_calls` counts paid provider calls: on the mock it reads 0 / 0 although the model line says
  "(mock, one call)".
