# Feedback

Under every answer a user rates it Helpful or Not helpful, adds an optional comment and clicks
"Send feedback". One `query_feedback` row is stored against the answer's `query_log` row.
Sending again for the same query replaces the earlier row (one row per query, latest wins),
and the message says so. The answer stays on the page after sending.

## Sub-features

- `fb-save`: rating (1 / -1) and comment stored with the right `query_id`.
- `fb-replace`: a second send updates, never duplicates.
- `fb-stay`: the answer is still shown after the form reruns the page.

## How to get to it (user POV)

- Ask a question on Ask; the "Feedback on this answer" box is under the meta line.

## Driving it

Preconditions: baseline.

- **Ask.** The answerable EDJ question; read the query number from `Query #N` in the meta line.
- **Send.** Pick "Not helpful", comment `verify-cee: wrong period`, click "Send feedback". Wait for
  "Feedback saved for query #N". `query_feedback` for N is exactly `-1|verify-cee: wrong period`.
  Citation links are still on the page.
- **Send again.** "Helpful", empty comment. Wait for "replaces the earlier one". Still one row: `1|`.

## Gotchas

- Without a rating the form warns and writes nothing.
- No feedback box when the query was not logged (no query number).
- Feedback is per query only; per-claim flags are out of scope (#11 answer 10).
