# Spec: Thematic research

**Owner:** C3 (starts W3, not later)
Rules: [CLAUDE.md](../CLAUDE.md). Design: [ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Purpose

Build the tier 5 corpus that theme-scan and segment-evidence questions depend on: industry
research, published investor surveys (Schwab, Fidelity, Vanguard), FINRA Foundation, CFP
Board, Cerulli (if library access), SEC/DOL regulatory direction. Indexed by **theme**, not
by firm. Own the topics taxonomy.

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
- Every chunk of a research document has at least one topic.

## Linked questions

Q16, Q17, Q18, Q19, Q20, Q21.

## Open questions

- Cerulli via WashU library: allowed to store? (ADR-000)
- Keyword topic tagging enough, or needs review by hand?
- Form ADV Part 2 fee schedules for Q18: C1 or C3? (proposal: C1 ingests, C3 tags topic)
