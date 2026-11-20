# #247 checks: the reduce step (prompt v5 over the evidence matrix)

Plan: `plans/0247-reduce.md`. Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. Code: every real call
was made at `4138847` (code gate: `git status` clean and `src scripts config` identical to `7b9a5b4`,
whose only difference from the mock-run sha `b6e0f02` is the verify driver). **Blind scoring: 5/8 PASS**
(section 3; Q11, Q23, Q24 FAIL). Follow-up findings: section 4.

## 1. Zero-call checks

- **pytest**: 901 passed locally; CI (no database) needed two eval tests to fake the corrective re-search
  (`dd099d7`).
- **Re-check of #246's 33 records** under the new matrix code, extract-v1, no key, `--max-calls 0`: 0 calls.
  - Q24 a1.MS is now derived: "Wealth Management segment" and "Wealth Management" are normalised to the
    same scope. RJF is still rejected (whole firm vs Private Client Group).
  - The `unverified` mark is gone from Q19 a1 / a5 / a11, Q26 a1, a2, a4-a6 and Q24 a4. Q24 a1 and a2
    keep it.
  - Q23 period gaps: EDJ 2024Q4, 2025Q4, 2026Q3; RJF every asked quarter but 2025Q3.
  - Every other label and behavior is unchanged.
- **Mock 35 questions** against main `a32eb64` with `--map`:
  - chunk lists, statuses, recall, coverage, forbidden hits and refusal are identical (33 PASS / 2 FAIL,
    refusal 8/8);
  - the mock reduce answered all 35: 0 `outside_matrix`, 0 `part_gap`, 0 why-lines missing, 0
    comparison claims missing, behavior = matrix behavior.
- **verify-cee**:
  - ask-answer PASS, including the new matrix step: `answer|answer|false|0|0`, no unlinked chip;
  - ask-progress PASS after a driver fix; gap-path, invalid-chunk, coverage, filters and feedback PASS;
  - open-citation passed in the full run; its read-back failed once on the re-run (the #248 render race);
  - download-document UNREACHABLE (no raw files).

## 2. Real check (46 DeepSeek calls)

- **Model**: `deepseek-v4-pro`, `/beta` strict tools, thinking on.
- **Settings**: `MAP=on`, `MAP_CONCURRENCY=6`, `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1.1, prompt
  v5, request version `ds-strict-1-think-on-a64000-p64000`. Pinned and logged by
  `D:\ALLPROJECTS\EDJ\cache\ev247\run-real-reduce.ps1` (with a `.sh` for Mac). `.env` was copied in for
  each phase and removed in `finally`.
- **Phases**:
  - A: 3 planner calls (Q1, Q3, Q22). The five targets reused their #246 plan records.
  - Count: 0 calls. Round 1 = 27 map calls (bound 30).
  - B: cap 63, **43 made** (27 map, 8 re-extraction, 8 reduce).
  - Total **46** of the planned 69.
  - No ProviderStop, no 400, no failed call, no invalid output.
  - 5 map outputs carried stray closing braces (`trailing_braces`, accepted by the #246 rule): Q22
    SCHW / MER / RJF, Q23 RJF, Q26 RJF.
- **Usage**: 1,072,899 input tokens (52,480 cache hits) and 776,405 output tokens (693,414 of them
  reasoning). 8,601 s of call time; phase B took 80 min elapsed.
- **Cost**: about **$4.28**.
  - Rates, USD per 1M tokens, `deepseek-v4-pro`, peak / off-peak: input cache hit 0.044 / 0.022, cache
    miss 1.32 / 0.66, output 3.96 / 1.98. Source: `docs/results/w11-deepseek-baseline.md` "Cost" (TL
    comment on #243; pricing page read 2026-11-20).
  - Peak hours are 01:00-04:00 and 06:00-10:00 UTC on weekdays. The band is decided by completion time.
  - 43 of the 46 calls finished at peak.
  - The 8 reduce calls cost $0.82 in all: $0.03-$0.21 each, up to 49,782 output tokens (Q24).
- **Raw records**: `docs/results/0247-raw/`, 46 records.

### Results per question (behavior by code, the answer, the code checks)

| Q | Behavior | Map + re-map | Reduce | Claims / adjacent / gaps | Code checks |
|---|---|---|---|---|---|
| Q1 | answer | 1 + 0 | 1 | 18 / 3 / 2 | clean |
| Q3 | answer | 1 + 0 | 1 | 23 / 0 / 0 | clean; a5 "where Schwab says it is losing ground" is a fact |
| Q11 | answer | 5 + 3 | 1 | 30 / 6 / 10 | 1 `number_not_found`; comparability caveats |
| Q19 | answer_with_boundary | 4 + 3 | 1 | 55 / 3 / 58 | hand-off last; **57 items re-sorted** (a12 is a recency aspect) |
| Q22 | answer | 5 + 0 | 1 | 42 / 9 / 2 | 11 `date_mismatch` |
| Q23 | answer | 5 + 0 | 1 | 16 / 9 / 5 | 3 period gaps named; MS 2020 counts are claims |
| Q24 | answer | 5 + 1 | 1 | 25 / 40 / 2 | comparison claim present; 3 `computed`, 2 `number_not_found`, 2 `date_mismatch` |
| Q26 | answer | 1 + 1 | 1 | 32 / 0 / 2 | why-line on 32 of 32 claims; newest first |

For every question: 0 `outside_matrix`, 0 `part_gap`, 0 comparison claims missing, 0 why-lines missing,
the model's behavior equals the decided one, and no answer was built by code.

**Per-target notes**:
- **Q11**: matrix MS a2 fact; SCHW a1-a3 different quantity, a4 fact; EDJ a2 fact (a1, a3, a4 not found);
  MER a1-a3 fact; RJF a1-a4 fact. 103 corrective re-search chunks joined the answer's hits. Label drift
  against #246: EDJ a1 / a3 / a4 were facts there and are not found now.
- **Q19**: EDJ has 23 claims, SCHW 9, research 22. MS, MER and RJF have no claim; every one of their
  cells has a code gap.
- **Q23**: with extract-v1.1 MS is a fact (the 2020 counts, rule 3). The period gaps are:
  - MS: "not found for the asked periods (2024Q4-2026Q3) ...; figures for other periods are listed";
  - EDJ: 2024Q4, 2025Q4, 2026Q3;
  - RJF: all but 2025Q3.

  The model also wrote a why-line on all 16 claims, though Q23 has neither a window nor a recency aspect.
- **Q24**: matrix and derived figures:
  - Derived by code: EDJ $2,647 billion / 20,514 = 129,033,831 USD per advisor (2026-06-26); MS 3,999
    billion / 15,950 = 250,721,003 (2020-12-31); RJF 1,730.6 billion / 8,943 = 193,514,481 (2025-09-30).
  - The comparison claim (part a4) says the comparison is not valid on this evidence: per-advisor figures
    exist for three firms only, at different periods and scopes. It cites them.
  - Caveats: the advisor-headcount comparability caveat and GWIM.

### Must-not chunks (`map_must_not`)

| Q | Must-not chunk | In the matrix |
|---|---|---|
| Q24 | `SCHW-TR-2026Q3#10` (16,000 RIA client firms) | a3.SCHW `different_quantity` (correct); **a4.SCHW `fact`** (the comparison aspect: Schwab's own statement, cited as evidence about comparability; comparison aspects decide nothing) |
| Q11 | `RJF-SUPP-2026Q1#14` | not cited |
| Q22 | `MS-PR-2026-04-15-01#15`, `SCHW-10Q-2026Q2#56` | not cited |

### Findings (reported, not re-run)

1. **Q19 re-sorted newest first.** It has a recency aspect (a12), so D4 re-sorted all 57 items by date,
   which mixes the aspect grouping. A narrower rule (re-sort only the recency aspect's items) is a
   candidate for #248 or a follow-up.
2. **Why-lines outside recency.** Q23's 16 claims carry why-lines. The prompt allows them only for recency
   and window questions; the code does not flag extra ones.
3. **Q24 derivation periods differ by firm**: MS 2020, RJF 2025-09-30, EDJ 2026-06-26. Each one is
   within-firm and same-basis, as rule 2 requires. The comparison claim names the period difference.
4. **Q24 must-not chunk** `SCHW-TR-2026Q3#10` is a `fact` under comparison aspect a4, not under the asked
   quantity.
5. **Q11 label drift** after the re-map (extract-v1.1): EDJ a1 / a3 / a4 are not found (facts in #246).
6. **Q22 `date_mismatch` x11**: still to be checked against the passages; the scorer reads them.

## 3. Blind scoring

verdicts-blind.json sha256 60260442705b938f6eda2b28e40a7052cc44ba29a5bf23933a861e76a12cc6cf (fresh scorer agent, `ev247\verdicts-blind.json`; committed before any comparison).

**5/8 PASS** (Q1, Q3, Q19, Q22, Q26; borderline: Q19, Q22, Q24, Q26). The scorer was a fresh agent that read
only `D:\ALLPROJECTS\EDJ\cache\ev247\blind-in\`: `answers-dump.txt`, `questions.yaml` and `verdict-rule.txt`.
The rule is #217 / #243's, with one line for Q24's superseded expected behavior (`answer`, ADR-021 rule 8;
passes_if unchanged). The scorer prompt is `ev247\scorer-prompt.txt` and the input hashes are in
`ev247\blind-in-hashes.txt`. The verdict file is `docs/results/0247-raw/verdicts-blind.json`.

| Q | Tier | #217 (Claude, v4.1) | #243 DeepSeek like-for-like (v4.1) | #246 map only (matrix behavior) | **#247 blind** | Class | Borderline | Reason (scorer) |
|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | PASS | PASS | not run | **PASS** | | | Channels management credits, in its words, every claim dated; 2024-25 vs 2026 emphasis kept apart |
| Q3 | 1 | PASS | FAIL | not run | **PASS** | | | Framing, priorities, named competitors and concessions (long/short throttling, SAN referral network, Ameritrade RIA attrition), dated and sourced |
| Q11 | 1 | FAIL | FAIL | answer | **FAIL** | s, r | | Only RJF and BAC (a 2023 supplement) get quoted definitions; MS, EDJ and SCHW have counts or adjacent text only; differences not named beyond the generic caveat |
| Q19 | 3 | FAIL | FAIL | answer_with_boundary | **PASS** | | yes | Cohort evidence and competitor moves (mainly Schwab), dated and sourced, then the hand-off; competitor moves thin, claims duplicated, many meaningless gap rows |
| Q22 | 1 | PASS | PASS | not run | **PASS** | | yes | Value, period, source and definition per firm; Merrill not reporting with GWIM flows labelled; stray 2020 MS values; EDJ 4Q25 / 3Q26 holes not flagged |
| Q23 | 1 | FAIL | FAIL | answer | **FAIL** | s, r | | Series far from complete (MS 2019-2020, RJF one point plus an undated figure, Merrill 2022-2023); EDJ 4Q25 in the corpus but missing; EDJ U.S.-only vs firm-total break not flagged |
| Q24 | 3 | FAIL | FAIL | answer (after the 0-call re-check) | **FAIL** | s, r | yes | Validity half answered well; ratios computed on inconsistent inputs (RJF AUA includes RCS assets whose advisors are excluded; MS 2020 headcount over a base including self-directed and workplace assets); current MS advisor counts missed |
| Q26 | 1 | FAIL | FAIL | answer | **PASS** | | yes | Newest first, all inside the 90-day window, resolvable sources; why-lines mostly restate the fact, items duplicated, trade press only |

**Against #243 like-for-like on the same eight questions:** 2/8 -> 5/8.
- Q3, Q19 and Q26 move from FAIL to PASS. These are the shape failures #243 named: Q3's missing
  concession leg, Q19's missing competitor leg, Q26's missing why-lines.
- No PASS turns into a FAIL: Q1 and Q22 keep PASS (Q22 is now borderline).
- Q11, Q23 and Q24 stay FAIL. The reason has moved from behavior and shape to coverage and basis:
  - Q11: definitions missing for three firms;
  - Q23: an incomplete series;
  - Q24: ratios on inconsistent inputs.

**Against #217 (Claude):** Q19 and Q26 are new PASSes; Q11, Q23 and Q24 are unchanged FAILs.

**Against #246** (map only, no answer scored): the behaviors decided by code match the effective
expected behavior for all eight, as they did in #246 for the five targets. The scorer's failures are in
what the matrix holds (coverage, scope), not in the behavior.

**Issue acceptance (real items):**
- Q11 / Q23: **not met**. The behavior is `answer` and the gaps are named, but each firm's definition or
  series is incomplete.
- Q24: **not met**. The comparison claim and the EDJ ratio are present, but the RJF and MS ratios use
  inconsistent inputs.
- Q26: **met** (blind PASS, borderline).
- Q19: **met** (blind PASS, borderline; competitor moves are mostly Schwab, and MS / MER / RJF have named
  gaps).
- Q1, Q3, Q22 kept PASS: **met**. Q3 moved from FAIL in the DeepSeek baseline to PASS.

## 4. Findings for follow-up (nothing re-run)

1. **Newest-first re-sort over a whole answer** (Q19). One recency aspect (a12) re-sorted all 57 items
   and mixed the aspect grouping. Candidate rule: re-sort only the recency aspect's items.
2. **Why-lines outside recency** (Q23: 16 of 16 claims). The code does not flag extra ones. Why-line
   quality is the next item.
3. **Why-line quality and duplicate claims** (scorer: Q26, Q19). Why-lines mostly restate the fact,
   items repeat, and Q19's 58 gap rows (one per empty cell of 13 aspects x 5 firms) add noise.
   Candidates:
   - a code check that a why-line adds something beyond the claim;
   - deduplication of claims citing the same chunk with the same text;
   - aggregating empty-cell gaps per firm or per aspect.
4. **Series coverage in retrieval and the map** (scorer: Q23, Q11; also Q22 holes):
   - EDJ 4Q25 is in the corpus (the 10-K year-end figure) but was not retrieved or extracted as a 4Q25
     point;
   - current MS advisor counts were not found (only the 2020 supplement);
   - RJF has one point.
   Candidates: per-period retrieval for series aspects, and a re-search triggered by period gaps (the
   B4 gap names exactly what is missing).
5. **Scope inside a within-firm derivation** (scorer: Q24). `derive()` accepts inputs whose scope
   strings match but whose definitions differ: RJF client assets include RCS while the advisor count
   excludes RCS; MS total client assets include self-directed and workplace assets.
   - `derive()` should refuse such a ratio, or mark it not comparable, when the numerator's and the
     denominator's definitions cover different populations within one firm.
   - `config/metric_definitions.yaml` needs a scope or population field for each input metric (client
     assets, advisor headcount) so code can test it. Today client assets is not registered at all.
6. **Basis break inside a series** (scorer: Q23). EDJ switches between U.S.-only and firm-total counts
   without a flag. Candidate: a code flag when one firm's series items carry different scopes or
   definitions.
7. **Derivation periods differ across firms** (Q24: MS 2020, RJF 2025-09-30, EDJ 2026-06-26). Each is
   within-firm and same-basis, and the comparison claim names the difference. Together with finding 4,
   the MS ratio should use a current headcount when the corpus holds one.
8. **Must-not chunk on a comparison aspect** (Q24 `SCHW-TR-2026Q3#10` as a fact under a4). Comparison
   aspects decide nothing, but the chunk is cited. Candidate: the eval's must-not check should also
   report comparison-aspect facts (it already does), and a decision on whether such a citation should
   fail the refusal check.
9. **Label drift after the extract-v1.1 re-map** (Q11 EDJ a1 / a3 / a4 not found; facts in #246).
10. **Q22 `date_mismatch` x11**: the scorer passed Q22 after reading the passages. The flags look like
   checker false positives on quarter wording; they should be checked against the date-check rules.