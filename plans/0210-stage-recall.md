# 0210 - Per-stage retrieval recall (pool vs final) and the missed passages in the answer key

Issue: #210    Role: TL    Spec: specs/retrieval.md

## Goal
The mock eval tells, for every expected passage, whether it was never a candidate (recall
problem) or was a candidate and lost in `select()` (selection problem): `eval_run.py` reports
recall@pool and recall@final per question and in the summary, and the answer key holds the
passages Gate 4 named as missed. Retrieval behavior does not change: the final chunk ids of all
30 questions are identical before and after.

## Facts (2026-11-18, read only; DB `cee` = `corpus-2026-11-17`, sync check up to date)
- Base: `main` 40a963a (Gate 4, #209). Committed mock baseline
  `evals/baselines/corpus-2026-11-17/report.json` (commit 635c542, as of 2026-11-17): 29 PASS /
  1 FAIL (Q19), tier-1 doc recall 0.788, passage recall 0.607 (17 of 18 tier-1 keyed), refusal
  19/19.
- `search()` (src/cee/retrieve/fts.py) fetches, before any `select()`: `rows` (firm pool, main
  SQL), `research_rows` and `on_theme_rows` (entity+theme only), `peer_rows` (theme peers,
  #205; `peer_floor()` cuts them before their `select()`), and `answers` (answer turns of kept
  question turns, `answer_turns()`). Early returns (unmapped firm, firm filter leaves none) fetch
  nothing.
- Callers of `search()`: `src/cee/ask.py`, `src/cee/smoke.py`, `scripts/eval_run.py`. Only
  eval_run gets the new argument; the others are untouched.
- Every named id exists in `chunks` (count = 1 each): `SCHW-10K-2025#27`,
  `RJF-PR-web-affiliation-options#1`, `BAC-TR-2026Q2#21`, `EDJ-10K-2025#88`, `MS-10K-2025#153`.
  Q20 documents: `FIDELITY-III-2025` (research, 2 chunks; #0 "Wealthy next generation investors
  want something new ... Fidelity's 2025 Investor Insights") and `UBS-NEXTGEN-2026` (candidate
  sample chunks #13, #16, #28: "those surveyed"). Exact Q20 ids are pinned in step 1.
- Answer key today (`evals/expected_chunks.yaml`) has keys for Q1, Q4, Q11, Q22, Q24-Q26,
  Q28-Q30. Q25 already lists `MS-10K-2025#153`. Q17 and Q20 are scored from
  `expected_doc_ids` in questions.yaml (#56); Q7, Q15, Q19 have no key at all.
  `key_for()` prefers the hand key, so a new hand key for Q17 / Q20 would drop their #56 rows
  unless it carries them over.

## Files to change
Owner review waived, TL decision 2026-11-17 (#187): `src/cee/retrieve/fts.py` and
`specs/retrieval.md` (S1), `evals/expected_chunks.yaml` (C1).
- `src/cee/retrieve/fts.py` (S1; owner review waived, TL decision 2026-11-17 (#187)) - a small `PoolTrace` dataclass (chunk-id lists `firm`, `research`,
  `on_theme`, `peers`, `answers`; `ids()` = their union) and `search(q, k=None, trace=None)`
  appending the ids of each pool right after it is fetched. Trace only: no SQL, ordering,
  `select()` argument, floor, quota or budget change; `trace=None` (the default, every app
  caller) runs exactly today's code path.
- `scripts/eval_run.py` - pass a `PoolTrace` to `search()`; per question `recall_pool` (rows
  with an id in the pool union / rows; same `DOC#seq` and `DOC` matching and the same window
  filtering as today's passage recall), `recall_final` (= today's `passage_recall`), per row a
  stage `final` / `pool` (in pool, lost in select) / `none` (not in pool), `pool_size`,
  `tokens_est` (= chars / 4, rounded). Summary: mean recall@pool and recall@final over keyed
  questions (all tiers, and tier 1), total passages and total estimated tokens. Columns in the
  report.md table and the console line; per-question section shows each row's stage.
- `evals/expected_chunks.yaml` (C1; owner review waived, TL decision 2026-11-17 (#187)) - the
  Gate 4 missed passages:
  Q7 new key [`MS-10K-2025#153`]; Q15 new key [`SCHW-10K-2025#27`]; Q17 new key = its 9
  `expected_doc_ids` as one row each + [`BAC-TR-2026Q2#21`]; Q19 new key [`EDJ-10K-2025#88`];
  Q20 new key = its 7 `expected_doc_ids` as one row each + the Fidelity row + the UBS sample row;
  Q25 + [`RJF-PR-web-affiliation-options#1`]. New keys have `must_not_return: []`. Comments cite
  Gate 4 "Known gaps" / #210. `evals/expected_results.md` is not changed (out of the issue's list;
  noted in the PR).
- `evals/baselines/corpus-2026-11-17/report.json`, `report.md` - replaced by the new mock run
  (the old one stays in git history at 40a963a).
- `specs/retrieval.md` (S1; owner review waived, TL decision 2026-11-17 (#187)) - Acceptance:
  recall@pool and recall@final defined.
- Not changed: README "Retrieval check" numbers (out of scope, reviewer note 3).
- `tests/test_retrieval_trace.py` (new) - with the fake-connection pattern of
  `tests/test_retrieval_themes.py` (`monkeypatch.setattr(fts, "connect", ...)`): `search()` with
  and without a trace returns the same hits in the same order (entity and entity+theme with
  peers), and the trace holds every pool's ids (a final hit is always in `trace.ids()`).
- `tests/test_eval_run.py` - pool-recall scoring: row stages final / pool / none, `DOC` row
  matched by a pool chunk of the document, window rows filtered, tokens = chars / 4, summary means.

## Steps
1. Pin the Q20 ids: query `chunks` for `FIDELITY-III-2025` and the UBS chunk that states who was
   surveyed (sample size / population); record the query and output in the Progress log. Check
   every id added in step 4 exists (`SELECT chunk_id FROM chunks WHERE chunk_id = ANY(...)`) and
   keep that output for the PR.
2. "Before" run on unchanged code: `.venv\Scripts\python.exe scripts/eval_run.py --as-of
   2026-11-17 --out .eval-runs/0210-before` (mock, 0 real calls).
3. Add `PoolTrace` and the `trace` argument to `search()`; write `tests/test_retrieval_trace.py`;
   pytest.
4. Extend `eval_run.py` (pool recall, stages, tokens, summary, table columns, console line); add
   the unit tests to `tests/test_eval_run.py`; add the answer-key rows (step 1 ids).
5. "After" run: `.venv\Scripts\python.exe scripts/eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0210-after`. Diff the final
   chunk ids per question between `0210-before/report.json` and `0210-after/report.json` (a
   short Python comparison, output kept for the PR): must be 30/30 identical, same order. Any
   difference stops the work: find the cause, never re-key around it.
6. Build the PR table from the after run: each named passage -> "in final", "in pool, lost in
   select" or "not in pool" (Q7, Q15, Q17, Q19, Q20 x2, Q25 x2).
7. Copy the after run to `evals/baselines/corpus-2026-11-17/` (report.json, report.md).
8. `specs/retrieval.md` metric definitions.
9. pytest (full), `python scripts/verify_cee.py run` (all features PASS). No user feature
   changes (Ask page, ask.py untouched), so no verify-cee recipe update.

Unsure: recall summary numbers move because the key grows (new rows, new keyed questions Q7,
Q15, Q19), not because retrieval changed; the PR states this next to the chunk-id diff. Status
changes vs the old baseline (e.g. a newly keyed question failing its refusal check) are reported
as findings, not fixed here (#213 owns ranking/selection).

## Acceptance
- [x] `python scripts/eval_run.py --as-of 2026-11-17` (mock) prints recall@pool and recall@final
  per question (console line and report.md table) and in the summary row -> check: the after
  run's console output and report.md show both, for every keyed question.
- [x] No behavior change: final chunk ids of all 30 questions identical before/after -> check:
  step 5 diff of `.eval-runs/0210-before/report.json` vs `.eval-runs/0210-after/report.json`
  prints 30/30 identical (same ids, same order); plus `tests/test_retrieval_trace.py` (with vs
  without trace, same hits).
- [x] PR table of the named missed passages, each "not in pool" or "in pool, lost in select"
  (or "in final") -> Q7 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q17 `BAC-TR-2026Q2#21`,
  Q19 `EDJ-10K-2025#88`, Q20 Fidelity + UBS sample, Q25 `RJF-PR-web-affiliation-options#1` and
  `MS-10K-2025#153`; stages read from the after run's per-row stage.
- [x] Every added id in `evals/expected_chunks.yaml` exists in `chunks` -> check: step 1 query
  returns every added id (output in the PR).
- [x] Linked questions Q7, Q15, Q17, Q19, Q20, Q25 each have a key row for their Gate 4 missed
  passage; Q17 and Q20 keep their #56 doc rows.
- [x] Estimated tokens (chars / 4) and passages per question and in the summary.
- [x] New mock baseline in `evals/baselines/corpus-2026-11-17/`; `specs/retrieval.md` defines
  both metrics.
- [x] pytest passes; `python scripts/verify_cee.py run` all features PASS.
- [x] 0 real calls (mock only).

## Progress log
- 2026-11-18 21:51 - plan written (branch `tl/210-stage-recall` from main 40a963a).
- 2026-11-18 21:56 - plan approved by the reviewer agent (issue comment 6999170726); notes
  applied: owner-review tags in Files to change, Q20 UBS choice recorded, README numbers left.
  Step 1, Q20 ids pinned (`SELECT chunk_id, text FROM chunks WHERE chunk_id =
  ANY(...)`): `FIDELITY-III-2025#0` (the study's summary: wealthy next-generation households vs
  baby boomers; the document's only other chunk, #1, is related links; no sample size stored).
  UBS sample row = `UBS-NEXTGEN-2026#119` or `#13`: #119 is the methodology chunk that names the
  sample ("two global surveys conducted among YIO members", May 2025 "112 responses", Dec 2025 -
  Jan 2026 "63 responses", "10 deep-dive interviews"); #13 gives its ages ("from below 21 to above
  45, with the majority being between 26 and 40") and regions. #16 / #28 only say "those
  surveyed", so they were not picked. Gate 4 failed Q20 for "UBS and BofA give no age cut-off or
  sample size"; #119 and #13 are the text that has them. Existence check: 8/8 added chunk ids and
  16/16 carried-over #56 documents found.
- 2026-11-18 21:57 - step 2, before run on unchanged code: `.eval-runs/0210-before`, 29 PASS / 1
  FAIL (Q19), same as the Gate 4 baseline.
- 2026-11-18 21:58 - steps 3-4: `PoolTrace` + `search(trace=)`; eval_run stages, tokens, summary
  row; key rows; 42 eval_run + trace tests pass.
- 2026-11-18 22:01 - step 5, after run at f0ebc30 (`.eval-runs/0210-final`, baseline = Gate 4):
  final chunk ids 30/30 identical to the before run and to the Gate 4 baseline; statuses 30/30
  unchanged (no PASS -> FAIL). Change labels IMPROVED (Q7, Q15, Q19: newly keyed) and REGRESSED
  (Q17 passage 0.667 -> 0.6, Q20 0.429 -> 0.333: a new row not retrieved) come from the key only.
  Summary: recall@pool 0.686, recall@final 0.484 (21 questions with rows); tier 1 0.803 / 0.597;
  675 passages, ~195,683 tokens.
- 2026-11-18 22:01 - step 6, named passages: only `BAC-TR-2026Q2#21` (Q17) is in the pool and
  lost in select; the other seven are not in the pool (recall problems for #211 / #213 / #214).
- 2026-11-18 22:02 - steps 7-9: baseline replaced by the f0ebc30 run; spec metrics added; pytest
  549 passed; verify-cee all 9 features PASS (`.verify-runs/20261118-215956-9e554af`, working tree
  with the change). 0 real calls.
