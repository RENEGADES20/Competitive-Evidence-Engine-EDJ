# 0126 - Compare fts / hybrid-norerank / hybrid on the question bank; tune per mode

Issue: #126    Role: TL    Spec: specs/retrieval.md (S1 owns `fts.py` and the spec: S1 FYI), ADR-001, ADR-009
Branch: `tl/126-hybrid-eval` from `origin/exp/hybrid` 795056b -> PR into **`exp/hybrid`** (never `main`;
sponsor portability spec EJ-10, TL decision on #125)

## Goal
One committed report under `evals/` that compares three retrieval modes on the 30-question bank
(corpus-2026-10-29, `--as-of 2026-10-29`, mock only) and gives tuned constants per mode, chosen by a
rule fixed in this plan before any grid run:
1. `fts` - `main`'s keyword retrieval (as on `exp/hybrid`, with `synonym_only`);
2. `hybrid-norerank` - keyword + vector legs fused with RRF; the final order is the RRF score;
3. `hybrid` - #125 as merged: RRF decides only which candidates enter the pool; the final order is
   the cross-encoder score (the common industry setup).
The report is the input for the decision record in #127. No default mode changes anywhere.

## Facts checked before planning (2026-11-05, read-only)
- `origin/exp/hybrid` = 795056b (PR #158, #125). `src/cee/retrieve/hybrid.py`: legs per firm
  (`LEG_K` 100), RRF per firm (`RRF_K` 60), (firm, doc type) groups take turns into `RERANK_N` 50
  (research part `THEME_RERANK_N` 20), MiniLM-L-12 cross-encoder, `Hit.rank` = sigmoid, absolute
  `RERANK_FLOOR` 0, then `fts.select(pool, k, floor=0)` with `fts.MAX_PER_DOC` (3) and
  `fts.DUP_JACCARD` (0.6). Window questions: floor 0, `WINDOW_MAX_PER_DOC` 8; entity+theme research
  part: `THEME_MAX_PER_DOC` 2.
- `fts.select()` reads `FLOOR`, `MAX_PER_DOC`, `DUP_JACCARD` as module globals at call time; the
  relative floor is `rank >= FLOOR x the firm's best rank` (first hit seen per firm = best).
- `fts.search()` accepts `fts | hybrid`; anything else -> `ValueError`. `ask()` adds ` (<mode>)` to
  the search trace line for any mode other than `fts`. `Settings.retrieval_mode` is a free string.
- `scripts/eval_run.py --mode fts|hybrid` already records `search_s` per question, an untimed
  warm-up search (`warmup_s`, model loading) and the median, plus per-hit `ranks`.
- #125 reference numbers (`.eval-runs/`, plan `plans/0125-hybrid-retrieval.md` Progress log):
  | run | PASS/FAIL | tier-1 docs | passages | refusal gap / all keyed | median search |
  |---|---|---|---|---|---|
  | `p125r-fts-after` (fts, FLOOR 0.3, MAX_PER_DOC 3) | 28 / 2 | 0.796 | 0.402 | 5/5, 10/10 | 0.40 s |
  | `p125r-hybrid` (= `p125r-hybrid-f0`, RERANK_FLOOR 0) | 27 / 3 | 0.728 | 0.373 | 5/5, 10/10 | 10.2 s |
  Absolute `RERANK_FLOOR` 0.01 / 0.05 / 0.1 lost passage recall every time (0.339 / 0.323 / 0.310).
- Q29 in `hybrid` (`.eval-runs/p125r-diag/diag.json`): answer passages `MS-10K-2025#153` (pool
  rank 47, score 0.0000) and `#170` (pool rank 42, 0.0001) reach the 50-pool, but MiniLM scores the
  guarantee note `MS-10K-2025#702` ("likelihood of any payment ... is remote") 0.95, `#417` 0.90,
  `#128` 0.73; `MAX_PER_DOC` 3 gives the MS 10-K places to those three -> coverage 0, FAIL.
  `#702` is **not** on Q29's `must_not_return` list (`evals/expected_chunks.yaml`), so it does not
  count as a forbidden or misleading hit; Q29 fails on coverage only. The answer key is C1's and is
  not changed here.
- Q25: `SCHW-10K-2025#558` (executive compensation, must-not) no longer reaches the pool since the
  (firm, doc type) pool; hybrid refusal gap 5/5.
- Spec `specs/retrieval.md`: "Duplicate rate after dedupe: no two hits > 90% similar"; "Similarity
  measure for dedupe: trigram (pg_trgm) is simplest".
- Machine: 12 logical CPUs, Intel64 Family 6 Model 186; no GPU is used (onnxruntime CPU).
- Venvs: repo `.venv` has fastembed 0.9.1 (vectors venv); `D:\ALLPROJECTS\EDJ\wt-144\.venv` has
  none (core venv). DB `cee-db`: `chunk_embeddings` 17183 rows = `chunks`. All models cached in
  `D:\ALLPROJECTS\EDJ\cache\fastembed`; nothing to download.

## Disk and download rule (TL machine)
In the shell session only: `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`,
`TMP`/`TEMP=D:\ALLPROJECTS\EDJ\cache\tmp`, `PYTHONPATH=<checkout>\src` (log `cee.__file__` before
every eval). No download, no pip install. `.eval-runs/` is git-ignored; only the final report goes
into `evals/`.

## Design

### Modes
- `fts`: unchanged code path.
- `hybrid-norerank` (new): the **same candidates as `hybrid`** (same legs, RRF, (firm, doc type)
  pool of `RERANK_N` 50 / research `THEME_RERANK_N` 20), so the only difference between the two
  hybrid modes is the final order. `Hit.rank` = the chunk's RRF score; the pool is sorted by
  (-RRF, chunk_id); no cross-encoder is loaded or called (only the embedding model). Then the same
  floor and `select()` as below. Reusing the 50-pool keeps it a clean ablation of the reranker; a
  larger pool is a different experiment (open question 2).
- `hybrid`: #125 unchanged except that the floor below is applied to the pool before scoring.
- Dispatch: `fts.search(q, k, mode)` accepts `hybrid-norerank` behind the same vectors gate
  (`HybridUnavailable` before importing `hybrid`) and calls `hybrid.search(q, k, rerank=False)`.

### How the `FLOOR` grid {0.2, 0.3, 0.4} applies to each mode's score scale
`FLOOR` means "a chunk weaker than FLOOR x its firm's best match gets no slot". That ratio only
makes sense on a score where 0 means "no match" and bigger means "more evidence":
- `fts`: `ts_rank` is such a score -> `fts.FLOOR` as today (0.3 is the current value).
- `hybrid-norerank`: the RRF score per firm is such a score: `sum over legs 1/(60 + rank)`, best
  possible 2/61 = 0.0328 (rank 1 in both legs). FLOOR 0.3 keeps a chunk with RRF >= 0.0098, i.e.
  ranked in both legs, or in one leg only up to rank ~41; 0.2 -> one leg up to rank ~92; 0.4 -> one
  leg up to rank ~16. So the grid reads as "how much the two legs must agree", a sensible scale.
  Applied as `select(pool, k, floor=FLOOR)` on the RRF-ordered pool.
- `hybrid`: the cross-encoder sigmoid is **not** a ratio scale (#125: `select()`'s relative floor on
  it emptied the pool; MiniLM logits sit mostly below 0). So in this mode `FLOOR` is the same
  relative **RRF** floor as in `hybrid-norerank`, applied to the 50-pool **before** the rerank
  (candidates below FLOOR x the firm's best RRF score are not scored); `select()` keeps floor 0 and
  the absolute `RERANK_FLOOR` stays 0 (#125 grid 0.01-0.1 lost evidence each time; not re-run).
  Result: both hybrid modes see exactly the same candidate set for a given FLOOR, and differ only in
  the order (RRF vs cross-encoder) -> the reranker's effect is measured directly. This is a gate
  on an existing score, not a blend: the cross-encoder score alone decides the final order.
- Both hybrid modes also run FLOOR **0** (no gate = #125's merged behavior), because the hybrid
  modes have no prior value; `fts` keeps the issue's grid (its default 0.3 is in it).
- Inside a time window every mode keeps floor 0, as today (Q26: every document in the window is on
  topic). Entity+theme research part: same floor rule per group (research is its own group).

### `MAX_PER_DOC` grid {2, 3, 4}
Applied to the firm part of every mode (`fts.MAX_PER_DOC` in fts; per-mode constants in
`hybrid.py`). The window cap `WINDOW_MAX_PER_DOC` (8, time-window questions) and the research cap
`THEME_MAX_PER_DOC` (2, research part of entity+theme questions) stay unchanged in every mode and
are not tuned (out of the issue's grid; stated in the report); a test checks that setting the
per-mode `MAX_PER_DOC` leaves both caps in force.

Grid size: `fts` 3 x 3 = 9 runs; `hybrid-norerank` and `hybrid` 4 x 3 = 12 runs each; 33 runs of 30
questions. Estimated time: fts ~2 min, norerank ~15 min, hybrid ~60 min (about 10 s per question).

### Selection rule (fixed now, applied by code to each mode's grid)
1. **Eligible** grid points: forbidden hits 0 on all 30 questions; refusal accuracy on the gap
   questions (Q24, Q25, Q28, Q29, Q30) >= the `fts` reference run (fts at FLOOR 0.3, MAX_PER_DOC 3;
   5/5 expected); refusal accuracy over all keyed questions >= the fts reference (10/10 expected).
2. Among eligible points: highest **tier-1 passage recall** (3 decimals, as reported).
3. Ties, in order: higher tier-1 doc recall; more PASS; the mode's current default (fts 0.3/3,
   hybrid modes 0/3); higher FLOOR (fewer weak hits); smaller MAX_PER_DOC (more documents).
4. No eligible point: the mode gets no tuned constants (current defaults stay) and the report says
   the mode fails the refusal acceptance.
The rule is coded in `eval_run.py` (`choose()`), unit-tested on a hand-made grid, and the grid
summary prints why the winner won. Caveat stated in the report: tuned and scored on the same 30
questions (no held-out set), so small differences (one passage = ~0.02 recall) are not strong
evidence.

### Duplicate measure (`DUP_JACCARD`)
Per question, over every pair of final hits (firm and research parts together): (a) character
trigram similarity, the spec's suggested measure; (b) word 5-gram Jaccard, the measure `select()`
dedupes with. pg_trgm is **not installed** in `cee-db`, so (a) is a Python re-implementation of
pg_trgm's `similarity()`, and the report says so: text lower-cased; words = runs of
alphanumeric characters (everything else is a separator); each word padded with two spaces in front
and one behind; trigrams = every 3-character substring of a padded word, as a set; similarity =
shared trigrams / all distinct trigrams of both texts (0 when either set is empty). Report per run:
questions with a pair > 0.9, number of such pairs, max pair similarity, on both measures.
`select()` drops > 0.6 on (b) within a part, so (b) > 0.9 can only appear across the
firm/research parts.
`DUP_JACCARD` is **per mode for the hybrid modes only**: `hybrid.DUP_JACCARD = {"hybrid": 0.6,
"hybrid-norerank": 0.6}`, passed to `select()` through a new optional `dup_jaccard` argument
(default None = `fts.DUP_JACCARD`, so fts mode is untouched). **fts's `DUP_JACCARD` (0.6) is measured
and reported, never changed** (fts.py constants mirror `main`; S1/#127).
Rule (fixed now), per hybrid mode: keep 0.6 if the mode's chosen point has 0 pairs > 0.9 on (a). If
not, rerun that point with `DUP_JACCARD` 0.5 and 0.4 and take the highest value that gives 0 such
pairs without lowering tier-1 passage recall; if none does, keep 0.6 and list the pairs in the
report. For fts, any pair > 0.9 is reported as a finding only.

### Latency (CPU)
`search_s` per question as today; the warm-up search on the first question (loads the embedding
model and, in `hybrid`, the reranker; warms the DB cache) is excluded and reported as `warmup_s`.
Grid points after the first one in the same process are warm too. Summary adds p90 and max next
to the median; meta adds CPU (`platform.processor()`, `os.cpu_count()`) and the onnxruntime version
when loaded. Latency in the report comes from: `fts` - the chosen fts grid point's run (inside
`p126-grid-fts`, fts has no confirmation run since its defaults do not change); `hybrid-norerank`
and `hybrid` - the confirmation runs `p126-norerank` and `p126-hybrid` (step 7, one mode per
process, its own warm-up). Per-question times in the appendix.

### eval_run.py changes
- `--mode fts|hybrid|hybrid-norerank`.
- `--floor` and `--max-per-doc` (each one value or a comma list) and `--dup-jaccard` (one value):
  set the mode's constants for the run through one explicit mapping
  (fts: `fts.FLOOR`, `fts.MAX_PER_DOC`; hybrid modes: `hybrid.FLOOR[mode]`,
  `hybrid.MAX_PER_DOC[mode]`, `hybrid.DUP_JACCARD[mode]`), restored after each run.
  `--dup-jaccard` with `--mode fts` is refused (argparse error): fts's value is never changed. The values used go
  into `meta.constants` (always, also with no option, so every report says what it ran with).
- More than one combination = grid: one run folder per point (`<out>/f<floor>-m<max>/report.md|json`),
  model loaded once, then `<out>/grid.md` and `grid.json` with every point's summary and `choose()`'s
  pick and reason. One combination = today's single run, same folder layout as now.
- Per question `dup` (both measures); summary: duplicate counts, p90/max search time.
- No option given -> constants untouched: fts results identical to `p125r-fts-after` (gate below).

### hybrid.py changes
- `FLOOR = {"hybrid": 0.0, "hybrid-norerank": 0.0}`, `MAX_PER_DOC = {"hybrid": 3,
  "hybrid-norerank": 3}`, `DUP_JACCARD = {"hybrid": 0.6, "hybrid-norerank": 0.6}` (start = #125
  behavior; set to the chosen values in step 7). Window and research parts keep
  `WINDOW_MAX_PER_DOC` / `THEME_MAX_PER_DOC` as now.
- `candidates()` also returns the RRF score per chunk; `gate(ids, rrf, entity_of, floor)` drops
  chunks below floor x their firm's best RRF score in the pool (no-op at 0 or inside a window).
- `search(q, k, scorer=None, timings=None, rerank=True)`: `rerank=False` -> no `reranker()` call,
  `Hit.rank` = RRF score, pool sorted by (-RRF, chunk_id); `select(..., floor=0,
  max_per_doc=MAX_PER_DOC[mode], dup_jaccard=DUP_JACCARD[mode])` in both modes (the gate already
  applied the floor).

### Comparison report
`scripts/eval_compare.py` (new, small): reads the three modes' chosen `report.json` files and
`grid.json` files and writes `evals/hybrid-eval/corpus-2026-10-29/report.md` and `summary.json`:
- per mode at its chosen constants: PASS/FAIL per question (side by side, with PASS -> FAIL vs fts
  listed), tier-1 doc and passage recall, refusal accuracy (Q24, Q25, Q28, Q29, Q30 each, and all
  keyed), forbidden hits, duplicate measure, latency median / p90 / max and warm-up;
- the same at each mode's current default (fts 0.3/3, hybrid 0/3 = `p125r-hybrid`);
- the selection rule (verbatim) and every grid point (appendix);
- "Is the cross-encoder reliable on this financial text?" (input for #127): `hybrid` vs
  `hybrid-norerank` on the same candidates, per question; Q29's scores from `p125r-diag`
  (`#702` 0.95 vs `#153` 0.0000 / `#170` 0.0001), with the note that `#702` is not on Q29's
  must-not list (it changes only forbidden/misleading counts, not PASS; no answer-key change here);
  Q24's table passage (`MS-SUPP-2026Q2#37`, 0.22). Reported as evidence; no rule is added for Q29.
- no choice of a default mode: the report gives numbers; #127 records the decision.
The three chosen runs' `report.md`/`report.json` and the three `grid.md`/`grid.json` are copied
under `evals/hybrid-eval/corpus-2026-10-29/<mode>/`.

## Files to change (all reaching only `exp/hybrid`)
- `scripts/eval_run.py` - `--mode hybrid-norerank`, `--floor`/`--max-per-doc`/`--dup-jaccard`, grid
  runs, `choose()`, `meta.constants`, CPU meta, `dup` per question, p90/max search time.
- `scripts/eval_compare.py` (new) - the three-mode comparison report.
- `src/cee/retrieve/hybrid.py` - `rerank=False` path, RRF gate, per-mode `FLOOR`/`MAX_PER_DOC`/`DUP_JACCARD`.
- `src/cee/retrieve/fts.py` (**S1 reviews**) - `MODES` + dispatch for `hybrid-norerank` behind the
  vectors gate; `select()` gets an optional `dup_jaccard=None` argument (None = `DUP_JACCARD`, so
  every existing caller and fts mode behave as before); no constant changes.
- `src/cee/ask.py`, `src/cee/config.py` - docstring/comment only: mode list `fts | hybrid |
  hybrid-norerank`.
- Tests: `tests/test_hybrid.py` (norerank: no reranker call, RRF order, gate drops below FLOOR x
  firm best and keeps window questions, same candidates as rerank mode; `test_mode_switch` with the
  new mode; vectors off -> `HybridUnavailable` for `hybrid-norerank`, `hybrid` not imported;
  per-mode `MAX_PER_DOC` 2 and 4 leave the window cap 8 and research cap 2 in force; per-mode
  `DUP_JACCARD` reaches `select()` while `fts.DUP_JACCARD` stays 0.6; `select()` without
  `dup_jaccard` behaves as before),
  `tests/test_eval_run.py` (`--mode hybrid-norerank` accepted; constant mapping per mode and restore;
  no option = constants untouched; `--dup-jaccard` with `--mode fts` refused; grid writes one folder per point + `grid.json`; `choose()` on a
  hand-made grid incl. eligibility and every tie-break; trigram and 5-gram duplicate measure on
  hand-made texts), `tests/test_eval_compare.py` (new; report built from two tiny fake runs).
- `evals/hybrid-eval/corpus-2026-10-29/` (new) - `report.md`, `summary.json`, per-mode chosen runs
  and grids (as above).
- `specs/retrieval.md` (**S1 reviews**) - "Retrieval modes": add `hybrid-norerank`, the floor per mode, and
  a pointer to the report; the open question "When would hybrid search be justified?" stays for #127.
- `docs/RUN.md` - hybrid section: the third mode and the grid command (PowerShell + bash blocks).
- `.env.example` - `RETRIEVAL_MODE` comment lists the third value.
- `.claude/skills/verify-cee/features/ask-progress.md` - search line may end with ` (hybrid)` or
  ` (hybrid-norerank)`.
- Not changed: `fts.py` constants (`FLOOR`, `MAX_PER_DOC`, `DUP_JACCARD`, `WINDOW_MAX_PER_DOC`,
  `THEME_MAX_PER_DOC`: fts's tuned values and its duplicate measure are reported only; changing
  `main`'s fts is #127/S1), `evals/questions.yaml`,
  `evals/expected_chunks.yaml`, `docs/DECISIONS.md` (ADR is #127), DB, corpus, prompts, UI, `main`.

## Steps
1. Shell setup (rule above). `pytest -q` in both venvs on 795056b -> record counts (floor: core 304
   passed / 2 skipped, vectors 306 passed per #125). Fresh reference runs on 795056b, vectors venv,
   `CEE_VECTORS=on`: `eval_run.py --mode fts --as-of 2026-10-29 --out .eval-runs/p126-ref-fts` and
   `--mode hybrid --out .eval-runs/p126-ref-hybrid`; check chunk_ids equal `p125r-fts-after` /
   `p125r-hybrid` (30/30 each) so the DB and code are the #125 state. (`p125r-hybrid` ran at
  587109a, before the #158 squash 795056b; the fresh `p126-ref-*` runs on 795056b are the
  references every later gate compares against.)
2. Code: `hybrid.py` (norerank, gate, per-mode constants), `fts.py` dispatch, docstrings, tests.
   `pytest -q` both venvs.
3. Code: `eval_run.py` (options, grid, `choose()`, dup, latency summary), tests. Then the
   no-change gates: with no constant options, `--mode fts` (core venv, vectors off) and `--mode
   hybrid` (vectors venv) give chunk_ids identical to `p126-ref-fts` / `p126-ref-hybrid` on 30/30.
4. Grids (vectors venv, `CEE_VECTORS=on`, `--as-of 2026-10-29`, `--baseline
   .eval-runs/p126-ref-fts/report.json`, `--k 20`):
   `--mode fts --floor 0.2,0.3,0.4 --max-per-doc 2,3,4 --out .eval-runs/p126-grid-fts`;
   `--mode hybrid-norerank --floor 0,0.2,0.3,0.4 --max-per-doc 2,3,4 --out .eval-runs/p126-grid-norerank`;
   `--mode hybrid --floor 0,0.2,0.3,0.4 --max-per-doc 2,3,4 --out .eval-runs/p126-grid-hybrid`
   (background, ~60 min). Gates inside the grids: fts point 0.3/3 = `p126-ref-fts` and hybrid point
   0/3 = `p126-ref-hybrid` (chunk_ids 30/30).
5. Read `choose()`'s pick per mode from each `grid.md`; no manual override (if the pick looks wrong,
   that is a finding for the report, not a reason to change the rule).
6. Duplicate rule (Design) on the three picks; extra `--dup-jaccard` runs only if it fires.
7. Set `hybrid.FLOOR` / `hybrid.MAX_PER_DOC` / `hybrid.DUP_JACCARD` (the last only if step 6
   changed it for that mode) to the picks; `fts.py` constants are not touched. Confirmation runs
   with no options, one mode per process (`p126-norerank`, `p126-hybrid`) -> chunk_ids identical to
   the chosen grid points (or the step-6 rerun, if it changed `DUP_JACCARD`); their latency is the
   reported latency.
8. `eval_compare.py` -> `evals/hybrid-eval/corpus-2026-10-29/`; copy the chosen runs and grids there.
9. Docs: spec section, RUN.md (PowerShell + bash), `.env.example`, verify-cee recipe line.
10. Final checks: `pytest -q` both venvs; `verify_cee.py run` with `RETRIEVAL_MODE=fts` (core venv,
    vectors off), `RETRIEVAL_MODE=hybrid` and `RETRIEVAL_MODE=hybrid-norerank` (vectors venv,
    `CEE_VECTORS=on`) -> VERIFY PASS each.
11. `/finish-task`: PR base **`exp/hybrid`**, body says **`Part of #126`** with the open item "S1
    review of the `fts.py` dispatch / `select(dup_jaccard=)` and the `specs/retrieval.md` section";
    S1 is requested as reviewer. As with PR #158, the TL decides whether S1 reviews before or after
    the merge into `exp/hybrid`; if S1 has not reviewed, the PR reviewer escalates that point to
    the TL instead of deciding it. #126 is closed by hand when every item is done (a merge into a
    non-default branch does not auto-close). The body has the summary table, the picks, 0 real
    calls, and says `progress.yml` fires only on `main`, so the Progress line stays in the PR.

Stop rule: if a no-change gate (step 1, 3, 4 or 7) fails, stop, log the diff and bring the plan
back. A mode with no eligible grid point, or hybrid worse than fts, is **not** a stop: it is the
finding, reported as such.

Risks: overfitting 30 questions (stated in the report); the hybrid grid takes ~1 h (one
background run; scores are recomputed per point, no caching that could change results); onnxruntime
thread scheduling makes latency vary run to run (median and p90 reported, machine named).

## Acceptance
All on the PR head, local DB `corpus-2026-10-29`, `--as-of 2026-10-29`, mock provider, **0 real calls**.
- [x] Report `evals/hybrid-eval/corpus-2026-10-29/report.md` committed on the branch (into
      `exp/hybrid`) with all three modes: PASS/FAIL per question for Q1-Q30, tier-1 doc and passage
      recall, refusal accuracy on Q24, Q25, Q28, Q29, Q30 and all keyed, forbidden hits, duplicate
      measure, latency (median, p90, max, warm-up), at chosen and at default constants, plus the
      full grid and the selection rule.
- [x] **Refusal accuracy in `hybrid` and in `hybrid-norerank` >= fts** at the chosen constants
      (gap questions Q24, Q25, Q28, Q29, Q30 and all keyed; `summary.json` shows both numbers). If a
      mode cannot meet it, the report says so and the item is reported as not met.
- [x] Forbidden hits 0 on all 30 in every chosen run (covers Merrill = BAC GWIM only: Q4, Q27, Q30; Q7).
- [x] Q7 (quotas): every named firm has a hit in each chosen run. Q26: no hit outside the window,
      newest first, in each chosen run.
- [x] Q29: report lists per mode the MS 10-K chunks returned, `#702`'s presence and the diag scores;
      states `#702` is not on the must-not list; no answer-key change, no Q29-specific rule.
- [x] Tuned constants per mode chosen by `choose()` (grid.md shows the pick and reason); the hybrid
      picks are the defaults in `hybrid.py`; confirmation runs reproduce the picked grid points
      (chunk_ids 30/30).
- [x] fts unchanged: with no constant options, fts chunk_ids = `p126-ref-fts` (= `p125r-fts-after`)
      on 30/30, core venv, vectors off; and `hybrid` at 0/3 = `p126-ref-hybrid` on 30/30.
- [x] Duplicate measure reported per mode (trigram measure labelled as a Python re-implementation
      of pg_trgm); hybrid modes' `DUP_JACCARD` kept or changed by the stated rule; `fts.DUP_JACCARD`
      still 0.6 (`git diff origin/exp/hybrid -- src/cee/retrieve/fts.py` shows no constant line changed).
- [x] Window cap 8 and research cap 2 unchanged in every mode (unit test with per-mode
      `MAX_PER_DOC` set to 2 and 4).
- [x] **Mock only**: no command in this plan, the Progress log or the PR uses `--real`; every
      `report.json` under `.eval-runs/p126-*` and `evals/hybrid-eval/` has `meta.mode == "mock"` and
      `meta.real_calls == 0`. Check (vectors venv, repo root), expected output `N runs, all mock, 0 real calls`:
      `python -c "import json,glob; fs=glob.glob('.eval-runs/p126-*/**/report.json',recursive=True)+glob.glob('evals/hybrid-eval/**/report.json',recursive=True); bad=[f for f in fs if (m:=json.load(open(f,encoding='utf-8'))['meta'])['mode']!='mock' or m['real_calls']!=0]; print(f'{len(fs)} runs, all mock, 0 real calls' if fs and not bad else f'BAD {bad}')"`
      (same line in PowerShell and bash; Mac: `.venv/bin/python`).
- [ ] S1 has reviewed the `fts.py` changes and the spec section, or the TL has decided it happens
      after the merge (PR says `Part of #126` until then).
- [x] `pytest -q` passes in both venvs, none fewer than step 1's counts; new tests as in Files.
- [x] `verify_cee.py run` VERIFY PASS in `fts` (core venv), `hybrid` and `hybrid-norerank`.
- [x] Every new RUN.md PowerShell block has a bash block.
- [x] Linked questions: Q1-Q30 in the report; refusal Q24, Q25, Q28, Q29, Q30; quotas Q7.

Out of scope (issue + TL): changing the default mode (#127); alpha-blending the rerank score with
RRF; any rule added for Q29; changing the answer key; new retrieval features beyond the third mode;
`fts.py` default constants; anything on `main`.

## Open questions (accepted as planned by plan review round 1)
1. In `hybrid` mode the FLOOR grid is applied as a relative RRF floor before the rerank (so both
   hybrid modes share the candidates). The alternative reading, an absolute sigmoid `RERANK_FLOOR`
   of 0.2 / 0.3 / 0.4, is not run: #125 showed 0.01-0.1 already lose evidence, and a floor only
   removes the lowest scores. Accept, or run it as 9 extra points (~45 min)?
2. `hybrid-norerank` uses the same 50-candidate pool as `hybrid` (clean ablation). Without a
   reranker the cap is not needed for speed; a version over the full fused lists would be a
   separate experiment (not planned).
3. If fts's pick differs from 0.3/3, it is reported only (fts.py is S1's and mirrors `main`);
   whether to change `main`'s constants is for #127 / S1.

## Progress log
- 2026-11-05 18:23 - plan written on `tl/126-hybrid-eval` from `origin/exp/hybrid` 795056b. Inputs:
  issue #126 (body names `exp/hybrid`, EJ-10), #125 comments and decision record, `plans/0125-hybrid-retrieval.md`
  (Progress log numbers and Q21/Q24/Q25/Q29 diagnosis), closed #59, #127, `hybrid.py`, `fts.py`,
  `eval_run.py`, existing tests. No file other than this plan changed; no run made.
- 2026-11-05 18:29 - plan review round 1: changes requested; open questions 1-3 accepted as planned.
  Blocking fixed: (1) `DUP_JACCARD` is per mode in `hybrid.py` only (passed through a new optional
  `select(dup_jaccard=)`); fts's value is measured and reported, never changed; step 7, Files, Not
  changed and Acceptance agree. (2) S1 reviews the `fts.py` changes and the spec section; PR says
  `Part of #126`; TL decides S1 review before/after the merge, the PR reviewer escalates if S1 has
  not reviewed. (3) Mock-only Acceptance line with a one-line check over every `report.json` (dry
  run on the 7 `p125r-*` reports, PowerShell and Git Bash: `7 runs, all mock, 0 real calls`).
  Non-blocking taken: pg_trgm not installed -> Python re-implementation defined and labelled;
  window cap 8 / research cap 2 unchanged + test; latency sources named (chosen fts grid point,
  hybrid confirmation runs); `p125r-hybrid` ran at 587109a, the `p126-ref-*` runs are the references.
- 2026-11-05 18:43 - plan approved (round 2, eedec7d). **Step 1**: `pytest -q` on eedec7d (= 795056b
  code): core venv 304 passed / 2 skipped, vectors venv 306 passed. References (vectors venv,
  `CEE_VECTORS=on`, `cee.__file__` = repo\src): `p126-ref-fts` PASS 28 / FAIL 2, docs 0.796,
  passages 0.402, refusal gap 5/5, median 0.35 s; `p126-ref-hybrid` PASS 27 / FAIL 3, docs 0.728,
  passages 0.373, gap 5/5, median 8.4 s. chunk_ids vs `p125r-fts-after` and vs `p125r-hybrid`:
  30/30 identical each (gate passed). **Steps 2-3** coded: `hybrid.py` (`rerank=False`, `gate()`,
  per-mode `FLOOR`/`MAX_PER_DOC`/`DUP_JACCARD`), `fts.py` (mode list, dispatch, `select(dup_jaccard=)`),
  `eval_run.py` (options, grid, `choose()`, duplicates, p90/max, CPU), `eval_compare.py`, tests,
  docs. No-change gates: `p126-nochange-fts` (core venv, vectors off) = `p126-ref-fts` 30/30;
  `p126-nochange-hybrid` = `p126-ref-hybrid` 30/30 (gate passed). Core venv pytest 329 passed / 2
  skipped. First duplicate numbers (default constants): trigram pairs > 0.9: fts 1 (max 0.911),
  hybrid 2 (max 0.938); word 5-gram: 0 in both (max 0.58 / 0.59).
- 2026-11-05 19:33 - **Step 4 grids** (vectors venv, `CEE_VECTORS=on`, code d784e30, baseline `p126-ref-fts`,
  18:44-19:32): `p126-grid-fts` (9 points), `p126-grid-norerank` (12), `p126-grid-hybrid` (12). Grid gates:
  fts 0.3/3 = `p126-ref-fts` 30/30, hybrid 0/3 = `p126-ref-hybrid` 30/30 (passed). **Step 5 picks**
  (`choose()`, no override): fts **0.2/3** (passages 0.474, PASS 27; 0.x/4 not eligible: refusal 4/5,
  9/10); hybrid-norerank **0.4/3** (passages 0.405, beats 0.4/4 on smaller MAX_PER_DOC); hybrid
  **0.4/4** (passages 0.402, beats 0.4/3 on PASS 28 vs 27). All 12 hybrid and 12 norerank points:
  refusal 5/5, 10/10, forbidden 0. **Step 6**: both hybrid picks have 0 trigram pairs > 0.9 (max 0.893)
  -> `DUP_JACCARD` 0.6 kept in both hybrid modes, no extra runs. fts pick has 1 pair (Q19, two EDJ 10-Q
  tables, 0.911; also at fts 0.3/3): reported only. **Step 7**: `hybrid.FLOOR` = 0.4 / 0.4,
  `MAX_PER_DOC` = 4 (hybrid) / 3 (norerank) in 3950a80; `fts.py` constants untouched. Confirmation runs
  (one mode per process): `p126-norerank` = grid `f0.4-m3` 30/30, `p126-hybrid` = grid `f0.4-m4` 30/30
  (gate passed); latency median / p90: norerank 0.31 / 0.53 s, hybrid 5.1 / 8.2 s (warm-up 1.6 s, 4.5 s).
  Two test assertions read the tuned defaults from `hybrid.py` instead of hard-coding #125's values.
- 2026-11-05 19:38 - **Step 8**: `eval_compare.py` gained a reranker ablation (both hybrid modes at every
  grid point, and per question at hybrid's pick with `p126-grid-norerank/f0.4-m4` as `--same-constants`);
  Q29 text no longer assumes FAIL. Report in `evals/hybrid-eval/corpus-2026-10-29/` (report.md,
  summary.json, chosen run + grid per mode, 496 KB). Defaults in the report are the grid points fts 0.3/3,
  norerank 0/3, hybrid 0/3 (same chunk_ids as the references, with the new duplicate and p90 fields).
  Checks on the chosen runs: forbidden 0, misleading 0; Q7 hits MS, BAC GWIM, RJF; Q26 8 hits, none
  outside the window, newest first. Q29 in hybrid passes at MAX_PER_DOC 4 only through `MS-10K-2025#163`
  (Wealth Management income table, sigmoid 0.25); `#153`/`#170` still not returned, `#702` still the top
  MS 10-K hit (0.95), and RRF order returns `#702` too. Mock check: `42 runs, all mock, 0 real calls`.
- 2026-11-05 19:46 - **Steps 9-10**: docs (spec section, RUN.md: third mode + grid command, 1 new
  PowerShell + 1 bash block pair, `.env.example`, ask-progress recipe line). `pytest -q`: core venv 330
  passed / 2 skipped, vectors venv 332 passed (step-1 floor 304 / 306). verify-cee VERIFY PASS, 8
  features each: fts, core venv, vectors off (`.verify-runs/20261105-193845-3950a80`, summary fts/off);
  hybrid (`20261105-194017-3950a80`, hybrid/on, trace "... (hybrid)"); hybrid-norerank
  (`20261105-194220-3950a80`, hybrid-norerank/on, trace "... (hybrid-norerank)"). `git diff
  origin/exp/hybrid -- src/cee/retrieve/fts.py`: no constant line changed. 0 real calls. Open: S1
  review of the `fts.py` dispatch / `select(dup_jaccard=)` and the spec section (PR says `Part of #126`).
