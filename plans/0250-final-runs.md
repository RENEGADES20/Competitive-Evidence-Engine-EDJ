# 0250 - W11 final DeepSeek 30-question scored runs: fts (main) and hybrid-norerank (exp/hybrid), shared plans

Issue: #250    Role: TL    Spec: evals/questions.yaml (scoring: `docs/results/w11-deepseek-baseline.md` "How this was run",
`docs/results/0247-reduce-4-check.md` sections 6-7)

## Goal
Two scored runs of Q1-Q30 through the W11 map-reduce pipeline. Both use DeepSeek `deepseek-v4-pro` with thinking on,
snapshot `corpus-2026-11-19` and as-of 2026-11-17, and both answer from the **same 30 plans**:
- **fts** on `main`;
- **hybrid-norerank** on `exp/hybrid`.

Retrieval is the only difference between the two runs. Each run is scored blind by a fresh scorer the TL starts. Each
run gets a second read in its PR review, and is compared with:
- the DeepSeek baseline #243 (15/30 like-for-like, pre-map-reduce pipeline);
- W10 Claude (#217 fts 24/30, #240 hybrid-norerank 25/30);
- #247's adjudicated targets (6/8 on Q1, Q3, Q11, Q19, Q22, Q23, Q24, Q26).

The reports give the cost per question. `docs/NEXT.md` is rewritten and the README Status is updated. No code
changes.

## Inputs read
Issue #250 and both TL comments: the go-ahead (2026-11-19) and the competitor-floor decision (from #249 / PR #264).
`CLAUDE.md` "Paid API calls", `PLANS.md`, `.claude/commands/tl-run.md`, `start-task.md`, `plans/0217-final-run.md`,
`plans/0240-hybrid-parity.md`, `plans/0249-hybrid-sync.md`, `docs/results/w10-report.md`,
`docs/results/w11-deepseek-baseline.md`, `docs/RUN.md` (`--naive-tz`, `--reuse-plans`, `--cache`, `--plan-only`,
`--map-only`, the count rule), `docs/results/0247-reduce-{2,3,4}-check.md`, `plans/0247-reduce-4.md` (run, replay
and guard scripts), and `scripts/eval_run.py`: `RealRunner`, the `plan_cache_key`, `map_cache_key` and
`reduce_cache_key` functions, and `run_bank`.

## Code under test (fixed before any call)
- **fts:** `main` **08b0ac4**, run from `tl/250-final`. That branch is 08b0ac4 plus this plan and evidence only.
  08b0ac4 is 3326abc (#247 part 4 merged) plus one bot line in `docs/PROGRESS.md`, so the code is the same.
  - Code gate before every paid command: `git diff 08b0ac4 HEAD -- src scripts config evals` must be empty.
- **hybrid-norerank:** `exp/hybrid` **36b0b58**, the merge of PR #266, which contains main 08b0ac4.
  - Run from `tl/250-hybrid` (branched from 36b0b58), worktree `D:\ALLPROJECTS\EDJ\wt-250h`.
  - Code gate: `git diff 36b0b58 HEAD -- src scripts config evals` must be empty.
  - `git diff 08b0ac4 36b0b58 -- src/cee/retrieve/planner.py src/cee/retrieve/fts.py src/cee/answer config` must be
    empty. PR #266 proved this, with fts parity 35/35.
- **Versions** (0-call print at 08b0ac4, `DEEPSEEK_THINKING=on`):
  - planner `plan-v3.1`, extract `extract-v1.1`, reduce `v5.2`;
  - request `ds-strict-1-think-on-a64000-p64000`; planner, map and reduce caps 64000.
- **Settings pinned in the run scripts:**
  - `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`,
    `DEEPSEEK_THINKING=on`;
  - `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=6`;
  - `--as-of 2026-11-17 --naive-tz America/Chicago --questions Q1,...,Q30`;
  - hybrid also gets `--mode hybrid-norerank`, `CEE_VECTORS=on` and
    `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`.
- **DB:** `sync-db.ps1 -Check` must say "Database is up to date: corpus-2026-11-19". 21,161 chunks, and 21,161
  `chunk_embeddings` rows for hybrid.

## Saved records reused (CLAUDE.md rule 3; TL note 2)
The run cache is seeded only from the committed DeepSeek record folders `docs/results/0242-deepseek-raw/` (both
subfolders), `0245-planner-raw/`, `0246-map-raw/`, `0247-raw/`, `0247b-raw/` and `0247d-raw/`.
- That is 160 `Q*.json` files, 136 distinct names. The 24 names that appear twice are byte-identical.
- A record is reused only when its file name holds the key the current code computes. A record whose key does not
  match is never read.

The keys guarantee that a reused record had the same input on the same versions:
- **planner:** question, `PLANNER_VERSION`, snapshot, provider, model, the planner cap, the registered metric keys,
  the resolved query and the request version (thinking mode and caps);
- **map:** question, `EXTRACT_VERSION`, snapshot, provider, model, the cap, the request version, the call id, its
  cells, the input chunk ids in order, and the window;
- **reduce:** question, `REDUCE_VERSION`, snapshot, provider, model, the cap, the request version, and sha256 of the
  v5 system prompt, of the rendered reduce message and of the schema.

**The 0-call check** (`ev250\count0-fts`, main 08b0ac4, `--real --max-calls 0`, no key, no `.env`) gives:
- `real_calls` 0; **45 records reused**, all from the #247 work:
  - **8 plans:** Q1, Q3, Q11, Q19, Q22, Q23, Q24, Q26;
  - **all 34 map calls of those 8 questions:** 27 round-1 and 7 re-extraction. Q1 1; Q3 1; Q11 5 + 2; Q19 4 + 3;
    Q22 5; Q23 5; Q24 5 + 1; Q26 1 + 1;
  - **3 reduces:** Q19, Q23, Q26.
- The reused records cost $2.62 when they were made, in #247. They are not new spend in #250.
- **New calls are still needed for:**
  - **the 5 reduces of Q1, Q3, Q11, Q22, Q24.** Their key no longer matches: #247 parts 3-4 changed the rendered
    reduce message, for example Q11's and Q24's new count notes. #247 scored those five as 0-call replays with the
    key pinned to the old record. That was right for a code check, but it is not the current input. A new call here
    is a new input, not a re-roll.
  - **the 22 questions without a saved plan**, for which nothing can be reused (the maps depend on the plan).

Same code and prompt versions, beyond the keys:
- The 0247b-raw records were made at `102f0ad` and the 0247d-raw ones at `2d5f25b`.
- `git diff 102f0ad 08b0ac4 -- src/cee/answer/extract.py src/cee/answer/llm.py src/cee/retrieve/planner.py` holds
  only:
  - #248's timing and usage fields (`finished_at`, the `usage` dict, Anthropic cache-token counts);
  - #247 part 4's `series_pins`, a retrieval pin that reaches the map key through its chunk ids;
  - a comment.
- No prompt text, schema or request option changed, and `src/cee/answer/prompt.py` is unchanged.

The #243 (`plan-v2`, single answer call) and #217 / #240 (Claude) records are a different model and pipeline, so
their keys never match.

## Paid-call plan (CLAUDE.md "Paid API calls"; TL go-ahead on #250, 2026-11-19)
- **Questions:** Q1-Q30, one run each, in each mode. One run is the full flow:
  - a planner call (fts only; hybrid reuses the plan);
  - one map call per firm, plus research;
  - at most one re-extraction per firm with a re-searched cell;
  - one reduce call, or none when code builds the answer.
- **Why the mock cannot show it:** the score is a reading of real answers, and the mock uses rule plans and a mock
  map / reduce. The real planner's sub-questions change the retrieved sets.
- **Phase P, planner (fts worktree): `--plan-only --max-calls 22`.**
  - Exactly the 22 questions with no saved plan (Q2, Q4-Q10, Q12-Q18, Q20, Q21, Q25, Q27-Q30); the 8 saved plans are
    reused.
  - Cost: 22 x ~$0.01-0.02.
- **Count C-fts, 0 calls** (after P): `--real --max-calls 0` over Q1-Q30, seeded cache. Per question it gives:
  - plan origin;
  - round-1 map calls to make (`map_capped_calls`);
  - the reduce at the cap.
- **fts cap** = round-1 map calls (C-fts) + one re-extraction per firm of those calls (the upper bound; the count
  cannot know which cells get re-searched) + one reduce per question whose reduce is not reused (27). It is written
  into the Progress log, with the per-question numbers, **before** the fts run.
  - Estimate: ~70 round-1 calls + ~70 + 27 = ~165 at most; about 100-130 made.
- **Count C-hyb, 0 calls** (after the fts run), on 36b0b58:
  - `--real --max-calls 0 --mode hybrid-norerank --reuse-plans deepseek:deepseek-v4-pro`;
  - the cache is seeded from the committed records plus every record of the fts run;
  - a map call is reused only where its cells and chunk ids are identical, which is the same input.
- **hybrid cap:** the same formula on C-hyb, written down before the hybrid run.
- **Rough cost:**
  - Off-peak: the #247 eight cost $0.18-0.59 per question, $0.33 on average.
  - Most questions are lighter, so about $6-12 per run and $12-25 for both.
  - Peak price is about 2x. DeepSeek's peak window is 01:00-04:00 and 06:00-10:00 UTC on weekdays; the runs start
    off-peak where possible, which changes the price only, not the output.
- **Saved:** every record goes into the run's own cache folder (`--cache`, outside the repo) and its run folder
  `raw/`, valid, invalid or failed. That includes `usage`, reasoning, `stop_reason` and `finished_at`.
  - fts raw is committed to `docs/results/w11-run/raw/`.
  - hybrid raw is committed to `evals/hybrid-eval/corpus-2026-11-19/deepseek/raw/`.
- **Stop rules** (no re-rolls):
  - **ProviderStop** (401 key / 402 balance / 429 rate): the run stops, and nothing is saved for that call, because
    the provider gave no output.
    - The cause is fixed: top-up, wait, or the user fixes the key.
    - The run resumes with the same command and cap minus the calls made. Saved calls are reused at 0 calls.
    - This is not a re-roll: no output existed. It is logged with the HTTP status.
  - **HTTP 400:** the run stops after the round is saved (`bad_request`). There is **no resume without the TL**,
    because a 400 means the request shape is wrong, and fixing that is a code change.
  - **Timeout / 5xx / connection on a map or reduce call:** saved as `failed_call`, counted, and never called again.
    - A failed map cell: that question answers without it, and it is named.
    - A failed reduce: that question is FAIL, class i.
  - **Planner failure:** rule-plan fallback, counted and named. The hybrid run reuses the same record, so it gets the
    same rule plan.
  - **Invalid output:** a finding, class i, never re-called.
  - **Process crash outside a call:** resume with the same command, as above.
- **Total per run** = calls made (`meta.real_calls`) = new files in `raw/`, as defined in Acceptance. It is stated
  per phase and per attempt, and it stays within the caps.

## Run scripts (TL note 1: evidence, not code; parameterised for #259)
Committed in `docs/results/w11-run/`, and copied unchanged into `evals/hybrid-eval/corpus-2026-11-19/deepseek/` on
the hybrid branch. Each has a `.ps1` and a `.sh` twin.

**`seed-cache.ps1` / `.sh <cache dir> <worktree> [extra record folders...]`**
- Copies `Q*.json` from the committed record folders, plus any extra folder (for hybrid: the fts run's `raw/`), into
  a new, empty cache folder.
- Stops if the folder exists, or if two files with one name differ.

**`run-mock.ps1` / `.sh -Wt <worktree> -Out <name> [-Mode fts|hybrid-norerank] [-ReusePlans PROVIDER:MODEL -Cache <dir>]`**
- `LLM_PROVIDER` mock, 0 calls.

**`run-scored.ps1` / `.sh`**
- Parameters:
  - `-Wt <worktree> -Out <name> -Cache <dir> -MaxCalls <n> -Phase plan|count|run`;
  - `-Provider deepseek|anthropic -Model <id> [-Mode fts|hybrid-norerank] [-ReusePlans]`.
- The provider block pins the settings above. `anthropic` sets `LLM_MODEL` instead, for #259 with
  `claude-sonnet-5-5`, and `-ReusePlans` takes `<provider>:<model>`.
- Guard before a run. It stops with exit 3 and makes no call if any of these fails:
  - `git status` clean;
  - no `.env` in the worktree;
  - out folder new;
  - the code gate holds.
  It logs HEAD, branch and time to `head-log.txt`.
- `-Phase count` forces `--max-calls 0` and never copies `.env`.
- `-Phase plan|run`:
  - copies the main repo's `.env` into the worktree inside `try` (trap on Mac);
  - removes it in `finally` and logs that it is absent;
  - unsets the pinned variables afterwards.
  The script only copies `.env`; it never reads or prints it, and it is never committed.
- Logs HEAD, branch and `.env` absence after the run.

**`replay.ps1` / `.sh`**
- A 0-call replay of a finished run, with the run's own `raw/` as the cache.
- Expected: `real_calls` 0, every record reused, and answers identical to the run's `report.json`.

Scratch scripts (dump, blind-in builder, comparison, cost) live in `D:\ALLPROJECTS\EDJ\cache\ev250\`. They are not
committed. Their outputs are committed or quoted in the reports.

## Files to change
**PR 1, `tl/250-final` -> `main`, "Part of #250":**
- `plans/0250-final-runs.md`: this plan and its Progress log.
- `docs/results/w11-run/`:
  - the run scripts above;
  - `raw/` (every record the fts run served, new and reused copies);
  - `count-fts.md` (the 0-call counts and caps);
  - `head-log.txt`;
  - `verdicts-blind.json` (committed alone first);
  - `run-report.json` (the run's `report.json`).
- `docs/results/w11-report.md` and `docs/results/w11-report.json`, the fts report:
  - how it was run, the score and tier-1 score;
  - the per-question table with cost;
  - the comparisons, the second-read table, and the 30 answers;
  - the json has `blind` (the exact bytes), `verdicts`, `first_read` / `second_read`, and `cost`.
- `docs/NEXT.md`: rewritten from the W11 failures (fts, with the hybrid line added by PR 2's note; see step 12).
- `README.md`: the "Status" section only.

**PR 2, `tl/250-hybrid` -> `exp/hybrid`, "Closes #250"** (the TL closes the issue by hand: `exp/hybrid` is not the
default branch). `evals/hybrid-eval/corpus-2026-11-19/deepseek/` holds:
- the scripts (copied);
- `raw/`, `count-hyb.md`, `head-log.txt`;
- `verdicts-blind.json` (committed alone first);
- `run-report.json`;
- `report.md` and `report.json`: the hybrid verdicts and the comparison with W11 fts, W10 hybrid (#240), #243 and
  #247;
- `mock-real-plans.md`: the step 5 tables.

No file in `src/`, `config/`, `scripts/`, `tests/`, `evals/questions.yaml`, `evals/expected_chunks.yaml`, the
baselines or the database changes, in either PR.

## Steps
1. **Pre-checks, 0 calls**, both worktrees:
   - `git status` clean, no `.env`;
   - the code gates;
   - the version print;
   - `sync-db -Check`;
   - `chunk_embeddings` count;
   - log `git rev-parse HEAD`.
2. **Scripts.** Write the run scripts. Test each with `-Phase count` / mock only (0 calls), including the
   guard's stop paths: dirty tree, `.env` present, out folder exists. The `.sh` twins are run under Git Bash with
   `-Phase count`. A teammate's Mac run is not needed: the scripts touch no OS-specific path beyond the parameters.
3. **Mock, both modes, 0 calls** (rule plans, Q1-Q35, `--as-of 2026-11-17`):
   - fts at `tl/250-final` and hybrid-norerank at `tl/250-hybrid` (36b0b58 code).
   - Expected: identical to PR #266's runs on the same code (`ev250sync\main-fts`, `ev250sync\hyb-norerank`): chunk
     lists, statuses and answers on 35/35.
   - fts: 33 PASS / 2 FAIL, refusal gap 8/8, keyed 26/26, 0 forbidden. Also against
     `evals/baselines/corpus-2026-11-19/report.json` with `--baseline`: changes listed, none unexplained.
   - hybrid-norerank: 31 PASS, refusal gap 7/8, keyed 24/26 (Q22 and Q24 retrieve a must-not chunk and do not
     cite it).
   - Any other difference stops the paid work and is reported.
4. **Phase P, 22 planner calls** (fts worktree, `run-scored -Phase plan -MaxCalls 22`, cache
   `ev250\cache-fts` seeded by `seed-cache`). Then check:
   - `real_calls` 22; new plan files 22;
   - the 8 saved plans reused;
   - no fallback, or each fallback named;
   - every `finish_reason` `tool_calls`.
5. **Mock on the real plans, both modes, 0 calls** (`run-mock -ReusePlans deepseek:deepseek-v4-pro -Cache
   ev250\cache-fts`, hybrid on a copy of that cache). #249's tables on the DeepSeek plans, saved as
   `mock-real-plans.md` (PR 2):
   - plans identical across modes, 30/30;
   - per-question chunk lists, shared chunks, refusal and keyed checks;
   - pins per sub-question;
   - **the competitor floor table**: per competitor sub-question, before -> after the floor, dropped / emptied,
     competitor passages to the map, and the corrective re-search on competitor sub-questions.
   The TL decision covers Q19 a1.MER on the mock plans. **If the floor fires on any other question or
   sub-question with the DeepSeek plans, the table goes to the TL before the hybrid paid run (step 8).** The fts
   run does not wait.
6. **Count C-fts, 0 calls** (`-Phase count`). The caps are computed as in the paid-call plan and committed with the
   per-question table in `docs/results/w11-run/count-fts.md`, before step 7.
7. **fts run** (`-Phase run -MaxCalls <cap>`). Then:
   - `replay` (0 calls, guard: answers identical);
   - copy `raw/` and `report.json` into `docs/results/w11-run/`;
   - record `real_calls`, reused, per-question calls by type, `how`, stop reasons, invalid / failed calls, tokens
     and USD (new and total).
8. **Count C-hyb, 0 calls, then the hybrid run.** In `wt-250h` (36b0b58 code):
   - `seed-cache ev250\cache-hyb <wt> <fts raw>`;
   - `-Phase count` with `-Mode hybrid-norerank -ReusePlans deepseek:deepseek-v4-pro` (a missing plan stops it at 0
     calls); cap committed in `count-hyb.md`;
   - `-Phase run`, then `replay`, and copy into the evidence folder.
   `PlanMissing` or any planner call is a defect: stop and report.
9. **Blind inputs, one set per run** (TL note 4):
   - `ev250\blind-in-fts\` and `ev250\blind-in-hyb\`, each with:
     - `answers-dump.txt`: the 30 answers with claims and cited passage text, adjacent items, gaps, caveats, parts;
       the same dump format as #243 / #247;
     - `questions.yaml`;
     - `verdict-rule.txt`.
   - Verdict rule (#217 / #243 bar): PASS only if the project lead would forward it with his name on it against
     `passes_if`; no half credit; borderline named. Classes:
     - r: retrieval missed a passage the corpus holds;
     - s: shape, or a required part missing;
     - b: behavior;
     - c: corpus gap;
     - i: invalid output.
   - Scorer prompts are `ev250\scorer-prompt-{fts,hyb}.txt`, with sha256 of every input in `blind-in-*-hashes.txt`.
   - The dumps hold no mode name, no run name and no earlier verdict.
   - **The TL starts two fresh scorer agents.** The hybrid scorer never sees the fts answers or verdicts.
   - Each `verdicts-blind.json` is committed **alone**, with its sha256 in the Progress log, before any comparison
     is opened. PR 1 gets the fts file, PR 2 the hybrid file.
   - Citation check per run: every cited chunk is in its retrieved set (retrieval plus corrective re-search) and in
     the database. Code number-check flags are checked against their passages.
10. **Comparison, 0 calls.** For each run, per question:
    - #243 like-for-like (15/30, tier 1 10/18);
    - W10 (#217 fts 24/30; #240 hybrid-norerank 25/30);
    - #247's adjudicated final for its eight (Q1, Q3, Q19, Q22, Q24, Q26 PASS; Q11, Q23 FAIL).
    Every changed verdict gets a label with the deciding chunk ids:
    - **plan:** DeepSeek plan-v3.1 sub-questions vs the earlier plans;
    - **retrieval:** a deciding passage entered or left;
    - **pipeline:** map-reduce vs the single answer call;
    - **model:** DeepSeek vs Claude, or one sample vs another where the inputs are the same;
    - **scorer reading:** the same answer shape read differently; the earlier answer is compared.
    The eight #247 questions reuse #247's maps (and Q19 / Q23 / Q26 their reduces), so a verdict that differs from
    #247's on a byte-identical answer is named as scorer variance.
    **Between modes (PR 2):**
    - Same plans, so a difference is retrieval, or model variance where the deciding passages reached both maps.
    - **Q19 (TL floor decision):** any Q19 difference that comes from Merrill or other competitor passages is
      attributed to the ADR-018 competitor floor (fts cuts, hybrid-norerank keeps), not to ranking, with the floor
      table from step 5. The same applies to any question where step 5 shows the floor firing.
    - Questions whose two answers are byte-identical (every record shared) and whose verdicts differ are scorer
      variance, named.
11. **Reports.** Generated by scratch scripts.
    - `w11-report.md` / `.json` (fts):
      - how it was run (commit, settings, request version, commands, attempts, caps, calls per phase, reused list);
      - score and tier 1;
      - the per-question table: tier, expected -> got behavior, #243, W10 fts, #247 (eight), W11 fts verdict,
        class, borderline, change label, calls (new / reused) and **USD per question** (new and total, peak /
        off-peak);
      - the changes tables;
      - known findings carried from `docs/NEXT.md` / #247 (Q11 definitions corpus limit, Q23 corpus gap NEXT
        item 11, Q22 / Q25 must-not, Q19 competitor leg), each marked still holds / gone / changed;
      - the second-read table (step 12);
      - the 30 answers.
    - The hybrid `report.md` / `.json`: the same, plus the mode-vs-mode table and the floor attribution.
    - Cost: from `report.json` `cost` (USD per call, by completion time) and `scripts/eval_cost.py` over each `raw/`.
      Reused calls are shown at their original cost but not as new spend.
12. **Second read** (#217 protocol), done by the PR-review reviewer agent, not the implementer. In round 1 it reads
    the answers from the dump against `passes_if` before opening the report, and posts its verdicts as a PR
    comment. The return is planned, not blocking. Round 2 checks the "Second read" table and merges.
    - **PR 1 reads:** every borderline question in the fts blind file, the six W10 failures (Q11, Q19, Q20, Q23,
      Q24, Q26) and every verdict change against #243 or W10 fts.
    - **PR 2 reads:**
      - every borderline question in the hybrid blind file;
      - the six W10 failures;
      - **every question whose hybrid verdict differs from the final W11 fts verdict**, with both answers read side
        by side.
      A changed fts reading in PR 2 is recorded in the hybrid report as a range; `w11-report.md`, already merged, is
      not rewritten.
    - Each report gives the first (blind) score, the second-read verdicts, the final score, and the range the
      second read implies.
13. **NEXT.md and README.**
    - NEXT is rewritten from the W11 fts failures, each item with question IDs, class, size and the check.
      #243 / W10 items that W11 closed are dropped or marked done. The hybrid result goes in as one line that points
      to PR 2's report, once PR 2 has a final score; until then it says "pending (#250 PR 2)".
    - README Status: date, the W11 fts score next to W10 and #243, links.
    - The scratch NEXT check: every FAIL question appears in an item, and no item rests only on passing questions.
14. **/finish-task** for each PR:
    - `.github/pull_request_template.md` with Verification: calls per phase and attempt, model, why, reused records,
      USD;
    - the Progress line;
    - the borderline / second-read list for the reviewer.
    verify-cee is not required: no change to `src/`, `config/`, the database or the corpus (stated). The PRs must
    have `gh pr checks` green.

## Acceptance
- [ ] The TL go-ahead (#250, 2026-11-19) predates the first paid call (`head-log.txt` times).
- [ ] Mock first (step 3): fts and hybrid-norerank identical to PR #266's runs on 35/35, with the expected
      PASS / refusal / keyed counts; step 5 tables on the real plans written, and the floor table sent to the TL if it
      fires beyond Q19 a1.MER.
- [ ] Plans shared: hybrid `--reuse-plans`, 0 planner calls; the plan files of both runs are identical (30/30 by
      name and sha256).
- [ ] Caps written before each paid phase (22; C-fts; C-hyb). Per phase and attempt, `meta.real_calls` = new raw
      files. New raw files are those absent from the seeded cache before the phase, excluding copies of reused
      records; an answer stopped under a ProviderStop has a log entry and no file.
- [ ] 0 re-rolls: no question, map or reduce called twice for one key. A replay of each run gives 0 calls and
      identical answers.
- [ ] Settings pinned: every new record has `provider` deepseek, `model` deepseek-v4-pro and `request_version`
      `ds-strict-1-think-on-a64000-p64000`. `.env` is absent before and after each paid command, never committed
      and never read.
- [ ] The checkout did not move: HEAD before = after for every paid command; code gates held.
- [ ] Blind: one blind-in set per run, two fresh scorers started by the TL, and each `verdicts-blind.json` committed
      alone with its sha256 before any comparison.
- [ ] Reports: all 30 verdicts per run; score and tier 1; every change against #243, W10 and #247's eight labelled
      with chunk ids; USD per question and the run total (new and reused); the Q19 floor attribution in the mode
      comparison.
- [ ] Second read in each PR review (round 1 comment), and the reports' "Second read" tables match it.
- [ ] `docs/NEXT.md` rewritten (the check script passes); README Status updated.
- [ ] 0 code changes: `git diff 08b0ac4 --stat` (PR 1) and `git diff 36b0b58 --stat` (PR 2) list only the files
      above.
- [ ] `gh pr checks` green on both PRs.

## Risks
- **One sample per question.** A verdict change can be model variance. It is labelled "model" where the deciding
  passages were available both times, and it is not re-rolled.
- **Shared records between modes.** Identical map inputs reuse one output, so both modes get the same sample there.
  That is the intended like-for-like, and the report shows how many map calls each question shared.
- **The 8 #247 questions** mostly reuse #247's records (tuned on). Their verdicts are compared with #247's
  adjudicated ones and reported separately from the other 22.
- **Floor on the real plans:** the DeepSeek plans may give competitor sub-questions beyond Q19. Step 5 measures this
  and the TL sees it before the hybrid run.
- **Peak pricing / long calls:** thinking on, up to 64k output per call, and the 3600 s read timeout. A timeout is a
  failed call: saved, never re-called, a finding.
- **Scorer bias:** fresh blind scorers, hash-first commits, a second read in review, and the range reported.

## Progress log
- 2026-11-20 - Step 0 is done before this plan: PR #266 merged `main` 08b0ac4 into `exp/hybrid` with a merge
  commit. `exp/hybrid` is now 36b0b58.
  - fts parity 35/35 vs main.
  - The competitor floor table is unchanged (Q19 a1.MER only).
  - pytest 1148 with vectors on; 1146 + 2 skipped with vectors off.
  - 0 calls.
- 2026-11-20 - plan written on `tl/250-final` from main 08b0ac4.
  - The 0-call coverage check (`ev250\count0-fts`, no key, no `.env`) reuses 45 records (8 plans, 34 maps,
    3 reduces) and gives 22 planner calls to make.
  - The 5 reduces of Q1, Q3, Q11, Q22 and Q24 have new keys (parts 3-4 changed the rendered message).
  - Model-facing code since `102f0ad`: timing and usage fields and `series_pins` only.
  - 0 calls so far.
