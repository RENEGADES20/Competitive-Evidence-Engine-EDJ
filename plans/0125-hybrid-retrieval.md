# 0125 - Hybrid retrieval: keyword + vector, RRF, local rerank, per-request mode

Issue: #125    Role: TL    Spec: specs/retrieval.md (S1 owns `fts.py`: S1 reviews), ADR-001, ADR-003

## Goal
A second retrieval mode, `hybrid`, chosen per request (`search(q, mode=...)`, `ask(..., mode=...)`,
default from `RETRIEVAL_MODE`, default `fts`). Inside the same SQL entity / segment / window
`WHERE`, it fuses keyword and vector candidates with RRF, reranks them with a local cross-encoder,
drops weak matches below a score floor and hands the rest to the same `select()` quotas.
`fts` mode keeps today's results for every question except Q29, whose misleading chunk goes away
in both modes. The eval compares both modes on the question bank (the comparison ADR-001 asks for).

## Facts checked before planning (2026-10-30, branch base 3fa63a9, nothing installed)
- Local DB `cee-db`: snapshot `corpus-2026-10-29`, 17,183 chunks, **0 embeddings**, pgvector 0.8.1.
  Vectors come from `python -m cee.retrieve.embed --missing` (#124, about 18 min, offline, model
  cache `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`). No `build-snapshot`, nothing
  written to Box: publishing the first vector snapshot is a separate TL step (open on #124).
- Latest FTS eval on this snapshot (`.eval-runs/p123-no-vector`, `p124-test-snapshot`, as of
  2026-10-29): PASS 27 / FAIL 3 (Q15, Q19, Q29), tier-1 doc recall 0.796, passage recall 0.347,
  refusal gap questions 4/5. (The issue's 0.809 is #102 on corpus-2026-10-22.)
- **Q29 diagnosis (fts mode).** Search terms `pay financial advisors`, synonyms of `pay`:
  `compensation`, `payout`. Matches: `MS-10K-2025#696` (FICC client clearing guarantees, must-not)
  has `pay` ("pay any net liquidation amount") and `payout` -> rank 9.80; the answer chunk
  `MS-10K-2025#153` ("formulaic payouts ... compensation") has `compensation` and `payout`
  -> 8.52. `MAX_PER_DOC` = 3 lets `#170`, `#128`, `#696` in from MS-10K-2025. In filings the bare
  verb "pay" almost always means paying an obligation, not advisor pay. A dry run with the bare
  word left out of the FTS words (synonyms kept) gives `#153` in and no must-not chunk; in the
  MS 10-K `#170` and `#128` stay, and two transcript slots change (out `MS-TR-2025Q2#26`,
  `MS-TR-2024Q4#56`; in `MS-TR-2025Q4#15`, `MS-TR-2025Q4#8`). `pay` occurs in no other question of `evals/questions.yaml` (only Q29, line
  442), so this changes only Q29 in the bank.
- Rerankers in fastembed 0.9.1 (already pinned, `TextCrossEncoder`, ONNX, no new package, so no
  new wheel question on Windows / Intel Mac / Apple Silicon; onnxruntime stays 1.23.2):
  `BAAI/bge-reranker-base` (MIT, 1.04 GB, the issue's example) and
  `Xenova/ms-marco-MiniLM-L-12-v2` (Apache-2.0, 0.12 GB). Both download into the same fastembed
  cache on D:. Their scores are logits; we map them to 0..1 with a sigmoid so `select()`'s
  relative `FLOOR` still works.
- pgvector HNSW with a `WHERE` filter returns at most `hnsw.ef_search` (default 40) rows unless
  iterative scans are on. 0.8.1 has `hnsw.iterative_scan`; we set it per transaction
  (`SET LOCAL hnsw.iterative_scan = strict_order`, `hnsw.ef_search = 100`); `max_scan_tuples`
  (20,000) exceeds the corpus. `EXPLAIN` (plan review round 1): the per-firm leg
  (`PARTITION BY entity_id`) reads every eligible row and sorts, so it is exact; only the
  no-firm (theme) leg, `ORDER BY ... LIMIT 100`, uses the HNSW index. Step 4 checks both shapes.
- PR #140 review note 3: `embed.model()` catches every exception from the cached load and then
  downloads, so a broken onnxruntime shows up as a download error. Fixed here (step 2).
- The stray `efsmain` line in `docs/RUN.md` (#124 open item) is already gone on main.

## Disk and download rule (TL machine)
Every download goes to D:. In the shell session only (never user env vars):
`FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`, `HF_HOME=D:\DevTools\cache\huggingface`,
`TMP`/`TEMP=D:\ALLPROJECTS\EDJ\cache\tmp`, `PIP_CACHE_DIR=D:\DevTools\cache\pip` (no pip install is
planned). Reranker downloads: at most 1.04 + 0.12 GB. `.cache/`, `.eval-runs/`, `.verify-runs/`
are git-ignored.

## Design
- `fts.search(q, k=K, mode=None)`: `mode` None -> `settings().retrieval_mode` (`RETRIEVAL_MODE`,
  default `fts`). `fts` -> today's code path unchanged; `hybrid` -> `hybrid.search(q, k)` (imported
  late, so fts mode never loads a model); anything else -> `ValueError`.
- `hybrid.search(q, k)`:
  1. Gap path first, unchanged: unmapped firms only -> `[]`, no model load, no SQL.
  2. Fails loudly (clear message: run `python -m cee.retrieve.embed --missing` or restore a
     snapshot built after #124) when any chunk has `embedding IS NULL`; never a silent FTS fallback.
  3. Same `entity_filter()` and `window_filter()` fragments in both legs (hard filters in SQL).
     Keyword leg: the FTS words, synonyms and `rank_sql` of fts mode (window questions: words only
     rank, as in fts). Vector leg: `ORDER BY c.embedding <=> query_vector`, query from
     `embed_query(question)`. Each leg: top `LEG_K` = 100 per named firm (`PARTITION BY entity_id`;
     theme questions: top 100 overall).
  4. RRF: `score = sum over legs of 1 / (RRF_K + rank)`, `RRF_K` = 60, ranks from 1, ties by
     `chunk_id`. Pure function `rrf()`.
  5. Rerank pool: firms take turns down the RRF list until `RERANK_N` = 50 candidates (so Q7's
     three firms all reach the reranker). Cross-encoder scores `(question, prefix + ' ' + text)`;
     `Hit.rank` = sigmoid(score).
  6. Floor: drop hits with `rank < RERANK_FLOOR` (outside time windows only; a "what's new"
     question names no topic, as in fts `floor=0`). Then the same `select()` with the same
     constants; window questions use `floor=0, max_per_doc=WINDOW_MAX_PER_DOC` and newest first,
     as in fts.
- Q29 in both modes: `config/entities.yaml` gets `synonym_only: [pay]` (an ambiguous word is searched
  only through its synonyms); `_search_terms` leaves such a word out of the FTS words after
  `expand_synonyms` has read it. General rule, not keyed to the answer key; it touches only
  questions that contain the bare word.
- `ask(question, provider=None, log=True, progress=None, mode=None)`: passes `mode` to `search`;
  the trace line becomes `Searching the corpus: N passages from M documents (hybrid)` (suffix
  only, so `verify_cee.py`'s regex still matches); `query_log.filters` gets `retrieval_mode`.
- Reranker model: both candidates are run in the hybrid eval (step 8). Rule: keep
  `BAAI/bge-reranker-base` only if its tier-1 passage recall is at least 0.02 above MiniLM-L-12's,
  its refusal accuracy is not lower, and its median hybrid search time is <= 5 s per question on
  this laptop; otherwise `Xenova/ms-marco-MiniLM-L-12-v2` (8x smaller for offline teammates).
  `RERANK_FLOOR`: the lowest of {0.01, 0.05, 0.1} that keeps every must-not chunk of Q24, Q25,
  Q28, Q29, Q30 out without losing a must-return passage the no-floor run found. Constants live in
  `hybrid.py`; `RERANK_MODEL` can be overridden by an environment variable of the same name (used
  for the comparison, listed as optional in `.env.example`); tuning them is #126.
- No new LLM call (ADR-003: the reranker is a local deterministic model, retrieval stays
  deterministic). No new pip package.

## Files to change
- `src/cee/retrieve/hybrid.py` (new) - legs, `rrf()`, rerank + floor, `search()`; `python -m
  cee.retrieve.hybrid --check` loads both models and scores one pair (offline check).
- `src/cee/retrieve/fts.py` (S1 reviews) - `search(..., mode=None)` entry point; `synonym_only`
  words left out of the FTS words; helpers the keyword leg reuses split out without behavior change.
- `src/cee/retrieve/embed.py` - one loader `load_cached(cls, name)` shared by the embedder and the
  reranker: tries `local_files_only=True`, prints the first exception (type and message) to stderr
  before downloading, and chains it if the download fails too.
- `src/cee/config.py` - `Settings.retrieval_mode` from `RETRIEVAL_MODE` (default `fts`).
- `src/cee/ask.py` - `mode` argument, trace suffix, `retrieval_mode` in the query log.
- `config/entities.yaml` (synonyms section: S1 reviews; C1 FYI as owner of the file) -
  `synonym_only: [pay]`.
- `scripts/eval_run.py` - `--mode fts|hybrid` (default `RETRIEVAL_MODE`), recorded as
  `retrieval_mode` in report meta and header (the meta key `mode` stays mock/real, the per-question
  `mode` stays entity/theme). Times `search()` per question (`search_s` in `report.json`) and
  writes the median to the summary and the report header. Model load is kept out: before the
  timed loop, one untimed warm-up `search()` on the first question, its time saved as `warmup_s`.
- `scripts/verify_cee.py` - record `RETRIEVAL_MODE` in `summary.json` (the app subprocess already
  inherits the shell environment).
- `tests/test_hybrid.py` (new), `tests/test_fts_synonyms.py`, `tests/test_embed.py`,
  `tests/test_ask_progress.py`, `tests/test_eval_run.py` - see Acceptance.
- `.env.example` - `RETRIEVAL_MODE=fts` with a comment.
- `docs/RUN.md` - "Hybrid retrieval (#125, optional)": `RETRIEVAL_MODE=hybrid` in `.env`, fill
  missing vectors, reranker download size, offline check. It says the Box `models/` folder holds
  only the embedding model, so the first hybrid question needs HuggingFace access to fetch the
  reranker (adding it to Box is part of the vector-snapshot TL step). Every PowerShell block has a bash block.
- `docs/DECISIONS.md` - new ADR-008 "Hybrid retrieval as a per-request mode" with the eval numbers;
  ADR-001 body untouched (old ADRs are not edited), only its Status line becomes "Accepted;
  amended by ADR-008" (ADR-008 states that `chunks.embedding` is now filled). **ADR change: the PR
  is escalated to the TL**, not merged by the reviewer.
- `specs/retrieval.md` (S1 reviews) - retrieval modes section, Q29 rule, open question
  "When would hybrid search be justified?" answered with a link to ADR-008.
- `.claude/skills/verify-cee/features/ask-progress.md` - the search line may end with the mode.
- No change to `build-snapshot.*`, `restore.*`, Box, `evals/questions.yaml`, prompts or the UI (#128).

## Steps
1. Shell setup on D: (see rule above). Start `python -m cee.retrieve.embed --missing` in the
   background (about 18 min) -> `17183 embedded, 0 still NULL`. Meanwhile, before any code change,
   run the FTS "before" eval on this commit:
   `python scripts/eval_run.py --as-of 2026-10-29 --out .eval-runs/p125-fts-before`.
2. `embed.py`: shared `load_cached()`, first-exception logging; unit test with a fake model class
   (cached load raises `RuntimeError("bad wheel")`, download raises `OSError`) -> stderr names
   `bad wheel`, the raised error chains it.
3. `config.py` + `fts.search` mode switch + `synonym_only`; tests. Run fts eval
   (`--out .eval-runs/p125-fts-after --baseline .eval-runs/p125-fts-before/report.json`) and the
   chunk_id comparison (Acceptance) before going on.
4. `hybrid.py` legs (SQL builders as functions, so tests can read the filters). Save `EXPLAIN`
   for both leg shapes (per-firm: Q29; theme: Q16) in the Progress log. Check the vector leg
   against an exact scan (`SET LOCAL enable_indexscan = off`) on Q4, Q7, Q26, Q29 (per-firm) and
   Q16, Q17, Q21 (theme, the HNSW path): expected identical chunk_ids in the same order. If a theme
   question differs, raise `hnsw.ef_search` to 200 and re-check; if it still differs, make the
   theme leg exact too (`SET LOCAL enable_indexscan = off`) and re-check.
5. `rrf()`, rerank pool (firms take turns), reranker via `load_cached(TextCrossEncoder, ...)`,
   sigmoid, floor, `select()`; unit tests with a fake scorer (no DB, no network).
6. `ask.py` `mode`, trace suffix, log; `eval_run.py --mode`; `verify_cee.py` summary; tests.
7. Download both rerankers into the D: cache (`python -m cee.retrieve.hybrid --check` with
   `RERANK_MODEL` overridden in the shell for the second one) and time them.
8. Hybrid evals, as of 2026-10-29, baseline `p125-fts-after`: one per reranker with no floor, then
   the chosen reranker with the floor grid. Pick model and floor by the rules in Design; record
   every number in the Progress log. **Stop rule:** if no floor in the grid meets the rule, or
   hybrid turns any question from PASS to FAIL against `p125-fts-after`, stop, log the numbers
   and bring the plan back for review before going on.
9. `RETRIEVAL_MODE=hybrid` retrieval check for Q4, Q7, Q26, Q27, Q29, Q30 (read the per-question
   lines of the hybrid report); for Q26 also check the retrieved list is sorted by `published_at`
   descending (one-line script over `p125-hybrid/report.json` and the DB dates).
10. Docs: RUN.md (PowerShell + bash), `.env.example`, ADR-008 + ADR-001 wording, spec section,
    verify-cee recipe line.
11. `pytest -q`; `verify_cee.py run` with `RETRIEVAL_MODE=fts`, then with `RETRIEVAL_MODE=hybrid`.
12. `/finish-task`: PR with both eval tables, timings, model choice, `0 real calls`, S1 (and C1 FYI)
    review requested, "ADR change: escalate to TL".

Risks: hybrid can lower recall on some questions (the default stays `fts`; the ADR reports it
honestly); the reranker is slow on CPU (timed; the size rule picks the small one); a wrong floor
empties gap questions' adjacent evidence (the floor rule checks must-return passages);
`synonym_only` is a new config key S1 may prefer to name differently; teammates on the published
`corpus-2026-10-29` have no vectors, so hybrid fails loudly there until the vector snapshot is
published (separate TL step); Mac runs need a teammate.

## Acceptance
All checks on the PR head, local DB `corpus-2026-10-29` + `--missing` vectors, `--as-of 2026-10-29`,
mock provider.
- [ ] Linked questions, hybrid (`.eval-runs/p125-hybrid`): **Q4, Q27, Q30** (Merrill) and **Q7**
      forbidden 0, so no BAC chunk without a GWIM/Merrill segment; **Q7** every named firm (MS,
      MER, RJF) has hits; **Q26** refusal `ok` (nothing older than the 90-day window, hits
      newest first); **Q29** refusal `ok`; **Q30** refusal `ok`. Forbidden 0 on all 30.
- [ ] Hard filters hold in hybrid (unit): `test_hybrid.py` builds both leg SQLs for MER and for a
      window query and finds the `entity_filter` segment clause and the `window_filter` clause in
      each.
- [ ] Q29 in both modes: no chunk from its `must_not_return` list; refusal `ok` in
      `p125-fts-after` and `p125-hybrid`; `MS-10K-2025#153` comes back in fts mode.
- [ ] `RETRIEVAL_MODE=fts` gives the same results as before: a script comparing
      `p125-fts-before` and `p125-fts-after` `report.json` -> identical `chunk_ids` (same order)
      for 29 of 30 questions; only Q29 differs. PASS count 28 (Q29 FAIL -> PASS), no PASS -> FAIL,
      refusal accuracy gap questions 5/5.
- [ ] Eval comparison fts vs hybrid in the PR and ADR-008: PASS/FAIL, tier-1 doc and passage
      recall, refusal accuracy (gap and all-keyed), forbidden hits, median search time, per
      reranker. Hybrid: no question PASS -> FAIL vs `p125-fts-after`, refusal accuracy not lower
      (gap 5/5). Recall is reported, not gated (default stays `fts`).
- [ ] Vector leg = exact scan (step 4): Q4, Q7, Q26, Q29 (per-firm shape) and Q16, Q17, Q21
      (theme shape, HNSW) -> identical chunk_ids in the same order, with the final settings;
      `EXPLAIN` of both shapes in the Progress log.
- [ ] Search time: `report.json` of each fts and hybrid run has `search_s` per question,
      `warmup_s`, and the median in the header; the reranker rule uses these medians.
- [ ] Tests: `test_hybrid.py` - `rrf()` scores and ties on a hand-worked example; rerank floor
      drops below-floor hits and keeps order; no floor inside a window; unmapped-only question
      returns `[]` without loading a model; NULL embeddings raise the clear error; window questions
      come back newest first; mode switch
      (`fts` never imports `hybrid`, `hybrid` calls `hybrid.search`, default from `RETRIEVAL_MODE`
      is `fts`, unknown mode -> `ValueError`). `test_fts_synonyms.py` - `pay` left out of the FTS
      words, `compensation`/`payout` kept. `test_embed.py` - first exception logged and chained.
      `test_ask_progress.py` - `ask(mode=...)` reaches `search` and the trace suffix.
      `test_eval_run.py` - `--mode` lands in meta as `retrieval_mode`; `search_s` and the median
      are written (fake search, no DB). Real-model
      rerank test only when cached (never downloads).
- [ ] `pytest -q` -> all pass, none fewer than on main (228 at the PR #140 review).
- [ ] `python scripts/verify_cee.py run` -> VERIFY PASS, all 7 features, with `RETRIEVAL_MODE=fts`
      and again with `RETRIEVAL_MODE=hybrid`; each `summary.json` shows the mode.
- [ ] Offline reranker: `python -m cee.retrieve.hybrid --check` with `HF_HUB_OFFLINE` and
      `TRANSFORMERS_OFFLINE` unset and sockets blocked in-process -> scores printed, no error.
- [ ] Every new RUN.md PowerShell block has a bash block (grep count equal in the new section).
- [ ] S1 reviews the `fts.py` entry point, the `synonym_only` rule and the spec section (requested
      in the PR; the PR says "Part of #125" until S1 has reviewed).
- [ ] Paid API calls: 0 (mock only; the reranker is local).

Open items for teammates (not required checks; listed on the issue, "Part of #125" while open):
- Mac (Intel and Apple Silicon): `python -m cee.retrieve.hybrid --check` and
  `python scripts/eval_run.py --mode hybrid` on a vector snapshot, once the TL publishes one.
- Offline teammates: hybrid needs the reranker from HuggingFace until the TL adds it to Box
  `models/` with the vector snapshot (separate TL step).

## Progress log
- 2026-10-30 10:38 - plan written on `tl/125-hybrid-retrieval` from main 3fa63a9 (Q29 fts diagnosis
  and the `pay` dry run were read-only queries on the local DB; no file other than this plan changed).
- 2026-10-30 10:46 - plan review round 1 (e7118f6): changes requested. Added theme questions
  (HNSW path) and `EXPLAIN` to the exact-scan check, per-question search timing in `eval_run.py`,
  `retrieval_mode` naming, ADR-001 Status-line-only change, a stop rule, the Q26 order check,
  the corrected Q29 dry-run wording and the offline-reranker note.
