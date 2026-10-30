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
- A required check fails or was not run (pytest, verify-cee, eval, as step 3 of PR mode requires).
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

## Later rounds
When a plan or PR comes back after a return, do not review it from scratch:
- Re-check each blocking item from the earlier verdicts: fixed or not.
- Review only what changed since the last reviewed commit (`git diff <last reviewed sha>..HEAD`),
  and re-run the checks (pytest etc.) on the new head.
- Do not raise new findings on unchanged lines unless they are blocking.

## Mode `plan <issue#>`
The plan is `plans/<NNNN>-*.md` on branch `tl/<issue#>-*` (`git fetch origin`, then read it from that branch).
Each of these that does not hold is a blocking finding:
1. Every Acceptance item of the issue maps to a plan Acceptance item with a concrete check (command -> expected result, question ID -> behavior).
2. "Files to change" stays inside the issue's scope; nothing from "Out of scope"; no teammate-owned file without naming the owner as reviewer (CLAUDE.md spec table).
3. No invariant is bent (hard filters in SQL, one LLM call, citations only to retrieved chunks, caveats by code, question bank append-only).
4. Windows and Mac: any script or setup step has both versions.
5. Paid calls: 0, or planned per CLAUDE.md (question IDs, why, count).
6. Steps are small and testable; risks named.

Verdict: post on the issue with `gh issue comment <issue#> --body "..."`. The body always ends with both lists:
```
Blocking: <numbered, specific fixes, or "none">
Non-blocking: <numbered notes (and follow-up issue links), or "none">
```
- No blocking finding: `PLAN APPROVED (reviewer agent)` + what you checked + both lists. Non-blocking notes go to the implementer; no re-review.
- At least one blocking finding: `PLAN CHANGES REQUESTED (reviewer agent)` + what you checked + both lists.

## Mode `pr <PR#>`
1. `gh pr view <PR#>`, `gh pr diff <PR#>`; `gh pr checkout <PR#>`.
2. Check the diff against the approved plan and the issue: no file outside the plan, no leftover debug, `.ps1` and `.sh` twins match.
3. **Re-run the evidence yourself; never trust the PR text.**
   - `pytest -q` (venv Python for this OS).
   - Change touches `src/`, `config/`, the database, scripts or the corpus: `python scripts/verify_cee.py run`.
   - Retrieval or answer change: `python scripts/eval_run.py --as-of <date in PR> --baseline <latest baseline>`; no PASS -> FAIL, refusal accuracy not lower.
   - Mock only. Never make a paid call during review.
4. Proof of work honest: every ticked box is true; `Closes #N` only if every acceptance item is done, else `Part of #N` with the open items; the ExecPlan Progress log is current; no `.env`, `*.dump`, `data/raw/` in the diff; `docs/PROGRESS.md` untouched.
5. Verdict as a PR comment (an account cannot approve its own PR on GitHub). The body always ends with
   `Blocking: <numbered fixes, or "none">` and `Non-blocking: <numbered notes (and follow-up issue links), or "none">`.
   - No blocking finding -> approve: `gh pr review <PR#> --comment --body "APPROVED (reviewer agent): <what you re-ran and saw> ... Blocking: none. Non-blocking: ..."`, then
     `gh pr merge <PR#> --squash --delete-branch`, `git switch main && git pull`.
     Non-blocking notes do not hold the merge.
     If the PR says `Part of #N`, comment on the issue with what stays open.
   - At least one blocking finding -> return: `gh pr review <PR#> --comment --body "CHANGES REQUESTED (reviewer agent)"` + both lists; each blocking fix is specific (file, line, what to change, how you will check it). Do not merge.

## Never merge; escalate to the tech lead instead
- A new or changed ADR, or a change to CLAUDE.md ground rules or invariants.
- Any paid API call in the change or needed to verify it.
- Deleting data, documents, snapshots or questions from `evals/questions.yaml`.
- A teammate-owned file changed without that teammate's review on the PR.
- A check you could not run, or one that fails on `main` too and the PR does not say so.
Post "ESCALATED TO TL (reviewer agent): <reason>" on the PR and stop.
