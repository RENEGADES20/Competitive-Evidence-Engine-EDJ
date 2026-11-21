# #250 hybrid-norerank: 0-call count, cap and map message-hash check (before the hybrid run)

Code: exp/hybrid 36b0b58 (worktree `wt-250h`, branch `tl/250-hybrid`). Plans: `--reuse-plans deepseek:deepseek-v4-pro` (30 saved plans, 0 planner calls).
First count `count1-hyb` on a cache with every committed record plus the fts run's 101 new records: 30 plans reused, **0 inherited map / remap records reused** (all 76 round-1 map calls have different inputs from fts and #247), so the allow list is empty (C3).
Final cache `cache-hyb-final`: plans and reduces only (152 inherited map / remap records left out). Final count `count2-hyb`: real_calls 0, reused 30, 0 inherited map records served; no fts reduce reused at the count.

# hybrid-norerank count C-hyb (count2-hyb, exp/hybrid 36b0b58)

From `count2-hyb\report.json` (0 calls; meta.real_calls 0, reused 30).

| Q | plan | sub-q | round-1 maps served | round-1 to make | row keys (non-comparison) | remaps served | round-2 bound | reduce | reduce to make | cap |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | cached: Q1-plan-2842fd95a4bd | 5 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q2 | cached: Q2-plan-1c13be5ec7a6 | 7 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q3 | cached: Q3-plan-751ecc3596a7 | 5 | 0 | 1 | SCHW | 0 | 1 | code_built | 1 | 3 |
| Q4 | cached: Q4-plan-82545e2a7b7f | 12 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |
| Q5 | cached: Q5-plan-ba18bc1a7fbf | 1 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q6 | cached: Q6-plan-0a8df5867283 | 3 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q7 | cached: Q7-plan-5dfaf706584d | 21 | 0 | 4 | MER, MS, RJF | 0 | 3 | code_built | 1 | 8 |
| Q8 | cached: Q8-plan-43c66da6bf28 | 4 | 0 | 2 | RJF, SCHW | 0 | 2 | code_built | 1 | 5 |
| Q9 | cached: Q9-plan-a963b7a4c0a8 | 10 | 0 | 2 | MER, MS | 0 | 2 | code_built | 1 | 5 |
| Q10 | cached: Q10-plan-ec78e571764 | 10 | 0 | 6 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 12 |
| Q11 | cached: Q11-plan-10d2767ebe7 | 20 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q12 | cached: Q12-plan-3c795856ff6 | 8 | 0 | 2 | EDJ, SCHW | 0 | 2 | code_built | 1 | 5 |
| Q13 | cached: Q13-plan-378afa8a249 | 5 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q14 | cached: Q14-plan-b25fe402463 | 8 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q15 | cached: Q15-plan-82186d401f1 | 10 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q16 | cached: Q16-plan-6c86ffcde7f | 11 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q17 | cached: Q17-plan-947690fbef6 | 7 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q18 | cached: Q18-plan-8b4b10bfb12 | 2 | 0 | 1 |  | 0 | 0 | code_built | 1 | 2 |
| Q19 | cached: Q19-plan-fa97302df6c | 65 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q20 | cached: Q20-plan-3a1787ce9cf | 6 | 0 | 1 | all | 0 | 1 | code_built | 1 | 3 |
| Q21 | cached: Q21-plan-f2cc541f326 | 80 | 0 | 6 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 12 |
| Q22 | cached: Q22-plan-cbce9d55f95 | 10 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q23 | cached: Q23-plan-1b401760014 | 5 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q24 | cached: Q24-plan-9998b66bd82 | 20 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q25 | cached: Q25-plan-17c16379324 | 30 | 0 | 5 | EDJ, MER, MS, RJF, SCHW | 0 | 5 | code_built | 1 | 11 |
| Q26 | cached: Q26-plan-b3e8c05eb52 | 8 | 0 | 1 | RJF | 0 | 1 | code_built | 1 | 3 |
| Q27 | cached: Q27-plan-7d9cf938c1a | 13 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |
| Q28 | cached: Q28-plan-7fd84151946 | 6 | 0 | 3 | EDJ, MER | 0 | 2 | code_built | 1 | 6 |
| Q29 | cached: Q29-plan-f692994e5bd | 2 | 0 | 1 | MS | 0 | 1 | code_built | 1 | 3 |
| Q30 | cached: Q30-plan-5cc5df215e8 | 3 | 0 | 1 | MER | 0 | 1 | code_built | 1 | 3 |

**Cap = 177** (round-1 76 + round-2 bound 71 + reduces 30).

## Map message-hash check

now: 36b0b58 (count2-hyb.tsv)

| record | served now | producing source | message | system | schema | request | result |
|---|---|---|---|---|---|---|---|

Inherited records reused now: 0; hash match (allowed): 0; differ: 0; no source hash: 0.
