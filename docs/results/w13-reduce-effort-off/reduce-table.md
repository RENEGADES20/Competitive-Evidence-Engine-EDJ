| Set | Records | Wall p50 s | Wall p90 s | Max s | Tokens/s p50 | Output tokens | USD as run | USD at peak | Period | Failed |
|---|---|---|---|---|---|---|---|---|---|---|
| v8-off (this run), Q1-Q30 | 30 | 10.4 | 18.8 | 136.61 | 73.1 | 68,004 | 0.746 | 0.870 | off_peak, peak | 0 |
| v5.2 (#272 test B), Q1-Q30 | 30 | 124.2 | 155.3 | 302.7 | 180.8 | 602,621 | 1.555 | 3.111 | off_peak | 1 |
| v8-off, Q5 Q8 Q22 Q24 | 4 | 6.8 | 12.1 | 13.97 | 78.5 | 2,538 | 0.013 | 0.013 | peak | 0 |
| v8-low (#292), Q5 Q8 Q22 Q24 | 4 | 142.2 | 318.0 | 343.0 | 78.3 | 50,355 | 0.267 | 0.267 | peak | 0 |
| v5.2 (#272), Q5 Q8 Q22 Q24 | 4 | 108.5 | 146.4 | 152.69 | 183.7 | 74,570 | 0.182 | 0.364 | off_peak | 0 |

| Q | v8-off version / request | wall s | out / reasoning | tok/s | USD (period) | v5.2 wall s | v5.2 out | v8-low wall s |
|---|---|---|---|---|---|---|---|---|
| Q1 | v8 / ds-strict-2-reduce-off-c64000-s1 | 5.92 | 331 / None | 55.91 | 0.0036 (peak) | 10.5 | 1884 | - |
| Q2 | v8 / ds-strict-2-reduce-off-c64000-s1 | 9.17 | 598 / None | 65.21 | 0.0194 (peak) | 79.58 | 14306 | - |
| Q3 | v8 / ds-strict-2-reduce-off-c64000-s1 | 8.89 | 715 / None | 80.43 | 0.0162 (peak) | 101.75 | 18702 | - |
| Q4 | v8 / ds-strict-2-reduce-off-c64000-s1 | 9.31 | 707 / None | 75.94 | 0.0134 (peak) | 128.7 | 22375 | - |
| Q5 | v8 / ds-strict-2-reduce-off-c64000-s1 | 7.69 | 383 / None | 49.8 | 0.0019 (peak) | 38.61 | 7272 | 14.58 |
| Q6 | v8 / ds-strict-2-reduce-off-c64000-s1 | 8.14 | 631 / None | 77.52 | 0.0177 (peak) | 69.83 | 12419 | - |
| Q7 | v8 / ds-strict-2-reduce-off-c64000-s1 | 10.62 | 809 / None | 76.18 | 0.0541 (peak) | 158.77 | 31571 | - |
| Q8 | v8 / ds-strict-2-reduce-off-c64000-s1 | 5.95 | 443 / None | 74.45 | 0.0023 (peak) | 85.25 | 15146 | 24.67 |
| Q9 | v8 / ds-strict-2-reduce-off-c64000-s1 | 7.83 | 678 / None | 86.59 | 0.0145 (peak) | 55.67 | 11225 | - |
| Q10 | v8 / ds-strict-2-reduce-off-c64000-s1 | 24.53 | 2067 / None | 84.26 | 0.0305 (peak) | 137.25 | 24330 | - |
| Q11 | v8 / ds-strict-2-reduce-off-c64000-s1 | 11.25 | 775 / None | 68.89 | 0.0223 (peak) | 93.77 | 16844 | - |
| Q12 | v8 / ds-strict-2-reduce-off-c64000-s1 | 11.45 | 791 / None | 69.08 | 0.0216 (peak) | 131.36 | 25635 | - |
| Q13 | v8 / ds-strict-2-reduce-off-c64000-s1 | 10.47 | 751 / None | 71.73 | 0.0191 (peak) | 124.2 | 22458 | - |
| Q14 | v8 / ds-strict-2-reduce-off-c64000-s1 | 6.48 | 451 / None | 69.6 | 0.0128 (peak) | 68.34 | 12636 | - |
| Q15 | v8 / ds-strict-2-reduce-off-c64000-s1 | 13.53 | 634 / None | 46.86 | 0.072 (peak) | 99.7 | 18098 | - |
| Q16 | v8 / ds-strict-2-reduce-off-c64000-s1 | 10.39 | 521 / None | 50.14 | 0.0496 (peak) | 128.91 | 27248 | - |
| Q17 | v8 / ds-strict-2-reduce-off-c64000-s1 | 13.05 | 652 / None | 49.96 | 0.0448 (peak) | 154.45 | 29953 | - |
| Q18 | v8 / ds-strict-2-reduce-off-c64000-s1 | 15.47 | 694 / None | 44.86 | 0.0253 (peak) | 136.69 | 24657 | - |
| Q19 | v8 / ds-strict-2-reduce-off-c64000-s1 | 10.47 | 840 / None | 80.23 | 0.0218 (peak) | 117.14 | 21036 | - |
| Q20 | v8 / ds-strict-2-reduce-off-c64000-s1 | 9.84 | 759 / None | 77.13 | 0.017 (peak) | 137.56 | 25861 | - |
| Q21 | v8 / ds-strict-2-reduce-off-c64000-s1 | 18.2 | 1179 / None | 64.78 | 0.0608 (peak) | 302.7 | 57498 | - |
| Q22 | v8 / ds-strict-2-reduce-off-c64000-s1 | 5.92 | 558 / None | 94.26 | 0.0029 (peak) | 131.69 | 24824 | 259.69 |
| Q23 | v8 / ds-strict-2-reduce-off-c64000-s1 | 12.0 | 713 / None | 59.42 | 0.0114 (peak) | 69.53 | 12706 | - |
| Q24 | v8 / ds-strict-2-reduce-off-c64000-s1 | 13.97 | 1154 / None | 82.61 | 0.0058 (peak) | 152.69 | 27328 | 343.0 |
| Q25 | v8 / ds-strict-2-reduce-off-c64000-s1 | 11.47 | 765 / None | 66.7 | 0.0364 (peak) | 169.31 | 30175 | - |
| Q26 | v5.2 / ds-strict-2-reduce-low-c128000-s1 | 130.72 | 22906 / 16128 | 175.23 | 0.0635 (off_peak) | 130.72 | 22906 | - |
| Q27 | v5.2 / ds-strict-2-reduce-low-c128000-s1 | 136.61 | 24936 / 20027 | 182.53 | 0.0605 (off_peak) | 136.61 | 24936 | - |
| Q28 | v8 / ds-strict-2-reduce-off-c64000-s1 | 7.25 | 654 / None | 90.21 | 0.0086 (peak) | 97.12 | 16052 | - |
| Q29 | v8 / ds-strict-2-reduce-off-c64000-s1 | 6.86 | 560 / None | 81.63 | 0.01 (peak) | 3660.36 | None | - |
| Q30 | v8 / ds-strict-2-reduce-off-c64000-s1 | 4.88 | 349 / None | 71.52 | 0.0057 (peak) | 19.95 | 2540 | - |
