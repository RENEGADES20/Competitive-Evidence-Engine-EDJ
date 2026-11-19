# hybrid-norerank, 30 real answers on corpus-2026-11-17 (#212)

**Score: 21/30 at acting quality** (tier 1: 12/18), against Gate 4's 21/30 (tier 1: 12/18) with `fts` on the same snapshot, model and prompt. Scored by the TL agent (Claude) on 2026-11-19. One verdict changed each way: **Q17 PASS->FAIL** (retrieval) and **Q28 FAIL->PASS** (model). This is one run per question, so a changed verdict cannot be separated from run-to-run variation of the model; Gate 4's own 30 answers also came from two runs (11 calls in its final run, 19 answers reused from its R2 run).

## How this was run

- Snapshot `corpus-2026-11-17` (219 documents, 21,143 chunks, 21,143 embeddings), time windows as of 2026-11-17.
- Code: `exp/hybrid` 264d778 (#211) plus this branch's plan commits (no code change). Retrieval `hybrid-norerank` with `CEE_VECTORS=on`, constants FLOOR 0.4, MAX_PER_DOC 3, RERANK_N 50 x k/20, WINDOW_MAX_PER_DOC 8, THEME_MAX_PER_DOC 2 (plans/0211-hybrid-retest.md; nothing retuned).
- Model `claude-sonnet-5-5`, prompt v3, one model call per question, `scripts/eval_run.py --real`. Plan: [plans/0212-hybrid-real.md](../../../../plans/0212-hybrid-real.md); TL go-ahead and reopening on #212.
- **Calls: 30 in total, 30 raw outputs.** Attempt 1 (commit 60af2a4, `--max-calls 30`) answered Q1-Q17 (17 calls) and stopped when python crashed locally in `tokenizers.pyd` (0xc0000409) while embedding Q18's search query, before Q18's model call. Attempt 2 (commit 875edf3, TL decision #212 comment 7001200270, `--max-calls 13`) reused the 17 saved answers from the cache (same question, prompt, snapshot, model and chunk ids) and called Q18-Q30 (13 calls). The final run `corpus-2026-11-17-20261119-000405` covers all 30. No question was called twice.
- Mock checks before the first call (0 calls): the same 30 questions in hybrid-norerank gave the same chunk ids as #211's run on 30/30, PASS 28 / FAIL 2 (Q19, Q22, as #211), 0 forbidden, refusal 5/5; mock answers built for 30/30; a `--max-calls 0` dry run made 0 calls. The real run's chunk ids equal the mock run's on 30/30.
- Evidence: `real/run-report.json` (the run's report.json, answers and chunk ids), `real/raw/` (the 30 raw model outputs), `real/summary.json` (verdicts, comparison, call counts); local copies in `D:\ALLPROJECTS\EDJ\cache\ev212\` (`real-30`, `real-30-cache`, scoring pack, logs).
- Scoring: Gate 4's method. Each answer read against its `passes_if` line in `evals/questions.yaml`: would the project lead forward it with his name on it? One verdict, no half credit, Gate 4's failure classes (r retrieval missed a passage the corpus holds, s shape or required part missing, b behavior choice, c corpus gap). All 30 verdicts were written (`verdicts_hybrid.json`) before Gate 4's answers were opened; the scorer had seen Gate 4's verdict table and its one-line reasons for Q1-Q11 while planning. No verdict was changed after the comparison.
- Citations: 411 in total; every cited passage was in the retrieved set and exists in the database. The number check flagged 2 claims (Q16, Q19); each figure was found in its passage (checker false positives).

## Scores

Retrieval: passages in both sets / in Gate 4's set (fts) / in hybrid's set. Cause (changed verdicts only): retrieval = the deciding passage was in one set only; model = the deciding passages were in both sets.

| Q | Tier | Expected -> got (hybrid) | Gate 4 | hybrid | Change | Class | Retrieval both / fts / hybrid | Cause |
|---|---|---|---|---|---|---|---|---|
| Q1 | 1 | answer -> answer | PASS | **PASS** |  |  | 11 / 20 / 20 |  |
| Q2 | 1 | answer -> answer | PASS | **PASS** |  |  | 8 / 20 / 20 |  |
| Q3 | 1 | answer -> answer | FAIL | **FAIL** |  | s | 7 / 20 / 20 |  |
| Q4 (trap) | 1 | answer -> answer | PASS | **PASS** |  |  | 11 / 20 / 20 |  |
| Q5 | 1 | answer -> answer | PASS | **PASS** |  |  | 6 / 20 / 20 |  |
| Q6 | 1 | answer -> answer | PASS | **PASS** |  |  | 11 / 20 / 20 |  |
| Q7 | 2 | answer -> answer | FAIL | **FAIL** |  | s | 5 / 20 / 20 |  |
| Q8 | 2 | answer -> answer | PASS | **PASS** |  |  | 8 / 20 / 20 |  |
| Q9 | 3 | answer -> answer | PASS | **PASS** |  |  | 8 / 20 / 20 |  |
| Q10 | 3 | answer -> answer | PASS | **PASS** |  |  | 11 / 30 / 30 |  |
| Q11 | 1 | answer -> gap_with_adjacent | FAIL | **FAIL** |  | c, b | 10 / 30 / 30 |  |
| Q12 | 3 | answer_with_boundary -> answer_with_boundary | FAIL | **FAIL** |  | s | 7 / 20 / 20 |  |
| Q13 | 1 | answer -> answer | PASS | **PASS** |  |  | 9 / 20 / 20 |  |
| Q14 | 3 | answer -> answer | PASS | **PASS** |  |  | 10 / 20 / 20 |  |
| Q15 | 3 | answer -> answer | FAIL | **FAIL** |  | r, s | 9 / 30 / 30 |  |
| Q16 | 3 | answer -> answer | PASS | **PASS** |  |  | 5 / 20 / 20 |  |
| Q17 | 1 | answer -> answer | PASS | **FAIL** | PASS->FAIL | r | 7 / 20 / 20 | retrieval |
| Q18 | 3 | answer -> answer | PASS | **PASS** |  |  | 5 / 20 / 20 |  |
| Q19 | 3 | answer_with_boundary -> answer_with_boundary | PASS | **PASS** |  |  | 9 / 20 / 25 |  |
| Q20 | 1 | answer -> gap_with_adjacent | FAIL | **FAIL** |  | r, b | 6 / 20 / 20 |  |
| Q21 | 2 | answer -> answer | PASS | **PASS** |  |  | 17 / 30 / 30 |  |
| Q22 | 1 | answer -> answer | PASS | **PASS** |  |  | 13 / 30 / 30 |  |
| Q23 | 1 | answer -> gap_with_adjacent | FAIL | **FAIL** |  | c, b, r | 11 / 30 / 30 |  |
| Q24 | 3 | gap_with_adjacent -> gap_with_adjacent | PASS | **PASS** |  |  | 8 / 30 / 30 |  |
| Q25 | 1 | gap_with_adjacent -> answer | FAIL | **FAIL** |  | r, b | 7 / 30 / 30 |  |
| Q26 | 1 | answer -> answer | PASS | **PASS** |  |  | 12 / 15 / 20 |  |
| Q27 (trap) | 1 | answer -> answer | PASS | **PASS** |  |  | 13 / 20 / 20 |  |
| Q28 | 1 | gap_with_adjacent -> gap_with_adjacent | FAIL | **PASS** | FAIL->PASS |  | 9 / 20 / 20 | model |
| Q29 | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | **PASS** |  |  | 6 / 20 / 20 |  |
| Q30 (trap) | 1 | gap_with_adjacent -> gap_with_adjacent | PASS | **PASS** |  |  | 15 / 20 / 20 |  |

hybrid-norerank: 21/30. Gate 4 (fts): 21/30. Every question's retrieved set differs from Gate 4's (5 to 17 passages shared).

Borderline on the pass side: Q5, Q13, Q14, Q19, Q22, Q26. On the fail side: Q17. Another scorer could move the total by one or two either way, as Gate 4 said of its own score.

## Changes against Gate 4

### PASS -> FAIL

**Q17** (retrieval). Gate 4's PASS rested on named advisor tools (RJF tool list, MS LeadIQ, RJF AI-tools remark); all three passages were in Gate 4's retrieved set and none in hybrid's, so hybrid's answer had no named advisor tool for MS or RJF and ranked MS among those that 'say less'. Passages: `RJF-DECK-2025-investor-day#121`, `MS-TR-2025Q3#8`, `RJF-TR-2025Q4#6`.

### FAIL -> PASS

**Q28** (model). Gate 4 failed for leaving out the adjacent net headcount change and its difference from attrition. The passage with the net headcount (EDJ-10Q-2025Q2#64, 20,309 vs 19,589) was in both retrieved sets; hybrid's answer used it as adjacent with 'not attrition: it nets hires against departures'. Same evidence, different shape: model, not separable from run-to-run variation. Passage: `EDJ-10Q-2025Q2#64`.

### Same verdict, different answer

- **Q1** (PASS): Hybrid passage recall 0.125 vs 0.5; the answer still names the channels in management's words, dated.
- **Q3** (FAIL): Same failure (concessions missing) on a different set.
- **Q7** (FAIL): Same failure (two dimensions, payout philosophy missing).
- **Q11** (FAIL): Same: two of five definitions, gap_with_adjacent; the missing three are corpus gaps.
- **Q12** (FAIL): Same: Edward Jones cost structure not set alongside.
- **Q15** (FAIL): Same: Schwab revenue composition (`SCHW-10K-2025#27`) in neither set.
- **Q20** (FAIL): Behavior changed: Gate 4 answered (`answer`), hybrid chose `gap_with_adjacent`. Hybrid's passage recall 0.111 vs 0.429: fewer survey passages reached the model (retrieval). The Fidelity study and the UBS sample were in neither set.
- **Q22** (PASS): Hybrid's set holds the must-not passage `MS-PR-2026-04-15-01#15`; the answer cites it only for its NNA-definition footnote, not as NNA, so no substitution.
- **Q23** (FAIL): Adds class r: hybrid's answer says Raymond James gives no count; `RJF-TR-2025Q3#4` (8,943) was in neither set for this question.
- **Q25** (FAIL): Behavior changed: Gate 4 `gap_with_adjacent`, hybrid `answer`, on largely different evidence (7 of 30 passages shared). `MS-10K-2025#153` and `RJF-PR-web-affiliation-options#1` were in neither set.

## Findings

- **Same total.** hybrid-norerank's lower passage recall in #211 (tier-1 0.484 vs 0.597) did not lower the acting-quality score: 21/30 in both modes, 12/18 on tier 1. The one verdict hybrid lost (Q17) is a retrieval loss; the one it gained (Q28) is a model difference on shared evidence.
- **Q22's must-not passage was harmless in this run.** `MS-PR-2026-04-15-01#15` (fee-based asset flows footnote) reached the model; the answer cited it only for the NNA definition in the same chunk's footnote 12 and reported no fee-based flow as NNA. One run; a different run could use it differently.
- **Gate 4's missed passages are still missed.** Of the 9 chunk ids behind the passages Gate 4 named as missed (Q7 and Q25 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q17 `BAC-TR-2026Q2#21`, Q19 `EDJ-10K-2025#88`, Q20 `FIDELITY-III-2025#0`, `UBS-NEXTGEN-2026#119`, `UBS-NEXTGEN-2026#13`, Q25 `RJF-PR-web-affiliation-options#1`), none was in hybrid's retrieved set for its question in this run; the failures they explain (Q15 r, Q20 r, Q25 r) stay.
- **Behavior moved on two questions with unchanged verdicts:** Q20 `answer` -> `gap_with_adjacent` (fewer survey passages), Q25 `gap_with_adjacent` -> `answer`. Both FAIL in both runs.
- **No invalid or truncated output.** 30 valid Answers; 0 `INVALID_OUTPUT`, 0 `NOT_EVALUATED` in the final run.
- **Run interruption.** The first attempt stopped on a local crash in the embedding tokenizer (not an API error); 17 calls = 17 raw files at that point. Completed under a TL decision with cache reuse, 30 calls in total.

This report states results only; whether hybrid moves toward `main` is the tech lead's decision (ADR-010, ADR-011).

Rebuilt with (local helpers, no model calls): `ev212\pack.py` (scoring pack, Gate 4's), `ev212\compare.py` (per-question comparison), `ev212\build_summary.py`, `ev212\build_report.py` in `D:\ALLPROJECTS\EDJ\cache\`.
