# 0122 - Mac versions of every script; RUN.md for Windows and macOS

Issue: #122    Role: TL    Spec: docs/RUN.md (ops); ADR-006 snapshot flow unchanged

## Goal
Teammates on a Mac can install, restore a snapshot, ingest and (TL) build a snapshot with the
same steps as Windows users, without PowerShell.

## Files to change
- scripts/_common.sh (new) - shared helpers: repo root, venv Python (Mac or Git Bash), .env reader, database start/reset, row counts
- scripts/restore.sh, scripts/ingest.sh, scripts/build-snapshot.sh (new) - twins of the .ps1 scripts
- docs/RUN.md - Mac block next to every Windows block; Mac troubleshooting rows
- docs/DASHBOARD.md - snapshot checklist names both scripts

## Steps
1. Read the four .ps1 scripts; keep arguments, lookup order, checks, messages and exit codes.
2. Write the .sh twins; make them work in Git Bash too (Python path, `MSYS_NO_PATHCONV`), so they can be tested on Windows.
3. Test: syntax, restore + smoke, full `--allow-branch` build, error paths.
4. RUN.md and DASHBOARD.md.

## Acceptance
- [x] `bash -n` on every .sh
- [x] `restore.sh corpus-2026-10-29.dump` -> 111 docs / 17183 chunks; `cee.smoke` PASS; no-argument restore skips `-test` dumps
- [x] `build-snapshot.sh --allow-branch` full run -> same row counts as the official snapshot
- [x] Missing file / unknown argument / manifest failure -> clear message, exit 1
- [x] verify-cee all features PASS (`.verify-runs/20261029-232000-ab70a01`)
- [ ] `restore.sh` + smoke on a real Mac (needs a teammate)

## Progress log
- 2026-10-29 23:00 - plan written after the fact: #122 was done and merged (#130) without an ExecPlan (process slip); plan reconstructed from what was done
- 2026-10-29 23:20 - all Windows/Git Bash checks above pass; real-Mac run still open on #122
