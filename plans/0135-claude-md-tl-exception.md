# 0135 - CLAUDE.md: TL-owned PRs are reviewed and merged by the reviewer agent

Issue: #135    Role: TL    Spec: CLAUDE.md (Branch and PR rules), docs/DASHBOARD.md 3b

## Goal
CLAUDE.md states, in one place, that TL-owned PRs are reviewed and merged by an independent
reviewer agent (`/tl-run`, `/tl-review`), while teammate PRs keep the rule "the tech lead
reviews and merges; do not merge your own PR". Agents and teammates then read one consistent rule.

## Files to change
- CLAUDE.md - "Branch and PR rules", last bullet only (currently line 70). The existing sentence
  stays word for word; one exception sentence is appended. New text (4 lines):

  ```
  - The tech lead reviews and merges. Do not merge your own PR. Exception (TL only): PRs for
    `role:tl` issues are reviewed and merged by an independent reviewer agent through `/tl-run`
    and `/tl-review` (`.claude/commands/tl-run.md`, `.claude/commands/tl-review.md`; see
    `docs/DASHBOARD.md` section 3b). Teammate PRs: the tech lead reviews and merges.
  ```
- plans/0135-claude-md-tl-exception.md - this plan.

Not touched: any other CLAUDE.md line (ground rules, invariants, paid-API rules, other branch
rules); `.claude/commands/tl-run.md`, `.claude/commands/tl-review.md`, docs/DASHBOARD.md (Out of
scope: the commands themselves).

Approval note: CLAUDE.md edits normally go to the tech lead. The tech lead approved exactly this
exception in chat on 2026-10-29 (stated in the issue's Why). The change is in "Branch and PR
rules", not in "Ground rules" or "Architecture invariants", so the tl-review escalation item
"a change to CLAUDE.md ground rules or invariants" does not apply; the PR body will repeat this.

## Steps
1. Replace the last bullet of "Branch and PR rules" with the text above (keep the original
   sentence unchanged, wrap at about 95 characters like the rest of the file).
2. Run the checks in Acceptance.
3. pytest (docs only: verify-cee and eval skipped, per the issue's Verification); `/finish-task`
   with "Closes #135" and the approval note in the PR body.

## Acceptance
- [x] Diff limited to the Branch and PR rules lines -> `git diff main -- CLAUDE.md` shows one
  hunk; every removed/added line lies inside "## Branch and PR rules" (only the old line 70
  removed, its replacement lines added); `git diff --stat main` lists only CLAUDE.md and this plan.
- [x] Teammate rule still holds -> the bullet still contains, unchanged, "The tech lead reviews
  and merges. Do not merge your own PR." and the exception is limited to "`role:tl` issues";
  it ends "Teammate PRs: the tech lead reviews and merges." Check:
  `grep -n "Do not merge your own PR" CLAUDE.md` -> 1 hit in Branch and PR rules;
  `grep -n "Teammate PRs: the tech lead reviews and merges" CLAUDE.md` -> 1 hit.
- [x] Points to DASHBOARD 3b and both commands -> `grep -n -e "DASHBOARD.md. section 3b" -e "tl-run" -e "tl-review" CLAUDE.md`
  -> hits all fall in the Branch and PR rules bullet, naming `/tl-run`, `/tl-review`,
  `.claude/commands/tl-run.md`, `.claude/commands/tl-review.md` and `docs/DASHBOARD.md` section 3b.
- [x] Consistent with DASHBOARD 3b -> 3b says reviewer agent squash-merges TL PRs and "Teammate PRs
  are still reviewed by the tech lead"; the new CLAUDE.md text says the same (manual read).
- [x] `.venv\Scripts\python.exe -m pytest -q` (Mac: `.venv/bin/python -m pytest -q`) -> all pass,
  same count as main (222 with the old CLAUDE.md; 222 on this branch). verify-cee and eval skipped: docs only. 0 paid calls.

## Progress log
- 2026-10-30 00:36 - plan written; branch tl/135-claude-md-tl-exception from main (678c381); waiting for the reviewer agent's plan review
- 2026-10-30 00:38 - reviewer agent approved the plan (issue comment; blocking: none; 2 non-blocking notes: "2 lines" -> 4 lines, keep the wrapping as shown so the greps hit). Both applied
- 2026-10-30 00:39 - CLAUDE.md bullet replaced with the 4 lines above, wrapping as in the plan; diff is one hunk in Branch and PR rules; greps: "Do not merge your own PR" 1 hit (line 70), "Teammate PRs: ..." 1 hit (line 73), DASHBOARD 3b / tl-run / tl-review hits only on lines 70-73; pytest 222 passed (same as before the edit); next: PR
