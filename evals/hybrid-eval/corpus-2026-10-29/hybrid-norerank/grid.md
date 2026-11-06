# Grid hybrid-norerank

Reference (fts): `.eval-runs/p126-ref-fts/report.json`

Selection rule: 1. Eligible: forbidden hits 0 on all questions; refusal accuracy on the gap questions and on all keyed questions >= the fts reference run (--baseline). 2. Among eligible points: highest tier-1 passage recall (3 decimals). 3. Ties: higher tier-1 doc recall; more PASS; the mode's default before #126 (fts 0.3/3, hybrid modes 0/3); higher FLOOR; smaller MAX_PER_DOC. 4. No eligible point: no tuned constants (defaults stay); the mode fails the refusal acceptance.

| FLOOR | MAX_PER_DOC | PASS | tier-1 docs | passages | refusal gap | refusal all | forbidden | dup pairs > 0.9 (trigram / 5-gram) | median s | p90 s | run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 2 | 27 | 0.73 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.373 | 0.644 | f0.0-m2 |
| 0.0 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.363 | 0.625 | f0.0-m3 |
| 0.0 | 4 | 28 | 0.706 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.335 | 0.583 | f0.0-m4 |
| 0.2 | 2 | 27 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.371 | 0.581 | f0.2-m2 |
| 0.2 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.351 | 0.644 | f0.2-m3 |
| 0.2 | 4 | 28 | 0.706 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.372 | 0.587 | f0.2-m4 |
| 0.3 | 2 | 27 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.365 | 0.614 | f0.3-m2 |
| 0.3 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.36 | 0.603 | f0.3-m3 |
| 0.3 | 4 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.374 | 0.582 | f0.3-m4 |
| 0.4 | 2 | 26 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.355 | 0.583 | f0.4-m2 |
| 0.4 | 3 | 28 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.348 | 0.594 | f0.4-m3 |
| 0.4 | 4 | 28 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.342 | 0.555 | f0.4-m4 |

**Pick**: FLOOR 0.4, MAX_PER_DOC 3 (`f0.4-m3`)

Reason: eligible 12 of 12; best tier-1 passage recall 0.405; beats the runner-up f0.4-m4 on smaller MAX_PER_DOC
