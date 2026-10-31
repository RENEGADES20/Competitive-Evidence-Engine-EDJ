# 0144 - Vectors as an optional module, off by default

Issue: #144    Role: TL    Spec: specs/retrieval.md, docs/DECISIONS.md ADR-001

## Goal
With vectors off (the default), nothing on `main` needs pgvector, fastembed, onnxruntime, a model
file or network access, and `fts` retrieval returns exactly the same chunks as today. Turning
vectors on (`CEE_VECTORS=on`) brings back today's embedding behavior, with vectors in their own
table `chunk_embeddings` and no automatic model download.

## Files to change
- `docs/DECISIONS.md` - new **ADR-009** (core retrieval is extension-free and model-free; vectors
  are an optional module, off by default, never required by build, app or eval in `fts` mode).
  ADR-001 gets one Status-line pointer to ADR-009, nothing else.
- `db/schema.sql` - header comment only (no `vector`, points at `db/optional/vectors.sql`).
- `db/upgrade.sql` - core only: the `CREATE EXTENSION` / `embedding` column / HNSW index lines
  go away; the file stays as the home of future idempotent core additions (comments only today).
- `db/optional/vectors.sql` (new, idempotent, one transaction) - `CREATE EXTENSION IF NOT EXISTS
  vector`; `chunk_embeddings(chunk_id text PRIMARY KEY REFERENCES chunks ON DELETE CASCADE,
  embedding vector(384) NOT NULL)` + HNSW index (`vector_cosine_ops`); one-time move in a `DO`
  block: if `chunks.embedding` exists, copy its non-NULL rows (`ON CONFLICT DO NOTHING`), then
  check by anti-join that no chunk with a non-NULL `chunks.embedding` lacks a `chunk_embeddings`
  row (not raw totals, which `ON CONFLICT DO NOTHING` could mask) and `RAISE EXCEPTION` if any
  does (rolls everything back), then drop the column (its index goes with it). Dynamic SQL (`EXECUTE`) so the block parses when the column is gone.
- `docker-compose.yml` - keeps the pgvector image (switching on needs no new image); mounts only
  `01-schema.sql` + `02-upgrade.sql` (as today); comment says why the optional SQL is not mounted.
- `src/cee/config.py` - `vectors_enabled()`: reads `CEE_VECTORS` (env or `.env`); `on|true|1|yes`
  -> on, empty/`off|false|0|no` -> off, anything else -> `ValueError` naming the variable.
  (Not in the issue's Inputs; the parser has to live where `embed` and later #125 can share it
  without importing the embedding module.)
- `src/cee/retrieve/embed.py`
  - load path: checks the model folder in the cache (`<cache>/models--Qdrant--bge-small-en-v1.5-onnx-Q`
    with `snapshots/*/model_optimized.onnx`) **before** calling fastembed, because fastembed's
    own `define_cache_dir` creates the folder; missing -> `ModelNotCached` error naming
    `FASTEMBED_CACHE_PATH`, the folder looked in, and the command `python -m cee.retrieve.embed --fetch`.
    Present -> `TextEmbedding(..., local_files_only=True)`, no fallback download. No `mkdir`.
  - `--fetch`: the only path that downloads (creates the folder, then `TextEmbedding(model, cache_dir)`).
  - `--missing`: refuses with exit code 2 and a one-line message when `CEE_VECTORS` is off; when on,
    applies `db/optional/vectors.sql` (read from the repo, run through psycopg), then embeds every
    chunk with no `chunk_embeddings` row (`LEFT JOIN ... IS NULL`, same shortest-first order) and
    inserts `(chunk_id, %s::vector)`; the count of chunks still missing a row decides the exit code.
  - `--query` works with vectors on or off (no database), so a teammate can test the model alone.
  - `fastembed` stays imported only inside functions; CLI errors print one line, no traceback.
- `tests/test_embed.py` - existing tests adapted to `chunk_embeddings`; new: empty cache ->
  `ModelNotCached` with `FASTEMBED_CACHE_PATH` and `--fetch` in the message, the fake
  `TextEmbedding` is never called and no folder is created (path that does not exist stays absent);
  cached-folder case calls it with `local_files_only=True` only; `--fetch` calls the downloader;
  `--missing` with vectors off exits 2 without connecting. Fake `fastembed` module via
  `monkeypatch.setitem(sys.modules, ...)`, so these run without the extra. The real-model test
  uses `pytest.importorskip("fastembed")` plus the existing "model cached" skip.
- `tests/test_vectors_optional.py` (new) - `db/schema.sql` + `db/upgrade.sql` contain no `vector`
  type and no `CREATE EXTENSION` (word match, `tsvector` allowed); `db/optional/vectors.sql` has
  the table, index and move; a subprocess that blocks `fastembed`/`onnxruntime`
  (`sys.modules[...] = None`) can import `cee.retrieve.fts`, `cee.ask`, `cee.app.components` and
  `cee.app.views.*` (what `streamlit_app.py` imports; importing `streamlit_app` itself would run
  the page); `vectors_enabled()` parsing table incl. the error case; `docker-compose.yml` mounts
  no file from `db/optional/`.
- `requirements.txt` - drop `fastembed` / `onnxruntime` (and their comment).
- `requirements-vectors.txt` (new) - `fastembed==0.9.1`, `onnxruntime==1.23.2` with today's comment
  (Intel Mac / macOS 13 note).
- `pyproject.toml` - `[project.optional-dependencies] vectors = [same two pins]`.
- `.github/workflows/tests.yml` - unchanged install line (`requirements.txt` only); add a comment
  that this is on purpose (proves the core needs no vectors extra). If the issue reviewer prefers,
  an explicit `python -c "import fastembed"` that must fail can be added; planned: the comment only.
- `scripts/_common.sh` + `scripts/_common.ps1` - `vectors_on` / `Test-VectorsOn` (same parsing
  as Python, unknown value stops the script); `apply_vectors_sql` / `Invoke-VectorsSql` pipes
  `db/optional/vectors.sql` from the checkout into `psql` over stdin (`docker exec -i`), because
  the file is deliberately not mounted; model-folder helpers (`model_cache_env`, `copy_model_to_share`
  and the `.ps1` twins) unchanged but only called when on; `upgrade_schema` comment updated.
- `scripts/build-snapshot.sh` + `.ps1` - step 4 and step 7 run only when on; when off they print
  `4/7 Embedding skipped (CEE_VECTORS is off)` and `7/7 Embedding model skipped (CEE_VECTORS is off)`.
  When on: apply the optional SQL, then `embed --missing` (as today, "a chunk without a vector
  stops the build"). Header comment updated.
- `scripts/restore.sh` + `.ps1` - after `upgrade_schema`, apply `db/optional/vectors.sql` only when
  on (prints which).
- `.env.example` - `CEE_VECTORS=off` with a one-line comment; the `FASTEMBED_CACHE_PATH` comment
  says it matters only when vectors are on and the model is never downloaded by itself.
- `docs/RUN.md` - section 1: the default needs nothing extra (no extension, no model, no
  download); the "Database image update" and "Embedding model" blocks become one optional section
  "Vectors (optional, off by default)": install `requirements-vectors.txt`, fetch
  (`python -m cee.retrieve.embed --fetch`) or copy the `models/` folder from the shared corpus folder, set `CEE_VECTORS=on`,
  apply the optional SQL (restore does it when on), embed (`--missing`); every step with a
  PowerShell and a bash block. Build-snapshot paragraph and troubleshooting rows updated.
- `docs/ARCHITECTURE.md` - schema section: `chunks` loses `embedding`; optional `chunk_embeddings`
  table described as part of the vectors module.
- `docs/DASHBOARD.md` - the weekly snapshot checklist line "Every chunk has a vector (#124)"
  becomes "only when vectors are on: every chunk has a row in `chunk_embeddings`". (Not in the
  issue's Inputs; without this the checklist tells the tech lead to run a query that now fails.)
- Issue #125 - comment only (no file on its branch): when it resumes, hybrid reads
  `chunk_embeddings` and stays behind `CEE_VECTORS`; the shared local DB was migrated (see below).

Not touched: `src/cee/retrieve/hybrid.py` and branch `tl/125-hybrid-retrieval`, `fts.py`, any
ranking, synonyms, chunking, other portability work, publishing a snapshot.

## Steps
**Python environments (every check below uses one of these two, never the main checkout's venv).**
The main checkout's `.venv` has `cee` installed editable from the main checkout's `src` (the
paused #125 branch), and the scripts look for `<worktree>\.venv`. So:
- **Core venv** `<worktree>\.venv` (git-ignored), its own, not linked to any other venv:
  `<python 3.11> -m venv .venv`, then the core pins only and `pip install -e .`. At step 0
  `requirements.txt` still lists fastembed/onnxruntime, so step 0 installs it filtered
  (`grep -v -E '^(fastembed|onnxruntime)' requirements.txt > <scratch>\req-core.txt`); after step 4
  `pip install -r requirements.txt` must be a no-op. Plus `requirements-verify.txt` (Playwright)
  for verify-cee, with `PLAYWRIGHT_BROWSERS_PATH=<cache>\ms-playwright` (browsers already there).
  This venv **never** gets fastembed/onnxruntime: it is the real "without the vectors extra"
  environment for pytest, eval, smoke, verify-cee and both `.ps1` script runs.
- **Ingest dependencies in the core venv, before 7e** (build-snapshot re-ingests): after step 4,
  `pip install -r requirements-ingest.txt` (edgartools==5.59.1, docling==2.131.0; its
  `-r requirements.txt` no longer pulls fastembed by then; large, docling pulls in PyTorch, all on
  D:). Why: `parse_cache.tag()` calls `importlib.metadata.version(library)` before reading the
  cache, so a missing edgartools crashes step 3, and a missing docling is caught as ImportError
  in `pdf.py` and every PDF silently falls back to pymupdf (different chunks, nothing written to
  `parsed/`). After the install, `pip show docling edgartools` must show the pinned versions
  (the cache file tags depend on them) and `pip show fastembed onnxruntime` must find neither.
  (In the main checkout's venv `onnxruntime` is required only by fastembed, so docling is not
  expected to pull it.) If it does appear anyway: say so in the Progress log; the "without the
  extra" pytest run then counts only from before the ingest install (7d runs first, see below)
  and from CI, and the build-snapshot claim becomes "no embedding step, no model loaded" only.
- **Vectors venv** `<cache>\venv-144-vectors` (outside the worktree): `requirements.txt` +
  `requirements-vectors.txt` + `pip install -e <worktree>`. Used only for the vectors-on and model
  checks: 7b (`--missing`, `--query`), 7c (empty cache with fastembed present, so "no download"
  is a real test) and pytest "with the extra".
- pip cache: `PIP_CACHE_DIR` already points to D: (C: is full); `FASTEMBED_CACHE_PATH` stays on
  `<cache>` via `.env`.
- Proof: before every check, the same venv prints `python -c "import cee; print(cee.__file__)"`
  and the line goes into the evidence; it must be `<worktree>\src\cee\__init__.py`. For script
  runs, the script's own `$Python` is `<worktree>\.venv\Scripts\python.exe`; the check is run with
  that same interpreter.

Here `<worktree>` = `D:\ALLPROJECTS\EDJ\wt-144`, `<cache>` = `D:\ALLPROJECTS\EDJ\cache`,
`<main checkout>` = `D:\ALLPROJECTS\EDJ\repo` (never edited).

0. **Safety and baseline, before any code edit** (branch = `main` ea7d5ac + this plan only).
   The local Postgres (`cee-db`, database `cee`) is shared with the paused #125 branch.
   - Create the core venv (above) and log `cee.__file__`.
   - Record the main checkout's `snapshots/` listing (name, size, time; 6 dumps today,
     `corpus-2026-09-30` ... `corpus-2026-10-29`).
   - Record counts: `SELECT count(*), count(embedding) FROM chunks` -> expected `17183|17183`.
   - Back up: `docker exec cee-db pg_dump -U cee -d cee -Fc -f /tmp/cee-before-144.dump`, then
     `docker cp` it to `<cache>\backups\cee-before-144.dump` (outside any repo,
     never committed). Check it lists with `pg_restore -l`.
   - "Before" eval: `python scripts/eval_run.py --as-of 2026-10-30 --out <cache>\eval-144\before`
     (mock, FTS is the only mode on `main`; there is no `RETRIEVAL_MODE` on `main` yet, so
     "fts mode" = the default). Save the console output.
1. Schema split: `db/upgrade.sql` core only, `db/optional/vectors.sql`, `db/schema.sql` comment,
   `docker-compose.yml` comment. Check: plain-Postgres scratch run (Acceptance 1) and the
   migration on a copy (step 7).
2. `cee.config.vectors_enabled()` + tests.
3. `embed.py` (cache-only load, `--fetch`, `chunk_embeddings`, off-guard) + `tests/test_embed.py`
   + `tests/test_vectors_optional.py`. Run pytest.
4. Dependencies: `requirements.txt`, `requirements-vectors.txt`, `pyproject.toml` extra, CI comment.
5. Scripts, both `.ps1` and `.sh`: `_common`, `build-snapshot`, `restore`.
6. Docs: ADR-009 + ADR-001 pointer, `.env.example`, `RUN.md`, `ARCHITECTURE.md`, `DASHBOARD.md` line.
7. Verification runs (all on mock, 0 paid calls), in this order:
   a. Plain Postgres scratch (Acceptance 1): `docker run -d --rm --name cee-plainpg-144 -e
      POSTGRES_PASSWORD=x postgres:16.10` (image already local; no pgvector inside; check
      `pg_available_extensions` has no `vector`). Database `a`: `schema.sql`, `upgrade.sql`,
      `upgrade.sql` again; database `b`: the same sequence again. All via stdin with
      `ON_ERROR_STOP=1`. Also show `vectors.sql` fails there with "extension vector is not
      available" (expected: optional module needs the pgvector image). Container removed after.
   b. Migration on a copy of today's local DB (Acceptance 6), without touching `cee`:
      (SQL via `docker exec`; the Python commands in the vectors venv)
      `CREATE DATABASE cee_vec144`, `pg_restore` the backup into it; counts before (17183
      non-NULL); apply `vectors.sql` twice (second run is a no-op); then
      `count(*) FROM chunk_embeddings` = 17183, `chunks.embedding` absent
      (`information_schema.columns`), HNSW index present. `DATABASE_URL=.../cee_vec144
      CEE_VECTORS=on python -m cee.retrieve.embed --missing` -> `0 embedded, 0 still missing`.
      `python -m cee.retrieve.embed --query "test"` -> `384 dims`. Drop `cee_vec144` afterwards.
   c. Empty cache (Acceptance 5; vectors venv, so fastembed is importable and could download): `FASTEMBED_CACHE_PATH=<cache>\empty-144`
      (new empty folder) and once a path that does not exist, with `HF_ENDPOINT=http://127.0.0.1:9`
      so any download attempt would show as a connection error: `--query x` exits non-zero with
      the clear error; the non-existent folder is still absent afterwards.
   d. pytest in the core venv **before** the ingest dependencies are installed (no fastembed/
      onnxruntime, no docling: the real "without" run, same as CI) and in the vectors venv (with
      the extra). Both log `cee.__file__` first. Then install `requirements-ingest.txt` into the
      core venv with the `pip show` checks above, and run pytest in the core venv once more.
   e. `build-snapshot` with vectors off (Acceptance 4). It drops and rebuilds database `cee` and
      copies the dump to `CORPUS_SHARE_PATH`, so: `CORPUS_SHARE_PATH` = a scratch folder
      `<cache>\share-144` (the "scratch share") set up as:
      - `raw` = a **copy** (not a junction or symlink) of the shared corpus folder's `raw/`
        (measured 2026-10-30: 111 files, 0.22 GB; D: has 28 GB free). Why a copy: the scratch
        share then contains no link into the shared corpus folder, so deleting it afterwards
        cannot follow a link and delete shared raw files (PowerShell 5.1 `Remove-Item -Recurse`
        and `rm -rf` on a link are the risk), and Git Bash `ln -s` without
        `MSYS=winsymlinks:nativestrict` would silently copy anyway. The manifest check (step 1/7,
        sha256 of every file) then also proves the copy is complete.
      - Before copying: record the shared corpus folder's `raw` file count and total size (111
        files today); after the copy, the scratch `raw` has the same count. Before cleanup, check
        `share-144` holds no reparse point / symlink (`Get-ChildItem -Recurse -Attributes
        ReparsePoint` empty) - there should be none, since nothing was linked.
      - `parsed` = a **copy** (not a link) of the shared corpus folder's `parsed/` parse cache
        (#82; `parse_cache.cache_path` = `<write_root()>/parsed/`, used by `pdf.py` and `load.py`).
        A copy, so a cache miss writes into the scratch folder, never into the shared corpus
        folder. Without it every PDF would re-run docling (minutes each) and every filing
        edgartools: hours.
      - Record the file count of `share-144\parsed` before the run.
      Then `--allow-branch`; `CEE_VECTORS` unset in env and `.env`; from the worktree with
      `COMPOSE_PROJECT_NAME=repo` (the running `cee-db` belongs to that compose project; compose
      may recreate the container with the worktree's mounts, data volume kept). Nothing is copied
      to the real `snapshots/`, so nothing is published.
      **Expected duration and stop rule:** with a full parse cache, step 3 (re-ingest) only reads
      cached JSON and inserts rows: expected well under 15 minutes. Stop (Ctrl+C) if step 3 runs
      longer than 30 minutes or any new file appears in `share-144\parsed` (= a re-parse started);
      then restore `cee` from the backup as below and report it in the Progress log instead of
      continuing. After the run: **0 new files** in `share-144\parsed` (count equal to before),
      and the build log (step 3) has **0** lines `parsing with docling (cache ...)` and **0**
      lines `parsing with edgartools (cache ...)` (wording from `pdf.py` / `load.py`), and one
      `<file>: parse cache hit (<cache file>)` line per PDF and filing; no
      `ignoring unreadable parse cache` line. Row counts at the end match the backup's `cee`
      (documents and chunks; chunk count 17183), so the rebuild used the same parsers.
      If the counts differ while the log shows only cache hits, the difference comes from the
      manifest/corpus since the backup was built, not from the parsers: the Progress log then
      names the differing doc_ids (per-document chunk counts, rebuilt vs backup) instead of
      calling it a pass or fail by count alone.
      Run the `.ps1` (Windows) once, fully. **No full run of `build-snapshot.sh`** in this task:
      it would drop and re-ingest `cee` a second time for no extra proof of the vectors-off
      branch. The `.sh` twins get a non-destructive check instead: `bash -n` on every changed
      `.sh`; then, sourcing `scripts/_common.sh` in Git Bash, `vectors_on` with `CEE_VECTORS`
      unset / `off` / `on` / `bogus` -> off / off / on / stops with the error; and the skip lines
      in `build-snapshot.sh` / `restore.sh` sit behind that same function (read in the diff).
      Same for `restore.sh` (no full run; the `.ps1` restore below is the full one). A full
      macOS run of the `.sh` scripts stays with the next snapshot build (noted in the PR).
      Save the `.ps1` log; it must show the two "skipped" lines and no model path. Afterwards restore the backup into `cee`
      with `scripts\restore.ps1 <cache>\backups\cee-before-144.dump` (it stages
      the file into the mounted `snapshots/`; a dump left in the container's `/tmp` is gone once
      compose recreated the container), so #125 finds its data as before, and re-check
      `17183|17183`. Then `docker compose up -d --wait` from the main checkout's folder
      (`D:\ALLPROJECTS\EDJ\repo`; the Progress log records the folder each `docker compose up`
      ran from) to put the container's mounts back (no file there changes). Cleanup, in order:
      (1) confirm `share-144` has no reparse point / symlink (see above); (2) count the shared
      corpus folder's `raw` again -> unchanged (111 files, same size); (3) only then delete
      `share-144`, and in `<worktree>\snapshots\` (git-ignored; compose ran from the worktree, so
      the `-test` dump and the staged backup land there) only those two files;
      (4) count the shared `raw` once more -> unchanged; (5) the main checkout's `snapshots/`
      listing equals the one recorded in step 0 (same 6 dumps, sizes, times, nothing added);
      (6) after the final `docker compose up -d --wait` from `<main checkout>`, count `cee` again
      -> `17183|17183`.
   f. Covered by the restore in 7e: `restore.ps1` with vectors off prints that the optional SQL
      was skipped. (With vectors on it is covered by 7b's SQL; not re-run on `cee`, which keeps
      today's column for #125.)
   g. "After" eval on the restored `cee` (same data as "before"): `python scripts/eval_run.py
      --as-of 2026-10-30 --baseline <before>/report.json --out ...\eval-144\after`; plus a short
      inline diff of `chunk_ids` per question between the two `report.json` files (eval_run's
      baseline compare only compares status/coverage) -> 30/30 identical, every `change` UNCHANGED.
   h. `python -m cee.smoke` with vectors off -> PASS.
   i. verify-cee: `python scripts/verify_cee.py run` (all features, mock) -> PASS.
8. Comment on #125; `/finish-task`.

Unsure / risks:
- The shared local DB: the plan never runs `vectors.sql` on `cee` itself (only on the copy), and
  `cee` is restored from the backup after the build test. So #125 resumes on unchanged data and
  migrates when it adopts `chunk_embeddings`. The backup stays in `<cache>\backups`
  until #125 is done.
- Today's published snapshot still holds `chunks.embedding` + the `vector` extension. Restoring it
  keeps working on the pgvector image (unchanged); with vectors off the column is simply unused,
  with vectors on `vectors.sql` moves it. A snapshot built after this lands (vectors off) has
  neither, so it restores on plain Postgres. Not publishing one is in the issue's scope.
- The build-snapshot check (7e) re-ingests the whole corpus. It relies on a copy of the parse
  cache in the scratch share; a cache miss (new file or parser version) would start docling or
  edgartools runs that take hours. The stop rule in 7e (30 minutes or any new file in
  `share-144\parsed`) ends the check and `cee` is restored from the backup.
- Deleting the scratch share must never touch the shared corpus folder. The scratch share holds
  copies only (`raw`, `parsed`), no junction or symlink; cleanup first checks there is no
  reparse point and that the shared `raw` count is unchanged, and counts it again after.
- Only the `.ps1` build-snapshot and restore get a full run here (Windows machine); the `.sh`
  twins get `bash -n` + the `vectors_on` check. A full `.sh` run happens on the next snapshot
  build on macOS.
- Wording: the ADR, docs, PR and comments say "shared corpus folder", not the file-sharing
  service's name, and use generic placeholders (`<backup.dump>`, `<scratch folder>`) instead of
  this machine's local paths. Local paths appear only in this plan's verification steps.
- Changing the init mounts needs nothing: they are unchanged; only existing volumes keep the
  old column, which nothing in the core reads.

## Acceptance
- [x] Q1-Q30: mock eval after vs before (`--as-of 2026-10-30`, baseline compare + `chunk_ids` diff):
      identical `chunk_ids` on 30/30, same PASS/FAIL (all `UNCHANGED`)
- [x] Plain `postgres:16.10` container (no `vector` in `pg_available_extensions`): `schema.sql`,
      `upgrade.sql`, `upgrade.sql` apply with no error, on two fresh databases in a row
- [x] pytest green in CI (installs `requirements.txt` only, no fastembed/onnxruntime); green
      in the core venv (`<worktree>\.venv`, no fastembed/onnxruntime installed); green in the
      vectors venv (extra installed); `cee.__file__` logged as `<worktree>\src\...` for each
- [x] `build-snapshot.ps1 --allow-branch` with `CEE_VECTORS` unset: log shows
      `4/7 Embedding skipped (CEE_VECTORS is off)` and `7/7 ... skipped`, no model loaded, nothing
      written to the real share; 0 new files in the scratch `parsed`; 0 `parsing with docling` /
      `parsing with edgartools` lines, only `parse cache hit`; chunk count 17183 as before; `.sh` twins: `bash -n` +
      `vectors_on` check as in step 7e (no full `.sh` run)
- [x] Shared corpus folder `raw` file count and size unchanged (before the run, before cleanup,
      after cleanup: 111 files); the scratch share contained no link
- [x] `FASTEMBED_CACHE_PATH` = empty folder (and a missing one): `python -m cee.retrieve.embed
      --query x` exits non-zero, message names `FASTEMBED_CACHE_PATH` and `--fetch`, no download
      attempt (no connection error with the dead `HF_ENDPOINT`), missing folder not created
- [x] Copy of today's local DB (17183 non-NULL `chunks.embedding`): after `db/optional/vectors.sql`
      `chunk_embeddings` has 17183 rows, `chunks.embedding` is gone, a second apply changes
      nothing, `--missing` embeds 0, `--query "test"` prints `384 dims`
- [x] Shared `cee` DB after all tests: `17183|17183` as before (restored from backup) and again after the
      final `docker compose up -d --wait` from the main checkout
- [x] Main checkout's `snapshots/` unchanged (same 6 dumps, sizes, times); scratch dumps only in
      `<worktree>\snapshots\`, deleted after
- [x] Core venv after the ingest install: `pip show` lists docling 2.131.0 and edgartools 5.59.1,
      and neither fastembed nor onnxruntime (or the deviation is logged as described)
- [x] Every check ran on the worktree's code: `cee.__file__` -> `<worktree>\src\cee\__init__.py`
- [x] `python -m cee.smoke` -> PASS with vectors off
- [x] `python scripts/verify_cee.py run` -> PASS (all features, mock, fts)
- [x] Core SQL contains no `vector` / `CREATE EXTENSION` (test); compose mounts only core SQL
- [x] Every changed script ships `.ps1` + `.sh`; RUN.md has Windows and macOS blocks for each step
- [x] 0 paid API calls

## Deviations from the issue design
- "apply twice in a row": `db/schema.sql` is plain `CREATE TABLE` (first start of a volume only,
  not idempotent by design), so the check is `schema.sql` + `upgrade.sql` + `upgrade.sql` on one
  fresh database, then the whole sequence again on a second fresh database.
- "Local DB with today's vectors": the migration runs on a restored copy (`cee_vec144`) of the
  local DB, not on `cee` itself, because `cee` is shared with the paused #125 branch.
- Two small files outside the issue's Inputs: `src/cee/config.py` (the `CEE_VECTORS` parser)
  and one checklist line in `docs/DASHBOARD.md`.
- The import test covers `cee.app.components` and `cee.app.views.*` instead of
  `cee.app.streamlit_app` (importing that file runs the page).

## Progress log
- 2026-10-30 19:10 - plan written on branch `tl/144-vectors-optional` from `main` ea7d5ac.
  Local DB: 17183 chunks, 17183 with `chunks.embedding`; pgvector 0.8.1; `postgres:16.10` image
  already local for the plain-Postgres check.
- 2026-10-30 19:40 - plan review round 1 (CHANGES REQUESTED, 1 blocking): 7e now copies the parse
  cache `parsed/` into the scratch share, checks 0 new parse files, and has a 30-minute stop rule.
  Notes folded in: restore via `scripts\restore.ps1 <backup>` (covers 7f), log the folder of each
  `docker compose up`, generic "shared corpus folder" wording, anti-join check in `vectors.sql`.
- 2026-10-30 20:05 - plan review round 2 (CHANGES REQUESTED, 1 blocking): the scratch share now
  holds a copy of `raw` (0.22 GB) instead of a link, so cleanup cannot reach the shared corpus
  folder; shared `raw` count checked before the run, before and after cleanup (new Acceptance
  item). Notes folded in: no full `build-snapshot.sh` run (non-destructive `bash -n` +
  `vectors_on` check instead, reason given); generic placeholders in PR/ADR text.
- 2026-10-30 20:30 - plan review round 3 (CHANGES REQUESTED, 2 blocking; tech lead approved one
  more round): checks now run in a venv of the worktree's own (core, never gets fastembed) plus a
  separate vectors venv under `<cache>` for the vectors-on/model checks; `cee.__file__` logged per
  run. Scratch dumps land in `<worktree>\snapshots\` and are deleted there only; main checkout's
  `snapshots/` (6 dumps) checked unchanged. Note folded in: recount `cee` after the final compose up.
- 2026-10-30 21:00 - plan review round 4 (CHANGES REQUESTED, 1 blocking): the core venv gets
  `requirements-ingest.txt` after step 4 and before 7e (a missing docling would silently fall back
  to pymupdf); `pip show` checks pinned docling/edgartools and no fastembed/onnxruntime; pytest
  "without" runs before the ingest install; the build log must show only `parse cache hit` lines
  and the chunk count must match. PR and ADR text keep the same placeholders.
- 2026-10-30 21:40 - plan approved (round 5). Step 0: core venv `<worktree>\.venv` (core pins only,
  `cee.__file__` -> `<worktree>\src`); main checkout `snapshots/` listed (6 dumps); `cee` =
  17183|17183; backup `<cache>ackups\cee-before-144.dump` (8 tables of data); "before" eval on
  unchanged main code: PASS 27 / FAIL 3, 0 real calls.
- 2026-10-30 22:10 - steps 1-6 implemented (commit bc5cf52). pytest core venv (no fastembed,
  onnxruntime, docling): 256 passed, 1 skipped; vectors venv: 257 passed.
- 2026-10-30 22:15 - 7a plain `postgres:16.10` (vector not available): schema + upgrade + upgrade
  OK on databases a and b; `vectors.sql` fails there with `extension "vector" is not available`
  (expected). 7b copy `cee_vec144`: 17183 non-NULL before; `vectors.sql` twice OK (second a no-op);
  `chunk_embeddings` 17183, `chunks.embedding` gone, HNSW index present; `--missing` (on) ->
  `0 embedded, 0 still missing`; `--missing` (off) -> exit 2; `--query` -> 384 dims; `cee`
  untouched; copy dropped. Surprise: the worktree `.env` has no `FASTEMBED_CACHE_PATH`, so the first
  `--query` hit the default `<worktree>\.cacheastembed` and failed with the new clear error and
  created no folder (a free extra check); re-run with `FASTEMBED_CACHE_PATH=<cache>astembed`.
  7c empty and missing cache with dead `HF_ENDPOINT`: exit 1, clear error, no connection error,
  missing folder not created.
- 2026-10-30 22:20 - 7d: ingest deps installed in the core venv (docling 2.131.0, edgartools 5.59.1;
  `pip show fastembed onnxruntime` -> not found); pytest again 256 passed, 1 skipped. `.sh`:
  `bash -n` OK on the three files; `vectors_on` unset/off/on/bogus -> off/off/on/error exit 1;
  `.ps1` parse OK and `Test-VectorsOn` same results. No full `.sh` run (as planned).
- 2026-10-30 22:24 - 7e: scratch share = copies of `raw` (111 files, 236681498 bytes) and `parsed`
  (73 files), 0 reparse points. Pre-check (note 2): 32 PDFs + 41 filings = 73 expected cache hits,
  0 predicted misses with the pinned tags. `build-snapshot.ps1 -AllowBranch`, `CEE_VECTORS` unset,
  compose from `<worktree>` with `COMPOSE_PROJECT_NAME=repo` (container recreated): 40 s; 73
  `parse cache hit` lines = 73 PDFs + filings, 0 `parsing with docling`, 0 `parsing with
  edgartools`, 0 unreadable; `4/7 Embedding skipped (CEE_VECTORS is off)`, `7/7 Embedding model
  skipped (CEE_VECTORS is off)`, no model path; parsed still 73 files; rows chunks=17183,
  documents=111 (same as backup). Rebuilt `cee` had only `plpgsql` (no vector extension, no
  `chunks.embedding`); the `-test` dump restored on plain `postgres:16.10` (17183 chunks).
  7f: `restore.ps1 <backup>` -> `Vectors module skipped (CEE_VECTORS is off)`; `cee` 17183|17183,
  snapshot `corpus-2026-10-29`.
- 2026-10-30 22:27 - 7g after eval vs before: 30/30 identical `chunk_ids` (same order), 30/30 same
  status, all `UNCHANGED`. 7h smoke PASS. 7i verify-cee all 7 features PASS
  (`.verify-runs/20261030-222638-bc5cf52`).
- 2026-10-30 22:30 - cleanup: `docker compose up -d --wait` from `<main checkout>` (mounts back to
  the main checkout), `cee` 17183|17183; 0 reparse points; shared `raw` 111 files / 236681498 bytes
  before and after deleting `share-144`; the two scratch dumps deleted from `<worktree>\snapshots`;
  main checkout `snapshots/` listing identical to step 0. Evidence: `<cache>\ev144\`.
