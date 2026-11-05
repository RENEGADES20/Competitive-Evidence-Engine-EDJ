# 0052 - Flag numbers that do not appear in the cited chunk

Issue: #52    Role: S2    Spec: specs/answer-citations.md

## Goal
Every number in a claim or adjacent item is checked against the text of the chunks it cites.
A number with no match flags the claim `number_not_found` (flagged, never dropped); the flag
shows next to the claim in the app. The matching rule is written in the spec.

## Matching rule (decided with S2)
A claim number matches a number in a cited chunk if either:
1. it is within 0.1% of the chunk number; or
2. it shows at least one decimal place and equals the chunk number rounded (half up) to the
   claim's shown precision and scale ("20.4 thousand" vs 20,425; "$1.2 billion" vs $1,234 million;
   "2.9%" vs 2.88%).
Scale words (thousand, million, billion, trillion, k, mn, bn) are applied on both sides. A chunk
whose text says "in thousands / millions / billions" also offers its bare numbers at that scale.
Not checked: years 1990-2099, quarter and form labels (Q3, 3Q26, 10-K), day of month after a month
name, numbers written as words. Known weakness: a tiny value with one decimal ("$0.1 billion" vs
$0.14 billion) passes rule 2. The check proves a figure is in the cited text, not that it was read
from the right table column (MS-SUPP-2026Q3 p.8 case); the source label keeps the page for that.

## Files to change
- `src/cee/answer/llm.py` - mock clips at a word boundary (added during the task, see log)
- `src/cee/answer/validate.py` - `check_numbers()`, called at the end of `check_citations`
  (no change to `ask.py`)
- `specs/answer-citations.md` - the matching rule; closes the open question on rounding and units
- `tests/test_validate.py` - planted wrong figure, one test per rule row, the 2.88% case, the flag
  rendered by `components.claim_card`

## Steps
1. Tests first.
2. Number extraction and matching.
3. Call from `check_citations`; spec section.
4. pytest, smoke, `verify_cee.py run` (mock copies chunks verbatim, so no flag appears there; a
   test proves the claim card shows `number_not_found`).

## Acceptance
- [x] A planted wrong figure is flagged `number_not_found` (spec)
- [x] 20,425 vs 20.4 thousand is documented as matched, with the rule in the spec
- [x] Flags show in the app next to the claim
- [x] `pytest -q` passes; `verify_cee.py run` all PASS; mock only, 0 real calls
- Out of scope: unit conversion between firms, derived figures (they are flagged, as rule 4 wants).

## Progress log
- 2026-11-05 - plan approved by S2: 0.1% tolerance, or rounding with at least one decimal; table
  unit headers allowed
- 2026-11-05 13:40 - check_numbers() in validate.py, called from check_citations; 15 tests. A file
  write turned `\b` in the regexes into backspace characters; fixed and checked none remain
- 2026-11-05 13:55 - all 30 bank questions on mock: 4 false flags, all from the mock cutting chunk
  text at 300 characters mid-figure ("21 milli", "$11.90 trilli"). Fixes: mock clips at a word
  boundary (llm.py, S2-owned, outside the original file list); a claim figure without a unit may
  match the digits shown. Re-run: 87 claims, 195 figures, 0 flagged
- 2026-11-05 14:02 - pytest 289 passed; smoke PASS on corpus-2026-10-29; verify-cee all 8 features
  PASS (.verify-runs/20261105-140222-9dc4c9b), mock, 0 real calls. Rule written to the spec
