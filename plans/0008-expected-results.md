# 0008 - Expected retrieval results for 5 Tier-1 questions

Issue: #8    Role: S1    Spec: specs/retrieval.md

## Goal
For Q1, Q4, Q11, Q22 and Q26, write down by hand which documents and sections retrieval
should return, and which it must not return, so later retrieval changes can be scored
against it ("hit rate vs expected sources", specs/retrieval.md).

## Files to change
- `evals/expected_results.md` (new) - one section per question: expected documents and
  sections, must-not-return list, corpus status, what retrieval returns today.
- `plans/0008-expected-results.md` (new) - this plan.
- Not changed: `evals/questions.yaml` (append-only, owned by C1). `docs/PROGRESS.md` is
  filled by the bot from the PR's `## Progress line` (CLAUDE.md).

## Steps
1. One block per question with target documents, named by the doc_id conventions in
   `specs/filings.md` (`<ENTITY>-<FORM>-<PERIOD>`) and `specs/transcripts-ir.md`
   (`MS-TR-2025Q2`, `...-DECK-...`, `...-PR-YYYY-MM-DD-NN`), following `expected_sources`.
2. Name the sections that must come back.
3. Must-not-return list (trap Q4: BAC chunks without a GWIM/Merrill segment; Q26: older
   than 90 days).
4. Check against the real corpus (corpus-2026-09-30): which expected chunks exist, and what
   `resolve()` + `search()` return today.
5. Mark documents not yet loaded; section names and dates not checked -> `TODO-verify`.
6. Refresh against the 25 filings now in `data/manifest.csv` (10-K + four 10-Qs per firm,
   Item sections from #70): parse the raw files from Box with the repo's own splitter in a
   read-only scratch script (no DB writes, no raw files in git). For each "not loaded"
   10-K/10-Q row, replace the proposed name with the real `doc_id`, the real Item section
   and a quoted phrase; add the 10-Qs the questions need (Q22 per quarter, Q26 window);
   resolve `TODO-verify` items the filings answer. Transcript/deck/press/trade rows stay
   `not loaded`.

## Acceptance
- [x] All 5 questions (Q1, Q4, Q11, Q22, Q26) list concrete expected documents.
- [x] Trap included: Q4, with a must-not-return list for BAC chunks without GWIM/Merrill.
- [x] Each document marked in corpus / not loaded; EDJ entries checked with real queries.
- [x] Every cited chunk ID (83) exists in a database loaded from main's manifest (68 documents).
- [x] Today's retrieval run recorded per question (Q26: 7 of 8 hits outside the window).
- [x] No invented entity facts; unknowns marked `TODO-verify`.
- [x] `git diff main -- evals/questions.yaml` -> empty.
- [x] `.venv/bin/python -m pytest -q` -> all pass (no code changed).

## Progress log
- 2026-10-01 - plan written and approved.
- 2026-10-15 - branch s1/8-expected-results from main (47 commits newer). Rules changed:
  PROGRESS.md now filled by bot from PR "Progress line"; verify-cee only for src/config/db.
- 2026-10-15 - Corpus still one document (EDJ-10K-2025, 335 chunks). Found EDJ targets:
  #130 (highlights table: NNA + advisor count, footnote (2) defines NNA), #131, #148, #29.
- 2026-10-15 - Surprise: EDJ-10K-2025 gives "Financial advisors (actual)" but no
  include/exclude definition. Recorded as TODO-verify for C1 (Q11), not guessed.
- 2026-10-15 - Ran today's retrieval: Q11/Q22 resolve to no entities ("each of the five"
  is not mapped) and Q11 misses #130; Q26 has no time window in Query. Logged as findings
  for follow-up retrieval issues, not fixed here (out of scope).
- 2026-10-16 10:16 - merged main into the branch (Item sections #70, Query.firms #50 now
  in). Manifest now lists 25 filings (10-K + 4 10-Qs for EDJ, MS, SCHW, BAC, RJF); raw files
  are on Box, local DB still holds only EDJ-10K-2025. Added step 6: refresh the "not loaded"
  10-K/10-Q rows against those filings. Q26 window as of 2026-10-16 starts 2026-07-18.
- 2026-10-16 10:24 - step 6 done. Parsed all 25 manifest filings from Box with the repo's
  parser + Item splitter (12,097 chunks, same as #70; EDJ IDs #130/#131/#148/#29 unchanged);
  installed requirements-ingest.txt into .venv for edgartools. All 41 chunk IDs cited in
  expected_results.md exist. Surprises: BAC filings have no Merrill advisor count and no
  NNA line; MS and SCHW filings have no advisor count; BAC-10K-2025#18 (BAC-wide hiring of
  18,000) is the concrete Q4 trap chunk; every BAC chunk has segment None until #37, and
  BAC-10K-2025#1041 mixes GWIM and Global Banking. Q26 as of 2026-10-16: only
  RJF-10Q-2026Q2 is in the window. questions.yaml unchanged; pytest 76 passed; no src/
  change, 0 paid calls.
- 2026-10-19 14:47 - main added transcripts, supplements, decks and earnings releases
  (#39, #45, #48, #75; manifest 25 -> 68 documents), so "not loaded" rows were stale.
  Merged main again and refreshed every question from the local DB loaded from main's
  manifest. New: MS transcripts carry the NNA framing (workplace / stock-plan IPOs) for Q1;
  BAC transcripts carry Merrill advisor commentary for Q4, but still no stored document
  gives a Merrill or MS advisor count; BAC reports net client flows / AUM flows, not NNA
  (Q22); Q26 window as of today (from 2026-07-21) holds 5 RJF documents, 4 of which leave
  it on 2026-10-21. Recorded today's retrieval runs: Q26 returns 7 of 8 chunks older than
  the window; Q11 returns 0 expected chunks and 3 BAC chunks outside GWIM; Q4 returns
  nothing (no segment tags yet). Caught one misread: in RJF decks the value comes before
  its label. 83 cited chunk IDs all exist; pytest 106 passed; 0 paid calls.
