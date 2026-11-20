# 0250 - W11 final DeepSeek 30-question scored runs: fts (main) and hybrid-norerank (exp/hybrid), shared plans

Issue: #250    Role: TL    Spec: evals/questions.yaml (scoring: `docs/results/w11-deepseek-baseline.md` "How this was run",
`docs/results/0247-reduce-4-check.md` sections 6-7)

TL inputs on #250:
- the go-ahead (issuecomment-7029133145);
- the competitor-floor decision (issuecomment-7047676757);
- the TL notes for this plan (issuecomment-7048955602; cited below as "TL note 1-4");
- the TL rulings on plan review round 1 (issuecomment-7048978281; cited as "R1 ruling").

## Goal
Two scored runs of Q1-Q30 through the W11 map-reduce pipeline. Both use DeepSeek `deepseek-v4-pro` with thinking on,
snapshot `corpus-2026-11-19` and as-of 2026-11-17, and both answer from the **same 30 plans**:
- **fts** on `main`;
- **hybrid-norerank** on `exp/hybrid`.

Retrieval is the only difference between the two runs. Each run is scored blind by a fresh scorer the TL starts, and
gets a second read in its PR review. Each run is compared with:
- the DeepSeek baseline #243 (15/30 like-for-like, the pre-map-reduce pipeline);
- W10 Claude (#217 fts 24/30; #240 hybrid-norerank 25/30);
- #247's adjudicated targets (6/8 on Q1, Q3, Q11, Q19, Q22, Q23, Q24, Q26).

The reports give the cost per question. `docs/NEXT.md` is rewritten and the README Status is updated. No code changes.

## Inputs read
Issue #250 and the TL comments above. `CLAUDE.md` "Paid API calls", `PLANS.md`, `.claude/commands/tl-run.md`,
`start-task.md`, `plans/0217-final-run.md`, `plans/0240-hybrid-parity.md`, `plans/0249-hybrid-sync.md`,
`docs/results/w10-report.md`, `docs/results/w11-deepseek-baseline.md`, `docs/RUN.md` (`--naive-tz`, `--reuse-plans`,
`--cache`, `--plan-only`, `--map-only`, the count rule), `docs/results/0247-reduce-{2,3,4}-check.md`,
`plans/0247-reduce-4.md` (run, replay and guard scripts). From `scripts/eval_run.py`: `RealRunner`,
`plan_cache_key` / `map_cache_key` / `reduce_cache_key`, `run_bank`. From `src/cee/answer/extract.py`:
`extract_message`, `run_map`.

## Code under test (fixed before any call)
**fts:** `main` **08b0ac4**.
- 08b0ac4 is 3326abc (#247 part 4 merged) plus one bot line in `docs/PROGRESS.md`, so the code is the same.
- Run from `tl/250-final`, which holds only this plan and the evidence on top of 08b0ac4.
- Code gate (before every paid command): `git diff 08b0ac4 HEAD -- src scripts config evals` is empty. The fts
  evidence lives under `docs/`, outside the gate.

**hybrid-norerank:** `exp/hybrid` **36b0b58**, the merge of PR #266, which contains main 08b0ac4.
- Run from `tl/250-hybrid` (from 36b0b58), worktree `D:\ALLPROJECTS\EDJ\wt-250h`.
- Code gate (R1 ruling, blocking 2):
  `git diff 36b0b58 HEAD -- src scripts config evals ':(exclude)evals/hybrid-eval/corpus-2026-11-19/deepseek'` is
  empty. The hybrid evidence folder is committed during the work, so the gate excludes it.
- `git diff 08b0ac4 36b0b58 -- src/cee/retrieve/planner.py src/cee/retrieve/fts.py src/cee/answer config` is empty.
  The plan reviewer checked this: 0 lines. PR #266 proved fts parity 35/35.
- Both gates are a parameter of the run script (`-GateSha`, `-GateExclude`), not hard-coded.

**Versions** (0-call print at 08b0ac4 with `DEEPSEEK_THINKING=on`): planner `plan-v3.1`, extract `extract-v1.1`, reduce
`v5.2`; request `ds-strict-1-think-on-a64000-p64000`; planner / map / reduce caps 64000.

**Settings pinned in the run scripts:**
- `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`,
  `DEEPSEEK_THINKING=on`, `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=6`.
- `--as-of 2026-11-17 --naive-tz America/Chicago --questions Q1,...,Q30`.
- Hybrid also: `--mode hybrid-norerank`, `CEE_VECTORS=on`, and `FASTEMBED_CACHE_PATH` (a parameter;
  `D:\ALLPROJECTS\EDJ\cache\fastembed` here).

**DB:** `sync-db.ps1 -Check` reports "Database is up to date: corpus-2026-11-19". 21,161 chunks, and 21,161
`chunk_embeddings` rows (hybrid).

## Saved records reused (CLAUDE.md rule 3; TL note 2)
**Seed.** The run cache is seeded only from the committed DeepSeek record folders:
- `docs/results/0242-deepseek-raw/` (both subfolders), `0245-planner-raw/`, `0246-map-raw/`, `0247-raw/`,
  `0247b-raw/`, `0247d-raw/`;
- 160 `Q*.json` files, 136 distinct names; the 24 names that occur twice are byte-identical.

A record is reused only when its file name holds the key the current code computes. Any other record is never read.

**What the keys cover:**
- **planner:** question, `PLANNER_VERSION`, snapshot, provider, model, the planner cap, the registered metric keys,
  the resolved query and the request version (thinking mode and caps).
- **map:** question, `EXTRACT_VERSION`, snapshot, provider, model, cap, request version, call id, cells, the input chunk
  ids in order, and the window. It does **not** hash the per-sub-question grouping (`spec.groups`) or the
  `NO_PASSAGES` / `KEPT_ELSEWHERE` markers (`spec.pools`), and `extract_message` renders both (plan review nb 2). Map
  reuse is therefore also proved message by message (step 7). That is blocking for the hybrid run (R1 ruling) and is
  applied to fts too.
- **reduce:** question, `REDUCE_VERSION`, snapshot, provider, model, cap, request version, and sha256 of the v5 system
  prompt, of the rendered reduce message and of the schema.

**What the 0-call check reuses.** Check: `ev250\count0-fts` on main 08b0ac4, `--real --max-calls 0`, no key, no
`.env`. It reports `real_calls` 0 and **45 records reused**, all from the #247 work. None of them is invalid or
failed, and every `request_version` is `ds-strict-1-think-on-a64000-p64000`.

| Records | What | Made at (from the record folders and run logs) |
|---|---|---|
| 5 plans | Q11, Q19, Q23, Q24, Q26 | #246 (`0246-map-raw`), planner code as at b8c1242 |
| 3 plans | Q1, Q3, Q22 | #247 part 1 (`0247-raw`), gate 7b9a5b4 |
| 34 map / remap | Q1 1; Q3 1; Q11 5 + 2; Q19 4 + 3; Q22 5; Q23 5; Q24 5 + 1; Q26 1 + 1 | `0247-raw` (7b9a5b4), `0247b-raw` (run 6a3825a, code gate 715adda), and Q23 `map.RJF` from `0247d-raw` (2d5f25b) |
| 3 reduces | Q19, Q26 | `0247b-raw` (a0ceb61) |
|  | Q23 | `0247d-raw` (2d5f25b) |

These records cost $2.62 when #246 / #247 made them. That is not new spend in #250.

**Model-facing code since those commits.** Checked by the plan reviewer and here:
- `git diff 7b9a5b4 08b0ac4 -- src/cee/answer/extract.py src/cee/answer/llm.py` holds only timing, usage and call-log
  fields. `extract_message`, `system_prompt`, the schema and the DeepSeek request are unchanged.
- `git diff b8c1242 08b0ac4 -- src/cee/retrieve/planner.py` holds only `asked_firms`, the usage / `finished_at` stamp,
  and the pin and period passes (retrieval). No prompt, schema or request change.
- `src/cee/answer/prompt.py` changed by 26 lines: the reduce prompt went from v5 to v5.2 (746c8d0, 20663ec).
  - The map is not affected: `extract.py` does not import `prompt.py`.
  - The reused reduces are safe: their key hashes `REDUCE_VERSION` and the system prompt (plan review round 2, nb 3).

Retrieval changes since then reach the map key through its chunk ids. The grouping is checked by the message hashes
of step 7. The report's "how it was run" repeats these bases.

**Still to be called:**
- **The 5 reduces of Q1, Q3, Q11, Q22, Q24.** Their key no longer matches: #247 parts 3-4 changed `reduce.py` /
  `matrix.py`, which build the rendered message the key hashes. #247 scored those five as 0-call replays with the key
  pinned to the old record. These are new inputs, not re-rolls.
- **The 22 questions without a saved plan.**
- **Any #247 map record whose message hash differs** in step 7.

#243 records (`plan-v2`, a single answer call) and #217 / #240 records (Claude) have keys that never match.

## TL approval conditions (issuecomment-7049142807; plan review round 2, issuecomment-7049132420)
These override any step below that says otherwise.

**C1. The hash check runs on the worktree's own code** (round 2, blocking 1).
- `diag/map_msg_hash.py` takes `--wt <worktree>`:
  - It puts `<wt>/src` and `<wt>/scripts` first on `sys.path`, and the scripts also set `PYTHONPATH=<wt>\src`.
  - It imports `eval_run` from `<wt>/scripts` before any `cee` import.
- The tsv header records `extract.__file__`, `eval_run.__file__` and `git -C <wt> rev-parse HEAD`.
- It aborts (exit 3) unless both files are under `<wt>`.
- `DEEPSEEK_API_KEY` is set to empty for every hash run, so a slip can only fail with a 401.
- It refuses any `--max-calls` other than 0 (exit 3; round 2, nb 6).

**C2. The producing commit is assigned per record, from the record's `at`** (round 2, blocking 2):
- 7b9a5b4 for `at` 02:49-04:06;
- 715adda for 06:57-07:32 (Q11 five maps + `remap.MS`; Q22 `map.MS`; Q23 EDJ / MER / MS / SCHW; Q24 five maps +
  `remap.SCHW`);
- 2d5f25b for Q23 `map.RJF` (12:49).

No code commit falls inside those windows. Every record falling outside these windows has no producing commit; it is
left out and called.

Each historical replay:
- runs on a detached worktree at that commit with that commit's own CLI. 7b9a5b4 and 715adda have no `--cache` and no
  `--naive-tz`, so the seed goes into `<wt>/.eval-runs/cache` (gitignored);
- uses the producing run's questions, `--as-of 2026-11-17`, the pinned env and `--max-calls 0`.

`count-fts.md` gets a record -> `at` -> commit column.

**C3. Allow-list cache** (round 2, blocking 3).
- Of the inherited map / remap records (#247's, and for hybrid also the fts final `raw/`), the run cache holds **only**
  those the **final** 0-call count served with matching message hashes (message, system prompt, schema).
- Every other inherited `*map.*` / `*remap.*` record is left out, so any such call is made. A remap that only becomes
  reachable after a new round-1 call is therefore made, never reused unverified.
- Plans and reduces are unaffected: the plan key hashes the query, and the reduce key hashes the rendered message.
- The remaps and maps left out are counted in `count-fts.md` / `count-hyb.md`.

**C4. Round-2 non-blocking 1-6:**
1. The round-2 bound counts distinct `_row_key(entity)` values (a firm, or `all` for theme questions).
2. Cached remaps are subtracted only for questions whose round 1 was fully served at the count.
3. The `prompt.py` statement is corrected (above).
4. The reports count reduces shared between modes next to the shared map records.
5. An Acceptance line for the post-run tsv cross-check.
6. The wrapper refuses `--max-calls` other than 0 (C1).

## Paid-call plan (CLAUDE.md "Paid API calls"; TL go-ahead issuecomment-7029133145)
**Questions.** Q1-Q30, one run each in each mode. One run is the full flow:
- a planner call (fts only; hybrid reuses the plan);
- one map call per firm, plus research;
- at most one re-extraction per firm;
- one reduce call, or none when code builds the answer.

**Why the mock cannot show it.** The score is a reading of real answers. The mock uses rule plans and a mock map and
reduce, and the real planner's sub-questions change the retrieved sets.

**Phase P (planner, fts worktree): `--plan-only --max-calls 22`.** Exactly the 22 questions with no saved plan: Q2,
Q4-Q10, Q12-Q18, Q20, Q21, Q25, Q27-Q30. Cost about 22 x $0.01-0.02.

**Counts C-fts / C-hyb (0 calls)** give per question:
- the round-1 map calls to make (`map_capped_calls`);
- the round-2 bound: **its distinct firm rows of its non-research, non-comparison sub-questions**, minus remap records
  already cached (R1 ruling, blocking 1). This is #247's rule: `run_map` groups re-extractions by firm over every
  re-searched sub-question, including code cells of a firm with no round-1 call (#247's Q19 has `remap.RJF` without
  `map.RJF`);
- whether its reduce is cached.

**Cap per run** = Σ round-1 map calls to make + Σ round-2 bounds + the reduces not cached. It goes into
`count-fts.md` / `count-hyb.md` with the per-question table, committed **before** that run. Estimate for fts: about
70 + 70 + 27, so about 170 at most and 100-130 made.

**If a cap is reached anyway:**
- the capped calls are not made, and their questions and call ids are named (`map_capped_calls`, reduce `how = cap`);
- **no further call without the TL** (no silent top-up);
- a capped question is reported as not answered (`cap`), never scored as a model failure.

**C-hyb runs after the fts run**, on 36b0b58, with `--reuse-plans deepseek:deepseek-v4-pro`. Its cache is seeded from
the committed records plus the fts run's records. Reuse is filtered by step 7's message check.

**Rough cost (off-peak).**
- The #247 eight cost $0.18-0.59 per question ($0.33 on average). Most of the other 22 are lighter.
- About $6-12 per run, $12-25 for both. Peak is about 2x.
- DeepSeek peak is 01:00-04:00 and 06:00-10:00 UTC on weekdays (`config/pricing.yaml`). Runs start off-peak where
  possible; this changes the price, not the output.

**Saved.**
- Every record (valid, invalid or failed, with `usage`, reasoning, `stop_reason` and `finished_at`) goes into the run's
  cache folder (`--cache`, outside the repo) and into its attempt folder's `raw/`.
- The **final attempt's** `raw/` is committed: `docs/results/w11-run/raw/` for fts,
  `evals/hybrid-eval/corpus-2026-11-19/deepseek/raw/` for hybrid. It holds a copy of every record the final attempt
  served, including those made by earlier attempts (reused copies).

**Attempts and resume (R1 ruling, blocking 3).** Attempt 1 writes to `-Out <name>`. A resume is a **new** attempt:
- `-Out <name>-a2` (`-a3`, ...), with the **same** `-Cache` and `-MaxCalls` = cap minus the calls made by all earlier
  attempts;
- calls made per attempt are taken from that attempt's `meta.real_calls`, or from its log and new cache files when it
  wrote no report;
- the total across attempts stays at or below the cap;
- each attempt keeps its log and `head-log`;
- the report lists the calls of each attempt.

**Stop rules (no re-rolls).**
- **ProviderStop** (401 key / 402 balance / 429 rate): the run stops and nothing is saved for that call; the provider
  gave no output. After the cause is fixed (top-up, wait, or the user fixes the key), a resume attempt as above. This
  is not a re-roll: there was no output. The HTTP status is logged.
- **HTTP 400:** the run stops after the round is saved (`bad_request`). **No resume without the TL** (a request-shape
  fault needs a code change).
- **Timeout, 5xx or connection error** on a map or reduce call: saved as `failed_call`, counted, and reused as failed,
  never called again. A failed map cell: that question answers without it, and it is named. A failed reduce: FAIL,
  class i.
- **Planner failure:** rule-plan fallback, saved, counted, and named. Hybrid reuses the same record, so it gets the same
  rule plan.
- **Invalid output:** a finding (class i), never called again.
- **Crash outside a call:** a resume attempt.

**Count per run.** Total = Σ `meta.real_calls` over attempts = Σ new cache files per attempt (files absent from the
cache before the attempt). A ProviderStop'd call has a log entry and no file. All of this is within the caps.

## Run scripts (TL note 1: run evidence, not code; parameterised for #259)
Committed in `docs/results/w11-run/`, and copied unchanged into `evals/hybrid-eval/corpus-2026-11-19/deepseek/` on the
hybrid branch. Each is a `.ps1` with a `.sh` twin.

**`seed-cache.ps1` / `.sh <cache dir> <worktree> [extra record folders...]`**
- Copies `Q*.json` from the committed record folders (plus extra folders, e.g. the fts final `raw/`) into a new, empty
  cache.
- Stops if the cache folder exists or two same-named files differ.
- `-Drop <list file>`: names of records to leave out (step 7).

**`run-mock.ps1` / `.sh -Wt -Out [-Mode] [-ReusePlans PROVIDER:MODEL -Cache]`**
- `LLM_PROVIDER` mock, 0 calls.

**`run-scored.ps1` / `.sh`**
- Parameters: `-Wt -Out -Cache -MaxCalls -Phase plan|count|run -Provider deepseek|anthropic -Model`, plus
  `[-Mode] [-ReusePlans] -GateSha <sha> [-GateExclude <path>] [-FastembedPath <dir>] [-EnvFile <main repo .env path>]`.
- The provider block pins the settings above. `anthropic` sets `LLM_MODEL` for #259 (`claude-sonnet-5-5`).
- **Guard:** clean `git status`; no `.env` in the worktree; the out folder does not exist; the code gate holds.
  - Any failure: exit 3, no call.
  - HEAD, branch, time and settings go to `D:\ALLPROJECTS\EDJ\cache\ev250\<out>.head-log.txt`, next to the out folder
    and outside the worktree (plan review nb 4), so the tree stays clean. It is copied to the evidence folder
    afterwards.
- `-Phase count` forces `--max-calls 0` and never copies `.env`.
- `-Phase plan|run`:
  - copies `-EnvFile` into the worktree inside `try` (a trap on Mac);
  - removes it in `finally`;
  - logs that it is absent and unsets the pinned variables.
  The script only copies it: never read, printed or committed.

**`replay.ps1` / `.sh`**
- A 0-call replay of a finished attempt, with its `raw/` as the cache.
- Expected: `real_calls` 0, every record reused, answers identical to the attempt's `report.json`.

**`diag/map_msg_hash.py`** (0 calls, R1 ruling), a wrapper around `scripts/eval_run.py`:
- It patches nothing that reaches a provider. It wraps the `call` that `RealRunner.map` passes to `extract.run_map`.
  Through `eval_run.map_cache_key` it remembers each spec's key.
- For every map / remap spec served (new or reused), it logs:
  - the record file name;
  - sha256 of `extract.extract_message(question, spec, window, firms)` (the exact text the call sends or sent);
  - sha256 of `system_prompt(spec.research)` and of `extraction_schema(spec)`.
- It then runs `eval_run.main()` with the given arguments (`--max-calls 0` only).
- Output: a tsv per run.

Scratch scripts (dump, blind-in builder, comparison, cost) live in `D:\ALLPROJECTS\EDJ\cache\ev250\`, not committed.
Their outputs are committed or quoted in the reports.

## Files to change
**PR 1, `tl/250-final` -> `main`, "Part of #250":**
- `plans/0250-final-runs.md` (this plan and its Progress log).
- `docs/results/w11-run/`:
  - the run scripts and `diag/map_msg_hash.py`;
  - `count-fts.md` (counts, caps, the message-hash table for the #247 maps);
  - the head logs;
  - `raw/` (the final attempt);
  - `run-report.json` (the final attempt's `report.json`);
  - `verdicts-blind.json` (committed alone first).
- `docs/results/w11-report.md` / `.json`, the fts report:
  - how it was run, score and tier 1, the per-question table with USD per question;
  - comparisons, the second-read table, the 30 answers;
  - json: `blind` (exact bytes), `verdicts`, `first_read` / `second_read`, `cost`.
- `docs/NEXT.md` (rewritten) and `README.md` (the "Status" section only). The hybrid line reads "pending (#250 PR 2)".

**PR 2, `tl/250-hybrid` -> `exp/hybrid`, "Closes #250".** The TL closes the issue by hand once PR 3 merges.
`evals/hybrid-eval/corpus-2026-11-19/deepseek/` holds:
- the scripts (copied);
- `mock-real-plans.md` (step 5);
- `count-hyb.md` (counts, cap, the message-hash table, the dropped records);
- the head logs, `raw/`, `run-report.json`;
- `verdicts-blind.json` (committed alone first);
- `report.md` / `report.json`: hybrid verdicts; comparisons with W11 fts, W10 hybrid (#240), #243 and #247; the
  mode-vs-mode table and the floor attribution; the count of map records shared with fts.

**PR 3, a docs-only follow-up to `main`** (plan review nb 5, R1 ruling), after PR 2 merges. It changes only
`docs/NEXT.md` and `README.md` Status: the hybrid line gets PR 2's final score and links.

No file in `src/`, `config/`, `scripts/`, `tests/`, `evals/questions.yaml`, `evals/expected_chunks.yaml`, the baselines
or the database changes, in any of the three PRs.

## Steps
1. **Pre-checks (0 calls), both worktrees.** `git status` clean, no `.env`, the code gates, the version print,
   `sync-db -Check`, the `chunk_embeddings` count, and `git rev-parse HEAD` logged.

2. **Scripts.** Write them, and test each with mock / `-Phase count` only (0 calls). That includes the guard's stop
   paths:
   - a dirty tree;
   - a **dummy** `.env` file (never the real one; plan review nb 4);
   - an existing out folder;
   - a failing code gate.

   Run the `.sh` twins under Git Bash with `-Phase count`. Run `diag/map_msg_hash.py` at 0 calls on the mock count to
   show it logs every spec.

3. **Mock, both modes (0 calls)**, rule plans, Q1-Q35, `--as-of 2026-11-17`; fts at `tl/250-final` and
   hybrid-norerank at `tl/250-hybrid`. How "fts equals the main baseline" (issue) is read here (plan review nb 9): the
   fts mock is **identical** to PR #266's `main-fts` mock on the same code (`ev250sync\main-fts`): chunk lists,
   statuses and answers, 35/35. The diff against `evals/baselines/corpus-2026-11-19/report.json` (`--baseline`) is
   listed, with every change explained (the baseline predates W11).
   - fts expected: 33 PASS / 2 FAIL, refusal gap 8/8, keyed 26/26, 0 forbidden.
   - hybrid-norerank: identical to PR #266's `hyb-norerank`, 31 PASS, refusal gap 7/8, keyed 24/26 (Q22, Q24: a
     must-not chunk retrieved, not cited).
   - Any other difference stops the paid work and is reported.

4. **Phase P: 22 planner calls** (`run-scored -Phase plan -MaxCalls 22`; cache `ev250\cache-fts` from `seed-cache`).
   Check:
   - `real_calls` 22, and 22 new plan files;
   - the 8 saved plans are reused;
   - every `finish_reason` is `tool_calls`;
   - any fallback is named.

5. **Mock on the real plans, both modes (0 calls).** `run-mock -ReusePlans deepseek:deepseek-v4-pro -Cache` on a copy
   of `cache-fts`. #249's tables on the DeepSeek plans go into `mock-real-plans.md`:
   - plans identical across modes, 30/30;
   - per question: chunk lists, shared chunks, refusal and keyed checks;
   - pins per sub-question;
   - **competitor floor**: before -> after, dropped / emptied, competitor passages to the map, and the corrective
     re-search on competitor sub-questions.

   **Stop rules for this step** (plan review nb 3):
   - (a) Plans not identical across modes, or a pin difference other than dedup: a defect. Stop both paid runs and
     report.
   - (b) A crash, or `PlanMissing`: stop and report.
   - (c) The floor fires on any question or sub-question other than Q19 a1.MER: the table goes to the TL before the
     hybrid paid run (step 8). The fts run does not wait.
   - Retrieval differences between modes are the point of the experiment, not a stop.

6. **Count C-fts (0 calls)** under `diag/map_msg_hash.py` (`-Phase count`). The cap is computed as in the paid-call
   plan, with the per-question round-2 bound.

7. **Message check of reused map records (0 calls; R1 ruling).**
   - **fts, the 34 #247 map / remap records.** For each record, the hash of the message 08b0ac4 would send (from step
     6's tsv) is compared with the hash of the message it was made from. The latter comes from `diag/map_msg_hash.py`
     replays at 0 calls on detached worktrees at each record's producing code:
     - 7b9a5b4 for `0247-raw`;
     - 715adda (the code of the 6a3825a run) for `0247b-raw`;
     - 2d5f25b for `0247d-raw`.
     Each replay runs with the same seeded cache and `--max-calls 0`; there it reuses the record under the same key,
     so the message it renders is the one the record was made from.
   - Records whose hashes differ, or which the replay at the producing commit cannot reproduce (the wrapper fails or
     the record is not reused there), go into a drop list. `cache-fts` is rebuilt without them, so those calls are
     made, and step 6 is re-run.
   - The table (record, producing commit, hash then / now, same?) and the cap are committed in `count-fts.md`
     **before step 8**.

8. **fts run** (`-Phase run -MaxCalls <cap>`). Then:
   - `replay` under `diag/map_msg_hash.py` (0 calls, guard: identical answers; its tsv holds the message hash of every
     fts record);
   - the final attempt's `raw/` and `report.json` copied into `docs/results/w11-run/`;
   - recorded per attempt: `real_calls`, reused, per-question calls by type, `how`, stop reasons, invalid / failed
     calls, tokens and USD (new and total).

9. **Hybrid: count C-hyb, message check, run.** In `wt-250h` (36b0b58 code):
   - `seed-cache ev250\cache-hyb <wt> <fts final raw>`;
   - `-Phase count` under `diag/map_msg_hash.py` with `-Mode hybrid-norerank -ReusePlans deepseek:deepseek-v4-pro`.

   **Message check (blocking for the run):** every map / remap record the count would reuse, whether made by the fts
   run or by #247, is listed with:
   - the hash of the message hybrid would send;
   - the hash of the message the record was made from (the fts replay tsv of step 8, or the step-7 producing-commit
     tsv).

   Any record that differs or has no source hash goes into the drop list. `cache-hyb` is rebuilt without them, and the
   count is re-run until every reused record matches. The table, the dropped records and the cap are committed in
   `count-hyb.md` (outside the code gate) **before** `-Phase run`. Then the run, `replay` (0 calls), and the copy into
   the evidence folder. `PlanMissing` or any planner call is a defect: stop and report.

10. **Blind inputs, one set per run (TL note 4).** `ev250\blind-in-fts\` and `ev250\blind-in-hyb\`, each holding:
    - `answers-dump.txt`: the 30 answers with claims and cited passage text, adjacent items, gaps, caveats and parts
      (dump format as #243 / #247);
    - `questions.yaml`;
    - `verdict-rule.txt`.

    The verdict rule is the #217 / #243 bar: PASS only if the project lead would forward the answer with his name on
    it, against `passes_if`; no half credit; borderline named. Classes: r retrieval, s shape / part missing,
    b behavior, c corpus gap, i invalid output.

    Scorer prompts are `ev250\scorer-prompt-{fts,hyb}.txt`, with hashes in `blind-in-*-hashes.txt`. The dumps hold no
    mode name, run name or earlier verdict.

    **The TL starts two fresh scorer agents.** The hybrid scorer never sees the fts answers or verdicts. Each
    `verdicts-blind.json` is committed **alone**, with its sha256 in the Progress log, before any comparison is
    opened.

    Citation check per run: every cited chunk is in its retrieved set (retrieval plus corrective re-search) and in the
    database. Code number-check flags are checked against their passages.

11. **Comparison (0 calls).** For each run, per question, against:
    - #243 like-for-like (15/30, tier 1 10/18);
    - W10 (#217 fts 24/30; #240 hybrid-norerank 25/30);
    - #247's adjudicated final for its eight (Q1, Q3, Q19, Q22, Q24, Q26 PASS; Q11, Q23 FAIL).

    Every changed verdict gets a label, with the deciding chunk ids:
    - **plan:** DeepSeek plan-v3.1 sub-questions vs the earlier plans;
    - **retrieval;**
    - **pipeline:** map-reduce vs the single answer call;
    - **model:** DeepSeek vs Claude, or one sample vs another on the same inputs;
    - **scorer reading:** the earlier answer is compared.

    For the eight #247 questions:
    - a different verdict on a byte-identical answer is scorer variance;
    - their results are also reported apart from the other 22 (they were tuned on).

    **Between modes (PR 2):** the plans are the same, so a difference is retrieval, or model variance where the
    deciding passages reached both maps.
    - **Q19 (TL floor decision, issuecomment-7047676757):** a Q19 difference that comes from Merrill or other
      competitor passages is attributed to the ADR-018 competitor floor (fts cuts, hybrid-norerank keeps), not to
      ranking, citing step 5's floor table. The same applies wherever step 5 shows the floor firing.
    - Byte-identical answers across modes with different verdicts: scorer variance.
    - The report counts the map records hybrid shared with fts per question.

12. **Reports.** Built by scratch scripts.
    - `w11-report.md` / `.json` (fts):
      - how it was run: commits, settings, request version, commands, attempts, caps, calls per phase / attempt, the
        reused-records table and its producing commits;
      - score and tier 1;
      - per-question table: tier, expected -> got behavior, #243, W10 fts, #247 (eight), W11 fts verdict, class,
        borderline, change label, calls new / reused, **USD per question** (new and total, peak / off-peak);
      - the changes tables;
      - known findings carried from `docs/NEXT.md` / #247, each still holds / gone / changed (Q11 definitions corpus
        limit, Q23 corpus gap NEXT item 11, Q22 / Q25 must-not, Q19 competitor leg);
      - the second-read table and the 30 answers.
    - The hybrid `report.md` / `.json`: the same, plus the mode-vs-mode table and the floor attribution.
    - Cost: from `report.json` `cost` and `scripts/eval_cost.py` over each `raw/`. Reused calls are shown at their
      original cost and not as new spend.

13. **Second read (the #217 protocol).** The PR-review reviewer agent reads the answers in round 1 from the dump,
    against `passes_if`, before opening the report, and posts its verdicts. The return is planned, not blocking.
    Round 2 checks the "Second read" table and merges.
    - **PR 1:**
      - every borderline question in the fts blind file;
      - the six W10 fts failures: Q11, Q19, Q20, Q23, Q24, Q26;
      - every verdict change against #243, W10 fts or #247's adjudicated eight (plan review nb 8).
    - **PR 2:**
      - every borderline question in the hybrid blind file;
      - the six W10 fts failures plus #240's hybrid failures (Q11, Q19, Q23, Q24, Q26; already in the six, and Q20
        passed under #240, so the set stays the six; nb 8);
      - every verdict change against #240;
      - **every question whose hybrid verdict differs from the final W11 fts verdict**, with both answers read side by
        side.

      A different fts reading in PR 2 is recorded in the hybrid report as a range; `w11-report.md`, already merged, is
      not rewritten.
    - Each report states the blind score, the second-read verdicts, the final score and the range.

14. **NEXT.md and README (PR 1).**
    - NEXT is rewritten from the W11 fts failures; each item has question IDs, class, size and the check. #243 / W10
      items that W11 closed are dropped or marked done.
    - The hybrid line is "pending (#250 PR 2)".
    - README Status: date, the W11 fts score next to W10 and #243, links.
    - Scratch NEXT check: every FAIL question appears in an item, and no item rests only on passing questions.

15. **/finish-task** for PR 1 and PR 2. Use `.github/pull_request_template.md`, with Verification covering:
    - calls per phase and attempt, model, why;
    - the reused records and the message check;
    - USD;
    - the Progress line;
    - the second-read list.

    verify-cee is not required (no change to `src/`, `config/`, the database or the corpus); this is stated. Both PRs
    need `gh pr checks` green.

16. **PR 3** (after PR 2 merges): docs-only, to `main`. NEXT and README hybrid line with PR 2's final score. `gh pr
    checks` green.

## Acceptance
- [ ] The TL go-ahead (issuecomment-7029133145) predates the first paid call (head-log times).
- [ ] Mock first (step 3): both modes identical to PR #266's runs on 35/35, with the expected PASS / refusal / keyed
      counts; the baseline diff is explained.
- [ ] Step 5 tables written; no stop rule (a) / (b) hit; the floor table sent to the TL if (c).
- [ ] Plans shared: hybrid `--reuse-plans`, 0 planner calls; plan files of both runs identical, 30/30 by name and
      sha256.
- [ ] Message check: every reused map / remap record (the 34 #247 records in fts; every record hybrid reuses) has
      equal message hashes (system prompt and schema too), or was dropped and called. Tables are in `count-fts.md` /
      `count-hyb.md`, committed before each run.
- [ ] Post-run cross-check (C4.5): in each final replay's tsv (fts, hybrid), every inherited record that was reused
      has a source hash, and it matches.
- [ ] Caps written before each paid phase (22; C-fts; C-hyb), with the per-question round-2 bound.
- [ ] Calls per attempt: `meta.real_calls` (or the log) = new cache files of that attempt; the total over attempts is
      at or below the cap. A capped call is named and was not topped up without the TL.
- [ ] 0 re-rolls: no key called twice. The final attempt's replay gives 0 calls and identical answers.
- [ ] Every new record has `provider` deepseek, `model` deepseek-v4-pro and `request_version`
      `ds-strict-1-think-on-a64000-p64000`. `.env` is absent before and after each paid command, never read, never
      committed.
- [ ] HEAD before = after for every paid command, and the code gates held (the hybrid gate excludes
      `evals/hybrid-eval/corpus-2026-11-19/deepseek`).
- [ ] Blind: one blind-in set per run, two fresh scorers started by the TL, each `verdicts-blind.json` committed alone
      with its sha256 before any comparison.
- [ ] Reports:
      - all 30 verdicts per run, score and tier 1;
      - every change against #243, W10 and #247's eight labelled with chunk ids;
      - USD per question and in total (new and reused);
      - the Q19 floor attribution;
      - the map records shared with fts.
- [ ] Second read in each PR's round-1 review; the reports' "Second read" tables match it.
- [ ] `docs/NEXT.md` rewritten (the check passes) and README Status updated (PR 1); hybrid line updated by PR 3.
- [ ] 0 code changes: `git diff 08b0ac4 --stat` (PR 1, PR 3) and `git diff 36b0b58 --stat` (PR 2) list only the
      files above.
- [ ] `gh pr checks` green on all three PRs.

## Risks
- **One sample per question.** A verdict change can be model variance. It is labelled "model" where the deciding
  passages were available both times, and it is not re-rolled.
- **Map-key blind spot** (plan review nb 2). The map key hashes chunk ids, not their grouping or the
  `NO_PASSAGES` / `KEPT_ELSEWHERE` markers. Mitigation: step 7 / step 9 message hashes; a mismatched record is
  dropped and called. Residual risk: none for reused records once every hash matches.
- **Shared records between modes.** An identical map message reuses one output, so both modes get the same sample
  there. That is intended (same input); the report counts them.
- **The #247 eight** mostly reuse #247's records, which were tuned on. They are reported apart.
- **Floor on the real plans.** There may be competitor sub-questions beyond Q19. Step 5 measures it, and the TL sees
  it before the hybrid run.
- **Producing-commit replays** may not run on old code (the diag wrapper). Mitigation: such records are dropped and
  called, which costs a few calls (each is about $0.01-0.05). The counts and cap are re-run first.
- **Peak pricing and long calls.** Thinking on, up to 64k output, a 3600 s read timeout. A timeout is a failed call:
  saved, never re-called, a finding.
- **Scorer bias.** Fresh blind scorers, hash-first commits, a second read in review, and the range reported.

## Progress log
- 2026-11-20 - Step 0 done before this plan: PR #266 merged main 08b0ac4 into `exp/hybrid` (merge commit; HEAD
  36b0b58). fts parity 35/35, floor table unchanged (Q19 a1.MER only), pytest 1148 (vectors on) and 1146 + 2 skipped
  (off). 0 calls.
- 2026-11-20 - plan written on `tl/250-final` from main 08b0ac4 (64e8595). The 0-call coverage check
  (`ev250\count0-fts`) reuses 45 records (8 plans, 34 maps, 3 reduces) and needs 22 planner calls. The 5 reduces of
  Q1, Q3, Q11, Q22, Q24 have new keys. 0 calls.
- 2026-11-20 - plan review round 1 (issuecomment-7048943430): RETURN. TL rulings in issuecomment-7048978281.
  - Blocking 1: round 2 bounded per question by distinct firm rows; capped calls named; no top-up without the TL.
  - Blocking 2: hybrid code gate excludes the deepseek evidence folder; `-GateSha` / `-GateExclude` parameters.
  - Blocking 3: attempt folders `-a2` with the same cache and the remaining cap; final attempt's `raw/` committed and
    replayed; per-attempt logs.
  - nb 2, now blocking per TL: map message-hash check (`diag/map_msg_hash.py`, steps 7 and 9) for the 34 #247 maps
    and every record hybrid reuses; mismatches dropped and called.
  - nb 1: record provenance and diff bases corrected.
  - nb 3: step-5 stop rules.
  - nb 4: head-log outside the worktree; dummy `.env` for the guard test.
  - nb 5: PR 3, a docs-only follow-up to `main`.
  - nb 6: gate SHA and fastembed path as parameters.
  - nb 7: TL notes cited by comment id.
  - nb 8: second-read sets extended.
  - nb 9: the mock-baseline reading stated.
  - 0 calls.
- 2026-11-20 - plan review round 2 (issuecomment-7049132420) and TL approval at d5f337d on conditions
  (issuecomment-7049142807). The conditions are written in above as C1-C4: the wrapper runs on the worktree's own
  code; producing commit per record from `at`; an allow-list cache; round-2 nb 1-6. Execution starts after this
  commit. 0 calls.
