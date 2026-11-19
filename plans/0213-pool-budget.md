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
- Token count of a hit = `len(text) / 4` (the eval's `tokens_est`; every token figure in this
  plan, the PR and ADR-019 is this characters / 4 estimate, not a tokenizer count).
  `select(..., tokens=None)`: with `tokens` set, "full" = tokens of the kept list >= `tokens`
  (instead of `len(kept) >= k`); the loop and the answer-turn attach use one `full()` predicate
  (an answer turn is attached only while the list is not full). TRADE_KEEP still fires when
  `full()`, and in token mode it swaps only when the trade chunk is not longer than the pick it
  replaces (so the swap never raises the total). **Bound**: the list's tokens <= B + the tokens
  of the one chunk that crossed B (a question turn or its answer turn, or any pick); the largest
  crossing chunk is measured in step 3 and stated in ADR-019. Unit tests cover the bound,
  attach at the edge and a TRADE_KEEP fixture in token mode. The research part keeps its `THEME_K` = 4 passages and is
  selected first; its tokens are taken off the firm part's budget. Theme peers keep their 2
  passages per peer on top (ADR-018), not counted in the budget. Window questions use the same
  budget (their floor 0 and `WINDOW_MAX_PER_DOC` unchanged).
- `search(q, k=None, trace=None)`: `k=None` -> the configured rule (passages or tokens); an
  explicit `k` keeps passage mode with that k (tests, `eval_run.py --k`). `ask.py` and
  `smoke.py` call `search(query)` and are not changed.
- `eval_run.py` today always passes an explicit k (`search(query, k=budget(query) -
  peer_slots(query), ...)`, line ~563), which would force passage mode. Changed: without `--k`
  it calls `search(query, trace=trace)` (k=None, the app's path, the configured rule; the peers'
  slots stay inside `search()` as today); with `--k` it passes that k as today. The record's
  budget fields: passage mode `k` = `budget(q)` as today and `budget_tokens` = None; token mode
  `k` = None and `budget_tokens` = `budget_tokens(q)`; `prompt_size()` reports both, plus
  `fill` = `tokens_est / budget_tokens` (None in passage mode).
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
- `scripts/eval_run.py` - without `--k`, `search(query, trace=trace)` with k=None (see Settings);
  per question `search_s` (wall time of `search()`, `time.perf_counter`), `k` / `budget_tokens`
  / `fill` by mode; summary median / max of tokens per question and of `search_s`; meta
  `pool_per_group` and `token_budget` read from `fts`, so every grid report proves its settings;
  report.md header / summary line show them. Real runs: `cache_key()` also takes the answer
  call's `max_tokens` (`llm.MAX_TOKENS`), added to the hashed blob only when it is not 8000, so
  every cached output saved so far keeps its key and a run with another `max_tokens` never
  reuses an output made under 8000; the request meta saved with each raw output records
  `max_tokens`; an invalid record also saves the response's `stop_reason`
  (`ModelOutputError.stop_reason`).
- `tests/test_retrieval_budget.py` - defaults (`TOKEN_BUDGET=None`, pool 15) give the same
  `select()` output as the passage rule on a fixture pool; token mode stops at the budget with at
  most one chunk over; `budget_tokens()` 0/1/2/3/5 firms, Merrill once, unmapped, firm filter;
  research tokens taken off the firm part; peers still on top; explicit k keeps passage mode.
- `tests/test_eval_run.py` - with `fts.TOKEN_BUDGET` set and no `--k`, `eval_run.main` calls
  `search` with k=None (fake `search` records its arguments) and the record has `k` None,
  `budget_tokens` = `budget_tokens(q)` and `fill`; with `--k 20` it passes k=20; passage mode
  without `--k` keeps today's records; `search_s`, summary median / max, meta settings.
  Cache: `cache_key` is unchanged at `max_tokens` 8000 (same hash as today for a fixed input)
  and differs at 16000, so a `RealRunner` with a saved invalid output under 8000 makes a fresh
  (fake) call at 16000; an invalid record saves `stop_reason` and `max_tokens`. Fake clients
  only, 0 real calls.
- `specs/retrieval.md` (S1; waiver above) - budget in tokens, pool size setting, ADR-019 link.
- `docs/DECISIONS.md` - ADR-019 "Retrieval budget in tokens; pool size from a grid" (replaces
  ADR-013's passage count; Merrill counted once stays); ADR-013 status line notes the
  replacement. The PR is escalated to the TL for the ADR (expected).
- `src/cee/answer/llm.py` (S2; owner review waived, same #187 decision) - module constant
  `MAX_TOKENS = 8000` used by `anthropic_request()` (comment no longer says "20-30 chunks");
  `ModelOutputError` gets an optional `stop_reason`, set from the Anthropic response in both
  raise paths (no tool call; invalid tool input), so a cut-off output is identified from the
  saved record. `MAX_TOKENS` itself 8000 -> 16000 only on the truncation path in the paid-call
  plan. Tests: `tests/test_eval_run.py` (above) and the existing llm tests stay green.
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
One run each, no re-rolls. A wrong behavior is a finding: reported, not re-run. In particular, a
gap question (Q24, Q25, Q28-Q30) that does not return `gap_with_adjacent` fails the issue's real-run
acceptance item: the PR becomes "Part of #213" with that item open, or the TL picks the next
eligible grid point; either way any new call needs a new entry in this plan first.
Truncation path (only case with extra calls): a question whose output is `INVALID_OUTPUT`
because it was cut at `max_tokens` (saved `stop_reason` = `max_tokens`) -> `MAX_TOKENS` 8000 ->
16000 in `llm.py`, `pytest -q`, and **only that question run once more at 16000**
(`--questions <id> --max-calls 1`; at most 8 more calls, at most 16 in total). This is a planned
run with a different setting (CLAUDE.md "Paid API calls" step 2, planned here before the first
call), not a re-roll of the same request: the cache key includes `max_tokens` when it is not
8000, so the run gets a fresh call instead of the saved invalid output, and its request meta
says 16000. Raw outputs of that run go to its own `raw/` folder and
`...\ev213\real-16000`. Any other invalid or wrong output is a finding, not re-run.
If the pick is today's setting: 0 real calls (see the selection rule).

## Steps
1. **Plumbing, defaults = today.** `fts.py` settings (`TOKEN_BUDGET=None`, pool 15),
   `budget_tokens()`, `select(tokens=)` (attach / TRADE_KEEP respect the budget), `search()`
   wiring; `eval_run.py` k=None search without `--k`, `search_s`, `budget_tokens`, `fill`,
   medians, meta settings; `llm.py` `MAX_TOKENS` constant and `stop_reason`, `eval_run.py`
   cache key / request meta with `max_tokens`; unit tests. `pytest -q`.
2. **Defaults reproduce today.** Mock run at defaults:
   `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out D:\ALLPROJECTS\EDJ\cache\ev213\grid\p15-passages`.
   Diff script (scratch, `D:\ALLPROJECTS\EDJ\cache\ev213\diff.py`, not committed): final chunk ids
   30/30 identical, same order, to the baseline; any difference stops the work.
   This run is grid point (15, passage rule) and gives the "old" search times.
3. **Grid (mock).** Scratch driver `D:\ALLPROJECTS\EDJ\cache\ev213\grid.py` (not committed) sets
   `fts.POOL_PER_GROUP` and `fts.TOKEN_BUDGET` per point and calls `eval_run.main([...])` with the
   step-2 arguments, one folder per point `...\ev213\grid\p{15,30,50}-{passages,20k,30k,40k}`.
   **Check each report really used its point** (scratch check script, output kept for the PR):
   - meta `pool_per_group` / `token_budget` match the folder;
   - token points: `budget_tokens` = B for every question except Q10, Q11, Q15, Q21-Q25
     (1.5 x B); `k` None;
   - token points: every question's `tokens_est` <= `budget_tokens` + the tokens of its crossing
     chunk (the bound above), and `tokens_est` < `budget_tokens` only where `fill` < 1 because the
     eligible pool ran out (listed per point with the question IDs);
   - the (15, 20k) point's chunk lists differ from (15, passages) for at least the questions
     whose passage list was full (if they are identical, token mode did not run: stop and fix);
   - pool sizes at pool 30 / 50 >= those at 15 for every question;
   a report that fails a check is discarded and re-run after the fix.
   Grid table per point: PASS, forbidden, refusal gap / all, PASS->FAIL list, recall@pool /
   recall@final (all rows, tier 1), passages, total tokens, tokens per question median / max,
   search time per question median / max, eligibility, and the stage of each named missed passage.
4. **Pick** by the selection rule above; commit the pick as the defaults; `pytest -q`.
5. **Final mock run** at the pick from committed code (`--out .eval-runs/0213-final`): same numbers
   as its grid point (diff script: 30/30 identical chunk lists). Copy it to
   `evals/baselines/corpus-2026-11-17/` (if the pick differs from today).
6. **Docs.** ADR-019 (grid table, rule, pick, tokens median / max old vs new, search time,
   largest over-budget chunk, risks seen; states that tokens are characters / 4 estimates), ADR-013 status note, `specs/retrieval.md`, `llm.py` comment.
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
- **Prompt cost**: five-firm prompts at 40k reach ~60k estimated input tokens (characters / 4)
  per call (the tie-break to the
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
- [ ] Token mode really runs in the eval -> unit test (`search` called with k=None when
  `fts.TOKEN_BUDGET` is set and `--k` is not given) and the step-3 per-point checks (budget per
  question, over-budget bound, fill, (15, 20k) lists differ from (15, passages)).
- [ ] Truncation path ready before the first call -> tests: cache key unchanged at 8000 and
  different at 16000; a fresh fake call at 16000 despite a saved invalid output; `stop_reason`
  and `max_tokens` saved.
- [ ] Real run: Q24, Q25, Q28, Q29, Q30 each return `gap_with_adjacent` -> `.eval-runs/0213-real`
  report.json `behavior`; for Q7, Q15, Q20 the PR lists each named missed passage as "cited",
  "retrieved, not cited" or "not retrieved" (plus Q25's two); model, prompt version, call count
  (8, or up to 16 on the truncation path) and raw output folder stated. Skipped with 0 calls only
  if the pick is today's setting. A gap question without `gap_with_adjacent` -> finding: "Part of
  #213" or the TL picks the next eligible point (paid-call plan).
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
- 2026-11-18 23:55 - plan revised after review (issuecomment-7000843909): eval_run calls
  `search()` with k=None in rule mode (token mode really runs; test + step-3 checks: budget per
  question, over-budget bound, fill, 20k lists differ); truncation run gets a fresh call
  (`MAX_TOKENS` in the cache key when not 8000 and in the request meta, `stop_reason` saved;
  `llm.py` + `eval_run.py` + tests), stated as a planned run with another setting; attach and
  TRADE_KEEP respect the token budget (bound stated, TRADE_KEEP fixture test); gap-question
  finding handling; token figures are characters / 4 estimates.
