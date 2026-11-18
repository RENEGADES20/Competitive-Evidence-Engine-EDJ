# Eval run corpus-2026-11-17-20261118-011512

Snapshot `corpus-2026-11-17` | commit `635c542` | k=by question | min coverage 0.5 | as of 2026-11-17 | mode mock | 0 real calls

**PASS 29 | FAIL 1 | NOT_EVALUATED 0 | INVALID_OUTPUT 0** (baseline `evals/baselines/corpus-2026-11-17/report.json`)

**Tier-1 recall**: documents 0.788, passages 0.607 (mean over the 17 of 18 tier-1 questions with an answer key; the rest n/a until #56)  
**Refusal accuracy**: gap questions (Q24, Q25, Q28, Q29, Q30) 5/5; all questions with a key 19/19

Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the corpus; PASS when coverage of the available patterns >= min coverage.

Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window.

| Q | Tier | Use case | Expected | Firms (mode) | k | Hits | Chars | Coverage | Recall docs | Passages | Refusal | Forbidden | Status | Change |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 24182 | 4/4 | 8/9 | 4/8 | ok | 0 | PASS | IMPROVED |
| Q2 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 22045 | 4/4 | 6/9 | 6/9 | ok | 0 | PASS | IMPROVED |
| Q3 | 1 | entity_brief | answer | SCHW (entity) | 20 | 20 | 21817 | 3/3 | 4/6 | 4/6 | ok | 0 | PASS | IMPROVED |
| Q4 (trap) | 1 | entity_brief | answer | MER (entity) | 20 | 20 | 20700 | 4/4 | 4/5 | 5/7 | ok | 0 | PASS | IMPROVED |
| Q5 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 20740 | 4/4 | 5/6 | 5/6 | ok | 0 | PASS | IMPROVED |
| Q6 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 20905 | 3/3 | 6/6 | 6/6 | ok | 0 | PASS | IMPROVED |
| Q7 | 2 | head_to_head | answer | MS, MER, RJF (entity+theme) | 20 | 20 | 21041 | 8/9 | - | - | - | 0 | PASS | UNCHANGED |
| Q8 | 2 | head_to_head | answer | SCHW, RJF (entity) | 20 | 20 | 22305 | 4/4 | - | - | - | 0 | PASS | UNCHANGED |
| Q9 | 3 | head_to_head | answer | MS, MER (entity) | 20 | 20 | 24184 | 5/6 | - | - | - | 0 | PASS | UNCHANGED |
| Q10 | 3 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 32804 | 5/5 | - | - | - | 0 | PASS | UNCHANGED |
| Q11 | 1 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 38174 | 8/8 | 8/8 | 2/10 | ok | 0 | PASS | IMPROVED |
| Q12 | 3 | mechanism | answer_with_boundary | SCHW, EDJ (entity+theme) | 20 | 20 | 24302 | 4/4 | - | - | - | 0 | PASS | UNCHANGED |
| Q13 | 1 | mechanism | answer | MS (entity) | 20 | 20 | 25821 | 3/3 | 6/6 | 6/6 | ok | 0 | PASS | IMPROVED |
| Q14 | 3 | mechanism | answer | RJF (entity) | 20 | 20 | 23082 | 3/3 | - | - | - | 0 | PASS | UNCHANGED |
| Q15 | 3 | mechanism | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 33893 | 4/5 | - | - | - | 0 | PASS | IMPROVED |
| Q16 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 22645 | 3/3 | - | - | - | 0 | PASS | UNCHANGED |
| Q17 | 1 | theme_scan | answer | none (theme) | 20 | 20 | 22485 | 5/10 | 6/9 | 6/9 | ok | 0 | PASS | IMPROVED |
| Q18 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 22803 | 6/6 | - | - | - | 0 | PASS | UNCHANGED |
| Q19 | 3 | segment_evidence | answer_with_boundary | EDJ (entity+theme) | 28 | 20 | 24271 | 1/5 | - | - | - | 0 | FAIL | UNCHANGED |
| Q20 | 1 | segment_evidence | answer | none (theme) | 20 | 20 | 23716 | 1/1 | 3/7 | 3/7 | ok | 0 | PASS | IMPROVED |
| Q21 | 2 | segment_evidence | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 32083 | 6/6 | - | - | - | 0 | PASS | UNCHANGED |
| Q22 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 37049 | 7/7 | 14/33 | 3/8 | ok | 0 | PASS | IMPROVED |
| Q23 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 35727 | 4/7 | 7/20 | 7/20 | ok | 0 | PASS | IMPROVED |
| Q24 | 3 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 34414 | 5/5 | 3/5 | 0/4 | ok | 0 | PASS | UNCHANGED |
| Q25 | 1 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 35900 | 8/8 | 4/4 | 0/4 | ok | 0 | PASS | IMPROVED |
| Q26 | 1 | recency | answer | RJF (entity) | 20 | 15 | 19723 | 1/1 | - | - | ok | 0 | PASS | UNCHANGED |
| Q27 (trap) | 1 | recency | answer | MER (entity) | 20 | 20 | 25592 | 2/2 | 6/9 | 6/9 | ok | 0 | PASS | IMPROVED |
| Q28 | 1 | honest_miss | gap_with_adjacent | EDJ, MER (entity+theme) | 20 | 20 | 23823 | 2/3 | 6/6 | 3/4 | ok | 0 | PASS | IMPROVED |
| Q29 | 1 | honest_miss | gap_with_adjacent | MS (entity) | 20 | 20 | 21418 | 2/2 | 1/1 | 2/2 | ok | 0 | PASS | UNCHANGED |
| Q30 (trap) | 1 | honest_miss | gap_with_adjacent | MER (entity) | 20 | 20 | 25088 | 1/1 | 2/2 | 1/2 | ok | 0 | PASS | IMPROVED |

## Per question

### Q1 - PASS

What is Morgan Stanley's strategy to increase their net new assets?

- `MS:transcript`: hit MS-TR-2026Q3#15, MS-TR-2026Q2#16, MS-TR-2025Q4#19, MS-TR-2025Q3#45
- `MS:10-K#Wealth Management`: hit MS-10K-2025#165
- `MS:deck`: hit MS-DECK-2026-strategic-update#30, MS-DECK-2026-strategic-update#31, MS-DECK-2026-strategic-update#8
- `MS:supplement`: hit MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14
- Expected `MS-TR-2026Q2#3`: missing
- Expected `MS-TR-2026Q2#14, MS-TR-2026Q2#16`: found MS-TR-2026Q2#16
- Expected `MS-TR-2026Q3#3, MS-TR-2026Q3#12, MS-TR-2026Q3#13`: missing
- Expected `MS-TR-2026Q1#3, MS-TR-2026Q1#9, MS-TR-2026Q1#10, MS-TR-2026Q1#11`: missing
- Expected `MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5`: found MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5
- Expected `MS-10K-2025#125`: missing
- Expected `MS-10K-2025#127, MS-10K-2025#164, MS-10K-2025#166`: found MS-10K-2025#127
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14`: found MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14
- Retrieved: MS-TR-2026Q3#15, MS-10Q-2026Q2#58, MS-DECK-2026-strategic-update#30, MS-10K-2025#165, MS-PR-2026-10-14-01#5, MS-SUPP-2026Q3#16, MS-TR-2026Q2#16, MS-10Q-2026Q1#18, MS-DECK-2026-strategic-update#31, MS-10K-2025#127, MS-PR-2026-07-15-01#5, MS-SUPP-2026Q2#16, MS-TR-2025Q4#19, MS-10Q-2025Q3#57, MS-DECK-2026-strategic-update#8, MS-PR-2026-04-15-01#2, MS-SUPP-2026Q1#14, MS-TR-2025Q3#45, MS-10Q-2025Q2#18, MS-TRADE-2026-10-14-WM-01#0

### Q2 - PASS

How is Raymond James positioning itself to recruit advisors away from the wirehouses?

- `RJF:transcript`: hit RJF-TR-2026Q1#54, RJF-TR-2026Q2#6, RJF-TR-2025Q4#44, RJF-TR-2025Q3#20
- `RJF:10-K`: hit RJF-10K-2025#91, RJF-10K-2025#10, RJF-10K-2025#175
- `RJF:press`: hit RJF-PR-2026-04-22-01#1, RJF-PR-web-affiliation-options#0, RJF-PR-web-advisor-select#0, RJF-PR-web-bank-and-credit-union-advisors#0
- `RJF:trade`: hit RJF-TRADE-2026-11-04-IN-01#2
- Expected `RJF-10K-2025`: found RJF-10K-2025#91, RJF-10K-2025#10, RJF-10K-2025#175
- Expected `RJF-TR-2025Q4`: found RJF-TR-2025Q4#44
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#54
- Expected `RJF-TR-2026Q2`: found RJF-TR-2026Q2#6
- Expected `RJF-PR-2026-04-22-01`: found RJF-PR-2026-04-22-01#1
- Expected `RJF-PR-2026-07-22-01`: missing
- Expected `RJF-PR-web-affiliation-options`: found RJF-PR-web-affiliation-options#0
- Expected `RJF-PR-web-traditional-employee-advisor`: missing
- Expected `RJF-PR-web-independent-advisor`: missing
- Retrieved: RJF-TR-2026Q1#54, RJF-10K-2025#91, RJF-PR-2026-04-22-01#1, RJF-10Q-2026Q2#252, RJF-DECK-2025-investor-day#49, RJF-SUPP-2026Q2#45, RJF-TR-2026Q2#6, RJF-10K-2025#10, RJF-PR-web-affiliation-options#0, RJF-10Q-2026Q1#239, RJF-DECK-2025-investor-day#40, RJF-SUPP-2026Q1#44, RJF-TR-2025Q4#44, RJF-10K-2025#175, RJF-PR-web-advisor-select#0, RJF-10Q-2025Q4#199, RJF-TR-2025Q3#20, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-SUPP-2025Q4#12, RJF-TRADE-2026-11-04-IN-01#2

### Q3 - PASS

What is Schwab's strategy for its RIA custody business?

- `SCHW:transcript`: hit SCHW-TR-2026Q3#4, SCHW-TR-2025Q1#9, SCHW-TR-2025Q3#13
- `SCHW:10-K#Advisor Services`: hit SCHW-10K-2025#26
- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#305, SCHW-DECK-2026Q3#11, SCHW-DECK-2026Q2#14
- Expected `SCHW-10K-2025`: found SCHW-10K-2025#11, SCHW-10K-2025#26, SCHW-10K-2025#13
- Expected `SCHW-TR-2026Q1`: missing
- Expected `SCHW-TR-2026Q2`: missing
- Expected `SCHW-TR-2026Q3`: found SCHW-TR-2026Q3#4
- Expected `SCHW-DECK-2026Q3`: found SCHW-DECK-2026Q3#11
- Expected `SCHW-DECK-2026-investor-day`: found SCHW-DECK-2026-investor-day#305
- Retrieved: SCHW-10K-2025#11, SCHW-10Q-2026Q2#342, SCHW-TR-2026Q3#4, SCHW-DECK-2026-investor-day#305, SCHW-PR-2026-10-15-01#10, SCHW-MONTHLY-2026-05#2, SCHW-10K-2025#26, SCHW-10Q-2026Q1#275, SCHW-TR-2025Q1#9, SCHW-DECK-2026Q3#11, SCHW-PR-2026-07-21-01#2, SCHW-MONTHLY-2026-02#4, SCHW-10K-2025#13, SCHW-10Q-2025Q3#170, SCHW-TR-2025Q3#13, SCHW-DECK-2026Q2#14, SCHW-PR-2026-04-16-01#7, SCHW-MONTHLY-2026-02#5, SCHW-10Q-2025Q2#6, SCHW-TRADE-2026-10-28-WM-01#0

### Q4 - PASS

What is Merrill's advisor growth strategy, and how has it changed?

- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#19, BAC-TR-2026Q2#20, BAC-TR-2025Q4#106, BAC-TR-2025Q2#34, BAC-TR-2025Q1#28, BAC-TR-2026Q1#26, BAC-TR-2025Q2#35, BAC-TR-2026Q2#21, BAC-TR-2026Q2#63
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `MER:press`: hit MER-PR-web-becoming-a-merrill-lynch-advisor#0, MER-PR-web-advisor-development-program#0, MER-PR-2026-09-15-01#2, MER-PR-2026-09-15-01#0, MER-PR-2026-09-15-01#3
- `MER:trade`: hit MER-TRADE-2026-11-03-WM-01#0, MER-TRADE-2026-11-12-IN-01#0, MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-10-14-IN-02#2
- Expected `BAC-TR-2026Q1#25, BAC-TR-2026Q1#26`: found BAC-TR-2026Q1#26
- Expected `BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: missing
- Expected `BAC-TR-2026Q2#20, BAC-TR-2026Q2#21, BAC-TR-2026Q2#22`: found BAC-TR-2026Q2#20, BAC-TR-2026Q2#21
- Expected `BAC-TR-2026Q2#63`: found BAC-TR-2026Q2#63
- Expected `BAC-TR-2026Q3#19`: found BAC-TR-2026Q3#19
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246
- Expected `BAC-10Q-2026Q2#88, BAC-10Q-2026Q2#89, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91`: missing
- Retrieved: BAC-DECK-2025-investor-day#8, MER-PR-web-becoming-a-merrill-lynch-advisor#0, BAC-10K-2025#246, BAC-TR-2026Q3#19, MER-PR-web-advisor-development-program#0, BAC-TR-2026Q2#20, MER-PR-2026-09-15-01#2, BAC-TR-2025Q4#106, MER-PR-2026-09-15-01#0, BAC-TR-2025Q2#34, MER-PR-2026-09-15-01#3, BAC-TR-2025Q1#28, BAC-TR-2026Q1#26, BAC-TR-2025Q2#35, BAC-TR-2026Q2#21, BAC-TR-2026Q2#63, MER-TRADE-2026-11-03-WM-01#0, MER-TRADE-2026-11-12-IN-01#0, MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-10-14-IN-02#2

### Q5 - PASS

Where is Morgan Stanley investing in technology for its advisors?

- `MS:transcript`: hit MS-TR-2026Q3#16, MS-TR-2026Q1#44, MS-TR-2025Q4#8, MS-TR-2025Q3#8, MS-TR-2025Q1#54, MS-TR-2026Q3#8, MS-TR-2025Q4#65, MS-TR-2025Q3#37, MS-TR-2026Q1#6, MS-TR-2026Q3#35
- `MS:10-K`: hit MS-10K-2025#25, MS-10K-2025#76, MS-10K-2025#109
- `MS:deck`: hit MS-DECK-2026-strategic-update#10
- `MS:trade`: hit MS-TRADE-2026-11-15-AH-01#0
- Expected `MS-10K-2025`: found MS-10K-2025#25, MS-10K-2025#76, MS-10K-2025#109
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#8, MS-TR-2025Q4#65
- Expected `MS-TR-2026Q1`: found MS-TR-2026Q1#44, MS-TR-2026Q1#6
- Expected `MS-TR-2026Q2`: missing
- Expected `MS-TR-2026Q3`: found MS-TR-2026Q3#16, MS-TR-2026Q3#8, MS-TR-2026Q3#35
- Expected `MS-DECK-2026-strategic-update`: found MS-DECK-2026-strategic-update#10
- Retrieved: MS-TR-2026Q3#16, MS-10K-2025#25, MS-10Q-2026Q2#524, MS-PR-2026-10-14-01#5, MS-TR-2026Q1#44, MS-10K-2025#76, MS-10Q-2025Q3#63, MS-DECK-2026-strategic-update#10, MS-TR-2025Q4#8, MS-10K-2025#109, MS-10Q-2025Q3#64, MS-TR-2025Q3#8, MS-10Q-2026Q2#20, MS-TR-2025Q1#54, MS-TR-2026Q3#8, MS-TR-2025Q4#65, MS-TR-2025Q3#37, MS-TR-2026Q1#6, MS-TR-2026Q3#35, MS-TRADE-2026-11-15-AH-01#0

### Q6 - PASS

What has Raymond James said about its affiliation models, and has the mix shifted?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q1#45, RJF-TR-2026Q1#46, RJF-TR-2024Q3#66, RJF-TR-2026Q2#31, RJF-TR-2025Q4#50, RJF-TR-2025Q2#21
- `RJF:press`: hit RJF-PR-web-independent-advisor#1, RJF-PR-2026-04-22-01#1, RJF-PR-web-affiliation-options#0, RJF-PR-web-advisor-select#0, RJF-PR-2026-01-28-01#6
- Expected `RJF-10K-2025`: found RJF-10K-2025#462, RJF-10K-2025#10
- Expected `RJF-10Q-2026Q2`: found RJF-10Q-2026Q2#251
- Expected `RJF-TR-2025Q2`: found RJF-TR-2025Q2#21
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#45, RJF-TR-2026Q1#46
- Expected `RJF-TR-2026Q2`: found RJF-TR-2026Q2#31
- Expected `RJF-PR-web-affiliation-options`: found RJF-PR-web-affiliation-options#0
- Retrieved: RJF-TR-2026Q1#45, RJF-TR-2026Q1#46, RJF-PR-web-independent-advisor#1, RJF-10K-2025#462, RJF-DECK-2025-investor-day#49, RJF-10Q-2026Q2#251, RJF-TR-2024Q3#66, RJF-PR-2026-04-22-01#1, RJF-10K-2025#10, RJF-DECK-2025-investor-day#55, RJF-TR-2026Q2#31, RJF-PR-web-affiliation-options#0, RJF-10Q-2026Q1#267, RJF-TR-2025Q4#50, RJF-PR-web-advisor-select#0, RJF-10Q-2025Q4#259, RJF-TR-2025Q2#21, RJF-PR-2026-01-28-01#6, RJF-10Q-2025Q2#391, RJF-TRADE-2026-10-29-WM-01#0

### Q7 - PASS

How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `MS:transcript`: hit MS-TR-2024Q4#93, MS-TR-2026Q1#24, MS-TR-2026Q3#23
- `MS:10-K`: hit MS-10K-2025#51
- `BAC:transcript#GWIM`: hit BAC-TR-2025Q1#28
- `BAC:10-K#GWIM`: no hit
- `RJF:transcript`: hit RJF-TR-2025Q3#8
- `RJF:10-K`: hit RJF-10K-2025#90
- `MS:trade`: hit MS-TRADE-2026-10-26-IN-01#3
- `MER:trade`: hit MER-TRADE-2026-11-16-AH-01#1
- `RJF:trade`: hit RJF-TRADE-2026-11-06-IN-01#3
- Retrieved: MS-TR-2024Q4#93, RJF-TR-2025Q3#8, MER-PR-web-advisor-development-program#0, MS-10K-2025#51, BAC-TR-2025Q1#28, MS-TR-2026Q1#24, RJF-10K-2025#90, MER-PR-web-becoming-a-merrill-lynch-advisor#3, MS-10Q-2026Q2#144, RJF-PR-2026-04-22-01#1, BAC-DECK-2025-investor-day#8, RJF-10Q-2026Q2#316, MS-TR-2026Q3#23, MS-TRADE-2026-10-26-IN-01#3, RJF-TRADE-2026-11-06-IN-01#3, MER-TRADE-2026-11-16-AH-01#1, MCK-ADVISOR-SHORTAGE-2025#30, MCK-ADVISOR-SHORTAGE-2025#12, KITCES-WELLBEING-2023#58, KITCES-WELLBEING-2023#40

### Q8 - PASS

Compare how Schwab and Raymond James describe their value proposition to independent advisors.

- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#306, SCHW-DECK-2026Q3#12
- `SCHW:10-K`: hit SCHW-10K-2025#117
- `RJF:deck`: hit RJF-DECK-2025-investor-day#38
- `RJF:10-K`: hit RJF-10K-2025#23, RJF-10K-2025#24
- Retrieved: SCHW-TR-2026Q1#49, RJF-PR-web-independent-advisor#0, SCHW-10K-2025#117, RJF-10K-2025#23, SCHW-DECK-2026-investor-day#306, RJF-TR-2025Q4#50, SCHW-PR-2026-10-15-01#1, RJF-DECK-2025-investor-day#38, SCHW-MONTHLY-2026-08#2, RJF-10Q-2025Q4#171, SCHW-10Q-2026Q2#7, RJF-PR-web-bank-and-credit-union-advisors#3, SCHW-TR-2026Q3#10, RJF-10K-2025#24, RJF-TR-2026Q2#7, SCHW-DECK-2026Q3#12, SCHW-PR-2026-07-21-01#1, RJF-10Q-2025Q2#201, SCHW-TRADE-2026-10-29-WM-01#0, RJF-TRADE-2026-11-06-IN-01#2

### Q9 - PASS

How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

- `MS:10-K`: hit MS-10K-2025#190
- `MS:transcript`: hit MS-TR-2026Q3#33, MS-TR-2026Q2#60
- `MS:deck`: hit MS-DECK-2026-strategic-update#34
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `BAC:transcript#GWIM`: no hit
- `BAC:deck#GWIM`: hit BAC-DECK-2025-investor-day#12
- Retrieved: BAC-10K-2025#246, MS-10K-2025#190, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MS-10Q-2026Q2#186, BAC-DECK-2025-investor-day#12, MS-TR-2026Q3#33, MS-PR-2026-10-14-01#8, BAC-10Q-2026Q2#88, MS-SUPP-2026Q3#53, MER-PR-web-advisor-development-program#0, MS-DECK-2026-strategic-update#34, BAC-10Q-2025Q3#94, BAC-PR-2026-04-15-01#10, MS-10Q-2026Q1#208, BAC-10Q-2026Q1#71, MS-TR-2026Q2#60, BAC-PR-2026-01-14-01#12, MS-PR-2026-07-15-01#8, MER-TRADE-2026-09-08-WM-01#0, MS-TRADE-2026-10-01-IN-01#0

### Q10 - PASS

Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

- Theme mass_affluent: no chunk on the theme for EDJ
- `MS:transcript`: hit MS-TR-2025Q3#15, MS-TR-2026Q2#28
- `SCHW:transcript`: hit SCHW-TR-2025Q1#69
- `EDJ:10-K`: hit EDJ-10K-2025#0, EDJ-10K-2025#10
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q2#20
- `RJF:transcript`: hit RJF-TR-2025Q1#11
- Retrieved: MS-TRADE-2026-10-21-IN-01#3, BAC-DECK-2025-investor-day#12, RJF-DECK-2025-investor-day#129, SCHW-DECK-2026Q2#16, EDJ-10K-2025#0, MS-TR-2025Q3#15, BAC-DECK-2025-investor-day#8, RJF-TR-2025Q1#11, SCHW-TR-2025Q1#69, EDJ-10Q-2026Q2#0, MS-10K-2025#144, BAC-TR-2026Q2#20, RJF-10K-2025#33, EDJ-10K-2025#10, MS-10Q-2026Q2#0, BAC-DECK-2025-investor-day#9, RJF-10Q-2026Q2#0, SCHW-10K-2025#213, EDJ-10Q-2026Q1#24, MS-PR-2026-10-14-01#8, MER-PR-web-advisor-development-program#1, SCHW-10Q-2026Q2#206, MS-TR-2026Q2#28, MER-TRADE-2026-09-29-RB-01#4, RJF-PR-2026-07-22-01#2, RJF-TRADE-2026-09-29-IN-01#3, SCHW-TRADE-2026-10-29-WM-01#0, EDJ-TRADE-2026-08-18-IN-01#2, CERULLI-MASS-AFFLUENT-2026#0, CERULLI-MASS-AFFLUENT-2026#1

### Q11 - PASS

How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

- `MS:10-K`: hit MS-10K-2025#44
- `MS:supplement`: hit MS-SUPP-2026Q3#25
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-K`: hit EDJ-10K-2025#130, EDJ-10K-2025#41, EDJ-10K-2025#320
- `BAC:10-K#GWIM`: hit BAC-10K-2025#249
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q3#52
- `RJF:10-K`: hit RJF-10K-2025#12
- `RJF:supplement`: hit RJF-SUPP-2026Q2#25
- Expected `EDJ-10K-2025#130`: found EDJ-10K-2025#130
- Expected `EDJ-10K-2025#131, EDJ-10K-2025#148`: missing
- Expected `EDJ-10Q-2026Q2#60`: found EDJ-10Q-2026Q2#60
- Expected `EDJ-10K-2025#29`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `RJF-10K-2025#24`: missing
- Expected `MS-10K-2025#167, MS-SUPP-2026Q3#38`: missing
- Expected `BAC-10K-2025#246`: missing
- Expected `SCHW-10K-2025#18, SCHW-TR-2026Q1#4, SCHW-TR-2026Q1#5`: missing
- Retrieved: EDJ-10Q-2026Q2#60, RJF-10K-2025#12, MS-DECK-2026-strategic-update#31, SCHW-10Q-2026Q2#71, BAC-TR-2026Q3#19, EDJ-10K-2025#130, RJF-TR-2025Q3#4, MS-SUPP-2026Q3#25, SCHW-10K-2025#197, MER-PR-2026-09-15-01#2, EDJ-10Q-2025Q3#69, RJF-10Q-2026Q1#239, MS-10Q-2026Q2#60, SCHW-PR-2026-10-15-01#36, BAC-DECK-2025-investor-day#8, EDJ-10K-2025#41, RJF-PR-2026-04-22-01#1, MS-10K-2025#44, SCHW-DECK-2026Q3#35, BAC-SUPP-2026Q3#52, EDJ-10Q-2026Q1#51, RJF-DECK-2025-investor-day#142, MS-PR-2026-04-15-01#15, SCHW-TR-2026Q1#48, BAC-10K-2025#249, EDJ-10K-2025#320, RJF-SUPP-2026Q2#25, MS-TR-2026Q2#15, SCHW-MONTHLY-2026-08#7, BAC-10Q-2026Q2#88

### Q12 - PASS

How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

- Theme client_acquisition: no chunk on the theme for no firm (every named firm has one)
- `SCHW:transcript`: hit SCHW-TR-2025Q4#11, SCHW-TR-2026Q3#8, SCHW-TR-2026Q2#19
- `SCHW:10-K`: hit SCHW-10K-2025#13
- `SCHW:monthly`: hit SCHW-MONTHLY-2026-08#7
- `EDJ:10-K`: hit EDJ-10K-2025#8, EDJ-10K-2025#75, EDJ-10K-2025#87
- Retrieved: SCHW-TR-2025Q4#11, EDJ-10K-2025#8, SCHW-TR-2026Q3#8, EDJ-10K-2025#75, SCHW-PR-2026-10-15-01#7, EDJ-10Q-2026Q2#28, SCHW-10K-2025#13, EDJ-10K-2025#87, SCHW-DECK-2026-investor-day#251, EDJ-10Q-2026Q1#90, SCHW-10Q-2026Q2#8, EDJ-10Q-2025Q3#100, SCHW-MONTHLY-2026-08#7, EDJ-10Q-2025Q2#100, SCHW-TR-2026Q2#19, EDJ-10Q-2026Q2#85, SCHW-PR-2026-07-21-01#2, EDJ-10Q-2025Q2#66, SCHW-TRADE-2026-11-02-RB-01#4, EDJ-TRADE-2026-11-12-IN-01#1

### Q13 - PASS

How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

- `MS:transcript`: hit MS-TR-2026Q2#16, MS-TR-2025Q4#20, MS-TR-2026Q3#23, MS-TR-2026Q1#24
- `MS:10-K`: hit MS-10K-2025#168, MS-10K-2025#125, MS-10K-2025#165
- `MS:deck`: hit MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#28, MS-DECK-2026-strategic-update#31
- Expected `MS-10K-2025`: found MS-10K-2025#168, MS-10K-2025#125, MS-10K-2025#165
- Expected `MS-SUPP-2026Q3`: found MS-SUPP-2026Q3#16
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#20
- Expected `MS-TR-2026Q2`: found MS-TR-2026Q2#16
- Expected `MS-TR-2026Q3`: found MS-TR-2026Q3#23
- Expected `MS-DECK-2026-strategic-update`: found MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#28, MS-DECK-2026-strategic-update#31
- Retrieved: MS-10Q-2026Q2#61, MS-10K-2025#168, MS-SUPP-2025Q4#36, MS-DECK-2026-strategic-update#32, MS-TR-2026Q2#16, MS-PR-2026-07-15-01#5, MS-10Q-2026Q1#53, MS-10K-2025#125, MS-SUPP-2026Q3#16, MS-DECK-2026-strategic-update#28, MS-TR-2025Q4#20, MS-10Q-2025Q3#229, MS-10K-2025#165, MS-SUPP-2026Q2#16, MS-DECK-2026-strategic-update#31, MS-TR-2026Q3#23, MS-10Q-2025Q2#56, MS-SUPP-2026Q1#14, MS-TR-2026Q1#24, MS-TRADE-2026-10-21-IN-01#0

### Q14 - PASS

How does Raymond James's affiliation-choice model work commercially?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q1#23, RJF-TR-2026Q2#26, RJF-TR-2024Q4#8, RJF-TR-2025Q4#50, RJF-TR-2025Q1#79, RJF-TR-2024Q3#66, RJF-TR-2026Q1#4, RJF-TR-2026Q2#5, RJF-TR-2024Q4#23
- `RJF:press`: hit RJF-PR-web-affiliation-options#0, RJF-PR-web-independent-advisor#1, RJF-PR-web-affiliation-options#2, RJF-PR-web-affiliation-options#1
- Retrieved: RJF-PR-web-affiliation-options#0, RJF-TR-2026Q1#23, RJF-10K-2025#91, RJF-10Q-2026Q2#380, RJF-DECK-2025-investor-day#125, RJF-PR-web-independent-advisor#1, RJF-TR-2026Q2#26, RJF-10K-2025#10, RJF-10Q-2025Q4#142, RJF-PR-web-affiliation-options#2, RJF-TR-2024Q4#8, RJF-10K-2025#462, RJF-PR-web-affiliation-options#1, RJF-TR-2025Q4#50, RJF-TR-2025Q1#79, RJF-TR-2024Q3#66, RJF-TR-2026Q1#4, RJF-TR-2026Q2#5, RJF-TR-2024Q4#23, RJF-TRADE-2026-09-29-IN-01#1

### Q15 - PASS

What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

- `SCHW:10-K`: hit SCHW-10K-2025#13
- `MS:10-K`: hit MS-10K-2025#166
- `EDJ:10-K`: hit EDJ-10K-2025#20, EDJ-10K-2025#23
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: hit RJF-10K-2025#9
- Retrieved: MS-TR-2025Q3#3, SCHW-PR-2026-10-15-01#2, RJF-PR-2026-07-22-01#98, EDJ-10K-2025#20, BAC-TR-2026Q1#26, MS-DECK-2026-strategic-update#28, SCHW-TR-2025Q2#8, RJF-TR-2024Q4#5, EDJ-10Q-2026Q2#55, BAC-SUPP-2026Q3#52, MS-PR-2026-01-15-01#0, SCHW-MONTHLY-2026-04#9, RJF-SUPP-2026Q2#43, EDJ-10K-2025#23, BAC-DECK-2025-investor-day#8, MS-SUPP-2026Q3#16, SCHW-DECK-2026-investor-day#242, RJF-10Q-2026Q2#330, EDJ-10Q-2025Q3#78, MER-PR-web-advisor-development-program#0, MS-10K-2025#166, SCHW-10K-2025#13, RJF-10K-2025#9, BAC-10Q-2026Q2#86, MS-10Q-2026Q2#58, SCHW-10Q-2026Q2#9, RJF-DECK-2026Q2#4, EDJ-10Q-2025Q2#69, EDJ-TRADE-2026-11-12-IN-01#0, MER-TRADE-2026-11-12-IN-01#0

### Q16 - PASS

What will receiving financial advice in the future look like for clients?

- `THEME:research`: hit CAPGEMINI-WWR-2026#156, CERULLI-MASS-AFFLUENT-2026#1, CERULLI-GWT-2025#19
- `THEME:regulatory`: not in corpus
- `THEME:survey`: not in corpus
- `MS:transcript`: hit MS-TR-2025Q1#15
- `SCHW:transcript`: hit SCHW-TR-2026Q2#13
- Retrieved: CAPGEMINI-WWR-2026#156, MS-TR-2025Q1#15, SCHW-TR-2026Q2#13, EDJ-10K-2025#88, BAC-TR-2026Q1#13, RJF-TR-2026Q1#51, MER-PR-web-becoming-a-merrill-lynch-advisor#5, CERULLI-MASS-AFFLUENT-2026#1, MS-10K-2025#423, SCHW-10K-2025#261, EDJ-10Q-2026Q2#53, BAC-10K-2025#516, RJF-PR-web-bank-and-credit-union-advisors#1, CERULLI-GWT-2025#19, MS-DECK-2026-strategic-update#22, SCHW-DECK-2026Q3#18, BAC-PR-2026-10-14-01#9, RJF-10K-2025#91, EDJ-TRADE-2026-11-12-IN-01#1, MER-TRADE-2026-10-14-IN-01#0

### Q17 - PASS

What are these firms saying about AI in advice delivery, and who is claiming the most?

- `MS:transcript`: hit MS-TR-2025Q3#8
- `SCHW:transcript`: hit SCHW-TR-2026Q1#12
- `BAC:transcript#GWIM`: type only (qualifier not met): BAC-TR-2026Q2#6
- `RJF:transcript`: hit RJF-TR-2025Q4#6
- `MS:press`: no hit
- `SCHW:press`: hit SCHW-PR-2026-07-21-01#8
- `EDJ:press`: not in corpus
- `MER:press`: no hit
- `RJF:press`: no hit
- `MS:trade`: no hit
- `MER:trade`: hit MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-10-02-IN-01#0, MER-TRADE-2026-10-15-WM-01#1
- Expected `MS-10K-2025`: found MS-10K-2025#372
- Expected `MS-TR-2026Q2`: missing
- Expected `SCHW-TR-2026Q1`: found SCHW-TR-2026Q1#12
- Expected `SCHW-DECK-2026Q2`: found SCHW-DECK-2026Q2#22
- Expected `BAC-TR-2026Q2`: found BAC-TR-2026Q2#6
- Expected `BAC-TR-2026Q3`: missing
- Expected `RJF-TR-2025Q4`: found RJF-TR-2025Q4#6
- Expected `RJF-TR-2026Q1`: missing
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#26
- Retrieved: CAPGEMINI-WWR-2026#17, SCHW-TR-2026Q1#12, MER-TRADE-2026-10-14-IN-01#2, MS-TR-2025Q3#8, RJF-10K-2025#112, BAC-DECK-2026Q2#29, EDJ-10K-2025#26, DELOITTE-AGENTIC-2026#0, SCHW-PR-2026-07-21-01#8, MER-TRADE-2026-10-02-IN-01#0, MS-10K-2025#372, RJF-TR-2025Q4#6, BAC-TR-2026Q2#6, EDJ-10Q-2026Q2#47, FINRA-OVERSIGHT-2026#84, SCHW-DECK-2026Q2#22, MER-TRADE-2026-10-15-WM-01#1, MS-10Q-2026Q2#524, RJF-DECK-2025-investor-day#121, BAC-PR-2026-10-14-01#2

### Q18 - PASS

Where is the industry heading on fee structures and pricing transparency?

- `MS:adv`: hit MS-ADV-2026#127
- `SCHW:adv`: hit SCHW-ADV-2026#50
- `EDJ:adv`: hit EDJ-ADV-2026#108
- `MER:adv`: hit MER-ADV-2026#435
- `RJF:adv`: hit RJF-ADV-2026#33
- `THEME:regulatory`: not in corpus
- `THEME:research`: hit WEALTHTENDER-ADVISOR-SEARCH-2025#57, MCK-SIGNAL-SELLOFF-2026#9, UBS-NEXTGEN-2026#37
- Retrieved: WEALTHTENDER-ADVISOR-SEARCH-2025#57, EDJ-10K-2025#55, RJF-10K-2025#100, MS-ADV-2026#127, SCHW-ADV-2026#50, MER-ADV-2026#435, BAC-TR-2025Q4#53, MCK-SIGNAL-SELLOFF-2026#9, EDJ-ADV-2026#108, RJF-ADV-2026#33, MS-TR-2025Q4#19, SCHW-10K-2025#14, MER-PR-2026-09-15-01#2, BAC-10Q-2026Q1#31, UBS-NEXTGEN-2026#37, EDJ-10Q-2025Q2#67, RJF-TR-2026Q1#48, MS-10K-2025#276, SCHW-10Q-2026Q2#8, MER-TRADE-2026-09-29-RB-01#7

### Q19 - FAIL

How should the preferences of younger investors shape Edward Jones's offerings?

- Theme younger_investors: no chunk on the theme for EDJ
- `THEME:research`: hit CERULLI-GWT-2025#1, BOFA-PB-STUDY-2026#15, BOFA-PB-STUDY-2024#0, BOFA-PB-STUDY-2024#7
- `THEME:survey`: not in corpus
- `MS:press`: no hit
- `SCHW:press`: no hit
- `RJF:press`: no hit
- `MER:press`: no hit
- Retrieved: EDJ-10K-2025#304, EDJ-10Q-2026Q2#28, EDJ-10K-2025#56, EDJ-10Q-2026Q1#78, EDJ-10K-2025#16, EDJ-10Q-2025Q3#107, EDJ-10Q-2025Q2#17, EDJ-10Q-2026Q2#39, EDJ-10Q-2025Q3#19, EDJ-10Q-2025Q3#68, EDJ-10Q-2026Q2#11, EDJ-TRADE-2026-08-18-IN-01#1, EDJ-TRADE-2026-08-18-IN-01#4, EDJ-TRADE-2026-08-18-IN-01#5, CERULLI-GWT-2025#1, BOFA-PB-STUDY-2026#15, BOFA-PB-STUDY-2024#0, BOFA-PB-STUDY-2024#7, SCHW-TR-2026Q3#11, SCHW-TR-2025Q3#11

### Q20 - PASS

What evidence is there about how clients under 40 choose a financial advisor?

- `THEME:survey`: not in corpus
- `THEME:research`: hit CERULLI-GWT-2025#1, BOFA-PB-STUDY-2026#15, UBS-NEXTGEN-2026#83
- Expected `UBS-NEXTGEN-2026`: found UBS-NEXTGEN-2026#83
- Expected `CERULLI-GWT-2025`: found CERULLI-GWT-2025#1
- Expected `FINRAF-INVESTORS-2025`: missing
- Expected `KITCES-WELLBEING-2023`: missing
- Expected `BOFA-PB-STUDY-2026`: found BOFA-PB-STUDY-2026#15
- Expected `NM-PP-2026`: missing
- Expected `WEALTHTENDER-ADVISOR-SEARCH-2025`: missing
- Retrieved: CERULLI-GWT-2025#1, SCHW-TR-2026Q3#11, BAC-PR-2026-01-14-01#12, EDJ-10K-2025#19, RJF-TR-2026Q2#3, MER-PR-web-becoming-a-merrill-lynch-advisor#1, MS-TR-2026Q2#10, BOFA-PB-STUDY-2026#15, SCHW-DECK-2026-investor-day#131, BAC-DECK-2026Q2#36, EDJ-10Q-2025Q3#85, RJF-PR-2026-04-22-01#55, MER-PR-web-advisor-development-program#2, MS-SUPP-2026Q2#16, UBS-NEXTGEN-2026#83, SCHW-MONTHLY-2026-08#4, BAC-10K-2025#249, RJF-SUPP-2026Q1#13, EDJ-TRADE-2026-11-12-IN-01#1, MER-TRADE-2026-10-14-IN-01#0

### Q21 - PASS

What do we know about the generational wealth transfer, and how are these five preparing for it?

- Theme wealth_transfer: no chunk on the theme for no firm (every named firm has one)
- `THEME:research`: hit CERULLI-GWT-2025#24, CERULLI-GWT-2025#2, BOFA-PB-STUDY-2026#16, UBS-NEXTGEN-2026#6
- `MS:transcript`: hit MS-TR-2026Q3#25
- `SCHW:transcript`: hit SCHW-TR-2026Q3#11
- `EDJ:10-K`: hit EDJ-10K-2025#56, EDJ-10K-2025#304, EDJ-10K-2025#207
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q2#21
- `RJF:transcript`: hit RJF-TR-2026Q2#36
- Retrieved: SCHW-DECK-2026Q3#24, EDJ-10K-2025#56, MS-DECK-2026-strategic-update#22, RJF-TRADE-2026-11-06-IN-01#3, BAC-PR-2026-01-14-01#12, SCHW-TR-2026Q3#11, EDJ-10K-2025#304, MS-TR-2026Q3#25, RJF-TR-2026Q2#36, BAC-TR-2026Q2#21, SCHW-DECK-2026-investor-day#306, EDJ-10Q-2025Q3#72, MS-10K-2025#206, RJF-10K-2025#26, SCHW-PR-2026-07-21-01#8, EDJ-10K-2025#207, MS-10Q-2026Q2#97, RJF-PR-web-independent-ria-custody-services#0, BAC-10K-2025#246, SCHW-10Q-2026Q2#9, EDJ-10Q-2025Q2#67, MS-PR-2026-10-14-01#11, RJF-DECK-2025-investor-day#126, BAC-DECK-2025-investor-day#9, SCHW-TRADE-2026-10-29-WM-01#3, MER-TRADE-2026-11-16-AH-01#0, CERULLI-GWT-2025#24, CERULLI-GWT-2025#2, BOFA-PB-STUDY-2026#16, UBS-NEXTGEN-2026#6

### Q22 - PASS

Net new assets by quarter for each of the five, with each firm's own definition of the metric.

- `MS:supplement`: hit MS-SUPP-2026Q3#16
- `SCHW:monthly`: hit SCHW-MONTHLY-2026-02#2
- `SCHW:supplement`: not in corpus
- `EDJ:10-Q`: hit EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q3#54
- `RJF:supplement`: hit RJF-SUPP-2026Q2#9
- `MS:press`: hit MS-PR-2026-10-14-01#2
- `RJF:press`: hit RJF-PR-2026-07-22-01#25
- Expected `EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10K-2025#130`: found EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14, MS-10Q-2026Q2#57, MS-10Q-2026Q1#48, MS-10Q-2025Q3#56, MS-10Q-2025Q2#56, MS-PR-2026-01-15-01#2`: found MS-SUPP-2026Q3#16
- Expected `MS-SUPP-2026Q1#42, MS-10K-2025#166`: missing
- Expected `SCHW-PR-2026-01-21-01#2, SCHW-PR-2026-07-21-01#2, SCHW-DECK-2026Q3#7, SCHW-10Q-2026Q2#16, SCHW-10Q-2026Q1#16, SCHW-10Q-2025Q3#16, SCHW-10Q-2025Q2#16`: missing
- Expected `SCHW-10K-2025#122, SCHW-10K-2025#119, SCHW-DECK-2026Q3#20`: missing
- Expected `RJF-PR-2026-07-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-01-28-01#3, RJF-PR-2025-10-22-01#4, RJF-10Q-2026Q2#305, RJF-10Q-2026Q1#298, RJF-10Q-2025Q4#236, RJF-10Q-2025Q2#294`: missing
- Expected `RJF-10Q-2026Q2#306, RJF-SUPP-2026Q1#43`: missing
- Expected `BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#11`: found BAC-TR-2026Q3#19
- Retrieved: SCHW-TR-2026Q1#3, EDJ-10Q-2026Q2#60, RJF-TR-2025Q1#6, MS-TR-2026Q3#15, BAC-PR-2026-10-14-01#12, SCHW-PR-2026-04-16-01#3, EDJ-10K-2025#148, RJF-10K-2025#223, MS-DECK-2026-strategic-update#30, BAC-TR-2026Q3#19, SCHW-DECK-2026Q3#73, EDJ-10Q-2026Q1#51, RJF-10Q-2026Q1#323, MS-10K-2025#165, BAC-10K-2025#248, SCHW-10K-2025#136, EDJ-10K-2025#54, RJF-PR-2026-07-22-01#25, MS-10Q-2026Q2#58, BAC-10Q-2026Q1#74, SCHW-10Q-2026Q2#22, EDJ-10Q-2025Q3#67, RJF-SUPP-2026Q2#9, MS-SUPP-2026Q3#16, BAC-DECK-2026Q3#31, SCHW-MONTHLY-2026-02#2, EDJ-10K-2025#58, RJF-DECK-2026Q2#4, MS-PR-2026-10-14-01#2, BAC-SUPP-2026Q3#54

### Q23 - PASS

Advisor headcount over the last eight quarters across the five.

- `MS:supplement`: no hit
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-Q`: hit EDJ-10Q-2026Q2#60, EDJ-10Q-2025Q3#69, EDJ-10Q-2026Q1#51
- `EDJ:10-K`: hit EDJ-10K-2025#58, EDJ-10K-2025#70, EDJ-10K-2025#202
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `RJF:press`: hit RJF-PR-web-independent-ria-custody-services#0
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#58, EDJ-10K-2025#70, EDJ-10K-2025#202
- Expected `EDJ-10Q-2025Q2`: missing
- Expected `EDJ-10Q-2025Q3`: found EDJ-10Q-2025Q3#69
- Expected `EDJ-10Q-2026Q1`: found EDJ-10Q-2026Q1#51
- Expected `EDJ-10Q-2026Q2`: found EDJ-10Q-2026Q2#60
- Expected `MS-SUPP-2025Q4`: missing
- Expected `MS-SUPP-2026Q1`: missing
- Expected `MS-SUPP-2026Q2`: missing
- Expected `MS-SUPP-2026Q3`: missing
- Expected `BAC-10K-2025`: found BAC-10K-2025#247
- Expected `BAC-SUPP-2025Q4`: missing
- Expected `BAC-SUPP-2026Q1`: missing
- Expected `BAC-SUPP-2026Q2`: missing
- Expected `BAC-SUPP-2026Q3`: missing
- Expected `RJF-10K-2025`: found RJF-10K-2025#12
- Expected `RJF-SUPP-2025Q3`: missing
- Expected `RJF-SUPP-2025Q4`: missing
- Expected `RJF-SUPP-2026Q1`: missing
- Expected `RJF-SUPP-2026Q2`: missing
- Expected `SCHW-10K-2025`: found SCHW-10K-2025#197
- Retrieved: MS-TR-2025Q4#4, RJF-TR-2025Q3#8, EDJ-10Q-2026Q2#60, SCHW-TR-2026Q1#8, BAC-DECK-2025-investor-day#8, MS-10K-2025#44, RJF-10K-2025#12, EDJ-10K-2025#58, SCHW-10Q-2026Q2#25, MER-PR-web-advisor-development-program#0, MS-10Q-2026Q2#20, RJF-10Q-2026Q1#239, EDJ-10Q-2025Q3#69, SCHW-10K-2025#197, BAC-10K-2025#247, MS-DECK-2026-strategic-update#31, RJF-PR-web-independent-ria-custody-services#0, EDJ-10K-2025#70, SCHW-PR-2026-10-15-01#36, BAC-TR-2026Q2#63, MS-PR-2026-10-14-01#5, RJF-DECK-2025-investor-day#131, EDJ-10Q-2026Q1#51, SCHW-DECK-2026Q3#73, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MS-TR-2025Q1#2, RJF-TR-2026Q2#70, EDJ-10K-2025#202, SCHW-TR-2026Q2#33, BAC-TR-2026Q3#19

### Q24 - PASS

Client assets per advisor across the five -- and is that comparison even valid?

- `MS:supplement`: hit MS-SUPP-2026Q3#16
- `SCHW:10-K`: hit SCHW-10K-2025#136
- `EDJ:10-K`: hit EDJ-10K-2025#23, EDJ-10K-2025#208, EDJ-10K-2025#79
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q3#54
- `RJF:supplement`: hit RJF-SUPP-2026Q2#43
- Expected `EDJ-10K-2025#130`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38`: missing
- Retrieved: SCHW-TR-2025Q1#9, MS-DECK-2026-strategic-update#28, RJF-PR-2026-07-22-01#98, EDJ-10K-2025#23, BAC-TR-2026Q3#19, SCHW-DECK-2026-investor-day#25, MS-TR-2026Q3#18, RJF-TR-2025Q4#4, EDJ-10Q-2026Q2#61, BAC-DECK-2025-investor-day#8, SCHW-PR-2026-10-15-01#53, MS-PR-2026-01-15-01#0, RJF-10K-2025#9, EDJ-10K-2025#208, BAC-10K-2025#249, SCHW-MONTHLY-2026-08#4, MS-SUPP-2026Q3#16, RJF-SUPP-2026Q2#43, EDJ-10Q-2026Q1#52, MER-PR-web-becoming-a-merrill-lynch-advisor#3, SCHW-10K-2025#136, MS-10K-2025#177, RJF-10Q-2026Q2#330, EDJ-10K-2025#79, BAC-10Q-2026Q2#92, SCHW-10Q-2026Q2#22, MS-10Q-2026Q2#28, RJF-DECK-2025-investor-day#30, EDJ-10Q-2025Q3#60, BAC-SUPP-2026Q3#54

### Q25 - PASS

What has each of the five actually disclosed about advisor compensation structures?

- `MS:10-K`: hit MS-10K-2025#420
- `SCHW:10-K`: hit SCHW-10K-2025#512
- `EDJ:10-K`: hit EDJ-10K-2025#314, EDJ-10K-2025#22
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `RJF:10-K`: hit RJF-10K-2025#175
- `MS:DEF 14A`: not in corpus
- `SCHW:DEF 14A`: not in corpus
- `BAC:DEF 14A`: not in corpus
- `RJF:DEF 14A`: not in corpus
- `MS:adv`: hit MS-ADV-2026#198
- `EDJ:adv`: hit EDJ-ADV-2026#122
- `RJF:adv`: hit RJF-ADV-2026#114
- Expected `RJF-10K-2025#10, RJF-10K-2025#11`: missing
- Expected `EDJ-10K-2025#30, EDJ-10K-2025#264`: missing
- Expected `MS-10K-2025#153`: missing
- Expected `SCHW-10Q-2026Q2#25`: missing
- Retrieved: RJF-ADV-2026#114, MER-ADV-2026#449, MS-ADV-2026#198, EDJ-10K-2025#314, SCHW-ADV-2026#45, RJF-PR-web-affiliation-options#2, BAC-DECK-2025-investor-day#8, MS-10K-2025#420, EDJ-ADV-2026#122, SCHW-TR-2026Q1#48, RJF-10Q-2026Q2#252, MER-PR-2026-09-15-01#2, MS-10Q-2026Q2#454, EDJ-10Q-2026Q1#60, SCHW-10K-2025#512, RJF-10K-2025#175, BAC-10K-2025#246, MS-TR-2026Q3#58, EDJ-10K-2025#22, SCHW-10Q-2026Q2#177, RJF-TR-2025Q3#20, MS-DECK-2026-strategic-update#31, SCHW-DECK-2026Q3#13, RJF-SUPP-2026Q2#13, BAC-TR-2026Q3#19, MS-SUPP-2026Q3#38, EDJ-10Q-2026Q2#50, SCHW-PR-2026-10-15-01#36, MER-TRADE-2026-09-11-WM-01#1, EDJ-TRADE-2026-11-12-IN-01#1

### Q26 - PASS

What's new on Raymond James in the last 90 days?

- `RJF:*`: hit RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-29-IN-01#4, RJF-TRADE-2026-09-29-IN-01#2, RJF-TRADE-2026-09-29-WM-01#1, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-26-IN-01#2
- Window: 2026-08-19 to 2026-11-17
- Retrieved: RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-29-IN-01#4, RJF-TRADE-2026-09-29-IN-01#2, RJF-TRADE-2026-09-29-WM-01#1, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-26-IN-01#2

### Q27 - PASS

What has changed at Merrill since the start of the year?

- `MER:*`: hit MER-TRADE-2026-11-16-AH-01#1, MER-TRADE-2026-11-12-IN-01#2, BAC-DECK-2026Q3#31, BAC-SUPP-2026Q3#51, BAC-PR-2026-10-14-01#12, MER-TRADE-2026-10-14-IN-01#2, BAC-TR-2026Q3#19, MER-PR-2026-09-15-01#0, BAC-10Q-2026Q2#88, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-SUPP-2026Q2#52, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-TR-2026Q1#26, BAC-DECK-2026Q1#27, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247
- `BAC:*#GWIM`: hit BAC-DECK-2026Q3#31, BAC-SUPP-2026Q3#51, BAC-PR-2026-10-14-01#12, BAC-TR-2026Q3#19, BAC-10Q-2026Q2#88, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-SUPP-2026Q2#52, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-TR-2026Q1#26, BAC-DECK-2026Q1#27, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247
- Expected `MER-PR-2026-09-15-01`: found MER-PR-2026-09-15-01#0
- Expected `MER-PR-web-advisor-development-program`: missing
- Expected `MER-PR-web-becoming-a-merrill-lynch-advisor`: missing
- Expected `BAC-TR-2026Q1`: found BAC-TR-2026Q1#26
- Expected `BAC-TR-2026Q2`: found BAC-TR-2026Q2#21
- Expected `BAC-TR-2026Q3`: found BAC-TR-2026Q3#19
- Expected `BAC-SUPP-2026Q1`: missing
- Expected `BAC-SUPP-2026Q2`: found BAC-SUPP-2026Q2#52
- Expected `BAC-SUPP-2026Q3`: found BAC-SUPP-2026Q3#51
- Retrieved: MER-TRADE-2026-11-16-AH-01#1, MER-TRADE-2026-11-12-IN-01#2, BAC-DECK-2026Q3#31, BAC-SUPP-2026Q3#51, BAC-PR-2026-10-14-01#12, MER-TRADE-2026-10-14-IN-01#2, BAC-TR-2026Q3#19, MER-PR-2026-09-15-01#0, BAC-10Q-2026Q2#88, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-SUPP-2026Q2#52, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-TR-2026Q1#26, BAC-DECK-2026Q1#27, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247

### Q28 - PASS

What is Edward Jones's advisor attrition rate compared to Merrill's?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `EDJ:10-K`: hit EDJ-10K-2025#71, EDJ-10K-2025#27, EDJ-10K-2025#58
- `BAC:supplement#GWIM`: no hit
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- Expected `EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q3#68, EDJ-10Q-2025Q3#70`: found EDJ-10Q-2025Q3#70, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q2#64
- Expected `EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q3#69`: found EDJ-10Q-2025Q2#66
- Expected `BAC-TR-2026Q2#63, BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: found BAC-TR-2026Q2#63
- Expected `EDJ-10K-2025#130, EDJ-10Q-2026Q2#60`: missing
- Retrieved: EDJ-10Q-2025Q3#70, BAC-TR-2026Q2#63, EDJ-10Q-2025Q2#66, BAC-TR-2026Q3#19, EDJ-10K-2025#71, BAC-DECK-2025-investor-day#8, EDJ-10Q-2026Q1#60, MER-PR-web-advisor-development-program#2, EDJ-10K-2025#27, BAC-10K-2025#246, EDJ-10Q-2026Q2#61, BAC-TR-2026Q1#26, EDJ-10K-2025#58, BAC-DECK-2025-investor-day#18, EDJ-10Q-2025Q2#67, MER-PR-web-becoming-a-merrill-lynch-advisor#1, EDJ-10Q-2025Q2#64, KITCES-WELLBEING-2023#23, KITCES-WELLBEING-2023#17, MCK-ADVISOR-SHORTAGE-2025#25

### Q29 - PASS

What does Morgan Stanley pay its financial advisors?

- `MS:10-K#Wealth Management`: hit MS-10K-2025#170
- `MS:trade`: hit MS-TRADE-2026-08-25-RB-01#0
- Expected `MS-10K-2025#153`: found MS-10K-2025#153
- Expected `MS-10K-2025#128, MS-10K-2025#170`: found MS-10K-2025#170, MS-10K-2025#128
- Retrieved: MS-10Q-2026Q2#20, MS-10K-2025#170, MS-TR-2025Q4#22, MS-PR-2026-10-14-01#5, MS-SUPP-2026Q3#38, MS-10Q-2026Q1#19, MS-10K-2025#128, MS-TR-2025Q3#89, MS-PR-2026-07-15-01#17, MS-SUPP-2026Q1#25, MS-10Q-2025Q3#64, MS-10K-2025#153, MS-TR-2025Q1#54, MS-PR-2026-04-15-01#14, MS-SUPP-2026Q2#44, MS-10Q-2025Q2#20, MS-TR-2026Q3#36, MS-SUPP-2025Q4#42, MS-TR-2026Q2#23, MS-TRADE-2026-08-25-RB-01#0

### Q30 - PASS

What is Merrill's standalone profitability?

- `BAC:10-K#GWIM`: hit BAC-10K-2025#244, BAC-10K-2025#246
- Expected `BAC-PR-2026-01-14-01#12`: missing
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246
- Retrieved: BAC-TR-2025Q3#26, BAC-DECK-2026Q3#30, BAC-PR-2026-10-14-01#11, BAC-10K-2025#244, BAC-10Q-2026Q2#85, BAC-SUPP-2026Q3#51, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#19, BAC-PR-2026-07-14-01#10, BAC-10K-2025#246, BAC-10Q-2025Q3#90, BAC-SUPP-2026Q2#52, BAC-TR-2026Q1#26, BAC-DECK-2026Q1#26, BAC-PR-2026-04-15-01#10, BAC-SUPP-2026Q1#43, BAC-TR-2025Q1#28, BAC-DECK-2025-investor-day#10, BAC-PR-2026-01-14-01#11, MER-TRADE-2026-10-14-IN-01#1

