# 0049 - Time windows in SQL for recency questions

Issue: #49    Role: S1    Spec: specs/retrieval.md (+ ADR-007 T-09, `date_basis` from #35)

## Goal
`resolve()` recognises time phrases ("last 90 days", "since the start of the year") and
sets a date window; `search()` filters `published_at` to that window in SQL and leaves out
documents whose date is only the download date (`date_basis = 'retrieved'`).

## Files to change
- `src/cee/retrieve/fts.py`
  - `Query.window`: `(from, to)` dates or `None`.
  - `resolve(question, today=None)` parses "last/past N days|weeks|months", "since the
    start/beginning of the year" (calendar year of today, the spec's proposal), "year to
    date" / "YTD". `today` defaults to the real date; tests pass a fixed one.
  - The time phrase is stripped from the search terms (no "last", "90", "days" in ranking).
  - `window_filter()`: `d.date_basis = 'source' AND d.published_at BETWEEN from AND to`;
    no window -> `TRUE`.
- `tests/test_fts_window.py` (new) - phrase parsing (no database) and dated fixture rows
  around each window edge plus a `retrieved` row, in a throwaway schema of the local
  Postgres; skipped when Postgres is not reachable.
- `specs/retrieval.md` - close the open question: "start of the year" = calendar year.

## Steps
1. Tests first: fixture rows at today-91 / -90 / -89 / today, 31 Dec / 1 Jan, a
   `retrieved` row inside each window, a BAC non-GWIM row for Q27.
2. Window parsing in `resolve`, phrase stripped from terms.
3. SQL filter in `search`.
4. Local database: add `date_basis` (same ALTER as `cee.ingest.load`, #35; every document
   `source`). Q26/Q27 retrieval checks on corpus-2026-10-18; before/after top-20 for the
   5 no-time-phrase questions (Q2, Q5, Q6, Q8, Q12).
5. `pytest -q`; `verify_cee.py run` (mock).

## Acceptance
- [x] Q26 returns nothing older than 90 days (fixture test + corpus check)
- [x] Q27 returns nothing before 1 January of the current year (fixture test; corpus: Q27 has
      0 hits until #37, so the cut was checked on BAC "since the start of the year")
- [x] `date_basis = retrieved` documents never appear inside a window (fixture test)
- [x] No time phrase -> hit lists unchanged on 5 sample questions (Q2, Q5, Q6, Q8, Q12)
- [x] `pytest -q` 153 passed; `verify_cee.py run` 4 PASS + download-document UNREACHABLE
      (raw file not in local `data/raw/`); 0 real calls

## Out of scope
Quotas and dedupe (#59), UI date filter (U1), newest-first ordering of Q26 answers
(passes_if; ordering is not a filter), "last eight quarters" (Q23: a reporting-period span,
not a recency window), number words ("last ninety days").

## Notes
- Built on `s1/89-synonyms-peer-set` (PR #94, not merged): both edit `fts.py`. Rebase onto
  main once #94 merges.
- No snapshot newer than corpus-2026-10-18 exists in Box; it predates `date_basis`, so no
  real document is `retrieved` yet - the exclusion is proven by the fixture test only.

## Progress log
- 2026-10-21 14:19 - plan written (drafted and shown before #89); branch `s1/49-time-windows`
- 2026-10-21 - fixture tests first (failed: no window_filter), then window parsing and SQL
  filter; 19 window tests pass (throwaway schema `test_fts_window`, dropped after).
- 2026-10-21 - local database: `date_basis` added with the #35 ALTER (68 docs, all
  `source`). As of 2026-10-21: Q26 -> 17 hits, all `RJF-10Q-2026Q2` (2026-08-05), nothing
  before 2026-07-23 (as expected_results predicted for this date). Q27 -> 0 hits (MER needs
  GWIM tags, #37). BAC "since the start of the year": top-200 earliest 2026-01-14, 0 before
  1 Jan (without the window: 69 of 200). Q2/Q5/Q6/Q8/Q12 identical. Spec open question closed.
- 2026-10-22 - pytest 153 passed; verify-cee VERIFY PASS
  (.verify-runs/20261022-002532-11efc36, run on the uncommitted working tree;
  download-document UNREACHABLE, raw file absent).
