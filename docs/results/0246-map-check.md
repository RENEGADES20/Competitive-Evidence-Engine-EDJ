# #246 checks: the map step (per-firm extraction, corrective re-search, evidence matrix)

Plan: `plans/0246-map.md`. Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. Code: the mock runs and
every real call were made at `46eba66` (the code gate compared `src scripts config` with it before each
phase; later commits on the branch touch only `plans/` and `docs/`).

## 1. Mock (0 calls)

- **35 questions, `--map`, against main `9c198a7`** (a temporary detached worktree): chunk lists,
  statuses, recall@pool / @final, coverage and forbidden hits are identical for all 35 (33 PASS / 2
  FAIL: Q19 and Q33, as on main; refusal 8/8). The map step never changes retrieval.
- The mock map labels every cell that has passages `fact` by construction, so its matrix gives
  `answer` wherever retrieval finds something and `answer_with_boundary` for Q12 and Q19. It proves the
  pipeline (calls, checks, re-search, rules, log), not label quality.
- **verify-cee** (`.verify-runs/20261120-000131-0a37dab`): ask-progress PASS (8 steps; the map line reads
  "Map step off (MAP=off): no extraction calls"; `llm_calls` `{"map": 0, "remap": 0, "answer": 0,
  "planner": 0}`), ask-answer, gap-path, invalid-chunk, coverage, filters, feedback PASS;
  download-document UNREACHABLE (no raw files in the worktree). open-citation's read-back step failed
  twice on this branch and passed once on main. The page captured at that step holds the cited passage
  (`CITED PASSAGE · EDJ-10K-2025#19`): it is the render race handed to #248 (the body is read once,
  right after the page signals done). This branch does not touch the source page.

## 2. Real map check (33 DeepSeek calls)

- **Model:** `deepseek-v4-pro`, `/beta` strict tools, thinking on.
- **Settings** (pinned and logged by `D:\ALLPROJECTS\EDJ\cache\ev246\run-real-map.ps1`): `MAP=on`,
  `MAP_CONCURRENCY=6`, `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1, request version
  `ds-strict-1-think-on-a64000-p64000`, planner cap 64000, map cap 64000. `.env` was copied in for each
  phase and removed in `finally`.
- **Phases:**
  - A: 5 planner calls.
  - Count: 0 calls. Round 1 = **20** map calls (bound 22).
  - B: cap 41, **28** calls made (20 map + 8 re-extraction).
  - Total **33** of the planned bound 48. No ProviderStop, no 400, no failed call.
- **Usage:** 719,303 input tokens (27,136 cache hits), 484,885 output tokens (445,219 of them reasoning).
  Wall time 5,567 s summed over the calls; about 48 min elapsed with 6 in parallel.
- **Cost:** about **19.3 CNY**.
  - The run was 14:06-14:54 Beijing time on Friday 2026-11-20, inside the 14-18 peak band, so peak
    rates apply.
  - Prices are those #245 used (DeepSeek Models & Pricing page, checked 2026-11-19).
  - At off-peak rates it would have been about 9.7 CNY.
- **Raw records:** `docs/results/0246-map-raw/` holds all 33 records. Each record has its input chunk
  ids, `stop_reason`, usage, `reasoning_content`, the tool input (or the invalid payload) and wall time.
- **Plans:** every question was re-planned with plan-v3.1 (D7 superseded by B2). Each record's
  `plan_origin` names its new record file (below). #245's v3 plans were not used.

### Plans (plan-v3.1) compared with #245's v3 plans

| Q | Record | Aspects v3 -> v3.1 | Proxy aspects | Sub-questions |
|---|---|---|---|---|
| Q11 | `Q11-plan-10d2767ebe7b4d270fd1576b.json` | 4 -> 4 (define, report, includes, excludes) | none | 20 |
| Q19 | `Q19-plan-fa97302df6c77faa55d22896.json` | 7 -> 13 (5 preference kinds split out; a13 comparison) | none | 65 |
| Q23 | `Q23-plan-1b401760014517b26292c5cb.json` | 1 -> 1 (series, `advisor_headcount`) | none | 5 |
| Q24 | `Q24-plan-9998b66bd82c7934b39de385.json` | 4 -> 4 | **a2 total client assets (numerator), a3 advisor headcount (denominator)** | 20 |
| Q26 | `Q26-plan-b3e8c05eb52fef281eb8877b.json` | new: 8 (all recency) | none | 8 |

### Results per question

| Q | Behavior by code | Effective expected | Map + re-map calls | Result |
|---|---|---|---|---|
| Q11 | `answer` | answer | 5 + 2 | matches |
| Q19 | `answer_with_boundary` | answer_with_boundary | 4 + 3 | matches; competitor rows present |
| Q23 | `answer` | answer | 5 + 0 | matches |
| Q24 | **undecided** (`None`) | answer | 5 + 2 | **does not match**: 3 of 5 map outputs invalid (finding 1) |
| Q26 | `answer` | answer | 1 + 1 | matches |

**Q11 matrix** (rows x a1 define / a2 report / a3 includes / a4 excludes):
- EDJ: fact, fact, fact, fact (EDJ-10Q-2026Q2#60, EDJ-10K-2025#130, EDJ-10Q-2025Q2#89 and #80).
- RJF: fact x 4 (RJF-10K-2025#10, #12, #228; RJF-TR-2025Q3#4 "8,943 financial advisors" 2025-09-30).
- SCHW: a1 different_quantity (SCHW-10K-2025#120: full-time equivalent employees, "a broader all-employee
  headcount measure"), a2-a4 fact (10-Q and transcript text on Financial / Wealth Consultants).
- MS: a2 fact (MS-SUPP-2020Q4#1: 15,950 / 15,469 / 15,468 Wealth Management representatives, 2020-12-31,
  2020-09-30, 2019-12-31). a1, a3 and a4 are not_found after re-search (39, 29 and 16 new chunks were
  read, 1 re-extraction).
- MER: a1-a3 different_quantity (BAC-SUPP-2023Q4#2 "Total wealth advisors" across GWIM and Consumer
  Banking, a wider unit; BAC-DECK-2025-investor-day#9 ">15K"). a4 is not_found after re-search.
- Marks: a1-a4 `different_basis`. The comparability caveat quotes each firm's registered definition, and
  the GWIM caveat is added.
- Rejected citations: 3 items cited a chunk outside their cell's retrieved set. These are flagged
  `unmatched_citation`; their other ids still count.

**Q23 matrix** (a1 headcount, last eight quarters):
- EDJ fact: 19,885 (2024-09-27), 19,413 (2025-03-28), 20,309 (2025-06-27), 20,429 (2025-09-26), 19,674
  (2026-03-27), 20,514 (2026-06-26), from the 10-Qs.
- RJF fact: 8,943 (2025-09-30, RJF-TR-2025Q3#4 and RJF-10K-2025#228), about 9,000.
- MS different_quantity: the 2020 counts (MS-SUPP-2020Q4#1), "outside the window asked". By rule 3 this is
  arguably partial coverage, not a different quantity (finding 3).
- SCHW different_quantity: 16,000 RIA client firms (SCHW-TR-2026Q3#10) and 250 consultants (a narrower
  group).
- MER different_quantity: BAC Total wealth advisors, a wider unit.
- Mark `different_basis` with the caveat; GWIM caveat.

**Q24 matrix** (a1 per advisor / a2 assets, proxy / a3 advisors, proxy / a4 comparison):
- SCHW: a1 different_quantity after re-search; a2 fact ($13.08T 2026-06-30, $11.77T 2026-03-31, ...); a3
  different_quantity (16,000 RIA firms SCHW-TR-2026Q3#10, 33,000 employees); a4 fact.
- MER: a1 not_found after re-search; a2 fact (BAC GWIM client balances, $4,240,601M 2026-09-30); a3
  different_quantity (BAC Total wealth advisors, a wider unit); a4 fact.
- EDJ, MS, RJF: **failed**, because the output was invalid (finding 1). **a2.EDJ and a3.EDJ did not come
  back as fact in a valid output.**
- Behavior **undecided**, reason "no fact, extraction failed for Morgan Stanley, Edward Jones, Raymond
  James Financial". `incomplete_note`: "This answer is incomplete: the evidence for Morgan Stanley, Edward
  Jones, Raymond James Financial could not be extracted ...". No "does not support" gap is given for the
  aspects with failed cells (D5).
- Information only, never used by code: the invalid EDJ payload is valid JSON once its stray trailing
  `}` is removed. In it, a2.EDJ is a fact ($2,647B, 2026-06-26, EDJ-10Q-2026Q2#59), a3.EDJ is a fact
  (20,514 financial advisors, 2026-06-26, EDJ-10Q-2026Q2#60), and a1.EDJ proposes ratio a2.EDJ#0 /
  a3.EDJ#0. Code would have accepted that derivation (same period and scope).
- **Derivations accepted: none**, so no derivation input chunk ids are recorded.

**Q19 matrix** (13 aspects x EDJ, MS, SCHW, MER, RJF + research):
- EDJ: a7-a12 fact (management on younger clients, offerings, priorities, competition, where it loses
  ground, recent changes; EDJ-10K-2025#8, #10, #22, #26, #56, #57, #59, #88, #304; trade press). a1-a6
  (investor preferences) not_found after re-search.
- **Competitor rows:**
  - SCHW: a1-a6 fact (SCHW-TR-2025Q3#11, #12, #39; SCHW-TR-2026Q2#36: what younger clients prefer, from
    Schwab's own calls); a7-a12 not_found.
  - MER: a2 different_quantity (BAC-PR-2026-01-14-01#12, digitally active Private Bank relationships);
    the rest not_found.
  - MS: no passage was retrieved. All cells are code not_found; 12 re-searches found nothing.
  - RJF: no passage was retrieved. Code not_found; 1 re-search found 1 chunk, and the re-extraction gave
    not_found.
- Research: a1, a4, a5 fact (CERULLI-GWT-2025#1; BOFA-PB-STUDY-2024#0 and -2026#15).
- a13 (comparison, the normative ask) decides nothing. Behavior `answer_with_boundary` (rule 1e).

**Q26 matrix** (RJF, 8 recency aspects):
- a1, a2, a4-a8 fact, a3 not_found after re-search. All cited chunks are RJF trade press dated
  2026-08-19 to 2026-11-12, inside the window (the window is a SQL filter).
- a7 (advisor recruiting) has 6 items with rejected citations and 4 with `number_not_found` (finding 4).
- Marks: `unverified` on the qualitative aspects that carry a figure (finding 5).

### Must-not chunks (`map_must_not`)

| Q | Must-not chunk | Retrieved by v3.1 | In the matrix |
|---|---|---|---|
| Q11 | `RJF-SUPP-2026Q1#14` (FA compensation table) | yes | not cited |
| Q24 | `SCHW-TR-2026Q3#10` (16,000 RIA client firms) | yes | a3.SCHW **different_quantity** ("independent RIA firms ... not Schwab's own headcount") |
| Q24 | `SCHW-PR-2026-07-21-01#24`, `SCHW-PR-2026-10-15-01#23` (FTE employees) | no (the v3.1 plan does not retrieve them; #245's v3 plan did) | - |

- No must-not chunk is cited by a fact.
- No derivation was accepted, so no must-not chunk sits behind a derivation input.
- Q23 also cites `SCHW-TR-2026Q3#10` as different_quantity. It is not in Q23's must-not list.

### Findings (reported, not re-run)

1. **Q24: 3 of 5 map outputs invalid, all the same way.**
   - DeepSeek's strict tool arguments for map.EDJ, map.MS and map.RJF each hold a complete, valid JSON
     object followed by one stray `}` ("Extra data"; arguments of 4,837, 6,361 and 7,550 characters).
   - By the invalid-output rule these are saved and never re-rolled, so the cells are `failed` and the
     behavior is undecided instead of `answer`.
   - The EDJ payload holds exactly the expected same-basis assets and advisors and the ratio proposal.
   - The Q24 acceptance item is therefore not met by this run.
   - **Open for the TL** (either option is a decision, not made here):
     - (a) Treat a JSON object followed only by stray closing braces or whitespace as valid, with a flag,
       and re-check the saved records at 0 calls.
     - (b) Keep the rule and plan one re-run of Q24's three calls.
2. **Rejected citations are common in long outputs.** Q26 a7 has 6 items whose ids are outside the cell's
   retrieved set (chunks kept under other aspects and not in a7's pool). Q11 has 3 and Q24 SCHW has 3.
   They are flagged, never dropped, and the cells still count when another id holds.
3. **Q23 MS:** the model labels Morgan Stanley's 2020 counts `different_quantity` ("outside the eight
   quarters asked"). Rule 3 reads a figure for other periods as partial coverage. This is a prompt point
   for #247 / extract-v2, not a code rule.
4. **Flags:** `number_not_found` on 4 items (all Q26 trade-press advisor counts), `quote_not_found` on 15
   (Q19 3, Q23 5 BAC table quotes, Q24 2, Q26 5), `period_unparsed` on 7. The flags work as specified;
   the reduce step must keep flagged figures out of computed figures.
5. **The unverified mark fires on qualitative aspects that hold a figure** (Q19 a1, a5, a11; Q26 a1, a2,
   a4-a6). The mark text is accurate but noisy. #247 can show it only for aspects whose figures it
   compares.
6. **Q19:** MS and RJF have no chunk on the theme in this corpus (as in #245). The rows exist and every
   cell is a named gap.

**Calls for #246 in total:** 33 DeepSeek calls (5 planner, 20 map, 8 re-extraction), 0 answer calls.
Cost about 19.3 CNY at peak rates.
