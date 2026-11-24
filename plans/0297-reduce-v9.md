# 0297 - Reduce prompt v9: effort low, answer length follows the question, Gate 3

Issue: #297    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: `docs/results/w13-reduce-v9.md` (prompt
rules in full, Q1-Q30 passes_if mapping, Q19 roles, why v8 went past 5 sentences, cost detail)

## Goal
Synthesis-form answers (window / all-recency questions keep v5.2) are written by prompt **v9** at reduce effort `low`:
sentence 1 answers and cites, then exactly what the question asks for, so every asked part lands in the answer text,
not only in the evidence list (#295 lost Q5, Q7, Q22 that way). Gate 3 (TL go-ahead 2026-11-23) decides the default.

## Design
- **Prompt v9** (`SYSTEM_PROMPT_V9`; rules in the results doc): no sentence cap; length follows the question.
  Single fact -> 1-3 sentences; "for each firm" / "by quarter" / list -> one cited sentence per asked item; comparison ->
  one sentence per firm plus one cited verdict; "what do we know / how" -> the main points, each cited. Evidence the
  question did not ask for is not restated. Back from v7: future positions attributed and dated, no own forecast; trade
  press attributed; payout wording. New: newest period unless a series is asked; a figure keeps its item's label;
  each firm's metric definition alongside its figure or series; a firm that does not report the asked metric is said
  not to report it, never zero and never a near-neighbour metric (Q22, Q23); deployed vs stated intent and source kind
  kept apart when the question separates them.
- **Coverage rule (code, v9 only).** A cell is *asked* when it holds a fact or an accepted derivation (`holds`), its
  aspect is not comparison and not proxy, and its role is `named`, `all` or `research`, or `competitor` with the firm
  in the aspect's `asked_firms` (the planner asked for that competitor; Q19 a7). An asked cell no sentence covers (by
  cell id, or an aspect-id sentence citing its chunks, the v7 `aspect` state) gets a `part_gap`. No part_gap (state
  `evidence_list`, as v8): other `competitor` cells (home-firm widening the question did not ask for, Q19 a1-a4),
  comparison aspects (`comparison_missing`), proxy aspects and adjacent-only cells; empty cells and code gaps as today.
  The Computability box (#292) stays.
- **Code shape.** `P.SYNTHESIS_VERSIONS` += v9; `P.BRIEF_VERSIONS` (box, evidence list) += v9; new
  `P.ASKED_VERSIONS = ("v9",)` and `reduce.asked(m, query)`; `part_coverage` takes the mode. v5.2 / v7 / v8 unchanged.
  **Mock v9:** claim 1 "In short: <first holding item>." (part_id its aspect), comparison claims as v5.2, then one
  sentence per asked cell from its first counting item (part_id the cell id), skipped when claim 1 cites its chunks;
  no cap, no computation claims; adjacent as v5.2.
- v8 answers over 5 sentences in #295 (#296 reviewer): model behavior at effort off, not code; see the results doc.

## Files to change
`src/cee/answer/prompt.py`, `reduce.py`, `validate.py`, `src/cee/config.py` (`v9` choice; default per the decision
rule), `tests/test_reduce_synthesis.py`, spec #297 block in `specs/answer-citations.md`, `scripts/verify_cee.py` +
`.claude/skills/verify-cee/features/ask-layout.md` (version check accepts v9), results doc and
`docs/results/w13-reduce-v9/` (`run-gate3.ps1` / `.sh` from #295 with `REDUCE_PROMPT=v9`, no `_BRIEF` var, EvDir
`ev297`; `count.py`, `dump295.py`, `merge_verdicts.py`, `reduce_table.py` reused: they run on main; the #295 branch
code (per-form effort, fallback) is not needed at uniform `low` and is not taken).

## Steps
1. Code + tests (0 calls): v9 text and label; coverage rule (asked cell uncited -> part_gap; competitor in / not in
   `asked_firms`; comparison / proxy / adjacent-only -> no part_gap); a test that a series cell cited by a sentence
   naming one period is NOT flagged (the rule checks citations, not content); mock v9; v5.2, v7, v8 unchanged; box.
2. Mock (0 calls), `cmp_mock.py`, fts Q1-Q30, rule and #272 plans: v8 branch = main 30/30; v9 vs v8: Q26, Q27
   byte-identical, no new flag kind, part_gap / comparison_missing / outside_matrix / number_not_found / no_citation
   not above v8. Q19 roles dump from the #272 matrix (done at plan time from `ev295\g3-run\report.json`, results doc):
   re-check it on the count report; a competitor cell carrying a passes_if part outside `asked_firms`: stop and
   report. Then pytest.
3. verify-cee on mock, `REDUCE_PROMPT=v9`: ask-answer, ask-layout, ask-progress (layout unchanged, answer above evidence).
4. Count (0 calls) at the gate commit, clean worktree, cache `ev297\cache` = a copy of `ev295\cache`: expect **517
   reused** (30 plans, 454 maps, 31 re-maps, Q26 + Q27 v5.2-low reduces from #272) and **28 new reduce keys**. Any
   other count: stop and report.
5. Gate 3 run: `-Phase run -MaxCalls <count>` (28), `deepseek-v4-pro` `/beta`, plan off / map low / reduce low, stream
   on, idle 120 s, `REDUCE_PROMPT=v9`, MAP_PREFIX off, fts, as-of 2026-11-17, `corpus-2026-11-19`, `PYTHONHASHSEED=0`.
   No re-roll: a cut, stalled, invalid or failed record is a FAIL.
6. Scoring: #272 method + #295 text-only rule, on the **28 new answers** (Q1-Q25, Q28-Q30). `dump295.py` ->
   `ev297\blind-in\` (dump, questions.yaml, #250 `verdict-rule.txt` same sha256, scorer note) with hashes; four fresh
   Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q25 + Q28-Q30). A PASS is judged on what the answer asserts
   (sentences, citations, box); the evidence list is context; `text_only` per PASS. Merged verdicts with sha256.
   - **Q26, Q27** reuse the identical #272 v5.2 records, so they carry #272's adjudicated verdicts (both PASS) and are
     not re-scored.
   - **Borderline:** the #250 rule says only "Borderline verdicts are named (borderline: true) with the reason"; no
     criterion. Defined now (in the scorer note): a FAIL whose reason names a single missing or misworded part while
     the answer is otherwise correct.
   - **Second read:** the PR reviewer agent (fresh, not a scorer) re-reads borderline FAILs only, same verdict rule and
     text-only rule. Result = **text-only adjudicated count**, which the decision rule uses.
   - The implementer starts the scorers; if its session cannot start subagents, the TL starts them, same inputs.
7. Results doc + PR, only from saved raw outputs and the merged verdicts sha256: per-question verdicts vs #272 and
   #295; reduce wall p50 / p90, output and reasoning tokens, actual cost per call from the report, next to v5.2
   (#272) and v8-off (#295) (`reduce_table.py`).

## Decision rule (fixed before any call)
- Text-only adjudicated **>= 24/30**: v9 becomes `REDUCE_PROMPT_DEFAULT`.
- **<= 23/30**: the default goes back to `v5.2` in the same PR; v9 stays behind `REDUCE_PROMPT`; each regression
  against #272 named with its cause.
- #272's 24/30 was not scored under the text-only rule, so v9 meets a stricter bar (as in #295).

## Risks
- The coverage rule checks that a cell's chunks are cited, not what the sentence says: one sentence per firm citing a
  series can state only the latest quarter and pass (Q22, Q23, the #295 form failure). Prompt and scorers carry it;
  the mock cannot show it (step-1 test documents the limit).
- Latency at peak: v8-low p50 142 s, p90 318 s (Q22, Q24). A stream silent for 120 s is cut and is a FAIL (no re-roll).
- Asked-but-uncited cells now show visible "Not answered ..." gaps, which scorers may penalise.

## Acceptance
- [ ] pytest green (CI), with the step-1 tests. Mock eval and Q19 check as step 2; verify-cee on mock as step 3.
- [ ] Gate 3 scored, decision rule applied, latency / tokens / cost reported as step 7.

## Paid calls
- **28** new `deepseek-v4-pro` reduce calls (Q1-Q30 minus Q26, Q27), one run, `--max-calls` = the count. No plan,
  map or re-map call. Why: answer quality of v9 is the question; the mock cannot show it.
- **Estimate** (the PR quotes the actual cost from the report): v8-low mean $0.067 / call at peak (#292), v5.2-low
  $0.104 / question at peak (#272): 28 calls about $1.9-2.9 at peak (CNY 14-21); v9 has no reasoning cap, so it may
  exceed this. Balance about CNY 90.
- **Approval:** TL go-ahead 2026-11-23 (issue #297). Every other step makes 0 calls.

## Progress log
- 2026-11-23 23:35 - plan written from main 372303f; DB at corpus-2026-11-19 (sync check exit 0). 0 calls.
- 2026-11-23 - plan review CHANGES REQUESTED (issue comment 7123145488): Q26 / Q27 carry #272 verdicts; borderline
  and second read defined; stricter bar stated; Risks added; Q19 roles dumped (0 calls), competitor cells in
  `asked_firms` are asked; Q22 / Q23 rules in the prompt; citation-not-content test. Amended. 0 calls.
