# 0297 - Reduce prompt v9: effort low, answer length follows the question, Gate 3

Issue: #297    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: `docs/results/w13-reduce-v9.md` (prompt
rules in full, Q1-Q30 passes_if mapping, why v8 went past 5 sentences, cost detail)

## Goal
Synthesis-form answers (window / all-recency questions keep v5.2) are written by prompt **v9** at reduce effort `low`:
sentence 1 answers and cites, then exactly what the question asks for, so every asked part lands in the answer text,
not only in the evidence list (#295 lost Q5, Q7, Q22 that way). Gate 3 (TL go-ahead 2026-11-23) decides the default.

## Design
- **Prompt v9** (`SYSTEM_PROMPT_V9`; rules in the results doc): no sentence cap; length follows the question.
  Single fact -> 1-3 sentences; "for each firm" / "by quarter" / list -> one cited sentence per asked item; comparison ->
  one sentence per firm plus one cited verdict; "what do we know / how" -> the main points, each cited. Evidence the
  question did not ask for is not restated. Back from v7 (dropped in v8): future positions attributed and dated, no
  own forecast; trade press attributed; payout wording. New: newest period of a figure unless a series is asked; a
  figure keeps its item's label; deployed vs stated intent and source kind kept apart when the question separates them.
- **Coverage rule (code, v9 only).** A cell is *asked* when it holds a fact or an accepted derivation (`holds`), its
  aspect is not comparison and not proxy, and its role is `named`, `all` or `research`. An asked cell no sentence
  covers (by cell id, or an aspect-id sentence citing its chunks, the v7 `aspect` state) gets a `part_gap`. Not a
  part_gap (state `evidence_list`, as v8): `competitor` cells (firms the question did not name, e.g. Q19's widening),
  comparison aspects (`comparison_missing` guards them), proxy aspects and adjacent-only cells (adjacent path); cells
  with no fact and code gaps keep their gaps as today. The Computability box (#292) stays.
- **Code shape.** `P.SYNTHESIS_VERSIONS` += v9; `P.BRIEF_VERSIONS` (box, evidence list) += v9; new
  `P.ASKED_VERSIONS = ("v9",)` and `reduce.asked(m, query)`; `part_coverage` takes the mode and applies the rule.
  v5.2 / v7 / v8 behavior unchanged. **Mock v9:** claim 1 "In short: <first holding item>." (part_id its aspect),
  comparison claims as v5.2, then one sentence per asked cell from its first counting item (part_id the cell id),
  skipped when claim 1 already cites its chunks; no cap, no computation claims; adjacent as v5.2.
- **Why v8 went past 5 sentences** (#296 reviewer; Q2 Q3 Q10 Q17 Q18 Q19 in #295): Q2, Q17, Q18 = 5 + the comparison
  sentence written as a 6th; Q10 = 6 model sentences; Q3 = 8 and Q19 = 8 (cap ignored at effort off) + Q19's code
  hand-off. v9 has no cap; length is judged by the scorers against passes_if, and the mock check bounds the flags.

## Files to change
`src/cee/answer/prompt.py`, `reduce.py`, `validate.py`, `src/cee/config.py` (`v9` choice; default per the decision
rule), `tests/test_reduce_synthesis.py`, spec #297 block in `specs/answer-citations.md`, `scripts/verify_cee.py` +
`.claude/skills/verify-cee/features/ask-layout.md` (version check accepts v9), results doc and
`docs/results/w13-reduce-v9/` (`run-gate3.ps1` / `.sh` from #295 with `REDUCE_PROMPT=v9`, no `_BRIEF` var, EvDir
`ev297`; `count.py`, `dump295.py`, `merge_verdicts.py`, `reduce_table.py` reused from #295, which run on main: the
#295 branch code (per-form effort, fallback) is not needed at uniform `low` and is not taken).

## Steps
1. Code + tests (0 calls): v9 text and version label; coverage rule (asked cell uncited -> part_gap; competitor /
   comparison / proxy / adjacent-only cell -> no part_gap); mock v9 shape; v5.2, v7, v8 unchanged; box under v9.
2. Mock (0 calls), `cmp_mock.py`, fts Q1-Q30, rule and #272 plans: v8 branch = main 30/30; v9 vs v8: Q26, Q27
   byte-identical, no new flag kind, part_gap / comparison_missing / outside_matrix / number_not_found / no_citation
   not above v8. Then pytest.
3. verify-cee on mock, `REDUCE_PROMPT=v9`: ask-answer, ask-layout, ask-progress (layout unchanged, answer above evidence).
4. Count (0 calls) at the gate commit, clean worktree, cache `ev297\cache` = a copy of `ev295\cache`: expect **517
   reused** (30 plans, 454 maps, 31 re-maps, Q26 + Q27 v5.2-low reduces from #272) and **28 new reduce keys** (every
   other question: v9 is in the key). Any other count: stop and report.
5. Gate 3 run: `-Phase run -MaxCalls <count>` (28), deepseek `deepseek-v4-pro` `/beta`, plan off / map low / reduce
   low, stream on, idle 120 s, `REDUCE_PROMPT=v9`, MAP_PREFIX off, fts, as-of 2026-11-17, `corpus-2026-11-19`,
   `PYTHONHASHSEED=0`. No re-roll: a cut, invalid or failed record is a FAIL.
6. Scoring: #272 method + #295 text-only rule. `dump295.py` -> `ev297\blind-in\` (dump, questions.yaml, #250
   `verdict-rule.txt` same sha256) with hashes; four fresh Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21,
   Q22-Q30); a PASS is judged on what the answer asserts (sentences, citations, box), evidence list is context;
   `text_only` per PASS; merged verdicts with sha256; then the PR reviewer's second read of borderline FAILs gives
   the text-only adjudicated count. The implementer starts the scorers; if its session cannot start subagents, the
   TL starts them with the same inputs. Q26 / Q27: same records as #272 (zero delta by construction).
7. Results doc + PR: per-question verdicts vs #272 adjudicated and #295; reduce wall p50 / p90, output and reasoning
   tokens, cost next to v5.2 (#272) and v8-off (#295) (`reduce_table.py`).

## Decision rule (fixed before any call)
- Text-only adjudicated **>= 24/30**: v9 becomes `REDUCE_PROMPT_DEFAULT`.
- **<= 23/30**: the default goes back to `v5.2` in the same PR; v9 stays behind `REDUCE_PROMPT`; the results doc
  names each regression against #272 with its cause.

## Acceptance
- [ ] pytest green (CI), with the step-1 tests.
- [ ] Mock eval as step 2; verify-cee on mock as step 3.
- [ ] Gate 3 scored, decision rule applied, latency / tokens / cost reported as step 7.

## Paid calls
- **28** new `deepseek-v4-pro` reduce calls (Q1-Q30 minus Q26, Q27), one run, `--max-calls` = the count. No plan,
  map or re-map call. Why: answer quality of v9 is the question; the mock cannot show it.
- **Cost:** v8-low (#292) mean $0.067 / call at peak; v5.2-low (#272) $0.104 / question at peak. 28 calls: about
  $1.9-2.9 at peak (CNY 14-21), half off-peak; balance about CNY 90.
- **Approval:** TL go-ahead 2026-11-23 (issue #297). Every other step makes 0 calls.

## Progress log
- 2026-11-23 23:35 - plan written from main 372303f; DB at corpus-2026-11-19 (sync check exit 0). 0 calls.
