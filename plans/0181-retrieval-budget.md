# 0181 - Retrieval budget: slots per question by firm count, Merrill counted once

Issue: #181    Role: TL    Spec: `specs/retrieval.md` (S1; owner review waived by TL decision
2026-11-17, [#187 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/187#issuecomment-6964392200))

## Goal
A question that names several firms gets a larger passage budget, so every named firm keeps its
best evidence as the corpus grows (Q22 and Q24 pass again on `corpus-2026-11-16`), and Merrill
(`MER` documents plus BAC chunks in GWIM/Merrill) takes one firm's share, not two. Questions that
name one firm keep k=20 and their retrieved lists stay identical. FTS only; no model, no new
dependency.

## Files to change
- `src/cee/retrieve/fts.py` (S1-owned; waiver above) -
  - `quota_firm(hit, q)` / a firm key in `select()`: a BAC chunk that is in the pool only through
    a named child's segment path (MER -> BAC GWIM/Merrill, read from `parent` / `reported_as` in
    `config/entities.yaml`, no hard-coded IDs) counts as that child. When the question names the
    parent itself (BAC), its chunks stay BAC. The firm key drives turns, `best` (FLOOR base) and
    the theme-first counter; `Hit.entity_id` is not changed (citations, footer, `theme_gaps` and
    the eval read it as today).
  - `budget(q) -> int`: k by the number of covered firms the question names (`len(q.entities)`
    after `apply_filters`; MER is already one entity; unmapped firms do not count). 0 or 1 firm ->
    `K = 20`; 2-5 firms -> `BUDGET_RULE(n)`, a module-level function that a scratch driver can
    swap for the grid (step 3b); its committed value is the rule chosen in step 3b.
    `search(q, k=None)`: `None` means `budget(q)`; an explicit `k` is honoured as today (tests
    and `--k` keep working).
  - `select()` fills the larger budget with the existing rules (firm turns, document-type turns,
    `MAX_PER_DOC`, near-duplicate removal, `FLOOR`, `THEME_FIRST`); `POOL_PER_GROUP` stays 15
    unless step 3 shows a firm running out of pool (then reported, not silently raised).
    `THEME_K` research slots unchanged.
  - Step 4 only if kept: per-firm terms in each firm's pool query.
- `scripts/eval_run.py` - `--k` default `None` = the app's per-question budget (`budget(q)`); the
  report header says "k by question" (or the fixed k when given), and each question row / JSON
  record carries its k, passage count and prompt characters (sum of `len(h.text)`), so prompt
  size before/after is read from the reports.
- `tests/test_retrieval_budget.py` (new) - fixture pool, no database:
  - Merrill counted once: 5 firms (MS, SCHW, EDJ, MER, RJF) with MER documents and BAC GWIM
    chunks; at k=20 each of the five firms gets 4 slots and MER + BAC-GWIM together get 4.
  - Parent named: a question naming BAC and MER keeps BAC's own chunks under BAC.
  - `budget()`: 0/1 firm -> 20; 2..5 firms -> the chosen rule; unmapped firms and peer phrases
    resolved to members counted correctly; firm filter narrows the count.
  - A single-firm pool gives the same list as before at k=20 (guard for acceptance 2).
- `tests/test_eval_run.py` - `--k` default `None` uses `budget()`; the k/prompt-size fields
  are in the record.
- `specs/retrieval.md` (S1-owned; waiver above) - interface sketch: `retrieve(query, k=budget(q))`,
  the budget rule, Merrill counted once in the quota.
- `docs/DECISIONS.md` - ADR-013 "Retrieval budget by number of firms" (replaces the spec's fixed
  k=20 for multi-firm questions; the grid results and the chosen rule).
- `src/cee/answer/llm.py` (S2; owner review waived, same #187 comment) - the `max_tokens`
  comment ("20 chunks (fts.K)"); `max_tokens` itself goes from 4000 to **8000** only if a step-8
  real call (Q22 or Q24) comes back `INVALID_OUTPUT` from truncation (path (b) in the paid-call
  plan), then that question is re-run once.
- `config/entities.yaml` - only if step 4 is kept.
- `plans/0181-retrieval-budget.md` (this file)

Out of scope (separate issues the TL does next): FLOOR / MAX_PER_DOC retuning (#166), the Q21
theme slot below the floor (#190), entity+theme quotas (#117), `adv` restriction (#179),
embeddings / rerankers (#182), answer keys. Merging #178 / #150.

## Paid-call plan
Mock for everything that decides the change. Then, run last on finished code, **2 real calls**:
one run each of **Q22** and **Q24** (five firms, the largest prompts after the change; ADR-012
single-call path, so 1 call per question). Why the mock cannot show it: the mock always answers
from whatever it is given; only a real model shows whether ~2x the passages still produce a
complete, valid answer within `max_tokens` = 4000 (a truncated tool call would be an
`INVALID_OUTPUT`) and whether every firm's passages are still cited. One run each, no re-runs;
`--real --max-calls 2`, raw outputs saved in the run's `raw/` folder and copied to
`D:\ALLPROJECTS\EDJ\cache\ev181\real`. A wrong answer is a finding, reported, not re-rolled.

Truncation (path (b), pre-approved by the TL): if Q22 or Q24 comes back `INVALID_OUTPUT`
because the answer was cut off at `max_tokens` (stop reason `max_tokens` / an incomplete tool
input in the saved raw payload), `max_tokens` in `src/cee/answer/llm.py` goes from 4000 to 8000
and **only that question is re-run once** (`--real --max-calls 1` per question; **at most 2 more
calls**, so at most 4 real calls in total). Any other wrong or invalid answer is a finding and is
not re-run. Raw outputs of the re-run are saved the same way (`...\ev181\real-8000`).

## Steps
1. **Baselines (no code change).** On this branch before any edit (= current `main`, `47032d5`),
   DB `corpus-2026-11-16`: mock `eval_run.py --as-of 2026-10-29 --baseline
   D:\ALLPROJECTS\EDJ\cache\ev120-rev\freeze-1029\report.json --out D:\ALLPROJECTS\EDJ\cache\ev181\main-1029`
   and the same `--as-of 2026-11-16` (`main-1116`). Record PASS / recall / refusal and any
   difference from the freeze report (main moved since the freeze). Also note the numbers of
   `evals/baselines/corpus-2026-10-22/report.json` (older corpus, for information).
   A small diff script in `D:\ALLPROJECTS\EDJ\cache\ev181\` (not committed) compares two
   reports: changed chunk lists per question, firms per question, passages and characters.
2. **Merrill counted once** (firm key in `select()`), unit tests. Mock eval at fixed `--k 20`
   against `main-1029`: lists change only for questions naming Merrill (Q4, Q7, Q9, Q10, Q11,
   Q21-Q25, Q27, Q28, Q30); each change listed with its status.
3. **Budget plumbing, then the grid.**
   - 3a. Plumbing (committed): `budget(q)` with the swappable `BUDGET_RULE(n)`,
     `search(q, k=None)` -> `budget(q)`, `eval_run.py --k` default `None`, and per-question `k`,
     passage count and prompt characters in each JSON record and report row (unit tests in
     `tests/test_retrieval_budget.py` / `tests/test_eval_run.py`). Until 3b the rule is the
     fixed `K` (k = 20 for every n), so a mock eval with `--k` omitted must give the same chunk
     lists as step 2 (diff script: 0 changed lists).
   - 3b. Grid, mock, `--as-of 2026-10-29`, step 2 in place, `--k` omitted so each question's k
     comes from `budget(q)` (n = named covered firms; k for n = 2 / 3 / 5):
     - A: `max(20, 6n)` -> 20 / 20 / 30
     - B: `max(20, 7n)` -> 20 / 21 / 35
     - C: `max(20, 8n)` -> 20 / 24 / 40
     - D: `20 + 5(n - 1)` -> 25 / 30 / 40
     A scratch driver (not committed, `D:\ALLPROJECTS\EDJ\cache\ev181\grid.py`) sets
     `fts.BUDGET_RULE` to A..D and calls `eval_run.main([...])`, one run folder per rule.
     **Check the grid really changed k**, read from each report's per-question `k`: Q22 k =
     30 / 35 / 40 / 40 under A / B / C / D, Q7 k = 20 / 21 / 24 / 30, Q8 k = 20 / 20 / 20 / 25,
     Q1 and Q16 k = 20 under every rule; a report that does not show these is discarded.
     Pick the smallest rule that meets the acceptance items (0 forbidden, refusal 5/5 and 19/19,
     no REGRESSED, PASS >= 28, recall >= 0.629 / 0.460); ties go to fewer passages. If none
     meets them, stop and report the grid before going further.
4. **Per-firm sub-queries (try, keep only on a gain).** Each firm's pool query also uses that
   firm's own aliases / `segment_aliases` terms from `config/entities.yaml` **in the rank only**:
   they are added as rank probes, not to the match (`c.tsv @@ q.tsq` stays the question's words
   and synonyms), so a chunk that only names the firm does not enter the pool. Mock eval vs step
   3b: kept only with a gain and no REGRESSED; otherwise reverted and reported in the PR with its
   numbers.
5. Commit the chosen rule as `BUDGET_RULE`; spec + ADR-013 (consequences include: `THEME_K`
   stays 4, so tier 5 research's share in five-firm entity+theme questions Q10 / Q21 falls from
   1/5 to 1/8-1/10; Q21's theme slot is #190) + llm.py comment. `pytest -q`.
6. **Final mock evals**: `--as-of 2026-10-29` against the freeze report and against `main-1029`;
   `--as-of 2026-11-16` against `main-1116` (information); diff script for single-firm lists and
   prompt size (median / max passages and characters per question type: single-firm entity,
   multi-firm entity, entity+theme, theme, window). Reports in `D:\ALLPROJECTS\EDJ\cache\ev181\`.
7. **verify-cee** on the mock from this worktree (with `.env` copied and `CORPUS_SHARE_PATH`
   set): ask-answer, coverage, filters at least.
8. **Real calls last**: Q22, Q24, one run each (paid-call plan above). If one is
   `INVALID_OUTPUT` from truncation: `max_tokens` 4000 -> 8000 in `llm.py`, `pytest -q`, re-run
   only that question once.
9. `/finish-task`: PR "Closes #181" with before/after tables; the Merrill-only trap questions
   Q4, Q27, Q30 each listed with their chunk-list change next to their `expected_behavior` and
   eval status; the reviewer agent reviews and merges (`/tl-review`).

## Risks
- Pool exhaustion: at k = 30-40 a firm may run out of its `POOL_PER_GROUP` = 15 per document
  type or fall under FLOOR, so slots go to other firms; reported per question from the grid, not
  fixed here (FLOOR is #166).
- Merrill firm key changes the FLOOR base for BAC GWIM chunks (now MER's best): Q4 / Q27 / Q30
  may lose or gain BAC GWIM chunks; covered by refusal 19/19 and no REGRESSED, listed in the PR.
- Larger prompts: a five-firm answer may hit `max_tokens`; checked by the step-8 real calls
  (path (b)).
- No rule in the grid meets acceptance: stop after 3b and report.

## Acceptance
- [x] Linked questions Q10, Q11, Q22, Q23, Q24: mock eval on `corpus-2026-11-16`,
  `--as-of 2026-10-29`, baseline `D:\ALLPROJECTS\EDJ\cache\ev120-rev\freeze-1029\report.json`:
  0 forbidden hits; refusal 5/5 (gap) and 19/19 (all keyed); no question REGRESSED; PASS >= 28
  with Q22 and Q24 PASS; tier-1 document / passage recall >= 0.629 / 0.460. Same run against
  `main-1029` (current main): no REGRESSED.
- [x] All 30 as regression: the `--as-of 2026-11-16` run against `main-1116` reported (no
  REGRESSED expected; any change explained).
- [x] Single-firm questions (Q1-Q3, Q5, Q6, Q13-Q15, Q19, Q26, Q29): diff script shows 0 changed
  chunk lists vs `main-1029`. Merrill-only questions (Q4, Q27, Q30) may change through the
  Merrill rule; each change listed with its eval status. Theme-only questions (Q16-Q18, Q20)
  unchanged (k stays 20).
- [x] `pytest -q tests/test_retrieval_budget.py`: Merrill counted once (MER + BAC-GWIM one
  share, the other four firms keep theirs); parent-named case; `budget()` rule.
- [x] Prompt size: median and max passages and characters per question type, before vs after,
  in the PR (multi-firm growth stated as a number).
- [x] Step 4: kept with its own eval delta (no REGRESSED) or reported and dropped.
- [x] `pytest -q` passes; verify-cee PASS (ask-answer, coverage, filters at least).
- [x] `specs/retrieval.md` states the budget rule and Merrill counted once; ADR-013 in
  `docs/DECISIONS.md`.
- [x] Grid (step 3b): each rule's report shows the expected per-question k (Q22 30/35/40/40,
  Q7 20/21/24/30, Q8 20/20/20/25, Q1 and Q16 20); the grid table and the chosen rule are in the
  PR and ADR-013.
- [x] Real calls: 2 (Q22, Q24, one run each), model and outcome reported; raw outputs saved.
- [x] Truncation path: either neither Q22 nor Q24 is `INVALID_OUTPUT` from truncation
  (`max_tokens` stays 4000), or `max_tokens` = 8000 and the re-run of that question (at most 2
  more calls, at most 4 in total) returns a valid answer; raw outputs of both runs saved, the
  call count and outcome stated in the PR.

## Progress log
- 2026-11-17 18:07 - plan written. Worktree `D:\ALLPROJECTS\EDJ\wt-181`, branch
  `tl/181-retrieval-budget` from `origin/main` 47032d5; local DB = `corpus-2026-11-16`
  (`sync-db --check`). Note: the issue's `retrieve()` is `search()` in `fts.py`; the k=40
  diagnostic is in `D:\ALLPROJECTS\EDJ\cache\ev120\freeze-1029-k40`.
- 2026-11-17 18:40 - plan revised after review (issuecomment-6964864433): budget plumbing moved
  before the grid (step 3a) and the grid checks per-question k from the reports (3b);
  `max_tokens` path (b) chosen (8000, one re-run of a truncated Q22/Q24, at most 2 more calls);
  step 4 rank-only; Risks section; ADR-013 notes the `THEME_K` share; PR lists Q4/Q27/Q30.
- 2026-11-17 19:00 - plan approved by the reviewer agent
  ([issuecomment-6964907478](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/181#issuecomment-6964907478)).
- 2026-11-17 19:10 - step 1: `main-1029` = 26 PASS / 4 FAIL (Q15, Q19, Q22, Q24), recall 0.629 /
  0.460, refusal 5/5 and 19/19 (vs freeze: only Q21 IMPROVED, main moved). `main-1116` = 25 / 5
  (+Q26), recall 0.608 / 0.428. `evals/baselines/corpus-2026-10-22`: 25 PASS / 3 FAIL / 2 NE,
  0.809 / 0.347 on 9 keyed questions (older corpus, information only).
- 2026-11-17 19:25 - step 2 (Merrill counted once, k=20): 27 PASS; Q11, Q22, Q24 IMPROVED (Q22 back
  to PASS from the Merrill rule alone), no REGRESSED; lists change only for questions naming
  Merrill. Q4 drops two MER web pages below the merged floor (recall unchanged).
- 2026-11-17 19:35 - step 3a: plumbing with the fixed rule gives 0 changed lists vs step 2.
- 2026-11-17 19:55 - step 3b grid (vs freeze): every rule 28 PASS, 0 forbidden, refusal 5/5 and
  19/19, no REGRESSED (also none vs `main-1029`); docs / passages A 0.652 / 0.460, B 0.653 / 0.465,
  C 0.657 / 0.472, D 0.666 / 0.472; passages over 30 questions 648 / 684 / 722 / 748; k-check OK
  for every rule. Chosen: A, max(20, 6n).
- 2026-11-17 20:10 - step 4 (per-firm alias / segment terms in the rank only): 28 PASS, docs 0.660,
  passages 0.462; Q7, Q9, Q10, Q23, Q24 IMPROVED but Q11 REGRESSED (passages 2/10 -> 1/10).
  Dropped per the plan; `fts.py` back to step 3.
- 2026-11-17 20:30 - step 5-6: rule A committed, spec, ADR-013, llm.py comment; `pytest -q` 423
  passed. Final mock: 1029 vs freeze 28 PASS / 2 FAIL (Q15, Q19), 0.652 / 0.460, refusal 5/5 and
  19/19, IMPROVED Q11, Q21, Q22, Q24, no REGRESSED; 1116 vs `main-1116` 27 / 3 (Q15, Q19, Q26),
  0.631 / 0.428, no REGRESSED. Single-firm lists: 0 changed (Q1-Q3, Q5, Q6, Q13-Q15, Q19, Q26,
  Q29); theme-only unchanged; Merrill-only Q4 and Q27 changed, Q30 not.
- 2026-11-17 20:45 - step 7: verify-cee PASS, all 9 features (ask-answer, ask-progress,
  open-citation, gap-path, invalid-chunk, download-document, coverage, filters, feedback),
  `.verify-runs/20261117-182303-1ea4c94` in the worktree.
- 2026-11-17 20:55 - step 8: 2 real calls (claude-sonnet-5-5, prompt v2), `--as-of 2026-10-29`,
  raw outputs in `D:\ALLPROJECTS\EDJ\cache\ev181ealaw`. Q22 behavior `answer` (expected
  answer), 12 claims + 1 adjacent citing MS, SCHW, EDJ, RJF and BAC (GWIM) chunks; Q24
  `gap_with_adjacent` (expected), 2 claims + 4 adjacent, gap on advisor headcount stated. Both
  valid, not truncated: path (b) not used, `max_tokens` stays 4000, 0 extra calls.
