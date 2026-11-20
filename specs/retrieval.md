# Spec: Retrieval

**Owner:** S1
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-001, ADR-004, ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020, ADR-021 in [DECISIONS.md](../docs/DECISIONS.md).

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

plan_question(query) -> Plan{aspects: [Aspect{id, text, keyword_query, metric, kind, firms}],
                              subquestions: [SubQuestion{id, entity, aspect, role}], source, calls}
    # sub-question decomposition (#245, ADR-021 rule 6; ADR-020 as amended; src/cee/retrieve/planner.py):
    #   with a real provider and PLANNER=on, one call (the answer model, tool submit_plan, prompt
    #   plan-v3) lists every aspect the question asks, literally: no merge, no cap (PLANNER_MAX_PARTS
    #   removed), implicit asks and "the closest disclosed figure" as their own aspects; kind fact |
    #   series | recency | comparison; metric = a key of config/metric_definitions.yaml or "".
    # plan-v3.1 (#246): each aspect also carries a required boolean `proxy`: true when it asks for a
    #   stand-in for the asked quantity (the closest disclosed figure, a numerator or denominator to
    #   compute it, the nearest measure). Code (the map step) never lets a proxy aspect make the
    #   behavior `answer` (ADR-021 rule 1a); missing / not a boolean -> false with a note.
    # strict schema on every path: {aspects: [{id, text, keyword_query, firms, metric, kind, proxy}]}, all
    #   required, additionalProperties false, metric / kind enums ("" = no metric, no nullable type);
    #   anthropic minItems 1, openai / deepseek no array limits. Output cap 8000 (anthropic, openai;
    #   deepseek 8000 thinking off, 64000 on, #242 / #245).
    # firms decided by code (firm_scope): the resolved firms (role named, after the Ask page firm
    #   filter, Merrill once; firms we hold no documents for are not searched); for a home-firm market
    #   question (ADR-018's home-firm theme rule: q.theme_peers set; Q19) the competitors on the theme
    #   as real entities (role competitor); theme mode one entity None (role all). The planner
    #   message labels each firm: named / through "<peer phrase>" / competitor on the theme.
    # per-aspect firms (TL decision D3): an aspect may carry a subset of the scoped firms when the
    #   question itself asks it of some of them (Q12: Schwab's acquisition aspects SCHW only; Q15:
    #   "how an advisor-led model earns" MS, EDJ, MER, RJF only); code maps names / aliases, drops
    #   firms outside the scope (note), nothing left -> all; on a home-firm market question a list
    #   equal to the named firms counts as empty, so the competitors stay (Q19).
    # validation: ids a1..aM by code; empty text -> the question, empty words -> the text, words cut
    #   at 400 chars, unknown metric -> none, unknown kind -> fact (all with notes); neighbour guard
    #   (#224): code removes from an aspect's words every config `neighbour_phrases` entry the
    #   question does not name ("payout ratio" = the dividend payout ratio). Not usable (no aspects,
    #   wrong shape, no tool call, cut, refusal) or a failed call -> the rule plan, logged, the call
    #   counted, never re-rolled. Window, themes and the Ask page filters are not in the schema.
    # SubQuestion(entity, aspect): each aspect over its firm set, firm-major order, id
    #   "<aspect>.<firm>" ("a1.all" in theme mode). No cap: 8 firms x 100 aspects = 800.
    # rule plan (mock provider, PLANNER=off, unsearchable, fallback): one aspect a1 = the whole
    #   question (its own words), kind recency with a window else fact, metric = the registered key
    #   the question names; x every scoped firm (five-firm questions: 5 sub-questions; Q19: EDJ + 4
    #   competitors). Passage mode (TOKEN_BUDGET None or an explicit k): one whole-question part, no
    #   planner call.
search_subquestions(query, plan, search_fn=fts.search, research_fn=fts.research_pass) -> [Hit{..., part_id}]
    # every sub-question searches a copy of the resolved query with its firm and words (Query.terms)
    #   and the whole question's doc-type scope (Query.scope): entity / segment (Merrill = MER or BAC
    #   GWIM/Merrill), window, date range, keywords and doc-type scope are SQL filters in every one
    # research (<= THEME_K = 4 passages) once per question (research_fn), outside the sub-question
    #   budgets; then each sub-question with its own token budget SUBQUESTION_TOKENS (setting, value
    #   from the #245 grid, ADR-019 amendment): the question's total grows with the decomposition and
    #   is reported per question; chunks kept earlier are excluded from later pools and the
    #   answer-turn map (a chunk appears once, under its first sub-question). part_id = the
    #   sub-question id or "research". ADR-019's pool rule (POOL_PER_GROUP = 30) is unchanged.
    # competitors (Q19, ADR-018 safeguards kept, its 2 peer slots replaced): Query.on_theme_only
    #   (the firm pass AND the theme's keywords, no answer turn attached), Merrill only through BAC
    #   GWIM/Merrill, and the floor across the competitors of each aspect (FLOOR x their 2nd-best
    #   rank, after select; plan.competitor_floor; dropped ids logged, an emptied sub-question
    #   marked floor_emptied). peer_pass runs only without a plan (search(q)).
    # search_fn seam: called as search_fn(query, trace=, tokens=, exclude=, research=False,
    #   peers=False, text=<sub-question text>); fts.search ignores `text`; exp/hybrid passes
    #   hybrid.search (embeds `text`) and must honour Query.on_theme_only.
corrective_search(query, plan, sq_id, extra_words, exclude, search_fn, tokens) -> [Hit]
    # re-search hook for #246 (CRAG): one sub-question again with its words (the question's own
    #   words for a rule-plan aspect) + extra words, neighbour-guarded, never a chunk in `exclude`,
    #   every SQL filter kept (competitors: on the theme and the aspect's floor); the window is never
    #   widened (adjacent periods enter as words). 0 model calls; "once per not_found" is #246's rule.
    # #246 uses it once per not_found sub-question of the map step (extract.run_map): exclude = every
    #   chunk already retrieved for the question (and earlier re-search hits); extra words =
    #   extract.widen_words (the firm's metric definition entry: quote, includes, the full-text search
    #   phrases in looked_in; adjacent quarters as words). Its hits feed only the re-extraction (the
    #   evidence matrix), never the retrieved set, recall or query_log.chunk_ids.
    #   plan.pools (each sub-question's PoolTrace.ids(), the value part_pools gets) is the map's
    #   retrieved-set check; answer turns are pooled only after the exclude filter.

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
    # theme peers (#205, ADR-018; search() without a plan only: with a plan the competitors are
    #   sub-questions, #245, see search_subquestions above): one more SQL pass, entity_filter(theme_peers) AND the on-theme
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

### Series coverage passes (#247 part 2)
After every main sub-question search (unchanged), `planner.search_subquestions` runs two passes per
sub-question, every chunk kept so far excluded, on top of the budget:
- **Per-period sub-search**: a `series` aspect with asked periods ("last / past N quarters / years",
  `matrix.asked_periods`, no window): one FTS search per asked period with `Query.period_range` (a hard
  SQL filter on `documents.period_end`) and `exclude_ids` (kept chunks leave the SQL pool before the
  cut), `PERIOD_K = 3` passages. Hits: `origin = "period"`.
- **Pins** (`fts.fetch_pinned`): the firm's `populations` sources for the ratio inputs the aspect can
  hold, then its registered definition `chunk_id` and `see_also` for a registered metric
  (and, for a `series` aspect only, the entry's `series_pins`: dated counts in documents without
  `period_end`, which the per-period pass cannot reach; #247 part 4, Q23 `RJF-DECK-2025-investor-day#43`), at most
  `PIN_MAX = 8` (the cut is logged as `pins_cut`), fetched by ID under every hard filter of the
  sub-question (entity / segment, window, date range, keywords) and the doc-type scope except the `adv`
  exclusion (ADR-015 amendment). A pinned chunk another sub-question already kept still joins this
  sub-question's pool. Hits: `origin = "pinned"`.
Both join `plan.pools` (the map's retrieved-set check) and `plan.searched` (`period_hits`, `pinned`);
the eval records them as `added_chunk_ids`.

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
