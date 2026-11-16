# 0062 - Feedback on answers, stored with the query

Issue: #62    Role: U1    Spec: specs/ui.md

## Goal
Under an answer a user rates it (Helpful / Not helpful) and may comment; one `query_feedback`
row is stored against the answer's `query_log` row.

## Files to change
- src/cee/feedback.py - `save_feedback(query_id, rating, comment)`; one row per query, a second send replaces it
- src/cee/app/views/ask_page.py - answer kept in session state so it survives the form rerun; `feedback_form` replaces the #67 placeholder
- docs/DESIGN.md - feedback form, no placeholders left
- tests/test_feedback.py - save, replace, other queries untouched, bad rating
- scripts/verify_cee.py, .claude/skills/verify-cee/features/feedback.md, features/README.md - `feedback` feature

## Steps
1. Storage with the duplicate rule (delete + insert in one transaction, advisory lock per query).
2. Form under the meta line; keep the last answer on reruns.
3. Tests; verify driver sends twice and reads `query_feedback` back.

## Acceptance
- [x] Rating and optional comment write one `query_feedback` row with the right `query_id` (driver reads it back)
- [x] Submitting twice does not duplicate: the latest replaces the earlier row, and the message says so
- [x] `verify_cee.py run feedback` PASS and all others PASS
- [x] Linked questions: all (feedback is per query); mock only, 0 real model calls

## Progress log
- 2026-11-05 - plan written, implemented
- 2026-11-05 - pytest 280 passed; verify-cee all 9 features PASS (run 20261105-101539-9dc4c9b); 0 real model calls
