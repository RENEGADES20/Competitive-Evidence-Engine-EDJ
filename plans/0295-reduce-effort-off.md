# 0295 - Reduce effort off for v8 synthesis answers, comparison part-id fallback, Gate 3 run

Issue: #295    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: docs/results/w13-reduce-synthesis.md (v8);
results `docs/results/w13-reduce-effort-off.md` (new)

## Goal
v8 synthesis answers use reduce effort `off` (6-14 s per reduce in #292, against 15-343 s at `low`). A code fallback fixes
Q24's #292 `off` miss (verdict filed under `a1`, so `comparison_missing`). Gate 3 (TL go-ahead 2026-11-23, "好，这样做")
checks the score stays at or above #272 test B (24/30 adjudicated). Plan review: issue comment 7120735225.

## Design
- **Comparison fallback.** v8 brief synthesis form only. In `check_comparisons`, after the citation / outside / adjacent
  checks and before `check_parts`. It applies only when a comparison aspect has no claim under its own ids. Then the first
  model claim in order that meets all of the following is re-filed (`part_id` := aspect id):
  1. It cites `citable(m)` chunks that are counting items of that aspect's holding cells, for 2 or more firms. If fewer
     than 2 firms hold evidence, there is no fallback.
  2. Its text matches the new `P.COMPARISON_VERDICT` (compar*, side by side, like for like, apples to apples, on a
     same / different / consistent / common basis, defined / measured differently).
  3. It has none of the flags no_citation, unmatched_citation, outside_matrix, claim_from_adjacent, normative.
  4. It has not already been re-filed.

  Text and citations stay unchanged; `comparison_refiled` [{claim, old part id, aspect}] goes to the reduce log. If no
  claim qualifies, the `COMPARISON_MISSING` gap is added as today, so the fallback never invents a claim. v5.2, v7 and
  list form are unchanged.
  Q24 off: claim 1 cites a4.MS, a4.MER and a4.RJF and says "side-by-side ... on a different basis".
  Overfit note (results doc): the pattern was written from the two #292 Q24 sentences; Gate 3 shows whether it fires
  wrongly elsewhere.
- **Per-form effort.** New `DEEPSEEK_EFFORT_REDUCE_BRIEF` (default `off`), used when `reduce.brief(m, query)` holds;
  every other reduce keeps `DEEPSEEK_EFFORT_REDUCE` (default `low`). List form stays `low`: #275 R2 (off, list prompt v5.3)
  scored 20/30 blind, with Q26 (list form) a new FAIL (`docs/results/w12-reduce.md`).
  - `reduce.effort(m, query)`; the `llm.stage_*` helpers, `request_version` and `deepseek_tool_request` take an
    optional `effort`.
  - The matrix is passed through `reduce.max_tokens` / `requests` / `input_limit` / `call_reduce`, `runcache.reduce_key`,
    and `eval_run.py` (reduce key and meta per question; today one `self.reduce_version` per run).
  - The request strings are unchanged (`ds-strict-2-reduce-off-c64000-s1`, `-low-c128000-s1`), so the #292 and #272
    records are reused by key.

## Files to change
- Code: `src/cee/config.py`, `src/cee/answer/llm.py`, `src/cee/answer/reduce.py`, `src/cee/answer/prompt.py`,
  `src/cee/answer/runcache.py`, `scripts/eval_run.py`, `.env.example`.
- Tests: `tests/test_reduce_synthesis.py`, `tests/test_deepseek_stages.py`.
- Spec: #295 block in `specs/answer-citations.md`.
- Results: the results doc plus `docs/results/w13-reduce-effort-off/` (`run-gate3.ps1` / `.sh` with every setting pinned,
  `dump295.py`, verdicts, tables, raw copies).

## Steps
1. Code and tests (0 calls).
   - Fallback: the Q24-shaped verdict under `a1` is re-filed. Rejected: no verdict words, one firm's or no a4 cell, a
     flagged claim, any v5.2 answer.
   - Verdict-pattern negatives: e.g. "Schwab's client assets rose compared with 2025", "Edward Jones reports advisors on
     a quarterly basis", plain figures. Where a negative still matches, the 2-firm citation rule is what blocks it.
   - Effort: brief gives off / c64000, list form low / c128000.
2. Mock checks (0 calls), `cmp_mock.py`: fts Q1-Q30, rule and #272 plans, vs main d1bbed5: 30/30 identical, and
   `comparison_refiled` empty on all 30 questions. Then pytest.
3. Q24 replay (0 calls): `--max-calls 0 --questions Q24` on `ev295\cache` (a copy of `ev292\cache`). The g8-off record is
   reused; expect `comparison_missing` [] and `comparison_refiled` a1 -> a4.
4. verify-cee on mock: ask-answer, ask-layout, ask-progress (layout unchanged).
5. Count phase (0 calls) at the gate commit, clean worktree, `run-gate3.ps1 -Phase count`.
   - Expect 521 reused: 30 plans, 454 maps and 31 re-maps (#272 test B), plus 6 reduces (Q5, Q8, Q22, Q24 v8-off from
     #292; Q26, Q27 v5.2-low from #272).
   - Expect 24 new reduce keys (Q29 included: its #272 reduce failed under the low key).
   - Anything else: stop and report.
6. Gate 3 run: `-Phase run -MaxCalls <count>` (expected 24), deepseek, `deepseek-v4-pro` `/beta`.
   - Settings: plan off, map low, reduce low / brief off, stream on, idle 120 s, `REDUCE_PROMPT=v8`, MAP_PREFIX off, fts,
     as-of 2026-11-17, `corpus-2026-11-19`, `PYTHONHASHSEED=0`.
   - No re-roll: a cut, invalid or failed record is FAIL (i).
7. Scoring, the #272 method (`docs/results/w12-latency.md`, "How this was run"): a blind score, then the PR reviewer's
   second read of borderline FAILs gives the adjudicated score.
   - Four fresh Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30).
   - Inputs only `ev295\blind-in\`: the dump, `questions.yaml` and the #250 `verdict-rule.txt`, with hashes; merged
     verdicts with sha256.
   - Q29 is scoreable this time. Each question is compared with its #272 adjudicated verdict, named per question.
   - `dump295.py` = `dump272.py` plus a block marked "context only, not answer content": the evidence list shown under the
     answer (each fact cell's items and passages, the `ask.evidence_lines` rule). The Computability box is listed with
     the answer, as code-written answer content.
   - A PASS is judged on what the answer asserts: its sentences, their citations and the box. For every PASS, scorers
     also record `text_only`: whether it holds on the answer text and citations alone. Both counts are reported.
   - Side check (0 calls): `dump295.py` on 3-4 borderline #272 v5.2 records (Q4, Q7, Q15, Q22), scored with and without
     the block, shows how much the block moves verdicts.
8. Results doc and PR.
   - Score per question against #272, each change explained. Q26 and Q27 have a delta of zero by construction (the same
     v5.2-low record).
   - Reduce wall p50 / p90, cost and tokens/s for three rows: v8-off (30 questions), v5.2 (#272, 30 questions, p50 126 s /
     p90 160 s), and v8-low (the 4 #292 questions, like for like on those 4).
   - The v8-low comparison is confounded by service speed: #292 ran at peak (50-94 tokens/s), #272 off-peak (167-189).

## Decision rule (fixed before any call; the stricter text-only adjudicated count decides)
- **24/30 or more:** the defaults stay (brief `off`, fallback on).
- **23/30 or less (fail):** classify each question that regressed against #272 from its reduce record and claims.
  - *Effort-caused:* an error in what the sentences assert, such as a wrong figure, period or firm, an unsupported or
    flagged claim, a missed verdict, or invalid output.
  - *Form-caused:* a required part left out by the 5-sentence form while the matrix holds it. For Q5, Q8, Q22, Q24 the
    g8-low record decides directly.
  - All effort-caused: `DEEPSEEK_EFFORT_REDUCE_BRIEF` defaults back to `low`, the fallback stays, and the results doc
    records "v8-low unscored at 30 questions".
  - Any form-caused or not separable: stop and report to the TL before merge. Whether v5.2 returns as the default is the
    TL's call.

## Acceptance
- [ ] pytest green (CI), with the step-1 tests.
- [ ] The Q24 v8-off replay passes with the fallback (0 calls).
- [ ] Gate 3 fts Q1-Q30 scored, the decision rule applied, both counts reported, per-question changes explained, latency
      and cost reported as in step 8.
- [ ] verify-cee on mock: ask-answer, ask-layout, ask-progress PASS.
- [ ] Paid calls as below, reported in the PR.

## Paid calls
- **Calls:** 24 new `deepseek-v4-pro` reduce calls (Q1-Q30 minus the 6 reused). No plan, map or re-map call. One run with
  `--max-calls` equal to the count.
- **Why the mock cannot show it:** answer quality at effort off is the question.
- **Estimated cost:** about 520k input tokens (#272's reduce inputs) and 20k output: at most about $0.37 off-peak or $0.75
  peak with no cache hits, CNY 3-6 of about CNY 95.
- **Approval:** TL go-ahead 2026-11-23. All other steps make 0 calls.

## Progress log
- 2026-11-23 21:02 - plan written from main d1bbed5; DB at corpus-2026-11-19 (sync check exit 0). 0 calls.
- 2026-11-23 - plan review CHANGES REQUESTED (issue comment 7120735225): text-only pass count decides; 23/30 is a fail,
  with an effort- vs form-caused rule; verdict negatives, `comparison_refiled` mock assert, Q26 / Q27 zero delta, peak
  confound noted. Amended. 0 calls.
- 2026-11-23 - plan approved (issue comment 7120764517). Code + 18 tests (a7d9ed1); pytest 1235 passed.
- 2026-11-23 21:14 - Q24 replay (0 calls): the g8-off record reused, `comparison_missing` [], re-filed a1 -> a4.
  verify-cee on mock at a7d9ed1: ask-answer, ask-layout, ask-progress PASS. Mock fts Q1-Q30 vs main d1bbed5, rule and
  #272 plans: 30/30 identical on both; `comparison_refiled` empty everywhere.
- 2026-11-23 21:25 - side check (0 calls): #272 records Q3, Q4, Q8, Q22 (borderline ones; Q7 and Q15 dumps were too
  large for one scorer) scored by two fresh Sonnet scorers, with and without the evidence block.
- 2026-11-23 21:32 (03:32 UTC, peak) - count g3-count: 521 reused, 24 new reduce keys (= plan). Paid run g3-run started,
  `--max-calls 24`, not waiting for off-peak (TL instruction).
- 2026-11-23 21:43 - g3-run done: 24 calls, $0.609 at peak, none failed; fallback fired on Q24 only. Reduce wall p50
  10.4 s / p90 18.8 s.
- 2026-11-23 21:50 - blind scoring (four fresh Sonnet scorers): 14/30, text-only 14/30; at most 23/30 after a second
  read. Fail. Regressions Q5, Q7, Q22 form-caused, so the rule says stop and report to the TL before merge (results doc).
  No PR opened.
