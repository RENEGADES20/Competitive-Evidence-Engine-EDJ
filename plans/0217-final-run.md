# 0217 - Scored 30-question run of the W10 pipeline on corpus-2026-11-19

Issue: #217    Role: TL    Spec: evals/questions.yaml (scoring: docs/results/gate4-report.md "How this was run")

## Goal
One real run of all 30 questions through the full W10 pipeline on `corpus-2026-11-19`, scored at
acting quality against `passes_if`, written up as `docs/results/w10-report.md` (+ json) with every
change against Gate 4 (21/30) explained, and `docs/NEXT.md` rewritten from the failures that remain.
No code changes.

## Pipeline under test (main cdcb6ee, no change on the branch)
- Retrieval: token budget 40k (five firms 60k), pool 30 per (firm, doc type) (ADR-019).
- Planner: one call, `plan-v2`, `neighbour_phrases` guard, part cap 4, `max_tokens` 2000 (ADR-020, #224).
- Answer: prompt `v4.1` (parts, `part_id`, code `part_gap`, newest first across parts; #215, #230),
  `llm.MAX_TOKENS = 20000`, `max_retries=0`, strict tools, request version `strict-1` (#232).
- Model `claude-sonnet-5-5`. At most 2 calls per question (ADR-012 allows 5).
- Snapshot `corpus-2026-11-19` (224 docs, 21,161 chunks; = `corpus-2026-11-17` + 18 headcount
  chunks, #216). Local `cee` is on it (`scripts\sync-db.ps1 -Check`: "Database is up to date:
  corpus-2026-11-19", 2026-11-19 06:2x).

## Decisions fixed before the run
- **As-of date 2026-11-17**, not 2026-11-19. Reasons: (1) Gate 4 ran `--as-of 2026-11-17`, so Q26
  (90 days: 2026-08-19..2026-11-17) and Q27 (since 2026-01-01) see the same window and a change on
  them is not a window artefact; (2) both committed mock baselines (`corpus-2026-11-17`,
  `corpus-2026-11-19`) and every W10 partial real run used 2026-11-17; (3) the 18 new chunks are a
  2020 / 2023 supplement and 2026 Form ADV Part 1A pages, so 2026-11-19 adds no document to any
  window and would only drop 2026-08-19/20 from Q26's. Step 1 checks (3) on the database (0 calls).
- **No exp/hybrid run.** The issue repeats the run on `exp/hybrid` only "if #212 showed hybrid
  ahead". #212 (PR #221) scored hybrid-norerank 21/30 (tier 1 12/18), level with Gate 4 fts, not
  ahead. Hybrid stays on `exp/hybrid` (ADR-010/011). 0 calls there.
- **Verdict rule** (as Gate 4): one verdict per question, PASS only if the project lead would
  forward the answer with his name on it, read against its `passes_if` line; no half credit;
  borderline verdicts named. Failure classes as Gate 4 (r retrieval missed a passage the corpus
  holds, s shape / a required part missing, b behavior choice differs, c corpus gap), plus
  **i = invalid output** (cut, empty, no tool call, API refusal, failed call): scored FAIL, a
  finding, never re-run.
- **Change labels** (each verdict change against Gate 4 and against the W10 partial real runs):
  **retrieval** (the retrieved set gained or lost a passage that decides the verdict; chunk ids
  named; "new in corpus-2026-11-19" when it is one of #216's 18 chunks), **pipeline** (a W10 answer-
  path change: planner parts, prompt v4/v4.1, code `part_gap`, strict tools, 20000 cap), **model**
  (same deciding passages available, the model chose or wrote differently). Several labels allowed.

## Files to change
- `plans/0217-final-run.md` - this plan and its Progress log.
- `docs/results/w10-report.md` - new: how it was run, score, tier-1 score, per-question table,
  comparison with Gate 4 and the W10 partial runs, cost, known findings, borderline second read,
  the 30 answers with citations (same layout as `gate4-report.md`).
- `docs/results/w10-report.json` - new: the scored records (the last attempt's `report.json`, plus
  a log-entry record for any question stopped under resume rule (b)), the `blind` field (step 4)
  and a `verdicts` block (verdict,
  class, borderline, change label, chunk ids per question).
- `docs/NEXT.md` - rewritten from the new failures.
- `README.md` - "Status" section only: date, the W10 score line and links.
No file in `src/`, `config/`, `scripts/`, `tests/`, `evals/` (question bank, keys, baselines) or
the database changes. Scratch (not committed): `D:\ALLPROJECTS\EDJ\cache\ev217\`.

## Steps
1. **Pre-checks, 0 calls.** `git status` clean on `tl/217-final-run`; `sync-db.ps1 -Check` exit 0;
   `.venv\Scripts\python.exe -c "from cee.answer.prompt import PROMPT_VERSION; from cee.retrieve.planner import PLANNER_VERSION; from cee.answer import llm; print(PROMPT_VERSION, PLANNER_VERSION, llm.MAX_TOKENS, llm.ANTHROPIC_REQUEST_VERSION)"`
   -> `v4.1 plan-v2 20000 strict-1`. As-of check (decision (3)), SELECT only, saved to
   `ev217\asof-check.txt`: documents with `published_at` after 2026-11-17 (expected 0); RJF
   documents in 2026-08-19..2026-08-20 (listed; expected `RJF-TRADE-2026-08-19-IN-01`, which a
   2026-11-19 as-of would drop from Q26's window); the five #216 documents with `published_at` and
   `date_basis` (expected `MS-SUPP-2020Q4` 2021-01-20, `BAC-SUPP-2023Q4` 2024-01-12,
   `SCHW-ADV1A-2026` 2026-10-21, `MS-ADV1A-2026` 2026-11-04, `MER-ADV1A-2026` 2026-11-11, all
   `source`). The three ADV1A documents sit inside 2026 windows: `MER-ADV1A-2026` is inside Q27's
   window (since 2026-01-01, MER), so any Q27 change that touches `MER-ADV1A-2026#*` is labelled
   "retrieval, new in corpus-2026-11-19". Q26 (RJF only) gets no new document. Cache check: count
   `.eval-runs\cache` entries whose `snapshot` is `corpus-2026-11-19` (expected 0 -> no reuse).
   Log `git rev-parse HEAD` (expected the plan's head on `tl/217-final-run`).
2. **Mock run of all 30, 0 calls.**
   `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out .eval-runs\0217-mock`
   (`LLM_PROVIDER` mock). Expected: 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22,
   0 forbidden, no PASS -> FAIL, and 30/30 chunk lists identical to the baseline (nothing under
   `src/` or `scripts/` changed since the baseline commit f919a36; the files that did change,
   `config/metric_definitions.yaml`, `snapshots/LATEST.json`, the baseline files and docs, are not
   read by `src/` or `scripts/`). Diff saved to `ev217\mock-diff.txt`.
   Any difference stops the run (no paid call) and is reported.
3. **Real run of all 30, one run, last** (paid-call plan below):
   `$env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; .venv\Scripts\python.exe scripts\eval_run.py --real --max-calls 60 --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out .eval-runs\0217-real *> D:\ALLPROJECTS\EDJ\cache\ev217\real-run.log`
   then remove both env vars. Run from this checkout with no other agent working (none is now; a
   cleanup switching the checkout disturbed the #232 run, PR #234); log `git rev-parse HEAD` and
   `git branch --show-current` immediately before and after the paid command (both must equal the
   step 1 head). No commit is made between step 1 and the end of step 3 (the Progress-log lines for
   steps 1-3 are committed after step 3; the next commit is the one before step 5). Copy
   `.eval-runs\0217-real\raw\*`, `report.json`, `report.md` to
   `D:\ALLPROJECTS\EDJ\cache\ev217\real\` (attempt N >= 2: its new raw files and report to
   `ev217\real-N\`). Record `real_calls`, reused, per-question `how`
   (called / cached / invalid / cap), planner source (planner / rule fallback), `stop_reason`, input
   and output tokens from `usage`.
4. **Blind scoring.** Dump the 30 answers (claims with cited passage text, adjacent, gaps, caveats,
   parts) from the scored records (Paid-call plan, "Source of the scored records": the last
   attempt's `report.json`, plus a log-entry stub for any question stopped under rule (b)) to
   `ev217\answers-dump.txt` (adapted from `ev121\gen_report.py` / `ev230\dump.py`). Read
   each against its `passes_if` and expected behavior **before** opening Gate 4's or the W10 runs'
   verdicts; write `ev217\verdicts-blind.json` (verdict, class, borderline, one-line reason), add a
   Progress-log line with its time and sha256, and **commit and push that line before step 5** (the
   commit time shows the order). The blind verdicts are also kept unchanged in
   `docs/results/w10-report.json` (field `blind`, the file's exact bytes as a string) so the hash
   can be recomputed. Every cited chunk id is checked to be in the retrieved
   set and in the database (citation check, as Gate 4); every code number-check flag is checked
   against its passage.
5. **Comparison.** Per question: Gate 4 verdict (gate4-report.md table) and the W10 partial real
   runs (#213 PR #220, #214 PR #223, #224 PR #226, #215 PR #229, #230 PR #231, #232 PR #234; tables in
   `cache\ev213..ev232`); for every changed verdict a label (retrieval / pipeline / model) with the
   deciding chunk ids from both runs' retrieved and cited sets (`gate4-report.json` vs the new
   `report.json`). Blind verdicts are not edited in this step; if a comparison shows a reading error
   (e.g. a missed cited passage), the change is logged with the reason, the blind verdict kept beside it.
6. **Known findings**, checked against this run and listed in the report with the question IDs,
   each marked "still holds / gone / changed" with evidence:
   - Q25: bare "payout" pulls must-not Schwab dividend chunks (`SCHW-DECK-2026Q3#47`,
     `SCHW-DECK-2026Q2#45`, #224); undisclosed parts put in a cited "boundary note" claim, not gaps (#215).
   - Q7: Raymond James part has no training or pay words (#224); `MS-10K-2025#153` not selected.
   - Q22: must-not `MS-PR-2026-04-15-01#15` retrieved, not cited (#230, #232).
   - Q23: Merrill count not retrieved (#216 snapshot; `BAC-SUPP-2023Q4`).
   - Q11, Q23, Q24: Form ADV Part 1A employee counts (`*-ADV1A-2026`) are outside #179's headcount
     definition scope (employees, not advisors).
   - `MS-SUPP-2020Q4#1` has segment NULL (#216).
   - Q11 / Q23 behavior choice (`gap_with_adjacent` vs bank `answer`): NEXT item 5, a project-lead decision.
   - Hybrid: #212 hybrid-norerank 21/30, level with Gate 4 fts; stays on `exp/hybrid`.
   - #212: Q17 went PASS -> FAIL under hybrid-norerank (retrieval); listed with the hybrid line.
   - Number-check false positives (NEXT item 8): flags in this run listed.
   - Gate 4 / PR #218 missed passages still outside the mock final set on `corpus-2026-11-19`:
     Q15 `SCHW-10K-2025#27` (in pool, lost in select), Q19 `EDJ-10K-2025#88`, Q20
     `FIDELITY-III-2025#0` and `UBS-NEXTGEN-2026#119` / `#13`, Q25 `RJF-PR-web-affiliation-options#1`,
     Q17 Merrill AI-tools remark (`BAC-TR-2026Q2#21`). For each: in this real run's retrieved set
     (planner parts) and cited, or not.
   - Gate 4's Q7 uncited empty cells (`no_citation`) and Q26's trade-press-only window (no RJF
     primary document inside 90 days).
   - W10 fixes to confirm in this run: Q26 newest first across parts (#230), Q22 valid output
     (#232), Q3 a part for "where they concede ground" (#224), Q12 / Q28 named gaps (#215).
   - #232: Q1's one-part plan had passage recall 0.75 vs 0.875 in the mock; this run's Q1 plan and
     recall reported.
7. **Borderline list for the second read.** Always the seven of NEXT item 9 (Q15, Q17, Q19, Q22,
   Q25, Q26, Q28), plus Q7 (borderline in #215) and every question this scoring marks borderline.
   The second, independent read is done by the PR-review reviewer agent (not the implementer): it
   reads those answers from `.eval-runs\0217-real\report.md` / `ev217\answers-dump.txt` against
   `passes_if` before opening `w10-report.md` in the diff, and posts its verdicts as a PR comment.
   Protocol (stated in the PR too): **review round 1** posts the second-read verdicts and returns
   the PR with the "read twice" acceptance item open (no merge); the implementer adds a "Second
   read" table (both verdicts, differences discussed, the reported score stays the first scorer's
   with the range the second read implies) on the same branch; **review round 2** checks the table
   against the round-1 comment and merges. Round 1's return for this item is planned, not a
   blocking return.
8. **Report.** `docs/results/w10-report.md`: score /30, tier-1 score /18, Gate 4 target line, how it
   was run (commit, snapshot, as-of, model, prompt / planner / request versions, command), per-
   question table (tier, expected -> got behavior, Gate 4, W10 partial (if run), W10 final, class,
   change label), borderline named, cost (calls planner / answer per attempt, reused, input /
   output tokens summed from `usage` of the new raw files of every attempt, invalid outputs,
   fallbacks, any rule (b) stop), known findings, the 30 answers. Table and answers come from the
   scored records (last attempt's `report.json` + log entries of rule (b) stops). Generated by a
   scratch script in `ev217\` (not committed). `docs/results/w10-report.json` as in Files.
9. **NEXT.md** rewritten: each item names the failing question IDs of this run, its class, size
   and the check; Gate 4 items that W10 closed are dropped or marked done with the issue; open
   known findings from step 6 carried over.
10. **README Status**: "As of" date, the W10 score line next to Gate 4, link to the report.
11. `/finish-task`: PR "Closes #217" from `.github/pull_request_template.md` with Verification
    (real calls, model, why), Progress line, borderline list for the reviewer; verify-cee is not
    required (no change to `src/`, `config/`, database or corpus; stated in the PR).

## Paid-call plan (CLAUDE.md "Paid API calls")
- **Go-ahead**: TL comment on #217 (2026-11-18), quoted in the PR: "the 30-question scored run in
  this issue is approved, with the real model `claude-sonnet-5-5` and the call count planned in the
  approved ExecPlan. Budget approved."
- **Questions**: Q1-Q30, one run each, planner + answer = 2 calls per question. **Cap
  `--max-calls 60`.** Expected **60 real calls, 0 reused**: every planner and answer cache key
  contains the snapshot, and no saved output is for `corpus-2026-11-19` (step 1 confirms; the W10
  partial runs were on `corpus-2026-11-17`). Fewer planner calls only where code skips search
  (ADR-020); any such question is named.
- **Why the mock cannot show it**: the mock always answers when retrieval finds something and uses
  the rule plan; the score is a reading of real answers (wording, behavior, claims vs sources), and
  the planner's parts change the real retrieved sets.
- **Rough cost**: answer input ~1.0M tokens estimated (characters / 4; mock baseline 980,854) ~= 1.7M
  real (Q22 in #232: 60k est. -> 101k real) at $2 / M ~= $3.4; output 30 x 5-12k (cap 20k)
  ~= $1.5-6 at $10 / M; planner ~30 x (1k in, <=2k out) ~= $0.5. About $5-10 total.
- **Saved**: every raw output (question, prompt / planner version, model, request version,
  `stop_reason`, `usage`, payload) in `.eval-runs\0217-real\raw\` and `.eval-runs\cache\`, copied to
  `D:\ALLPROJECTS\EDJ\cache\ev217\real\`.
- **No re-runs.** An invalid output, a failed call or a planner fallback is a counted call and a
  finding (answer: FAIL, class i). What the code does: a planner call that fails (API / network
  error, timeout) saves a `failed_call` record and falls back to the rule plan; `RealRunner.answer`
  catches only `ModelOutputError`, so an API / network error or the 600 s timeout on an **answer**
  call stops the process with nothing saved for that question and no `report.json`. Resume rule
  (TL decision, coordinator 2026-11-19: use `--questions`, no TL round-trip):
  Attempt N >= 2 always runs on the same commit with `--out .eval-runs\0217-real-N` and log
  `ev217\real-run-N.log`, HEAD logged before and after as in step 3.
  - (a) **Stop outside a model call** (as #212: traceback not from a provider call): the same
    command with `--out` and `--max-calls` as below (all 30 questions); every question already answered is reused from the cache at 0 calls
    (`how` = cached), never re-called; `--max-calls` = 60 minus calls made.
  - (b) **Stop raised by the answer call** (traceback in the log from the answer request; a planner
    API / network error is caught by `RealRunner.plan` and never stops the process): that
    question's planner and answer calls are counted, and the question is a finding (FAIL, class i,
    the traceback quoted in the report); it is **never called again**. Resume with `--questions`
    listing **every question except the one(s) stopped under (b)** (in this or an earlier attempt).
    The questions already answered are then reused from the cache at 0 calls (plan and answer
    cached, `how` = cached; cache keys hold question, snapshot, model, versions and chunk ids, not the
    run), and the questions not yet called are called, so the resumed run's `report.json` holds every
    question but the stopped one(s). `--max-calls` = 2 x the number of questions not yet called
    (reused files do not count). A further (b) stop in a later attempt repeats the rule.
  - Counting across attempts: when an attempt wrote no `report.json`, its calls are counted from its
    log and its **new** raw files (#212 precedent: 17 + 13); a resumed run's `raw/` also holds
    copies of reused files, so each attempt's count is its new raw files, not its folder total. The
    report and PR give calls per attempt and the total (<= 60). In the last report a question
    answered in an earlier attempt shows `how` = cached; step 3's per-question `how` and the cost
    line take "called" from the attempt whose new raw file appeared, not from the last report.
  - **Source of the scored records**: the **last attempt's `report.json`** (every question except
    the stopped one(s), with code caveats, citation check, part coverage, status, recall, `how` and
    plan), plus, for each question stopped under (b), its log entry (question id, attempt, call
    counts, traceback; verdict FAIL, class i). Step 4's dump, step 8's table and
    `docs/results/w10-report.json` are built from exactly these. With no stop, that is
    `.eval-runs\0217-real\report.json` alone.

## Acceptance
- [x] TL go-ahead before the first call: `gh issue view 217 --comments` shows the 2026-11-18 TL
      comment; the real-run log's first line is later (timestamps in Progress log).
- [x] Mock first: `.eval-runs\0217-mock\report.md` -> 29 PASS / 1 FAIL (Q19), refusal gap 5/5,
      keyed 22/22, 0 forbidden, no PASS -> FAIL vs `evals/baselines/corpus-2026-11-19`; 30/30 chunk
      lists identical (`ev217\mock-diff.txt`).
- [x] Saved raw outputs match the call count: per attempt, calls made (`meta.real_calls`, or the
      log when the attempt wrote no report) = new raw files that attempt wrote (planner + answer,
      each counted; reused copies excluded) = the files copied to `ev217\real\` for it, except an
      answer call stopped by an API error under resume rule (b), which has a log entry and no file
      (named); total <= 60; the PR states calls per attempt, reused, model, tokens.
- [x] The checkout did not move: `git rev-parse HEAD` logged before and after each paid command
      equals the step 1 head.
- [x] Report: 30 verdicts in `docs/results/w10-report.md` (Q1-Q30, each PASS or FAIL, class for each
      FAIL), score and tier-1 score; every verdict that differs from Gate 4 has a retrieval /
      pipeline / model label with chunk ids; W10 partial-run verdicts shown where a question was run.
- [ ] Borderline questions read twice: the reviewer agent's PR comment gives a second verdict for
      every listed borderline question (at least Q7, Q15, Q17, Q19, Q22, Q25, Q26, Q28); the report's
      "Second read" table matches it.
- [x] Known findings (step 6) each marked still holds / gone / changed in the report.
- [x] `docs/NEXT.md` reflects the new failures: every FAIL question of this run appears in at least
      one item, and no item rests only on a question that now passes (checked by a scratch script
      listing question IDs per item vs the verdicts).
- [x] README Status line updated (date, W10 score, link).
- [x] 0 code changes: `git diff origin/main --stat` lists only the five files above.
- [ ] `gh pr checks <PR#>` all green on the PR head.

## Risks
- **Non-determinism**: one sample per question; a verdict change can be model variance. Labelled
  "model" when the deciding passages were available both times; not re-rolled.
- **Real retrieval differs from the mock**: the planner's parts change each question's retrieved
  set; real-run eval statuses (e.g. Q22, Q25 must-not) are reported next to the verdicts, not
  as verdicts.
- **Large inputs**: five-firm questions read ~100k real input tokens with a 20000 output cap on a
  non-streaming call (SDK 600 s rule); a timeout is a failed call (`max_retries=0`). On the answer
  call it stops the process with nothing saved (not caught by `RealRunner.answer`): resume rule (b),
  that question FAIL class i, never called again.
- **Checkout switched mid-run** (happened in #232, PR #234): no other agent runs; HEAD logged
  before and after.
- **One scorer bias**: the blind-first order and the reviewer's second read of borderline questions
  limit it; the report states the range.
- **Comparison with W10 partial runs**: those ran on `corpus-2026-11-17` and on earlier prompt /
  planner / request versions; differences are named with the version in force at the time.

## Progress log
- 2026-11-19 06:29 - plan written on `tl/217-final-run` from main cdcb6ee (PR #236 merged; local DB
  on `corpus-2026-11-19`, sync check exit 0). No cached output for `corpus-2026-11-19` found in
  `.eval-runs\cache` (139 files: 10-22, 10-29, 11-16, 11-17 only). 0 calls so far.
- 2026-11-19 - review round 1 (issuecomment-7009310047, CHANGES REQUESTED): fixed step 1's import
  (`cee.answer.llm`) and added `ANTHROPIC_REQUEST_VERSION`; resume rule split into (a) stop outside
  a model call and (b) stop raised by a model call (`--questions`, never re-called), counted per
  attempt from new raw files; non-blocking: wording on what changed since f919a36, as-of check lists
  the five #216 documents (Q27 / `MER-ADV1A-2026` label), blind-verdict hash committed before step 5
  and kept in the json, two-round second-read protocol, more known findings, HEAD logged around the
  paid command. 0 calls.
- 2026-11-19 - review round 2 (issuecomment-7010672644): rule (b) resumes with `--questions` =
  every question except the stopped one(s), so answered questions are reused at 0 calls and the
  last attempt's `report.json` holds all but the stopped one(s); scored records = that report +
  log entries of (b) stops, used by step 4, step 8 and `w10-report.json`; (b) names the answer
  request only; no commit between step 1 and the end of step 3. 0 calls.
- 2026-11-19 - plan approved (issuecomment-7010726375, reviewed c206cbe); its two non-blocking notes
  applied (per-attempt "called"; rule (a) wording). Execution starts after this commit.
- 2026-11-19 07:37 - step 1 at HEAD 99ac877 (`ev217\asof-check.txt`): `v4.1 plan-v2 20000 strict-1`;
  224 documents / 21,161 chunks; 0 documents after 2026-11-17; 2026-08-19..20: `RJF-TRADE-2026-08-19-IN-01`
  (and one SCHW item); the five #216 documents with the expected dates, all `source`; 0 cache
  entries for `corpus-2026-11-19`.
- 2026-11-19 07:38 - step 2 mock (`.eval-runs\0217-mock`, 0 calls): 29 PASS / 1 FAIL (Q19), refusal
  gap 5/5, keyed 22/22, 0 forbidden, no status change; 30/30 chunk lists identical to the baseline
  (`ev217\mock-diff.txt`).
- 2026-11-19 07:39-07:52 - step 3 attempt 1 (`.eval-runs\0217-real`, HEAD 99ac877 before and after):
  stopped at the Q14 answer call with `400 invalid_request_error: credit balance is too low`
  (req_011ChCQ27M4QAjWSyxH3Z69q), no output, no `report.json`. 28 calls (Q1-Q13 planner + answer,
  Q14 planner, the rejected Q14 answer), 27 new raw files (`ev217\real\`, `ev217\attempt1-stop.txt`).
  TL decision on #217 (issuecomment-7011133159): option (ii), a stop outside the model's work; Q14's
  answer is called again in the resume; the rejected request counts as 1 call with 0 output.
- 2026-11-19 13:49-14:06 - step 3 attempt 2 (`.eval-runs\0217-real-2`, `--max-calls 34`, HEAD 99ac877
  before and after, exit 0): `real_calls` 33 (Q14 answer + Q15-Q30 planner and answer), reused 27
  (Q1-Q13, Q14 plan), 33 new raw files (`ev217\real-2\`). Total 61 calls (60 with output + the
  rejected one). No invalid output, no planner fallback, every `stop_reason` `tool_use`.
- 2026-11-19 14:09 - step 4 blind verdicts written before opening any Gate 4 or W10 verdict for this
  run: `ev217\verdicts-blind.json`, sha256
  `ca89a9e4e70fb65de02220c84314d3def4ad051fa0605727990c56a44d5e958f`. Blind score 25/30 (tier 1 14/18).
  Citation check: every cited chunk is in its retrieved set and in the database.
- 2026-11-19 14:30 - steps 5-10 (0 calls): comparison with Gate 4 and the W10 partial runs
  (`ev217\cmp.py`): six FAIL -> PASS (Q3, Q7, Q12, Q15, Q25, Q28), two PASS -> FAIL (Q24 model with the
  part shape; Q26 scorer reading, Gate 4's answer had the same shape); blind verdicts unchanged.
  Known findings checked (`ev217\checks.py`, `checks2.py`): Q22's must-not passage holds the NNA
  definition it cites (key error); Q25 must-not chunks not retrieved; 2 of 7 number flags are real
  sibling-passage misses (Q1, Q4). Cost (`ev217\cost.json`): 61 calls, 60 raw files, 2,019,681 input
  / 261,308 output tokens, ~$6.65 at the plan's rates. Report `docs/results/w10-report.md` + `.json`
  (`ev217\gen_w10.py`), `docs/NEXT.md` rewritten (`ev217\next-check.txt`: every FAIL in an item, no
  item on passing questions only), README Status. Second read left for PR review round 1.
