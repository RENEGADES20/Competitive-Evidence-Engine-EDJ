# #247 part 3 checks: definition contrast, related-metric wording, quarter holes, gap sources (0 API calls)

Plan: `plans/0247-reduce-3.md` (approved at 9313a22 with the TL conditions written in at 0db59f2). Code at
`22a6555` (02a57c2 + the TL fix in section 6). Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. **0 API calls** in this part: no plan, map or
reduce call; `.env` never read or copied; no key set. Evidence folder `D:\ALLPROJECTS\EDJ\cache\ev247c\`.
**Blind scoring: not done yet** (the TL starts a fresh scorer; inputs in section 4).

## 1. Zero-call checks
- **pytest**: 972 passed on main 2f568c4 before any change; 998 at 02a57c2 (26 new in
  `tests/test_reduce_part3.py`, one assertion updated in `tests/test_series_coverage.py`). One full run had
  `tests/test_ask_page_trace.py::test_trace_stays_collapsed_after_the_answer` fail (Streamlit timing, a file
  this PR does not touch); it passed on re-run. The registry verbatim test ran against `cee-db` (not
  skipped): every contrast `text` is a substring of its chunk, including the EDJ #35 quote with U+2019.
- **Mock 35** (`run-mock.ps1`; main 2f568c4 in `wt-247c-base` vs the branch, `mock-direct.txt`): every
  question's chunk lists, sub-questions, added chunks and status identical (33 PASS / 2 FAIL, refusal 8/8 on
  both); claims identical everywhere; gaps / caveats differ only in Q11, Q19, Q22, Q23 (the new code rules).
  `compare_mock.py` (`mock-compare.txt`) shows the same statuses and recall; its "pinned" column counts the
  part-2 pins on both sides (main already has them). Mock answer checks: 0 outside the matrix, 0 part gaps,
  0 why-lines missing, 0 comparison claims missing.
- **verify-cee** (`.verify-runs/20261120-111924-02a57c2`): VERIFY PASS. ask-answer, ask-progress, gap-path,
  invalid-chunk, coverage, filters, feedback PASS; open-citation and download-document UNREACHABLE (no raw
  files in `data/raw/`, as in part 2).

## 2. Replays (0 calls) and the guard
Both runs with `replay.ps1` (twin `replay.sh`): the run cache seeded only from the committed
`docs/results/0247b-raw/*.json` (56 records, not the verdicts or the `.failed-1` record), the eight scored
reduce keys pinned (`diag/replay_part3.py`), `--max-calls 0`, `DEEPSEEK_API_KEY` empty, no `.env`, clean tree.

| Run | Commit | Guard (`diag/guard.py`, `head-log.txt`) |
|---|---|---|
| `replay-base` | main 2f568c4 (`wt-247c-base`, detached) | OK: real_calls 0, reused 50, model cached 8/8, 50 raw records identical to the committed blobs |
| `replay-02a57c2` | branch 02a57c2 (first replay, kept) | OK: real_calls 0, reused 50, model cached 8/8, 50 raw records identical to the committed blobs |
| `replay` | branch 22a6555 (after the section 6 fix) | OK: real_calls 0, reused 50, model cached 8/8, 50 raw records identical to the committed blobs |

The raw copies come from a Windows checkout (CRLF); the guard compares them with the git blobs after CRLF -> LF.
`docs/results/0247b-raw/` is unchanged (`git status` clean there before and after both runs).

**Baseline vs the scored dumps** (known part-2 differences only): Q3 = `blind-in`; Q19, Q26 = `blind-in-r2`;
Q1, Q11, Q22, Q23, Q24 = `blind-in-r3` (Q24 up to the trailing separator). Q1 differs from `blind-in` by
the a4.MS gap wording (R6b, part 2), as the reviewer noted.

## 3. Branch replay vs baseline replay (all eight)

| Q | Answer | What changed (code rules only; claims identical in all eight) |
|---|---|---|
| Q1 | identical | - |
| Q3 | identical | - |
| Q11 | changed | five `DEFINITION_CONTRAST` caveats (written definition, independents with the EDJ #35 quote, trainees, business lines, count date; every firm placed, one block); Schwab "publishes no count of this metric; reports a related figure instead"; "Merrill (Bank of America Corporation)"; EDJ "not stated" without an independents item; a4.MER source = parent's list; the a2.EDJ (same-date split) and a2.MER (undated item) break caveats gone |
| Q19 | **changed (not in the plan's table)** | the six folded "Competitors (Morgan Stanley, Merrill, Raymond James Financial)" gap rows: their joined source list now has Merrill's part, "Not yet in the corpus (parent Bank of America Corporation): Bank of America Form 8-K ...; Proxy statement" (before: no Merrill part). Cause: item 5's parent fallback in `suggested_sources("MER")`, which `COMPETITORS_GAP` joins per folded firm. Correct for Merrill (reported inside Bank of America), but a PASS answer changed, so Q19 joins the re-score |
| Q22 | changed | Schwab and Merrill (Bank of America Corporation) NNA "defines a related metric instead"; new gap EDJ 2024Q4, 2025Q4 ("inside its series 2024Q2-2026Q2; other firms report these quarters"); no MS gap; MS span "2024Q3 to 2026Q3 (9 points; earlier points 2019Q4 to 2020Q4, 3 points, are a separate segment)"; a1.MER / a2.MER source = parent's list |
| Q23 | changed | Schwab "reports a related figure instead"; Merrill names Bank of America; EDJ "not stated" without independents; RJF break caveat gone; a1.MER source = parent's list; spans unchanged |
| Q24 | changed | the by-firm caveat as Q23; a1.MER source = parent's list |
| Q26 | identical | - |

Dedupe removals: Q11 2, Q19 4, Q26 1, others 0, the same claims as the baseline (item 4 removed nothing more,
kept nothing more on these answers).

**Claim text vs the removed breaks** (review nb 6): no claim or adjacent item in Q11, Q19, Q22, Q23, Q24 says
"basis break", "not one series", "different bases", "publishes no definition" or "none: all advisors". The
model's Q11 items still label each figure's basis ("on the U.S. basis", "on the Canada basis", "on the Merrill
and Private Bank basis"): descriptions, not references to a break.

**Merrill ">15K" scope** (review nb 3): with the a2.MER break gone, the Merrill and Private Bank scope still
shows in Q11 C16 ("Bank of America's 2025 Investor Day deck ... '>15K Wealth Advisors' on the Merrill and
Private Bank basis (period not stated)"), in the "GWIM is not Merrill" config caveat, and in the contrast's
business-lines line for Bank of America ('all wealth management businesses in GWIM and Consumer Banking').
In Q23 it is the a1.MER gap's closest figure ("... combines Merrill and the Private Bank ...").

## 4. Blind inputs (prepared, not scored)
`D:\ALLPROJECTS\EDJ\cache\ev247c\blind-in\`: `answers-dump.txt` with only the answers that differ from the
baseline (Q11, Q19, Q22, Q23, Q24, from the branch replay), `questions.yaml` (from `evals/questions.yaml`),
`verdict-rule.txt` (r3's rule, question list Q11, Q19, Q22, Q23, Q24; Q24 against `answer` per
`behavior_supersede.yaml`). Scorer prompt `ev247c\scorer-prompt.txt` (writes `ev247c\verdicts-blind.json`).
Hashes (`ev247c\blind-in-hashes.txt`):
- answers-dump.txt df4a73dc6e15d06c0501fd8d393fe76964bc31f8bcf45dde1104598c35050e62 (rebuilt at 22a6555)
- questions.yaml 0f9400be52aca221bbbde8c404ab04335a0b4537593c767434ffd3ee59e89a5b
- verdict-rule.txt 1607043002b28bd66c5293a8b8c8376727a0a996bae7edb8efcdd3cd228df9b7
- scorer-prompt.txt 11a52683f0aa215b2bcc48b8c406cb97d7285525a6f41af3ba5fd879c904752c

Unchanged answers keep their part-2 verdicts: Q1, Q3, Q26 PASS. Acceptance: no PASS -> FAIL (Q19, Q22, Q24);
Q11 aims at PASS; Q23 stays a corpus gap unless the re-score says otherwise.

## 5. pytest at 22a6555
1000 passed (two more in `tests/test_reduce_part3.py`, section 6); `gh pr checks 263` green.

## 6. TL fix before scoring: the per-firm definitions caveat cited the wrong chunk
The `DEFINITIONS_BY_FIRM` caveat printed the registry's free-text `includes` / `excludes` / `not_stated` lists,
e.g. EDJ "includes U.S. and Canada financial advisors (split in EDJ-10K-2025#148)", but "Canada" is not in #148
(it is in #145). Fix (`matrix._scope_bits`): what a count includes or excludes is printed only from the entry's
`contrast` cells, each a verbatim registry text with the chunk that says it (EDJ: 'two operating and
reportable segments based upon geographic location, the U.S. and Canada' (EDJ-10K-2025#145)), or the fixed
phrase "not stated: <dimension labels>". The free-text lists stay in the registry (the map's words read
`includes`), so pins, `see_also` and map inputs are unchanged. Tests: outside the quotes the caveat has only
fixed words and firm names; every quote in it is verbatim in the chunk it cites (database, not skipped).
Re-replay (0 calls, guard OK) and re-diff against the baseline: Q1, Q3, Q26 identical; Q19 and Q22 unchanged
from 02a57c2; Q11, Q23, Q24 differ from 02a57c2 only in that caveat; no "#148" in any caveat. Blind inputs
rebuilt (hashes in section 4).

## 7. Notes (not changed in this part)

verdicts-blind.json sha256 c050ae7cb32a641fde588e9f5943c36ce44cefb8355b378ca05159f3a9d76c69 (part 3 re-check, five changed answers, fresh scorer agent, 0 API calls; committed alone before any comparison).

## 8. Blind re-score (part 3) and the final verdicts
**3/5 PASS** on the five changed answers (Q19, Q22, Q24 PASS; Q11, Q23 FAIL). Fresh scorer agent, inputs only
`ev247c\blind-in\` (hashes in section 4, the 22a6555 answers); file `docs/results/0247c/verdicts-blind.json`
(hash above, committed alone in 676eb3c).

| Q | Part 1 | Part 2 final | **Part 3** | Class | Borderline | Reason (scorer, short) |
|---|---|---|---|---|---|---|
| Q1 | PASS | PASS | PASS (identical, kept) | | | |
| Q3 | PASS | PASS | PASS (identical, kept) | | | |
| Q11 | FAIL | FAIL | **FAIL** | r | yes | differences now named; MS rests on a 2020 label with no definition, Merrill on a 2023 BAC supplement; "the RJF trainees claim overreads its passage" |
| Q19 | PASS (b) | PASS (b) | **PASS** | | yes | competitor moves almost only Schwab |
| Q22 | PASS (b) | PASS (b) | **PASS** | | no | EDJ Q4 holes flagged as gaps, not filled (no longer borderline) |
| Q23 | FAIL | FAIL | **FAIL** | r | no | MS 2019-20, Merrill 2022-23, RJF annual only; "MS/BAC/RJF quarterly supplements for 2025-2026 holding advisor counts are in the corpus" |
| Q24 | FAIL | PASS | **PASS** | | no | |
| Q26 | PASS (b) | PASS (b) | PASS (identical, kept) | | | |

No PASS -> FAIL: the acceptance is met. **Final for the eight: 6/8** (Q1, Q3, Q19, Q22, Q24, Q26 PASS; Q11,
Q23 FAIL), the same set as part 2; Q22 is no longer borderline, Q11 moves from s to r (the contrast fixed the
"differences not named" part).

## 9. Checking two scorer claims (0 calls)
**(a) RJF trainees** (Q11 contrast cell). `RJF-10K-2025#228` in full: "The number of financial advisors as of
September 30, 2025 increased compared to the prior year, as new recruits and trainees that were moved into
production roles exceeded departures and planned retirements. ... Advisors in our RCS division are not
included in our financial advisor metric ...". The trainees sentence explains a change in the count; it does
not say who the count includes. The cell `counted` overstated it. **Fixed in this PR** (one config line):
RJF `trainees: {value: not_stated}`. Effect: the contrast's Trainees caveat is skipped (every firm not
stated), and the per-firm definitions caveat reads "not stated: trainees" for RJF, in Q11, Q23 and Q24.

**(b) "Quarterly supplements for 2025-2026 holding advisor counts"** (Q23, Q11). SQL on `cee`
(`ev247c\diag\supp_advisors.txt`, `ev247c\diag\other_advisor_counts.txt`):
- The supplements with a period end from 2024-12-31: BAC-SUPP-2025Q4, 2026Q1-Q3; MS-SUPP-2025Q4, 2026Q1-Q3;
  RJF-SUPP-2025Q3, 2025Q4, 2026Q1, 2026Q2. **None has an advisor count.** BAC: only firmwide "Headcount"
  (213,207 etc., all employees) and "Financial advisory services" fees; the "Total wealth advisors" line ends
  with BAC-SUPP-2023Q4. MS: only "Advisor-led channel" asset lines and the footnote (f). RJF: only "Financial
  advisor compensation" in $ and loans to advisors. **Corpus gap** for all three (the scorer's claim does not
  hold for the supplements).
- Other documents in 2024Q4-2026Q3 with a count: BAC Investor Day ">15K Wealth Advisors" (Merrill and Private
  Bank, as of 3Q25; in both answers as adjacent); RJF FY2025 10-K (8,943; in the answers); RJF Investor Day deck
  `RJF-DECK-2025-investor-day#43` "Mar. 31, 2025** ... FINANCIAL ADVISORS ... 8,731" (tier 3, published
  2025-06-05): **retrieved for Q11 but not for Q23**, so Q23's RJF 2025Q1 point is a **retrieval miss (r)**, the
  only one found; trade press (tier 4, indicative): MS "15,000 or so" / "close to 15,000", RJF "about 8,900".
- So Q23's remaining failure is corpus (MS after 4Q2020, BAC after 4Q2023, RJF quarterly, EDJ 3Q26) plus one
  RJF point (2025Q1, investor-day deck) that retrieval missed; Q11's MS / Merrill bases are corpus (no MS
  definition or count after 2020 in any filing; BAC's last written footnote is 2023).

## 10. Merge of main (#248, e275175 / a1341d3) and the replays again (0 calls)
`origin/main` a1341d3 merged into the branch (7300621, no conflict). `eval_run.py` now needs `--naive-tz` for
saved records without a UTC offset; `diag/replay_part3.py` passes `--naive-tz America/Chicago` when the script
offers it. No key needed.
- Baseline on main a1341d3 (`wt-247c-base`, `replay-base`; the 2f568c4 baseline kept as `replay-base-2f568c4`):
  guard OK (real_calls 0, reused 50, 8/8 cached, 50 raw records identical to the committed blobs).
  **Identical to the 2f568c4 baseline for all eight** (#248 changes no answer text).
- Branch 7300621 (`replay`; the scored 22a6555 replay kept as `replay-22a6555`): guard OK, same numbers.
  - Q1, Q3, Q26 identical to the baseline; Q19, Q22 identical to the scored `blind-in` answers.
  - **Q11, Q23, Q24 differ from the scored answers**, only by the section 9a fix: the per-firm definitions caveat
    reads "not stated: trainees" for RJF instead of the #228 trainees quote, and Q11 loses the contrast's
    Trainees caveat (every firm not stated).
- pytest after the merge: 1033 passed.
- Second blind inputs prepared for these three (not scored): `ev247c\blind-in-r2\` (answers-dump.txt with Q11,
  Q23, Q24 from `replay`; questions.yaml; verdict-rule.txt for the three) and `ev247c\scorer-prompt-r2.txt`
  (writes `ev247c\verdicts-blind-r2.json`). Hashes (`ev247c\blind-in-r2-hashes.txt`):
  - answers-dump.txt ae69afb968c53240057fd7749b7c30c11383703e5e957f1d5cfd5b37ffdab156
  - questions.yaml 0f9400be52aca221bbbde8c404ab04335a0b4537593c767434ffd3ee59e89a5b
  - verdict-rule.txt 4957b1257650535f1c71adf813cdbacac4d2246947ec42a0ecd177ca0fdd21e6
  - scorer-prompt-r2.txt c2b1b3b19fca25b3396a83c1a7de4303f17dca2e080724a8d8631af37dc60a3a
