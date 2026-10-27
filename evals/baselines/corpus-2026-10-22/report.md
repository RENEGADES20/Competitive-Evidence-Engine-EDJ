# Eval run corpus-2026-10-22-20261027-164734

Snapshot `corpus-2026-10-22` | commit `58ee0cf` | k=20 | min coverage 0.5 | as of 2026-10-27 | mode mock | 0 real calls

**PASS 25 | FAIL 3 | NOT_EVALUATED 2**

**Tier-1 recall**: documents 0.809, passages 0.347 (mean over the 9 of 18 tier-1 questions with an answer key; the rest n/a until #56)  
**Refusal accuracy**: gap questions (Q24, Q25, Q28, Q29, Q30) 4/5; all questions with a key 9/10

Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the corpus; PASS when coverage of the available patterns >= min coverage.

Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window.

| Q | Tier | Use case | Expected | Firms (mode) | Hits | Coverage | Recall docs | Passages | Refusal | Forbidden | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | entity_brief | answer | MS (entity) | 20 | 3/3 | 7/9 | 2/8 | ok | 0 | PASS |
| Q2 | 1 | entity_brief | answer | RJF (entity) | 20 | 3/3 | - | - | - | 0 | PASS |
| Q3 | 1 | entity_brief | answer | SCHW (entity) | 20 | 3/3 | - | - | - | 0 | PASS |
| Q4 (trap) | 1 | entity_brief | answer | MER (entity) | 8 | 2/2 | 4/5 | 4/7 | ok | 0 | PASS |
| Q5 | 1 | entity_brief | answer | MS (entity) | 13 | 2/2 | - | - | - | 0 | PASS |
| Q6 | 1 | entity_brief | answer | RJF (entity) | 20 | 2/3 | - | - | - | 0 | PASS |
| Q7 | 2 | head_to_head | answer | MS, MER, RJF (entity) | 20 | 6/6 | - | - | - | 0 | PASS |
| Q8 | 2 | head_to_head | answer | SCHW, RJF (entity) | 20 | 3/4 | - | - | - | 0 | PASS |
| Q9 | 3 | head_to_head | answer | MS, MER (entity) | 20 | 3/5 | - | - | - | 0 | PASS |
| Q10 | 3 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 5/5 | - | - | - | 0 | PASS |
| Q11 | 1 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 7/8 | 7/8 | 3/10 | ok | 0 | PASS |
| Q12 | 3 | mechanism | answer_with_boundary | SCHW, EDJ (entity) | 20 | 3/3 | - | - | - | 0 | PASS |
| Q13 | 1 | mechanism | answer | MS (entity) | 20 | 2/2 | - | - | - | 0 | PASS |
| Q14 | 3 | mechanism | answer | RJF (entity) | 14 | 3/3 | - | - | - | 0 | PASS |
| Q15 | 3 | mechanism | answer | SCHW (entity) | 20 | 1/5 | - | - | - | 0 | FAIL |
| Q16 | 3 | theme_scan | answer | none (theme) | 20 | 2/2 | - | - | - | 0 | PASS |
| Q17 | 1 | theme_scan | answer | none (theme) | 20 | 6/7 | - | - | - | 0 | PASS |
| Q18 | 3 | theme_scan | answer | none (theme) | 20 | - | - | - | - | 0 | NOT_EVALUATED |
| Q19 | 3 | segment_evidence | answer_with_boundary | EDJ (entity) | 12 | 0/3 | - | - | - | 0 | FAIL |
| Q20 | 1 | segment_evidence | answer | none (theme) | 20 | - | - | - | - | 0 | NOT_EVALUATED |
| Q21 | 2 | segment_evidence | answer | none (theme) | 20 | 3/5 | - | - | - | 0 | PASS |
| Q22 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 4/6 | 8/33 | 0/8 | ok | 0 | PASS |
| Q23 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 5/7 | - | - | - | 0 | PASS |
| Q24 | 3 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 3/5 | 3/5 | 0/4 | ok | 0 | PASS |
| Q25 | 1 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 20 | 5/5 | 3/4 | 0/4 | ok | 0 | PASS |
| Q26 | 1 | recency | answer | RJF (entity) | 8 | 1/1 | 1/1 | 1/1 | ok | 0 | PASS |
| Q27 (trap) | 1 | recency | answer | MER (entity) | 20 | 2/2 | - | - | - | 0 | PASS |
| Q28 | 1 | honest_miss | gap_with_adjacent | EDJ, MER (entity) | 17 | 2/3 | 5/6 | 2/4 | ok | 0 | PASS |
| Q29 | 1 | honest_miss | gap_with_adjacent | MS (entity) | 20 | 1/1 | 1/1 | 1/2 | FAIL (1) | 0 | FAIL |
| Q30 (trap) | 1 | honest_miss | gap_with_adjacent | MER (entity) | 20 | 1/1 | 2/2 | 0/2 | ok | 0 | PASS |

## Per question

### Q1 - PASS

What is Morgan Stanley's strategy to increase their net new assets?

- `MS:transcript`: hit MS-TR-2026Q2#15, MS-TR-2026Q3#9, MS-TR-2026Q1#16, MS-TR-2026Q2#22, MS-TR-2026Q2#13
- `MS:10-K#Wealth Management`: hit MS-10K-2025#165, MS-10K-2025#180
- `MS:deck`: not in corpus
- `MS:supplement`: hit MS-SUPP-2026Q1#46, MS-SUPP-2026Q1#28, MS-SUPP-2026Q1#22, MS-SUPP-2026Q3#21
- Expected `MS-TR-2026Q2#3`: missing
- Expected `MS-TR-2026Q2#13, MS-TR-2026Q2#15`: found MS-TR-2026Q2#15, MS-TR-2026Q2#13
- Expected `MS-TR-2026Q3#2, MS-TR-2026Q3#8`: missing
- Expected `MS-TR-2026Q1#2, MS-TR-2026Q1#7, MS-TR-2026Q1#8`: missing
- Expected `MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5`: found MS-PR-2026-10-14-01#5
- Expected `MS-10K-2025#125`: missing
- Expected `MS-10K-2025#127, MS-10K-2025#164, MS-10K-2025#166`: missing
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14`: missing
- Retrieved: MS-TR-2026Q2#15, MS-10Q-2026Q1#18, MS-10K-2025#165, MS-SUPP-2026Q1#46, MS-PR-2026-01-15-01#3, MS-TR-2026Q3#9, MS-10Q-2026Q2#58, MS-10K-2025#180, MS-SUPP-2026Q1#28, MS-PR-2026-04-15-01#2, MS-TR-2026Q1#16, MS-10Q-2025Q2#57, MS-10K-2025#92, MS-SUPP-2026Q1#22, MS-PR-2026-10-14-01#5, MS-TR-2026Q2#22, MS-10Q-2025Q2#74, MS-SUPP-2026Q3#21, MS-TR-2026Q2#13, MS-10Q-2026Q1#61

### Q2 - PASS

How is Raymond James positioning itself to recruit advisors away from the wirehouses?

- `RJF:transcript`: hit RJF-TR-2026Q1#34, RJF-TR-2026Q1#14, RJF-TR-2026Q1#5, RJF-TR-2026Q2#32, RJF-TR-2026Q2#37
- `RJF:10-K`: hit RJF-10K-2025#91, RJF-10K-2025#175, RJF-10K-2025#334
- `RJF:press`: hit RJF-PR-2025-10-22-01#1, RJF-PR-2026-01-28-01#38, RJF-PR-2026-01-28-01#71
- `RJF:trade`: not in corpus
- Retrieved: RJF-TR-2026Q1#34, RJF-10K-2025#91, RJF-10Q-2026Q1#307, RJF-PR-2025-10-22-01#1, RJF-SUPP-2026Q1#44, RJF-TR-2026Q1#14, RJF-10K-2025#175, RJF-10Q-2026Q2#316, RJF-PR-2026-01-28-01#38, RJF-SUPP-2026Q2#45, RJF-TR-2026Q1#5, RJF-10K-2025#334, RJF-10Q-2025Q2#131, RJF-PR-2026-01-28-01#71, RJF-SUPP-2026Q1#14, RJF-TR-2026Q2#32, RJF-10Q-2025Q4#118, RJF-SUPP-2026Q2#14, RJF-TR-2026Q2#37, RJF-10Q-2025Q4#199

### Q3 - PASS

What is Schwab's strategy for its RIA custody business?

- `SCHW:transcript`: hit SCHW-TR-2026Q3#2, SCHW-TR-2026Q3#7, SCHW-TR-2026Q2#5, SCHW-TR-2026Q1#39, SCHW-TR-2026Q3#3
- `SCHW:10-K#Advisor Services`: hit SCHW-10K-2025#26
- `SCHW:deck`: hit SCHW-DECK-2026Q2#14, SCHW-DECK-2026Q3#11, SCHW-DECK-2026Q3#71
- Retrieved: SCHW-TR-2026Q3#2, SCHW-10K-2025#11, SCHW-10Q-2026Q2#342, SCHW-DECK-2026Q2#14, SCHW-PR-2026-04-16-01#7, SCHW-TR-2026Q3#7, SCHW-10K-2025#26, SCHW-10Q-2026Q2#343, SCHW-DECK-2026Q3#11, SCHW-PR-2026-07-21-01#2, SCHW-TR-2026Q2#5, SCHW-10K-2025#13, SCHW-10Q-2025Q2#310, SCHW-DECK-2026Q3#71, SCHW-PR-2026-01-21-01#7, SCHW-TR-2026Q1#39, SCHW-10Q-2026Q2#30, SCHW-PR-2026-04-16-01#3, SCHW-TR-2026Q3#3, SCHW-10Q-2026Q1#25

### Q4 - PASS

What is Merrill's advisor growth strategy, and how has it changed?

- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#13, BAC-TR-2026Q2#14, BAC-TR-2026Q1#20
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `MER:press`: hit BAC-PR-2026-07-14-01#10, BAC-PR-2026-01-14-01#12, BAC-PR-2026-04-15-01#10, BAC-PR-2026-10-14-01#11
- `MER:trade`: not in corpus
- Expected `BAC-TR-2026Q1#20`: found BAC-TR-2026Q1#20
- Expected `BAC-TR-2026Q1#48`: missing
- Expected `BAC-TR-2026Q2#13, BAC-TR-2026Q2#14`: found BAC-TR-2026Q2#14
- Expected `BAC-TR-2026Q2#38`: missing
- Expected `BAC-TR-2026Q3#13`: found BAC-TR-2026Q3#13
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: found BAC-10K-2025#246
- Expected `BAC-10Q-2026Q2#88, BAC-10Q-2026Q2#89, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91`: missing
- Retrieved: BAC-TR-2026Q3#13, BAC-10K-2025#246, BAC-TR-2026Q2#14, BAC-PR-2026-07-14-01#10, BAC-TR-2026Q1#20, BAC-PR-2026-01-14-01#12, BAC-PR-2026-04-15-01#10, BAC-PR-2026-10-14-01#11

### Q5 - PASS

Where is Morgan Stanley investing in technology for its advisors?

- `MS:transcript`: hit MS-TR-2026Q3#10, MS-TR-2026Q3#5, MS-TR-2026Q1#29, MS-TR-2026Q3#13, MS-TR-2026Q1#27, MS-TR-2026Q2#11, MS-TR-2026Q1#4, MS-TR-2026Q2#30
- `MS:10-K`: hit MS-10K-2025#25, MS-10K-2025#76, MS-10K-2025#109
- `MS:deck`: not in corpus
- `MS:trade`: not in corpus
- Retrieved: MS-TR-2026Q3#10, MS-10K-2025#25, MS-10Q-2026Q2#524, MS-TR-2026Q3#5, MS-10K-2025#76, MS-PR-2026-10-14-01#5, MS-TR-2026Q1#29, MS-10K-2025#109, MS-TR-2026Q3#13, MS-TR-2026Q1#27, MS-TR-2026Q2#11, MS-TR-2026Q1#4, MS-TR-2026Q2#30

### Q6 - PASS

What has Raymond James said about its affiliation models, and has the mix shifted?

- `RJF:10-K#Private Client Group`: type only (qualifier not met): RJF-10K-2025#462, RJF-10K-2025#320, RJF-10K-2025#639
- `RJF:transcript`: hit RJF-TR-2026Q1#30, RJF-TR-2026Q1#29, RJF-TR-2026Q2#10, RJF-TR-2026Q2#26, RJF-TR-2026Q2#22, RJF-TR-2026Q1#31
- `RJF:press`: hit RJF-PR-2026-01-28-01#6, RJF-PR-2026-04-22-01#5
- Retrieved: RJF-TR-2026Q1#30, RJF-10K-2025#462, RJF-10Q-2026Q1#267, RJF-PR-2026-01-28-01#6, RJF-TR-2026Q1#29, RJF-10K-2025#320, RJF-10Q-2025Q4#259, RJF-PR-2026-04-22-01#5, RJF-TR-2026Q2#10, RJF-10K-2025#639, RJF-10Q-2026Q1#243, RJF-TR-2026Q2#26, RJF-10Q-2026Q1#328, RJF-TR-2026Q2#22, RJF-10Q-2026Q2#251, RJF-TR-2026Q1#31, RJF-10Q-2026Q2#340, RJF-10Q-2025Q2#391, RJF-10Q-2025Q4#199, RJF-10Q-2026Q2#246

### Q7 - PASS

How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

- `MS:transcript`: hit MS-TR-2026Q1#16, MS-TR-2026Q2#20
- `MS:10-K`: hit MS-10K-2025#51, MS-10K-2025#112, MS-10K-2025#23
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#13, BAC-TR-2026Q1#20, BAC-TR-2026Q2#14
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `RJF:transcript`: hit RJF-TR-2026Q2#38, RJF-TR-2026Q1#17
- `RJF:10-K`: hit RJF-10K-2025#90, RJF-10K-2025#89
- `MS:trade`: not in corpus
- `MER:trade`: not in corpus
- `RJF:trade`: not in corpus
- Retrieved: RJF-TR-2026Q2#38, MS-10K-2025#51, BAC-TR-2026Q3#13, RJF-10K-2025#90, MS-TR-2026Q1#16, BAC-PR-2026-07-14-01#10, RJF-10Q-2025Q4#199, MS-10Q-2026Q1#125, BAC-10K-2025#246, RJF-PR-2026-07-22-01#103, MS-10K-2025#112, BAC-TR-2026Q1#20, RJF-SUPP-2026Q1#44, MS-TR-2026Q2#20, BAC-PR-2026-01-14-01#12, RJF-TR-2026Q1#17, MS-10Q-2025Q2#57, BAC-TR-2026Q2#14, RJF-10K-2025#89, MS-10K-2025#23

### Q8 - PASS

Compare how Schwab and Raymond James describe their value proposition to independent advisors.

- `SCHW:deck`: hit SCHW-DECK-2026Q2#6, SCHW-DECK-2026Q3#12
- `SCHW:10-K`: hit SCHW-10K-2025#13, SCHW-10K-2025#117
- `RJF:deck`: no hit
- `RJF:10-K`: hit RJF-10K-2025#27, RJF-10K-2025#23
- Retrieved: RJF-TR-2026Q2#4, SCHW-TR-2026Q1#33, RJF-10K-2025#27, SCHW-10K-2025#13, RJF-10Q-2025Q2#201, SCHW-DECK-2026Q2#6, RJF-PR-2026-01-28-01#71, SCHW-PR-2026-07-21-01#1, RJF-SUPP-2026Q2#45, SCHW-10Q-2025Q2#7, RJF-TR-2026Q1#4, SCHW-TR-2026Q1#31, RJF-10K-2025#23, SCHW-10K-2025#117, RJF-10Q-2025Q4#171, SCHW-DECK-2026Q3#12, RJF-PR-2026-01-28-01#1, SCHW-PR-2026-10-15-01#1, RJF-TR-2026Q2#38, SCHW-10Q-2025Q2#310

### Q9 - PASS

How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

- `MS:10-K`: hit MS-10K-2025#190, MS-10K-2025#311, MS-10K-2025#321
- `MS:transcript`: hit MS-TR-2026Q3#21, MS-TR-2026Q2#42
- `MS:deck`: not in corpus
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246, BAC-10K-2025#247
- `BAC:transcript#GWIM`: no hit
- `BAC:deck#GWIM`: no hit
- Retrieved: MS-10K-2025#190, BAC-10K-2025#246, MS-10Q-2025Q2#180, BAC-PR-2026-04-15-01#10, MS-TR-2026Q3#21, BAC-10Q-2025Q3#94, MS-PR-2026-04-15-01#8, BAC-10K-2025#247, MS-SUPP-2026Q2#52, BAC-10Q-2026Q2#88, MS-10K-2025#311, BAC-PR-2026-01-14-01#12, MS-10Q-2025Q2#87, BAC-10Q-2025Q2#93, MS-TR-2026Q2#42, BAC-10Q-2025Q3#93, MS-PR-2026-07-15-01#8, BAC-10Q-2026Q1#71, MS-SUPP-2026Q1#49, MS-10K-2025#321

### Q10 - PASS

Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

- `MS:transcript`: hit MS-TR-2026Q2#23
- `SCHW:transcript`: hit SCHW-TR-2026Q2#6
- `EDJ:10-K`: hit EDJ-10K-2025#0, EDJ-10K-2025#10
- `BAC:transcript#GWIM`: hit BAC-TR-2026Q3#13
- `RJF:transcript`: hit RJF-TR-2026Q2#45
- Retrieved: SCHW-DECK-2026Q2#16, MS-10K-2025#144, RJF-TR-2026Q2#45, EDJ-10K-2025#0, BAC-10K-2025#249, SCHW-TR-2026Q2#6, MS-TR-2026Q2#23, RJF-10K-2025#33, EDJ-10Q-2025Q2#0, BAC-PR-2026-01-14-01#13, SCHW-10K-2025#213, MS-10Q-2025Q2#0, RJF-10Q-2025Q2#0, EDJ-10K-2025#10, BAC-10Q-2026Q1#75, SCHW-10Q-2025Q2#193, MS-PR-2026-01-15-01#13, RJF-PR-2026-04-22-01#1, EDJ-10Q-2025Q2#28, BAC-TR-2026Q3#13

### Q11 - PASS

How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

- `MS:10-K`: hit MS-10K-2025#44
- `MS:supplement`: hit MS-SUPP-2026Q1#30
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-K`: hit EDJ-10K-2025#130, EDJ-10K-2025#41
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `BAC:supplement#GWIM`: hit BAC-SUPP-2026Q1#44
- `RJF:10-K`: hit RJF-10K-2025#12
- `RJF:supplement`: no hit
- Expected `EDJ-10K-2025#130`: found EDJ-10K-2025#130
- Expected `EDJ-10K-2025#131, EDJ-10K-2025#148`: missing
- Expected `EDJ-10Q-2026Q2#60`: found EDJ-10Q-2026Q2#60
- Expected `EDJ-10K-2025#29`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `RJF-10K-2025#24`: missing
- Expected `MS-10K-2025#167, MS-SUPP-2026Q3#38`: missing
- Expected `BAC-10K-2025#246`: found BAC-10K-2025#246
- Expected `SCHW-10K-2025#18, SCHW-TR-2026Q1#3`: missing
- Retrieved: EDJ-10Q-2026Q2#60, RJF-10K-2025#12, SCHW-10Q-2026Q2#71, MS-10K-2025#44, BAC-TR-2026Q3#13, EDJ-10K-2025#130, RJF-10Q-2026Q1#239, SCHW-10K-2025#197, MS-SUPP-2026Q1#30, BAC-PR-2026-01-14-01#12, EDJ-10Q-2025Q2#66, RJF-PR-2026-04-22-01#1, SCHW-PR-2026-01-21-01#36, MS-10Q-2025Q2#59, BAC-SUPP-2026Q1#44, EDJ-10K-2025#41, RJF-TR-2026Q1#15, SCHW-TR-2026Q1#5, MS-PR-2026-04-15-01#15, BAC-10K-2025#246

### Q12 - PASS

How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

- `SCHW:transcript`: hit SCHW-TR-2026Q3#6, SCHW-TR-2026Q1#16, SCHW-TR-2026Q2#14
- `SCHW:10-K`: hit SCHW-10K-2025#13, SCHW-10K-2025#92
- `SCHW:monthly`: not in corpus
- `EDJ:10-K`: hit EDJ-10K-2025#87, EDJ-10K-2025#75, EDJ-10K-2025#67
- Retrieved: SCHW-TR-2026Q3#6, EDJ-10K-2025#87, SCHW-PR-2026-07-21-01#2, EDJ-10Q-2025Q2#28, SCHW-10K-2025#13, EDJ-10K-2025#75, SCHW-10Q-2025Q2#8, EDJ-10Q-2025Q2#110, SCHW-DECK-2026Q1#14, EDJ-10K-2025#67, SCHW-TR-2026Q1#16, EDJ-10Q-2025Q2#100, SCHW-PR-2026-10-15-01#7, EDJ-10Q-2025Q3#100, SCHW-10K-2025#92, EDJ-10Q-2026Q2#85, SCHW-10Q-2026Q1#22, SCHW-DECK-2026Q3#51, SCHW-TR-2026Q2#14, SCHW-PR-2026-04-16-01#7

### Q13 - PASS

How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

- `MS:transcript`: hit MS-TR-2026Q3#33, MS-TR-2026Q3#8, MS-TR-2026Q1#8
- `MS:10-K`: hit MS-10K-2025#168, MS-10K-2025#125, MS-10K-2025#169
- `MS:deck`: not in corpus
- Retrieved: MS-10Q-2026Q2#61, MS-10K-2025#168, MS-SUPP-2026Q1#42, MS-TR-2026Q3#33, MS-PR-2026-07-15-01#5, MS-10Q-2026Q1#53, MS-10K-2025#125, MS-SUPP-2026Q1#14, MS-TR-2026Q3#8, MS-PR-2026-01-15-01#3, MS-10Q-2026Q1#49, MS-10K-2025#169, MS-SUPP-2026Q2#16, MS-TR-2026Q1#8, MS-PR-2026-04-15-01#3, MS-10Q-2025Q3#229, MS-SUPP-2026Q3#16, MS-PR-2026-07-15-01#3, MS-10Q-2025Q2#56, MS-SUPP-2026Q1#43

### Q14 - PASS

How does Raymond James's affiliation-choice model work commercially?

- `RJF:10-K#Private Client Group`: hit RJF-10K-2025#10
- `RJF:transcript`: hit RJF-TR-2026Q1#16, RJF-TR-2026Q2#19, RJF-TR-2026Q1#3, RJF-TR-2026Q2#3, RJF-TR-2026Q2#22, RJF-TR-2026Q1#31
- `RJF:press`: hit RJF-PR-2025-10-22-01#2
- Retrieved: RJF-TR-2026Q1#16, RJF-10K-2025#91, RJF-10Q-2025Q4#142, RJF-PR-2025-10-22-01#2, RJF-TR-2026Q2#19, RJF-10K-2025#10, RJF-10Q-2025Q2#370, RJF-TR-2026Q1#3, RJF-10K-2025#462, RJF-10Q-2025Q2#335, RJF-TR-2026Q2#3, RJF-10Q-2025Q2#366, RJF-TR-2026Q2#22, RJF-TR-2026Q1#31

### Q15 - FAIL

What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

- `SCHW:10-K`: hit SCHW-10K-2025#512, SCHW-10K-2025#13, SCHW-10K-2025#27
- `MS:10-K`: no hit
- `EDJ:10-K`: no hit
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: no hit
- Retrieved: SCHW-PR-2026-07-21-01#2, SCHW-TR-2026Q1#20, SCHW-10K-2025#512, SCHW-10Q-2025Q2#9, SCHW-DECK-2026Q3#6, SCHW-PR-2026-10-15-01#2, SCHW-TR-2026Q1#15, SCHW-10K-2025#13, SCHW-10Q-2026Q1#19, SCHW-DECK-2026Q2#6, SCHW-PR-2026-01-21-01#1, SCHW-TR-2026Q3#1, SCHW-10K-2025#27, SCHW-10Q-2026Q2#22, SCHW-DECK-2026Q2#20, SCHW-PR-2026-04-16-01#3, SCHW-TR-2026Q1#5, SCHW-10Q-2026Q1#62, SCHW-PR-2026-01-21-01#2, SCHW-TR-2026Q3#2

### Q16 - PASS

What will receiving financial advice in the future look like for clients?

- `THEME:research`: not in corpus
- `THEME:regulatory`: not in corpus
- `THEME:survey`: not in corpus
- `MS:transcript`: hit MS-TR-2026Q2#46
- `SCHW:transcript`: hit SCHW-TR-2026Q3#32
- Retrieved: SCHW-TR-2026Q3#32, MS-TR-2026Q2#46, EDJ-10K-2025#88, BAC-TR-2026Q1#11, RJF-TR-2026Q1#33, SCHW-10K-2025#261, MS-10K-2025#423, EDJ-10Q-2025Q2#57, BAC-10K-2025#516, RJF-10K-2025#91, SCHW-10Q-2026Q1#226, MS-10Q-2026Q1#208, EDJ-10K-2025#91, BAC-PR-2026-01-14-01#9, RJF-10Q-2025Q2#319, SCHW-DECK-2026Q2#18, MS-PR-2026-10-14-01#0, EDJ-10Q-2026Q2#62, BAC-10Q-2025Q2#716, RJF-PR-2026-04-22-01#1

### Q17 - PASS

What are these firms saying about AI in advice delivery, and who is claiming the most?

- `MS:transcript`: hit MS-TR-2026Q1#29
- `SCHW:transcript`: hit SCHW-TR-2026Q1#9
- `BAC:transcript#GWIM`: no hit
- `RJF:transcript`: hit RJF-TR-2026Q2#39
- `MS:press`: hit MS-PR-2026-10-14-01#0
- `SCHW:press`: hit SCHW-PR-2026-07-21-01#8
- `EDJ:press`: not in corpus
- `MER:press`: not in corpus
- `RJF:press`: hit RJF-PR-2026-04-22-01#1
- `MS:trade`: not in corpus
- `MER:trade`: not in corpus
- Retrieved: SCHW-PR-2026-07-21-01#8, RJF-10K-2025#112, BAC-DECK-2026Q2#29, MS-10K-2025#372, EDJ-10K-2025#26, SCHW-DECK-2026Q3#71, RJF-TR-2026Q2#39, BAC-10K-2025#1078, MS-TR-2026Q1#29, EDJ-10Q-2025Q2#57, SCHW-TR-2026Q1#9, RJF-10Q-2026Q1#365, BAC-10Q-2025Q2#321, MS-10Q-2026Q2#524, EDJ-10K-2025#56, SCHW-DECK-2026Q1#26, RJF-PR-2026-04-22-01#1, BAC-SUPP-2026Q1#7, MS-PR-2026-10-14-01#0, EDJ-10Q-2025Q2#51

### Q18 - NOT_EVALUATED

Where is the industry heading on fee structures and pricing transparency?

- `MS:adv`: not in corpus
- `SCHW:adv`: not in corpus
- `EDJ:adv`: not in corpus
- `MER:adv`: not in corpus
- `RJF:adv`: not in corpus
- `THEME:regulatory`: not in corpus
- `THEME:research`: not in corpus
- Retrieved: RJF-TR-2026Q1#31, EDJ-10K-2025#55, MS-TR-2026Q1#2, BAC-10Q-2026Q1#31, SCHW-10K-2025#14, RJF-10K-2025#100, EDJ-10Q-2025Q2#67, MS-10K-2025#59, BAC-10K-2025#246, SCHW-10Q-2025Q2#95, RJF-10Q-2026Q1#244, EDJ-10K-2025#293, MS-PR-2026-04-15-01#12, BAC-TR-2026Q2#37, SCHW-DECK-2026Q2#6, RJF-SUPP-2026Q1#43, EDJ-10Q-2025Q3#103, MS-10Q-2025Q2#148, BAC-DECK-2026Q2#57, SCHW-TR-2026Q1#15

### Q19 - FAIL

How should the preferences of younger investors shape Edward Jones's offerings?

- `THEME:research`: not in corpus
- `THEME:survey`: not in corpus
- `MS:press`: no hit
- `SCHW:press`: no hit
- `RJF:press`: no hit
- `MER:press`: not in corpus
- Retrieved: EDJ-10K-2025#16, EDJ-10Q-2025Q2#28, EDJ-10K-2025#22, EDJ-10Q-2025Q2#115, EDJ-10K-2025#304, EDJ-10Q-2026Q1#95, EDJ-10Q-2026Q2#39, EDJ-10Q-2025Q2#17, EDJ-10Q-2025Q3#107, EDJ-10Q-2025Q3#19, EDJ-10Q-2025Q3#68, EDJ-10Q-2026Q1#78

### Q20 - NOT_EVALUATED

What evidence is there about how clients under 40 choose a financial advisor?

- `THEME:survey`: not in corpus
- `THEME:research`: not in corpus
- Retrieved: EDJ-10K-2025#19, SCHW-TR-2026Q1#44, RJF-TR-2026Q2#4, MS-TR-2026Q2#9, BAC-TR-2026Q3#13, EDJ-10Q-2026Q1#60, SCHW-PR-2026-01-21-01#36, RJF-10K-2025#91, MS-10K-2025#44, BAC-DECK-2026Q2#36, EDJ-10K-2025#233, SCHW-10K-2025#80, RJF-PR-2025-10-22-01#2, MS-SUPP-2026Q2#16, BAC-PR-2026-07-14-01#10, EDJ-10Q-2025Q3#85, SCHW-DECK-2026Q1#43, RJF-10Q-2025Q4#199, MS-10Q-2025Q2#65, BAC-10K-2025#139

### Q21 - PASS

What do we know about the generational wealth transfer, and how are these five preparing for it?

- `THEME:research`: not in corpus
- `MS:transcript`: hit MS-TR-2026Q3#16
- `SCHW:transcript`: no hit
- `EDJ:10-K`: hit EDJ-10K-2025#56, EDJ-10K-2025#304
- `BAC:transcript#GWIM`: type only (qualifier not met): BAC-TR-2026Q3#18
- `RJF:transcript`: hit RJF-TR-2026Q2#22
- Retrieved: MS-TR-2026Q3#16, SCHW-PR-2026-07-21-01#8, EDJ-10K-2025#56, RJF-TR-2026Q2#22, BAC-TR-2026Q3#18, MS-10K-2025#206, SCHW-DECK-2026Q3#71, EDJ-10Q-2025Q2#67, RJF-10K-2025#26, BAC-10K-2025#43, MS-10Q-2025Q2#226, SCHW-10K-2025#76, EDJ-10K-2025#304, RJF-10Q-2025Q2#241, BAC-10Q-2026Q1#596, MS-PR-2026-01-15-01#16, SCHW-10Q-2025Q2#9, EDJ-10Q-2025Q2#69, RJF-PR-2025-10-22-01#3, BAC-PR-2026-01-14-01#12

### Q22 - PASS

Net new assets by quarter for each of the five, with each firm's own definition of the metric.

- `MS:supplement`: hit MS-SUPP-2026Q1#7
- `SCHW:monthly`: not in corpus
- `SCHW:supplement`: not in corpus
- `EDJ:10-Q`: hit EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q2#67
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `MS:press`: hit MS-PR-2026-04-15-01#22
- `RJF:press`: hit RJF-PR-2026-01-28-01#1
- Expected `EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10K-2025#130`: missing
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14, MS-10Q-2026Q2#57, MS-10Q-2026Q1#48, MS-10Q-2025Q3#56, MS-10Q-2025Q2#56, MS-PR-2026-01-15-01#2`: missing
- Expected `MS-SUPP-2026Q1#42, MS-10K-2025#166`: missing
- Expected `SCHW-PR-2026-01-21-01#2, SCHW-PR-2026-07-21-01#2, SCHW-DECK-2026Q3#7, SCHW-10Q-2026Q2#16, SCHW-10Q-2026Q1#16, SCHW-10Q-2025Q3#16, SCHW-10Q-2025Q2#16`: missing
- Expected `SCHW-10K-2025#122, SCHW-10K-2025#119, SCHW-DECK-2026Q3#20`: missing
- Expected `RJF-PR-2026-07-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-01-28-01#3, RJF-PR-2025-10-22-01#4, RJF-10Q-2026Q2#305, RJF-10Q-2026Q1#298, RJF-10Q-2025Q4#236, RJF-10Q-2025Q2#294`: missing
- Expected `RJF-10Q-2026Q2#306, RJF-SUPP-2026Q1#43`: missing
- Expected `BAC-TR-2026Q3#13, BAC-PR-2026-10-14-01#11`: missing
- Retrieved: SCHW-TR-2026Q1#2, MS-TR-2026Q3#9, RJF-TR-2026Q1#15, EDJ-10Q-2025Q2#66, BAC-PR-2026-04-15-01#11, SCHW-PR-2026-04-16-01#3, MS-SUPP-2026Q1#7, RJF-10K-2025#223, EDJ-10K-2025#207, BAC-TR-2026Q1#20, SCHW-DECK-2026Q3#71, MS-PR-2026-04-15-01#22, RJF-10Q-2026Q1#323, EDJ-10Q-2025Q2#67, BAC-10K-2025#248, SCHW-10K-2025#136, MS-10K-2025#165, RJF-PR-2026-01-28-01#1, EDJ-10K-2025#182, BAC-10Q-2026Q1#74

### Q23 - PASS

Advisor headcount over the last eight quarters across the five.

- `MS:supplement`: hit MS-SUPP-2026Q1#14
- `SCHW:10-K`: hit SCHW-10K-2025#197
- `EDJ:10-Q`: hit EDJ-10Q-2025Q2#66, EDJ-10Q-2026Q2#60
- `EDJ:10-K`: hit EDJ-10K-2025#58, EDJ-10K-2025#70
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `RJF:press`: hit RJF-PR-2025-10-22-01#2
- Retrieved: SCHW-TR-2026Q1#5, EDJ-10Q-2025Q2#66, RJF-10K-2025#12, MS-TR-2026Q3#15, BAC-TR-2026Q3#13, SCHW-10Q-2026Q1#60, EDJ-10K-2025#58, RJF-TR-2026Q1#20, MS-10K-2025#44, BAC-10K-2025#247, SCHW-10K-2025#197, EDJ-10Q-2026Q2#60, RJF-10Q-2026Q1#239, MS-10Q-2026Q1#19, BAC-10Q-2025Q3#95, SCHW-DECK-2026Q3#71, EDJ-10K-2025#70, RJF-PR-2025-10-22-01#2, MS-SUPP-2026Q1#14, BAC-PR-2026-07-14-01#10

### Q24 - PASS

Client assets per advisor across the five -- and is that comparison even valid?

- `MS:supplement`: hit MS-SUPP-2026Q1#14
- `SCHW:10-K`: hit SCHW-10K-2025#42
- `EDJ:10-K`: hit EDJ-10K-2025#22, EDJ-10K-2025#267
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- Expected `EDJ-10K-2025#130`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38`: missing
- Retrieved: SCHW-TR-2026Q3#2, RJF-10Q-2026Q1#244, MS-TR-2026Q2#13, EDJ-10K-2025#22, BAC-TR-2026Q3#13, SCHW-PR-2026-01-21-01#40, RJF-10K-2025#41, MS-SUPP-2026Q1#14, EDJ-10Q-2026Q1#60, BAC-10K-2025#246, SCHW-DECK-2026Q2#20, RJF-PR-2026-07-22-01#98, MS-10K-2025#109, EDJ-10K-2025#267, BAC-PR-2026-10-14-01#11, SCHW-10K-2025#42, RJF-TR-2026Q2#42, MS-PR-2026-01-15-01#0, EDJ-10Q-2025Q2#102, BAC-TR-2026Q1#20

### Q25 - PASS

What has each of the five actually disclosed about advisor compensation structures?

- `MS:10-K`: hit MS-10K-2025#521
- `SCHW:10-K`: hit SCHW-10K-2025#512
- `EDJ:10-K`: hit EDJ-10K-2025#22, EDJ-10K-2025#314
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- `RJF:10-K`: hit RJF-10K-2025#175
- `MS:DEF 14A`: not in corpus
- `SCHW:DEF 14A`: not in corpus
- `BAC:DEF 14A`: not in corpus
- `RJF:DEF 14A`: not in corpus
- `MS:adv`: not in corpus
- `EDJ:adv`: not in corpus
- `RJF:adv`: not in corpus
- Expected `RJF-10K-2025#10, RJF-10K-2025#11`: missing
- Expected `EDJ-10K-2025#30, EDJ-10K-2025#264`: missing
- Expected `MS-10K-2025#153`: missing
- Expected `SCHW-10Q-2026Q2#25`: missing
- Retrieved: SCHW-TR-2026Q1#32, EDJ-10K-2025#22, RJF-10Q-2025Q4#199, MS-10K-2025#521, BAC-TR-2026Q3#13, SCHW-10K-2025#512, EDJ-10Q-2026Q1#60, RJF-10K-2025#175, MS-10Q-2026Q1#210, BAC-10K-2025#246, SCHW-10Q-2025Q2#317, EDJ-10K-2025#314, RJF-TR-2026Q1#34, MS-TR-2026Q3#13, BAC-TR-2026Q1#20, SCHW-PR-2026-01-21-01#36, EDJ-10Q-2025Q2#54, RJF-PR-2025-10-22-01#2, MS-PR-2026-01-15-01#4, BAC-PR-2026-07-14-01#10

### Q26 - PASS

What's new on Raymond James in the last 90 days?

- `RJF:*`: hit RJF-10Q-2026Q2#322, RJF-10Q-2026Q2#66, RJF-10Q-2026Q2#387, RJF-10Q-2026Q2#34, RJF-10Q-2026Q2#245, RJF-10Q-2026Q2#345, RJF-10Q-2026Q2#38, RJF-10Q-2026Q2#330
- Window: 2026-07-29 to 2026-10-27
- Expected `RJF-10Q-2026Q2`: found RJF-10Q-2026Q2#322, RJF-10Q-2026Q2#66, RJF-10Q-2026Q2#387, RJF-10Q-2026Q2#34, RJF-10Q-2026Q2#245, RJF-10Q-2026Q2#345, RJF-10Q-2026Q2#38, RJF-10Q-2026Q2#330
- Retrieved: RJF-10Q-2026Q2#322, RJF-10Q-2026Q2#66, RJF-10Q-2026Q2#387, RJF-10Q-2026Q2#34, RJF-10Q-2026Q2#245, RJF-10Q-2026Q2#345, RJF-10Q-2026Q2#38, RJF-10Q-2026Q2#330

### Q27 - PASS

What has changed at Merrill since the start of the year?

- `MER:*`: hit BAC-TR-2026Q3#13, BAC-DECK-2026Q3#31, BAC-PR-2026-10-14-01#12, BAC-TR-2026Q2#14, BAC-DECK-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-SUPP-2026Q1#43, BAC-TR-2026Q1#20, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-SUPP-2026Q1#44, BAC-SUPP-2026Q1#45, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-10K-2025#244, BAC-PR-2026-01-14-01#13
- `BAC:*#GWIM`: hit BAC-TR-2026Q3#13, BAC-DECK-2026Q3#31, BAC-PR-2026-10-14-01#12, BAC-TR-2026Q2#14, BAC-DECK-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-SUPP-2026Q1#43, BAC-TR-2026Q1#20, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-SUPP-2026Q1#44, BAC-SUPP-2026Q1#45, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-10K-2025#244, BAC-PR-2026-01-14-01#13
- Retrieved: BAC-TR-2026Q3#13, BAC-DECK-2026Q3#31, BAC-PR-2026-10-14-01#12, BAC-TR-2026Q2#14, BAC-DECK-2026Q2#20, BAC-PR-2026-07-14-01#11, BAC-10Q-2026Q1#71, BAC-10Q-2026Q1#72, BAC-10Q-2026Q1#73, BAC-SUPP-2026Q1#43, BAC-TR-2026Q1#20, BAC-DECK-2026Q1#27, BAC-PR-2026-04-15-01#11, BAC-SUPP-2026Q1#44, BAC-SUPP-2026Q1#45, BAC-10K-2025#249, BAC-10K-2025#246, BAC-10K-2025#247, BAC-10K-2025#244, BAC-PR-2026-01-14-01#13

### Q28 - PASS

What is Edward Jones's advisor attrition rate compared to Merrill's?

- `EDJ:10-K`: hit EDJ-10K-2025#71, EDJ-10K-2025#27, EDJ-10K-2025#58
- `BAC:supplement#GWIM`: no hit
- `BAC:10-K#GWIM`: hit BAC-10K-2025#246
- Expected `EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q3#68, EDJ-10Q-2025Q3#70`: found EDJ-10Q-2025Q3#70, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q3#68
- Expected `EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q3#69`: found EDJ-10Q-2025Q2#66
- Expected `BAC-TR-2026Q2#38, BAC-TR-2026Q1#48`: missing
- Expected `EDJ-10K-2025#130, EDJ-10Q-2026Q2#60`: missing
- Retrieved: EDJ-10Q-2025Q3#70, BAC-TR-2026Q3#13, EDJ-10K-2025#71, BAC-PR-2026-07-14-01#10, EDJ-10Q-2025Q2#66, BAC-10K-2025#246, EDJ-10K-2025#27, BAC-TR-2026Q1#20, EDJ-10Q-2025Q2#67, BAC-PR-2026-01-14-01#12, EDJ-10K-2025#58, BAC-TR-2026Q2#14, EDJ-10Q-2025Q2#64, BAC-PR-2026-04-15-01#10, EDJ-10Q-2026Q1#60, BAC-PR-2026-10-14-01#11, EDJ-10Q-2025Q3#68

### Q29 - FAIL

What does Morgan Stanley pay its financial advisors?

- `MS:10-K#Wealth Management`: hit MS-10K-2025#170
- `MS:trade`: not in corpus
- Expected `MS-10K-2025#153`: missing
- Expected `MS-10K-2025#128, MS-10K-2025#170`: found MS-10K-2025#170, MS-10K-2025#128
- **Misleading (must not come back):** MS-10K-2025#696
- Retrieved: MS-10Q-2026Q2#20, MS-10K-2025#170, MS-PR-2026-10-14-01#5, MS-TR-2026Q2#37, MS-10Q-2025Q3#64, MS-10K-2025#128, MS-SUPP-2026Q2#37, MS-TR-2026Q1#45, MS-10Q-2026Q2#64, MS-10K-2025#696, MS-SUPP-2026Q1#25, MS-TR-2026Q2#11, MS-10Q-2025Q3#19, MS-SUPP-2026Q1#42, MS-10Q-2025Q3#63, MS-10Q-2026Q1#19, MS-10Q-2025Q2#20, MS-10Q-2025Q2#63, MS-10Q-2026Q1#55, MS-10Q-2025Q2#19

### Q30 - PASS

What is Merrill's standalone profitability?

- `BAC:10-K#GWIM`: hit BAC-10K-2025#244
- Expected `BAC-PR-2026-01-14-01#12`: missing
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: missing
- Retrieved: BAC-DECK-2026Q1#26, BAC-PR-2026-04-15-01#10, BAC-TR-2026Q1#20, BAC-10K-2025#244, BAC-SUPP-2026Q1#43, BAC-DECK-2026Q2#19, BAC-PR-2026-07-14-01#10, BAC-TR-2026Q2#14, BAC-SUPP-2026Q2#52, BAC-DECK-2026Q3#30, BAC-10Q-2025Q2#90, BAC-SUPP-2026Q3#51, BAC-PR-2026-10-14-01#11, BAC-10Q-2025Q3#90, BAC-PR-2026-01-14-01#11, BAC-10Q-2026Q2#85, BAC-PR-2026-01-14-01#13, BAC-10Q-2026Q1#69, BAC-PR-2026-04-15-01#11, BAC-PR-2026-07-14-01#11

