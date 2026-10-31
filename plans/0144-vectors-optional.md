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
  block: if `chunks.embedding` exists, copy its non-NULL rows (`ON CONFLICT DO NOTHING`), compare
  counts and `RAISE EXCEPTION` on a mismatch (rolls everything back), then drop the column (its
  index goes with it). Dynamic SQL (`EXECUTE`) so the block parses when the column is gone.
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
  (`python -m cee.retrieve.embed --fetch`) or copy the Box `models/` folder, set `CEE_VECTORS=on`,
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
ranking, synonyms, chunking, other portability work, Box publishing.

## Steps
0. **Safety and baseline, before any code edit** (branch = `main` ea7d5ac + this plan only).
   The local Postgres (`cee-db`, database `cee`) is shared with the paused #125 branch.
   - Record counts: `SELECT count(*), count(embedding) FROM chunks` -> expected `17183|17183`.
   - Back up: `docker exec cee-db pg_dump -U cee -d cee -Fc -f /tmp/cee-before-144.dump`, then
     `docker cp` it to `D:\ALLPROJECTS\EDJ\cache\backups\cee-before-144.dump` (outside any repo,
     never committed). Check it lists with `pg_restore -l`.
   - "Before" eval: `python scripts/eval_run.py --as-of 2026-10-30 --out D:\ALLPROJECTS\EDJ\cache\eval-144\before`
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
      `CREATE DATABASE cee_vec144`, `pg_restore` the backup into it; counts before (17183
      non-NULL); apply `vectors.sql` twice (second run is a no-op); then
      `count(*) FROM chunk_embeddings` = 17183, `chunks.embedding` absent
      (`information_schema.columns`), HNSW index present. `DATABASE_URL=.../cee_vec144
      CEE_VECTORS=on python -m cee.retrieve.embed --missing` -> `0 embedded, 0 still missing`.
      `python -m cee.retrieve.embed --query "test"` -> `384 dims`. Drop `cee_vec144` afterwards.
   c. Empty cache (Acceptance 5): `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\empty-144`
      (new empty folder) and once a path that does not exist, with `HF_ENDPOINT=http://127.0.0.1:9`
      so any download attempt would show as a connection error: `--query x` exits non-zero with
      the clear error; the non-existent folder is still absent afterwards.
   d. pytest locally with the extra installed (venv has it); and once with fastembed/onnxruntime
      blocked: `python -c "import sys; sys.modules['fastembed']=None; sys.modules['onnxruntime']=None;
      import pytest; sys.exit(pytest.main(['-q']))"` (local stand-in; CI is the real "without" proof).
   e. `build-snapshot` with vectors off (Acceptance 4). It drops and rebuilds database `cee` and
      copies the dump to `CORPUS_SHARE_PATH`, so: `CORPUS_SHARE_PATH` = a scratch folder
      `D:\ALLPROJECTS\EDJ\cache\share-144` whose `raw` is a junction (`.ps1` run) / symlink to the
      real share's `raw` (manifest check reads it; nothing is copied to the real `snapshots/`, so
      nothing is published); `--allow-branch`; `CEE_VECTORS` unset in env and `.env`; from the
      worktree with `COMPOSE_PROJECT_NAME=repo` (the running `cee-db` belongs to that compose
      project; compose may recreate the container with the worktree's mounts, data volume kept).
      Run the `.ps1` (Windows); run the `.sh` through Git Bash as far as it goes with the same
      settings, or at least `bash -n` plus the skip branch, and say which. Save the log; it must
      show the two "skipped" lines and no model path. Afterwards restore the backup into `cee`
      (`pg_restore` of `cee-before-144.dump`, so #125 finds its data as before) and re-check
      `17183|17183`; then `docker compose up -d --wait` from the main checkout's folder to put the
      container's mounts back (no file there changes). Delete the scratch dump.
   f. Restore script with vectors off on the backup dump: prints that the optional SQL was skipped.
      (With vectors on it is covered by 7b's SQL; not re-run on `cee`, which keeps today's column
      for #125.)
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
  migrates when it adopts `chunk_embeddings`. The backup stays in `D:\ALLPROJECTS\EDJ\cache\backups`
  until #125 is done.
- Today's Box snapshot still holds `chunks.embedding` + the `vector` extension. Restoring it
  keeps working on the pgvector image (unchanged); with vectors off the column is simply unused,
  with vectors on `vectors.sql` moves it. A snapshot built after this lands (vectors off) has
  neither, so it restores on plain Postgres. Not publishing one is in the issue's scope.
- Changing the init mounts needs nothing: they are unchanged; only existing volumes keep the
  old column, which nothing in the core reads.

## Acceptance
- [ ] Q1-Q30: mock eval after vs before (`--as-of 2026-10-30`, baseline compare + `chunk_ids` diff):
      identical `chunk_ids` on 30/30, same PASS/FAIL (all `UNCHANGED`)
- [ ] Plain `postgres:16.10` container (no `vector` in `pg_available_extensions`): `schema.sql`,
      `upgrade.sql`, `upgrade.sql` apply with no error, on two fresh databases in a row
- [ ] pytest green in CI (installs `requirements.txt` only, no fastembed/onnxruntime); green
      locally with them installed; green locally with them blocked
- [ ] `build-snapshot.ps1 --allow-branch` with `CEE_VECTORS` unset: log shows
      `4/7 Embedding skipped (CEE_VECTORS is off)` and `7/7 ... skipped`, no model loaded, nothing
      written to the real share; `.sh` twin checked as described in step 7e
- [ ] `FASTEMBED_CACHE_PATH` = empty folder (and a missing one): `python -m cee.retrieve.embed
      --query x` exits non-zero, message names `FASTEMBED_CACHE_PATH` and `--fetch`, no download
      attempt (no connection error with the dead `HF_ENDPOINT`), missing folder not created
- [ ] Copy of today's local DB (17183 non-NULL `chunks.embedding`): after `db/optional/vectors.sql`
      `chunk_embeddings` has 17183 rows, `chunks.embedding` is gone, a second apply changes
      nothing, `--missing` embeds 0, `--query "test"` prints `384 dims`
- [ ] Shared `cee` DB after all tests: `17183|17183` as before (restored from backup)
- [ ] `python -m cee.smoke` -> PASS with vectors off
- [ ] `python scripts/verify_cee.py run` -> PASS (all features, mock, fts)
- [ ] Core SQL contains no `vector` / `CREATE EXTENSION` (test); compose mounts only core SQL
- [ ] Every changed script ships `.ps1` + `.sh`; RUN.md has Windows and macOS blocks for each step
- [ ] 0 paid API calls

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
