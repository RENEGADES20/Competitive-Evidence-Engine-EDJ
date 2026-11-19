# 0213 - Wider candidate pool and a token budget for the retrieved set (ADR-019)

Issue: #213    Role: TL    Spec: specs/retrieval.md (S1; owner review waived, TL decision
2026-11-17, #187), specs/answer-citations.md (S2, only for the `max_tokens` check below)

## Goal
Pool size (`POOL_PER_GROUP`) and the retrieved-set budget are settings, the budget is counted in
tokens (passage characters / 4, summed in `select()` order) with ADR-013's per-firm growth
expressed in tokens, and both values are picked from a 12-point mock grid by the rule written
below before any grid run. ADR-019 records the grid and the pick and replaces ADR-013's passage
count. Eight planned real runs at the pick check gap behavior and whether the Gate 4 missed
passages get cited. FTS only, `main`; no model, no new dependency.

## Facts (2026-11-18, read only)
- Base: `main` 2a22e23 (#210 merged in PR #218). DB `cee` = `corpus-2026-11-17`
  (`sync-db.ps1 -Check`: up to date; the vector extension / `chunk_embeddings` from #211 are
  ignored by fts).
- Baseline `evals/baselines/corpus-2026-11-17/report.json` (f0ebc30, mock, `--as-of 2026-11-17`,
  k by question): 29 PASS / 1 FAIL (Q19); all-rows recall@pool 0.686 / recall@final 0.484 (21
  questions with rows); tier 1 0.803 / 0.597 (17); refusal gap 5/5 (Q24, Q25, Q28-Q30), all keyed
  22/22; 0 forbidden; 675 passages, ~195,683 tokens; tokens per question median 6,001, max 9,544
  (Q11); passages median 20, max 30.
- #210: of the 8 Gate 4 missed passages only Q17 `BAC-TR-2026Q2#21` is "in pool, lost in
  select"; Q7 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q19 `EDJ-10K-2025#88`, Q20
  `FIDELITY-III-2025#0` and `UBS-NEXTGEN-2026#119`/`#13`, Q25 `RJF-PR-web-affiliation-options#1`
  and `MS-10K-2025#153` are "not in pool".
- `fts.py` today: `K = 20`, `PER_FIRM = 6`, `budget(q)` = 20 for 0-1 named firm, max(20, 6n)
  for n >= 2 (five firms: 30), plus `peer_slots(q)` (2 per theme peer, ADR-018);
  `POOL_PER_GROUP = 15` applies to every SQL pass (firm, research, on-theme, peers) through
  `row_number() OVER (PARTITION BY entity_id, doc_type)`; research part = `min(THEME_K=4, k)`
  passages first, firm part `k - len(research)`; `select()` loops `while len(kept) < k`, the
  answer-turn attach checks `len(kept) < k`, TRADE_KEEP fires when `len(kept) >= k`.
- Answer call (`src/cee/answer/llm.py`, `prompt.py` v3): `build_user_message()` passes every hit
  with no passage or character cap; Anthropic `max_tokens` = 8000 (output); one call per question
  (ADR-012 one-call flow); model `LLM_MODEL` default `claude-sonnet-5-5`. Input at the largest
  grid point (five firms, 1.5 x 40k = 60k tokens of passages + ~3k prompt) is well inside the
  model's context window, so the only limit a larger budget can hit is the 8000-token output
  (truncated tool input -> `INVALID_OUTPUT`). 16000 stays below the SDK's non-streaming guard
  (~21k `max_tokens`), so the fallback below needs no streaming change.
- The issue text says "keyed 10/10"; the key now covers 22 questions (#210), so the rule uses
  the current number, 22/22.

## Settings (design)
- `POOL_PER_GROUP` (int): unchanged meaning; grid {15, 30, 50}.
- `TOKEN_BUDGET` (int | None): None = today's passage rule (ADR-013, `budget(q)` passages);
  an int B = the token budget of a question naming 0 or 1 firm.
- ADR-013's growth in tokens: `budget_tokens(q)` = B for 0-1 named covered firm; for n >= 2,
  max(B, round(B x PER_FIRM / K x n)) = max(B, 0.3 x B x n). Same ratio as today (6 of 20 per
  firm): 2-3 firms keep B, the five get 1.5 x B (20k -> 30k, 30k -> 45k, 40k -> 60k). n counts as
  today (after the firm filter, Merrill once, unmapped firms none).
- Token count of a hit = `len(text) / 4` (the eval's `tokens_est`). `select(..., tokens=None)`:
  with `tokens` set, "full" = tokens of the kept list >= `tokens` (instead of `len(kept) >= k`);
  the loop, the answer-turn attach and TRADE_KEEP use one `full()` predicate, so the list ends
  at most one chunk over the budget. The research part keeps its `THEME_K` = 4 passages and is
  selected first; its tokens are taken off the firm part's budget. Theme peers keep their 2
  passages per peer on top (ADR-018), not counted in the budget. Window questions use the same
  budget (their floor 0 and `WINDOW_MAX_PER_DOC` unchanged).
- `search(q, k=None, trace=None)`: `k=None` -> the configured rule (passages or tokens); an
  explicit `k` keeps passage mode with that k (tests, `eval_run.py --k`). `ask.py` and
  `smoke.py` call `search(query)` and are not changed.
- FLOOR, FLOOR_BASE, MAX_PER_DOC, THEME_K, slot order, near-duplicate removal: unchanged (out of
  scope); a list that ends below its budget because the eligible pool runs out is reported
  (fill = tokens / budget per question), not fixed here.

## Selection rule (fixed before the grid)
Grid: POOL_PER_GROUP in {15, 30, 50} x budget in {passage rule (today), 20k, 30k, 40k} = 12
points, each a full mock run of all 30 questions, `--as-of 2026-11-17`, baseline
`evals/baselines/corpus-2026-11-17/report.json`.
A point is **eligible** when all of these hold:
1. refusal gap 5/5 (Q24, Q25, Q28, Q29, Q30);
2. every keyed question refusal-correct: 22/22;
3. 0 forbidden hits over the 30 questions;
4. no mock PASS -> FAIL against the baseline (Q19 is FAIL there already);
5. all-rows and tier-1 recall@pool and recall@final each >= the baseline (0.686 / 0.484,
   tier 1 0.803 / 0.597) (the issue's second acceptance item, applied before the pick).
**Pick**: among eligible points, the highest tier-1 recall@final (= tier-1 passage recall),
compared at 3 decimals as reported. Ties -> smaller budget (passage rule < 20k < 30k < 40k), then
smaller pool. The baseline point (15, passage rule) is eligible by construction, so a pick always
exists; if it is the pick, the defaults stay as today, ADR-019 records the grid and the settings,
and the real runs are skipped (no retrieval change to check; 0 calls).

## Files to change
- `src/cee/retrieve/fts.py` (S1; owner review waived, TL decision 2026-11-17, #187) -
  `TOKEN_BUDGET`, `budget_tokens(q)`, `hit_tokens(h)`, `select(..., tokens=None)` with the `full()`
  predicate, `search()` wiring (research tokens off the firm part), docstrings; committed values
  = the pick.
- `scripts/eval_run.py` - per question `search_s` (wall time of `search()`, `time.perf_counter`)
  and `budget_tokens` (None in passage mode); summary median / max of tokens per question and of
  `search_s`; meta `pool_per_group` and `token_budget` read from `fts`, so every grid report
  proves its settings; report.md header / summary line show them.
- `tests/test_retrieval_budget.py` - defaults (`TOKEN_BUDGET=None`, pool 15) give the same
  `select()` output as the passage rule on a fixture pool; token mode stops at the budget with at
  most one chunk over; `budget_tokens()` 0/1/2/3/5 firms, Merrill once, unmapped, firm filter;
  research tokens taken off the firm part; peers still on top; explicit k keeps passage mode.
- `tests/test_eval_run.py` - `search_s`, `budget_tokens`, summary median / max, meta settings.
- `specs/retrieval.md` (S1; waiver above) - budget in tokens, pool size setting, ADR-019 link.
- `docs/DECISIONS.md` - ADR-019 "Retrieval budget in tokens; pool size from a grid" (replaces
  ADR-013's passage count; Merrill counted once stays); ADR-013 status line notes the
  replacement. The PR is escalated to the TL for the ADR (expected).
- `src/cee/answer/llm.py` (S2; owner review waived, same #187 decision) - the `max_tokens`
  comment (it says "20-30 chunks"); `max_tokens` itself 8000 -> 16000 only on the truncation
  path in the paid-call plan.
- `evals/baselines/corpus-2026-11-17/report.json`, `report.md` - replaced by the final mock run
  at the pick (old one stays in git history at f0ebc30), so later work compares with the new
  default. Not replaced if the pick is today's setting.
- `plans/0213-pool-budget.md` (this file).
Not changed: `ask.py`, `smoke.py`, UI, prompt, `evals/expected_chunks.yaml`, README numbers.

## Paid-call plan (CLAUDE.md "Paid API calls"; TL pre-approval comment on #213, 2026-11-18)
Mock for everything that decides the change. Then, last, on finished code after every mock check
and verify-cee: **8 real runs, one each, 1 call each (one-call flow) = 8 calls**:
Q24, Q25, Q28, Q29, Q30 (gap behavior) and Q7, Q15, Q20 (missed passages). Model
`claude-sonnet-5-5`, prompt v3, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; .venv\Scripts\python.exe scripts\eval_run.py --real --max-calls 8
--questions Q7,Q15,Q20,Q24,Q25,Q28,Q29,Q30 --as-of 2026-11-17 --baseline
evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0213-real`; raw outputs in the
run's `raw/` folder, copied to `D:\ALLPROJECTS\EDJ\cache\ev213\real`.
Why the mock cannot show it: the mock always answers from the first 3 hits and never chooses a
behavior, so it cannot show (a) whether a gap question still answers `gap_with_adjacent` when 2-3x
more passages, some adjacent to the gap (e.g. compensation expense next to payout grids, GWIM
next to Merrill), are in its context, nor (b) whether a passage now in the retrieved set (Q7
`MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q20 `FIDELITY-III-2025#0` / `UBS-NEXTGEN-2026#119` /
`#13`, and Q25's `RJF-PR-web-affiliation-options#1` / `MS-10K-2025#153`) is actually cited in a
claim; mock eval only shows it was retrieved.
One run each, no re-rolls. A wrong behavior is a finding: reported, not re-run.
Truncation path (only case with extra calls): a question whose output is `INVALID_OUTPUT`
because it was cut at `max_tokens` (stop reason `max_tokens` in the error, or a tool input that
is missing required fields in the saved raw payload) -> `max_tokens` 8000 -> 16000 in `llm.py`,
`pytest -q`, and **only that question re-run once** (`--max-calls 1`; at most 8 more calls, at
most 16 in total). Raw outputs of the re-run saved the same way (`...\ev213\real-16000`).
If the pick is today's setting: 0 real calls (see the selection rule).

## Steps
1. **Plumbing, defaults = today.** `fts.py` settings (`TOKEN_BUDGET=None`, pool 15),
   `budget_tokens()`, `select(tokens=)`, `search()` wiring; `eval_run.py` `search_s`,
   `budget_tokens`, medians, meta settings; unit tests. `pytest -q`.
2. **Defaults reproduce today.** Mock run at defaults:
   `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out D:\ALLPROJECTS\EDJ\cache\ev213\grid\p15-passages`.
   Diff script (scratch, `D:\ALLPROJECTS\EDJ\cache\ev213\diff.py`, not committed): final chunk ids
   30/30 identical, same order, to the baseline; any difference stops the work.
   This run is grid point (15, passage rule) and gives the "old" search times.
3. **Grid (mock).** Scratch driver `D:\ALLPROJECTS\EDJ\cache\ev213\grid.py` (not committed) sets
   `fts.POOL_PER_GROUP` and `fts.TOKEN_BUDGET` per point and calls `eval_run.main([...])` with the
   step-2 arguments, one folder per point `...\ev213\grid\p{15,30,50}-{passages,20k,30k,40k}`.
   **Check each report really used its point**: meta `pool_per_group` / `token_budget` match the
   folder; in token points every question's `budget_tokens` = B for 0-1 firm and 1.5 x B for the
   five-firm questions (Q10, Q11, Q15, Q21-Q25); pool sizes at pool 30/50 >= those at 15; a
   report that does not show this is discarded and re-run.
   Grid table per point: PASS, forbidden, refusal gap / all, PASS->FAIL list, recall@pool /
   recall@final (all rows, tier 1), passages, total tokens, tokens per question median / max,
   search time per question median / max, eligibility, and the stage of each named missed passage.
4. **Pick** by the selection rule above; commit the pick as the defaults; `pytest -q`.
5. **Final mock run** at the pick from committed code (`--out .eval-runs/0213-final`): same numbers
   as its grid point (diff script: 30/30 identical chunk lists). Copy it to
   `evals/baselines/corpus-2026-11-17/` (if the pick differs from today).
6. **Docs.** ADR-019 (grid table, rule, pick, tokens median / max old vs new, search time,
   risks seen), ADR-013 status note, `specs/retrieval.md`, `llm.py` comment.
7. **verify-cee**: `.venv\Scripts\python.exe scripts\verify_cee.py run`, all features PASS
   (PYTHONPATH = this checkout's `src`). No user feature recipe change (the Ask page shows more
   passages, same features).
8. **Real runs last** (paid-call plan). Per question: behavior vs expected; for Q7, Q15, Q20 (and
   Q25) which named missed passages are in the retrieved set and which are cited in a claim
   (`chunk_ids` of claims / adjacent in report.json). Truncation path only if needed.
9. `/finish-task`: PR "Closes #213" with the grid table, the pick, before/after tables, tokens
   median / max old vs new, search time, real-run table and call count; the reviewer agent
   escalates to the TL for ADR-019.

## Risks
- **Rank floor**: FLOOR is relative to a firm's 2nd-best chunk. A wider pool cannot change the
  base (the two best chunks of a firm are always in its top 15 per type) but lets many more
  chunks above 0.3 x base into the eligible lists; with a token budget they fill more slots, so
  a firm with many mid-rank chunks (5-firm questions) can take more of the list. Seen per question
  in the grid (passages per firm), not tuned here.
- **Slot order**: more unused documents inside the 0.9 newest band (ADR-016) can swap an older
  higher-ranked document for a newer one; TRADE_KEEP fires on "full", now in tokens.
- **Gap questions** (Q24, Q25, Q28-Q30) get more adjacent passages: mock refusal checks
  (`must_not_return`) in the rule; real behavior in step 8.
- **Search cost**: `rank_sql` runs one fixed count query per question (IDF over all chunks;
  independent of pool size); the main SQL ranks every matched row whatever the pool, so a larger
  pool costs more rows returned and more `select()` work (shingles per candidate, near-duplicate
  checks against every kept chunk, which grow with the budget). Search time median / max per point
  is in the grid table; a large slowdown is reported in the PR and ADR-019.
- **Output limit**: more passages -> longer grid answers for five-firm questions (Q15, Q24, Q25):
  truncation path above.
- **Prompt cost**: five-firm prompts at 40k reach ~60k input tokens per call (the tie-break to the
  smaller budget limits this).
- Grid points cannot fill their budget where the eligible pool runs out (MAX_PER_DOC, floor):
  fill reported, not fixed.

## Acceptance
- [ ] Grid report with all 12 points and the selection rule's pick -> step 3 table (12 rows, each
  report's meta settings checked) and the pick by the rule, in the PR and ADR-019.
- [ ] At the pick, recall@pool and recall@final not lower than the #210 baseline -> final run
  (`.eval-runs/0213-final/report.json`): all rows >= 0.686 / 0.484, tier 1 >= 0.803 / 0.597.
- [ ] Defaults reproduce today -> step 2 diff: 30/30 identical chunk lists vs the baseline; unit
  test: passage mode `select()` output unchanged.
- [ ] Real run: Q24, Q25, Q28, Q29, Q30 each return `gap_with_adjacent` -> `.eval-runs/0213-real`
  report.json `behavior`; for Q7, Q15, Q20 the PR lists each named missed passage as "cited",
  "retrieved, not cited" or "not retrieved" (plus Q25's two); model, prompt version, call count
  (8, or up to 16 on the truncation path) and raw output folder stated. Skipped with 0 calls only
  if the pick is today's setting.
- [ ] Tokens per question (median, max) for the old setting (6,001 / 9,544) and the new one, and
  search time median / max for both -> from the step 2 and step 5 reports, in the PR and ADR-019.
- [ ] Mock at the pick: refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS->FAIL (Q24, Q25,
  Q28-Q30 refusal_ok True; linked Q7, Q15, Q20 status and recall@final reported).
- [ ] ADR-019 written in `docs/DECISIONS.md`, ADR-013 marked as replaced in its passage count;
  `specs/retrieval.md` updated (the reviewer escalates the PR to the TL for the merge).
- [ ] `pytest -q` passes; `python scripts/verify_cee.py run` all features PASS.

## Progress log
- 2026-11-18 23:36 - plan written. Branch `tl/213-pool-budget` from `main` 2a22e23; DB
  `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`).
