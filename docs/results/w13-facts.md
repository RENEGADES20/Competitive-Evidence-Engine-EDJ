# W13 facts table (#285): metric figures extracted once, served by SQL

Plan `plans/0285-facts.md`; decision ADR-022 (`docs/DECISIONS.md`). Baseline: #272 test B fts
(`docs/results/w12-latency.md`): adjudicated 24/30, $0.519 per question off-peak, critical-path p50 184 s, 454 map calls.
Results are filled in after the run; this first section is the 0-call estimate the plan rests on.

## Estimate from the #272 records (0 calls)

Source: the 485 C1 map and re-map records of #272 test B in `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a`
(`deepseek-v4-pro`, `ds-strict-2-map-low-c128000-s1`), the 30 reused plans, and the extraction candidate chunks
(`w13-facts/candidates.sql`, 719 chunks in 76 documents: 10-K, 10-Q, supplement, press, monthly, deck of EDJ, MS, SCHW,
BAC, MER, RJF that mention a target metric next to a number). Script `w13-facts/coverage272.py`, output
`w13-facts/coverage272.txt`.

- 422 map cells; **95 metric cells** (the aspect names a target metric, by the registry tag or its text, and the map
  gave a figure). Most are narrative or definitional (Q11 "how the firm defines", Q21 "how firms prepare"), proxies
  (Q21 a8, Q24 a3, Q28) or splits (Q14 "across the affiliation-choice model"); the serving rule leaves them to the map.
- **33 servable cells** (serving rule of ADR-022 on the reused plans). **28 are estimated covered**: the map's figure
  cites a candidate chunk. The other 5 took their figure from trade press, transcripts or Form ADV (SCHW headcount,
  Q26 RJF NNA in the window, Q27 Merrill since January); at run time they are covered only if the lookup finds rows.
- Coverage estimate: 28/95 metric cells (29%), 28/33 servable (85%). Calls saved: 29 of 485 map + re-map calls (6%).
  Map $ saved: $0.85 of $13.97 off-peak, so about $0.519 -> $0.49 per question.
- Critical path, if only the covered map calls disappear: Q4 197 -> 156 s, Q22 208 -> 150 s, Q23 144 -> 71 s (less if
  SCHW stays a model cell); p50 184 -> about 175 s. The reduce (p50 126 s) stays the long pole.
- Target metrics: advisor_headcount and net_new_assets (registered) and client_assets (asked as a figure in Q14, Q21,
  Q24). Not targeted: revenue lines (Q15 only), attrition (Q28 only), compensation (Q25, Q29: not a firm figure series).

| Q | Cell | Kind | Metric | #272 map figures (first two) | Map wall s | Estimate |
|---|---|---|---|---|---|---|
| Q3 | a5.SCHW | series | advisor_headcount | more than 3,000; 3,000 | 20 | LLM (map figure from a non-candidate chunk) |
| Q4 | a5.MER | series | advisor_headcount | 18,916 F2023; 19,273 F2022 | 65 | covered |
| Q7 | a6.MER | series | advisor_headcount | 19,273 FY2022; 19,243 2023Q1 | 67 | covered |
| Q7 | a6.MS | series | advisor_headcount | 15,950 2020-12-31; 15,469 2020-09-30 | 38 | covered |
| Q7 | a6.RJF | series | advisor_headcount | 8,943 2025-09-30; 8,787 2024-09-30 | 51 | covered |
| Q11 | a2.EDJ | fact | advisor_headcount | 20,425 2025-12-31; 20,125 2024-12-31 | 48 | covered |
| Q11 | a2.MER | fact | advisor_headcount | 18,916 2023-12-31; 19,273 2022-12-31 | 47 | covered |
| Q11 | a2.MS | fact | advisor_headcount | 15,950 2020-12-31; 15,469 2020-09-30 | 38 | covered |
| Q11 | a2.RJF | fact | advisor_headcount | 8,943 F2025; 8,787 F2024 | 37 | covered |
| Q11 | a2.SCHW | fact | advisor_headcount | 30,690; 4,127 | 37 | LLM (map figure from a non-candidate chunk) |
| Q22 | a1.EDJ | series | net_new_assets | 18 2026Q2; 17 2025Q2 | 74 | covered |
| Q22 | a1.MER | series | net_new_assets | 19,980 2026Q3; 13,673 2026Q2 | 49 | covered |
| Q22 | a1.MS | series | net_new_assets | 232.4 2026Q3; 148.1 2026Q2 | 26 | covered |
| Q22 | a1.RJF | series | net_new_assets | 12,969 2024Q3; 14,020 2024Q4 | 41 | covered |
| Q22 | a1.SCHW | series | net_new_assets | 114.8 2024Q4; 138 2025Q1 | 41 | covered |
| Q23 | a1.EDJ | series | advisor_headcount | 20,514 2026-06-26; 19,674 2026-03-27 | 73 | covered |
| Q23 | a1.MER | series | advisor_headcount | >15K; 18,916 2023-12-31 | 55 | covered |
| Q23 | a1.MS | series | advisor_headcount | 15,950 2020-12-31; 15,469 2020-09-30 | 56 | covered |
| Q23 | a1.RJF | series | advisor_headcount | 8,943 2025-09-30; 8,787 2024-09-30 | 54 | covered |
| Q23 | a1.SCHW | series | advisor_headcount | 32,000 2025-09-30; 30,690 | 31 | covered |
| Q24 | a1.EDJ | fact | client_assets | $2.5 trillion F2025; $1.1 trillion F2025 | 40 | covered |
| Q24 | a1.MER | fact | client_assets | $1.7 trillion 2025-12-31; $1.7 trillion 2026-03-31 | 48 | covered |
| Q24 | a1.MS | fact | client_assets | $10.5 trillion 2026-09-30; $10.5 trillion 2026-09-30 | 33 | covered |
| Q24 | a1.RJF | fact | client_assets | $1,571.1 2024-09-30; $1,557.5 2024-12-31 | 31 | covered |
| Q24 | a1.SCHW | fact | client_assets | $13.33 trillion 2026-09-30; $13.08 trillion 2026-06-30 | 27 | covered |
| Q24 | a2.EDJ | fact | advisor_headcount | 20,514 2026Q2; 20,537 2026Q2 | 52 | covered |
| Q24 | a2.MER | fact | advisor_headcount | >15K; 18,916 2023Q4 | 21 | covered |
| Q24 | a2.MS | fact | advisor_headcount | 15,950 2020-12-31; 15,469 2020-09-30 | 21 | covered |
| Q24 | a2.RJF | fact | advisor_headcount | 8,943 2025-09-30; 3,878 2025-09-30 | 34 | covered |
| Q24 | a2.SCHW | fact | advisor_headcount | 4,127; 6,584 | 31 | LLM (map figure from a non-candidate chunk) |
| Q26 | a4.RJF | recency | net_new_assets | $98 billion F2026; $23 billion F2026Q4 | 34 | LLM (map figure from a non-candidate chunk) |
| Q27 | a3.MER | series | advisor_headcount | 552 2026 | 33 | LLM (map figure from a non-candidate chunk) |
| Q27 | a5.MER | series | net_new_assets | 20,372 2026Q1; 13,673 2026Q2 | 37 | covered |
