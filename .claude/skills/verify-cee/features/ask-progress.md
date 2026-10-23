# Answer progress and step trace

From the moment "Ask" is clicked, a progress bar and one line per pipeline stage show what
the system is doing (reading the question, searching, asking the model or skipping it,
checking citations, caveats and gaps). Each line states the stage's real output. Once the
answer shows, the trace stays on the page, collapsed under "How this answer was built".

## Sub-features

- `progress-early`: the progress bar and the first step line appear before the answer.
- `progress-facts`: the search line's passage count equals the footer's chunk count; the
  model line names the provider and "one call"; the citation line gives matched/flagged.
- `progress-collapsed`: after the answer the trace is collapsed and opens on click.
- `progress-skip`: on a question with no passages the model step reads "no model call".
- `progress-failed`: a failing stage is marked failed and its error shown (pytest
  `tests/test_ask_page_trace.py`; the driver cannot break a stage in the running app).

## How to get to it (user POV)

- Open the app, type a question, press "Ask"; watch above the answer.

## Driving it

Preconditions: baseline.

- **Early.** Ask the answerable question. As soon as "Asking the model" shows, the progress
  bar (`stProgress`) and the line "Reading the question: ..." are on the page and the meta
  line "LLM called:" is not (screenshot of the trace mid-run).
- **Collapsed.** A status box labelled "How this answer was built: 5 steps ..." is present
  and the trace lines are hidden; click the label and the five lines show.
- **Facts.** "Searching the corpus: N passages" equals "N chunks retrieved" in the meta line;
  the model line contains "(mock, one call)"; a "Checking citations: ... matched" line exists.
- **Skip.** Ask the no-evidence question, open the trace: "No passages found: no model call",
  and the meta line says "LLM called: False".

## Gotchas

- The mock answers in milliseconds, and Streamlit merges a bar that is shown and removed
  within one update, so the bar would never be drawn. The verify app sets `MOCK_DELAY_S=1.5`
  (the mock waits like a model would); without it, do not expect to see the bar.
- Streamlit renders `st.status` as an expander; open it by clicking its label.
