# fts vs hybrid-norerank on #217's planner plans (#240)

Snapshot `corpus-2026-11-19`, as of 2026-11-17, k by question (`fts.budget`), mock provider, 0 real calls. CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel, 12 logical CPUs, Windows. Commits: fts `101e332`, hybrid-norerank `101e332`.

Modes: `fts` = keyword search (equals `main`). `hybrid-norerank` = keyword + vector legs fused by RRF per quota firm, with every rule of `main`'s `fts.search()` (plans/0211-hybrid-retest.md R1-R11), final order by RRF score. `hybrid` = the same candidates ordered by the local cross-encoder; a reference only, it does not decide.

0.03 of tier-1 passage recall is about 1-2 passages on this bank; tuned and scored on the same 30 questions with no held-out set (ADR-010), so a difference this size is weak evidence.

## Summary

| Mode | PASS / FAIL | Tier-1 docs | Tier-1 passages | Tier-1 recall@pool | Tier-1 recall@final | recall@pool / @final (all rows) | Mean pool size | Refusal Q24, Q25, Q28-Q30 | Refusal all keyed | Forbidden | Passages | Search s median / p90 / max (warm-up) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fts` | 27 / 3 | 0.931 | 0.869 | 0.972 | 0.869 | 0.977 / 0.763 | 859.8 | 4/5 | 20/22 | 0 | 4124 | 2.731 / 4.056 / 4.589 (0.905) |
| `hybrid-norerank` | 27 / 3 | 0.923 | 0.875 | 0.957 | 0.875 | 0.965 / 0.851 | 610.4 | 4/5 | 20/22 | 0 | 3904 | 3.687 / 6.211 / 10.201 (2.207) |

Recall@pool: expected passages with a chunk in a candidate pool before any floor or `select()`; recall@final: in the retrieved set (#210). Both modes pool the best 30 per (firm, document type) per part; fts ranks by ts_rank over every match, hybrid by RRF over its two legs, whose keyword and vector legs each reach at most LEG_K = 100 chunks per quota firm across all document types, so a hybrid group can hold fewer than 30. Tier 1: 17 questions with expected passages; all rows: 21 questions.

## Passages Gate 4 named as missed (stage per mode)

| Q | Passage | `fts` | `hybrid-norerank` |
|---|---|---|---|
| Q7 | `MS-10K-2025#153` | in pool, lost in select | in pool, lost in select |
| Q15 | `SCHW-10K-2025#27` | in pool, lost in select | retrieved |
| Q17 | `BAC-TR-2026Q2#21` | retrieved | retrieved |
| Q19 | `EDJ-10K-2025#88` | retrieved | retrieved |
| Q20 | `FIDELITY-III-2025#0` | in pool, lost in select | retrieved |
| Q20 | `UBS-NEXTGEN-2026#119` / `UBS-NEXTGEN-2026#13` | in pool, lost in select | not in pool |
| Q25 | `MS-10K-2025#153` | in pool, lost in select | retrieved |
| Q25 | `RJF-PR-web-affiliation-options#1` | retrieved | retrieved |

## Per question

Cells: status / recall@pool / recall@final / passages found.

| Q | `fts` | `hybrid-norerank` |
|---|---|---|
| Q1 | PASS / 1.0 / 1.0 / 8/8 | PASS / 1.0 / 1.0 / 8/8 |
| Q2 | PASS / 1.0 / 1.0 / 9/9 | PASS / 1.0 / 1.0 / 9/9 |
| Q3 | PASS / 1.0 / 1.0 / 6/6 | PASS / 1.0 / 1.0 / 6/6 |
| Q4 | PASS / 0.857 / 0.857 / 6/7 | PASS / 0.857 / 0.857 / 6/7 |
| Q5 | PASS / 1.0 / 0.833 / 5/6 | PASS / 1.0 / 0.833 / 5/6 |
| Q6 | PASS / 1.0 / 1.0 / 6/6 | PASS / 1.0 / 1.0 / 6/6 |
| Q7 | PASS / 1.0 / 0.0 / 0/1 | PASS / 1.0 / 0.0 / 0/1 |
| Q8 | PASS / None / None / - | PASS / None / None / - |
| Q9 | PASS / None / None / - | PASS / None / None / - |
| Q10 | PASS / None / None / - | PASS / None / None / - |
| Q11 | PASS / 1.0 / 0.8 / 8/10 | PASS / 1.0 / 0.8 / 8/10 |
| Q12 | PASS / None / None / - | PASS / None / None / - |
| Q13 | PASS / 1.0 / 1.0 / 6/6 | PASS / 1.0 / 1.0 / 6/6 |
| Q14 | PASS / None / None / - | PASS / None / None / - |
| **Q15** | PASS / 1.0 / 0.0 / 0/1 | PASS / 1.0 / 1.0 / 1/1 |
| Q16 | PASS / None / None / - | PASS / None / None / - |
| **Q17** | PASS / 1.0 / 0.8 / 8/10 | PASS / 1.0 / 0.9 / 9/10 |
| Q18 | PASS / None / None / - | PASS / None / None / - |
| Q19 | FAIL / 1.0 / 1.0 / 1/1 | FAIL / 1.0 / 1.0 / 1/1 |
| **Q20** | PASS / 0.889 / 0.556 / 5/9 | PASS / 0.778 / 0.556 / 5/9 |
| Q21 | PASS / None / None / - | PASS / None / None / - |
| Q22 | FAIL / 1.0 / 1.0 / 8/8 | FAIL / 1.0 / 1.0 / 8/8 |
| **Q23** | PASS / 1.0 / 0.85 / 17/20 | PASS / 0.85 / 0.6 / 12/20 |
| **Q24** | FAIL / 1.0 / 0.25 / 1/4 | FAIL / 1.0 / 1.0 / 4/4 |
| Q25 | PASS / 1.0 / 0.8 / 4/5 | PASS / 1.0 / 0.8 / 4/5 |
| Q26 | PASS / None / None / - | PASS / None / None / - |
| Q27 | PASS / 0.778 / 0.778 / 7/9 | PASS / 0.778 / 0.778 / 7/9 |
| **Q28** | PASS / 1.0 / 1.0 / 4/4 | PASS / 1.0 / 0.75 / 3/4 |
| **Q29** | PASS / 1.0 / 0.5 / 1/2 | PASS / 1.0 / 1.0 / 2/2 |
| Q30 | PASS / 1.0 / 1.0 / 2/2 | PASS / 1.0 / 1.0 / 2/2 |

Bold: `fts` and `hybrid-norerank` differ in status, recall@pool, recall@final or passage recall (7 questions: Q15, Q17, Q20, Q23, Q24, Q28, Q29).

Rebuilt with: `python scripts/eval_compare.py --run fts=.eval-runs/0240-m3-fts-plans/report.json --run hybrid-norerank=.eval-runs/0240-m4-hybrid-norerank-plans/report.json --no-decision --title # fts vs hybrid-norerank on #217's planner plans (#240) --pool-note Both modes pool the best 30 per (firm, document type) per part; fts ranks by ts_rank over every match, hybrid by RRF over its two legs, whose keyword and vector legs each reach at most LEG_K = 100 chunks per quota firm across all document types, so a hybrid group can hold fewer than 30. --out evals/hybrid-eval/corpus-2026-11-19/mock/planner-plans`
