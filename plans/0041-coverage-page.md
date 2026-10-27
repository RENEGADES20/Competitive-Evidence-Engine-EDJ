# 0041 - Coverage page

Issue: #41    Role: U1    Spec: specs/ui.md

## Goal
A user opens Coverage and sees, per core firm and per document type the source registry expects, how many documents are stored and the date range; empty and thin combinations stand out.

## Files to change
- src/cee/app/views/coverage_page.py - grid from `documents` and `source_registry`; thin rule from `expected_cadence`
- src/cee/app/components.py - `coverage_grid`, table CSS; cells accept line breaks
- scripts/verify_cee.py, .claude/skills/verify-cee/ - `coverage` driver and recipe
- docs/DESIGN.md - coverage grid component; Coverage no longer a placeholder
- tests/test_coverage.py - states, counts, dates, not-tracked cells

## Steps
1. Count and date-range query per entity and doc_type; check against psql.
2. Build the grid (EDJ, MS, SCHW, RJF, MER, BAC filings) with covered / thin / empty cells.
3. Driver and recipe; run verify_cee.py run.

## Acceptance
- [x] Linked questions: none directly (supports all)
- [x] Covers EDJ, MS, SCHW, MER, BAC filings (labelled) and RJF, every registry-expected doc type
- [x] Each combination shows count and earliest/latest published_at
- [x] Empty and thin cells visibly distinct; thin threshold from the registry cadence (`COVERED_MIN`)
- [ ] On corpus-2026-09-30: EDJ 10-K = 1, all others empty (that snapshot is not restored here; checked on corpus-2026-10-18 instead)
- [x] Says themes are not shown yet
- [x] `verify_cee.py run` all PASS incl. `coverage`

## Progress log
- 2026-10-27 - plan written
- 2026-10-27 - built; cells reformatted to three short lines after the first screenshot wrapped dates; verify-cee 7/7 PASS, pytest 174 passed
- 2026-10-27 - TL review fixes: rows come from `config/entities.yaml` (adding a firm is config,
  CLAUDE.md); "thin" follows the registry's `expected_cadence` (one annual 10-K is covered, three
  quarterly transcripts are thin) instead of one constant; MER's note counts BAC GWIM-tagged
  chunks (same rule as the retrieval filter); stale notes about #37 and #6 removed. pytest 200 passed.
