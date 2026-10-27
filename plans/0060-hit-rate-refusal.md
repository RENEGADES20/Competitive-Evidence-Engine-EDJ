# 0060 - Hit rate and refusal accuracy per question

Issue: #60    Role: S1    Spec: specs/retrieval.md

## Goal
Every eval run reports, per question, recall (how many expected documents and passages came
back) and refusal accuracy (whether a misleading substitute came back), and a baseline report
for the current snapshot is committed under `evals/` so later tuning PRs compare against it.

## Files to change
- evals/expected_chunks.yaml (new) - the #87 answer key in machine-readable form: chunks that
  must come back, chunks that must not, the Q26 90-day rule; plus must-not lists for the gap
  questions Q24, Q25, Q28, Q29, Q30
- evals/expected_results.md - short sections for those five gap questions (the human-readable
  key stays the source the YAML is written from)
- scripts/eval_run.py - per-question recall (documents and passages), tier-1 overall,
  refusal check, `--as-of` for the Q26 window, report columns and summary; reads
  `expected_doc_ids` from questions.yaml when #56 adds it
- tests/test_eval_run.py - fake hits, no DB or network
- evals/baselines/corpus-2026-10-22/report.md + report.json - the baseline

## Steps
1. Tests first: recall maths, refusal rule, Q26 window.
2. YAML key for Q1, Q4, Q11, Q22, Q26 from expected_results.md; every chunk ID re-checked
   against the database.
3. Gap-question keys: for Q24, Q25, Q28, Q29, Q30 run retrieval and list the misleading
   substitutes that could come back. Unconfirmed items marked `TODO-verify`.
4. Metric into the runner's JSON, then the table.
5. Mock run of all 30 -> committed baseline; second run against it -> 30 UNCHANGED.

## Definitions
- Must-return rows: one row per passage; a row is found when any of its IDs is retrieved
  (an ID without `#` is a whole document). Document recall = expected doc_ids with at least
  one retrieved chunk / expected doc_ids. Passage recall = rows found / rows.
- Overall tier-1 recall = mean of per-question document recall over tier-1 questions that
  have a key; the rest show "n/a until #56".
- Refusal check (questions with a key): FAIL when any retrieved chunk is on the must-not list,
  is a forbidden hit (another firm; BAC outside GWIM for Merrill), or (windowed questions) was
  published before as-of minus the window. BAC GWIM chunks for a Merrill question are
  substitutes the code labels (entities.yaml caveat) and are not counted as misleading.
- A refusal FAIL makes the question's status FAIL (expected_results.md: one trap chunk = fail).

## Acceptance
- [x] Recall per tier-1 question and overall (9 of 18 tier-1 questions have a key; the other 9
      show "n/a until #56" and are scored from `expected_doc_ids` once #56 lands - still open)
- [x] Refusal accuracy for Q24, Q25, Q28, Q29, Q30 (and Q1, Q4, Q11, Q22, Q26)
- [x] Baseline report for corpus-2026-10-22 in `evals/baselines/` (first cut on corpus-2026-10-18, see log)
- [x] `pytest -q` passes (155); mock only, 0 real calls; no `src/` change (verify-cee not needed)

## Progress log
- 2026-10-22 18:38 - plan written; branch s1/60-hit-rate-refusal created from main (783c83f)
- 2026-10-22 18:40 - 7 tests (recall, refusal, window, #56 fallback, summary, IDs in manifest).
- 2026-10-22 18:42 - expected_chunks.yaml: five #87 questions (93 IDs, all found in the DB) and
  gap keys for Q24, Q25, Q28, Q29, Q30 (adjacent evidence + must-not traps, all IDs found).
  Surprise: EDJ does disclose an advisor attrition % (2025 10-Qs: 6.4%, 6.1%), so Q28's
  "neither discloses" is half wrong; noted for C1 in expected_results.md (question not edited).
- 2026-10-22 18:44 - runner: score_key / summarize / key_for, --as-of, --keys, new columns.
  Baseline (mock, k=8, as of 2026-10-22, corpus-2026-10-18): PASS 6, FAIL 22, NOT_EVALUATED 2;
  tier-1 recall documents 0.317, passages 0.139 (9 of 18 with a key); refusal accuracy gap
  5/5, all keyed 8/10 (Q22: fee-based flows footnote; Q26: 7 chunks older than the window).
  PASS 7 -> 6 vs #43's run: Q26 now fails its window. Re-run against the baseline: 30
  UNCHANGED. Q26 as of 2026-10-19: recall 1/5 passages, refusal FAIL (7), matching #87.
  pytest 155 passed. Caveats: Q4/Q30 retrieve nothing (BAC untagged in this snapshot), so
  their refusal "ok" is trivial; document recall is generous for large 10-Ks (Q29 1/1 docs,
  0/2 passages) - read it with passage recall.
- 2026-10-27 16:48 - TL: merged main (#101 windows, #106 retrieval). Fixed: `main()` resolved
  questions with today's date while scoring used `--as-of`, so retrieval and scoring windows
  could differ; `resolve(..., today=args.as_of)` + test. Q4/Q28 answer key: BAC-TR-2026Q1#48 and
  BAC-TR-2026Q2#38 annotated as untagged on purpose (#95), waiting on #107. Baseline moved to
  corpus-2026-10-22 (mock, k=20, as of 2026-10-27): PASS 25, FAIL 3 (Q15, Q19, Q29),
  NOT_EVALUATED 2; tier-1 recall documents 0.809, passages 0.347; refusal accuracy gap 4/5,
  all keyed 9/10. Q29 refusal FAIL: MS-10K-2025#696 (must-not) now retrieved at k=20, an S1
  tuning item. Re-run against the baseline: 30 UNCHANGED. pytest 197 passed. 0 real calls.
