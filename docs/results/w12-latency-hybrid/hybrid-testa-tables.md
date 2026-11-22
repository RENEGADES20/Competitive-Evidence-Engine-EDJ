### Hybrid test A (C1: plan off, map low, reduce low)

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
