# 0072 - Wait for the real Postgres server before restoring

Issue: #72    Role: TL    Spec: docs/ARCHITECTURE.md (shared corpus, snapshots), docs/RUN.md

## Goal
`scripts\restore.ps1` works on the first run after `docker compose down -v` or on a
teammate's first install, without a manual retry.

## Cause
On an empty volume the postgres image runs initdb and `/docker-entrypoint-initdb.d`
(`db/schema.sql`) on a temporary server, shuts it down, then starts the real server. The
temporary server is started with `listen_addresses=''`, so it listens on the Unix socket only.
The healthcheck `pg_isready -U cee -d cee` also uses the socket, so it can pass against the
temporary server. `docker compose up -d --wait` then returns "Healthy" and `Reset-Database`
hits `FATAL: the database system is shutting down`.

## Fix (simplest robust option)
Run the healthcheck over TCP: `pg_isready -h 127.0.0.1 -U cee -d cee`. Only the real server
listens on TCP, so "Healthy" now means the real server accepts connections. No retry loop is
needed in `Start-Database`, and every other `docker compose up --wait` caller gets the fix too.
Rejected: a retry loop in `Start-Database` ("select 1" twice in a row). It needs more code, it
only covers the scripts, and "twice in a row" still depends on timing.

## Files to change
- docker-compose.yml - healthcheck uses TCP; comment explains why.
- plans/0072-db-ready-wait.md - this plan.
- docs/RUN.md - no change: no manual step is left.

## Steps
1. Reproduce on main; show the race in a throwaway container whose init script sleeps.
2. Change the healthcheck.
3. `docker compose down -v` then `restore.ps1`, 3 times; each must succeed on the first run.
4. `python -m cee.smoke` and `scripts/verify_cee.py run` with LLM_PROVIDER=mock.

## Acceptance
- [x] Linked questions: none (infrastructure).
- [x] 3 x (`docker compose down -v`; `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1`)
      -> exit 0 and `chunks=12097, documents=25` (corpus-2026-10-15) each time.
- [x] Throwaway container during init: old check exit 0, new check exit 2 (no response).
- [x] `python -m cee.smoke` PASS; `scripts/verify_cee.py run` PASS (mock, 0 paid calls).

## Progress log
- 2026-10-15 23:40 - plan written. Logs on main show a connection hitting
  `FATAL: the database system is shutting down` during the init-to-real-server handoff. 1 full
  restore and 6 up/psql cycles on main passed: the race is timing-dependent. A throwaway
  container with a 15 s init script proved it: socket pg_isready "accepting" (exit 0), TCP
  pg_isready "no response" (exit 2) until init completes.
- 2026-10-15 23:46 - healthcheck changed. 3 x (down -v; restore.ps1): exit 0 on the first run
  each time, chunks=12097, documents=25, entities=6, no FATAL in container logs.
- 2026-10-15 23:47 - cee.smoke PASS; verify_cee run all 5 PASS (mock, 0 paid calls),
  .verify-runs/20261015-234655-7f6f3dc. RUN.md unchanged: no manual step left.
