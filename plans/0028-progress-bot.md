# 0028 - PROGRESS written by a bot on merge

Issue: #28    Role: TL    Spec: docs/DASHBOARD.md (review loop)

## Goal
Open PRs never conflict on `docs/PROGRESS.md`, and the log shows only merged work.

## Files to change
- scripts/progress_append.py, .github/workflows/progress.yml, tests/test_progress_append.py - new
- docs/PROGRESS.md - Status log split into one table per role
- CLAUDE.md, .github/pull_request_template.md, .claude/commands/finish-task.md, docs/DASHBOARD.md - rule moves to the PR's `## Progress line`

## Steps
1. Script: read the merged-PR event, take the `## Progress line` (or the title), append to the role table.
2. Workflow on merged PRs into main; one run at a time; push with retry.
3. Split PROGRESS by role; update the rules.

## Acceptance
- [x] Unit tests: 6 passed (section parsing, title fallback, escaping, role table, idempotent, new section)
- [ ] Merging this PR leaves a bot commit on main with a TL row for #29

## Progress log
- 2026-10-14 - found `|` inside a PROGRESS cell (the #25 line) broke the table; the script now replaces `|` in cells
