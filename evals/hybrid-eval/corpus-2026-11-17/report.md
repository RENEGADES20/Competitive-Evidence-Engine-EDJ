# fts vs hybrid-norerank on corpus-2026-11-17 (#211)

Snapshot `corpus-2026-11-17`, as of 2026-11-17, k by question (`fts.budget`), mock provider, 0 real calls. CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel, 12 logical CPUs, Windows. Commits: fts `7f12f60`, hybrid-norerank `7f12f60`, hybrid `7f12f60`.

Modes: `fts` = keyword search (equals `main`). `hybrid-norerank` = keyword + vector legs fused by RRF per quota firm, with every rule of `main`'s `fts.search()` (plans/0211-hybrid-retest.md R1-R11), final order by RRF score. `hybrid` = the same candidates ordered by the local cross-encoder; a reference only, it does not decide.

## Decision

**Decision: #212 is closed as not planned** (conditions A, C not met).

Rule (fixed before any run): hybrid-norerank tier-1 passage recall >= fts + 0.03 (3 decimals), refusal 5/5 on Q24, Q25, Q28, Q29, Q30, refusal correct on every keyed question (the issue's "10/10 keyed": every keyed question on today's key) and 0 forbidden hits -> #212 runs; otherwise #212 is closed as not planned. hybrid (with the reranker) is a reference only; recall@pool is reported, not decided on.

- A: NOT met (tier-1 passage recall 0.484 vs fts 0.597 + 0.03 = 0.627)
- B: met (refusal on Q24, Q25, Q28-Q30 5/5)
- C: NOT met (refusal on every keyed question 21/22)
- D: met (forbidden hits 0)

0.03 of tier-1 passage recall is about 1-2 passages on this bank; tuned and scored on the same 30 questions with no held-out set (ADR-010), so a difference this size is weak evidence.

## Summary

| Mode | PASS / FAIL | Tier-1 docs | Tier-1 passages | Tier-1 recall@pool | Tier-1 recall@final | recall@pool / @final (all rows) | Mean pool size | Refusal Q24, Q25, Q28-Q30 | Refusal all keyed | Forbidden | Passages | Search s median / p90 / max (warm-up) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fts` | 29 / 1 | 0.785 | 0.597 | 0.803 | 0.597 | 0.686 / 0.484 | 244.6 | 5/5 | 22/22 | 0 | 675 | 0.469 / 0.871 / 1.129 (0.701) |
| `hybrid-norerank` | 28 / 2 | 0.619 | 0.484 | 0.623 | 0.484 | 0.528 / 0.403 | 64.5 | 5/5 | 21/22 | 0 | 685 | 0.573 / 1.281 / 1.605 (2.018) |
| `hybrid` | 27 / 3 | 0.627 | 0.479 | 0.623 | 0.479 | 0.528 / 0.411 | 64.5 | 4/5 | 20/22 | 0 | 685 | 9.026 / 16.019 / 21.798 (6.68) |

Recall@pool: expected passages with a chunk in a candidate pool before any floor or `select()`; recall@final: in the retrieved set (#210). recall@pool is not like-for-like: fts pools 15 per (firm, document type) with no total cap, hybrid pools RERANK_N candidates per part (50 x k / 20). Tier 1: 17 questions with expected passages; all rows: 21 questions.

## Passages Gate 4 named as missed (stage per mode)

| Q | Passage | `fts` | `hybrid-norerank` | `hybrid` |
|---|---|---|---|---|
| Q7 | `MS-10K-2025#153` | not in pool | not in pool | not in pool |
| Q15 | `SCHW-10K-2025#27` | not in pool | not in pool | not in pool |
| Q17 | `BAC-TR-2026Q2#21` | in pool, lost in select | not in pool | not in pool |
| Q19 | `EDJ-10K-2025#88` | not in pool | not in pool | not in pool |
| Q20 | `FIDELITY-III-2025#0` | not in pool | not in pool | not in pool |
| Q20 | `UBS-NEXTGEN-2026#119` / `UBS-NEXTGEN-2026#13` | not in pool | not in pool | not in pool |
| Q25 | `MS-10K-2025#153` | not in pool | in pool, lost in select | in pool, lost in select |
| Q25 | `RJF-PR-web-affiliation-options#1` | not in pool | not in pool | not in pool |

## Per question

Cells: status / recall@pool / recall@final / passages found.

| Q | `fts` | `hybrid-norerank` | `hybrid` |
|---|---|---|---|
| **Q1** | PASS / 0.625 / 0.5 / 4/8 | PASS / 0.375 / 0.125 / 1/8 | PASS / 0.375 / 0.125 / 1/8 |
| **Q2** | PASS / 0.889 / 0.667 / 6/9 | PASS / 0.778 / 0.667 / 6/9 | PASS / 0.778 / 0.667 / 6/9 |
| **Q3** | PASS / 1.0 / 0.667 / 4/6 | PASS / 0.667 / 0.667 / 4/6 | PASS / 0.667 / 0.667 / 4/6 |
| **Q4** | PASS / 0.857 / 0.714 / 5/7 | PASS / 0.714 / 0.571 / 4/7 | PASS / 0.714 / 0.571 / 4/7 |
| **Q5** | PASS / 0.833 / 0.833 / 5/6 | PASS / 0.5 / 0.5 / 3/6 | PASS / 0.5 / 0.5 / 3/6 |
| **Q6** | PASS / 1.0 / 1.0 / 6/6 | PASS / 0.833 / 0.833 / 5/6 | PASS / 0.833 / 0.833 / 5/6 |
| Q7 | PASS / 0.0 / 0.0 / 0/1 | PASS / 0.0 / 0.0 / 0/1 | PASS / 0.0 / 0.0 / 0/1 |
| Q8 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| Q9 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| Q10 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| **Q11** | PASS / 0.6 / 0.2 / 2/10 | PASS / 0.4 / 0.3 / 3/10 | PASS / 0.4 / 0.3 / 3/10 |
| Q12 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| **Q13** | PASS / 1.0 / 1.0 / 6/6 | PASS / 0.833 / 0.667 / 4/6 | PASS / 0.833 / 0.833 / 5/6 |
| Q14 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| Q15 | PASS / 0.0 / 0.0 / 0/1 | PASS / 0.0 / 0.0 / 0/1 | PASS / 0.0 / 0.0 / 0/1 |
| Q16 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| **Q17** | PASS / 1.0 / 0.6 / 6/10 | PASS / 0.6 / 0.5 / 5/10 | PASS / 0.6 / 0.5 / 5/10 |
| Q18 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| Q19 | FAIL / 0.0 / 0.0 / 0/1 | FAIL / 0.0 / 0.0 / 0/1 | FAIL / 0.0 / 0.0 / 0/1 |
| **Q20** | PASS / 0.444 / 0.333 / 3/9 | PASS / 0.111 / 0.111 / 1/9 | PASS / 0.111 / 0.111 / 1/9 |
| Q21 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| **Q22** | PASS / 0.875 / 0.375 / 3/8 | FAIL / 0.5 / 0.375 / 3/8 | FAIL / 0.5 / 0.375 / 3/8 |
| **Q23** | PASS / 1.0 / 0.35 / 7/20 | PASS / 0.65 / 0.4 / 8/20 | PASS / 0.65 / 0.4 / 8/20 |
| **Q24** | PASS / 0.75 / 0.0 / 0/4 | PASS / 0.5 / 0.25 / 1/4 | PASS / 0.5 / 0.5 / 2/4 |
| **Q25** | PASS / 0.0 / 0.0 / 0/5 | PASS / 0.6 / 0.2 / 1/5 | FAIL / 0.6 / 0.2 / 1/5 |
| Q26 | PASS / None / None / - | PASS / None / None / - | PASS / None / None / - |
| **Q27** | PASS / 0.778 / 0.667 / 6/9 | PASS / 0.778 / 0.556 / 5/9 | PASS / 0.778 / 0.556 / 5/9 |
| Q28 | PASS / 0.75 / 0.75 / 3/4 | PASS / 0.75 / 0.75 / 3/4 | PASS / 0.75 / 0.5 / 2/4 |
| **Q29** | PASS / 1.0 / 1.0 / 2/2 | PASS / 1.0 / 0.5 / 1/2 | PASS / 1.0 / 0.5 / 1/2 |
| **Q30** | PASS / 1.0 / 0.5 / 1/2 | PASS / 0.5 / 0.5 / 1/2 | PASS / 0.5 / 0.5 / 1/2 |

Bold: `fts` and `hybrid-norerank` differ in status, recall@pool, recall@final or passage recall (17 questions: Q1, Q2, Q3, Q4, Q5, Q6, Q11, Q13, Q17, Q20, Q22, Q23, Q24, Q25, Q27, Q29, Q30).

Rebuilt with: `python scripts/eval_compare.py --run fts=evals/hybrid-eval/corpus-2026-11-17/inputs/fts-report.json --run hybrid-norerank=evals/hybrid-eval/corpus-2026-11-17/inputs/hybrid-norerank-report.json --run hybrid=evals/hybrid-eval/corpus-2026-11-17/inputs/hybrid-report.json --out evals/hybrid-eval/corpus-2026-11-17`
