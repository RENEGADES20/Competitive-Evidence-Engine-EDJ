### W11 #250 fts, the six test-A questions (baseline)

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

### C1: plan off, map low, reduce low (chosen)

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

### C2: plan off, map off, reduce low

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

### C3: C1 with the map on deepseek-flash

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
