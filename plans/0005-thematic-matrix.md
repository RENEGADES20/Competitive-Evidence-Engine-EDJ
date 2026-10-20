# 0005 - Feasibility matrix: tier 5 thematic research

Issue: #5    Role: C3    Spec: specs/thematic.md

## Goal
`docs/source_matrix.csv` holds one row per tier 5 source for the thematic questions (Q16-Q21):
access route, cost, terms, cadence, earliest edition and where the date is, so #81 can ingest
from it. Every seed theme and Q16-Q21 is covered. Nothing is ingested. Cerulli library access
gets a written answer.

## Files to change
- `docs/source_matrix.csv` - tier 5 rows (`tier=5`, `owner=C3`, `entity_id=THEME`,
  `doc_type=research`). Per the TL comment on #5, tier 5 goes in this same matrix.
- `docs/SOURCE_MATRIX.md` - a "Tier 5 (C3)" section: how to read the rows, coverage per theme
  and per Q16-Q21, the Cerulli library answer, considered-and-rejected sources.
- `tests/test_source_matrix.py` (C2's file; noted in the PR) - smallest change that lets tier 5
  rows in: tier 5, owner C3, entity THEME; tier 5 iff doc_type research. Tier 3-4 checks
  unchanged. One new test: every seed theme has a tier 5 row.

## Steps
1. Candidate list from `specs/thematic.md` "Institutional research publishers", plus
   Edward Jones / Age Wave studies and CFP Board consumer research.
2. Check each on the live site: url, sample report url, access, cost, terms url and read date,
   format, cadence, earliest edition, date field; for surveys the sample in `notes`.
   ADR-007 settles storage, so terms columns record what the site says and cite T-08/ADR-007.
3. Cerulli: check the WashU Libraries database list; record the result (TL: no library email).
4. Tests; coverage tables; progress log.

Unsure / for review:
- `entity_id=THEME` follows `evals/questions.yaml` (`THEME:research`), but the manifest rule
  for tier 5 says `entity_id` empty. The matrix uses THEME as a grouping key only.
- Editing C2's test file: required by the TL's "same matrix" decision; C2 to be told.

## Acceptance
- [x] Tier 5 rows with access / cost / terms; each seed theme and Q16-Q21 covered (39 rows)
- [x] Rows for at least McKinsey, Goldman Sachs, FINRA and BofA (#81 minimum)
- [x] Library access to Cerulli answered in writing: Database Finder shows no Cerulli (2026-10-20); TL decided no library email is needed; free white papers are the route
- [x] Check: `.venv/bin/python -m pytest -q` -> 122 passed

## Progress log
- 2026-10-20 - plan written; branch c3/5-thematic-matrix created
- 2026-10-20 - 39 tier 5 rows added (22 research, 12 survey, 5 regulatory); all 8 seed themes have
  >= 2 publishers (new test). advisor_selection (merged in #65) used as a theme id.
- 2026-10-20 - Cerulli: WashU Database Finder returns 0 databases for "cerulli". Email to the business
  librarian drafted for the user to send; reply pending. WashU responsible-use guide (T-64) bars building
  our own database from licensed content: flagged in T-65 for the TL.
- 2026-10-20 - URL checker run on the tier 5 rows only (temp CSV, C2 rows untouched): 63 ok, 5 blocked,
  3 dead, 2 error, 1 moved. Dead DOL/CFA/Vanguard landing URLs replaced; Kitces now behind a login (noted).
- 2026-10-20 - Surprise: the DOL 1210-AC02 rule page is gone (rule vacated per trade press); kept as
  TODO-verify against the Federal Register.
- 2026-10-20 - TL: no email to the library needed. Cerulli answer recorded from the Database Finder;
  free white papers are the route. All acceptance items ticked.
