# 0167 - Advisor-pay gap stated per firm (Q25, Q29)

Issue: #167    Role: S2    Spec: specs/answer-citations.md

## Goal
The advisor-pay gap is stated per firm and never contradicts cited evidence. A firm whose cited
chunk publishes payout ranges (the Raymond James recruiting pages added in #151) is reported as
company-published headline ranges with their "page content as of" date, and its gap reads
"Headline payout ranges are published (company recruiting page, as of <date>); the full payout
grid is not public." Firms with nothing published keep "Payout grids are not public."
Prompt v1 -> v2.

## Files to change
- `src/cee/answer/prompt.py` - `PROMPT_VERSION = "v2"`, `PAYOUT_RANGES_PUBLISHED`, per-firm advisor-pay rule
- `specs/answer-citations.md` - "Advisor pay" row of the standard wording table
- `tests/test_prompt.py` - version, new wording, per-firm rule
- `src/cee/answer/schema.py`, `tests/test_schema.py` - accept "answer" (boolean) as an alias for "answerable" (added during the task, see log)
- `plans/0167-payout-gap-per-firm.md` (this file)

## Paid-call plan (written before the first call)
| Q | Why the mock cannot show it | Calls |
|---|---|---|
| Q25 | whether the model reports RJF's ranges as company-published headline ranges with the as-of date and never writes "payout grids are not public" for RJF | 1 |
| Q29 | the prompt changed, so MS must be re-checked: gap still "payout grids are not public", aggregate compensation still a different quantity | 1 |
Cap `--max-calls 2`.

**Re-run (planned 2026-11-16, before the calls):** the first paid run spent 1 call on Q25 and
crashed before its output was saved (see log). Q25 is run once more and Q29 once: cap
`--max-calls 2`, task total 3 real calls. Not a re-roll: the first answer was never seen.
 No question is split into parts today (ADR-012 splitting is not implemented),
so each question is one call. Prompt v2 invalidates the v1 cache. One run, no re-rolls.

## Steps
1. Prompt v2, spec row, tests; pytest and verify-cee on the mock.
2. Check on the free path: corpus-2026-11-16 holds the six RJF pages; Q25 retrieval returns them.
3. Paid: `LLM_PROVIDER=anthropic scripts/eval_run.py --real --max-calls 2 --questions Q25,Q29`
   (provider set for that command only); judge against the acceptance items.

## Acceptance
- [x] Q25: RJF's published ranges are reported as company-published headline ranges with their "as of" date; no claim says payout grids are not public for RJF; firms with nothing published are still marked undisclosed
- [x] Q29 (MS) unchanged in behavior: gap "payout grid not public" plus aggregate compensation as a different quantity
- [x] Mock tests and verify-cee PASS; real-call count reported in the PR

## Progress log
- 2026-11-16 - plan approved by S2; corpus-2026-11-16 synced (137 docs), the six RJF pages present
- 2026-11-16 19:25 - prompt v2, spec row, tests: pytest 380 passed; smoke PASS on corpus-2026-11-16;
  verify-cee all 9 PASS (open-citation with CORPUS_SHARE_PATH: .verify-runs/20261116-192907-d75c712;
  others .verify-runs/20261116-192713-d75c712). Mock: Q25 retrieves RJF-PR-web-affiliation-options#2
  ("81% to 90% payout", Corporate RIA)
- 2026-11-16 19:31 - first paid run (`--max-calls 2`): 1 real call (Q25). The model sent "answer"
  instead of "answerable"; `Answer(**...)` raised before the runner cached the output, so the
  output is lost and no report was written. Q29 not called
- 2026-11-16 19:40 - fix: `Answer` accepts "answer" (boolean only) as an alias for "answerable",
  like the existing list-as-string tolerance; 2 tests; pytest 382 passed. Saving raw output before
  validation in `scripts/eval_run.py` (TL-owned) goes to a separate issue
- 2026-11-16 19:36 - verify-cee all 9 PASS after the schema change (.verify-runs/20261116-193518-d75c712)
- 2026-11-16 19:45 - planned re-run `--max-calls 2`: 2 real calls (Q25, Q29), claude-sonnet-5-5.
  Task total 3 real calls. `.eval-runs/s2-167-real-v2`
  - Q25: RJF's "81% to 90% payout" (Corporate RIA) reported as the recruiting page's figure,
    "page content as of 2026-04-21"; RJF gap is the new published-ranges wording; EDJ, MS, Merrill
    and Schwab each "Payout grids are not public."; no claim says grids are not public for RJF.
    Content meets acceptance item 1. Behavior is `answer` (expected `gap_with_adjacent`): runner
    status FAIL. The RJF gap line does not name the firm (its suggested_source does)
  - Q29: `gap_with_adjacent`, "Morgan Stanley: Payout grids are not public.", aggregate
    compensation as adjacent with COMPENSATION_DIFFERS: unchanged in behavior (acceptance item 2)
- 2026-11-16 19:50 - filed #187 (TL): the runner loses a paid output when the answer fails validation
- 2026-11-16 20:00 - decisions (S2): Q25 behavior `answer` recorded as a finding, not fixed by a prompt
  change; commented on #156 for C1 to decide Q25's expectation with Q28. RJF gap line without the
  firm name left for the next prompt change (would need one more Q25 call); noted in the PR
