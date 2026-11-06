# Grid hybrid

Reference (fts): `.eval-runs/p126-ref-fts/report.json`

Selection rule: 1. Eligible: forbidden hits 0 on all questions; refusal accuracy on the gap questions and on all keyed questions >= the fts reference run (--baseline). 2. Among eligible points: highest tier-1 passage recall (3 decimals). 3. Ties: higher tier-1 doc recall; more PASS; the mode's default before #126 (fts 0.3/3, hybrid modes 0/3); higher FLOOR; smaller MAX_PER_DOC. 4. No eligible point: no tuned constants (defaults stay); the mode fails the refusal acceptance.

| FLOOR | MAX_PER_DOC | PASS | tier-1 docs | passages | refusal gap | refusal all | forbidden | dup pairs > 0.9 (trigram / 5-gram) | median s | p90 s | run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 2 | 27 | 0.728 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 8.046 | 9.376 | f0.0-m2 |
| 0.0 | 3 | 27 | 0.728 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.186 | 9.544 | f0.0-m3 |
| 0.0 | 4 | 28 | 0.728 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.424 | 9.411 | f0.0-m4 |
| 0.2 | 2 | 27 | 0.716 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 8.229 | 9.396 | f0.2-m2 |
| 0.2 | 3 | 27 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.308 | 9.488 | f0.2-m3 |
| 0.2 | 4 | 28 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.174 | 9.386 | f0.2-m4 |
| 0.3 | 2 | 27 | 0.716 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 6.692 | 9.327 | f0.3-m2 |
| 0.3 | 3 | 27 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 4 / 0 | 6.617 | 9.307 | f0.3-m3 |
| 0.3 | 4 | 28 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 4 / 0 | 6.781 | 9.361 | f0.3-m4 |
| 0.4 | 2 | 26 | 0.738 | 0.333 | 5/5 | 10/10 | 0 | 0 / 0 | 5.796 | 8.723 | f0.4-m2 |
| 0.4 | 3 | 27 | 0.738 | 0.402 | 5/5 | 10/10 | 0 | 0 / 0 | 5.127 | 8.113 | f0.4-m3 |
| 0.4 | 4 | 28 | 0.738 | 0.402 | 5/5 | 10/10 | 0 | 0 / 0 | 5.075 | 8.067 | f0.4-m4 |

**Pick**: FLOOR 0.4, MAX_PER_DOC 4 (`f0.4-m4`)

Reason: eligible 12 of 12; best tier-1 passage recall 0.402; beats the runner-up f0.4-m3 on PASS
