# Spec: User interface

**Owner:** U1
Rules: [CLAUDE.md](../CLAUDE.md). Design: [ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Purpose

A deliberately plain Streamlit app: ask, read, click a citation to see the source, see what
the corpus covers, leave feedback. No accounts, no mobile, no alerts.

## Reference projects

- [earnings-intelligence](https://github.com/arnenyeck06/earnings-intelligence): Streamlit app,
  query log and feedback.
- [sec-insights](https://github.com/run-llama/sec-insights): PDF viewer that highlights the cited passage.
- [dhalexander/sec-10k-rag](https://github.com/dhalexander/sec-10k-rag): company/year filters in Streamlit.

## Interface draft (sketch)

```
Page "Ask"
  inputs: question text, optional filters (company multiselect, date range, keywords)
  output: answer claims, each with numbered citations [1] [2]
          citation chip = source_label + tier label (filing | licensed | IR | trade press (indicative only) | research)
          caveats box (always visible if present), gaps box with suggested sources (code flags
          such as part_gap / uncited_cell as chips, #215), coverage note
  feedback: thumbs up/down + comment -> query_feedback
  while answering (after "Ask" is clicked, before the answer shows):
          a progress bar plus a live step trace saying what the system is doing now, e.g.
            Reading the question: firms MS, EDJ; mode compare; window last 4 quarters
            Planning the search (anthropic, one call): 2 aspects x 2 firms = 4 sub-questions: a1.MS; a2.MS; a1.EDJ; a2.EDJ
            Searching the corpus: 14 passages from 6 documents in 4 sub-questions
            Extracting per firm (deepseek, 2 calls in parallel, 1 re-searched, 1 re-extraction):
              4 cells: 3 fact, 1 not found; behavior by code: answer   (#246; on by default since #247)
              | with MAP=off: Map step off (MAP=off): no extraction calls; legacy single answer call
            Asking the model to write the answer from the evidence matrix (deepseek, one call)
              | or: No model call: the answer is built by code (refuse | incomplete | answer_with_boundary)
              | or: No passages found: no model call
            Checking citations: 9 matched, 1 flagged
            Adding caveats and gaps
          #247: the behavior header gains "Incomplete" (an extraction failed and no firm holds the asked
          figure); the incomplete note shows as a warning above the claims on any behavior (also a
          boundary answer); the reduce step's flags show as chips with plain labels (cited outside the
          evidence matrix, computed by code from cited inputs, no why-it-might-matter line, an asked
          figure shown as adjacent, a different quantity shown as a claim); citation chips link
          corrective re-search passages too (they are part of the answer's passages). With an Ask-page
          date filter alone the answer keeps its aspect-by-firm order (newest first and the why-line
          check apply only to the question's own time window or a recency aspect).
          #247 part 2: three more chips: "written by code: computable or not, with the population
          sources" (a per-firm computation claim code added), "why-line removed (not a recency item)"
          and "why-line replaced: it restated the item". Without a time window only the recency
          items move newest first, inside their own slots; the other aspects keep their order.
          each step reports what the pipeline really did (counts, filters, provider), never
          invented "reasoning" text; the trace stays readable (collapsed) after the answer

Page "Source"
  input: chunk_id
  output: document metadata, the chunk text highlighted, PDF opened at page, download link
          (file from the shared corpus folder via CORPUS_SHARE_PATH)
          undated web page (date_basis = retrieved, ADR-007 T-09): "Page content as of: <date>" in place
          of "Filed:"; the "Latest filing" ticker counts source-dated documents only

Page "Coverage"
  table: entity x doc_type -> count, earliest and latest published_at; empty cells highlighted
         (undated pages, date_basis = retrieved, are counted but kept out of the date span)
```

## Acceptance

- Every citation opens the stored document at the right chunk/page (no external URL composed).
- Tier label visible on every citation; trade press shows "indicative only".
- Caveats and gaps are never collapsed or hidden.
- Coverage page shows thin areas for all five firms and themes.
- Feedback writes a row to `query_feedback` linked to the `query_log` row.
- After "Ask" is clicked, a progress bar and a step trace appear at once and advance with the
  pipeline stages (#248, ADR-021): reading the question, decompose (the planner, #214 / #245),
  search N sub-questions, extract from k firms (the map, #246), re-search (corrective re-search and
  re-extraction, #246), synthesize (the reduce call, or the answer built by code, #247), citation
  check, caveats/gaps, saving the query. Each
  step line comes from the stage's real output; a failed stage is shown as failed, not hidden.
  The trace adds no extra LLM call (it reports the planner call, the map calls and the reduce call;
  calls follow the decomposition, ADR-021 rule 7). The plan
  line lists the sub-question decomposition (#245, ADR-021 rule 6).
- Screenshot of each page attached to the PR.

## Linked questions

All questions (the UI is how every answer is read); especially Q26 (newest first, links
resolve), Q29 (tier labels), Q30 (caveat visible).

## Open questions

- Show the snapshot name in the footer? (proposal: yes, helps scoring)
- Head-to-head as a table view when behavior is `answer` and several entities are named?
