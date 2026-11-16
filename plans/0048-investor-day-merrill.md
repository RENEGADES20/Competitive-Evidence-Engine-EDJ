# 0048 - Investor-day / strategy decks and Merrill newsroom releases

Issue: #48    Role: C2    Spec: specs/transcripts-ir.md

## Goal
The latest investor-day or strategy deck for MS, SCHW, BAC and RJF is stored with page
numbers, and every Merrill-specific newsroom release from 2026-08-01 to 2026-10-30 is stored
as entity MER, so Q1, Q4, Q8, Q9 and Q27 can retrieve them. EDJ has no deck (reason in PR).

## Files to change
- data/manifest.csv - add 5 rows:
  - MS-DECK-2026-strategic-update (deck, tier 3, published_at 2026-01-15)
  - SCHW-DECK-2026-investor-day (deck, tier 3, 2026-05-14; date from the events page, the cover shows the year only)
  - BAC-DECK-2025-investor-day (deck, tier 3, 2025-11-05; GWIM section PDF, entity BAC)
  - RJF-DECK-2025-investor-day (deck, tier 3, 2025-06-05; web.archive.org copy of the IR PDF).
    Changed during work: the 2026 Analyst & Investor Day (2026-05-27) has no PDF (IR site: video and
    slide viewer only; 8-K Ex.99.1 is 128 slide images with hidden text), so the 2025 deck is the
    latest one available as a PDF. Cover reads "JUNE 5, 2025".
  - MER-PR-2026-09-15-01 (press, tier 3, entity MER, 2026-09-15)
  All rows: date_basis=source, period_end empty, exact source URL, storage_path raw/<doc_id>.<ext>,
  added_by C2, added_at 2026-10-30, publisher empty.
- scripts/convert_press_web.py - new, C2-owned. Converts a saved newsroom HTML page to
  <doc_id>.txt (article body via cee.ingest.webpage.article_text). Checks that the date line
  matches published_at and that no markup or nav text is left (pattern: scripts/convert_transcript_web.py).
  This avoids changing load.py, which would otherwise chunk the page chrome of a .html press page.
- plans/0048-investor-day-merrill.md - this plan.
Raw files (PDFs, .txt) are NOT committed; they go to the TL via the Box upload link.

## Steps
0. Environment (once, user approves each):
   - Box: Make Available Offline for EDJ/raw, parsed, snapshots (user, in Finder).
   - pip install -r requirements.txt and -r requirements-ingest.txt (docling==2.131.0, torch).
   - docker compose up -d --wait (pgvector image).
   - bash scripts/restore.sh <Box>/snapshots/corpus-2026-10-29.dump.
   - cee.smoke PASS, pytest -q, verify_cee.py doctor.
   - Copy deck/supplement PDFs from Box raw/ into data/raw/ so the source viewer and verify can open them.
1. Baseline (before any new doc): eval_run --questions Q1,Q4,Q8,Q9,Q27 --as-of 2026-10-30
   --out .eval-runs/48-before; full bank baseline; explicit Q8 and Q27/Q4 checks (expected: Q8 has no
   RJF deck chunk, Q27 has no MER chunk).
2. One deck end to end: MS (21 pp). Download to data/raw/, record sha256, add the manifest row,
   bash scripts/ingest.sh --doc MS-DECK-2026-strategic-update. Confirm the log says
   "parsing with docling", 0 chunks with page NULL, and pages-with-chunks / total pages.
3. The rest: SCHW (187 pp, slow docling parse), BAC GWIM, RJF (user downloads the PDF from the
   IR presentations page in a browser). Same checks per deck.
4. Merrill: fetch the 2026-09-15 release (honest UA, delay) into data/interim/, convert with
   scripts/convert_press_web.py to data/raw/MER-PR-2026-09-15-01.txt, read the text, then add the row and load it.
   Confirm entity_id=MER, date_basis=source.
5. Page spot-check: pick 10 investor-day chunks (2-3 per deck, including tables and picture
   slides); word-share check >= 80% on the PDF page; open each via ?chunk=<id> in the app
   (verify_cee.py launch) and screenshot "Page N of M".
6. After checks: Q8 and Q27/Q4 explicit checks; eval_run with --baseline (5 questions + full
   bank, look for REGRESSED); pytest -q; verify_cee.py run and confirm SUMMARY shows PASS for all 7
   features (UNREACHABLE is not a pass).
7. /finish-task: PR with "Part of #48" or "Closes #48", per-deck table (cover, published_at,
   chunks, pages), MER count = 1 with routing reasons, EDJ reason, raw-file list for TL, 0 real calls.

## Acceptance
- [x] One deck per firm or a written reason: MS, SCHW, BAC, RJF stored; EDJ reason in PR;
      published_at = event date from the source. (RJF: 2025-06-05 deck, the 2026 event has no PDF.)
- [ ] Deck chunks keep page numbers: 0 chunks with page NULL; 10 citations open on the right page
      (word share >= 80% and app caption "Page N of M" matches), table in PR.
      PARTLY: 0 NULL pages; caption and page image right for 10/10; word share >= 80% for 9/10
      (SCHW-DECK-2026-investor-day#46 p28: 68%, block spans p28-29). 4% of all new deck chunks.
- [x] Merrill releases stored as entity MER, not BAC: SELECT shows MER-PR-* with entity MER;
      count in PR = 1 for 2026-08-01..2026-10-30, with the 4 GWIM items listed as BAC#GWIM (not ingested).
- [x] Q8 retrieval returns SCHW and RJF deck chunks (explicit top-20 check, mock).
- [x] Q27: at least 1 MER chunk, no untagged BAC, nothing before 2026-01-01. Q4: MER:press hit, 0 forbidden hits.
- [ ] Q1/Q9: MS:deck moves from "not in corpus" to hit / no hit; no REGRESSED in full-bank eval_run.
      PARTLY: MS:deck hit in Q1 and Q9 (Q9 IMPROVED). 7 rows REGRESSED but still PASS (Q1, Q10, Q11,
      Q17, Q22, Q23, Q28): slot competition under K=20, S1's area (see Progress log).
- [x] pytest -q passes; verify_cee.py run: all 7 features PASS.
- [x] 0 paid API calls.

## Risks (report, do not fix here)
- Q8 RJF may still miss: FLOOR = 0.3 per firm and no synonyms ("RIA", "independent contractor")
  are S1's area. Report the rank ratio.
- BAC GWIM deck chunks are tagged GWIM only if slide titles match segment aliases (C1, #37).
- Registry rows (config/source_registry.csv, C1) still say TODO-verify for these URLs; suggest an update.

## Progress log
- 2026-10-30 15:15 - plan written; sources verified on 2026-10-30.
- 2026-10-30 15:20 - env: installed requirements + requirements-ingest (docling 2.131.0, torch 2.15.0),
  cee-db on pgvector image, restored corpus-2026-10-29 (111 docs). smoke PASS, pytest 231 passed,
  verify doctor PASS. Baseline: eval_run 5/5 PASS (full bank 27/30), but explicit Q8 (no RJF deck),
  Q27 and Q4 (no MER chunk) FAIL as expected.
- 2026-10-30 15:20 - surprise: docling crashes on macOS 14 (torch MPS: "-[MPSNDArray
  initWithBuffer:offset:descriptor:]: unrecognized selector"). Fixed without code: run ingest with
  DOCLING_DEVICE=cpu (docling AcceleratorOptions env setting). MS deck parses in ~17 s on CPU.
- 2026-10-30 15:30 - loaded MS (37 chunks, 21/21 pages), BAC GWIM (134 chunks, 39/41 pages), SCHW
  (287 chunks, 178/187 pages); 0 chunks without a page. BAC: only 6 of 134 chunks tagged GWIM/Merrill
  (slide titles do not match segment aliases) - report to C1, not fixed here.
- 2026-10-30 15:35 - Merrill: newsroom HTML holds the release twice and spells abbreviations twice for
  screen readers, so webpage.article_text output was noisy; wrote scripts/convert_press_web.py.
  MER-PR-2026-09-15-01 loaded as MER (4 chunks). Q27 and Q4 explicit checks now PASS.
- 2026-11-01 14:10 - RJF: user found no PDF for the 2026 investor day (video/slides only). EDGAR 8-K
  Ex.99.1 is 128 JPG slides plus hidden per-slide text; tried rebuilding a PDF from it (image + text
  layer, image + visible text, text only) but pdf.py/docling kept only 38-75% of the words. User chose
  the 2025-06-05 deck (Wayback copy, 118 pp): 141 chunks, 105/118 pages, 0 without a page.
  Q8 explicit check now PASS (SCHW #16, #199; RJF #106, #38).
- 2026-11-01 14:20 - page check: 10 chunks (2-3 per deck) opened via ?chunk= in the verify app: caption
  "Page N of M" and one page image for all 10. Words on the page >= 80% for 9/10; SCHW #46 (p28) 68%:
  one sentence is from p29 (docling block spanning two slides stored under its first page, as in #78).
  Across all new deck chunks: 21 of 528 judged chunks (4%) below 80% on their page (SCHW 18, RJF 3,
  MS 0, BAC 0). Not fixed here (pdf.py prov[0]; follow-up).
- 2026-11-01 14:25 - pytest 231 passed; verify_cee.py run: all 7 features PASS, 0 FAIL steps
  (.verify-runs/20261101-141917-ea7d5ac). eval_run full bank vs baseline: 27/30 PASS before and after,
  traps Q4/Q27/Q30 unchanged, 0 forbidden; IMPROVED Q8, Q9; REGRESSED (still PASS) Q1, Q10, Q11, Q17,
  Q22, Q23, Q28. Diagnosed per question: re-running select() on the live pool without the 5 new docs
  reproduces the before top-20 exactly, so every change is slot competition under K=20 (MER gets its own
  turn and 0.3 floor next to BAC-GWIM; a new deck type takes a turn per firm) - S1's area. One
  must_return chunk lost: BAC-10K-2025#246 (Q11). Noise to note: MS End Notes pp.18-20, RJF bios, BAC
  forward-looking pages.
