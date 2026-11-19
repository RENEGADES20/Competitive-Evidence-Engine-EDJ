# 0216 - Advisor headcount sources for Morgan Stanley, Schwab and Merrill; new snapshot

Issue: #216    Role: TL    Spec: specs/filings.md (advisor headcount definitions, Form ADV,
Q11/Q23); also specs/transcripts-ir.md (decks, IR pages, press), docs/ARCHITECTURE.md,
docs/DECISIONS.md (ADR-006 snapshots, ADR-007 source use), docs/RUN.md sections 4 and 7,
docs/DASHBOARD.md section 8

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
  `snapshots/LATEST.json` = `corpus-2026-11-17`, sha256 `47c1ffca...bfae1`. Dumps are about
  5 MB each (`corpus-2026-11-17.dump` 5,157,162 bytes); Box Drive is on C: (12 GB free).
- Committed baseline `evals/baselines/corpus-2026-11-17/report.json` (code 9358af5, as of
  2026-11-17, app budget, planner on): 29 PASS / 1 FAIL (Q19); Q11 PASS (recall_final 0.4),
  Q23 PASS (0.6), Q24 PASS (0.0). `main` moved since (#229, #231, #234), so step 1 re-runs the
  base on today's code. `docs/RUN.md` section 7 says "The final snapshot is
  `corpus-2026-11-17`" and runs its free check and the Gate 4 reproduction on whatever `cee`
  holds, against that baseline folder.
- Gate 4 (`docs/results/gate4-report.md`): Q11 FAIL, Q23 FAIL (c, b), Q24 PASS; reason "advisor
  headcount for Morgan Stanley, Schwab and Merrill is not in the corpus". The latest real Q23
  (`D:\ALLPROJECTS\EDJ\cache\ev232\real\Q23-224db199870212504b06b77a.json`, prompt v4.1,
  `gap_with_adjacent`) cites `BAC-DECK-2025-investor-day#9` as adjacent: ">15K Wealth Advisors"
  for Merrill | Private Bank, "a combined count ... at one date ... rounded". In the **mock**
  baseline, Q11 and Q24 retrieve `#9`, Q23 does not (only `#8`).
- **Pre-check, 0 downloads (step 1 repeats it with saved evidence).** SQL over `chunks` for
  MS/BAC/MER/SCHW (no trade press), regex for "financial advisors", "wealth advisors",
  "advisors", "financial consultants", "Wealth Management representative(s)", "FAs" within
  ~80 characters of a count (`15,357`, `15K`, `16 thousand`); then the raw PDFs (pypdfium2
  text, not the chunks) of `MS-SUPP-2025Q4`, `MS-SUPP-2026Q3`, `BAC-SUPP-2026Q3`,
  `BAC-DECK-2026Q3`, `MS-DECK-2026-strategic-update`, `SCHW-DECK-2026Q3`,
  `SCHW-DECK-2026-investor-day`, `BAC-DECK-2025-investor-day`, `SCHW-MONTHLY-2026-08`:
  - **MS: none.** Supplements 2025Q4-2026Q3 have no advisor line in the raw PDF either (only
    "Advisor-led client assets" and footnote (f) "accounts that have a Wealth Management
    representative assigned"); 10-K/10-Qs, strategic-update deck, transcripts and the Part 2A
    brochure (`MS-ADV-2026#153`/`#187`, no number): no count. Chunking did not lose it.
  - **MER/BAC: one stored count, already chunked.** `BAC-DECK-2025-investor-day` (Investor Day
    2025-11-05) slide 4 (`#9`, page 4, segment GWIM) ">15K Wealth Advisors" under
    "Merrill | Private Bank", and slide 7 (`#13`, page 7, **segment NULL**, so the Merrill
    filter drops it) ">15K >6K ... Wealth Advisors ... Supporting Client Team Members";
    "2.4K Advisor trainees" on slide 17 (`#34`). Notes slide: "All data presented as of 3Q25";
    no definition of "Wealth Advisors". GWIM-wide (Merrill + Private Bank), rounded, one date.
    `config/metric_definitions.yaml` still says BAC `not_disclosed` and does not list it. BAC
    supplements, decks and releases: only "Financial advisory services" (IB fees) and award
    counts (">300 Merrill advisors on Barron's 2026 Top 1,500 Financial Advisors").
  - **SCHW: no staff advisor count.** `SCHW-TR-2025Q2#5`/`#33` "16,000 advisors",
    `SCHW-TR-2025Q3#13` "16,000 RIA firms", investor-day "16K Schwab independent RIAs" / "16K
    Advisory Firms" are RIA clients. Investor day: "Hired hundreds of new Financial
    Consultants", "33K+ employees", "400+ branch locations"; no FC/WC count.
    `SCHW-10K-2025#18` describes FCs, Active Trader FCs and Wealth Consultants without a number.
- Form ADV: only Part 2A brochures are stored (`EDJ/MS/SCHW/MER/RJF-ADV-2026`, tier 2,
  doc_type `adv`). Part 1A (Item 5: employees, of them performing investment advisory
  functions, registered representatives of a broker-dealer) is not stored. CRDs are verified
  in `config/entities.yaml` (#55): MS Morgan Stanley Smith Barney LLC 149777, Merrill Lynch,
  Pierce, Fenner & Smith 7691, Charles Schwab & Co., Inc. 5393. `src/cee/retrieve/fts.py`
  `doc_type_scope` (#179, ADR-015) searches `adv` only for fee/pricing questions, so an `adv`
  chunk is **not** retrieved for Q11/Q23/Q24.
- `tests/test_metric_definitions.py`: exactly one entry per (entity, metric) for EDJ, MS, SCHW,
  BAC, RJF (Merrill lives in the BAC entry); a non-`not_disclosed` headcount entry needs
  `quote`, `chunk_id`, `includes`, `excludes`; every `chunk_id`/`see_also` must exist in the
  database `DATABASE_URL` points at (skipped only if it is down or none exist) and the quote
  must be verbatim. CI (`.github/workflows/tests.yml`) has no database, so CI skips that test.
- Ingestion: TL route (`docs/RUN.md` section 4). Raw files live in Box Drive
  `CORPUS_SHARE_PATH` = `C:\Users\14370\Box\EDJ` (value known from plan 0200; `.env` is not
  read), flat `raw/<doc_id>.<ext>`; `data/raw/` is git-ignored. Parse cache `parsed/` in the
  same folder (keyed by sha256), so the snapshot build re-uses the parse made in step 4.
  `scripts/ingest.ps1 -Doc <id>` / `ingest.sh --doc <id>` runs `python -m cee.ingest.load --doc`;
  `cee.config` reads `DATABASE_URL` from the environment first (`load_dotenv` does not
  override), but the scripts' "Row counts" line always reads `cee`.
- Earlier corpus PRs added hand-written manifest rows (#45 supplements: `MS-SUPP-2025Q4`
  `https://www.morganstanley.com/content/dam/msdotcom/en/about-us-ir/finsup4q2025/finsup4q2025.pdf`,
  `BAC-SUPP-2025Q4` cloudfront PDF "8-K Ex.99.3"; #48 decks; web pages as `<ENT>-PR-web-<slug>`;
  #55 brochures). Tiers in use: supplement 3, deck 3, IR web page 3, EDGAR press exhibit 2,
  Form ADV 2, transcript 3.
- `build-snapshot` must run on a clean `main` (`-AllowBranch` only names a `...-test` dump that
  must not be shared) and stamps `corpus-<build date>`. So the manifest rows must be on `main`
  before the build: this issue needs **two PRs**, an exception to "one issue -> one PR" that
  follows DASHBOARD section 8 (corpus PRs merged first, then a snapshot PR publishing
  `LATEST.json`); this one plan covers both.
- `exp/hybrid` follows `main` through `sync/exp-hybrid-<date>` PRs (last: #233).

## Files to change
PR A (this branch, `tl/216-headcount-sources`, "Part of #216"; or "Closes #216" in the N = 0
case, see step 7):
- `plans/0216-headcount-sources.md` - this plan, findings, Progress log.
- `data/manifest.csv` - one row per new document (doc_id, entity_id, doc_type, source_tier,
  published_at, date_basis, period_end, url, storage_path, sha256, added_by=TL, added_at).
  Owner review waived, TL decision 2026-11-17 (#187).
- `config/metric_definitions.yaml` - **only chunk_ids that exist in `corpus-2026-11-17`**
  (blocking 1, option a): the BAC entry quotes `BAC-DECK-2025-investor-day#9`; MS and SCHW
  `looked_in` list every source tried (new doc_ids and searches as quoted strings; text, not
  chunk_ids). Entries that quote a new chunk wait for PR B. Owner review waived, TL decision
  2026-11-17 (#187).
- `specs/filings.md` - the advisor-headcount table rows for MS, SCHW, BAC, with the same rule
  (only chunks in `corpus-2026-11-17`). Owner review waived, TL decision 2026-11-17 (#187).
- `config/source_registry.csv` - only the `url_pattern` of rows this issue actually used and
  verified (MS/BAC supplement, SCHW monthly/deck, Form ADV Part 1A), replacing `TODO-verify`;
  nothing else. Owner review waived, TL decision 2026-11-17 (#187).

PR B (branch `tl/216-snapshot-<SNAP>` from `main` after PR A is merged, "Closes #216"):
- `snapshots/LATEST.json` - from the build.
- `evals/baselines/<SNAP>/report.json`, `report.md` - new mock baseline. **Kept:**
  `evals/baselines/corpus-2026-11-17/` (Gate 4 record, used by RUN.md section 7's Gate 4
  reproduction after a restore), a deliberate exception to "one folder at a time".
- `config/metric_definitions.yaml`, `specs/filings.md` - the entries that quote new chunks
  (now in SNAP): quote, chunk_id, valid_from, includes/excludes/not_stated, `see_also`.
  Owner review waived, TL decision 2026-11-17 (#187).
- `docs/RUN.md` - section 7 only: SNAP is the current snapshot; Gate 4 was scored on
  `corpus-2026-11-17`; the free check points at `evals/baselines/<SNAP>/` with its expected
  result; before the Gate 4 commands a restore of the old dump (both blocks) and `/sync-db`
  back to SNAP afterwards.
- `README.md` - Status section only (snapshot name, counts, retrieval check line).
- `plans/0216-headcount-sources.md` - Progress log, PR B findings.

Never in a diff: raw files, `data/raw/`, `*.dump`, `.env`. No code, retrieval, prompt, question
bank or answer-key change (`evals/expected_chunks.yaml` stays; the "retrieves the new chunks"
check reads `chunk_ids` in `report.json`). No new script pair (scratch scripts live in `EV`).

## Steps
`EV` = `D:\ALLPROJECTS\EDJ\cache\ev216` (logs, reports, scratch scripts, downloads under
`EV\dl\<doc_id>\`, one empty folder per file). Run from the repo folder. Environment (mock,
vectors off, temp and model caches on D:):
```powershell
$PY = "D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe"; $env:PYTHONUTF8="1"; $env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; $env:HF_HOME="D:\ALLPROJECTS\EDJ\cache\hf"; $env:LLM_PROVIDER="mock"; Remove-Item Env:CEE_VECTORS,Env:PYTHONPATH,Env:DATABASE_URL -ErrorAction SilentlyContinue
```
```bash
# macOS (Windows Git Bash: PY=.venv/Scripts/python.exe, HF_HOME=/d/ALLPROJECTS/EDJ/cache/hf)
PY=.venv/bin/python; export PYTHONUTF8=1 LLM_PROVIDER=mock HF_HOME="$HOME/.cache/huggingface"; unset CEE_VECTORS PYTHONPATH DATABASE_URL
```
Scratch database on/off (steps 4-7):
```powershell
$env:DATABASE_URL="postgresql://cee:cee@localhost:5432/cee_216"     # on
Remove-Item Env:DATABASE_URL                                         # off (back to cee)
```
```bash
export DATABASE_URL=postgresql://cee:cee@localhost:5432/cee_216      # on
unset DATABASE_URL                                                   # off (back to cee)
```
Below, `PY x` means `& $PY x` in PowerShell and `$PY x` in bash; paths use `EV/...` in both.
`ASOF` = 2026-11-17 for every eval (same as the committed baseline and Gate 4, so only the
corpus differs).

### PR A - documents, manifest, definitions
1. **Stored-corpus check (0 downloads), with evidence.** Scratch `EV/stored.sql` (the regex
   above, per firm and doc_type, trade excluded):
   `Get-Content EV\stored.sql | docker exec -i cee-db psql -U cee -d cee -P pager=off > EV\stored.txt`
   / `docker exec -i cee-db psql -U cee -d cee -P pager=off < EV/stored.sql > EV/stored.txt`.
   Scratch `EV/pdfgrep.py` (pypdfium2) over every MS/BAC/SCHW supplement, deck and monthly PDF
   in Box `raw/`: `PY -I EV/pdfgrep.py <files> > EV/rawgrep.txt`. Expected = the pre-check
   above. A count found in a raw PDF but in no chunk = a chunking loss: record page and text,
   report to the TL as a C1/C2 parse issue (not fixed here); it counts as "stored" only if a
   chunk carries it. Also: `PY -m pytest -q > EV/pytest-base.txt` on `cee`, 0da68fd -> the
   pass-count floor.
2. **Find sources, in this order per firm.** Window = 2024Q4-2026Q3 (Q23's eight quarters).
   Every try (URL, date, result: count found / no count / blocked) goes into
   `EV/sources-tried.md`, later into the findings and `looked_in`. Polite access (ADR-007
   T-08): EDGAR with the `EDGAR_IDENTITY` user agent read through `cee.config.settings()` in
   the scratch script (never printed), 1 s between requests per host; IR sites by script or by
   hand in the browser; Wayback copy when a site blocks scripts.
   a. **EDGAR full-text search** (8-K exhibits, i.e. supplements and releases, plus 10-K/10-Q),
      2023-01-01 to today:
      `https://efts.sec.gov/LATEST/search-index?q="<phrase>"&ciks=<CIK>&forms=8-K,10-K,10-Q&dateRange=custom&startdt=2023-01-01&enddt=2026-11-19`
      (UI: `https://www.sec.gov/edgar/search/#/q=...`), CIKs from `config/source_registry.csv`
      (MS 895421, BAC 70858, SCHW 316709). Phrases: MS "financial advisors", "Wealth
      Management representatives"; BAC "financial advisors", "wealth advisors", "Merrill
      advisors"; SCHW "financial consultants", "Wealth Consultants". Keep a hit only if a
      number sits on the advisor line.
   b. **Quarterly financial supplements** (T-03: the EDGAR copy if it is an 8-K exhibit, else IR):
      - MS: `https://www.morganstanley.com/content/dam/msdotcom/en/about-us-ir/finsup<q>q<yyyy>/finsup<q>q<yyyy>.pdf`
        for 4Q2024, then 4Q2023 (IR page `https://www.morganstanley.com/about-us-ir/earnings-releases`),
        Wealth Management metrics page: "Financial advisors" / "Wealth Management representatives".
      - BAC: `https://investor.bankofamerica.com/quarterly-earnings` "Supplemental Information"
        (or 8-K Ex.99.3 on EDGAR) for 4Q2024, then 4Q2023, GWIM key indicators:
        "Financial advisors", "Total wealth advisors, including financial advisors".
      - SCHW: no supplement with headcount; check the latest earnings deck and the 10-K
        "Human Capital" text for an FC/WC count.
   c. **Form ADV Part 1A** (tier 2, IAPD) for the three advisory entities, CRDs from
      `config/entities.yaml` (verified #55, matching the stored brochures' cover pages; if a
      cover page disagrees, mark TODO-verify and ask the TL): MSSB 149777, MLPF&S 7691,
      Charles Schwab & Co. 5393. URL: `https://reports.adviserinfo.sec.gov/reports/ADV/<CRD>/PDF/<CRD>.pdf`
      (fallback: the firm page `https://adviserinfo.sec.gov/firm/summary/<CRD>` -> "Part 1").
      Item 5.A/5.B: total employees, employees performing investment advisory functions,
      registered representatives of a broker-dealer. doc_id `<ENT>-ADV1A-2026`, doc_type
      `adv`, tier 2, `published_at` = the filing date printed on the report.
   d. **Firm fact pages and investor-day/business-update decks** (tier 3): MS
      `https://www.morganstanley.com/about-us` and `https://www.morganstanley.com/what-we-do/wealth-management`;
      Merrill `https://www.ml.com/about-merrill.html` and the BAC newsroom
      (`https://newsroom.bankofamerica.com`, search "financial advisors"); Schwab
      `https://www.aboutschwab.com/financial-reports`, `https://www.aboutschwab.com/` (company
      facts) and the 2024 Investor Day deck (`SCHW-DECK-2024-investor-day`). Prefer pages with
      a printed date: a page with `date_basis = retrieved` is excluded from time windows
      (ADR-007 T-09), so it cannot fill Q23's series; it is added only if it is the sole
      statement of a count, and the findings say so.
   e. **Wayback Machine** (`https://web.archive.org/web/2026*/<url>`) for any of a-d that blocks.
   f. Not tried: tier 1 licensed data (no Bloomberg/Capital IQ export in hand); trade press
      (tier 4; Q11/Q23 need firm sources; NEXT item 6 owns press ingestion).
   **Search stops** for a firm at the first source that gives an own-label count dated inside
   the window. The stored `BAC-DECK-2025-investor-day#9` does **not** stop the BAC search
   (GWIM-wide, rounded, one date, no definition): the search continues for a dated, defined
   Merrill or GWIM series. Form ADV Part 1A (c) is fetched for all three firms either way.
   **Selection rules.** A document is added only if it states a count. Each figure keeps its
   own label (MS "Financial advisors" vs "Wealth Management representatives"; BAC "financial
   advisors" vs "wealth advisors", GWIM vs Merrill); no figure is derived from another.
   "16K independent RIAs" is not a Schwab headcount and is not added. MS/BAC supplements: the
   quarters inside the window that carry the line; if the line stops before 2024Q4, only the
   **last** supplement that prints it (definition and break, not series). **Form ADV Part 1A
   figures** keep their Form ADV label ("employees performing investment advisory functions",
   "registered representatives") and are never called "advisor headcount": in
   `metric_definitions.yaml` they are the firm's `closest_metric` (when no own-label count
   exists) or a `see_also` + note (when one does), and the Part 1A doc_id is in `looked_in`
   either way. Cap: about 12 new documents; more needs a TL note. Downloads:
   `EV/dl/<doc_id>/<doc_id>.<ext>`, sha256 recorded, text checked with `EV/pdfgrep.py` (or the
   html text) before anything else.
3. **Manifest rows and Box.** doc_ids by the existing convention (`MS-SUPP-2024Q4`,
   `BAC-SUPP-2024Q4`, `MS-ADV1A-2026`, `SCHW-DECK-2024-investor-day`, `MER-PR-web-<slug>`, ...);
   tier as the same doc_type already uses; `published_at` from the source (8-K filing date,
   ADV filing date or printed date; T-09 order); `date_basis`; `period_end`; url (+ "(fetched
   via web.archive.org ...)" when so); `added_by` TL, `added_at` the day. sha256:
   `(Get-FileHash -Algorithm SHA256 <file>).Hash.ToLower()` / `shasum -a 256 <file>`. Copy each
   file to Box `raw/<doc_id>.<ext>` (`Copy-Item` / `cp`; Box path above, Mac
   `~/Library/CloudStorage/Box-Box/EDJ/raw/`). Checks:
   `PY -c "from cee.ingest.manifest import check_files, read_manifest; print(len(check_files(read_manifest())), 'files OK')"`
   -> 219 + N; 0 rows with empty `published_at`;
   `PY scripts/check_dates.py --today 2026-11-19 --skip-missing --out EV/dates.md` for new
   deck/press rows -> date source named, no mismatch.
4. **Scratch load (DB `cee_216`; `cee` stays `corpus-2026-11-17`).**
   `docker exec cee-db createdb -U cee cee_216`;
   `docker exec cee-db pg_restore -U cee -d cee_216 --no-owner /snapshots/corpus-2026-11-17.dump`
   (same command in both shells); scratch DB **on**; for each new doc
   `powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1 -Doc <doc_id>` /
   `bash scripts/ingest.sh --doc <doc_id>` (their "Row counts" line reads `cee`; ignore it).
   New PDFs are parsed by docling once here (cache written to Box `parsed/`). Checks (in
   `cee_216`, `docker exec cee-db psql -U cee -d cee_216 -c "..."`): `PY -m cee.smoke` PASS with
   the scratch DB on; documents = 219 + N, every new doc has chunks; for each firm the chunk(s)
   holding the count: chunk_id, page, section, segment (BAC chunks with GWIM text -> `GWIM`),
   count and label in the same chunk. A count split from its label by chunking: report it (C1
   parse issue), not fixed here. **Save the new chunks** (chunk_id, md5 of segment, section,
   page, prefix, text) for every chunk of the N new documents to `EV/new-chunks.txt`; `cee_216`
   is also kept until step 9 is done, then dropped.
5. **Definitions (PR A part).** Scratch DB off (`cee`). `config/metric_definitions.yaml`:
   BAC `advisor_headcount` -> quotes `BAC-DECK-2025-investor-day#9` (">15K Wealth Advisors",
   status `quoted`, valid_from 2025-09-30, includes: [Merrill and Private Bank advisors (GWIM)],
   excludes: [] (the test needs both keys); not_stated: definition, trainees, exact number; note: as of 3Q25, rounded, GWIM is not Merrill);
   MS and SCHW: `looked_in` extended by every source tried. `specs/filings.md` table to match.
   No new chunk_id anywhere in PR A. Checks: `PY -m pytest -q tests/test_metric_definitions.py`
   on `cee` -> pass (the verbatim test runs, not skipped); `PY -m pytest -q` on `cee` -> all
   pass, count >= the step-1 floor.
6. **Mock eval, same code, both corpora.**
   - Base (scratch DB off, `cee`): `PY scripts/eval_run.py --as-of 2026-11-17 --out EV/base`.
   - New (scratch DB on, `cee_216`): `PY scripts/eval_run.py --as-of 2026-11-17 --baseline EV/base/report.json --out EV/new`.
   - Scratch `EV/compare.py` -> `EV/compare.txt`: for Q11, Q23, Q24 which new count chunk_ids
     (step 4) are in `chunk_ids`; for the other 27 questions `recall_final` (and `doc_recall`,
     status) new vs base. **Merrill check for Q23:** if a new BAC/MER count chunk exists, that
     chunk; if none (N_BAC = 0), the stored `BAC-DECK-2025-investor-day#9` (GWIM; `#13` is
     segment NULL and cannot pass the Merrill filter) - its absence from mock Q23 today is
     recorded and reported to the TL as a retrieval gap (no retrieval change here).
     **Form ADV Part 1A chunks** are not expected in Q11/Q23/Q24 (`doc_type_scope`, #179):
     the acceptance for those firms is the `metric_definitions.yaml` record (PR B), and the
     gap is reported to the TL as a follow-up (S1), no retrieval change here.
   - **Stop rule:** any PASS -> FAIL, any of the 27 with lower `recall_final`, a forbidden hit,
     or refusal accuracy below base -> stop, classify (crowd-out by a new document, or other),
     report to the TL. A new non-`adv` count chunk not retrieved for Q11/Q23/Q24 -> record
     rank/pool (`recall_pool`) and report; that acceptance item stays open.
7. **PR A.** `git diff --name-only origin/main...HEAD` = the PR A files only; no `data/raw/`,
   `*.dump`. verify-cee (`/finish-task`) runs `PY scripts/verify_cee.py run` with the **scratch
   DB on (`cee_216`, corpus-2026-11-17 + the N new documents)**; before it, in the same shell,
   `docker exec cee-db psql -At -U cee -d cee_216 -c "SELECT count(*) FROM documents"` ->
   219 + N. Commit, push, PR ("Part of #216"; Verification: 0 real calls, evidence `EV`),
   `gh pr checks <PR#> --watch` -> all green; reviewed and merged via `/tl-review`.
   **N = 0** (no new document qualifies after a-f): no new snapshot (the corpus does not change);
   PR A carries the BAC `#9` entry, the MS/SCHW `looked_in` and the full documented search, says
   "Closes #216", and reports the snapshot/restore acceptance items as not applicable (nothing to
   snapshot) for the reviewer to accept or reject; steps 8-14 are skipped.

### PR B - snapshot (after PR A is merged)
8. **Build** in `D:\ALLPROJECTS\EDJ\repo` on `main` (clean, `git pull --ff-only`, HEAD =
   origin/main recorded; scratch DB off; no other session uses `cee`). `docker compose down -v`
   is **not** run (it would delete `cee_84`, `cee_84_rev`, `cee_216`); PR B says so, and the
   restore test is step 10. DASHBOARD 8 pre-checks (manifest `published_at`, sha256 via the
   build's 1/7). Notes (no links): "<219+N> documents, N more than corpus-2026-11-17: advisor
   headcount sources for Morgan Stanley, Merrill and Schwab (#216). Code since: planner (#214),
   part gaps (#215), answer v4.1 (#230), strict tools (#232)."
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "<notes>" *> D:\ALLPROJECTS\EDJ\cache\ev216\build.log
   ```
   ```bash
   bash scripts/build-snapshot.sh --notes "<notes>" 2>&1 | tee EV/build.log
   ```
   `SNAP` = the name it stamps: `corpus-2026-11-19` if built on 2026-11-19 (local date), else
   that day's date; announced as is (renaming would break the sha256 in `LATEST.json`).
   Log: `<219+N> files OK`; `Select-String -Path EV\build.log -Pattern "parsing with (docling|edgartools)"`
   / `grep -cE "parsing with (docling|edgartools)" EV/build.log` -> no match (parse cache from
   step 4); `4/7 Embedding skipped`; `Dumping SNAP.dump`; `Copying to Box`.
9. **Snapshot checks** (DB `cee` = `SNAP`; `psql` via `docker exec`, same in both shells):
   `obj_description('documents'::regclass)` = `SNAP`; documents = manifest doc_ids (219 + N);
   chunks = 21,143 + the lines of `EV/new-chunks.txt`; every chunk of the 219 old documents
   identical to `corpus-2026-11-17` (md5 over chunk_id, segment, section, page, prefix, text
   vs a scratch restore `cee_prev_216` of the local `snapshots/corpus-2026-11-17.dump`, its
   sha256 checked first against `47c1ffca...bfae1`); the new documents' chunks = `EV/new-chunks.txt`
   (and = `cee_216`). sha256 Box dump = local dump = `LATEST.json`
   (`Get-FileHash` / `shasum -a 256`); `docker exec cee-db pg_restore --list /snapshots/SNAP.dump`
   exit 0; `PY scripts/page_sweep.py > EV/page_sweep.txt` -> `MISPLACED 0` on every line.
   **Stop rule:** any old chunk differs, a count differs without an explanation, or a sha256
   differs -> stop, do not publish (no PR B), report to the TL; the dump stays in Box
   unannounced. After the checks: drop `cee_prev_216` and `cee_216`
   (`docker exec cee-db dropdb -U cee <name>`).
10. **Restore + smoke, both scripts** (each replaces `cee` with the same dump; `cee_84`,
    `cee_84_rev` untouched):
    `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 C:\Users\14370\Box\EDJ\snapshots\SNAP.dump`
    then `PY -m cee.smoke` -> PASS; `bash scripts/restore.sh <Box>/snapshots/SNAP.dump` (Git
    Bash here: `/c/Users/14370/Box/EDJ/snapshots/SNAP.dump`; Mac:
    `~/Library/CloudStorage/Box-Box/EDJ/snapshots/SNAP.dump`) then `PY -m cee.smoke` -> PASS.
    `powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1 -Check` and
    `bash scripts/sync-db.sh --check` -> exit 0 "up to date: SNAP". `PY scripts/verify_cee.py doctor`
    -> DOCTOR PASS.
11. **Definitions (PR B part) and baseline on `SNAP`.** `metric_definitions.yaml` and the
    `specs/filings.md` table get the entries quoting new chunks (and Part 1A `see_also` /
    `closest_metric`); `PY -m pytest -q tests/test_metric_definitions.py` on `cee` = SNAP ->
    pass. Eval: `PY scripts/eval_run.py --as-of 2026-11-17 --out EV/snap` (no `--baseline`;
    the committed file carries no local path); `PY scripts/eval_run.py --as-of 2026-11-17 --baseline EV/base/report.json --out EV/snap-vs`;
    rerun `PY scripts/eval_run.py --as-of 2026-11-17 --baseline EV/snap/report.json --out EV/snap-rerun`
    -> 30 UNCHANGED. Same checks and stop rule as step 6; base for the comparison is re-run on
    the same code (`EV/base-B` on a scratch restore of `corpus-2026-11-17` if `main`'s code
    moved since step 6). `EV/snap` and `EV/new` agree per question when the code is the same;
    any difference is explained by the code change, not the corpus. Copy `EV/snap/report.json`, `report.md` to `evals/baselines/SNAP/`.
12. **RUN.md section 7 and README.** RUN.md 7: "The current snapshot is `SNAP` (<219+N>
    documents). Gate 4 was scored 21/30 on `corpus-2026-11-17` ..."; the free check uses
    `--baseline evals/baselines/SNAP/report.json` with SNAP's expected result; before "Reproduce
    the Gate 4 answers" add the restore of the old dump, both blocks:
    `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 <Box>\snapshots\corpus-2026-11-17.dump`
    / `bash scripts/restore.sh <Box>/snapshots/corpus-2026-11-17.dump` (teammates: download
    that dump from the team Box link into `snapshots/`), and after it "run `/sync-db` to return
    to SNAP". Then `PY -m pytest -q` -> all pass (>= floor); `PY scripts/verify_cee.py run` on
    SNAP -> VERIFY PASS (one re-run on a clearly environmental failure).
13. **Publish**: branch `tl/216-snapshot-SNAP` from `main`; `LATEST.json` from the build;
    baseline; definitions; RUN.md 7; README Status; plan Progress log; in `repo`
    `git restore snapshots/LATEST.json` on `main` if the build left it modified. PR "Closes
    #216" (notes: `docker compose down -v` skipped, why; baseline folder kept, why),
    `gh pr checks <PR#> --watch` -> green, `/tl-review`, merge = sync note; one chat line for
    the TL: "New snapshot SNAP: run /sync-db".
14. **exp/hybrid** (not in these PRs): the next `sync/exp-hybrid-<date>` PR merges `main` and,
    after `/sync-db` to `SNAP`, runs `python -m cee.retrieve.embed --missing`, which embeds only
    the new chunks (the old 21,143 keep their vectors). Recorded on #216 as a hand-off comment.

**Paid calls: 0.** Data issue; everything runs on the mock provider.

## Acceptance
- [ ] **MS, MER, SCHW each:** a stored chunk that states an advisor count with its own label,
      definition and date (chunk_id + verbatim quote in `config/metric_definitions.yaml`), or a
      documented search that found none (`looked_in` + `EV/sources-tried.md` + findings list
      every source tried, incl. Form ADV Part 1A). Form ADV Part 1A figures recorded as
      `closest_metric` / `see_also` with their Form ADV label, never as advisor headcount.
      Check: step 4 query prints the chunk per firm; `pytest tests/test_metric_definitions.py`
      passes on `cee` (corpus-2026-11-17) for PR A and on `cee` (SNAP) for PR B.
- [ ] Stored-corpus check done before any download (`EV/stored.txt`, `EV/rawgrep.txt`); any
      chunking loss reported.
- [ ] Each new manifest row: source url, tier, `published_at`, `date_basis`, sha256; manifest
      check `219+N files OK`; 0 empty `published_at`; no inferred or derived figure anywhere.
- [ ] Mock (step 6 on `cee_216`, step 11 on SNAP): Q11, Q23, Q24 `chunk_ids` contain the new
      non-`adv` count chunks; the Merrill chunk named in step 6 is reported for Q23; `adv`
      retrieval gap reported to the TL; the other 27 questions: `recall_final` not lower than
      base, 0 PASS -> FAIL, 0 forbidden, refusal accuracy >= base; rerun 30 UNCHANGED.
- [ ] Snapshot `SNAP` built on clean `main` with `build-snapshot`; log checks pass; documents
      and chunk counts as expected; old chunks identical; new chunks = `EV/new-chunks.txt`;
      sha256 Box = local = `LATEST.json`.
- [ ] `restore.ps1` + smoke PASS and `restore.sh` + smoke PASS; both `sync-db` checks
      "up to date: SNAP"; DOCTOR PASS; VERIFY PASS (PR A on `cee_216`, PR B on SNAP);
      `pytest -q` all pass (>= floor) in PR A (on `cee`) and PR B (on SNAP).
- [ ] New baseline `evals/baselines/SNAP/` committed; `corpus-2026-11-17/` kept (Gate 4).
- [ ] `docs/RUN.md` section 7: `Select-String -Path docs/RUN.md -Pattern "restore.ps1 .*corpus-2026-11-17.dump","restore.sh .*corpus-2026-11-17.dump","sync-db","baselines/SNAP"`
      / `grep -nE "restore\.(ps1|sh) .*corpus-2026-11-17\.dump|sync-db|baselines/SNAP" docs/RUN.md`
      -> each of the four found in section 7.
- [ ] `git diff --name-only origin/main...HEAD` of PR A and PR B: no `data/raw/`, no `*.dump`.
- [ ] `gh pr checks` green on PR A and PR B.
- [ ] exp/hybrid `embed --missing` hand-off noted on #216 (done at the next sync).
- [ ] 0 real model calls (stated in both PRs).
- [ ] N = 0 case only: PR A closes #216 with the documented search; snapshot items reported
      not applicable.

## Progress log
- 2026-11-19 05:10 - plan written on `tl/216-headcount-sources` from origin/main 0da68fd.
  Read-only pre-check done (Facts): MS no count stored or in raw supplements; Merrill only the
  GWIM-wide ">15K Wealth Advisors" (investor day, as of 3Q25), already chunked (`#9` GWIM;
  `#13` segment NULL), retrieved by the real Q23 and by mock Q11/Q24 (not mock Q23), missing
  from `metric_definitions.yaml`; Schwab no staff advisor count ("16K" are independent RIAs).
  Two PRs needed because `build-snapshot` runs on `main` only. No file other than this plan
  changed.
- 2026-11-19 - review on #216 (reviewed 0e219a8): PLAN CHANGES REQUESTED, 5 blocking.
  Applied: (1) option (a), PR A cites only chunks in `corpus-2026-11-17`, new-chunk entries in
  PR B; (2) new chunks saved to `EV/new-chunks.txt` in step 4 and `cee_216` kept until step 9;
  (3) PR B updates RUN.md section 7 (current snapshot, old-dump restore both blocks,
  `/sync-db` back) with a grep check; (4) Form ADV Part 1A added to the source order
  (closest_metric with its own label, `looked_in` either way, `adv` retrieval gap reported);
  (5) Mac/bash forms for every step. Non-blocking applied: #187 waiver tags, dump size ~5 MB,
  Q23 Merrill chunk and N = 0 outcome, `#9` does not stop the BAC search, exact `pg_restore`
  and row-count note, prefer source-dated pages, step 9 stop rule, `down -v` skipped, verify-cee
  DB named for PR A. Also found: the metric test allows one entry per (entity, metric), so a
  Part 1A figure is the entry only when no own-label count exists, else `see_also` + note.
