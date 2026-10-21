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
| 2026-10-16 | 10-K and four 10-Qs for all five filers stored (24 rows, 11,977 chunks loaded) (#69) | Q30 needs #37 GWIM tags; BAC/MS/SCHW sections not split (chunk.py Item regex) | #44 snapshot with the new corpus; #37; #45 |
| 2026-10-16 | C1: BAC, SCHW and MS 10-K/10-Q chunks now split into Item sections (MS via its cross-reference table of contents); EDJ/RJF chunk IDs unchanged (#70) (#71) | Blockers: none | Next: GWIM segment tagging inside BAC Item 7 / 10-Q Item 2 (#37) |
| 2026-10-18 | 8 quarterly supplements (BAC, MS Q1-Q3 2026; RJF two quarters) stored with page numbers; PDF tables and picture-nested slide text now kept (pdf.py) (#77) | SCHW supplement/monthly missing; Q23 ranks only BAC supplements (#59); docling adds ~4-7 min per PDF to rebuilds | #46 metric definitions from these supplements; snapshot rebuild |

### C2

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-15 | Source feasibility matrix, tiers 3-4 (#3): `docs/source_matrix.csv` (100 rows), `docs/SOURCE_MATRIX.md` (terms quoted, questions T-01..T-64 for ADR-000), monthly URL checker `python -m cee.ingest.check_sources` (#19) | Terms answers from ADR-000 (no site explicitly allows our use; no free transcript archive except BAC's own from 1Q26); 57 blocked/error URLs not yet opened by hand; 19 rows with TODO-verify date field | #4: TL review, manual URL check, pick the first transcripts |
| 2026-10-18 | 11 earnings-call transcripts (BAC, MS, SCHW Q1-Q3 2026; RJF two quarters) stored as text with speakers, 535 chunks (#76) | Transcripts rank below 10-K/10-Q chunks in top-8 (#59); 8-quarter backfill (#47) | #45 supplements and #48 decks from the same package; #38 releases via EDGAR |
| 2026-10-18 | 8 quarterly earnings presentations (BAC, SCHW Q1-Q3 2026; RJF two quarters) stored with page numbers (#78) | Investor-day decks and Merrill press (MER) still open; decks rank below 10-Ks (#59) | #48 investor-day decks; #38 releases via EDGAR |
| 2026-10-18 | C2 #38: 16 quarterly earnings releases (8-K EX-99.1; MS, SCHW, BAC, RJF x 4 quarters) in the manifest via `cee.ingest.releases` (#75) | Q26 still ranks the in-window RJF release 106th until the S1 time window and #59 quotas land | TL moves the 16 raw files into Box `raw/` and rebuilds the snapshot; unblocks #44 and #49 |

### C3

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-16 | Topics taxonomy v0 (#6): 19 topics covering Q16-Q21 with definitions, keywords and tagging rules in config/topics.yaml (#65) | C1 review pending | C3 builds keyword tagging (tag_topics) and starts thematic ingestion |
| 2026-10-21 | #5 tier 5 source matrix: 39 thematic sources (research/survey/regulatory), all 8 themes with >= 2 publishers, Cerulli via free white papers (no WashU subscription) (#92) | Blockers: none | Next: #81 ingest institutional research from these rows |

### S1

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-16 | Synonym list v0 drafted in config/entities.yaml; spec open questions posted on #7 (#66) | Firm-specific metric wording unverified (only EDJ in local corpus) | Wire expand_synonyms() into fts.py (W3) |
| 2026-10-18 | #50 footer and gap box now name the same firms (Query.firms; Vanguard shows "VGD (no documents)") (#74) | none | U1 may restyle the footer marker; mode for unmapped-only questions stays "theme" per spec |
| 2026-10-20 | S1: hand-written expected results for Q1, Q4, Q11, Q22, Q26 (83 chunk IDs, trap Q4 must-not list, Q26 window) (#87) | Merrill filter returns nothing until GWIM segment tags (#37) | Next: time window in Query (Q26), map "each of the five" (Q11, Q22) |
| 2026-10-21 | Synonyms from config expand search (phrases, exact-case acronyms, 2x match bonus); "the five" resolves to MS, SCHW, EDJ, MER, RJF in SQL; Q22 NNA from 3 of 5 (#89, part) (#94) | Q11 table chunks (EDJ-10K-2025#130, RJF-10K-2025#227) not in top-20: needs table-aware ranking | #49 time windows, then #59 quotas |

### S2

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-15 | Prompt v0 and standard gap/boundary wording (#10): `src/cee/answer/prompt.py`, wording table in specs/answer-citations.md (Q12, Q19, Q28-Q30) (#27) | Real-model check of Q28-Q30 waits for BAC/MS documents in the corpus | Code-inserted caveats, boundary sentence and number check (S2, W3+) |

### U1

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-16 | U1 design language and page shell: theme, components, Ask/Coverage/Design nav, placeholders, snapshot footer, DESIGN.md (#68) | none | #42 citation chips on real answers, #41 coverage table |

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
| 2026-10-15 | EDGAR fetch: quarter-aware 10-Q IDs, `--count N`, skips documents already in the manifest; `source_registry` (49 rows) loaded by `cee.ingest.load` (#32) | - | C1 ingests 10-Ks and 10-Qs; S2 can use registry rows for suggested_source |
| 2026-10-15 | Paid API rule in CLAUDE.md (mock by default, plan and cap real calls, save outputs, no loops, report count); dispatch keeps UI design open and queues several weeks (#34) | - | W4-W6 issues |
| 2026-10-15 | Dispatch applied W4-W6: 29 issues (#35-#63) with board fields and blocked-by links; apply now survives the board's auto-add (#64) | - | Teammates start W4 issues |
| 2026-10-16 | #72 restore.ps1 now works on the first run after a fresh volume (healthcheck over TCP waits for the real Postgres server) (#73) | none | #44 checklist restore test can be re-run |
| 2026-10-17 | Specs for Ask progress trace and institutional research (#79) | none | U1 and C3 issues via dispatch |
| 2026-10-18 | Corpus line re-planned after TL ingestion: TEAM.md W4-W7 for C1/C2/C3/TL, intake rule, new TL issues #82-#84 (#85) | none | C1 #37, C2 #47, C3 #81 |
| 2026-10-19 | #82 parse cache: docling and edgartools output stored in Box parsed/ by sha256 + version; warm full load 10.5 s (was ~50 min), build-snapshot 15 s, chunks identical (#86) | none | build the next snapshot with C2's earnings releases (#75); bump PARSER_VERSION in #84 |
| 2026-10-20 | date_basis (source (#88) | retrieved) in the manifest and documents; existing databases gain the column on load; all 68 documents source | none / #49 (S1) time windows can exclude retrieved-dated pages |
| 2026-10-20 | verify-cee waits for the finished page (answer meta line, source page text) instead of network idle; 5 of 5 runs PASS on the 68-document corpus (#91) | none | merge #90 (eval runner), then Gate 2 (#54) |
| 2026-10-20 | Eval runner: per-question pattern hits, coverage, forbidden hits and status for all 30 questions, baseline compare, capped and cached real-model mode; corpus-2026-10-18 mock: PASS 7, FAIL 21, N/E 2 (#90) | verify-cee flaky on the 68-document corpus (#83) | #60 hit-rate report, #54 Gate 2, #15 weekly X/30 |

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
