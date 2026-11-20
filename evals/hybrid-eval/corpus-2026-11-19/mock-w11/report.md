# #249 hybrid-norerank vs fts on the same plans (mock, 0 real calls)

fts: `fts/report.json` (exp/hybrid 388811e, `--mode fts`)  
hybrid-norerank: `hybrid-norerank/report.json` (exp/hybrid 388811e)

Plans: rule plans (mock) in both runs; identical by construction (checked below).

## Summary

| measure | fts | hybrid-norerank |
|---|---|---|
| PASS | 33 | 31 |
| refusal gap | 8/8 | 7/8 |
| refusal all keyed | 26/26 | 24/26 |
| forbidden hits | 0 | 0 |
| tier-1 doc recall | 0.937 | 0.869 |
| tier-1 passage recall | 0.851 | 0.708 |
| recall@pool | 0.816 | 0.761 |
| recall@final | 0.698 | 0.612 |
| passages | 5313 | 4305 |
| tokens est | 1530829 | 1190400 |
| median search s | 1.115 | 1.565 |
| statuses | {'PASS': 33, 'FAIL': 2, 'NOT_EVALUATED': 0} | {'PASS': 31, 'FAIL': 4, 'NOT_EVALUATED': 0} |

## Per question

| Q | plan same | status fts / hyb | refusal fts / hyb | behavior fts / hyb | chunks fts / hyb | shared | doc recall fts / hyb |
|---|---|---|---|---|---|---|---|
| Q1 | yes | PASS / PASS | ok / ok | answer / answer | 74 / 40 | 32 | 1.0 / 0.556 |
| Q2 | yes | PASS / PASS | ok / ok | answer / answer | 89 / 38 | 24 | 1.0 / 0.889 |
| Q3 | yes | PASS / PASS | ok / ok | answer / answer | 71 / 40 | 32 | 1.0 / 0.5 |
| Q4 | yes | PASS / PASS | ok / ok | answer / answer | 25 / 60 | 24 | 0.8 / 1.0 |
| Q5 | yes | PASS / PASS | ok / ok | answer / answer | 43 / 29 | 16 | 1.0 / 0.667 |
| Q6 | yes | PASS / PASS | ok / ok | answer / answer | 47 / 34 | 24 | 1.0 / 1.0 |
| Q7 | yes | PASS / PASS | ok / ok | answer / answer | 164 / 123 | 65 | 1.0 / 1.0 |
| Q8 | yes | PASS / PASS | - / - | answer / answer | 141 / 74 | 46 | None / None |
| Q9 | yes | PASS / PASS | - / - | answer / answer | 89 / 119 | 46 | None / None |
| Q10 | yes | PASS / PASS | - / - | answer / answer | 219 / 220 | 106 | None / None |
| Q11 | yes | PASS / PASS | ok / ok | answer / answer | 267 / 202 | 126 | 1.0 / 0.875 |
| Q12 | yes | PASS / PASS | - / - | answer_with_boundary / answer_with_boundary | 133 / 51 | 29 | None / None |
| Q13 | yes | PASS / PASS | ok / ok | answer / answer | 55 / 43 | 24 | 1.0 / 1.0 |
| Q14 | yes | PASS / PASS | - / - | answer / answer | 35 / 41 | 25 | None / None |
| Q15 | yes | PASS / PASS | ok / ok | answer / answer | 307 / 232 | 121 | 1.0 / 1.0 |
| Q16 | yes | PASS / PASS | - / - | answer / answer | 134 / 156 | 60 | None / None |
| Q17 | yes | PASS / PASS | ok / ok | answer / answer | 147 / 161 | 78 | 1.0 / 1.0 |
| Q18 | yes | PASS / PASS | - / - | answer / answer | 141 / 158 | 51 | None / None |
| Q19 | yes | FAIL / FAIL | ok / ok | answer_with_boundary / answer_with_boundary | 32 / 44 | 17 | 1.0 / 1.0 |
| Q20 | yes | PASS / PASS | ok / ok | answer / answer | 133 / 136 | 66 | 0.75 / 0.875 |
| Q21 | yes | PASS / PASS | - / - | answer / answer | 253 / 190 | 124 | None / None |
| Q22 | yes | PASS / FAIL | ok / FAIL | answer / answer | 296 / 215 | 159 | 1.0 / 0.939 |
| Q23 | yes | PASS / PASS | ok / ok | answer / answer | 188 / 187 | 94 | 0.6 / 0.7 |
| Q24 | yes | PASS / FAIL | ok / FAIL | answer / answer | 274 / 220 | 144 | 1.0 / 1.0 |
| Q25 | yes | PASS / PASS | ok / ok | answer / answer | 253 / 170 | 83 | 1.0 / 1.0 |
| Q26 | yes | PASS / PASS | ok / ok | answer / answer | 30 / 30 | 24 | None / None |
| Q27 | yes | PASS / PASS | ok / ok | answer / answer | 97 / 96 | 93 | 0.778 / 0.778 |
| Q28 | yes | PASS / PASS | ok / ok | answer / answer | 46 / 62 | 38 | 1.0 / 1.0 |
| Q29 | yes | PASS / PASS | ok / ok | answer / answer | 69 / 44 | 26 | 1.0 / 1.0 |
| Q30 | yes | PASS / PASS | ok / ok | answer / answer | 46 / 44 | 35 | 1.0 / 1.0 |
| Q31 | yes | PASS / PASS | ok / ok | answer / answer | 258 / 213 | 106 | 1.0 / 1.0 |
| Q32 | yes | PASS / PASS | - / - | answer / answer | 323 / 216 | 137 | None / None |
| Q33 | yes | FAIL / FAIL | ok / ok | answer / answer | 362 / 218 | 153 | 0.0 / 0.0 |
| Q34 | yes | PASS / PASS | ok / ok | answer / answer | 199 / 207 | 104 | 1.0 / 1.0 |
| Q35 | yes | PASS / PASS | ok / ok | answer / answer | 273 / 192 | 89 | 1.0 / 1.0 |

Plans (aspects and sub-questions) identical on 35 / 35 questions.

## Competitor floor (ADR-018 safeguard across competitors)

Per competitor sub-question, from `plan.searched`: before = the main search's hits (`passages` minus the period / pinned hits added to it) + `len(floor_dropped)`; after = the main search's hits kept by the floor; to map = `passages` (after the floor, plus the period and pin passes).

| Q | sub-question | fts before -> after floor (dropped, emptied) | to map fts | hyb before -> after floor (dropped, emptied) | to map hyb |
|---|---|---|---|---|---|
| Q19 | a1.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a1.SCHW | 11 -> 11 (0, False) | 11 | 16 -> 16 (0, False) | 16 |
| Q19 | a1.MER | 4 -> 0 (4, True) | 0 | 5 -> 5 (0, False) | 5 |
| Q19 | a1.RJF | 0 -> 0 (0, False) | 0 | 1 -> 1 (0, False) | 1 |

Totals: fts dropped 4, emptied 1, competitor passages to the map 11; hybrid-norerank dropped 0, emptied 0, competitor passages to the map 22.

Questions with no competitor sub-question: Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q20, Q21, Q22, Q23, Q24, Q25, Q26, Q27, Q28, Q29, Q30, Q31, Q32, Q33, Q34, Q35.

Floor value per aspect (`plan.competitor_floor`):

| Q | fts | hybrid-norerank |
|---|---|---|
| Q19 | {"a1": 8.8362} | {"a1": 0.0097} |

## Corrective re-search on competitor sub-questions (map, mock)

| Q | mode | sub-question | hits | chunk ids |
|---|---|---|---|---|
| Q19 | fts | a1.MS | 0 |  |
| Q19 | fts | a1.MER | 0 |  |
| Q19 | fts | a1.RJF | 0 |  |
| Q19 | hybrid-norerank | a1.MS | 0 |  |

Corrective re-searches in total (any sub-question): fts 3, hybrid-norerank 1.

## Pins (registered chunks, `fts.fetch_pinned` in both modes)

| Q | sub-question | pinned fts | pinned hyb | pins_cut same | result |
|---|---|---|---|---|---|
| Q1 | a1.MS | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | True | same |
| Q11 | a1.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q11 | a1.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q11 | a1.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q11 | a1.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q11 | a1.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q22 | a1.MS | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | True | same |
| Q22 | a1.SCHW | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | True | same |
| Q22 | a1.EDJ | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | True | same |
| Q22 | a1.MER | BAC-10K-2025#249 | BAC-10K-2025#249 | True | same |
| Q22 | a1.RJF | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | True | same |
| Q23 | a1.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q23 | a1.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q23 | a1.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q23 | a1.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q23 | a1.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |

Sub-questions with pins: 16; identical in both modes: 16.

## Reading (no decision here; #250 decides)

- **Competitor floor (known #250 difference, plans/0249 "Known difference").** Only Q19 has competitor
  sub-questions on the mock (rule) plans. In fts the floor across competitors is 8.8362 (0.3 x the
  2nd-best `ts_rank`) and cuts all 4 of Merrill's chunks (a1.MER emptied: ADR-018's own example);
  11 competitor passages reach the map. In hybrid-norerank the floor is 0.0097 (0.3 x the 2nd-best RRF
  score, a rank inside each firm) and cuts nothing: Merrill keeps 5 chunks and RJF 1, so 22 competitor
  passages reach the map. The corrective re-search added no competitor chunk in either mode (fts
  re-searched a1.MS, a1.MER, a1.RJF; hybrid-norerank a1.MS; 0 hits each). TL decision pending: accept
  as part of "retrieval" in #250, or fix first in a follow-up issue.
- **Refusal.** hybrid-norerank fails the refusal check on Q22 (`SCHW-10Q-2026Q2#56`) and Q24
  (`SCHW-TR-2026Q3#10`): a must-not chunk is retrieved; the mock map cites neither (`map_must_not` empty).
  Neither question has a competitor sub-question, so this is not the floor.
- **Pins** are identical in both modes on all 16 sub-questions that have any (gap 2 end to end).
- Plans are identical on 35/35 (rule plans; the plan key has no mode).
