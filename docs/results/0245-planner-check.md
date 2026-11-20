# #245 checks: sub-question decomposition (planner v3)

Plan: `plans/0245-decompose.md`. Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. Code at
`9cae90e` (mock runs and the real check). This report adds no code.

## 1. `SUBQUESTION_TOKENS` mock grid (0 calls)

The rule was fixed before the grid ran (plans/0245-decompose.md). It was scored on the 30 questions of
`evals/baselines/corpus-2026-11-19`; Q31-Q35 are NEW and were not compared. Each point used the rule
plan, which is one whole-question aspect for every scoped firm.

| SUBQUESTION_TOKENS | recall@pool | recall@final | tier 1 pool / final | PASS (30) | PASS -> FAIL | refusal gap / keyed | forbidden | tokens median / max / total (35) | eligible |
|---|---|---|---|---|---|---|---|---|---|
| baseline (plan-v2 rule plan) | 0.814 | 0.654 | 0.903 / 0.808 | 29 | - | 5/5, 22/22 | 0 | 33,643 / 60,322 / 980,854 (30) | - |
| 12000 | 0.814 | 0.593 | 0.903 / 0.733 | 29 | none | 5/5, 22/22 | 0 | 12,887 / 56,804 / 969,624 | no (recall@final) |
| 20000 | 0.814 | 0.640 | 0.903 / 0.790 | 29 | none | 5/5, 22/22 | 0 | 20,222 / 85,444 / 1,346,283 | no (recall@final) |
| **40000** | 0.814 | 0.654 | 0.903 / 0.808 | 29 | none | 5/5, 22/22 | 0 | 39,953 / 108,780 / 1,519,747 | **yes (pick)** |

At the pick:
- **The 30 baseline questions:** all 30 are UNCHANGED (status, recall and coverage). One-firm questions return the same lists.
- **Multi-firm questions:** they read more, because each firm now has its own 40k budget:

  | Question | Tokens before | Tokens at the pick |
  |---|---|---|
  | Q7 | 40k | 46k |
  | Q11 | 60k | 71k |
  | Q12 | 27k | 38k |
  | Q15 | 60k | 88k |
  | Q22 | 60k | 81k |
  | Q24 | 60k | 76k |
- **Q19 stays FAIL (1/5, as on the baseline):**
  - Schwab is now a competitor sub-question with 11 on-theme passages; before, it had 2 peer slots.
  - Merrill's 4 on-theme chunks are all cut by the floor across competitors. The sub-question is marked `floor_emptied`.
  - MS and RJF have no chunk on the theme.
  - The expected competitor press is not on the theme in this corpus (TL decision D-Q19, ADR-018).
- **Interim answer input:** at most ~123k tokens (Q33), against the DeepSeek guard limit of 933,000. The guard trims nothing.

The final mock run at `9cae90e` (default 40000, no env override) gives the same 35 chunk lists as the
40000 grid point. Its result is 33 PASS / 2 FAIL (Q19, Q33), refusal 8/8 with Q31-Q35 and keyed 26/26.

### Q31-Q35 (appended by #244; NEW, not in the baseline)

| Q | #245 mock | main (`eac02d1`) mock | Cause of a FAIL |
|---|---|---|---|
| Q31 | PASS (1.0, recall 1.0) | PASS | - |
| Q32 | PASS (1.0) | PASS | - |
| Q33 | **FAIL** (coverage 0.0, recall 0/2) | **FAIL** (same) | Its `expected_sources` are industry research (`MCK-ADVISOR-SHORTAGE-2025`, `KITCES-WELLBEING-2023`, pattern `THEME:research`). Q33 resolves to five firms with no theme (mode `entity`). Tier-5 research (no firm) is searched only in `entity+theme` mode (`research_pass`), so neither document is ever a candidate ("not in pool"). The cause is not #245: it fails the same way on main. |
| Q34 | PASS (1.0, recall 1.0) | PASS | - |
| Q35 | PASS (0.8, recall 1.0) | PASS | - |

## 2. Real planner check (9 DeepSeek calls, planner only, 0 answer calls)

- **Run:**
  - Script: `D:\ALLPROJECTS\EDJ\cache\ev245\run-real.ps1`, not committed.
  - Code gate: `git status` was clean and `src scripts config` had no diff against the mock-run sha `9cae90e`.
  - `.env` was copied for the run only and removed in `finally`.
  - Settings were pinned and logged: `deepseek-v4-pro`, `/beta`, thinking on, `plan-v3`, `SUBQUESTION_TOKENS=40000`, request version `ds-strict-1-think-on-a64000-p16000`, planner cap 16000, input limit 933000.
- **Command:** `eval_run.py --real --plan-only --max-calls 9 --questions Q19,Q11,Q23,Q24,Q1,Q3,Q22,Q12,Q15 --as-of 2026-11-17`.
- **Outcome:**
  - 9 calls, 0 reused, no 400, no ProviderStop.
  - 8 outputs were valid. Q19 was cut at the cap (below).
- **Usage:**
  - Input: 12,337 tokens, 8,576 of them cache hits.
  - Output: 63,059 tokens, 60,081 of them reasoning.
  - Wall time: 655 s.
- **Cost:**
  - Prices: DeepSeek deepseek-v4-pro, CNY per 1M tokens (Models & Pricing page, checked 2026-11-19).
  - Off-peak rates applied. The run was 12:42-12:54 Beijing time, Friday, which is outside the weekday 9-12 and 14-18 peak bands.
  - Off-peak: **about 0.87 CNY**.
  - At peak rates it would have been about 1.74 CNY.
- **Raw records:** `docs/results/0245-planner-raw/`. Each holds the call's input, `reasoning_content`, `stop_reason`, usage and wall time.

| Q | Plan source | Aspects | Sub-questions | Passages / tokens | Interim input (limit 933,000) | Planner out (reasoning) |
|---|---|---|---|---|---|---|
| Q1 | model | 6 | 6 | 278 / 82k | 93,521 | 8,384 (7,956) |
| Q3 | model | 5 | 5 | 211 / 56k | 65,388 | 3,749 (3,353) |
| Q11 | model | 4 | 20 | 773 / 216k | 244,188 | 3,093 (2,805) |
| Q12 | model | 9 | 10 | 427 / 124k | 140,630 | 11,297 (10,574) |
| Q15 | model | 5 | 15 | 813 / 237k | 267,031 | 8,947 (8,442) |
| Q19 | **fallback** (cut at max_tokens) | 1 (rule) | 5 | 32 / 8k | 12,062 | 16,000 (16,000) |
| Q22 | model | 2 | 10 | 453 / 127k | 144,958 | 2,191 (2,005) |
| Q23 | model | 1 | 5 | 283 / 82k | 93,851 | 575 (459) |
| Q24 | model | 4 | 20 | 848 / 239k | 270,219 | 8,823 (8,487) |

The guard drops nothing on any real plan. The largest interim input is ~270k (Q24), well under DeepSeek's 1M context.

### The plans
Each line gives the aspect, its kind, its metric and firms when set, the aspect text, then `||` and the search words.

**Q1** (MS). The plan has 6 aspects, all kind `fact`, giving 6 sub-questions. The implicit asks are kept.
- a1: the strategy to increase net new assets.
- a2: the initiatives and actions to increase net new assets.
- a3: the priorities stated for increasing net new assets.
- a4: the drivers of net new assets the firm names.
- a5: the competition named in relation to growing net new assets.
- a6: where the firm says it is losing ground or pulling back in net new assets.

**Q3** (SCHW). The plan has 5 aspects, giving 5 sub-questions. The implicit asks are kept: the stated strategy, how management describes the business, priorities, competition named, and where it is losing ground or pulling back.

**Q11** (five firms). The plan has 4 aspects × 5 firms = 20 sub-questions. Every asked aspect is there for every firm.
- a1: how each firm defines advisor headcount.
- a2 (metric `advisor_headcount`): how each firm reports advisor headcount.
- a3: what each firm's definition includes.
- a4: what each firm's definition excludes.

**Q12** (SCHW, EDJ). The plan has 9 aspects and 10 sub-questions. The firms are restricted as the question restricts them.
- a1-a4, `firms SCHW`:
  - how the firm uses its scale to acquire new clients;
  - low-cost acquisition tactics and channels;
  - the reported cost to acquire a client, or the closest disclosed figure;
  - acquisition results.
- a5-a8, `firms EDJ`:
  - the current acquisition approach;
  - scale, resources and constraints relevant to replicating;
  - how the firm could replicate the strategy;
  - the cost to acquire a client, or the closest disclosed figure.
- a9, kind `comparison`, no firm restriction, so both firms: a scale-driven model against an advisor-led model, and whether the strategy transfers.
- Sub-questions: a1-a4 and a9 for SCHW; a5-a9 for EDJ.

**Q15** (SCHW named; MS, EDJ, MER and RJF through "an advisor-led model"). The plan has 5 aspects and 15 sub-questions.
- a1, `firms SCHW`: how the self-directed brokerage and custody model earns on client assets.
- a2, `firms MS,EDJ,MER,RJF`: how the advisor-led model earns on client assets.
- a3, `firms SCHW`: the disclosed yield on client assets, or the closest figure.
- a4, `firms MS,EDJ,MER,RJF`: the disclosed yield on client assets, or the closest figure.
- a5, kind `comparison`, all five firms: the drivers of the difference.
- Sub-questions: a1, a3 and a5 for SCHW; a2, a4 and a5 for each advisor-led firm.

**Q19** (EDJ named; MS, SCHW, MER and RJF as competitors on the theme). The planner output was **cut at max_tokens**:
- `finish_reason` was `length`.
- All 16,000 output tokens were reasoning; there was no tool call.
- The record was saved as invalid. The run fell back to the rule plan; the call counted and was not re-rolled.

The decomposition still holds the four competitors, because code sets them, not the planner:
- Sub-questions: a1.EDJ (named); a1.MS, a1.SCHW, a1.MER, a1.RJF (competitor).

The saved reasoning shows the model working towards about 9 aspects. It weighs `firms [EDJ]` on the offering aspects; the home-firm guard turns that into "competitors kept". It also discusses how to keep "recommendations" and "strategic priorities" apart without merging them. It had not called the tool when the cap was reached.

**Q22** (five firms). The plan has 2 aspects × 5 = 10 sub-questions.
- a1, kind `series`, metric `net_new_assets`: net new assets by quarter.
- a2: each firm's own definition of the metric.

**Q23** (five firms). The plan has 1 aspect × 5 = 5 sub-questions.
- a1, kind `series`, metric `advisor_headcount`: advisor headcount for each of the last eight quarters.

**Q24** (five firms). The plan has 4 aspects × 5 = 20 sub-questions. Every asked aspect is there for every firm.
- a1: client assets per advisor as reported.
- a2: total client assets, as the closest disclosed numerator.
- a3, metric `advisor_headcount`: advisor headcount, as the closest disclosed denominator.
- a4, kind `comparison`: whether the figures can be compared across the firms.

### Findings (reported, not re-run)

1. **Q19 planner cut at the thinking-on cap. TL decision: raise the cap to 64000 and make one more call; see section 3.** The 16,000-token cap (#242: `DEEPSEEK_PLANNER_MAX_TOKENS[True]`) was all spent on reasoning about the plan-v3 aspect and firm rules.
   - Code still put the four competitors into the decomposition (rule-plan fallback).
   - Getting Q19's real aspects needs a larger thinking-on planner cap or thinking off (cap 8000), plus one more planner call.
   - That call is not planned here and is the TL's call.
2. **Retrieval refusal check on the real plans.** More sub-questions bring `must_not_return` chunks into the retrieved set of three gap-path questions. None of them is cited, since no answer call was made.

   | Question | `must_not_return` chunks retrieved | Sub-question that kept each |
   |---|---|---|
   | Q11 | `RJF-SUPP-2026Q1#14` | a1.RJF |
   | Q22 | `MS-PR-2026-04-15-01#15` (also retrieved in the #232 real run) | a1.MS |
   | Q22 | `SCHW-10Q-2026Q2#56` | a1.SCHW |
   | Q24 | `SCHW-TR-2026Q3#10` | a3.SCHW |
   | Q24 | `SCHW-PR-2026-07-21-01#24` | a4.SCHW |
   | Q24 | `SCHW-PR-2026-10-15-01#23` | a4.SCHW |

   The mock (rule plan) keeps refusal 5/5. With the real plans these questions read substitutes. Labelling them (`different_quantity` / adjacent) is #246's extraction step (ADR-021 rule 3).
3. **Totals grow with the decomposition, as ADR-021 intends.** 20-sub-question plans read ~216k-239k tokens (Q11, Q24) where the mock read 60k. The interim guard is not reached on DeepSeek.

## 3. Q19 at the planner cap 64000 (TL decision, 1 DeepSeek call)

TL decision, after finding 1: quality first. The thinking-on DeepSeek planner cap goes from 16000 to 64000, the same as the answer cap and DeepSeek's own thinking default. Exactly one more planner call is made, for Q19 only.
- **Why this is not a re-roll:** the cap is part of the request version (`ds-strict-1-think-on-a64000-p64000`), so this is a new, planned request after a cap finding, not the same request again.
- **Rule set by the TL:** if Q19 were cut again at 64000, stop and do not call again. It was not cut.
- **Run:**
  - Script: `D:\ALLPROJECTS\EDJ\cache\ev245\run-real-q19.ps1`, not committed. It uses the same code gate as section 2, now against `b6069e5`, the mock-run sha after the cap change. The mock lists are identical to section 1's.
  - `.env` was copied for the run only and removed in `finally`.
  - Command: `--real --plan-only --max-calls 1 --questions Q19`.
- **Result:**
  - Valid output: `finish_reason` `tool_calls`.
  - Output 9,507 tokens, of which **8,928 reasoning, against the 64,000 cap (14%)**.
  - Input 1,386 tokens (1,280 cache hits).
  - **Wall time 97.4 s.**
  - About **0.13 CNY** at off-peak rates (13:01 Beijing time).
- **Raw record:** `docs/results/0245-planner-raw/Q19-plan-7671939d689a522f3aa0397e.json`. The section 2 record, the cut one, is `Q19-plan-f39de5647e8a2f9372182001.json`.

**Q19 plan (plan-v3).** The plan has 7 aspects across 5 firms, giving 35 sub-questions: EDJ named; MS, SCHW, MER and RJF as competitors.

| Aspect | Kind | `firms` as the model wrote it | After code |
|---|---|---|---|
| a1: what younger investors and clients under 40 prefer from wealth managers and advisors | fact | [] | all five firms |
| a2: current offerings, products, services and channels | fact | [EDJ] | all five firms |
| a3: how younger-investor preferences are shaping offerings | recency | [EDJ] | all five firms |
| a4: how management describes younger investors | fact | [EDJ] | all five firms |
| a5: priorities stated for serving younger investors | fact | [EDJ] | all five firms |
| a6: competition named for younger investors | fact | [EDJ] | all five firms |
| a7: where it says it is losing ground or pulling back with younger investors | fact | [EDJ] | all five firms |

The model wrote `firms [EDJ]` on a2-a7. Under the home-firm guard, a list equal to the named firms counts as empty, so the competitors stay. Code logged six corrections of the form "aspect N: named firms only on a home-firm market question, competitors kept".

**Retrieval of this plan (0 calls):** 130 passages, ~38.9k tokens. The interim answer input is ~47.8k tokens against the 933,000 limit, so the guard drops nothing.

| Firm | Passages kept | Dropped by the floor across competitors |
|---|---|---|
| EDJ | 105 | - |
| SCHW | 19 | none |
| MER | 2 | 3 (BAC press) |
| RJF | 0 | 1; its only chunk, so the sub-question reads "nothing found" |
| MS | 0 | - |

Eval status (retrieval only) is still FAIL, but better than before:
- Coverage 0.2 -> **0.4**. `MER:press` is now hit by `BAC-PR-2026-01-14-01#12` and `BAC-PR-2026-07-14-01#10`.
- recall@final 0 -> **1.0**. The expected `EDJ-10K-2025#88` is now retrieved.
- MS, SCHW and RJF press are still not hit: no such chunk is on the theme in this corpus.

**Calls for #245 in total:** 10 DeepSeek planner calls (9 + 1) and 0 answer calls. Cost was about 0.87 + 0.13 = **1.00 CNY** at off-peak rates.
