# W13 reduce prompt v9: effort low, answer length follows the question, Gate 3 (#297), fts

Plan: `plans/0297-reduce-v9.md` (approved, issue #297 comments 7123145488 and 7123192555). Evidence:
`docs/results/w13-reduce-v9/` (committed copies) and `D:\ALLPROJECTS\EDJ\cache\ev297\` (working copies).

**Result: Gate 3 fails. Blind 19/30, text-only 19/30, against #272's 24/30 adjudicated.** Only 3 FAILs are
borderline (Q3, Q8, Q28), so a second read can reach at most 22/30. Under the plan's decision rule **the default goes
back to `v5.2`** in this PR (`REDUCE_PROMPT_DEFAULT`); v9 (and v8) stay behind `REDUCE_PROMPT`.
- v9 beats v8-off (#295, 14/30 blind) by 5.
- It recovers Q5, Q6, Q12, Q15, Q19, Q21 and Q22.
- It loses Q7, Q8, Q16, Q17 and Q25 against #272.
- Reduce wall time p50 185 s, p90 254 s at peak; 28 calls cost $2.028, about CNY 14.7.

## Why v9
- #292 made v8 the default (at most 5 short cited sentences), checked on 4 questions.
- #295 (v8 at effort off) scored 14/30 against #272's 24/30 (`w13-reduce-effort-off.md`). Effort-caused errors: Q12,
  Q15, Q16, Q19. Form-caused: Q5, Q7, Q22 (the required items sat only in the evidence list).
- TL decision 2026-11-23: "用low然后长度跟着问题" (effort `low`, length follows the question).

## Prompt v9 rules (synthesis form only; list form keeps v5.2 byte for byte)
Kept from v8: evidence only (cite only listed chunk ids, no outside knowledge, no own arithmetic, nothing normative);
date from the source line; firm's own terms; no ids in the text; "figure not found" / "quote not verbatim" items
handled as today; adjacent-only cells in adjacent with differs_because; code gaps and caveats are code's; boundary and
gap_with_adjacent behaviors as v8; derived figures with formula and both inputs; the Computability box is code's.

Shape (replaces v8's 5-sentence cap):
1. Claim 1 answers the question directly (headline fact, figure or verdict) and MUST cite the items it rests on.
2. Then exactly what the question asks for, each sentence ONE claim that cites every chunk it rests on (aim 35 words
   or fewer; no run of items inside one sentence):
   - a single fact or figure -> 1-3 sentences in total;
   - "for each firm", "each of the five", "by quarter", "list", "what has each disclosed" -> one cited sentence per
     asked item (per firm, per quarter series, per initiative); a short run of such sentences is fine;
   - a comparison -> one sentence per firm in its own terms, plus the comparison verdict (part_id the comparison
     aspect id) saying whether it can be made on this evidence and why; rank only when marked same_basis, at the
     shared periods;
   - "what do we know", "how", "what is the strategy" -> the main points, one per asked aspect, each cited.
3. Evidence the question did not ask for is not restated; the evidence list under the answer shows it.
4. Every cell the coverage rule calls asked is covered by a sentence (by its cell id, or an aspect-id sentence citing
   its items). Where a firm or aspect has no evidence, code adds the gap; do not fill it.
Restored from v7 (v8 dropped them): positions about the future that others hold are attributed and dated, two that
disagree are reported as disagreeing, no forecast of your own (Q16); trade press is stated attributed ("trade press
reports ..."); the advisor-pay standard wording (payout ranges with the page date, or the payout gap) (Q25, Q29).
New, from #295's effort-caused errors: when items give several periods for the same figure, state the newest unless
the question asks for a series (Q12); a figure keeps the label its item gives it (what it measures) (Q15); when the
question separates kinds of evidence, say which kind each statement is (filing, management on a call, survey with its
sample and date, research, trade press) and keep a deployed, named tool apart from a stated intention (Q17, Q18, Q20).
From the Q22 / Q23 passes_if (plan review): each firm's own definition of the metric goes alongside its figure or
series; a firm that does not report the asked metric on that basis is said not to report it, never shown as zero and
never replaced by a near-neighbour metric (that one goes in adjacent); a definition change mid-series is stated as a
break, never smoothed.

## Coverage rule (code, v9 only)
| Cell | Uncited by any sentence | Why |
|---|---|---|
| holds a fact / accepted derivation; aspect fact or series, not proxy; role named, all or research | `part_gap` | the question asked for it (aspect from the question, firm named or theme / research row) |
| role competitor, firm in the aspect's `asked_firms` (Q19 a7) | `part_gap` | the planner asked for that competitor |
| role competitor, firm not in `asked_firms` (home-firm "competitors kept" widening, Q19 a1-a4) | no gap, `evidence_list` | the question did not ask for that firm there |
| comparison aspect | no part gap | `comparison_missing` checks the verdict sentence |
| proxy aspect, adjacent-only cell | no part gap | goes in adjacent (adjacent path) |
| no fact (empty, different quantity) / code gap | code gap as today | unchanged |

The rule checks that a cell's chunks are cited, not what the sentence says (a sentence citing a series may state
one quarter and pass); completeness of a series rests on the prompt and the scorers (plan, Risks).

## Q19 roles (plan review finding 3; 0 calls, from `ev295\g3-run\report.json`, the #272 plan and maps)
Q19's passes_if asks for "competitor moves aimed at [the cohort]". Matrix aspects and holding cells by role:
| Aspect | Kind | `asked_firms` | Holding cells |
|---|---|---|---|
| a1 product / service / channel preferences | fact | (none) | a1.EDJ named, a1.SCHW competitor, a1.research |
| a2 communication channels | fact | (none) | a2.EDJ named, a2.SCHW competitor |
| a3 advice / service model preferences | fact | (none) | a3.EDJ named, a3.SCHW competitor, a3.research |
| a4 growth in younger clients | series | (none) | a4.SCHW competitor |
| a5 EDJ offerings vs preferences | fact | EDJ | a5.EDJ named |
| a6 EDJ strategy for younger clients | fact | EDJ | a6.EDJ named, a6.SCHW competitor (not asked) |
| a7 competitor offerings and strategies | fact | MS, SCHW, MER, RJF | a7.SCHW competitor |
| a8 EDJ vs competitors | comparison | (none) | a8.EDJ named, a8.SCHW competitor |

- a7.SCHW carries the passes_if part "competitor moves" and has role `competitor`. Under a rule that exempts every
  competitor cell it would sit only in the evidence list, so the rule asks for competitor cells whose firm is in the
  aspect's `asked_firms` (a7.SCHW is asked).
- a1.SCHW-a4.SCHW come from the home-firm widening (no `asked_firms`) and a6.SCHW is outside a6's `asked_firms` (EDJ), so they are not asked. The research rows
  a1 / a3 (cohort preferences) are asked.
- Step 2 checks this again on the count report (same plan and maps).

## passes_if mapping (Q1-Q30): what the v9 shape must put in the answer text
| Q | Shape | Must land in the text |
|---|---|---|
| Q1 | strategy | each channel management credits, with its emphasis, dated |
| Q2 | strategy | pitch parts (affiliation choice, payout, autonomy, platform) + disclosed recruiting results |
| Q3 | strategy | framing, priorities, acknowledged pressure / conceded ground |
| Q4 | strategy | Merrill-only pipeline, headcount trajectory, sourcing shift |
| Q5 | list | each platform / initiative with management's purpose; spend only where disclosed |
| Q6 | list + change | each affiliation option; disclosed mix movement, quoted |
| Q7 | grid | same dimensions for all three firms, each cell cited; empty cells as code gaps |
| Q8 | comparison | each firm's own language; custody vs affiliation kept distinct |
| Q9 | comparison | each firm's segmentation and thresholds; "not disclosed" as a gap |
| Q10 | verdict | the dated statements and the basis for "most explicit" |
| Q11 | per firm | five quoted definitions, differences named |
| Q12 | boundary | Schwab channels, economics, cost claims, EDJ cost structure; hand-off by code |
| Q13 | how | channel end to end, figures with their periods |
| Q14 | how | each option's economics for advisor and firm, from RJF |
| Q15 | comparison | revenue composition per model, mechanism, where it breaks |
| Q16 | positions | organised by position, attributed, dated, no own forecast |
| Q17 | verdict | deployed named tools vs aspiration, then who claims most |
| Q18 | positions | disclosed changes, regulation, research vs commentary, labelled |
| Q19 | boundary | dated preferences evidence + competitor moves; hand-off by code |
| Q20 | list | survey findings with source, sample, date; disagreements |
| Q21 | two halves | estimates with source and vintage; each firm's stated actions |
| Q22 | per firm series | value, period, source per quarter, with each definition; non-reporters marked |
| Q23 | per firm series | complete series with definitions; breaks flagged |
| Q24 | gap + verdict | figure only where computable (box); where the comparison is invalid and why |
| Q25 | per firm | what each discloses; the rest marked undisclosed |
| Q26, Q27 | list form | v5.2, unchanged (same records as #272) |
| Q28-Q30 | gap with adjacent | the gap wording, the asked firm's figure, the labelled adjacent quantity |

## Why v8 answers went past 5 sentences (#296 reviewer point; #295 `g3-run/report.json`)
- Q2 (a6), Q17 (a6), Q18 (a6): 5 sentences + the comparison verdict written as a 6th. v8's prompt counts it "within
  the 5", the model at effort off did not.
- Q10: 6 model sentences, one per aspect (a1-a6), no comparison aspect: the model went past the cap.
- Q3: 8 model sentences (a1, three under a2 incl. a "cannot compare" sentence, two each under a3 and a6); Q19: 8 model sentences plus the code-added
  boundary hand-off (not a model sentence).
- None of it is a code bug: no code path adds claims besides the boundary hand-off (and the box, outside the claims).
  v9 drops the cap, so the count is no longer a rule; the scorers judge length against passes_if.

## Gate 3 run (as planned)
- Cache `ev297\cache` = a copy of `ev295\cache` (which holds #272 test B plans, maps, re-maps and the Q26 / Q27
  v5.2-low reduces). Count first: 517 reused, 28 new reduce keys; else stop. `--max-calls` = the count.
- Cost basis (`w13-reduce-effort-off/reduce-table.md`): v8-low Q5 Q8 Q22 Q24 $0.267 at peak (mean $0.067); v5.2-low
  30 questions $3.111 at peak ($0.104 each). 28 calls: about $1.9-2.9 at peak (CNY 14-21).
- Scoring: the 28 new answers are scored; Q26 and Q27 carry #272's adjudicated verdicts (PASS, PASS), since their
  records are identical. Borderline, the second read and the decision rule: plan (step 6, "Decision rule"). #272's
  24/30 was not scored under the text-only rule, so v9 meets a stricter bar.
- The result is filled only from saved raw outputs and the merged verdicts sha256; cost is the actual cost per call
  from the report, not this estimate (v9 has no reasoning cap).

## How this was run
- **Code under test:** gate f8edf82 (v9 prompt, `validate.asked_cell` coverage rule, mock v9), from the clean
  worktree `wt-297gate`. Run script `run-gate3.ps1` (with an `.sh` twin), every setting pinned:
  - snapshot `corpus-2026-11-19`, as-of 2026-11-17, `deepseek-v4-pro` on `/beta`;
  - plan off, map low, reduce low, stream on, idle 120 s;
  - `REDUCE_PROMPT=v9`, MAP_PREFIX off, fts, `PYTHONHASHSEED=0`.
- **Checks before the paid call (0 calls):**
  - pytest: 1223 passed at the gate (6 new tests).
  - Mock fts Q1-Q30 (`cmp_mock.py` of #292, `docs/results/w13-reduce-synthesis/cmp_mock.py`), rule plans and #272
    plans (`mock-compare.txt`):
    - v8 at the gate = main 372303f, 30/30 identical on both;
    - v9 vs v8: Q26 and Q27 identical, 0 new flag kinds, 0 higher part_gap / comparison_missing / outside_matrix /
      number_not_found / no_citation.
  - verify-cee on mock, `REDUCE_PROMPT=v9`: ask-answer, ask-layout, ask-progress PASS
    (`.verify-runs/20261123-235950-f42762e`). Q5, Q8 and Q24 log v9 with the direct sentence first; Q26 logs v5.2.
  - Q19 roles (`q19_roles.py` on the count report): a7.SCHW asked; no competitor-aspect cell missed.
- **Count `g3-count` (0 calls):** 517 reused (30 plans, 454 maps, 31 re-maps, Q26 and Q27 reduces) and 28 new reduce
  keys, exactly the plan (`g3-count-summary.txt`).
- **Run `g3-run`:** Tuesday 2026-11-24, 06:06-07:32 UTC, **peak** (the TL said not to wait for off-peak).
  - `--max-calls 28`: 28 new `deepseek-v4-pro` reduce calls; none cut, stalled, invalid or failed.
  - $2.028 as billed (all peak), about CNY 14.7.
  - Raw records of the new calls: `g3-run/raw/`; the report is `g3-run/report.json`.

## Scores
Method: #272 plus the #295 text-only rule (plan step 6).
- **Scorers:** four fresh Sonnet scorers by range: Q1-Q10, Q11-Q16, Q17-Q21, and Q22-Q25 + Q28-Q30.
- **Inputs:** only `ev297\blind-in\` (hashes in `blind-in-hashes.txt`). `verdict-rule.txt` is the #250 one (same
  sha256 as #272 and #295). `scorer-note.txt` adds the borderline definition and the part's question list.
- **Dump:** `dump295.py`, with the evidence list marked as context only.
- **Merged verdicts:** `verdicts-blind-full.json`, sha256
  `bf36dcf070497fe18fc8eb9a0b82667ede5353b8ccc3981d59b7050f9f29cdd1`. Q26 and Q27 are carried from #272 adjudicated
  (PASS, PASS), not re-scored.
- **Full table with every reason:** `score-table.md` (made by `merge297.py`).

| Count | #297 (v9, low) | #295 (v8, off) | #272 test B (v5.2, low) |
|---|---|---|---|
| Blind | **19/30** | 14/30 | 22/30 |
| Text-only (decides) | **19/30** (every scored PASS is text_only) | 14/30 | - |
| Adjudicated | at most 22/30 (19 + borderline Q3, Q8, Q28); the PR reviewer's second read | at most 23/30 | 24/30 |

| Change against #272 adjudicated | Q | Reason (short; `score-table.md`) |
|---|---|---|
| lost | Q7 | Dimensions not applied evenly: payout philosophy absent for MS and Merrill, training for MS; stale MS headcount; a trade-press line cited to an unrelated article |
| lost | Q8 | Declares the comparison valid on "overlapping terms"; custody and affiliation not kept distinct (borderline) |
| lost | Q16 | Organised by aspect, not by position; claim 1 states one synthesised view of the future |
| lost | Q17 | Deployed tools and aspirations not separated; "claims the most" judged on rhetoric |
| lost | Q25 | Leans on trade-press pay items that passes_if rules out; undisclosed items only partly marked |
| gained | - | none |
| same FAIL | Q3, Q11, Q20, Q23, Q28, Q29 | as #272 (Q28 borderline: the adjacent net headcount change is missing) |

Against #295 (v8-off), v9 regained Q5, Q6, Q12, Q15, Q19, Q21 and Q22. Q26 is also counted as regained, but only
because it is carried. v9 lost Q8, Q25 and Q28. The three form-caused #295 losses are back: Q5, Q22 and (for Q7)
the grid. Q7 still fails, on uneven dimensions.

## Speed and cost (`reduce-table.md`, made by `reduce_table297.py`)
| Set | Wall p50 s | Wall p90 s | Tokens/s p50 | Output tokens | Reasoning tokens | USD as run | USD at peak |
|---|---|---|---|---|---|---|---|
| v9-low, 28 new calls | 184.6 | 254.1 | 79 | 357,988 | 270,775 | 2.028 (peak) | 2.028 |
| v5.2-low (#272), the same 28 | 117.1 | 156.2 | 181 | 554,779 | 344,540 | 1.431 (off-peak) | 2.863 |
| v8-off (#295), its 24 new calls | 10.4 | 14.9 | 71 | 17,624 | 0 | 0.609 (peak) | 0.609 |

- **Output tokens:** v9 writes 35 % fewer output tokens and 21 % fewer reasoning tokens than v5.2. At peak prices it
  costs 29 % less ($2.028 against $2.863 at peak for the same 28).
- **Wall time:** v9 is slower because this run was at peak (79 tokens/s against 181 off-peak for #272). Wall time
  across the two runs is confounded by service speed.
- **Length:** v9 answers have 0-125 claims, median 32.5 (v5.2: 0-205, median 47.5; v8-off: 0-9, median 5).

## Findings
- **The coverage rule did its job.** The parts #295 left only in the evidence list are back in the text: Q5's
  initiatives with their purpose, Q22's quarterly series with definitions, Q19's competitor moves. part_gap is 0 on all
  28 answers: the model covered every asked cell.
- **"Length follows the question" became "cover every asked cell".**
  - Answers stay long: a median of 33 claims, and Q21 has 125.
  - The scorers call several of them padded or repetitive (Q3, Q5, Q18, Q19, Q25).
  - The rule makes one sentence per holding cell, much like v5.2's one claim per item.
- **What v9 still gets wrong is the asked shape, not coverage:**
  - Q16 is organised by aspect where the question wants positions;
  - Q17 does not separate deployed tools from aspirations;
  - Q8 has a weak comparison verdict;
  - Q25 relies on trade press.

  The prompt has rules for Q16 and Q17, and the model did not follow them at `low`.
- **No re-roll:** these are findings. v9 stays behind `REDUCE_PROMPT=v9` for later work.
