# 0050 - Footer and gap box agree on firms

Issue: #50    Role: S1    Spec: specs/retrieval.md (+ specs/ui.md, footer is in U1's view)

## Goal
When a question names a firm, the footer under the answer lists it, and it is the same firm
the gap box names, including known firms we hold no documents for (e.g. Vanguard).

## What's wrong (reproduced)
`resolve("What is Vanguard's advisor headcount?")` gives `entities=[]`, `unmapped=['VGD']`.
The gap box is built from `unmapped` (names Vanguard); the footer
(`src/cee/app/views/ask_page.py`) prints only `entities`, so it says `firms: none`.
Entity detection is correct; the footer reads only half of it.

## Files to change
- `src/cee/retrieve/fts.py` - add `Query.firms`: every firm the question names (covered
  first, then unmapped). Search filters unchanged.
- `src/cee/app/views/ask_page.py` - footer built from `query.firms`, firms without documents
  marked, e.g. `firms: VGD (no documents)`. U1's file: PR mentions both specs.
- `tests/test_validate.py` - Vanguard case: footer firms == gap firms == `['VGD']`; mixed
  question (Edward Jones + Vanguard); core-five firms resolve as before.
- `.claude/skills/verify-cee/features/gap-path.md` + `scripts/verify_cee.py` - `gap-footer`
  step: footer does not say `firms: none` on the gap question.

## Steps
1. Add `Query.firms` and the tests.
2. Switch the footer to it.
3. Add the verify step and recipe line.
4. `pytest -q`; `verify_cee.py run ask-answer gap-path`; core-five run; screenshot of the
   Vanguard question in the app (mock provider, 0 real calls).

## Acceptance
- [x] Test: Vanguard question -> footer firms == gap firms == `['VGD']`
- [x] Core-five questions unchanged (`entities` and retrieved chunks identical; search untouched)
- [x] `verify_cee.py run gap-path` PASS; `pytest -q` passes
- [x] Screenshot of U1's Vanguard question in the app

## Out of scope
- Gap wording (S2).
- `mode` is `"theme"` for a question naming only an unmapped firm; matches the spec rule,
  noted in the PR instead of changed.

## Progress log
- 2026-10-16 09:56 - plan written and approved; branch `s1/50-footer-firms` created
- 2026-10-16 09:56 - step 1 done: Query.firms (property, so query_log shape is unchanged) + 3 tests in tests/test_validate.py; pytest -q 79 passed
- 2026-10-16 09:58 - step 2 done: footer uses footer_firms(query) in ask_page.py (unmapped marked '(no documents)') + footer test; pytest -q 80 passed. App not checked yet (step 4)
- 2026-10-16 09:59 - step 3 done: gap-footer step in scripts/verify_cee.py + recipe line in features/gap-path.md; driver compiles, not yet run against the app (step 4)
- 2026-10-16 10:00 - step 4 done: pytest -q 80 passed; doctor PASS; verify_cee run ask-answer gap-path -> VERIFY PASS (new footer step: 'LPLA (no documents)'), evidence .verify-runs/20261016-095930-17cae93. Core-five: resolve + retrieved chunk_ids identical on main vs branch for one question per core firm + Vanguard (snapshot corpus-2026-09-30 holds EDJ docs only, so MS/SCHW/MER/RJF return 0 chunks on both). Vanguard question in app: gap 'no documents for Vanguard', footer 'firms: VGD (no documents)'; screenshot .verify-runs/20261016-095958-17cae93/issue-50/vanguard.png. Mock provider, 0 real calls.
- 2026-10-16 10:02 - finish-task: full verify_cee run -> ask-answer, open-citation, gap-path, invalid-chunk PASS; download-document UNREACHABLE (raw EDJ-10K-2025.htm not in data/raw/, unrelated precondition); evidence .verify-runs/20261016-100229-17cae93
