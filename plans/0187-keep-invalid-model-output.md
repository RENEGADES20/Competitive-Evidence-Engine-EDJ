# 0187 - Keep a paid model output that fails validation

Issue: #187    Role: TL    Spec: `CLAUDE.md` "Paid API calls" step 3, `specs/answer-citations.md` (Answer JSON), `scripts/eval_run.py` docstring (eval runner)

## Goal
When a real model returns an answer that does not fit the `Answer` schema (or no answer tool
call at all), the eval runner keeps the raw provider payload on disk, reports the question as
`INVALID_OUTPUT`, counts the call against `--max-calls`, and moves on to the next question,
instead of crashing and losing what was paid for. The app keeps showing an error for such an
answer, as today (its error message now says the output was invalid).

## Files to change
- `src/cee/answer/llm.py` - new `ModelOutputError(RuntimeError)` carrying `raw` (the provider
  payload: Anthropic `block.input` or the list of content blocks when no `submit_answer` call;
  OpenAI message content as text) and `provider`. `_anthropic` raises it when there is no tool
  call or `Answer(...)` fails; `_openai` raises it when the content is not JSON or `Answer(...)`
  fails. The original exception is chained (`raise ... from e`). Valid outputs are unchanged.
- `scripts/eval_run.py` - `RealRunner.answer` catches `ModelOutputError`: writes the cache file
  with the usual metadata plus `"invalid": true`, `"error"` and `"raw_payload"` (no `"raw"`),
  copies it to `.eval-runs/<run>/raw/`, returns `(None, "invalid")`. A cached invalid file is
  reused as `"invalid"` (counted in `reused`, no second call: a wrong output is a finding, not a
  re-roll). `apply_real` maps `"invalid"` to status `INVALID_OUTPUT` with a note pointing at the
  raw file. `STATUSES` gains `INVALID_OUTPUT`; the report header and the console summary show
  its count; docstring explains it.
- `tests/test_llm_openai.py` - fake Anthropic client with an invalid tool input and with no tool
  call, fake OpenAI client with non-JSON and with schema-invalid JSON: each raises
  `ModelOutputError` whose `raw` equals the payload.
- `tests/test_eval_run.py` - fake `generate` that raises `ModelOutputError`: payload on disk in
  cache and run `raw/`, `how == "invalid"`, `calls == 1`, next question still answered; a second
  runner reuses the invalid cache file with 0 calls; `apply_real(..., "invalid")` gives
  `INVALID_OUTPUT`; `write_reports` counts it.
- `plans/0187-keep-invalid-model-output.md` (this file)

Not changed: `src/cee/ask.py` (`answer_for` passes the exception through; the app's ask page
already catches any exception and shows it), `src/cee/answer/schema.py`.

## Paid-call plan
0 real calls. The bug is in what happens after the provider returns; fake clients and a fake
`generate` reproduce the exact failure (an invalid tool input), so a real model adds nothing.
No question IDs are run against a paid model.

## Steps
1. `llm.py`: add `ModelOutputError`, raise it from `_anthropic` / `_openai`; tests in
   `tests/test_llm_openai.py`.
2. `eval_run.py`: catch in `RealRunner.answer`, write cache + raw copy, `"invalid"` path for a
   cached invalid file, `apply_real` -> `INVALID_OUTPUT`, `STATUSES`, report/console counts,
   docstring; tests in `tests/test_eval_run.py`.
3. Full `pytest` and `ruff` (if configured) on the mock.
4. End-to-end on the free path: `scripts/eval_run.py --real --max-calls 2 --questions Q25,Q29`
   with `LLM_PROVIDER=anthropic` but `cee.answer.llm._anthropic` swapped for a fake that returns
   `{"answer": "yes"}` for the first question (a small throwaway driver script in the
   scratchpad, not committed; no API key needed, no network). Check that the run finishes,
   `report.md` lists Q25 as `INVALID_OUTPUT` and Q29 as answered, `raw/` holds Q25's payload, and
   real calls = 2.
5. verify-cee skill on the mock (the `src/` change must not change the app's normal path).

## Acceptance
- [ ] A fake client returning an invalid payload: the raw payload is on disk (cache file and
  `.eval-runs/<run>/raw/`), the question is reported as `INVALID_OUTPUT`, the run continues
  (`pytest tests/test_eval_run.py tests/test_llm_openai.py` -> pass)
- [ ] The paid-call count still includes the failed call (`runner.calls == 1` after one invalid
  output; report header "real calls 2 of max 2" in the step-4 end-to-end run)
- [ ] An invalid output is never re-called: a second run reuses the cached invalid file (0 calls)
- [ ] Linked questions: Q25, Q29 (the #167 run that lost Q25's output) - step 4 end-to-end run with a
  fake provider: Q25 `INVALID_OUTPUT`, Q29 evaluated, report written
- [ ] Valid outputs unchanged: existing `test_real_cap_and_cache` and LLM request tests pass;
  full `pytest` green; verify-cee on the mock passes
- [ ] 0 real model calls

## Progress log
- 2026-11-17 17:42 - plan written (branch `tl/187-keep-invalid-model-output` from main `36dba99`)
