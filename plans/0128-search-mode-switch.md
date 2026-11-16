# 0128 - Search mode switch: Exact match / Smart search

Issue: #128    Role: U1    Spec: specs/ui.md    Branch base: exp/hybrid (ADR-010; PR targets exp/hybrid)

## Goal
In the sidebar the user picks Exact match or Smart search; the answer says which mode found it,
and the mode is kept with the query and its feedback.

## Files to change
- src/cee/app/views/ask_page.py - `search_mode_sidebar` (default from RETRIEVAL_MODE, locked on Exact match when vectors are off), mode passed to `ask(..., mode=)`, "Found with" + meta label, trace says "(Smart search)", plain error if Smart search setup is incomplete
- tests/test_search_mode.py - default, two modes only, plain labels, no internal words
- scripts/verify_cee.py - `--mode` launches the app in that mode; new feature `search-mode`
- .claude/skills/verify-cee/features/search-mode.md, README.md

## Steps
1. Switch and labels in the Ask page only; no retrieval change (TL), no schema change.
2. Mode with feedback: `query_log.filters` already stores `retrieval_mode`; feedback links by `query_id` (no new column).
3. Tests; verify in fts mode; hybrid mode needs the vectors setup (docs/RUN.md).

## Acceptance
- [ ] Same question in both modes shows both answers with their mode labelled (fts shown; hybrid needs vectors)
- [x] verify-cee PASS in fts mode, plus the new mode-label check
- [ ] verify-cee PASS in hybrid mode (vectors not set up on this machine; TL offered to run it)
- [x] With CEE_VECTORS off Smart search is disabled with one help line; no crash
- [x] No "hybrid", "rerank", "FTS" in UI text; 0 real model calls

## Progress log
- 2026-11-16 - plan written, implemented
- 2026-11-16 - pytest 404 passed; verify-cee --mode fts: 9 PASS, open-citation UNREACHABLE on cite-date only (no retrieved-dated doc in corpus-2026-10-29) (run 20261116-103442-0107c7e); search-mode PASS (run 20261116-103531-0107c7e)
