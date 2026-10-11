# 0025 - Dispatch: draft next issues from the real project state

Issue: #25    Role: TL    Spec: docs/DASHBOARD.md (3a), docs/TEAM.md (week plan)

## Goal
After a merge or once a week, the tech lead gets a draft of the next issues per role,
decided from what actually landed, with checkable acceptance, plus draft replies to
teammate comments. Nothing reaches GitHub until the tech lead approves.

## Files to change
- scripts/project_state.py - new, read-only state report for the planner
- scripts/dispatch_apply.py - new, validates and applies an approved draft
- .claude/commands/dispatch.md - new command: after <PR#> | week [Wn] | inbox
- .github/ISSUE_TEMPLATE/task.yml - Why, Inputs, Deliverable, Verification, Out of scope, Depends on
- config/team.yaml - role -> GitHub login, project number
- tests/test_dispatch_apply.py - fake gh: validation, links, resumable apply
- docs/DASHBOARD.md, .gitignore (.dispatch/), docs/PROGRESS.md

## Steps
1. State report from gh (board via GraphQL, issues with comments, PRs, TEAM.md, PROGRESS).
2. Command with readiness rules (assign / assign with stub / defer / ask), load and
   file-overlap limits, comment triage (Q/B/D/S/I), issue body sections.
3. Apply script: check-only default, validation, create + board fields + blocked-by, two-pass
   cross-links, replies, resumable record, last-run time.
4. Run it for real on W4 (draft only) and fix what the run shows.

## Acceptance
- [x] State report on the live repo: 22 issues/PRs, comments on #9, #11, #12 marked NEW
- [x] Apply script tests: 3 passed (check-only changes nothing; vague/unordered draft
      rejected; links, dependencies, board week and resume after a failure)
- [x] W4 draft from the current state passes the apply script's check
- [ ] Applied on GitHub after tech-lead approval (separate decision)

## Progress log
- 2026-10-10 22:40 - state report first run; comments over 1500 chars were cut (U1's
  questions in #11), limit raised to 6000
- 2026-10-10 23:00 - planning W4 found edgar.py builds 10-Q IDs from the year only, so two
  10-Qs of one year collide; the draft adds a TL issue before C1's 10-Q work
- 2026-10-10 23:10 - drafts reference issues created later in the same run; apply now
  creates all issues first, then fills the cross-links
- 2026-10-10 23:20 - made each apply step resumable (create, board, each blocked-by link)
