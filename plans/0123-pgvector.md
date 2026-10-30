# 0123 - pgvector image and embedding column

Issue: #123    Role: TL    Spec: docs/ARCHITECTURE.md (schema), ADR-001 (docs/DECISIONS.md)

## Goal
The local database can store vectors for hybrid retrieval (#125): the Docker image ships
pgvector, `chunks` has an `embedding` column and index, and every snapshot, old or new,
restores on Windows and Mac without changing what FTS retrieves.

## Files to change
- docker-compose.yml - image `postgres:16.10` -> a pgvector image; mount `db/upgrade.sql`
- db/upgrade.sql (new) - idempotent: vector extension, `chunks.embedding vector(384)`, HNSW index
- db/schema.sql - header note only
- scripts/_common.ps1, scripts/_common.sh - `Update-Schema` / `upgrade_schema` helper
- scripts/restore.ps1, scripts/restore.sh - run the upgrade after `pg_restore`
- scripts/build-snapshot.ps1, scripts/build-snapshot.sh - run the upgrade after the schema
- docs/RUN.md - one-time image update (both OS), troubleshooting rows
- docs/ARCHITECTURE.md - schema line for `embedding`

## Steps
1. Pull the pgvector image; check it has amd64 and arm64 builds.
2. Write `db/upgrade.sql` so it can run any number of times; mount it as `02-upgrade.sql`.
3. Call it from restore and build-snapshot (ps1 and sh).
4. Test on the existing volume (what teammates have), then on a fresh volume.
5. Run the eval with and without the column; retrieval must be identical.
6. RUN.md, ARCHITECTURE.md.

Unsure: whether the new image's OS matches the old one (Postgres data depends on glibc collations).

## Acceptance
- [x] Existing volume + new image: `restore.ps1` and `restore.sh` of `corpus-2026-10-29` -> 111 docs, 17183 chunks, `embedding` column + `chunks_embedding_idx`
- [x] Fresh volume (`docker compose down -v`): column created at init; restore + `cee.smoke` PASS
- [x] `db/upgrade.sql` twice: no error
- [x] `eval_run.py --as-of 2026-10-29` with and without the column: identical `chunk_ids` on Q1-Q30 (27 PASS / 3 FAIL both)
- [x] pytest passes; verify-cee all features PASS
- [ ] `restore.sh` + smoke on a real Mac (needs a teammate)

## Progress log
- 2026-10-29 23:05 - plan written after the fact: the change was started without an ExecPlan (process slip); plan reconstructed from what was done
- 2026-10-29 23:10 - `pgvector/pgvector:0.8.1-pg16` (Debian bookworm) on the existing volume: `collation version mismatch` (2.41 vs 2.36), restore could not drop the database. Switched to `0.8.1-pg16-trixie` (same OS as postgres:16.10): no warning, existing volume works
- 2026-10-29 23:20 - all checks above pass on Windows (`.verify-runs/20261029-232741-c989e76`); Mac open
