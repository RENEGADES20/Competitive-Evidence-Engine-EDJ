# Eval run corpus-2026-11-17-20261117-223334

Snapshot `corpus-2026-11-17` | commit `960b742` | k=by question | min coverage 0.5 | as of 2026-11-17 | mode mock | 0 real calls

**PASS 28 | FAIL 2 | NOT_EVALUATED 0 | INVALID_OUTPUT 0**

**Tier-1 recall**: documents 0.547, passages 0.42 (mean over the 17 of 18 tier-1 questions with an answer key; the rest n/a until #56)  
**Refusal accuracy**: gap questions (Q24, Q25, Q28, Q29, Q30) 5/5; all questions with a key 19/19

Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the corpus; PASS when coverage of the available patterns >= min coverage.

Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window.

| Q | Tier | Use case | Expected | Firms (mode) | k | Hits | Chars | Coverage | Recall docs | Passages | Refusal | Forbidden | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 24171 | 4/4 | 5/9 | 2/8 | ok | 0 | PASS |
| Q2 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 22106 | 4/4 | 3/9 | 3/9 | ok | 0 | PASS |
| Q3 | 1 | entity_brief | answer | SCHW (entity) | 20 | 20 | 23160 | 3/3 | 3/6 | 3/6 | ok | 0 | PASS |
| Q4 (trap) | 1 | entity_brief | answer | MER (entity) | 20 | 20 | 20822 | 4/4 | 4/5 | 4/7 | ok | 0 | PASS |
| Q5 | 1 | entity_brief | answer | MS (entity) | 20 | 20 | 22535 | 4/4 | 4/6 | 4/6 | ok | 0 | PASS |
| Q6 | 1 | entity_brief | answer | RJF (entity) | 20 | 20 | 21902 | 2/3 | 3/6 | 3/6 | ok | 0 | PASS |
| Q7 | 2 | head_to_head | answer | MS, MER, RJF (entity+theme) | 20 | 20 | 21841 | 8/9 | - | - | - | 0 | PASS |
| Q8 | 2 | head_to_head | answer | SCHW, RJF (entity) | 20 | 20 | 23417 | 4/4 | - | - | - | 0 | PASS |
| Q9 | 3 | head_to_head | answer | MS, MER (entity) | 20 | 20 | 25061 | 5/6 | - | - | - | 0 | PASS |
| Q10 | 3 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 32654 | 5/5 | - | - | - | 0 | PASS |
| Q11 | 1 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 38461 | 8/8 | 6/8 | 2/10 | ok | 0 | PASS |
| Q12 | 3 | mechanism | answer_with_boundary | SCHW, EDJ (entity+theme) | 20 | 20 | 24559 | 4/4 | - | - | - | 0 | PASS |
| Q13 | 1 | mechanism | answer | MS (entity) | 20 | 20 | 25842 | 3/3 | 3/6 | 3/6 | ok | 0 | PASS |
| Q14 | 3 | mechanism | answer | RJF (entity) | 20 | 20 | 24129 | 3/3 | - | - | - | 0 | PASS |
| Q15 | 3 | mechanism | answer | SCHW (entity) | 20 | 20 | 22930 | 1/5 | - | - | - | 0 | FAIL |
| Q16 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 25147 | 3/3 | - | - | - | 0 | PASS |
| Q17 | 1 | theme_scan | answer | none (theme) | 20 | 20 | 22588 | 6/10 | 3/9 | 3/9 | ok | 0 | PASS |
| Q18 | 3 | theme_scan | answer | none (theme) | 20 | 20 | 23631 | 6/6 | - | - | - | 0 | PASS |
| Q19 | 3 | segment_evidence | answer_with_boundary | EDJ (entity+theme) | 20 | 19 | 24103 | 1/5 | - | - | - | 0 | FAIL |
| Q20 | 1 | segment_evidence | answer | none (theme) | 20 | 20 | 24814 | 1/1 | 2/7 | 2/7 | ok | 0 | PASS |
| Q21 | 2 | segment_evidence | answer | MS, SCHW, EDJ, MER, RJF (entity+theme) | 30 | 30 | 35528 | 6/6 | - | - | - | 0 | PASS |
| Q22 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 37206 | 7/7 | 12/33 | 1/8 | ok | 0 | PASS |
| Q23 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 35999 | 4/7 | 6/20 | 6/20 | ok | 0 | PASS |
| Q24 | 3 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 35068 | 5/5 | 3/5 | 0/4 | ok | 0 | PASS |
| Q25 | 1 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 30 | 30 | 36260 | 8/8 | 3/4 | 0/4 | ok | 0 | PASS |
| Q26 | 1 | recency | answer | RJF (entity) | 20 | 15 | 19723 | 1/1 | - | - | ok | 0 | PASS |
| Q27 (trap) | 1 | recency | answer | MER (entity) | 20 | 20 | 24249 | 2/2 | 3/9 | 3/9 | ok | 0 | PASS |
| Q28 | 1 | honest_miss | gap_with_adjacent | EDJ, MER (entity+theme) | 20 | 20 | 23932 | 2/3 | 5/6 | 3/4 | ok | 0 | PASS |
| Q29 | 1 | honest_miss | gap_with_adjacent | MS (entity) | 20 | 20 | 23332 | 2/2 | 1/1 | 2/2 | ok | 0 | PASS |
| Q30 (trap) | 1 | honest_miss | gap_with_adjacent | MER (entity) | 20 | 20 | 25582 | 1/1 | 1/2 | 1/2 | ok | 0 | PASS |

## Per question

### Q1 - PASS

What is Morgan Stanley's strategy to increase their net new assets?

- `MS:transcript`: hit MS-TR-2026Q2#16, MS-TR-2026Q3#15, MS-TR-2025Q3#24
- `MS:10-K#Wealth Management`: hit MS-10K-2025#165, MS-10K-2025#180
- `MS:deck`: hit MS-DECK-2026-strategic-update#30, MS-DECK-2026-strategic-update#31, MS-DECK-2026-strategic-update#8
- `MS:supplement`: hit MS-SUPP-2026Q1#46, MS-SUPP-2025Q4#39, MS-SUPP-2026Q1#28
- Expected `MS-TR-2026Q2#3`: missing
- Expected `MS-TR-2026Q2#14, MS-TR-2026Q2#16`: found MS-TR-2026Q2#16
- Expected `MS-TR-2026Q3#3, MS-TR-2026Q3#12, MS-TR-2026Q3#13`: missing
- Expected `MS-TR-2026Q1#3, MS-TR-2026Q1#9, MS-TR-2026Q1#10, MS-TR-2026Q1#11`: missing
- Expected `MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5`: found MS-PR-2026-10-14-01#5
- Expected `MS-10K-2025#125`: missing
- Expected `MS-10K-2025#127, MS-10K-2025#164, MS-10K-2025#166`: missing
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14`: missing
- Retrieved: MS-TR-2026Q2#16, MS-10Q-2026Q1#18, MS-DECK-2026-strategic-update#30, MS-10K-2025#165, MS-SUPP-2026Q1#46, MS-PR-2026-01-15-01#3, MS-TRADE-2026-10-14-WM-01#2, MS-TR-2026Q3#15, MS-10Q-2026Q2#58, MS-DECK-2026-strategic-update#31, MS-10K-2025#180, MS-SUPP-2025Q4#39, MS-PR-2026-04-15-01#2, MS-TRADE-2026-10-14-WM-01#0, MS-TR-2025Q3#24, MS-10Q-2025Q2#57, MS-DECK-2026-strategic-update#8, MS-10K-2025#669, MS-SUPP-2026Q1#28, MS-PR-2026-10-14-01#5

### Q2 - PASS

How is Raymond James positioning itself to recruit advisors away from the wirehouses?

- `RJF:transcript`: hit RJF-TR-2026Q1#54, RJF-TR-2024Q3#23, RJF-TR-2024Q4#26
- `RJF:10-K`: hit RJF-10K-2025#91, RJF-10K-2025#175, RJF-10K-2025#334
- `RJF:press`: hit RJF-PR-web-bank-and-credit-union-advisors#0, RJF-PR-web-advisor-select#0, RJF-PR-web-traditional-employee-advisor#0
- `RJF:trade`: hit RJF-TRADE-2026-09-02-IN-01#2, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-11-05-IN-01#2
- Expected `RJF-10K-2025`: found RJF-10K-2025#91, RJF-10K-2025#175, RJF-10K-2025#334
- Expected `RJF-TR-2025Q4`: missing
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#54
- Expected `RJF-TR-2026Q2`: missing
- Expected `RJF-PR-2026-04-22-01`: missing
- Expected `RJF-PR-2026-07-22-01`: missing
- Expected `RJF-PR-web-affiliation-options`: missing
- Expected `RJF-PR-web-traditional-employee-advisor`: found RJF-PR-web-traditional-employee-advisor#0
- Expected `RJF-PR-web-independent-advisor`: missing
- Retrieved: RJF-TRADE-2026-09-02-IN-01#2, RJF-TR-2026Q1#54, RJF-PR-web-bank-and-credit-union-advisors#0, RJF-10K-2025#91, RJF-10Q-2026Q1#307, RJF-SUPP-2025Q4#12, RJF-DECK-2025-investor-day#40, RJF-TRADE-2026-11-04-IN-01#2, RJF-TR-2024Q3#23, RJF-PR-web-advisor-select#0, RJF-10K-2025#175, RJF-10Q-2026Q2#316, RJF-SUPP-2025Q4#37, RJF-DECK-2025-investor-day#42, RJF-TRADE-2026-11-05-IN-01#2, RJF-TR-2024Q4#26, RJF-PR-web-traditional-employee-advisor#0, RJF-10K-2025#334, RJF-10Q-2025Q2#131, RJF-SUPP-2026Q1#44

### Q3 - PASS

What is Schwab's strategy for its RIA custody business?

- `SCHW:transcript`: hit SCHW-TR-2026Q3#4, SCHW-TR-2025Q1#9, SCHW-TR-2026Q3#10
- `SCHW:10-K#Advisor Services`: hit SCHW-10K-2025#26
- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#305, SCHW-DECK-2026Q2#14, SCHW-DECK-2026-investor-day#119
- Expected `SCHW-10K-2025`: found SCHW-10K-2025#11, SCHW-10K-2025#26, SCHW-10K-2025#13
- Expected `SCHW-TR-2026Q1`: missing
- Expected `SCHW-TR-2026Q2`: missing
- Expected `SCHW-TR-2026Q3`: found SCHW-TR-2026Q3#4, SCHW-TR-2026Q3#10
- Expected `SCHW-DECK-2026Q3`: missing
- Expected `SCHW-DECK-2026-investor-day`: found SCHW-DECK-2026-investor-day#305, SCHW-DECK-2026-investor-day#119
- Retrieved: SCHW-TRADE-2026-10-28-WM-01#0, SCHW-10K-2025#11, SCHW-10Q-2026Q2#342, SCHW-TR-2026Q3#4, SCHW-DECK-2026-investor-day#305, SCHW-PR-2026-04-16-01#7, SCHW-MONTHLY-2026-01#3, SCHW-TRADE-2026-10-29-WM-01#0, SCHW-10K-2025#26, SCHW-10Q-2026Q2#343, SCHW-TR-2025Q1#9, SCHW-DECK-2026Q2#14, SCHW-PR-2026-07-21-01#2, SCHW-MONTHLY-2026-02#4, SCHW-TRADE-2026-10-15-WM-01#1, SCHW-10K-2025#13, SCHW-10Q-2025Q2#310, SCHW-TR-2026Q3#10, SCHW-DECK-2026-investor-day#119, SCHW-PR-2026-01-21-01#7

### Q4 - PASS

What is Merrill's advisor growth strategy, and how has it changed?

- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#19, BAC-TR-2026Q2#20, BAC-TR-2025Q4#106, BAC-TR-2025Q2#34, BAC-TR-2025Q1#28, BAC-TR-2025Q2#35, BAC-TR-2026Q1#26
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `MER:press`: hit MER-PR-web-becoming-a-merrill-lynch-advisor#0, MER-PR-2026-09-15-01#2, MER-PR-2026-09-15-01#0, MER-PR-2026-09-15-01#3, MER-PR-web-advisor-development-program#0
- `MER:trade`: hit MER-TRADE-2026-11-03-WM-01#0, MER-TRADE-2026-11-12-IN-01#0, MER-TRADE-2026-10-14-IN-01#2, MER-TRADE-2026-10-14-IN-02#2, MER-TRADE-2026-11-12-IN-01#1, MER-TRADE-2026-11-03-WM-01#2
- Expected `BAC-TR-2026Q1#25, BAC-TR-2026Q1#26`: found BAC-TR-2026Q1#26
- Expected `BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: missing
- Expected `BAC-TR-2026Q2#20, BAC-TR-2026Q2#21, BAC-TR-2026Q2#22`: found BAC-TR-2026Q2#20
- Expected `BAC-TR-2026Q2#63`: missing
- Expected `BAC-TR-2026Q3#19`: found BAC-TR-2026Q3#19
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246
- Expected `BAC-10Q-2026Q2#88, BAC-10Q-2026Q2#89, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91`: missing
- Retrieved: BAC-DECK-2025-investor-day#8, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MER-TRADE-2026-11-03-WM-01#0, BAC-10K-2025#246, BAC-TR-2026Q3#19, MER-PR-2026-09-15-01#2, MER-TRADE-2026-11-12-IN-01#0, BAC-TR-2026Q2#20, MER-PR-2026-09-15-01#0, MER-TRADE-2026-10-14-IN-01#2, BAC-TR-2025Q4#106, MER-PR-2026-09-15-01#3, MER-TRADE-2026-10-14-IN-02#2, BAC-TR-2025Q2#34, MER-PR-web-advisor-development-program#0, BAC-TR-2025Q1#28, MER-TRADE-2026-11-12-IN-01#1, BAC-TR-2025Q2#35, MER-TRADE-2026-11-03-WM-01#2, BAC-TR-2026Q1#26

### Q5 - PASS

Where is Morgan Stanley investing in technology for its advisors?

- `MS:transcript`: hit MS-TR-2026Q3#16, MS-TR-2025Q3#8, MS-TR-2025Q4#8, MS-TR-2026Q3#8, MS-TR-2025Q4#65, MS-TR-2025Q3#37
- `MS:10-K`: hit MS-10K-2025#25, MS-10K-2025#76, MS-10K-2025#111
- `MS:deck`: hit MS-DECK-2026-strategic-update#10
- `MS:trade`: hit MS-TRADE-2026-11-15-AH-01#0, MS-TRADE-2026-10-27-IN-01#2, MS-TRADE-2026-08-22-RB-01#11, MS-TRADE-2026-10-14-WM-01#2, MS-TRADE-2026-11-15-AH-01#1
- Expected `MS-10K-2025`: found MS-10K-2025#25, MS-10K-2025#76, MS-10K-2025#111
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#8, MS-TR-2025Q4#65
- Expected `MS-TR-2026Q1`: missing
- Expected `MS-TR-2026Q2`: missing
- Expected `MS-TR-2026Q3`: found MS-TR-2026Q3#16, MS-TR-2026Q3#8
- Expected `MS-DECK-2026-strategic-update`: found MS-DECK-2026-strategic-update#10
- Retrieved: MS-TR-2026Q3#16, MS-10K-2025#25, MS-TRADE-2026-11-15-AH-01#0, MS-10Q-2026Q2#524, MS-PR-2026-10-14-01#5, MS-TR-2025Q3#8, MS-10K-2025#76, MS-TRADE-2026-10-27-IN-01#2, MS-10Q-2025Q3#63, MS-DECK-2026-strategic-update#10, MS-TR-2025Q4#8, MS-10K-2025#111, MS-TRADE-2026-08-22-RB-01#11, MS-10Q-2025Q3#64, MS-TR-2026Q3#8, MS-TRADE-2026-10-14-WM-01#2, MS-TR-2025Q4#65, MS-TRADE-2026-11-15-AH-01#1, MS-10Q-2026Q2#20, MS-TR-2025Q3#37

### Q6 - PASS

What has Raymond James said about its affiliation models, and has the mix shifted?

- `RJF:10-K#Private Client Group`: type only (qualifier not met): RJF-10K-2025#462, RJF-10K-2025#320, RJF-10K-2025#639
- `RJF:transcript`: hit RJF-TR-2026Q1#45, RJF-TR-2026Q1#46, RJF-TR-2024Q3#79, RJF-TR-2025Q4#57, RJF-TR-2024Q3#22
- `RJF:press`: hit RJF-PR-2026-01-28-01#6, RJF-PR-2026-04-22-01#5, RJF-PR-web-affiliation-options#1
- Expected `RJF-10K-2025`: found RJF-10K-2025#462, RJF-10K-2025#320, RJF-10K-2025#639
- Expected `RJF-10Q-2026Q2`: missing
- Expected `RJF-TR-2025Q2`: missing
- Expected `RJF-TR-2026Q1`: found RJF-TR-2026Q1#45, RJF-TR-2026Q1#46
- Expected `RJF-TR-2026Q2`: missing
- Expected `RJF-PR-web-affiliation-options`: found RJF-PR-web-affiliation-options#1
- Retrieved: RJF-TR-2026Q1#45, RJF-10K-2025#462, RJF-TRADE-2026-08-26-IN-01#1, RJF-10Q-2026Q1#267, RJF-DECK-2025-investor-day#55, RJF-PR-2026-01-28-01#6, RJF-TR-2026Q1#46, RJF-10K-2025#320, RJF-TRADE-2026-08-19-IN-01#0, RJF-10Q-2025Q4#259, RJF-DECK-2025-investor-day#83, RJF-TR-2024Q3#79, RJF-10K-2025#639, RJF-TRADE-2026-10-27-WM-01#1, RJF-10Q-2026Q1#243, RJF-PR-2026-04-22-01#5, RJF-TR-2025Q4#57, RJF-TRADE-2026-09-02-IN-01#1, RJF-PR-web-affiliation-options#1, RJF-TR-2024Q3#22

### Q7 - PASS

How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `MS:transcript`: hit MS-TR-2026Q1#24
- `MS:10-K`: hit MS-10K-2025#51
- `BAC:transcript#GWIM`: hit BAC-TR-2025Q1#28
- `BAC:10-K#GWIM`: no hit
- `RJF:transcript`: hit RJF-TR-2026Q1#25, RJF-TR-2026Q2#67
- `RJF:10-K`: hit RJF-10K-2025#90
- `MS:trade`: hit MS-TRADE-2026-10-26-IN-01#3, MS-TRADE-2026-10-27-IN-01#2, MS-TRADE-2026-10-26-IN-01#1
- `MER:trade`: hit MER-TRADE-2026-11-16-AH-01#1, MER-TRADE-2026-11-03-WM-01#0
- `RJF:trade`: hit RJF-TRADE-2026-09-24-IN-01#3
- Retrieved: MS-TRADE-2026-10-26-IN-01#3, RJF-TR-2026Q1#25, MER-TRADE-2026-11-16-AH-01#1, MS-TRADE-2026-10-27-IN-01#2, RJF-TR-2026Q2#67, MER-TRADE-2026-11-03-WM-01#0, MS-10K-2025#51, RJF-10K-2025#90, BAC-TR-2025Q1#28, MS-TR-2026Q1#24, RJF-TRADE-2026-09-24-IN-01#3, MER-PR-web-advisor-development-program#2, MS-10Q-2026Q1#125, RJF-10Q-2026Q2#316, BAC-DECK-2025-investor-day#8, MS-TRADE-2026-10-26-IN-01#1, MCK-ADVISOR-SHORTAGE-2025#30, MCK-ADVISOR-SHORTAGE-2025#12, KITCES-WELLBEING-2023#58, KITCES-WELLBEING-2023#40

### Q8 - PASS

Compare how Schwab and Raymond James describe their value proposition to independent advisors.

- `SCHW:deck`: hit SCHW-DECK-2026-investor-day#16
- `SCHW:10-K`: hit SCHW-10K-2025#13, SCHW-10K-2025#117
- `RJF:deck`: hit RJF-DECK-2025-investor-day#110
- `RJF:10-K`: hit RJF-10K-2025#27, RJF-10K-2025#23
- Retrieved: RJF-TR-2025Q3#8, SCHW-TR-2026Q1#49, RJF-PR-web-bank-and-credit-union-advisors#3, SCHW-10K-2025#13, RJF-10K-2025#27, SCHW-TRADE-2026-08-26-WM-01#4, RJF-TRADE-2026-11-06-IN-01#2, SCHW-DECK-2026-investor-day#16, RJF-DECK-2025-investor-day#110, SCHW-PR-2026-07-21-01#1, RJF-10Q-2025Q2#201, SCHW-MONTHLY-2026-01#3, RJF-SUPP-2025Q4#37, SCHW-10Q-2025Q2#7, RJF-TR-2025Q4#5, SCHW-TR-2026Q1#47, RJF-PR-web-independent-advisor#0, SCHW-10K-2025#117, RJF-10K-2025#23, SCHW-TRADE-2026-08-24-IN-01#1

### Q9 - PASS

How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

- `MS:10-K`: hit MS-10K-2025#190, MS-10K-2025#311
- `MS:transcript`: hit MS-TR-2026Q3#33
- `MS:deck`: hit MS-DECK-2026-strategic-update#34
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246, BAC-10K-2025#247
- `BAC:transcript#GWIM`: no hit
- `BAC:deck#GWIM`: hit BAC-DECK-2025-investor-day#12
- Retrieved: MER-TRADE-2026-09-08-WM-01#0, MS-TRADE-2026-10-01-IN-01#0, BAC-10K-2025#246, MS-10K-2025#190, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MS-10Q-2025Q2#180, BAC-DECK-2025-investor-day#12, MS-TR-2026Q3#33, MER-TRADE-2026-11-03-WM-01#1, MS-PR-2026-04-15-01#8, BAC-10K-2025#247, MS-SUPP-2025Q4#42, BAC-10Q-2025Q3#94, MS-DECK-2026-strategic-update#34, MER-TRADE-2026-09-29-RB-01#3, MS-TRADE-2026-10-01-IN-01#3, MER-PR-web-advisor-development-program#0, MS-10K-2025#311, BAC-10Q-2026Q2#88, MS-10Q-2025Q2#87

### Q10 - PASS

Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

- Theme mass_affluent: no chunk on the theme for EDJ
- `MS:transcript`: hit MS-TR-2025Q3#15
- `SCHW:transcript`: hit SCHW-TR-2024Q4#33
- `EDJ:10-K`: hit EDJ-10K-2025#0, EDJ-10K-2025#10
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q2#20
- `RJF:transcript`: hit RJF-TR-2025Q1#11
- Retrieved: MS-TRADE-2026-10-21-IN-01#3, BAC-DECK-2025-investor-day#12, RJF-TRADE-2026-09-29-IN-01#3, SCHW-TRADE-2026-09-03-WM-01#0, EDJ-TRADE-2026-08-18-IN-01#2, MS-TRADE-2026-08-25-RB-01#2, BAC-DECK-2025-investor-day#8, RJF-TRADE-2026-08-26-IN-01#2, SCHW-TR-2024Q4#33, EDJ-10K-2025#0, MS-TR-2025Q3#15, BAC-TR-2026Q2#20, RJF-TR-2025Q1#11, SCHW-TRADE-2026-10-29-WM-01#0, EDJ-10Q-2025Q2#0, MS-10K-2025#144, MER-PR-web-advisor-development-program#1, RJF-10K-2025#33, SCHW-DECK-2026-investor-day#180, EDJ-TRADE-2026-08-18-IN-01#4, MS-10Q-2025Q2#0, BAC-DECK-2025-investor-day#9, RJF-10Q-2025Q2#0, SCHW-10K-2025#213, EDJ-10K-2025#10, MS-PR-2026-01-15-01#13, CERULLI-MASS-AFFLUENT-2026#0, CERULLI-MASS-AFFLUENT-2026#1, KITCES-WELLBEING-2023#107, KITCES-WELLBEING-2023#38

### Q11 - PASS

How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

- `MS:10-K`: hit MS-10K-2025#44
- `MS:supplement`: hit MS-SUPP-2025Q4#23
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-K`: hit EDJ-10K-2025#130, EDJ-10K-2025#41, EDJ-10K-2025#320
- `BAC:10-K#GWIM`: hit BAC-10K-2025#249
- `BAC:supplement#GWIM`: hit BAC-SUPP-2025Q4#57
- `RJF:10-K`: hit RJF-10K-2025#12
- `RJF:supplement`: hit RJF-SUPP-2025Q3#25
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
- Retrieved: EDJ-10Q-2026Q2#60, RJF-10K-2025#12, MS-DECK-2026-strategic-update#31, SCHW-10Q-2026Q2#71, BAC-TR-2026Q3#19, EDJ-10K-2025#130, RJF-TR-2025Q3#4, MS-SUPP-2025Q4#23, SCHW-10K-2025#197, BAC-PR-2026-01-14-01#12, EDJ-10Q-2025Q2#66, RJF-10Q-2026Q1#239, MS-10Q-2025Q2#59, SCHW-PR-2026-01-21-01#36, BAC-DECK-2025-investor-day#8, EDJ-10K-2025#41, RJF-PR-2026-04-22-01#1, MS-10K-2025#44, SCHW-DECK-2026-investor-day#305, BAC-SUPP-2025Q4#57, EDJ-10Q-2025Q2#64, RJF-DECK-2025-investor-day#142, MS-PR-2026-04-15-01#15, SCHW-TR-2025Q4#5, BAC-10K-2025#249, EDJ-10K-2025#320, RJF-SUPP-2025Q3#25, MS-TR-2026Q1#10, SCHW-MONTHLY-2026-01#8, BAC-10Q-2025Q2#93

### Q12 - PASS

How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

- Theme client_acquisition: no chunk on the theme for no firm (every named firm has one)
- `SCHW:transcript`: hit SCHW-TR-2025Q4#11, SCHW-TR-2026Q3#8, SCHW-TR-2025Q4#9
- `SCHW:10-K`: hit SCHW-10K-2025#13
- `SCHW:monthly`: hit SCHW-MONTHLY-2026-01#8
- `EDJ:10-K`: hit EDJ-10K-2025#8, EDJ-10K-2025#75, EDJ-10K-2025#87
- Retrieved: SCHW-TR-2025Q4#11, EDJ-10K-2025#8, SCHW-TR-2026Q3#8, EDJ-TRADE-2026-11-12-IN-01#1, SCHW-TRADE-2026-10-15-RB-01#2, EDJ-10K-2025#75, SCHW-PR-2026-10-15-01#7, EDJ-10Q-2025Q2#28, SCHW-10K-2025#13, EDJ-TRADE-2026-08-18-IN-01#6, SCHW-DECK-2026-investor-day#251, EDJ-10K-2025#87, SCHW-10Q-2025Q2#8, EDJ-10Q-2025Q2#110, SCHW-MONTHLY-2026-01#8, EDJ-TRADE-2026-09-30-WM-01#0, SCHW-TR-2025Q4#9, EDJ-10Q-2025Q2#100, SCHW-TRADE-2026-08-20-RB-01#3, EDJ-TRADE-2026-09-30-WM-01#1

### Q13 - PASS

How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

- `MS:transcript`: hit MS-TR-2024Q4#26, MS-TR-2025Q4#52, MS-TR-2025Q4#8
- `MS:10-K`: hit MS-10K-2025#168, MS-10K-2025#125, MS-10K-2025#169
- `MS:deck`: hit MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#28, MS-DECK-2026-strategic-update#31
- Expected `MS-10K-2025`: found MS-10K-2025#168, MS-10K-2025#125, MS-10K-2025#169
- Expected `MS-SUPP-2026Q3`: missing
- Expected `MS-TR-2025Q4`: found MS-TR-2025Q4#52, MS-TR-2025Q4#8
- Expected `MS-TR-2026Q2`: missing
- Expected `MS-TR-2026Q3`: missing
- Expected `MS-DECK-2026-strategic-update`: found MS-DECK-2026-strategic-update#32, MS-DECK-2026-strategic-update#28, MS-DECK-2026-strategic-update#31
- Retrieved: MS-10Q-2026Q2#61, MS-10K-2025#168, MS-SUPP-2025Q4#36, MS-DECK-2026-strategic-update#32, MS-TR-2024Q4#26, MS-TRADE-2026-09-16-IN-01#0, MS-PR-2026-07-15-01#5, MS-10Q-2026Q1#53, MS-10K-2025#125, MS-SUPP-2026Q1#42, MS-DECK-2026-strategic-update#28, MS-TR-2025Q4#52, MS-TRADE-2026-10-14-WM-01#1, MS-PR-2026-01-15-01#3, MS-10Q-2026Q1#49, MS-10K-2025#169, MS-SUPP-2026Q1#14, MS-DECK-2026-strategic-update#31, MS-TR-2025Q4#8, MS-TRADE-2026-10-21-IN-01#0

### Q14 - PASS

How does Raymond James's affiliation-choice model work commercially?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q1#23, RJF-TR-2026Q2#26, RJF-TR-2024Q4#8, RJF-TR-2026Q1#4, RJF-TR-2026Q2#5
- `RJF:press`: hit RJF-PR-web-affiliation-options#0, RJF-PR-web-affiliation-options#2, RJF-PR-web-affiliation-options#1, RJF-PR-web-independent-advisor#1
- Retrieved: RJF-PR-web-affiliation-options#0, RJF-TR-2026Q1#23, RJF-TRADE-2026-09-29-IN-01#1, RJF-10K-2025#91, RJF-10Q-2025Q4#142, RJF-DECK-2025-investor-day#125, RJF-PR-web-affiliation-options#2, RJF-TR-2026Q2#26, RJF-TRADE-2026-09-02-IN-01#1, RJF-10K-2025#10, RJF-10Q-2025Q2#370, RJF-PR-web-affiliation-options#1, RJF-TR-2024Q4#8, RJF-TRADE-2026-10-27-WM-01#0, RJF-10K-2025#462, RJF-PR-web-independent-advisor#1, RJF-TRADE-2026-09-29-WM-01#1, RJF-TR-2026Q1#4, RJF-TRADE-2026-10-27-WM-01#1, RJF-TR-2026Q2#5

### Q15 - FAIL

What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

- `SCHW:10-K`: hit SCHW-10K-2025#13, SCHW-10K-2025#512, SCHW-10K-2025#27
- `MS:10-K`: no hit
- `EDJ:10-K`: no hit
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: no hit
- Retrieved: SCHW-PR-2026-07-21-01#2, SCHW-TR-2026Q1#28, SCHW-DECK-2026-investor-day#130, SCHW-TRADE-2026-09-30-IN-01#0, SCHW-10K-2025#13, SCHW-10Q-2025Q2#9, SCHW-MONTHLY-2026-02#2, SCHW-PR-2026-10-15-01#2, SCHW-TR-2026Q2#24, SCHW-DECK-2026Q3#6, SCHW-TRADE-2026-11-02-RB-01#8, SCHW-10K-2025#512, SCHW-10Q-2026Q1#62, SCHW-MONTHLY-2026-04#9, SCHW-PR-2026-01-21-01#1, SCHW-TR-2025Q1#9, SCHW-DECK-2026Q2#20, SCHW-TRADE-2026-10-28-WM-01#1, SCHW-10K-2025#27, SCHW-10Q-2025Q2#88

### Q16 - PASS

What will receiving financial advice in the future look like for clients?

- `THEME:research`: hit CERULLI-AFFLUENT-FEE#1, WEALTHTENDER-ADVISOR-SEARCH-2025#62, WEALTHTENDER-ADVISOR-SEARCH-2025#37
- `THEME:regulatory`: not in corpus
- `THEME:survey`: not in corpus
- `MS:transcript`: hit MS-TR-2025Q1#15
- `SCHW:transcript`: hit SCHW-TR-2026Q2#13
- Retrieved: CERULLI-AFFLUENT-FEE#1, MS-TR-2025Q1#15, SCHW-TRADE-2026-10-15-RB-01#1, EDJ-10K-2025#88, BAC-TR-2025Q1#114, RJF-TR-2025Q1#83, MER-PR-web-becoming-a-merrill-lynch-advisor#5, WEALTHTENDER-ADVISOR-SEARCH-2025#62, MS-TRADE-2026-08-24-IN-01#1, SCHW-TR-2026Q2#13, EDJ-TRADE-2026-08-18-IN-01#1, BAC-10K-2025#516, RJF-PR-web-bank-and-credit-union-advisors#1, MER-TRADE-2026-10-02-IN-01#0, WEALTHTENDER-ADVISOR-SEARCH-2025#37, MS-10K-2025#423, SCHW-10K-2025#261, EDJ-10Q-2025Q2#57, BAC-PR-2026-01-14-01#9, RJF-10K-2025#91

### Q17 - PASS

What are these firms saying about AI in advice delivery, and who is claiming the most?

- `MS:transcript`: hit MS-TR-2025Q3#55
- `SCHW:transcript`: no hit
- `BAC:transcript#GWIM`: type only (qualifier not met): BAC-TR-2025Q2#12
- `RJF:transcript`: hit RJF-TR-2025Q4#6
- `MS:press`: no hit
- `SCHW:press`: hit SCHW-PR-2026-07-21-01#8
- `EDJ:press`: not in corpus
- `MER:press`: hit MER-PR-web-advisor-development-program#1
- `RJF:press`: no hit
- `MS:trade`: hit MS-TRADE-2026-11-15-AH-01#0
- `MER:trade`: hit MER-TRADE-2026-10-14-IN-01#0, MER-TRADE-2026-10-02-IN-01#0
- Expected `MS-10K-2025`: found MS-10K-2025#372
- Expected `MS-TR-2026Q2`: missing
- Expected `SCHW-TR-2026Q1`: missing
- Expected `SCHW-DECK-2026Q2`: missing
- Expected `BAC-TR-2026Q2`: missing
- Expected `BAC-TR-2026Q3`: missing
- Expected `RJF-TR-2025Q4`: found RJF-TR-2025Q4#6
- Expected `RJF-TR-2026Q1`: missing
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#26
- Retrieved: FINRA-OVERSIGHT-2026#84, SCHW-PR-2026-07-21-01#8, RJF-10K-2025#112, BAC-DECK-2026Q2#29, MS-TRADE-2026-11-15-AH-01#0, MER-TRADE-2026-10-14-IN-01#0, EDJ-10K-2025#26, MCK-ADVISOR-SHORTAGE-2025#28, SCHW-TRADE-2026-09-23-IN-01#0, RJF-TR-2025Q4#6, BAC-TR-2025Q2#12, MS-10K-2025#372, MER-PR-web-advisor-development-program#1, EDJ-TRADE-2026-09-24-IN-01#0, DELOITTE-AGENTIC-2026#0, SCHW-DECK-2026Q3#73, RJF-DECK-2025-investor-day#121, BAC-10K-2025#1078, MS-TR-2025Q3#55, MER-TRADE-2026-10-02-IN-01#0

### Q18 - PASS

Where is the industry heading on fee structures and pricing transparency?

- `MS:adv`: hit MS-ADV-2026#127
- `SCHW:adv`: hit SCHW-ADV-2026#32
- `EDJ:adv`: hit EDJ-ADV-2026#108
- `MER:adv`: hit MER-ADV-2026#226
- `RJF:adv`: hit RJF-ADV-2026#33
- `THEME:regulatory`: not in corpus
- `THEME:research`: hit MCK-SIGNAL-SELLOFF-2026#9, WEALTHTENDER-ADVISOR-SEARCH-2025#57, WEALTHTENDER-ADVISOR-SEARCH-2025#21
- Retrieved: MCK-SIGNAL-SELLOFF-2026#9, MS-ADV-2026#127, RJF-ADV-2026#33, SCHW-ADV-2026#32, EDJ-10K-2025#55, BAC-10Q-2026Q1#31, MER-PR-2026-09-15-01#2, WEALTHTENDER-ADVISOR-SEARCH-2025#57, MS-TRADE-2026-10-26-IN-01#3, RJF-10K-2025#100, SCHW-TRADE-2026-09-30-IN-01#4, EDJ-ADV-2026#108, BAC-TR-2025Q4#118, MER-ADV-2026#226, WEALTHTENDER-ADVISOR-SEARCH-2025#21, MS-TR-2025Q4#19, RJF-TR-2026Q1#48, SCHW-10K-2025#14, EDJ-TRADE-2026-08-18-IN-01#6, BAC-10K-2025#246

### Q19 - FAIL

How should the preferences of younger investors shape Edward Jones's offerings?

- Theme younger_investors: no chunk on the theme for EDJ
- `THEME:research`: hit CERULLI-GWT-2025#1, BOFA-PB-STUDY-2026#15, BOFA-PB-STUDY-2024#0, BOFA-PB-STUDY-2024#7
- `THEME:survey`: not in corpus
- `MS:press`: no hit
- `SCHW:press`: no hit
- `RJF:press`: no hit
- `MER:press`: no hit
- Retrieved: EDJ-10K-2025#304, EDJ-10Q-2025Q2#28, EDJ-TRADE-2026-08-18-IN-01#1, EDJ-10K-2025#56, EDJ-10Q-2026Q2#39, EDJ-TRADE-2026-08-18-IN-01#4, EDJ-10K-2025#16, EDJ-10Q-2025Q2#17, EDJ-TRADE-2026-08-18-IN-01#5, EDJ-10Q-2025Q3#107, EDJ-10Q-2025Q3#19, EDJ-10Q-2025Q3#68, EDJ-10Q-2026Q1#78, EDJ-10Q-2026Q2#11, EDJ-10Q-2026Q2#30, CERULLI-GWT-2025#1, BOFA-PB-STUDY-2026#15, BOFA-PB-STUDY-2024#0, BOFA-PB-STUDY-2024#7

### Q20 - PASS

What evidence is there about how clients under 40 choose a financial advisor?

- `THEME:survey`: not in corpus
- `THEME:research`: hit UBS-NEXTGEN-2026#83, KITCES-WELLBEING-2023#68, CERULLI-AFFLUENT-FEE#0
- Expected `UBS-NEXTGEN-2026`: found UBS-NEXTGEN-2026#83
- Expected `CERULLI-GWT-2025`: missing
- Expected `FINRAF-INVESTORS-2025`: missing
- Expected `KITCES-WELLBEING-2023`: found KITCES-WELLBEING-2023#68
- Expected `BOFA-PB-STUDY-2026`: missing
- Expected `NM-PP-2026`: missing
- Expected `WEALTHTENDER-ADVISOR-SEARCH-2025`: missing
- Retrieved: UBS-NEXTGEN-2026#83, EDJ-10K-2025#19, SCHW-DECK-2026-investor-day#306, RJF-TR-2026Q1#5, MS-TR-2026Q2#10, BAC-DECK-2025-investor-day#8, MER-TRADE-2026-10-14-IN-01#0, KITCES-WELLBEING-2023#68, EDJ-TRADE-2026-11-12-IN-01#1, SCHW-TR-2026Q1#68, RJF-TRADE-2026-11-06-IN-01#2, MS-TRADE-2026-10-30-IN-01#0, BAC-PR-2026-07-14-01#10, MER-PR-web-advisor-development-program#2, CERULLI-AFFLUENT-FEE#0, EDJ-10Q-2026Q1#60, SCHW-TRADE-2026-11-02-RB-01#3, RJF-10K-2025#91, MS-10K-2025#44, BAC-TR-2026Q3#19

### Q21 - PASS

What do we know about the generational wealth transfer, and how are these five preparing for it?

- Theme wealth_transfer: no chunk on the theme for no firm (every named firm has one)
- `THEME:research`: hit CERULLI-GWT-2025#24, CERULLI-GWT-2025#2, BOFA-PB-STUDY-2026#16, UBS-NEXTGEN-2026#6
- `MS:transcript`: hit MS-TR-2026Q3#25
- `SCHW:transcript`: hit SCHW-TR-2026Q3#11
- `EDJ:10-K`: hit EDJ-10K-2025#56, EDJ-10K-2025#304, EDJ-10K-2025#207
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q2#21
- `RJF:transcript`: hit RJF-TR-2025Q3#62
- Retrieved: MS-TRADE-2026-08-22-RB-01#19, SCHW-DECK-2026Q3#24, RJF-TRADE-2026-09-29-IN-01#3, EDJ-10K-2025#56, BAC-PR-2026-01-14-01#12, MS-TR-2026Q3#25, SCHW-TRADE-2026-10-29-WM-01#3, RJF-TRADE-2026-11-06-IN-01#3, EDJ-10K-2025#304, BAC-TR-2026Q2#21, MS-10K-2025#206, SCHW-TR-2026Q3#11, RJF-TR-2025Q3#62, EDJ-10Q-2025Q2#67, MER-TRADE-2026-09-29-RB-01#5, MS-10Q-2025Q2#226, SCHW-DECK-2026Q3#73, RJF-10K-2025#26, EDJ-TRADE-2026-08-18-IN-01#1, MER-PR-web-becoming-a-merrill-lynch-advisor#1, MS-PR-2026-01-15-01#16, SCHW-PR-2026-07-21-01#8, RJF-PR-web-independent-ria-custody-services#0, EDJ-10K-2025#207, BAC-10K-2025#246, MS-SUPP-2025Q4#23, CERULLI-GWT-2025#24, CERULLI-GWT-2025#2, BOFA-PB-STUDY-2026#16, UBS-NEXTGEN-2026#6

### Q22 - PASS

Net new assets by quarter for each of the five, with each firm's own definition of the metric.

- `MS:supplement`: hit MS-SUPP-2026Q1#7
- `SCHW:monthly`: hit SCHW-MONTHLY-2026-02#2
- `SCHW:supplement`: not in corpus
- `EDJ:10-Q`: hit EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q2#67, EDJ-10Q-2026Q2#62
- `BAC:supplement#GWIM`: hit BAC-SUPP-2025Q4#57
- `RJF:supplement`: hit RJF-SUPP-2025Q3#9
- `MS:press`: hit MS-PR-2026-04-15-01#22
- `RJF:press`: hit RJF-PR-2026-01-28-01#1
- Expected `EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10K-2025#130`: missing
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14, MS-10Q-2026Q2#57, MS-10Q-2026Q1#48, MS-10Q-2025Q3#56, MS-10Q-2025Q2#56, MS-PR-2026-01-15-01#2`: missing
- Expected `MS-SUPP-2026Q1#42, MS-10K-2025#166`: missing
- Expected `SCHW-PR-2026-01-21-01#2, SCHW-PR-2026-07-21-01#2, SCHW-DECK-2026Q3#7, SCHW-10Q-2026Q2#16, SCHW-10Q-2026Q1#16, SCHW-10Q-2025Q3#16, SCHW-10Q-2025Q2#16`: missing
- Expected `SCHW-10K-2025#122, SCHW-10K-2025#119, SCHW-DECK-2026Q3#20`: missing
- Expected `RJF-PR-2026-07-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-01-28-01#3, RJF-PR-2025-10-22-01#4, RJF-10Q-2026Q2#305, RJF-10Q-2026Q1#298, RJF-10Q-2025Q4#236, RJF-10Q-2025Q2#294`: missing
- Expected `RJF-10Q-2026Q2#306, RJF-SUPP-2026Q1#43`: missing
- Expected `BAC-TR-2026Q3#19, BAC-PR-2026-10-14-01#11`: found BAC-TR-2026Q3#19
- Retrieved: SCHW-TR-2026Q1#3, MS-DECK-2026-strategic-update#31, RJF-TR-2025Q1#6, EDJ-10Q-2025Q2#66, BAC-PR-2026-04-15-01#11, SCHW-PR-2026-04-16-01#3, MS-SUPP-2026Q1#7, RJF-10K-2025#223, EDJ-10K-2025#207, BAC-TR-2026Q3#19, SCHW-DECK-2026Q3#73, MS-TR-2024Q4#24, RJF-10Q-2026Q1#323, EDJ-10Q-2025Q2#67, BAC-10K-2025#248, SCHW-10K-2025#136, MS-PR-2026-04-15-01#22, RJF-PR-2026-01-28-01#1, EDJ-10K-2025#182, BAC-10Q-2026Q1#74, SCHW-10Q-2026Q1#19, MS-10K-2025#165, RJF-SUPP-2025Q3#9, EDJ-10Q-2026Q2#62, BAC-DECK-2025-investor-day#10, SCHW-MONTHLY-2026-02#2, MS-10Q-2026Q2#58, RJF-DECK-2025-investor-day#75, EDJ-10K-2025#54, BAC-SUPP-2025Q4#57

### Q23 - PASS

Advisor headcount over the last eight quarters across the five.

- `MS:supplement`: no hit
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-Q`: hit EDJ-10Q-2025Q2#66, EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q2#82
- `EDJ:10-K`: hit EDJ-10K-2025#58, EDJ-10K-2025#70, EDJ-10K-2025#202
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `RJF:press`: hit RJF-PR-web-affiliation-options#2
- Expected `EDJ-10K-2025`: found EDJ-10K-2025#58, EDJ-10K-2025#70, EDJ-10K-2025#202
- Expected `EDJ-10Q-2025Q2`: found EDJ-10Q-2025Q2#66
- Expected `EDJ-10Q-2025Q3`: missing
- Expected `EDJ-10Q-2026Q1`: missing
- Expected `EDJ-10Q-2026Q2`: found EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q2#82
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
- Retrieved: MS-TR-2025Q4#4, RJF-TR-2025Q3#8, EDJ-10Q-2025Q2#66, SCHW-TR-2026Q1#8, BAC-DECK-2025-investor-day#8, MS-10K-2025#44, RJF-10K-2025#12, EDJ-10K-2025#58, SCHW-10Q-2026Q1#60, MER-PR-web-advisor-development-program#0, MS-10Q-2026Q1#19, RJF-10Q-2026Q1#239, EDJ-10Q-2026Q2#60, SCHW-10K-2025#197, BAC-10K-2025#247, MS-DECK-2026-strategic-update#31, RJF-PR-web-affiliation-options#2, EDJ-10K-2025#70, SCHW-PR-2026-07-21-01#37, BAC-TR-2026Q2#63, MS-PR-2026-10-14-01#5, RJF-DECK-2025-investor-day#131, EDJ-10Q-2026Q2#82, SCHW-DECK-2026Q3#73, MER-PR-web-becoming-a-merrill-lynch-advisor#0, MS-TR-2025Q4#8, RJF-TR-2025Q3#4, EDJ-10K-2025#202, SCHW-TR-2024Q4#3, BAC-TR-2026Q3#19

### Q24 - PASS

Client assets per advisor across the five -- and is that comparison even valid?

- `MS:supplement`: hit MS-SUPP-2026Q1#14
- `SCHW:10-K`: hit SCHW-10K-2025#42
- `EDJ:10-K`: hit EDJ-10K-2025#23, EDJ-10K-2025#22, EDJ-10K-2025#267
- `BAC:supplement#GWIM`: hit BAC-SUPP-2025Q4#57
- `RJF:supplement`: hit RJF-SUPP-2026Q2#43
- Expected `EDJ-10K-2025#130`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38`: missing
- Retrieved: SCHW-TR-2025Q1#9, MS-DECK-2026-strategic-update#28, RJF-TR-2025Q1#4, EDJ-10K-2025#23, BAC-TR-2026Q3#19, SCHW-DECK-2026-investor-day#25, MS-TR-2025Q4#4, RJF-10Q-2026Q1#244, EDJ-10Q-2025Q2#102, BAC-DECK-2025-investor-day#8, SCHW-PR-2026-07-21-01#54, MS-PR-2026-01-15-01#0, RJF-10K-2025#41, EDJ-10K-2025#22, BAC-10K-2025#249, SCHW-MONTHLY-2026-04#6, MS-SUPP-2026Q1#14, RJF-PR-2026-07-22-01#98, EDJ-10Q-2026Q2#43, MER-PR-2026-09-15-01#2, SCHW-10K-2025#42, MS-10K-2025#109, RJF-SUPP-2026Q2#43, EDJ-10K-2025#267, BAC-10Q-2026Q1#75, SCHW-10Q-2026Q1#19, MS-10Q-2025Q2#156, RJF-DECK-2025-investor-day#30, EDJ-10Q-2025Q2#28, BAC-SUPP-2025Q4#57

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
- `EDJ:adv`: hit EDJ-ADV-2026#122, EDJ-ADV-2026#92
- `RJF:adv`: hit RJF-ADV-2026#114
- Expected `RJF-10K-2025#10, RJF-10K-2025#11`: missing
- Expected `EDJ-10K-2025#30, EDJ-10K-2025#264`: missing
- Expected `MS-10K-2025#153`: missing
- Expected `SCHW-10Q-2026Q2#25`: missing
- Retrieved: RJF-ADV-2026#114, MER-ADV-2026#449, MS-ADV-2026#198, EDJ-10K-2025#314, SCHW-TRADE-2026-10-23-WM-01#4, RJF-PR-web-affiliation-options#2, MER-TRADE-2026-09-11-WM-01#1, MS-TRADE-2026-11-04-RB-01#4, EDJ-ADV-2026#122, SCHW-ADV-2026#45, RJF-10Q-2025Q4#199, BAC-DECK-2025-investor-day#8, MS-10K-2025#420, EDJ-10Q-2026Q1#60, SCHW-TR-2026Q1#48, RJF-10K-2025#175, MER-PR-2026-09-15-01#2, MS-10Q-2026Q2#454, EDJ-TRADE-2026-11-12-IN-01#1, SCHW-10K-2025#512, RJF-TR-2025Q3#20, BAC-10K-2025#246, MS-TR-2026Q3#58, EDJ-10K-2025#22, SCHW-10Q-2025Q2#170, RJF-TRADE-2026-10-16-WM-01#1, MER-ADV-2026#511, MS-DECK-2026-strategic-update#31, EDJ-ADV-2026#92, SCHW-DECK-2026-investor-day#306

### Q26 - PASS

What's new on Raymond James in the last 90 days?

- `RJF:*`: hit RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-IN-01#4, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-29-IN-01#2, RJF-TRADE-2026-09-29-WM-01#1, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-26-IN-01#2
- Window: 2026-08-19 to 2026-11-17
- Retrieved: RJF-TRADE-2026-11-06-IN-01#1, RJF-TRADE-2026-11-05-IN-01#0, RJF-TRADE-2026-11-04-IN-01#2, RJF-TRADE-2026-10-29-WM-01#1, RJF-TRADE-2026-10-16-WM-01#0, RJF-TRADE-2026-10-08-WM-01#0, RJF-TRADE-2026-09-29-IN-01#0, RJF-TRADE-2026-09-29-IN-01#4, RJF-TRADE-2026-09-29-WM-01#0, RJF-TRADE-2026-09-29-IN-01#2, RJF-TRADE-2026-09-29-WM-01#1, RJF-TRADE-2026-09-24-IN-01#0, RJF-TRADE-2026-09-16-WM-01#0, RJF-TRADE-2026-09-02-IN-01#0, RJF-TRADE-2026-08-26-IN-01#2

### Q27 - PASS

What has changed at Merrill since the start of the year?

- `MER:*`: hit MER-TRADE-2026-11-12-IN-01#2, MER-TRADE-2026-11-03-WM-01#0, MER-TRADE-2026-10-14-IN-01#2, BAC-DECK-2026Q3#31, MER-PR-2026-09-15-01#0, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-TR-2026Q1#26, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-SUPP-2025Q4#53, BAC-PR-2026-01-14-01#13, BAC-SUPP-2025Q4#54
- `BAC:*#GWIM`: hit BAC-DECK-2026Q3#31, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-TR-2026Q1#26, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-SUPP-2025Q4#53, BAC-PR-2026-01-14-01#13, BAC-SUPP-2025Q4#54
- Expected `MER-PR-2026-09-15-01`: found MER-PR-2026-09-15-01#0
- Expected `MER-PR-web-advisor-development-program`: missing
- Expected `MER-PR-web-becoming-a-merrill-lynch-advisor`: missing
- Expected `BAC-TR-2026Q1`: found BAC-TR-2026Q1#26
- Expected `BAC-TR-2026Q2`: found BAC-TR-2026Q2#21, BAC-TR-2026Q2#20
- Expected `BAC-TR-2026Q3`: missing
- Expected `BAC-SUPP-2026Q1`: missing
- Expected `BAC-SUPP-2026Q2`: missing
- Expected `BAC-SUPP-2026Q3`: missing
- Retrieved: MER-TRADE-2026-11-12-IN-01#2, MER-TRADE-2026-11-03-WM-01#0, MER-TRADE-2026-10-14-IN-01#2, BAC-DECK-2026Q3#31, MER-PR-2026-09-15-01#0, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#20, BAC-TR-2026Q2#20, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-TR-2026Q1#26, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-SUPP-2025Q4#53, BAC-PR-2026-01-14-01#13, BAC-SUPP-2025Q4#54

### Q28 - PASS

What is Edward Jones's advisor attrition rate compared to Merrill's?

- Theme advisor_recruiting: no chunk on the theme for no firm (every named firm has one)
- `EDJ:10-K`: hit EDJ-10K-2025#71, EDJ-10K-2025#27, EDJ-10K-2025#58
- `BAC:supplement#GWIM`: no hit
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- Expected `EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q3#68, EDJ-10Q-2025Q3#70`: found EDJ-10Q-2025Q3#70, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q3#68
- Expected `EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q3#69`: found EDJ-10Q-2025Q2#66
- Expected `BAC-TR-2026Q2#63, BAC-TR-2026Q1#80, BAC-TR-2026Q1#81`: found BAC-TR-2026Q2#63
- Expected `EDJ-10K-2025#130, EDJ-10Q-2026Q2#60`: missing
- Retrieved: EDJ-10Q-2025Q3#70, BAC-TR-2026Q2#63, EDJ-10Q-2025Q2#66, BAC-TR-2026Q3#19, EDJ-10K-2025#71, BAC-DECK-2025-investor-day#8, EDJ-10Q-2025Q2#67, MER-PR-web-advisor-development-program#2, EDJ-10K-2025#27, BAC-10K-2025#246, EDJ-10Q-2025Q2#64, BAC-TR-2026Q1#26, EDJ-10K-2025#58, BAC-DECK-2025-investor-day#18, EDJ-10Q-2025Q3#68, MER-PR-web-becoming-a-merrill-lynch-advisor#1, EDJ-10Q-2026Q1#60, KITCES-WELLBEING-2023#23, KITCES-WELLBEING-2023#17, MCK-ADVISOR-SHORTAGE-2025#25

### Q29 - PASS

What does Morgan Stanley pay its financial advisors?

- `MS:10-K#Wealth Management`: hit MS-10K-2025#170
- `MS:trade`: hit MS-TRADE-2026-08-25-RB-01#0, MS-TRADE-2026-08-26-RB-01#0, MS-TRADE-2026-08-26-RB-01#1, MS-TRADE-2026-11-04-RB-01#5
- Expected `MS-10K-2025#153`: found MS-10K-2025#153
- Expected `MS-10K-2025#128, MS-10K-2025#170`: found MS-10K-2025#170, MS-10K-2025#128
- Retrieved: MS-10Q-2026Q2#20, MS-10K-2025#170, MS-TRADE-2026-08-25-RB-01#0, MS-TR-2025Q4#22, MS-PR-2026-10-14-01#5, MS-SUPP-2025Q4#36, MS-10Q-2025Q3#64, MS-10K-2025#128, MS-TRADE-2026-08-26-RB-01#0, MS-TR-2025Q1#54, MS-PR-2026-04-15-01#14, MS-SUPP-2026Q1#25, MS-10Q-2026Q2#64, MS-10K-2025#153, MS-TRADE-2026-08-26-RB-01#1, MS-TR-2025Q3#89, MS-PR-2026-07-15-01#17, MS-SUPP-2025Q4#42, MS-10Q-2025Q3#19, MS-TRADE-2026-11-04-RB-01#5

### Q30 - PASS

What is Merrill's standalone profitability?

- `BAC:10-K#GWIM`: hit BAC-10K-2025#244, BAC-10K-2025#246, BAC-10K-2025#247
- Expected `BAC-PR-2026-01-14-01#12`: missing
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246, BAC-10K-2025#247
- Retrieved: BAC-TR-2025Q3#26, BAC-DECK-2026Q1#26, BAC-PR-2026-04-15-01#10, BAC-10K-2025#244, BAC-10Q-2025Q2#90, BAC-SUPP-2025Q4#53, MER-TRADE-2026-10-02-IN-01#1, BAC-TR-2026Q2#21, BAC-DECK-2026Q2#19, BAC-PR-2026-07-14-01#10, BAC-10K-2025#246, BAC-10Q-2025Q3#90, BAC-SUPP-2026Q1#43, MER-TRADE-2026-10-14-IN-01#1, BAC-TR-2026Q1#26, BAC-DECK-2026Q3#30, BAC-PR-2026-10-14-01#11, BAC-10K-2025#247, BAC-SUPP-2026Q2#52, BAC-TR-2026Q2#20

