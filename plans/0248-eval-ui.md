# 0248 - Eval harness and app for map-reduce: per-call cache, cost per question, progress stages

Issue: #248    Role: TL    Spec: specs/ui.md, evals/questions.yaml (also specs/answer-citations.md for
the logged cost; docs/DECISIONS.md ADR-021 rule 7 and ADR-012)

Scope: the issue body (W11 plan item I-6) and the two TL comments on #248: (a) CLAUDE.md "Paid API calls"
names `deepseek`; (b) the dollar cost in `docs/results/0242-deepseek-check.md`, made by the new cost code;
(c) the verify-cee open-citation flake; (d) `CONTEXT_WINDOW["openai"]` TODO-verify. Branch
`tl/248-eval-ui` from origin/main 2f568c4. Real calls: **0** (cache replay of saved records proves the
cache and the cost). Feeds #250 (DeepSeek fts + hybrid) and #259 (Claude) scored runs.

Not touched (another implementer, #247 part 3): `src/cee/answer/reduce.py`, `src/cee/answer/validate.py`,
`config/metric_definitions.yaml`. If a step turns out to need them, I stop and ask the TL.

## Goal
`eval_run.py` caches and saves every call of the W11 flow (plan, map per firm, re-extraction, reduce;
the legacy answer call too) so a resumed run never pays twice, and it reports per question the calls,
tokens, provider cache-hit tokens and dollar cost from a dated, sourced price table in config, with
off-peak calls marked, plus the run total in `report.json`. `--reuse-plans` works on main, so fts and
hybrid answer from one set of plans. The app's progress shows the new stages: decompose / search N
sub-questions / extract k firms / re-search / synthesize, and the app logs each question's cost too.

## Call types and their cache keys (step 1 of the issue: today's state, checked in `scripts/eval_run.py`)

| Call | Key function | Cache file | Saved raw | State on main |
|---|---|---|---|---|
| plan | `plan_cache_key` | `<Q>-plan-<key>.json` | yes (valid, invalid, failed) | done (#214, #245) |
| map, one per firm (+ research) | `map_cache_key` (spec id `map.<FIRM>`, round 1) | `<Q>-map.<FIRM>-<key>.json` | yes | done (#246) |
| re-extraction after corrective re-search | `map_cache_key` (spec id `remap.<FIRM>`, round 2, the new chunk ids) | `<Q>-remap.<FIRM>-<key>.json` | yes | done (#246) |
| reduce | `reduce_cache_key` | `<Q>-reduce-<key>.json` | yes | done (#247) |
| legacy single answer (`--legacy`) | `cache_key` | `<Q>-<key>.json` | yes | done |
| corrective re-search itself | - (SQL, 0 calls) | - | - | no call |

So every key exists. What is missing: (1) no test proves a resumed run reuses **every** call type and
makes 0 calls; (2) no cost; (3) `--reuse-plans` only on exp/hybrid; (4) a cached record is not counted
per question by type. **No key function changes in this issue** (a key change would orphan the saved
records #250 / #259 reuse); the replay acceptance item proves it.

## Decisions
- **D1 Price table** `config/pricing.yaml` (new), one entry per provider + model, each with `source`,
  `read_on` date and rates in USD per 1M tokens:
  - `deepseek` / `deepseek-v4-pro`: peak / off-peak: input cache hit 0.044 / 0.022, input cache miss
    1.32 / 0.66, output 3.96 / 1.98. Peak 01:00-04:00 and 06:00-10:00 UTC, Monday-Friday; every other
    time off-peak. Chinese public holidays (off-peak all day) are a `holidays: []` list, empty now with a
    note (none falls in the W11 run window; the TL fills it if a run lands on one). Source: TL comment on
    #243 (issuecomment-7030358880, api-docs.deepseek.com/quick_start/pricing read 2026-11-19; re-read
    2026-11-20 in `docs/results/w11-deepseek-baseline.md`, same rates). `deepseek-flash` from the same
    comment.
  - `anthropic` / `claude-sonnet-5-5` (for #259): input 2.00, output 10.00, cache read 0.10, cache write
    (5-minute) 2.50 (1.25 x input), no peak window. Source: Anthropic's model price table as given by the
    claude-api reference (cached 2026-11-03; https://platform.claude.com/docs/en/about-claude/pricing,
    which the plan reviewer read on 2026-11-20 with the same row); the #259 report re-reads the page at
    report time and notes any difference. Same as the $2 / $10 #217 used. Our requests set no
    `cache_control`, so cache read / write are 0 today; the formula covers them. A note in the file: the
    rates are for default global routing; US-only `inference_geo` costs 1.1x and the 1-hour cache write is
    $4.00; neither is used now (review note 5).
  - `openai`: no entry. An unpriced call is reported as `unpriced` (cost `null`), never as $0.
  - `mock`: always $0, 0 calls.
- **D2 Formula** (`src/cee/answer/cost.py`, new, pure, 0 calls):
  - deepseek: `hit x rate_hit + miss x rate_miss + output x rate_out` (reasoning tokens are inside
    `output_tokens`); when hit / miss are absent, all input is a miss (the dearer rate).
  - anthropic: `input x in + output x out + cache_read x read + cache_creation x write`.
  - **Peak or off-peak by completion time** (start `at` + `wall_s`, in UTC), the rule #243 used; a call
    without `wall_s` uses `at`. Each call also gets `usd_peak` (what it would cost at peak), so "full
    price" is always shown.
  - **Time zone, explicit and recorded** (review blocking 2). Pricing never depends on the zone of the
    machine that prices.
    - New records (eval runs and the app's `finished_at` stamps for planner, map and reduce) carry their
      UTC offset: `datetime.now().astimezone().isoformat()`. Their zone is the one they were written in,
      so no flag is needed for them.
    - Every record saved so far has a naive `at`. For those, `cost.price_call(..., naive_tz=...)` takes the
      zone as an explicit argument (an IANA name such as `America/Chicago`, or a fixed offset such as
      `-06:00`), and `eval_run.py` / `eval_cost.py` take `--naive-tz`. There is no machine default:
      - `eval_cost.py`: a naive record without `--naive-tz` exits 2 before printing, naming the file.
      - `eval_run.py --real`: before any search or call, the cache folder is scanned; if it holds a naive
        record and `--naive-tz` is not given, the run exits 2 (nothing called). The shared
        `.eval-runs/cache` holds naive records today, so #250 / #259 pass `--naive-tz America/Chicago`.
      - The zone used is printed, stored in `report.json` `meta.cost.naive_tz` and on each call row
        (`tz`: `record offset` or `--naive-tz America/Chicago`).
    - The zone of every record written so far is **America/Chicago** (this machine; UTC-6 in November),
      stated in `docs/RUN.md` and next to the 0242 figure. With it, the 12 calls of 0242 ran
      03:35-03:51 UTC on Friday 2026-11-20 (completion time), all peak, so the off-peak-aware figure equals
      the full price, $0.79.
    - Tests pass a fixed zone (`-06:00`, and UTC) and never rely on the process TZ. IANA names need the
      tz database (`zoneinfo`; present on this venv, CI's Linux and macOS); tests use fixed offsets only.
  - A failed call (no usage) is a call with cost `null` and reason `no usage`; it still counts.
- **D3 Ledger.** `RealRunner` appends one row per call it serves (thread-safe for parallel maps): `type`
  (plan / map / remap / reduce / answer), `file`, `new` (made in this run) or reused (from the cache),
  `provider`, `model`, `usage`, `at`, `wall_s`, and the priced cost. Each question's record gets
  `cost`: calls by type, new and reused counts, input / output / cache-hit / cache-miss / reasoning
  tokens, `usd` (the answer's full cost, reused calls at what they cost when made), `usd_new` (spent
  in this run), `usd_peak`, `peak_calls`, `off_peak_calls`, `unpriced_calls`, `tz_assumed`, and the per-call
  rows. `summary.cost` and `meta.cost` hold the run totals; `report.md` gets a cost line in the header
  and a Cost column. Mock runs: every field 0.
- **D4 Two meanings of "cache"**, kept apart in every report: *reused* = an eval cache file served
  the call (no new spend); *cache-hit tokens* = the provider's prompt cache (cheaper input).
- **D5 `--reuse-plans PROVIDER:MODEL`** ported from exp/hybrid (#240) onto main's key (no part cap
  since plan-v3): `plans_wanted`, `plan_path`, `PlanMissing`, `missing_plans`, `SavedPlans`,
  `RealRunner(plans_only=...)`. Real: a missing plan stops the run before any search or call (exit 2);
  provider / model unlike the run's: exit 2, nothing called. Mock: plans read from the files, `calls` 0.
  `--max-calls` stays the run-wide cap over every call type. Merge with #249's sync (review note 2):
  exp/hybrid's `plan_path` / `plan_cache_key` take `cap` and its `RealRunner(cache_dir=None)` differs
  from main's `cache_dir=CACHE`; the PR says #249 resolves both to main's versions, and the T9 / T10
  test names are kept identical, so that merge is mechanical. Also `--cache DIR` (default
  `.eval-runs/cache`), so a replay can read a copied record folder without touching the shared cache.
- **D6 Progress stages** (`cee.ask.STAGES`), 9 lines instead of 8:
  `resolve, decompose, search, extract, research, synthesize, check, caveats, log`.
  - decompose: "Decomposing the question (rules, no model call): 1 aspect x 1 firm = 1 sub-question:
    a1.EDJ" (real: "(deepseek, one call)"; fallback line kept).
  - search: "Searching 2 sub-questions: N passages from D documents".
  - extract: "Extracting from 2 firms (mock, no model call): N cells: ...; behavior by code: answer"
    (real: "(deepseek, 2 calls in parallel)"). `run_map` gets an optional `on_research` hook (in
    `extract.py`, before the corrective re-search) so the extract line is done and the re-search line
    runs while it happens.
  - research: "Re-searching sub-questions with no evidence: R re-searched, P with new passages, E
    re-extractions" or skipped "Re-search: every sub-question has evidence" (skipped with reason when
    MAP=off or no passages).
  - synthesize: "Synthesizing the answer from the evidence matrix (mock, one call): N claims"; built by
    code: "No model call: the answer is built by code (...)"; legacy (MAP=off): "Writing the answer
    (deepseek, one legacy call)"; no passages: "No passages found: no model call".
  - **Mock delay: no new sleep** (review blocking 3; my first draft's premise was wrong). On main,
    `mock_extract` (`extract.py:512`) and `mock_reduce` (`reduce.py:548`) already sleep `MOCK_DELAY_S`,
    and the legacy mock answer does too (`llm._mock`). The ask-progress verify question
    ("What does Edward Jones's 10-K say...", one firm) takes this path: decompose (rules) -> search 1
    sub-question -> `run_map` with one `map.EDJ` spec (`mock_extract`, sleeps) -> behavior `answer`, so
    `needs_call` is true -> `R.raw_answer` -> `mock_reduce` (sleeps). The mid-run catch waits for
    "Synthesizing the answer", which the existing `mock_reduce` sleep makes reliable. The code-built path
    (no model call) is not taken by any verify question, so it gets no delay either. The step count in
    the app and the driver comes from `len(STAGES)`, never a literal (review note 6).
  - The app logs each question's cost: `query_log.filters.cost` (same shape as D3, from the plan's
    usage, each map call's usage and the reduce usage), satisfying the CLAUDE.md invariant "every call is
    logged with tokens and cost". The planner's usage and completion time are kept on the `Plan`
    (`usage`, `finished_at`, in `to_log`); map calls get `finished_at` in `_call_log`; the reduce's
    completion time is stamped in `ask._reduce_for`. No change to `reduce.py`.

## Round-2 notes (plan approved at f381049, issuecomment-7044228917; adopted, written in before any code)
1. **Map completion time per call.** Each map call's `finished_at` (offset-aware) is stamped inside the
   worker, on `CallResult`, and copied by `_call_log`; not one time for the whole round. `price_call`
   accepts either form: `at` + `wall_s`, or `finished_at`.
2. **The resume test asserts its preconditions**, so a later change fails loudly instead of quietly
   changing the counts: the fake aspect is not `comparison`; the fake search returns no `research`-part
   hits (no `map.research` call); the corrective search is monkeypatched (`RealRunner.map` passes no
   `search_fn`); A's `fact` passes the quote / number checks, so run A's behavior is `answer` and its reduce
   is `cap`, not `code_built`.
3. **tzdata.** `tzdata` is pinned in `requirements.txt` (Windows has no system tz database), and `cost.py`
   turns a `ZoneInfoNotFoundError` into a clear message suggesting a fixed offset (e.g. `-06:00`).
   `requirements.txt` joins the file list.

## Files to change
- `config/pricing.yaml` (new) - D1.
- `requirements.txt` - pin `tzdata` (round-2 note 3).
- `src/cee/answer/cost.py` (new) - D2: `load_prices`, `is_peak`, `price_call`, `summarize`.
- `src/cee/answer/llm.py` - Anthropic usage adds `cache_read_input_tokens` / `cache_creation_input_tokens`
  when the SDK returns them; `CONTEXT_WINDOW["openai"]` verified (step 9).
- `src/cee/retrieve/planner.py` - `plan_question` passes `meta` to `call_planner`; `Plan.usage`,
  `Plan.finished_at` (in `to_log`).
- `src/cee/answer/extract.py` - `_call_log` adds `finished_at`; `run_map(..., on_research=None)`.
- `src/cee/ask.py` - D6 stages and texts, offset-aware reduce `finished_at`, `log_filters` `cost` (no
  new sleep).
- `src/cee/app/views/ask_page.py` - only if the first bar text needs it; the step count stays
  `len(STAGES)`.
- `scripts/eval_run.py` - D3 ledger and cost, D5 `--reuse-plans` and `--cache`, `--naive-tz` (D2), offset-aware `at`,
  report columns; docstring.
- `scripts/eval_cost.py` (new) - prices a folder of saved records (`raw/` or a results folder), prints a
  per-call and total table (new spend, full price), `--naive-tz` (required when a record has a naive `at`;
  printed and in the output), `--json` for the reports. Pure Python, no OS-specific
  script, so no `.ps1` / `.sh` pair is needed; `docs/RUN.md` gets both command blocks.
- `scripts/verify_cee.py` - `feature_ask_progress` for D6 (9 lines, new texts, mid-run catch on
  "Synthesizing the answer"); `feature_open_citation` waits for `CITED PASSAGE · <chunk_id>` (or the
  stored snippet) with the render timeout before reading the body (TL comment item 1).
- `.claude/skills/verify-cee/features/ask-progress.md`, `open-citation.md` - recipe text and gotcha.
- `specs/ui.md` - the stage list.
- `CLAUDE.md` - "Paid API calls": `LLM_PROVIDER=anthropic`, `openai` or `deepseek`.
- `docs/results/0242-deepseek-check.md` - the dollar cost from `eval_cost.py` (expected $0.79 at full
  price: $0.27 thinking off, $0.52 on; off-peak-aware with `--naive-tz America/Chicago`: all 12 peak,
  also $0.79; the zone is stated next to the figure).
- `docs/RUN.md` - Windows and Mac blocks: `--reuse-plans`, `--cache`, `--naive-tz`, `eval_cost.py`, reading
  cost; states that records written before #248 are America/Chicago (UTC-6 in November).
- Tests: `tests/test_cost.py` (new), `tests/test_eval_run.py`, `tests/test_ask_progress.py`,
  `tests/test_ask_page_trace.py`, `tests/test_verify_wait.py`.

## Steps
1. `config/pricing.yaml` + `cost.py` + `tests/test_cost.py`: peak edges (00:59 off, 01:00 peak, 03:59
   peak, 04:00 off, 05:59 off, 06:00 peak, 09:59 peak, 10:00 off, Saturday 02:00 off, a listed holiday
   off), completion vs start across 06:00, offset-aware `at` (its own offset wins over `naive_tz`), naive
   `at` with `naive_tz="-06:00"` and with `naive_tz="+00:00"` (different periods, both explicit), naive
   `at` with no zone -> error; deepseek hit / miss / no split, anthropic with cache read / write, openai
   unpriced, failed call. A test prices the 12 committed records in `docs/results/0242-deepseek-raw/{off,on}`
   with `naive_tz="-06:00"`: full price $0.79 ($0.27 off, $0.52 on) to the cent, all 12 peak, so the
   off-peak-aware total is also $0.79.
2. Ledger and cost in `eval_run.py` (D3), `--cache`, offset-aware `at` for new records; tests with the
   existing fake clients: cost per question and `summary.cost` in `report.json` for planner + map +
   remap + reduce; reused calls priced at their saved usage with `usd_new` 0; mock run all 0.
3. **Resume test (acceptance 1), fakes, 0 real calls** (review blocking 1). On main a sub-question with
   no passage makes no round-1 map call (`extract.map_specs` turns it into a code `not_found` cell), so
   the design is: a two-firm question (firms A and B, fake planner: 1 aspect x 2 firms); the fake search
   gives **both** sub-questions passages; the fake map client returns a `fact` for A's cell and
   `not_found` for B's cell (eligible for research); the fake corrective search returns new passages for
   B, so round 2 has one `remap.B`; the fake map client returns a `fact` for it; the fake reduce returns a
   valid answer. Each fake counts its calls. Expected (calls made / records reused, per type):

   | Run | `--max-calls` | plan | map (A, B) | remap.B | reduce | `real_calls` | `reused` | answer |
   |---|---|---|---|---|---|---|---|---|
   | A | 3 | 1 new | 2 new | 0 (capped, listed in `map_capped_calls`, no file) | 0 (`cap`, no file) | 3 | 0 | `NOT_EVALUATED`, note "not run: --max-calls reached" |
   | B | 2 | reused | 2 reused | 1 new | 1 new | 2 | 3 | the answer |
   | C | 0 | reused | 2 reused | 1 reused | 1 reused | 0 | 5 | equal to B's |

   Fake counters after the three runs: planner 1, map 2, remap 1, reduce 1 (no call made twice). Run C's
   `cost`: `calls` {plan 1, map 2, remap 1, reduce 1}, new 0, reused 5, `usd_new` 0, `usd` equal to run
   B's `usd` (the same five records), `calls_reserved` 0. Run B's `usd_new` = the remap + reduce cost.
   Legacy (`--legacy`, answer key), one firm: A' cap 1 -> plan new, answer `cap` (`real_calls` 1); B' cap 1
   -> plan reused, answer new (`real_calls` 1, `reused` 1); C' cap 0 -> plan and answer reused
   (`real_calls` 0, `reused` 2); counters planner 1, answer 1.
4. `--reuse-plans` (D5) and its tests (ported T9 / T10 on main: the plan file is shared by two runs and
   the second makes no planner call; real with a missing plan exits 2 before any call; mismatch exits 2;
   mock reads the saved plan with `calls` 0).
5. App: planner usage on `Plan`, map `finished_at`, `on_research` hook, D6 stages and texts, mock delay,
   `log_filters.cost`; update `tests/test_ask_progress.py` / `tests/test_ask_page_trace.py` (9 stages,
   research done / skipped, failed stage marked, real-provider lines with fake clients, cost in the log).
6. `verify_cee.py` + recipes: ask-progress (9 lines, decompose / search / extract / research /
   synthesize texts; the two-firm question: "1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.RJF" and
   "Searching 2 sub-questions"; `query_log` row adds `cost` with 0 calls); open-citation wait; a unit test
   for the new wait (a fake page that renders late passes, one that never renders is a RenderTimeout).
7. `eval_cost.py`; run it on `docs/results/0242-deepseek-raw` and write the cost into
   `0242-deepseek-check.md` (TL comment item 2).
8. CLAUDE.md provider list (TL comment item 1 of the #253 hand-over), `specs/ui.md`, `docs/RUN.md`.
9. `CONTEXT_WINDOW["openai"]`: read OpenAI's model page for `gpt-5` (the `OPENAI_MODEL` default). If it
   states the context window, set it and replace TODO-verify with the URL and date; if the page cannot be
   read or does not say, keep the TODO with a note saying so. 0 calls (a docs read, not the API).
10. Checks (below), then `/finish-task`.

## Acceptance
- [ ] Linked questions Q1-Q30: retrieval unchanged. Mock eval of the bank (0 calls, `--as-of 2026-11-17`):
      every chunk list identical to main 2f568c4's mock run; refusal and keyed checks unchanged; every
      question has `cost` with 0 calls and $0; `summary.cost` present.
- [ ] **A resumed run reuses every saved call** (issue acceptance 1): step 3's tests pass (0 real calls).
- [ ] **0-call replay of saved real records** (proves the keys did not move and the cost reads real
      usage). Run on this branch **before any rebase onto #247 part 3** (review note 3): copy
      `docs/results/0247b-raw` (records only, not `verdicts*`) to a scratch cache, run
      `LLM_PROVIDER=deepseek DEEPSEEK_THINKING=on eval_run.py --real --max-calls 0 --cache <copy>
      --naive-tz America/Chicago --questions Q1,Q3,Q11,Q19,Q22,Q23,Q24,Q26 --as-of 2026-11-17`.
      Settings are pinned in the command; `cee.config` loads `<repo>/.env` on import, and wt-248 has no
      `.env` (existence checked only, never read), so every unpinned setting is a config default; no
      `.env` is created or edited (review note 1). Expected: `real_calls` 0, `calls_reserved` 0, no question
      `cap`; served from the copy: plan 8, map 27, re-extraction 7, reduce 8 = 50 records, the part-2
      replay-final count; each question has a non-null `usd` with `usd_new` 0, every call tz
      `--naive-tz America/Chicago`, and the run total is stated. Q3's failed reduce attempt
      (`Q3-reduce-...failed-1.json`) is not a cache file, so its spend is not in the replay's Q3 cost; the
      report says so next to the total and compares it with part 2's stated spend (~$1.90 for 33 calls)
      (review note 4). If part 3 merges first and bumps `REDUCE_VERSION` (0 calls, so no saved reduce
      record under the new key), the replay is run on the pre-rebase commit and that SHA is logged; if a
      rebase came first anyway, it uses part 3's own replay records if they exist, or reports the 8 reduce
      misses as `cap` (plans and maps still 0 calls) and says so.
- [ ] Cost per question and run total in report.json (issue acceptance 2): tests in steps 1-2; the
      0242 records price to $0.79 full price ($0.27 off, $0.52 on), now in `0242-deepseek-check.md`.
- [ ] `--reuse-plans` on main: step 4 tests; `--max-calls` still caps every call type (a test: cap 1 on a
      two-firm question makes the plan call only).
- [ ] verify-cee shows the new stages (issue acceptance 3): `python scripts/verify_cee.py run` all features
      PASS (ask-progress: 9 lines, the new texts, `query_log.filters.cost`), evidence folder named in the PR.
- [ ] Open-citation flake: `python scripts/verify_cee.py run open-citation` passes 5 runs in a row
      (5 run folders listed in the PR).
- [ ] `CONTEXT_WINDOW["openai"]` verified with a source, or the TODO kept with a note.
- [ ] CLAUDE.md names `deepseek`; `docs/RUN.md` has Windows and Mac blocks for the new flags.
- [ ] `pytest` green locally (PYTHONPATH=wt-248/src) and `gh pr checks` green.
- [ ] 0 real calls (stated in the PR's Verification section).

## Progress log
- 2026-11-20 09:51 - plan written. Branch `tl/248-eval-ui` from origin/main 2f568c4; DB check: up to date
  (corpus-2026-11-19). Every call type already has a key; the work is the resume proof, cost,
  `--reuse-plans`, stages and the four TL comment items. 0 real calls planned.
- 2026-11-20 10:40 - plan review round 1 (issuecomment-7044101304), CHANGES REQUESTED, with TL rulings.
  Blocking 1: resume test redesigned (both firms have passages, B's map cell `not_found` -> re-search ->
  remap.B) with exact per-run counts. Blocking 2: naive `at` priced only with an explicit `--naive-tz`
  (required when naive records are present), recorded in report.json; new records and app stamps carry
  offsets; existing records are America/Chicago; tests use fixed offsets. Blocking 3: premise corrected,
  `mock_extract` / `mock_reduce` already sleep; no new sleep; verify question path named. Notes 1-6
  adopted (.env wording, #249 merge note, replay before rebase onto part 3, Q3 failed attempt outside the
  replay cost, Anthropic geo / 1h notes, step count from `len(STAGES)`).
