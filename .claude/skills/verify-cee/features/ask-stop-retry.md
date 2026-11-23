# Stop and Retry

While an answer is being built, a **Stop** button ends the run within a few seconds: no new model call
starts, open streams are closed, and the page shows "Stopped while <stage>" with the plan line and the
cited evidence already found, never a final answer (#277). **Retry** appears after a stop and after any
failure. It asks again with the same question and filters, once. Calls that finished with a valid output
are reused from the run cache, and only the missing, failed, cut or cancelled ones run again. Every
attempt is logged in `query_log`: a stopped or failed attempt has no answer (NULL) and `filters.run`.

## Sub-features

- `stop-map`: Stop clicked during the map. "Stopped while extracting evidence" appears within 5 s, with the
  evidence cards already shown. There is no "LLM called:" footer, no answer block above the evidence (#291), no
  "Answer (in progress" block and no
  Stop button, and no card arrives afterwards.
- `stop-log`: the stopped row has `answer` NULL and `filters.run.status = stopped`, `reason` `stop` (a click on
  another widget reads `page`), stage `extract`. Its records
  are `map.a1.MS` ok and `map.a1.RJF` cancelled (plus `map.research`, queued behind it), and `stop_s` (click to worker end) is 5 s or less.
- `retry-after-stop`: Retry completes the answer. The new row has `run.attempt = 2` and `retry_of` = the
  stopped row. `reused` is `{"map": 1}` (the ok call) and `made` is `{"map": 2, "reduce": 1}` (the cancelled calls and the reduce).
- `retry-after-failure`: with `MOCK_FAIL_FILE` naming `reduce`, the run shows "The answer could not be built
  ... injected reduce failure" and Retry. Its row is `failed` at stage `synthesize`. Once the file is
  removed, Retry gives the answer with every map call reused (`{"map": 3}`) and `made` `{"reduce": 1}`.
- pytest only (`tests/test_stop_retry.py`), because the driver cannot produce these in the running app:
  - a closed DeepSeek stream;
  - an uncut call that lands after the stop (kept, reused);
  - Retry disabled while the stopped run's worker still runs (no Stop button, no new run);
  - "Retry the failed calls" under an answer with a failed map cell;
  - a stall (`StreamIdle`, `tests/test_reduce_stream.py`).

## How to get to it (user POV)

- Open the app, type a question, press "Ask", then press "Stop" while the page says "Working for N s".
- After a stop or an error, press "Retry".

## Driving it

Preconditions: baseline. The verify app runs the mock with `MOCK_DELAY_S=1.5` and `MOCK_FAIL_FILE` =
`<run folder>/mock-fail.txt`, which does not exist by default.

- **Stop.** Ask "How do Morgan Stanley and Raymond James approach advisor recruiting?" (3 map calls: `map.a1.MS`, `map.a1.RJF`, `map.research`). The mock
  map call k waits 1.5 s x (k + 1), so the Morgan Stanley card lands about 1.5 s before Raymond James. When the
  first "EVIDENCE - " card shows, a Stop button is on the page (screenshot). Click Stop. Within 5 s,
  "Stopped while extracting evidence" shows with the card still there and no answer (screenshot; counted once the
  rerun is drawn, as the old run's cards stay on screen for a moment). Wait 5 s:
  no new card, and Retry is offered.
- **Stopped row.** In `cee_verify`, the newest `query_log` row has `answer` NULL and
  `filters->'run'` status `stopped`, stage `extract`, records `map.a1.MS` ok and `map.a1.RJF` and `map.research` cancelled,
  and `stop_s` <= 5. The worker writes the row once it ends, so the driver polls for up to 15 s.
- **Retry after the stop.** Click Retry and wait for "LLM called:". The newest answered row has
  `run.attempt` 2, `retry_of` the stopped row, `reused` the ok calls (`{"map": 1}`) and `made` the cancelled ones plus the reduce (`{"map": 2, "reduce": 1}`); the driver takes the counts from the stopped row.
- **Retry after a failure.**
  1. Write `reduce` to the mock-fail file and ask the same question again; Ask starts a new run cache.
  2. The page shows "The answer could not be built. RuntimeError: injected reduce failure (MOCK_FAIL_FILE)"
     and a Retry button, with no answer.
  3. Remove the file and click Retry: the answer shows. The failed row has stage `synthesize`. The newest row
     has `retry_of` the failed row, `reused` `{"map": 3}` and `made` `{"reduce": 1}`.

## Gotchas

- This feature runs last in `FEATURES`: it leaves rows with no answer. Every other feature reads the newest
  row `WHERE answer IS NOT NULL`.
- A click on any other widget during a run (a sidebar filter, for example) stops the run the same way. The
  Stopped view then adds "The run stopped because the page changed while the answer was being built.", and
  the row's `reason` reads `page`. The pump tells the two apart from the widget states in Streamlit's rerun
  exception (the Stop button's trigger).
- While a stopped run's worker still finishes a call that cannot be cut, Ask and Retry are both disabled
  ("Finishing the stopped call ..."), so no call runs twice (pytest; the mock's calls are always cut).
- The driver always removes the mock-fail file, even when a step fails. A file left behind makes every later
  mock reduce of that app fail.
- `made` counts the mock's calls too (0 paid calls). `filters.llm_calls` and `filters.cost` still count paid
  calls only.
