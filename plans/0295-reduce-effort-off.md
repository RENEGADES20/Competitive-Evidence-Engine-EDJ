# 0295 - Reduce effort off for v8 synthesis answers, comparison part-id fallback, Gate 3 run

Issue: #295    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: docs/results/w13-reduce-synthesis.md (v8),
results doc `docs/results/w13-reduce-effort-off.md` (new)

## Goal
v8 synthesis answers are written with reduce effort `off` (6-14 s per reduce at #292 instead of 15-343 s). A code fallback
stops Q24's #292 `off` failure (verdict filed under part id `a1`, so `comparison_missing`). A 30-question scored run
(Gate 3, approved by the TL 2026-11-23: "好，这样做") checks the score stays at or above #272's 24/30 adjudicated.

## Design
- **Comparison fallback (v8 brief synthesis form only; `check_comparisons(answer, m, brief=...)`).** Applies only when
  a comparison aspect has no claim under its own ids (the aspect or one of its cells). Then the first model claim, in answer
  order, that meets all four conditions is re-filed: its `part_id` becomes the aspect id. Text and citations are
  unchanged, and `comparison_refiled` [{claim index, old part id, aspect}] goes in the reduce log.
  1. It cites valid matrix chunks (in `citable(m)`) that are counting items of that aspect's holding cells, for at least
     2 firms (rows). If fewer than 2 firms hold evidence for the aspect, there is no fallback and the gap stays.
  2. Its text states a comparability verdict: a new `P.COMPARISON_VERDICT` pattern (compar*, side by side, like for
     like, apples to apples, on a same / different / consistent / common basis, defined / measured differently). It is
     fixed and tested on both #292 Q24 sentences (low and off).
  3. It carries none of the flags `no_citation`, `unmatched_citation`, `outside_matrix`, `claim_from_adjacent`,
     `normative`.
  4. It has not already been re-filed for another aspect.

  The fallback never writes, merges or cites anything. If no claim qualifies, the `COMPARISON_MISSING` gap is added as
  today. It runs where `check_comparisons` runs now (after the citation / outside-matrix / adjacent checks, before
  `check_parts`), so the part check sees the re-filed id. v5.2 / v7 and list-form answers are unchanged.
  Q24 off: claim 1 cites a4.MS, a4.MER and a4.RJF chunks (3 firms) and says "side-by-side ... on a different basis".
- **Per-form effort.** New setting `DEEPSEEK_EFFORT_REDUCE_BRIEF` (`config.deepseek_effort_reduce_brief`, default
  `off`). It is used for the reduce call when `reduce.brief(m, query)` is true (v8 synthesis form). Every other reduce
  call keeps `DEEPSEEK_EFFORT_REDUCE` (default `low`).
  - This covers list-form v5.2 answers (window / all-recency questions: Q26, Q27 in #272's plans) and v5.2 / v7 when
    configured.
  - List form stays `low` because #275 R2 (reduce off, list prompt v5.3) scored 20/30 blind, and Q26 (list form) was one
    of its new FAILs (`docs/results/w12-reduce.md`). This run does not test list form at `off`.
  - Code: `reduce.effort(m, query)`. The `llm.stage_*` helpers, `request_version` and `deepseek_tool_request` take an
    optional `effort` override, so that effort sets the thinking mode, the cap (off streamed 64000) and the request
    version per question.
  - Callers that must pass the matrix: `reduce.max_tokens`, `requests`, `input_limit`, `call_reduce`; the app run cache
    `runcache.reduce_key`; `eval_run.py` reduce key and record meta (today one `self.reduce_version` per run).
  - Request strings stay `ds-strict-2-reduce-off-c64000-s1` / `-low-c128000-s1`, so the #292 and #272 records are reused
    by key.

## Files to change
`src/cee/config.py`, `src/cee/answer/llm.py`, `src/cee/answer/reduce.py`, `src/cee/answer/prompt.py` (verdict pattern),
`src/cee/answer/runcache.py`, `scripts/eval_run.py`, `.env.example`. Tests: `tests/test_reduce_synthesis.py`,
`tests/test_deepseek_stages.py`. Spec: the #295 block in `specs/answer-citations.md`. Results doc plus folder
`docs/results/w13-reduce-effort-off/`: `run-gate3.ps1` / `.sh` (from `run-synthesis`, every setting pinned plus
`DEEPSEEK_EFFORT_REDUCE_BRIEF`), `dump295.py`, tables, verdicts, committed raw copies.

## Steps
1. Code and tests (0 calls). Fallback tests on a Q24-shaped matrix: the verdict under `a1` citing 2+ firms' a4 cells is
   accepted and re-filed. Not accepted: a sentence without the verdict; a verdict citing only one firm's a4 cell or no a4
   cell; a flagged claim; any v5.2 answer. Effort tests: brief gets off / c64000, list form low / c128000, keys differ
   only there.
2. Mock checks (0 calls), with `cmp_mock.py` (#292). Mock fts Q1-Q30 with rule plans and #272 plans, new vs main
   d1bbed5: 30/30 identical, since the mock writes comparison claims under the aspect id. Then pytest.
3. Q24 replay (0 calls): `eval_run --real --max-calls 0 --questions Q24` on cache `ev295\cache`, a copy of
   `ev292\cache` (#272 `cache-a` plus the #292 records). The g8-off reduce record is reused; expect
   `comparison_missing` [] and `comparison_refiled` [a1 -> a4].
4. verify-cee on mock (ask-answer, ask-layout, ask-progress): answer layout unchanged.
5. Gate 3 count phase (0 calls) at the gate commit, clean worktree, `run-gate3.ps1 -Phase count`.
   - Expected: 521 records reused: 30 plans, 454 maps and 31 re-maps (#272 test B), plus 6 reduces (Q5, Q8, Q22, Q24
     v8-off from #292; Q26, Q27 v5.2-low from #272).
   - Expected new: 24 reduce keys (v8-off for the other 24 questions, Q29 included: its #272 reduce failed under the
     low key).
   - Any new plan, map or re-map key, or a different reduce count: stop and report, no call.
6. Gate 3 run: `-Phase run -MaxCalls <count from step 5>` (expected 24), provider deepseek, `deepseek-v4-pro` `/beta`.
   - Settings as #272 test B / #292: plan off, map low, reduce `low` with brief `off`, stream on, idle 120 s,
     `REDUCE_PROMPT=v8`, MAP_PREFIX off, fts, as-of 2026-11-17, `corpus-2026-11-19`, `PYTHONHASHSEED=0`.
   - Every record is saved. No re-roll: a cut, invalid or failed record is a FAIL (i).
7. Scoring, the #272 / #275 method (`docs/results/w12-latency.md` "How this was run").
   - Four fresh Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30), each reading its part in full.
   - Inputs only `ev295\blind-in\`: the dump, `questions.yaml` and the #250 `verdict-rule.txt` unchanged, with hashes.
     Merged verdicts with sha256.
   - Then the PR reviewer's second read of the borderline FAILs gives the adjudicated score, as in PR #273.
   - Dump change, stated in the results doc: `dump295.py` = `dump272.py` plus the lines the v8 page shows under the
     answer. These are the evidence list (each fact cell's items with their cited passages, the rule of
     `ask.evidence_lines`) and the Computability box. A v8 answer is 1-5 sentences by design; the evidence list carries
     the rest, as the user sees it (#291, #292).
8. Results doc. Score against #272, per question, with each change explained. Reduce wall p50 / p90, cost and tokens/s:
   - v8-off: 30 questions.
   - v5.2: #272 test B, 30 questions, p50 126 s / p90 160 s.
   - v8-low: the 4 #292 questions, like for like with v8-off on the same 4.
   - Peak / off-peak noted. Then PR.

## Decision rule (fixed before any call)
Adjudicated >= 24/30: the defaults stay (brief `off`, fallback on). Below 24/30: before merge,
`DEEPSEEK_EFFORT_REDUCE_BRIEF` defaults back to `low`. The fallback and the setting stay, and the results doc says why.

## Acceptance
- [ ] pytest green (CI), including the fallback and effort tests in step 1.
- [ ] Q24 v8-off replay passes with the fallback (0 calls).
- [ ] Gate 3 fts Q1-Q30 scored on the new default; adjudicated score not below 24/30 (#272 test B); per-question changes
      explained; reduce wall p50 / p90 and cost reported next to v8-low and v5.2.
- [ ] verify-cee on mock: ask-answer, ask-layout, ask-progress PASS (answer layout unchanged).
- [ ] Paid calls as planned below, and reported in the PR.

## Paid calls
- **Gate 3:** 24 new `deepseek-v4-pro` reduce calls (Q1-Q30 minus Q5, Q8, Q22, Q24, Q26, Q27, which are reused). No
  plan, map or re-map call. One run, `--max-calls` equal to the count phase.
- **Why the mock cannot show it:** answer quality at effort off is the question.
- **Estimated cost:** about 520k input tokens (#272's reduce inputs for those questions) plus about 20k output, at most
  about $0.37 off-peak and $0.75 peak if no input hits the cache. That is CNY 3-6 of the about CNY 95 balance.
- Approved by the TL 2026-11-23. Replay, count and mock steps: 0 calls.

## Progress log
- 2026-11-23 21:02 - plan written on `tl/295-reduce-effort-off` from main d1bbed5; local DB at corpus-2026-11-19 (sync check
  exit 0). 0 calls.
