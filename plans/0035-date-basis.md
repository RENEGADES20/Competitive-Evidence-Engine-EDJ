# 0035 - date_basis in the manifest and documents

Issue: #35    Role: TL    Spec: docs/DECISIONS.md (ADR-007 T-09), specs/transcripts-ir.md

## Goal
Every document records whether `published_at` came from the source (`source`) or, for an
undated page, from the retrieval date (`retrieved`), so S1's time windows (#49) can leave the
latter out of recency questions (Q26, Q27).

## Files to change
- src/cee/ingest/manifest.py - `date_basis` in FIELDS; `date_basis_of(row)`: missing or empty
  reads `source`, anything but source/retrieved is an error; `upsert_row` fills the default,
  so `edgar.py` and `releases.py` need no change
- db/schema.sql - `documents.date_basis text NOT NULL DEFAULT 'source'` with a CHECK
- src/cee/ingest/load.py - `ensure_schema()` adds the column to an existing database
  (ADD COLUMN IF NOT EXISTS) before loading; INSERT writes the value
- data/manifest.csv - the column added, all 68 rows `source`
- tests/test_manifest.py - default, old manifest without the column, invalid value, upsert
- specs/transcripts-ir.md - one line on when to write `retrieved`

## Steps
1. Tests first for `date_basis_of` and `upsert_row`.
2. manifest.py, schema.sql, load.py.
3. Rewrite data/manifest.csv with the column (values `source`).
4. On the existing local database (corpus-2026-10-18, no column): `python -m cee.ingest.load`;
   row counts before and after; `SELECT date_basis, count(*) FROM documents GROUP BY 1`.
5. Fresh schema: `docker compose down -v`, restore the snapshot, load again (column added).
6. pytest; verify_cee.py run (mock).

## Acceptance
- [x] `data/manifest.csv` has a `date_basis` column; existing rows read `source`
- [x] `python -m cee.ingest.load` on an existing database adds the column without losing rows
- [x] `SELECT date_basis, count(*) FROM documents GROUP BY 1` pasted in the PR
- [x] `pytest -q` passes; `verify_cee.py run` all PASS; 0 real calls

## Progress log
- 2026-10-19 - plan written; branch tl/35-date-basis created
- 2026-10-19 - manifest.py (`date_basis_of`, default in `upsert_row`), schema.sql, load.py
  (`ensure_schema`, INSERT, check before any write), 2 tests; pytest 108 passed.
- 2026-10-19 - manifest rewritten with the column: 68 rows, all `source` (every date so far was
  read from the document itself).
- 2026-10-19 - Existing database (corpus-2026-10-18, no column): load added it, 68 docs /
  14,682 chunks / query_log 0 before and after, `source 68`, 12 s (parse cache).
  Fresh schema: `build-snapshot.ps1 -AllowBranch` -> 68 docs, column default 'source', NOT
  NULL; an INSERT with 'download' violates documents_date_basis_check. Test dump deleted.
  verify-cee all PASS (.verify-runs/20261019-205934-2edd2dc). 0 real calls.
