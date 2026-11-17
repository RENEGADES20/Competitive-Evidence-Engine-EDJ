# 0187 - Keep a paid model output that fails validation

Issue: #187    Role: TL    Spec: `CLAUDE.md` "Paid API calls" step 3, `specs/answer-citations.md` (Answer JSON), `scripts/eval_run.py` docstring (eval runner)

## Goal
When a real model returns an answer that does not fit the `Answer` schema (or no answer tool
call at all), the eval runner keeps the raw provider payload on disk, reports the question as
`INVALID_OUTPUT`, counts the call against `--max-calls`, and moves on to the next question,
instead of crashing and losing what was paid for. The app keeps showing an error for such an
answer, as today (its error message now says the output was invalid).

## Files to change
- `src/cee/answer/llm.py` (S2; owner review waived by TL decision 2026-11-17, see #187 comment) -
  new `ModelOutputError(RuntimeError)` carrying `raw` (the provider payload) and `provider`.
  `raw` is always JSON-safe: Anthropic `block.input` (a dict) when the tool was called, or
  `[b.model_dump() for b in resp.content]` when there is no `submit_answer` call (plain
  `{type, text}` / `{type, name, input}` dicts for fakes without `model_dump`); OpenAI the
  message content as returned (a string or `None`). `_anthropic` raises it when there is no
  tool call or `Answer(...)` fails; `_openai` raises it on any `(ValueError, TypeError)` from
  `json.loads` / `Answer(**data)` (covers content `None`, non-JSON, JSON that is not an object,
  and pydantic `ValidationError`, which is a `ValueError`). The original exception is chained
  (`raise ... from e`). Valid outputs are unchanged.
- `scripts/eval_run.py` - `RealRunner.answer` catches `ModelOutputError`: writes the cache file
  with the usual metadata plus `"invalid": true`, `"error"` and `"raw_payload"` (no `"raw"`),
  written with `json.dumps(..., default=str)` as a backstop so an unexpected payload type can
  never crash the write, copies it to `.eval-runs/<run>/raw/`, returns `(None, "invalid")`.
  A cached invalid file is reused as `"invalid"` (counted in `reused`, no second call: a wrong
  output is a finding, not a re-roll). `apply_real` maps `"invalid"` to status `INVALID_OUTPUT`
  with a note that keeps the retrieval status and points at the raw file (e.g. "retrieval FAIL;
  model output invalid, see raw/<file>"). `STATUSES` gains `INVALID_OUTPUT`; the report header
  and the console summary show its count; docstring explains it.
- `tests/test_llm_openai.py` (S2; owner review waived by TL decision 2026-11-17, see #187
  comment) - fake Anthropic client with an invalid tool input and with only a `text` block (no
  tool call); fake OpenAI client with non-JSON, with schema-invalid JSON and with
  `content=None`: each raises `ModelOutputError` whose `raw` is the payload and passes
  `json.dumps` without `default`.
- `tests/test_eval_run.py` - fake `generate` that raises `ModelOutputError`: payload on disk in
  cache and run `raw/`, `how == "invalid"`, `calls == 1`, next question still answered; a second
  runner reuses the invalid cache file with 0 calls; `apply_real(..., "invalid")` gives
  `INVALID_OUTPUT` and keeps the retrieval status in the note; `write_reports` counts it.
  New test `test_real_invalid_no_tool_call_is_saved`: `generate` raises the
  `ModelOutputError` that `_anthropic` itself builds from a fake response with a `text` block
  and no tool call; the cache file and the `raw/` copy are written, `how == "invalid"`, and the
  next question is still answered.
- `plans/0187-keep-invalid-model-output.md` (this file)

Not changed: `src/cee/ask.py` (`answer_for` passes the exception through; the app's ask page
already catches any exception and shows it), `src/cee/answer/schema.py`.

## Paid-call plan
0 real calls. The bug is in what happens after the provider returns; fake clients and a fake
`generate` reproduce the exact failure (an invalid tool input), so a real model adds nothing.
No question IDs are run against a paid model.

## Steps
1. `llm.py`: add `ModelOutputError`, raise it from `_anthropic` / `_openai` with a JSON-safe
   `raw`; tests in `tests/test_llm_openai.py`.
2. `eval_run.py`: catch in `RealRunner.answer`, write cache + raw copy (`default=str`),
   `"invalid"` path for a cached invalid file, `apply_real` -> `INVALID_OUTPUT` (retrieval status
   kept in the note), `STATUSES`, report/console counts, docstring; tests in
   `tests/test_eval_run.py`, including `test_real_invalid_no_tool_call_is_saved`.
3. Full `pytest` and `ruff` (if configured) on the mock.
4. End-to-end on the free path: `scripts/eval_run.py --real --max-calls 2 --questions Q25,Q29`
   with `LLM_PROVIDER=anthropic` but `cee.answer.llm._anthropic` swapped for a fake that returns
   `{"answer": "yes"}` for the first question (a small throwaway driver script in the
   scratchpad, not committed; no API key needed, no network). Check that the run finishes,
   `report.md` lists Q25 as `INVALID_OUTPUT` and Q29 as answered, `raw/` holds Q25's payload, and
   real calls = 2.
5. verify-cee skill on the mock (the `src/` change must not change the app's normal path), and
   a mock eval run against the latest baseline
   (`scripts/eval_run.py --baseline evals/baselines/corpus-2026-10-22/report.json`) to show the
   mock path's statuses and summary are unchanged apart from the new `INVALID_OUTPUT` count (0).
6. `/finish-task`: PR with "Closes #187"; the reviewer agent reviews and merges (`/tl-review`).

## Acceptance
- [ ] A fake client returning an invalid payload: the raw payload is on disk (cache file and
  `.eval-runs/<run>/raw/`), the question is reported as `INVALID_OUTPUT`, the run continues
  (`pytest tests/test_eval_run.py tests/test_llm_openai.py` -> pass)
- [ ] The paid-call count still includes the failed call (`runner.calls == 1` after one invalid
  output; report header "real calls 2 of max 2" in the step-4 end-to-end run)
- [ ] A no-tool-call Anthropic response (fake response with only a `text` block) is saved, not
  crashed on: `raw` is JSON-safe, the cache file and `raw/` copy are written, `how == "invalid"`,
  the next question is still answered (`pytest tests/test_eval_run.py -k
  test_real_invalid_no_tool_call_is_saved` -> pass)
- [ ] `_openai` with `content=None`, non-JSON or schema-invalid JSON raises `ModelOutputError`,
  never a bare `TypeError` / `JSONDecodeError` (`pytest tests/test_llm_openai.py` -> pass)
- [ ] An invalid output is never re-called: a second run reuses the cached invalid file (0 calls)
- [ ] Linked questions: Q25, Q29 (the #167 run that lost Q25's output) - step 4 end-to-end run
  with a fake provider: Q25 `INVALID_OUTPUT`, Q29 evaluated, report written
- [ ] Valid outputs unchanged: existing `test_real_cap_and_cache` and LLM request tests pass;
  full `pytest` green; verify-cee on the mock passes; mock eval vs
  `evals/baselines/corpus-2026-10-22/report.json` shows the same statuses, `INVALID_OUTPUT` 0
- [ ] 0 real model calls

## Progress log
- 2026-11-17 17:42 - plan written (branch `tl/187-keep-invalid-model-output` from main `36dba99`)
- 2026-11-17 17:46 - reviewer: PLAN CHANGES REQUESTED. Tagged the S2 files (owner review waived
  by the TL decision on #187, no S2 review step); `raw` always JSON-safe plus a `default=str`
  backstop and the named no-tool-call test; `_openai` catches `(ValueError, TypeError)` with a
  `content=None` test; retrieval status kept in the INVALID_OUTPUT note; mock eval vs baseline
  in step 5. Work moved to worktree `D:\ALLPROJECTS\EDJ\wt-187` (the main checkout was
  switched back to `main` by another session).
