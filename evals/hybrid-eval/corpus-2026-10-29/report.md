# Retrieval modes compared: fts, hybrid-norerank, hybrid (#126)

Snapshot `corpus-2026-10-29`, as of 2026-10-29, k=20, min coverage 0.5, mock provider, 0 real calls. CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel, 12 logical CPUs, Windows, onnxruntime 1.23.2. Commits: fts `d784e30`, hybrid-norerank `3950a80`, hybrid `3950a80`.

Modes: `fts` = keyword search (`main`'s mode). `hybrid-norerank` = keyword + vector legs fused by RRF per firm, 50-candidate pool by (firm, document type), final order by RRF score. `hybrid` = the same candidates, final order by the local cross-encoder (Xenova/ms-marco-MiniLM-L-12-v2). FLOOR is relative: fts on ts_rank, both hybrid modes on the RRF score before any rerank (the cross-encoder sigmoid is not a ratio scale). Time-window questions have no floor in any mode; the window cap (8) and the research cap (2) are not tuned. fts's DUP_JACCARD is measured, never changed.

This report gives numbers; the decision on the default mode is #127.

## At the constants the selection rule picked

| Mode | Constants | PASS / FAIL | Tier-1 docs | Tier-1 passages | Refusal Q24, Q25, Q28-Q30 | Refusal all keyed | Forbidden hits | Dup pairs > 0.9 (trigram / 5-gram; max trigram) | Search s median / p90 / max (warm-up) |
|---|---|---|---|---|---|---|---|---|---|
| `fts` | FLOOR 0.2, MAX_PER_DOC 3, DUP_JACCARD 0.6 | 27 / 3 | 0.782 | 0.474 | 5/5 | 10/10 | 0 | 1 / 0; 0.911 | 0.336 / 0.506 / 0.778 (0.469) |
| `hybrid-norerank` | FLOOR 0.4, MAX_PER_DOC 3, DUP_JACCARD 0.6 | 28 / 2 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0; 0.893 | 0.307 / 0.526 / 0.66 (1.618) |
| `hybrid` | FLOOR 0.4, MAX_PER_DOC 4, DUP_JACCARD 0.6 | 28 / 2 | 0.738 | 0.402 | 5/5 | 10/10 | 0 | 0 / 0; 0.893 | 5.107 / 8.199 / 8.613 (4.52) |

## At each mode's default before #126

| Mode | Constants | PASS / FAIL | Tier-1 docs | Tier-1 passages | Refusal Q24, Q25, Q28-Q30 | Refusal all keyed | Forbidden hits | Dup pairs > 0.9 (trigram / 5-gram; max trigram) | Search s median / p90 / max (warm-up) |
|---|---|---|---|---|---|---|---|---|---|
| `fts` | FLOOR 0.3, MAX_PER_DOC 3, DUP_JACCARD 0.6 | 28 / 2 | 0.796 | 0.402 | 5/5 | 10/10 | 0 | 1 / 0; 0.911 | 0.342 / 0.687 / 0.867 (0.469) |
| `hybrid-norerank` | FLOOR 0.0, MAX_PER_DOC 3, DUP_JACCARD 0.6 | 28 / 2 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0; 0.893 | 0.363 / 0.625 / 0.802 (2.092) |
| `hybrid` | FLOOR 0.0, MAX_PER_DOC 3, DUP_JACCARD 0.6 | 27 / 3 | 0.728 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0; 0.938 | 8.186 / 9.544 / 9.841 (9.505) |

## Selection rule (fixed in `plans/0126-hybrid-eval.md` before any grid run)

1. Eligible: forbidden hits 0 on all questions; refusal accuracy on the gap questions and on all keyed questions >= the fts reference run (--baseline). 2. Among eligible points: highest tier-1 passage recall (3 decimals). 3. Ties: higher tier-1 doc recall; more PASS; the mode's default before #126 (fts 0.3/3, hybrid modes 0/3); higher FLOOR; smaller MAX_PER_DOC. 4. No eligible point: no tuned constants (defaults stay); the mode fails the refusal acceptance.

Tuned and scored on the same 30 questions (no held-out set): one passage is about 0.02 of tier-1 passage recall, so small differences are weak evidence.

## Findings

Numbers only; the decision on the default mode is #127.

1. **Picks.** `fts`: FLOOR 0.2, MAX_PER_DOC 3 (tier-1 passages 0.402 -> 0.474, PASS 28 -> 27: Q17
   FAIL, coverage 3/7, from 4/7). `hybrid-norerank`: FLOOR 0.4, MAX_PER_DOC 3 (passages 0.389 -> 0.405).
   `hybrid`: FLOOR 0.4, MAX_PER_DOC 4 (passages 0.373 -> 0.402, PASS 27 -> 28). The fts pick is reported
   only: `fts.py` constants are unchanged on `exp/hybrid` (they mirror `main`; #127 / S1). The hybrid
   picks are the defaults in `hybrid.py` on `exp/hybrid`. Both hybrid picks sit at the edge of the grid
   (FLOOR 0.4); higher values were not run.
2. **Refusal acceptance met.** Every point of every grid has refusal 5/5 on Q24, Q25, Q28, Q29, Q30
   and 10/10 on all keyed questions, except fts with MAX_PER_DOC 4 (4/5, 9/10; not eligible). Forbidden
   hits 0 at every point; Q7 has hits from MS, BAC GWIM (Merrill) and RJF in each chosen run; Q26 has
   8 hits, none outside the window, newest first, in each chosen run.
3. **At picked constants the three modes are close** on this bank: PASS 27 / 28 / 28, tier-1 passages
   0.474 / 0.405 / 0.402, documents 0.782 / 0.715 / 0.738 (fts / hybrid-norerank / hybrid). fts keeps the
   highest recall; the hybrid modes fix Q17 (AI in advice delivery, 4/7 sources) and lift Q22 and Q24
   passages, and lose passages on Q4, Q28, Q29. With 30 questions, one passage is about 0.02.
4. **The reranker adds little on this text.** Same candidates and constants, only the order differs:
   at every one of the 12 grid points the cross-encoder's tier-1 passage recall is lower than RRF order
   (0.402 vs 0.405 at the hybrid pick; 0.317 vs 0.389 at MAX_PER_DOC 2), PASS equal or one lower, doc
   recall up to +0.023 higher. At the hybrid pick, 28 of 30 questions find the same answer passages in
   both orders (Q11 +1 with rerank, Q22 -1).
5. **Q29: the cross-encoder ranks the wrong passage first.** MiniLM gives the guarantee note
   `MS-10K-2025#702` ("likelihood of any payment by the Firm ... is remote") 0.95 and the firm overview
   `#417` 0.90, while the answer passages `#153` (formulaic payouts) and `#170` enter the 50-pool and score
   0.0000 and 0.0001. At the default MAX_PER_DOC 3 this fails Q29 (coverage 0). At the picked MAX_PER_DOC 4
   Q29 passes, but only because the fourth MS 10-K place goes to `#163`, a Wealth Management income table
   (sigmoid 0.25) that satisfies the coverage pattern; `#153` and `#170` are still not returned. RRF order
   (`hybrid-norerank`) returns `#128`, `#170` and also `#702` (the vector leg ranks it high too). `#702` is
   not on Q29's must-not list, so no run counts it; no answer-key change, no Q29 rule.
6. **Latency (CPU, warm-up excluded).** Median / p90 per question: fts 0.34 / 0.51 s; hybrid-norerank
   0.31 / 0.53 s; hybrid 5.1 / 8.2 s at the pick (8.2 / 9.5 s at FLOOR 0). The RRF floor shortens the
   rerank because fewer candidates are scored. Warm-up (model load): 0.5 s, 1.6 s, 4.5 s.
7. **Duplicates.** Word 5-gram pairs > 0.9: 0 everywhere (max 0.58-0.59). Trigram pairs > 0.9: fts pick
   1 (Q19: `EDJ-10Q-2025Q2#17` / `EDJ-10Q-2025Q3#19`, the same partnership-interest table in two 10-Qs,
   0.911; also at the fts default); both hybrid picks 0 (max 0.893), so `DUP_JACCARD` stays 0.6 in both
   hybrid modes by the rule. At the #125 default `hybrid` had 2 such pairs (Q5 MD&A intro vs 10-K
   overview 0.938; Q14 two RJF 10-Q tables 0.916). fts's value is reported, not changed.

## PASS / FAIL per question (chosen constants)

Status, passages found / expected (answer key), expected-source coverage.

| Q | Expected | `fts` status (passages, coverage) | `hybrid-norerank` status (passages, coverage) | `hybrid` status (passages, coverage) | Change vs fts |
|---|---|---|---|---|---|
| Q1 | answer | PASS (2/8, 3/3) | PASS (2/8, 3/3) | PASS (2/8, 3/3) | - |
| Q2 | answer | PASS (-, 3/3) | PASS (-, 2/3) | PASS (-, 2/3) | - |
| Q3 | answer | PASS (-, 3/3) | PASS (-, 3/3) | PASS (-, 3/3) | - |
| Q4 | answer | PASS (5/7, 2/2) | PASS (4/7, 2/2) | PASS (4/7, 2/2) | - |
| Q5 | answer | PASS (-, 2/2) | PASS (-, 2/2) | PASS (-, 2/2) | - |
| Q6 | answer | PASS (-, 2/3) | PASS (-, 2/3) | PASS (-, 2/3) | - |
| Q7 | answer | PASS (-, 6/6) | PASS (-, 6/6) | PASS (-, 6/6) | - |
| Q8 | answer | PASS (-, 3/4) | PASS (-, 3/4) | PASS (-, 3/4) | - |
| Q9 | answer | PASS (-, 4/5) | PASS (-, 5/5) | PASS (-, 5/5) | - |
| Q10 | answer | PASS (-, 5/5) | PASS (-, 5/5) | PASS (-, 5/5) | - |
| Q11 | answer | PASS (3/10, 7/8) | PASS (2/10, 6/8) | PASS (3/10, 7/8) | - |
| Q12 | answer_with_boundary | PASS (-, 3/3) | PASS (-, 3/3) | PASS (-, 3/3) | - |
| Q13 | answer | PASS (-, 2/2) | PASS (-, 2/2) | PASS (-, 2/2) | - |
| Q14 | answer | PASS (-, 3/3) | PASS (-, 2/3) | PASS (-, 2/3) | - |
| Q15 | answer | FAIL (-, 1/5) | FAIL (-, 1/5) | FAIL (-, 1/5) | - |
| Q16 | answer | PASS (-, 3/3) | PASS (-, 3/3) | PASS (-, 3/3) | - |
| Q17 | answer | FAIL (-, 3/7) | PASS (-, 4/7) | PASS (-, 4/7) | hybrid-norerank: FAIL -> PASS; hybrid: FAIL -> PASS |
| Q18 | answer | PASS (-, 1/1) | PASS (-, 1/1) | PASS (-, 1/1) | - |
| Q19 | answer_with_boundary | FAIL (-, 1/4) | FAIL (-, 1/4) | FAIL (-, 1/4) | - |
| Q20 | answer | PASS (-, 1/1) | PASS (-, 1/1) | PASS (-, 1/1) | - |
| Q21 | answer | PASS (-, 5/6) | PASS (-, 5/6) | PASS (-, 5/6) | - |
| Q22 | answer | PASS (0/8, 4/6) | PASS (3/8, 5/6) | PASS (2/8, 4/6) | - |
| Q23 | answer | PASS (-, 5/7) | PASS (-, 4/7) | PASS (-, 5/7) | - |
| Q24 | gap_with_adjacent | PASS (0/4, 3/5) | PASS (2/4, 4/5) | PASS (2/4, 4/5) | - |
| Q25 | gap_with_adjacent | PASS (0/4, 5/5) | PASS (0/4, 5/5) | PASS (0/4, 5/5) | - |
| Q26 | answer | PASS (1/1, 1/1) | PASS (1/1, 1/1) | PASS (1/1, 1/1) | - |
| Q27 | answer | PASS (-, 2/2) | PASS (-, 2/2) | PASS (-, 2/2) | - |
| Q28 | gap_with_adjacent | PASS (2/4, 2/3) | PASS (1/4, 2/3) | PASS (1/4, 2/3) | - |
| Q29 | gap_with_adjacent | PASS (2/2, 1/1) | PASS (1/2, 1/1) | PASS (1/2, 1/1) | - |
| Q30 | gap_with_adjacent | PASS (1/2, 1/1) | PASS (1/2, 1/1) | PASS (1/2, 1/1) | - |

## Refusal questions

| Q | `fts` | `hybrid-norerank` | `hybrid` |
|---|---|---|---|
| Q24 | ok | ok | ok |
| Q25 | ok | ok | ok |
| Q28 | ok | ok | ok |
| Q29 | ok | ok | ok |
| Q30 | ok | ok | ok |

## Is the cross-encoder reliable on this financial text? (input for #127)

Both hybrid modes at every grid point (same candidates and constants; only the final order differs: RRF score vs cross-encoder):

| FLOOR | MAX_PER_DOC | PASS (RRF / rerank) | Tier-1 docs (RRF / rerank) | Tier-1 passages (RRF / rerank) | Median search s (RRF / rerank) |
|---|---|---|---|---|---|
| 0.0 | 2 | 27 / 27 | 0.73 / 0.728 | 0.389 / 0.317 | 0.373 / 8.046 |
| 0.0 | 3 | 28 / 27 | 0.718 / 0.728 | 0.389 / 0.373 | 0.363 / 8.186 |
| 0.0 | 4 | 28 / 28 | 0.706 / 0.728 | 0.389 / 0.373 | 0.335 / 8.424 |
| 0.2 | 2 | 27 / 27 | 0.718 / 0.716 | 0.389 / 0.317 | 0.371 / 8.229 |
| 0.2 | 3 | 28 / 27 | 0.718 / 0.716 | 0.389 / 0.373 | 0.351 / 8.308 |
| 0.2 | 4 | 28 / 28 | 0.706 / 0.716 | 0.389 / 0.373 | 0.372 / 8.174 |
| 0.3 | 2 | 27 / 27 | 0.718 / 0.716 | 0.389 / 0.317 | 0.365 / 6.692 |
| 0.3 | 3 | 28 / 27 | 0.718 / 0.716 | 0.389 / 0.373 | 0.36 / 6.617 |
| 0.3 | 4 | 28 / 28 | 0.718 / 0.716 | 0.389 / 0.373 | 0.374 / 6.781 |
| 0.4 | 2 | 26 / 26 | 0.715 / 0.738 | 0.405 / 0.333 | 0.355 / 5.796 |
| 0.4 | 3 | 28 / 27 | 0.715 / 0.738 | 0.405 / 0.402 | 0.348 / 5.127 |
| 0.4 | 4 | 28 / 28 | 0.715 / 0.738 | 0.405 / 0.402 | 0.342 / 5.075 |

Per question at `hybrid`'s picked constants (FLOOR 0.4, MAX_PER_DOC 4, DUP_JACCARD 0.6), `hybrid-norerank` run with the same constants: the cross-encoder finds more answer passages on 1 questions, fewer on 1, the same on 28. Questions where status or passages differ:

| Q | `hybrid-norerank` status, passages | `hybrid` status, passages | Shared hits |
|---|---|---|---|
| Q11 | PASS, 2/10 | PASS, 3/10 | 10 of 20 |
| Q22 | PASS, 3/8 | PASS, 2/8 | 12 of 20 |

### Q29 (what Morgan Stanley pays its advisors)

MS 10-K chunks each mode returns for Q29 (score = the mode's `Hit.rank`: ts_rank, RRF, or cross-encoder sigmoid):

- `fts`: PASS, coverage 1.0; MS 10-K: `MS-10K-2025#170` (11.3255), `MS-10K-2025#128` (11.3155), `MS-10K-2025#153` (8.5173); `MS-10K-2025#702` not returned
- `hybrid-norerank`: PASS, coverage 1.0; MS 10-K: `MS-10K-2025#128` (0.0243), `MS-10K-2025#702` (0.022), `MS-10K-2025#170` (0.0152); `MS-10K-2025#702` returned
- `hybrid`: PASS, coverage 1.0; MS 10-K: `MS-10K-2025#702` (0.9497), `MS-10K-2025#417` (0.9001), `MS-10K-2025#128` (0.727), `MS-10K-2025#163` (0.2473); `MS-10K-2025#702` returned

Cross-encoder scores in the #125 diagnosis (`p125r-diag`, committed as `inputs/p125r-diag.json`; `hybrid`, 50-candidate pool, MiniLM-L-12, sigmoid):

- top 5 of the pool: `MS-TR-2025Q3#2` 0.988, `MS-10K-2025#702` 0.95, `MS-PR-2026-01-15-01#13` 0.944, `MS-TR-2024Q4#10` 0.914, `MS-10K-2025#417` 0.9
- `MS-10K-2025#153` (must_return): keyword rank 12, vector rank None, sigmoid 0.0, pool rank 47 of 50, returned False
- `MS-10K-2025#128` (must_return): keyword rank 7, vector rank 47, sigmoid 0.727, pool rank 15 of 50, returned True
- `MS-10K-2025#170` (must_return): keyword rank 6, vector rank None, sigmoid 0.0001, pool rank 42 of 50, returned False
- `MS-10K-2025#693` (must_not): keyword rank 14, vector rank None, sigmoid 0.0001, pool rank 44 of 50, returned False
- `MS-10K-2025#699` (must_not): keyword rank 15, vector rank None, sigmoid 0.0001, pool rank 41 of 50, returned False

`MS-10K-2025#702` (a guarantee note: "likelihood of any payment by the Firm under these arrangements is remote") is not on Q29's `must_not_return` list in `evals/expected_chunks.yaml`, so it counts as neither forbidden nor misleading: extending the key (C1's call) would change only those counts, never PASS, which depends on coverage. No answer-key change and no Q29-specific rule here.

## Duplicate measure

Every pair of final hits per question: (a) character trigram similarity computed like pg_trgm's `similarity()` (Python re-implementation: pg_trgm is not installed in `cee-db`; lower case, words = runs of letters and digits, each padded with two spaces in front and one behind, shared trigrams / all distinct trigrams); (b) word 5-gram Jaccard, the measure `select()` dedupes with (DUP_JACCARD). Spec: no two hits > 0.9 similar. Counts are in the tables above.

## Grid (appendix)

### `fts`

| FLOOR | MAX_PER_DOC | PASS | Tier-1 docs | Passages | Refusal gap | Refusal all | Forbidden | Dup > 0.9 (trigram / 5-gram) | Median s |
|---|---|---|---|---|---|---|---|---|---|
| 0.2 | 2 | 27 | 0.794 | 0.432 | 5/5 | 10/10 | 0 | 0 / 0 | 0.385 |
| 0.2 | 3 | 27 | 0.782 | 0.474 | 5/5 | 10/10 | 0 | 1 / 0 | 0.336 |
| 0.2 | 4 | 26 | 0.763 | 0.474 | 4/5 | 9/10 | 0 | 1 / 0 | 0.384 |
| 0.3 | 2 | 28 | 0.809 | 0.361 | 5/5 | 10/10 | 0 | 0 / 0 | 0.348 |
| 0.3 | 3 | 28 | 0.796 | 0.402 | 5/5 | 10/10 | 0 | 1 / 0 | 0.342 |
| 0.3 | 4 | 27 | 0.796 | 0.402 | 4/5 | 9/10 | 0 | 1 / 0 | 0.353 |
| 0.4 | 2 | 28 | 0.809 | 0.361 | 5/5 | 10/10 | 0 | 0 / 0 | 0.333 |
| 0.4 | 3 | 28 | 0.796 | 0.402 | 5/5 | 10/10 | 0 | 1 / 0 | 0.37 |
| 0.4 | 4 | 27 | 0.796 | 0.402 | 4/5 | 9/10 | 0 | 1 / 0 | 0.372 |

Pick: FLOOR 0.2, MAX_PER_DOC 3. eligible 6 of 9; best tier-1 passage recall 0.474; beats the runner-up f0.2-m2 on passage recall.

- not eligible f0.2-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts
- not eligible f0.3-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts
- not eligible f0.4-m4: refusal gap 4/5 < fts; refusal all 9/10 < fts

### `hybrid-norerank`

| FLOOR | MAX_PER_DOC | PASS | Tier-1 docs | Passages | Refusal gap | Refusal all | Forbidden | Dup > 0.9 (trigram / 5-gram) | Median s |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 2 | 27 | 0.73 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.373 |
| 0.0 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.363 |
| 0.0 | 4 | 28 | 0.706 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.335 |
| 0.2 | 2 | 27 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.371 |
| 0.2 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.351 |
| 0.2 | 4 | 28 | 0.706 | 0.389 | 5/5 | 10/10 | 0 | 0 / 0 | 0.372 |
| 0.3 | 2 | 27 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.365 |
| 0.3 | 3 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.36 |
| 0.3 | 4 | 28 | 0.718 | 0.389 | 5/5 | 10/10 | 0 | 1 / 0 | 0.374 |
| 0.4 | 2 | 26 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.355 |
| 0.4 | 3 | 28 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.348 |
| 0.4 | 4 | 28 | 0.715 | 0.405 | 5/5 | 10/10 | 0 | 0 / 0 | 0.342 |

Pick: FLOOR 0.4, MAX_PER_DOC 3. eligible 12 of 12; best tier-1 passage recall 0.405; beats the runner-up f0.4-m4 on smaller MAX_PER_DOC.


### `hybrid`

| FLOOR | MAX_PER_DOC | PASS | Tier-1 docs | Passages | Refusal gap | Refusal all | Forbidden | Dup > 0.9 (trigram / 5-gram) | Median s |
|---|---|---|---|---|---|---|---|---|---|
| 0.0 | 2 | 27 | 0.728 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 8.046 |
| 0.0 | 3 | 27 | 0.728 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.186 |
| 0.0 | 4 | 28 | 0.728 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.424 |
| 0.2 | 2 | 27 | 0.716 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 8.229 |
| 0.2 | 3 | 27 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.308 |
| 0.2 | 4 | 28 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 2 / 0 | 8.174 |
| 0.3 | 2 | 27 | 0.716 | 0.317 | 5/5 | 10/10 | 0 | 4 / 0 | 6.692 |
| 0.3 | 3 | 27 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 4 / 0 | 6.617 |
| 0.3 | 4 | 28 | 0.716 | 0.373 | 5/5 | 10/10 | 0 | 4 / 0 | 6.781 |
| 0.4 | 2 | 26 | 0.738 | 0.333 | 5/5 | 10/10 | 0 | 0 / 0 | 5.796 |
| 0.4 | 3 | 27 | 0.738 | 0.402 | 5/5 | 10/10 | 0 | 0 / 0 | 5.127 |
| 0.4 | 4 | 28 | 0.738 | 0.402 | 5/5 | 10/10 | 0 | 0 / 0 | 5.075 |

Pick: FLOOR 0.4, MAX_PER_DOC 4. eligible 12 of 12; best tier-1 passage recall 0.402; beats the runner-up f0.4-m3 on PASS.


## Search time per question, chosen constants (appendix)

Seconds per `search()`; the first, untimed warm-up search (model loading) is excluded. fts from its chosen grid point; the hybrid modes from their confirmation runs.

| Q | `fts` s | `hybrid-norerank` s | `hybrid` s |
|---|---|---|---|
| Q1 | 0.292 | 0.304 | 3.048 |
| Q2 | 0.151 | 0.192 | 2.373 |
| Q3 | 0.302 | 0.236 | 4.791 |
| Q4 | 0.189 | 0.207 | 3.645 |
| Q5 | 0.253 | 0.302 | 3.647 |
| Q6 | 0.126 | 0.187 | 4.072 |
| Q7 | 0.32 | 0.304 | 4.873 |
| Q8 | 0.279 | 0.203 | 5.013 |
| Q9 | 0.352 | 0.303 | 8.613 |
| Q10 | 0.452 | 0.351 | 7.457 |
| Q11 | 0.778 | 0.588 | 8.199 |
| Q12 | 0.445 | 0.526 | 5.039 |
| Q13 | 0.439 | 0.31 | 4.437 |
| Q14 | 0.236 | 0.186 | 3.57 |
| Q15 | 0.444 | 0.364 | 4.476 |
| Q16 | 0.399 | 0.485 | 5.611 |
| Q17 | 0.497 | 0.391 | 4.139 |
| Q18 | 0.503 | 0.451 | 5.061 |
| Q19 | 0.293 | 0.451 | 6.482 |
| Q20 | 0.38 | 0.472 | 8.162 |
| Q21 | 0.436 | 0.471 | 5.154 |
| Q22 | 0.756 | 0.66 | 8.239 |
| Q23 | 0.506 | 0.494 | 7.227 |
| Q24 | 0.541 | 0.581 | 7.228 |
| Q25 | 0.375 | 0.439 | 6.259 |
| Q26 | 0.302 | 0.238 | 6.483 |
| Q27 | 0.222 | 0.258 | 8.605 |
| Q28 | 0.268 | 0.192 | 6.546 |
| Q29 | 0.18 | 0.178 | 4.675 |
| Q30 | 0.158 | 0.228 | 6.426 |

## How this report was built

From the repo root, from committed inputs only (no database, no model):

```
python scripts/eval_compare.py --chosen fts=evals/hybrid-eval/corpus-2026-10-29/fts/report.json --chosen hybrid-norerank=evals/hybrid-eval/corpus-2026-10-29/hybrid-norerank/report.json --chosen hybrid=evals/hybrid-eval/corpus-2026-10-29/hybrid/report.json --default fts=evals/hybrid-eval/corpus-2026-10-29/inputs/fts-default-f0.3-m3.json --default hybrid-norerank=evals/hybrid-eval/corpus-2026-10-29/inputs/hybrid-norerank-default-f0.0-m3.json --default hybrid=evals/hybrid-eval/corpus-2026-10-29/inputs/hybrid-default-f0.0-m3.json --grid fts=evals/hybrid-eval/corpus-2026-10-29/fts/grid.json --grid hybrid-norerank=evals/hybrid-eval/corpus-2026-10-29/hybrid-norerank/grid.json --grid hybrid=evals/hybrid-eval/corpus-2026-10-29/hybrid/grid.json --same-constants evals/hybrid-eval/corpus-2026-10-29/inputs/hybrid-norerank-f0.4-m4.json --diag evals/hybrid-eval/corpus-2026-10-29/inputs/p125r-diag.json --notes evals/hybrid-eval/corpus-2026-10-29/inputs/findings.md --out evals/hybrid-eval/corpus-2026-10-29
```
