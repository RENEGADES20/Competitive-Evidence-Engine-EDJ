# Filters

On the Ask page a user narrows a question with sidebar filters: firms, a published-date
range and keywords. Only passages that match every filter are searched; the filters are SQL
`WHERE` clauses, never prompt text. The answer's meta line lists the filters used, and they
are stored with the query in `query_log.filters`.

## Sub-features

- `filter-firm`: firm multiselect; every cited chunk is from a chosen firm (MER keeps BAC GWIM chunks).
- `filter-dates`: date range, both ends inclusive; documents dated only by download are left out.
- `filter-keywords`: comma-separated; every keyword must appear in the passage.
- `filter-log`: the meta line and `query_log.filters` show the filters.

## How to get to it (user POV)

- Open Ask. The sidebar shows **Filters**. Pick firms, a start and end date, type keywords, then ask.

## Driving it

Preconditions: baseline.

- **Set.** In the sidebar pick `RJF` in Firms, type `2026-01-01 – 2026-06-30` in Date range
  and press Enter, type `advisor` in Keywords and press Enter.
- **Ask.** "What do the firms say about advisor recruiting?" (names no firm). Wait for "LLM called:".
- **Meta line.** Contains `filters: firms RJF; dates 2026-01-01 to 2026-06-30; keywords advisor`.
- **Read-back.** For every citation link, `cee_verify` says entity `RJF`, `published_at` in the range
  with `date_basis = 'source'`, and the chunk's `tsv` matches the keyword.
- **Log.** The newest `query_log` row's `filters` holds `firm_filter`, `date_range`, `keywords`.
- **Prompt.** `src/cee/answer/prompt.py` does not read the filter fields.

## Gotchas

- Firms intersect with the firms the question names. A filter that leaves none of them gives
  "No evidence", never every firm.
- One picked date is not a range: the filter waits for the end date and says so in the sidebar.
- Filters show on the Ask page only.
