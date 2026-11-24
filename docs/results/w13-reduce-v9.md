# W13 reduce prompt v9: effort low, answer length follows the question, Gate 3 (#297), fts

**Status: plan stage, no run yet.** Plan: `plans/0297-reduce-v9.md`. Evidence will go to `docs/results/w13-reduce-v9/`
(committed copies) and `D:\ALLPROJECTS\EDJ\cache\ev297\` (working copies). Result, scores and speed: filled in after
the Gate 3 run.

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

## Coverage rule (code, v9 only)
| Cell | Uncited by any sentence | Why |
|---|---|---|
| holds a fact / accepted derivation; aspect fact or series, not proxy; role named, all or research | `part_gap` | the question asked for it (aspect from the question, firm named or theme / research row) |
| role competitor (home-firm "competitors kept" widening, Q19) | no gap, `evidence_list` | the question did not name that firm |
| comparison aspect | no part gap | `comparison_missing` checks the verdict sentence |
| proxy aspect, adjacent-only cell | no part gap | goes in adjacent (adjacent path) |
| no fact (empty, different quantity) / code gap | code gap as today | unchanged |

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

## Gate 3 run (planned)
- Cache `ev297\cache` = a copy of `ev295\cache` (which holds #272 test B plans, maps, re-maps and the Q26 / Q27
  v5.2-low reduces). Count first: 517 reused, 28 new reduce keys; else stop. `--max-calls` = the count.
- Cost basis (`w13-reduce-effort-off/reduce-table.md`): v8-low Q5 Q8 Q22 Q24 $0.267 at peak (mean $0.067); v5.2-low
  30 questions $3.111 at peak ($0.104 each). 28 calls: about $1.9-2.9 at peak (CNY 14-21).
- Decision rule and scoring: plan.

## Result
Not run yet.
