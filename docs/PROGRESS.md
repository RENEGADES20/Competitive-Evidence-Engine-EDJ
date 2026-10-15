# Progress

**Do not edit the Status log by hand.** Write one line in your PR description under
`## Progress line` (`What landed | Blockers | Next`). When the tech lead merges the PR,
`.github/workflows/progress.yml` appends it to your role's table below (role = branch
prefix, e.g. `c1/...`). Only merged work appears here, and PRs never conflict on this file.

## Status log

### C1

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-15 | Core-five CIKs verified on EDGAR (MS, SCHW, BAC, RJF, MER/MLPF&S); Merrill Edge placement in BAC Consumer Banking confirmed from BAC-10K-2024 (#1) (#20) | Question-bank review with project lead pending | C1 holds the review; change requests as append-only PRs |
| 2026-10-15 | Expansion eleven mapped with reporting shape (`docs/EXPANSION.md`); source registry data for core entities (`config/source_registry.csv`, 49 rows); RJF `monthly` added (#2) (#21) | CSV not yet loaded into the `source_registry` table (needs TL-owned `load.py`); IR URLs and ADV CRDs TODO-verify | TL decides who writes the loader |

### C2

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-15 | Source feasibility matrix, tiers 3-4 (#3): `docs/source_matrix.csv` (100 rows), `docs/SOURCE_MATRIX.md` (terms quoted, questions T-01..T-64 for ADR-000), monthly URL checker `python -m cee.ingest.check_sources` (#19) | Terms answers from ADR-000 (no site explicitly allows our use; no free transcript archive except BAC's own from 1Q26); 57 blocked/error URLs not yet opened by hand; 19 rows with TODO-verify date field | #4: TL review, manual URL check, pick the first transcripts |

### C3

| Date | What landed | Blockers | Next |
|---|---|---|---|

### S1

| Date | What landed | Blockers | Next |
|---|---|---|---|

### S2

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-15 | Prompt v0 and standard gap/boundary wording (#10): `src/cee/answer/prompt.py`, wording table in specs/answer-citations.md (Q12, Q19, Q28-Q30) (#27) | Real-model check of Q28-Q30 waits for BAC/MS documents in the corpus | Code-inserted caveats, boundary sentence and number check (S2, W3+) |

### U1

| Date | What landed | Blockers | Next |
|---|---|---|---|

### TL

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-09-28 | Skeleton docs created | Licensing question open (ADR-000) | Tech lead builds end-to-end skeleton (plans/0001) |
| 2026-09-30 | End-to-end skeleton on TL machine (#13): EDJ 10-K (335 chunks), FTS, Answer JSON + citation check, gap/refuse path, Streamlit source view, build-snapshot/restore, smoke check, 11 tests | ADR-000 still open | Install on the other six machines and Gate 1 (#14) |
| 2026-09-30 | First official snapshot `corpus-2026-09-30` (1 document, 335 chunks) built from main and published to Box `snapshots/`; restore now skips `-test` dumps | Windows Smart App Control once blocked a pandas DLL during build-snapshot (a retry passed) | Teammates restore it during #14 |
| 2026-10-10 | Verification workflow (#22): `verify-cee` skill drives the UI like a user (5 features, screenshots in `.verify-runs/`), wired into `/finish-task` and the PR template; guard hook fixed for macOS; `docs/WORKFLOW-SETUP.md` for teammates | Guard still lets unparsable input through; macOS setup not yet run by a teammate | Teammates run setup and report on #23; next: move ground rules into CI checks |
| 2026-10-10 | Dispatch (#25): `/dispatch` (after a merge, weekly, inbox) drafts the next issues from the real state (merged PRs, open work, dependencies, comments) with checkable acceptance; `scripts/dispatch_apply.py` applies an approved draft; richer issue template | Corpus still one document; ADR-000 open; three PRs waiting for review | TL approves the W4 draft; review #19-#21 |
| 2026-10-15 | PROGRESS is written by a bot from each merged PR's progress line; no more PROGRESS conflicts (#29) | - | Merge #27, #20, #21, #19 through it |
| 2026-10-15 | ADR-007 settles source use (T-01..T-09): all sources allowed, transcripts tier 3, Bloomberg exports tier 1; rule 5 updated (#30) | - | C2 transcripts and IR, C3 thematic ingestion unblocked |

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
