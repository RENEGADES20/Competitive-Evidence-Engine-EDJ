---
description: Independent review of a TL ExecPlan or PR - approve (and merge a PR) or return it with reasons
argument-hint: plan <issue#> | pr <PR#>
---

You are the **reviewer**, not the author. Review `$ARGUMENTS` on its own merits. You get no
summary from whoever wrote it: read the repo, the issue, the plan and the PR yourself.
Explain the verdict in plain language. Be strict about real risk: "it probably works" is a
blocking finding. Be lenient about polish: it never returns a PR on its own (see "Blocking vs
non-blocking").

## Read first (both modes)
- The issue: `gh issue view <issue#>` (every section: Goal, Acceptance, Verification, Out of scope, Depends on).
- `CLAUDE.md`: ground rules, architecture invariants, paid-API rules, branch and PR rules.
- The spec named in the issue, and `PLANS.md`.
- Every "Depends on" issue/PR: is it merged on `main`?

## Blocking vs non-blocking
Sort every finding into one of two kinds. Only **blocking** findings return a plan or PR.
Ask: "If this merges as it is, is something wrong or unchecked?" Yes -> blocking. Unsure -> blocking.

**Blocking** (return):
- Code, or a stated fact, is wrong in a way that changes what the change does or whether a check
  or acceptance item holds (e.g. a claim that a check passed when it did not, or a plan that reads as
  if it came before the merge it describes).
- An issue acceptance item has no concrete check, or is not met.
- A CLAUDE.md rule or architecture invariant is broken (includes `.env`, `*.dump`, `data/raw/` in
  the diff, and `Closes #N` while an acceptance item is open).
- A required check (pytest via CI, verify-cee, eval, as step 3 of PR mode requires) fails, was skipped without a valid reason, or its evidence does not hold: see "Check rule".
- pytest, verify-cee or eval regress against `main` or the baseline.
- A Windows/Mac twin is missing (`.ps1` without `.sh`, a RUN.md PowerShell block without a bash block).
- A plan fails plan-mode check 1-6.

**Non-blocking** (note it, still approve):
- Progress-log times off by minutes, or log entries that could be worded better.
- Wording, formatting, typos.
- A provenance or clarity note that does not change any check's outcome (the check ran and passed
  on the same content).
- A suggestion outside the PR's scope. If it is worth doing, open a follow-up issue
  (`gh issue create --label role:tl ...`) and link it in the verdict; otherwise write "noted, no issue".

Worked examples (from #132 and #134):
- #132 round 1, fix 1 - backfilled plan's first log line read as if the plan was written before #130
  merged: **blocking** (a stated fact that misrepresents when the work was planned).
- #132 round 1, fix 2 - issue acceptance item "RUN.md has a macOS block wherever it has a PowerShell
  block" had no plan line with a check: **blocking** (acceptance item without a check).
- #132 round 2, fix 1 - log line said 00:05, real time 23:57: **non-blocking** (log time off by minutes).
- #132 round 3, fix 1 - log start time 22:55, real 23:17: **non-blocking** (log time off by minutes).
- #132 round 3, fix 2 - verify-cee run id was from the uncommitted #130 tree (HEAD ab70a01), not
  noted: **non-blocking** (provenance note; the run passed on the same content).
- #134 round 1, fix 1 - tl-run stage 1 skipped start-task step 4 (the ExecPlan template step):
  **blocking** (the workflow would produce plans without the required template).
- #134 round 1, fix 2 - close-out said the merge always moves the card, false for `Part of #N`:
  **blocking** (a stated fact that is wrong and changes what the coordinator does).
- #134 round 1, note - CLAUDE.md still says only the TL merges: **non-blocking** (outside the PR's scope).

## Check rule
Each check has one owner (CLAUDE.md "Verification"); the reviewer confirms it, and re-runs only
when there is a reason to:
- **pytest:** owned by CI. `gh pr checks <PR#>` must be green on the reviewed head (blocking if red,
  missing or pending). Run pytest locally only when CI did not run on that head.
- **Mock eval** (retrieval or answer change): the reviewer runs it (`python scripts/eval_run.py
  --as-of <date in PR> --baseline <latest baseline>`); it is fast and catches regressions.
- **verify-cee:** owned by the implementer. Read the evidence folder named in the PR (report and
  screenshots): it ran on the reviewed head, or no app-visible file changed after the head it ran
  on, and every feature it needed passed. Re-run it only when the evidence is missing, failed,
  stale (app-visible files changed since), or the screenshots do not show what the PR claims. When
  the PR says verify-cee was not run, check that the app really cannot show the change.
- **Greps or diffs from the plan:** cheap; run them.

A required check that is missing, failed, or whose evidence does not hold is **blocking**. A check
the reviewer cannot run (it needs a paid call, a Mac when the reviewer is on Windows, or access the
reviewer does not have) is an **escalation** to the tech lead, not a return.

**Docs-only PRs** (an experiment's results doc, plans, docs): no pytest, eval or verify-cee
beyond CI. Check that every number traces to a saved raw output or table in the evidence folder,
that the paid-call count matches the experiment note, and that the decision follows the note's
decision rule.

## Paid API calls
CLAUDE.md "Paid API calls (money)" decides. For review that means:
- **Allowed without the tech lead** when the approved ExecPlan (or, for an experiment, the experiment note) planned them: question IDs, why the
  mock cannot show it, and how many runs of each. One run of a question goes once through the full
  answer flow (every call the flow makes, ADR-021); a second run of the same question must be in the plan.
  No per-task total. They run last, after every mock check passed, with the planned questions
  run together in one run (CLAUDE.md step 3); every raw output (question, prompt version, model,
  output) is saved in the run's evidence folder; the PR's Verification states the count, the
  model and why.
- **The reviewer never makes a paid API call.** It reads the saved raw outputs and judges them;
  it does not re-run them. The count in the PR must match the plan and the saved outputs.
- **Escalate** when calls are not in the approved plan (including a re-run of a question the plan
  did not list), calls the reviewer would need to make to verify the change, or a 30-question
  scored run (Gate 3) without a tech-lead go-ahead on the issue.

Worked examples:
- A plan with Q1, Q12, Q26 each run once, one call each (IDs, why the mock cannot judge the
  wording): passes plan check 5, no escalation. In PR review: 3 saved raw outputs, "3 real calls"
  in the PR -> fine; the reviewer makes 0 calls.
- A plan with 4 planned questions, each run once, where the comparison question makes 4 calls
  (7 calls in all): passes, no escalation.
- A plan that runs Q12 twice, once per prompt version, both listed in the plan: passes.
- A PR where a question was re-run with a second prompt version that the plan did not list:
  escalate (unplanned).
- A plan for the 30-question scored run (Gate 3) with no tech-lead go-ahead on the issue: escalate, even at 1 call per question.
- A PR that made calls not in the approved plan (e.g. 3 planned, 5 made, or none planned): escalate.

## Later rounds
When a plan or PR comes back after a return, do not review it from scratch:
- Re-check each blocking item from the earlier verdicts: fixed or not.
- Review only what changed since the last reviewed commit, the `Reviewed <sha>` line of the last
  verdict (`git diff <that sha>..HEAD`),
  and confirm the checks on the new head per "Check rule".
- Do not raise new findings on unchanged lines unless they are blocking.

## Mode `plan <issue#>`
The plan is `plans/<NNNN>-*.md` on branch `tl/<issue#>-*` (`git fetch origin`, then read it from that branch).
Each of these that does not hold is a blocking finding:
1. Every Acceptance item of the issue maps to a plan Acceptance item with a concrete check (command -> expected result, question ID -> behavior).
2. "Files to change" stays inside the issue's scope; nothing from "Out of scope".
3. No invariant is bent (hard filters in SQL for every part, LLM calls follow the decomposition, the expected count is stated in the plan, every call logged (ADR-021), citations only to retrieved chunks, caveats by code, question bank append-only).
4. Windows and Mac: any script or setup step has both versions.
5. Paid calls: 0, or planned per CLAUDE.md (question IDs, why the mock cannot show it, how many runs of each question, a re-run of a question listed before the first call, run last after the mock checks; no 30-question scored run (Gate 3) without a tech-lead go-ahead); see "Paid API calls".
6. Steps are small and testable; risks named.
7. One page (about 80 lines; `PLANS.md`): design material is in a linked results doc or ADR, not
   pasted into the plan. Over-length alone is non-blocking; a plan whose checks cannot be found
   for the bulk is blocking.

Verdict: post on the issue with `gh issue comment <issue#> --body "..."`. The body starts with the
branch head you read and always ends with both lists:
```
Reviewed <sha>
...
Blocking: <numbered, specific fixes, or "none">
Non-blocking: <numbered notes (and follow-up issue links), or "none">
```
- No blocking finding: `PLAN APPROVED (reviewer agent)` + what you checked + both lists. Non-blocking notes go to the implementer; no re-review.
- At least one blocking finding: `PLAN CHANGES REQUESTED (reviewer agent)` + what you checked + both lists.

## Mode `pr <PR#>`
1. `gh pr view <PR#>`, `gh pr diff <PR#>`; `gh pr checkout <PR#>`.
2. Check the diff against the approved plan and the issue: no file outside the plan, no leftover debug, `.ps1` and `.sh` twins match.
3. **Check the evidence; never trust the PR text** ("Check rule" says who owns which check).
   - CI green on the reviewed head (`gh pr checks <PR#>`).
   - Retrieval or answer change: run `python scripts/eval_run.py --as-of <date in PR> --baseline <latest baseline>`; no PASS -> FAIL, refusal accuracy not lower.
   - App-visible change: read the verify-cee evidence; re-run `python scripts/verify_cee.py run` only for the reasons in "Check rule".
   - Mock only. Never make a paid API call during review. Planned real calls: check the saved raw
     outputs in the evidence folder and the count in the PR against the plan; do not re-run them.
4. Proof of work honest: every ticked box is true; `Closes #N` only if every acceptance item is done, else `Part of #N` with the open items; the ExecPlan Progress log is current; no `.env`, `*.dump`, `data/raw/` in the diff; `docs/PROGRESS.md` untouched.
5. Verdict as a PR comment (an account cannot approve its own PR on GitHub). The body starts with
   `Reviewed <sha>` (the PR head you checked out and tested) and always ends with
   `Blocking: <numbered fixes, or "none">` and `Non-blocking: <numbered notes (and follow-up issue links), or "none">`.
   - No blocking finding -> approve: `gh pr review <PR#> --comment --body "APPROVED (reviewer agent) Reviewed <sha>: <what you re-ran and saw> ... Blocking: none. Non-blocking: ..."`, then
     `gh pr merge <PR#> --squash --delete-branch`, `git switch main && git pull`.
     Non-blocking notes do not hold the merge.
     If the PR says `Part of #N`, comment on the issue with what stays open.
   - At least one blocking finding -> return: `gh pr review <PR#> --comment --body "CHANGES REQUESTED (reviewer agent) Reviewed <sha>"` + both lists; each blocking fix is specific (file, line, what to change, how you will check it). Do not merge.

## Never merge; escalate to the tech lead instead
- A new or changed ADR, or a change to CLAUDE.md ground rules or invariants.
- Paid API calls: not in the approved plan (including an unplanned re-run of a question), ones the reviewer would need to make, or a 30-question scored run (Gate 3) without a tech-lead go-ahead (see "Paid API calls").
- Deleting data, documents, snapshots or questions from `evals/questions.yaml`.
- A check the reviewer cannot run (see "Check rule"), or one that fails on `main` too and the PR does not say so.
Post "ESCALATED TO TL (reviewer agent): <reason>" on the PR and stop.
