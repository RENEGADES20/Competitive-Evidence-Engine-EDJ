# Coverage page

A user opens Coverage and sees, for each core firm and each document type the source
registry expects, how many documents are stored and their date range; empty and thin
combinations stand out.

## Sub-features

- `cov-table`: firms (EDJ, MS, SCHW, RJF, MER, BAC filings) x document types.
- `cov-cell`: each cell says COVERED, THIN or EMPTY with a count and earliest/latest date.
- `cov-note`: a note says themes are not shown yet.

## How to get to it (user POV)

- Click "Coverage" in the top navigation, or open `/coverage`.

## Driving it

Preconditions: baseline.

- **Open.** Go to `<app>/coverage`. Wait for "are not shown yet". Page text has EDJ and 10-K.
- **Read-back.** Count and min/max `published_at` of EDJ 10-K in `cee_verify` equal the cell
  text (`THIN 1 doc <date>` with one document; the cell is one line of state, one of count, then dates).
- **Empty.** If the registry expects an EDJ type with no document, `EMPTY 0 docs` is shown.
- **Note.** Page text contains "Themes (tier 5 research) are not shown yet".

## Gotchas

- Thin means one document or fewer (constant `THIN_MAX` in `coverage_page.py`).
- A cell reads "not tracked" when the registry does not expect that type for the firm.
