### #283 probe Q10 (first_chunk)

1 questions, 42 call records: critical path p50 271 s, p90 271 s, max 271 s; first evidence p50 22.6 s, p90 22.6 s; first claim p50 230 s, p90 230 s; cut 0, invalid 0, failed 0.

| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |
|---|---|---|---|---|---|---|---|---|---|---|
| Q10 | 9.6 | 31 | 86.6 | 9 | 14.6 | 160 | 271 | 22.6 | 230 | 0 |

| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |
|---|---|---|---|---|---|---|---|---|---|
| plan | 1 | 9.55 | 9.55 | 9.55 | 1.59 | 1.59 | 483 | 483 | - |
| map | 31 | 28.28 | 51.48 | 68.44 | 2.39 | 4.88 | 2,030 | 7,518 | 0.84 |
| remap | 9 | 4.89 | 12.6 | 14.56 | 1.7 | 2.14 | 308 | 1,247 | 0.72 |
| reduce | 1 | 160 | 160 | 160 | 1.34 | 1.34 | 21,158 | 21,158 | 0.66 |

| Calls | n | input tokens | cache-hit tokens | hit share | gate wait p50 s | gate wait max s |
|---|---|---|---|---|---|---|
| plan | 1 | 1,386 | 0 | 0 | - | - |
| map | 31 | 2,383,276 | 1,832,704 | 0.769 | 7.55 | 18.22 |
| remap | 9 | 65,983 | 0 | 0 | - | - |
| reduce | 1 | 15,168 | 1,664 | 0.11 | - | - |
| all | 42 | 2,465,813 | 1,834,368 | 0.744 | 7.55 | 18.22 |
| map cell | 1 | 2,701 | 0 | 0 | - | - |
| map follower | 25 | 1,985,060 | 1,832,704 | 0.923 | 10.75 | 18.22 |
| map leader | 5 | 395,515 | 0 | 0 | 0 | 0 |

Probe rule (plans/0283-prefix-cache.md, B4): 25 followers, prefix tokens 1,973,312, cache-hit tokens 1,832,704, share 0.929 -> MAP_PREFIX_GATE=first_chunk (share 0.929 >= 0.5).
