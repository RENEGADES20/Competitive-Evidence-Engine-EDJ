# 0216 - Advisor headcount sources for Morgan Stanley, Schwab and Merrill; new snapshot

Issue: #216    Role: TL    Spec: specs/filings.md (advisor headcount definitions, Q11/Q23);
also specs/transcripts-ir.md (decks, IR pages, press), docs/ARCHITECTURE.md, docs/DECISIONS.md
(ADR-006 snapshots, ADR-007 source use), docs/RUN.md section 4, docs/DASHBOARD.md section 8

## Goal
For Morgan Stanley (MS), Merrill (MER, reported inside BAC's GWIM) and Schwab (SCHW) the corpus
holds a document that states an advisor count, each stored with its own definition and date
(ground rule 4: no inferred headcount), or, where the firm publishes none, a documented search
that lists every source tried. The documents reach a new snapshot built from `main` with
`build-snapshot`, restored with `restore.ps1` and `restore.sh`, with a new mock baseline;
`exp/hybrid` embeds only the new chunks at its next sync. 0 real model calls.

## Facts (read-only, 2026-11-19 05:10, origin/main 0da68fd)
- `main` = 0da68fd (includes #234 strict tools). `data/manifest.csv`: 219 rows. Database `cee`
  = `corpus-2026-11-17` (219 documents, 21,143 chunks); `sync-db.ps1 -Check` exit 0.
  `snapshots/LATEST.json` = `corpus-2026-11-17`, sha256 `47c1ffca...bfae1`.
- Committed baseline `evals/baselines/corpus-2026-11-17/report.json` (code 9358af5, as of
  2026-11-17, app budget, planner on): 29 PASS / 1 FAIL (Q19); Q11 PASS (recall_final 0.4),
  Q23 PASS (0.6), Q24 PASS (0.0). `main` moved since (#229, #231, #234), so step 1 re-runs the
  base on today's code. `docs/RUN.md` section 7 reproduces Gate 4 with that folder.
- Gate 4 (`docs/results/gate4-report.md`): Q11 FAIL, Q23 FAIL (c, b), Q24 PASS; reason "advisor
  headcount for Morgan Stanley, Schwab and Merrill is not in the corpus". Latest real Q23
  (`D:\ALLPROJECTS\EDJ\cache\ev232\real\Q23-224db199870212504b06b77a.json`, prompt v4.1,
  `gap_with_adjacent`) already cites `BAC-DECK-2025-investor-day#9` as adjacent: ">15K Wealth
  Advisors" for Merrill | Private Bank, "a combined count ... at one date ... rounded".
- **Pre-check, 0 downloads (step 1 repeats it with saved evidence).** SQL over `chunks` for
  MS/BAC/MER/SCHW (no trade press), regex for "financial advisors", "wealth advisors",
  "advisors", "financial consultants", "Wealth Management representative(s)", "FAs" within
  ~80 characters of a count (`15,357`, `15K`, `16 thousand`); then the raw PDFs (pypdfium2
  text, not the chunks) of `MS-SUPP-2025Q4`, `MS-SUPP-2026Q3`, `BAC-SUPP-2026Q3`,
  `BAC-DECK-2026Q3`, `MS-DECK-2026-strategic-update`, `SCHW-DECK-2026Q3`,
  `SCHW-DECK-2026-investor-day`, `BAC-DECK-2025-investor-day`, `SCHW-MONTHLY-2026-08`:
  - **MS: none.** Supplements 2025Q4-2026Q3 have no advisor line in the raw PDF either (only
    "Advisor-led client assets" and footnote (f) "accounts that have a Wealth Management
    representative assigned"); 10-K/10-Qs, strategic-update deck and transcripts: no count.
    So chunking did not lose it; MS no longer prints it in these documents.
  - **MER/BAC: one stored count, already chunked.** `BAC-DECK-2025-investor-day` (Investor Day
    2025-11-05) slide 4 (`#9`, page 4, segment GWIM) ">15K Wealth Advisors" under
    "Merrill | Private Bank", and slide 7 (`#13`) ">15K ... Wealth Advisors" (plus ">6K
    Supporting Client Team Members", "2.4K Advisor trainees" on slide 17, `#34`). Notes slide:
    "All data presented as of 3Q25"; no definition of "Wealth Advisors". GWIM-wide (Merrill +
    Private Bank), rounded, one date. `config/metric_definitions.yaml` still says BAC
    `not_disclosed` and does not list it. BAC supplements 2025Q4-2026Q3, decks and releases:
    only "Financial advisory services" (IB fees) and award counts (">300 Merrill advisors on
    Barron's ..."), not headcount.
  - **SCHW: no advisor headcount.** `SCHW-TR-2025Q2#5`/`#33` "16,000 advisors" and investor-day
    slide 10 "16K Schwab independent RIAs" are RIA clients of Advisor Services, not Schwab
    staff. Investor day: "Hired hundreds of new Financial Consultants" (p 52), "33K+
    employees", "400+ branch locations"; no FC/WC count. `SCHW-10K-2025#18` describes Financial
    Consultants, Active Trader FCs and Wealth Consultants without a number.
- Ingestion: TL route (`docs/RUN.md` section 4). Raw files live in Box Drive
  `CORPUS_SHARE_PATH` = `C:\Users\14370\Box\EDJ` (value known from plan 0200; `.env` is not
  read), flat `raw/<doc_id>.<ext>`; `data/raw/` is git-ignored. Parse cache `parsed/` in the
  same folder (keyed by sha256), so the snapshot build re-uses the parse made in step 4.
  `scripts/ingest.ps1 -Doc <id>` / `ingest.sh --doc <id>` loads one manifest row
  (`python -m cee.ingest.load --doc`). `cee.config` reads `DATABASE_URL` from the environment
  first (`load_dotenv` does not override), so a scratch database can be targeted.
- Earlier corpus PRs added hand-written manifest rows (#45 supplements: `MS-SUPP-2025Q4`
  `https://www.morganstanley.com/content/dam/msdotcom/en/about-us-ir/finsup4q2025/finsup4q2025.pdf`,
  `BAC-SUPP-2025Q4` cloudfront PDF "8-K Ex.99.3"; #48 decks; web pages as `<ENT>-PR-web-<slug>`).
  Tiers in use: supplement 3, deck 3, IR web page 3, EDGAR press exhibit 2, transcript 3.
- `build-snapshot` must run on a clean `main` (`-AllowBranch` only names a `...-test` dump that
  must not be shared) and stamps `corpus-<build date>`. So the manifest rows must be on `main`
  before the build: this issue needs **two PRs** (see Steps), an exception to "one issue -> one
  PR" that follows DASHBOARD section 8 (corpus PRs merged first, then a snapshot PR publishing
  `LATEST.json`); this one plan covers both. Box Drive is on C: (12 GB free);
  one dump is a few hundred MB; downloads and evidence go to D:.
- `exp/hybrid` follows `main` through `sync/exp-hybrid-<date>` PRs (last: #233).

## Files to change
PR A (this branch, `tl/216-headcount-sources`, "Part of #216"):
- `plans/0216-headcount-sources.md` - this plan, findings, Progress log.
- `data/manifest.csv` - one row per new document (doc_id, entity_id, doc_type, source_tier,
  published_at, date_basis, period_end, url, storage_path, sha256, added_by=TL, added_at).
- `config/metric_definitions.yaml` - MS, BAC (Merrill) and SCHW `advisor_headcount` entries:
  `quoted` with the firm's own wording, chunk_id, valid_from, includes/excludes/not_stated,
  or `not_disclosed` with `looked_in` extended by every source tried (incl. web/EDGAR searches
  as quoted strings). The stored `BAC-DECK-2025-investor-day#9` is added either way.
- `specs/filings.md` - the "Advisor headcount and NNA definitions" table rows for MS, SCHW, BAC.
- `config/source_registry.csv` - only the `url_pattern` of rows this issue actually used and
  verified (MS/BAC supplement, SCHW monthly/deck), replacing `TODO-verify`; nothing else.

PR B (branch `tl/216-snapshot-<SNAP>` from `main` after PR A is merged, "Closes #216"):
- `snapshots/LATEST.json` - from the build.
- `evals/baselines/<SNAP>/report.json`, `report.md` - new mock baseline. **Kept:**
  `evals/baselines/corpus-2026-11-17/` (Gate 4 record; `docs/RUN.md` section 7 reproduces Gate 4
  with it), a deliberate exception to "one folder at a time", said in the PR.
- `README.md` - Status section only (snapshot name, counts, retrieval check line).
- `plans/0216-headcount-sources.md` - Progress log, PR B findings.

Never in a diff: raw files, `data/raw/`, `*.dump`, `.env`. No code, retrieval, prompt, question
bank or answer-key change (`evals/expected_chunks.yaml` stays; the "retrieves the new chunks"
check reads `chunk_ids` in `report.json`). No new script pair (scratch scripts live in `EV`).

## Steps
`EV` = `D:\ALLPROJECTS\EDJ\cache\ev216` (logs, reports, scratch scripts, downloads under
`EV\dl\<doc_id>\`, one empty folder per file). `PY` = `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe`.
Environment for every step (mock, vectors off, temp and model caches on D:):
```powershell
$env:PYTHONUTF8="1"; $env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; $env:HF_HOME="D:\ALLPROJECTS\EDJ\cache\hf"; $env:LLM_PROVIDER="mock"; Remove-Item Env:CEE_VECTORS,Env:PYTHONPATH,Env:DATABASE_URL -ErrorAction SilentlyContinue
```
```bash
export PYTHONUTF8=1 LLM_PROVIDER=mock HF_HOME=/d/ALLPROJECTS/EDJ/cache/hf; unset CEE_VECTORS PYTHONPATH DATABASE_URL
```
`ASOF` = 2026-11-17 for every eval (same as the committed baseline and Gate 4, so only the
corpus differs).

### PR A - documents, manifest, definitions
1. **Stored-corpus check (0 downloads), with evidence.** Scratch `EV\stored.sql` (the regex
   above, per firm and doc_type, trade excluded) -> `EV\stored.txt`; scratch `EV\pdfgrep.py`
   (pypdfium2, run with `PY -I`) over every MS/BAC/SCHW supplement, deck and monthly PDF in Box
   `raw/` -> `EV\rawgrep.txt`. Expected = the pre-check above. A count found in a raw PDF but in
   no chunk = a chunking loss: record page and text, report to the TL as a C1/C2 parse issue
   (the parse is not fixed here), and still count it as "stored" only if a chunk carries it.
2. **Find sources, in this order per firm; stop at the first that states a count for the
   window 2024Q4-2026Q3 (Q23's eight quarters).** Every try (URL, date, result: count found /
   no count / blocked) goes into `EV\sources-tried.md` and later into the plan and `looked_in`.
   Polite access (ADR-007 T-08): EDGAR with the `EDGAR_IDENTITY` user agent read through
   `cee.config.settings()` in the scratch script (never printed), 1 s between requests per host;
   IR sites by script or by hand in the browser; Wayback copy when a site blocks scripts.
   a. **EDGAR full-text search** (covers 8-K exhibits, i.e. supplements and releases, plus
      10-K/10-Q), 2023-01-01 to today:
      `https://efts.sec.gov/LATEST/search-index?q="<phrase>"&ciks=<CIK>&forms=8-K,10-K,10-Q&dateRange=custom&startdt=2023-01-01&enddt=2026-11-19`
      (UI: `https://www.sec.gov/edgar/search/#/q=...`), CIKs from `config/source_registry.csv`
      (MS 895421, BAC 70858, SCHW 316709). Phrases: MS "financial advisors", "Wealth
      Management representatives", "Financial Advisors"; BAC "financial advisors", "wealth
      advisors", "Merrill advisors"; SCHW "financial consultants", "Wealth Consultants". Open
      each hit's exhibit and keep it only if a number sits on the advisor line.
   b. **Quarterly financial supplements** (T-03: EDGAR copy if the supplement is an 8-K exhibit,
      else the IR PDF):
      - MS: `https://www.morganstanley.com/content/dam/msdotcom/en/about-us-ir/finsup<q>q<yyyy>/finsup<q>q<yyyy>.pdf`
        for 4Q2024, then 4Q2023 (from IR page `https://www.morganstanley.com/about-us-ir/earnings-releases`),
        Wealth Management metrics page: "Financial advisors" / "Wealth Management representatives".
      - BAC: `https://investor.bankofamerica.com/quarterly-earnings` "Supplemental Information"
        (or the 8-K Ex.99.3 on EDGAR) for 4Q2024, then 4Q2023, GWIM key indicators page:
        "Financial advisors", "Total wealth advisors, including financial advisors".
      - SCHW: no supplement with headcount (`config/source_registry.csv` row is TODO-verify);
        check the latest quarterly earnings deck and 10-K "Human Capital" for an FC/WC count.
   c. **Firm fact pages and investor-day/business-update decks** (tier 3; `published_at` per
      T-09, `date_basis = retrieved` only if no date exists):
      MS `https://www.morganstanley.com/about-us` and the Wealth Management pages
      (`https://www.morganstanley.com/what-we-do/wealth-management`); Merrill
      `https://www.ml.com/about-merrill.html` and the BAC newsroom
      (`https://newsroom.bankofamerica.com`, search "financial advisors"); Schwab
      `https://www.aboutschwab.com/financial-reports`, `https://www.aboutschwab.com/` (company
      facts) and the 2024 Investor Day deck (aboutschwab.com, `SCHW-DECK-2024-investor-day`).
   d. **Wayback Machine** (`https://web.archive.org/web/2026*/<url>`) for any of a-c that blocks.
   e. Not tried: tier 1 licensed data (no Bloomberg/Capital IQ export in hand); trade press
      (tier 4, Q11/Q23 need firm sources; NEXT item 6 owns press ingestion).
   **Selection rules.** A document is added only if it states a count (or, for SCHW, if it is
   the firm's own statement that is the closest published figure, e.g. "16K independent
   RIAs" is **not** added as headcount). At most: MS and BAC supplements for the quarters that
   carry the line inside the window; if the line stops before 2024Q4, only the **last**
   supplement that prints it (to document the definition and the break, not to fill the
   series). Each figure keeps its own label (MS "Financial advisors" vs "Wealth Management
   representatives"; BAC "financial advisors" vs "wealth advisors", GWIM vs Merrill); no
   figure is derived from another. Cap: about 12 new documents; more needs a TL note.
   Downloads: `EV\dl\<doc_id>\<doc_id>.<ext>`, sha256 recorded, text checked with
   `EV\pdfgrep.py` (or html text) before anything else.
3. **Manifest rows and Box.** doc_ids by the existing convention (`MS-SUPP-2024Q4`,
   `BAC-SUPP-2024Q4`, `SCHW-DECK-2024-investor-day`, `MER-PR-web-<slug>`, ...); tier as the
   same doc_type already uses (supplement 3, deck 3, IR web page 3, EDGAR exhibit press 2);
   `published_at` from the source (8-K filing date or printed date; T-09 order); `date_basis`;
   `period_end`; url (+ "(fetched via web.archive.org ...)" when so); `added_by` TL,
   `added_at` the day. Copy each file to `C:\Users\14370\Box\EDJ\raw\<doc_id>.<ext>`
   (TL route, flat). Checks: `PY -c "from cee.ingest.manifest import check_files, read_manifest; print(len(check_files(read_manifest())), 'files OK')"`
   -> 219 + N; 0 rows with empty `published_at`; `PY scripts/check_dates.py --today 2026-11-19 --skip-missing`
   for new deck/press rows -> date source named, no mismatch.
4. **Scratch load (DB `cee_216`; `cee` stays `corpus-2026-11-17`).**
   `docker exec cee-db createdb -U cee cee_216`; `pg_restore` `/snapshots/corpus-2026-11-17.dump`
   into it; `$env:DATABASE_URL="postgresql://cee:cee@localhost:5432/cee_216"`; for each new
   doc `powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1 -Doc <doc_id>` (Mac:
   `DATABASE_URL=... bash scripts/ingest.sh --doc <doc_id>`). New PDFs are parsed by docling
   once here (cache written to Box `parsed/`). Checks: `PY -m cee.smoke` PASS on `cee_216`;
   documents = 219 + N, every new doc has chunks; for each firm the chunk(s) holding the count:
   chunk_id, page, section, segment (BAC/MER chunks with GWIM text -> `GWIM`), and the count
   and its label in one chunk (not split from its label). If a count is split away from its
   label by chunking: report it (C1 parse issue); not fixed here.
5. **Definitions.** Update `config/metric_definitions.yaml` (MS, SCHW, BAC entries) and the
   `specs/filings.md` table from the chunks of step 4 and the stored
   `BAC-DECK-2025-investor-day#9`: verbatim quote, chunk_id, valid_from, includes/excludes/
   not_stated (GWIM = Merrill + Private Bank; rounded ">15K"; as of 3Q25), the break where a
   label changes; `not_disclosed` + full `looked_in` for a firm with no count (expected SCHW).
   `PY -m pytest -q tests/test_metric_definitions.py` with `DATABASE_URL` = `cee_216` -> pass
   (quote verbatim in chunk); `PY -m pytest -q` (cee) -> all pass, count >= today's floor
   (run once on 0da68fd first and recorded).
6. **Mock eval, same code, both corpora.**
   - Base: `PY scripts/eval_run.py --as-of 2026-11-17 --out EV/base` on `cee` (`corpus-2026-11-17`,
     no `DATABASE_URL`).
   - New: with `DATABASE_URL` = `cee_216`: `PY scripts/eval_run.py --as-of 2026-11-17 --baseline EV/base/report.json --out EV/new`.
   - Scratch `EV\compare.py` -> `EV\compare.txt`: for Q11, Q23, Q24 the new count chunk_ids
     (step 4) that are in `chunk_ids`; for the other 27 questions per-question
     `recall_final` (and `doc_recall`, status) new vs base.
   - **Stop rule:** any PASS -> FAIL, any of the 27 with lower `recall_final`, a forbidden hit,
     or refusal accuracy below base -> stop, classify (crowd-out by a new document, or other),
     report to the TL; no retrieval change in this issue. A new count chunk not retrieved for
     Q11/Q23/Q24 -> record rank/pool (`recall_pool`) and report; the acceptance item stays open.
7. **PR A.** `git diff --name-only origin/main...HEAD` = the PR A files only; no `data/raw/`,
   `*.dump`. Commit, push, `/finish-task` (PR "Part of #216", Verification: 0 real calls,
   evidence `EV`), `gh pr checks <PR#> --watch` -> all green; reviewed and merged via
   `/tl-review`. `cee_216` dropped after merge.

### PR B - snapshot (after PR A is merged)
8. **Build** in `D:\ALLPROJECTS\EDJ\repo` on `main` (clean, `git pull --ff-only`, HEAD =
   origin/main recorded; no other session uses `cee`; `docker compose down -v` is not run).
   DASHBOARD 8 pre-checks (manifest `published_at`, sha256 via the build's 1/7). Notes (no
   links): "<219+N> documents, N more than corpus-2026-11-17: advisor headcount sources for
   Morgan Stanley, Merrill and Schwab (#216). Code since: planner (#214), part gaps (#215),
   answer v4.1 (#230), strict tools (#232)."
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "<notes>" *> D:\ALLPROJECTS\EDJ\cache\ev216\build.log
   ```
   ```bash
   bash scripts/build-snapshot.sh --notes "<notes>" 2>&1 | tee /d/ALLPROJECTS/EDJ/cache/ev216/build.log
   ```
   `SNAP` = the name it stamps: `corpus-2026-11-19` if built on 2026-11-19 (local date), else
   that day's date; announced as is (renaming would break the sha256 in `LATEST.json`).
   Log: `<219+N> files OK`; `parsing with docling|edgartools` -> no match (parse cache from
   step 4); `4/7 Embedding skipped`; `Dumping SNAP.dump`; `Copying to Box`.
9. **Snapshot checks** (DB `cee` = `SNAP`): `obj_description('documents'::regclass)` = `SNAP`;
   documents = manifest doc_ids (219 + N); chunks = 21,143 + new chunks of step 4; every chunk
   of the 219 old documents identical to `corpus-2026-11-17` (md5 over chunk_id, segment,
   section, page, prefix, text vs a scratch restore `cee_prev_216` of the local
   `corpus-2026-11-17.dump`, sha256 checked against main's old `LATEST.json`, dropped after);
   new chunks = those of `cee_216`. sha256 Box dump = local dump = `LATEST.json`;
   `pg_restore --list` exit 0. `PY scripts/page_sweep.py` -> `MISPLACED 0` on every line.
10. **Restore + smoke, both scripts** (each replaces `cee` with the same dump; `cee_84`,
    `cee_84_rev` untouched):
    `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 C:\Users\14370\Box\EDJ\snapshots\SNAP.dump`
    then `PY -m cee.smoke` -> PASS; Git Bash
    `bash scripts/restore.sh /c/Users/14370/Box/EDJ/snapshots/SNAP.dump` then
    `.venv/Scripts/python.exe -m cee.smoke` -> PASS (on a Mac: `bash scripts/restore.sh`,
    `.venv/bin/python -m cee.smoke`). `sync-db.ps1 -Check` and `bash scripts/sync-db.sh --check`
    -> exit 0 "up to date: SNAP". `PY scripts/verify_cee.py doctor` -> DOCTOR PASS.
11. **Baseline on `SNAP`**: `PY scripts/eval_run.py --as-of 2026-11-17 --out EV/snap` (no
    `--baseline`, committed file carries no local path); `... --baseline EV/base/report.json --out EV/snap-vs`;
    rerun `--baseline EV/snap/report.json --out EV/snap-rerun` -> 30 UNCHANGED. Same checks as
    step 6 (Q11/Q23/Q24 retrieve the count chunks; other 27: 0 PASS -> FAIL, `recall_final`
    not lower; 0 forbidden; refusal accuracy >= base). `EV\snap` and `EV\new` agree (same
    corpus content). Copy to `evals/baselines/SNAP/`.
12. **verify-cee**: `PY scripts/verify_cee.py run` on `SNAP` -> VERIFY PASS (one re-run on a
    clearly environmental failure). `PY -m pytest -q` -> all pass.
13. **Publish**: branch `tl/216-snapshot-SNAP` from `main`; `LATEST.json` from the build;
    `evals/baselines/SNAP/`; README Status; plan Progress log; in `repo` `git restore
    snapshots/LATEST.json` on `main` if the build left it modified. PR "Closes #216",
    `gh pr checks <PR#> --watch` -> green, `/tl-review`, merge = sync note; one chat line for
    the TL: "New snapshot SNAP: run /sync-db".
14. **exp/hybrid** (not in these PRs): the next `sync/exp-hybrid-<date>` PR merges `main` and,
    after `/sync-db` to `SNAP`, runs `python -m cee.retrieve.embed --missing`, which embeds only
    the new chunks (the old 21,143 keep their vectors). Recorded on #216 as a hand-off comment.

**Paid calls: 0.** Data issue; everything runs on the mock provider.

## Acceptance
- [ ] **MS, MER, SCHW each:** a stored chunk that states an advisor count with its own
      definition/label and date (chunk_id, quote in `config/metric_definitions.yaml`), or a
      documented search that found none (`looked_in` + `EV\sources-tried.md` + plan findings
      list every source tried). Check: step 4 query prints the chunk per firm; `pytest
      tests/test_metric_definitions.py` passes against the database holding the chunks.
- [ ] Stored-corpus check done before any download (`EV\stored.txt`, `EV\rawgrep.txt`); any
      chunking loss reported.
- [ ] Each new manifest row: source url, tier, `published_at`, `date_basis`, sha256; manifest
      check `219+N files OK`; 0 empty `published_at`; no inferred or derived figure anywhere.
- [ ] Mock (step 6 and again on `SNAP`, step 11): Q11, Q23, Q24 `chunk_ids` contain the new
      count chunks (per firm with a count); the other 27 questions: `recall_final` not lower
      than base, 0 PASS -> FAIL, 0 forbidden, refusal accuracy >= base; rerun 30 UNCHANGED.
- [ ] Snapshot `SNAP` built on clean `main` with `build-snapshot`; log checks pass; documents
      and chunk counts as expected; old chunks identical; sha256 Box = local = `LATEST.json`.
- [ ] `restore.ps1` + smoke PASS and `restore.sh` + smoke PASS; both `sync-db` checks
      "up to date: SNAP"; DOCTOR PASS; VERIFY PASS; `pytest -q` all pass.
- [ ] New baseline `evals/baselines/SNAP/` committed; `corpus-2026-11-17/` kept (Gate 4).
- [ ] `git diff --name-only origin/main...HEAD` of PR A and PR B: no `data/raw/`, no `*.dump`.
- [ ] `gh pr checks` green on PR A and PR B.
- [ ] exp/hybrid `embed --missing` hand-off noted on #216 (done at the next sync).
- [ ] 0 real model calls (stated in both PRs).

## Progress log
- 2026-11-19 05:10 - plan written on `tl/216-headcount-sources` from origin/main 0da68fd.
  Read-only pre-check done (Facts): MS no count stored or in raw supplements; Merrill only the
  GWIM-wide ">15K Wealth Advisors" (investor day, as of 3Q25), already chunked and retrieved
  by Q23 but missing from `metric_definitions.yaml`; Schwab no staff advisor count ("16K" are
  independent RIAs). Two PRs needed because `build-snapshot` runs on `main` only. No file other
  than this plan changed. Not reviewed yet.
