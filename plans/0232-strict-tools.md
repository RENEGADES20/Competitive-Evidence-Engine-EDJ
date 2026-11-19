# 0232 - Strict tool use on the Anthropic answer and planner calls (Q22 empty tool call)

Issue: #232    Role: TL    Spec: specs/answer-citations.md (S2; owner review waived, TL decision
2026-11-17, #187). Also touches ADR-020 (one sentence: the planner tool is strict on Anthropic, no
`maxItems`; the TL merges ADR edits, so the reviewer escalates the PR to the TL for the merge).
Depends on #230 (PR #231, merged at e749466; `main` f9fd055).

## Goal
On the Anthropic path the API itself enforces the input schema of the answer tool (`submit_answer`)
and the planner tool (`submit_plan`), so a tool input that breaks the schema (Q22's
`{"answer": null}`) cannot come back. A response that still ends without a valid tool call stays an
invalid output: a finding, saved, never re-rolled.

## Facts (2026-11-19, read only, 0 calls)
- Base: `main` f9fd055; DB `cee` = `corpus-2026-11-17` (`sync-db.ps1 -Check`: up to date). Branch
  `tl/232-strict-tools`.
- **Q22 #230 record** (`D:\ALLPROJECTS\EDJ\cache\ev230\real\Q22-586fba087e1902a0f72f04b0.json`, prompt
  v4.1, claude-sonnet-5-5, `max_tokens` 20000): `invalid: true`, `raw_payload = {"answer": null}`,
  `stop_reason` `tool_use`, usage 102,835 input / 4,223 output tokens, blocks `thinking`, `tool_use`.
  The error: `answerable` and `behavior` missing. Not a cut: the model called the tool with an input
  the schema forbids (missing required keys, an unknown key `answer`).
- **Today's requests**: `llm.anthropic_request` sends `tools=[{name, description, input_schema:
  llm_output_schema()}]`, no `strict`, `tool_choice {"type": "auto"}`, no `thinking` field (adaptive
  by default on claude-sonnet-5-5). `planner.anthropic_plan_request` the same with
  `plan_schema(cap=cap)` (`parts`: `minItems 1`, `maxItems cap`). The OpenAI requests already send
  `strict: true` (answer `response_format.json_schema.strict`, planner with `plan_schema(strict=True)`,
  which has no `minItems` / `maxItems`). Clients `max_retries=0` (#230).
- **How enforcement is requested** (claude-api skill, `shared/tool-use-concepts.md` "Structured
  outputs" and "Tool Choice Options", `python/claude-api/tool-use.md` "Strict Tool Use"; live docs
  `platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use`, read 2026-11-19):
  `"strict": true` as a **top-level field of the tool definition**, next to `name`, `description`,
  `input_schema` (not on `tool_choice`, no beta header, plain `client.messages.create`). Installed SDK
  `anthropic` **1.9.0**: `anthropic.types.ToolParam` has `strict: bool` ("When true, guarantees
  schema validation on tool names and inputs"); our request is a plain dict, so the field goes
  through as is. claude-sonnet-5-5 is in the docs' supported-models list.
- **What strict guarantees**: "Tool `input` strictly follows the `input_schema`" (grammar-constrained
  sampling) **when the model calls the tool**. It does not force a call: on claude-sonnet-5-5 forced
  `tool_choice` (`any` / `tool`) returns a 400 (skill: "Forced tool use removed ... Claude Sonnet
  5.5"), the documented pattern is `auto` + `strict: true` + an instruction naming the tool, "check
  that one was made". So "no `submit_answer` call" stays possible and stays invalid (#187 rule).
  Strict works with extended thinking (skill: "Works with: Batches API, streaming, token counting,
  extended thinking"). On `stop_reason` `refusal` the skill says "the output may not match your
  schema" and "never execute that turn's tools"; on `max_tokens` the output may be incomplete
  (already invalid since #230).
- **Strict-mode schema rules** (structured-outputs docs "JSON Schema limitations", shared by JSON
  outputs and strict tools; the SDK's own `anthropic.transform_schema`, exported at top level in
  1.9.0, applies the same rules): supported: all basic types, `enum` / `const` (scalars), nested
  objects, `anyOf` / `allOf`, `$ref` / `$defs`, `required`, `additionalProperties` **must be false**
  on every object, array `minItems` **0 or 1 only**, a fixed list of string formats. Not supported:
  recursive schemas, `oneOf`, numerical constraints, `minLength` / `maxLength`, array constraints
  beyond `minItems` 0/1 (so **no `maxItems`**), `additionalProperties` other than false. An
  unsupported feature returns a **400** (docs). `transform_schema` moves an unsupported keyword into
  the description (`{maxItems: 4}`).
- **Offline check of today's schemas** (`transform_schema(s) == s`, i.e. nothing to strip):
  `llm_output_schema()` **passes as is** (objects all `additionalProperties: false`, every property
  required, `behavior` a string `enum`, nested `claims` / `adjacent` / `gaps` objects).
  `plan_schema(cap=4)` **fails**: `parts.maxItems 4` is not supported (`minItems 1` is).
  `plan_schema(strict=True)` passes.
- **Cache keys** (`scripts/eval_run.py`): answer key = (id, text, `PROMPT_VERSION`, snapshot,
  provider, model, chunk ids [, `{"max_tokens"}` if not 8000] [, `{"parts"}`] [, `{"window"}`]);
  planner key = (id, text, `PLANNER_VERSION`, snapshot, provider, model, cap, `PLANNER_MAX_TOKENS`,
  resolved query). Neither contains the tool definition, so today a strict request would silently
  reuse a non-strict output. Invalid records (answer and plan) are reused and reported, never
  re-called.
- Saved plan-v2 outputs (`.eval-runs/cache`, claude-sonnet-5-5, `corpus-2026-11-17`, cap 4): **Q1,
  Q22** only; none for Q10, Q21, Q23.
- Gate 4 (`docs/results/gate4-report.md`): Q10 `answer` PASS; Q21 `answer` PASS; Q23
  `gap_with_adjacent` FAIL (bank `answer`; NEXT item 5, the known behavior choice); Q1 `answer` PASS
  (also #230 v4.1). Baseline (`evals/baselines/corpus-2026-11-17`): Q10 214 / Q21 216 / Q23 170
  passages (~60k / 60k / 47k tokens est.).

## Design

### 1. Strict answer tool (`llm.py`)
`anthropic_request` adds `"strict": True` to the `submit_answer` tool. Schema unchanged
(`llm_output_schema()` already meets the strict rules; a test pins that). `tool_choice` stays
`{"type": "auto"}` (forced is a 400 on this model); system prompt unchanged (it already says "You
MUST return the result by calling the submit_answer tool"). No `thinking` / effort change.
OpenAI request unchanged.

### 2. Strict planner tool (`planner.py`)
`anthropic_plan_request` adds `"strict": True` to `submit_plan`, with a schema strict mode accepts:
`plan_schema` for Anthropic keeps `parts.minItems 1` and **drops `maxItems`** (the one change strict
mode requires). The part cap still reaches the model in the system prompt ("in at most {max_parts}
parts") and the user message ("Most parts: N"), and code still cuts extra parts (`validate_plan`:
"cut to N parts", logged). Shape: `plan_schema(strict=False)` (the Anthropic tool) now returns
`minItems: 1` only; `plan_schema(strict=True)` (OpenAI) unchanged; the `cap` parameter is removed
from `plan_schema` if nothing else uses it. Planner prompt and `PLANNER_VERSION` text unchanged.

### 3. Invalid outputs stay findings (`llm.py`, `planner.py`)
- No tool call -> invalid (answer, #187) / rule-plan fallback (planner), as today.
- Tool input that fails `Answer(**raw)` -> invalid, as today (the API should no longer produce one;
  the check stays as the last line).
- `stop_reason` `max_tokens` -> invalid, as today (#230).
- **New, small**: `stop_reason` `refusal` -> invalid for the answer (added to the cut rule as its own
  message "Model output stopped by refusal") and planner output rejected (rule-plan fallback), even
  when a tool input is present: the skill says a refusal can stop a tool input mid-way and that the
  input may not match the schema, so strict's guarantee does not hold there. Named in the PR as a
  small extension of the Goal ("ends without a valid tool call"). Spec table gets the row, which
  keeps the API's `stop_reason` `refusal` (invalid) apart from the model's own answer `behavior:
  refuse` with `answerable` false (a valid answer, unchanged).
- Never re-rolled: `max_retries=0` and the eval's reuse of invalid records are unchanged.

### 4. Cache keys and request version (`llm.py`, `planner.py`, `eval_run.py`)
The Anthropic request changes (a new tool field and, for the planner, a schema change), so a saved
non-strict output must not be reused for a strict request. Version bump on the **request**, not on
the prompt texts (they are unchanged, and the OpenAI request is unchanged):
- `llm.ANTHROPIC_REQUEST_VERSION = "strict-1"` and `llm.request_version(provider)` -> `"strict-1"`
  for `anthropic`, `None` otherwise.
- `cache_key(..., request=None)` and `plan_cache_key(..., request=None)` add `{"request": "strict-1"}`
  only when given; `RealRunner` passes `request_version(provider)`. Effect: every Anthropic answer and
  plan key changes (saved #229 / #230 Anthropic outputs, including Q22's invalid record and the Q1 /
  Q22 plan-v2 plans, are no longer reused by an Anthropic run); OpenAI and mock keys are byte-identical
  to today (literal tests). Records save `"request_version"` next to `prompt_version` /
  `planner_version`. `PROMPT_VERSION` stays `v4.1`, `PLANNER_VERSION` stays `plan-v2` (texts
  unchanged); the request version is stated in the spec and ADR-020.
- Consequence for the real run: **no planner output is reusable** (keys changed), so Q1 and Q22
  get new plans; Q22's retrieval may differ from #230's (named in Risks; its chunk list vs #230 is
  reported).

### 5. Tests (fakes and offline, 0 calls)
- Request payload: `anthropic_request(...)["tools"][0]["strict"] is True`, `tool_choice ==
  {"type": "auto"}`; `anthropic_plan_request(...)["tools"][0]["strict"] is True`; OpenAI requests
  unchanged (strict already).
- **Strict-mode schema check, offline, two ways**: (a) a small rule walker in the test (no SDK, so it
  runs in CI): every object has `additionalProperties: false` and `required` equal to all its
  properties; no keyword outside the set our schemas use and strict mode supports (`type,
  properties, required, additionalProperties, items, enum, description, title, format` with a
  supported format, `minItems` 0 or 1; `const`, `anyOf`, `allOf`, `$ref` are supported by strict mode
  but deliberately not allowed by the walker, so a schema that starts using them needs a test change
  first); no `oneOf`, `maxItems`, `minimum`, `maximum`, `minLength`, `maxLength`, `pattern`; applied
  to the exact `input_schema` of both Anthropic tools. (b) with the SDK
  (`pytest.importorskip("anthropic")`; `requirements.txt` pins `anthropic==1.9.0`, so it also runs
  in CI): `anthropic.transform_schema(s) == s` for both tool schemas (the SDK would strip nothing). Plus a negative case: today's
  `plan_schema` with `maxItems` fails both checks.
- Invalid fakes: a fake Anthropic response whose tool input is `{"answer": None}` (the #230 Q22
  payload, i.e. what a strict API would not send but a fake can) -> `ModelOutputError`, and through
  `RealRunner.answer` saved as `invalid` with `raw_payload`, `stop_reason`, `usage`, reported
  `INVALID_OUTPUT`, no second call on re-run; a fake with no tool call (text only, `end_turn`) ->
  invalid; a fake with `stop_reason` `refusal` and a valid input -> invalid; planner fake with
  `refusal` -> rule-plan fallback, record `invalid`.
- Keys: `cache_key` / `plan_cache_key` without `request` equal today's literals; with
  `request="strict-1"` differ; `RealRunner` on provider `anthropic` uses the strict key (a saved
  record under the old key is not reused: fake call counted), on `openai` the old key.
- Existing tests that pin the planner request schema or `plan_cache_key("anthropic")` updated.

## Files to change
- `src/cee/answer/llm.py` - `strict: True` on `submit_answer`; `ANTHROPIC_REQUEST_VERSION`,
  `request_version()`; `refusal` stop -> invalid.
- `src/cee/retrieve/planner.py` - `strict: True` on `submit_plan`; `plan_schema` without `maxItems`
  for Anthropic; `refusal` stop -> `PlannerOutputError`.
- `scripts/eval_run.py` - `request` in `cache_key` / `plan_cache_key`; `RealRunner` passes it and
  saves `request_version` in answer and plan records.
- `tests/test_llm_openai.py`, `tests/test_planner.py`, `tests/test_eval_run.py` (and
  `tests/test_schema.py` for the schema walker if it fits better there) - as in Design 5.
- `specs/answer-citations.md` - strict answer tool on Anthropic, request version `strict-1`, the
  refusal row in "Invalid model outputs".
- `docs/DECISIONS.md` - ADR-020 amendment (#232), one short paragraph: planner tool strict on
  Anthropic, `maxItems` dropped (cap in the prompt and in code), request version in the plan key.
- `plans/0232-strict-tools.md` (this file).
Not changed: prompt texts and versions, retrieval, `config/`, `evals/`, the mock, the UI, the OpenAI
requests, `MAX_TOKENS`, thinking settings, verify-cee recipe and driver.

## Steps
1. Design 1-3 with tests (fakes, offline schema check). `pytest -q`.
2. Design 4 keys with tests (literals: OpenAI / no-request keys unchanged). `pytest -q`.
3. Offline proof (0 calls), scratch `D:\ALLPROJECTS\EDJ\cache\ev232\offline.txt` (not committed): the
   two Anthropic request tool dicts as sent (JSON), `transform_schema` diff (empty) for both, the
   #230 Q22 `raw_payload` run through `Answer(**raw)` (invalid) and listed against the schema
   (missing `answerable`, `behavior`, `claims`, `adjacent`, `gaps`; unknown `answer`).
4. **Mock eval**: `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0232-mock`; scratch diff: 30/30
   chunk lists identical (same order), 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22,
   0 forbidden, no PASS -> FAIL, 0 real calls. Any difference stops the work.
5. Docs: spec, ADR-020 amendment.
6. **verify-cee** (port 8599 checked free): all features PASS (mock; the request builders changed).
7. **Real runs last** (below), judged; table in `D:\ALLPROJECTS\EDJ\cache\ev232\real-table.txt`.
8. `/finish-task`: PR "Closes #232" (or "Part of #232" with the open items), with the enforcement
   field and SDK version, schema change, key change, mock diff, verify-cee run, actual
   `real_calls` / `reused`, model, per-question `stop_reason` / output tokens / behavior / verdict,
   the TL pre-approval quoted, deviations (refusal row; request version instead of prompt / planner
   version bump; planner cache not reusable). **`gh pr checks <PR#>` all green on the PR head**
   before `/finish-task` completes (CI installs `requirements.txt`, which pins `anthropic==1.9.0`,
   so both the rule-walker and the `transform_schema` tests run there).

## Paid-call plan (CLAUDE.md "Paid API calls"; TL note on #232, 2026-11-19)
TL note, quoted: "The real calls planned in the approved ExecPlan are approved under the W10
pre-approval." Last, on finished code after steps 1-6 pass: **5 questions, one run each, planner +
answer = 2 calls each, cap `--max-calls 10`**: Q22 (target), Q10, Q21, Q23 (other five-firm inputs,
~47-60k est. / ~100k real input tokens), Q1 (regression). Model `claude-sonnet-5-5`, prompt v4.1,
planner plan-v2, request `strict-1`, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; .venv\Scripts\python.exe
scripts\eval_run.py --real --max-calls 10 --questions Q1,Q10,Q21,Q22,Q23 --as-of 2026-11-17
--baseline evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0232-real`.
**Expected: 10 real calls, 0 reused.** Planner: the request changed, so the planner key carries
`strict-1` and matches no saved plan (Q1 and Q22 had plan-v2 plans under the non-strict key; Q10,
Q21, Q23 had none): 5 planner calls. Answer: every Anthropic answer key changed: 5 answer calls. The
cap equals the expected count; the report's actual `real_calls` / `reused` are quoted. Rough cost:
~430k input tokens over the 5 answers (~$0.9 at $2 / M) plus output (at most 5 x 20k, ~$1 at
$10 / M) plus 5 small planner calls (~$0.1). Raw outputs (planner and answer, request meta,
`request_version`, `stop_reason`, `usage`) in the run's `raw/`, copied to
`D:\ALLPROJECTS\EDJ\cache\ev232\real`.
Why the mock cannot show it: the mock never calls a tool; only a real call shows that the API
accepts both strict schemas (a schema it rejects is a 400 before any output) and that Q22's large
five-firm input now yields a schema-valid answer. One run each, no re-runs. A missing tool call, an
input that still fails, a cut or a refusal is `INVALID_OUTPUT` (a finding, its acceptance item
open); a failed or rejected planner call falls back to the rule plan (counted, a finding); a 400 on
the schema is a failed call (counted, a finding, fixed offline before any further call). No other
call path.

## Risks
- **Strict does not force a call**: with `auto` the model can still answer in text or stop; that
  stays invalid (finding). The PR reports it from `usage.blocks`.
- **The API may reject a schema the offline checks pass** (a rule not in the docs or the SDK, e.g. a
  size limit): the first planner call would 400. Counted, reported, no retry in the run.
- **Strict may change outputs**: grammar-constrained sampling could change answers on Q10 / Q21 /
  Q1; judged against `passes_if` and Gate 4 behavior.
- **Planner without `maxItems`**: the model could write more than 4 parts; code cuts them (logged
  correction), as for OpenAI today.
- **Q22 attribution**: Q22 gets a new plan (key changed), so its input may differ from #230's
  102,835 tokens; a pass is attributed to strict only together with the chunk list compared to
  #230's. Not a clean A/B, stated.
- **Q23**: expected to stay `gap_with_adjacent` (NEXT item 5); a move to `answer` is reported, not
  claimed as a fix.

## Acceptance
- [ ] Real (`.eval-runs/0232-real`, <= 10 calls): **Q22** returns a valid answer (not
  `INVALID_OUTPUT`) with claims per firm (every one of the five firms has a claim or a gap; a firm
  that does not report NNA marked as not reporting, never zero, never a substitute presented as
  NNA), `stop_reason` recorded (`tool_use`), judged PASS against `passes_if`.
- [ ] Real: **Q10, Q21, Q23, Q1** return valid outputs (not `INVALID_OUTPUT`) and keep their Gate 4
  behavior: Q10 `answer` PASS, Q21 `answer` PASS, Q23 `gap_with_adjacent` as at Gate 4 (NEXT item 5),
  Q1 `answer` PASS; `stop_reason` and output tokens recorded for all five; actual `real_calls` /
  `reused` quoted (expected 10 / 0).
- [ ] Tests: `strict: true` on the Anthropic answer and planner tools (request payload); the
  strict-mode schema check passes offline for both tool schemas (rule walker and SDK
  `transform_schema` fixed point, both locally and in CI) and fails for a `maxItems` schema; a fake `{"answer":
  null}` input, a no-tool response and a `refusal` stop are saved as invalid (planner: fallback),
  never re-called; OpenAI and no-request keys unchanged (literals), Anthropic keys carry `strict-1`.
- [ ] Mock (`.eval-runs/0232-mock`): 30/30 chunk lists identical to the baseline, 29 PASS / 1 FAIL
  (Q19), refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL, 0 real calls.
- [ ] `pytest -q` passes; verify-cee all features PASS.
- [ ] Spec and the ADR-020 amendment updated.
- [ ] `gh pr checks <PR#>` all green on the PR head before `/finish-task` completes.

## Progress log
- 2026-11-19 04:32 - plan written. Branch `tl/232-strict-tools` from `main` f9fd055 (PR #231 merged
  at e749466); DB `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`). Read: issue #232 + TL note,
  specs/answer-citations.md, CLAUDE.md "Paid API calls", ADR-012 / 019 / 020, `llm.py`, `schema.py`,
  `planner.py`, `eval_run.py` (keys, `RealRunner`, invalid records), the #230 Q22 record and plan,
  the `anthropic` 1.9.0 SDK (`ToolParam.strict`, `transform_schema`), the claude-api skill (strict
  tool use, structured outputs, forced tool choice on claude-sonnet-5-5) and the live strict tool
  use / structured outputs docs; offline `transform_schema` check of both schemas (answer passes,
  planner fails on `maxItems`).
- 2026-11-19 04:38 - plan approved by the reviewer agent (issuecomment-7006685532, reviewed
  7686bf5), no blocking item. Non-blocking notes applied to this plan: (1) the `transform_schema`
  test runs in CI too (`requirements.txt` pins `anthropic==1.9.0`); (2) the rule walker does not
  allow `const` / `anyOf` / `allOf` / `$ref` (supported by strict mode, unused by our schemas: the
  difference is stated in Design 5); (3) the spec row keeps the API `stop_reason` `refusal`
  (invalid) apart from the model's `behavior: refuse` with `answerable` false (valid).
  `origin/main` unchanged (f9fd055).
- 2026-11-19 04:41 - steps 1-2 (commit 775a245): `strict: True` on `submit_answer` and
  `submit_plan`; planner Anthropic schema `minItems 1`, no `maxItems` (`plan_schema(strict=False)`,
  `cap` parameter removed); API `stop_reason` `refusal` -> invalid answer / planner fallback;
  `llm.ANTHROPIC_REQUEST_VERSION = "strict-1"`, `llm.request_version()`; `cache_key` /
  `plan_cache_key(..., request=None)`, `RealRunner` passes it and saves `request_version` in answer
  and plan records. Tests: 15 new test functions (`test_llm_openai.py` 8 incl. the strict rule walker
  and the SDK `transform_schema` check, `test_planner.py` 2, `test_eval_run.py` 5); the planner
  request test and one reuse test updated. `pytest -q` 698 passed.
- 2026-11-19 04:42 - step 3 offline proof (`D:/ALLPROJECTS/EDJ/cache/ev232/offline.txt`, 0 calls):
  both tool dicts as sent carry `"strict": true`; `transform_schema` leaves both schemas unchanged
  (SDK 1.9.0); the #230 Q22 `raw_payload` `{"answer": null}` fails `Answer(**raw)`: missing
  `answerable`, `behavior`, `claims`, `adjacent`, `gaps`, unknown `answer`. Step 4 mock
  (`.eval-runs/0232-mock`, diff `D:/ALLPROJECTS/EDJ/cache/ev232/mock-diff.txt`): 30/30 chunk lists
  identical (same order), 29 PASS / 1 FAIL (Q19), no PASS -> FAIL, all UNCHANGED, refusal gap 5/5,
  keyed 22/22, 0 forbidden, 0 real calls. Step 5 docs (commit 1702528): spec (refusal row kept
  apart from `behavior: refuse`, strict note), ADR-020 amendment.
- 2026-11-19 04:44 - step 6 verify-cee (doctor PASS, port 8599 free): all 9 features PASS,
  `.verify-runs/20261119-044306-1702528`. Next: the planned real run.
