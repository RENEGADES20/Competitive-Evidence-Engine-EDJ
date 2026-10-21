# 0037 - Tag BAC chunks in the GWIM section with segment GWIM

Issue: #37    Role: C1    Spec: specs/filings.md, specs/retrieval.md

## Goal
BAC chunks from the GWIM part of the 10-K, 10-Qs, decks and supplements carry `segment = GWIM`,
and nothing else does, so the Merrill filter (`entity=BAC` and `segment` in GWIM/Merrill) only
ever sees GWIM text. Tagging is driven by config; another firm needs only config.
Rule throughout: untagged beats mis-tagged.

## Files to change
- `src/cee/ingest/chunk.py` - new `SegmentTagger`, used as `segment_for` by `chunk_sections`
  (which now also passes the page).
- `src/cee/ingest/load.py` - build one tagger per document from the entity's config.
- `config/entities.yaml` - new optional `segment_stops` (headings that end a segment without
  tagging); BAC: Consumer Banking, Global Banking, Global Markets, All Other.
- `tests/test_segment.py` - fixture tests, including a made-up firm configured only by config.

## Steps
1. Find where GWIM starts and ends in the stored BAC chunks. Found: a line that is only
   "Global Wealth & Investment Management" starts it and a line that is only "Global Banking"
   ends it (10-K Item 7 #243-#249, 10-Q 2026Q2 Item 2 #83-#93); the heading lands at the end of
   the previous chunk.
2. Fixture tests first, then `SegmentTagger`: a chunk takes the segment in force at its first
   line; the segment resets at each new section (and page).
3. Decks and supplements: a section titled with an alias is tagged whole, except on pages with
   titles of two segments (multi-column slides, BAC-DECK-2026Q1 p19).
4. A chunk with another segment's heading in the middle and text after it is left untagged
   (BAC-10K-2025#1041, segment note: GWIM then Global Banking).
5. Reload BAC, run the acceptance SQL, spot-check 20 chunks, run Q4/Q27/Q30 retrieval, verify-cee.
6. Press releases and transcripts have no heading lines: out of this PR, moved to #95.

## Acceptance
- [x] Linked questions: Q4, Q27, Q30 retrieval returns no BAC chunk without a GWIM/Merrill segment
- [x] Spec: spot-check 20 BAC chunks in GWIM sections, 0 wrong; IDs listed in the PR
- [x] `SELECT doc_id, segment, count(*) FROM chunks WHERE doc_id LIKE 'BAC-%' GROUP BY 1, 2`:
      GWIM > 0 for every BAC SEC filing (10-K, 10-Q)
- [x] Another firm needs only config (fixture test)
- [x] `pytest -q` passes; `verify_cee.py run` PASS

## Progress log
- 2026-10-20 - Section headings printed; GWIM boundaries found in 10-K Item 7 / 10-Q Item 2.
  This plan was not written up front (TL asked for it in review); the entries below are
  reconstructed from the PR and session.
- 2026-10-20 - Fixture tests written, `SegmentTagger` + `segment_stops` implemented, wired into
  load.py. First reload: 10-K/10-Q tagged, decks/supplements 0 because their heading is the
  section title, not a text line -> added section-title rule.
- 2026-10-21 - Agreed with TL: "every BAC filing" = SEC filings; decks/supplements kept; PR/TR
  moved to #95.
- 2026-10-21 - First spot-check found BAC-DECK-2026Q1#34 wrong (Consumer Banking text under the
  GWIM column heading of a multi-segment slide) -> mixed-page rule; also reset on page change.
  Re-check: 20/20 right. PR #96 opened. Merged origin/main (import conflict in load.py).
- 2026-10-21 - Q4/Q27/Q30 retrieval: 0 BAC chunks without GWIM. verify-cee PASS.
- 2026-10-21 - TL review: BAC-10K-2025#1041 mis-tagged (GWIM paragraph, then "Global Banking"
  heading and Global Banking text in the same chunk; I had only read its start). Added the
  mid-chunk heading rule + test. 10-K GWIM 7 -> 6. Scanned every GWIM chunk for a segment
  heading after line 1: only 5 hits, all with "Global Banking" as the last line (allowed).
  Q30 now has 0 hits (its only hit was #1041) - retrieval recall, for S1.
