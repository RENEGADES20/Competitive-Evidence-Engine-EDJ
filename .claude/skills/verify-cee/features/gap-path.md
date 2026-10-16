# No evidence

When nothing stored answers the question, the app says so and names what would fill the
gap. Ground rule 3: "No evidence" is a correct answer.

## Sub-features

- `gap-heading`: heading "Not in the corpus" or "No evidence".
- `gap-no-cites`: no citation links at all.
- `gap-note`: a "Gap:" box, with a suggested source when one is known.
- `gap-footer`: the footer's `firms:` names the same firm as the gap box, marked
  "(no documents)" when nothing is stored for it; never `none` (#50).

## How to get to it (user POV)

- Ask about a firm or topic the corpus does not cover yet.

## Driving it

Preconditions: baseline; no LPL Financial documents stored.

- **Ask.** Ask the no-evidence question. Heading "Not in the corpus" or "No evidence".
- **No invented sources.** Zero links containing `?chunk=`.
- **Gap note.** Page text contains "Gap:".
- **Footer firms.** The footer reads `firms: LPLA (no documents)`, not `firms: none`.

## Gotchas

- Once LPL documents are ingested this question stops being a gap; switch to a firm or
  topic still missing and update README.md and `NO_EVIDENCE_Q` together. (MS was the gap
  firm until #36 stored its filings.)
