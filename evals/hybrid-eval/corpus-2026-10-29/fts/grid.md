# Grid fts

Reference (fts): `.eval-runs/p126-ref-fts/report.json`

Selection rule: 1. Eligible: forbidden hits 0 on all questions; refusal accuracy on the gap questions and on all keyed questions >= the fts reference run (--baseline). 2. Among eligible points: highest tier-1 passage recall (3 decimals). 3. Ties: higher tier-1 doc recall; more PASS; the mode's default before #126 (fts 0.3/3, hybrid modes 0/3); higher FLOOR; smaller MAX_PER_DOC. 4. No eligible point: no tuned constants (defaults stay); the mode fails the refusal acceptance.

| FLOOR | MAX_PER_DOC | PASS | tier-1 docs | passages | refusal gap | refusal all | forbidden | dup pairs > 0.9 (trigram / 5-gram) | median s | p90 s | run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 2 | 27 | 0.794 | 0.432 | 5/5 | 10/10 | 0 | 0 / 0 | 0.385 | 0.61 | f0.2-m2 |
| 0.2 | 3 | 27 | 0.782 | 0.474 | 5/5 | 10/10 | 0 | 1 / 0 | 0.336 | 0.506 | f0.2-m3 |
| 0.2 | 4 | 26 | 0.763 | 0.474 | 4/5 | 9/10 | 0 | 1 / 0 | 0.384 | 0.603 | f0.2-m4 |
| 0.3 | 2 | 28 | 0.809 | 0.361 | 5/5 | 10/10 | 0 | 0 / 0 | 0.348 | 0.56 | f0.3-m2 |
| 0.3 | 3 | 28 | 0.796 | 0.402 | 5/5 | 10/10 | 0 | 1 / 0 | 0.342 | 0.687 | f0.3-m3 |
| 0.3 | 4 | 27 | 0.796 | 0.402 | 4/5 | 9/10 | 0 | 1 / 0 | 0.353 | 0.739 | f0.3-m4 |
| 0.4 | 2 | 28 | 0.809 | 0.361 | 5/5 | 10/10 | 0 | 0 / 0 | 0.333 | 0.65 | f0.4-m2 |
| 0.4 | 3 | 28 | 0.796 | 0.402 | 5/5 | 10/10 | 0 | 1 / 0 | 0.37 | 0.677 | f0.4-m3 |
| 0.4 | 4 | 27 | 0.796 | 0.402 | 4/5 | 9/10 | 0 | 1 / 0 | 0.372 | 0.619 | f0.4-m4 |

**Pick**: FLOOR 0.2, MAX_PER_DOC 3 (`f0.2-m3`)

Reason: eligible 6 of 9; best tier-1 passage recall 0.474; beats the runner-up f0.2-m2 on passage recall
- not eligible f0.2-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts
- not eligible f0.3-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts
- not eligible f0.4-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts
