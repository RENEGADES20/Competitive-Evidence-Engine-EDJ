# W13 reduce effort off for v8 synthesis answers, comparison fallback, Gate 3 (#295), fts

Plan: `plans/0295-reduce-effort-off.md` (approved, issue #295 comments 7120735225 and 7120764517). Evidence:
`docs/results/w13-reduce-effort-off/` (committed copies) and `D:\ALLPROJECTS\EDJ\cache\ev295\` (working copies).

**Result: Gate 3 fails. Blind 14/30, text-only 14/30, against #272's 24/30 adjudicated (22/30 blind).** The second
read cannot rescue it: only 9 FAILs are borderline, so the most it could reach is 23/30, and 23/30 counts as a fail. Some
regressions are form-caused: the 5-sentence v8 form leaves out parts the question asks for (Q5, Q7, Q22). Under the
plan's decision rule this means **stop and report to the TL before merge.** Whether v5.2 returns as the default is the
TL's call. Nothing is merged, and no PR is open.

**Speed:** reduce wall time p50 10.4 s and p90 18.8 s across Q1-Q30 (v5.2 in #272: 124 s / 155 s). The 24 new calls cost
$0.609, all at peak.

## How this was run
- **Code under test:** `tl/295-reduce-effort-off` a7d9ed1, from the clean worktree `wt-295gate`. Run script
  `run-gate3.ps1` (with an `.sh` twin), every setting pinned:
  - snapshot `corpus-2026-11-19`, as-of 2026-11-17, `deepseek-v4-pro` on `/beta`;
  - plan off, map low, reduce `low` with brief `off`, stream on, idle 120 s;
  - `REDUCE_PROMPT=v8`, MAP_PREFIX off, fts, `PYTHONHASHSEED=0`.
- **Checks before the paid call (0 calls):**
  - pytest: 1235 passed (18 new tests).
  - Mock fts Q1-Q30 against main d1bbed5, rule plans and #272 plans: 30/30 identical on both, and
    `comparison_refiled` empty on every question (`mock-compare.txt`).
  - Q24 replay: the #292 g8-off record was reused, `comparison_missing` [], re-filed a1 -> a4 (`r-q24.head-log.txt`).
  - verify-cee on mock: ask-answer, ask-layout, ask-progress PASS (`wt-295gate\.verify-runs\20261123-211541-a7d9ed1`).
- **Count `g3-count` (0 calls):** 521 records reused (30 plans, 454 maps, 31 re-maps, 6 reduces) and 24 new reduce keys,
  exactly the plan (`g3-count-summary.txt`).
- **Run `g3-run`:** Tuesday 2026-11-24, 03:32-03:43 UTC, **peak** (the TL said not to wait).
  - `--max-calls 24`: 24 new `deepseek-v4-pro` reduce calls, none cut, invalid or failed. $0.609 as billed (about
    CNY 4.4).
  - Reused reduces: Q5, Q8, Q22, Q24 (v8-off records from #292) and Q26, Q27 (v5.2-low records from #272). Q26 and Q27
    are the same answers as #272 by construction.
  - Raw records of the new calls: `w13-reduce-effort-off/g3-run/raw/`; the report is `g3-run/report.json`.
- **Comparison fallback in the run:** it fired once, on Q24 (a1 -> a4). No other question needed it:
  `comparison_missing` is empty on all 30.

## Scores
Method: the #272 method.
- Four fresh Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30), each reading its part in full.
- Inputs: only `ev295\blind-in\` (hashes in `blind-in-hashes.txt`). The #250 `verdict-rule.txt` is unchanged (same
  sha256 as #272); `scorer-note.txt` covers the plan-review change.
- The dump is `dump295.py`. It lists the answer and the Computability box as answer content and adds the evidence list
  in a block marked "context only, not answer content". For each PASS the scorers recorded `text_only`.
- Merged verdicts: `verdicts-blind-full.json`, sha256 `07a7235cabd948d4a79ffac7442d0c3071b0a55664f33d03e45b2a7e206682c4`.
- Full table with every reason: `score-table.md`.

| Count | #295 (v8, reduce off) | #272 test B (v5.2, reduce low) |
|---|---|---|
| Blind | **14/30** | 22/30 |
| Text-only (decides) | **14/30** (every PASS is text_only) | - |
| Adjudicated | at most 23/30 (14 + 9 borderline FAILs); no second read needed for the decision | 24/30 |

- **Lost against #272 adjudicated:** Q5, Q6, Q7, Q12, Q15, Q16, Q17, Q19, Q21, Q22, Q26 (11).
- **Gained:** Q28.
- **Q26 changed only through the scorer:** the record is identical to #272's (zero delta by construction), and the
  verdict went PASS -> FAIL, borderline. This is scorer variance on a borderline question, not a change in the answer.

### Regressions: effort-caused or form-caused (plan decision rule; from the reduce records and claims)
| Q | Verdict reason (short) | Cause |
|---|---|---|
| Q5 | Initiatives with management's purpose (Carta, Zero Hash, lending tools) only in the evidence list | **form**: the #292 v8-low answer has the same 4-sentence selection |
| Q7 | No same-dimension grid; retention / recruiting only in the evidence list | **form** |
| Q22 | "By quarter" asked; the answer gives one latest quarter per firm, the series only in the evidence list | **form**: #292 v8-low also gave latest figures only (`w13-reduce-synthesis.md`) |
| Q6 | AUA mix by model absent from the answer; two CEO remarks from different years paraphrased | not separable (form and effort) |
| Q17 | Deployed tools vs aspiration not separated | not separable |
| Q21 | Firm half weak; adjacent A2 garbled | not separable |
| Q12 | Schwab cost per account uses 2020 although the passage has 2025; "not found" for figures present | effort |
| Q15 | $485.7B stated as net interest revenue (it is sweep cash) | effort |
| Q16 | States the answer's own forecast; positions not attributed | effort |
| Q19 | Citations that do not support "preferences" | effort |
| Q26 | Same record as #272 | neither (scorer variance) |

At least three are form-caused, so the rule's "all effort-caused -> brief back to `low`" branch does not apply. The
failures come from the v8 form itself, which is also main's current default at `low` (v8-low has never been scored on
30 questions). That puts the default reduce prompt in question, not only the effort.

### Side check: does the evidence block move verdicts? (0 calls)
Two fresh Sonnet scorers read the #272 v5.2 answers for Q3, Q4, Q8 and Q22 (borderline in #272), one dump with the
evidence block and one without. Q7 and Q15, named in the plan, were too large for one scorer.

| Q | With block | Without block | #272 adjudicated |
|---|---|---|---|
| Q3 | PASS (text_only true) | FAIL | FAIL |
| Q4 | PASS | PASS | PASS |
| Q8 | FAIL | FAIL | PASS |
| Q22 | PASS | PASS | PASS |

- The only difference, Q3, was marked `text_only: true`, so it is scorer variance on a borderline question, not the
  block.
- Q8 differs from #272's adjudicated PASS in both reads.
- On v5.2 answers the block did not move verdicts. Borderline questions flip between fresh scorers.
- Files: `side/side-verdicts-*.json`, `side/side-hashes.txt`.

## Speed and cost (`reduce-table.md`, made by `reduce_table.py`)
| Set | Wall p50 s | Wall p90 s | Tokens/s p50 | Output tokens | USD as run | USD at peak |
|---|---|---|---|---|---|---|
| v8-off, Q1-Q30 (Q26, Q27 are reused v5.2-low records) | 10.4 | 18.8 | 73 | 68,004 | 0.746 | 0.870 |
| v5.2, #272 test B, Q1-Q30 | 124.2 | 155.3 | 181 | 602,621 | 1.555 (off-peak) | 3.111 |
| v8-off, Q5 Q8 Q22 Q24 | 6.8 | 12.1 | 79 | 2,538 | 0.013 | 0.013 |
| v8-low (#292), Q5 Q8 Q22 Q24 | 142.2 | 318.0 | 78 | 50,355 | 0.267 | 0.267 |

- The v8-off 24 new calls: wall 4.9-24.5 s, output 331-2,067 tokens, no reasoning.
- The v5.2 rows ran off-peak (167-189 tokens/s); #292 and this run ran at peak (45-94 tokens/s). Wall-time comparisons
  across them are confounded by service speed. Output tokens are the like-for-like measure: off writes 3-10 % of v5.2's
  output.

## Findings
- **The fallback works and stays rare.** It fired only on Q24, the case it was written for. In the mock it fired
  nowhere, and in this run on no other question. Overfit note: `P.COMPARISON_VERDICT` was written from the two #292
  Q24 sentences. This run shows it does not fire wrongly on these 30, not that it is general.
- **Effort off makes the reduce fast** (p50 10 s, against 124 s for v5.2 at low) and cheap.
- **The quality loss is mostly the brief form.** The scorers fault answers where a required part is only in the
  evidence list (Q5, Q7, Q22), plus some wrong or unsupported assertions (Q12, Q15, Q16, Q19).
  - #275's reduce at off with the list prompt v5.3 scored 20/30 blind.
  - v8 at off scores 14/30 blind.
- **Answers above 5 sentences:** Q2, Q10, Q17 and Q18 have 6 claims, Q3 8 and Q19 9 (code-added boundary or
  computation items, or the model went past the cap). Not investigated here.
