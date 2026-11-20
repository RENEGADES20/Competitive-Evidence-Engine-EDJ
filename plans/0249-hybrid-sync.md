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

**Known difference: the competitor floor is close to a no-op in hybrid-norerank** (review round 1,
blocking 1). `_competitor_floor` cuts every competitor sub-question's hits of one aspect at `fts.FLOOR`
(0.3) x the 2nd-best `Hit.rank` across those competitors. `hybrid.candidates` fuses per quota firm
(`_per_firm`) and a competitor sub-question searches one firm, so hybrid-norerank's RRF score depends
only on a chunk's rank inside its own firm, not on how well its text matches: every competitor's best
chunk scores about 2/61 = 0.033, the floor is about 0.0098, and any chunk at rank 41 or better in one
leg passes (1/101 = 0.0099). The hits that reach the floor are already the top few after `select()`
under the sub-question budget, so the floor almost never fires; `corrective_search` reuses
`plan.competitor_floor` and has the same problem. In fts the floor compares `ts_rank` across firms and
does fire (ADR-018's example: Merrill's advisor-ranking chunks are cut). This is not "a relative cut
like hybrid's own 0.4": that one is per firm, and ADR-018 rejects a per-firm floor for peers. On
`hybrid` (rerank) the cut is a ratio of sigmoid scores, also not comparable to fts.
Effect on #250: hybrid-norerank can keep competitor chunks that fts drops, so a disabled ADR-018
safeguard would be credited or blamed on "hybrid". This issue does **not** fix it (a fix changes
`hybrid.search`'s rank semantics or `planner.py`, which must equal `main`). It **measures** it at 0
calls (step 6) and records it as a known #250 difference. TL ruling (2026-11-20): the numbers go to
the TL before the PR is marked ready; the TL decides on #250 whether to accept them as part of
"retrieval" or to fix them first in a follow-up issue before #250 (for example a cross-firm
comparable score for competitor queries).

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
  the branch's capped duplicates go (PR #262 notes). Test names T9/T10 kept as on `main`. Also kept
  (0240 sync rule NB9): `current_constants`' mode-aware hybrid keys.
- `scripts/eval_compare.py` - no conflict; kept as on the branch, including `--no-decision` and
  `--pool-note` (0240 NB9).
- `src/cee/app/views/ask_page.py` - auto-merged (hybrid file whose base moved); not edited by hand,
  checked by the verify-cee Smart search step.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md`, `specs/retrieval.md`,
  `docs/RUN.md` - `main`'s text plus the branch's mode / hybrid hunks; the "Retrieval modes" section of
  the spec and the RUN.md "Hybrid retrieval" section describe the `search_fn` seam and the shared
  plans (`--reuse-plans`, `--naive-tz`), PowerShell and bash blocks.
- Tests:
  - `tests/test_hybrid.py`: remove T3 parity (`test_t3_hybrid_search_parts_mirrors_planner_search_parts`,
    `test_t3_passage_mode_and_not_searchable_branches`) and `test_t3b_planner_search_parts_source_is_pinned`;
    move the vectors-once and the DB hard-filter tests from `search_parts` to `modes.search(plan=...)`;
    new tests for gap 1 (both legs carry the on-theme filter, no answer turn, every hit `on_theme`,
    `trace.on_theme` gets the firm pass ids as in fts; unchanged when `on_theme_only` is False or the
    mode is not entity+theme; in `hybrid` (rerank) every hit is exempt from `gate()` and is scored,
    pinned by a test or, if a test is not practical, by a code comment) and gap 3
    (`period_range` / `exclude_ids` reach both legs).
  - `tests/test_search_mode.py`: fts with a plan calls `planner.search_subquestions` with the default
    functions; hybrid with a plan calls it with hybrid `search_fn` / `research_fn` (rerank by mode)
    and `pin_fn=fts.fetch_pinned`; `search_fn(mode)`.
  - `tests/test_eval_run.py`, `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`: `main`'s
    versions plus the mode tests; one test that hybrid-norerank's `run_map` gets the hybrid `search_fn`.
- Evidence: `evals/hybrid-eval/corpus-<snapshot>/mock-w11/` (report.md, summary.json, both report.json,
  `fts-parity.md` with the parity script's 35 per-question rows, identical or not, and the competitor
  floor / pins tables of step 6).
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
   ordered chunk lists, statuses, plan, map behavior, answer text. Expected: identical on 35/35. Its
   per-question output (35 rows) is saved as `mock-w11/fts-parity.md`, so the claim is checkable
   without the script.
6. **hybrid-norerank, mock, 0 calls.** The same command with `--mode hybrid-norerank` on this branch.
   Same plans by construction (rule plans on mock; `plan_path` has no mode in its key; T9 test).
   Reported against the fts run: refusal checks, keyed checks, PASS/FAIL, recall@final and the
   per-question chunk-list differences; via `scripts/eval_compare.py --run` if it still reads the W11
   records, otherwise from both report.json files (noted). No decision is taken here; #250 decides.
   `hybrid` (rerank) is covered by tests only. Two more tables, 0 calls, from `plan.searched` in both
   report.json files:
   - **Competitor floor** (blocking 1): per question and competitor sub-question, fts vs
     hybrid-norerank: `floor_dropped` count, `floor_emptied`, and the competitor chunks that reach the
     map (passages per competitor sub-question after the floor, period and pin passes), plus
     `plan.competitor_floor` per aspect. Questions with no competitor sub-question are listed as such.
     If Q1-Q35 show no difference, the report says so with the counts.
   - **Pins** (gap 2 end to end): per sub-question, `pinned` and `pins_cut` in fts vs hybrid-norerank.
     Same plan means the same pins, apart from dedup against chunks already kept; any other
     difference is a defect.
   Floor table details (round 2 notes): per competitor sub-question the hit count before the floor
   (`passages` + `len(floor_dropped)`) next to the count after it, so "the floor did not fire" is
   told apart from "different hits"; and the map's corrective re-search hits on competitor
   sub-questions (`corrective_search` also cuts at `plan.competitor_floor`), fts vs hybrid-norerank,
   or a line stating that no corrective re-search ran on a competitor sub-question.
   The competitor floor table goes to the TL (TL ruling) before the PR is marked ready; the outcome
   and the TL decision are recorded in the evidence report and as a comment on #250.
7. **verify-cee** on this branch: search-mode (Smart search) and ask-progress in hybrid-norerank (the 9
   W11 stages, "Searching N sub-questions"), plus ask-answer in fts.
8. **Re-sync check** (blocking 2): `git fetch origin` before opening the PR and again before the merge.
   If `origin/main` has moved past `e15ccf8`, merge it again by the same rule (step 1) and re-run step 1's
   diff and byte-equality checks, step 4 (pytest), step 5 (fts parity) and step 6 (hybrid-norerank mock
   and its tables) on the new `main` SHA. A re-run step 6 sends the new competitor floor table to the
   TL again, and the #250 comment cites the final SHA's numbers.
9. `/finish-task`: PR into `exp/hybrid`, `Closes #249`, `gh pr checks` green. The PR body names the `main`
   SHA the parity was proved against; #250 runs fts on that same `main` SHA, or re-syncs first. The PR
   stays draft until the TL has the competitor floor numbers.

## Acceptance
- [x] Linked questions Q1-Q30 (bank Q1-Q35 run): fts mock on this branch identical to `main` (chunk
      lists, statuses, plans, map behavior, answers) -> 30/30 (35/35).
- [x] hybrid-norerank mock runs on all questions with 0 calls; refusal and keyed checks and the
      per-question differences against fts on the same plans are in the evidence report.
- [ ] Competitor floor measured at 0 calls: per question, fts vs hybrid-norerank `floor_dropped` /
      `floor_emptied` counts and competitor chunks reaching the map, in the evidence report; numbers
      given to the TL before the PR is marked ready; outcome and TL decision commented on #250.
- [x] `pinned` / `pins_cut` per sub-question equal in fts and hybrid-norerank (apart from dedup), in the
      evidence report.
- [ ] Re-sync: `git fetch` before the PR and before merge; if `origin/main` moved past e15ccf8, re-merged
      and steps 1, 4, 5, 6 re-run on the new SHA; the PR body names the `main` SHA of the parity proof.
- [x] Hybrid modes use the shared loop: `test_search_mode.py` shows `search_subquestions` called with
      hybrid `search_fn` / `research_fn` and `pin_fn=fts.fetch_pinned`; `run_map` gets the hybrid
      `search_fn`; `git grep search_parts -- src scripts tests` is empty; no source-hash pin left.
- [x] `hybrid.search` honours `on_theme_only` (tests); `period_range` / `exclude_ids` reach both legs (test).
- [x] Plans do not depend on the mode: `test_plan_cache_is_shared_by_every_retrieval_mode`,
      `test_reuse_plans_with_real_never_calls_the_planner`, `test_reuse_plans_in_a_mock_run_reads_the_saved_plan` pass.
- [x] `git diff origin/main --stat` lists only hybrid files; `planner.py`, `fts.py`, `src/cee/answer/` equal `main`.
- [ ] pytest green (vectors on and off), verify-cee (Smart search, ask-progress) PASS, `gh pr checks` green.
- [x] 0 real calls.

## Risks
- **`main` moves after the sync.** #247 part 4 (retrieval and reduce) may merge to `main` after this
  sync. Then `exp/hybrid` lags `main`, and #250 (fts on `main` vs hybrid-norerank here) would differ
  in pipeline, not only in retrieval. Mitigation: step 8's re-sync check, the `main` SHA named in the
  PR body, and #250 running fts on that SHA or re-syncing first.
- **Competitor floor in hybrid-norerank** (see "Known difference" above): measured here, decided by the
  TL on #250.
- **Large conflict in `eval_run.py`.** Mitigation: start from `main`'s file, re-apply only the listed
  mode hunks, and the 35/35 fts parity proves nothing else moved.

## Progress log
- 2026-11-20 - plan written. Trial merge: 8 conflicts. Gaps found: `on_theme_only` in hybrid.search,
  explicit `pin_fn` for hybrid, competitor floor on RRF/sigmoid ranks (recorded, loop kept as `main`).
- 2026-11-20 - plan review round 1 (RETURN). Blocking 1: the competitor-floor paragraph corrected (per-firm
  RRF makes the cross-competitor floor close to a no-op); step 6 measures floor_dropped / floor_emptied and
  competitor chunks reaching the map, fts vs hybrid-norerank, for the TL before the PR is ready (TL ruling).
  Blocking 2: re-sync rule added (step 8, acceptance, Risks). Non-blocking 1-5 adopted (trace and gate
  tests, NB9 hunks named, pins table, parity rows kept, ask_page.py named).
- 2026-11-20 - plan approved at f60fe35 (round 2). Notes adopted before code: a re-run floor table goes to
  the TL again; the floor table covers corrective re-search competitor hits (or states none ran); counts
  before and after the floor.
- 2026-11-20 - build at 388811e (merge of `origin/main` e15ccf8, fetched first: main unchanged). The
  merge commit carries the conflict resolution and the seam together (the 8 conflicts could not be
  resolved without it). `eval_run.py`: main's question loop moved into `run_bank()` (the branch's grid
  shape); `RealRunner` signature as main's (`cache_dir=CACHE`, `plans_only` attribute) plus a
  `retrieval_mode` attribute for the map's re-search. `modes.plan_for` and `hybrid.peer_pass` had no
  caller left and went with their tests. `test_eval_run.py`: main's file plus the branch's 13 mode tests,
  the warm-up counts and T9 now runs its second run in hybrid-norerank (names kept).
- pytest 1132 passed (vectors on, incl. the DB hybrid tests), 1128 passed + 4 skipped (vectors off).
- Mock 0 calls, as-of 2026-11-17, corpus-2026-11-19: fts identical to main on 35/35 (8 fields per
  question); hybrid-norerank PASS 31 vs 33, refusal gap 7/8 vs 8/8 (Q22, Q24: must-not chunk retrieved,
  not cited by the mock map), keyed 24/26 vs 26/26; plans 35/35 identical; pins 16/16 identical.
  Competitor floor (Q19 only): fts floor 8.8362 drops MER's 4 (emptied), 11 competitor passages to the map;
  hybrid-norerank floor 0.0097 drops 0, 22 to the map. Corrective re-search on competitors: 0 hits in both.
  Evidence `evals/hybrid-eval/corpus-2026-11-19/mock-w11/`. Floor table goes to the TL before ready.
- verify-cee `--mode hybrid`: search-mode, ask-progress, ask-answer, gap-path PASS
  (`.verify-runs/20261120-123125-388811e`). The app offers only `hybrid` (Smart search), not
  hybrid-norerank (#128), so ask-progress ran in `hybrid`; hybrid-norerank is covered by the mock eval.
  verify-cee `--mode fts`: search-mode, ask-progress, ask-answer PASS (`.verify-runs/20261120-123601-388811e`).
