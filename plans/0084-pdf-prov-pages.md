# 0084 - PDF chunks: take pages from every docling provenance span

Issue: #84    Role: TL    Spec: specs/ui.md (source page), docs/DECISIONS.md ADR-005

## Goal
Text from a docling item is stored under the page it is actually on, so a citation opens the PDF
at the right page. An item whose provenance covers two pages is split at the page break (docling
gives the exact character span per page). Every PDF in the manifest is re-parsed once, before the
corpus freeze on 11/11 (#120), and answer-key chunk IDs that move are re-pointed.

## Facts found (read-only, 2026-11-08)
- `_parse_docling` stores each item under `item.prov[0].page_no`. The parse cache (#82) holds only
  the finished `(section, page, text)` list, so provenance is not in it; a re-parse is needed.
- docling on `SCHW-DECK-2026Q1` (211 s, 35 pages): 480 items, 6 with more than one prov entry, 4 of
  them across pages. The issue's example (p4): `pages=[4,4,4,5]`, charspans `(0,19) (20,42) (43,78)`
  on p4 and `(79,160)` on p5; chars 79-160 are "Our "Through Clients' Eyes" Strategy continues to
  drive growth across all fronts.", which pymupdf finds on p5 only. Charspans index into
  `item.text`, so the text can be cut at them.
- The other cross-page items in that deck: pages `[8,9,9]`, `[12,12,13]`, `[13,14]`.
- Prototype of the split on the saved DoclingDocument (scratch, not committed): SCHW-DECK-2026Q1
  goes from 62 to 66 chunks and from 58/62 to 66/66 chunks with >= 90% of their tokens on their
  stated page. Chunk IDs shift from `#6` on (answer-key `SCHW-DECK-2026Q1#40` -> `#44`, same text).
- A DoclingDocument saved with `export_to_dict()` (0.54 MB for that deck) and reloaded with
  `DoclingDocument.model_validate` gives exactly the cached v1 items, so the docling output itself
  can be cached and our post-processing re-run from it without docling.
- Sweep today (scratch script; cached parses chunked exactly as `load.py` does; a chunk token
  counts as "on the page" when it occurs in the page's pymupdf text with all spaces and punctuation
  removed, because some PDFs have fused words, e.g. MCK "requirewealthmanagersto"): 37 of the 47
  manifest PDFs have a docling cache: **3,177 of 3,220 chunks >= 90%**; 43 below, 17 of them with
  another page holding more of their tokens. The 16 decks and supplements from #77/#78: 1,057 of
  1,063; the 6 below are the issue's 6 SCHW chunks under today's IDs: SCHW-DECK-2026Q1 #6 p4, #14 p8,
  #21 p12, #22 p13; SCHW-DECK-2026Q2 #14 p8; SCHW-DECK-2026Q3 #49 p25 (the issue's "#42 p25"; IDs
  moved since #78). The rest: SCHW/RJF/BAC investor-day decks (#146, 23 below), FINRAF, CAPGEMINI,
  UBS, KITCES, NM, MCK research PDFs. (The issue's "962 of 976" used another count; this plan uses
  the metric above throughout, before and after.)
- 10 PDFs from #147 (BAC/MS/RJF supplements 2025Q3-Q4, six SCHW monthly reports) have no docling
  cache on Box yet; manifest PDFs: 47, 1,526 pages. At ~6 s/page a full docling run is ~2.5 h.
- Docker is not running right now; the shared DB `cee` (corpus-2026-10-29, 111 docs) predates
  #146/#147, so it lacks at least the 4 investor-day decks and the 10 #147 PDFs.

## Files to change
- `src/cee/ingest/pdf.py` - split `_parse_docling` into `_convert` (docling, slow) and
  `doc_items(doc, is_table)` (pure; duck-typed, so tests need no docling). In `doc_items`, a
  non-table item whose prov covers more than one page is cut at the charspan where the page
  changes; each part goes under its own page and joins the run of the same `(section, page)` as
  today. Spans that are out of order or outside the text: keep the whole item on the page with the
  most characters (counted, printed per document). Tables keep `prov[0]` (rows have no page; the
  sweep shows whether any table crosses a page). `PARSER_VERSION = 2`. Docling output cache (see
  next line) read before converting.
- `src/cee/ingest/parse_cache.py` - nothing new in the API; the DoclingDocument is stored with the
  existing `write`/`read` as `<sha256>-docling<version>-doc.json` (no `PARSER_VERSION` in the name:
  it is docling's own output). A later post-processing change then needs a version bump only, not
  another 2.5-hour docling run; this keeps the review loop before 11/11 cheap. Docstring: the name
  does not encode the pipeline options (`do_ocr=False`); changing them needs a new name (e.g. a
  `-doc2` suffix), or old docling output would be reused.
- `tests/test_pdf_pages.py` (new) - fake two-page item `pages [4,4,5]` -> text before the p5
  charspan on p4, the rest on p5, and the p5 part merges with the next p5 item; spans `[4,5,4]` ->
  three parts in order; one-page multi-span item unchanged; bad charspan -> dominant page; table
  with two pages -> first page; an item with no prov skipped (as today).
- `tests/test_parse_cache.py` - fakes take the new `_parse_docling` signature; names end `-v2`; new
  test: `PARSER_VERSION` bump with a docling-output cache present converts nothing; `use_cache=False`
  converts again and refreshes both files.
- `scripts/page_sweep.py` (new) - the sweep above as a script: PDF chunks from the DB
  (`DATABASE_URL`), raw files through `cee.config.resolve_path`; prints per document, the total, and
  every chunk below 90% with the page that holds most of its tokens, marked `PASS-SAMEPAGE` (that
  page is the stated page) or `MISPLACED` (another page holds more); counts per group (all PDFs;
  the 16 #77/#78 PDFs). Exit 0 always (a report). Scoring function importable for tests.
- `scripts/chunk_dump.py` - `remap OLD.json NEW.json ID...`: for each old chunk ID the new ID with
  identical text, else the new chunk(s) of the same document holding the most of its text.
- `tests/test_chunk_dump.py` (new) - `remap`: identical text -> new ID after a shift; a chunk split
  in two -> both IDs; another document's chunk never matched. `tests/test_page_sweep.py` (new) -
  the scoring function on fake page texts: fused words count, `PASS-SAMEPAGE` vs `MISPLACED`.
- `evals/expected_chunks.yaml`, `evals/expected_results.md` - PDF chunk IDs re-pointed with
  `remap` (ID numbers only; rows, quotes and reasons unchanged). Owners S1/C1; see open question 1.
- `scripts/verify_cee.py` - `PDF_PAGE_SAMPLES` re-pointed if `SCHW-DECK-2026Q2#53` /
  `MS-SUPP-2026Q3#16` move; `--source-db` (default `cee`, verify copy `<source>_verify`) so verify-cee
  runs on the private copy and does not collide with #129's verify runs. #129 also edits this file
  (`CONTAINER` line): whichever PR merges second merges `origin/main` into its branch (never
  rebase) and re-runs verify-cee.
- `.claude/skills/verify-cee/features/open-citation.md` - same ID re-pointing; one line for
  `--source-db` in `.claude/skills/verify-cee/SKILL.md`.
- `docs/DECISIONS.md` ADR-005 - note: pages come from every prov span (#84); docling output cache.

Not changed: `evals/baselines/*` (historic runs keep the IDs of their snapshot); `query_log.chunk_ids`
(history); unit-test fixture IDs in `tests/` that are not read from a DB (checked one by one).

## Steps
Shell for every step (Windows; Mac the same with `export`): `TMP`/`TEMP=D:\ALLPROJECTS\EDJ\cache\tmp`,
`HF_HOME=D:\ALLPROJECTS\EDJ\cache\hf`, `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-84\src`,
`CORPUS_SHARE_PATH=C:\Users\14370\Box\EDJ`, `DATABASE_URL=postgresql://cee:cee@localhost:5432/cee_84`,
`LLM_PROVIDER=mock`, `CEE_VECTORS=off`. Work in worktree `D:\ALLPROJECTS\EDJ\wt-84`. The shared `cee`
is only read; there is no interim write to it at any point (TL decision, plan review round 1).

0. **Private DB and baseline.** Start Docker. `CREATE DATABASE cee_84 TEMPLATE cee` (if `cee` has
   open connections, restore `corpus-2026-10-29.dump` into `cee_84` instead). List its PDF documents.
   `chunk_dump.py dump --all before.json`; `page_sweep.py > sweep-before.txt`;
   `eval_run.py --as-of 2026-10-29 --out .eval-runs/84-before`. Evidence folder:
   `D:\ALLPROJECTS\EDJ\cache\ev84` (outside git).
1. **Code + unit tests** (`pdf.py`, `test_pdf_pages.py`, `test_parse_cache.py`); `pytest -q`.
2. **Check on one deck before the long run:** `load --doc SCHW-DECK-2026Q1` into `cee_84` (docling,
   ~4 min; writes the v2 and docling-output cache files to Box `parsed/`). Sweep that document:
   66/66 expected; the 4 SCHW-DECK-2026Q1 chunks of the issue on the right pages. Reload it: both
   caches hit, 0 converts, same chunks.
3. **Re-parse the PDFs already in `cee_84`**, one `load --doc` per PDF in a background loop with a
   log per document (~2 h). Then: `chunk_dump.py dump --all after.json`; `compare before.json
   after.json` -> only PDF documents with a cross-page item differ; every HTML/text chunk identical.
4. **Re-point the answer key:** `chunk_dump.py remap before.json after.json <every PDF chunk ID in
   expected_chunks.yaml, expected_results.md, verify_cee.py, open-citation.md>`. Check each new ID
   against its quote in `expected_results.md`; a passage now split over two chunks lists both IDs
   in its row (a row is found when any ID is retrieved). Mapping table goes in the PR.
5. **Mock eval after:** `eval_run.py --as-of 2026-10-29 --baseline .eval-runs/84-before/report.json
   --out .eval-runs/84-after` with the re-pointed key. Every change against the baseline is
   explained in the PR (expected: UNCHANGED, or a page-split chunk ranking differently).
6. **The rest of the manifest** (may run in the background alongside steps 4-5): `load --doc` for
   each manifest PDF not in `cee_84` (the #146 decks, the 10 #147 PDFs, any other; ~1 h). Now all 47
   manifest PDFs are in `cee_84`, and their v2 and docling-output cache files are on Box `parsed/`
   well before 11/11 (checked: 47 `-doc.json` and 47 `-v2.json` files matching the manifest
   sha256s), so the freeze build (#120) runs no docling.
7. **Sweep all PDF chunks** in `cee_84` (`page_sweep.py > sweep-after.txt`) and apply the pass rule
   (Acceptance, sweep item). Every `MISPLACED` chunk is fixed, or listed in the PR with a linked
   follow-up TL issue (opened by me: chunk IDs, stated page, page holding most tokens, cause).
8. **verify-cee** on the copy: `verify_cee.py run --source-db cee_84 --port 8684` (open-citation
   opens the re-pointed PDF samples at their pages). `pytest -q`. Old v1 parse files stay (main
   reads them until merge).
9. ADR-005 note, Progress log, `/finish-task`: PR to main, `Closes #84`, 0 real calls. The PR body
   states **"merge together with the #120 build"** and names the review inputs (`cee_84`,
   `.eval-runs/84-before`). Request S1 and C1 as reviewers as soon as the PR opens (answer-key IDs).
10. **Review and merge timing (TL decision).** The reviewer approves on `cee_84`
    (`verify_cee.py run --source-db cee_84`, eval against `.eval-runs/84-before/report.json`).
    `cee_84` and `.eval-runs/84-before` are kept until the merge. The PR then stays open, approved
    and not merged, so `cee`, teammates' databases and main's answer key stay consistent with each
    other. On 11/11 it is merged immediately before the #120 freeze build; that build loads from the
    manifest and the parse cache with the new parser, so the freeze snapshot carries the re-parsed
    chunks and the new answer-key IDs together. If main moves before then, merge `origin/main` into
    the branch (never rebase) and re-run `pytest -q` and verify-cee on `cee_84`. Drop `cee_84` and
    `cee_84_verify` after the merge.

## Acceptance
- [x] Linked questions: Q8 and Q22 retrieval (mock, `--as-of 2026-10-29`) on `cee_84` not worse
      than the baseline on the same copy; Q22's PDF rows (MS/RJF supplements, SCHW deck) re-pointed
      and still found if found before. Any change explained.
- [x] The 6 SCHW chunks (SCHW-DECK-2026Q1 #6 p4, #14 p8, #21 p12, #22 p13; SCHW-DECK-2026Q2 #14 p8;
      SCHW-DECK-2026Q3 #49 p25; today's IDs): each piece of their text is in a chunk whose page is
      where pymupdf finds it, >= 90% tokens on that page; shown in the PR with old ID -> new ID(s).
- [x] Sweep of all PDF chunks of all 47 manifest PDFs (`page_sweep.py` on `cee_84`). Pass rule: a
      chunk passes when >= 90% of its tokens are on its stated page; a chunk below 90% passes only
      if its stated page is the page the sweep reports as holding most of its tokens
      (`PASS-SAMEPAGE`). A chunk where another page holds more of its tokens (`MISPLACED`; 17 today)
      is fixed, or listed in the PR with a linked follow-up issue. The 16 #77/#78 PDFs: 0 chunks
      below 90%. The PR states before/after counts for both groups (>= 90%, `PASS-SAMEPAGE`,
      `MISPLACED`). Before, 37 cached PDFs: 3,177/3,220 >= 90%, 43 below, 17 `MISPLACED`; 16 #77/#78
      PDFs: 1,057/1,063, 6 below, 1 `MISPLACED` (SCHW-DECK-2026Q1#6).
- [x] All 47 manifest PDFs have a docling-output and a v2 cache file on Box `parsed/` before 11/11.
- [ ] PR body says "merge together with the #120 build"; the PR is approved on `cee_84` and is not
      merged before the #120 freeze build on 11/11; no write to the shared `cee` before then.
- [x] `chunk_dump.py compare before after`: every non-PDF chunk identical; PDF documents without a
      cross-page item identical.
- [x] Every PDF chunk ID in `evals/expected_chunks.yaml`, `evals/expected_results.md`,
      `scripts/verify_cee.py`, `open-citation.md` points at a chunk with the quoted text (remap table).
- [x] Re-load of one PDF after a `PARSER_VERSION` bump in a test: 0 docling conversions (unit test)
      and a real reload hits both caches.
- [x] `pytest -q` passes; `verify_cee.py run --source-db cee_84` all PASS; `cee` unchanged
      (document and chunk counts and `obj_description` the same before and after); 0 real calls.

## Decisions from plan review round 1
1. Accepted: `evals/expected_chunks.yaml` (S1) and `evals/expected_results.md` (C1) get the ID
   renumbering here (nothing else); S1 and C1 are requested as PR reviewers.
2. Replaced by the concrete sweep pass rule in Acceptance (`PASS-SAMEPAGE` / `MISPLACED`).
3. Accepted: docling-output cache (one extra file per PDF, ~0.5-5 MB on Box), so a review round
   that changes the post-processing costs no new ~2.5 h docling run before 11/11.
4. TL: no interim write to `cee`; approved on `cee_84`, merged on 11/11 right before the #120 build.

## Progress log
- 2026-11-08 12:08 - plan written; branch tl/84-pdf-prov-pages (worktree wt-84) from origin/main
  83e9152. Facts above from read-only runs (docling on SCHW-DECK-2026Q1, cached parses, pymupdf);
  no DB touched (Docker was down).
- 2026-11-08 12:40 - plan review round 1 CHANGES REQUESTED: added merge timing (approved on
  `cee_84`, merged on 11/11 right before the #120 build, no interim write to `cee`), all 47 docling
  caches on Box before 11/11, the sweep pass rule with before/after counts per group; notes taken:
  #129 merge order, tests for `remap`/sweep scoring, cache-name docstring, S1/C1 reviewers, step 6
  in the background.
- 2026-11-08 13:05 - plan approved (round 2). `cee` before: 111 docs, 17,183 chunks,
  corpus-2026-10-29, 32 PDFs. `cee_84` created from it; before dump, `page_sweep.py` on `cee`
  (read-only): all 32 PDFs 2,335/2,355 >= 90%, 10 PASS-SAMEPAGE, 10 MISPLACED; 16 #77/#78 PDFs
  1,057/1,063, 5 PASS-SAMEPAGE, 1 MISPLACED. Baseline mock eval `.eval-runs/84-before`: 28 PASS,
  2 FAIL (Q15, Q19), tier-1 recall 0.796. Code and unit tests written. SCHW-DECK-2026Q1 into
  `cee_84`: docling 3m37s, 66 chunks; reload hits the v2 file (0.7 s); with the v2 file deleted it
  hits the docling-output file (2.7 s, 0 converts). Re-parse running in the background; docling
  is slower than in #82 (BAC-SUPP-2026Q1 882 s), so two extra cache-only workers run alongside.
  pytest blocks while a load holds its transaction on `cee_84` (DB tests use scratch schemas
  there); it runs after the loads.
- 2026-11-08 18:40 - re-parse of the 32 PDFs in `cee_84` done (docling 2-60 min per PDF; tables
  are slow; one cache-only worker died of a full page file with four workers and was not
  restarted; no document needed the charspan fallback). `chunk_dump compare`: every non-PDF chunk
  identical; 22 PDFs identical; 10 changed (SCHW-DECK-2026Q1/Q2/Q3, CAPGEMINI, CERULLI, FINRAF-
  FINFLUENCERS, KITCES, MCK-ADVISOR-SHORTAGE, NM-PP, UBS-NEXTGEN), 17,183 -> 17,199 chunks.
  Sweep on `cee_84`: 32 PDFs 2,371/2,371 >= 90%, 0 below. Remap of the 21 PDF chunk IDs in the
  answer key, verify_cee and open-citation: 19 unchanged, `SCHW-DECK-2026Q3#7` keeps its ID (now
  also holds the p4 sentence that sits on p5), `SCHW-DECK-2026Q1#40` -> `#44` (same text, only
  in `expected_chunks.yaml` Q25 must_not_return). `remap` got a "contains the old text" rule and
  a stricter split rule (the first version listed every chunk sharing common words). Mock eval
  after: 30/30 UNCHANGED (28 PASS, 2 FAIL Q15/Q19 as before, tier-1 recall 0.796); 8 questions
  retrieve different IDs, mostly renumbered chunks. pytest 350 passed.
- 2026-11-08 19:10 - the 15 manifest PDFs not in `cee_84` (#146 decks, #147 supplements and
  monthlies, FINRA-OVERSIGHT, MS strategic update) loaded from the cache (all hits). Box `parsed/`:
  all 47 manifest PDFs have `-doc.json` and `-v2.json`. Sweep on `cee_84`, 47 PDFs: 3,568/3,568
  >= 90%, 0 PASS-SAMEPAGE, 0 MISPLACED (no follow-up issue needed); 16 #77/#78 PDFs 1,069/1,069.
  verify-cee `--source-db cee_84 --port 8684`: VERIFY PASS, every feature PASS except open-citation
  UNREACHABLE at its last step (cite-date: no `date_basis = 'retrieved'` document in the 10-29
  snapshot, also 0 in `cee`); its five PDF page checks PASS (SCHW-DECK-2026Q2#53 p29,
  MS-SUPP-2026Q3#16 p8, ...). Run `.verify-runs/20261108-160258-f6d02b8`. `cee` unchanged: 111 docs,
  17,183 chunks, corpus-2026-10-29. `expected_results.md`, `verify_cee.py` samples and
  `open-citation.md` needed no ID change. 0 real calls.
