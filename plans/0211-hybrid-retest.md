# 0211 - exp/hybrid: sync main, adapt hybrid.py, mock comparison on corpus-2026-11-17

Issue: #211    Role: TL    Spec: specs/retrieval.md
Base branch: `exp/hybrid` (ADR-011: model-based work stays off `main`). Branch `tl/211-hybrid-retest`
from `origin/exp/hybrid` 965b7f6; the PR targets `exp/hybrid`, never `main`.

## Goal
`exp/hybrid` equals `main` outside the hybrid files, `hybrid.py` applies every retrieval rule `main`
added since the branch was last synced (#179, #181, #190, #198, #199, #203, #205, #210), and one
mock comparison of `fts` and `hybrid-norerank` on `corpus-2026-11-17` decides, by a rule fixed
below before any run, whether the 30-question real run #212 happens. 0 real calls.

## Inputs read
Issue #211 (+ TL comment 2026-11-18), `CLAUDE.md`, `specs/retrieval.md` (main and branch),
ADR-009 to ADR-018, `main`'s `src/cee/retrieve/fts.py` and `scripts/eval_run.py` (#210, PR #218),
on `origin/exp/hybrid`: `src/cee/retrieve/hybrid.py`, `scripts/eval_compare.py`, `scripts/eval_run.py`,
`plans/0125-hybrid-retrieval.md`, `plans/0126-hybrid-eval.md`, `evals/hybrid-eval/corpus-2026-10-29/report.md`.
State checked: local DB is `corpus-2026-11-17` (sync-db -Check exit 0), 21,143 chunks, no `vector`
extension and no `chunk_embeddings` yet. Both models are already in
`D:\ALLPROJECTS\EDJ\cache\fastembed` (`models--Qdrant--bge-small-en-v1.5-onnx-Q`,
`models--Xenova--ms-marco-MiniLM-L-12-v2`); nothing is downloaded. `.venv` has fastembed 0.9.1,
onnxruntime 1.23.2.

## Files to change
Hybrid files (the only files allowed to differ from `origin/main` after this issue). Why the mode
plumbing counts as hybrid: ADR-010's Decision keeps "the hybrid code (`hybrid.py`, the mode switch,
`RETRIEVAL_MODE`, `synonym_only`)" on `exp/hybrid`; `modes.py`, `ask.py`, `config.py`, `ask_page.py`,
`verify_cee.py`, `eval_run.py` and `.env.example` differ from `main` only by that mode switch /
`RETRIEVAL_MODE` (and the #126 eval measures for the modes).
- `src/cee/retrieve/hybrid.py` - apply main's rules (table below), fill `PoolTrace`, `k=None` budget.
- `src/cee/retrieve/modes.py` (new) - the mode switch moved out of `fts.py`: `MODES`,
  `HybridUnavailable`, `HYBRID_NEEDS_VECTORS`, `search(q, k=None, mode=None, trace=None)`
  (fts -> `fts.search`; hybrid modes -> late import of `hybrid`, only with `CEE_VECTORS=on`).
  This lets `src/cee/retrieve/fts.py` be byte-equal to `main`.
- Mode plumbing kept from #125/#126/#128, re-applied on top of `main`'s version of each file, every
  hunk about the retrieval mode only: `src/cee/ask.py` (mode param, `modes.search`, `retrieval_mode`
  in the log), `src/cee/config.py` (`retrieval_mode`), `src/cee/app/views/ask_page.py` (Exact match /
  Smart search switch, #128; owner U1, owner review waived, TL decision 2026-11-17 (#187)),
  `scripts/verify_cee.py` (search-mode driver), `scripts/eval_run.py`
  (`--mode`, search timing and warm-up, duplicate measure, `--floor`/`--max-per-doc` grid; search goes
  through `modes.search(..., trace=...)`), `.env.example` (`RETRIEVAL_MODE`).
- `scripts/eval_compare.py` - adds a `--run MODE=report.json` comparison (fts vs hybrid-norerank,
  hybrid as reference) with recall@pool, recall@final, the Gate 4 missed-passage stages and the
  decision line computed by code. The #126 interface (`--chosen`, `--default`, `--grid`, `--diag`,
  `--notes`) is kept unchanged: `evals/hybrid-eval/corpus-2026-10-29/report.md` was written by it at
  `exp/hybrid` 3449cc5, and its test stays.
- Tests: `tests/test_hybrid.py`, `tests/test_search_mode.py`, `tests/test_eval_compare.py`,
  `tests/test_vectors_optional.py`, and the mode parts of `tests/test_eval_run.py`,
  `tests/test_ask_page_trace.py`, `tests/test_ask_progress.py`.
- Docs: `specs/retrieval.md` ("Retrieval modes" section only; owner S1, owner review waived, TL
  decision 2026-11-17 (#187)), `docs/RUN.md` ("Hybrid retrieval"
  section only, PowerShell + bash blocks), `.claude/skills/verify-cee/features/search-mode.md`,
  `features/README.md`, `features/ask-progress.md` (mode line only).
- Evidence: `evals/hybrid-eval/` as a whole is a hybrid path. New: `evals/hybrid-eval/corpus-2026-11-17/`
  (report.md, summary.json, inputs/*.json). `evals/hybrid-eval/corpus-2026-10-29/` is kept unchanged
  (the #126 record ADR-010 links to).
- Plans: `plans/0125-*`, `0126-*`, `0128-*` (already on the branch), this plan.
Everything else (incl. `src/cee/retrieve/fts.py`, `config/entities.yaml`, `evals/expected_chunks.yaml`)
equals `origin/main`. Not changed: ADRs, `main`.

## Steps

### 1. Merge `origin/main` into the branch (merge, not rebase)
`git fetch origin; git merge --no-ff origin/main` on `tl/211-hybrid-retest`. Merge base 80fc60d;
files changed on both sides: `fts.py`, `ask.py`, `ask_page.py`, `eval_run.py`, `verify_cee.py`,
`specs/retrieval.md`, `docs/RUN.md`, `features/ask-progress.md`, `tests/test_eval_run.py`.
Conflict rule:
- A file outside the hybrid list above: take `main`'s version (`git checkout origin/main -- <file>`).
- `src/cee/retrieve/fts.py`: take `main`'s version whole. The branch's additions to it move out:
  the mode switch to `modes.py`; the `dup_jaccard` parameter of `select()` is dropped (both hybrid
  modes use 0.6 = `fts.DUP_JACCARD`, picked in #126; `hybrid.DUP_JACCARD` and `--dup-jaccard` go);
  the docstring note moves to `hybrid.py`/`modes.py`.
- A hybrid-list file changed on both sides: start from `main`'s version, re-apply only the branch's
  mode hunks (list above). `eval_run.py` keeps main's `PoolTrace`/`budget()`/recall@pool code
  unchanged and calls `modes.search(query, k=..., mode=..., trace=trace)`.
- `specs/retrieval.md`, `docs/RUN.md`: `main`'s text plus the branch's modes / hybrid sections.
Check after the merge commit: `git diff origin/main --stat` lists only hybrid-list files;
`git diff origin/main -- src/cee/retrieve/fts.py config evals/expected_chunks.yaml` is empty; each
remaining hunk in a shared file is about the mode (read the diff). pytest is run; hybrid tests that
fail only because `hybrid.py` is not adapted yet are noted and fixed in step 3.

### 2. Embeddings for corpus-2026-11-17 (background, starts right after step 1)
Uses `main`'s unchanged `embed.py`. Environment only for the process, `.env` is not touched:
```powershell
New-Item -ItemType Directory -Force D:\ALLPROJECTS\EDJ\cache\ev211 | Out-Null
$env:CEE_VECTORS = 'on'; $env:FASTEMBED_CACHE_PATH = 'D:\ALLPROJECTS\EDJ\cache\fastembed'
.\.venv\Scripts\python.exe -m cee.retrieve.embed --missing *> D:\ALLPROJECTS\EDJ\cache\ev211\embed.log
```
In `docs/RUN.md` the macOS block is
`CEE_VECTORS=on FASTEMBED_CACHE_PATH="$HOME/cee-cache/fastembed" .venv/bin/python -m cee.retrieve.embed --missing`
(a Mac cache path, `.venv/bin/python`); the PowerShell block uses a `D:\...\cache\fastembed`-style
path. The same pairing applies to the eval_run and eval_compare commands of steps 6-7.
21,143 chunks at about 15 chunks/s on CPU: about 25 minutes, run in the background while step 3 is
coded; it commits per batch, so a stop resumes. Before: `python -m cee.retrieve.embed --query test`
with the same env proves the cached model loads (no fetch). After: `SELECT count(*) FROM chunks` =
`SELECT count(*) FROM chunk_embeddings` = 21,143. This adds the `vector` extension and the optional
`chunk_embeddings` table to the local `cee-db` (ADR-009; `fts` ignores them; undo:
`DROP TABLE chunk_embeddings; DROP EXTENSION vector;`). `sync-db -Check` is run again afterwards.

### 3. Adapt `hybrid.py`: every rule of `main`'s `fts.search()` that `hybrid.search()` lacks
| # | Rule on `main` (ADR / issue) | `hybrid.search()` today | How hybrid applies it |
|---|---|---|---|
| R1 | `doc_type_scope_sql(q)`: no `adv` outside fee/ADV questions and never in a window; no tier 4 for benchmark questions (ADR-015, #179) | not applied | `part_filters()` ANDs `doc_type_scope_sql(q)` into `filters` for every SQL pass: keyword leg, vector leg, firm / research / on-theme / peer parts, answer turns |
| R2 | budget `k = budget(q) - peer_slots(q)` when `k is None`; `PER_FIRM` 6 x n (ADR-013, #181) | `k = K` (20) | `search(q, k=None, ...)`: same default as `fts.search`. The candidate count scales with it: `RERANK_N x k / K` (50 at k=20, 75 at k=30) so a five-firm question is not starved; nothing else is tuned |
| R3 | `quota_firms(q.entities)`: Merrill's MER and BAC GWIM chunks share one firm's quota and floor base (ADR-013) | firm = `entity_id` everywhere | one quota-firm key for everything. The SQL legs partition by it, not by `entity_id`: `row_number() OVER (PARTITION BY {quota_key} ...)` with `{quota_key}` = `CASE WHEN d.entity_id = %(qf_parent0)s THEN %(qf_child0)s ... ELSE d.entity_id END` built from `quota_firms(q.entities)` (`ELSE d.entity_id` alone when the map is empty). So MER and BAC GWIM chunks form one ranked list per leg (ranks 1..n, one rank 1, LEG_K for the pair, not per entity); `_per_firm()`, `group_of` (turns), the floor base and `select(firm_of=...)` use the same key. Test: a Merrill query's legs, rows of MER and BAC interleaved, give one list with one rank 1 per leg and RRF scores on one scale; the SQL contains the CASE key |
| R4 | `FLOOR` measured from the firm's `FLOOR_BASE`-th (2nd) best rank; research part base 1 (ADR-014, #166) | `gate()`: share of the firm's best RRF | `hybrid-norerank`: no separate gate; the RRF score is `Hit.rank` and `select(floor=FLOOR[mode])` applies the floor with `FLOOR_BASE`, research `floor_base=1`, exactly as `fts`. `hybrid` (reference): the gate before the cross-encoder uses the same 2nd-best base; `select(floor=0)` on sigmoid scores as before |
| R5 | entity+theme on-theme pool (`on_theme_filter`, #117) and `Hit.on_theme`; THEME_FIRST slot ignores the floor (#190, ADR-014) | no on-theme pool, `on_theme` always False (so `theme_gaps()` would call every named firm a theme gap) | an on-theme part: both legs with `entity_filter AND on_theme_filter`, RRF, turns; merged into the firm pool with `on_theme=True`; the floor in `select()` already exempts the theme slot. `hybrid`: on-theme candidates skip the pre-rerank gate. Scores where the parts merge (the on-theme part has its own RRF, whose rank 1 would score like the firm part's rank 1): a chunk in both parts keeps its **firm-part** RRF score (`on_theme=True`); an **on-theme-only** chunk gets `rank = m x s / s_max`, where `s` is its on-theme RRF score, `s_max` the best on-theme-only score of its quota firm and `m` the lowest firm-part RRF score of that quota firm in the pool (`1 / (RRF_K + LEG_K)` when the firm has none). So it ranks below every firm-part chunk of its firm, keeps its on-theme order, and cannot move the `FLOOR_BASE` (2nd-best) base of a firm with 2+ firm-part chunks; it reaches the list through the theme slot (tier 0), not rank turns. Test: a firm with firm-part scores 0.032 / 0.030 and an on-theme-only chunk at on-theme rank 1 keeps base 0.030, the on-theme-only chunk ranks below the lowest firm-part chunk, a both-part chunk keeps its firm-part score, and the on-theme-only chunk still takes the THEME_FIRST slot |
| R6 | answer turns `PAIR_TURNS = "attach"` (`answer_turns`, `is_question_turn`; ADR-017, #203) | not applied | `fts.answer_turns(conn, question turns in the pool, where, window, filters + scope, params)` and `select(answers=...)` |
| R7 | home-firm theme peers (`q.theme_peers`, `peer_slots`, `peer_floor`, `PEER_THEME_PER_FIRM`; ADR-018, #205) | not applied | a peer part: both legs with `entity_filter(q.theme_peers, prefix="peer_") AND on_theme_filter`, RRF, then `peer_floor(pool, FLOOR[mode])` (hybrid: on the RRF score, before rerank), then main's peer `select()` and 2-per-firm loop, appended after the named firms; kept in a window |
| R8 | slot order: `TIER_LAST`/`LAST_TIERS`/`TRADE_KEEP` (trade press last, not in a window, not in research) and `NEW_DOC_FIRST`/`NEWEST_BAND` (not in research) (ADR-016, #198, #199) | `select()` was called with no slot-order flags (branch `select()` had none) | pass the same flags as `fts.search`: firm part `trade_last=not q.window`; research `trade_last=False, new_doc_first=False`; peers `trade_last=not q.window` |
| R9 | window opts: `floor 0`, `WINDOW_MAX_PER_DOC`, `trade_last False`; newest first (Q26) | floor 0, window cap, newest first | unchanged plus R8 |
| R10 | `Hit.date_basis` from `documents` (ADR-007 T-09, window and caveats) | `ROWS_SQL` lacks it (defaults to "source") | `ROWS_SQL` selects `d.date_basis` |
| R11 | `PoolTrace` (#210) | none | `search(..., trace=None)`: `trace.firm` = firm-part candidates before any floor (the RRF turns, the equivalent of `fts`'s per-group pool before `select()`), `research`, `on_theme`, `peers` (before `peer_floor`), `answers`; recording only, same hits with or without it (test) |
| R12 | words, synonyms, `synonym_only`, inflected / phrase keys (#203), boilerplate weight, entity filter with segments, window filter, Ask filters, gap path | via `fts.keyword_terms`, `_tsquery_sql`, `rank_sql`, `entity_filter`, `window_filter`, `filters_sql` | reused as they are on `main` (signatures checked after the merge); a test pins the shared calls |
Constants are not retuned: `FLOOR[hybrid-norerank] = 0.4`, `MAX_PER_DOC = 3`; `hybrid` 0.4 / 4;
`LEG_K 100`, `RRF_K 60`, `RERANK_N 50` (scaled by R2), `THEME_RERANK_N 20`.
Tests (`tests/test_hybrid.py`, fake connection and scorer as today): one test per R1-R11 (the SQL
carries the scope clause; `k=None` -> `budget()`; MER + BAC GWIM one quota; floor from the 2nd best;
on-theme flag and theme slot below the floor; answer turn attached; peers appended at most 2 each;
trade last / new document first reach `select()`; `date_basis` read; trace filled and hits
unchanged with and without trace).

### 4. Hard-filter check in hybrid mode (DB-backed, needs step 2)
A test in `tests/test_hybrid.py`, skipped unless `CEE_VECTORS=on` and every chunk has a vector:
`hybrid-norerank` (and `hybrid` if the reranker is cached) on Q4 "What is Merrill's advisor growth
strategy ..." returns only `entity_id = MER` or (`BAC` and segment in GWIM / Merrill); Q26 "What's new
on Raymond James in the last 90 days?" (as of 2026-11-17) returns only `date_basis = source`
documents with `published_at` inside the window, no `adv`. Run it once here with the env of step 2.

### 5. Decision rule (fixed here, before any run; the issue's rule)
From the two mock runs of step 6 on the same branch commit, `hybrid-norerank` is compared with `fts`:
- **A.** tier-1 passage recall (`summary.tier1_passage_recall`, = tier-1 recall@final, 3 decimals):
  hybrid-norerank >= fts + 0.03; **and**
- **B.** refusal correct on all 5 gap questions Q24, Q25, Q28, Q29, Q30 (5/5); **and**
- **C.** refusal correct on every keyed question: the issue writes "10/10 keyed", the count on the
  corpus-2026-10-29 key; with today's key (#210) that is 22/22. Read as "every keyed question", not
  as any 10; **and**
- **D.** 0 forbidden hits over all 30 questions.
All four hold -> **#212 runs** (the 30-question real run). Any one fails -> **#212 is closed as not
planned.** `hybrid` (with reranker) is a reference only and never decides. recall@pool is reported
for both modes, with the stage of the 8 Gate 4 missed passages (I-1 / PR #218: 7 of 8 are "not in
pool" for `fts`: Q7 and Q25 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q19 `EDJ-10K-2025#88`, Q20
`FIDELITY-III-2025#0` and `UBS-NEXTGEN-2026#119`/`#13`, Q25 `RJF-PR-web-affiliation-options#1`;
Q17 `BAC-TR-2026Q2#21` in pool), but recall@pool does not change the decision. `eval_compare.py`
computes the line from the two report.json files with these constants in code.

### 6. Runs (mock, 0 real calls), as of 2026-11-17, k by budget, `LLM_PROVIDER=mock`
Same env as step 2, outputs under `.eval-runs/0211-*` and copied to
`evals/hybrid-eval/corpus-2026-11-17/inputs/`:
```powershell
$env:LLM_PROVIDER = 'mock'; $base = 'evals/baselines/corpus-2026-11-17/report.json'
.\.venv\Scripts\python.exe scripts/eval_run.py --mode fts --as-of 2026-11-17 --baseline $base --out .eval-runs/0211-fts
.\.venv\Scripts\python.exe scripts/eval_run.py --mode hybrid-norerank --as-of 2026-11-17 --baseline $base --out .eval-runs/0211-hybrid-norerank
.\.venv\Scripts\python.exe scripts/eval_run.py --mode hybrid --as-of 2026-11-17 --baseline $base --out .eval-runs/0211-hybrid
```
Sanity: the `fts` run's final chunk ids equal `main`'s baseline on 30/30 questions (proves the merge
left `fts` untouched). Each mode runs once; nothing is re-run to change a number.

### 7. Comparison report and decision
`python scripts/eval_compare.py --run fts=... --run hybrid-norerank=... --run hybrid=... --out
evals/hybrid-eval/corpus-2026-11-17` writes report.md and summary.json: per mode PASS/FAIL, recall@pool,
recall@final (all and tier 1), tier-1 doc and passage recall, refusal gap / all keyed, forbidden hits,
mean pool size with the label "recall@pool is not like-for-like: fts pools 15 per (firm, document
type) with no total cap, hybrid pools RERANK_N candidates per part (scaled by R2)", search median / p90 / max and warm-up, CPU; per-question differences (recall@pool,
recall@final, status); the Gate 4 missed-passage stage table; the decision line (step 5); and the sentence "0.03 of tier-1
passage recall is about 1-2 passages on this bank; tuned and scored on the same 30 questions with no
held-out set (ADR-010), so a difference this size is weak evidence". Commit it.

### 8. Docs, app check, finish
- `docs/RUN.md` "Hybrid retrieval": embed command, the three eval runs and the compare command, each
  in a PowerShell and a bash block. `specs/retrieval.md` modes section: R1-R11 and the #211 result.
- verify-cee in hybrid mode: app with `CEE_VECTORS=on`, Smart search (search-mode feature) plus the
  other features; evidence folder under `.verify-runs/`.
- pytest on the branch. `/finish-task`: PR to `exp/hybrid` with the decision line; comment the
  outcome on #212 (runs, or closed as not planned per the rule).

## Risks
- **Merge changed fts (stop rule).** If the `fts` run on the branch (step 6) does not reproduce
  `main`'s `corpus-2026-11-17` baseline chunk ids on 30/30 questions (same ids, same order): stop,
  run no hybrid mode, find and fix the merge (fts.py / config / key must equal main), commit the fix
  and re-run `fts`. No decision line is written from a commit whose `fts` run failed this check; the
  decision uses only runs from one commit that passed it.
- **Score comparability.** Hybrid ranks are RRF scores (a different scale from `ts_rank`); where the
  firm, on-theme and peer parts merge, a part's own rank 1 could look like the firm's best and move
  the floor base or turn order. R3 / R5 pin one scale per quota firm, with tests. recall@pool is not
  like-for-like (fts 15 per group, hybrid RERANK_N per part): reported next to the mean pool size,
  never part of the decision.
- **Shared local cee-db.** Step 2 adds the `vector` extension and `chunk_embeddings` to the local
  database every branch uses. `fts` and `main` ignore them (ADR-009); `sync-db -Check` is re-run
  after. Undo: `DROP TABLE chunk_embeddings; DROP EXTENSION vector;` (docker exec cee-db psql -U cee -d cee).
  A later `/sync-db` restore drops them too; then step 2 must be run again before a hybrid run.
- **Small threshold.** +0.03 tier-1 passage recall is about 1-2 passages on this bank, tuned and
  scored on the same 30 questions with no held-out set (ADR-010). The rule stands as fixed; the report
  says how weak the evidence is.
- **Long embed.** About 25 minutes on CPU; it resumes per batch if stopped. No hybrid run starts
  before the row counts match.

## Acceptance
- [x] Merge, not rebase: the branch has a merge commit with parents (exp/hybrid tip, origin/main tip).
- [x] `git diff origin/main --stat` (after the merge into the branch) lists only the hybrid-list files
      in "Files to change" (`evals/hybrid-eval/` as a whole); `git diff origin/main -- src/cee/retrieve/fts.py config evals/expected_chunks.yaml` is empty;
      `git diff 965b7f6 -- evals/hybrid-eval/corpus-2026-10-29` is empty.
- [x] pytest passes on the branch (count recorded).
- [x] `SELECT count(*) FROM chunk_embeddings` = `SELECT count(*) FROM chunks` = 21,143 on corpus-2026-11-17.
- [x] `hybrid.py` applies R1-R11; each has a passing unit test in `tests/test_hybrid.py`, incl. the
      R3 one-list quota-firm test and the R5 merged-score / floor-base test.
- [x] Hard-filter test: Q4 (Merrill) in hybrid mode returns only MER or GWIM/Merrill-tagged BAC chunks;
      Q26 (90-day window) returns only in-window, source-dated documents (step 4, run and passed).
- [x] `fts` on the branch reproduces `main`'s `corpus-2026-11-17` baseline chunk ids on 30/30 questions.
- [x] `evals/hybrid-eval/corpus-2026-11-17/report.md` committed with recall@pool and recall@final for
      both modes, tier-1 recall, refusal, forbidden hits, search time, per-question differences, the
      Gate 4 missed-passage stages and the decision line from step 5.
- [x] Linked questions Q1-Q30 all run in both modes; gap questions Q24, Q25, Q28-Q30 reported per mode.
- [x] Every new run command (embed, eval_run --mode, eval_compare) has a PowerShell and a bash block in `docs/RUN.md`.
- [x] verify-cee in hybrid mode (Smart search) passes; evidence folder named in the PR.
- [x] 0 real calls (mock only), stated in the PR.

## Progress log
- 2026-11-18 22:12 - plan written on `tl/211-hybrid-retest` (from `origin/exp/hybrid` 965b7f6; `origin/main` 2a22e23 incl. #210 / PR #218). DB checked: corpus-2026-11-17, 21,143 chunks, no vectors yet; models already cached on D:. Waiting for the reviewer agent's approval before step 1.
- 2026-11-18 22:40 - revised after review (issue #211 comment 6999547584): `evals/hybrid-eval/` listed whole, 10-29 kept unchanged; R3 quota-firm key in the SQL partition; R5 merged-score rule; Risks section with the fts 30/30 stop rule; owner-waiver tags, ADR-010 citation, Mac RUN.md block, recall@pool label, eval_compare keeps the #126 interface.
- 2026-11-18 22:36 - correction: the revision entry above was committed at 22:19 (2e1080d), not 22:40. Plan approved by the reviewer agent (issue comment 6999588521); non-blocking notes applied: R5 uses `ON_THEME_SCALE = 0.99` so an on-theme-only chunk ranks strictly below its firm's firm-part chunks.
- 2026-11-18 22:32 - step 1: `git merge --no-ff origin/main` (2a22e23) committed as e4a649a (parents 2e1080d, 2a22e23). Conflicts in fts.py (took main's whole), ask_page.py, verify_cee.py, eval_run.py, test_eval_run.py (main + mode hunks). The mode switch moved to `src/cee/retrieve/modes.py`; `hybrid.DUP_JACCARD` and `--dup-jaccard` removed. The merge commit also carries step 3 (hybrid.py R1-R11 and their tests), because the merged tests needed it. `git diff origin/main --name-only` lists only hybrid-list files; `git diff origin/main -- src/cee/retrieve/fts.py config evals/expected_chunks.yaml` is empty. pytest 623 passed, 2 skipped (the DB hard-filter test skips until the vectors are in).
- 2026-11-18 22:21 - step 2 started in the background: `embed --query test` loaded the cached model from `D:\ALLPROJECTS\EDJ\cache\fastembed` (384 dims, no fetch); `embed --missing` running (about 13 chunks/s).
- 2026-11-18 22:33 - stop-rule check: `fts` on e4a649a (`.eval-runs/0211-fts`, mock, as of 2026-11-17) has the same chunk ids as `main`'s baseline on 30/30 questions (PASS 29 / FAIL 1, tier-1 passages 0.597, recall@pool 0.686, refusal 5/5 and 22/22, 0 forbidden). Hybrid runs may start once the vectors are complete.
- 2026-11-18 22:51 - step 2 done: `embed --missing` exit 0, "21143 embedded, 0 still missing (1789 s, model BAAI/bge-small-en-v1.5, cache D:\ALLPROJECTS\EDJ\cache\fastembed)"; `chunks` = `chunk_embeddings` = 21,143 (log `D:\ALLPROJECTS\EDJ\cache\ev211\embed.log`). Step 4: the DB hard-filter test passed in both hybrid modes (Q4 only MER / BAC GWIM-Merrill; Q26 only source-dated in-window documents, no `adv`).
- 2026-11-18 22:55 - step 6, all three runs on 7f12f60 (mock, as of 2026-11-17, 0 real calls). Stop rule re-checked on this commit: `fts` = `main`'s baseline chunk ids on 30/30. fts: PASS 29, tier-1 passages 0.597, tier-1 recall@pool 0.803, refusal 5/5 and 22/22, 0 forbidden. hybrid-norerank: PASS 28 (Q19, Q22 FAIL), tier-1 passages 0.484, tier-1 recall@pool 0.623, refusal 5/5 and 21/22 (Q22 retrieves its must-not `MS-PR-2026-04-15-01#15`), 0 forbidden. hybrid (reference): PASS 27, passages 0.479, refusal 4/5 and 20/22, median search 9.0 s. Mean pool size fts 244.6 vs hybrid 64.5 (not like-for-like).
- 2026-11-18 23:00 - step 7: `evals/hybrid-eval/corpus-2026-11-17/` written by `eval_compare.py --run`. Decision by the fixed rule: **#212 is closed as not planned** (A: 0.484 < 0.627; C: 21/22). Gate 4 missed passages: hybrid finds none of fts's 7 "not in pool" passages except Q25 `MS-10K-2025#153` (in pool, lost in select), and loses Q17 `BAC-TR-2026Q2#21` from the pool. Nothing was re-run or retuned after the numbers came in.
- 2026-11-18 23:05 - step 8: verify-cee `run --mode hybrid` with `CEE_VECTORS=on` on 7f12f60: all 10 features PASS incl. search-mode (Smart search enabled, `query_log` retrieval_mode = hybrid), evidence `.verify-runs/20261118-225935-7f12f60`. Its summary line says "Retrieval: fts" because it reads the driver's own settings, not the app's; the logged queries show hybrid. pytest 625 passed, 2 skipped (without the vectors env); the 2 DB tests pass with it.
- 2026-11-18 22:36 - eval_compare `--run` (decision computed by code, Gate 4 stage table, per-question diffs) with tests; RUN.md re-test commands (PowerShell + bash); specs/retrieval.md modes section updated.
