# 0249 - exp/hybrid: sync the W11 pipeline, hybrid search through search_fn, drop the search_parts copy

Issue: #249    Role: TL    Spec: specs/retrieval.md
Base branch: `exp/hybrid` (ADR-011: model-based work stays off `main`). Branch `tl/249-hybrid-sync`
from `origin/exp/hybrid` be68334; the PR targets `exp/hybrid`, never `main`.

## Goal
`exp/hybrid` has `main`'s full W11 pipeline (#245 decompose, #246 map, #247 reduce parts 1-3,
#248 eval/cost/stages; `origin/main` e15ccf8) through one merge commit. The hybrid modes search a
plan through `main`'s own loop, `planner.search_subquestions(..., search_fn, research_fn)`, with
`hybrid.search` as the search function; the copy `hybrid.search_parts`, its parity tests and its
source-hash pin are gone. Plans do not depend on the retrieval mode, so #250 can share them across
fts (on `main`) and hybrid-norerank (here) with `--reuse-plans`. 0 real calls.

## Inputs read
Issue #249 and both TL comments (#245 note: honour `Query.on_theme_only` and the floor across
competitors; the sync is deferred to this issue), PR #262's "Notes for #249", `CLAUDE.md`,
`PLANS.md`, `.claude/commands/tl-run.md`, `plans/0211-hybrid-retest.md` (sync rule, hybrid file list),
`plans/0240-hybrid-parity.md`. On `origin/main`: `src/cee/retrieve/planner.py`
(`search_subquestions`, `_extra_passes`, `_competitor_floor`, `corrective_search`),
`src/cee/retrieve/fts.py` (`search(..., text=)`, `on_theme_only`, `period_range`, `exclude_ids`,
`fetch_pinned`), `src/cee/ask.py`, `src/cee/answer/extract.py` (`run_map(..., search_fn=)`),
`scripts/eval_run.py`. On `exp/hybrid`: `src/cee/retrieve/modes.py`, `hybrid.py`, `tests/test_hybrid.py`,
`tests/test_search_mode.py`.

State checked (2026-11-20): merge base `eac02d1`. A trial merge (aborted) conflicts in 8 files:
`.claude/skills/verify-cee/features/ask-progress.md`, `scripts/eval_run.py`, `scripts/verify_cee.py`,
`specs/retrieval.md`, `src/cee/ask.py`, `src/cee/config.py`, `tests/test_ask_page_trace.py`,
`tests/test_ask_progress.py`. Docker `cee-db`: 21,161 chunks, 21,161 rows in `chunk_embeddings`
(bge-small). The source-hash pin is `tests/test_hybrid.py::test_t3b_planner_search_parts_source_is_pinned`.

## What the seam needs from hybrid (found while reading)
`main`'s loop calls `search_fn(sub_q, trace=, tokens=, exclude=, research=False, peers=False, text=sq.text)`,
`research_fn(q, trace=)`, `period_fn(sub_q, k=PERIOD_K, research=False, peers=False, text=)` (default
`search_fn`) and `pin_fn(sub_q, ids)`. `hybrid.search` already takes every one of these keywords and
embeds `text` in the vector leg. Three gaps:
1. **`on_theme_only`** (competitor sub-questions, ADR-018): `hybrid.search` ignores it today. It must do
   what `fts.search` does when `q.on_theme_only and q.mode == "entity+theme" and q.themes`: the firm
   pass carries the on-theme filter in **both** legs (`part_where(q, "on_theme")` is already that
   where-clause), every kept chunk is `on_theme=True`, the separate on-theme pass is not run, and no
   answer turn is attached. The floor across the competitors of an aspect is `main`'s
   `_competitor_floor`, applied by the shared loop to `Hit.rank` (RRF score in hybrid-norerank).
2. **`pin_fn`**: `main` defaults it to a no-op when `search_fn is not fts.search` (for test fakes).
   Hybrid must pass `pin_fn=fts.fetch_pinned` explicitly, or it would silently lose the registered
   definition / population chunks (#247 part 2) and differ from fts for a reason that is not ranking.
3. **`period_range` / `exclude_ids`**: `hybrid.hard_filters` builds its filters from `fts.filters_sql(q)`,
   which on `main` now adds both, so both legs get them with no hybrid change. A test pins it.

Unsure (written down for the reviewer): `_competitor_floor` uses `fts.FLOOR` (0.3) x the 2nd-best rank.
On RRF scores that is a relative cut like hybrid's own (0.4); on `hybrid`'s sigmoid scores it is a
ratio of probabilities (hybrid.py notes "a sigmoid is not a ratio"). I keep `main`'s loop unchanged
(the point of the issue) and only record this; `hybrid` (rerank) is the reference mode and not in #250.

## Files to change
Only hybrid files may differ from `origin/main` afterwards (the list in `plans/0211-hybrid-retest.md`
plus `plans/0212-*`, `0240-*`, this plan and `evals/hybrid-eval/`).
- Merge commit: `origin/main` into `tl/249-hybrid-sync`, conflicts resolved by the 0211 rule.
- `src/cee/retrieve/modes.py` - `search(q, k=None, mode=None, trace=None, plan=None, part_pools=None, as_of=None)`:
  with a plan and k None, fts -> `planner.search_subquestions(q, plan, trace=, part_pools=, as_of=)`
  exactly as `main` (default functions); hybrid modes -> check vectors once, then
  `planner.search_subquestions(q, plan, search_fn=partial(hybrid.search, rerank=..., checked=True),
  research_fn=partial(hybrid.research_pass, rerank=..., checked=True), pin_fn=fts.fetch_pinned, ...)`.
  New `search_fn(mode)`: None for fts (so `run_map` keeps `main`'s default), the same hybrid partial
  otherwise, for the map's corrective re-search. `plan_for` stays only if a caller is left; otherwise
  it goes with its test. Docstring: the seam, not the copy.
- `src/cee/retrieve/hybrid.py` - remove `search_parts` (and `peer_pass` if no caller is left; `main`'s
  loop has no peer pass, competitors are sub-questions); `search()` honours `on_theme_only` (gap 1);
  module docstring updated.
- `src/cee/ask.py` - `main`'s version plus the mode hunks: `mode` param, `resolve_mode`,
  `modes.search(query, mode=, plan=, as_of=)` in place of `search_subquestions`, `map_step` passes
  `search_fn=modes.search_fn(mode)` to `run_map`, `Result.retrieval_mode`, `retrieval_mode` in the log,
  the mode suffix on the search trace line. The plan call stays `main`'s (`plan_question`), mode-free.
- `src/cee/config.py` - `main`'s version plus `retrieval_mode`. `planner_max_parts` goes (`main`
  dropped it with the plan-v3 "no cap" rule, #245).
- `scripts/eval_run.py` - `main`'s version plus the mode hunks (`--mode`, search timing and warm-up,
  duplicate measure, `--floor`/`--max-per-doc` grid, `run_bank`); search goes through
  `modes.search(query, ..., mode=, plan=, as_of=)`; `RealRunner.map` and the mock `run_map` get
  `search_fn=modes.search_fn(mode)`. Plan cache: `main`'s `plan_cache_key` / `plan_path` (no cap),
  `RealRunner(cache_dir=CACHE)`, `plans_only` as an attribute, `main`'s `SavedPlans`/`missing_plans`;
  the branch's capped duplicates go (PR #262 notes). Test names T9/T10 kept as on `main`.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md`, `specs/retrieval.md`,
  `docs/RUN.md` - `main`'s text plus the branch's mode / hybrid hunks; the "Retrieval modes" section of
  the spec and the RUN.md "Hybrid retrieval" section describe the `search_fn` seam and the shared
  plans (`--reuse-plans`, `--naive-tz`), PowerShell and bash blocks.
- Tests:
  - `tests/test_hybrid.py`: remove T3 parity (`test_t3_hybrid_search_parts_mirrors_planner_search_parts`,
    `test_t3_passage_mode_and_not_searchable_branches`) and `test_t3b_planner_search_parts_source_is_pinned`;
    move the vectors-once and the DB hard-filter tests from `search_parts` to `modes.search(plan=...)`;
    new tests for gap 1 (both legs carry the on-theme filter, no answer turn, every hit `on_theme`;
    unchanged when `on_theme_only` is False or the mode is not entity+theme) and gap 3
    (`period_range` / `exclude_ids` reach both legs).
  - `tests/test_search_mode.py`: fts with a plan calls `planner.search_subquestions` with the default
    functions; hybrid with a plan calls it with hybrid `search_fn` / `research_fn` (rerank by mode)
    and `pin_fn=fts.fetch_pinned`; `search_fn(mode)`.
  - `tests/test_eval_run.py`, `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`: `main`'s
    versions plus the mode tests; one test that hybrid-norerank's `run_map` gets the hybrid `search_fn`.
- Evidence: `evals/hybrid-eval/corpus-<snapshot>/mock-w11/` (report.md, summary.json, both report.json).
  The `main` fts run is kept outside the repo in `D:\ALLPROJECTS\EDJ\cache\ev249`.
Byte-equal to `origin/main` afterwards: `src/cee/retrieve/planner.py`, `fts.py`, `src/cee/answer/*`,
`config/`, `evals/expected_chunks.yaml`, `evals/questions.yaml`.

## Steps
1. **Merge.** `git merge --no-ff origin/main`; resolve the 8 conflicts by the 0211 rule (start from
   `main`, re-apply only the mode hunks); take `main` for every non-hybrid file. Commit the merge.
   Check: `git diff origin/main --stat` lists only hybrid files; `git diff origin/main --
   src/cee/retrieve/planner.py src/cee/retrieve/fts.py src/cee/answer config evals/expected_chunks.yaml
   evals/questions.yaml` is empty. pytest; failures caused only by `search_parts` are fixed in step 2.
2. **Seam.** `modes.search` / `modes.search_fn` as above; `ask.py` and `eval_run.py` route search and
   `run_map` through them; remove `hybrid.search_parts`, the parity tests and the hash pin.
   Check: `git grep -n search_parts -- src scripts tests` finds nothing.
3. **`on_theme_only`** in `hybrid.search` (gap 1) and the gap 1 / gap 3 tests.
4. **Tests.** `pytest` with `PYTHONPATH=<wt>\src`, `CEE_VECTORS=on`,
   `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed` (DB tests on `cee-db`), and once with
   vectors off (the vectors-optional tests).
5. **fts parity, mock, 0 calls.** The DB snapshot is checked with `scripts/sync-db.ps1 -Check`. The same
   `eval_run.py` mock command (fts, full bank Q1-Q35, `--as-of 2026-11-17`) on a detached worktree at
   `origin/main` and on this branch. A one-off scratch script (not committed) compares per question:
   ordered chunk lists, statuses, plan, map behavior, answer text. Expected: identical on 35/35.
6. **hybrid-norerank, mock, 0 calls.** The same command with `--mode hybrid-norerank` on this branch.
   Same plans by construction (rule plans on mock; `plan_path` has no mode in its key; T9 test).
   Reported against the fts run: refusal checks, keyed checks, PASS/FAIL, recall@final and the
   per-question chunk-list differences; via `scripts/eval_compare.py --run` if it still reads the W11
   records, otherwise from both report.json files (noted). No decision is taken here; #250 decides.
   `hybrid` (rerank) is covered by tests only.
7. **verify-cee** on this branch: search-mode (Smart search) and ask-progress in hybrid-norerank (the 9
   W11 stages, "Searching N sub-questions"), plus ask-answer in fts.
8. `/finish-task`: PR into `exp/hybrid`, `Closes #249`, `gh pr checks` green.

## Acceptance
- [ ] Linked questions Q1-Q30 (bank Q1-Q35 run): fts mock on this branch identical to `main` (chunk
      lists, statuses, plans, map behavior, answers) -> 30/30 (35/35).
- [ ] hybrid-norerank mock runs on all questions with 0 calls; refusal and keyed checks and the
      per-question differences against fts on the same plans are in the evidence report.
- [ ] Hybrid modes use the shared loop: `test_search_mode.py` shows `search_subquestions` called with
      hybrid `search_fn` / `research_fn` and `pin_fn=fts.fetch_pinned`; `run_map` gets the hybrid
      `search_fn`; `git grep search_parts -- src scripts tests` is empty; no source-hash pin left.
- [ ] `hybrid.search` honours `on_theme_only` (tests); `period_range` / `exclude_ids` reach both legs (test).
- [ ] Plans do not depend on the mode: `test_plan_cache_is_shared_by_every_retrieval_mode`,
      `test_reuse_plans_with_real_never_calls_the_planner`, `test_reuse_plans_in_a_mock_run_reads_the_saved_plan` pass.
- [ ] `git diff origin/main --stat` lists only hybrid files; `planner.py`, `fts.py`, `src/cee/answer/` equal `main`.
- [ ] pytest green (vectors on and off), verify-cee (Smart search, ask-progress) PASS, `gh pr checks` green.
- [ ] 0 real calls.

## Progress log
- 2026-11-20 - plan written. Trial merge: 8 conflicts. Gaps found: `on_theme_only` in hybrid.search,
  explicit `pin_fn` for hybrid, competitor floor on RRF/sigmoid ranks (recorded, loop kept as `main`).
