# 0070 - Item sections for BAC, SCHW and MS filings

Issue: #70    Role: C1    Spec: specs/filings.md

## Goal
Every 10-K and 10-Q chunk of the five filers sits in a real Item section (`Item 1`,
`Item 1A`, `Item 7`, ...) instead of one "Document" section, so GWIM tagging (#37) has an
Item 7 boundary to work inside and the source page shows where a passage comes from.

## Files to change
- `src/cee/ingest/chunk.py` - `split_10k_sections`: match `Item 1.` in any case; skip
  table-of-contents lines and "Item 1. Business, continued" page headers; fall back to
  the cross-reference table of contents (title -> Item column) for filers like MS that
  print no "Item" headings.
- `tests/test_chunk.py` (new) - small text fixtures for each layout.
- `plans/0070-item-sections.md` - this plan.

## Steps
1. Measure the parsed text of all 25 documents: which heading forms appear, where the table
   of contents sits, which lines are page headers.
2. Item headings, any case. A heading line is skipped when it is a table-of-contents entry:
   a column gap of 3+ spaces or a trailing page number, or an entry that sits just before
   another table-of-contents entry (BAC 10-Q prints "Item 2. Management's Discussion ..."
   with no page number). Lines ending in "continued" are page headers, not headings.
3. Cross-reference fallback (no Item headings at all): read table-of-contents rows that
   carry an Item column ("Risk Factors   1A 13"); find each title as a whole line after the
   table of contents, in table order; when a title has no heading line (MS 10-Q "Consolidated
   Financial Statements and Notes"), use the next row's title.
4. Fixture tests for: mixed case, upper case, TOC skipping, page headers, 10-Q Part I/II
   repeats, cross-reference layout, no headings -> "Document".
5. Check EDJ and RJF splits against the old splitter: chunk IDs must not change (the
   verify recipe opens `EDJ-10K-2025#58`).
6. Reload all 25 documents, paste section counts per document, run `pytest -q` and
   `scripts/verify_cee.py run` with `LLM_PROVIDER=mock`.

## Acceptance
- [ ] Linked questions: Q4, Q27, Q30 (through #37: BAC Item 7 boundary exists)
- [ ] BAC and SCHW: Item sections in every 10-K/10-Q (counts per document in the PR)
- [ ] MS: Item sections from the cross-reference table, or one section with a written reason
- [ ] EDJ and RJF chunk IDs unchanged (old vs new split compared)
- [ ] `pytest -q` passes; `scripts/verify_cee.py run` PASS with `LLM_PROVIDER=mock`, 0 paid calls

## Progress log
- 2026-10-15 23:40 - plan written. Measured: BAC/SCHW use "Item 1." (BAC 10-K 46 lines
  incl. TOC), EDJ has 100+ "Item 1. Business, continued" page headers, MS has none but its
  TOC has Part/Item/Page columns and each Item title appears once as a body line.
- 2026-10-15 23:55 - splitter done. Old vs new split on all 25 parsed texts: EDJ and RJF
  chunk lists identical (so `EDJ-10K-2025#58` keeps its ID); BAC/SCHW/MS now split.
  Surprise: MS 10-Q TOC says "Consolidated Income Statement (Unaudited)" but the body drops
  "(Unaudited)", so title matching ignores a trailing parenthetical.
- 2026-10-16 00:20 - reloaded 25 documents (12,097 chunks, 0 in "Document"); pytest 76 passed;
  verify_cee run all PASS (mock, 0 paid calls). Note for #37: BAC GWIM text sits in Item 7
  (10-Q Item 2) and in the segment note of Item 8 (10-Q Item 1), so #37 still needs the GWIM
  sub-heading inside those Items. Follow-up: 10-Q Part I and Part II both have "Item 1"/"Item 2";
  labels do not say which Part.
