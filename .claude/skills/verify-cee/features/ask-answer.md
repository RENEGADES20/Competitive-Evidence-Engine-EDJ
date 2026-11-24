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
- `ask-matrix` (#247): the answer is written from the evidence matrix (map step, then the reduce
  step; on by default): the shown behavior is the matrix's (`filters->'map'->>'behavior'`; or
  `answer_with_boundary` when code withheld a normative sentence, `filters->'reduce'->>'behavior_rejudged'`
  true), no claim cites outside the matrix (`filters->'reduce'->>'outside_matrix'` = 0), every
  cited id is in the row's `chunk_ids` (retrieval plus corrective re-search hits, origin in
  `filters->'chunk_origin'`), and every citation chip is linked. The code-built answers (refuse,
  incomplete, an evidence-free boundary answer), the comparison claim, the why-lines and the
  newest-first order need a model or a failed extraction; proven by `tests/test_reduce.py`, not
  driven here. The "Incomplete" header and its warning are rendered in `tests/test_reduce.py`.
- `ask-part-gap`: every part of the question's plan has a cited claim, an adjacent item or a gap
  (since #247 the matrix's code gaps name every cell that holds nothing); a part with none of
  them gets a gap built by code, flagged `part_gap` (chip on the gap box) (#215). Its wording
  comes from the part's candidate pool: "No evidence retrieved for: <part>" when the part's search
  found nothing, else "Not answered from the evidence retrieved for: <part>". The mock cites its
  top 3 passages only, so a two-firm mock answer usually gets a part gap for the firm it did not
  cite; since #245 every sub-question (firm x aspect) is a part, so a five-firm mock answer can
  show up to four such gaps (expected, not a failure). An uncited grid cell moved to gaps (`uncited_cell`) needs a model; proven by
  `tests/test_part_check.py`, not driven here.
  With `REDUCE_PROMPT=v7` (#292) a synthesis sentence whose part_id is an aspect id covers each cell of that aspect
  whose chunk it cites (`part_coverage` state `aspect`); the driver reads the cells from `filters.map.cells`.
  With `REDUCE_PROMPT=v8` a holding cell the answer does not cite is covered by the evidence list (no part gap;
  `part_coverage` state `evidence_list`); the driver treats every fact or derived cell as covered.
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
- **Matrix (#247).** The newest `query_log` row: `filters.map.behavior` equals `answer.behavior`
  (or the documented re-judge), `filters.reduce.outside_matrix` is 0, no cited id is missing
  from `chunk_ids`, and the page shows no "not in the retrieved set" chip. The verify app runs
  with `MAP=on` set by the driver.
- **Part gaps.** After the EDJ question (one sub-question) and after the two-firm question
  "How do Morgan Stanley and Raymond James approach advisor recruiting?" (rule plan, #245:
  sub-questions a1.MS, a1.RJF), read the newest `query_log` row: the gaps flagged `part_gap` are exactly one per plan
  part that no claim, adjacent item or code gap names (`part_id`), and each such gap's text and a
  `part_gap` chip are on the page (expected for the EDJ question: none).
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
