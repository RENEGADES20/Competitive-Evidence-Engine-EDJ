# #247 part 3 checks: definition contrast, related-metric wording, quarter holes, gap sources (0 API calls)

Plan: `plans/0247-reduce-3.md` (approved at 9313a22 with the TL conditions written in at 0db59f2). Code at
`02a57c2`. Snapshot `corpus-2026-11-19`, `--as-of 2026-11-17`. **0 API calls** in this part: no plan, map or
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
| `replay` | branch 02a57c2 | OK: real_calls 0, reused 50, model cached 8/8, 50 raw records identical to the committed blobs |

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
- answers-dump.txt 5fcae2c79b942c65355e92499c402dff6ad2382bc39667b5b74e31cab90be9be
- questions.yaml 0f9400be52aca221bbbde8c404ab04335a0b4537593c767434ffd3ee59e89a5b
- verdict-rule.txt 1607043002b28bd66c5293a8b8c8376727a0a996bae7edb8efcdd3cd228df9b7

Unchanged answers keep their part-2 verdicts: Q1, Q3, Q26 PASS. Acceptance: no PASS -> FAIL (Q19, Q22, Q24);
Q11 aims at PASS; Q23 stays a corpus gap unless the re-score says otherwise.

## 5. Notes (not changed in this part)
- The `DEFINITIONS_BY_FIRM` caveat still prints EDJ "includes U.S. and Canada financial advisors (split in
  EDJ-10K-2025#148)" from the registry's `includes`; #148 holds the two columns, "Canada" is in #145 / #146
  (review round 1 table). The contrast cites #145; the `includes` wording is part-2 registry text.
