# #249 hybrid-norerank vs fts on the same plans (mock, 0 real calls)

fts: `mockplans-fts\report.json`  
hybrid-norerank: `mockplans-hnr\report.json`

Plans: rule plans (mock) in both runs; identical by construction (checked below).

## Summary

| measure | fts | hybrid-norerank |
|---|---|---|
| PASS | None | 26 |
| refusal gap | 3/5 | 3/5 |
| refusal all keyed | 18/22 | 19/22 |
| forbidden hits | None | 0 |
| tier-1 doc recall | 0.972 | 0.962 |
| tier-1 passage recall | 0.947 | 0.921 |
| recall@pool | 0.967 | 0.962 |
| recall@final | 0.91 | 0.936 |
| passages | 15319 | 11674 |
| tokens est | 4364868 | 3212653 |
| median search s | None | 8.199 |
| statuses | {'PASS': 25, 'FAIL': 5, 'NOT_EVALUATED': 0} | {'PASS': 26, 'FAIL': 4, 'NOT_EVALUATED': 0} |

## Per question

| Q | plan same | status fts / hyb | refusal fts / hyb | behavior fts / hyb | chunks fts / hyb | shared | doc recall fts / hyb |
|---|---|---|---|---|---|---|---|
| Q1 | yes | PASS / PASS | ok / ok | answer / answer | 232 / 118 | 94 | 1.0 / 1.0 |
| Q2 | yes | PASS / PASS | ok / ok | answer / answer | 291 / 185 | 153 | 1.0 / 1.0 |
| Q3 | yes | PASS / PASS | ok / ok | answer / answer | 228 / 161 | 114 | 1.0 / 1.0 |
| Q4 | yes | PASS / PASS | ok / ok | answer / answer | 145 / 143 | 139 | 1.0 / 1.0 |
| Q5 | yes | PASS / PASS | ok / ok | answer / answer | 51 / 32 | 19 | 1.0 / 0.833 |
| Q6 | yes | PASS / PASS | ok / ok | answer / answer | 136 / 100 | 59 | 1.0 / 1.0 |
| Q7 | yes | PASS / PASS | ok / ok | answer / answer | 885 / 592 | 464 | 1.0 / 1.0 |
| Q8 | yes | PASS / PASS | - / - | answer / answer | 236 / 149 | 111 | None / None |
| Q9 | yes | PASS / PASS | - / - | answer / answer | 338 / 285 | 213 | None / None |
| Q10 | yes | PASS / PASS | - / - | answer / answer | 576 / 407 | 261 | None / None |
| Q11 | yes | FAIL / PASS | FAIL / ok | answer / answer | 807 / 536 | 371 | 1.0 / 1.0 |
| Q12 | yes | PASS / PASS | - / - | answer_with_boundary / answer_with_boundary | 423 / 232 | 184 | None / None |
| Q13 | yes | PASS / PASS | ok / ok | answer / answer | 252 / 170 | 122 | 1.0 / 1.0 |
| Q14 | yes | PASS / PASS | - / - | answer / answer | 362 / 253 | 196 | None / None |
| Q15 | yes | PASS / PASS | ok / ok | answer / answer | 575 / 424 | 275 | 1.0 / 1.0 |
| Q16 | yes | PASS / PASS | - / - | answer / answer | 1569 / 1516 | 888 | None / None |
| Q17 | yes | PASS / PASS | ok / ok | answer / answer | 1006 / 791 | 575 | 1.0 / 1.0 |
| Q18 | yes | PASS / PASS | - / - | refuse / refuse | 267 / 290 | 94 | None / None |
| Q19 | yes | FAIL / FAIL | ok / ok | answer_with_boundary / answer_with_boundary | 189 / 177 | 116 | 1.0 / 1.0 |
| Q20 | yes | PASS / PASS | ok / ok | answer / answer | 832 / 882 | 520 | 0.75 / 1.0 |
| Q21 | yes | PASS / PASS | - / - | answer / answer | 2449 / 1634 | 1368 | None / None |
| Q22 | yes | FAIL / FAIL | FAIL / FAIL | answer / answer | 459 / 390 | 279 | 1.0 / 1.0 |
| Q23 | yes | PASS / PASS | ok / ok | answer / answer | 382 / 335 | 205 | 1.0 / 0.75 |
| Q24 | yes | FAIL / FAIL | FAIL / FAIL | answer / answer | 816 / 614 | 448 | 1.0 / 1.0 |
| Q25 | yes | FAIL / FAIL | FAIL / FAIL | answer / answer | 1272 / 732 | 492 | 1.0 / 1.0 |
| Q26 | yes | PASS / PASS | ok / ok | answer / answer | 51 / 45 | 44 | None / None |
| Q27 | yes | PASS / PASS | ok / ok | answer / answer | 109 / 108 | 108 | 0.778 / 0.778 |
| Q28 | yes | PASS / PASS | ok / ok | answer / answer | 137 / 149 | 113 | 1.0 / 1.0 |
| Q29 | yes | PASS / PASS | ok / ok | answer / answer | 123 / 101 | 57 | 1.0 / 1.0 |
| Q30 | yes | PASS / PASS | ok / ok | answer / answer | 121 / 123 | 104 | 1.0 / 1.0 |

Plans (aspects and sub-questions) identical on 30 / 30 questions.

## Competitor floor (ADR-018 safeguard across competitors)

Per competitor sub-question, from `plan.searched`: before = the main search's hits (`passages` minus the period / pinned hits added to it) + `len(floor_dropped)`; after = the main search's hits kept by the floor; to map = `passages` (after the floor, plus the period and pin passes).

| Q | sub-question | fts before -> after floor (dropped, emptied) | to map fts | hyb before -> after floor (dropped, emptied) | to map hyb |
|---|---|---|---|---|---|
| Q19 | a1.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a2.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a3.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a4.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a5.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a6.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a7.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a8.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a9.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a10.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a11.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a12.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a13.MS | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a1.SCHW | 12 -> 12 (0, False) | 12 | 16 -> 16 (0, False) | 16 |
| Q19 | a2.SCHW | 4 -> 4 (0, False) | 4 | 3 -> 3 (0, False) | 3 |
| Q19 | a3.SCHW | 3 -> 3 (0, False) | 3 | 0 -> 0 (0, False) | 0 |
| Q19 | a4.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a5.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a6.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a7.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a8.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a9.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a10.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a11.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a12.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a13.SCHW | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a1.MER | 5 -> 1 (4, False) | 1 | 5 -> 5 (0, False) | 5 |
| Q19 | a2.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a3.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a4.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a5.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a6.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a7.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a8.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a9.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a10.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a11.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a12.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a13.MER | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a1.RJF | 1 -> 0 (1, True) | 0 | 1 -> 1 (0, False) | 1 |
| Q19 | a2.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a3.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a4.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a5.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a6.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a7.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a8.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a9.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a10.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a11.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a12.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |
| Q19 | a13.RJF | 0 -> 0 (0, False) | 0 | 0 -> 0 (0, False) | 0 |

Totals: fts dropped 5, emptied 1, competitor passages to the map 20; hybrid-norerank dropped 0, emptied 0, competitor passages to the map 25.

Questions with no competitor sub-question: Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12, Q13, Q14, Q15, Q16, Q17, Q18, Q20, Q21, Q22, Q23, Q24, Q25, Q26, Q27, Q28, Q29, Q30.

Floor value per aspect (`plan.competitor_floor`):

| Q | fts | hybrid-norerank |
|---|---|---|
| Q19 | {"a1": 14.5424, "a2": 3.0714, "a3": 0.8479} | {"a1": 0.0097, "a2": 0.0081} |

## Corrective re-search on competitor sub-questions (map, mock)

| Q | mode | sub-question | hits | chunk ids |
|---|---|---|---|---|
| Q19 | fts | a1.MS | 0 |  |
| Q19 | fts | a2.MS | 0 |  |
| Q19 | fts | a3.MS | 0 |  |
| Q19 | fts | a4.MS | 0 |  |
| Q19 | fts | a5.MS | 0 |  |
| Q19 | fts | a6.MS | 0 |  |
| Q19 | fts | a7.MS | 0 |  |
| Q19 | fts | a8.MS | 0 |  |
| Q19 | fts | a9.MS | 0 |  |
| Q19 | fts | a10.MS | 0 |  |
| Q19 | fts | a11.MS | 0 |  |
| Q19 | fts | a12.MS | 0 |  |
| Q19 | fts | a4.SCHW | 0 |  |
| Q19 | fts | a5.SCHW | 0 |  |
| Q19 | fts | a6.SCHW | 0 |  |
| Q19 | fts | a7.SCHW | 0 |  |
| Q19 | fts | a8.SCHW | 0 |  |
| Q19 | fts | a9.SCHW | 0 |  |
| Q19 | fts | a10.SCHW | 0 |  |
| Q19 | fts | a11.SCHW | 0 |  |
| Q19 | fts | a12.SCHW | 0 |  |
| Q19 | fts | a2.MER | 4 | MER-PR-web-becoming-a-merrill-lynch-advisor#3, BAC-PR-2026-10-14-01#11, BAC-PR-2026-07-14-01#10, BAC-PR-2026-04-15-01#10 |
| Q19 | fts | a3.MER | 0 |  |
| Q19 | fts | a4.MER | 0 |  |
| Q19 | fts | a5.MER | 0 |  |
| Q19 | fts | a6.MER | 0 |  |
| Q19 | fts | a7.MER | 0 |  |
| Q19 | fts | a8.MER | 0 |  |
| Q19 | fts | a9.MER | 0 |  |
| Q19 | fts | a10.MER | 0 |  |
| Q19 | fts | a11.MER | 0 |  |
| Q19 | fts | a12.MER | 0 |  |
| Q19 | fts | a1.RJF | 0 |  |
| Q19 | fts | a2.RJF | 1 | RJF-DECK-2025-investor-day#42 |
| Q19 | fts | a3.RJF | 0 |  |
| Q19 | fts | a4.RJF | 0 |  |
| Q19 | fts | a5.RJF | 0 |  |
| Q19 | fts | a6.RJF | 0 |  |
| Q19 | fts | a7.RJF | 0 |  |
| Q19 | fts | a8.RJF | 0 |  |
| Q19 | fts | a9.RJF | 0 |  |
| Q19 | fts | a10.RJF | 0 |  |
| Q19 | fts | a11.RJF | 0 |  |
| Q19 | fts | a12.RJF | 0 |  |
| Q19 | hybrid-norerank | a1.MS | 0 |  |
| Q19 | hybrid-norerank | a2.MS | 0 |  |
| Q19 | hybrid-norerank | a3.MS | 0 |  |
| Q19 | hybrid-norerank | a4.MS | 0 |  |
| Q19 | hybrid-norerank | a5.MS | 0 |  |
| Q19 | hybrid-norerank | a6.MS | 0 |  |
| Q19 | hybrid-norerank | a7.MS | 0 |  |
| Q19 | hybrid-norerank | a8.MS | 0 |  |
| Q19 | hybrid-norerank | a9.MS | 0 |  |
| Q19 | hybrid-norerank | a10.MS | 0 |  |
| Q19 | hybrid-norerank | a11.MS | 0 |  |
| Q19 | hybrid-norerank | a12.MS | 0 |  |
| Q19 | hybrid-norerank | a3.SCHW | 0 |  |
| Q19 | hybrid-norerank | a4.SCHW | 0 |  |
| Q19 | hybrid-norerank | a5.SCHW | 0 |  |
| Q19 | hybrid-norerank | a6.SCHW | 0 |  |
| Q19 | hybrid-norerank | a7.SCHW | 0 |  |
| Q19 | hybrid-norerank | a8.SCHW | 0 |  |
| Q19 | hybrid-norerank | a9.SCHW | 0 |  |
| Q19 | hybrid-norerank | a10.SCHW | 0 |  |
| Q19 | hybrid-norerank | a11.SCHW | 0 |  |
| Q19 | hybrid-norerank | a12.SCHW | 0 |  |
| Q19 | hybrid-norerank | a2.MER | 0 |  |
| Q19 | hybrid-norerank | a3.MER | 0 |  |
| Q19 | hybrid-norerank | a4.MER | 0 |  |
| Q19 | hybrid-norerank | a5.MER | 0 |  |
| Q19 | hybrid-norerank | a6.MER | 0 |  |
| Q19 | hybrid-norerank | a7.MER | 0 |  |
| Q19 | hybrid-norerank | a8.MER | 0 |  |
| Q19 | hybrid-norerank | a9.MER | 0 |  |
| Q19 | hybrid-norerank | a10.MER | 0 |  |
| Q19 | hybrid-norerank | a11.MER | 0 |  |
| Q19 | hybrid-norerank | a12.MER | 0 |  |
| Q19 | hybrid-norerank | a2.RJF | 0 |  |
| Q19 | hybrid-norerank | a3.RJF | 0 |  |
| Q19 | hybrid-norerank | a4.RJF | 0 |  |
| Q19 | hybrid-norerank | a5.RJF | 0 |  |
| Q19 | hybrid-norerank | a6.RJF | 0 |  |
| Q19 | hybrid-norerank | a7.RJF | 0 |  |
| Q19 | hybrid-norerank | a8.RJF | 0 |  |
| Q19 | hybrid-norerank | a9.RJF | 0 |  |
| Q19 | hybrid-norerank | a10.RJF | 0 |  |
| Q19 | hybrid-norerank | a11.RJF | 0 |  |
| Q19 | hybrid-norerank | a12.RJF | 0 |  |

Corrective re-searches in total (any sub-question): fts 61, hybrid-norerank 59.

## Pins (registered chunks, `fts.fetch_pinned` in both modes)

| Q | sub-question | pinned fts | pinned hyb | pins_cut same | result |
|---|---|---|---|---|---|
| Q2 | a5.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | True | same |
| Q2 | a6.RJF | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | True | same |
| Q4 | a3.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q6 | a2.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | True | same |
| Q7 | a4.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q7 | a4.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q7 | a4.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | True | same |
| Q11 | a1.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q11 | a2.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q11 | a3.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q11 | a4.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q11 | a1.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q11 | a2.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q11 | a3.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q11 | a4.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q11 | a1.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q11 | a2.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q11 | a3.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q11 | a4.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q11 | a1.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q11 | a2.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q11 | a3.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q11 | a4.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q11 | a1.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q11 | a2.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q11 | a3.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q11 | a4.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q14 | a8.RJF | RJF-10K-2025#228 | RJF-10K-2025#228 | True | same |
| Q21 | a14.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q21 | a15.MS | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | True | same |
| Q21 | a14.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q21 | a15.SCHW | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | True | same |
| Q21 | a14.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q21 | a15.EDJ | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | True | same |
| Q21 | a14.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q21 | a15.MER | BAC-10K-2025#249 | BAC-10K-2025#249 | True | same |
| Q21 | a14.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | True | same |
| Q21 | a15.RJF | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | True | same |
| Q22 | a1.MS | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | MS-10K-2025#166, MS-10K-2025#165, MS-SUPP-2025Q4#34 | True | same |
| Q22 | a1.SCHW | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | SCHW-10K-2025#119, SCHW-MONTHLY-2026-01#8 | True | same |
| Q22 | a1.EDJ | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | EDJ-10Q-2026Q2#60, EDJ-10K-2025#130 | True | same |
| Q22 | a1.MER | BAC-10K-2025#249 | BAC-10K-2025#249 | True | same |
| Q22 | a1.RJF | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | RJF-10K-2025#224, RJF-SUPP-2025Q4#8 | True | same |
| Q23 | a1.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q23 | a1.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q23 | a1.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q23 | a1.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q23 | a1.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24, RJF-DECK-2025-investor-day#43 | True | same |
| Q24 | a2.MS | MS-10K-2025#125, MS-SUPP-2026Q3#38, MS-SUPP-2020Q4#3 | MS-10K-2025#125, MS-SUPP-2026Q3#38, MS-SUPP-2020Q4#3 | True | same |
| Q24 | a3.MS | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | MS-SUPP-2020Q4#3, MS-SUPP-2020Q4#1, MS-SUPP-2025Q4#36, MS-SUPP-2026Q3#38, MS-10K-2025#167, MS-ADV1A-2026#1 | True | same |
| Q24 | a3.SCHW | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | SCHW-ADV1A-2026#1, SCHW-10K-2025#18, SCHW-10K-2025#23 | True | same |
| Q24 | a2.EDJ | EDJ-10Q-2026Q2#59, EDJ-10K-2025#130 | EDJ-10Q-2026Q2#59, EDJ-10K-2025#130 | True | same |
| Q24 | a3.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q24 | a2.MER | BAC-SUPP-2023Q4#2 | BAC-SUPP-2023Q4#2 | True | same |
| Q24 | a3.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q24 | a2.RJF | RJF-10K-2025#228 | RJF-10K-2025#228 | True | same |
| Q24 | a3.RJF | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | RJF-10K-2025#228, RJF-10K-2025#227, RJF-10K-2025#24 | True | same |
| Q27 | a3.MER | BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q27 | a4.MER | BAC-10K-2025#249 | BAC-10K-2025#249 | True | same |
| Q28 | a3.EDJ | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | EDJ-10K-2025#130, EDJ-10K-2025#148, EDJ-10Q-2026Q2#60, EDJ-10K-2025#29 | True | same |
| Q28 | a3.MER | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | BAC-SUPP-2023Q4#2, BAC-DECK-2025-investor-day#9, BAC-10K-2025#246, MER-ADV1A-2026#1 | True | same |
| Q29 | a2.MS | MS-SUPP-2020Q4#3 | MS-SUPP-2020Q4#3 | True | same |
| Q30 | a2.MER | BAC-SUPP-2023Q4#2 | BAC-SUPP-2023Q4#2 | True | same |
| Q30 | a3.MER | BAC-SUPP-2023Q4#2 | BAC-SUPP-2023Q4#2 | True | same |

Sub-questions with pins: 64; identical in both modes: 64.

