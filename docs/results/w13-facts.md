# W13 facts table (#285): metric figures extracted once, served by SQL

**Outcome: G0 STOP (TL ruling 2026-11-23). Under the tightened serving rule, at most 5 of the 485 map and re-map calls of
the #272 test-B run would be saved (Q23 EDJ, MER, MS, RJF; Q26 RJF), below the gate's 15, even with a perfect
extraction. The extraction was not run; 0 paid calls. `FACTS` ships off by default with the facts module, the
extraction script and its checks, the serving hook, the `facts` table (schema and upgrade) and the loader;
`config/facts.jsonl` is not created. ADR-022 is Deferred; CLAUDE.md is unchanged.**

Plan `plans/0285-facts.md` (TL conditions B1-B7 and G0 of review round 1); decision ADR-022 (`docs/DECISIONS.md`).
Baseline: #272 test B fts (`docs/results/w12-latency.md`): adjudicated 24/30, $0.519 per question off-peak,
critical-path p50 184 s, 454 map calls.

## What happened
- Built at `576e992` (facts module, extraction, checks, setting, hook, schema) and `dbba1ea` (serving and hook tests,
  G0 script); pytest green.
- The extraction run (`w13-facts/run-extract.ps1 -Phase run -GateSha 576e992`, 76 planned calls, off-peak) stopped on
  its first call at 11:02 UTC on 2026-11-23: DeepSeek 402, insufficient balance. Nothing was billed or saved
  (`D:\ALLPROJECTS\EDJ\cache\ev285\extract-run.log`, `extract.head-log.txt`). Count phase (0 calls): 76 documents,
  721 candidate chunks, about 254k estimated input tokens.
- The TL then ruled to decide G0 at 0 calls on the #272 records instead of waiting for a top-up: STOP.

## G0: upper bound on the #272 records (0 calls)
Script `w13-facts/g0_upper_bound.py`, output `w13-facts/g0.json`. Every #272 map / re-map cell is passed through the
shipped rule (`cee.facts.eligible` and `registered_basis`: metric tag registered and served, kind fact / series /
recency, not proxy, no non-figure word in the aspect text, the sub-question text or the question, registry status
`quoted`), and every eligible cell is assumed fully covered.

| | Count |
|---|---|
| Map + re-map calls in #272 test B | 485 |
| Cells with a metric tag | 89 |
| Eligible cells | 5 (Q23 a1 EDJ, MER, MS, RJF; Q26 a4 RJF) |
| **Map calls saved, upper bound** | **5** (threshold 15) -> **STOP** |

The five would still face the later tests (registered basis rows, every asked period present, no newer document in
the pool, SQL re-check), so the real number could only be lower. Why the other 84 metric-tagged cells are not served
(the issue's "metric cells not served, and why"): 67 carry a non-figure word in the aspect, sub-question or question
text (Q11 "define ... include or exclude", Q22 "definition", Q24 "per advisor", Q4 "strategy ... changed", Q7
"recruiting and retention", Q27 "changed"), 8 are proxies, 8 are research rows, 1 is a registry `closest_metric`
(Q23 SCHW).

| Q | Aspect (firms) | Metric | Kind | Reason |
|---|---|---|---|---|
| Q1 | a1 (MS) | net_new_assets | fact | non-figure word 'strateg' |
| Q2 | a4 (RJF) | advisor_headcount | series | non-figure word 'recruit' |
| Q3 | a5 (SCHW) | advisor_headcount | series | non-figure word 'strateg' |
| Q4 | a5 (MER) | advisor_headcount | series | non-figure word 'how' |
| Q6 | a7 (RJF) | advisor_headcount | series | proxy aspect |
| Q7 | a6 (MER, MS, RJF) | advisor_headcount | series | non-figure word 'how' |
| Q7 | a6 (research) | advisor_headcount | series | not a firm row |
| Q7 | a7 (MER, MS, RJF) | net_new_assets | series | non-figure word 'attribut' |
| Q7 | a7 (research) | net_new_assets | series | not a firm row |
| Q11 | a1 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'defin' |
| Q11 | a2 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'defin' |
| Q11 | a3 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'defin' |
| Q11 | a4 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'defin' |
| Q11 | a5 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'disclos' |
| Q12 | a3 (SCHW) | net_new_assets | fact | non-figure word 'source' |
| Q12 | a4 (SCHW) | net_new_assets | series | non-figure word 'growth' |
| Q14 | a3 (RJF) | advisor_headcount | series | non-figure word 'recruit' |
| Q14 | a4 (RJF) | net_new_assets | series | non-figure word 'across the affiliation' |
| Q16 | a8 (all) | advisor_headcount | fact | not a firm row |
| Q21 | a3 (EDJ, MER, MS, RJF, SCHW) | net_new_assets | fact | non-figure word 'how' |
| Q21 | a3 (research) | net_new_assets | fact | not a firm row |
| Q21 | a4 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'how' |
| Q21 | a4 (research) | advisor_headcount | fact | not a firm row |
| Q21 | a8 (EDJ, MER, MS, RJF, SCHW) | net_new_assets | series | proxy aspect |
| Q21 | a8 (research) | net_new_assets | series | not a firm row |
| Q22 | a1 (EDJ, MER, MS, RJF, SCHW) | net_new_assets | series | non-figure word 'defin' |
| Q22 | a2 (EDJ, MER, MS, RJF, SCHW) | net_new_assets | fact | non-figure word 'defin' |
| Q23 | a1 (SCHW) | advisor_headcount | series | registry status closest_metric |
| Q24 | a2 (EDJ, MER, MS, RJF, SCHW) | advisor_headcount | fact | non-figure word 'per' |
| Q26 | a3 (RJF) | advisor_headcount | recency | non-figure word 'recruit' |
| Q27 | a3 (MER) | advisor_headcount | series | non-figure word 'change' |
| Q27 | a5 (MER) | net_new_assets | series | non-figure word 'change' |
| Q28 | a2 (EDJ) | advisor_headcount | series | proxy aspect |
| Q28 | a2 (research) | advisor_headcount | series | not a firm row |
| Q28 | a4 (MER) | advisor_headcount | series | proxy aspect |
| Q28 | a4 (research) | advisor_headcount | series | not a firm row |

## Acceptance against issue #285 (findings)
- Met: the ADR is written (Deferred, with the G0 finding); schema, upgrade and loader; the extraction script with
  code checks (Windows and Mac run scripts); the query-time path behind `FACTS` with facts-served vs LLM cells in the
  matrix log; tests with 0 real calls; the coverage of #272 metric cells is reported with the gaps explained (above).
- Not met, by the G0 ruling: no extraction run, so no row count, check pass rate, audit sample or 50-fact audit; no
  real Q1-Q30 run, so no map calls, $, latency or quality against #272; verify-cee not run (FACTS off shows nothing
  new in the app; the mock compare below proves the default path is unchanged).
- `FACTS=off` (default): the mock compare against clean `main` is in the next section.

## Mock compare, FACTS off vs clean main (0 calls)

PENDING

## Plan-time estimate from the #272 records (0 calls; an upper bound, superseded by G0)

Source: the 485 C1 map and re-map records of #272 test B in `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a`
(`deepseek-v4-pro`, `ds-strict-2-map-low-c128000-s1`), the 30 reused plans, and the extraction candidate chunks
(`w13-facts/candidates.sql`, 719 chunks in 76 documents: 10-K, 10-Q, supplement, press, monthly, deck of EDJ, MS, SCHW,
BAC, MER, RJF that mention a target metric next to a number). Script `w13-facts/coverage272.py`, output
`w13-facts/coverage272.txt`.

- 422 map cells; **95 metric cells** (the aspect names a target metric, by the registry tag or its text, and the map
  gave a figure). Most are narrative or definitional (Q11 "how the firm defines", Q21 "how firms prepare"), proxies
  (Q21 a8, Q24 a3, Q28) or splits (Q14 "across the affiliation-choice model"); the serving rule leaves them to the map.
- **33 servable cells** (the plan's first serving rule, aspect text only). **28 counted as covered** when ANY of the
  map's items cites a candidate chunk; only **21 of 33 have ALL items in candidates** (plan review, item 1), so 28 is an
  upper bound of prefilter recall, not of rows the extraction would yield. The other 5 took their figure from trade press, transcripts or Form ADV (SCHW headcount,
  Q26 RJF NNA in the window, Q27 Merrill since January); at run time they are covered only if the lookup finds rows.
- Coverage estimate: 28/95 metric cells (29%), 28/33 servable (85%). Calls saved: 29 of 485 map + re-map calls (6%).
  Map $ saved: at most $0.85 of $13.97 off-peak, so at best about $0.519 -> $0.49 per question.
- Critical path, if only the covered map calls disappear: Q4 197 -> 156 s, Q22 208 -> 150 s, Q23 144 -> 71 s (less if
  SCHW stays a model cell); p50 184 -> at best about 175 s. The reduce (p50 126 s) stays the long pole.
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
