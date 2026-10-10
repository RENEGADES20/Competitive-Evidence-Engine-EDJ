# 0002 - Map expansion eleven; seed source registry data

Issue: #2    Role: C1    Spec: specs/filings.md

## Goal
The expansion eleven are documented with their reporting shape (mapped, not ingested), the
core entities' `expected_sources` are checked, and the data for the `source_registry` table
exists as a C1-owned file.

## Files to change
- docs/EXPANSION.md - new: reporting shape, verified CIKs and forms for the eleven
- config/source_registry.csv - new: one row per core entity + doc type (columns match db table, plus `note`)
- config/entities.yaml - RJF gets `monthly`; header comments point to the two new files
- docs/PROGRESS.md - one line

## Steps
1. Check core filings on EDGAR (forms filed since 2024-10-01).
2. Write source_registry.csv from `expected_sources`; consistency check against the yaml.
3. Check expansion CIKs, forms and segment names on EDGAR; write EXPANSION.md.
4. Not in scope: loading the CSV into Postgres (needs a change in TL-owned `src/cee/ingest/load.py`).

## Acceptance
- [x] Expansion eleven listed with reporting shape (docs/EXPANSION.md)
- [x] `expected_sources` filled for all core entities, and every (entity, doc_type) has exactly one CSV row
- [x] Nothing ingested for the eleven (documents table: only EDJ-10K-2025)
- [x] Q29: gap_with_adjacent, `suggested_source` lists the checked MS sources
- [ ] Q28: returns `answer` from 8 EDJ-10K chunks (mock), expected gap_with_adjacent. Not caused by
      this config change (no code touched); retrieval/answer path is S1/S2 - flagged in PR
- [x] `git diff main -- evals/questions.yaml src/` -> empty
- [x] pytest all pass; smoke PASS

## Progress log
- 2026-10-10 - plan written; branch c1/2-expansion-registry (from main; PR #20 not merged yet)
- 2026-10-10 - Core filings match yaml: EDJ has 10-K/10-Q/8-K and no DEF 14A; MS, SCHW, BAC, RJF file all four.
- 2026-10-10 - Surprise: RJF files monthly "RJF OPERATING DATA" as 8-K Item 7.01, but yaml had no `monthly`. Added.
- 2026-10-10 - Expansion: CIKs found for 9 public firms (UBS 20-F/6-K, RBC 40-F/6-K). Fidelity and
  Vanguard have several EDGAR entities each; left TODO-verify. Wealth segment names confirmed by
  full-text search except LPLA and HOOD (TODO-verify).
- 2026-10-10 - IR-page URLs (transcripts, supplements, decks, press) and Form ADV CRD numbers not
  checked yet: marked TODO-verify in the CSV `note` column.
- 2026-10-10 - Ran Q28/Q29 on corpus-2026-09-30. Q29 OK. Q28 answers from EDJ-10K chunks instead of
  a gap; outside C1 scope, reported in the PR for S1/S2.
