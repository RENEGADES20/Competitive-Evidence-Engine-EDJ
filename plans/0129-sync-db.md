# 0129 - Snapshot manifest in the repo and /sync-db (Windows and macOS)

Issue: #129    Role: TL    Spec: docs/RUN.md, docs/ARCHITECTURE.md (shared corpus flow), docs/DECISIONS.md ADR-006 / ADR-007 / ADR-009

## Goal
After a snapshot PR is merged, a teammate types `/sync-db` (or runs `scripts/sync-db.ps1` /
`scripts/sync-db.sh`) and their local database is on the snapshot named in `snapshots/LATEST.json`,
checked by sha256 and by `python -m cee.smoke`, with no hand-written txt. The dump itself stays on
Box (public repo, ADR-007); only its name, sha256, counts and notes go into git. Works with vectors
off (the default, ADR-009/010) and needs no embedding model. First real use: the 11/11 freeze
snapshot (#120).

No ADR change: `LATEST.json` is metadata, like `data/manifest.csv` (ADR-006); dumps and the Box
link never enter the repo (ADR-007). No paid API call (ops change; mock provider only).

## Design in brief
- `snapshots/LATEST.json` (committed; the rest of `snapshots/` stays ignored):
  `{"name", "sha256", "documents", "chunks", "built_at", "notes"}`; `name` has no `.dump`
  (it equals the `COMMENT ON TABLE documents` stamp); `built_at` is UTC ISO 8601; 2-space JSON,
  UTF-8 without BOM, LF, trailing newline.
- One small OS-neutral helper, `scripts/snapshot_latest.py`, does the JSON and the hashing for
  both twins, so the `.ps1` and `.sh` cannot drift (no `jq` on a Mac, no BOM from PowerShell 5.1):
  - `write --out F --dump D --documents N --chunks N --notes T [--built-at ISO]`: name = dump file
    stem, sha256 computed from the file; refuses empty notes, and notes that contain a Box URL
    (`box.com`), since the repo is public.
  - `show --file F [--field K]`: prints one field, or a plain summary.
  - `locate --file F --search DIR [DIR ...] [--depth N]`: looks for exactly `<name>.dump`
    (directories in the order given; recursive up to `--depth`, default 6; a 0-byte file is read
    once so Box makes it local, then re-checked). Prints the path of the first file whose sha256
    matches and exits 0. None found: prints `Download <name>.dump from the Box snapshots folder into
    <repo>/snapshots/` and exits 2. Found but every copy differs: names the files, says the file is
    old or incomplete, the same download line, exits 2.
- `scripts/sync-db.ps1` / `scripts/sync-db.sh` (same arguments, steps, messages, exit codes):
  - `-Latest <file>` / `--latest <file>`: which manifest to read (default `snapshots/LATEST.json`;
    used by the tests, not by teammates).
  - `-Check` / `--check`: read-only, for `/start-task`. Compares the database's stamp with
    `LATEST.json`: up to date -> exit 0; behind or no stamp -> prints
    `Your database has <x>; the newest snapshot is <name>. Run /sync-db.` and exits 2; Docker or the
    container not running -> one line, exit 1; no `LATEST.json` yet -> says so, exit 0.
  - Normal run:
    1. `1/4 Updating code`: on branch `main` -> `git pull --ff-only`; on another branch -> warning
       (`you are on <branch>; switch to main to get the newest LATEST.json`), no switch, no pull
       (never moves a teammate off their work). Then `pip install -q -r requirements.txt` and
       `docker compose up -d --wait` (existing `Start-Database` / `start_database`).
    2. Read `LATEST.json` (missing -> clear message, exit 1). Read the database stamp. Equal ->
       `Already up to date: <name>. Nothing to do.` exit 0 (nothing after step 1 runs).
    3. `2/4 Finding <name>.dump`: `locate` in, in order, `<repo>/snapshots`,
       `CORPUS_SHARE_PATH/snapshots` (when set), Box Drive (`%USERPROFILE%\Box` on Windows and in
       Git Bash, `~/Library/CloudStorage` on a Mac). Missing or different -> message, exit 2,
       database untouched (nothing has been dropped yet).
    4. `3/4 Restoring`: calls the existing `restore.ps1` / `restore.sh` with that path (staging,
       drop/create, `pg_restore`, `db/upgrade.sql`, and the vectors module only when
       `CEE_VECTORS=on`). Then checks the stamp equals `name` (else exit 1).
    5. `4/4 Smoke test`: `python -m cee.smoke`; its exit code is the script's. Last lines:
       the `notes`, and `Synced to <name> (<documents> documents, <chunks> chunks). Smoke PASS.`
       With `CEE_VECTORS=on` one extra line: run `python -m cee.retrieve.embed --missing`
       (the dump has no vectors when built with vectors off). sync-db never loads a model.
- `build-snapshot.ps1` / `.sh`: new `-Notes "<text>"` / `--notes "<text>"`, required for an
  official build and checked first (before the branch check and before the database is touched).
  After the dump: `Write-Host "Writing snapshots/LATEST.json"` via `snapshot_latest.py write` with
  the row counts from the database. `-AllowBranch` / `--allow-branch` builds write
  `snapshots/LATEST-test.json` instead (stays git-ignored, never published), notes default
  `test build`. The end message says: commit `snapshots/LATEST.json` on a branch and open a PR;
  merging it is the notice to the team.
- Container name and port become settings, defaults unchanged, so a second, throwaway database can
  run beside the shared one for tests (and a teammate with a busy port 5432 has a cleaner fix):
  `docker-compose.yml` `container_name: ${CEE_DB_CONTAINER:-cee-db}`,
  ports `"${CEE_DB_PORT:-5432}:5432"`; `_common.ps1` / `_common.sh` read `CEE_DB_CONTAINER`
  (environment or `.env`, default `cee-db`); `scripts/verify_cee.py` reads it from the environment.

## Files to change
- `snapshots/LATEST.json` (new, committed) - seeded with the current snapshot `corpus-2026-10-29`
  (sha256 `c09106674162753175416834b7d1be81041e5409972793dc292b4197d895495f`, the same for the Box
  copy and the local copy), documents/chunks counted after restoring it into the test database
  (expected 111 / 17183, as in plans/0122), `built_at` = the Box file's modified time
  `2026-10-29T22:32:13Z`, notes from the 10-29 txt (#108, #111). #120 replaces it on 11/11.
- `.gitignore` - `snapshots/` -> `snapshots/*` + `!snapshots/LATEST.json` (`*.dump` stays ignored).
- `scripts/snapshot_latest.py` (new) - the helper above (standard library only).
- `scripts/sync-db.ps1`, `scripts/sync-db.sh` (new) - the twins above.
- `scripts/build-snapshot.ps1`, `scripts/build-snapshot.sh` - `-Notes`/`--notes`, write
  `LATEST.json` / `LATEST-test.json`, end message.
- `scripts/_common.ps1`, `scripts/_common.sh` - `CEE_DB_CONTAINER`; new `Get-SnapshotName` /
  `snapshot_name` (database stamp, empty when none).
- `docker-compose.yml` - container name and host port from `CEE_DB_CONTAINER` / `CEE_DB_PORT`
  with today's defaults.
- `.env.example` - `CEE_DB_CONTAINER=` and `CEE_DB_PORT=` (empty = defaults), with one comment line.
- `scripts/verify_cee.py` - `CONTAINER = os.getenv("CEE_DB_CONTAINER") or "cee-db"` (one line), so
  verify-cee can run against the test database.
- `tests/test_snapshot_latest.py` (new) - `write`: fields, sha256 equals `hashlib` of the file,
  name = stem, UTC `built_at`, exact bytes (no BOM, LF), empty notes and Box URL refused; `show`;
  `locate`: exact name only (`corpus-X-test.dump`, `corpus-X (1).dump` ignored), first matching
  directory wins, depth limit, mismatch -> exit 2 with the file named, missing -> exit 2 with the
  download line; `.gitignore` keeps `LATEST.json` tracked and the dump ignored
  (`git check-ignore`, skipped without git); `docker-compose.yml` keeps `cee-db` / `5432` defaults.
- `.claude/commands/sync-db.md` (new) - run the script for this OS (Windows `powershell
  -ExecutionPolicy Bypass -File scripts\sync-db.ps1`, Mac `bash scripts/sync-db.sh`); report in
  plain words: up to date, or synced with the `notes` and the smoke result; on exit 2 tell the
  teammate to download that file from the team Box link (team chat) into `snapshots/` and run
  `/sync-db` again; never restore by hand, never print `.env`.
- `.claude/commands/start-task.md` - step 2 gains: after `git switch main && git pull`, run
  `sync-db -Check` / `--check`; exit 2 -> tell the user and suggest `/sync-db` before testing
  anything; exit 1 -> mention Docker is not running, continue. Placed right after the pull rather
  than literally first, so it compares against the newest `LATEST.json` (the issue's intent).
- `docs/RUN.md` - section 2 "Daily use": `/sync-db` or the script, Windows and Mac blocks, what
  the download message means; section 4: `build-snapshot -Notes` / `--notes`, `LATEST.json` PR,
  no txt; section 5: rows for the new messages, and the port row points at `CEE_DB_PORT`.
- `docs/DASHBOARD.md` section 8 - build with notes; commit `LATEST.json` via PR; the team-chat
  notice is one line ("run /sync-db"), no txt.
- `docs/WORKFLOW-SETUP.md` section 4 - the manual find/restore steps become the sync-db script
  (both OS), keeping the "ask the teammate to download from the Box link" fallback.
- `docs/ARCHITECTURE.md` - shared corpus flow step 5: `/sync-db` reads `snapshots/LATEST.json`.
- `plans/0129-sync-db.md` - this plan.

Not changed: `scripts/restore.*` (sync-db calls them as they are), `docs/DECISIONS.md`, `src/`.

## Steps
1. `.gitignore`, `snapshot_latest.py` and its pytest file; `pytest -q` green.
2. `docker-compose.yml`, `.env.example`, `_common.*` (`CEE_DB_CONTAINER`, snapshot-name helper),
   `verify_cee.py` line. Check: `docker compose config` with no variables shows `cee-db` and
   `5432:5432`; with the test variables shows the test name and port.
3. `sync-db.ps1` and `sync-db.sh`; `bash -n`; run tests T1-T5 below on both.
4. `build-snapshot.*` changes; tests T6-T7.
5. Seed `snapshots/LATEST.json` with `snapshot_latest.py write --built-at 2026-10-29T22:32:13Z`
   from the Box copy, counts from the test database after T1.
6. `.claude/commands/sync-db.md`, `start-task.md`, RUN.md, DASHBOARD.md, WORKFLOW-SETUP.md,
   ARCHITECTURE.md.
7. pytest, verify-cee against the test database, T8 (shared database unchanged), teardown.

### Test setup: a throwaway database, never the shared `cee`
The shared container `cee-db` (database `cee`, snapshot `corpus-2026-10-29`) is used by others and
is never restored over, recreated or written. All restore/sync tests use a second Compose project
from the worktree `D:\ALLPROJECTS\EDJ\wt-129`:
- Variables in the test shell (PowerShell `$env:...`, Git Bash `export ...`):
  `COMPOSE_PROJECT_NAME=cee-synctest`, `CEE_DB_CONTAINER=cee-synctest-db`, `CEE_DB_PORT=5433`,
  `DATABASE_URL=postgresql://cee:cee@localhost:5433/cee`, `CEE_VECTORS=off`,
  `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\tmp\p129-nomodel` (empty folder: proves no model
  is needed), `PYTHONPATH=<wt>\src`, `TMP`/`TEMP=D:\ALLPROJECTS\EDJ\cache\tmp`.
  Own project name -> own volume `cee-synctest_cee-pgdata`; own container name and port; its
  `/snapshots` mount is `<wt>\snapshots`. If a variable is missing, Compose fails with "name
  already in use" instead of touching `cee-db` (a safe failure).
- The worktree has no `.env` (so `CORPUS_SHARE_PATH` is empty, like a teammate's fresh clone) and
  no venv: `<wt>\.venv` is a junction to `D:\ALLPROJECTS\EDJ\repo\.venv` (git-ignored; removed at
  the end with `cmd /c rmdir`, which removes the link only). sync-db's `pip install -r
  requirements.txt` then runs against the shared venv; the branch does not change
  `requirements.txt`, so it installs nothing.
- Build tests (T6-T7) set `CORPUS_SHARE_PATH=D:\ALLPROJECTS\EDJ\cache\tmp\p129-share`, a folder
  holding junctions `raw` -> `C:\Users\14370\Box\EDJ\raw` and `parsed` -> `...\Box\EDJ\parsed`,
  so ingestion reads the real files but the build's copy step writes `snapshots/` into the temp
  folder, never into the team Box folder. Junctions are removed with `cmd /c rmdir` (never
  `Remove-Item -Recurse`, which can delete through a junction).
- Before and after everything (T0 / T8): `docker inspect cee-db --format "{{.State.StartedAt}}"`,
  its stamp and `documents`/`chunks`/`entities` counts (read-only `psql` against `cee`).
- Teardown: `docker compose -p cee-synctest down -v`, junctions and temp folders removed.

### Tests (each on `sync-db.ps1` in PowerShell and `sync-db.sh` in Git Bash, unless noted)
- T1 fresh + dump in `snapshots/`: `docker compose -p cee-synctest down -v`; copy
  `corpus-2026-10-29.dump` into `<wt>\snapshots`; `sync-db` -> `Using <wt>\snapshots\...`,
  restore, stamp `corpus-2026-10-29`, smoke five `[ok]` + `PASS`, notes printed, exit 0.
- T1b fresh + dump only in Box: down -v, remove the local copy -> found under
  `C:\Users\14370\Box\EDJ\snapshots`, same result.
- T2 second run: `Already up to date: corpus-2026-10-29. Nothing to do.`, exit 0, no
  `Restoring` line, test database counts unchanged.
- T3 wrong dump: copy of `LATEST.json` (via `-Latest`) with a wrong sha256 -> message names the
  file and says it differs, the download line, exit 2; test database stamp and counts unchanged.
  Old dump: `name` = `corpus-2026-10-27`, sha256 of 10-29 -> exit 2, unchanged. Unknown name
  `corpus-2099-01-01` -> `Download corpus-2099-01-01.dump from the Box snapshots folder into ...`,
  exit 2, unchanged.
- T4 `-Check` / `--check`: up to date -> exit 0; `-Latest` naming another snapshot -> the
  "Run /sync-db" line, exit 2; container stopped (`docker compose -p cee-synctest stop`) -> one
  line, exit 1 (then start it again).
- T5 no model: `grep -n "embed\|fastembed" scripts/sync-db.*` -> only the printed `--missing`
  hint; T1-T4 ran with `CEE_VECTORS=off` and an empty model folder; the folder is still empty.
- T6 `build-snapshot.ps1 -AllowBranch` (PowerShell) on the test database: full run ->
  `snapshots/LATEST-test.json` with name `corpus-<today>-test`, sha256 equal to
  `Get-FileHash` of `<wt>\snapshots\corpus-<today>-test.dump`, documents/chunks equal to the test
  database counts, `built_at` today UTC, notes `test build`; nothing new in
  `C:\Users\14370\Box\EDJ\snapshots`. Then `sync-db -Latest snapshots/LATEST-test.json` on a
  fresh test volume -> smoke PASS (round trip). Same with `build-snapshot.sh --allow-branch` in Git
  Bash (sha256 checked with `sha256sum`).
- T7 official path, without touching any database: `build-snapshot.ps1` / `.sh` without notes
  -> `Pass -Notes "<what changed, issue numbers>"` (`--notes`), exit 1, before the branch check;
  `git check-ignore -v snapshots/LATEST.json` -> not ignored, `snapshots/x.dump` and
  `snapshots/LATEST-test.json` -> ignored; the official `write` call is the same function the
  pytest covers.
- T8 the shared `cee-db` has the same `StartedAt`, stamp `corpus-2026-10-29` and counts as T0.

## Acceptance
- [ ] Issue "Fresh clone + dump in `snapshots/` -> `sync-db` ends with smoke PASS on Windows and
      Mac" -> T1 (and T1b) on Windows with `sync-db.ps1`, and `sync-db.sh` in Git Bash: smoke PASS,
      exit 0. **Mac itself needs a teammate's Mac** (`bash scripts/sync-db.sh` on a fresh clone with
      the dump in `snapshots/` -> PASS); if not done by PR time, the PR says `Part of #129` with this
      item open.
- [ ] Issue "Wrong or old dump -> clear message, database untouched" -> T3: exit 2, message names
      the file and the Box download step; test database stamp and counts identical before/after.
- [ ] Issue "Second run on an up-to-date machine does nothing but say so" -> T2: one "Already up to
      date" line, exit 0, no restore.
- [ ] Issue "build-snapshot writes a correct `LATEST.json`" -> T6 (real `-AllowBranch` builds, both
      twins, fields checked against the dump hash and the database counts) + pytest on `write`
      (exact format) + T7 (official path asks for notes; `LATEST.json` is tracked, dumps are not).
- [ ] Issue deliverable `/start-task` check -> T4 (`-Check` exit codes) and `start-task.md` step 2
      text; `.claude/commands/sync-db.md` exists and names both scripts.
- [ ] Issue deliverable RUN.md -> section 2 is `/sync-db` or the script; every new `powershell`
      block is followed by its `bash` twin (count of both fence kinds equal); no snapshot txt is a
      step anywhere (`grep -n "\.txt" docs/RUN.md docs/DASHBOARD.md docs/WORKFLOW-SETUP.md` -> only
      `requirements*.txt`).
- [ ] Vectors off, no model (ADR-009/010) -> T5.
- [ ] Shared database untouched -> T8.
- [ ] `pytest -q` all pass; `bash -n scripts/*.sh` clean.
- [ ] Issue "verify-cee all features PASS" -> `python scripts/verify_cee.py run` with
      `CEE_DB_CONTAINER=cee-synctest-db` and `DATABASE_URL` on port 5433, after T1 (snapshot
      `corpus-2026-10-29`): all features PASS, run id in the PR. (If port 8599 is taken by the #84
      run, wait until it is free; verify-cee is not run on the shared container.)
- [ ] Paid API calls: 0.

## Risks
- Compose interpolation in `container_name` changes nothing for people without the variables
  (checked with `docker compose config`); a typo there would rename everyone's container, so the
  pytest also pins the defaults.
- `pip install` in sync-db can be slow on a first run; it is quiet (`-q`) and runs before the
  "already up to date" check, as the issue orders.
- A teammate not on `main` gets no pull; the warning says so. Switching branches for them could
  lose work, so the script does not.
- Box Drive placeholders: reading the file makes Box fetch it; a half-synced file fails the sha256
  check with the download message, never a restore.
- If `restore` fails half-way the local database is incomplete; the error says to run `/sync-db`
  again (that is what the txt route did too).
- Mac is checked only through Git Bash until a teammate runs it.

## Open questions
- `/start-task` check placement: right after `git pull` (step 2), not literally the first step.
- On a branch other than `main`, sync-db warns and does not pull/switch. Alternative: refuse to run.
- `LATEST.json` is seeded now with `corpus-2026-10-29` so `/sync-db` works before #120.

## Progress log
- 2026-11-08 12:00 - plan written (worktree `D:\ALLPROJECTS\EDJ\wt-129`, branch `tl/129-sync-db` from origin/main 83e9152); Docker Desktop was not running, so the shared database was not queried; dump sha256 of Box and local `corpus-2026-10-29.dump` read (equal)
