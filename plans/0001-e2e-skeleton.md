# 0001 - End-to-end skeleton

Issue: #13    Role: TL    Spec: docs/ARCHITECTURE.md, docs/DECISIONS.md (ADR-001, 002, 005, 006)

## Goal
One real document goes all the way through: ingested -> stored -> searched -> answered
(badly is fine) -> shown with a citation that opens the stored source. Every teammate runs
it on their own Windows machine by end of W2, so nobody starts W3 from a blank file.

## Files to change
- `docker-compose.yml` - Postgres 16 service, named volume, port 5432
- `pyproject.toml` / `requirements.txt` - pinned dependencies (edgartools, docling, pymupdf, psycopg, streamlit, anthropic, openai, pyyaml)
- `src/` - minimal packages: ingest, store, retrieve, answer, app (layout decided here)
- `db/schema.sql` - tables from the ARCHITECTURE.md draft
- `scripts/restore` and `scripts/build-snapshot` - see below
- `docs/RUN.md` - the run page: setup, daily use, "when it breaks"
- `README.md` - replace the quick-start placeholder with real commands

## Steps
1. Docker Compose Postgres; `schema.sql` applied on first start.
2. PDF tool check (ADR-005): install docling on all 7 machines (Windows, Python 3.11).
   Record per machine: installs? parses a sample investor-day PDF with page numbers?
   If any machine fails, switch the parser interface to pymupdf for everyone or per machine; note it in ADR-005.
3. Ingest one real document: EDJ 10-K (CIK 815917) via edgartools -> raw file in the shared
   folder -> manifest row -> sections -> chunks with prefix `[EDJ||10-K|<period>]`.
4. Search: one FTS query over `chunks.tsv` with entity filter.
5. Answer: one LLM call returning the Answer JSON; validator checks chunk_ids; gap path
   returns "no evidence" when retrieval is empty (built now, not later).
6. Streamlit page: question box, answer, citation link -> source view of the stored chunk.
7. `build-snapshot`: from a clean `main` checkout, drop and recreate the database, re-ingest
   everything listed in `data/manifest.csv` from the shared folder (verify sha256), then
   `pg_dump -Fc` to `corpus-YYYY-MM-DD.dump` and copy it to the shared `snapshots/` folder.
8. `restore <dump>`: one command that starts Docker Postgres if needed, drops the local
   database and runs `pg_restore` from the given (default: latest) snapshot in `CORPUS_SHARE_PATH/snapshots/`.
9. Write `docs/RUN.md`: install Docker Desktop + Python + Git + gh, copy `.env.example`,
   `restore`, run the app, top 10 errors and fixes.
10. Install session: each teammate follows RUN.md unaided on their machine; fix what breaks.

## Acceptance
- [ ] Asking "What does Edward Jones's 10-K say about its number of financial advisors?"
      returns an answer with at least one citation that opens the stored 10-K chunk.
- [ ] Asking about Vanguard returns the gap path (behavior `gap_with_adjacent` or `refuse`), no invented facts.
- [ ] `build-snapshot` then `restore` on a second machine gives identical row counts.
- [ ] docling install result recorded for all 7 machines; fallback decided.
- [ ] All 7 people have run the skeleton end to end (names ticked in PROGRESS.md). Gate 1.

## Progress log
- 2026-09-28 - plan written
- 2026-09-30 - Scope for #13 narrowed to the TL machine; the other six installs and Gate 1 moved to #14.
- 2026-09-30 - Built: docker-compose (postgres 16.10) + db/schema.sql (no embedding column per
  ADR-001; chunks.prefix separate from text); EDJ 10-K FY2025 fetched with edgartools into Box
  raw/ (flat, relative storage_path), 335 chunks split by Item; FTS with SQL entity filter
  (MER only sees BAC chunks tagged GWIM/Merrill); Answer JSON + citation check (flag, never
  drop); empty retrieval answers in code without an LLM call (gap_with_adjacent for covered
  firms, refuse + suggested sources for mapped expansion firms such as Vanguard); Streamlit
  ask page + source view; build-snapshot/restore/ingest PowerShell scripts; cee.smoke; 11 tests.
- 2026-09-30 - Surprises: Windows PowerShell 5.1 treats docker's stderr progress as an error
  (fixed in scripts/_common.ps1); setting an env var to "" in PS 5.1 deletes it, so the
  teammate route was tested with an .env whose CORPUS_SHARE_PATH is empty; writing HTML with
  Python text mode changed line endings (now written byte-exact). The Anthropic key in use
  is not workspace-scoped: added optional ANTHROPIC_WORKSPACE_ID.
- 2026-09-30 - Checks: pytest 11 passed; smoke PASS; restore from Box Drive and from a hand-
  downloaded dump both give documents=1, chunks=335, entities=6; docling parses a 10-page PDF
  with page numbers on the TL machine (ADR-005). Real Anthropic acceptance call: pending workspace ID.
