# Spec: Filings and structured data

**Owner:** C1 (also domain owner)
Rules: [CLAUDE.md](../CLAUDE.md). Design: [ARCHITECTURE.md](../docs/ARCHITECTURE.md).

## Purpose

Get tier 2 sources for the core five into the corpus, correctly dated, chunked and
segment-tagged: SEC filings (10-K, 10-Q, 8-K, DEF 14A), quarterly financial supplements,
Form ADV / IAPD data. Own the entity config, the source registry, and the metric definitions
(advisor headcount, net new assets) that benchmark questions depend on.

## Reference projects

- [edgartools](https://github.com/dgunning/edgartools): fetch filings and items by CIK; XBRL facts.
- [edgar-crawler](https://github.com/lefterisloukas/edgar-crawler): 10-K split into Items as JSON.
- [bt4103-team8-sec-filing-assistant](https://github.com/niclow236/bt4103-team8-sec-filing-assistant):
  resumable pipeline with a manifest, ingestion validation checks, no cross-section chunks.
- [agentic-sec-rag](https://github.com/mr-j90/agentic-sec-rag): source registry per entity for coverage.

## Interface draft (sketch, not implementation)

```
fetch_filings(entity_id, forms=["10-K","10-Q","8-K","DEF 14A"], since="2019-01-01")
    -> writes raw/<entity>/<doc_id>.<ext>, appends rows to data/manifest.csv

parse_filing(doc_id) -> Document{doc_id, entity_id, doc_type, source_tier=2,
                                 published_at, period_end, url, storage_path, sha256,
                                 sections: [Section{name, page?, text}]}

tag_segment(entity_id, section) -> segment | None
    # uses segment_aliases from config/entities.yaml
    # e.g. BAC 10-K "Global Wealth & Investment Management" -> "GWIM"

chunk(document) -> [Chunk{chunk_id="<doc_id>#<n>", section, segment, page, text}]
    # text starts with "[entity|segment|doc_type|period]"; never crosses a section

metric_definitions.yaml   # later: entity, metric, definition quote, doc_id, valid_from
```

doc_id convention: `<ENTITY>-<FORM>-<PERIOD>` e.g. `BAC-10K-2025`, `RJF-10Q-2026Q2`.

## Acceptance

- `published_at` coverage 100%: no document without a publication date.
- Every stored document has a row in `data/manifest.csv` (with sha256 and storage_path).
- BAC chunks in the GWIM section carry `segment = GWIM`; spot-check 20 chunks, 0 wrong.
- Five advisor-headcount definitions quoted with doc_id (Q11).
- Re-running ingestion skips documents already in the manifest.
- Adding a sixth firm needs only a new entry in `config/entities.yaml` and source_registry rows.

## Linked questions

Q11, Q22, Q23, Q24, Q25, Q28, Q29, Q30 (primary); segment tagging also serves Q4, Q27.

## Open questions

- Verify CIKs for MS, SCHW, BAC, RJF (marked TODO-verify).
- How far back is deep enough? Proposal: 2019 onward for 10-K/10-Q.
- Which quarterly supplements are HTML vs PDF per firm?
- Is Form ADV bulk data useful for the core five or mainly for Fidelity/Vanguard later?
