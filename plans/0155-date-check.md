# 0155 - Flag a claim whose stated period does not match the cited document

Issue: #155    Role: S2    Spec: specs/answer-citations.md

## Goal
A claim that dates itself with a month and year ("quarter ended September 2025", "as of
December 31, 2025", "published October 2026") is checked against the cited documents. A
mismatch flags the claim `date_mismatch`: flagged, never dropped, shown next to the claim like
`number_not_found`. Option 1 of the issue (code check, no model call), decided with S2.

## Rule
| Claim says | Compared with | Result |
|---|---|---|
| "quarter / period / year / months / fiscal year ended <Month> [day,] YYYY", "as of <Month> [day,] YYYY" | a cited document's `period_end` or `published_at` (year + month) | no match: `date_mismatch` |
| "published [in] <Month> [day,] YYYY" | a cited document's `published_at` (year + month) | no match: `date_mismatch` |
| the same month and year appear in a cited chunk's text (a comparative column) | chunk text | match |
| several cited documents | any one matching is enough | |
| "3Q26", "fiscal 3Q25" | not checked (fiscal vs calendar quarters, e.g. RJF's year ends in September) | known limit |

## Files to change
- `src/cee/answer/validate.py` - `check_dates()`, called in `check_citations` after `check_numbers`
  (no change to `ask.py`)
- `specs/answer-citations.md` - "Date check" section
- `tests/test_validate.py` - Q29 A4's real text plus one test per rule row

## Steps
1. Tests first.
2. `check_dates()`.
3. Free: the cached real answers (#61, #118; 6 questions, Q19 shared): Q29 A4 flagged, nothing else; 30 mock questions: 0.
4. pytest, smoke, verify-cee; rule into the spec.

## Acceptance
- [x] Q29 A4 (saved output) is flagged `date_mismatch`
- [x] Mock tests; 0 real calls
- [x] No other cached real answer or mock answer flagged; `pytest -q` and verify-cee pass

## Progress log
- 2026-11-16 - plan approved by S2: option 1, flag only
- 2026-11-16 14:30 - `check_dates()` in validate.py, called from `check_citations` after the number
  check; 6 tests (Q29 A4's real text first). pytest 371 passed
- 2026-11-16 14:35 - free check: cached real answers from #61 and #118 (6 questions, 40 claims):
  only Q29 A4 flagged; 30 mock questions: 87 claims, 0 flagged. 0 real calls
- 2026-11-16 14:45 - smoke PASS; verify-cee 8 PASS + open-citation UNREACHABLE (cite-date needs a
  date_basis='retrieved' document, not in corpus-2026-10-29; same precondition as in #172).
  Evidence .verify-runs/20261116-004217-8f92cb1. Rule written to the spec
