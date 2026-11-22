# Answer progress and step trace

From the moment "Ask" is clicked, a progress bar and one line per pipeline stage show what
the system is doing. The stages follow the W11 flow (#248, ADR-021): reading the question,
decompose (the planner), search N sub-questions, extract from k firms (the map, #246), re-search
(corrective re-search and re-extraction), synthesize (the reduce call, or the answer built by code,
#247), checking citations, caveats and gaps, saving the query. Each line states the stage's real
output. Once the answer shows, the trace stays on the page, collapsed under "How this answer was
built".

## Sub-features

- `progressive` (#272): while the answer is built, the page shows the plan first ("Plan: Decomposing the
  question ..."), then "Evidence so far" with one card per cited item of each map call as it lands
  ("EVIDENCE - <firm> - <aspect>", with the citation chip of a retrieved passage), and the answer last.
  Each card cites a chunk the map's code check kept (inside the cell's retrieved set), so rule 1 holds.
- `streamed-answer` (#275): while the reduce streams, "Answer (in progress: checks running)" lists each claim
  that passed the per-claim checks ("CLAIM (CHECKING)" cards with citation chips); when the final answer shows,
  the block is gone. Adjacent items and flagged claims wait for the final answer. A stalled stream shows an
  error with a "Try again" button (pytest `tests/test_reduce_stream.py`; the driver cannot stall the mock).

- `progress-early`: the progress bar and the first step line appear before the answer.
- `progress-facts`: the search line's passage count equals the footer's chunk count (in the hybrid
  modes the line ends with the plain label "(Smart search)", #125, #126, #128); the
  synthesize line reads "Synthesizing the answer from the evidence matrix (<provider>, one call)";
  the citation line gives matched/flagged.
- `progress-collapsed`: after the answer the trace is collapsed and opens on click.
- `progress-skip`: on a question with no passages the synthesize step reads "No passages found: no
  model call" (and extract / re-search are skipped).
- `progress-failed`: a failing stage is marked failed and its error shown (pytest
  `tests/test_ask_page_trace.py`, `tests/test_ask_progress.py` for a failing re-search; the driver
  cannot break a stage in the running app).
- `plan-parts` (#214, ADR-020; sub-questions since #245, ADR-021): the decompose line says who planned
  and how many calls ("rules, no model call" on the mock) and lists the decomposition,
  "<M> aspects x <N> firms = <K> sub-questions: a1.MS; ..." (sub-question ids `<aspect>.<firm>`); a
  two-firm question is one sub-question per firm ("Searching 2 sub-questions", "Extracting from 2
  firms"), and its `query_log` row holds the plan (aspects, sub-questions, parts), the call count
  (`filters->'plan'`, `filters->'llm_calls'`) and the cost (`filters->'cost'`, #248: calls, tokens, USD).
  A real planner call ("deepseek, one call") and its fallback line are covered by pytest
  (`tests/test_ask_progress.py`); the verify app runs the mock. On `exp/hybrid`
  with `--mode hybrid` the hybrid modes decompose and search the sub-questions with `main`'s loop and
  `hybrid.search` (#249): the same decompose line, search line "Searching 2 sub-questions: ... (Smart search)".
- `research` (#248): the re-search line reads "Re-search: every sub-question has evidence; nothing
  re-searched" or "Re-searching sub-questions with no evidence: R re-searched, P with new passages, E
  re-extractions (...)".

## How to get to it (user POV)

- Open the app, type a question, press "Ask"; watch above the answer.

## Driving it

Preconditions: baseline.

- **Plan first (#272).** Ask the answerable question. As soon as "Plan:" shows, the plan line reads
  "Plan: Decomposing the question ..." and neither "Evidence so far" nor the meta line "LLM called:" is
  on the page (screenshot).
- **Evidence next (#272).** Once "Evidence so far" shows, at least one "EVIDENCE - Edward Jones" card with
  a citation chip is there and "LLM called:" is not (screenshot); the answer follows.
- **Streamed answer (#275).** After "Synthesizing the answer" shows, "Answer (in progress: checks running)"
  appears with at least one "CLAIM (CHECKING)" card carrying a citation chip, and "LLM called:" is not on the
  page (screenshot); once "LLM called:" shows, the in-progress block and its cards are gone.
- **Early.** Still on the answerable question. As soon as "Synthesizing the answer" shows, the progress
  bar (`stProgress`) and the line "Reading the question: ..." are on the page and the meta
  line "LLM called:" is not (screenshot of the trace mid-run).
- **Collapsed.** A status box labelled "How this answer was built: 9 steps ..." is present
  and the trace lines are hidden; click the label and the nine lines show (the driver takes the
  count from `cee.ask.STAGES`).
- **Extract (#246, #248).** The extract line reads "Extracting from 1 firm (mock, no model call): N
  cells: ...; behavior by code: answer". The driver sets `MAP=on` for the verify app, so an older
  `.env` with `MAP=off` cannot change the run. `MAP=off` (the legacy single answer call) reads "Map
  step off (MAP=off): no extraction calls; legacy single answer call" (pytest
  `tests/test_ask_progress.py`).
- **Re-search.** A line starting "Re-search" is there (see `research` above).
- **Decompose.** The line "Decomposing the question (rules, no model call): 1 aspect x 1 firm = 1
  sub-question: a1.EDJ" is there (the answerable question names Edward Jones only).
- **Facts.** "Searching 1 sub-question: N passages" equals "N passages found" in the meta line;
  the synthesize line contains "from the evidence matrix (mock, one call)"; a "Checking citations: ...
  matched" line exists.
- **Skip.** Ask the no-evidence question, open the trace: "No passages found: no model call",
  and the meta line says "LLM called: False".
- **Parts.** Ask "How do Morgan Stanley and Raymond James approach advisor recruiting?", open
  the trace: "Decomposing the question (rules, no model call): 1 aspect x 2 firms = 2 sub-questions:
  a1.MS; a1.RJF", "Searching 2 sub-questions: ..." and "Extracting from 2 firms ...". The newest
  `query_log` row in `cee_verify` has plan source `rules`, 2 parts (one per sub-question),
  `llm_calls` `{"map": 0, "remap": 0, "answer": 0, "planner": 0}` and cost 0 calls / $0 (the mock map
  and reduce make no paid call).
  With `--mode hybrid` (exp/hybrid, #249): the same decompose line and row; the search line ends
  "(Smart search)" (the page shows the plain mode label). The driver picks the check from `--mode`
  (`VERIFY_RETRIEVAL_MODE`, else `RETRIEVAL_MODE`).

## Gotchas

- The mock answers in milliseconds, and Streamlit merges a bar that is shown and removed
  within one update, so the bar would never be drawn. The verify app sets `MOCK_DELAY_S=1.5`:
  the mock map (`mock_extract`) and the mock reduce (`mock_reduce`) each wait that long, like a model
  would; on the Ask page the mock reduce then streams its output and waits that long again spread over its
  items (#275), so the checked claim is seen before the final answer. The answerable question takes map.a1.EDJ (#272: one call per cell) -> behavior answer -> the reduce call, so the page is
  caught while "Synthesizing the answer" runs. Without the delay, do not expect to see the bar.
- Streamlit renders `st.status` as an expander; open it by clicking its label.
- `llm_calls` and `cost` count paid provider calls: on the mock they read 0 although the synthesize
  line says "(mock, one call)".
