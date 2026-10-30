# 0133 - Agent-run TL workflow with an independent reviewer

Issue: #133    Role: TL    Spec: docs/DASHBOARD.md, CLAUDE.md (branch and PR rules)

## Goal
A TL issue goes from `/start-task` to merged without the tech lead clicking: one agent does
the work by the normal flow, a second, independent agent approves or returns the plan and
the PR, and merges. The tech lead is pulled in only for the escalation cases.

## Files to change
- .claude/commands/tl-run.md (new) - orchestrator: who runs what, in which order, loop limits, escalation
- .claude/commands/tl-review.md (new) - reviewer checklist for a plan or a PR; usable alone (`/tl-review pr 131`)
- docs/DASHBOARD.md - section "3b. TL workflow (agent-run)"
- plans/0133-tl-agent-review.md - this plan

## Steps
1. Write `/tl-review`: two modes (plan, pr), what to read, what to re-run, how to record the verdict.
2. Write `/tl-run`: implementer agent (start-task flow, plan committed on the branch), reviewer on the plan, implement + finish-task, reviewer on the PR, merge or return; at most 2 return rounds each.
3. DASHBOARD section.
4. Dogfood: run the reviewer on this PR; it merges or returns.

Note: GitHub does not let an account approve or request changes on its own PR, so the
verdict is a PR comment (`gh pr review --comment` / `gh pr comment`), headed APPROVED or CHANGES REQUESTED.

## Acceptance
- [ ] `/tl-run` covers implementer -> plan review -> implement -> PR review -> merge, max 2 rounds each
- [ ] Reviewer gets only issue / plan / PR numbers, never the implementer's summary
- [ ] Escalation list: third round, ADR change, paid API call, deleting data or snapshots, CLAUDE.md ground rules, teammate-owned files without their review
- [ ] Written verdict on the PR before merge
- [ ] This PR reviewed and merged by the reviewer agent

## Progress log
- 2026-10-29 23:40 - plan written; design approved by the TL in chat (reviewer agent also approves ExecPlans)
- 2026-10-29 23:50 - tl-review.md, tl-run.md, DASHBOARD 3b written; next: PR and reviewer-agent review of this PR
- 2026-10-29 23:58 - reviewer agent returned the PR (2 fixes in tl-run.md: run start-task steps 1-6 with the reviewer replacing the user's approval in step 4; close-out covers Part of vs Closes). Both fixed
