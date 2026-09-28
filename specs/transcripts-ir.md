# Spec: Transcripts and investor relations

**Owner:** C2
Rules: [CLAUDE.md](../CLAUDE.md). Design: [ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Purpose

Get what management said in its own words into the corpus: earnings-call transcripts,
investor-day decks (PDF), press releases, monthly metrics releases (tier 3), and 90 days of
trade press (tier 4). Own date quality: recency questions (Q26, Q27) fail if dates are wrong.

## Reference projects

- [earnings-intelligence](https://github.com/arnenyeck06/earnings-intelligence): multi-firm,
  multi-year transcripts; speaker-aware records.
- [Financial-Filings-RAG](https://github.com/AshishBhalala11/Financial-Filings-RAG): PDF chunks
  with page numbers.
- [bt4103-team8-sec-filing-assistant](https://github.com/niclow236/bt4103-team8-sec-filing-assistant):
  raw -> interim -> processed layers with a manifest.

## Interface draft (sketch)

```
register_document(entity_id, doc_type, url, file_path, published_at, source_tier)
    -> doc_id, copies file to raw/<entity>/<doc_id>.<ext>, appends manifest row

parse_transcript(doc_id) -> sections: [Section{name="prepared remarks"|"Q&A", speaker?, text}]
parse_pdf(doc_id)        -> sections: [Section{name=slide/section title, page, text}]
    # parser from the tech lead (docling, pymupdf fallback)

trade_press_item: {doc_id, entity_id, outlet, headline, published_at, url,
                   storage: "full" | "excerpt"}   # depends on ADR-000 terms
```

doc_id examples: `MS-TR-2025Q2`, `RJF-DECK-2025-investor-day`, `SCHW-PR-2026-03-14-01`.

## Acceptance

- `published_at` coverage 100%, taken from the source (call date, release date), never the download date.
- Every stored document has a row in `data/manifest.csv`.
- PDF chunks keep page numbers; spot-check 10 citations open on the right page.
- For each of the five: every available earnings transcript, latest investor-day deck,
  quarterly supplements, 90 days of trade coverage (or a written reason why not).
- Trade-press URLs checked to resolve; re-check monthly (feed rot).
- Merrill press releases are stored as entity MER, not BAC.

## Linked questions

Q1, Q2, Q3, Q4, Q5, Q6, Q13, Q26, Q27.

## Open questions

- Transcript source without tier 1 license: company IR sites, SEC 8-K exhibits? (ADR-000)
- Which trade-press sites allow full-text storage? (ADR-000)
- Speaker labels: worth keeping for "management said" vs analyst question?
