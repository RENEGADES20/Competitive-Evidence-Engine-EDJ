# Ask a question

A user types a question and gets an answer whose claims each link to a stored passage.

## Sub-features

- `ask-heading`: the answer type is shown as a heading (Answer, Not in the corpus, ...).
- `ask-citations`: each claim carries one or more citation links.
- `ask-coverage`: a coverage note ("Coverage: searched ...") names the firms, document
  types and period of the retrieved passages; always visible, never collapsed (#40).
- `ask-withheld`: a claim that recommends an action for the home firm is not shown; a
  "Withheld:" notice takes its place (#118). The mock never writes one, so this is proven by
  tests in `tests/test_validate.py`, not driven here.
- `ask-footer`: the footer shows firms, chunk count and whether an LLM was called.
- `ask-log`: every asked question writes one `query_log` row.
- `ask-theme-gap`: a question about several firms on one theme (Q21) gets a coverage line
  "No passages on the theme (...) for X" naming each firm with no passage on it (#117).

## How to get to it (user POV)

- Open the app, type into "Question", press "Ask".

## Driving it

Preconditions: baseline.

- **Ask.** Fill textbox "Question" with the answerable question, click button "Ask".
  A heading such as "Answer" appears.
- **Citations.** At least one link whose address contains `?chunk=`.
- **Coverage.** Page text contains a line starting `Coverage: searched`.
- **Footer.** Page text contains `LLM called: False` (mock).
- **Side effect.** `SELECT count(*) FROM query_log` in `cee_verify` is one higher than
  before the ask.
- **Theme gap.** Ask Q21 ("What do we know about the generational wealth transfer, and how
  are these five preparing for it?"). The firms named after
  `No passages on the theme (Generational wealth transfer) for` in the `Coverage:` line are
  exactly the firms with no on-theme chunk in the database (read from `cee_verify` with the
  question's entity filter, the theme's keyword filter and its document-type scope); with no
  such firm the phrase is absent. A firm with one on-theme chunk is no gap even when it ranks
  below the floor (#190: MS's `MS-DECK-2026-strategic-update#22`). corpus-2026-11-16 alone:
  Raymond James Financial is the gap; with the trade press loaded (#57) RJF has on-theme
  articles and no firm is.

## Gotchas

- Typing alone does not ask; only the "Ask" button does.
- The mock answers whenever retrieval finds something. A PASS here says nothing about
  answer quality.
