# No evidence

When nothing stored answers the question, the app says so and names what would fill the
gap. Ground rule 3: "No evidence" is a correct answer.

## Sub-features

- `gap-heading`: heading "Not in the corpus" or "No evidence".
- `gap-no-cites`: no citation links at all.
- `gap-note`: a "Gap:" box, with a suggested source when one is known.

## How to get to it (user POV)

- Ask about a firm or topic the corpus does not cover yet.

## Driving it

Preconditions: baseline; no Morgan Stanley filings stored.

- **Ask.** Ask the no-evidence question. Heading "Not in the corpus" or "No evidence".
- **No invented sources.** Zero links containing `?chunk=`.
- **Gap note.** Page text contains "Gap:".

## Gotchas

- Once MS filings are ingested this question stops being a gap; switch to a firm or
  topic still missing and update README.md and `NO_EVIDENCE_Q` together.
