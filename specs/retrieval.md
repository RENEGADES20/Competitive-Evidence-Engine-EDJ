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
    # themes: top-level topics from config/topics.yaml, matched with the chunk tagger's rules
    # entity+theme (#116): one firm + a theme only; several firms + a theme stay entity
    #   until per-firm theme quotas (#117) - research slots pushed Q23's headcount figures out

expand_synonyms(terms) -> terms     # NNA -> "net new assets"; FA -> "financial advisor"

retrieve(query, k=20) -> [Hit{chunk_id, doc_id, entity_id, segment, doc_type,
                               source_tier, published_at, page, rank, text}]
    # SQL: WHERE entity/segment filter AND published_at BETWEEN window AND tsv @@ query
    # MER: entity_id='MER' OR (entity_id='BAC' AND segment IN ('GWIM','Merrill'))
    # quota: k split evenly per entity (entity mode); entity+theme: up to 4 of k for tier 5
    #   research tagged with the theme (entity_id IS NULL, chunk_topics), 2 per document,
    #   the firm keeps the rest; the firm filter still holds for every firm document
    # dedupe: fetch 3k, drop chunks > 90% similar to a higher-ranked one
```

## Retrieval modes (#125, #126, experimental branch `exp/hybrid` only)

`main` has one mode, `fts` (ADR-001, ADR-009). The other two modes live on the branch `exp/hybrid`
until #127 records a decision with the #126 numbers.

`search(q, mode=...)` / `ask(..., mode=...)`; default `RETRIEVAL_MODE` in `.env`, else `fts`.

- `fts` (default): the keyword search above (`src/cee/retrieve/fts.py`).
- `hybrid` (`src/cee/retrieve/hybrid.py`, needs `CEE_VECTORS=on`, table `chunk_embeddings`):
  inside the same entity / segment / window / Ask-filter `WHERE`, keyword top 100 + vector top 100
  per firm -> reciprocal rank fusion (k = 60) per firm -> (firm, document type) groups take turns
  into 50 candidates -> local cross-encoder rerank -> absolute score floor (none inside a time
  window) -> the same `select()` quotas with no relative floor. Entity+theme questions get the
  research part the same way, with the theme filter. The gap path is unchanged: unmapped firms
  return nothing. With vectors off, `hybrid` stops with a clear message; nothing loads a model.
- `hybrid-norerank` (#126, same requirements): the same candidates as `hybrid`, ordered by the
  RRF score; no reranker is loaded. It isolates what the reranker adds.
- Floors (#126): `fts` keeps `FLOOR` x the firm's best `ts_rank`. Both hybrid modes apply
  `hybrid.FLOOR[mode]` x the firm's best RRF score to the 50 candidates before any rerank (RRF is
  a ratio-like score: 0 = no leg found it; the cross-encoder sigmoid is not, so `select()` runs with
  floor 0 there). No floor inside a time window in any mode. `MAX_PER_DOC` and `DUP_JACCARD` are per
  mode for the hybrid modes (`hybrid.py`); the window cap (8), the research cap (2) and every
  `fts.py` constant are unchanged.
- All modes: words listed under `synonym_only` in `config/entities.yaml` (`pay`) are searched only
  through their synonyms (Q29: "pay any net liquidation amount" is not advisor pay).
- Comparison and tuned constants per mode (#126): `evals/hybrid-eval/corpus-2026-10-29/report.md`
  (picked by a rule fixed before the grid ran, `plans/0126-hybrid-eval.md`). `LEG_K`, `RRF_K`,
  `RERANK_N` and `RERANK_FLOOR` were not tuned.

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
- When would hybrid search be justified? Needs a comparison run (ADR-001).
