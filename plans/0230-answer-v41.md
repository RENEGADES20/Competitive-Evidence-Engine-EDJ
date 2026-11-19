# 0230 - Answer v4.1: no empty answer on large inputs, newest first across parts in time windows

Issue: #230    Role: TL    Spec: specs/answer-citations.md (S2; owner review waived, TL decision
2026-11-17, #187). Also touches ADR-019 (one amendment: the answer's output cap; the TL merges ADR
edits, issue note 2026-11-19, so the reviewer escalates the PR to the TL for the merge) and
docs/ARCHITECTURE.md (Answer JSON: two code-owned fields). Depends on #215 (PR #229, merged at
49daf4b; `main` bba9acf).

## Goal
No answer is ever empty because the output ran out or came back empty: a cut at `max_tokens`, or an
answer with no claims, no adjacent items and no gaps, is an invalid output (a finding), never shown
or scored as an answer. Every real output records why it stopped and how many tokens it used. The
answer's output cap is raised for large inputs. Prompt v4.1: a question with a time window reads
newest first across the whole answer, whatever its parts.

## Facts (2026-11-19, read only, 0 calls)
- Base: `main` bba9acf; DB `cee` = `corpus-2026-11-17` (`sync-db.ps1 -Check`: up to date). Branch
  `tl/230-answer-v41`.
- **Q22 saved output** (`D:\ALLPROJECTS\EDJ\cache\ev215\real\Q22-08a2840ac285e7c767c17f2f.json`,
  prompt v4, `max_tokens` 8000, claude-sonnet-5-5): the record holds `raw = {answerable: true,
  behavior: "answer", claims: [], adjacent: [], gaps: []}` and no `stop_reason`, no usage. `raw` is
  `Answer.model_dump()` **after** pydantic, not the tool input the model sent: keys the schema does
  not know are dropped silently (pydantic's default `extra="ignore"`), and text blocks outside the
  tool call are never read (`_anthropic` reads only the `submit_answer` block). So the saved file
  cannot tell apart (a) a tool input cut at `max_tokens` whose unfinished `claims` array was
  dropped, (b) items sent under a key the schema ignores, (c) the answer written outside the tool
  call. The issue's "max_tokens cut" is likely, not proven.
- Q22 input: 209 passages, ~60,165 tokens (`tokens_est`, chars / 4, `report.json` of the #229 run);
  plan-v2 split it into 4 parts (quarterly NNA for all five, definitions for all five, Merrill's
  closest equivalent, Schwab/RJF variants). Earlier Q22 outputs (30 passages, v2/v3) were 4.5-9.9k
  characters with 10-15 claims; a five-firm, by-quarter grid over 209 passages with `part_id` on
  every item needs more.
- Call timing from the saved `at` stamps (each stamp is taken before its call): the Q22 answer call
  took ~52 s (03:35:40 -> next record 03:36:34, minus Q25's 1.8 s search), the same as Q25 (~52 s,
  8.8k output characters, 53k input) and Q12 / Q7 (~50 s, 11.5-12.1k characters). So the model spent
  several thousand tokens on Q22 that were lost; timing alone cannot say whether it reached 8000.
- **Thinking counts against `max_tokens`**: `anthropic_request` sends no `thinking` field; on
  claude-sonnet-5-5 an omitted `thinking` runs adaptive thinking (claude-api skill, model table
  cached 2026-11-03: "Omitting thinking: runs adaptive", effort default `high`, thinking text
  omitted by default). Thinking tokens are billed as output and come off the same 8000, so a large
  input with a hard question can leave little room for the tool input. Not visible today (no usage
  saved); the new `usage` record shows it.
- **SDK non-streaming limit** (installed `anthropic` 1.9.0, `_base_client._calculate_nonstreaming_timeout`):
  a non-streaming `messages.create` raises when `3600 * max_tokens / 128000 > 600` s, i.e.
  `max_tokens > 21,333`, or above `MODEL_NONSTREAMING_TOKENS[model]` (claude-sonnet-5-5 is not in
  that table; only Opus 4 / 4.1 ids at 8,192). The #213 plan's "~21k" is confirmed. Model output
  ceiling for claude-sonnet-5-5: 128K (claude-api skill model notes; not queried live, 0 calls).
- **Stop reason on a tool answer**: a response that ends with a tool call has `stop_reason`
  `tool_use`, not `end_turn` (claude-api skill, Stop Reasons). The issue's "its stop_reason is
  `end_turn`" is read as "a natural stop, not `max_tokens`": `tool_use` (or `end_turn`). Deviation
  named in the PR.
- **Q26 saved output** (`...\ev215\real\Q26-8c6982e8922e51b1c73451af.json`): window
  `2026-08-19..2026-11-17` (`query.window`), 46 passages (~14,638 tokens), 4 parts (results,
  advisors, outlook, news). The 16 claims run p1, p1, p1, p1, p2 x 6, p3 x 3, p4 x 3: newest first
  inside some parts (p2 2026-11-12 -> 09-02), but the answer restarts at each part (p3 starts
  2026-10-29 after p2 ended 2026-09-02 / 10-16; p4 runs 09-29, 09-16, 10-19). v4's system prompt has
  "Questions about recent change (what is new, what changed since a given date): newest first." and
  the Parts rule "groups the evidence under the part it was found for"; the model followed the
  grouping.
- **Cache keys** (`scripts/eval_run.py`): answer key = (id, text, `PROMPT_VERSION`, snapshot,
  provider, model, chunk ids [, `{"max_tokens"}` when not 8000] [, `{"parts"}` when a plan]).
  Planner key = (id, text, `PLANNER_VERSION`, snapshot, provider, model, cap, `PLANNER_MAX_TOKENS`,
  resolved query); it does not include the answer's `max_tokens` or `PROMPT_VERSION`.
- Saved plan-v2 outputs (`.eval-runs/cache`, claude-sonnet-5-5, `corpus-2026-11-17`, cap 4,
  `max_tokens` 2000, valid): **Q1, Q22, Q26** (#229 run); **none for Q11, Q24**.
- Earlier real outputs for the regression questions: Q11 v3 (Gate 4 / ev212, 30 passages)
  `gap_with_adjacent` (bank `answer`; Gate 4 FAIL, known NEXT item 5: no headcount for MS, SCHW,
  MER in the corpus); Q24 v3 at the #213 pick (214 passages, 60k) `gap_with_adjacent`, 11 claims,
  not cut at 8000; Q1 v4 (#229) `answer`, 24 claims, PASS.
- The planner already rejects a cut at `max_tokens` (`PlannerOutputError`, falls back to the rule
  plan); its valid outputs save no `stop_reason` either.
- The Ask page catches any exception from `ask()` and shows "The answer could not be built.
  <Error>: <message>" (`ask_page.py` line 101), so a `ModelOutputError` there is visible, not empty.
- Tests pinning today's cap: `tests/test_prompt.py:167`, `tests/test_eval_run.py:622,643`.

## Design

### 1. Output budget: flat `MAX_TOKENS = 20000` (`llm.py`), stated in ADR-019
- Rule: one cap for every answer call, **20000**, the largest round value under the SDK's
  non-streaming limit (21,333; a test fails if `MAX_TOKENS` would make the SDK refuse a
  non-streaming call). Not a size rule: the cap is a ceiling, billed only for tokens produced, so a
  small question costs the same at 8000 or 20000; a size rule would add a threshold to tune and still
  miss a small input with a long answer or long thinking. 2.5x today's cap covers Q22's lost output
  plus thinking with room; a cut at 20000 is still an invalid output (a finding, the next step
  would be streaming, not in this issue).
- **Cache key change, stated**: `cache_key` is unchanged in code; with `max_tokens` 20000 every new
  answer key carries `{"max_tokens": 20000}`. Saved keys made at 8000 keep their keys (the
  `!= 8000` rule stays), and a run at 20000 never reuses an output made at 8000. In this issue the
  prompt bump to v4.1 changes every answer key anyway, so no reusable answer is lost by the cap.
  Planner keys do not contain the answer cap or prompt version: the saved Q1, Q22, Q26 plans stay
  reusable.
- Planner cap (`PLANNER_MAX_TOKENS` 2000) unchanged (planner out of scope).

### 2. Every real output records why it stopped (`schema.py`, `llm.py`, `planner.py`, `eval_run.py`)
- `Answer.stop_reason: str = ""` and `Answer.usage: dict = {}` (code-owned, not in
  `llm_output_schema()`; older saved outputs parse with the defaults). `_anthropic` sets
  `stop_reason = resp.stop_reason` and `usage = {"input_tokens", "output_tokens"` (from
  `resp.usage`, `None` when a fake has none) `, "blocks": [types of resp.content]}` (e.g.
  `["thinking", "tool_use"]`: shows whether thinking ran). `_openai`: `finish_reason` and
  `prompt_tokens` / `completion_tokens`. The mock leaves both empty. They travel with the answer into
  `query_log.answer` (no schema change) and into the eval cache's `raw`.
- `ModelOutputError` gets `usage` (as `stop_reason` today). Its `raw` stays the provider payload.
- Eval (`RealRunner.answer`): a valid record saves top-level `stop_reason`, `usage` next to `raw`;
  an invalid record saves `stop_reason`, `usage`, `raw_payload` (today: no usage). The report's real
  records get `stop_reason` and `output_tokens` (also for cached and invalid outputs; "" / None for
  a saved output made before #230). `report.md` unchanged.
- Planner (only bookkeeping, behavior unchanged): `call_planner(..., meta=None)` fills
  `meta["stop_reason"]`, `meta["usage"]` when a dict is passed; `RealRunner.plan` saves them in the
  plan record. Planner key and `PLANNER_VERSION` unchanged, so saved plans are reused.

### 3. Invalid outputs (`llm.py`, `eval_run.py`)
New `llm.check_output(answer)` raising `ModelOutputError`, called by `_anthropic` / `_openai` on a
fresh output and by `RealRunner.answer` on a cached one:
1. **Cut**: Anthropic `stop_reason == "max_tokens"` (OpenAI `finish_reason == "length"`) ->
   invalid ("Model output cut at max_tokens (<n> output tokens)"), **even when the partial input
   validates** (a cut answer is never trusted). `raw` = every content block as JSON (thinking and
   the partial tool input), so the cut is diagnosable.
2. **Empty**: no claims, no adjacent items, no gaps and not a refusal -> invalid ("Model output
   has no claims, adjacent items or gaps"). `raw` = the tool input as the model sent it (before
   pydantic), so a misnamed key (Fact (b)) is visible. **A refusal is exempt** only when it is
   behavior `refuse` **with `answerable` false** (the prompt's definition, reviewer note 3), so an
   empty `{answerable: true, behavior: "refuse"}` is still invalid; no bank question expects
   `refuse` ("none yet"); a cut refusal is still caught by rule 1. Deviation from the issue's
   wording, named in the PR.
3. Checked on the model's own output, **before** code adds gaps (`check_parts` part gaps, caveats):
   the #229 Q22 answer only looked non-empty because code added 4 `part_gap` gaps.
4. A cached output that fails rule 2 (or a saved `stop_reason` `max_tokens`) is reported as
   `INVALID_OUTPUT` on reuse, never re-called (same as #187's invalid records).
In the eval an invalid output is `INVALID_OUTPUT` (the retrieval status kept in the note, #187); in
the app it is the Ask page's existing error message. Never re-rolled (CLAUDE.md "Paid API calls" 4).

### 3b. No SDK retries on paid calls (TL-requested change, 2026-11-19, after plan approval)
`llm.anthropic_client()` and `llm.openai_client()` (the only builders; the answer call and the
planner both use them) build the SDK client with `max_retries=0`. The SDK default (2) would resend
a request after a transport timeout (at 20000 the non-streaming timeout is the full 600 s), a second
paid request counted once. Now a timeout or transport error is a reported failure: the eval saves
it as a failed call (planner: rule-plan fallback) and never repeats it. Test: the built clients get
`max_retries=0` (fake SDK modules, and the real `anthropic.Anthropic` when installed).

### 4. Prompt v4.1 (`prompt.py`, `llm.py`)
`PROMPT_VERSION = "v4.1"`. The rest of v4 stays word for word except:
- **Recency rule** (Writing claims) replaced: "Questions about recent change (what is new, what
  changed since a given date) and questions with a time window: order the claims and the adjacent
  items newest first across the whole answer, by the date of what each reports, not part by part;
  each item keeps its part_id. Gaps come after." And the sentence before it, "When the same topic
  appears in several periods, keep them apart and oldest to newest, so a change over time is
  visible.", gets "(in a question with a time window, newest first instead)" so the two rules no
  longer conflict.
- **Parts rule**: one sentence added: "The grouping is how the evidence is listed, not the order of
  the answer."
- **User message**: when the resolved query has a window or a date range (`query.window` /
  `query.date_range`, filtered in SQL), one line after the question: "Time window: <from> to <to>
  (only passages dated in it were searched). Order the answer newest first across all parts."
  `build_user_message(question, hits, plan=None, window=None)`; `generate` / the request builders
  pass it; `ask.answer_for` passes the query's window. No window: the message is byte-identical to
  v4's (test).
- **Cache key**: `cache_key(..., window=None)` adds `{"window": [from, to]}` only when a window is
  given (the message now depends on it; `--as-of` moves a relative window); without one the key
  shape is today's (test with the literal).
- Leak test re-run on the **whole v4.1 prompt** and on the new user-message line: no question ID, no
  6-word run shared with any `passes_if` (standard wording exempt, Q28 / Q30 as today) or any
  question text (no exception). Q26's `passes_if` ("Items newest first, each with one line ...",
  "Nothing older than the window sneaks in") must not be copied.
- Grid, part, behavior and standard-wording rules are otherwise unchanged.

## Files to change
- `src/cee/answer/llm.py` - `MAX_TOKENS` 20000 (comment: SDK limit, ADR-019), `check_output`,
  `stop_reason` / `usage` on answers and on `ModelOutputError`, window line, `window` through
  `generate` / requests.
- `src/cee/answer/schema.py` - `Answer.stop_reason`, `Answer.usage` (code-owned).
- `src/cee/answer/prompt.py` - v4.1 (recency rule, oldest-to-newest exception, grouping sentence).
- `src/cee/ask.py` - `answer_for` passes the query window to `generate`.
- `src/cee/retrieve/planner.py` - `call_planner(..., meta=None)` (bookkeeping only).
- `scripts/eval_run.py` - `RealRunner`: `check_output` on cached outputs, `stop_reason` / `usage` in
  valid, invalid and plan records, `window` in `cache_key`, `stop_reason` / `output_tokens` in real
  report records.
- `tests/test_llm_openai.py`, `tests/test_eval_run.py`, `tests/test_prompt.py`,
  `tests/test_schema.py`, `tests/test_planner.py`, `tests/test_part_check.py` - as needed (below).
- `specs/answer-citations.md` - output cap 20000, invalid outputs, `stop_reason` / `usage`, v4.1
  window order.
- `docs/ARCHITECTURE.md` - Answer JSON: `stop_reason`, `usage` (code-owned).
- `docs/DECISIONS.md` - ADR-019 amendment (#230): the answer's output cap 20000 and why (thinking
  shares the cap, SDK non-streaming limit 21,333, a cut is invalid, key change).
- `plans/0230-answer-v41.md` (this file).
Not changed: retrieval (`fts.py`), the planner's prompt / version / cap, `config/`,
`evals/questions.yaml`, `evals/expected_chunks.yaml`, the mock baseline, the UI (the Ask page's
existing error path shows an invalid output), the verify-cee recipe and driver (no user feature
changes; a real-only path the mock cannot reach).

## Steps
1. **Diagnosis note (0 calls)**: scratch `D:\ALLPROJECTS\EDJ\cache\ev230\diagnosis.txt` (not
   committed): the Q22 / Q26 Facts above (saved record fields, sizes, timing table for the 9 #229
   answer calls, Q26 part order with each claim's newest cited `published_at`).
2. **Budget + stop reason + invalid rules, with tests** (fakes, no SDK call):
   - a fake Anthropic response with `stop_reason` `max_tokens` and a tool input that validates ->
     `ModelOutputError`, `stop_reason` `max_tokens`, `usage` kept, `raw` = all blocks; in the eval it
     is saved as `invalid` with `stop_reason` and `usage` (`INVALID_OUTPUT` in the report);
   - an empty valid-shaped tool input (`{"answerable": true, "behavior": "answer"}`, the #229 Q22
     shape) -> invalid, `raw` = the input as sent; same with a misnamed list key (`{"answerable":
     true, "behavior": "answer", "items": [...]}`); `refuse` with no claims stays valid;
   - a valid response -> the answer and the eval record carry `stop_reason` (`tool_use`) and `usage`
     (`output_tokens`, `blocks`); report record has `stop_reason` / `output_tokens`;
   - a cached empty output (the #229 Q22 `raw` literal) -> `INVALID_OUTPUT` on reuse, no call;
   - OpenAI: `finish_reason` `length` -> invalid; usage saved;
   - `MAX_TOKENS == 20000`, `anthropic_request(...)["max_tokens"] == 20000`; with the SDK installed
     (`pytest.importorskip("anthropic")`), its `_calculate_nonstreaming_timeout(MAX_TOKENS,
     MODEL_NONSTREAMING_TOKENS.get(model))` does not raise (CI has no SDK: skipped there);
   - `cache_key` without window equals today's literal; at 20000 differs from 8000 (existing test
     kept); the existing 8000 / 16000 tests updated to the new cap;
   - planner: a fake valid plan call fills `meta` (`stop_reason`, `usage`); plan record saves them;
     `plan_cache_key` unchanged (literal).
   `pytest -q`.
3. **Prompt v4.1 + window line** and tests: version; new recency sentence and the
   oldest-to-newest exception present, v4's recency sentence gone; grouping sentence present; the
   user message with a window has the line, without one is byte-identical to v4's (literal from a
   fixture plan); `answer_for` passes the window; leak test over the whole v4.1 prompt and the
   window line (question text and `passes_if`, standard wording exempt as today). `pytest -q`.
4. **Offline replay (0 calls)**, scratch `D:\ALLPROJECTS\EDJ\cache\ev230\replay.py` (not committed):
   rebuild Q22 and Q26 hits from the saved plan-v2 plans with `search_parts` (`--as-of`
   2026-11-17 window) and check the chunk lists equal the #229 run's (209 / 46); write the v4.1
   user messages to `...\ev230\user-message-Q22.txt` / `-Q26.txt` with their sizes (chars / 4) and
   the Q26 window line; run the saved #229 Q22 and Q26 raws through `check_output` (Q22 ->
   invalid "no claims, adjacent items or gaps"; Q26 valid).
5. **Mock eval**: `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0230-mock`; scratch diff vs the
   baseline: 30/30 chunk lists identical (same order), 29 PASS / 1 FAIL (Q19), refusal gap 5/5,
   keyed 22/22, 0 forbidden, no PASS -> FAIL, 0 real calls. Any difference stops the work.
6. **Docs**: spec, ARCHITECTURE, ADR-019 amendment.
7. **verify-cee** (port 8599 checked free): all features PASS (mock; the answer path changed:
   `generate` signature, new fields in `query_log.answer`).
8. **Real runs last** (paid-call plan below), judged; tables in `...\ev230\real-table.txt`.
9. `/finish-task`: PR "Closes #230" (or "Part of #230" with the missed items) with the diagnosis,
   the budget rule and key change, the mock diff, verify-cee run, actual `real_calls` / `reused`,
   model, per-question `stop_reason` / output tokens, judgements, the TL pre-approval quoted, the
   two deviations (stop reason `tool_use`; `refuse` exempt from the empty rule). **`gh pr checks
   <PR#>` all green on the PR head** before `/finish-task` completes (CI: `requirements.txt` only, no
   Postgres, no SDK credentials).

## Paid-call plan (CLAUDE.md "Paid API calls"; TL note on #230, 2026-11-19)
TL note, quoted: "The real calls planned in the approved ExecPlan are approved under the W10
pre-approval." Last, on finished code after steps 2-7 pass: **5 questions, one run each, planner +
answer = up to 2 calls each, cap `--max-calls 10`**: Q22, Q26 (targets), Q11, Q24 (five-firm, ~60k
inputs: the cap and the invalid rules on large inputs), Q1 (regression). Model `claude-sonnet-5-5`,
prompt v4.1, planner plan-v2, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; .venv\Scripts\python.exe
scripts\eval_run.py --real --max-calls 10 --questions Q1,Q11,Q22,Q24,Q26 --as-of 2026-11-17
--baseline evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0230-real`.
**Expected: 7 real calls, 3 reused.** Planner: Q1, Q22, Q26 reuse their saved plan-v2 outputs (same
planner version, snapshot, model, cap, planner cap and resolved query as #229), so they search
exactly #229's parts; Q11 and Q24 have no saved plan: 2 planner calls. Answer: v4.1 and the 20000
cap miss every saved answer: 5 answer calls. If the plan reuse misses, up to 10 calls, inside the
cap; the report's actual `real_calls` / `reused` are quoted. Rough cost: ~235k input tokens over
the 5 answers (~$0.5 at $2 / M) plus output (at most 5 x 20k, ~$1 at $10 / M). Raw outputs (planner
and answer, request meta, `stop_reason`, `usage`) in the run's `raw/`, copied to
`D:\ALLPROJECTS\EDJ\cache\ev230\real`.
Why the mock cannot show it: the mock never reads the prompt, never thinks, never runs out of
output and always cites its top 3 passages; only a model call shows whether Q22's five-firm answer
fits the new cap, how many output tokens it uses, and whether Q26's items come newest first. The
invalid rules themselves are proven offline (fakes, the saved #229 Q22 raw).
One run each, no re-runs. A cut or empty output is `INVALID_OUTPUT` (a finding, its acceptance item
open), a failed planner call falls back to the rule plan (counted, a finding). No other call path.

## Risks
- **Q22's cause stays unproven if it now passes**: a pass at 20000 with `output_tokens` > 8000 points
  to the cut; a pass under 8000 points to a one-off empty output. The PR reports which, from the
  saved `usage`.
- **Thinking eats the cap**: adaptive thinking (no `thinking` field) shares the 20000. Not changed
  here (no thinking or effort setting in the issue); the saved `usage.blocks` and `output_tokens`
  show it, and a cut is a finding.
- **Longer, costlier answers**: the cap only bounds output; a five-firm answer may now produce 10k+
  output tokens (~$0.1 each). Reported per question.
- **SDK upgrade**: a later SDK could list claude-sonnet-5-5 in `MODEL_NONSTREAMING_TOKENS` below
  20000 and refuse the call before it is made (no cost); the SDK-limit test catches it locally.
- **`refuse` exemption**: an empty refusal is accepted. No bank question expects `refuse`; a
  refusal on a question expecting another behavior already FAILs on behavior.
- **Newest first by prompt, not code**: the order is the model's; the real-table computes it (each
  claim's newest cited `published_at`) so the judgement is not by eye. Code does not reorder (a claim
  citing several dates has no single date).
- **In-sample**: Q26 drove the window wording; Q22 drove the cap. Q1, Q11, Q24 are the check.
- **Regression attribution**: Q11 and Q24 run with a planner for the first time (2 new plan-v2
  calls); a change there may come from the plan, not v4.1. Their chunk lists vs the baseline are in
  the PR.

## Acceptance
- [x] Tests (fakes, 0 calls): a fake response with `stop_reason` `max_tokens` is saved as invalid with
  its `stop_reason` and `usage`, even when its partial input validates; an empty valid-shaped answer
  (and one with a misnamed list key) is invalid with the input as sent saved; `refuse` with no
  claims stays valid; a valid output saves `stop_reason` and `usage` (answer, cache record, report
  record); a cached empty output is `INVALID_OUTPUT` on reuse with no call; OpenAI `length` is
  invalid; the planner record saves `stop_reason` / `usage`.
- [x] Tests: `MAX_TOKENS == 20000` in the request; the SDK's non-streaming check accepts it (skipped
  without the SDK); `cache_key` without window equals today's literal; with window differs;
  `plan_cache_key` unchanged.
- [x] Tests: `PROMPT_VERSION == "v4.1"`; new recency rule, oldest-to-newest exception and grouping
  sentence present, v4 recency sentence gone; window line only when the query has a window, the
  message without one byte-identical to v4's; leak test (whole v4.1 prompt + window line) passes.
- [x] Replay (0 calls): Q22 / Q26 chunk lists equal #229's (209 / 46); the saved #229 Q22 raw is
  invalid under `check_output`, Q26's valid; v4.1 user messages and sizes written.
- [x] Mock (`.eval-runs/0230-mock`): 30/30 chunk lists identical to the baseline, 29 PASS / 1 FAIL
  (Q19), refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL, 0 real calls.
- [x] `pytest -q` passes; verify-cee all features PASS.
- [ ] (open: Q22 INVALID_OUTPUT, tool input `{"answer": null}`, `stop_reason` `tool_use`, 4,223 output tokens: not a cut) Real (`.eval-runs/0230-real`, <= 10 calls): **Q22** has claims for every firm that reports net
  new assets, and every one of the five firms has a claim or a gap (a non-reporting firm marked
  as not reporting, never zero, never a substitute presented as NNA); judged PASS against
  `passes_if`; `stop_reason` `tool_use` (or `end_turn`), not `max_tokens`; output tokens recorded.
- [x] (0 inversions over 23 claims, parts interleaved; PASS, borderline on "why it might matter") Real: **Q26** claims are newest first across the whole answer (no inversion of the claims'
  newest cited `published_at`, ties allowed; computed in the real-table) and judged PASS against
  `passes_if` (one line on why each item might matter; nothing older than the window).
- [x] (Q1 answer PASS, Q11 gap_with_adjacent as Gate 4, Q24 gap_with_adjacent PASS; all `tool_use`) Real: **Q11, Q24, Q1** are not empty (not `INVALID_OUTPUT`), keep their behavior (Q11
  `gap_with_adjacent` as in Gate 4 / v3, bank `answer` known NEXT item 5; Q24 `gap_with_adjacent`;
  Q1 `answer` and PASS against `passes_if`); `stop_reason` and output tokens recorded for all five.
- [x] Spec, ARCHITECTURE and the ADR-019 amendment updated.
- [x] (PR #231, pytest pass on fbe2fc2) `gh pr checks <PR#>` all green on the PR head before `/finish-task` completes.

## Progress log
- 2026-11-19 03:59 - plan written. Branch `tl/230-answer-v41` from `main` bba9acf (PR #229 merged
  at 49daf4b); DB `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`). Read: issue #230 + TL note,
  specs/answer-citations.md, CLAUDE.md "Paid API calls", ADR-019, ADR-020 (incl. the #215
  sentence and the #224 amendment), plans/0215-part-gaps.md, `llm.py`, `prompt.py` (v4),
  `schema.py`, `ask.answer_for`, `eval_run.py` (`RealRunner`, `cache_key`, invalid records),
  `planner.call_planner`, the #229 Q22 / Q26 raws, plans and `report.json` sizes, earlier Q11 / Q22 /
  Q24 raws, the `anthropic` 1.9.0 non-streaming check.
- 2026-11-19 04:04 - plan approved by the reviewer agent (issuecomment-7005930218, reviewed
  08b57d1), no blocking item. Coordinator notes applied: (1) the PR says the ~52 s timing does not
  favour the cut and attributes Q22 only from `usage.output_tokens`; (2) TL decision: `max_retries=0`
  on the real Anthropic / OpenAI clients (answer and planner), with a test (Design 3b, a
  TL-requested change); (3) the refusal exemption needs `answerable` false; (4) the PR justifies the
  planner bookkeeping by the Goal, behavior unchanged; (5) the PR states adaptive thinking only as
  far as `usage.blocks` shows a thinking block.
- 2026-11-19 04:10 - steps 2-3 (commit 0481913): `MAX_TOKENS` 20000, `check_output` (cut / empty,
  refusal only with `answerable` false), `Answer.stop_reason` / `usage`, `ModelOutputError.usage`,
  OpenAI `finish_reason` / usage, `max_retries=0` on both client builders, `call_planner(meta=)`,
  eval: `stop_reason` / `usage` in valid, invalid and plan records, `check_output` on cached outputs,
  `window` in `cache_key`, `stop_reason` / `output_tokens` in real report records; `ask.answer_window`
  (window and date range overlap) passed to `generate`; prompt v4.1 (recency rule across parts,
  oldest-to-newest exception, grouping sentence) and the window line. Tests: 21 new test functions
  (`test_llm_openai.py` 11, `test_eval_run.py` 7, `test_prompt.py` 3); version and cap pins moved to
  v4.1 / 20000; test fakes take `window` / `meta`.
- 2026-11-19 04:11 - steps 1 and 4 (`D:/ALLPROJECTS/EDJ/cache/ev230/replay.py`, `diagnosis.txt`,
  `replay.txt`, 0 calls): the #229 Q22 / Q26 records save no `stop_reason` or usage; answer-call
  timing Q22 ~52.7 s vs Q25 ~52.4 s (8.9k output characters), Q12 ~51.9 s (12.1k), Q7 ~50.0 s
  (11.7k): the timing does not favour a cut, Q22 is attributed only from the new
  `usage.output_tokens`. Q26 v4 claims by newest cited `published_at`: 5 inversions (restarts at
  each part, and multi-item claims). Replay: Q22 209 / Q26 46 passages, chunk lists identical to
  #229; v4.1 user messages ~67.4k (Q22) / ~16.3k (Q26) tokens (chars / 4) plus a ~2.2k-token system
  prompt; Q26's message carries "Time window: 2026-08-19 to 2026-11-17 ..."; the saved #229 Q22 raw
  is invalid under `check_output` ("no claims, adjacent items or gaps"), Q26's valid.
- 2026-11-19 04:12 - step 5 mock (`.eval-runs/0230-mock`, `.../ev230/mock-diff.txt`): 30/30 chunk
  lists identical (same order), 29 PASS / 1 FAIL (Q19), no PASS -> FAIL, refusal gap 5/5, keyed
  22/22, 0 forbidden, recall@pool 0.814 / @final 0.654, 0 real calls. Step 6 docs (commit ed77643):
  spec (v4.1 window order, cap 20000, invalid outputs, `max_retries=0`), ARCHITECTURE Answer JSON,
  ADR-019 amendment.
- 2026-11-19 04:13 - step 7 verify-cee (`doctor` PASS; port 8599 free): all 9 features PASS,
  `.verify-runs/20261119-041311-ed77643`.
- 2026-11-19 04:19 - step 8 real run (started 04:15:14, after every mock check, on commit ed77643;
  `.eval-runs/0230-real`, raw copied to `D:/ALLPROJECTS/EDJ/cache/ev230/real`, table
  `.../ev230/real-table.txt`, answers `.../ev230/answers-dump.txt`): **7 real calls, 3 reused**
  (planner reused for Q1, Q22, Q26; planner called for Q11, Q24; 5 answer calls), as expected;
  claude-sonnet-5-5, prompt v4.1, cap 20000. Every answer response has a `thinking` block before
  the tool call (`usage.blocks`); input tokens (tokenizer) 26.8k-102.8k, well above the chars / 4
  estimates. Per question (stop_reason, output tokens incl. thinking, behavior, verdict vs
  `passes_if`): **Q1** `tool_use`, 8,099, `answer`, PASS (channels management credits, dated per
  call, 2024 vs 2026 kept apart); **Q11** `tool_use`, 6,259, `gap_with_adjacent` (as Gate 4 / v3;
  bank `answer`, NEXT item 5), status FAIL on behavior as in Gate 4, not empty; **Q22** `tool_use`,
  4,223, **INVALID_OUTPUT**: the tool input was `{"answer": null}` (102,835 input tokens): not a cut,
  a near-empty tool call after thinking; the empty #229 output was most likely the same failure,
  not `max_tokens` (attributed from `usage`, as planned); not re-run (finding, item open);
  **Q24** `tool_use`, **11,885**, `gap_with_adjacent`, PASS (no derived ratio; "not like-for-like"
  answered with reasons per firm); **Q26** `tool_use`, 7,105, `answer`, 23 claims newest first across
  parts (0 inversions, earliest 2026-08-19), PASS, borderline on "one line on why it might matter".
  Q1 and Q24 would have been cut at the old 8000 cap (8,099 and 11,885 output tokens). PR is
  "Part of #230" (Q22 open).
  `pytest -q` 683 passed.
- 2026-11-19 04:22 - step 9 /finish-task: PR #231 opened ("Part of #230", Q22 open; ADR-019 amendment, escalated to the TL for the merge); origin/main unchanged (bba9acf), no merge needed; `gh pr checks 231` pytest pass on fbe2fc2 (38 s).
