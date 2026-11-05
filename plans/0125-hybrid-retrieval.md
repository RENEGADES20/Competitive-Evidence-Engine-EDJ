# 0125 - Hybrid retrieval: keyword + vector, RRF, local rerank, per-request mode

Issue: #125    Role: TL    Spec: specs/retrieval.md (S1 owns `fts.py`: S1 reviews), ADR-001, ADR-003, ADR-009
Branch: `tl/125-hybrid-retrieval` -> PR into **`exp/hybrid`** (never `main`)

## Goal
A second retrieval mode, `hybrid`, chosen per request (`search(q, mode=...)`, `ask(..., mode=...)`,
default from `RETRIEVAL_MODE`, default `fts`), living on the long-lived experimental branch
`exp/hybrid`. Inside the same SQL entity / segment / window / Ask-filter `WHERE`, it fuses keyword
and vector candidates with RRF, reranks them with a local cross-encoder, drops weak matches below
an absolute score floor and hands the rest to the same `select()` quotas. Hybrid reads the optional
`chunk_embeddings` table and runs only with `CEE_VECTORS=on` (ADR-009); with vectors off nothing
imports fastembed. `fts` mode keeps `main`'s results for every question except Q29, whose
misleading chunk goes away in both modes. #125 proves hybrid is **correct** (hard filters, gap
path, window, fts unchanged); how good it is (PASS/FAIL, recall) is measured and reported here
and tuned in #126.

## Revision 2 (2026-11-05): what changed and why
1. **Stop rule at step 8 fired** (Progress log 2026-10-30 11:45): `select()`'s relative `FLOOR`
   (0.3 x the firm's best) on sigmoid rerank scores emptied the pool. Design now: hybrid calls
   `select(..., floor=0)` and uses only an absolute `RERANK_FLOOR` (section "Floor" below).
2. **main moved** (PR #145 / #144, ADR-009; also #116 entity+theme, #63 Ask filters): vectors are an
   optional module, off by default. The branch takes `main` in by **merge** (never rebase or
   force-push); hybrid reads `chunk_embeddings`, needs `CEE_VECTORS=on`, and both models load
   from the cache only (fetched by an explicit command, never at query time).
3. **Sponsor constraint** (portability spec, item 10: no embeddings, pgvector or rerankers on
   `main`; explore semantic retrieval on a branch, documented). Tech lead decision: #124/#125
   hybrid work stays off `main`. Branch `exp/hybrid` was created from `origin/main` 9dc4c9b and
   pushed (2026-11-05); the #125 PR targets it and the reviewer merges into it.
4. **Scope cut:** no ADR change in #125 (no ADR-008, no ADR-001 Status line, no escalation for an
   ADR). The decision ADR moves to #127, after the #126 comparison. Docs that say how to run hybrid
   on `exp/hybrid` stay.
5. **Gates:** correctness gates only (Acceptance). PASS/FAIL and recall vs fts are reported, not
   gated, because tuning per mode is #126's job (#126 also owns "refusal accuracy in hybrid >= fts").
6. **Reranker settled:** `Xenova/ms-marco-MiniLM-L-12-v2` (step-8 numbers below); bge stays
   selectable through `RERANK_MODEL` for #126 only.
7. **Pool shape** (from the Q21 / Q24 diagnosis): legs rank per firm in every mode and the rerank
   pool takes turns over (firm, document type) groups, the same groups fts mode pools by.

## Facts checked before planning
Original facts (2026-10-30, base 3fa63a9) that still hold:
- Local DB `cee-db`: snapshot `corpus-2026-10-29`, 17,183 chunks, 111 documents, pgvector 0.8.1.
- **Q29 diagnosis (fts mode).** Search terms `pay financial advisors`, synonyms of `pay`:
  `compensation`, `payout`. `MS-10K-2025#696` (FICC client clearing guarantees, must-not) has `pay`
  ("pay any net liquidation amount") and `payout` -> rank 9.80; the answer chunk `MS-10K-2025#153`
  ("formulaic payouts ... compensation") -> 8.52. Leaving the bare word out of the FTS words
  (synonyms kept) brings `#153` in and keeps every must-not chunk out. `pay` occurs in no other
  question of `evals/questions.yaml` (only Q29), so this changes only Q29 in the bank.
- pgvector HNSW with a `WHERE` filter can miss rows; step 4 (2026-10-30) found the theme leg via
  HNSW missed 7 of the top 100 for Q16 even at `ef_search` 200, so the vector leg is an exact scan.

New facts (2026-11-05, read-only queries and existing `.eval-runs/p125-*` reports):
- `origin/main` = 9dc4c9b; `exp/hybrid` = 9dc4c9b. `git merge-tree HEAD origin/main`: conflicts in
  `src/cee/ask.py` (#63 `filters` vs our `mode`), `src/cee/retrieve/embed.py` (#144 cache-only
  loader vs our `load_cached`), `src/cee/retrieve/fts.py` (#116 entity+theme and #63 filters vs our
  mode switch / `synonym_only` / keyword helpers). Everything else merges cleanly.
- Local DB still has `chunks.embedding` (`count(*)` = `count(embedding)` = 17183) and no
  `chunk_embeddings` table. A pre-#144 backup is at `D:\ALLPROJECTS\EDJ\cache\backups\cee-before-144.dump`
  (outside the repo). Applying `db/optional/vectors.sql` moves the 17183 vectors into
  `chunk_embeddings` and drops the column: planned, no data is deleted. `chunk_topics` has 1522
  rows (needed by #116's `theme_filter`). The DB does not hold the 10 documents #147 added to the
  manifest (111 loaded vs 121 in `main`'s manifest); every run here stays on `corpus-2026-10-29`
  with `--as-of 2026-10-29`, as #126 also specifies.
- Model cache `D:\ALLPROJECTS\EDJ\cache\fastembed` holds all three models:
  `models--Qdrant--bge-small-en-v1.5-onnx-Q/snapshots/*/model_optimized.onnx`,
  `models--Xenova--ms-marco-MiniLM-L-12-v2/snapshots/*/onnx/model.onnx`,
  `models--BAAI--bge-reranker-base/snapshots/*/onnx/model.onnx`. Nothing needs downloading.
- Python environments: the repo `.venv` has fastembed 0.9.1 + onnxruntime 1.23.2 ("vectors venv");
  `D:\ALLPROJECTS\EDJ\wt-144\.venv` has neither ("core venv", from #144). Both have `cee` installed
  editable from their own checkout, so every run sets `PYTHONPATH=<checkout>\src` and logs
  `python -c "import cee; print(cee.__file__)"` first.
- **Reranker choice (approved rule, step-8 numbers, floor 0 in the rerank, select FLOOR 0.3):**
  MiniLM-L-12 passages 0.265, median search 8.5 s; bge-reranker-base passages 0.271 (+0.006, rule
  needs +0.02), median 25.0 s (rule needs <= 5 s), refusal gap 4/5 for both. -> MiniLM-L-12.
- **Why the relative FLOOR fails on rerank scores** (`p125-hybrid-minilm-f0` vs
  `p125-diag-minilm-noselectfloor`, both MiniLM, no rerank floor): hits per question with
  `select()` FLOOR 0.3 -> 0: Q4 6 -> 20, Q30 1 -> 20, Q19 4 -> 7, Q7 16 -> 20, Q26 8 -> 8 (window,
  floor already 0). PASS 17 -> 24, docs 0.471 -> 0.693, passages 0.265 -> 0.428 (fts 0.402).
  FTS `ts_rank` is 0 for "no match" and grows with matches, so "30 % of the firm's best" means
  "much weaker match". A sigmoid of cross-encoder logits is not a ratio scale: MiniLM's logits sit
  mostly below 0 (the `--check` pair scored -1.125 and -1.413 -> 0.245 and 0.196), so a top hit at
  logit 1 (0.73) cuts every passage below logit -1.3 (0.22), i.e. most of the pool. A cut on this
  scale has to be absolute.
- **Diagnosis of the four PASS -> FAIL questions** (diag run vs `p125-fts-after`):
  - **Q21** (theme, generational wealth transfer, 6 patterns): fts 4/6 patterns, 20 hits over 17
    documents of every firm; hybrid 1/6, only **13** hits, all tier 5 research (BOFA-PB 6, UBS 3,
    CERULLI 3, FIDELITY 1). Cause: in theme mode the legs were "top 100 overall" and the pool "top 50
    RRF overall", so research (which talks about the topic in every sentence) filled both legs and
    the pool; `select()` gives firms turns, but no firm chunk was left to take one. Not a reranker
    problem; a pool-shape problem (fts pools per firm and document type, `POOL_PER_GROUP` 15).
  - **Q24** (client assets per advisor, 5 firms, gap_with_adjacent): coverage 0.6 -> 0.2, lost
    `MS:supplement` (`MS-SUPP-2026Q1#14`, a markdown table) and `SCHW:10-K`. Hybrid's 20 hits are
    transcripts and press releases. Causes: (a) the pool takes turns by firm only, so within a firm
    the 10 pool places go to the best-fused texts, which are prose; (b) cross-encoders trained on
    web QA (MS MARCO) score tables low. Refusal stays ok (no misleading chunk).
  - **Q25** (advisor compensation disclosures, gap_with_adjacent): refusal FAIL because
    `SCHW-10K-2025#558` ("Item 11. Executive Compensation ... incorporated by reference from the
    Proxy Statement", must-not in `evals/expected_chunks.yaml` line 155) comes back. It matches
    "compensation" by meaning and by keyword; the reranker scores it high, so **no score floor can
    remove it** (a floor removes only low scores). Passage recall rose (0 -> 0.25, `EDJ-10K-2025#30`).
    Starting point for #126: this is a semantic near-miss (executive vs advisor pay), not a filter
    failure; candidate remedies are #126/#127 decisions (e.g. rerank on the question without the
    firm list, a larger `RERANK_N`, or accepting it as a known hybrid weakness).
  - **Q29** (what MS pays its advisors, gap_with_adjacent): refusal stays ok, coverage 1 -> 0. fts
    returned `MS-10K-2025#170` (segment Wealth Management, the pattern hit), `#128`, `#153`; hybrid's
    three MS 10-K places (`MAX_PER_DOC` 3) went to `#702` (guarantee note: "likelihood of any payment
    by the Firm under these arrangements is remote"), `#417` (firm overview) and `#128`. The reranker
    sees the raw question with the word "pay" (`synonym_only` only shapes the keyword leg) and ranks
    "payment" passages up. `#702` is the same kind of trap as the listed must-not chunks
    (`#687`-`#699`) but is not on the list, so the eval does not count it (the answer key is C1's;
    not changed here). Whether `#153`/`#170` reached the 50-candidate pool is not in the reports;
    step 6 records it.

## Disk and download rule (TL machine)
Every download goes to D:. In the shell session only (never user env vars):
`FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`, `HF_HOME=D:\DevTools\cache\huggingface`,
`TMP`/`TEMP=D:\ALLPROJECTS\EDJ\cache\tmp`, `PIP_CACHE_DIR=D:\DevTools\cache\pip`. No download and no
pip install is planned (all models cached, both venvs exist). `.cache/`, `.eval-runs/`,
`.verify-runs/` are git-ignored.

## Design
- **Mode switch** `fts.search(q, k=K, mode=None)`: `mode` None -> `settings().retrieval_mode`
  (`RETRIEVAL_MODE`, default `fts`). `fts` -> `main`'s code path (with `synonym_only`). `hybrid` ->
  if `vectors_enabled()` is false, raise `HybridUnavailable` ("hybrid retrieval needs the optional
  vectors module: set CEE_VECTORS=on, install requirements-vectors.txt, see docs/RUN.md 'Hybrid
  retrieval'") **before** importing `hybrid`; else `hybrid.search(q, k)` (imported late). Anything
  else -> `ValueError`. So with vectors off, fts mode never imports `hybrid` or fastembed.
- **Database checks** (`hybrid.check_vectors`, before any model load): `to_regclass('chunk_embeddings')`
  is NULL -> `MissingVectors` ("apply the vectors module: `python -m cee.retrieve.embed --missing`
  with CEE_VECTORS=on"); any chunk without a `chunk_embeddings` row (`NOT EXISTS`) -> the same error
  with the count. Never a silent FTS fallback.
- **Models, cache only** (ADR-009): the embedding model through `embed.model()` from `main`
  unchanged (`ModelNotCached` -> `embed --fetch`). Reranker: `hybrid.reranker()` checks the cache
  folder first (table `RERANKERS = {name: (folder, "onnx/model.onnx", size)}` for MiniLM-L-12 and
  bge-reranker-base, same no-fastembed check as `embed.model_cached`), missing -> `RerankerNotCached`
  naming `FASTEMBED_CACHE_PATH`, the folder and `python -m cee.retrieve.hybrid --fetch`; present ->
  `TextCrossEncoder(..., local_files_only=True)`, no fallback download. `RERANK_MODEL` not in the
  table -> `ValueError` listing the known names. The branch's `embed.load_cached` (download on
  failure) and its test are dropped in the merge: `main`'s loader already surfaces a broken runtime
  directly (the PR #140 concern), and auto-download is what ADR-009 removed.
  `python -m cee.retrieve.hybrid --fetch` is the only path that downloads the reranker;
  `--check` loads both models from the cache and scores one pair.
- **`hybrid.search(q, k)`**:
  1. Gap path unchanged: unmapped firms only -> `[]`; firm filter leaves no named firm -> `[]`
     (as `main`'s fts). No model load, no SQL.
  2. Hard filters, the same fragments as fts mode in both legs: `entity_filter()`, `window_filter()`,
     `filters_sql()` (#63 date range, keywords). Entity+theme questions (#116) run a second,
     research part with `theme_filter()` instead of `entity_filter()`, as fts does.
  3. Legs, each ranked **per firm in every mode** (`PARTITION BY d.entity_id`; theme questions
     include `entity_id IS NULL` research as its own group), top `LEG_K` = 100 per firm. Keyword leg:
     fts words, synonyms and `rank_sql` (window questions: words only rank). Vector leg:
     `JOIN chunk_embeddings e USING (chunk_id) ... ORDER BY e.embedding <=> query_vector`; the window
     function reads every eligible row, so it is exact (no HNSW settings, no flag).
  4. RRF per firm: `score = sum over legs of 1 / (RRF_K + rank)`, `RRF_K` = 60, ties by `chunk_id`.
  5. Rerank pool: **(firm, document type) groups take turns** down their fused lists until
     `RERANK_N` = 50 (research part: `THEME_RERANK_N` = 20). Same grouping as fts's `pooled` CTE, so
     `select()`'s quotas have something from every firm and type to choose (Q21, Q24).
  6. Cross-encoder scores `(question, prefix + ' ' + text)`; `Hit.rank` = sigmoid(score).
  7. **Floor**: drop hits with `rank < RERANK_FLOOR` (absolute; not inside a time window, where
     fts also uses floor 0), then `select(pool, k, floor=0)` with fts's other constants
     (`MAX_PER_DOC`, `DUP_JACCARD`); window questions: `max_per_doc=WINDOW_MAX_PER_DOC`, newest
     first. Entity+theme: research `select(..., min(THEME_K, k), max_per_doc=THEME_MAX_PER_DOC)`,
     firm part gets `k - len(research)`, as fts.
  `RERANK_FLOOR` rule (step 7): grid {0.01, 0.05, 0.1}; the highest value whose run has the same
  tier-1 passage recall as the floor-0 run and loses no must-return passage the floor-0 run found
  on Q24, Q25, Q28, Q29, Q30 (drop as much weak text as possible without losing evidence); if none,
  0.01. Reported with every number; tuning is #126.
- **Q29 in both modes**: `config/entities.yaml` `synonym_only: [pay]` (an ambiguous word is searched
  only through its synonyms); `_search_terms` leaves it out of the FTS words after
  `expand_synonyms` has read it. General rule, not keyed to the answer key.
- **`ask(question, provider=None, log=True, progress=None, filters=None, mode=None)`**: passes `mode`
  to `search`; trace line `Searching the corpus: N passages from M documents` + ` (hybrid)` only in
  hybrid mode; `query_log.filters` gets `retrieval_mode`.
- **Reranker**: `Xenova/ms-marco-MiniLM-L-12-v2` (Apache-2.0, about 120 MB), chosen by the approved
  rule (Facts). No new LLM call (ADR-003); no new pip package (fastembed 0.9.1 already in
  `requirements-vectors.txt`).
- **Not done here (stated so #126 can pick it up):** a `hybrid-norerank` mode (#126 deliverable),
  tuning `FLOOR`/`MAX_PER_DOC`/`RERANK_N`/`RERANK_FLOOR`, a fix for Q25's `#558` or Q29's `#702`.

## Files to change (all on `tl/125-hybrid-retrieval`, reaching only `exp/hybrid`)
- Merge commit `origin/main` -> branch: conflict resolution in `src/cee/ask.py`,
  `src/cee/retrieve/embed.py` (take `main`'s file; drop `load_cached`), `src/cee/retrieve/fts.py`,
  and `tests/test_embed.py` (drop the `load_cached` test).
- `src/cee/retrieve/hybrid.py` - as Design: vectors/table checks, `chunk_embeddings` leg, per-firm
  legs in all modes, (firm, doc type) pool, research part, Ask filters, absolute floor, cache-only
  reranker, `--fetch` / `--check`; no ADR-008 references.
- `src/cee/retrieve/fts.py` (S1 reviews) - mode switch with the vectors gate, `synonym_only`,
  keyword helpers reused by the keyword leg (no behavior change in fts mode).
- `src/cee/config.py` - `Settings.retrieval_mode` (merges with `main`'s `vectors_enabled`).
- `src/cee/ask.py` - `mode` next to `main`'s `filters`, trace suffix, `retrieval_mode` in the log.
- `config/entities.yaml` (synonyms: S1 reviews; C1 FYI) - `synonym_only: [pay]` (already on branch).
- `scripts/eval_run.py` - `--mode fts|hybrid`, `retrieval_mode` in meta, `search_s`/`warmup_s`/median
  (already on branch); new: per-question `ranks` (each hit's `Hit.rank`, additive key) for #126.
- `scripts/verify_cee.py` - `RETRIEVAL_MODE` and `CEE_VECTORS` in `summary.json`.
- Tests: `tests/test_hybrid.py`, `tests/test_vectors_optional.py` (subprocess: hybrid importable
  with fastembed blocked; `search(mode="hybrid")` with vectors off raises `HybridUnavailable` and
  leaves `cee.retrieve.hybrid` and `fastembed` out of `sys.modules`), `tests/test_fts_synonyms.py`,
  `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`, `tests/test_eval_run.py`.
- `.env.example` - `RETRIEVAL_MODE=fts` and `RERANK_MODEL=` with a comment (hybrid needs
  `CEE_VECTORS=on`; experimental branch only).
- `docs/RUN.md` - "Hybrid retrieval (experimental branch `exp/hybrid`, #125)": install
  `requirements-vectors.txt`, `CEE_VECTORS=on`, `embed --fetch` and `hybrid --fetch` (or copy the
  models), `embed --missing` (applies `db/optional/vectors.sql`), `RETRIEVAL_MODE=hybrid`, `--check`,
  `eval_run --mode`; every PowerShell block has a bash block. Replaces the branch's draft (which
  said the reranker downloads by itself).
- `specs/retrieval.md` (S1 reviews) - "Retrieval modes" section without ADR references, saying
  hybrid lives on `exp/hybrid`; the open question "When would hybrid search be justified?" stays
  open (answered in #127); the branch's strike-through is reverted.
- `.claude/skills/verify-cee/features/ask-progress.md` - search line may end with " (hybrid)".
- Not changed: `docs/DECISIONS.md` (no ADR), `db/`, `build-snapshot.*`, `restore.*`, Box,
  `evals/questions.yaml`, `evals/expected_chunks.yaml`, prompts, UI (#128), `requirements*.txt`.

## Steps
0. Done 2026-11-05: `exp/hybrid` created from `origin/main` 9dc4c9b and pushed.
1. **Baseline on `main`'s code, before the merge.** Shell setup (rule above). `git worktree add
   D:\ALLPROJECTS\EDJ\wt-125-main origin/main`; core venv with `PYTHONPATH=D:\ALLPROJECTS\EDJ\wt-125-main\src`,
   `CEE_VECTORS` unset; log `cee.__file__`; `python scripts/eval_run.py --as-of 2026-10-29 --out
   D:\ALLPROJECTS\EDJ\repo\.eval-runs\p125r-fts-main`; `pytest -q` count (the "none fewer" number).
   Remove the worktree.
2. **Merge** `git merge origin/main` on `tl/125-hybrid-retrieval` (no rebase, no force-push).
   Resolve the three conflicts as in Files; drop `load_cached`; remove ADR-008 wording from
   `hybrid.py` and the spec. `pytest -q` in both venvs. Commit the merge, push.
3. **Move the vectors** (planned, not deleted data): check the backup lists
   (`pg_restore -l` on `cee-before-144.dump`); vectors venv, `CEE_VECTORS=on python -m
   cee.retrieve.embed --missing` -> applies `db/optional/vectors.sql`, `0 embedded, 0 still missing`;
   then `count(*) FROM chunk_embeddings` = 17183, `chunks.embedding` absent.
4. **fts after**, core venv (no fastembed installed), vectors off, `PYTHONPATH=<repo>\src`:
   `eval_run.py --mode fts --as-of 2026-10-29 --out .eval-runs/p125r-fts-after --baseline
   .eval-runs/p125r-fts-main/report.json`; script compares `chunk_ids` per question (Acceptance).
5. **Hybrid code** per Design + tests (fake scorer, fake fastembed module, no DB, no network).
   `EXPLAIN` of the vector leg for Q29 (per firm) and Q16 (theme) into the Progress log (expect a
   sequential scan of `chunk_embeddings`, no index scan).
6. **Hybrid evals**, vectors venv, `CEE_VECTORS=on`, baseline `p125r-fts-after`: floor 0
   (`p125r-hybrid-f0`), then 0.01 / 0.05 / 0.1; choose `RERANK_FLOOR` by the rule; the chosen run is
   copied to `p125r-hybrid`. A scratch script (not committed) records, for Q21, Q24, Q25, Q29,
   whether each must-return / must-not chunk was in the keyword leg, the vector leg, the 50-pool,
   its rerank score and why it was or was not kept; output in `.eval-runs/p125r-diag/`, summary in
   the Progress log for #126.
7. **Retrieval checks** on `p125r-hybrid`: Q4, Q7, Q26, Q27, Q29, Q30 per-question lines; Q26 sorted
   by `published_at` descending and no hit outside the window (one-line script over `report.json`
   and DB dates).
8. **Docs**: RUN.md (PowerShell + bash), `.env.example`, spec section, verify-cee recipe line.
9. **Final checks**: `pytest -q` in the core venv and in the vectors venv; `verify_cee.py run` with
   `RETRIEVAL_MODE=fts`, vectors off, core venv; then `RETRIEVAL_MODE=hybrid`, `CEE_VECTORS=on`,
   vectors venv. Offline reranker check (Acceptance). Reranker never fetched at query time:
   `--check` with `FASTEMBED_CACHE_PATH` pointed at a new empty folder and
   `HF_ENDPOINT=http://127.0.0.1:9` -> `RerankerNotCached` naming `--fetch`, the folder not created.
10. `/finish-task`: PR **base `exp/hybrid`**, both eval tables, the four-question diagnosis, timings,
    reranker choice, `0 real calls`, S1 (and C1 FYI) review requested. Body says "Part of #125"
    until S1 has reviewed (a merge into a non-default branch does not close an issue anyway; the
    reviewer closes #125 by hand when every item is done). No ADR, no escalation for an ADR.

**Stop rule (revised):** if a correctness gate in Acceptance fails and the fix is not inside this
Design (e.g. a hard filter cannot be expressed in a leg, or fts mode differs on a question other
than Q29), stop, log the numbers and bring the plan back for review. A PASS -> FAIL or lower
recall against fts is **not** a stop: it is reported with its diagnosis for #126.

Risks: hybrid keeps losing on some questions (reported, default stays `fts`, #126 tunes); the
(firm, doc type) pool spreads 50 places thin on theme questions with many groups (reported; #126
can raise `RERANK_N`); reranker CPU time about 8 s per question (reported); `synonym_only` may be
renamed by S1; the fts Q29 fix lives only on `exp/hybrid` (see open question in the PR); Mac runs
need a teammate.

## Acceptance
All checks on the PR head, local DB `corpus-2026-10-29` (vectors moved to `chunk_embeddings`),
`--as-of 2026-10-29`, mock provider, 0 real calls.

Correctness gates (must hold):
- [ ] **Hard filters, unit**: `test_hybrid.py` builds both leg SQLs for MER (finds the
      `entity_filter` segment clause), for a window query (`window_filter` clause), for Ask
      filters (date range and keyword clauses from `filters_sql`) and for an entity+theme question
      (research part uses `theme_filter`), in each leg.
- [ ] **Forbidden hits 0 on all 30** in `p125r-hybrid` (eval `forbidden` empty for every question;
      covers Q4, Q27, Q30 Merrill = no BAC chunk without a GWIM/Merrill segment, and Q7).
- [ ] **Q7**: every named firm (MS, MER, RJF) has at least one hit in hybrid.
- [ ] **Q26** in hybrid: no hit outside the 90-day window (`outside_window` empty), hits sorted
      newest first (step 7 script).
- [ ] **Q29 both modes**: no chunk from its `must_not_return` list in `p125r-fts-after` and
      `p125r-hybrid`; `MS-10K-2025#153` comes back in fts mode.
- [ ] **fts mode = `main`** except Q29: `p125r-fts-main` vs `p125r-fts-after` -> identical
      `chunk_ids` in the same order for 29 of 30 questions; only Q29 differs; no PASS -> FAIL.
- [ ] **No fastembed with vectors off**: `test_vectors_optional.py` subprocess cases pass, and the
      fts eval (step 4), pytest and verify-cee fts run in the core venv, which has no fastembed.
- [ ] **Hybrid refuses cleanly**: vectors off -> `HybridUnavailable`; no `chunk_embeddings` table
      or a chunk without a row -> `MissingVectors`; reranker not cached -> `RerankerNotCached`
      naming `--fetch`, no download, no folder created (unit with fakes + step 9 check).
- [ ] **Gap path**: unmapped-only question and an empty firm-filter intersection return `[]`
      without loading a model or opening a connection (unit).
- [ ] **Tests**: `rrf()` hand-worked example and ties; (firm, doc type) turn-taking; floor drops
      below-floor hits, keeps order, none inside a window; `select` called with `floor=0`; window
      newest first; mode switch (fts never imports `hybrid`, default `fts`, unknown -> `ValueError`);
      `pay` left out of FTS words; `ask(mode=...)` and trace suffix; `eval_run --mode`, `search_s`,
      `ranks`. `pytest -q` all pass in both venvs, none fewer than `main` (count from step 1) minus
      the dropped `load_cached` test.
- [ ] `python scripts/verify_cee.py run` -> VERIFY PASS, all features, fts (vectors off, core venv)
      and hybrid (`CEE_VECTORS=on`); each `summary.json` shows `RETRIEVAL_MODE` and `CEE_VECTORS`.
- [ ] Offline reranker: `python -m cee.retrieve.hybrid --check` with sockets blocked in-process ->
      scores printed, no error.
- [ ] Every new RUN.md PowerShell block has a bash block.
- [ ] S1 reviews the `fts.py` entry point, `synonym_only` and the spec section ("Part of #125"
      until then). Paid API calls: 0.

Reported, not gated (PR table; #126 tunes and gates):
- fts vs hybrid (floor 0 and each grid floor): PASS/FAIL per question with PASS -> FAIL listed,
  tier-1 doc and passage recall, refusal accuracy (gap and all-keyed), median `search_s`, `warmup_s`.
- The chosen `RERANK_FLOOR` and why; the reranker choice numbers (Facts).
- Diagnosis update for Q21, Q24, Q25, Q29 from step 6 (did the pool change fix Q21/Q24?).

Why these gates and not PASS/FAIL: the old gate ("no PASS -> FAIL vs fts") judged quality with
fts's constants (`FLOOR`, `MAX_PER_DOC`, `K`) on a different score scale; #126 exists to tune those
per mode, and the default stays `fts` on a branch that never reaches `main`. What #125 must
guarantee is that hybrid cannot break a ground rule or invariant: hard filters in SQL, the gap
path, windows, and fts unchanged.

Open items for teammates (listed on the issue, not required checks):
- Mac (Intel and Apple Silicon): `hybrid --check` and `eval_run.py --mode hybrid` on `exp/hybrid`.
- Offline teammates: the reranker is not in the shared `models/` folder yet (copy it there or use
  `hybrid --fetch` once).

## Progress log
- 2026-10-30 10:38 - plan written on `tl/125-hybrid-retrieval` from main 3fa63a9 (Q29 fts diagnosis
  and the `pay` dry run were read-only queries on the local DB; no file other than this plan changed).
- 2026-10-30 10:46 - plan review round 1 (e7118f6): changes requested. Added theme questions
  (HNSW path) and `EXPLAIN` to the exact-scan check, per-question search timing in `eval_run.py`,
  `retrieval_mode` naming, ADR-001 Status-line-only change, a stop rule, the Q26 order check,
  the corrected Q29 dry-run wording and the offline-reranker note.
- 2026-10-30 10:47 - plan approved (round 2, 2e649c4). Step 1: `embed --missing` started in the
  background; FTS "before" eval on 2e649c4 code (`p125-fts-before`): PASS 27 / FAIL 3 (Q15, Q19,
  Q29), tier-1 docs 0.796, passages 0.347, refusal gap 4/5.
- 2026-10-30 10:56 - steps 2, 3, 5, 6 coded (3f637e6): `load_cached`, mode switch, `synonym_only`,
  `hybrid.py`, `ask(mode=)`, `eval_run --mode` + timing, verify summary. Deviations: the trace adds
  " (hybrid)" only in hybrid mode (fts line unchanged); `test_ask_page_trace.py` needed the new
  `search(q, mode=None)` signature in its fakes. `pytest -q`: 248 passed, 1 skipped.
- 2026-10-30 10:58 - fts after (`p125-fts-after`, baseline `p125-fts-before`): identical chunk_ids
  on 29/30, only Q29 differs; PASS 28 / FAIL 2 (Q15, Q19); docs 0.796, passages 0.402; refusal gap
  5/5, all keyed 10/10; median search 1.19 s (warm-up excluded).
- 2026-10-30 11:00 - step 7: both rerankers downloaded to D:\ALLPROJECTS\EDJ\cache\fastembed.
  `--check`: MiniLM-L-12 scores [-1.125, -1.413] (advisor pay vs guarantee), bge-reranker-base
  [0.295, -2.736].
- 2026-10-30 11:24 - `embed --missing` done: 17183 embedded, 0 NULL (2166 s).
- 2026-10-30 11:26 - step 4: per-firm vector leg = exact scan (Q4, Q7, Q26, Q29 identical; EXPLAIN:
  seq scan + window sort). Theme leg via HNSW differed (ef_search 100: Q16 90/100, Q21 98/100;
  ef_search 200: Q16 93/100). Per the plan, the theme leg is now exact too
  (`EXACT_VECTOR_SEARCH = True`): Q16, Q17, Q21 identical; EXPLAIN: seq scan + top-N sort.
- 2026-10-30 11:45 - step 8, no-floor hybrid evals (baseline `p125-fts-after`):
  MiniLM-L-12 (`p125-hybrid-minilm-f0`): PASS 17 / FAIL 13, docs 0.471, passages 0.265, refusal
  gap 4/5 (Q25 `SCHW-10K-2025#558`), median search 8.5 s. bge-reranker-base (`p125-hybrid-bge-f0`):
  PASS 13 / FAIL 17, docs 0.509, passages 0.271, refusal gap 4/5 (same chunk), median 25.0 s.
  Forbidden 0 everywhere; Q26 PASS; Q29 refusal ok but coverage 0 (no MS 10-K WM chunk).
  **Stop rule fired:** both rerankers turn many PASS into FAIL already at floor 0, and a floor only
  removes hits, so no floor in the grid can meet the rule. Cause found: `select()`'s relative
  `FLOOR` (0.3 x the firm's best) on sigmoid rerank scores drops most of the pool (e.g. Q30 1 hit,
  Q19 4, Q4 6 vs fts 20, 12, 11). Diagnostic only (not a fix, not committed as a setting):
  MiniLM with `select()` floor 0 and no rerank floor (`p125-diag-minilm-noselectfloor`): PASS 24 /
  FAIL 6, docs 0.693, passages 0.428 (fts 0.402), refusal gap 4/5, median 8.2 s; PASS -> FAIL on
  Q21, Q24, Q25, Q29. Stopped here: the plan goes back for review before step 9.
- 2026-11-05 16:02 - **plan revision 2** (no code changed, `main` not merged yet). Inputs: the
  step-8 stop, PR #145 (#144, ADR-009: vectors optional, `chunk_embeddings`, `CEE_VECTORS`,
  cache-only models), #116 and #63 on `main` (entity+theme research part, Ask filters: both now in
  the hybrid Design), the sponsor's no-vectors-on-`main` constraint and the TL decision to keep
  hybrid on `exp/hybrid`. Created and pushed `exp/hybrid` from `origin/main` 9dc4c9b; the PR now
  targets it. Removed ADR-008 / ADR-001 edits and the ADR escalation (decision ADR -> #127). Design:
  `select(floor=0)` + absolute `RERANK_FLOOR` (numbers in Facts), per-firm legs in all modes,
  (firm, doc type) rerank pool, research part for entity+theme, `filters_sql` in both legs,
  vectors gate before importing `hybrid`, cache-only reranker with `--fetch`. Reranker settled:
  MiniLM-L-12. Gates: correctness only; PASS/FAIL and recall reported for #126. Diagnosed Q21
  (theme pool filled with research), Q24 (pool by firm only; tables score low), Q25 (`#558`
  executive compensation scores high; no floor can remove it), Q29 (reranker sees "pay"; `#702`
  guarantee chunk not on the must-not list). Read-only facts: merge conflicts in `ask.py`,
  `embed.py`, `fts.py`; DB still `chunks.embedding` 17183, no `chunk_embeddings`, backup in
  `cache\backups`; all three models cached; core venv `wt-144\.venv` has no fastembed.
