# Eval run corpus-2026-11-17-20261118-225234

Snapshot `corpus-2026-11-17` | commit `7f12f60` | k=by question | min coverage 0.5 | as of 2026-11-17 | mode mock | retrieval hybrid-norerank | median search 0.573 s (p90 1.281 s, max 1.605 s; warm-up 2.018 s) | 0 real calls

**PASS 28 | FAIL 2 | NOT_EVALUATED 0 | INVALID_OUTPUT 0** (baseline `evals/baselines/corpus-2026-11-17/report.json`)

**Tier-1 recall**: documents 0.619, passages 0.484 (mean over the 17 of 18 tier-1 questions with an answer key; the rest n/a until #56)  
**Recall by stage** (#210, mean over the 21 questions with expected passages): recall@pool 0.528, recall@final 0.403; tier 1 (17): recall@pool 0.623, recall@final 0.484  
**Prompt size**: 685 passages, ~193085 tokens (characters / 4) over 30 questions  
**Refusal accuracy**: gap questions (Q24, Q25, Q28, Q29, Q30) 5/5; all questions with a key 21/22  
**Constants**: FLOOR 0.4, MAX_PER_DOC 3, DUP_JACCARD 0.6, RERANK_FLOOR 0.0, RERANK_N 50, WINDOW_MAX_PER_DOC 8, THEME_MAX_PER_DOC 2  
**Duplicates** (pairs of hits > 0.9 similar): trigram (pg_trgm-style, Python) 1 pairs in 1 questions, max 0.911; word 5-gram 0 pairs in 0 questions, max 0.591  
**CPU**: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel, 12 logical CPUs, Windows, onnxruntime 1.23.2

Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the corpus; PASS when coverage of the available patterns >= min coverage.

Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window. Recall@pool: expected passages with a chunk in any candidate pool before select(); recall@final: in the retrieved set (= Passages). Tokens: characters / 4.

| Q | Tier | Use case | Expected | Firms (mode) | k | Hits | Chars | Tokens | Coverage | Recall docs | Passages (final) | Pool | Refusal | Forbidden | Status | Change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 24226 | 6056 | 3/4 | 3/9 | 1/8 | 3/8 | ok | 0 | PASS | REGRESSED |
| Q2 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 21256 | 5314 | 4/4 | 6/9 | 6/9 | 7/9 | ok | 0 | PASS | UNCHANGED |
| Q3 | 1 | entity_brief | answer | SCHW (entity) | 20 | 20 | 20885 | 5221 | 3/3 | 4/6 | 4/6 | 4/6 | ok | 0 | PASS | UNCHANGED |
| Q4 (trap) | 1 | entity_brief | answer | MER (entity) | 20 | 20 | 21161 | 5290 | 4/4 | 4/5 | 4/7 | 5/7 | ok | 0 | PASS | REGRESSED |
| Q5 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 20914 | 5228 | 3/4 | 3/6 | 3/6 | 3/6 | ok | 0 | PASS | REGRESSED |
| Q6 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 19726 | 4932 | 3/3 | 5/6 | 5/6 | 5/6 | ok | 0 | PASS | REGRESSED |
| Q7 | 2 | head_to_head | answer | MS, MER, RJF (entity+theme) | 20 | 20 | 20918 | 5230 | 9/9 | 1/1 | 0/1 | 0/1 | ok | 0 | PASS | IMPROVED |
| Q8 | 2 | head_to_head | answer | SCHW, RJF (entity) | 20 | 20 | 21532 | 5383 | 4/4 | - | - | - | - | 0 | PASS | UNCHANGED |
| Q9 | 3 | head_to_head | answer | MS, MER (entity) | 20 | 20 | 24314 | 6078 | 6/6 | - | - | - | - | 0 | PASS | IMPROVED |
| Q10 | 3 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 35555 | 8889 | 5/5 | - | - | - | - | 0 | PASS | UNCHANGED |
| Q11 | 1 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 33575 | 8394 | 8/8 | 5/8 | 3/10 | 4/10 | ok | 0 | PASS | REGRESSED |
| Q12 | 3 | mechanism | answer_with_boundary | SCHW, EDJ (entity+theme) | 20 | 20 | 24326 | 6082 | 3/4 | - | - | - | - | 0 | PASS | REGRESSED |
| Q13 | 1 | mechanism | answer | MS (entity) | 20 | 20 | 25784 | 6446 | 3/3 | 4/6 | 4/6 | 5/6 | ok | 0 | PASS | REGRESSED |
| Q14 | 3 | mechanism | answer | RJF (entity) | 20 | 20 | 23436 | 5859 | 3/3 | - | - | - | - | 0 | PASS | UNCHANGED |
| Q15 | 3 | mechanism | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 32778 | 8194 | 5/5 | 1/1 | 0/1 | 0/1 | ok | 0 | PASS | IMPROVED |
| Q16 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 23081 | 5770 | 3/3 | - | - | - | - | 0 | PASS | UNCHANGED |
| Q17 | 1 | theme_scan | answer | none (theme) | 20 | 20 | 20473 | 5118 | 6/10 | 5/9 | 5/10 | 6/10 | ok | 0 | PASS | REGRESSED |
| Q18 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 22559 | 5640 | 5/6 | - | - | - | - | 0 | PASS | REGRESSED |
| Q19 | 3 | segment_evidence | answer_with_boundary | EDJ (entity+theme) | 28 | 25 | 29247 | 7312 | 2/5 | 1/1 | 0/1 | 0/1 | ok | 0 | FAIL | IMPROVED |
| Q20 | 1 | segment_evidence | answer | none (theme) | 20 | 20 | 24834 | 6208 | 1/1 | 1/8 | 1/9 | 1/9 | ok | 0 | PASS | REGRESSED |
| Q21 | 2 | segment_evidence | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 29248 | 7312 | 6/6 | - | - | - | - | 0 | PASS | UNCHANGED |
| Q22 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 35166 | 8792 | 7/7 | 12/33 | 3/8 | 4/8 | FAIL (1) | 0 | FAIL | REGRESSED |
| Q23 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 31157 | 7789 | 6/7 | 8/20 | 8/20 | 13/20 | ok | 0 | PASS | IMPROVED |
| Q24 | 3 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 32414 | 8104 | 4/5 | 3/5 | 1/4 | 2/4 | ok | 0 | PASS | IMPROVED |
| Q25 | 1 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 31953 | 7988 | 7/8 | 3/5 | 1/5 | 3/5 | ok | 0 | PASS | REGRESSED |
| Q26 | 1 | recency | answer | RJF (entity) | 20 | 20 | 25687 | 6422 | 1/1 | - | - | - | ok | 0 | PASS | UNCHANGED |
| Q27 (trap) | 1 | recency | answer | MER (entity) | 20 | 20 | 24811 | 6203 | 2/2 | 5/9 | 5/9 | 7/9 | ok | 0 | PASS | REGRESSED |
| Q28 | 1 | honest_miss | gap_with_adjacent | EDJ, MER (entity+theme) | 20 | 20 | 23814 | 5954 | 2/3 | 5/6 | 3/4 | 3/4 | ok | 0 | PASS | REGRESSED |
| Q29 | 1 | honest_miss | gap_with_adjacent | MS (entity) | 20 | 20 | 22611 | 5653 | 2/2 | 1/1 | 1/2 | 2/2 | ok | 0 | PASS | REGRESSED |
| Q30 (trap) | 1 | honest_miss | gap_with_adjacent | MER (entity) | 20 | 20 | 24894 | 6224 | 1/1 | 2/2 | 1/2 | 1/2 | ok | 0 | PASS | UNCHANGED |
| **All** | | | | | | 685 | 772335 | 193085 | | | 0.403 (mean) | 0.528 (mean) | 21/22 | 0 | PASS 28 |  |

## Per question

### Q1 - PASS

What is Morgan Stanley's strategy to increase their net new assets?

- `MS:transcript`: hit MS-TR-2025Q3#24, MS-TR-2025Q2#34, MS-TR-2025Q4#8, MS-TR-2025Q1#12, MS-TR-2024Q4#24, MS-TR-2025Q4#19
- `MS:10-K#Wealth Management`: hit MS-10K-2025#180, MS-10K-2025#165
- `MS:deck`: hit MS-DECK-2026-strategic-update#30, MS-DECK-2026-strategic-update#31
- `MS:supplement`: no hit
- Expected `MS-TR-2026Q2#3`: missing (not in pool)
- Expected `MS-TR-2026Q2#14, MS-TR-2026Q2#16`: missing (not in pool)
- Expected `MS-TR-2026Q3#3, MS-TR-2026Q3#12, MS-TR-2026Q3#13`: missing (not in pool)
- Expected `MS-TR-2026Q1#3, MS-TR-2026Q1#9, MS-TR-2026Q1#10, MS-TR-2026Q1#11`: missing (not in pool)
- Expected `MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5`: found MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5
- Expected `MS-10K-2025#125`: missing (not in pool)
- Expected `MS-10K-2025#127, MS-10K-2025#164, MS-10K-2025#166`: missing (in pool, lost in select: MS-10K-2025#127, MS-10K-2025#164)
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14`: missing (in pool, lost in select: MS-SUPP-2026Q1#14, MS-SUPP-2026Q2#16, MS-SUPP-2026Q3#16)
- Retrieved: MS-TR-2025Q3#24, MS-10Q-2026Q2#58, MS-DECK-2026-strategic-update#30, MS-10K-2025#180, MS-PR-2026-10-14-01#5, MS-TR-2025Q2#34, MS-10Q-2026Q1#18, MS-DECK-2026-strategic-update#31, MS-PR-2026-07-15-01#5, MS-TR-2025Q4#8, MS-10Q-2025Q3#57, MS-10K-2025#165, MS-TR-2025Q1#12, MS-10Q-2025Q2#74, MS-PR-2026-04-15-01#2, MS-TR-2024Q4#24, MS-10Q-2026Q1#61, MS-PR-2026-01-15-01#3, MS-TR-2025Q4#19, MS-TRADE-2026-10-14-WM-01#0

### Q2 - PASS

How is Raymond James positioning itself to recruit advisors away from the wirehouses?

- `RJF:transcript`: hit RJF-TR-2026Q1#54, RJF-TR-2025Q4#98, RJF-TR-2025Q3#8, RJF-TR-2025Q2#21, RJF-TR-2025Q1#11, RJF-TR-2025Q2#25, RJF-TR-2025Q4#44, RJF-TR-2025Q3#30, RJF-TR-2026Q1#5
- `RJF:10-K`: hit RJF-10K-2025#27, RJF-10K-2025#91, RJF-10K-2025#10
- `RJF:press`: hit RJF-PR-web-affiliation-options#0, RJF-PR-web-advisor-select#0, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-PR-web-independent-advisor#0, RJF-PR-web-traditional-employee-advisor#0, RJF-PR-web-affiliation-options#2
- `RJF:trade`: hit RJF-TRADE-2026-11-04-IN-01#2
- Expected `RJF-10K-2025`: found RJF-10K-2025#27, RJF-10K-2025#91, RJF-10K-2025#10
- Expected `RJF-TR-2025Q4`: found RJF-TR-2025Q4#98, RJF-TR-2025Q4#44
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#54, RJF-TR-2026Q1#5
- Expected `RJF-TR-2026Q2`: missing (not in pool)
- Expected `RJF-PR-2026-04-22-01`: missing (in pool, lost in select: RJF-PR-2026-04-22-01#1)
- Expected `RJF-PR-2026-07-22-01`: missing (not in pool)
- Expected `RJF-PR-web-affiliation-options`: found RJF-PR-web-affiliation-options#0, RJF-PR-web-affiliation-options#2
- Expected `RJF-PR-web-traditional-employee-advisor`: found RJF-PR-web-traditional-employee-advisor#0
- Expected `RJF-PR-web-independent-advisor`: found RJF-PR-web-independent-advisor#0
- Retrieved: RJF-PR-web-affiliation-options#0, RJF-TR-2026Q1#54, RJF-10K-2025#27, RJF-DECK-2025-investor-day#36, RJF-PR-web-advisor-select#0, RJF-TR-2025Q4#98, RJF-10K-2025#91, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-TR-2025Q3#8, RJF-10K-2025#10, RJF-PR-web-independent-advisor#0, RJF-TR-2025Q2#21, RJF-PR-web-traditional-employee-advisor#0, RJF-TR-2025Q1#11, RJF-PR-web-affiliation-options#2, RJF-TR-2025Q2#25, RJF-TR-2025Q4#44, RJF-TR-2025Q3#30, RJF-TR-2026Q1#5, RJF-TRADE-2026-11-04-IN-01#2

### Q3 - PASS

What is Schwab's strategy for its RIA custody business?

- `SCHW:transcript`: hit SCHW-TR-2026Q3#4, SCHW-TR-2025Q3#13, SCHW-TR-2026Q2#15, SCHW-TR-2025Q1#9, SCHW-TR-2024Q4#11, SCHW-TR-2026Q3#10, SCHW-TR-2026Q3#5, SCHW-TR-2025Q3#9
- `SCHW:10-K#Advisor Services`: hit SCHW-10K-2025#26, SCHW-10K-2025#24, SCHW-10K-2025#23
- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#62, SCHW-DECK-2026Q2#14, SCHW-DECK-2026-investor-day#305
- Expected `SCHW-10K-2025`: found SCHW-10K-2025#26, SCHW-10K-2025#24, SCHW-10K-2025#23
- Expected `SCHW-TR-2026Q1`: missing (not in pool)
- Expected `SCHW-TR-2026Q2`: found SCHW-TR-2026Q2#15
- Expected `SCHW-TR-2026Q3`: found SCHW-TR-2026Q3#4, SCHW-TR-2026Q3#10, SCHW-TR-2026Q3#5
- Expected `SCHW-DECK-2026Q3`: missing (not in pool)
- Expected `SCHW-DECK-2026-investor-day`: found SCHW-DECK-2026-investor-day#62, SCHW-DECK-2026-investor-day#305
- Retrieved: SCHW-10K-2025#26, SCHW-10Q-2026Q2#7, SCHW-TR-2026Q3#4, SCHW-DECK-2026-investor-day#62, SCHW-10K-2025#24, SCHW-10Q-2026Q1#25, SCHW-TR-2025Q3#13, SCHW-DECK-2026Q2#14, SCHW-10K-2025#23, SCHW-10Q-2026Q2#30, SCHW-DECK-2026-investor-day#305, SCHW-TR-2026Q2#15, SCHW-TR-2025Q1#9, SCHW-TR-2024Q4#11, SCHW-TR-2026Q3#10, SCHW-TR-2026Q3#5, SCHW-TR-2025Q3#9, SCHW-TRADE-2026-10-29-WM-01#0, SCHW-TRADE-2026-10-28-WM-01#0, SCHW-TRADE-2026-11-02-RB-01#3

### Q4 - PASS

What is Merrill's advisor growth strategy, and how has it changed?

- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#19, BAC-TR-2025Q4#106, BAC-TR-2025Q2#34, BAC-TR-2026Q2#20, BAC-TR-2025Q3#26
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246, BAC-10K-2025#247
- `MER:press`: hit MER-PR-web-becoming-a-merrill-lynch-advisor#0, MER-PR-web-advisor-development-program#0, MER-PR-2026-09-15-01#0, MER-PR-2026-09-15-01#2, MER-PR-web-becoming-a-merrill-lynch-advisor#1
- `MER:trade`: hit MER-TRADE-2026-10-14-IN-01#2
- Expected `BAC-TR-2026Q1#25, BAC-TR-2026Q1#26`: missing (not in pool)
- Expected `BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: missing (not in pool)
- Expected `BAC-TR-2026Q2#20, BAC-TR-2026Q2#21, BAC-TR-2026Q2#22`: found BAC-TR-2026Q2#20
- Expected `BAC-TR-2026Q2#63`: missing (in pool, lost in select: BAC-TR-2026Q2#63)
- Expected `BAC-TR-2026Q3#19`: found BAC-TR-2026Q3#19
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246, BAC-10K-2025#247
- Expected `BAC-10Q-2026Q2#88, BAC-10Q-2026Q2#89, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91`: found BAC-10Q-2026Q2#88
- Retrieved: MER-PR-web-becoming-a-merrill-lynch-advisor#0, BAC-TR-2026Q3#19, BAC-10K-2025#246, BAC-DECK-2025-investor-day#18, BAC-10Q-2026Q2#88, MER-PR-web-advisor-development-program#0, BAC-TR-2025Q4#106, BAC-10K-2025#247, BAC-10Q-2026Q1#73, MER-PR-2026-09-15-01#0, BAC-TR-2025Q2#34, BAC-DECK-2025-investor-day#8, BAC-10Q-2025Q3#94, MER-PR-2026-09-15-01#2, BAC-TR-2026Q2#20, BAC-DECK-2025-investor-day#9, MER-PR-web-becoming-a-merrill-lynch-advisor#1, BAC-TR-2025Q3#26, BAC-10Q-2025Q2#93, MER-TRADE-2026-10-14-IN-01#2

### Q5 - PASS

Where is Morgan Stanley investing in technology for its advisors?

- `MS:transcript`: hit MS-TR-2026Q3#32, MS-TR-2025Q4#8, MS-TR-2025Q3#37, MS-TR-2025Q1#54, MS-TR-2024Q4#44, MS-TR-2025Q4#35, MS-TR-2026Q3#21, MS-TR-2025Q3#52, MS-TR-2025Q3#8, MS-TR-2025Q4#9, MS-TR-2025Q1#70, MS-TR-2024Q4#10
- `MS:10-K`: hit MS-10K-2025#58, MS-10K-2025#25, MS-10K-2025#76
- `MS:deck`: no hit
- `MS:trade`: hit MS-TRADE-2026-09-16-IN-01#0
- Expected `MS-10K-2025`: found MS-10K-2025#58, MS-10K-2025#25, MS-10K-2025#76
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#8, MS-TR-2025Q4#35, MS-TR-2025Q4#9
- Expected `MS-TR-2026Q1`: missing (not in pool)
- Expected `MS-TR-2026Q2`: missing (not in pool)
- Expected `MS-TR-2026Q3`: found MS-TR-2026Q3#32, MS-TR-2026Q3#21
- Expected `MS-DECK-2026-strategic-update`: missing (not in pool)
- Retrieved: MS-TR-2026Q3#32, MS-10K-2025#58, MS-PR-2026-10-14-01#8, MS-TR-2025Q4#8, MS-10K-2025#25, MS-PR-2026-07-15-01#8, MS-TR-2025Q3#37, MS-10K-2025#76, MS-PR-2026-04-15-01#8, MS-TR-2025Q1#54, MS-PR-2026-01-15-01#13, MS-TR-2024Q4#44, MS-TR-2025Q4#35, MS-TR-2026Q3#21, MS-TR-2025Q3#52, MS-TR-2025Q3#8, MS-TR-2025Q4#9, MS-TR-2025Q1#70, MS-TR-2024Q4#10, MS-TRADE-2026-09-16-IN-01#0

### Q6 - PASS

What has Raymond James said about its affiliation models, and has the mix shifted?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q2#31, RJF-TR-2025Q4#50, RJF-TR-2025Q2#21, RJF-TR-2025Q1#11, RJF-TR-2024Q4#8, RJF-TR-2024Q3#10, RJF-TR-2025Q2#66, RJF-TR-2025Q2#25
- `RJF:press`: hit RJF-PR-web-affiliation-options#0, RJF-PR-web-independent-advisor#1, RJF-PR-web-advisor-select#0, RJF-PR-2026-04-22-01#1, RJF-PR-web-independent-advisor#0
- Expected `RJF-10K-2025`: found RJF-10K-2025#462, RJF-10K-2025#10
- Expected `RJF-10Q-2026Q2`: found RJF-10Q-2026Q2#237
- Expected `RJF-TR-2025Q2`: found RJF-TR-2025Q2#21, RJF-TR-2025Q2#66, RJF-TR-2025Q2#25
- Expected `RJF-TR-2026Q1`: missing (not in pool)
- Expected `RJF-TR-2026Q2`: found RJF-TR-2026Q2#31
- Expected `RJF-PR-web-affiliation-options`: found RJF-PR-web-affiliation-options#0
- Retrieved: RJF-TR-2026Q2#31, RJF-PR-web-affiliation-options#0, RJF-10K-2025#462, RJF-10Q-2026Q2#237, RJF-DECK-2025-investor-day#49, RJF-TR-2025Q4#50, RJF-PR-web-independent-advisor#1, RJF-10K-2025#10, RJF-TR-2025Q2#21, RJF-PR-web-advisor-select#0, RJF-TR-2025Q1#11, RJF-PR-2026-04-22-01#1, RJF-TR-2024Q4#8, RJF-PR-web-independent-advisor#0, RJF-TR-2024Q3#10, RJF-TR-2025Q2#66, RJF-TR-2025Q2#25, RJF-TRADE-2026-10-29-WM-01#0, RJF-TRADE-2026-09-02-IN-01#1, RJF-TRADE-2026-08-26-IN-01#1

### Q7 - PASS

How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `MS:transcript`: hit MS-TR-2025Q2#33, MS-TR-2025Q1#54, MS-TR-2024Q4#10
- `MS:10-K`: hit MS-10K-2025#51
- `BAC:transcript#GWIM`: hit BAC-TR-2025Q4#106
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `RJF:transcript`: hit RJF-TR-2025Q3#8
- `RJF:10-K`: hit RJF-10K-2025#27
- `MS:trade`: hit MS-TRADE-2026-10-26-IN-01#4
- `MER:trade`: hit MER-TRADE-2026-11-16-AH-01#1
- `RJF:trade`: hit RJF-TRADE-2026-10-29-WM-01#0
- Expected `MS-10K-2025#153`: missing (not in pool)
- Retrieved: BAC-TR-2025Q4#106, RJF-TR-2025Q3#8, MS-TR-2025Q2#33, MER-PR-web-advisor-development-program#2, MS-TR-2025Q1#54, RJF-10K-2025#27, MS-10K-2025#51, BAC-DECK-2025-investor-day#9, RJF-PR-web-affiliation-options#0, MS-10Q-2026Q2#144, BAC-10K-2025#246, RJF-10Q-2026Q2#167, MS-TR-2024Q4#10, MER-TRADE-2026-11-16-AH-01#1, RJF-TRADE-2026-10-29-WM-01#0, MS-TRADE-2026-10-26-IN-01#4, MCK-ADVISOR-SHORTAGE-2025#23, MCK-ADVISOR-SHORTAGE-2025#30, KITCES-WELLBEING-2023#131, KITCES-WELLBEING-2023#92

### Q8 - PASS

Compare how Schwab and Raymond James describe their value proposition to independent advisors.

- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#306, SCHW-DECK-2026-investor-day#54
- `SCHW:10-K`: hit SCHW-10K-2025#13, SCHW-10K-2025#19
- `RJF:deck`: hit RJF-DECK-2025-investor-day#38
- `RJF:10-K`: hit RJF-10K-2025#27
- Retrieved: RJF-TR-2025Q4#50, SCHW-DECK-2026-investor-day#306, RJF-PR-web-independent-advisor#0, SCHW-TR-2026Q1#28, RJF-10K-2025#27, SCHW-10K-2025#13, RJF-DECK-2025-investor-day#38, SCHW-10Q-2026Q2#7, RJF-TR-2026Q2#7, SCHW-PR-2026-10-15-01#36, RJF-PR-web-affiliation-options#0, SCHW-DECK-2026-investor-day#54, SCHW-TR-2026Q1#49, RJF-10Q-2026Q2#237, SCHW-10K-2025#19, RJF-TR-2025Q2#7, SCHW-PR-2026-01-21-01#36, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-TRADE-2026-10-29-WM-01#0, SCHW-TRADE-2026-10-29-WM-01#0

### Q9 - PASS

How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

- `MS:10-K`: hit MS-10K-2025#190
- `MS:transcript`: hit MS-TR-2026Q3#33, MS-TR-2025Q1#27
- `MS:deck`: hit MS-DECK-2026-strategic-update#29
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#19
- `BAC:deck#GWIM`: hit BAC-DECK-2025-investor-day#9, BAC-DECK-2026Q3#31
- Retrieved: BAC-10K-2025#246, MS-10K-2025#190, BAC-10Q-2026Q2#88, MS-10Q-2025Q3#86, BAC-DECK-2025-investor-day#9, MS-PR-2026-10-14-01#8, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MS-TR-2026Q3#33, BAC-TR-2026Q3#19, MS-DECK-2026-strategic-update#29, BAC-SUPP-2026Q2#55, MS-10Q-2025Q2#18, BAC-10Q-2025Q2#93, MS-PR-2026-07-15-01#8, BAC-DECK-2026Q3#31, MS-TR-2025Q1#27, BAC-PR-2026-04-15-01#10, MS-SUPP-2026Q3#27, MER-TRADE-2026-11-03-WM-01#1, MS-TRADE-2026-10-14-WM-01#0

### Q10 - PASS

Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

- Theme mass_affluent: no chunk on the theme for EDJ
- `MS:transcript`: hit MS-TR-2026Q3#11, MS-TR-2026Q2#3
- `SCHW:transcript`: hit SCHW-TR-2024Q4#32
- `EDJ:10-K`: hit EDJ-10K-2025#88, EDJ-10K-2025#10
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#19
- `RJF:transcript`: hit RJF-TR-2026Q2#9
- Retrieved: BAC-DECK-2025-investor-day#12, RJF-TR-2026Q2#9, MS-TRADE-2026-10-21-IN-01#3, EDJ-10K-2025#88, SCHW-DECK-2026Q2#16, MS-10K-2025#125, EDJ-10Q-2026Q1#24, SCHW-TR-2024Q4#32, BAC-TR-2026Q3#19, RJF-10Q-2026Q2#223, MS-TR-2026Q3#11, EDJ-10K-2025#10, BAC-10K-2025#249, RJF-10K-2025#33, MS-10K-2025#144, EDJ-TRADE-2026-11-12-IN-01#1, SCHW-10K-2025#213, MER-PR-web-becoming-a-merrill-lynch-advisor#4, RJF-DECK-2025-investor-day#125, MS-TR-2026Q2#3, EDJ-TRADE-2026-08-18-IN-01#0, SCHW-10Q-2025Q3#195, BAC-10Q-2026Q1#75, MER-TRADE-2026-11-12-IN-01#2, RJF-TRADE-2026-11-04-IN-01#2, SCHW-TRADE-2026-10-29-WM-01#0, CERULLI-MASS-AFFLUENT-2026#0, KITCES-WELLBEING-2023#107, CERULLI-MASS-AFFLUENT-2026#1, KITCES-WELLBEING-2023#38

### Q11 - PASS

How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

- `MS:10-K`: hit MS-10K-2025#167
- `MS:supplement`: hit MS-SUPP-2026Q2#37
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-K`: hit EDJ-10K-2025#202, EDJ-10K-2025#141, EDJ-10K-2025#130
- `BAC:10-K#GWIM`: hit BAC-10K-2025#249
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q3#52
- `RJF:10-K`: hit RJF-10K-2025#228
- `RJF:supplement`: hit RJF-SUPP-2025Q4#1
- Expected `EDJ-10K-2025#130`: found EDJ-10K-2025#130
- Expected `EDJ-10K-2025#131, EDJ-10K-2025#148`: missing (not in pool)
- Expected `EDJ-10Q-2026Q2#60`: missing (not in pool)
- Expected `EDJ-10K-2025#29`: missing (not in pool)
- Expected `RJF-10K-2025#227`: missing (not in pool)
- Expected `RJF-10K-2025#228`: found RJF-10K-2025#228
- Expected `RJF-10K-2025#24`: missing (not in pool)
- Expected `MS-10K-2025#167, MS-SUPP-2026Q3#38`: found MS-10K-2025#167
- Expected `BAC-10K-2025#246`: missing (in pool, lost in select: BAC-10K-2025#246)
- Expected `SCHW-10K-2025#18, SCHW-TR-2026Q1#4, SCHW-TR-2026Q1#5`: missing (not in pool)
- Retrieved: MS-DECK-2026-strategic-update#31, EDJ-10K-2025#202, BAC-SUPP-2026Q3#52, RJF-10K-2025#228, SCHW-10Q-2026Q1#60, MS-SUPP-2026Q2#37, EDJ-10Q-2025Q3#69, BAC-PR-2026-10-14-01#13, RJF-10Q-2026Q2#452, SCHW-10K-2025#197, MS-10Q-2025Q3#85, EDJ-10K-2025#141, BAC-DECK-2026Q3#31, RJF-TR-2025Q3#4, SCHW-DECK-2026-investor-day#59, MS-10K-2025#167, EDJ-10Q-2025Q3#60, BAC-TR-2026Q3#19, RJF-DECK-2025-investor-day#93, SCHW-PR-2026-10-15-01#43, MS-PR-2026-04-15-01#15, EDJ-10K-2025#130, BAC-10K-2025#249, RJF-PR-web-independent-ria-custody-services#1, SCHW-TR-2025Q1#42, SCHW-TR-2025Q1#43, MS-DECK-2026-strategic-update#32, BAC-10Q-2026Q2#88, RJF-SUPP-2025Q4#1, SCHW-10Q-2026Q2#179

### Q12 - PASS

How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

- Theme client_acquisition: no chunk on the theme for no firm (every named firm has one)
- `SCHW:transcript`: hit SCHW-TR-2025Q4#9, SCHW-TR-2026Q3#14, SCHW-TR-2026Q1#13, SCHW-TR-2025Q2#13
- `SCHW:10-K`: hit SCHW-10K-2025#13
- `SCHW:monthly`: no hit
- `EDJ:10-K`: hit EDJ-10K-2025#88, EDJ-10K-2025#82, EDJ-10K-2025#208
- Retrieved: SCHW-TR-2025Q4#9, EDJ-10K-2025#88, SCHW-TR-2026Q3#14, EDJ-10Q-2026Q2#28, SCHW-10K-2025#13, EDJ-10K-2025#82, SCHW-10Q-2026Q2#8, EDJ-10Q-2025Q2#110, SCHW-PR-2026-10-15-01#7, EDJ-10K-2025#208, SCHW-DECK-2026-investor-day#251, EDJ-10Q-2025Q3#69, SCHW-TR-2026Q1#13, EDJ-10Q-2026Q1#84, EDJ-10Q-2025Q2#64, SCHW-PR-2026-07-21-01#2, EDJ-10Q-2025Q3#67, SCHW-TR-2025Q2#13, EDJ-TRADE-2026-11-12-IN-01#1, SCHW-TRADE-2026-08-20-RB-01#3

### Q13 - PASS

How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

- `MS:transcript`: hit MS-TR-2025Q4#8, MS-TR-2025Q2#34, MS-TR-2024Q4#94
- `MS:10-K`: hit MS-10K-2025#168, MS-10K-2025#123, MS-10K-2025#165
- `MS:deck`: hit MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#31
- Expected `MS-10K-2025`: found MS-10K-2025#168, MS-10K-2025#123, MS-10K-2025#165
- Expected `MS-SUPP-2026Q3`: found MS-SUPP-2026Q3#16
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#8
- Expected `MS-TR-2026Q2`: missing (in pool, lost in select: MS-TR-2026Q2#3)
- Expected `MS-TR-2026Q3`: missing (not in pool)
- Expected `MS-DECK-2026-strategic-update`: found MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#31
- Retrieved: MS-10Q-2026Q1#53, MS-DECK-2026-strategic-update#32, MS-TR-2025Q4#8, MS-10K-2025#168, MS-SUPP-2026Q1#44, MS-PR-2026-10-14-01#8, MS-10Q-2026Q2#232, MS-DECK-2026-strategic-update#31, MS-10K-2025#123, MS-SUPP-2026Q3#16, MS-PR-2026-07-15-01#8, MS-10Q-2026Q2#57, MS-TR-2025Q2#34, MS-10K-2025#165, MS-SUPP-2026Q2#16, MS-PR-2026-04-15-01#8, MS-10Q-2026Q2#61, MS-SUPP-2025Q4#36, MS-TR-2024Q4#94, MS-TRADE-2026-10-21-IN-01#2

### Q14 - PASS

How does Raymond James's affiliation-choice model work commercially?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q2#26, RJF-TR-2025Q4#50, RJF-TR-2025Q1#79, RJF-TR-2024Q4#23, RJF-TR-2025Q3#5, RJF-TR-2026Q2#31
- `RJF:press`: hit RJF-PR-web-affiliation-options#0, RJF-PR-web-independent-advisor#1, RJF-PR-web-advisor-select#0, RJF-PR-web-independent-ria-custody-services#1, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-PR-web-traditional-employee-advisor#0, RJF-PR-web-affiliation-options#2
- Retrieved: RJF-PR-web-affiliation-options#0, RJF-TR-2026Q2#26, RJF-10K-2025#9, RJF-DECK-2025-investor-day#110, RJF-PR-web-independent-advisor#1, RJF-TR-2025Q4#50, RJF-10K-2025#91, RJF-10Q-2025Q4#142, RJF-PR-web-advisor-select#0, RJF-TR-2025Q1#79, RJF-10K-2025#10, RJF-10Q-2025Q4#191, RJF-PR-web-independent-ria-custody-services#1, RJF-TR-2024Q4#23, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-TR-2025Q3#5, RJF-PR-web-traditional-employee-advisor#0, RJF-TR-2026Q2#31, RJF-PR-web-affiliation-options#2, RJF-TRADE-2026-10-29-WM-01#0

### Q15 - PASS

What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

- `SCHW:10-K`: hit SCHW-10K-2025#13
- `MS:10-K`: hit MS-10K-2025#167
- `EDJ:10-K`: hit EDJ-10K-2025#20, EDJ-10K-2025#131, EDJ-10K-2025#58
- `BAC:10-K#GWIM`: hit BAC-10K-2025#249
- `RJF:10-K`: hit RJF-10K-2025#173
- Expected `SCHW-10K-2025#27`: missing (not in pool)
- Retrieved: EDJ-10K-2025#20, SCHW-10K-2025#13, BAC-TR-2026Q1#26, RJF-TR-2024Q3#8, MS-10Q-2026Q2#59, EDJ-10Q-2026Q2#62, SCHW-10Q-2026Q2#40, BAC-10K-2025#249, RJF-10Q-2026Q1#300, MS-SUPP-2026Q3#38, EDJ-10K-2025#131, SCHW-DECK-2026-investor-day#62, BAC-DECK-2025-investor-day#8, RJF-10K-2025#173, MS-10K-2025#167, EDJ-10Q-2025Q2#69, SCHW-PR-2026-01-21-01#1, BAC-10Q-2026Q1#75, RJF-PR-2026-07-22-01#98, MS-TR-2026Q1#3, EDJ-10K-2025#58, SCHW-TR-2025Q3#34, BAC-SUPP-2026Q3#52, RJF-SUPP-2026Q2#43, MS-DECK-2026-strategic-update#31, EDJ-10Q-2025Q2#67, SCHW-MONTHLY-2026-04#9, BAC-PR-2026-07-14-01#10, RJF-DECK-2026Q1#4, MS-PR-2026-10-14-01#13

### Q16 - PASS

What will receiving financial advice in the future look like for clients?

- `THEME:research`: hit VANGUARD-VALUE-2025#21, VANGUARD-VALUE-2025#1
- `THEME:regulatory`: not in corpus
- `THEME:survey`: not in corpus
- `MS:transcript`: hit MS-TR-2026Q2#28
- `SCHW:transcript`: hit SCHW-TR-2026Q1#16
- Retrieved: MER-PR-web-becoming-a-merrill-lynch-advisor#3, MS-TR-2026Q2#28, VANGUARD-VALUE-2025#21, EDJ-10K-2025#88, RJF-TR-2026Q1#51, BAC-TR-2025Q1#114, SCHW-TR-2026Q1#16, MER-PR-web-becoming-a-merrill-lynch-advisor#4, MS-10K-2025#170, VANGUARD-VALUE-2025#1, EDJ-10Q-2026Q2#62, RJF-DECK-2025-investor-day#35, BAC-10K-2025#482, SCHW-DECK-2026Q3#53, MER-TRADE-2026-10-14-IN-01#0, RJF-PR-web-bank-and-credit-union-advisors#1, BAC-DECK-2026Q2#55, SCHW-10Q-2026Q2#13, MS-TRADE-2026-10-21-IN-01#2, EDJ-TRADE-2026-11-12-IN-01#1

### Q17 - PASS

What are these firms saying about AI in advice delivery, and who is claiming the most?

- `MS:transcript`: hit MS-TR-2026Q3#42
- `SCHW:transcript`: hit SCHW-TR-2026Q1#16
- `BAC:transcript#GWIM`: type only (qualifier not met): BAC-TR-2026Q2#6, BAC-TR-2025Q2#14
- `RJF:transcript`: hit RJF-TR-2026Q1#30
- `MS:press`: no hit
- `SCHW:press`: hit SCHW-PR-2026-07-21-01#8
- `EDJ:press`: not in corpus
- `MER:press`: hit MER-PR-web-becoming-a-merrill-lynch-advisor#5, MER-PR-web-advisor-development-program#1
- `RJF:press`: no hit
- `MS:trade`: no hit
- `MER:trade`: hit MER-TRADE-2026-10-14-IN-01#0
- Expected `MS-10K-2025`: found MS-10K-2025#372
- Expected `MS-TR-2026Q2`: missing (not in pool)
- Expected `SCHW-TR-2026Q1`: found SCHW-TR-2026Q1#16
- Expected `SCHW-DECK-2026Q2`: missing (not in pool)
- Expected `BAC-TR-2026Q2`: found BAC-TR-2026Q2#6
- Expected `BAC-TR-2026Q3`: missing (not in pool)
- Expected `RJF-TR-2025Q4`: missing (in pool, lost in select: RJF-TR-2025Q4#75)
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#30
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#56
- Expected `BAC-TR-2026Q2#21`: missing (not in pool)
- Retrieved: EDJ-10K-2025#56, MER-PR-web-becoming-a-merrill-lynch-advisor#5, SCHW-TR-2026Q1#16, BAC-TR-2026Q2#6, DELOITTE-AGENTIC-2026#0, RJF-TR-2026Q1#30, MS-TR-2026Q3#42, EDJ-10Q-2026Q1#46, MER-PR-web-advisor-development-program#1, SCHW-DECK-2026-investor-day#182, BAC-DECK-2026Q2#29, ACCENTURE-GENAI#12, RJF-10K-2025#112, MS-10K-2025#372, MER-TRADE-2026-10-14-IN-01#0, SCHW-PR-2026-07-21-01#8, BAC-TR-2025Q2#14, RJF-DECK-2025-investor-day#119, MS-10Q-2026Q2#524, EDJ-TRADE-2026-09-30-WM-01#0

### Q18 - PASS

Where is the industry heading on fee structures and pricing transparency?

- `MS:adv`: hit MS-ADV-2026#223
- `SCHW:adv`: no hit
- `EDJ:adv`: hit EDJ-ADV-2026#54
- `MER:adv`: hit MER-ADV-2026#450
- `RJF:adv`: hit RJF-ADV-2026#33
- `THEME:regulatory`: not in corpus
- `THEME:research`: hit MCK-SIGNAL-SELLOFF-2026#9, WEALTHTENDER-ADVISOR-SEARCH-2025#21
- Retrieved: MCK-SIGNAL-SELLOFF-2026#9, RJF-TR-2026Q1#48, SCHW-10K-2025#95, MER-ADV-2026#450, MS-10K-2025#393, EDJ-10K-2025#151, BAC-10K-2025#621, WEALTHTENDER-ADVISOR-SEARCH-2025#21, RJF-10K-2025#110, SCHW-TR-2026Q1#62, MER-PR-2026-09-15-01#2, MS-ADV-2026#223, EDJ-ADV-2026#54, BAC-10Q-2025Q3#659, RJF-ADV-2026#33, SCHW-10Q-2025Q2#72, MS-TR-2025Q1#81, BAC-DECK-2025-investor-day#42, MER-TRADE-2026-09-29-RB-01#7, EDJ-TRADE-2026-08-18-IN-01#6

### Q19 - FAIL

How should the preferences of younger investors shape Edward Jones's offerings?

- Theme younger_investors: no chunk on the theme for EDJ
- `THEME:research`: hit BOFA-PB-STUDY-2026#4, FINRAF-INVESTORS-2025#18, FINRAF-INVESTORS-2025#36, BOFA-PB-STUDY-2024#9
- `THEME:survey`: not in corpus
- `MS:press`: no hit
- `SCHW:press`: no hit
- `RJF:press`: no hit
- `MER:press`: hit BAC-PR-2026-10-14-01#11, BAC-PR-2026-07-14-01#10
- Expected `EDJ-10K-2025#88`: missing (not in pool)
- Retrieved: EDJ-10K-2025#204, EDJ-10Q-2026Q2#39, EDJ-10K-2025#41, EDJ-10Q-2026Q1#82, EDJ-10K-2025#9, EDJ-10Q-2025Q3#107, EDJ-10Q-2025Q2#17, EDJ-10Q-2025Q3#19, EDJ-10Q-2025Q3#68, EDJ-10Q-2026Q1#78, EDJ-TRADE-2026-08-18-IN-01#4, EDJ-TRADE-2026-09-30-WM-01#2, EDJ-TRADE-2026-11-12-IN-01#0, EDJ-TRADE-2026-09-24-IN-01#0, EDJ-TRADE-2026-08-18-IN-01#5, EDJ-TRADE-2026-08-18-IN-01#2, BOFA-PB-STUDY-2026#4, FINRAF-INVESTORS-2025#18, FINRAF-INVESTORS-2025#36, BOFA-PB-STUDY-2024#9, BAC-PR-2026-10-14-01#11, SCHW-TR-2026Q3#11, RJF-DECK-2025-investor-day#42, BAC-PR-2026-07-14-01#10, SCHW-TR-2025Q4#11

### Q20 - PASS

What evidence is there about how clients under 40 choose a financial advisor?

- `THEME:survey`: not in corpus
- `THEME:research`: hit UBS-NEXTGEN-2026#83, CFPB-MISINFO-2025#9
- Expected `UBS-NEXTGEN-2026`: found UBS-NEXTGEN-2026#83
- Expected `CERULLI-GWT-2025`: missing (not in pool)
- Expected `FINRAF-INVESTORS-2025`: missing (not in pool)
- Expected `KITCES-WELLBEING-2023`: missing (not in pool)
- Expected `BOFA-PB-STUDY-2026`: missing (not in pool)
- Expected `NM-PP-2026`: missing (not in pool)
- Expected `WEALTHTENDER-ADVISOR-SEARCH-2025`: missing (not in pool)
- Expected `FIDELITY-III-2025#0`: missing (not in pool)
- Expected `UBS-NEXTGEN-2026#119, UBS-NEXTGEN-2026#13`: missing (not in pool)
- Retrieved: EDJ-10K-2025#22, SCHW-TR-2025Q3#12, MER-PR-web-advisor-development-program#2, UBS-NEXTGEN-2026#83, MS-TR-2026Q2#10, BAC-DECK-2026Q3#45, RJF-10K-2025#91, EDJ-10Q-2025Q3#69, SCHW-DECK-2026-investor-day#306, MER-PR-web-advisor-development-program#0, CFPB-MISINFO-2025#9, MS-SUPP-2026Q2#16, BAC-TR-2026Q3#19, RJF-TR-2026Q1#5, SCHW-10K-2025#496, MER-TRADE-2026-10-14-IN-01#0, MS-10K-2025#190, BAC-PR-2026-07-14-01#10, RJF-PR-web-affiliation-options#0, EDJ-TRADE-2026-11-12-IN-01#1

### Q21 - PASS

What do we know about the generational wealth transfer, and how are these five preparing for it?

- Theme wealth_transfer: no chunk on the theme for no firm (every named firm has one)
- `THEME:research`: hit CERULLI-GWT-2025#2, CERULLI-GWT-2025#13, UBS-NEXTGEN-2026#6, UBS-NEXTGEN-2026#12
- `MS:transcript`: hit MS-TR-2024Q4#50
- `SCHW:transcript`: hit SCHW-TR-2026Q3#11
- `EDJ:10-K`: hit EDJ-10K-2025#304, EDJ-10K-2025#56
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q2#63
- `RJF:transcript`: hit RJF-TR-2025Q4#45
- Retrieved: SCHW-DECK-2026Q3#24, BAC-PR-2026-01-14-01#12, RJF-TRADE-2026-11-06-IN-01#3, MS-DECK-2026-strategic-update#22, EDJ-10K-2025#304, SCHW-DECK-2026-investor-day#70, RJF-TR-2025Q4#45, MS-TR-2024Q4#50, EDJ-10K-2025#56, SCHW-TR-2026Q3#11, BAC-TR-2026Q2#63, RJF-PR-web-independent-ria-custody-services#2, MS-10Q-2025Q3#59, EDJ-10Q-2025Q3#72, SCHW-10Q-2026Q2#9, BAC-10Q-2025Q2#88, RJF-10Q-2025Q4#84, MS-10K-2025#206, SCHW-PR-2026-07-21-01#8, BAC-SUPP-2026Q1#45, RJF-10K-2025#26, MS-SUPP-2025Q4#49, EDJ-10Q-2025Q2#67, SCHW-TRADE-2026-10-29-WM-01#3, MER-TRADE-2026-11-16-AH-01#0, EDJ-TRADE-2026-11-12-IN-01#3, CERULLI-GWT-2025#2, CERULLI-GWT-2025#13, UBS-NEXTGEN-2026#6, UBS-NEXTGEN-2026#12

### Q22 - FAIL

Net new assets by quarter for each of the five, with each firm's own definition of the metric.

- `MS:supplement`: hit MS-SUPP-2025Q4#14
- `SCHW:monthly`: hit SCHW-MONTHLY-2026-01#8
- `SCHW:supplement`: not in corpus
- `EDJ:10-Q`: hit EDJ-10Q-2026Q2#60, EDJ-10Q-2025Q3#69, EDJ-10Q-2025Q2#86
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q1#44
- `RJF:supplement`: hit RJF-SUPP-2026Q2#9
- `MS:press`: hit MS-PR-2026-04-15-01#15
- `RJF:press`: hit RJF-PR-2026-01-28-01#20
- Expected `EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10K-2025#130`: found EDJ-10Q-2026Q2#60, EDJ-10K-2025#130
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14, MS-10Q-2026Q2#57, MS-10Q-2026Q1#48, MS-10Q-2025Q3#56, MS-10Q-2025Q2#56, MS-PR-2026-01-15-01#2`: missing (in pool, lost in select: MS-10Q-2026Q2#57)
- Expected `MS-SUPP-2026Q1#42, MS-10K-2025#166`: missing (not in pool)
- Expected `SCHW-PR-2026-01-21-01#2, SCHW-PR-2026-07-21-01#2, SCHW-DECK-2026Q3#7, SCHW-10Q-2026Q2#16, SCHW-10Q-2026Q1#16, SCHW-10Q-2025Q3#16, SCHW-10Q-2025Q2#16`: found SCHW-10Q-2026Q1#16
- Expected `SCHW-10K-2025#122, SCHW-10K-2025#119, SCHW-DECK-2026Q3#20`: found SCHW-DECK-2026Q3#20
- Expected `RJF-PR-2026-07-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-01-28-01#3, RJF-PR-2025-10-22-01#4, RJF-10Q-2026Q2#305, RJF-10Q-2026Q1#298, RJF-10Q-2025Q4#236, RJF-10Q-2025Q2#294`: missing (not in pool)
- Expected `RJF-10Q-2026Q2#306, RJF-SUPP-2026Q1#43`: missing (not in pool)
- Expected `BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#11`: missing (not in pool)
- **Misleading (must not come back):** MS-PR-2026-04-15-01#15
- Retrieved: EDJ-10Q-2026Q2#60, MS-DECK-2026-strategic-update#30, RJF-10Q-2026Q1#323, BAC-10K-2025#248, SCHW-PR-2026-10-15-01#1, EDJ-10K-2025#130, MS-10K-2025#165, RJF-TR-2025Q1#6, BAC-SUPP-2026Q1#44, SCHW-MONTHLY-2026-01#8, EDJ-10Q-2025Q3#69, MS-10Q-2026Q2#58, RJF-PR-2026-01-28-01#20, BAC-10Q-2026Q1#74, SCHW-10Q-2026Q1#16, EDJ-10K-2025#148, MS-SUPP-2025Q4#14, RJF-SUPP-2026Q2#9, BAC-TR-2026Q2#20, SCHW-DECK-2026Q3#20, EDJ-10Q-2025Q2#86, MS-PR-2026-04-15-01#15, RJF-10K-2025#224, BAC-PR-2026-04-15-01#11, SCHW-10K-2025#136, EDJ-10K-2025#127, MS-TR-2026Q3#22, RJF-10Q-2025Q4#256, BAC-DECK-2026Q3#31, SCHW-TR-2026Q1#3

### Q23 - PASS

Advisor headcount over the last eight quarters across the five.

- `MS:supplement`: hit MS-SUPP-2026Q3#17
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-Q`: hit EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q3#69
- `EDJ:10-K`: hit EDJ-10K-2025#202, EDJ-10K-2025#141, EDJ-10K-2025#130
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q3#53
- `RJF:supplement`: no hit
- `RJF:press`: hit RJF-PR-web-bank-and-credit-union-advisors#0
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#202, EDJ-10K-2025#141, EDJ-10K-2025#130
- Expected `EDJ-10Q-2025Q2`: found EDJ-10Q-2025Q2#64
- Expected `EDJ-10Q-2025Q3`: found EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q3#69
- Expected `EDJ-10Q-2026Q1`: missing (not in pool)
- Expected `EDJ-10Q-2026Q2`: missing (not in pool)
- Expected `MS-SUPP-2025Q4`: missing (not in pool)
- Expected `MS-SUPP-2026Q1`: missing (in pool, lost in select: MS-SUPP-2026Q1#15)
- Expected `MS-SUPP-2026Q2`: missing (in pool, lost in select: MS-SUPP-2026Q2#17)
- Expected `MS-SUPP-2026Q3`: found MS-SUPP-2026Q3#17
- Expected `BAC-10K-2025`: found BAC-10K-2025#247
- Expected `BAC-SUPP-2025Q4`: missing (in pool, lost in select: BAC-SUPP-2025Q4#56)
- Expected `BAC-SUPP-2026Q1`: missing (not in pool)
- Expected `BAC-SUPP-2026Q2`: missing (in pool, lost in select: BAC-SUPP-2026Q2#55)
- Expected `BAC-SUPP-2026Q3`: found BAC-SUPP-2026Q3#53
- Expected `RJF-10K-2025`: found RJF-10K-2025#228, RJF-10K-2025#12
- Expected `RJF-SUPP-2025Q3`: missing (in pool, lost in select: RJF-SUPP-2025Q3#14)
- Expected `RJF-SUPP-2025Q4`: missing (not in pool)
- Expected `RJF-SUPP-2026Q1`: missing (not in pool)
- Expected `RJF-SUPP-2026Q2`: missing (not in pool)
- Expected `SCHW-10K-2025`: found SCHW-10K-2025#197
- Retrieved: RJF-TR-2025Q3#8, BAC-TR-2026Q2#63, EDJ-10Q-2025Q3#67, SCHW-TR-2026Q2#33, MS-TR-2026Q1#23, RJF-10K-2025#228, MER-PR-web-becoming-a-merrill-lynch-advisor#4, EDJ-10K-2025#202, SCHW-10Q-2026Q2#25, MS-SUPP-2026Q3#17, RJF-PR-web-bank-and-credit-union-advisors#0, BAC-SUPP-2026Q3#53, EDJ-10Q-2025Q2#64, SCHW-DECK-2026-investor-day#58, MS-DECK-2026-strategic-update#13, RJF-DECK-2025-investor-day#83, BAC-10Q-2025Q3#95, EDJ-10K-2025#141, SCHW-10K-2025#197, MS-10Q-2026Q1#58, RJF-TR-2025Q4#25, BAC-DECK-2025-investor-day#9, EDJ-10Q-2025Q3#69, SCHW-PR-2026-10-15-01#36, MS-PR-2026-10-14-01#4, RJF-10K-2025#12, BAC-10K-2025#247, EDJ-10K-2025#130, SCHW-MONTHLY-2026-05#5, MS-10K-2025#44

### Q24 - PASS

Client assets per advisor across the five -- and is that comparison even valid?

- `MS:supplement`: hit MS-SUPP-2026Q3#38
- `SCHW:10-K`: hit SCHW-10K-2025#124
- `EDJ:10-K`: hit EDJ-10K-2025#131, EDJ-10K-2025#58, EDJ-10K-2025#20
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q2#56
- `RJF:supplement`: no hit
- Expected `EDJ-10K-2025#130`: missing (not in pool)
- Expected `RJF-10K-2025#227`: missing (in pool, lost in select: RJF-10K-2025#227)
- Expected `RJF-10K-2025#228`: missing (not in pool)
- Expected `MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38`: found MS-SUPP-2026Q3#38
- Retrieved: SCHW-DECK-2026Q2#20, BAC-10K-2025#249, RJF-TR-2025Q3#7, EDJ-10Q-2026Q1#52, MS-DECK-2026-strategic-update#5, SCHW-PR-2026-10-15-01#41, MER-PR-web-becoming-a-merrill-lynch-advisor#4, RJF-10K-2025#9, EDJ-10K-2025#131, MS-TR-2026Q3#18, SCHW-10K-2025#124, BAC-TR-2026Q3#19, RJF-10Q-2026Q1#323, EDJ-10Q-2025Q2#67, MS-10Q-2026Q1#51, SCHW-MONTHLY-2026-04#6, BAC-DECK-2025-investor-day#9, RJF-DECK-2025-investor-day#30, EDJ-10K-2025#58, MS-10K-2025#167, SCHW-10Q-2026Q1#9, BAC-10Q-2026Q1#75, RJF-PR-2026-07-22-01#98, EDJ-10Q-2026Q1#51, MS-SUPP-2026Q3#38, SCHW-TR-2026Q3#4, BAC-SUPP-2026Q2#56, RJF-TR-2025Q2#6, EDJ-10K-2025#20, MS-PR-2026-01-15-01#0

### Q25 - PASS

What has each of the five actually disclosed about advisor compensation structures?

- `MS:10-K`: hit MS-10K-2025#193
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-K`: hit EDJ-10K-2025#141, EDJ-10K-2025#314, EDJ-10K-2025#30
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: hit RJF-10K-2025#29
- `MS:DEF 14A`: not in corpus
- `SCHW:DEF 14A`: not in corpus
- `BAC:DEF 14A`: not in corpus
- `RJF:DEF 14A`: not in corpus
- `MS:adv`: hit MS-ADV-2026#239
- `EDJ:adv`: hit EDJ-ADV-2026#68
- `RJF:adv`: hit RJF-ADV-2026#108
- Expected `RJF-10K-2025#10, RJF-10K-2025#11`: missing (in pool, lost in select: RJF-10K-2025#10)
- Expected `EDJ-10K-2025#30, EDJ-10K-2025#264`: found EDJ-10K-2025#30
- Expected `MS-10K-2025#153`: missing (in pool, lost in select: MS-10K-2025#153)
- Expected `RJF-PR-web-affiliation-options#1`: missing (not in pool)
- Expected `SCHW-10Q-2026Q2#25`: missing (not in pool)
- Retrieved: SCHW-ADV-2026#45, RJF-ADV-2026#108, MER-ADV-2026#400, EDJ-10K-2025#141, MS-ADV-2026#239, SCHW-DECK-2026-investor-day#169, RJF-TR-2025Q3#20, MER-PR-web-becoming-a-merrill-lynch-advisor#4, EDJ-10Q-2026Q1#60, MS-10K-2025#193, SCHW-10K-2025#197, RJF-10Q-2026Q1#239, MER-ADV-2026#474, EDJ-ADV-2026#68, MS-10Q-2026Q2#6, SCHW-TR-2026Q1#48, RJF-10K-2025#29, MER-PR-web-becoming-a-merrill-lynch-advisor#3, EDJ-10K-2025#314, MS-TR-2026Q3#58, SCHW-10Q-2025Q2#155, RJF-DECK-2025-investor-day#92, MER-ADV-2026#411, EDJ-10Q-2025Q2#78, MS-DECK-2026-strategic-update#7, SCHW-PR-2026-10-15-01#31, RJF-PR-2026-04-22-01#95, MER-TRADE-2026-09-11-WM-01#1, EDJ-10K-2025#30, MS-SUPP-2026Q1#25

### Q26 - PASS

What's new on Raymond James in the last 90 days?

- `RJF:*`: hit RJF-TRADE-2026-11-12-WM-01#0, RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-05-WM-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-27-WM-01#0, RJF-TRADE-2026-10-23-WM-01#1, RJF-TRADE-2026-10-19-IN-01#0, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-24-WM-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-28-IN-01#1, RJF-TRADE-2026-08-26-IN-01#2, RJF-TRADE-2026-08-21-IN-01#1
- Window: 2026-08-19 to 2026-11-17
- Retrieved: RJF-TRADE-2026-11-12-WM-01#0, RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-05-WM-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-27-WM-01#0, RJF-TRADE-2026-10-23-WM-01#1, RJF-TRADE-2026-10-19-IN-01#0, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-24-WM-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-28-IN-01#1, RJF-TRADE-2026-08-26-IN-01#2, RJF-TRADE-2026-08-21-IN-01#1

### Q27 - PASS

What has changed at Merrill since the start of the year?

- `MER:*`: hit MER-TRADE-2026-11-16-AH-01#1, BAC-DECK-2026Q3#31, BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#12, MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-09-29-RB-01#5, MER-PR-2026-09-15-01#0, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-SUPP-2026Q1#45, BAC-DECK-2026Q1#27, BAC-TR-2026Q1#26, BAC-10K-2025#247, BAC-10K-2025#246, BAC-10K-2025#248, BAC-SUPP-2025Q4#56
- `BAC:*#GWIM`: hit BAC-DECK-2026Q3#31, BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#12, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-SUPP-2026Q1#45, BAC-DECK-2026Q1#27, BAC-TR-2026Q1#26, BAC-10K-2025#247, BAC-10K-2025#246, BAC-10K-2025#248, BAC-SUPP-2025Q4#56
- Expected `MER-PR-2026-09-15-01`: found MER-PR-2026-09-15-01#0
- Expected `MER-PR-web-advisor-development-program`: missing (not in pool)
- Expected `MER-PR-web-becoming-a-merrill-lynch-advisor`: missing (not in pool)
- Expected `BAC-TR-2026Q1`: found BAC-TR-2026Q1#26
- Expected `BAC-TR-2026Q2`: found BAC-TR-2026Q2#20
- Expected `BAC-TR-2026Q3`: found BAC-TR-2026Q3#19
- Expected `BAC-SUPP-2026Q1`: found BAC-SUPP-2026Q1#45
- Expected `BAC-SUPP-2026Q2`: missing (in pool, lost in select: BAC-SUPP-2026Q2#55)
- Expected `BAC-SUPP-2026Q3`: missing (in pool, lost in select: BAC-SUPP-2026Q3#53)
- Retrieved: MER-TRADE-2026-11-16-AH-01#1, BAC-DECK-2026Q3#31, BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#12, MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-09-29-RB-01#5, MER-PR-2026-09-15-01#0, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-SUPP-2026Q1#45, BAC-DECK-2026Q1#27, BAC-TR-2026Q1#26, BAC-10K-2025#247, BAC-10K-2025#246, BAC-10K-2025#248, BAC-SUPP-2025Q4#56

### Q28 - PASS

What is Edward Jones's advisor attrition rate compared to Merrill's?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `EDJ:10-K`: hit EDJ-10K-2025#71, EDJ-10K-2025#19, EDJ-10K-2025#141
- `BAC:supplement#GWIM`: no hit
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- Expected `EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q3#68, EDJ-10Q-2025Q3#70`: found EDJ-10Q-2025Q3#70, EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q3#68
- Expected `EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q3#69`: found EDJ-10Q-2025Q2#66
- Expected `BAC-TR-2026Q2#63, BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: found BAC-TR-2026Q2#63
- Expected `EDJ-10K-2025#130, EDJ-10Q-2026Q2#60`: missing (not in pool)
- Retrieved: BAC-TR-2026Q2#63, EDJ-10K-2025#71, BAC-TR-2026Q3#19, EDJ-10K-2025#19, MER-PR-web-advisor-development-program#1, EDJ-10Q-2026Q2#28, BAC-DECK-2025-investor-day#9, EDJ-10K-2025#141, BAC-10K-2025#246, EDJ-10Q-2025Q3#70, BAC-10Q-2025Q3#90, EDJ-10Q-2025Q2#64, BAC-TR-2025Q4#106, EDJ-10Q-2025Q3#68, MER-PR-web-becoming-a-merrill-lynch-advisor#1, EDJ-10Q-2025Q2#66, KITCES-WELLBEING-2023#17, KITCES-WELLBEING-2023#55, MCK-SIGNAL-SELLOFF-2026#9, MCK-ADVISOR-SHORTAGE-2025#7

### Q29 - PASS

What does Morgan Stanley pay its financial advisors?

- `MS:10-K#Wealth Management`: hit MS-10K-2025#170
- `MS:trade`: hit MS-TRADE-2026-10-26-IN-01#4
- Expected `MS-10K-2025#153`: missing (in pool, lost in select: MS-10K-2025#153)
- Expected `MS-10K-2025#128, MS-10K-2025#170`: found MS-10K-2025#170, MS-10K-2025#128
- Retrieved: MS-TR-2026Q3#32, MS-10Q-2026Q2#20, MS-PR-2026-01-15-01#13, MS-10K-2025#170, MS-TR-2026Q2#41, MS-10Q-2026Q1#207, MS-PR-2026-10-14-01#8, MS-10K-2025#128, MS-TR-2025Q4#10, MS-10Q-2025Q3#64, MS-PR-2026-07-15-01#8, MS-10K-2025#417, MS-TR-2025Q1#8, MS-10Q-2025Q2#20, MS-PR-2026-04-15-01#8, MS-TR-2024Q4#10, MS-10Q-2026Q2#64, MS-TR-2025Q4#22, MS-10Q-2025Q3#19, MS-TRADE-2026-10-26-IN-01#4

### Q30 - PASS

What is Merrill's standalone profitability?

- `BAC:10-K#GWIM`: hit BAC-10K-2025#246, BAC-10K-2025#247
- Expected `BAC-PR-2026-01-14-01#12`: missing (not in pool)
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246, BAC-10K-2025#247
- Retrieved: BAC-TR-2025Q3#26, BAC-DECK-2025-investor-day#10, BAC-PR-2026-07-14-01#10, BAC-10K-2025#246, BAC-10Q-2026Q2#89, BAC-SUPP-2026Q3#51, BAC-TR-2026Q2#21, BAC-DECK-2026Q3#30, BAC-PR-2026-04-15-01#10, BAC-10K-2025#247, BAC-10Q-2025Q3#93, BAC-SUPP-2026Q2#52, BAC-TR-2026Q1#26, BAC-DECK-2026Q2#19, BAC-PR-2026-01-14-01#11, BAC-10Q-2025Q2#93, BAC-SUPP-2026Q1#43, BAC-TR-2025Q1#28, BAC-DECK-2026Q1#26, MER-TRADE-2026-10-02-IN-01#1

