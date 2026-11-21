# What to build next

Rewritten on 2026-11-21 from the W11 scored run (#250; [docs/results/w11-report.md](results/w11-report.md)).
The run used DeepSeek `deepseek-v4-pro` (thinking on) and the map-reduce pipeline, with fts retrieval on
`corpus-2026-11-19`.
- **Scores:** the blind full read scores it 19/30 (tier 1: 11/18). The adjudicated score follows the PR review's second read.
- **Same plans, hybrid-norerank on `exp/hybrid`:** 21/30 blind. Adjudicated: pending (#250 PR 2).
- **Earlier runs:** W10 with Claude, single answer call: 24/30 fts, 25/30 hybrid. The DeepSeek baseline #243, single
  answer call: 15/30.

The eleven fts failures are Q5, Q10, Q11, Q16, Q18, Q20, Q21, Q23, Q25, Q28 and Q29. Items are ranked by how many
questions each would move and by how sure we are of the cause. Each item names:
- the question IDs behind it;
- a rough size (S = under a day, M = 1-3 days, L = a week or more);
- the check that would show it worked.

Nothing here is started.

1. **Output cut at the 64,000-token cap: the output limit and the reasoning budget** (Q20, Q21 fts; Q27 hybrid;
   class i). Three outputs were cut at `max_tokens`, with the reasoning taking most of the budget:
   - Q20 `map.all`;
   - Q21 reduce;
   - Q27 `map.MER` (hybrid).

   It cost two fts questions and one hybrid question, all of which would otherwise have been read. Options:
   - a lower reasoning effort for map calls;
   - splitting a firm's map call when its cells or passages are many (Q21 has 12 calls; Q20 is one theme call
     over many passages);
   - a planned re-call at a larger cap (none exists today).

   Size M. Check: the three saved inputs re-run once each in a planned real check, with valid outputs; a 0-call count
   names any other call near the cap.
2. **Behavior choice in the reduce** (Q10, Q18, Q29; class b).
   - Q10 returned `gap_with_adjacent` where the bank expects `answer`: no firm is named or ranked as most explicit,
     although the dated statements are there. Hybrid's Q10 answered and passed.
   - Q18 refused (`comparison_missing`), although the corpus holds Form ADV fee schedules, McKinsey fee-pressure
     research and firm fee disclosures.
   - Q29 answered where the bank expects `gap_with_adjacent`: it never says payout grids are not public, and it uses
     trade press as if it were the answer.

   Size M. Check: the three reduces re-run from their saved matrices (planned real calls); the behavior matches the
   bank's, and the other 27 are unchanged on a 0-call replay.
3. **Required part or shape missing** (Q5, Q16, Q25, Q28; class s).
   - Q5 keeps two claims from 51 passages.
   - Q16 is organised by sub-question and firm, not by position, with off-topic claims.
   - Q25 leans on trade press for Schwab and MS pay and does not mark Schwab's structure as not public.
   - Q28 never states plainly how net headcount change differs from attrition.

   Q25 and Q28 are borderline in the full read and differ from the first read, so the second read decides them. Size
   M (reduce prompt rules for "by position" and "not public", with tests on the rendered message). Check: the four
   answers re-scored blind after a planned re-run.
4. **Definitions and series limited by the corpus** (Q11, Q23; r, s, c). These are unchanged since W10 and #247:
   - Q11 has no written MS, EDJ or Schwab definition in tier 1-3;
   - Q23's series stops at 2020 for MS and 2023 for Merrill, RJF has four points, and Schwab has none (#247 part 4,
     the old NEXT item 11).

   Size L (corpus: new filings or supplements). Check: SQL over the new documents, then Q11 and Q23 re-run.
5. **A reduce caveat the code writes from saved map outputs is not deterministic** (Q12; both modes).
   - The 0-call replay of each run, from the same saved map records, built Q12's series-span caveat differently:
     "2024 to 2026Q3" in the run, "2024Q4 to 2026Q3" in the replay.
   - So the reduce key changed and the saved answer was not reused.
   - The scored record is the run's own answer.

   Size S. Check: two 0-call replays give byte-identical matrices for all 30 questions; a test pins the caveat on
   reordered map results.
6. **A mode-aware competitor floor** (Q19; `exp/hybrid`). The ADR-018 floor compares `ts_rank` across firms in fts;
   in hybrid-norerank it compares per-firm RRF ranks and almost never fires. On the DeepSeek plans it cut Q19 a1.MER
   (4 of 5) and a1.RJF (1, emptied) in fts only. The TL decisions on #250 attribute the Q19 differences to the floor.
   Size M (`exp/hybrid`). Check: the floor table from #249 / #250 shows comparable cuts in both modes.
7. **Scoring method for large dumps.**
   - A 30-answer dump is about 1.2-1.4 MB. The first fts scorer cut passages to about 110 characters to fit it, and
     the full read moved Q12, Q25 and Q28.
   - Both runs were therefore read by four scorers, each over a question range.

   Size S (a dump with each cited passage once per question, and the split built in). Check: one scorer reads a whole
   range without truncating.

Done in W11 and dropped from this list:
- map-reduce with per-firm extraction, corrective re-search and a reduce call (#245-#248);
- the Q24 EDJ ratio and the Q26 newest-first window (both pass);
- the Q19 competitor leg (passes in both modes);
- the Q3, Q7, Q8, Q12, Q15, Q17 drops of #243 (pass again).

W10 failures now passing in W11 fts: Q19, Q24, Q26.
