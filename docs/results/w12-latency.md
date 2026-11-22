# W12 answer latency: effort per stage, map per cell, streaming (#272), fts

**Test B fts (Gate 3): blind full read 22/30 (tier 1 11/18); adjudicated 24/30 (tier 1 12/18) after the reviewer's
second read (PR #273 review round 1: Q8 and Q17 back to PASS, Q3 stays FAIL); floor fts >= 18/30 met.** Against #250:
18/30 adjudicated, 19/30 blind.

**Latency, Q1-Q30, end to end (critical path = plan + slowest map call + slowest re-map + reduce):
p50 184 s, p90 251 s, max 3,750 s** (Q29: one reduce call stalled with no output until the 3600 s read timeout).
Without Q29: p50 179 s, p90 243 s, max 383 s. **First cited evidence: p50 18 s, p90 30 s.** #250: p50 415 s,
p90 822 s, max 1,079 s; first evidence p50 204 s. The 30 s first-evidence target is met at p50; the 30 s end-to-end
target is not (the reduce call, p50 126 s, is now the long pole).

## How this was run

- Plan `plans/0272-latency.md` (TL ruling issuecomment-7067044356, conditions 1-3). Code under test: `tl/272-latency`
  4a64f79 (gate for test B; test A ran at gate 2172170, which differs only in the effort defaults), from the clean
  worktree `wt-272run`. Run scripts `docs/results/w12-latency/run-latency.ps1` / `.sh`; every setting pinned.
- Snapshot `corpus-2026-11-19`, as-of 2026-11-17, `deepseek-v4-pro` on `/beta`, `PLANNER=on`,
  `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=24`, `MAP_CALL_TOKENS=60000`, streaming on. Planner `plan-v3.1`,
  extract `extract-v1.2`, reduce `v5.2`. Request versions `ds-strict-2-plan-off-c8000-s1`,
  `ds-strict-2-map-low-c128000-s1`, `ds-strict-2-reduce-low-c128000-s1`.
- Mock checks before any call (0 calls): pytest 1093 passed; mock Q1-Q30 fts with rule plans and with the #250 plans,
  30/30 identical to clean `main` 7657d64 (status, retrieved chunks, behavior, every cell label, every claim and its
  chunk ids); verify-cee 10/10 PASS.
- Test A: Q5, Q10, Q19, Q21, Q24, Q26 under C1 / C2 / C3, then the fixed choice rule (plan step 10). Test B: C1 on
  Q1-Q30, plans and the six test-A answers reused from test A by key.
- Interruptions (each logged in the plan): DeepSeek 429 at Q25 (run stopped, resumed); 402 insufficient balance
  (stopped; resumed after the top-up); the database was down once before any call (Docker restarted, 0 calls). No
  output was ever re-rolled: every saved record was reused.
- Scoring: blind, four fresh Sonnet scorers by question range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30, balanced by dump
  size), each reading its part in full; inputs only `ev272lind-in-fts\` (the answers dump with each cited passage,
  `questions.yaml`, the #250 `verdict-rule.txt`). Merged verdicts `verdicts-blind-full.json`, sha256
  `f7e3171b26de8c5272a28fad6097b5d1eed7f163714e732a3dbd89c37dcfb16d`.

## Test A: choosing the config

| Config | Critical path p50 / p90 / max | First evidence p50 | Cut / invalid | Behavior = expected | New calls | USD |
|---|---|---|---|---|---|---|
| #250 (same six) | 848 / 996 / 1,079 s | 209 s | 1 / 1 | 4/6 | - | - |
| **C1** plan off, map low, reduce low | **209 / 313 / 383 s** | 17 s | 0 / 0 | 6/6 | 152 | 3.60 |
| C2 plan off, map off, reduce low | 172 / 289 / 360 s | 9 s | 0 / 1 | 6/6 | 156 | 0.83 |
| C3 C1 with map on deepseek-flash | 206 / 361 / 456 s | 10 s | 0 / 3 | 6/6 | 149 | 1.31 |

Rule (fixed before any call): eligible = 0 cut, 0 invalid, behavior match >= 4/6 (#250); then the lowest median.
Only C1 is eligible (C2: Q19 map.a1.EDJ arguments not JSON with thinking off; C3: three flash maps not JSON).
**C1 chosen; flash not adopted.** Defaults set in `src/cee/config.py`. A stream probe on Q5 (6 calls, $0.13) first
showed that streaming works with strict tools, thinking on and off.

## Test B: scores

Classes: r retrieval, s shape / part missing, b behavior, c corpus gap, i invalid output. bl = borderline.

| Q | Tier | Expected -> got | #250 adjudicated | Blind (this run) | Adjudicated (this run) | Class (blind) | Critical path s | First evidence s | Calls |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | answer -> answer | PASS | **PASS** | **PASS** |  | 28.4 | 17.9 | 3 |
| Q2 | 1 | answer -> answer | PASS | **PASS** | **PASS** |  | 166.8 | 21.0 | 8 |
| Q3 | 1 | answer -> answer | PASS | **FAIL** bl | **FAIL** bl | s | 152.9 | 17.9 | 8 |
| Q4 | 1 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 197.4 | 20.2 | 9 |
| Q5 | 1 | answer -> answer | FAIL | **PASS** | **PASS** |  | 91.5 | 25.7 | 6 |
| Q6 | 1 | answer -> answer | PASS | **PASS** | **PASS** |  | 142.3 | 21.9 | 10 |
| Q7 | 2 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 246.9 | 19.9 | 38 |
| Q8 | 2 | answer -> answer | PASS | **FAIL** bl | **PASS** bl | s | 120.1 | 19.2 | 6 |
| Q9 | 3 | answer -> answer | PASS | **PASS** | **PASS** |  | 91.9 | 15.6 | 15 |
| Q10 | 3 | answer -> answer | FAIL | **PASS** | **PASS** |  | 239 | 21.1 | 40 |
| Q11 | 1 | answer -> answer | FAIL | **FAIL** | **FAIL** | r, s | 165.1 | 7.9 | 34 |
| Q12 | 3 | answer_with_boundary -> answer_with_boundary | FAIL | **PASS** | **PASS** |  | 188.2 | 13.1 | 13 |
| Q13 | 1 | answer -> answer | PASS | **PASS** | **PASS** |  | 169 | 17.3 | 10 |
| Q14 | 3 | answer -> answer | PASS | **PASS** | **PASS** |  | 157.1 | 23.6 | 7 |
| Q15 | 3 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 208.1 | 12.2 | 43 |
| Q16 | 3 | answer -> answer | FAIL | **PASS** bl | **PASS** bl |  | 204.1 | 14.3 | 26 |
| Q17 | 1 | answer -> answer | PASS | **FAIL** bl | **PASS** bl | s | 284.7 | 41.5 | 20 |
| Q18 | 3 | answer -> answer | FAIL | **PASS** bl | **PASS** bl |  | 215.6 | 19.0 | 16 |
| Q19 | 3 | answer_with_boundary -> answer_with_boundary | PASS | **PASS** | **PASS** |  | 177.2 | 9.7 | 29 |
| Q20 | 1 | answer -> answer | FAIL | **FAIL** bl | **FAIL** bl | s, c | 218.8 | 9.1 | 29 |
| Q21 | 2 | answer -> answer | FAIL | **PASS** bl | **PASS** bl |  | 383.2 | 13.4 | 56 |
| Q22 | 1 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 208.2 | 8.4 | 12 |
| Q23 | 1 | answer -> answer | FAIL | **FAIL** bl | **FAIL** bl | c, r | 144.2 | 32.9 | 7 |
| Q24 | 3 | answer -> answer | PASS | **PASS** | **PASS** |  | 241.8 | 24.8 | 22 |
| Q25 | 1 | answer -> answer | FAIL | **PASS** bl | **PASS** bl |  | 239.8 | 9.8 | 39 |
| Q26 | 1 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 179.3 | 11.6 | 10 |
| Q27 | 1 | answer -> answer | PASS | **PASS** bl | **PASS** bl |  | 215.4 | 16.3 | 10 |
| Q28 | 1 | answer -> answer | FAIL | **FAIL** bl | **FAIL** bl | s | 173.2 | 9.2 | 9 |
| Q29 | 1 | gap_with_adjacent -> None | FAIL | **FAIL** | **FAIL** | i | 3749.8 | 30.1 | 7 |
| Q30 | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | **PASS** | **PASS** |  | 62.9 | 43.0 | 3 |

Second read (PR #273 review round 1): Q3 FAIL (no concession by management is shown and the gap is not marked), Q8 PASS
(borderline), Q17 PASS (borderline); every other question equals the blind verdict.
Changes against #250, adjudicated: PASS -> FAIL Q3; FAIL -> PASS Q5, Q10, Q12, Q16, Q18, Q21, Q25 (blind read: also
Q8 and Q17 PASS -> FAIL). Q29 is FAIL (i):
its reduce call stalled with no output and timed out after 3660 s (saved as a failed call, never re-called).

## Latency tables

#### Test B fts, Q1-Q30 (C1)

30 questions, 545 call records: critical path p50 184 s, p90 251 s, max 3,750 s; first evidence p50 17.9 s, p90 30.38 s; cut 0, invalid 1, failed 1.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 3.3 | 1 | 14.6 | 0 | - | 10.5 | 28.4 | 17.9 | 0 |
| Q2 | 4.9 | 6 | 82.3 | 0 | - | 79.6 | 167 | 21 | 0 |
| Q3 | 4 | 6 | 47.2 | 0 | - | 102 | 153 | 17.9 | 0 |
| Q4 | 4.1 | 7 | 64.7 | 0 | - | 129 | 197 | 20.2 | 0 |
| Q5 | 5.3 | 4 | 47.6 | 0 | - | 38.6 | 91.5 | 25.7 | 0 |
| Q6 | 5.1 | 7 | 64.1 | 1 | 3.3 | 69.8 | 142 | 21.9 | 0 |
| Q7 | 6.2 | 35 | 79.1 | 1 | 2.8 | 159 | 247 | 19.9 | 0 |
| Q8 | 2.8 | 4 | 32.1 | 0 | - | 85.2 | 120 | 19.2 | 0 |
| Q9 | 5 | 12 | 27.4 | 1 | 3.8 | 55.7 | 91.9 | 15.6 | 0 |
| Q10 | 9.6 | 31 | 72.1 | 7 | 20.1 | 137 | 239 | 21.1 | 0 |
| Q11 | 3.6 | 25 | 58.6 | 7 | 9.1 | 93.8 | 165 | 7.9 | 0 |
| Q12 | 5.1 | 11 | 51.8 | 0 | - | 131 | 188 | 13.1 | 0 |
| Q13 | 5.9 | 8 | 38.9 | 0 | - | 124 | 169 | 17.3 | 0 |
| Q14 | 3.8 | 5 | 85 | 0 | - | 68.3 | 157 | 23.6 | 0 |
| Q15 | 9.6 | 41 | 98.8 | 0 | - | 99.7 | 208 | 12.2 | 0 |
| Q16 | 5.4 | 24 | 69.8 | 0 | - | 129 | 204 | 14.3 | 0 |
| Q17 | 4.5 | 18 | 126 | 0 | - | 154 | 285 | 41.5 | 0 |
| Q18 | 4 | 14 | 75 | 0 | - | 137 | 216 | 19 | 0 |
| Q19 | 6.1 | 24 | 50.2 | 3 | 3.7 | 117 | 177 | 9.7 | 0 |
| Q20 | 6.2 | 27 | 75 | 0 | - | 138 | 219 | 9.1 | 0 |
| Q21 | 7.5 | 46 | 55.3 | 8 | 17.7 | 303 | 383 | 13.4 | 0 |
| Q22 | 2.2 | 10 | 74.3 | 0 | - | 132 | 208 | 8.4 | 0 |
| Q23 | 1.8 | 5 | 72.8 | 0 | - | 69.5 | 144 | 32.9 | 0 |
| Q24 | 3.5 | 20 | 85.6 | 0 | - | 153 | 242 | 24.8 | 0 |
| Q25 | 5 | 34 | 57.7 | 3 | 7.8 | 169 | 240 | 9.8 | 0 |
| Q26 | 5.3 | 8 | 43.3 | 0 | - | 131 | 179 | 11.6 | 0 |
| Q27 | 5.1 | 8 | 73.7 | 0 | - | 137 | 215 | 16.3 | 0 |
| Q28 | 3.4 | 7 | 72.7 | 0 | - | 97.1 | 173 | 9.2 | 0 |
| Q29 | 3.8 | 5 | 85.6 | 0 | - | 3,660 | 3,750 | 30.1 | 0 |
| Q30 | 2.2 | 1 | 40.8 | 0 | - | 19.9 | 62.9 | 43 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 30 | 4.93 | 6.38 | 9.61 | 1.29 | 1.53 | 488 | 1,282 | - |
| map | 454 | 34.16 | 59.61 | 126 | 4.22 | 7.45 | 3,733 | 20,813 | 0.77 |
| remap | 31 | 4.69 | 9.11 | 20.12 | 2.12 | 3.09 | 308 | 2,806 | 0.69 |
| reduce | 30 | 126 | 160 | 3,660 | 2.47 | 4.35 | 22,375 | 57,498 | 0.63 |

#### W11 #250 fts, the six test-A questions (baseline)

6 questions, 44 call records: critical path p50 848 s, p90 996 s, max 1,079 s; first evidence p50 209 s, p90 405 s; cut 1, invalid 1, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|
| Q5 | 33.1 | 1 | 97 | 0 | - | 8.9 | 139 | 130 | 0 |
| Q10 | 53.8 | 6 | 135 | 0 | - | 321 | 510 | 63.2 | 0 |
| Q19 | 144 | 4 | 365 | 3 | 13.9 | 556 | 1,079 | 214 | 0 |
| Q21 | 122 | 6 | 285 | 4 | 69.5 | 340 | 816 | 268 | 1 |
| Q24 | 30.8 | 5 | 377 | 1 | 180 | 325 | 913 | 204 | 0 |
| Q26 | 40.3 | 1 | 501 | 1 | 10.1 | 328 | 879 | 542 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 47.05 | 133 | 144 | - | - | 5,404 | 16,531 | 0.92 |
| map | 23 | 176 | 358 | 501 | - | - | 24,557 | 50,927 | 0.9 |
| remap | 9 | 10.81 | 91.71 | 180 | - | - | 1,023 | 19,145 | 0.9 |
| reduce | 6 | 326 | 448 | 556 | - | - | 53,422 | 64,000 | 0.88 |

#### C1: plan off, map low, reduce low (chosen)

6 questions, 163 call records: critical path p50 209 s, p90 312 s, max 383 s; first evidence p50 17.25 s, p90 25.25 s; cut 0, invalid 0, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5.3 | 4 | 47.6 | 0 | - | 38.6 | 91.5 | 25.7 | 0 |
| Q10 | 9.6 | 31 | 72.1 | 7 | 20.1 | 137 | 239 | 21.1 | 0 |
| Q19 | 6.1 | 24 | 50.2 | 3 | 3.7 | 117 | 177 | 9.7 | 0 |
| Q21 | 7.5 | 46 | 55.3 | 8 | 17.7 | 303 | 383 | 13.4 | 0 |
| Q24 | 3.5 | 20 | 85.6 | 0 | - | 153 | 242 | 24.8 | 0 |
| Q26 | 5.3 | 8 | 43.3 | 0 | - | 131 | 179 | 11.6 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 5.71 | 8.53 | 9.55 | 1.5 | 1.81 | 541 | 810 | - |
| map | 133 | 29.48 | 47.71 | 85.61 | 4.47 | 8.37 | 2,990 | 11,523 | 0.77 |
| remap | 18 | 4.22 | 17.71 | 20.12 | 2 | 2.43 | 298 | 2,806 | 0.69 |
| reduce | 6 | 134 | 228 | 303 | 2.66 | 3.63 | 23,618 | 57,498 | 0.65 |

#### C2: plan off, map off, reduce low

6 questions, 162 call records: critical path p50 172 s, p90 289 s, max 360 s; first evidence p50 8.95 s, p90 12.8 s; cut 0, invalid 1, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5.3 | 4 | 10.7 | 0 | - | 46.2 | 62.2 | 13.8 | 0 |
| Q10 | 9.6 | 31 | 12.2 | 5 | 5.3 | 131 | 158 | 11.8 | 0 |
| Q19 | 6.1 | 24 | 10.1 | 4 | 2.5 | 163 | 182 | 8.2 | 0 |
| Q21 | 7.5 | 46 | 21.8 | 6 | 2.4 | 187 | 219 | 9.7 | 0 |
| Q24 | 3.5 | 20 | 12.6 | 2 | 5.6 | 338 | 360 | 6.4 | 0 |
| Q26 | 5.3 | 8 | 13.2 | 0 | - | 144 | 162 | 7.5 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 5.71 | 8.53 | 9.55 | 1.5 | 1.81 | 541 | 810 | - |
| map | 133 | 8.7 | 13.6 | 21.8 | 1.73 | 2.32 | 905 | 2,737 | - |
| remap | 17 | 2.12 | 3.82 | 5.59 | 1.44 | 2.08 | 121 | 818 | - |
| reduce | 6 | 153 | 263 | 338 | 2.16 | 3.73 | 27,998 | 57,633 | 0.58 |

#### C3: C1 with the map on deepseek-flash

6 questions, 155 call records: critical path p50 206 s, p90 361 s, max 456 s; first evidence p50 10.25 s, p90 18.7 s; cut 0, invalid 3, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | cut |
|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5.3 | 4 | 42.8 | 0 | - | 25.6 | 73.7 | 22.2 | 0 |
| Q10 | 9.6 | 31 | 45.9 | 3 | 4.6 | 206 | 266 | 15.2 | 0 |
| Q19 | 6.1 | 24 | 33.6 | 4 | 2.7 | 213 | 256 | 8.9 | 0 |
| Q21 | 7.5 | 46 | 89.7 | 3 | 2.1 | 357 | 456 | 10.6 | 0 |
| Q24 | 3.5 | 20 | 39.9 | 0 | - | 101 | 144 | 9.9 | 0 |
| Q26 | 5.3 | 8 | 47.4 | 0 | - | 103 | 156 | 8.3 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 5.71 | 8.53 | 9.55 | 1.5 | 1.81 | 541 | 810 | - |
| map | 133 | 24.89 | 58.33 | 89.69 | 1.31 | 1.83 | 3,517 | 16,158 | 0.78 |
| remap | 10 | 2.05 | 2.89 | 4.62 | 1.04 | 1.23 | 190 | 963 | 0.46 |
| reduce | 6 | 155 | 285 | 357 | 2.54 | 3.43 | 27,521 | 68,438 | 0.65 |

## Calls and cost (DeepSeek, all off-peak, prices `config/pricing.yaml`)

- Test A: 468 new calls (probe 6, C1 plan 5 + run 152, C2 156, C3 149), USD 5.87.
- Test B: 380 new calls (planner 24, run 298 before the 402, 58 after), USD 11.94. The 30 answers used 545 calls
  (planner 30, map 454, re-map 31, reduce 30), USD 15.56 for every call they used (#250: 146 calls, USD 9.52):
  about $0.52 per question. One call per cell repeats the cell's pool passages, so input tokens grew to 16.5M.
- Total new for #272 so far: 848 calls, USD 17.81. Re-run with reduce `high`: not needed (floor met).

## Findings

1. **Latency** fell from 415 s to 184 s median (-56%); the first cited evidence shows at 18 s median. The reduce
   call (p50 126 s, about 22k output tokens at effort low) is now most of the remaining time; the map's slowest call
   is 34-60 s. 30 s end to end is not reached; the plan's direct-answer path needs the median under 60 s first
   (item 7b, ADR-021 amendment) and is left as a follow-up.
2. **A stalled stream waits for the 3600 s read timeout** (Q29 reduce: no chunk for an hour). With streaming, a much
   shorter read timeout between chunks would turn this into a quick failed call. Follow-up.
3. **Thinking off is less reliable for strict JSON**: C2 (map off) and flash (C3) each produced map arguments that
   are not JSON; C1 had none in 163 test-A and 545 test-B records.
4. **The reduce message is not byte-stable across processes**: Q21's reduce key changed between test A and test B
   although every plan and map record was reused (one extra call); #250 saw the same on Q12. Follow-up.
5. Cost per question rose (input repeated per cell). Prefix caching barely applied (cache hits 4%).

Evidence: `docs/results/w12-latency/` (raw records and reports of every run, head logs, verdicts, helper scripts);
working copies and caches `D:\ALLPROJECTS\EDJ\cache\ev272\`.
