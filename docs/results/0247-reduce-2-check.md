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

## 2. Real check (26 DeepSeek calls)
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
- **Raw records**: `docs/results/0247b-raw/` (50: the 26 new and the 24 reused).

### Per question (behavior by code, the answer, the code checks)

| Q | Behavior | Calls (map + re-map + reduce) | Claims / adjacent / gaps | Code checks |
|---|---|---|---|---|
| Q1 | answer | 0 + 0 + 1 | 18 / 3 / 2 | clean |
| Q3 | (none) | 0 + 0 + 1 failed | - | reduce call failed (connection error) |
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
1. **Q3 has no answer**: the reduce call failed with a connection error (a failed call, saved). Re-running it is
   an unplanned re-run (TL decision); the blind scorer sees "no answer".
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

## 3. Blind scoring (pending)
Prepared for a fresh scorer: `D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in\` (`answers-dump.txt` with the eight
answers, Q3 shown as no answer; `questions.yaml`; `verdict-rule.txt`, part 1's rule) and
`ev247b\scorer-prompt.txt`; hashes in `ev247b\blind-in-hashes.txt`. Baseline: part 1 blind (Q1, Q3, Q19,
Q22, Q26 PASS; Q11, Q23, Q24 FAIL).
