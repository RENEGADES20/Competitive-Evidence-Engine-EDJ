# 0105 - Real-model answers for the 12 retrieval-passing questions

Issue: #105 (also closes #95)    Role: TL    Spec: specs/retrieval.md, specs/answer-citations.md, specs/transcripts-ir.md

## Goal
With `LLM_PROVIDER=anthropic`, the 12 questions that pass the mock eval (Q1-Q5, Q8, Q12, Q13,
Q16, Q26, Q27, Q30) get real, cited answers that meet their `passes_if`, instead of
"Not in the corpus".

## What was wrong (found with the real model, 2026-10-22)
- Retrieval handed the model 8 chunks ranked by `ts_rank_cd`, which ignores how rare a word is.
  For Q1 all 8 were the NNA *definition* footnote, copied across four 10-Qs and three press
  releases. The earnings-call passages on NNA strategy were never retrieved. The model then
  (correctly) said the evidence held no strategy: `gap_with_adjacent`, shown as "Not in the corpus".
- The mock eval passed these questions because it only checks that an expected document *type*
  was hit, not that the passages answer the question.
- Merrill questions saw only 64 GWIM-tagged BAC chunks: transcripts and press releases were
  untagged (#95), so management's Merrill commentary was filtered out.
- Prompt v0 sent anything short of a literal answer to `gap_with_adjacent`.
- Time windows (Q26, Q27) and the code-owned GWIM caveat (Q30) were not implemented.

## Files to change
- src/cee/retrieve/fts.py - IDF-weighted rank, boilerplate penalty, instruction words out of the
  search terms, over-fetch per (firm, doc type), quotas, near-duplicate removal, per-doc cap,
  relevance floor, k=20, SQL time windows
- src/cee/ingest/chunk.py, src/cee/ingest/load.py, config/entities.yaml - mention-based GWIM
  tagging for flat BAC transcripts/press releases (#95); `technology` synonym
- src/cee/answer/prompt.py (v1), src/cee/answer/llm.py - dated, attributed claims; partial
  answers with gaps; source line shows segment and publication date; max_tokens 4000
- src/cee/answer/validate.py, src/cee/ask.py - insert_caveats (code-owned)
- scripts/eval_run.py - --k defaults to the app's k
- tests/ - quotas, windows, mention tagging, caveats

## Acceptance
- [x] Mock eval, all 30: no forbidden hits, no regressions vs the 2026-10-22 baseline
- [x] Real run of the 12: each meets `passes_if` (reviewed by hand, answers saved)
- [x] Every GWIM-tagged BAC PR/TR chunk spot-checked: 0 wrong (#95)
- [x] pytest passes; verify-cee passes

## Progress log
- 2026-10-22 - reproduced from query_log (Q1, Q2 real answers: gap_with_adjacent); root causes above
- 2026-10-22 - retrieval rewritten to the spec (k=20, over-fetch, dedupe, quotas, windows) plus
  IDF rank; first look showed footnotes still won inside each doc type, hence IDF and the
  boilerplate penalty
- 2026-10-22 - GWIM mention tagging: first rule (no other business named at all) missed key
  chunks; switched to a 2:1 dominance rule. All 15 tagged PR/TR chunks read in full: 0 wrong
- 2026-10-22 - mock eval 12 -> 26 PASS of 30, 0 forbidden; real run of the 12 (12 calls,
  claude-sonnet-5-5): 12/12 behavior as expected; 163/163 figures found in cited chunks
