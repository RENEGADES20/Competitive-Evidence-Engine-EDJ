# #247 part 2 checks: populations, series coverage, basis breaks, less noise (prompt v5.1)

Plan: `plans/0247-reduce-2.md`. Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. Every real call was made
at `6a3825a` (code gate: `git status` clean, `src scripts config` identical to the mock-run sha `715adda`).
**Blind scoring: not done yet** (the TL starts a fresh blind scorer; inputs in section 3).

## 1. Zero-call checks
- **pytest**: 957 passed (new: `tests/test_populations.py`, `tests/test_series_coverage.py`,
  `tests/test_reduce_noise.py`).
- **Mock 35** (main c4ba303 vs 715adda, `ev247b\mock-compare2.txt`): every main sub-question chunk list is
  identical; the only additions are `pinned` (Q1 2, Q11 12, Q22 5, Q23 17; the mock rule plan has no series
  aspect, so no period pass); recall is not lower anywhere (Q11 @final 0.4 -> 1.0, Q22 0.75 -> 0.875); no new
  forbidden hit; statuses and refusal unchanged (33 PASS / 2 FAIL, refusal 8/8). Mock answers: 0 outside
  the matrix, 0 part gaps, 0 why-lines missing, 0 comparison claims missing, behavior = matrix behavior.
- **verify-cee** (`.verify-runs/20261120-064407-9f66be3`): VERIFY PASS. ask-answer, ask-progress, gap-path,
  invalid-chunk, coverage, filters, feedback PASS; open-citation and download-document UNREACHABLE (no raw
  files in `data/raw/`, the same precondition as part 1).
- **Replay of part 1** (`ev247b\diag\replay_part1.txt`; part 1's logged matrices and saved reduce outputs,
  pools rebuilt with the new retrieval passes, 0 calls):
  - Q24: EDJ accepted (edj_firm / edj_firm); MS refused (all channels vs advisor-led); RJF refused (AUA incl.
    RCS vs advisors excl. RCS). Three code computability claims, 0 outside the matrix.
  - Q26: 27 of 30 part-1 why-lines would be replaced as restating; 2 duplicates.
  - Q19: gap rows 58 -> 16; 12 duplicates; 3 items re-sorted (a12 only).
  - Q23: 25 why-lines removed (not recency); `EDJ-10K-2025#130` reached by the 2025Q4 period search.
- **0-call count** (`ev247b\real-count`): 8 plans reused; round 1 = 16 map calls (Q11 5, Q22 1, Q23 5, Q24 5);
  re-extraction bound 16; reduce 8; **cap 40** (ceiling 59). Largest map input: Q24 RJF ~72,337 tokens /
  221 passages (limit 936,000).

## 2. Real check (27 DeepSeek calls: 26 + 1 transport retry)
- **Model**: `deepseek-v4-pro`, `/beta` strict tools, thinking on; `MAP=on`, `MAP_CONCURRENCY=6`,
  `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1.1, prompt v5.1, request version
  `ds-strict-1-think-on-a64000-p64000`. Wrapper `D:\ALLPROJECTS\EDJ\cache\ev247b\run-real.ps1` (with `.sh`);
  `.env` copied in for the run and removed in `finally`.
- **Calls**: 26 made of the cap 40: 16 map, 2 re-extraction (Q11 MS, Q24 SCHW), 8 reduce. 24 records reused
  (8 plans; the Q1, Q3, Q19, Q26 maps; Q22 SCHW / EDJ / MER / RJF; Q19 / Q26 and Q11 MER re-extractions). No ProviderStop,
  no 400, no invalid output. **One failed call: Q3's reduce** (`APIConnectionError: Connection error.`
  after 106 s), saved as `failed_call`, not re-run: Q3 has no answer in this run.
- **Usage**: 755,867 input tokens (348,672 cache hits), 546,619 output tokens (487,293 reasoning); 5,482 s of
  call time; 06:53-07:50 local (12:53-13:50 UTC), 57 min elapsed.
- **Cost**: about **$1.36** (all calls finished off-peak, 12:53-13:50 UTC on a weekday; rates per 1M tokens,
  off-peak: cache hit $0.022, miss $0.66, output $1.98; source as part 1: `docs/results/w11-deepseek-baseline.md`
  "Cost"). Part 1 + part 2 for #247: 72 calls.
- **TL decision: 1 transport retry** (Q3). The failed reduce call returned no model output (a transport
  failure, not a wrong answer), so the TL allowed exactly one retry with the same inputs and settings
  (`run-real.ps1 -Phase run -Cap 1 -Questions Q3`, 07:55-07:57 local, code gate passed, `.env` copied in and
  removed in `finally`). It returned a valid answer (stop `tool_calls`, 11,092 output tokens, about $0.02).
  The failed record is kept as `Q3-reduce-ec259fc6b468c54a5288cdfa.failed-1.json`, the retry's record next
  to it under its cache key. **Total: 27 calls, about $1.38.**
  - The retry's output folder name was shadowed in the wrapper (PowerShell variables are not case-sensitive),
    so it wrote into `ev247b\real-run` and replaced that run's `report.json` and log. The eight-question report
    was rebuilt from the saved records with 0 calls (`--max-calls 0`, no key: `ev247b\real-run-final`, all 8
    answers reused); the seven other answers are identical to the first dump (diffed). The raw records of the
    26-call run were already in `docs/results/0247b-raw/`, and the run summary is in `ev247b\head-log.txt`.
- **Raw records**: `docs/results/0247b-raw/` (51: the 26 new, the Q3 retry, the 24 reused; Q3's failed
  record under the `.failed-1` name).

### Per question (behavior by code, the answer, the code checks)

| Q | Behavior | Calls (map + re-map + reduce) | Claims / adjacent / gaps | Code checks |
|---|---|---|---|---|
| Q1 | answer | 0 + 0 + 1 | 18 / 3 / 2 | clean |
| Q3 | answer | 0 + 0 + 1 failed + 1 retry | 23 / 0 / 0 | first reduce call failed (connection error); TL decision: 1 transport retry, valid |
| Q11 | answer | 5 + 1 (+1 reused) + 1 | 23 / 8 / 8 | 9 pinned passages; 5 duplicates removed; basis breaks a2.EDJ, a2.MER |
| Q19 | answer_with_boundary | 0 + 0 + 1 | 43 / 2 / 24 | gap rows (matrix) 58 -> 16; 2 duplicates; 3 re-sorted (a12 only); comparison missing a13 |
| Q22 | answer | 1 + 0 + 1 | 42 / 9 / 2 | 1 pinned (MS); 11 `date_mismatch` (as part 1) |
| Q23 | answer | 5 + 0 + 1 | 13 / 12 / 5 | 102 period + 8 pinned passages; 22 why-lines removed; 9 duplicates; basis break a1.RJF |
| Q24 | answer | 5 + 1 + 1 | 4 / 65 / 6 | EDJ computed; MS refused (populations differ); RJF refused (see finding 2); the model wrote all three computation claims (0 by code) |
| Q26 | answer | 0 + 0 + 1 | 31 / 0 / 2 | why-lines from the stated context, 0 restated; 1 duplicate |

For every question with an answer: 0 outside the matrix, 0 part gaps, 0 why-lines missing.

**Target notes**:
- **Q23**: EDJ now has 2Q25, 3Q25, 4Q25 (20,425, from `EDJ-10K-2025#130` via the 2025Q4 period search), 1Q26,
  2Q26 and the 2024 comparatives; EDJ's only period gap is 2026Q3 (no 3Q26 10-Q in the corpus). MS: the 2020
  counts as claims, the asked periods named as a gap. RJF: the 10-K's FY2023-FY2025 totals and the employee /
  independent split. SCHW and Merrill: Form ADV figures as adjacent (pinned).
- **Q24**: the three per-firm computation claims cite the inputs and the population sources (EDJ
  `EDJ-10Q-2026Q2#59`, `EDJ-10K-2025#130`; MS `MS-10K-2025#125`, `MS-SUPP-2020Q4#3`; RJF `RJF-10K-2025#228`).
- **Q11**: MS, SCHW, EDJ, Merrill and RJF definition cells now see their registered passages (EDJ a1-a4
  facts; SCHW cells are different quantities from the Form ADV figures).

### Findings (reported, not re-run)
1. **Q3's first reduce call failed** with a connection error (no model output). TL decision: 1 transport retry,
   which returned a valid answer; both records are saved.
2. **Q24 RJF refused for the wrong reason**: the 8,943 item's quote names "financial advisors" after the
   figure ("We had 8,943 employee and independent contractor financial advisors"), and the rule reads only the
   phrases before the figure, so the item got no population key: the ratio was refused as "population not
   stated" instead of "populations differ", and the claim says the headcount's population is not stated
   although `RJF-10K-2025#228` (cited) states it. The outcome (not computed) is right; the reason is not.
   Fix candidate: fall back to the whole quote when no phrase stands before the figure.
3. **Q23 RJF basis-break caveat is noise**: the employee / independent-contractor split items carry no
   population key, so "whole firm (rjf_advisors_excl_rcs)" and "whole firm" read as two bases. Fix candidate:
   group by scope only when a key is missing.
4. **Q19 comparison gap twice and a13 missing**: the normative comparison aspect a13 has no claim of its own
   (the hand-off carries no part id), so `COMPARISON_MISSING` fired, and the re-check after the dedupe added it
   a second time. Fix candidate: the re-check adds only gaps not already present; the hand-off counts for a
   normative comparison aspect.
5. Q11 / Q22 / Q24 refusal flags in the retrieval scoring are the same must-not retrievals as part 1 (main
   search, not the additions); no must-not chunk is cited as a fact in any matrix.

## 3. Blind scoring

**5/8 PASS** (Q1, Q3, Q19, Q22, Q24; borderline: Q19, Q22, Q24, Q26). Fresh scorer agent, inputs only
`ev247b\blind-in\` (after the Q3 transport retry); file `docs/results/0247b-raw/verdicts-blind.json`.

| Q | Part 1 blind | **Part 2 blind** | Class | Borderline | Reason (scorer, short) |
|---|---|---|---|---|---|
| Q1 | PASS | **PASS** | | | Channels management credits, dated; $10T flagged as a stock target |
| Q3 | PASS | **PASS** | | | Framing, priorities, competitors and concessions, dated |
| Q11 | FAIL | **FAIL** | s, r | | Not five quoted definitions (MS none and 2020 only, EDJ a label, Merrill a 2023 footnote, Schwab a gap); differences not named |
| Q19 | PASS (b) | **PASS** | | yes | Cohort evidence and competitor moves (Schwab only), hand-off; gap lines for a7-a12 contradict EDJ claims found |
| Q22 | PASS (b) | **PASS** | | yes | Value, period, source and definition per firm; stray 2019-20 MS cells, a few missing quarters, EDJ 10-K vs 10-Q definition wording not flagged |
| Q23 | FAIL | **FAIL** | r, s | | MS 2020 only, RJF fiscal year-ends only, Merrill 2023 only; EDJ near complete |
| Q24 | FAIL | **PASS** | | yes | Ratio only for EDJ, others declined, validity half answered; RJF reason muddled, EDJ hedged "definition unverified" |
| Q26 | PASS (b) | **FAIL** | s | yes | About a third of items say "the source does not say"; trade press only; one article repeated |

Against part 1 on the same eight: 5/8 -> 5/8. **Q24 FAIL -> PASS; Q26 PASS -> FAIL** (a regression: the
acceptance does not allow it, so the PR does not merge as is; plan "Revision after scoring").
- Q26: the 11 "the source does not say" lines were written by the model (v5.1 tells it to when the item's own
  context gives no reason); code replaced none (`why_line_restated` 0). The 0-call replay's 27 replacements were
  part 1's restating why-lines run through the new check, a different output.

## 3a. Blind inputs (as prepared)
Prepared for a fresh scorer: `D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in\` (`answers-dump.txt` with the eight
answers, Q3 from the retry; `questions.yaml`; `verdict-rule.txt`, part 1's rule) and
`ev247b\scorer-prompt.txt`; hashes in `ev247b\blind-in-hashes.txt`. Baseline: part 1 blind (Q1, Q3, Q19,
Q22, Q26 PASS; Q11, Q23, Q24 FAIL).

verdicts-blind.json sha256 fbde54a73ecdcab33dba81149abf077806716c5628265f842cc646cf8be77df1 (fresh scorer agent, `ev247b\verdicts-blind.json`; committed alone before any comparison).

## 4. Revision after scoring and re-check (R1-R6, prompt v5.2)

Plan section "Revision after scoring" (R1-R5, TL comment after 645d79c) and R6 (TL comment after it). Code
`20663ec`; real calls at `a0ceb61` (code gate: `src scripts config` identical to `20663ec`).

### 4.1 Zero-call checks
- pytest: 966 passed (revision tests in `tests/test_populations.py`, `tests/test_series_coverage.py`,
  `tests/test_reduce_noise.py`).
- Mock 35 vs main c4ba303 (`ev247b\mock-compare-r2.txt`): retrieval identical apart from the pinned additions;
  0 outside the matrix, 0 part gaps, 0 why-lines missing, 0 comparison claims missing.
- verify-cee (`.verify-runs/20261120-081908-20663ec`): VERIFY PASS (open-citation, download-document
  UNREACHABLE: no raw files).
- 0-call count (`ev247b\count-r2`, no key): the 6 plans and all 38 map / re-extraction records reused; only the
  6 reduce calls would be made. **Cap 6.**

### 4.2 Real re-check (6 DeepSeek calls)
Reduce only, Q11, Q19, Q22, Q23, Q24, Q26, one run each, `ev247b\real-r2` (wrapper `-OutDir`), 08:24-09:03
local (14:24-15:03 UTC, off-peak): 6 calls, all valid (`tool_calls`), 0 reused reduce, 38 records reused;
7,040 cache-hit + 69,115 cache-miss input tokens, 238,816 output tokens; about **$0.52**. Raw records in
`docs/results/0247b-raw/` (the six `*-reduce-*` files dated 2026-11-20T08:2x-08:5x).
**#247 part 2 in all: 33 calls (26 + 1 transport retry + 6), about $1.90.**

| Q | Claims / adjacent / gaps | Code checks |
|---|---|---|
| Q11 | 16 / 8 / 8 | `DEFINITIONS_BY_FIRM` caveat (each firm named); Schwab gaps name the closest figure (Form ADV); 12 "duplicates" removed (10 of them distinct data points: the dedupe bug, section 7); basis breaks a2.EDJ, a2.MER |
| Q19 | 44 / 2 / 16 | no comparison gap (the hand-off covers a13); 6 model gaps contradicting found claims dropped; 4 duplicates |
| Q22 | 42 / 9 / 2 | clean |
| Q23 | 11 / 12 / 5 | `SERIES_SPAN` per firm (MS 2019-12-31 to 2020-12-31, EDJ 2024-09-27 to 2026-06-26, RJF FY2023-FY2025); 34 why-lines removed; 11 "duplicates" removed, all distinct data points (EDJ 3Q25 / 4Q25 / 1Q26, MS 15,950 / 15,468, RJF FY2023-24): the dedupe bug, section 7; 11 duplicates |
| Q24 | 4 / 65 / 4 | RJF now refused with "the two figures cover different populations" (R2); EDJ computed, not "unverified" |
| Q26 | 31 / 0 / 2 | 0 "the source does not say" (v5.1: 11); why-lines from the stated context; 1 duplicate |

Remaining observation (not changed before scoring): Q23 RJF still gets a basis-break caveat. With the R2
whole-quote fallback, the undated "approximately 9,000" PCG item now carries `rjf_advisors_excl_rcs`, so it is
a keyed group of its own; R3 only drops undated items without a population. A one-line follow-up (undated
items make no basis, keyed or not) if the TL wants it.

### 4.3 Blind inputs for the re-check (pending)
`D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in-r2\` (`answers-dump.txt` with the six answers, `questions.yaml`,
`verdict-rule.txt` for six questions) and `ev247b\scorer-prompt-r2.txt` (writes `ev247b\verdicts-blind-r2.json`);
hashes in `ev247b\blind-in-r2-hashes.txt`. Q1 and Q3 keep their part-2 answers and verdicts (PASS).

## 5. Q11 / Q23: corpus gaps vs answer problems (0 calls, SQL on `cee`)

| Item | Kind | Evidence | Where it goes |
|---|---|---|---|
| MS advisor count after 4Q2020 | corpus gap | 0 count lines in every MS 10-K / 10-Q / supplement / press release with a period end from 2024Q4 (`MS-SUPP-2025Q4`..`2026Q3` have no "Wealth Management representatives" line); later figures only tier-4 trade press ("close to 15,000") and Form ADV (13,000 advisory employees) | NEXT |
| RJF quarterly headcount | corpus gap | the only counts with a period end in 2024Q4-2026Q3: FY2025 10-K (8,943; 3,878 / 5,065, `RJF-10K-2025#24`, `#227`) and the 3Q25 call; trade press says RJF "no longer reports advisor headcount" | NEXT |
| Merrill / BAC count after 4Q2023 | corpus gap | BAC 10-K / 10-Q / supplements / press 2024-2026: award lists and ">15K Wealth Advisors" (investor day, 3Q25, approximate) only | NEXT |
| EDJ 3Q26 | corpus gap | `EDJ-10Q-2026Q3` not stored | NEXT |
| Written definitions (MS, EDJ; BAC after 2023; Schwab) | corpus gap | MS and EDJ publish none; BAC's latest is the 2023 supplement footnote; Schwab publishes no count (registered figure: Form ADV) | NEXT |
| Q11 differences not named | answer | fixed by R6a (`DEFINITIONS_BY_FIRM`) | this PR |
| Q11 Schwab shown as a bare gap | answer | fixed by R6b (gap names the closest figure) | this PR |
| Q23 where each series stops | answer | fixed by R6c (`SERIES_SPAN`) | this PR |
| Q23 EDJ 3Q25 / 4Q25 / 1Q26 and MS 15,950 missing from the scored answer | **answer (code bug)** | written by the model, removed by `dedupe_claims` (one quoted table row read as the same claim); restored in the 0-call replay (section 7) | this PR (fixed) |
| Q11 MS 15,950, EDJ 2Q26 splits, Merrill 2023 / 2022, RJF totals missing | **answer (code bug)** | the same dedupe bug; 10 claims restored in the replay | this PR (fixed) |

verdicts-blind-r2.json sha256 cba0e16cf45017c37218467be019897bbfb7468e24d0ced7aa8ec2a1a9e54e23 (re-check, fresh scorer agent; committed alone before any comparison).

## 6. Blind scoring of the re-check

**4/6 PASS** (Q19, Q22, Q24, Q26; borderline Q19, Q22, Q26). Fresh scorer agent, inputs only
`ev247b\blind-in-r2\`; file `docs/results/0247b-raw/verdicts-blind-r2.json` (hash above, committed alone in
d422467). With Q1 and Q3 (part-2 PASS, answers unchanged) **part 2 is 6/8**.

| Q | Part 1 | Part 2 (v5.1) | **Re-check (v5.2)** | Class | Borderline | Reason (scorer, short) |
|---|---|---|---|---|---|---|
| Q1 | PASS | PASS | (not re-run) | | | |
| Q3 | PASS | PASS (after the transport retry) | (not re-run) | | | |
| Q11 | FAIL | FAIL | **FAIL** | r, s | | Only EDJ, RJF, BAC (2023) definitions quoted; MS none and a 2020 count; Schwab none; differences not named side by side |
| Q19 | PASS (b) | PASS (b) | **PASS** | | yes | Cohort evidence, Schwab moves, EDJ disclosures, hand-off; competitor moves Schwab only; one claim oddly framed as a comparison; one BofA figure (94% collectables) slightly misread |
| Q22 | PASS (b) | PASS (b) | **PASS** | | yes | Quarterly values with period, source and definition; stray 2019-20 MS points; EDJ 2025Q4 missing; a caveat wrongly says Schwab publishes no definition |
| Q23 | FAIL | FAIL | **FAIL** | r, s | | MS 2020 only, RJF fiscal year-ends, Merrill 2023 only; EDJ near complete |
| Q24 | FAIL | PASS (b) | **PASS** | | | EDJ computed on a consistent basis; MS, RJF, Schwab, Merrill declined with reasons; validity answered |
| Q26 | PASS (b) | FAIL (b) | **PASS** | | yes | Newest first, in window, a why-line each; many why-lines restate another fact; redundant splits; Clark Capital repeats a May 2026 close |

Merge acceptance (TL): Q26 back to PASS; Q19, Q22, Q24 kept PASS; Q1 and Q3 unchanged answers: **met**.
Against part 1 on the eight: 5/8 -> 6/8 (Q24 FAIL -> PASS; no PASS lost). Q11 and Q23 stay open.

### Findings for follow-up (no code change in this PR, nothing re-run; checked with 0 calls)
1. **Q23 RJF basis break** (one line): an undated item makes no basis whether or not it carries a population
   (R2's whole-quote fallback tagged the undated "approximately 9,000" PCG item).
2. **Q22 "Schwab publishes no definition"**: the registry marks Schwab's net new assets entry `closest_metric`
   (its headline is *core* net new assets, `SCHW-10K-2025#119`, quoted), and R6a's wording for
   `closest_metric` says "publishes no definition of this metric". Wrong for Schwab NNA (it defines a related
   metric, core NNA). Fix: word `closest_metric` as "defines a related metric instead: '<quote>'".
3. **Q11 differences not side by side**: the R6a caveat lists each firm's definition, includes / excludes and
   not-stated items in one long line, but never says how they differ (e.g. MS counts representatives of
   advisor-led accounts; EDJ counts all U.S. and Canada advisors with no written definition; RJF excludes RCS;
   BAC includes Consumer Banking; Schwab publishes no count). Candidate: a comparison aspect forced by code
   on "define ... include or exclude" questions, or a code table of the registry's includes / excludes.
4. **Q19 misread figure** (BofA "94% collectables") and **Q26 why-lines restating another fact, near-duplicate
   items** (one article split into several claims): reduce-quality findings; the dedupe threshold (content
   containment 0.85) does not catch splits of one passage.
5. **MS 2025 10-K and 2026 supplements as "expected sources"** (scorer, Q11 / Q23): SQL over `MS-10K-2025`,
   `MS-SUPP-2025Q4` .. `MS-SUPP-2026Q3`: no advisor count line anywhere; the only text about representatives is
   the footnote "Advisor-led client assets represent client assets in accounts that have a Wealth Management
   representative assigned" (`MS-10K-2025#167`, `MS-SUPP-2025Q4#36`, `MS-SUPP-2026Q1#43`, `MS-SUPP-2026Q2#37`,
   `MS-SUPP-2026Q3#38`), which defines advisor-led assets, not a headcount. **Corpus gap confirmed** (no count,
   no headcount definition). Side note: the MS registry entry quotes the 2020 count line; its closest current
   wording is that footnote (pinned already); the registry could name it as `closest_metric` text.

## 7. PR #261 review round 1: the dedupe bug, fixes, 0-call replay of the eight scored answers

**Blocking 1** (`reduce.dedupe_claims`): two claims citing one chunk were "held in" each other when the figures
of the shorter appeared in the longer, and a quoted table row ("At year end 20,425 20,125 19,232") carries
every period's figure, so per-period claims about one row were removed as duplicates. Fix: figures and stated
periods (dates, quarter labels) are compared **outside quoted text**, and every period the shorter states must be
stated by the longer. Tests: the `EDJ-10K-2025#130` 20,425 / 20,125 case, the MS 15,950 case (the exact repeat
still goes), same figure for different quarters.

**Other fixes** (non-blocking): the registry's list items quoted (`independents (none: ...)` parsed as a
mapping, BAC / MS / Schwab items split at commas), with a test that every item is plain text; R5 compares
only fact cells and like-for-like documents (10-K / 10-Q one family): it now fires on Q22 EDJ net new assets
(10-K 2025 vs 10-Q 2Q26) and no longer on Merrill (a supplement footnote vs Form ADV wording in a
different-quantity cell); ADR-021 / spec wording of the R2 whole-quote fallback; this doc's damaged paths;
the plan's file list and the dropped `basis_break` chip.

**0-call replay** (`ev247b\replay-final`, no key, `--max-calls 0`; plans and maps reused, 50 records; each
question's reduce output is the scored record, so no model output changed; `ev247b\diag\replay_final.py`),
compared with the scored dumps (`blind-in\` for Q1 / Q3, `blind-in-r2\` for the six):

| Q | Answer text | Claims | Caveats / gaps |
|---|---|---|---|
| Q1 | changed | 18 -> 18 | one gap reworded (R6b: names the closest figure, MS's stated $10T client-asset goal) |
| Q3 | identical | 23 | - |
| Q11 | changed | 16 -> 26 (**10 restored**: MS 15,950 / 15,468; EDJ 2Q26 whole firm / U.S. / Canada; Merrill 2023 and 2022; RJF totals x3) | definitions caveat: plain text instead of a printed dict |
| Q19 | identical | 44 | - |
| Q22 | changed | 42 -> 42 | + EDJ net-new-assets definition-wording caveat (10-K vs 10-Q) |
| Q23 | changed | 11 -> 22 (**11 restored**: EDJ 3Q25 20,429, 4Q25 20,425, 1Q26 20,550; MS 15,950, 15,468; RJF FY2023 / FY2024 totals and employee / independent splits) | definitions caveat: plain text |
| Q24 | changed | 4 -> 4 | Merrill false-positive wording caveat gone; definitions caveat plain text |
| Q26 | identical | 31 | - |

The removals the review called true duplicates (Q19, Q22, Q24, Q26) are unchanged (identical or same claims).

**What is the bug and what is corpus** (Q11, Q23): the points above were in the model's answers and were removed
by the bug; they are restored. What stays missing is corpus (section 5): no MS count after 4Q2020, no RJF
quarterly count, no BAC / Merrill count after 4Q2023, no EDJ 3Q26 10-Q, no written MS / EDJ / Schwab
definition. Q11's "differences not named side by side" stays an answer finding (section 6, finding 3).

**Re-score (0 API calls, pending)**: the five questions whose answer text changed (Q1, Q11, Q22, Q23, Q24) go to a
fresh blind scorer: `D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in-r3\` (their replayed answers, `questions.yaml`,
`verdict-rule.txt`) and `ev247b\scorer-prompt-r3.txt` (writes `ev247b\verdicts-blind-r3.json`); hashes in
`ev247b\blind-in-r3-hashes.txt`. Q3, Q19 and Q26 are byte-identical and keep their verdicts (PASS).

verdicts-blind-r3.json sha256 ab7745129c55c08b64ecc8e2c07bebf3b7774bbb0e521afc375071d7865da86f (second re-check, five changed answers, fresh scorer agent, 0 API calls; committed alone before any comparison).
