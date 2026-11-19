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
# macOS (Windows Git Bash: EV=/d/ALLPROJECTS/EDJ/cache/ev216, PY=.venv/Scripts/python.exe, HF_HOME=/d/ALLPROJECTS/EDJ/cache/hf)
EV=$HOME/cee-ev216; mkdir -p "$EV"; PY=.venv/bin/python; export PYTHONUTF8=1 LLM_PROVIDER=mock HF_HOME="$HOME/.cache/huggingface"; unset CEE_VECTORS PYTHONPATH DATABASE_URL
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
      `config/entities.yaml` (from #55's IAPD check; the stored brochures' cover pages name the same
      legal entities; if one disagrees, mark TODO-verify and ask the TL): MSSB 149777, MLPF&S 7691,
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
   `gh pr checks <PR#> --watch` -> all green; reviewed and merged via `/tl-review`. PR A says
   that the MS/SCHW (and any BAC) entries quoting new chunks are finalized in PR B.
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
    `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 snapshots\corpus-2026-11-17.dump`
    / `bash scripts/restore.sh snapshots/corpus-2026-11-17.dump` (one path: the repo's
    `snapshots/` folder; teammates download the dump there from the team Box link, the TL copies
    it there from Box `snapshots/`), and after it "run `/sync-db` to return
    to SNAP". Then `PY -m pytest -q` -> all pass (>= floor); `PY scripts/verify_cee.py run` on
    SNAP -> VERIFY PASS (one re-run on a clearly environmental failure).
13. **Publish**: branch `tl/216-snapshot-SNAP` from `main`; `LATEST.json` from the build;
    baseline; definitions; RUN.md 7; README Status; plan Progress log; in `repo`
    `git restore snapshots/LATEST.json` on `main` if the build left it modified. PR "Closes
    #216" (notes: `docker compose down -v` skipped, why; baseline folder kept, why; for a firm
    whose only new evidence is a Form ADV Part 1A `adv` chunk, how "Q11, Q23, Q24 retrieve the new
    chunks" is met: the step 6 treatment, metric_definitions record plus the reported S1 gap),
    `gh pr checks <PR#> --watch` -> green, `/tl-review`, merge = sync note; one chat line for
    the TL: "New snapshot SNAP: run /sync-db".
14. **exp/hybrid** (not in these PRs): the next `sync/exp-hybrid-<date>` PR merges `main` and,
    after `/sync-db` to `SNAP`, runs `python -m cee.retrieve.embed --missing`, which embeds only
    the new chunks (the old 21,143 keep their vectors). Recorded on #216 as a hand-off comment.

**Paid calls: 0.** Data issue; everything runs on the mock provider.

## Acceptance
- [x] **MS, MER, SCHW each:** (MS `MS-SUPP-2020Q4#1`; MER `BAC-SUPP-2023Q4#2` and `BAC-DECK-2025-investor-day#9`; SCHW none published, Form ADV `SCHW-ADV1A-2026#1` as closest_metric) a stored chunk that states an advisor count with its own label,
      definition and date (chunk_id + verbatim quote in `config/metric_definitions.yaml`), or a
      documented search that found none (`looked_in` + `EV/sources-tried.md` + findings list
      every source tried, incl. Form ADV Part 1A). Form ADV Part 1A figures recorded as
      `closest_metric` / `see_also` with their Form ADV label, never as advisor headcount.
      Check: step 4 query prints the chunk per firm; `pytest tests/test_metric_definitions.py`
      passes on `cee` (corpus-2026-11-17) for PR A and on `cee` (SNAP) for PR B.
- [x] Stored-corpus check done before any download (`EV/stored.txt`, `EV/rawgrep.txt`); any
      chunking loss reported.
- [x] Each new manifest row: source url, tier, `published_at`, `date_basis`, sha256; manifest
      check `219+N files OK`; 0 empty `published_at`; no inferred or derived figure anywhere.
- [x] (Q23 Merrill chunk and ADV1A chunks not retrieved: accepted by the TL as W10 findings, #216) Mock (step 6 on `cee_216`, step 11 on SNAP): Q11, Q23, Q24 `chunk_ids` contain the new
      non-`adv` count chunks; the Merrill chunk named in step 6 is reported for Q23; `adv`
      retrieval gap reported to the TL; the other 27 questions: `recall_final` not lower than
      base, 0 PASS -> FAIL, 0 forbidden, refusal accuracy >= base; rerun 30 UNCHANGED.
- [x] Snapshot `SNAP` built on clean `main` with `build-snapshot`; log checks pass; documents
      and chunk counts as expected; old chunks identical; new chunks = `EV/new-chunks.txt`;
      sha256 Box = local = `LATEST.json`.
- [x] `restore.ps1` + smoke PASS and `restore.sh` + smoke PASS; both `sync-db` checks
      "up to date: SNAP"; DOCTOR PASS; VERIFY PASS (PR A on `cee_216`, PR B on SNAP);
      `pytest -q` all pass (>= floor) in PR A (on `cee`) and PR B (on SNAP).
- [x] New baseline `evals/baselines/SNAP/` committed; `corpus-2026-11-17/` kept (Gate 4).
- [x] `docs/RUN.md` section 7: `Select-String -Path docs/RUN.md -Pattern "restore.ps1 .*corpus-2026-11-17.dump","restore.sh .*corpus-2026-11-17.dump","sync-db","baselines/SNAP"`
      / `grep -nE "restore\.(ps1|sh) .*corpus-2026-11-17\.dump|sync-db|baselines/SNAP" docs/RUN.md`
      -> each of the four found, and the PR quotes the `-n` line numbers, all inside the section 7
      heading range (`## 7.` to end of file).
- [x] `git diff --name-only origin/main...HEAD` of PR A and PR B: no `data/raw/`, no `*.dump`.
- [x] `gh pr checks` green on PR A (#235: pytest pass) and PR B.
- [x] exp/hybrid `embed --missing` hand-off noted on #216 (done at the next sync).
- [x] 0 real model calls (stated in both PRs).
- [x] (not applicable: N = 5) N = 0 case only: PR A closes #216 with the documented search; snapshot items reported
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
- 2026-11-19 05:20 - round 2 on #216 (reviewed 0c84c7f): **PLAN APPROVED** (reviewer agent),
  https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/216#issuecomment-7007680892 ;
  0 blocking, 6 non-blocking. Applied: bash/Mac `EV` line; RUN.md grep quotes `-n` lines inside
  section 7; one dump path (`snapshots/`) in RUN.md; PR A says the new-chunk entries are
  finalized in PR B; PR B states how the issue item is met for Form ADV-only evidence; CRD
  wording (#55's IAPD check).
- 2026-11-19 05:24 - step 1 done (`cee` = corpus-2026-11-17, read-only): `EV/stored.txt`
  (35 rows) and `EV/rawgrep.txt` (23 PDFs) = the pre-check; no chunking loss. `pytest -q`
  on 0da68fd: 698 passed (floor, `EV/pytest-base.txt`).
- 2026-11-19 05:36 - step 2 done, every try in `EV/sources-tried.md` (EDGAR full-text search
  `EV/efts.txt`, `EV/efts-ms-early.txt`; contexts `EV/efts-ctx.txt`). Found: MS supplements
  print "Wealth Management representatives" last in 4Q2020 (8-K Ex.99.2 filed 2021-01-20;
  1Q2021-4Q2024 and the stored 2025Q4-2026Q3 do not); BAC supplements print "Total wealth
  advisors (3)" last in 4Q2023 (filed 2024-01-12; footnote "Includes advisors across all wealth
  management businesses in GWIM and Consumer Banking"); Schwab publishes no FC/WC count (10-K,
  10-Q, decks incl. the 2024 investor day, aboutschwab.com via Wayback); firm pages none. Form
  ADV Part 1A Item 5 for MSSB, MLPF&S and Charles Schwab & Co. fetched (390/681/75-page PDFs,
  18-34 MB; stored as verbatim text extracts of the page 1 header and Item 5.A-5.B, because
  parsing the full filings would add thousands of unrelated chunks). No count exists inside the
  Q23 window for MS, Merrill or Schwab under the firms' own labels.
- 2026-11-19 05:37 - step 3: 5 manifest rows (`MS-SUPP-2020Q4` htm EDGAR Ex.99.2,
  `BAC-SUPP-2023Q4`, `MS-ADV1A-2026`, `MER-ADV1A-2026`, `SCHW-ADV1A-2026`), files in Box `raw/`,
  sha256 in `EV/sha256-new.txt`; manifest check 224 files OK, 0 empty `published_at`.
- 2026-11-19 05:39 - step 4: `cee_216` restored (219 docs, 21,143 chunks) and the 5 docs
  ingested; smoke PASS. Found: the BAC EDGAR htm parses as one flat section, so the GWIM page
  chunk had segment NULL (the Merrill filter would drop it) and the count split over two chunks.
  Switched `BAC-SUPP-2023Q4` to the IR PDF (same as the other BAC supplements, docling headings
  tag GWIM); htm removed from Box `raw/` and `cee_216`, manifest row updated. The first
  `ingest.ps1 -Doc MS-SUPP-2020Q4` exited 1 (edgartools cache miss; error text not kept); a
  rerun of `cee.ingest.load --doc` succeeded (86 chunks).
- 2026-11-19 05:48 - step 4 done: `BAC-SUPP-2023Q4.pdf` parsed by docling (cache written),
  109 chunks. `cee_216`: 224 documents, 21,347 chunks (+204: MS-SUPP-2020Q4 86, BAC-SUPP-2023Q4
  109, three ADV1A 3 each); md5s in `EV/new-chunks.txt` (204 lines). Count chunks:
  `MS-SUPP-2020Q4#31` (segment Wealth Management) "Wealth Management representatives 15,950
  15,469 15,468"; `BAC-SUPP-2023Q4#61` (page 20, GWIM) "Total wealth advisors (3) | 18,916 |
  19,273 | ..." with footnote (3) in `#62` (GWIM); `MS-ADV1A-2026#1`, `MER-ADV1A-2026#1`,
  `SCHW-ADV1A-2026#1` Item 5.A/5.B. Every count sits with its label in one chunk.
- 2026-11-19 05:49 - step 5: `config/metric_definitions.yaml` (BAC quotes
  `BAC-DECK-2025-investor-day#9`; MS/SCHW `looked_in` extended; notes say PR B finalizes),
  `specs/filings.md` table, `config/source_registry.csv` (MS/BAC supplement URL patterns).
  `pytest tests/test_metric_definitions.py` on `cee`: 13 passed, 0 skipped; `pytest -q`: 698
  passed (= floor).
- 2026-11-19 05:50 - step 6: base (`cee`) 29 PASS / 1 FAIL (Q19); new (`cee_216`) 29 / 1; 0
  forbidden; refusal 5/5 and 22/22 both; `EV/compare.txt`. Q11 retrieves `BAC-SUPP-2023Q4#61`,
  `#62`, `BAC-DECK-2025-investor-day#9`; Q23 retrieves `BAC-SUPP-2023Q4#61` (not `#9`); Q24
  retrieves `MS-SUPP-2020Q4#31`, `BAC-SUPP-2023Q4#61`, `#9`. Not retrieved: `MS-SUPP-2020Q4#31`
  for Q11 and Q23; the three ADV1A chunks for Q11/Q23/Q24 (expected, `doc_type_scope` #179).
  **Stop rule hit:** Q17 `recall_final` 1.0 -> 0.9: `BAC-TR-2026Q2#21` (Merrill's AI-tools
  remark) lost its slot to `BAC-SUPP-2023Q4#10` (2023 income statement, "Information
  processing and communications" row). Class (b), ranking crowd-out by a new document; Q17
  stays PASS; no other question moves. Stopped before PR A; reported to the TL.
- 2026-11-19 05:51 - **TL decision** (relayed by the coordinator; comment on #216
  https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/216#issuecomment-7008345965):
  do not accept the drop; store the two old supplements as verbatim page extracts (count page
  and its footnote/definition, page numbers kept), like the Form ADV Part 1A extracts; keep
  the BAC count chunk GWIM-tagged; remove the full-document rows/files; re-run step 6.
- 2026-11-19 05:53 - done. `MS-SUPP-2020Q4.txt` = pages 8 (Wealth Management metrics) and 15
  (notes) of the 18-page IR PDF `finsup4q2020.pdf`; `BAC-SUPP-2023Q4.txt` = page 20 of the
  34-page IR PDF (GWIM key indicators, count and footnote (3)); script `EV/scripts/page_extract.py`,
  each page written as "Page N:" with its exact text. doc_ids unchanged (the ADV1A extracts
  carry no page suffix either; the manifest url field names the source URL, the pages and
  that the file is an extract). sha256 of the extracts in the manifest. Removed from Box
  `raw/`: `MS-SUPP-2020Q4.htm`, `BAC-SUPP-2023Q4.pdf` (the earlier `BAC-SUPP-2023Q4.htm` was
  removed at 05:39); removed from `cee_216`. Orphaned parse-cache files left in Box `parsed/`:
  `e6c3efa2...-edgartools5.59.1-v1.json` (MS htm), `e359e686...-edgartools5.59.1-v1.json` (BAC
  htm), `d2b72cb7...-docling2.131.0-doc.json` and `-v2.json` (BAC PDF). `cee_216`: 224 documents,
  21,161 chunks (+18: MS-SUPP-2020Q4 6, BAC-SUPP-2023Q4 3, ADV1A 3 x 3); `EV/new-chunks.txt`
  rewritten (18 lines). Count chunks: `MS-SUPP-2020Q4#1` ("Wealth Management representatives
  15,950 15,469 15,468"; segment NULL, MS needs no segment filter), `BAC-SUPP-2023Q4#2` (GWIM;
  "Total wealth advisors (3) 18,916 ..." and footnote (3) in the same chunk); all 3 BAC chunks
  GWIM (mention rule on the flat text).
- 2026-11-19 05:54 - step 6 re-run (`EV/new2`, `EV/compare2.txt`; base `EV/base` unchanged,
  same code 7b0d6ca = 0da68fd + data/config): 29 PASS / 1 FAIL (Q19) on both, **0 questions
  flagged** (Q17 back to 1.0; no PASS -> FAIL, no `recall_final` lower), 0 forbidden, refusal
  5/5 and 22/22, overall recall@final 0.654 = base. Q11 retrieves `MS-SUPP-2020Q4#1`,
  `BAC-SUPP-2023Q4#2`, `BAC-DECK-2025-investor-day#9`; Q23 retrieves `MS-SUPP-2020Q4#1`;
  Q24 retrieves `MS-SUPP-2020Q4#1`, `BAC-SUPP-2023Q4#1`/`#2`, `#9`. **Open:** Q23 retrieves no
  Merrill count chunk (`BAC-SUPP-2023Q4#2` and `#9` both outside its final set); the ADV1A
  chunks are not retrieved for Q11/Q23/Q24 (`doc_type_scope`, #179). Both reported to the TL
  (S1 follow-up), no retrieval change here.
- 2026-11-19 05:57 - verify-cee on `cee_216`: `PY scripts/verify_cee.py run --source-db cee_216`
  (the script copies its source database; `DATABASE_URL` alone is not used for the copy, so the
  first run at 05:55 tested `cee`): corpus 21,161 chunks, VERIFY PASS (9 features), evidence
  `.verify-runs/20261119-055719-7b0d6ca`. `pytest -q` on `cee`: 698 passed; manifest check
  224 files OK. PR A next ("Part of #216").
- 2026-11-19 06:00 - PR A #235 approved and merged (7b03b7a). TL decision on #216: Q23's missing
  Merrill count chunk and the ADV1A chunks outside Q11/Q23/Q24 (#179 scope) are accepted as W10
  findings (to the #217 report and docs/NEXT.md); PR B may close #216; tag `MS-SUPP-2020Q4#1`
  Wealth Management only if existing tagging does it without new code.
- 2026-11-19 06:09 - step 8: `main` f919a36 (= 7b03b7a + PROGRESS line), clean. Build exit 0:
  `224 files OK`, 0 `parsing with docling|edgartools`, 93 `parse cache hit`, `4/7 Embedding
  skipped`, `Dumping corpus-2026-11-19.dump`, `Copying to Box`. SNAP = **corpus-2026-11-19**,
  built 2026-11-19T12:09:55Z, 224 documents, 21,161 chunks, sha256
  `1d0d34b534cbb14a1bb1654f90d3ee7262b5a6e2305a103a12058cdf60283fb0` (Box dump = local dump =
  `LATEST.json`).
- 2026-11-19 06:11 - step 9: name stamped `corpus-2026-11-19`; documents = the manifest's 224
  doc_ids, none without chunks; `pg_restore --list` exit 0; `corpus-2026-11-17.dump` sha256 =
  `47c1ffca...bfae1`, restored as `cee_prev_216`: all 21,143 old chunks identical (md5 over
  chunk_id, segment, section, page, prefix, text), the 18 added chunks = `EV/new-chunks.txt`,
  and SNAP = `cee_216` chunk for chunk. `page_sweep`: 52 PDFs, `MISPLACED 0` on every line. Stop
  rule not hit. `cee_prev_216` and `cee_216` dropped (`cee`, `cee_84`, `cee_84_rev` kept).
  `MS-SUPP-2020Q4#1` keeps segment NULL: its first line is "Page 8:" and the page heading line
  is not exactly a segment alias, so the existing tagger cannot tag it without new code or
  non-verbatim text (TL decision: record it). It does not matter for MS questions today (no
  segment filter); a segment-filtered MS question would drop it.
- 2026-11-19 06:12 - step 10: `restore.ps1 <Box>/snapshots/corpus-2026-11-19.dump` exit 0 ->
  smoke PASS (snapshot corpus-2026-11-19, 21,161 chunks); `bash scripts/restore.sh` (Git Bash)
  same dump exit 0 -> smoke PASS; `sync-db.ps1 -Check` and `sync-db.sh --check` exit 0 "up to
  date: corpus-2026-11-19"; DOCTOR PASS. `docker compose down -v` not run (it would delete
  `cee_84`, `cee_84_rev`).
- 2026-11-19 06:15 - step 11: no code change since 0da68fd (`git diff 0da68fd HEAD -- src scripts
  config/entities.yaml` empty). `EV/snap` (committed as `evals/baselines/corpus-2026-11-19/`):
  29 PASS / 1 FAIL (Q19), tier-1 doc recall 0.937, recall@final 0.654, refusal 5/5 and 22/22, 0
  forbidden. vs `EV/base` (corpus-2026-11-17): 0 flagged (`EV/compare-snap.txt`); `EV/snap` and
  `EV/new2` have identical `chunk_ids` for all 30 questions; rerun 30 UNCHANGED. Extract chunks in
  other questions' final sets (`EV/extracts-in-final-sets.txt`): MS-SUPP-2020Q4 in Q1, Q9, Q13,
  Q15, Q18, Q20, Q21, Q22; BAC-SUPP-2023Q4 in Q21 (incl. its header `#0`), Q22, Q28; ADV1A in
  Q25 (`MER-ADV1A-2026#1`, `SCHW-ADV1A-2026#0`); no status or recall moved. Definitions quoting
  new chunks in `config/metric_definitions.yaml` (MS `MS-SUPP-2020Q4#1` quoted; BAC
  `BAC-SUPP-2023Q4#2` quoted with `#9` in see_also; SCHW `SCHW-ADV1A-2026#1` closest_metric) and
  `specs/filings.md`; `pytest tests/test_metric_definitions.py` on SNAP: 13 passed.
- 2026-11-19 06:18 - step 12: RUN.md section 7 (current snapshot, free check on the new
  baseline, old-dump restore in both shells, `/sync-db` back; grep lines 262, 272, 275, 288, all
  in section 7 = lines 236-288) and README Status. `pytest -q`: 698 passed; verify-cee on SNAP:
  VERIFY PASS (9 features), `.verify-runs/20261119-061624-f919a36`. Notes for readers: the 18
  extract chunks have `page` NULL (text files; the source page is the "Page N:" label in the
  text; "Page 6:"-style references inside MS page 15 are the supplement's own printed page
  numbers); each extract's `#0` is the extractor's header (title, source, pages), not source
  text. Orphaned parse-cache files in Box `parsed/` as listed in PR A.
