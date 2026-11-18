# Spec: Retrieval

**Owner:** S1
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-001, ADR-004, ADR-010, ADR-011, ADR-013, ADR-014, ADR-015 in [DECISIONS.md](../docs/DECISIONS.md).

## Purpose

Given a question, return the right chunks and only eligible chunks: Postgres full-text
search with a synonym list, hard filters (entity, segment, time window) in SQL, three
retrieval modes chosen by rules, per-entity quotas, near-duplicate removal.

## Reference projects

- [sec_rag_assistant](https://github.com/lazfa04/sec_rag_assistant): filters in the retrieval
  layer, per-company quotas, pitfalls list.
- [agentic-sec-rag](https://github.com/mr-j90/agentic-sec-rag): deterministic entity/period resolution.
- [Grounded-Rag-Analyst](https://github.com/Monesh76/Grounded-Rag-Analyst): Postgres FTS; RRF evaluated on `exp/hybrid`,
  not adopted (ADR-010).
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
    # themes: top-level topics from config/topics.yaml, plus S1's firm_themes (config/entities.yaml;
    #   themes firms talk about that tier 5 research is not indexed by, e.g. client_acquisition, Q12),
    #   matched with the chunk tagger's rules
    # metric_phrases (config/entities.yaml, #117) name a figure, never a theme: "advisor headcount"
    #   (Q11, Q23) stays entity - theme slots pushed Q23's supplement and press release out

expand_synonyms(terms) -> terms     # NNA -> "net new assets"; FA -> "financial advisor"
    # synonym_only (config/entities.yaml, #159): "pay" is searched only through its synonyms;
    #   the bare word leaves the FTS words (Q29: "pay any net liquidation amount" is not advisor pay)

retrieve(query, k=budget(query)) -> [Hit{chunk_id, doc_id, entity_id, segment, doc_type,
                               source_tier, published_at, page, rank, text}]
    # SQL: WHERE entity/segment filter AND published_at BETWEEN window AND tsv @@ query
    # MER: entity_id='MER' OR (entity_id='BAC' AND segment IN ('GWIM','Merrill'))
    # budget (#181, ADR-013): k = 20 for a question naming 0 or 1 firm; n >= 2 firms ->
    #   k = max(20, 6 x n) (2-3 firms: 20, the five: 30). n counts covered firms after the Ask
    #   page firm filter; Merrill is one firm; firms we hold no documents for take no slots.
    #   The pool over-fetch (15 per firm and document type) and every quota rule below fill it.
    # Merrill counted once (#181): with MER named and BAC not, BAC GWIM/Merrill chunks share MER's
    #   quota turns and relevance floor (one firm, one share); Hit.entity_id stays BAC
    # quota: k split evenly per entity (entity mode); entity+theme: up to 4 of k for tier 5
    #   research tagged with the theme (entity_id IS NULL, chunk_topics), 2 per document,
    #   the firms keep the rest; the firm filter still holds for every firm document
    # entity+theme per firm (#117): a firm chunk is on the theme when its text has one of the
    #   theme's keywords (pooled in its own SQL pass); each firm's first turn goes to its best
    #   chunk on the theme (THEME_FIRST = 1), then rank order. A named firm with no chunk on the
    #   theme is a theme gap: theme_gaps() -> coverage note "No passages on the theme (...) for X."
    #   The theme slot is not subject to the rank floor (#190, ADR-014): a firm's best chunk on the
    #   theme takes it even when it ranks below the floor (Q21: MS's only on-theme chunk, a deck
    #   slide at 2.32 vs MS's best 11.66); rank-order turns keep the floor.
    # floor (#166, ADR-014): a chunk below 0.3 x its firm's 2nd-best rank gets no slot (one
    #   outlier does not lift the floor for the whole firm: Q28 with speaker-turn transcripts);
    #   window questions have no floor; the research part keeps the best chunk as its base
    # doc-type scope (#179, ADR-015; config `doc_type_scope`): Form ADV brochures (`adv`) are
    #   searched only when the question is on fees / pricing (theme fees_pricing) or names the
    #   brochure ("Form ADV", "ADV", "brochure"), and never in a question with a time window (a
    #   brochure revision is not news, Q26 / Q27); a benchmark question (2+ firms and a metric:
    #   "advisor headcount", "net new assets", "assets per advisor", Q22-Q24) does not search
    #   tier 4 trade press. A hard SQL filter on every pass; brochures and trade press otherwise
    #   crowded MS:supplement, SCHW:10-K and RJF:press out of Q23 / Q24 (#178, #186)
    # dedupe: fetch 3k, drop chunks > 90% similar to a higher-ranked one
```

## Acceptance

- Time windows filtered in SQL: Q26 returns nothing older than 90 days.
- Merrill queries (Q4, Q27, Q30) return zero BAC chunks without a GWIM/Merrill segment.
- Head-to-head (Q7): every named firm gets its quota; no firm fills the list.
- Firms on a theme (Q12, Q21): every named firm has a chunk on the theme, or code reports it as a gap.
- Duplicate rate after dedupe: no two hits > 90% similar.
- Hit rate vs `expected_sources` in `evals/questions.yaml` reported per question.
- **Refusal accuracy tracked alongside recall**: for gap questions (Q24, Q25, Q28-30) retrieval
  must not surface misleading substitutes unlabeled. Any tuning PR reports both numbers.

## Linked questions

Q4, Q7, Q12, Q21, Q26, Q27, Q30 (primary); every question uses retrieval.

## Open questions

- ~~"Since the start of the year" = calendar year of today's date?~~ Settled in #49: yes,
  1 January of the current calendar year to today. Windows filter `published_at` (both
  ends inclusive) and leave out `date_basis = retrieved` documents (ADR-007 T-09).
- Similarity measure for dedupe: trigram (pg_trgm) is simplest.
- ~~When would hybrid search be justified?~~ Compared in #126 on `exp/hybrid`: not on this
  question bank; `main` stays FTS-only (ADR-010; model-based retrieval stays on a branch, ADR-011). Report:
  [evals/hybrid-eval/corpus-2026-10-29/report.md at 3449cc5](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/3449cc52171406a45dfd4d13e39e227adbecd1e3/evals/hybrid-eval/corpus-2026-10-29/report.md).
