# 0212 - exp/hybrid: 30-question real run of hybrid-norerank on corpus-2026-11-17

Issue: #212    Role: TL    Spec: specs/retrieval.md, evals/questions.yaml
Base branch: `exp/hybrid` (ADR-011: model-based work stays off `main`). Branch `tl/212-hybrid-real`
from `origin/exp/hybrid` 264d778 (#211 / PR #219), worktree `D:\ALLPROJECTS\EDJ\wt-212`; the PR
targets `exp/hybrid`, never `main`.

## Goal
One real, scored run of all 30 bank questions with `hybrid-norerank` retrieval on `corpus-2026-11-17`
(as of 2026-11-17, `claude-sonnet-5-5`, prompt v3, one run per question), so the team sees whether
hybrid's answers are better or worse than Gate 4's (fts, same snapshot, model and prompt, 21/30),
question by question, and whether each changed verdict comes from different retrieved passages.

## Why this runs (and why the mock cannot answer it)
- #211's mock decision rule closed #212 (A: tier-1 passage recall 0.484 < 0.627; C: Q22 retrieves
  its must-not passage). The tech lead reopened it (issue comment, 2026-11-19): "#212 has to be
  done; hybrid looked worse only because it was never tested with real calls". The mock rule no
  longer gates this run; the TL go-ahead for the 30-question scored run (issue comment, 2026-11-18)
  still holds (CLAUDE.md "Paid API calls" step 2, Gate 3 clause).
- The mock provider "always answers when retrieval finds something" (CLAUDE.md "Verification"). It
  cannot show (a) answer quality against `passes_if` (wording, dating, the shape a question asks for),
  (b) the behavior choice (`answer` / `gap_with_adjacent` / `answer_with_boundary`; Q11, Q23 changed
  behavior only with the real model), (c) whether claims match the passages they cite, or (d) whether
  the model uses a misleading passage it is handed (Q22's `MS-PR-2026-04-15-01#15`). Passage recall
  measures what is retrieved, not whether the answer passes: Gate 4 passed Q17, Q19, Q22 with
  passages missing, and failed Q3, Q7, Q28 with the key passages present.

## Inputs read
Issue #212 (body and all comments: TL go-ahead 2026-11-18, #211 closing note, TL reopening
2026-11-19), `CLAUDE.md` ("Paid API calls", "Verification", working rules), `.claude/commands/start-task.md`,
`PLANS.md`, `specs/retrieval.md` (incl. "Retrieval modes"), `docs/results/gate4-report.md` ("How this was
run", scores, scoring method, borderline list) and `docs/results/gate4-report.json`, `docs/RUN.md`
section 7 and "Hybrid retrieval", on `origin/exp/hybrid`: `plans/0211-hybrid-retest.md`,
`evals/hybrid-eval/corpus-2026-11-17/report.md` (+ `inputs/*-report.json`), `scripts/eval_run.py`
(`RealRunner`, `cache_key`, `apply_real`, `--real`/`--max-calls`/`--mode`), `src/cee/retrieve/modes.py`,
`src/cee/retrieve/hybrid.py`, `src/cee/config.py` (`LLM_MODEL` default, `CEE_VECTORS`), `evals/questions.yaml`,
`evals/expected_chunks.yaml` (Q22 `must_not_return`).

State checked (read-only, 2026-11-18 23:45): `sync-db -Check` exit 0, "Database is up to date:
corpus-2026-11-17"; `chunks` = `chunk_embeddings` = 21,143, 219 documents.

Facts this plan rests on (checked on the committed files, no run):
- Gate 4's retrieved chunk ids (`docs/results/gate4-report.json`, run `corpus-2026-11-17-20261118-013723`,
  commit 40fe462) equal the #211 `fts` mock run on `exp/hybrid` 7f12f60 on 30/30 questions. So the
  Gate 4 answers are the fts answers of this branch's code on this snapshot.
- #211's `hybrid-norerank` mock run (`inputs/hybrid-norerank-report.json`, 7f12f60) has hits on all 30
  questions (so 30 calls, none skipped by "no hits -> no call") and its chunk-id list equals Gate 4's
  on none of the 30 (overlap 5-17 passages of 15-30). The cache key is question + text + prompt
  version + snapshot + provider + model + the ordered chunk-id list, so no Gate 4 output can be
  reused: every question is a new call.
- Gate 4's run folder: `D:\ALLPROJECTS\EDJ\cache\ev121\r3-real-30\` (report.json, report.md, raw/ 30
  files), scoring pack `ev121\r3-scoring\Q<n>.md`, verdicts `ev121\verdicts_r3.json`
  (`{Q: [verdict, class, reason]}`), pack builder `ev121\pack.py`, report generator `ev121\gen_report.py`.
- `eval_run.py --real` makes one model call per question with hits (`answer_for`), counts the call
  before making it, caps at `--max-calls`, saves every output (valid or invalid) in
  `.eval-runs/cache/` and the run's `raw/` folder, and never re-calls a cached invalid output.

## Files to change
- `plans/0212-hybrid-real.md` - this plan.
- `evals/hybrid-eval/corpus-2026-11-17/real/report.md` (new) - the scored report (layout in step 7).
- `evals/hybrid-eval/corpus-2026-11-17/real/summary.json` (new) - per question: hybrid verdict, class,
  borderline flag, Gate 4 verdict, change, retrieval overlap counts, deciding passages and their
  explanation; totals; run meta (calls, model, prompt version, commit, run id).
- `evals/hybrid-eval/corpus-2026-11-17/real/run-report.json` (new) - the run's `report.json` as
  written by `eval_run.py` (answers, chunk ids, statuses; no raw documents), like
  `docs/results/gate4-report.json`.
- `evals/hybrid-eval/corpus-2026-11-17/real/raw/` (new) - the 30 raw model outputs from the run's
  `raw/` folder (about 225 KB at Gate 4's size; model output only, no document text beyond what the
  model quoted), so the call count in the PR can be checked on the branch.
- `docs/RUN.md` - "Hybrid retrieval" section only: the #212 real-run command (paid, TL go-ahead
  needed) in a PowerShell and a bash block, and a link to the report.
- `specs/retrieval.md` - "Retrieval modes" section, the "Comparisons" bullet only: one line linking
  the #212 real run and its score (owner S1, owner review waived, TL decision 2026-11-17 (#187)).
Nothing in `src/`, `config/`, `scripts/`, `tests/`, the database or the corpus changes; no prompt
change, no retrieval change, no re-run of a question (issue "Out of scope"). Local only (not
committed): `D:\ALLPROJECTS\EDJ\cache\ev212\` (mock run, real-run copy, logs, scoring pack, verdicts,
comparison helper).

## Steps

### 1. Pre-checks (free, 0 calls)
- Worktree `D:\ALLPROJECTS\EDJ\wt-212` on `tl/212-hybrid-real` at 264d778 + this plan. Python is the
  main checkout's venv with `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-212\src` and `PYTHONUTF8=1` (the
  worktree has no `.venv`); `eval_run.py` also puts its own `src/` first on `sys.path`. Below,
  `$PY = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe'`, called as `& $PY`; commands run from
  the worktree root `D:\ALLPROJECTS\EDJ\wt-212`.
- `sync-db -Check` exit 0 and `chunks` = `chunk_embeddings` = 21,143 (re-run on the day of the run).
- pytest on the branch (with and without `CEE_VECTORS=on`); expected as on #211: 625 passed, 2 skipped
  without the vectors env; the 2 DB hard-filter tests pass with it. A failure stops the plan.
- The process environment for every run (this terminal only; `.env` is never opened, edited or printed):
  ```powershell
  $env:PYTHONPATH = 'D:\ALLPROJECTS\EDJ\wt-212\src'; $env:PYTHONUTF8 = '1'
  $env:CEE_VECTORS = 'on'; $env:FASTEMBED_CACHE_PATH = 'D:\ALLPROJECTS\EDJ\cache\fastembed'
  $env:RETRIEVAL_MODE = 'hybrid-norerank'; $env:LLM_MODEL = 'claude-sonnet-5-5'
  ```
  `LLM_MODEL` is set explicitly so the model does not depend on `.env` (process variables win over
  `.env`: `load_dotenv` does not override them). `--mode hybrid-norerank` is also passed on every
  command.
- API key for the real run: `config.py` loads `<worktree>/.env`, and `wt-212` has none. The main
  checkout's `.env` is copied as a file (`Copy-Item D:\ALLPROJECTS\EDJ\repo\.env D:\ALLPROJECTS\EDJ\wt-212\.env`),
  never opened, printed or listed with content, as the earlier worktrees did (`wt-144` holds one).
  `git check-ignore -v .env` in `wt-212` is run **before** the copy (must name `.gitignore:2`), and
  `git status` after it shows nothing new. The copy is made right before the paid command and
  deleted right after it (step 3 "After the run"), also if the run stops part-way; the Progress log
  records `Test-Path D:\ALLPROJECTS\EDJ\wt-212\.env` -> False. Its `LLM_PROVIDER` line does not
  matter: the process variable is set per command.
- Right before the paid command, the resolved `cee.__file__` is logged (expected under
  `wt-212\src`), proving the run used the branch code and `wt-212\.env`.

### 2. Mock run of the same 30 questions (0 calls) - every check must pass
```powershell
$env:LLM_PROVIDER = 'mock'
& $PY scripts\eval_run.py --mode hybrid-norerank --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-17\report.json --out D:\ALLPROJECTS\EDJ\cache\ev212\mock-hybrid-norerank *> D:\ALLPROJECTS\EDJ\cache\ev212\mock.log
```
Mock checks (all must hold, else stop and report; nothing paid starts):
- M1: the run finishes; 30 records, 0 `INVALID_OUTPUT`, 0 errors in the log.
- M2: retrieval is the one #211 measured: chunk ids equal `inputs/hybrid-norerank-report.json` on 30/30
  questions (same ids, same order). This also fixes the set the real run will hand the model.
- M3: as #211: PASS 28 / FAIL 2 (Q19, Q22 retrieval checks, both known: Q19 is a pattern-coverage
  check Gate 4's real answer passed; Q22 is the must-not passage, a finding this run is meant to
  test with the real model), forbidden hits 0, refusal 5/5 on Q24, Q25, Q28-Q30.
- M4: every question has hits (30 of 30), so the real run plans exactly 30 calls.
- M5: mock answers built for all 30 (the answer flow, citation check and caveats run end to end).
Then a free dry run of the paid path: `$env:LLM_PROVIDER = 'anthropic'; & $PY scripts\eval_run.py --real
--max-calls 0 --mode hybrid-norerank --as-of 2026-11-17 --out D:\ALLPROJECTS\EDJ\cache\ev212\dry-0`
-> `real calls 0`, `reused 0` (the worktree cache is empty, so nothing old is reused), 30
`NOT_EVALUATED` ("--max-calls reached"). This proves the provider switch and the cap with 0 calls.

### 3. The real run (paid; one run, all 30 questions together)
| What | Value |
|---|---|
| Questions | Q1-Q30, one run each, together in one command |
| Retrieval | `hybrid-norerank`, `CEE_VECTORS=on`, constants as on 264d778 (FLOOR 0.4, MAX_PER_DOC 3, RERANK_N 50 x k/20) |
| Model / prompt / snapshot / as of | `claude-sonnet-5-5` / v3 / `corpus-2026-11-17` / 2026-11-17 |
| Calls | 30 planned (one per question; every question has hits, M4); cap `--max-calls 30`; a question with no hits would make none |
| Why each is needed | the verdict against `passes_if` is the deliverable; the mock cannot give it (section above) |
| Approval | TL go-ahead comment on #212 (2026-11-18), TL reopening (2026-11-19) |
| Size | about 193k input tokens in all (the #211 mock run's `tokens_est` for hybrid-norerank), plus the answers |
```powershell
$env:LLM_PROVIDER = 'anthropic'
& $PY scripts\eval_run.py --real --max-calls 30 --mode hybrid-norerank --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-17\report.json --out .eval-runs\0212-hybrid-real *> D:\ALLPROJECTS\EDJ\cache\ev212\real.log
```
(`--baseline` only labels retrieval UNCHANGED/IMPROVED/REGRESSED against the fts baseline; it calls
nothing.) The script prints the "more than 10 calls" note; the TL go-ahead covers it.
After the run:
- `real calls` in the log = number of `called` + `invalid` records = number of new files in `raw/`;
  expected 30, `reused 0`.
- The run folder (report.json, report.md, raw/) is copied to `D:\ALLPROJECTS\EDJ\cache\ev212\real-30\`,
  and `.eval-runs\cache\` files of this run to `ev212\real-30-cache\`.
- The retrieved chunk ids of the real run equal the mock run's (M2) on 30/30; a difference is reported.
- Each raw file names question, prompt version v3, snapshot, provider, model `claude-sonnet-5-5`,
  chunk ids and time; the model name is checked in all 30.
- Delete `wt-212\.env` (also if the run stopped part-way) and log `Test-Path` -> False.
- If an API error (not a `ModelOutputError`) stopped the run, a call was counted with no raw file:
  the report and PR state real calls and raw files as two separate numbers.

**A wrong, truncated or invalid output is a finding, not a re-roll.** `INVALID_OUTPUT` (not a valid
Answer: wrong field, no tool call, truncated JSON), `NOT_EVALUATED` (cap reached), a call error or an
answer that fails is scored FAIL (an invalid output cannot pass `passes_if`), its raw payload is kept
and quoted in the report, and nothing is called again: no second run of any question, no retry, no
re-run of the command (issue "Out of scope"; CLAUDE.md step 4). If the run stops part-way (network,
crash), the outputs already saved stay; the report states the calls made and the questions with no
answer as "not answered (run stopped)", FAIL; any completion run would need a new TL decision and is
not part of this plan.

### 4. Scoring pack (free)
Copy `ev121\pack.py` to `ev212\pack.py` (unchanged) and build `ev212\scoring\Q<n>.md` +
`summary.csv` from `ev212\real-30`: per question the text, `passes_if`, expected vs got behavior, each
claim / adjacent item with its cited passages (text from the DB), code flags (unmatched citation,
number check), gaps, caveats, withheld claims, and whether every citation was retrieved and exists.

### 5. Scoring: one verdict per question, Gate 4's method and standard
- Each answer is read against its `passes_if` line in `evals/questions.yaml`: "would the project lead
  forward it with his name on it?" (acting quality). One verdict per question, PASS or FAIL, no half
  credit. Expected behavior must match unless `passes_if` itself allows the other one (as Gate 4).
  Failure classes as Gate 4: r (retrieval missed a passage the corpus holds), s (shape / required
  part missing), b (behavior choice), c (corpus gap); for an invalid output: `i` (model output not a
  valid Answer).
- Every flagged number (code's number check) is checked against its passage, as Gate 4 did; every
  citation must be in the retrieved set and exist in the DB (ground rules 1, 2).
- Q22 specifically: the answer fails if it uses `MS-PR-2026-04-15-01#15` (fee-based asset flows) or
  `SCHW-10Q-2026Q2#56` as net new assets (`passes_if`: "never quietly substituted with a
  near-neighbour metric"); citing it labelled as a different metric is allowed.
- Blind first: all 30 verdicts and one-line reasons are written to `ev212\verdicts_hybrid.json`
  (`{Q: [verdict, class, reason]}`, Gate 4's format) and timestamped before Gate 4's answers or
  verdict reasons for that question are opened again. In step 6 a verdict may change only to make the
  standard equal to Gate 4's on the same kind of failure (e.g. the same missing part); each such change
  is logged in the report with both verdicts and the reason.
- Borderline questions are named (pass side and fail side), as Gate 4 did.

### 6. Per-question comparison with Gate 4 (free)
A helper in `ev212\compare.py` (local, not committed; it is described in the report) reads Gate 4's
`docs/results/gate4-report.json` (= `ev121\r3-real-30\report.json`), the real run's report.json and
the two verdict files, and writes per question:
- the two verdicts and the change: PASS->FAIL, FAIL->PASS, or same;
- retrieval: passages in both sets / only in Gate 4 (fts) / only in hybrid, and the tier-1 key
  passages (`expected_chunks.yaml`) found by each;
- citations: chunks each answer cited, and which of them were not in the other run's retrieved set.
For **every changed verdict** the report says which passages explain it, by reading the two answers:
- "retrieval": the claim or gap that decides the verdict rests on a passage only one run retrieved
  (named by chunk id), or a passage the passing answer needed is absent from the failing run's set;
- "model": the deciding passages were in both sets; the difference is the model's wording, shape or
  behavior choice on largely shared evidence (one run each, the model is not deterministic, so this
  is not separable from run-to-run variation; said so);
- "both", when both apply.
Unchanged verdicts also get the retrieval line (every question's set differs from Gate 4's), and a
note where the answer content changed although the verdict did not (e.g. a different failing part).

### 7. Report and summary (committed)
`evals/hybrid-eval/corpus-2026-11-17/real/report.md`:
- Score line: hybrid-norerank N/30 (tier 1: n/18) vs Gate 4 21/30 (12/18), scored by the TL agent;
  the sentence that one run per question cannot separate retrieval from model variation, and that
  Gate 4's own 30 answers came from two runs (11 calls in its final run, 19 reused from R2).
- "How this was run": snapshot, as of, commit, mode and constants, model, prompt v3, calls made /
  reused / planned, run id, evidence folders (`.eval-runs\0212-hybrid-real`, `D:\ALLPROJECTS\EDJ\cache\ev212\real-30`,
  `real/raw/` on the branch), scoring method (step 5), citation and number-check totals.
- Score table: Q, tier, expected -> got behavior, Gate 4 verdict, hybrid verdict, change, class,
  retrieval overlap, explanation (retrieval / model / both, with chunk ids).
- PASS->FAIL and FAIL->PASS lists, each with the passages that explain it; borderline questions;
  findings (incl. Q22's must-not passage: handed to the model, used or not, how labelled; Gate 4's
  8 missed passages and whether hybrid's answers needed them; every invalid or truncated output).
- No recommendation on `main` (that is the TL's call; ADR-010/011 stay as they are).
`real/summary.json`: the machine-readable version (Files to change).

### 8. Docs, checks, finish
- `docs/RUN.md` "Hybrid retrieval": the real-run command of step 3 in a PowerShell and a bash block
  (`CEE_VECTORS=on FASTEMBED_CACHE_PATH=... RETRIEVAL_MODE=hybrid-norerank LLM_PROVIDER=anthropic
  .venv/bin/python scripts/eval_run.py --real --max-calls 30 --mode hybrid-norerank --as-of 2026-11-17 ...`),
  marked paid, TL go-ahead needed, and the report link. `specs/retrieval.md`: one line in the
  "Comparisons" bullet.
- pytest on the branch again (no code changed, same counts). verify-cee is not required: no change
  to `src/`, `config/`, the database or the corpus (CLAUDE.md "Verification"); said so in the PR.
- `/finish-task`: PR into `exp/hybrid` with "Closes #212"; the Verification section states the real
  calls (number, model `claude-sonnet-5-5`, why: the 30 verdicts), "0 calls made by the reviewer",
  and the evidence folders. Comment the result on #212.

## Risks
- **One scorer.** The verdicts are one agent's reading, the same agent family that scored Gate 4 and
  that knows Gate 4's verdicts. Mitigation: blind first (step 5), Gate 4's standard and failure
  classes, borderline questions named, every changed verdict explained with chunk ids so the reviewer
  can check it from the committed answers. Gate 4 itself says "another scorer could move the total by
  one or two either way"; a difference of 1-2 between 21 and the hybrid score is within that.
- **One run per question.** The model is not deterministic and Gate 4's 30 answers came from two runs
  (19 R2 + 11 R3). A changed verdict with the same deciding passages may be noise; the report labels
  it "model", never "retrieval".
- **Q22's must-not passage.** Hybrid hands the model `MS-PR-2026-04-15-01#15` (fee-based asset flows
  footnote); if the answer reports it as Morgan Stanley NNA, Q22 fails (Gate 4 passed it). Scored by
  `passes_if`, reported whichever way it goes.
- **Lower passage recall.** Hybrid's tier-1 passage recall is 0.484 vs 0.597 (#211); answers on Q1,
  Q5, Q20 etc. had fewer key passages in the mock run. The run measures whether that costs verdicts;
  nothing is tuned after the numbers come in.
- **Cost.** 30 calls, about 193k input tokens plus output, capped by `--max-calls 30`; no retries,
  no re-runs. The cache key includes the chunk-id list, so no Gate 4 output is reused (checked:
  0 of 30 sets equal). If the real run's retrieval differs from the mock run (M2 holds but the DB
  changed in between), the report says so; the calls are not repeated.
- **API key in a worktree.** The `.env` copy (step 1) is gitignored, never opened or printed, and
  deleted after the run. If the reviewer rejects the copy, the alternative is running from a checkout
  that has `.env` on this branch, which would mean switching the main checkout another agent reads;
  not done without approval.
- **Shared local database.** Another branch could restore a snapshot (`/sync-db`) and drop
  `chunk_embeddings` before the run; step 1 re-checks counts on the day, and M2 is checked right
  before the paid command.

## Acceptance
- [ ] TL go-ahead comment on #212 before the first call (present: 2026-11-18; reopening 2026-11-19).
- [ ] pytest passes on the branch (counts recorded); mock checks M1-M5 pass and the free dry run
      shows 0 calls, before the paid command.
- [ ] Linked questions Q1-Q30: one real run each with `hybrid-norerank`, `claude-sonnet-5-5`, prompt v3,
      as of 2026-11-17; real calls = 30 (or fewer, each missing one explained), reused 0.
- [ ] 30 saved raw outputs in the run's evidence folder, copied to `D:\ALLPROJECTS\EDJ\cache\ev212\real-30\`
      and committed in `real/raw/`; the call count in the PR equals the raw files made by the run.
- [ ] `real/report.md` gives a verdict for all 30 questions against `passes_if` (Gate 4 method, no half
      credit), names borderline questions, lists every PASS->FAIL and FAIL->PASS against Gate 4, and
      for each change says whether it comes from different retrieved passages (chunk ids).
- [ ] `real/summary.json` and `real/run-report.json` committed; `docs/RUN.md` real-run command in
      PowerShell and bash blocks.
- [ ] Invalid / truncated outputs (if any) reported as findings; no question run twice.
- [ ] `git diff origin/exp/hybrid --stat` lists only the files in "Files to change".
- [ ] 0 calls made by the reviewer (all evidence is in committed files and `ev212`).

## Progress log
- 2026-11-18 23:46 - plan written on `tl/212-hybrid-real` (from `origin/exp/hybrid` 264d778, worktree
  `wt-212`). DB checked: corpus-2026-11-17 up to date, 21,143 chunks and embeddings. Checked on
  committed files: Gate 4 chunk ids = #211 fts mock run 30/30; hybrid-norerank sets differ from
  Gate 4 on 30/30 and all have hits (30 calls planned). Waiting for the reviewer agent's approval
  before step 1. 0 real calls so far.
- 2026-11-18 23:50 - plan approved by the reviewer agent (issue comment 7001006461, on 095dd24); its
  non-blocking notes applied: S1 owner tag on `specs/retrieval.md`, `.env` guards (check-ignore
  before the copy, delete also on a part-way stop, Test-Path logged; step number fixed), real calls vs
  raw files stated separately on an API error, `cee.__file__` logged before the paid command, Gate 4's
  two-run origin in the score line.
- 2026-11-18 23:54 - step 1: pytest 625 passed, 2 skipped (no vectors env); `tests/test_hybrid.py` with
  `CEE_VECTORS=on` 53 passed (incl. the 2 DB hard-filter tests). Step 2: mock run
  `D:\ALLPROJECTS\EDJ\cache\ev212\mock-hybrid-norerank` (095dd24, 0 calls): PASS 28 / FAIL 2 (Q19, Q22),
  tier-1 passages 0.484, forbidden 0, refusal 5/5, tokens~193,085. `ev212\mock_checks.py`: M1-M5 all
  PASS (30 records; chunk ids = #211's run on 30/30; fails exactly Q19, Q22; hits on 30/30; mock answer
  flow built for 30/30 with the same retrieval), `cee` from `wt-212\src`. Dry run `ev212\dry-0`
  (`--real --max-calls 0`): 30 NOT_EVALUATED, real calls 0, reused 0; no `.eval-runs\cache` in `wt-212`.
