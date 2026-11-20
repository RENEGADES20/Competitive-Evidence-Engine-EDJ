# 0243 - DeepSeek baseline: today's pipeline, 30-question scored run on corpus-2026-11-19

Issue: #243    Role: TL    Spec: evals/questions.yaml (scoring: docs/results/w10-report.md "How this was run")

## Goal
One real run of Q1-Q30 through today's pipeline (main 739cb3c, the #242 merge) on DeepSeek with the
#242 settings, scored blind at acting quality against `passes_if`, and compared question by question
with the Claude run #217 (24/30, `docs/results/w10-report.md` / `.json`). The report
`docs/results/w11-deepseek-baseline.md` (+ `.json`) separates the model change from the W11 pipeline
change that #245 will bring. No code changes.

## Pipeline under test (main 739cb3c, no change on the branch)
- Same pipeline as #217 except the provider: retrieval fts, token budget 40k (five firms 60k), pool 30
  (ADR-019); planner `plan-v2`, part cap 4 (ADR-020, #224); answer prompt `v4.1` (#215, #230).
  `git diff cdcb6ee 739cb3c -- src scripts config` is the #242 provider code (plus #244 docs, no code);
  step 1 logs that diff's `--stat` so the report can name it.
- Provider path (#242): `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`,
  `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta` (strict function tools), `DEEPSEEK_THINKING=on`
  (the #242 default, pinned anyway), `tool_choice` `auto`, answer `max_tokens` 64000, planner
  `max_tokens` 16000, `max_retries=0`, read timeout 3600 s, request version
  `ds-strict-1-think-on-a64000-p16000`. `PLANNER=on`, `PLANNER_MAX_PARTS=4`.
- Differences from #217 that are not the model itself, named in the report as "provider path":
  thinking (reasoning shares the output cap), caps 64000 / 16000 vs 20000 / 2000, `tool_choice` auto
  vs forced, DeepSeek's strict-mode JSON (may be invalid, #242 R-off Q22).
- Snapshot `corpus-2026-11-19` (224 docs, 21,161 chunks). Local `cee` (docker `cee-db`) is on it:
  `scripts\sync-db.ps1 -Check` from the main checkout -> "Database is up to date: corpus-2026-11-19"
  (2026-11-19 22:1x; `snapshots/` is unchanged between 739cb3c and main's HEAD). The worktree has no
  `.venv`; every command uses `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe` with
  `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-243\src`.

## Decisions fixed before the run
- **Questions Q1-Q30 only.** The bank at 739cb3c has Q1-Q35; Q31-Q35 are new and not scored here.
  Every `eval_run.py` command passes `--questions Q1,...,Q30` (the full list, written out in the
  script), because without it the script runs all 35.
- **As-of 2026-11-17**, as #217 (same Q26 / Q27 windows; #217 plan, decision (3)).
- **Worktree pinned at 739cb3c** (`D:\ALLPROJECTS\EDJ\wt-243`, branch `tl/243-ds-baseline`). Never
  rebased onto newer main before the run: #245 changes the pipeline. Commits on the branch touch only
  `plans/` and `docs/results/`.
- **Reuse of #242's thinking-on outputs (CLAUDE.md "Paid API calls" step 3: reuse saved outputs
  before calling again).** #242's R-on run (`D:\ALLPROJECTS\EDJ\cache\ev242\real-on\raw\`, 6 files:
  Q1, Q22, Q24 plan + answer) was made with the same settings, snapshot, as-of and request version,
  at f604ab2, whose `src scripts config` differ from 739cb3c only in the thinking default in
  `config.py` (pinned on in both runs; checked: `git diff --stat f604ab2 739cb3c -- src scripts config`
  -> `src/cee/config.py` only). Step 1 copies those 6 files into the worktree's `.eval-runs\cache\`
  (sha256 logged before and after). The runner reuses them only when the cache keys match (question,
  snapshot, model, versions, request version, chunk ids, parts, window); a miss means the question is
  called and counted, named in the report. These three are one sample each, like every other
  question; the report marks them "from #242" and gives their cost as paid in #242. **Expected: 54
  new calls, 6 reused.** (If the reviewer prefers fresh calls for Q1 / Q22 / Q24, drop this step:
  60 calls, same cap.)
- **Verdict rule** (as #217 / Gate 4): one verdict per question, PASS only if the project lead would
  forward the answer with his name on it, read against `passes_if`; no half credit; borderline named.
  Classes: r retrieval, s shape / part missing, b behavior choice, c corpus gap, i invalid output
  (cut, empty, no tool call, bad JSON, `content_filter`, `insufficient_system_resource`, API error on
  the answer call): FAIL, a finding, never re-run.
- **Blind scorer.** The implementer read `w10-report.md` while writing this plan, so it does not
  score. Step 4's blind verdicts are written by a **fresh scorer agent** whose only inputs are the
  answers dump, `evals/questions.yaml` and the verdict rule above; it is told not to open
  `docs/results/w10-report.*`, `gate4-report.*`, `D:\ALLPROJECTS\EDJ\cache\ev217\` or
  `docs/results/0242-deepseek-check.md`. The implementer commits the hash before step 5.
- **Change labels** against #217's final verdicts (after its second read, 24/30; the #217 blind
  first read is shown beside them): **plan** (DeepSeek's planner gave different parts: firms or
  aspects searched differ; part texts named), **retrieval** (a deciding passage entered or left the
  retrieved set; chunk ids from both runs), **model** (the deciding passages were in both retrieved
  sets; DeepSeek chose or wrote differently: behavior, shape, a missed or wrong claim), **invalid**
  (class i), **scorer reading** (the same answer shape read differently). Several allowed; each
  change names its evidence.
- **Cost rule.** Per call, from the saved `usage`: `cache_miss_tokens` x $1.32 / M +
  `cache_hit_tokens` x $0.044 / M + `output_tokens` (reasoning included) x $3.96 / M, the full
  `deepseek-v4-pro` price (TL figures in the issue brief). Off-peak is half price: a call counts as
  off-peak only if its completion time (record `at` + `wall_s`, converted to UTC with the offset
  logged by the run script) falls inside DeepSeek's off-peak window as published on
  api-docs.deepseek.com at report time; if the page does not state the window, every call is priced
  full and the report says so. Per question = planner + answer. Reported: new spend of this run, and
  the full per-question cost including the three reused questions (marked "paid in #242").

## Files to change
- `plans/0243-ds-baseline.md` - this plan and its Progress log.
- `docs/results/w11-deepseek-baseline.md` - new: how it was run, score, tier-1 score, per-question
  table (tier, expected -> got, #217 final, #217 first read, DeepSeek, class, change label,
  borderline, cost), every change against #217 with its cause, borderline and second read, cost
  (per question and total; tokens incl. cache hit / reasoning; wall time; cap used), known findings,
  the 30 answers with citations (same layout as `w10-report.md`).
- `docs/results/w11-deepseek-baseline.json` - new: meta, the scored records (`report.json` of the
  last attempt + log entries of any rule (b) stop), per-call usage and cost, `blind` (the blind file's
  exact bytes) and `blind_sha256`, `verdicts` (verdict, class, borderline, reason, #217 verdict,
  change label, chunk ids), `score`, `first_read` / `second_read`.
Not changed: anything in `src/`, `config/`, `scripts/`, `tests/`, `evals/`, the database, `README.md`,
`docs/NEXT.md` (not asked by the issue; #250 consumes this report). Raw outputs are not committed
(size; reasoning text); they stay in `D:\ALLPROJECTS\EDJ\cache\ev243\` and `.eval-runs\` (as #217).

## Steps
1. **Pre-checks, 0 calls** (logged to `D:\ALLPROJECTS\EDJ\cache\ev243\precheck.txt`):
   - `git status --short` empty on `tl/243-ds-baseline`; `git rev-parse HEAD`;
     `git diff --stat 739cb3c HEAD -- src scripts config evals` empty.
   - `sync-db.ps1 -Check` (main checkout, read-only) exit 0, `corpus-2026-11-19`.
   - Versions: `python -c "from cee.answer.prompt import PROMPT_VERSION; from cee.retrieve.planner import PLANNER_VERSION; print(PROMPT_VERSION, PLANNER_VERSION)"`
     -> `v4.1 plan-v2`; and, with the run's env pinned (no `.env`), `ev243\settings_log.py` (copy of
     #242's) -> `provider=deepseek model=deepseek-v4-pro base_url=https://api.deepseek.com/beta
     thinking=True planner=True max_parts=4 request_version=ds-strict-1-think-on-a64000-p16000
     answer_cap=64000 planner_cap=16000 timeout_s=3600.0 key_set=False`.
   - `git diff --stat cdcb6ee 739cb3c -- src scripts config` (for the report).
   - Cache: the worktree's `.eval-runs\cache\` is empty before the seed; then the 6 #242 R-on files are
     copied in (decision above), sha256 of each logged against the source.
2. **Mock run of Q1-Q30, 0 calls.** `LLM_PROVIDER=mock`, `PYTHONPATH=<wt>\src`:
   `python scripts\eval_run.py --questions Q1,...,Q30 --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out .eval-runs\0243-mock`
   -> expected 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22, 0 forbidden, no status change,
   and 30/30 chunk lists identical (same order) to the baseline (`ev243\mockdiff.py`, adapted from
   `ev217\mockdiff.py`, -> `ev243\mock-diff.txt`). Any difference stops the run (no paid call) and is
   reported.
3. **Real run of Q1-Q30, one run, last** (paid-call plan below), by `ev243\run-real.ps1` (one-off,
   not committed, same pattern as `ev242\run-real.ps1`), started in the background:
   - logs to `ev243\head-log.txt`: start time with UTC offset (`Get-Date -Format o`), HEAD, branch,
     `git status --short` (must be empty) and `git diff 739cb3c HEAD -- src scripts config evals`
     (must be empty); exits before touching `.env` otherwise;
   - `try`: copies `D:\ALLPROJECTS\EDJ\repo\.env` to the worktree (never read or printed); pins
     `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`,
     `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`, `DEEPSEEK_THINKING=on`, `PLANNER=on`,
     `PLANNER_MAX_PARTS=4`, `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-243\src`; logs the resolved settings
     line (`settings_log.py`, `key_set=True` expected, never the key);
     `python scripts\eval_run.py --real --max-calls 60 --questions Q1,...,Q30 --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out .eval-runs\0243-real *> ev243\real-run.log`;
     logs exit code, start / end with UTC offset;
   - `finally`: removes the worktree `.env` and every pinned variable, logs HEAD again and
     `env-removed True`.
   No other writer works in `wt-243` during the run; no commit between step 1 and the end of step 3.
   Afterwards copy `.eval-runs\0243-real\raw\*`, `report.json`, `report.md` to `ev243\real\`
   (attempt N >= 2: `ev243\real-N\`). Record `real_calls`, `reused`, per question `how`
   (called / cached / invalid / cap), plan source (model / rule fallback), `finish_reason`, usage
   (input, cache hit / miss, output, reasoning), `wall_s`, `tokens_per_s`, cap used.
4. **Blind scoring.** Dump the 30 answers (claims with cited passage text, part, adjacent, gaps, code
   caveats, parts, behavior) from the scored records to `ev243\answers-dump.txt` (adapted from
   `ev217\dump217.py`); no #217 data in the dump. A fresh scorer agent (decision above) writes
   `ev243\verdicts-blind.json` (verdict, class, borderline, one-line reason per question). The
   implementer adds a Progress-log line with its time and sha256 and **commits and pushes that line
   before step 5**. The blind file's exact bytes go into the report json (`blind`). Citation check:
   every cited chunk id is in its retrieved set and in the database; every code number-check flag is
   checked against its passage (real miss / false positive).
5. **Comparison with #217.** Per question: #217 final and first-read verdicts
   (`w10-report.json` `verdicts`), DeepSeek blind verdict, label (decision above) with the deciding
   chunk ids from both runs' retrieved and cited sets (`w10-report.json` `questions` vs this
   `report.json`) and both plans' parts. Blind verdicts are never edited; a reading error found here
   is logged beside the blind verdict with the reason.
6. **Known findings**, each marked still holds / gone / changed with evidence:
   - #217's open items: Q19 planner scoped all parts to EDJ (competitor leg missing); Q24 no
     cross-firm validity statement and no ratio where both inputs are disclosed; Q26 no "why it might
     matter" line and order; Q22 Schwab 3Q26 core NNA `SCHW-PR-2026-10-15-01#3` not retrieved and the
     must-not `MS-PR-2026-04-15-01#15` key error; Q24 must-not `SCHW-TR-2026Q3#10` cited; Q20
     `FIDELITY-III-2025#0`, `UBS-NEXTGEN-2026#119` / `#13` not retrieved; Q15 `SCHW-10K-2025#27`;
     Q25 Schwab dividend-deck must-not chunks; Q11 / Q23 behavior choice; number-check false
     positives on dates.
   - #242 findings: strict-mode arguments that are not JSON (R-off Q22); `number_not_found` flags
     (Q22 x3, Q24 x1 in R-on); reasoning + output tokens against the 64000 / 16000 caps (largest in
     #242: 52%); wall time and tokens/s (46-107 in #242) against the 3600 s read timeout.
7. **Borderline list for the second read**: #217's ten (Q7, Q15, Q16, Q17, Q19, Q22, Q24, Q25, Q26,
   Q28), every question the blind read marks borderline, and every question whose verdict differs
   from #217's final verdict. Protocol as #217: **PR review round 1** - the reviewer agent reads those
   answers in `ev243\answers-dump.txt` / `.eval-runs\0243-real\report.md` against `passes_if` before
   opening the report in the diff, posts its verdicts as a PR comment and returns the PR with the
   "read twice" item open (planned, not a blocking return); the implementer adds the "Second read"
   table (both verdicts, differences discussed, the score stays the first read's with the range the
   second read implies; a disagreement goes to the TL as in #217); **round 2** checks the table and
   merges.
8. **Report**: `docs/results/w11-deepseek-baseline.md` and `.json` as in Files, generated by a
   scratch script in `ev243\` (adapted from `ev217\gen_w10.py`, not committed). Headline: DeepSeek
   score /30 and tier 1 /18 next to #217's 24/30 (14/18), net change split by label, total cost.
9. `/finish-task`: PR "Closes #243" from `.github/pull_request_template.md`; Verification gives real
   calls per attempt, reused, model, why, tokens and dollars; borderline list for the reviewer;
   verify-cee not required (no change to `src/`, `config/`, database or corpus; stated in the PR);
   `gh pr checks` green.

## Paid-call plan (CLAUDE.md "Paid API calls")
- **Go-ahead**: TL comment on #243 (2026-11-19, user approval "批准计划执行以及后续真实调用"):
  run only after every mock check passes, one run per question, a run-level `--max-calls` stated in
  the ExecPlan, no re-rolls, every raw output saved with usage and cost.
- **Questions**: Q1-Q30, one run each, planner + answer = 2 calls per question (all 30 are searched
  in token-budget mode, so the planner is called; any question where code skips the planner is
  named). **Cap `--max-calls 60`.** Expected **54 new calls + 6 reused** (Q1, Q22, Q24 from #242);
  60 if those keys miss.
- **Why the mock cannot show it**: the mock answers whenever retrieval finds something and uses the
  rule plan; the score is a reading of real answers, and DeepSeek's planner parts change the
  retrieved sets.
- **Rough cost** (full price): input ~30 x (1k planner + ~50k answer) ~= 1.5M, almost all cache miss,
  x $1.32 / M ~= $2.0; output with thinking ~30 x (4k planner + ~20k answer) ~= 0.7M x $3.96 / M
  ~= $2.9 (#242 R-on: 10k-33k output per answer). About $4-7 total, about half off-peak. Wall time
  ~2-3 h (#242 R-on: 100-310 s per answer, 25-100 s per planner call).
- **Saved**: every planner and answer record (question, prompt / planner version, model, request
  version, max_tokens, chunk ids, raw output or raw payload, `reasoning_content`, `finish_reason`,
  usage with cache hit / miss and reasoning tokens, `at`, `wall_s`, `tokens_per_s`) in
  `.eval-runs\0243-real\raw\` and `.eval-runs\cache\`, copied to `ev243\real\`.
- **No re-runs.** An invalid output or a planner fallback is a counted call and a finding (answer:
  FAIL, class i). What the code does (#242): an invalid output is saved (`ModelOutputError`,
  `PlannerOutputError`); a planner API / network error saves a `failed_call` record and uses the rule
  plan; a 401 / 402 / 429 raises `ProviderStop` -> `SystemExit("stopped: ...")`, nothing saved, the
  call counted; any other answer-call error (timeout, 400 / 500 / 503) propagates and stops the run
  with nothing saved for that question and no `report.json`. Resume rules (as #217; attempt N >= 2
  on the same commit, `--out .eval-runs\0243-real-N`, log `ev243\real-run-N.log`, same script and
  gates):
  - (a) **Stop outside a model call** (traceback not from a provider request): same command, all 30
    questions; answered questions are reused from the cache at 0 calls; `--max-calls` = 60 minus the
    calls made.
  - (a') **`ProviderStop`** (402 balance, 429 rate limit, 401 key): the provider refused before any
    output, as #217's billing stop (TL decision issuecomment-7011133159, option ii). The refused
    request counts as 1 call with 0 output. Resume only after the coordinator confirms the top-up /
    wait; then as (a), and the refused question's call is made again.
  - (b) **Stop raised by the answer request** (timeout, 400 / 500 / 503): that question's planner and
    answer calls are counted; it is FAIL class i with the traceback quoted, and **never called
    again**. Resume with `--questions` = every question of Q1-Q30 except the stopped one(s);
    answered questions are reused at 0 calls; `--max-calls` = 2 x the questions not yet called.
  - Counting across attempts: per attempt, its **new** raw files (not reused copies) and, when it
    wrote no `report.json`, its log. The report and PR give calls per attempt and the total (<= 60).
  - **Scored records**: the last attempt's `report.json` plus, for each (b) stop, its log entry.
    Step 4's dump, step 8's tables and the report json are built from exactly these.

## Acceptance
- [ ] TL go-ahead before the first call: `gh issue view 243 --comments` shows the 2026-11-19 TL
      comment; `head-log.txt`'s first paid-run line is later.
- [ ] Mock first: `.eval-runs\0243-mock` -> 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22,
      0 forbidden, no status change; 30/30 chunk lists identical (`ev243\mock-diff.txt`).
- [ ] Call count matches the saved raw outputs; 0 re-rolls: per attempt `meta.real_calls` (or the
      log) = new raw files that attempt wrote, except a (b) / (a') stop with a log entry and no file
      (named); reused = 6 (#242) + any resume reuse; total new calls <= 60.
- [ ] Run settings logged: `head-log.txt` shows the pinned settings line, HEAD before and after equal,
      code diff vs 739cb3c empty, `.env` removed.
- [ ] Blind hash committed before the comparison (Progress-log commit precedes any comparison
      commit; hash recomputable from the json's `blind`); second read of the borderline questions
      in PR review round 1, and the report's "Second read" table matches the reviewer's comment.
- [ ] Report lists all 30 verdicts (PASS / FAIL, class for each FAIL), score and tier-1 score, and
      every change against #217 with its label and evidence; cost per question and total in dollars
      (rule above), tokens incl. cache hit and reasoning.
- [ ] 0 code changes: `git diff origin/main...HEAD --stat` lists only the three files above.
- [ ] `gh pr checks <PR#>` all green on the PR head.

## Risks
- **Non-determinism**: one sample per question; a change against #217 may be variance. Labelled, not
  re-rolled.
- **Planner differences**: DeepSeek's plans (e.g. #242's one-part Q1 plan) change retrieval; the
  report names plan-caused changes apart from answer-caused ones.
- **Invalid strict JSON** (#242 R-off Q22): saved, FAIL class i, never re-run.
- **Long calls**: thinking answers took up to 309 s in #242; a timeout (3600 s per read) is rule (b).
- **Reused #242 outputs**: three questions are #242's samples, not new ones; disclosed per question.
  The keys only match under the same code path and settings, so a stale reuse is not possible.
- **Comparison is across models and provider paths**: the report names the provider-path differences
  (thinking, caps, tool_choice) and does not attribute them to the model alone.

## Progress log
- 2026-11-19 22:17 - plan written on `tl/243-ds-baseline` (worktree `D:\ALLPROJECTS\EDJ\wt-243`, at
  739cb3c, the #242 merge). DB up to date (`corpus-2026-11-19`, sync check from the main checkout,
  exit 0; `cee-db` healthy). `git diff --stat f604ab2 739cb3c -- src scripts config` -> only
  `src/cee/config.py` (thinking default), so #242's R-on outputs are reusable. The bank has Q1-Q35,
  so every command lists Q1-Q30. 0 calls.
