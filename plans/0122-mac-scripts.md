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
- [x] verify-cee all features PASS (`.verify-runs/20261029-232000-ab70a01`; run on the uncommitted #130 working tree, HEAD ab70a01)
- [x] Issue: "Each .sh matches its .ps1 (same arguments, same checks, same exit codes)" -> read side by side: `-Doc`/`--doc`, `-AllowBranch`/`--allow-branch`, same lookup order (CORPUS_SHARE_PATH/snapshots, then ./snapshots, `-test` skipped), same messages, exit 1 on every failure
- [x] Issue: "RUN.md has a macOS block wherever it has a PowerShell block" -> in `docs/RUN.md` as merged in #130 (c989e76): 8 `powershell` code blocks, 8 `bash` code blocks, each bash block right after its PowerShell twin
- [ ] Issue: "`restore.sh` + `python -m cee.smoke` PASS on a Mac" -> needs a teammate's Mac
- [x] Issue: "verify-cee PASS" -> see above

## Progress log
- 2026-10-29 23:17-23:21 - checks above run on Windows / Git Bash for #130, before it was merged (#130 merged 23:21)
- 2026-10-29 23:33 - plan written after the fact: #122 was done and merged (#130) without an ExecPlan (process slip); plan reconstructed from what was done
- 2026-10-29 23:57 - reviewer agent returned #132 (round 1): wrong time on the first log line; two issue items had no acceptance line
- 2026-10-29 23:58 - both fixed (lines above); RUN.md block count (indented fences included) checked on c989e76
- 2026-10-29 23:59 - round 2 returned: the 00:05 time on the round-1 line was wrong (later than its own commit); corrected to the review time 23:57
- 2026-10-30 00:28 - round 3 escalated to the TL (two one-line fixes: check times 23:17-23:21, verify-cee run was on the uncommitted tree); TL decided: apply both and merge
