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
          caveats box (always visible if present), gaps box with suggested sources, coverage note
  feedback: thumbs up/down + comment -> query_feedback

Page "Source"
  input: chunk_id
  output: document metadata, the chunk text highlighted, PDF opened at page, download link
          (file from the shared corpus folder via CORPUS_SHARE_PATH)

Page "Coverage"
  table: entity x doc_type -> count, earliest and latest published_at; empty cells highlighted
```

## Acceptance

- Every citation opens the stored document at the right chunk/page (no external URL composed).
- Tier label visible on every citation; trade press shows "indicative only".
- Caveats and gaps are never collapsed or hidden.
- Coverage page shows thin areas for all five firms and themes.
- Feedback writes a row to `query_feedback` linked to the `query_log` row.
- Screenshot of each page attached to the PR.

## Linked questions

All questions (the UI is how every answer is read); especially Q26 (newest first, links
resolve), Q29 (tier labels), Q30 (caveat visible).

## Open questions

- Show the snapshot name in the footer? (proposal: yes, helps scoring)
- Head-to-head as a table view when behavior is `answer` and several entities are named?
