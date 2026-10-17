# Spec: Thematic research

**Owner:** C3 (starts W3, not later)
Rules: [CLAUDE.md](../CLAUDE.md). Design: [ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Purpose

Build the tier 5 corpus that theme-scan and segment-evidence questions depend on: industry
research, published investor surveys (Schwab, Fidelity, Vanguard), FINRA Foundation, CFP
Board, Cerulli (if library access), SEC/DOL regulatory direction. Indexed by **theme**, not
by firm. Own the topics taxonomy.

### Institutional research publishers

Research reports from large institutions are in scope, including but not limited to:

| Kind | Publishers (examples, not a closed list) |
|---|---|
| Consultancies | McKinsey, BCG, Bain, Deloitte, PwC, EY, Accenture, Oliver Wyman, Capgemini (World Wealth Report) |
| Bank and broker research | Goldman Sachs (Research, Insights), BofA Global Research and BofA Institute, Morgan Stanley Research, J.P. Morgan (Insights, Guide to Retirement), UBS (Global Wealth Report), Wells Fargo Investment Institute, Citi GPS |
| Regulators and self-regulators | FINRA (Industry Snapshot, FINRA Foundation, Investor Insights), SEC (staff reports, OIAD), DOL, CFP Board |
| Industry bodies and research houses | Cerulli, Morningstar, J.D. Power, Kitces Research, CFA Institute, ICI, SIFMA, Broadridge |
| Investor surveys | Schwab, Fidelity, Vanguard, Northwestern Mutual (Planning & Progress) |

Rules for these documents:
- `source_tier=5`, `doc_type="research"`, `entity_id` empty, and the **publisher** recorded.
- A report published by a firm in the competitive set (Goldman, BofA, Morgan Stanley,
  J.P. Morgan, UBS, Wells Fargo) stays tier 5 research: it is evidence on the theme, never a
  source for that firm's own metrics (ground rule 4 still points those to filings).
- Paywalled or library-only reports (Cerulli, BofA Global Research, Goldman Research) record
  the access route in `docs/source_matrix.csv`; ADR-007 allows storing them in full.

## Reference projects

No project indexes by theme; this is our own design. Borrow the document shape from
[Grounded-Rag-Analyst](https://github.com/Monesh76/Grounded-Rag-Analyst) and the manifest
pattern from [bt4103-team8-sec-filing-assistant](https://github.com/niclow236/bt4103-team8-sec-filing-assistant).

## Interface draft (sketch)

```
register_document(entity_id=None, doc_type="research", source_tier=5, url, file_path,
                  published_at, publisher, sample_desc?)   # sample/size/date matter for surveys

topics.yaml (seed in config/entities.yaml `themes:`)
  - id: advice_future      label: Future of advice delivery
  - id: ai_advice          label: AI in advice
  - id: fees_pricing       label: Fees and pricing transparency
  - id: younger_investors  label: Younger investors
  - id: wealth_transfer    label: Generational wealth transfer
  - id: advisor_recruiting label: Advisor recruiting and retention

tag_topics(chunk) -> [topic_id]   # keyword rules first; written to chunk_topics
```

## Acceptance

- `published_at` coverage 100% (survey vintage is a fact: a 2021 and a 2026 survey differ).
- Every stored document has a row in `data/manifest.csv`, `entity_id` empty.
- Each theme in the seed list has at least 3 documents from at least 2 publishers by W5.
- Survey documents record publisher, sample and date.
- Every institutional research document records its publisher; the corpus holds reports
  from at least McKinsey, Goldman Sachs, FINRA and BofA.
- Every chunk of a research document has at least one topic.

## Linked questions

Q16, Q17, Q18, Q19, Q20, Q21.

## Open questions

- Keyword topic tagging enough, or needs review by hand?
- Form ADV Part 2 fee schedules for Q18: C1 or C3? (proposal: C1 ingests, C3 tags topic)
