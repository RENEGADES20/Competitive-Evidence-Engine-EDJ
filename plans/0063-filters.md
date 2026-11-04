# 0063 - Filters: company, date range, keywords

Issue: #63    Role: U1    Spec: specs/ui.md, specs/retrieval.md

## Goal
On the Ask page a user narrows a question to chosen firms, a published-date range and keywords;
retrieval only searches matching passages, as SQL `WHERE` clauses (no prompt text).

## Files to change
- src/cee/retrieve/fts.py - `Query` gains `firm_filter`, `date_range`, `keywords`; `apply_filters`, `filters_sql`; `search` adds the clauses (S1 area: new fields only, existing behavior unchanged)
- src/cee/ask.py - `ask(..., filters=)`; trace line lists filters; query_log stores dates as ISO text (dates failed the JSON dump, also for time-window questions)
- src/cee/app/views/ask_page.py, src/cee/app/streamlit_app.py - live sidebar filters on Ask (placeholder removed); meta line lists filters
- docs/DESIGN.md - placeholder note
- tests/test_filters.py - SQL clauses and fixture-row checks
- scripts/verify_cee.py, .claude/skills/verify-cee/features/filters.md, features/README.md - `filters` feature

## Steps
1. Query fields and SQL clauses; firms intersect with firms the question names (empty -> no evidence, never every firm).
2. Sidebar controls on Ask; pass into `ask`.
3. Tests; verify driver reads cited chunks back from the database.

## Acceptance
- [x] Company filter: no hit from another entity (driver reads back cited chunks; MER keeps only BAC GWIM in tests)
- [x] Date range: no hit outside the range (both ends inclusive; download-dated documents left out)
- [x] Filters are SQL `WHERE` clauses; prompt.py does not read them
- [x] `verify_cee.py run filters` PASS and all others PASS
- [x] Linked questions Q26, Q27: window tests unchanged and passing; mock only, 0 real model calls

## Progress log
- 2026-11-03 - plan written, implemented
- 2026-11-03 - pytest 265 passed; verify-cee all 8 features PASS (run 20261103-101820-f336093); 0 real model calls
- 2026-11-03 - TL: merged main after #148; theme research query now gets the filter clauses too (missing kwarg raised KeyError on entity+theme questions); firm filter drops firm-less research; 2 tests in test_retrieval_themes.py
