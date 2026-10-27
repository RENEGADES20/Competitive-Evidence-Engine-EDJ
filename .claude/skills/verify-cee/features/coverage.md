# Coverage page

A user opens Coverage and sees, for each core firm and each document type the source
registry expects, how many documents are stored and their date range; empty and thin
combinations stand out.

## Sub-features

- `cov-table`: every firm in `config/entities.yaml` (in config order) x document types.
- `cov-cell`: each cell says COVERED, THIN or EMPTY with a count and earliest/latest date.
- `cov-note`: a note says themes are not shown yet.

## How to get to it (user POV)

- Click "Coverage" in the top navigation, or open `/coverage`.

## Driving it

Preconditions: baseline.

- **Open.** Go to `<app>/coverage`. Wait for "are not shown yet". Page text has EDJ and 10-K.
- **Read-back.** Count and min/max `published_at` of EDJ 10-K in `cee_verify` equal the cell
  text (`COVERED 1 doc <date>` for one annual 10-K; the state follows `cell_state(n, expected_cadence)`;
  the cell is one line of state, one of count, then dates).
- **Empty.** If the registry expects an EDJ type with no document, `EMPTY 0 docs` is shown.
- **Note.** Page text contains "Themes (tier 5 research) are not shown yet".

## Gotchas

- Thin means fewer documents than one period of the registry's `expected_cadence` (`COVERED_MIN`
  in `coverage_page.py`: annual 1, quarterly 4, monthly 3, other 2).
- MER's row note counts BAC chunks tagged GWIM, the same rule as the retrieval filter.
- A cell reads "not tracked" when the registry does not expect that type for the firm.
