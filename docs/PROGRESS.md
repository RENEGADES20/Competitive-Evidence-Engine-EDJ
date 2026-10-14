# Progress

Add one line per landed PR or notable event, newest at the bottom. Keep it short.

## Status log

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-09-28 | Skeleton docs created | Licensing question open (ADR-000) | Tech lead builds end-to-end skeleton (plans/0001) |
| 2026-09-30 | End-to-end skeleton on TL machine (#13): EDJ 10-K (335 chunks), FTS, Answer JSON + citation check, gap/refuse path, Streamlit source view, build-snapshot/restore, smoke check, 11 tests | ADR-000 still open | Install on the other six machines and Gate 1 (#14) |
| 2026-09-30 | First official snapshot `corpus-2026-09-30` (1 document, 335 chunks) built from main and published to Box `snapshots/`; restore now skips `-test` dumps | Windows Smart App Control once blocked a pandas DLL during build-snapshot (a retry passed) | Teammates restore it during #14 |
| 2026-10-10 | Verification workflow (#22): `verify-cee` skill drives the UI like a user (5 features, screenshots in `.verify-runs/`), wired into `/finish-task` and the PR template; guard hook fixed for macOS; `docs/WORKFLOW-SETUP.md` for teammates | Guard still lets unparsable input through; macOS setup not yet run by a teammate | Teammates run setup and report on #23; next: move ground rules into CI checks |
| 2026-10-13 | Prompt v0 and standard gap/boundary wording (#10): `src/cee/answer/prompt.py`, wording table in specs/answer-citations.md (Q12, Q19, Q28-Q30) | Real-model check of Q28-Q30 waits for BAC/MS documents in the corpus | Code-inserted caveats, boundary sentence and number check (S2, W3+) |

## Weekly score (from W6)

Posted by the domain owner (C1) every week. "Snapshot" is the corpus dump the scores were
run against, e.g. `corpus-2026-11-02`. How to score: [evals/questions.yaml](../evals/questions.yaml)
(four axes: correct, cited, complete, honest; verdict: would the project lead forward it?).

| Date | Snapshot | X/30 | Failing IDs |
|---|---|---|---|
| | | | |

## Individual scoring sheet (from W6)

| Date | Scorer | Snapshot | Question | Correct | Cited | Complete | Honest | Verdict (pass/fail) | Note |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |
