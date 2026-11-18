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
    `K = 20`; 2-5 firms -> the rule chosen in step 3. `search(q, k=None)`: `None` means
    `budget(q)`; an explicit `k` is honoured as today (tests and `--k` keep working).
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
- `src/cee/answer/llm.py` - the `max_tokens` comment only ("20 chunks (fts.K)"), and `max_tokens`
  itself only if step 7 shows a truncated answer (then planned in the Progress log first).
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
3. **Budget grid**, measured on the mock at `--as-of 2026-10-29` with step 2 in place (n = named
   firms; k for n = 2 / 3 / 5):
   - A: `max(20, 6n)` -> 20 / 20 / 30
   - B: `max(20, 7n)` -> 20 / 21 / 35
   - C: `max(20, 8n)` -> 20 / 24 / 40
   - D: `20 + 5(n - 1)` -> 25 / 30 / 40
   Implemented as a `--budget A|B|C|D` throwaway switch in a scratch driver (not committed) that
   sets `fts.budget`. Pick the smallest rule that meets the acceptance items (0 forbidden,
   refusal 5/5 and 19/19, no REGRESSED, PASS >= 28, recall >= 0.629 / 0.460); ties go to fewer
   passages. If none meets them, stop and report the grid before going further.
4. **Per-firm sub-queries (try, keep only on a gain).** Each firm's pool query also ORs that
   firm's own aliases / `segment_aliases` terms from `config/entities.yaml` as rank terms (not as
   a new filter). Mock eval vs step 3: kept only with a gain and no REGRESSED; otherwise reverted
   and reported in the PR with its numbers.
5. Wire the chosen rule as the default (`budget()`, `search(k=None)`, `eval_run.py --k` default),
   spec + ADR-013 + llm.py comment. `pytest -q`.
6. **Final mock evals**: `--as-of 2026-10-29` against the freeze report and against `main-1029`;
   `--as-of 2026-11-16` against `main-1116` (information); diff script for single-firm lists and
   prompt size (median / max passages and characters per question type: single-firm entity,
   multi-firm entity, entity+theme, theme, window). Reports in `D:\ALLPROJECTS\EDJ\cache\ev181\`.
7. **verify-cee** on the mock from this worktree (with `.env` copied and `CORPUS_SHARE_PATH`
   set): ask-answer, coverage, filters at least.
8. **Real calls last**: Q22, Q24, one run each (paid-call plan above).
9. `/finish-task`: PR "Closes #181" with before/after tables; the reviewer agent reviews and
   merges (`/tl-review`).

## Acceptance
- [ ] Linked questions Q10, Q11, Q22, Q23, Q24: mock eval on `corpus-2026-11-16`,
  `--as-of 2026-10-29`, baseline `D:\ALLPROJECTS\EDJ\cache\ev120-rev\freeze-1029\report.json`:
  0 forbidden hits; refusal 5/5 (gap) and 19/19 (all keyed); no question REGRESSED; PASS >= 28
  with Q22 and Q24 PASS; tier-1 document / passage recall >= 0.629 / 0.460. Same run against
  `main-1029` (current main): no REGRESSED.
- [ ] All 30 as regression: the `--as-of 2026-11-16` run against `main-1116` reported (no
  REGRESSED expected; any change explained).
- [ ] Single-firm questions (Q1-Q3, Q5, Q6, Q13-Q15, Q19, Q26, Q29): diff script shows 0 changed
  chunk lists vs `main-1029`. Merrill-only questions (Q4, Q27, Q30) may change through the
  Merrill rule; each change listed with its eval status. Theme-only questions (Q16-Q18, Q20)
  unchanged (k stays 20).
- [ ] `pytest -q tests/test_retrieval_budget.py`: Merrill counted once (MER + BAC-GWIM one
  share, the other four firms keep theirs); parent-named case; `budget()` rule.
- [ ] Prompt size: median and max passages and characters per question type, before vs after,
  in the PR (multi-firm growth stated as a number).
- [ ] Step 4: kept with its own eval delta (no REGRESSED) or reported and dropped.
- [ ] `pytest -q` passes; verify-cee PASS (ask-answer, coverage, filters at least).
- [ ] `specs/retrieval.md` states the budget rule and Merrill counted once; ADR-013 in
  `docs/DECISIONS.md`.
- [ ] Real calls: 2 (Q22, Q24, one run each), model and outcome reported; raw outputs saved.

## Progress log
- 2026-11-17 18:07 - plan written. Worktree `D:\ALLPROJECTS\EDJ\wt-181`, branch
  `tl/181-retrieval-budget` from `origin/main` 47032d5; local DB = `corpus-2026-11-16`
  (`sync-db --check`). Note: the issue's `retrieve()` is `search()` in `fts.py`; the k=40
  diagnostic is in `D:\ALLPROJECTS\EDJ\cache\ev120\freeze-1029-k40`.
