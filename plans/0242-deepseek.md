# 0242 - DeepSeek as an answer and planner provider

Issue: #242    Role: TL    Spec: specs/answer-citations.md (also specs/retrieval.md for the planner, ADR-020)

## Goal
`LLM_PROVIDER=deepseek` works end to end: the question planner and the answer call go to DeepSeek
through the OpenAI SDK with strict function tools, every untrustworthy output is saved as invalid and
never re-rolled, a 402 / 429 stops with a clear message, tests make 0 real calls, and the default of
`DEEPSEEK_THINKING` is chosen from a 12-call real check on Q1, Q22 and Q24.

## Inputs read
`src/cee/config.py`, `src/cee/answer/llm.py`, `src/cee/answer/schema.py`, `src/cee/retrieve/planner.py`,
`src/cee/ask.py`, `src/cee/app/views/ask_page.py` (line 105 shows any exception as "The answer could
not be built"), `scripts/eval_run.py` (`cache_key`, `plan_cache_key`, `RealRunner`), `tests/conftest.py`,
`tests/test_no_paid_calls.py`, `tests/test_llm_openai.py`, `tests/test_eval_run.py`, `.env.example`,
`docs/RUN.md` section 7, `specs/answer-citations.md` ("Invalid model outputs", strict tool input),
CLAUDE.md "Paid API calls", ADR-011/012/020, `D:\ALLPROJECTS\EDJ\cache\ev240\run-real.ps1` (the
`.env` copy pattern). Local DB: `sync-db -Check` -> up to date, `corpus-2026-11-19`.

## DeepSeek facts re-checked 2026-11-19 (api-docs.deepseek.com)
- `guides/tool_calls`: strict mode needs `base_url=https://api.deepseek.com/beta` and `"strict": true`
  on every function; every object lists all properties in `required` and has
  `additionalProperties: false`; `minItems` / `maxItems` / `minLength` / `maxLength` unsupported;
  "Strict mode works in both thinking and non-thinking mode".
- `api/create-chat-completion`: `max_tokens` default 8K without thinking, 64K with thinking (so it
  very likely counts reasoning tokens; the docs do not say, the real check records
  `completion_tokens_details.reasoning_tokens`). `thinking` omitted -> enabled. "`required` and named
  tool choices are not supported in thinking mode; the API returns a 400". `finish_reason`: `stop`,
  `length`, `content_filter`, `tool_calls`, `insufficient_system_resource`, `aborted`. Usage has
  `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens` (sum = `prompt_tokens`) and
  `completion_tokens_details.reasoning_tokens`. Function arguments: "the model does not always
  generate valid JSON, and may hallucinate parameters not defined by your function schema".
- `guides/thinking_mode`: OpenAI SDK passes `extra_body={"thinking": {"type": "enabled"|"disabled"}}`;
  default effort `high`; output carries `reasoning_content`.
- `quick_start/error_codes`: 401 bad key, 402 insufficient balance, 429 rate limit, 500 / 503 retry later.
- `quick_start/rate_limit`: "If the request has not started inference after 10 minutes, the server
  will close the connection"; empty keep-alive lines meanwhile (the SDK's JSON parser handles them).
- Models: `deepseek-v4-pro`, `deepseek-flash` (legacy `deepseek-v4-flash` names served by Flash).
  Prices are not on the pages fetched; the PR reports tokens (incl. cache hits), not dollars.

## Design (every provider switch point)
1. **`config.py`.** `Settings` gains `deepseek_model` (`DEEPSEEK_MODEL`, default `deepseek-v4-pro`),
   `deepseek_base_url` (`DEEPSEEK_BASE_URL`, default `https://api.deepseek.com/beta`) and
   `deepseek_thinking: bool` (`DEEPSEEK_THINKING`, parsed like `CEE_VECTORS`: on|true|1|yes /
   off|false|0|no / empty -> the default; anything else -> `ValueError`). The default is set in
   step 9 from the real check; until then `off` (see "Thinking default").
2. **`llm.py`.**
   - `deepseek_client()`: `openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=settings().deepseek_base_url,
     max_retries=0, timeout=httpx2-compatible 1200 s read / 30 s connect)` - above the server's
     10-minute close, and long enough for a 32k-token thinking answer. A missing / empty
     `DEEPSEEK_API_KEY` raises a clear `RuntimeError` before any client exists (never falls back to
     `OPENAI_API_KEY`).
   - Caps by thinking mode: `DEEPSEEK_MAX_TOKENS = {False: 20000, True: 32000}` (answer; off = the
     project's 20000, on = room for reasoning, since it shares `max_tokens`) and
     `DEEPSEEK_PLANNER_MAX_TOKENS = {False: 2000, True: 8000}` (off = `PLANNER_MAX_TOKENS`). Helper
     `answer_max_tokens(provider)` returns these for deepseek and `MAX_TOKENS` otherwise.
   - `deepseek_request(question, hits, plan, window)`: `model`, `max_tokens` (explicit), system
     prompt = `SYSTEM_PROMPT` + the same "MUST call submit_answer" line as Anthropic,
     `tools=[{"type": "function", "function": {"name": "submit_answer", "description": ...,
     "strict": True, "parameters": llm_output_schema()}}]`, user message from `build_user_message`,
     `extra_body={"thinking": {"type": "enabled"|"disabled"}}`. `tool_choice`: thinking off ->
     the named function (forced; allowed without thinking); thinking on -> `"auto"` (forced is a 400).
     No `temperature` (ignored in thinking mode; not set in either mode, so the modes differ only in
     thinking, tool_choice and caps). `reasoning_effort` not sent (default high).
   - Shared helpers used by the answer and the planner: `deepseek_create(client, request)` maps
     `openai.APIStatusError` 401 / 402 / 429 to a new `ProviderStop(RuntimeError)` with a plain
     message ("DeepSeek: insufficient balance (402); top up the account, then run again"; 429 rate
     limit; 401 key rejected); other errors propagate unchanged. `deepseek_tool_call(resp, name)` ->
     (tool call or None, finish_reason, usage, payload) where `usage` = `input_tokens`,
     `output_tokens`, `cache_hit_tokens`, `cache_miss_tokens`, `reasoning_tokens`, `tool_calls`
     (count), `thinking` (on/off) and `payload` = `message.model_dump(mode="json")` (content,
     `reasoning_content`, tool calls; a dict build for fakes).
   - `_deepseek(question, hits, client=None, plan=None, window=None)`. Invalid (`ModelOutputError`,
     saved, never re-rolled), checked in this order:
     a. `finish_reason` not in (`tool_calls`, `stop`): `length` (cut, even if the arguments parse),
        `content_filter` (stop_reason recorded as-is, treated like `refusal`), `insufficient_system_resource`,
        `aborted`; raw = the whole message payload.
     b. no `submit_answer` tool call; raw = payload.
     c. arguments not JSON (`json.loads` fails) or not an object; raw = the arguments string.
     d. pydantic failure (`Answer(**args)`); raw = the parsed arguments.
     e. `check_output` (empty answer; cut already caught by a).
     The answer's `stop_reason` = `finish_reason`, `usage` as above.
   - `generate`: `deepseek` branch. Module docstring lists the provider.
   - `request_version(provider)`: anthropic `strict-1` (unchanged), openai `None` (unchanged),
     deepseek `ds-strict-1-think-{on|off}-a{answer cap}-p{planner cap}` (e.g.
     `ds-strict-1-think-off-a20000-p2000`), so an output made in one thinking mode or cap is never
     reused for the other. Model and base model name are already in the keys.
   - `CUT_REASONS` unchanged; a `DEEPSEEK_OK = ("tool_calls", "stop")` constant.
3. **`planner.py`.**
   - `deepseek_plan_request(q, cap)`: same shape as the answer request with function `submit_plan`,
     `plan_schema(strict=True)` (no `minItems`), `strict: True`, `max_tokens =
     DEEPSEEK_PLANNER_MAX_TOKENS[thinking]`, same `tool_choice` / `extra_body` rule.
   - `call_planner` deepseek branch: `llm.deepseek_create`; `meta` gets `stop_reason` and `usage`;
     `PlannerOutputError` (raw saved) on: finish_reason not ok (`length` = cut), no `submit_plan` call,
     arguments not JSON, not an object. Same branch order as the answer.
   - **OpenAI planner length cut (gap found in the issue):** the openai branch raises
     `PlannerOutputError("planner output cut at max_tokens", content, stop)` when `finish_reason`
     is in `llm.CUT_REASONS`, before `json.loads` (today a cut that parses is accepted).
   - `ProviderStop` is not swallowed: `plan_question` re-raises it (before its `except Exception`
     fallback) so a 402 / 429 stops the question with the clear message instead of silently using
     the rule plan and failing again on the answer call.
   - `model_for`: `deepseek -> settings().deepseek_model`. `planner_max_tokens(provider)` helper
     (deepseek: by thinking mode; others `PLANNER_MAX_TOKENS`), used by eval_run's record.
4. **`ask.py`.** `model_name`: add `deepseek -> deepseek_model` (query_log `model` column). The
   `log_filters` docstring names deepseek among paid providers. No other change: `ask_page` already
   shows any exception (ProviderStop's message included).
5. **`scripts/eval_run.py`.** `RealRunner`: the mock message reads "anthropic, openai or deepseek";
   `self.max_tokens = llm.answer_max_tokens(provider)` (unchanged value for anthropic / openai, so
   their keys are unchanged); plan records' `max_tokens = planner.planner_max_tokens(provider)`;
   `request_version` already comes from `llm.request_version`. `ProviderStop` in `answer` or `plan`:
   nothing is saved (no output was produced), the run stops with `SystemExit("stopped: <message>")`;
   `plan`'s `except Exception` gets an `except llm.ProviderStop: raise` before it. Docstring line on
   `--real` names deepseek. `cache_key` / `plan_cache_key` signatures unchanged.
6. **`.env.example`.** Provider comment `mock | anthropic | openai | deepseek`; `DEEPSEEK_API_KEY=`,
   `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta` (comment:
   /beta is needed for strict tools), `DEEPSEEK_THINKING=<chosen default>` with one comment line.
7. **`docs/RUN.md`.** Step 1 `.env` paragraph names deepseek; section 7 gains "Ask with DeepSeek"
   with a PowerShell block and a bash block each for the app and for `eval_run.py --real`
   (`$env:LLM_PROVIDER="deepseek"` / `LLM_PROVIDER=deepseek ...`), plus a line on 402 / 429.
8. **Docs naming the provider list** (one-line edits): `specs/answer-citations.md` ("Invalid model
   outputs" table rows for DeepSeek finish reasons, bad-JSON arguments; strict paragraph: DeepSeek
   strict via /beta, request version; line 191 provider list), `README.md` line 145, CLAUDE.md
   "Paid API calls" first line (`anthropic`, `openai` or `deepseek`). **Not** `docs/DECISIONS.md`:
   ADR-012's provider list is left to #244 (ADR-021), named in the PR.

## Test guards (0 real calls)
- `tests/conftest.py`: also stubs `llm.deepseek_client` with `_blocked`; removes every `DEEPSEEK_*`
  variable; sets `DEEPSEEK_BASE_URL=http://127.0.0.1:9`. Docstring updated (three builders).
- `tests/test_no_paid_calls.py`: `test_environment_is_cleared` expects `DEEPSEEK_BASE_URL` left
  (closed port) and no other `DEEPSEEK_*`; `test_client_builders_are_blocked` covers
  `deepseek_client`; the guard test adds `llm.generate(provider="deepseek")` -> blocked and
  `planner.plan_question(q, "deepseek")` -> fallback "blocked", `sent == []`. New control test: the
  real `deepseek_client` (captured at import, as `test_llm_openai.py` does) with a dummy
  `DEEPSEEK_API_KEY` sends exactly one request, to `http://127.0.0.1:9/chat/completions`, seen by the
  httpx2 counter (proves the counter sees DeepSeek traffic and the base URL is honored); without a
  key it raises before any request.

## Unit tests (fake clients; new `tests/test_llm_deepseek.py`, plus `tests/test_planner.py`, `tests/test_eval_run.py`)
- D1 schema: a recursive checker over `llm_output_schema()` and `plan_schema(strict=True)`: every
  object has all properties required and `additionalProperties: false`; no `minItems`, `maxItems`,
  `minLength`, `maxLength` anywhere.
- D2 answer request, thinking off: `strict` true, `parameters == llm_output_schema()`, `max_tokens`
  20000, `tool_choice` names `submit_answer`, `extra_body` thinking disabled, model from settings.
  Thinking on: `tool_choice == "auto"`, thinking enabled, `max_tokens` 32000.
- D3 planner request: same checks for `submit_plan` (max_tokens 2000 / 8000).
- D4 valid tool call -> Answer, `llm_called`, `stop_reason` `tool_calls`, usage with cache hit / miss
  and reasoning tokens.
- D5 invalid, each saved with its raw: `finish_reason` `length` with valid arguments; `content_filter`;
  no tool call (text only); arguments `"{not json"` (raw is the string); arguments a JSON list;
  pydantic failure (`behavior: "maybe"`); empty answer. Each raises `ModelOutputError` with
  provider `deepseek` and usage.
- D6 errors: fake client raising `openai.APIStatusError` 402 / 429 (built with an `httpx2.Response`)
  -> `ProviderStop` with the plain message, from `generate` and from `plan_question` (not a fallback
  plan); a 500 from the planner -> fallback plan (call counted), unchanged behavior.
- D7 planner outputs: valid -> dict; length cut, no tool call, bad JSON -> `PlannerOutputError` with
  raw and stop_reason; meta has usage.
- D8 OpenAI planner: `finish_reason == "length"` with JSON content -> `PlannerOutputError` (new).
- D9 `request_version`: anthropic `strict-1`, openai `None`, deepseek differs between thinking on
  and off; `model_name` / `model_for` deepseek -> `deepseek-v4-pro`.
- D10 config: `DEEPSEEK_THINKING` on / off / empty / bad value; defaults of model and base URL.
- D11 client: the real builder (captured before conftest) with a dummy key: `max_retries == 0`,
  timeout read > 600 s, base URL `/beta/`; no key -> RuntimeError.
- D12 eval_run: `RealRunner("deepseek", ...)` with a fake `generate` / planner: the answer and plan
  records carry the deepseek request version and max_tokens; switching `DEEPSEEK_THINKING` changes
  both keys (no reuse); a `ProviderStop` saves nothing and exits with the message; an invalid
  output is saved and reused as invalid on a second run (no second call).

## Steps
1. Code (Design 1-8) and tests; `pytest` with `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-242\src`, all green.
2. `ruff` as CI runs it (if configured).
3. **Mock checks, 0 calls.** `eval_run.py` (mock, `--as-of 2026-11-17`, `--baseline
   evals\baselines\corpus-2026-11-19\report.json`, `--out .eval-runs\0242-mock`): 30/30 chunk lists
   unchanged (UNCHANGED for all). `verify-cee` (mock driver) green. Logs to `D:\ALLPROJECTS\EDJ\cache\ev242\`.
4. Commit and push code; record the mock-runs sha in `ev242\mruns-sha.txt`.
5. **Real check (last, one script, both modes back to back)** - see "Paid-call plan".
6. **Thinking default** chosen by the rule below, after both real runs; set it in `config.py` and
   `.env.example` (D10 pins it). The real runs set `DEEPSEEK_THINKING` explicitly, so the placeholder
   default never affects them; the code gate runs before the paid command, so this later commit
   does not touch it. pytest, mock eval and verify-cee are re-run after the change (0 calls).
7. **App check (2 calls)**: Streamlit with `LLM_PROVIDER=deepseek` and the chosen default, Q1 asked
   on the Ask page by a small Playwright script in `ev242\` (not committed): screenshot, footer
   `LLM called: True`, the query_log row's `model = deepseek-v4-pro` and `llm_calls`.
8. Evidence committed: `docs/results/0242-deepseek-check.md` (per run: question, mode, planner
   source, finish_reason, valid / invalid and why, behavior vs expected, citation flags, tokens incl.
   cache hit / reasoning, wall time; the decision) and `docs/results/0242-deepseek-raw/*.json` (the
   12 raw records the runs saved). Full run folders and logs in `D:\ALLPROJECTS\EDJ\cache\ev242\`.
9. `/finish-task`: PR with "Closes #242", Verification lists every real call, DeepSeek named for
   ADR-012 / #244; `gh pr checks` green.

## Paid-call plan (CLAUDE.md "Paid API calls")
- **Why the mock cannot show it:** the mock never sends a request; only DeepSeek shows whether
  strict tools are accepted on /beta in both thinking modes, whether outputs validate, cut or skip
  the tool, what usage looks like, and how the two modes behave on citations and gaps.
- **Questions:** Q1 (one firm, `answer`), Q22 (five firms, largest input, `answer`), Q24 (five
  firms, `gap_with_adjacent`, a trap). Each one run through the full flow = 1 planner call + 1 answer
  call (all three are searchable in token-budget mode, so the planner is called).
- **Runs:** R-off `DEEPSEEK_THINKING=off`, then R-on `DEEPSEEK_THINKING=on`, each
  `eval_run.py --real --max-calls 6 --questions Q1,Q22,Q24 --as-of 2026-11-17 --baseline ...
  --out .eval-runs\0242-real-{off|on}`, `PLANNER=on`, `PLANNER_MAX_PARTS=4`, model
  `deepseek-v4-pro`. **Cap 6 per run, 12 total.** Plus **2 calls** for the app check (step 7, Q1 once
  more in the chosen mode, planned here). **Total cap: 14 calls.** No re-run: an invalid, cut or
  failed output is a finding, saved and reported. A 402 / 429 stops the run (no output, nothing to
  re-roll); continuing after a top-up / wait needs the coordinator, and the cached outputs are reused.
- **Execution** (as #240's `run-real.ps1`): `D:\ALLPROJECTS\EDJ\cache\ev242\run-real.ps1` logs HEAD,
  `git status --short` (must be empty) and `git diff <mruns sha> HEAD -- src scripts config` (must be
  empty) to `ev242\head-log.txt`, exits before touching `.env` otherwise; then in `try` copies
  `D:\ALLPROJECTS\EDJ\repo\.env` to the worktree (never read or printed), sets `PYTHONPATH`,
  `PLANNER`, `PLANNER_MAX_PARTS`, `DEEPSEEK_THINKING` per run, runs R-off then R-on with output to
  `ev242\real-{off|on}.log`; `finally` removes the worktree `.env` and the variables and logs that it
  is gone. Run in the background. Afterwards copy each run folder (`raw/`, `report.json`,
  `report.md`) to `ev242\real-{off|on}\`.
- **Saved:** every planner and answer record (question, prompt / planner version, model, request
  version, max_tokens, chunk ids, raw output or raw payload, finish_reason, usage with cache hit /
  miss and reasoning tokens).

## Thinking default (decision rule, fixed before the calls)
Compare R-off and R-on, in this order; the first criterion that differs decides:
1. Valid outputs out of 6 (3 plans with source `model` + 3 valid answers).
2. Behavior equal to `expected_behavior` (Q1 answer, Q22 answer, Q24 gap_with_adjacent), out of 3.
3. Citation discipline, summed over the 3 answers: unmatched citations + claims without chunk ids +
   number-check flags + code-added part gaps (fewer is better).
Tie on all three -> **off** (forced tool call possible, fewer output tokens, faster). The table
with every number and the reading of the claims goes in the PR. If neither mode gives a valid answer
on a question, that is reported as a finding; the default still follows the rule.

## Files to change
- `src/cee/config.py` - three DeepSeek settings.
- `src/cee/answer/llm.py` - client, requests, `_deepseek`, `ProviderStop`, caps, `request_version`, docstring.
- `src/cee/retrieve/planner.py` - deepseek request and branch, OpenAI length cut, `ProviderStop`
  re-raise, `model_for`, `planner_max_tokens`.
- `src/cee/ask.py` - `model_name`, docstring.
- `scripts/eval_run.py` - RealRunner messages, max_tokens records, ProviderStop stop.
- `tests/conftest.py`, `tests/test_no_paid_calls.py`, `tests/test_llm_deepseek.py` (new),
  `tests/test_planner.py`, `tests/test_eval_run.py`.
- `.env.example`, `docs/RUN.md`, `specs/answer-citations.md`, `README.md` (one line), `CLAUDE.md`
  (one line).
- `docs/results/0242-deepseek-check.md`, `docs/results/0242-deepseek-raw/` (evidence).
- `plans/0242-deepseek.md` - this plan.
Not changed: `docs/DECISIONS.md` (#244), prompts (`PROMPT_VERSION` v4.1, `PLANNER_VERSION` plan-v2),
`schema.py`, the anthropic / openai answer paths, the anthropic planner, verify-cee driver and
recipes (no user-facing feature changes; the app check is a one-off script in `ev242`).

## Acceptance
- [ ] `LLM_PROVIDER=deepseek` answers Q1 in the running app (step 7: screenshot, footer, query_log row).
- [ ] Tests D1-D12 and the guard tests pass: strict flag and explicit `max_tokens` on both tools;
      cut, no-tool, bad-JSON and pydantic-failure outputs saved as invalid; 402 / 429 stop; OpenAI
      planner rejects `length`; 0 real calls (httpx2 counter `sent == []`).
- [ ] Real: 6 question-runs (Q1, Q22, Q24 x thinking on / off), 12 calls at most, every raw record
      saved with usage; thinking default chosen by the rule above, evidence in the PR and
      `docs/results/0242-deepseek-check.md`.
- [ ] Mock `eval_run.py` 30/30 chunk lists unchanged vs `evals/baselines/corpus-2026-11-19`;
      pytest, verify-cee (mock) and `gh pr checks` green.

## Progress log
- 2026-11-19 21:12 - plan written; DeepSeek docs re-checked (tool_calls, create-chat-completion,
  thinking_mode, error_codes, rate_limit, models). Worktree `D:\ALLPROJECTS\EDJ\wt-242`, branch
  `tl/242-deepseek` from origin/main af873e6. DB up to date (corpus-2026-11-19).
