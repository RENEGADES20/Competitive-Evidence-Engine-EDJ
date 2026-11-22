# 0277 - Ask page: Stop generation and manual Retry

Issue: #277    Role: TL    Spec: specs/ui.md, specs/answer-citations.md

## Goal
While an answer is being built, a **Stop** button ends the run within a few seconds: no new model call starts,
open DeepSeek streams are closed, and the page shows "Stopped" with the cited evidence already found (never a
final answer). After a stop or any failure, a **Retry** button runs the same question and filters once more,
reusing every call that already finished with a valid result and running only the missing, failed, cut or
cancelled ones. 0 real API calls.

## How it works today (read before the plan)
- `ask_page.ask_with_trace` calls `ask()` **in the Streamlit script thread**. The planner and the reduce stream
  run in that thread; the map runs in a `ThreadPoolExecutor` inside `extract.run_round`, whose
  `as_completed` loop blocks the script thread.
- Streamlit 1.64 (installed) handles a click during a run as a RERUN request. The running script is
  interrupted only at a *yield point*: any `st.*` call that sends a message, or a `st.session_state` read
  (`ScriptRunner._maybe_handle_execution_control_request`). It raises `RerunException` / `StopException`
  there. A script blocked in a socket read or in `as_completed` has no yield point, so a click waits until
  the next draw. Worse, when the exception unwinds through `with ThreadPoolExecutor(...)`, `shutdown(wait=True)`
  waits for **every queued map call**, which keep running and billing. A button `on_click` callback runs only
  at the start of the *next* run, after the old one ended, so it cannot be the stop signal by itself.
- No call cache exists in the app. The eval's cache (`scripts/eval_run.py`) saves failures on purpose and
  never re-calls them (the eval's "never re-roll" rule); the app must not copy that rule for Retry, where the
  user explicitly asks for one more attempt.
- `#275`: a `StreamIdle` shows `STALL_TEXT` and the "Try again" button (`key="retry-ask"`, sets
  `session_state.retry_ask`); every other failure shows only an error.

## Design decisions
1. **Cancel token** (`src/cee/answer/cancel.py`, new). `CancelToken` (a `threading.Event` plus `reason`,
   `stage`, `set_at`), `Cancelled(BaseException)`, a `contextvars.ContextVar` holding the active token with
   `use(token)`, `current()`, `check()` (raises `Cancelled` when set) and `sleep(s)` (waits on the event;
   raises `Cancelled` when set; plain `time.sleep` with no token). `Cancelled` subclasses `BaseException`
   (like `KeyboardInterrupt`) so no generic `except Exception` turns a stop into a failure or a fallback:
   `ask._Trace.stage` (ask.py:73), `ask.map_step` (ask.py:216), `llm.read_stream`, `extract.provider_call`,
   `planner.plan_question`'s rule-plan fallback, `ask_page`'s `except Exception`. `ThreadPoolExecutor` stores a
   `BaseException` in the future and `f.result()` re-raises it. `_Trace.stage` and `map_step` add an
   explicit `except Cancelled:` that reports the running stage as "stopped" (not "failed") and re-raises.
   The token reaches the map workers because `run_round` submits each call through its own
   `contextvars.copy_context().run(...)`, **one fresh copy per submitted call** (one `Context` cannot be
   entered by two threads at once; executor threads do not inherit context vars). No call signature changes
   beyond `ask(..., cancel=None, cache=None, run=None)`.
2. **Checks**: `cancel.check()` before every model call (planner `call_planner` site in `plan_question`,
   `extract.call_extract` via `provider_call`, `reduce.call_reduce`, legacy `llm.generate`) and at each stage
   boundary in `ask()` (after resolve, decompose, search, map round 1, re-search, round 2, before reduce).
   `extract.run_round`: a call whose turn comes after the token is set is not made (`CallResult(skipped,
   error="cancelled")`). The `with ThreadPoolExecutor(...)` block becomes `try / finally:
   ex.shutdown(wait=False, cancel_futures=True)`, because the `with` exit is `shutdown(wait=True)` and would
   wait for every queued call. On `Cancelled` the round cancels the queued futures, still collects the futures
   already running (they end within ~1 s once their stream closes) so their results are recorded and cached,
   marks the rest `cancelled`, then re-raises.
3. **Stream close**: `llm.read_stream`'s watchdog (already polling every <= 1 s) also watches the active
   token; when set it closes the stream like an idle stall, and the loop raises `Cancelled` (not
   `StreamIdle`) with the partial output attached. `deepseek_create` checks the token before `create`.
   Not cut (stated in the spec): non-streamed requests (anthropic / openai, `DEEPSEEK_STREAM=off`) and the
   wait inside `client.chat.completions.create(stream=True)` before the first byte (before `read_stream` and
   its watchdog exist; bounded by the connect timeout and `DEEPSEEK_IDLE_S`). Such a call runs to its end and
   is billed; its output is cached `ok` if valid; no new call starts after it. A cut stream has no `usage`
   (DeepSeek sends usage last), so its record's cost reads "cost unknown", never 0.
4. **How the Stop click reaches the workers** (the issue's key point). `ask_with_trace` runs `ask()` in a
   **worker thread** and turns the script thread into a UI pump: progress and `on_event` callbacks put
   messages on a `queue.Queue`; the pump drains it every 0.2 s and draws (Streamlit is drawn only from the
   script thread, as before), and updates an "elapsed N s" caption each second, which is a guaranteed yield
   point. The token lives in `st.session_state["ask_run"]` (with the worker thread, the question, filters,
   stage, plan text and the evidence lines drawn so far). The Stop button (`key="stop-ask"`) is drawn before
   the pump starts. Its click makes Streamlit raise `RerunException` at the pump's next yield point (<= 1 s);
   the pump catches `BaseException`, sets the token (`reason="stop"`), marks the run `stopped` at its current
   stage, and re-raises so Streamlit reruns. The rerun draws the Stopped view from session state. Any other
   interrupting click (a sidebar filter, a new Ask) also stops the run the same way, so no run keeps billing
   after the page moved on. The worker sees the token at its next check (<= 1 s for streams and queued calls).
   - **Worker rule**: the worker thread has no script-run context and never touches `st.*` or
     `st.session_state`. It writes only to the queue, the plain `Run` object (a dataclass held in
     `session_state["ask_run"]`, mutated under its own lock) and the `RunCache`. Tested with AppTest and a fake
     `ask` (no "missing ScriptRunContext" warning, no exception).
   - **Late result**: a worker that finishes after the token was set (e.g. an uncut call) stores its records
     and logs its row, but its answer is never shown: the page draws a final answer only from a run whose status
     is `done` and whose token is not set.
   - **The Stop rerun**: on the rerun caused by Stop, `render()` sees `ask_run.status == "stopped"` and draws
     the Stopped view; it never starts a run. A run starts only on Ask (new `Run`, new `RunCache`) or Retry
     (new `Run`, same `RunCache`); `session_state["ask_run"]` is replaced before the new worker starts.
5. **Run cache** (`src/cee/answer/runcache.py`, new): in memory, held in `st.session_state["ask_cache"]`
   for the current question + filters; Ask always starts a new one, only Retry reuses it (so asking again
   never silently replays an old answer). Thread-safe (a lock; map workers write concurrently). Each record:
   stage, call id, key, status, output, provider, model, usage, finished_at, error, attempt. Status is one of
   `ok | invalid | cut | failed | idle | cancelled | skipped`. **`get(key)` returns an output only for `ok`.**
   A call that returns a valid output is recorded `ok` first, and only then is the token checked: a result
   that lands after the click is kept and reused, never paid twice. Only a call that raised `Cancelled` (or
   was never started) is `cancelled`.
   A failed, cut, invalid, idle or cancelled record is kept for the run log but is never returned as an
   output, so a failure is never replayed as an answer. Keys reuse the eval's ingredients (no snapshot):
   - plan: provider, model, `PLANNER_VERSION`, request version, the resolved query; stored only when the
     planner call returned a usable plan (no `plan.error`); a planner failure (rule-plan fallback) re-runs.
   - map / remap: provider, model, `EXTRACT_VERSION`, cap, request version, call id, cells, input chunk ids
     in order, window. Wired through `run_map(call=...)`: a wrapper around `provider_call` returns
     `CallResult(raw=deepcopy, cached=True, usage, stop_reason)` on a hit (`log_filters` already leaves
     `cached` calls out of the paid count and the cost); `invalid` -> `invalid` (`cut` when the stop reason is
     a cut), `failed_call` -> `failed`, `skipped` with "cancelled" -> `cancelled`.
   - reduce: provider, model, `prompt_version()`, cap, request version, sha256 of the system prompt, of
     `reduce_message(...)` and of the schema. The raw `Answer` is recorded `ok` only after `call_reduce`,
     `to_answer` **and `R.finish_answer`** succeed (a check that raises on that output records `invalid`, so
     Retry asks the model again rather than replaying it); `ModelOutputError` -> `invalid` / `cut`,
     `StreamIdle` -> `idle`, `Cancelled` -> `cancelled`, other errors -> `failed`. A reused reduce goes
     through the existing `raw` path ("Reusing the saved model output: no model call") and every code check.
   - The mock goes through the same keys (0 paid calls), so verify-cee can show reuse: the mock map through
     the `run_map(call=...)` wrapper around `provider_call("mock")`; the mock reduce in `_reduce_for`, where
     the `provider == "mock"` branch (`R.raw_answer`) and the real branch (`R.call_reduce` + `to_answer`) are
     both wrapped by the same cache lookup / record step.
6. **Retry** (replaces "Try again"; label `RETRY_LABEL = "Retry"`, same `key="retry-ask"`, same
   `session_state.retry_ask` flag, one click = one attempt, never automatic). Shown: after a stop; after any
   failed run (`StreamIdle` keeps `STALL_TEXT`; other errors keep their message); and under a finished
   answer when a call failed or was invalid (failed map cell, failed planner fallback), labelled "Retry the
   failed calls". It re-runs `ask()` with the saved question and filters (not the current text box), the
   same run cache and `attempt + 1`. Retry never starts a second worker while the previous one is alive: the
   Stopped / failed view checks the previous worker; while it is alive Retry is drawn disabled with "The
   previous call is still finishing" and the page polls (up to 15 s per rerun, `st.rerun` after); Retry is
   enabled once the worker has ended (streams end within ~1 s; an uncut call may take longer). So no call
   ever runs twice at once.
7. **Rule 1 on a stopped or failed page**: the Stopped view shows the plan line, the heading
   "Stopped at <stage>" with "The answer was not built. Evidence found before the stop is below; each item
   cites a stored passage.", the "Evidence so far" cards (map items: code-checked, cited, chips to retrieved
   chunks) and Retry. The streamed "CLAIM (CHECKING)" block is **not** kept (as for a failure since #275: no
   caveats, gaps or dedupe were applied yet), and no behavior header, final claims or "LLM called:" line.
8. **Run log** (deliverable 4). Every attempt writes one `query_log` row. A finished attempt adds
   `filters.run = {attempt, retry_of, status: "done", reused: {plan, map, remap, reduce counts}, made: {...},
   records: [{stage, id, status}]}`. A stopped or failed attempt (the worker catches `Cancelled` or the
   error, logs, re-raises) writes a row with `answer` NULL and `filters.run = {attempt, retry_of, status:
   "stopped" | "failed", stage, reason, error, stop_s (token set -> worker end), reused, made, cancelled,
   records}` plus `filters.cost` priced from the records that made a paid call (the existing
   `cost.price_call`; a record with no usage is listed as "cost unknown"), so calls of a stopped run are
   logged with tokens and cost too. Readers checked: only `ask._log` writes; no `src` reader of `answer`
   (nullable, `db/schema.sql:56`); feedback needs a shown `query_id`, which stopped runs do not show.
   `scripts/verify_cee.py` reads the newest row (e.g. line 341): the new recipe runs last in `FEATURES`, and
   the other features' newest-row queries add `WHERE answer IS NOT NULL` so a stray stopped row can never be
   read as an answer.
9. **Mock for verify** (`config.py`): the mock map call k of a run (submission order) waits
   `MOCK_DELAY_S x min(k + 1, 3)`, so evidence cards land one by one (a single-call question is unchanged;
   a two-call question: 1.5 s, 3 s). The mock waits through `cancel.sleep` so a stop cuts it. New
   `MOCK_FAIL_FILE` (path; unset by default): while that file exists and names a stage (`map` or `reduce`),
   the mock call of that stage raises an injected `RuntimeError`. Mock only; never read for a real provider.
   The driver writes the file, asks, deletes it, clicks Retry.

## Files to change
- `src/cee/answer/cancel.py` (new) - token, `Cancelled`, context var, `check`, `sleep`.
- `src/cee/answer/runcache.py` (new) - `RunCache`, keys, record statuses, `get` only for `ok`, run summary.
- `src/cee/answer/llm.py` - token check in `deepseek_create`; watchdog closes the stream on cancel and
  raises `Cancelled`; `_mock` waits through `cancel.sleep`.
- `src/cee/answer/extract.py` - `run_round` check per call, context copy, `cancel_futures`, cancelled
  records; `provider_call` re-raises `Cancelled`; mock stagger, `cancel.sleep`, injected map failure;
  `run_map` checks before re-search and round 2.
- `src/cee/answer/reduce.py` - check before the call; mock waits through `cancel.sleep`; injected reduce
  failure.
- `src/cee/retrieve/planner.py` - check before the call; `Cancelled` never becomes the rule-plan fallback.
- `src/cee/ask.py` - `ask(..., cancel, cache, run)`: `cancel.use`, stage checks, cached plan / map / reduce,
  `filters.run`, stopped / failed rows (answer NULL) with cost.
- `src/cee/config.py` - `mock_fail_file` (`MOCK_FAIL_FILE`).
- `src/cee/app/views/ask_page.py` - worker thread + UI pump, Stop button, session-held run state, Stopped
  view, Retry for stop and every failure (replaces "Try again").
- `.env.example` - `MOCK_FAIL_FILE` line (commented, verify only).
- `specs/ui.md`, `specs/answer-citations.md` - Stop, Retry, cancel token, run cache, run log.
- `.claude/skills/verify-cee/features/ask-stop-retry.md` (new), `features/README.md` (index),
  `features/ask-progress.md` ("Try again" -> "Retry").
- `scripts/verify_cee.py` - `MOCK_FAIL_FILE` in the launch env, driver `feature_ask_stop_retry`, `FEATURES`
  and `DRIVERS` entries.
- Tests: `tests/test_stop_retry.py` (new); `tests/test_stream_idle.py`, `tests/test_ask_page_trace.py`,
  `tests/test_map_fanout.py` (only if the stagger or the round change needs it).

## Steps
1. `cancel.py` + tests: `check`, `sleep` returns early on set, context var reaches pool workers via
   `copy_context`.
2. `llm.read_stream` / `deepseek_create` cancel + test with a fake slow stream: token set mid-way -> stream
   `close()` called, `Cancelled` raised within ~1 s, partial attached; no token -> unchanged (existing
   `test_stream_idle.py` stays green).
3. `extract.run_round` / `run_map` / `provider_call`, planner, reduce checks + tests with a fake call: token
   set after the first call lands -> no further call starts, queued cells cancelled, `Cancelled` propagates,
   `run_round` returns without waiting for queued calls; concurrency 2 with a fresh context per call (no
   "already entered"); planner does not fall back to the rule plan on `Cancelled`; after a stop no trace
   stage reads "failed" (the running one reads "stopped").
4. `runcache.py` + `ask()` wiring + tests (fake call functions, mock provider, `_log` stubbed): cancelled,
   failed, cut, invalid and idle records are never returned by `get`; a valid result that lands after the token
   is set is recorded `ok` and reused; a reduce output whose `finish_answer` raises is not `ok`; a retry after a stop reuses the
   finished map calls and makes only the missing ones; a retry after an injected reduce failure reuses
   every map call and makes the reduce once; one Retry = one attempt (call counts asserted).
5. Run log rows: stopped row (answer NULL, `filters.run.status = stopped`, stage, counts, `stop_s`) and the
   retry row (`attempt 2`, `retry_of`, reused / made counts); unit-tested on `log_filters` / the run summary.
6. Ask page: worker + pump, Stop, Stopped view, Retry. Tests (AppTest + a pure pump test): an interrupt
   raised at the pump's yield point sets the token and marks the run stopped; the Stopped view shows evidence
   cards and Retry, no final answer, no "CLAIM (CHECKING)"; Retry shows for `StreamIdle`, a generic error and
   a finished answer with a failed cell; the Retry click re-runs with the saved question and filters; the Stop
   rerun starts no run; Retry is disabled while the previous worker is alive; a worker result that lands after
   a stop is never shown; the worker never touches `st` (AppTest with a fake `ask`).
7. Mock stagger and `MOCK_FAIL_FILE`; spec text; `.env.example`.
8. verify-cee recipe + driver (`ask-stop-retry` last in `FEATURES`; other features' newest-row reads use
   `answer IS NOT NULL`); run `verify_cee.py run` (all features, so the stagger is checked against the
   other recipes too).
9. Mock 30/30 run (`scripts/eval_run.py`, mock), full pytest, PR, `gh pr checks`.

Unsure / to confirm while building: that a `st.session_state` read is a yield point in 1.64 (the elapsed
caption is the guaranteed one either way); how long AppTest lets a worker thread run (tests use fakes with no
delay, the pump logic is tested as a pure function).

## Acceptance
- [x] Linked questions: Q29 (the stall path now shows Retry: `tests/test_reduce_stream.py::test_a_stall_shows_an_error_and_retry`,
      fake idle stream); any question for Stop (verify uses the two-firm question "How do Morgan Stanley and Raymond James
      approach advisor recruiting?", 3 map calls on the mock: map.a1.MS, map.a1.RJF, map.research).
- [x] Spec items: ui.md Stop / Retry / Stopped view lines; answer-citations.md cancel token, run cache and
      run log lines; rule 1 on a stopped page (AppTest: no "LLM called:", no "CLAIM (CHECKING)").
- [x] `pytest tests/test_stop_retry.py` -> 29 passed, covering: the token stops new calls and closes a fake
      stream mid-way (close called, `Cancelled` < 2 s, partial kept); cancelled, failed, cut, invalid, idle and skipped
      records are never reused by the cache; a valid result landing after the stop is reused; a retry reuses finished
      calls and runs only the missing ones (exact call counts); a planner `Cancelled` never yields the rule
      plan; no stage reads "failed" after a stop; one Retry click makes one attempt; the stopped row's
      `filters.run.records` and `filters.run.stop_s` are present; the Retry poll draws no Stop and starts no run.
- [x] `pytest` (whole suite) -> 1160 passed; `tests/test_no_paid_calls.py` green (0 real calls).
- [x] Mock eval: `python scripts/eval_run.py` -> PASS 33 | FAIL 2 on the 35-question bank, the same as the run on
      `main` earlier today (`.eval-runs/corpus-2026-11-19-20261122-115549`): every question's status and chunk ids
      identical (Q26 differs only in its as-of window date). The 2 FAILs (Q19, Q33) are pre-existing. The bank grew
      from 30 to 35 since the issue was written.
- [x] `python scripts/verify_cee.py run` -> 11/11 features PASS (`.verify-runs/20261122-124300-a132160`); the new
      `ask-stop-retry` recipe shows:
      - Stop clicked after the first evidence card (during the map): "Stopped while extracting evidence" visible
        in < 1 s; the evidence card still shown; no "LLM called:", no "Answer (in progress", no Stop button;
        5 s later no new card;
      - newest `query_log` row: `answer` NULL, `filters.run.status = stopped`, stage `extract`, map.a1.MS ok,
        map.a1.RJF and map.research cancelled, `stop_s` 0.06-0.11;
      - Retry completes the answer; newest row `attempt` 2, `retry_of` the stopped row, reused `{"map": 1}`,
        made `{"map": 2, "reduce": 1}`;
      - with `MOCK_FAIL_FILE` naming `reduce`: the error and Retry show, no claims; failed row stage
        `synthesize`; file removed, Retry -> the answer, reused `{"map": 3}`, made `{"reduce": 1}`.
- [x] `gh pr checks` green (PR #279, pytest pass).
- [x] 0 real API calls (stated in the PR Verification section).

## Progress log
- 2026-11-22 12:12 - plan written (branch `tl/277-stop-retry` from `main` 621aaec, database up to date:
  corpus-2026-11-19). Read Streamlit 1.64's rerun handling: a click is honoured only at a yield point, and an
  executor `with` block would wait for every queued call; hence the worker thread + UI pump.
- 2026-11-22 12:30 - plan review (reviewer agent, round 1): CHANGES REQUESTED, 8 findings, all taken:
  `Cancelled` is a `BaseException` and stages report "stopped"; `run_round` drops the `with` block, one
  context copy per call; valid late results cached `ok`; reduce `ok` only after `finish_answer`, mock branch
  wrapped too; uncut steps and "cost unknown" documented, Retry disabled while the old worker lives; worker
  never touches `st`, late results never shown, the Stop rerun starts no run; stop-retry recipe last and
  newest-row reads skip NULL answers.
- 2026-11-22 12:40 - plan review round 2: APPROVE (all 8 findings checked in the plan). Build note from the
  reviewer: while the old worker is alive, the Retry poll (`st.rerun`) must not draw a second Stop button or
  start a run; add a test for it in step 6.
- 2026-11-22 12:35 - steps 1-6 built: `cancel.py`, `runcache.py`, checks in llm / extract / reduce / planner,
  `ask()` with token + cache + stopped / failed rows, Ask page worker + pump, Stop, Stopped view, Retry.
  Changes from the plan: (a) the Retry wait while the old worker lives is a `st.fragment(run_every=1)` that
  reruns the page once the worker ends, not a 15 s blocking poll (no blocking, nothing to start); (b) the trace
  gets a "stopped" mark and colour (`src/cee/app/components.py`, 2 lines, outside the file list);
  (c) `cancel.sleep(0)` neither waits nor checks, so a mock with no delay never cuts a call that has its output;
  (d) user-stop records are `cancelled` with `CallResult.cancelled` and `STOPPED_ERROR`, distinct from a
  ProviderStop's "cancelled after the provider stopped the run" (reviewer note 1).
  Surprise: the page's failure path now logs a row, and two existing AppTest tests wrote 4 rows into the local
  `cee` query_log; the tests now stub `_log_attempt` and the 4 rows were deleted. pytest 1160 passed.
- 2026-11-22 12:45 - specs, `.env.example`, recipe `ask-stop-retry.md` + driver. First verify runs: the map has
  3 calls on the mock (map.research too), so the driver takes the reused / made counts from the stopped row; the
  Stopped view first showed "still finishing" because the worker was still writing the stopped row, so the view
  now joins the worker for up to 2 s (`GRACE_S`) before it falls back to the 1 s fragment poll. Stale cards
  from the interrupted run are counted only after the rerun settles.
- 2026-11-22 12:50 - verify-cee all 11 features PASS (`.verify-runs/20261122-124300-a132160`); mock eval
  unchanged against `main` (33 / 2 on 35 questions); pytest 1160 passed; 0 real calls.
- 2026-11-22 12:58 - PR #279 opened; `gh pr checks` pytest pass. Not merged (independent review).
