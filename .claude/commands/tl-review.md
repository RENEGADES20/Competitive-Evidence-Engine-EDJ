---
description: Independent review of a TL ExecPlan or PR - approve (and merge a PR) or return it with reasons
argument-hint: plan <issue#> | pr <PR#>
---

You are the **reviewer**, not the author. Review `$ARGUMENTS` on its own merits. You get no
summary from whoever wrote it: read the repo, the issue, the plan and the PR yourself.
Explain the verdict in plain language. Be strict: "it probably works" is a return.

## Read first (both modes)
- The issue: `gh issue view <issue#>` (every section: Goal, Acceptance, Verification, Out of scope, Depends on).
- `CLAUDE.md`: ground rules, architecture invariants, paid-API rules, branch and PR rules.
- The spec named in the issue, and `PLANS.md`.
- Every "Depends on" issue/PR: is it merged on `main`?

## Mode `plan <issue#>`
The plan is `plans/<NNNN>-*.md` on branch `tl/<issue#>-*` (`git fetch origin`, then read it from that branch).
Return it unless all hold:
1. Every Acceptance item of the issue maps to a plan Acceptance item with a concrete check (command -> expected result, question ID -> behavior).
2. "Files to change" stays inside the issue's scope; nothing from "Out of scope"; no teammate-owned file without naming the owner as reviewer (CLAUDE.md spec table).
3. No invariant is bent (hard filters in SQL, one LLM call, citations only to retrieved chunks, caveats by code, question bank append-only).
4. Windows and Mac: any script or setup step has both versions.
5. Paid calls: 0, or planned per CLAUDE.md (question IDs, why, count).
6. Steps are small and testable; risks named.

Verdict: post on the issue
`gh issue comment <issue#> --body "PLAN APPROVED (reviewer agent) ..."` or `"PLAN CHANGES REQUESTED (reviewer agent)"` + numbered, specific fixes.

## Mode `pr <PR#>`
1. `gh pr view <PR#>`, `gh pr diff <PR#>`; `gh pr checkout <PR#>`.
2. Check the diff against the approved plan and the issue: no file outside the plan, no leftover debug, `.ps1` and `.sh` twins match.
3. **Re-run the evidence yourself; never trust the PR text.**
   - `pytest -q` (venv Python for this OS).
   - Change touches `src/`, `config/`, the database, scripts or the corpus: `python scripts/verify_cee.py run`.
   - Retrieval or answer change: `python scripts/eval_run.py --as-of <date in PR> --baseline <latest baseline>`; no PASS -> FAIL, refusal accuracy not lower.
   - Mock only. Never make a paid call during review.
4. Proof of work honest: every ticked box is true; `Closes #N` only if every acceptance item is done, else `Part of #N` with the open items; the ExecPlan Progress log is current; no `.env`, `*.dump`, `data/raw/` in the diff; `docs/PROGRESS.md` untouched.
5. Verdict as a PR comment (an account cannot approve its own PR on GitHub):
   - Approve: `gh pr review <PR#> --comment --body "APPROVED (reviewer agent): <what you re-ran and saw>"`, then
     `gh pr merge <PR#> --squash --delete-branch`, `git switch main && git pull`.
     If the PR says `Part of #N`, comment on the issue with what stays open.
   - Return: `gh pr review <PR#> --comment --body "CHANGES REQUESTED (reviewer agent)"` + numbered, specific fixes (file, line, what to change, how you will check it). Do not merge.

## Never merge; escalate to the tech lead instead
- A new or changed ADR, or a change to CLAUDE.md ground rules or invariants.
- Any paid API call in the change or needed to verify it.
- Deleting data, documents, snapshots or questions from `evals/questions.yaml`.
- A teammate-owned file changed without that teammate's review on the PR.
- A check you could not run, or one that fails on `main` too and the PR does not say so.
Post "ESCALATED TO TL (reviewer agent): <reason>" on the PR and stop.
