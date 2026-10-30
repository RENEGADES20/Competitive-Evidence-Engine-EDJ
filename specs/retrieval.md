# Spec: Retrieval

**Owner:** S1
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-001, ADR-004 in [DECISIONS.md](../docs/DECISIONS.md).

## Purpose

Given a question, return the right chunks and only eligible chunks: Postgres full-text
search with a synonym list, hard filters (entity, segment, time window) in SQL, three
retrieval modes chosen by rules, per-entity quotas, near-duplicate removal.

## Reference projects

- [sec_rag_assistant](https://github.com/lazfa04/sec_rag_assistant): filters in the retrieval
  layer, per-company quotas, pitfalls list.
- [agentic-sec-rag](https://github.com/mr-j90/agentic-sec-rag): deterministic entity/period resolution.
- [Grounded-Rag-Analyst](https://github.com/Monesh76/Grounded-Rag-Analyst): Postgres FTS; RRF later.
- [rag-pipeline-sec-filings](https://github.com/avivakahlon/rag-pipeline-sec-filings): over-fetch 3x
  then drop > 90% similar chunks (boilerplate repeated across years).

## Interface draft (sketch)

```
resolve(question) -> Query{
    entities: [entity_id],          # alias match against config/entities.yaml
    themes:   [topic_id],           # keyword match against themes list
    window:   {from: date, to: date} | None,   # "last 90 days", "since the start of the year"
    mode:     "entity" | "theme" | "entity+theme"
}
    # rules: entities and no theme -> entity; theme and no entities -> theme; both -> entity+theme

expand_synonyms(terms) -> terms     # NNA -> "net new assets"; FA -> "financial advisor"

retrieve(query, k=20) -> [Hit{chunk_id, doc_id, entity_id, segment, doc_type,
                               source_tier, published_at, page, rank, text}]
    # SQL: WHERE entity/segment filter AND published_at BETWEEN window AND tsv @@ query
    # MER: entity_id='MER' OR (entity_id='BAC' AND segment IN ('GWIM','Merrill'))
    # quota: k split evenly per entity (entity mode) or per part (entity+theme)
    # dedupe: fetch 3k, drop chunks > 90% similar to a higher-ranked one
```

## Retrieval modes (#125, ADR-008)

`search(q, mode=...)` / `ask(..., mode=...)`; default `RETRIEVAL_MODE` in `.env`, else `fts`.

- `fts` (default): the keyword search above (`src/cee/retrieve/fts.py`).
- `hybrid` (`src/cee/retrieve/hybrid.py`): inside the same entity / segment / window `WHERE`,
  keyword top 100 + vector top 100 per named firm -> reciprocal rank fusion (k = 60) -> firms take
  turns into 50 candidates -> local cross-encoder rerank -> score floor (none inside a time
  window) -> the same `select()` quotas. The gap path is unchanged: unmapped firms return nothing.
- Both modes: words listed under `synonym_only` in `config/entities.yaml` (`pay`) are searched only
  through their synonyms (Q29: "pay any net liquidation amount" is not advisor pay).
- Constants (`LEG_K`, `RRF_K`, `RERANK_N`, `RERANK_FLOOR`) are tuned per mode in #126.

## Acceptance

- Time windows filtered in SQL: Q26 returns nothing older than 90 days.
- Merrill queries (Q4, Q27, Q30) return zero BAC chunks without a GWIM/Merrill segment.
- Head-to-head (Q7): every named firm gets its quota; no firm fills the list.
- Duplicate rate after dedupe: no two hits > 90% similar.
- Hit rate vs `expected_sources` in `evals/questions.yaml` reported per question.
- **Refusal accuracy tracked alongside recall**: for gap questions (Q24, Q25, Q28-30) retrieval
  must not surface misleading substitutes unlabeled. Any tuning PR reports both numbers.

## Linked questions

Q4, Q7, Q21, Q26, Q27, Q30 (primary); every question uses retrieval.

## Open questions

- ~~"Since the start of the year" = calendar year of today's date?~~ Settled in #49: yes,
  1 January of the current calendar year to today. Windows filter `published_at` (both
  ends inclusive) and leave out `date_basis = retrieved` documents (ADR-007 T-09).
- Similarity measure for dedupe: trigram (pg_trgm) is simplest.
- ~~When would hybrid search be justified? Needs a comparison run (ADR-001).~~ Comparison run
  in #125: hybrid is a per-request mode, `fts` stays the default (ADR-008).
