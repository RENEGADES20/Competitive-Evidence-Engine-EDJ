# Ask a question

A user types a question and gets an answer whose claims each link to a stored passage.

## Sub-features

- `ask-heading`: the answer type is shown as a heading (Answer, Not in the corpus, ...).
- `ask-citations`: each claim carries one or more citation links.
- `ask-footer`: the footer shows firms, chunk count and whether an LLM was called.
- `ask-log`: every asked question writes one `query_log` row.

## How to get to it (user POV)

- Open the app, type into "Question", press "Ask".

## Driving it

Preconditions: baseline.

- **Ask.** Fill textbox "Question" with the answerable question, click button "Ask".
  A heading such as "Answer" appears.
- **Citations.** At least one link whose address contains `?chunk=`.
- **Footer.** Page text contains `LLM called: False` (mock).
- **Side effect.** `SELECT count(*) FROM query_log` in `cee_verify` is one higher than
  before the ask.

## Gotchas

- Typing alone does not ask; only the "Ask" button does.
- The mock answers whenever retrieval finds something. A PASS here says nothing about
  answer quality.
