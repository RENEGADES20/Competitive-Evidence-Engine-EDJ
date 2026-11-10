# 0118 - Boundary behavior: code backs the hand-off on Q12 and Q19

Issue: #118    Role: S2    Spec: specs/answer-citations.md

## Goal
Ground rule 6 is enforced by code as well as by the prompt. A claim that recommends an action
for the home firm is **withheld**: not shown, replaced by a fixed notice, kept in the answer JSON
(and so in `query_log`) for review, never silently dropped. The answer is re-judged as
`answer_with_boundary`, and a boundary answer always ends with the hand-off sentence, added by
code when the model left it out.

Decided with S2: withhold rather than only flag, because a recommendation that is shown, even
flagged, has already reached the reader.

## Files to change
- `src/cee/answer/schema.py` - code-owned `Answer.withheld` (not in the model's output schema)
- `src/cee/answer/validate.py` - `is_normative()`, `withhold_normative()`, `ensure_handoff()`,
  run at the start of `check_citations` (no change to `ask.py`)
- `src/cee/app/components.py`, `src/cee/app/views/ask_page.py` (U1) - an always-visible notice box
- `.claude/skills/verify-cee/features/ask-answer.md` - sub-feature note (the mock never triggers it)
- `specs/answer-citations.md` - the rule
- `tests/test_validate.py` - fixtures

## Rule
Withheld: a sentence that tells the home firm (Edward Jones and its aliases, EJ, EDJ, the home firm;
not "we" / "you", see log) what to do: "<home firm> should / ought to / needs to / must / would benefit from /
could replicate|adopt|copy|emulate|consider"; "we/I recommend|suggest|advise"; "it would be
wise|advisable|prudent"; "recommend ... <home firm>".
Not withheld: the hand-off sentence itself; another firm's own words ("Schwab said clients should");
factual "recommend" ("advisors recommend products"); conditional "should conditions worsen".

## Steps
1. Tests first (each row of the rule, handoff added once, not duplicated).
2. Schema field, validator functions, notice box.
3. Free: all 30 bank questions on mock and the five cached #61 real answers, 0 withheld.
4. Paid: `eval_run.py --real --max-calls 4 --questions Q12,Q19`. Q19 should reuse the #61 cache
   (same prompt, snapshot, retrieval); Q12 needs 1 call. Expected 1 call, cap 4.
5. pytest, smoke, verify-cee; rule into the spec.

## Acceptance
- [x] A validator test rejects a fixture answer with "should"/"recommend" aimed at the home firm
- [x] Q12 and Q19 on the real model: no normative sentence (at most 4 calls, outputs saved)
- [x] verify-cee PASS; `pytest -q` passes

## Progress log
- 2026-11-10 - plan approved by S2: withhold + re-judge + keep for review
- 2026-11-10 12:00 - schema `Answer.withheld`, `is_normative()` / `withhold_normative()` /
  `ensure_handoff()` at the start of `check_citations`, Withheld notice on the Ask page. Filing
  duties ("Edward Jones must maintain net capital") excluded: must / needs to only for "the home firm"
- 2026-11-10 12:05 - free check: mock bank 87 claims, 1 withheld, a false positive (Q6 transcript,
  analyst's "we should expect"). Narrowed: "we" / "you" are not the home firm; quoted text is not
  checked. Re-run: mock 0 of 87 withheld; #61 cached real answers 0 of 31. pytest 353 passed
- 2026-11-10 12:11 - paid run `--real --max-calls 4 --questions Q12,Q19`: 1 real call (Q12), 1 reused
  (Q19, #61 cache), claude-sonnet-5-5. Both answer_with_boundary, hand-off verbatim, 0 normative,
  0 withheld. `.eval-runs/s2-118-real`
- 2026-11-10 12:13 - smoke PASS; verify-cee 8 PASS + open-citation UNREACHABLE (cite-date needs a
  date_basis='retrieved' document, not in corpus-2026-10-29: a data precondition this change does
  not touch; not re-run on main). Rule written to the spec
