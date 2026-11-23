# 0292 - Reduce prompt v7: direct answer plus short cited synthesis

Issue: #292    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: docs/results/w13-reduce-synthesis.md

## Goal
Outside window questions, the answer paragraph reads as a direct answer plus a short cited synthesis instead of one
claim per evidence card. New reduce prompt **v7** behind `REDUCE_PROMPT` (`v6` was #284's, removed by #289); default
only if the acceptance below passes. v7's rules and the mock: results doc, "Design".

## Form rule (one helper)
`reduce.list_form(aspects, query, version)`, read by the reduce (prompt, message, mock, checks), the streamed answer
and the final answer on the Ask page. **List**: the question's own window, or (v5.2 / v5.3, #291) any recency aspect,
or (v7) every aspect recency; under v7 a list-form question is answered by v5.2 exactly (prompt, message, mock, label,
cache key: Q26, Q27). Else **synthesis** (v7). Why not #291's rule under v7: 15/30 #272 plans have a recency aspect,
Q5 among them. ADR-021 rule 5 is amended (why-lines in list-form answers only), so **the PR goes to the TL**.

## Files to change
- `src/cee/answer/prompt.py` (`SYSTEM_PROMPT_V7`), `src/cee/config.py` (`REDUCE_PROMPTS` + v7; default per the rule).
- `src/cee/answer/reduce.py` - `list_form`, `synthesis`, per-question `prompt_version` / `system_prompt`, message
  variant, `mock_synthesis`, the check changes below. `src/cee/answer/validate.py` - `part_coverage` state `aspect`.
- `src/cee/answer/runcache.py`, `scripts/eval_run.py` - reduce key / record use the per-question version.
- `src/cee/app/views/ask_page.py` - `list_form` calls `reduce.list_form` (no layout change).
- `tests/test_reduce_synthesis.py`; `specs/answer-citations.md`; `docs/DECISIONS.md` (ADR-021 amendment);
  `.claude/skills/verify-cee/features/ask-layout.md`, `scripts/verify_cee.py` (reduce version step);
  `docs/results/w13-reduce-synthesis.md` + folder (run-synthesis `.ps1` / `.sh`, `cmp_mock.py`, raw copies).

## Checks (synthesis form only; list form and every v5.2 path unchanged)
Coverage: an aspect-id claim covers each cell of that aspect whose item / input chunk it cites. Computability: an
aspect-id claim citing all inputs and populations counts. `dedupe_claims` never drops claim 1. `check_adjacent`: an
aspect-id claim citing only adjacent-only cells -> `claim_from_adjacent`. No why-line check or newest-first re-sort.
Unchanged: citation, outside_matrix, number, date, normative, comparison, gaps, caveats, streaming checks.

## Steps
1. Code + tests (form rule; v5.2 request byte-identical; v7 list form = v5.2; coverage across cells; computability
   by aspect id; claim 1 kept; streamed and final form agree).
2. Mock eval fts Q1-Q30, rule plans and #272 plans: v5.2 vs main identical 30/30; v7 vs v5.2: list-form questions
   identical, the rest no new flag kind and no higher part_gap / comparison_missing / outside_matrix /
   number_not_found / no_citation (`cmp_mock.py`).
3. verify-cee on mock, default and `REDUCE_PROMPT=v7`: ask-answer, ask-layout, ask-progress.
4. Count phase (0 calls), then the paid run. 5. Results doc, spec, ADR line, default per rule. 6. PR to the TL.

## Paid calls
- **Why the mock cannot show it:** whether a model writes a direct first sentence and a synthesis that stays cited.
- **Setup:** deepseek at current defaults (`deepseek-v4-pro` `/beta`, effort plan off / map low / reduce low, stream on,
  MAP_PREFIX off), fts, as-of 2026-11-17, `corpus-2026-11-19`, `run-synthesis.ps1`, gate = the run commit.
- **Questions:** Q5, Q8, Q22, Q24, one full flow each, `REDUCE_PROMPT=v7`. Full flow (ADR-021 rule 7): Q5 6 (plan 1,
  map 4, reduce 1), Q8 6, Q22 12, Q24 22 = 46. Cache = copy of `ev272\cache-a` in `ev292\cache`; only reduce /
  prompt / config code changed since #284's count (all plans and maps reused), so **4 new calls expected** (the v7
  reduces). Count phase must show exactly 4; else stop and report. `--max-calls 4`.
- **v5.2 comparison:** `docs/results/w12-latency/b-fts/raw/Q{5,8,22,24}-reduce-*.json` (#272 test B); not re-called.
- **Cost (balance CNY 97):** v5.2's four reduces: 56.8k in / 74.6k out = $0.19 off-peak; v7 at 0.7-1.5x output
  $0.13-0.30 off-peak, <= $0.60 peak (about CNY 4).
- **Evidence:** `D:\ALLPROJECTS\EDJ\cache\ev292\`, committed copies in `docs/results/w13-reduce-synthesis/`.

## Acceptance
- [ ] pytest green (CI `gh pr checks`).
- [ ] Mock eval (step 2); Q26, Q27 byte-identical to v5.2.
- [ ] Real: 4 calls; per question v5.2 vs v7 text, output / reasoning tokens, cost, wall time, tokens/s. Every shown
      sentence cited (no_citation 0, outside_matrix 0); sentence 1 answers the question; no item-by-item restatement
      (sentences <= 5 + comparison + computation + per-firm figure sentences, and each read).
- [ ] verify-cee on mock (step 3): answer paragraph above evidence, footnotes resolve.
- [ ] **Default rule:** v7 becomes the default only if every real item passes on all four and no question has more
      part_gap / comparison_missing / number_not_found than its v5.2 record and none is invalid or cut. Else it stays
      behind `REDUCE_PROMPT=v7` and the results doc says why. Cost is reported, not a gate. If switched, the PR
      proposes the 30-question scored run (Gate 3, TL go-ahead); not part of #292.

## Progress log
- 2026-11-23 17:30 - plan written; local DB at corpus-2026-11-19.
- 2026-11-23 - plan approved (issue comment 7117074418); notes applied: plan trimmed (rules in the results doc), one
  form helper for reduce, streamed and final view (tested), PR to the TL for the ADR-021 amendment.
- 2026-11-23 - code + 10 tests (6d821a9); pytest 1200 + 10 pass locally. Mock rule plans: v5.2 = main 30/30; v7:
  Q26, Q27 identical, 28 changed, worse 0.
