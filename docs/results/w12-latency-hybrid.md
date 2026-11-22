# W12 answer latency on hybrid-norerank (#272, exp/hybrid)

**Test B hybrid-norerank (Gate 3), blind full read: 22/30 (tier 1 11/18). Floor (adjudicated >= 22/30): met by
the blind read; the adjudicated score is this read plus the second read in the PR #274 review (as in #250).**
Against #250 hybrid: 22/30 adjudicated, 21/30 blind. fts on main (PR #273): 24/30 adjudicated.

**Latency, Q1-Q30, end to end (critical path = plan + slowest map call + slowest re-map + reduce):**

| | p50 | p90 | max |
|---|---|---|---|
| Without retrieval | 237 s | 338 s | 455 s |
| With retrieval (+ search_s) | 246 s | 368 s | 547 s |
| Retrieval alone (search_s) | 7.7 s | 35 s | 92 s |
| of which query embedding (embed_s) | 0.29 s | 1.6 s | 8.8 s |
| First cited evidence (plan + fastest map call) | 18 s | 33 s | - |
| First cited evidence with retrieval | 28 s | 69 s | 106 s |

#250 hybrid: p50 522 s, p90 702 s, max 997 s; with retrieval 532 / 724 / 1,093 s; first evidence p50 227 s. The 30 s
first-evidence target holds at p50 with retrieval (28 s); the 30 s end-to-end target is not met (the reduce call,
p50 153 s, is the long pole). Retrieval is mostly the SQL candidate searches per sub-question, not the embedding.

## How this was run

- Code: `tl/272-hybrid-sync` 62d26d7 (gate): `exp/hybrid` 4d656d8 + main 99c6569 (merge 8771e5a) + the `embed_s`
  timing. Worktree `wt-272h`, run script `docs/results/w12-latency/run-latency.ps1 -Mode hybrid-norerank`, every
  setting pinned. Config C1 (chosen by the fts test A rule): plan off, map low, reduce low, `deepseek-v4-pro`,
  streaming, `MAP_CONCURRENCY=24`, `MAP_CALL_TOKENS=60000`; `CEE_VECTORS=on`, fastembed cache
  `D:\ALLPROJECTS\EDJ\cacheastembed`. Snapshot `corpus-2026-11-19`, as-of 2026-11-17.
- Plans: the same 30 plans as fts test B (cache `cache-h` seeded with the plan records only), so retrieval is the only
  difference from fts; every map and reduce call is new to hybrid.
- Mock checks before any call (0 calls): pytest 1194 passed; mock hybrid-norerank Q1-Q30 with the #250 plans 30/30
  identical to `exp/hybrid` 4d656d8; fts parity on the branch 30/30 identical to main; verify-cee `--mode hybrid` 11/11
  PASS (two features re-run with the corpus path and `PYTHONUTF8=1`, see PR #274).
- Interruptions: 429 at Q17 (resumed once after 5 minutes), then 402 (balance) at Q17; resumed after the top-up as
  hb-run3. No output was re-rolled.
- Scoring: blind, four fresh Sonnet scorers (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30), each reading its part; inputs only
  `ev272lind-in-hyb\` (answers dump with each cited passage, `questions.yaml`, the #250 `verdict-rule.txt`).
  Merged verdicts `verdicts-hyb-full.json`, sha256 `c9229dd753831648d6fb7e6bdbbeebce137031fefaa61c4f4e1403bfb769aaef`.
  Two scorers noted reading parts of very long answers by skimming (Q7 passage dump; Q17-Q21 adjacent lines).

## Test A (hybrid, the six questions, C1)

169 new calls, USD 3.23; 0 cut, 0 invalid, 0 failed; behavior 6/6. Critical path p50 309 s, p90 415 s, max 497 s
(fts C1: 209 / 313 / 383 s); retrieval p50 20 s; first evidence p50 15 s. Tables below.

## Test B: scores

Classes: r retrieval, s shape / part missing, b behavior, c corpus gap, i invalid. bl = borderline.

| Q | Tier | Expected -> got | #250 hybrid adj. | fts #273 adj. | Hybrid blind (this run) | Class | Retrieval s | Embed s | Critical path s | With retrieval s | First evidence s | Calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | answer -> answer | PASS | PASS | **PASS** |  | 1.033 | 0.031 | 29.2 | 30.3 | 18.7 | 3 |
| Q2 | 1 | answer -> answer | PASS | PASS | **PASS** |  | 3.356 | 0.079 | 193.9 | 197.2 | 35.3 | 8 |
| Q3 | 1 | answer -> answer | PASS | FAIL | **PASS** bl |  | 3.192 | 0.095 | 154.5 | 157.7 | 25.4 | 8 |
| Q4 | 1 | answer -> answer | PASS | PASS | **PASS** bl |  | 3.808 | 0.386 | 220.5 | 224.3 | 19.7 | 9 |
| Q5 | 1 | answer -> answer | FAIL | PASS | **PASS** |  | 4.592 | 0.409 | 102.3 | 106.9 | 26.2 | 6 |
| Q6 | 1 | answer -> answer | PASS | PASS | **PASS** |  | 7.242 | 0.833 | 391.1 | 398.4 | 21.7 | 9 |
| Q7 | 2 | answer -> answer | PASS | PASS | **PASS** bl |  | 67.056 | 4.887 | 267.3 | 334.4 | 38.0 | 34 |
| Q8 | 2 | answer -> answer | PASS | PASS | **PASS** |  | 2.433 | 0.091 | 246.8 | 249.2 | 22.0 | 6 |
| Q9 | 3 | answer -> answer | PASS | PASS | **PASS** |  | 5.459 | 0.12 | 251.1 | 256.6 | 11.3 | 15 |
| Q10 | 3 | answer -> answer | PASS | PASS | **PASS** |  | 30.592 | 0.594 | 334.2 | 364.8 | 16.1 | 45 |
| Q11 | 1 | answer -> answer | FAIL | FAIL | **FAIL** bl | r, s | 12.863 | 0.28 | 219.7 | 232.5 | 16.0 | 32 |
| Q12 | 3 | answer_with_boundary -> answer_with_boundary | FAIL | PASS | **PASS** bl |  | 8.215 | 0.142 | 193.1 | 201.3 | 13.7 | 10 |
| Q13 | 1 | answer -> answer | PASS | PASS | **PASS** |  | 5.808 | 0.128 | 261.6 | 267.4 | 24.3 | 10 |
| Q14 | 3 | answer -> answer | PASS | PASS | **PASS** bl |  | 2.88 | 0.097 | 130.8 | 133.6 | 22.3 | 7 |
| Q15 | 3 | answer -> answer | PASS | PASS | **PASS** bl |  | 17.436 | 0.578 | 279.4 | 296.8 | 17.7 | 42 |
| Q16 | 3 | answer -> answer | FAIL | PASS | **FAIL** bl | s | 11.766 | 0.181 | 195.8 | 207.5 | 13.6 | 25 |
| Q17 | 1 | answer -> answer | PASS | PASS | **PASS** bl |  | 6.625 | 0.14 | 226.5 | 233.2 | 7.3 | 17 |
| Q18 | 3 | answer -> answer | FAIL | PASS | **PASS** bl |  | 8.674 | 0.093 | 261.1 | 269.7 | 28.6 | 13 |
| Q19 | 3 | answer_with_boundary -> answer_with_boundary | PASS | PASS | **PASS** |  | 37.268 | 0.825 | 298.9 | 336.2 | 9.6 | 37 |
| Q20 | 1 | answer -> answer | PASS | FAIL | **FAIL** bl | s | 12.459 | 0.207 | 287.4 | 299.9 | 12.8 | 30 |
| Q21 | 2 | answer -> answer | PASS | PASS | **PASS** bl |  | 91.904 | 8.789 | 454.9 | 546.8 | 13.8 | 55 |
| Q22 | 1 | answer -> answer | PASS | PASS | **PASS** bl |  | 14.973 | 1.291 | 226.9 | 241.9 | 10.9 | 12 |
| Q23 | 1 | answer -> answer | FAIL | FAIL | **FAIL** | r, c, s | 34.894 | 3.916 | 374.5 | 409.4 | 33.0 | 7 |
| Q24 | 3 | answer -> answer | PASS | PASS | **PASS** bl |  | 8.798 | 0.243 | 319 | 327.8 | 17.9 | 22 |
| Q25 | 1 | answer -> answer | PASS | PASS | **FAIL** bl | s | 11.936 | 0.308 | 302.9 | 314.8 | 10.8 | 37 |
| Q26 | 1 | answer -> answer | PASS | PASS | **FAIL** bl | s | 3.843 | 0.967 | 285.8 | 289.6 | 11.5 | 10 |
| Q27 | 1 | answer -> answer | FAIL | PASS | **PASS** bl |  | 4.807 | 1.125 | 200.1 | 204.9 | 15.8 | 10 |
| Q28 | 1 | answer -> answer | PASS | FAIL | **FAIL** bl | s | 10.421 | 1.135 | 208.3 | 218.7 | 10.2 | 9 |
| Q29 | 1 | gap_with_adjacent -> answer | FAIL | FAIL | **FAIL** | b, s | 6.726 | 0.719 | 116.7 | 123.4 | 28.1 | 7 |
| Q30 | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | PASS | **PASS** |  | 1.23 | 0.172 | 96.3 | 97.5 | 72.3 | 3 |

Changes against #250 hybrid (adjudicated): FAIL -> PASS Q5, Q12, Q18, Q27; PASS -> FAIL Q20, Q25, Q26, Q28.

## Latency tables

#### Hybrid test B (C1), Q1-Q30

30 questions, 538 call records: critical path p50 237 s, p90 338 s, max 455 s; first evidence p50 17.8 s, p90 33.23 s; cut 0, invalid 0, failed 0.

Retrieval (search_s): p50 7.73 s, p90 35.13 s, max 91.9 s; query embedding (embed_s): p50 0.29 s, p90 1.55 s, max 8.79 s; critical path with retrieval: p50 246 s, p90 368 s, max 547 s.

| Q | retrieval s | embed s | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1.033 | 0.031 | 3.3 | 1 | 15.4 | 0 | - | 10.6 | 29.2 | 18.7 | 0 |
| Q2 | 3.356 | 0.079 | 4.9 | 6 | 58.3 | 0 | - | 131 | 194 | 35.3 | 0 |
| Q3 | 3.192 | 0.095 | 4 | 6 | 66.5 | 0 | - | 84.1 | 154 | 25.4 | 0 |
| Q4 | 3.808 | 0.386 | 4.1 | 7 | 72.2 | 0 | - | 144 | 220 | 19.7 | 0 |
| Q5 | 4.592 | 0.409 | 5.3 | 4 | 36.6 | 0 | - | 60.5 | 102 | 26.2 | 0 |
| Q6 | 7.242 | 0.833 | 5.1 | 7 | 111 | 0 | - | 275 | 391 | 21.7 | 0 |
| Q7 | 67.056 | 4.887 | 6.2 | 31 | 96.1 | 1 | 2.2 | 163 | 267 | 38 | 0 |
| Q8 | 2.433 | 0.091 | 2.8 | 4 | 27.6 | 0 | - | 216 | 247 | 22 | 0 |
| Q9 | 5.459 | 0.12 | 5 | 12 | 51.1 | 1 | 5.4 | 190 | 251 | 11.3 | 0 |
| Q10 | 30.592 | 0.594 | 9.6 | 31 | 123 | 12 | 9.4 | 192 | 334 | 16.1 | 0 |
| Q11 | 12.863 | 0.28 | 3.6 | 25 | 74 | 5 | 5.5 | 137 | 220 | 16 | 0 |
| Q12 | 8.215 | 0.142 | 5.1 | 8 | 69.5 | 0 | - | 118 | 193 | 13.7 | 0 |
| Q13 | 5.808 | 0.128 | 5.9 | 8 | 86.1 | 0 | - | 170 | 262 | 24.3 | 0 |
| Q14 | 2.88 | 0.097 | 3.8 | 5 | 66.1 | 0 | - | 60.8 | 131 | 22.3 | 0 |
| Q15 | 17.436 | 0.578 | 9.6 | 40 | 94.3 | 0 | - | 176 | 279 | 17.7 | 0 |
| Q16 | 11.766 | 0.181 | 5.4 | 23 | 60.6 | 0 | - | 130 | 196 | 13.6 | 0 |
| Q17 | 6.625 | 0.14 | 4.5 | 15 | 85.7 | 0 | - | 136 | 226 | 7.3 | 0 |
| Q18 | 8.674 | 0.093 | 4 | 11 | 73.8 | 0 | - | 183 | 261 | 28.6 | 0 |
| Q19 | 37.268 | 0.825 | 6.1 | 32 | 66.2 | 3 | 4.3 | 222 | 299 | 9.6 | 0 |
| Q20 | 12.459 | 0.207 | 6.2 | 27 | 118 | 1 | 9.5 | 153 | 287 | 12.8 | 0 |
| Q21 | 91.904 | 8.789 | 7.5 | 46 | 111 | 7 | 9.8 | 326 | 455 | 13.8 | 0 |
| Q22 | 14.973 | 1.291 | 2.2 | 10 | 84.8 | 0 | - | 140 | 227 | 10.9 | 0 |
| Q23 | 34.894 | 3.916 | 1.8 | 5 | 64.8 | 0 | - | 308 | 374 | 33 | 0 |
| Q24 | 8.798 | 0.243 | 3.5 | 20 | 90.8 | 0 | - | 225 | 319 | 17.9 | 0 |
| Q25 | 11.936 | 0.308 | 5 | 30 | 109 | 5 | 11.9 | 177 | 303 | 10.8 | 0 |
| Q26 | 3.843 | 0.967 | 5.3 | 8 | 62.1 | 0 | - | 218 | 286 | 11.5 | 0 |
| Q27 | 4.807 | 1.125 | 5.1 | 8 | 42.5 | 0 | - | 152 | 200 | 15.8 | 0 |
| Q28 | 10.421 | 1.135 | 3.4 | 7 | 89.3 | 0 | - | 116 | 208 | 10.2 | 0 |
| Q29 | 6.726 | 0.719 | 3.8 | 5 | 44.1 | 0 | - | 68.7 | 117 | 28.1 | 0 |
| Q30 | 1.23 | 0.172 | 2.2 | 1 | 70.1 | 0 | - | 24 | 96.3 | 72.3 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 30 | 4.93 | 6.38 | 9.61 | 1.29 | 1.53 | 488 | 1,282 | - |
| map | 443 | 37.25 | 69.31 | 123 | 3.58 | 6.89 | 3,836 | 14,697 | 0.78 |
| remap | 35 | 4.98 | 8.65 | 11.91 | 1.56 | 1.98 | 410 | 1,248 | 0.67 |
| reduce | 30 | 153 | 230 | 326 | 2.46 | 3.88 | 22,800 | 50,344 | 0.67 |

#### Hybrid test A (C1), the six questions

6 questions, 175 call records: critical path p50 309 s, p90 415 s, max 497 s; first evidence p50 14.95 s, p90 22.05 s; cut 0, invalid 0, failed 0.

Retrieval (search_s): p50 19.75 s, p90 44.52 s, max 52.09 s; query embedding (embed_s): p50 0.46 s, p90 0.81 s, max 0.9 s; critical path with retrieval: p50 332 s, p90 457 s, max 549 s.

| Q | retrieval s | embed s | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | 1.685 | 0.026 | 5.3 | 4 | 36.6 | 0 | - | 60.5 | 102 | 26.2 | 0 |
| Q10 | 30.962 | 0.718 | 9.6 | 31 | 123 | 12 | 9.4 | 192 | 334 | 16.1 | 0 |
| Q19 | 36.95 | 0.732 | 6.1 | 32 | 66.2 | 3 | 4.3 | 222 | 299 | 9.6 | 0 |
| Q21 | 52.086 | 0.897 | 7.5 | 46 | 111 | 7 | 9.8 | 368 | 497 | 13.8 | 0 |
| Q24 | 8.545 | 0.205 | 3.5 | 20 | 90.8 | 0 | - | 225 | 319 | 17.9 | 0 |
| Q26 | 2.59 | 0.082 | 5.3 | 8 | 62.1 | 0 | - | 218 | 286 | 11.5 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 5.71 | 8.53 | 9.55 | 1.5 | 1.81 | 541 | 810 | - |
| map | 141 | 31.92 | 66.48 | 123 | 3.02 | 6.5 | 2,720 | 14,697 | 0.79 |
| remap | 22 | 4.41 | 7.43 | 9.83 | 1.5 | 1.86 | 385 | 1,104 | 0.66 |
| reduce | 6 | 220 | 297 | 368 | 3.12 | 4.95 | 31,635 | 58,103 | 0.68 |

## Calls and cost (DeepSeek `deepseek-v4-pro`, all off-peak)

- Hybrid test A: 169 new calls, USD 3.23.
- Hybrid test B: 340 new calls (216 before the 402, 124 after), USD 9.94. The 30 answers used 538 calls (planner 30
  reused from fts, map 443, re-map 35, reduce 30), USD 13.05 for every call they used.
- Hybrid total: 509 new calls, USD 13.17. #272 total (fts 848 / USD 17.81 + hybrid): 1,357 calls, USD 30.98.
- Reduce-high re-run: not run (the blind read meets the floor; it is run once if the adjudicated score falls below 22).

## Findings

1. Hybrid answers take longer than fts with the same plans (p50 237 s vs 184 s), although hybrid retrieves fewer
   passages (13,359 vs 17,153 in all): the reduce call is slower (p50 153 s vs 126 s, about the same output, 22.8k vs
   22.4k tokens) and the map's slowest call too (p50 37 s vs 34 s). Not explained here; one sample per question.
2. Retrieval adds p50 8 s (p90 35 s, max 92 s); the query embedding is under 0.3 s at p50. The slow cases are many
   sub-questions times several SQL legs, not the model.
3. 0 cut and 0 invalid outputs in 538 records; no stalled stream this time.
4. Follow-ups from the fts report stand (shorter stream read timeout; reduce message byte stability).

Evidence: `docs/results/w12-latency-hybrid/` (raw records, reports, head logs, verdicts); working copies
`D:\ALLPROJECTS\EDJ\cache\ev272\`.
