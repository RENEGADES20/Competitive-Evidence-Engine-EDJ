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
  will close the connection"; a non-streaming request gets empty lines while it waits (the SDK's
  JSON parser handles them). Nothing is documented about lines during inference.
- Models: `deepseek-v4-pro`, `deepseek-flash` (legacy `deepseek-v4-flash` names served by Flash).
  Prices are not on the pages fetched; the PR reports tokens (incl. cache hits), not dollars.

## Design (every provider switch point)
1. **`config.py`.** `Settings` gains `deepseek_model` (`DEEPSEEK_MODEL`, default `deepseek-v4-pro`),
   `deepseek_base_url` (`DEEPSEEK_BASE_URL`, default `https://api.deepseek.com/beta`) and
   `deepseek_thinking: bool` (`DEEPSEEK_THINKING`, parsed like `CEE_VECTORS`: on|true|1|yes /
   off|false|0|no / empty -> the default; anything else -> `ValueError`). The default is set in
   step 6 from the real check; until then `off` (see "Thinking default").
2. **`llm.py`.**
   - `deepseek_client()`: `openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=settings().deepseek_base_url,
     max_retries=0, timeout=Timeout(3600 s, connect=30 s))` (TL decision, review 2). Why it fits:
     the httpx read timeout is per read (the longest wait for the next bytes), not per request.
     The docs say only that empty lines are sent while a non-streaming request is waiting, and that
     the server closes a request that has not started inference after 10 minutes. They say nothing
     about lines during inference, so the plan assumes none: the whole generation may be one silent
     read. 3600 s then covers a 64000-token thinking answer at about 18 tokens/s or faster. That
     speed is an assumption, not a sourced figure, so every call's wall time and tokens per second
     are recorded (eval_run, Design 5) to check it. A timeout is a failed call: reported, not
     re-rolled (see "Other API errors"), and the question drops from the comparison ("Thinking
     default"). A missing / empty
     `DEEPSEEK_API_KEY` raises a clear `RuntimeError` before any client exists (never falls back to
     `OPENAI_API_KEY`).
   - Caps by thinking mode: `DEEPSEEK_MAX_TOKENS = {False: 20000, True: 64000}` (answer; off = the
     project's 20000; on = the API's own thinking default of 64K, because reasoning shares
     `max_tokens`; the API allows up to 384K) and
     `DEEPSEEK_PLANNER_MAX_TOKENS = {False: 2000, True: 16000}` (off = `PLANNER_MAX_TOKENS`; on =
     room for reasoning at the default effort, high). Quality first (TL decision). Helper
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
     `reasoning_content`, tool calls; a dict build for fakes). **Several tool calls:** the first
     call named `submit_answer` (`submit_plan` for the planner) wins; the others are ignored, and
     `usage.tool_calls` keeps the count, so the record shows it happened.
   - **Reasoning kept for valid outputs too (review NB1).** `Answer` gets a pydantic
     `PrivateAttr` `_provider_payload` (`schema.py`, one line). It is not a field, so `model_dump`,
     query_log and the UI never see it. `_deepseek` sets it to `{"reasoning_content": ..., "content":
     ...}` from the message. RealRunner's answer record adds `"reasoning_content"` from it for valid
     answers (invalid ones already keep the whole message in `raw_payload`). The planner's `meta`
     dict gets `reasoning_content`, and RealRunner's plan record saves it. It is not in
     `Answer.usage`. Each call is single-turn, so the docs' rule to pass `reasoning_content` back
     does not apply.
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
   `--real` names deepseek. `cache_key` / `plan_cache_key` signatures unchanged; `plan_cache_key`
   gets a one-line comment: its `PLANNER_MAX_TOKENS` is the constant 2000, and the DeepSeek
   planner cap is kept apart through the request version (review NB6). Valid answer and plan
   records also save `reasoning_content` (Design 2). Every saved answer and plan record (valid or
   invalid, all providers) gains `wall_s` (time around the call, `time.monotonic`) and
   `tokens_per_s` (output tokens / `wall_s`). These are new bookkeeping fields in the record, not in
   the cache key.
6. **`.env.example`.** Provider comment `mock | anthropic | openai | deepseek`; `DEEPSEEK_API_KEY=`,
   `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta` (comment:
   /beta is needed for strict tools), `DEEPSEEK_THINKING=<chosen default>` with one comment line.
7. **`docs/RUN.md`.** Step 1 `.env` paragraph names deepseek; section 7 gains "Ask with DeepSeek"
   with a PowerShell block and a bash block each for the app and for `eval_run.py --real`
   (`$env:LLM_PROVIDER="deepseek"` / `LLM_PROVIDER=deepseek ...`), plus a line on 402 / 429.
8. **Docs naming the provider list** (one-line edits): `specs/answer-citations.md` ("Invalid model
   outputs" table rows for DeepSeek finish reasons, bad-JSON arguments; strict paragraph: DeepSeek
   strict via /beta, request version; line 191 provider list), `README.md` line 145. **Not** CLAUDE.md
   and **not** `docs/DECISIONS.md` (TL decision): #244 (ADR-021) owns both. The PR states that the
   CLAUDE.md "Paid API calls" provider list and ADR-012's provider list go to #244.

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
  Thinking on: `tool_choice == "auto"`, thinking enabled, `max_tokens` 64000.
- D3 planner request: same checks for `submit_plan` (max_tokens 2000 / 16000).
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
- D9 `request_version`: anthropic `strict-1`, openai `None`, deepseek
  `ds-strict-1-think-off-a20000-p2000` and `ds-strict-1-think-on-a64000-p16000`; `model_name` / `model_for` deepseek -> `deepseek-v4-pro`.
- D10 config: `DEEPSEEK_THINKING` on / off / empty / bad value; defaults of model and base URL.
- D11 client: the real builder (captured before conftest) with a dummy key: `max_retries == 0`,
  timeout read 3600 s and connect 30 s, base URL `/beta/`; no key -> RuntimeError.
- D12 eval_run: `RealRunner("deepseek", ...)` with a fake `generate` / planner: the answer and plan
  records carry the deepseek request version and max_tokens; switching `DEEPSEEK_THINKING` changes
  both keys (no reuse); valid answer and plan records hold `reasoning_content`, and the answer's
  `model_dump()` / query_log JSON do not; a `ProviderStop` saves nothing and exits with the message;
  an invalid output is saved and reused as invalid on a second run (no second call).
- D13 several tool calls: two `submit_answer` calls -> the first one is used, `usage.tool_calls == 2`
  (same for `submit_plan`).
- D14 (review 2 NB2): `RealRunner("deepseek", ...).answer` with a fake `generate` that raises a
  non-ProviderStop error (e.g. `openai.APITimeoutError` or a 500 `APIStatusError`): the exception
  propagates out of `answer`, no record is written in the cache or `raw/`, and `runner.calls` went
  up by one (the call is counted).
- D15 timing: valid and invalid answer and plan records carry `wall_s` (measured around the call)
  and `tokens_per_s` (= completion tokens / `wall_s`; None when either is missing).

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
   Commit and push; record that sha in `ev242\app-sha.txt`.
7. **App check (2 calls, TL-approved inside the cap of 14).** `ev242\run-app.ps1` (one-off, not
   committed), same guards as the real runs: a code gate (`git status --short` empty and
   `git diff <app sha> HEAD -- src scripts config` empty, logged to `ev242\head-log.txt`, exit
   before `.env` otherwise); then in `try` the `.env` copy, explicit env (`LLM_PROVIDER=deepseek`,
   `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`,
   `DEEPSEEK_THINKING=<chosen>`, `PLANNER=on`, `PLANNER_MAX_PARTS=4`, `PYTHONPATH`), the resolved
   non-secret settings logged; Streamlit on port 8598; a Playwright script asks Q1 on the Ask page
   once, waits up to 2 h (two calls, each up to the 3600 s read timeout), saves a screenshot and the page text, checks the footer
   `LLM called: True` and the query_log row (`model = deepseek-v4-pro`, `llm_calls` planner 1 /
   answer 1); `finally` stops Streamlit, removes `.env` and the variables, logs that `.env` is gone.
   This is the evidence for acceptance 1. `verify_cee.py` forces `LLM_PROVIDER=mock`, so the PR says
   the real-provider proof is this one-off check and verify-cee (mock) proves the pipeline (NB4).
8. Evidence committed: `docs/results/0242-deepseek-check.md` (per run: question, mode, planner
   source, finish_reason, valid / invalid and why, behavior vs expected, citation flags, tokens incl.
   cache hit / reasoning, wall time; cap findings; dropped questions; the decision; review 2 NB1:
   for every call, wall time, tokens per second, and reasoning + output tokens against its cap
   (e.g. "41,200 / 64,000 = 64%"), so the room the caps left shows even without a cut) and
   `docs/results/0242-deepseek-raw/*.json` (the raw records the runs saved, `reasoning_content`
   included). Full run folders and logs in `D:\ALLPROJECTS\EDJ\cache\ev242\`.
9. `/finish-task`: PR with "Closes #242". Verification lists every real call. The PR states that the
   CLAUDE.md "Paid API calls" provider list and ADR-012's provider list are left to #244.
   `gh pr checks` green.

## Paid-call plan (CLAUDE.md "Paid API calls")
- **Why the mock cannot show it:** the mock never sends a request; only DeepSeek shows whether
  strict tools are accepted on /beta in both thinking modes, whether outputs validate, cut or skip
  the tool, what usage looks like, and how the two modes behave on citations and gaps.
- **Questions:** Q1 (one firm, `answer`), Q22 (five firms, largest input, `answer`), Q24 (five
  firms, `gap_with_adjacent`, a trap). Each one run through the full flow = 1 planner call + 1 answer
  call (all three are searchable in token-budget mode, so the planner is called).
- **Runs:** R-off `DEEPSEEK_THINKING=off`, then R-on `DEEPSEEK_THINKING=on`, each
  `eval_run.py --real --max-calls 6 --questions Q1,Q22,Q24 --as-of 2026-11-17 --baseline ...
  --out .eval-runs\0242-real-{off|on}`. **Cap 6 per run, 12 total.** Plus **2 calls** for the app
  check (step 7, Q1 once more in the chosen mode, TL-approved). **Total cap: 14 calls.** No re-run:
  an invalid, cut or failed output is a finding, saved and reported. A 402 / 429 stops the run (no
  output, nothing to re-roll); continuing after a top-up / wait needs the coordinator, and the
  cached outputs are reused.
- **Other API errors (NB2).** A non-ProviderStop API error on the answer path (400 schema reject,
  500, 503, a timeout) propagates and aborts `eval_run` with nothing saved, as it does today for the
  other providers. The script records the nonzero exit code per run in `head-log.txt`; it is not
  counted as an output. A planner call that fails this way falls back to the rule plan and is saved
  as a failed call (existing path). R-on still runs after an R-off abort (separate command).
  Retrying an aborted run is not re-rolling an output, but it needs the coordinator.
- **Execution** (as #240's `run-real.ps1`): `D:\ALLPROJECTS\EDJ\cache\ev242\run-real.ps1` logs HEAD,
  `git status --short` (must be empty) and `git diff <mruns sha> HEAD -- src scripts config` (must be
  empty) to `ev242\head-log.txt`, exits before touching `.env` otherwise. Then in `try`:
  - copies `D:\ALLPROJECTS\EDJ\repo\.env` to the worktree (never read or printed);
  - **pins every run setting explicitly** (review B3; `load_dotenv` never overrides a set variable,
    so the copied `.env` only supplies `DEEPSEEK_API_KEY` and anything not pinned):
    `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`,
    `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`, `DEEPSEEK_THINKING` (off, then on),
    `PLANNER=on`, `PLANNER_MAX_PARTS=4`, `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-242\src`;
  - logs the resolved non-secret settings per run to `head-log.txt` (a one-line Python print of the
    `settings()` fields provider, deepseek model / base URL / thinking, planner, max parts,
    `llm.request_version("deepseek")`, the two caps, and whether a key is set as true / false;
    never the key);
  - runs R-off then R-on with output to `ev242\real-{off|on}.log`, exit codes logged.
  `finally` removes the worktree `.env` and the variables and logs that it is gone. Run in the
  background. Afterwards copy each run folder (`raw/`, `report.json`, `report.md`) to
  `ev242\real-{off|on}\`.
- **Saved:** every planner and answer record (question, prompt / planner version, model, request
  version, max_tokens, chunk ids, raw output or raw payload, `reasoning_content`, finish_reason,
  usage with cache hit / miss and reasoning tokens, wall_s, tokens_per_s).

## Thinking default (decision rule, fixed before the calls)
**Cap findings first.** A planner or answer output cut at its cap (`finish_reason` `length`) in
either mode is reported as a cap finding (question, mode, call, output and reasoning tokens). That
question is then dropped from criteria 1-3 **for both modes**, not counted against the mode that
was cut.

**No model output drops too (review 2, B2).** A question with no model output in either mode drops
from criteria 1-3 **for both modes** and is named in the report, like a cap finding. "No model
output" means:
- a failed call, planner or answer: a timeout, a 400 / 500 / 503, or a planner failure that fell
  back to the rule plan (saved as `failed_call`);
- a question never run because its run aborted.
A saved invalid output still counts against its mode: no tool call, bad JSON, pydantic failure,
`content_filter`, an empty answer, or a plan that `validate_plan` rejects.

If every question drops, the comparison has no evidence and the default is **on**; the PR says so.

Compare R-off and R-on over the questions left, in this order; the first criterion that differs decides:
1. Valid outputs (plans with source `model` + valid answers), out of 2 x the questions left.
2. Behavior equal to `expected_behavior` (Q1 answer, Q22 answer, Q24 gap_with_adjacent).
3. Citation discipline, summed over the answers: unmatched citations + claims without chunk ids +
   number-check flags + code-added part gaps (fewer is better).
Tie on all three -> **on** (quality first, TL decision). `off` is only the placeholder default
before the check. The table with every number and the reading of the claims (with the saved
`reasoning_content` where it explains a difference) goes in the PR. If neither mode gives a valid
answer on a question, that is reported as a finding; the default still follows the rule.

## Files to change
- `src/cee/config.py` - three DeepSeek settings.
- `src/cee/answer/llm.py` - client, requests, `_deepseek`, `ProviderStop`, caps, `request_version`, docstring.
- `src/cee/answer/schema.py` - one `PrivateAttr` `_provider_payload` on `Answer` (not a field, not dumped).
- `src/cee/retrieve/planner.py` - deepseek request and branch, OpenAI length cut, `ProviderStop`
  re-raise, `model_for`, `planner_max_tokens`, `reasoning_content` in `meta`.
- `src/cee/ask.py` - `model_name`, docstring.
- `scripts/eval_run.py` - RealRunner messages, max_tokens records, `reasoning_content` in records,
  ProviderStop stop, `plan_cache_key` comment.
- `tests/conftest.py`, `tests/test_no_paid_calls.py`, `tests/test_llm_deepseek.py` (new),
  `tests/test_planner.py`, `tests/test_eval_run.py`.
- `.env.example`, `docs/RUN.md`, `specs/answer-citations.md`, `README.md` (one line).
- `docs/results/0242-deepseek-check.md`, `docs/results/0242-deepseek-raw/` (evidence).
- `plans/0242-deepseek.md` - this plan.
Not changed: `CLAUDE.md` and `docs/DECISIONS.md` (#244 owns both), prompts (`PROMPT_VERSION` v4.1,
`PLANNER_VERSION` plan-v2), `Answer`'s fields, the anthropic / openai answer paths, the anthropic
planner, verify-cee driver and recipes (no user-facing feature changes; the app check is a one-off
script in `ev242`). The one-off scripts in `ev242` are Windows-only and not committed, so they get
no `.sh` twin; if one is ever committed it gets one.

## Acceptance
- [ ] `LLM_PROVIDER=deepseek` answers Q1 in the running app (step 7 one-off Playwright check:
      screenshot, footer, query_log row; verify-cee's driver is mock-only).
- [ ] Tests D1-D15 and the guard tests pass: strict flag and explicit `max_tokens` on both tools;
      cut, no-tool, bad-JSON and pydantic-failure outputs saved as invalid; 402 / 429 stop; OpenAI
      planner rejects `length`; `reasoning_content` saved for valid outputs; 0 real calls (httpx2
      counter `sent == []`).
- [ ] Real: 6 question-runs (Q1, Q22, Q24 x thinking on / off), 12 calls at most (14 with the app
      check), every raw record saved with usage; cap findings reported; thinking default chosen by
      the rule above, evidence in the PR and `docs/results/0242-deepseek-check.md`.
- [ ] Mock `eval_run.py` 30/30 chunk lists unchanged vs `evals/baselines/corpus-2026-11-19`;
      pytest, verify-cee (mock) and `gh pr checks` green.

## Progress log
- 2026-11-19 21:12 - plan written; DeepSeek docs re-checked (tool_calls, create-chat-completion,
  thinking_mode, error_codes, rate_limit, models). Worktree `D:\ALLPROJECTS\EDJ\wt-242`, branch
  `tl/242-deepseek` from origin/main af873e6. DB up to date (corpus-2026-11-19).
- 2026-11-19 21:21 - plan review 1 (CHANGES REQUESTED, issue comment 7029290431) addressed:
  B1 tie -> on; B2 CLAUDE.md out (#244); B3 every run setting pinned in run-real.ps1 and the app
  check (own code gate, try/finally, settings logged); B4 thinking caps raised to 64000 / 16000
  with a 2700 s per-read timeout, plus the cap-finding rule. NB1 `reasoning_content` saved for valid
  outputs (PrivateAttr, schema.py added), NB2 other API errors, NB3 first tool call wins (D13),
  NB4 app check is the real-provider proof, NB6 `plan_cache_key` comment. TL approved the 2 app
  calls (cap 14).
- 2026-11-19 21:24 - plan review 2 (CHANGES REQUESTED, issue comment 7029356630) addressed: read
  timeout 3600 s (TL), keep-alive sentence limited to what the docs say (empty lines while waiting;
  nothing documented during inference), D11 updated; wall_s and tokens_per_s in every record (D15)
  and per-call reasoning + output vs cap in the report; drop rule for a question with no model
  output in either mode (failed call, planner fallback, run aborted; saved invalid outputs still
  count; all dropped -> on); D14 pins a non-ProviderStop answer error (propagates, nothing saved,
  counted).
- 2026-11-19 21:35 - plan approved (TL, 5820a7f). Built Design 1-8 and tests D1-D15 (commit 6b76881):
  full pytest 737 passed with `PYTHONPATH=<wt>\src`. Mock eval (`.eval-runs\0242-mock`): 29 PASS /
  1 FAIL (Q19, as the baseline), refusal 5/5, 30/30 UNCHANGED and chunk lists identical to
  `evals/baselines/corpus-2026-11-19` (30/30, `ev242\mock-compare.txt`), 0 calls. verify-cee (mock)
  VERIFY PASS (`.verify-runs\20261119-213310-6b76881`); open-citation and download-document
  UNREACHABLE because the worktree has no `data/raw/` (same as #240), not a #242 change. No ruff in
  CI (pytest only). Mock-runs sha 6b76881 recorded; real check next.
- 2026-11-19 21:52 - real check done (`ev242\run-real.ps1`, code gate passed at f604ab2 vs mock sha
  6b76881, `.env` removed after): R-off 6 calls, R-on 6 calls, exit 0 both, no 401/402/429.
  No cut (largest: R-on Q22 answer 33,166 / 64,000 = 52%, planner 8,288 / 16,000 = 52%), no failed
  call, so no question dropped. Criterion 1: valid outputs off 5/6, on 6/6 -> **on**. The invalid
  output: R-off Q22 answer, finish_reason tool_calls but the strict-mode arguments stop mid-string
  after 8,926 characters (2,923 output tokens, far under the cap): bad JSON, saved, not re-rolled.
  (Criterion 2 would also give on: off 1/2 answers with the expected behavior, Q24 answered instead
  of gap_with_adjacent; on 3/3.) Default set to on (config + .env.example + D10 pin); pytest 737
  passed, mock eval 30/30 UNCHANGED again (`.eval-runs\0242-mock-2`).
