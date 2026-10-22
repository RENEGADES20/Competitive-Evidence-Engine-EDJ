# Eval run corpus-2026-10-18-20261022-184408

Snapshot `corpus-2026-10-18` | commit `783c83f` | k=8 | min coverage 0.5 | as of 2026-10-22 | mode mock | 0 real calls

**PASS 6 | FAIL 22 | NOT_EVALUATED 2**

**Tier-1 recall**: documents 0.317, passages 0.139 (mean over the 9 of 18 tier-1 questions with an answer key; the rest n/a until #56)  
**Refusal accuracy**: gap questions (Q24, Q25, Q28, Q29, Q30) 5/5; all questions with a key 8/10

Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the corpus; PASS when coverage of the available patterns >= min coverage.

Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window.

| Q | Tier | Use case | Expected | Firms (mode) | Hits | Coverage | Recall docs | Passages | Refusal | Forbidden | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | entity_brief | answer | MS (entity) | 8 | 1/3 | 2/9 | 1/8 | ok | 0 | FAIL |
| Q2 | 1 | entity_brief | answer | RJF (entity) | 8 | 2/3 | - | - | - | 0 | PASS |
| Q3 | 1 | entity_brief | answer | SCHW (entity) | 8 | 1/3 | - | - | - | 0 | FAIL |
| Q4 (trap) | 1 | entity_brief | answer | MER (entity) | 0 | 0/2 | 0/5 | 0/7 | ok | 0 | FAIL |
| Q5 | 1 | entity_brief | answer | MS (entity) | 8 | 1/2 | - | - | - | 0 | PASS |
| Q6 | 1 | entity_brief | answer | RJF (entity) | 8 | 1/3 | - | - | - | 0 | FAIL |
| Q7 | 2 | head_to_head | answer | MS, MER, RJF (entity) | 8 | 1/6 | - | - | - | 0 | FAIL |
| Q8 | 2 | head_to_head | answer | SCHW, RJF (entity) | 8 | 2/4 | - | - | - | 0 | PASS |
| Q9 | 3 | head_to_head | answer | MS, MER (entity) | 8 | 1/5 | - | - | - | 0 | FAIL |
| Q10 | 3 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 2/5 | - | - | - | 0 | FAIL |
| Q11 | 1 | head_to_head | answer | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 1/8 | 1/8 | 0/10 | ok | 0 | FAIL |
| Q12 | 3 | mechanism | answer_with_boundary | SCHW, EDJ (entity) | 8 | 2/3 | - | - | - | 0 | PASS |
| Q13 | 1 | mechanism | answer | MS (entity) | 8 | 1/2 | - | - | - | 0 | PASS |
| Q14 | 3 | mechanism | answer | RJF (entity) | 8 | 1/3 | - | - | - | 0 | FAIL |
| Q15 | 3 | mechanism | answer | SCHW (entity) | 8 | 1/5 | - | - | - | 0 | FAIL |
| Q16 | 3 | theme_scan | answer | none (theme) | 8 | 1/2 | - | - | - | 0 | PASS |
| Q17 | 1 | theme_scan | answer | none (theme) | 8 | 1/7 | - | - | - | 0 | FAIL |
| Q18 | 3 | theme_scan | answer | none (theme) | 8 | - | - | - | - | 0 | NOT_EVALUATED |
| Q19 | 3 | segment_evidence | answer_with_boundary | EDJ (entity) | 8 | 0/3 | - | - | - | 0 | FAIL |
| Q20 | 1 | segment_evidence | answer | none (theme) | 8 | - | - | - | - | 0 | NOT_EVALUATED |
| Q21 | 2 | segment_evidence | answer | none (theme) | 8 | 1/5 | - | - | - | 0 | FAIL |
| Q22 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 2/6 | 3/33 | 1/8 | FAIL (1) | 0 | FAIL |
| Q23 | 1 | benchmark | answer | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 1/7 | - | - | - | 0 | FAIL |
| Q24 | 3 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 1/5 | 3/5 | 1/4 | ok | 0 | FAIL |
| Q25 | 1 | benchmark | gap_with_adjacent | MS, SCHW, EDJ, MER, RJF (entity) | 8 | 1/5 | 1/4 | 0/4 | ok | 0 | FAIL |
| Q26 | 1 | recency | answer | RJF (entity) | 8 | 1/1 | 1/1 | 1/1 | FAIL (7) | 0 | FAIL |
| Q27 (trap) | 1 | recency | answer | MER (entity) | 0 | 0/2 | - | - | - | 0 | FAIL |
| Q28 | 1 | honest_miss | gap_with_adjacent | EDJ, MER (entity) | 8 | 1/3 | 1/6 | 0/4 | ok | 0 | FAIL |
| Q29 | 1 | honest_miss | gap_with_adjacent | MS (entity) | 8 | 0/1 | 1/1 | 0/2 | ok | 0 | FAIL |
| Q30 (trap) | 1 | honest_miss | gap_with_adjacent | MER (entity) | 0 | 0/1 | 0/2 | 0/2 | ok | 0 | FAIL |

## Per question

### Q1 - FAIL

What is Morgan Stanley's strategy to increase their net new assets?

- `MS:transcript`: no hit
- `MS:10-K#Wealth Management`: type only (qualifier not met): MS-10K-2025#166
- `MS:deck`: not in corpus
- `MS:supplement`: hit MS-SUPP-2026Q1#43
- Expected `MS-TR-2026Q2#3`: missing
- Expected `MS-TR-2026Q2#13, MS-TR-2026Q2#15`: missing
- Expected `MS-TR-2026Q3#2, MS-TR-2026Q3#8`: missing
- Expected `MS-TR-2026Q1#2, MS-TR-2026Q1#7, MS-TR-2026Q1#8`: missing
- Expected `MS-PR-2026-10-14-01#5, MS-PR-2026-07-15-01#5`: missing
- Expected `MS-10K-2025#125`: missing
- Expected `MS-10K-2025#127, MS-10K-2025#164, MS-10K-2025#166`: found MS-10K-2025#166
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14`: missing
- Retrieved: MS-10Q-2026Q2#58, MS-PR-2026-01-15-01#18, MS-PR-2026-04-15-01#15, MS-10K-2025#166, MS-10Q-2025Q2#57, MS-10Q-2025Q3#57, MS-10Q-2026Q1#50, MS-SUPP-2026Q1#43

### Q2 - PASS

How is Raymond James positioning itself to recruit advisors away from the wirehouses?

- `RJF:transcript`: hit RJF-TR-2026Q1#17
- `RJF:10-K`: hit RJF-10K-2025#27, RJF-10K-2025#90, RJF-10K-2025#452, RJF-10K-2025#10, RJF-10K-2025#89
- `RJF:press`: no hit
- `RJF:trade`: not in corpus
- Retrieved: RJF-10K-2025#27, RJF-10K-2025#90, RJF-10K-2025#452, RJF-10K-2025#10, RJF-10Q-2026Q1#307, RJF-10Q-2026Q2#316, RJF-TR-2026Q1#17, RJF-10K-2025#89

### Q3 - FAIL

What is Schwab's strategy for its RIA custody business?

- `SCHW:transcript`: hit SCHW-TR-2026Q2#34, SCHW-TR-2026Q3#7
- `SCHW:10-K#Advisor Services`: type only (qualifier not met): SCHW-10K-2025#26, SCHW-10K-2025#11
- `SCHW:deck`: no hit
- Retrieved: SCHW-10Q-2026Q2#342, SCHW-TR-2026Q2#34, SCHW-10K-2025#26, SCHW-10Q-2026Q2#343, SCHW-10K-2025#11, SCHW-10Q-2026Q2#30, SCHW-10Q-2026Q2#341, SCHW-TR-2026Q3#7

### Q4 - FAIL

What is Merrill's advisor growth strategy, and how has it changed?

- `BAC:transcript#GWIM`: no hit
- `BAC:10-K#GWIM`: no hit
- `MER:press`: not in corpus
- `MER:trade`: not in corpus
- Expected `BAC-TR-2026Q1#20`: missing
- Expected `BAC-TR-2026Q1#48`: missing
- Expected `BAC-TR-2026Q2#13, BAC-TR-2026Q2#14`: missing
- Expected `BAC-TR-2026Q2#38`: missing
- Expected `BAC-TR-2026Q3#13`: missing
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: missing
- Expected `BAC-10Q-2026Q2#88, BAC-10Q-2026Q2#89, BAC-10Q-2026Q2#90, BAC-10Q-2026Q2#91`: missing
- Retrieved: nothing

### Q5 - PASS

Where is Morgan Stanley investing in technology for its advisors?

- `MS:transcript`: no hit
- `MS:10-K`: hit MS-10K-2025#178, MS-10K-2025#26, MS-10K-2025#145, MS-10K-2025#462
- `MS:deck`: not in corpus
- `MS:trade`: not in corpus
- Retrieved: MS-10K-2025#178, MS-10K-2025#26, MS-SUPP-2026Q1#46, MS-SUPP-2026Q2#40, MS-SUPP-2026Q3#41, MS-10K-2025#145, MS-10K-2025#462, MS-10Q-2025Q2#398

### Q6 - FAIL

What has Raymond James said about its affiliation models, and has the mix shifted?

- `RJF:10-K#Private Client Group`: type only (qualifier not met): RJF-10K-2025#364, RJF-10K-2025#365, RJF-10K-2025#319
- `RJF:transcript`: hit RJF-TR-2026Q2#22, RJF-TR-2026Q1#30
- `RJF:press`: no hit
- Retrieved: RJF-10K-2025#364, RJF-10K-2025#365, RJF-TR-2026Q2#22, RJF-10Q-2025Q2#421, RJF-10Q-2026Q1#423, RJF-10Q-2026Q2#434, RJF-TR-2026Q1#30, RJF-10K-2025#319

### Q7 - FAIL

How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?

- `MS:transcript`: no hit
- `MS:10-K`: no hit
- `BAC:transcript#GWIM`: no hit
- `BAC:10-K#GWIM`: no hit
- `RJF:transcript`: hit RJF-TR-2026Q2#4, RJF-TR-2026Q1#17, RJF-TR-2026Q2#38, RJF-TR-2026Q2#19, RJF-TR-2026Q1#3, RJF-TR-2026Q2#24, RJF-TR-2026Q1#34, RJF-TR-2026Q1#4
- `RJF:10-K`: no hit
- `MS:trade`: not in corpus
- `MER:trade`: not in corpus
- `RJF:trade`: not in corpus
- Retrieved: RJF-TR-2026Q2#4, RJF-TR-2026Q1#17, RJF-TR-2026Q2#38, RJF-TR-2026Q2#19, RJF-TR-2026Q1#3, RJF-TR-2026Q2#24, RJF-TR-2026Q1#34, RJF-TR-2026Q1#4

### Q8 - PASS

Compare how Schwab and Raymond James describe their value proposition to independent advisors.

- `SCHW:deck`: no hit
- `SCHW:10-K`: hit SCHW-10K-2025#343
- `RJF:deck`: no hit
- `RJF:10-K`: hit RJF-10K-2025#27, RJF-10K-2025#24, RJF-10K-2025#521, RJF-10K-2025#523, RJF-10K-2025#90
- Retrieved: RJF-10K-2025#27, SCHW-10K-2025#343, SCHW-10Q-2025Q3#265, SCHW-10Q-2026Q1#236, RJF-10K-2025#24, RJF-10K-2025#521, RJF-10K-2025#523, RJF-10K-2025#90

### Q9 - FAIL

How do Morgan Stanley and Merrill differ in how they segment clients by wealth tier?

- `MS:10-K`: hit MS-10K-2025#310, MS-10K-2025#166, MS-10K-2025#190, MS-10K-2025#125, MS-10K-2025#419
- `MS:transcript`: no hit
- `MS:deck`: not in corpus
- `BAC:10-K#GWIM`: no hit
- `BAC:transcript#GWIM`: no hit
- `BAC:deck#GWIM`: no hit
- Retrieved: MS-10K-2025#310, MS-10K-2025#166, MS-10K-2025#190, MS-10Q-2025Q2#87, MS-10Q-2025Q3#86, MS-10K-2025#125, MS-10K-2025#419, MS-10Q-2026Q1#16

### Q10 - FAIL

Which of the five has been most explicit about serving mass-affluent clients, and what exactly have they said?

- `MS:transcript`: hit MS-TR-2026Q2#3
- `SCHW:transcript`: hit SCHW-TR-2026Q1#14, SCHW-TR-2026Q1#2
- `EDJ:10-K`: no hit
- `BAC:transcript#GWIM`: no hit
- `RJF:transcript`: no hit
- Retrieved: SCHW-TR-2026Q1#14, MS-10K-2025#166, MS-10Q-2025Q3#48, SCHW-10K-2025#14, MS-10Q-2025Q2#48, MS-10Q-2026Q1#51, MS-TR-2026Q2#3, SCHW-TR-2026Q1#2

### Q11 - FAIL

How does each of the five define and report advisor headcount -- and what does each definition include or exclude?

- `MS:10-K`: no hit
- `MS:supplement`: no hit
- `SCHW:10-K`: no hit
- `EDJ:10-K`: hit EDJ-10K-2025#21, EDJ-10K-2025#42, EDJ-10K-2025#41
- `BAC:10-K#GWIM`: no hit
- `BAC:supplement#GWIM`: no hit
- `RJF:10-K`: no hit
- `RJF:supplement`: no hit
- Expected `EDJ-10K-2025#130`: missing
- Expected `EDJ-10K-2025#131, EDJ-10K-2025#148`: missing
- Expected `EDJ-10Q-2026Q2#60`: missing
- Expected `EDJ-10K-2025#29`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `RJF-10K-2025#24`: missing
- Expected `MS-10K-2025#167, MS-SUPP-2026Q3#38`: missing
- Expected `BAC-10K-2025#246`: missing
- Expected `SCHW-10K-2025#18, SCHW-TR-2026Q1#3`: missing
- Retrieved: RJF-TR-2026Q2#4, RJF-TR-2026Q2#19, RJF-TR-2026Q2#24, EDJ-10K-2025#21, RJF-TR-2026Q1#34, RJF-TR-2026Q1#4, EDJ-10K-2025#42, EDJ-10K-2025#41

### Q12 - PASS

How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones replicate a similar strategy?

- `SCHW:transcript`: hit SCHW-TR-2026Q1#2, SCHW-TR-2026Q1#14, SCHW-TR-2026Q2#14
- `SCHW:10-K`: hit SCHW-10K-2025#116, SCHW-10K-2025#14, SCHW-10K-2025#70, SCHW-10K-2025#71
- `SCHW:monthly`: not in corpus
- `EDJ:10-K`: no hit
- Retrieved: SCHW-TR-2026Q1#2, SCHW-10Q-2026Q2#343, SCHW-TR-2026Q1#14, SCHW-TR-2026Q2#14, SCHW-10K-2025#116, SCHW-10K-2025#14, SCHW-10K-2025#70, SCHW-10K-2025#71

### Q13 - PASS

How does Morgan Stanley convert workplace and stock-plan participants into wealth management clients?

- `MS:transcript`: no hit
- `MS:10-K`: hit MS-10K-2025#125, MS-10K-2025#419
- `MS:deck`: not in corpus
- Retrieved: MS-10Q-2026Q2#61, MS-10K-2025#125, MS-10K-2025#419, MS-10Q-2025Q2#60, MS-10Q-2025Q3#60, MS-10Q-2026Q1#16, MS-10Q-2026Q1#209, MS-10Q-2026Q2#16

### Q14 - FAIL

How does Raymond James's affiliation-choice model work commercially?

- `RJF:10-K#Private Client Group`: type only (qualifier not met): RJF-10K-2025#364, RJF-10K-2025#365, RJF-10K-2025#299
- `RJF:transcript`: hit RJF-TR-2026Q2#22, RJF-TR-2026Q2#19
- `RJF:press`: no hit
- Retrieved: RJF-10K-2025#364, RJF-10K-2025#365, RJF-TR-2026Q2#22, RJF-10Q-2025Q2#421, RJF-10Q-2026Q1#423, RJF-10Q-2026Q2#434, RJF-TR-2026Q2#19, RJF-10K-2025#299

### Q15 - FAIL

What drives the difference between how Schwab earns on client assets and how an advisor-led model earns?

- `SCHW:10-K`: hit SCHW-10K-2025#27
- `MS:10-K`: no hit
- `EDJ:10-K`: no hit
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: no hit
- Retrieved: SCHW-TR-2026Q3#7, SCHW-TR-2026Q3#2, SCHW-10K-2025#27, SCHW-TR-2026Q1#2, SCHW-TR-2026Q1#44, SCHW-TR-2026Q3#26, SCHW-PR-2026-01-21-01#52, SCHW-PR-2026-07-21-01#54

### Q16 - PASS

What will receiving financial advice in the future look like for clients?

- `THEME:research`: not in corpus
- `THEME:regulatory`: not in corpus
- `THEME:survey`: not in corpus
- `MS:transcript`: no hit
- `SCHW:transcript`: hit SCHW-TR-2026Q1#14
- Retrieved: RJF-10K-2025#438, EDJ-10K-2025#239, BAC-10K-2025#249, EDJ-10Q-2026Q1#27, EDJ-10Q-2026Q2#32, SCHW-10K-2025#361, MS-10Q-2025Q3#48, SCHW-TR-2026Q1#14

### Q17 - FAIL

What are these firms saying about AI in advice delivery, and who is claiming the most?

- `MS:transcript`: no hit
- `SCHW:transcript`: hit SCHW-TR-2026Q1#9
- `BAC:transcript#GWIM`: no hit
- `RJF:transcript`: no hit
- `MS:press`: no hit
- `SCHW:press`: no hit
- `EDJ:press`: not in corpus
- `MER:press`: not in corpus
- `RJF:press`: no hit
- `MS:trade`: not in corpus
- `MER:trade`: not in corpus
- Retrieved: RJF-10K-2025#112, MS-10K-2025#707, MS-10Q-2025Q2#412, MS-10Q-2026Q1#383, MS-10Q-2026Q2#426, SCHW-TR-2026Q1#9, MS-10Q-2025Q3#418, RJF-10K-2025#58

### Q18 - NOT_EVALUATED

Where is the industry heading on fee structures and pricing transparency?

- `MS:adv`: not in corpus
- `SCHW:adv`: not in corpus
- `EDJ:adv`: not in corpus
- `MER:adv`: not in corpus
- `RJF:adv`: not in corpus
- `THEME:regulatory`: not in corpus
- `THEME:research`: not in corpus
- Retrieved: SCHW-10K-2025#175, SCHW-10Q-2025Q3#65, EDJ-10K-2025#24, SCHW-10K-2025#161, SCHW-10K-2025#310, EDJ-10K-2025#236, EDJ-10K-2025#237, EDJ-10K-2025#238

### Q19 - FAIL

How should the preferences of younger investors shape Edward Jones's offerings?

- `THEME:research`: not in corpus
- `THEME:survey`: not in corpus
- `MS:press`: no hit
- `SCHW:press`: no hit
- `RJF:press`: no hit
- `MER:press`: not in corpus
- Retrieved: EDJ-10K-2025#265, EDJ-10Q-2026Q2#39, EDJ-10K-2025#91, EDJ-10K-2025#16, EDJ-10K-2025#26, EDJ-10K-2025#45, EDJ-10K-2025#59, EDJ-10K-2025#147

### Q20 - NOT_EVALUATED

What evidence is there about how clients under 40 choose a financial advisor?

- `THEME:survey`: not in corpus
- `THEME:research`: not in corpus
- Retrieved: RJF-TR-2026Q2#4, RJF-TR-2026Q2#24, RJF-TR-2026Q1#4, RJF-TR-2026Q2#19, EDJ-10K-2025#21, RJF-TR-2026Q1#20, RJF-TR-2026Q1#3, RJF-TR-2026Q1#34

### Q21 - FAIL

What do we know about the generational wealth transfer, and how are these five preparing for it?

- `THEME:research`: not in corpus
- `MS:transcript`: no hit
- `SCHW:transcript`: hit SCHW-TR-2026Q3#8
- `EDJ:10-K`: no hit
- `BAC:transcript#GWIM`: no hit
- `RJF:transcript`: no hit
- Retrieved: SCHW-TR-2026Q3#8, BAC-10Q-2025Q2#393, BAC-10Q-2025Q3#395, BAC-10Q-2026Q2#380, BAC-10K-2025#668, BAC-10Q-2026Q1#332, BAC-10K-2025#246, BAC-PR-2026-01-14-01#12

### Q22 - FAIL

Net new assets by quarter for each of the five, with each firm's own definition of the metric.

- `MS:supplement`: no hit
- `SCHW:monthly`: not in corpus
- `SCHW:supplement`: not in corpus
- `EDJ:10-Q`: no hit
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `MS:press`: hit MS-PR-2026-04-15-01#15
- `RJF:press`: hit RJF-PR-2026-04-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-07-22-01#4, RJF-PR-2026-07-22-01#5
- Expected `EDJ-10Q-2026Q2#60, EDJ-10Q-2026Q1#51, EDJ-10Q-2025Q3#67, EDJ-10Q-2025Q2#64, EDJ-10K-2025#130`: missing
- Expected `MS-SUPP-2026Q3#16, MS-SUPP-2026Q2#16, MS-SUPP-2026Q1#14, MS-10Q-2026Q2#57, MS-10Q-2026Q1#48, MS-10Q-2025Q3#56, MS-10Q-2025Q2#56, MS-PR-2026-01-15-01#2`: missing
- Expected `MS-SUPP-2026Q1#42, MS-10K-2025#166`: missing
- Expected `SCHW-PR-2026-01-21-01#2, SCHW-PR-2026-07-21-01#2, SCHW-DECK-2026Q3#7, SCHW-10Q-2026Q2#16, SCHW-10Q-2026Q1#16, SCHW-10Q-2025Q3#16, SCHW-10Q-2025Q2#16`: missing
- Expected `SCHW-10K-2025#122, SCHW-10K-2025#119, SCHW-DECK-2026Q3#20`: missing
- Expected `RJF-PR-2026-07-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-01-28-01#3, RJF-PR-2025-10-22-01#4, RJF-10Q-2026Q2#305, RJF-10Q-2026Q1#298, RJF-10Q-2025Q4#236, RJF-10Q-2025Q2#294`: found RJF-PR-2026-04-22-01#3, RJF-PR-2026-07-22-01#4
- Expected `RJF-10Q-2026Q2#306, RJF-SUPP-2026Q1#43`: missing
- Expected `BAC-TR-2026Q3#13, BAC-PR-2026-10-14-01#11`: missing
- **Misleading (must not come back):** MS-PR-2026-04-15-01#15
- Retrieved: RJF-PR-2026-04-22-01#4, RJF-PR-2026-04-22-01#3, RJF-PR-2026-07-22-01#4, RJF-PR-2026-07-22-01#5, SCHW-TR-2026Q2#23, SCHW-TR-2026Q3#25, MS-PR-2026-04-15-01#15, MS-10Q-2026Q2#58

### Q23 - FAIL

Advisor headcount over the last eight quarters across the five.

- `MS:supplement`: no hit
- `SCHW:10-K`: no hit
- `EDJ:10-Q`: no hit
- `EDJ:10-K`: hit EDJ-10K-2025#21
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- `RJF:press`: no hit
- Retrieved: RJF-TR-2026Q2#4, RJF-TR-2026Q1#3, RJF-TR-2026Q2#19, RJF-TR-2026Q2#24, RJF-TR-2026Q1#20, RJF-TR-2026Q2#3, RJF-TR-2026Q2#38, EDJ-10K-2025#21

### Q24 - FAIL

Client assets per advisor across the five -- and is that comparison even valid?

- `MS:supplement`: hit MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38
- `SCHW:10-K`: no hit
- `EDJ:10-K`: no hit
- `BAC:supplement#GWIM`: no hit
- `RJF:supplement`: no hit
- Expected `EDJ-10K-2025#130`: missing
- Expected `RJF-10K-2025#227`: missing
- Expected `RJF-10K-2025#228`: missing
- Expected `MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38`: found MS-SUPP-2026Q1#43, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38
- Retrieved: RJF-TR-2026Q2#4, MS-10Q-2026Q1#51, RJF-TR-2026Q1#3, RJF-TR-2026Q2#24, MS-SUPP-2026Q1#43, MS-10K-2025#166, MS-SUPP-2026Q2#37, MS-SUPP-2026Q3#38

### Q25 - FAIL

What has each of the five actually disclosed about advisor compensation structures?

- `MS:10-K`: no hit
- `SCHW:10-K`: no hit
- `EDJ:10-K`: hit EDJ-10K-2025#21, EDJ-10K-2025#42
- `BAC:10-K#GWIM`: no hit
- `RJF:10-K`: no hit
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
- Retrieved: RJF-TR-2026Q2#4, RJF-TR-2026Q2#19, RJF-TR-2026Q2#24, RJF-TR-2026Q1#34, EDJ-10K-2025#21, RJF-TR-2026Q1#4, EDJ-10K-2025#42, RJF-TR-2026Q1#20

### Q26 - FAIL

What's new on Raymond James in the last 90 days?

- `RJF:*`: hit RJF-10K-2025#351, RJF-10Q-2025Q2#414, RJF-10Q-2025Q4#343, RJF-10Q-2026Q1#415, RJF-10Q-2026Q2#426, RJF-10K-2025#352, RJF-10Q-2025Q4#236, RJF-10Q-2025Q4#344
- Window: 2026-07-24 to 2026-10-22
- Expected `RJF-10Q-2026Q2`: found RJF-10Q-2026Q2#426
- **Outside the window:** RJF-10K-2025#351, RJF-10Q-2025Q2#414, RJF-10Q-2025Q4#343, RJF-10Q-2026Q1#415, RJF-10K-2025#352, RJF-10Q-2025Q4#236, RJF-10Q-2025Q4#344
- Retrieved: RJF-10K-2025#351, RJF-10Q-2025Q2#414, RJF-10Q-2025Q4#343, RJF-10Q-2026Q1#415, RJF-10Q-2026Q2#426, RJF-10K-2025#352, RJF-10Q-2025Q4#236, RJF-10Q-2025Q4#344

### Q27 - FAIL

What has changed at Merrill since the start of the year?

- `MER:*`: no hit
- `BAC:*#GWIM`: no hit
- Retrieved: nothing

### Q28 - FAIL

What is Edward Jones's advisor attrition rate compared to Merrill's?

- `EDJ:10-K`: hit EDJ-10K-2025#21, EDJ-10K-2025#42, EDJ-10K-2025#71, EDJ-10K-2025#41, EDJ-10K-2025#19, EDJ-10K-2025#61, EDJ-10K-2025#268, EDJ-10K-2025#58
- `BAC:supplement#GWIM`: no hit
- `BAC:10-K#GWIM`: no hit
- Expected `EDJ-10Q-2025Q2#64, EDJ-10Q-2025Q2#67, EDJ-10Q-2025Q3#68, EDJ-10Q-2025Q3#70`: missing
- Expected `EDJ-10Q-2025Q2#66, EDJ-10Q-2025Q3#69`: missing
- Expected `BAC-TR-2026Q2#38, BAC-TR-2026Q1#48`: missing
- Expected `EDJ-10K-2025#130, EDJ-10Q-2026Q2#60`: missing
- Retrieved: EDJ-10K-2025#21, EDJ-10K-2025#42, EDJ-10K-2025#71, EDJ-10K-2025#41, EDJ-10K-2025#19, EDJ-10K-2025#61, EDJ-10K-2025#268, EDJ-10K-2025#58

### Q29 - FAIL

What does Morgan Stanley pay its financial advisors?

- `MS:10-K#Wealth Management`: type only (qualifier not met): MS-10K-2025#462, MS-10K-2025#781
- `MS:trade`: not in corpus
- Expected `MS-10K-2025#153`: missing
- Expected `MS-10K-2025#128, MS-10K-2025#170`: missing
- Retrieved: MS-10Q-2025Q2#51, MS-10Q-2025Q3#51, MS-10K-2025#462, MS-10Q-2025Q3#19, MS-10K-2025#781, MS-10Q-2025Q2#75, MS-10Q-2026Q1#213, MS-10Q-2026Q2#236

### Q30 - FAIL

What is Merrill's standalone profitability?

- `BAC:10-K#GWIM`: no hit
- Expected `BAC-PR-2026-01-14-01#12`: missing
- Expected `BAC-10K-2025#245, BAC-10K-2025#246, BAC-10K-2025#247`: missing
- Retrieved: nothing

