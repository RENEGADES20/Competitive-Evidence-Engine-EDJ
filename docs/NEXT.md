# What to build next

Written at the end of the term (2026-11-18), from the Gate 4 run on `corpus-2026-11-17`
(21/30, [docs/results/gate4-report.md](results/gate4-report.md)). The items are ranked by how
many questions each would move and by how sure we are of the cause. Each item names the question
IDs behind it, a rough size (S = under a day, M = 1-3 days, L = a week or more) and the check that
would show it worked. Nothing here is started.

| # | Build | Questions | Size | Shows it worked |
|---|---|---|---|---|
| 1 | **Advisor headcount sources.** Add documents that give an advisor count for Morgan Stanley, Schwab and Merrill: the Bank of America and Morgan Stanley quarterly supplements' advisor lines (if published), firm fact sheets or investor-day pages. Each count is stored with its own definition (ground rule 4: no inferred headcount). | Q11, Q23, Q24 | M | Q11 lists five definitions with quotes; Q23 gives a series per firm with breaks flagged; mock coverage up |
| 2 | **Retrieval recall for named facts.** Passages the corpus holds still miss the pool: MS formulaic payout (Q25, Q7), RJF payout ranges on `RJF-PR-web-affiliation-options#1` (Q25), Schwab revenue composition `SCHW-10K-2025#27` (Q15), Fidelity next-gen study and UBS sample (Q20), `BAC-TR-2026Q2#21` (Q17), `EDJ-10K-2025#88` (Q19). Options: more synonyms, a second query pass per asked part of the question (ADR-012 allows up to 5 calls), or the hybrid search kept on `exp/hybrid` (ADR-011) once re-evaluated on this corpus. | Q7, Q15, Q17, Q19, Q20, Q25 | M-L | each named passage in the retrieved set (mock); no PASS -> FAIL; R-run of the six questions |
| 3 | **Every asked part answered or named as a gap.** Today a part with no evidence can disappear (Q3 "where they concede ground", Q12 "Edward Jones's cost structure", Q28 "net headcount is not attrition"). A code check after the answer, comparing the question's parts with claims and gaps, would flag it, or a per-part call (ADR-012). | Q3, Q12, Q28 | M | the three answers name the missing part; no new uncited claim |
| 4 | **Comparison grid from the question, not the evidence.** The grid should take its dimensions from the question (Q7: recruiting posture, payout, training, retention). Empty cells go to `gaps`, not uncited claims; code already flags them (`no_citation`). | Q7 (Q8, Q22 as checks) | S-M | Q7 has four dimensions x three firms, every non-empty cell cited, empty cells in gaps |
| 5 | **Behavior when most firms lack a figure.** Prompt v3 sends Q11 and Q23 to `gap_with_adjacent`. Decide with the project lead whether a partial table plus named gaps (`answer`) is the wanted behavior for benchmark questions; then adjust the rule and the bank's expectation together (the bank is append-only, so a new question, not an edit). | Q11, Q23 | S | decision recorded in an ADR; behavior matches it |
| 6 | **Primary sources inside short windows.** Q26's 90-day window holds only trade press for Raymond James. Ingest press releases and 8-Ks on a schedule (weekly snapshot) so recency questions cite the firm first. | Q26, Q27 | M | Q26 cites at least one RJF release or filing inside the window |
| 7 | **Fee-schedule documents.** Q18 is scored on Form ADV brochures only; add published fee schedules for the five. | Q18 | S | Q18 cites a fee schedule per firm |
| 8 | **Number check false positives.** The #52 checker flagged four correct figures in Gate 4 (table rows, abbreviations like 1MM). Normalise number formats before matching. | Q4, Q9, Q20, Q22 | S | 0 flags on these four, real mismatches still caught (tests) |
| 9 | **A second scorer.** Gate 3 and Gate 4 were scored by one agent; seven verdicts are borderline (Q15, Q17, Q19, Q22, Q25, Q26, Q28). A second, independent read of those seven would make the score sturdier. | 7 borderline | S | two verdicts per borderline question, differences discussed |

Out of scope for this list (term rules): alerts, live web browsing, recommendations, forecasts,
internal or client data, multi-user.
