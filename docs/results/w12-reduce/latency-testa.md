### a-r1-q5

1 questions, 6 call records: critical path p50 72.8 s, p90 72.8 s, max 72.8 s; first evidence p50 25.7 s, p90 25.7 s; first claim p50 57.9 s, p90 57.9 s; cut 0, invalid 0, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |
|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5.3 | 4 | 47.6 | 0 | - | 19.9 | 72.8 | 25.7 | 57.9 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 1 | 5.27 | 5.27 | 5.27 | 2 | 2 | 295 | 295 | - |
| map | 4 | 32.28 | 43.04 | 47.62 | 3.42 | 3.81 | 4,438 | 6,546 | 0.76 |
| reduce | 1 | 19.88 | 19.88 | 19.88 | 1.78 | 1.78 | 2,818 | 2,818 | - |
### a-r1

5 questions, 157 call records: critical path p50 112 s, p90 142 s, max 150 s; first evidence p50 13.4 s, p90 23.32 s; first claim p50 83.8 s, p90 102 s; cut 0, invalid 0, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |
|---|---|---|---|---|---|---|---|---|---|---|
| Q10 | 9.6 | 31 | 72.1 | 7 | 20.1 | 28.3 | 130 | 21.1 | 108 | 0 |
| Q19 | 6.1 | 24 | 50.2 | 3 | 3.7 | 35.7 | 95.7 | 9.7 | 63 | 0 |
| Q21 | 7.5 | 46 | 55.3 | 8 | 17.7 | 69.4 | 150 | 13.4 | 83.8 | 0 |
| Q24 | 3.5 | 20 | 85.6 | 0 | - | 22.6 | 112 | 24.8 | 92.3 | 0 |
| Q26 | 5.3 | 8 | 43.3 | 0 | - | 39.4 | 88 | 11.6 | 52.8 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 5 | 6.14 | 8.73 | 9.55 | 1.41 | 1.6 | 599 | 810 | - |
| map | 129 | 28.86 | 47.75 | 85.61 | 4.48 | 8.44 | 2,932 | 11,523 | 0.77 |
| remap | 18 | 4.22 | 17.71 | 20.12 | 2 | 2.43 | 298 | 2,806 | 0.69 |
| reduce | 5 | 35.67 | 57.42 | 69.44 | 1.73 | 1.98 | 5,954 | 9,957 | - |
### a-r2

6 questions, 163 call records: critical path p50 113 s, p90 175 s, max 187 s; first evidence p50 17.25 s, p90 25.25 s; first claim p50 75.85 s, p90 102 s; cut 0, invalid 0, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |
|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5.3 | 4 | 47.6 | 0 | - | 21.2 | 74 | 25.7 | 58.9 | 0 |
| Q10 | 9.6 | 31 | 72.1 | 7 | 20.1 | 62.1 | 164 | 21.1 | 108 | 0 |
| Q19 | 6.1 | 24 | 50.2 | 3 | 3.7 | 44.5 | 104 | 9.7 | 64.6 | 0 |
| Q21 | 7.5 | 46 | 55.3 | 8 | 17.7 | 106 | 187 | 13.4 | 87.1 | 0 |
| Q24 | 3.5 | 20 | 85.6 | 0 | - | 32 | 121 | 24.8 | 94.8 | 0 |
| Q26 | 5.3 | 8 | 43.3 | 0 | - | 44.7 | 93.3 | 11.6 | 54.1 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 6 | 5.71 | 8.53 | 9.55 | 1.5 | 1.81 | 541 | 810 | - |
| map | 133 | 29.48 | 47.71 | 85.61 | 4.47 | 8.37 | 2,990 | 11,523 | 0.77 |
| remap | 18 | 4.22 | 17.71 | 20.12 | 2 | 2.43 | 298 | 2,806 | 0.69 |
| reduce | 6 | 44.61 | 84.31 | 106 | 3.22 | 4.36 | 6,786 | 16,586 | - |
