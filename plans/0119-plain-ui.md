# 0119 - Plain UI pass before Gate 3

Issue: #119    Role: U1    Spec: specs/ui.md

## Goal
A first-time user can ask, read, open a source and leave feedback without help: every page says
in one line what it shows, and empty or no-evidence results read in plain language.

## Files to change
- src/cee/app/views/ask_page.py - plain intro naming the five firms; empty state; one sentence under each answer heading (BEHAVIOR_HELP); "filters may be hiding the evidence" note on gap answers; meta line "passages found | model: <provider>"
- src/cee/app/views/coverage_page.py - one-line purpose, legend for COVERED / THIN / EMPTY / not tracked, plain date note
- src/cee/app/views/source_page.py - one-line purpose; plain message for an unknown chunk
- src/cee/app/views/design_page.py - says it is for the team and not evidence
- scripts/verify_cee.py, .claude/skills/verify-cee/features/gap-path.md, ask-progress.md - meta wording; gap-path checks the plain sentence

## Steps
1. Wording on each page; no new features, no change to answers (gap text in validate.py is S2's and unchanged).
2. Update the driver for the new meta wording; add the gap-path plain-line check.
3. verify-cee full run; before/after screenshots of Ask, gap answer, source, unknown chunk, Coverage.

## Acceptance
- [x] Every page has a one-line explanation of what it shows (Ask, Source, Coverage, Design)
- [x] Empty states (before asking, no results, gap answer, unknown chunk) read in plain language
- [x] verify-cee all features PASS; screenshots in the PR
- [x] 0 real model calls
- [ ] After #62 merges: sync with main and rerun verify-cee including `feedback`

## Progress log
- 2026-11-05 - plan written, implemented
- 2026-11-05 - pytest 276 passed; verify-cee all 8 features PASS (run 20261105-101955-9dc4c9b); before = run 20261105-101539-9dc4c9b; 0 real model calls
