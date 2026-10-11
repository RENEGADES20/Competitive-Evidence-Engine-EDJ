# 0022 - Verification workflow: verify-cee and teammate setup

Issue: #22    Role: TL    Spec: CLAUDE.md (Verification), specs/ui.md (features driven)

## Goal
Any agent on any teammate's laptop can prove a change in the running app, with
screenshots and step logs, before opening a PR. Tests passing stops counting as proof.

## Files to change
- scripts/verify_cee.py - new control CLI: doctor, launch, drive, cleanup, run
- .claude/skills/verify-cee/ - skill and feature map (5 features)
- requirements-verify.txt, .gitignore - Playwright pin; ignore .verify-runs/
- .claude/commands/finish-task.md, .github/pull_request_template.md - verification step and
  section; "Part of #N" for partial delivery
- CLAUDE.md - Verification rules
- .claude/settings.json - guard hook finds python3/python/py (macOS has no `python`)
- docs/WORKFLOW-SETUP.md - one-time setup run by each teammate's Claude
- docs/PROGRESS.md - log line

## Steps
1. Write verify_cee.py against the live app; isolate it (copy db to cee_verify, own port,
   mock provider, kill only what it started).
2. Run all features; fix the recipe when the failure is the script's, not the app's.
3. Seed a defect in the app and confirm the matching feature FAILs; revert.
4. Write the skill, feature map, finish-task step, PR template, CLAUDE.md rules.
5. Make the guard hook cross-platform; test block / allow / no-python.
6. Write the teammate setup file; run its checks on Windows.

## Acceptance
- [x] `verify_cee.py run`: 5/5 PASS on TL machine, snapshot corpus-2026-09-30
- [x] Seeded defect (changed "not in the stored corpus" message) -> invalid-chunk FAIL
- [x] Guard: push to main exit 2; commit on branch exit 0; no Python -> exit 2
- [x] pytest 11 passed
- [ ] macOS run of WORKFLOW-SETUP.md by one teammate (reported on #23)

## Progress log
- 2026-10-10 21:30 - plan written; verify_cee.py first run: 3 PASS, 2 FAIL
- 2026-10-10 21:33 - both FAILs were the script's: citations open in a new tab; `#` in chunk
  IDs must be URL-encoded. Fixed; 5/5 PASS
- 2026-10-10 21:35 - seeded defect caught; reverted
- 2026-10-10 21:40 - found the guard hook never ran on macOS (`python` missing); fixed.
  Found the guard lets a command through when its input does not parse (e.g. PowerShell
  pipe adds a BOM); left as is, noted for the next hardening PR
- 2026-10-10 22:10 - setup made prompt-driven; runs record the snapshot name, because
  every laptop has its own local database
