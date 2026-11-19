# Spec: Retrieval

**Owner:** S1
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-001, ADR-004, ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020 in [DECISIONS.md](../docs/DECISIONS.md).

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
    # peer sets (config `peer_sets`): "the five" -> MS, SCHW, EDJ, MER, RJF; "an advisor-led model",
    #   "advisor-led models / firms" -> MS, EDJ, MER, RJF (#205, ADR-018; Q15), unioned with the
    #   firms named; indefinite and plural phrases only ("Edward Jones's advisor-led model" = EDJ)
    # theme_peers (#205, ADR-018; config `home_firm`): an entity+theme question whose only named
    #   firm (covered or not) is the home firm (EDJ) also searches the other members of
    #   `home_firm.theme_peers` (MS, SCHW, MER, RJF) - their chunks on the theme only (Q19). A firm
    #   filter on the Ask page clears it
    # themes: top-level topics from config/topics.yaml, plus S1's firm_themes (config/entities.yaml;
    #   themes firms talk about that tier 5 research is not indexed by, e.g. client_acquisition, Q12),
    #   matched with the chunk tagger's rules
    # metric_phrases (config/entities.yaml, #117) name a figure, never a theme: "advisor headcount"
    #   (Q11, Q23) stays entity - theme slots pushed Q23's supplement and press release out

expand_synonyms(terms) -> terms     # NNA -> "net new assets"; FA -> "financial advisor"
    # synonym_only (config/entities.yaml, #159): "pay" is searched only through its synonyms;
    #   the bare word leaves the FTS words (Q29: "pay any net liquidation amount" is not advisor pay)
    # key matching (#203, ADR-017): a lower-case key fires with a hyphen or spaces between its words
    #   and an inflected last word ("stock-plan" -> `stock plan`, Q13; "recruiting" -> `recruit`);
    #   all-caps keys exact case; config `synonym_exact` keeps the plain match (`compensation
    #   structure`: gap question Q25 stays clear of "payout grid"); a multi-word key in the question
    #   is searched as a phrase too ("net new assets", Q22)

plan_question(query) -> Plan{parts: [Part{id, text, firms, keyword_query}], source, calls}
    # question planner (#214, ADR-020; src/cee/retrieve/planner.py): with a real provider and
    #   PLANNER=on, one call (the answer model, tool submit_plan) splits the question into at most
    #   PLANNER_MAX_PARTS = 4 parts with their firms and rewritten search words. Code validates it:
    #   firms must be resolve()'s (unknown / unasked / no-document firms dropped; a dropped resolved
    #   firm comes back as a part, or joins the part with the fewest firms at the cap); more parts than
    #   the cap are cut; empty words -> the part's text; ids p1..pn by code. Window, themes and the
    #   Ask page filters are not in the planner's schema. Not usable (no tool call, wrong shape, cut
    #   at max_tokens) or a failed call -> the rule plan, logged, the call counted, never re-rolled.
    # prompt plan-v2 (#224): list the asks first (incl. what the question asks without naming it),
    #   give every ask a part or its own words in a part, keep search words on the asked concept.
    # neighbour guard (#224): code removes from a part's words every config `neighbour_phrases`
    #   entry (a different figure sharing a word: "payout ratio" = the dividend payout ratio) the
    #   question does not name; matched like a synonym key; correction "part N: dropped neighbour
    #   phrase X"; words left empty -> the question's words. The rule plan is never touched.
    # rule plan (mock provider, PLANNER=off, fallback): one part per named covered firm for 2-4
    #   firms, else one whole-question part (five firms exceed the cap). Passage mode (TOKEN_BUDGET
    #   None or an explicit k): one whole-question part, no planner call.
search_parts(query, plan) -> [Hit{..., part_id}]
    # every part searches a copy of the resolved query with its firms and words (Query.terms) and
    #   the whole question's doc-type scope (Query.scope): every hard SQL filter in every part
    # research (<= THEME_K = 4 passages) once per question first (research_pass), then the parts in
    #   order with share_i = max(0, T - R - used) / (parts left) of T = budget_tokens(query) (R =
    #   research tokens; unused share flows to later parts), chunks kept earlier excluded from the
    #   pools and the answer-turn map, then the theme peers once (peer_pass). Budgeted total <=
    #   max(T, R) + one chunk. A one-part plan returns exactly search(query). part_id: p1..pn,
    #   "research", "peers"
    # unused share is not handed back to earlier parts (#224, ADR-020 "not now"): a 0-call replay
    #   of #214's Q25 gave p1 its share plus p2/p3's surplus (15.0k -> 33.6k) and p1 still stopped
    #   at select()'s floor (68 passages, 21.9k) with MS-10K-2025#153 in the pool; in the mock it
    #   would change Q7, Q9, Q12 with no key row to gain; surplus spent in a weak part buys low-rank
    #   matches (Q25 p4); a second pass would restate ADR-019's bound. Revisit when a replay with
    #   the surplus brings a lost key row into the final set.

retrieve(query, budget_tokens(query)) -> [Hit{chunk_id, doc_id, entity_id, segment, doc_type,
                               source_tier, published_at, page, rank, text}]
    # SQL: WHERE entity/segment filter AND published_at BETWEEN window AND tsv @@ query
    # MER: entity_id='MER' OR (entity_id='BAC' AND segment IN ('GWIM','Merrill'))
    # budget (#213, ADR-019; replaces ADR-013's passage count): estimated tokens of the retrieved
    #   set (passage characters / 4, summed in select() order), TOKEN_BUDGET = 40000 for a question
    #   naming 0 or 1 firm; n >= 2 firms -> max(40000, 40000 x 6 x n // 20) (2-3 firms: 40k, the
    #   five: 60k). n counts covered firms after the Ask page firm filter; Merrill is one firm;
    #   firms we hold no documents for take no share. The list ends at most one chunk past the
    #   budget (an answer turn is attached only while it is not full; the trade swap never makes it
    #   longer) and stops short when the eligible pool runs out. Research (up to 4 passages) is
    #   selected first and its tokens come off the firm part; theme peers come on top. An explicit
    #   k (tests, `eval_run.py --k`) is the old passage rule: k = 20 for 0-1 firm, max(20, 6 x n).
    #   The pool over-fetch (POOL_PER_GROUP = 30 per firm and document type, #213; was 15) and
    #   every quota rule below fill it. Both values were picked from a 12-point grid (ADR-019).
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
    #   brochure ("Form ADV", "ADV", "brochure", "brochures") or "compensation" (how advisors are
    #   paid, Q25), and never in a question with a time window (a brochure revision is not news,
    #   Q26 / Q27); a benchmark question (2+ firms and a metric: "advisor headcount", "net new
    #   assets", "assets per advisor", "attrition rate"; Q11, Q22-Q24, Q28) does not search
    #   tier 4 trade press. A hard SQL filter on every pass; brochures and trade press otherwise
    #   crowded MS:supplement, SCHW:10-K and RJF:press out of Q23 / Q24 (#178, #186)
    # slot order inside a firm (#198, #199, ADR-016), theme and rank turns alike, never for the
    #   research part:
    #   - trade last (not inside a time window: Q26 reads its news as ranked): tier 4 trade press
    #     takes a firm's turn only when no other document type of the firm can give a chunk (Q2,
    #     Q5, Q30 lost filings and calls to trade articles); when the list is then full, the
    #     firm's best trade chunk replaces its last second chunk of a document (or of a document
    #     type), never its only chunk of a type (Q7, Q29 keep a *:trade source; Q30's release stays)
    #   - new document first (window questions too, Q27): a document type gives a document not
    #     yet in the list before a second chunk of a used one (speaker-turn chunks of one call
    #     pushed the firm's other calls out of Q6, Q11, Q13, Q27); among unused documents ranked
    #     within 0.9 of the type's best, the newest wins (Q11: SCHW-TR-2026Q1 vs 2025Q4)
    # answer turn with its question turn (#203, ADR-017; PAIR_TURNS = "attach"): a kept transcript
    #   question turn (operator hand-off, "Q - " label, or "?" at the end under a non-executive
    #   label) brings the next chunk of the call right after it; fetched with every hard filter
    #   (entity/segment, window, date range, keywords, doc-type scope), no word match; MAX_PER_DOC,
    #   dedupe and k still apply (Q6: the CEO's answer RJF-TR-2026Q1#46 after the analyst's #45)
    # theme peers (#205, ADR-018): one more SQL pass, entity_filter(theme_peers) AND the on-theme
    #   keywords AND every other hard filter (window, date range, keywords, doc-type scope), with the
    #   word match; the pool is cut at FLOOR x its 2nd-best rank across all peers (its only chunk
    #   with one; also inside a window) so a firm whose only text on the theme is an advisor ranking
    #   ("Top 40 Advisors Under 40") takes no slot; then up to PEER_THEME_PER_FIRM = 2 per peer firm
    #   (Merrill counted once). The home firm and research parts are unchanged; the peers' slots
    #   come on top, outside the token budget (passage rule: budget() = 20 + 2 x 4 = 28 for Q19;
    #   an explicit k gets them on top too).
    #   Coverage note: "on the theme also ..." and the peers with nothing on the theme
    # dedupe: fetch 3k, drop chunks > 90% similar to a higher-ranked one
```

## Retrieval modes (#125, #126, #211, experimental branch `exp/hybrid` only)

`main` has one mode, `fts` (ADR-010, ADR-011). The other two modes live on the branch `exp/hybrid`.

`cee.retrieve.modes.search(q, k=None, mode=..., trace=None)` / `ask(..., mode=...)`; default
`RETRIEVAL_MODE` in `.env`, else `fts`. `k=None` is the app default of each mode: `fts` applies
`fts.search`'s own rule (the token budget `budget_tokens(q)`, #213, ADR-019); the hybrid modes keep
the passage budget `budget(q) - peer_slots(q)` (their candidate counts scale with k and were not
tuned for a token budget; synced 2026-11-19 after #220). An explicit k is passages in every mode.
`fts.py` itself is byte-equal to `main` (#211).

Question planner (#214, ADR-020) on this branch: `fts` plans and searches exactly as `main`
(`modes.plan_for` -> `planner.plan_question`; `modes.search(q, mode="fts", plan=plan)` ->
`planner.search_parts`: research once, the parts with token shares, the peers once). The hybrid
modes do not split the question: `plan_for` gives the one-part whole-question plan with no planner
call, and `modes.search` runs one `hybrid.search` on the whole question (every hit `part_id` "p1"),
as before #214. `eval_run.py` plans only in `fts` token mode, so a hybrid eval run makes no planner
call. Per-part hybrid retrieval would need hybrid's candidate counts tuned for token shares; not done
(synced 2026-11-19 after #223).

- `fts` (default): the keyword search above (`src/cee/retrieve/fts.py`).
- `hybrid-norerank` (`src/cee/retrieve/hybrid.py`, needs `CEE_VECTORS=on`, table
  `chunk_embeddings`): inside every hard filter of `fts` (entity / segment, window, Ask filters,
  document-type scope of ADR-015), each part of the question (named firms; for entity+theme also
  the firms' chunks on the theme, tier 5 research on the theme and the home firm's theme peers)
  runs keyword top 100 + vector top 100 per quota firm (Merrill's MER and BAC GWIM chunks are one
  firm, ADR-013) -> reciprocal rank fusion (k = 60) -> (quota firm, document type) groups take turns
  into 50 x k / 20 candidates. `Hit.rank` is the RRF score and `fts.select()` does the rest as in
  `fts`: relative floor `hybrid.FLOOR[mode]` from the firm's 2nd-best score (ADR-014; research
  base 1; none in a window), theme slot below the floor, Merrill counted once, trade press last and
  a new document first (ADR-016), answer turns with their question turns (ADR-017), peers 2 per firm
  after `fts.peer_floor()` (ADR-018). An on-theme-only chunk scores 0.99 x its firm's lowest
  firm-part score x its on-theme score / the best on-theme-only score, so it ranks below every
  firm-part chunk and never moves the floor base. The gap path is unchanged. With vectors off,
  both hybrid modes stop with a clear message; nothing loads a model.
- `hybrid` (same requirements, reference only): the same candidates; the RRF floor is applied
  before a local cross-encoder (the theme part exempt), whose sigmoid score orders the pool;
  `select()` runs with floor 0 there (a sigmoid is not a ratio).
- `MAX_PER_DOC` is per mode for the hybrid modes (`hybrid.py`); near-duplicates use
  `fts.DUP_JACCARD` in every mode; the window cap (8), the research cap (2) and every `fts.py`
  constant are unchanged.
- All modes: words listed under `synonym_only` in `config/entities.yaml` (`pay`) are searched only
  through their synonyms (Q29).
- Comparisons: #126 on `corpus-2026-10-29` (`evals/hybrid-eval/corpus-2026-10-29/report.md`, tuned
  constants per mode); #211 on `corpus-2026-11-17` (`evals/hybrid-eval/corpus-2026-11-17/report.md`,
  recall@pool / recall@final per mode and the #212 decision); #212 real answers with `hybrid-norerank`
  on `corpus-2026-11-17` (`evals/hybrid-eval/corpus-2026-11-17/real/report.md`, 21/30 at acting
  quality, as Gate 4's `fts`; Q17 lost, Q28 gained). `LEG_K`, `RRF_K`, `RERANK_N` and
  `RERANK_FLOOR` were not tuned.

## Acceptance

- Time windows filtered in SQL: Q26 returns nothing older than 90 days.
- Merrill queries (Q4, Q27, Q30) return zero BAC chunks without a GWIM/Merrill segment.
- Head-to-head (Q7): every named firm gets its quota; no firm fills the list.
- Firms on a theme (Q12, Q21): every named firm has a chunk on the theme, or code reports it as a gap.
- Firm scope (#205): "an advisor-led model" (Q15) searches MS, EDJ, Merrill and RJF next to the named
  firm; a home-firm theme question (Q19) gets competitor chunks on the theme only, never an
  off-theme chunk, and Merrill only through BAC GWIM/Merrill.
- Duplicate rate after dedupe: no two hits > 90% similar.
- Hit rate vs `expected_sources` in `evals/questions.yaml` reported per question.
- Recall by stage (#210), per question and in the summary of `scripts/eval_run.py`, over the
  expected passages (rows) in `evals/expected_chunks.yaml` (a row counts when any of its ids
  is there; `DOC` alone is any chunk of the document; window rows as for passage recall):
  - **recall@pool** = rows with a chunk in any candidate pool `search()` fetches before
    `select()` (firm pool, research, firms on the theme, theme peers before their floor,
    answer turns; recorded by `PoolTrace`) / rows. A row missing here is a recall problem
    (query, pool size, vectors).
  - **recall@final** = rows with a chunk in the retrieved set / rows (= passage recall). A row
    in the pool but not in the final set was lost in `select()` (quotas, floor, budget).
  Each run also reports passages and estimated tokens (characters / 4) per question and in total,
  and (#213) the token budget, the budgeted tokens apart from the theme peers', `fill` (budgeted
  tokens / budget), the search time per question and the pool / budget settings in the run meta.
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
