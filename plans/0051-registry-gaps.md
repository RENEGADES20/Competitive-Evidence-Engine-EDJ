# 0051 - Name the missing source from source_registry in gap answers

Issue: #51    Role: S2    Spec: specs/answer-citations.md

## Goal
Gap answers name the registry sources that are expected for the firm but not yet in the corpus
(e.g. "Morgan Stanley Trade press", "Morgan Stanley Form ADV (SEC IAPD)"), computed by code.
If the registry is unavailable or the firm is not in it, they fall back to today's text.

## Files to change
- `src/cee/answer/validate.py` - `suggested_sources(entity_id)` = registry rows minus ingested doc
  types, with a swappable lookup (tests need no database) and a fallback; `fill_suggested_sources()`
- `src/cee/ask.py` (TL) - call `fill_suggested_sources()` after caveats
- `tests/test_validate.py` - fixture tests; existing tests pinned to the fallback

## Steps
1. Tests first: MS suggests 8-K, DEF 14A, deck, trade, ADV and not 10-K or supplement; an
   ingested type is never suggested; unknown firm or database error falls back without error;
   a Q29 gap answer (fixture) gets an MS registry source; a model-written source is kept.
2. Rewrite `suggested_sources()`.
3. `fill_suggested_sources()` in `ask.answer_for`: fills only empty `suggested_source`
   (S2 decision: the model's own text is kept, not appended to).
4. pytest, smoke, `verify_cee.py run gap-path` and all features; print the Q28/Q29 gap text
   from the live database.

## Acceptance
- [x] Q29 gap names at least one MS source from the registry (fixture test; live text in the PR)
- [x] A doc type already ingested is not suggested
- [x] Unknown entity falls back to the current text without error
- [x] `verify_cee.py run gap-path` PASS; `pytest -q` passes; mock only, 0 real calls
- Merrill uses only its own registry rows (press, trade, adv); BAC rows are not merged in.
- Out of scope: caveats, number check (#52), prompt changes.

## Progress log
- 2026-10-29 - plan approved by S2: code fills only empty suggested_source
- 2026-10-29 12:05 - steps 1-3 done: `suggested_sources()` reads source_registry minus ingested doc types (swappable `registry_lookup`, config fallback); `fill_suggested_sources()` in `ask.answer_for` fills only empty sources. Existing tests pinned to the fallback with an autouse fixture so they do not depend on a running database
- 2026-10-29 12:10 - two firms (Q28) now share one "Not yet in the corpus:" prefix. pytest 222 passed; smoke PASS; verify-cee all 7 features PASS (.verify-runs/20261029-121016-685beba), mock, 0 real calls. Live Q29: "Not yet in the corpus: Morgan Stanley Form 8-K current report (SEC EDGAR); Morgan Stanley Form ADV (SEC IAPD); Morgan Stanley Investor-day presentation; Morgan Stanley Proxy statement (SEC EDGAR); Morgan Stanley Trade press (tier 4, docs/BRIEF.md)"
- Found: registry trade rows read "Trade press (tier 4, docs/BRIEF.md)" in source_name (C1 data); left as is
