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
