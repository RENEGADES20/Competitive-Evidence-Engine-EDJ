# 0247 - Reduce part 2: input populations, series coverage, basis breaks, less noise

Issue: #247 (part 2, "Part of #247")    Role: TL    Spec: specs/answer-citations.md, specs/retrieval.md
(also specs/ui.md for the new chips; specs/filings.md for the new `populations` list in
`config/metric_definitions.yaml`)

Scope: the TL comment on #247 (issuecomment-7037181983), items 1-5, after PR #260 (merge 547dc91).
Owners (TL takeover): `src/cee/answer/*`, `specs/answer-citations.md` S2; `src/cee/retrieve/*`,
`specs/retrieval.md` S1; `config/metric_definitions.yaml`, `specs/filings.md` C1; Ask page and
`specs/ui.md` U1. Binding: ADR-021 rules 0-8 and its #246 / #247 amendments, CLAUDE.md ground rules and
"Paid API calls". Branch `tl/247-reduce-2` from origin/main c4ba303.

## Goal
Close the open #247 items before the #250 scored runs. Q24: code never computes a ratio whose two
inputs cover different populations of one firm, and the answer says per firm what is and is not
computable, citing both inputs. Q23 / Q11: a series aspect reaches every period the corpus holds
(EDJ 4Q25 and 4Q24 are in the corpus), each firm's registered definition passage reaches the map, and
a basis break inside one firm's series is flagged by code. Less noise: no duplicate claims, no gap rows
outside an aspect's firm scope, why-lines only on recency / window items and only with the source's
stated context, and the newest-first re-sort only over recency items.

## TL approval conditions (plan approved at 238b3d1 after review rounds 1-2; binding, written in before any code)
1. **Population sources are citable** (round-2 blocking 1): `derive()` records `population_chunk_ids`
   on every proposal (accepted or rejected), only ids that are in the input cell's `plan.pools`
   (`EvidenceMatrix.pools`, set by `run_map`). `EvidenceMatrix.chunk_ids()` (so `reduce.citable(m)`,
   the reduce schema enum and the Sources list) includes them, and their `Hit`s are in `m.hits` (the
   pinned hits are retrieval hits, so `_hits_for` and the quote check see the chunk text). The code
   computability claims are added in `finish_answer` **before** `check_citations`, so the citation,
   number and quote checks run on them like on the model's claims. `derived_values` matches a
   `COMPUTED` claim that cites the input ids plus the population ids (a superset of the inputs).
2. **Population pins only where a ratio input can be** (round-2 blocking 2): a `populations` entry is
   pinned on (a) aspects whose `metric` equals the entry's `input`, and (b) proxy aspects, matched by
   this rule: a proxy aspect with a `metric` takes the entries with `input == metric`; a proxy aspect
   without one takes the entries whose input words are in its text or keyword query
   (`client_assets`: "client assets", "assets under", "AUA", "AUM", "client balances";
   `advisor_headcount`: "advisor", "headcount", "representatives"); none matched -> every entry of the
   firm. Q24: a2 (proxy, "Total client assets ...") -> client-asset entries; a3 (`advisor_headcount`)
   -> headcount entries; a1, a4 -> none. Q11 a1-a4 and Q23 a1 -> headcount entries only. **Q22 gets
   no population pins** (no entry has `input: net_new_assets`), tested.
3. **Round-2 non-blocking 1-4**: (1) `fetch_pinned` applies the doc-type scope except the `adv`
   exclusion (tier 4 stays); (2) the Q24 0-call re-derive rebuilds the pools with the new retrieval
   passes (0 calls) before tagging, then tags and derives over part 1's logged Q24 matrix; (3)
   `PIN_MAX = 8` order: population ids first, then the definition `chunk_id`, then `see_also`; a cut is
   logged (`pins_cut`), never silent; (4) the dated label works both ways: an input older or newer than
   its population statement's `valid_from` (different calendar quarter) gets "population per the
   <document label>, dated <valid_from>".

## Industry terms used
Population (the set of clients or advisors a figure covers; a ratio is valid only over one
population), per-period retrieval (one search per asked period, a "temporal sub-query"), pinned
retrieval (a curated passage fetched by ID under the same SQL filters), structural break (a series
whose basis changes mid-way), near-duplicate removal (shingle overlap, as `fts.DUP_JACCARD`).

## 0. Diagnosis (0 calls; evidence `D:\ALLPROJECTS\EDJ\cache\ev247b\diag\`)
Run on the saved part-1 records (`ev247\real-reduce\report.json`), the saved plan-v3.1 records
(`docs/results/0246-map-raw/`) and the database (`diag_series.py`, `diag_rank.py`, FTS and SQL only).

**Q23 EDJ 4Q25 (and 4Q24) not extracted: a per-document cap, not ranking.**
- `EDJ-10K-2025#130` ("Financial advisors (actual): At year end 20,425 20,125 19,232") holds 4Q25 and
  4Q24 (the prior-year column); `#148` holds the U.S. / Canada split at year end.
- Sub-question a1.EDJ: pool 60 (30 per firm and document type, EDJ has two types), 15 passages kept,
  4,588 tokens of a 40,000 budget. EDJ has five documents and `fts.MAX_PER_DOC = 3`, so 15 is the
  ceiling. In the 10-K, #130 ranks 4th and #148 6th by `ts_rank`; the cap kept #58, #70, #202 (pool
  positions 2, 5, 6; #130 is 7). The budget was not the limit.
- No EDJ document in the corpus has a period end in 2024Q4 or 2026Q3 (the 3Q26 10-Q is not stored):
  2024Q4 comes only from the 10-K's prior-year column, 2026Q3 is a true gap.

**"Current MS advisor counts": none is firm-filed after 4Q2020; the two later figures are filtered out
by design.**
- SQL over every MS chunk: the last count in a filing or supplement is `MS-SUPP-2020Q4#1` (15,950 at
  2020-12-31), as `config/metric_definitions.yaml` already records ("From 1Q2021 the supplements drop
  the line").
- Later figures: trade press (tier 4) "close to 15,000" (`MS-TRADE-2026-09-16-IN-01#0`) and "15,000 or
  so" (`MS-TRADE-2026-08-24-IN-01#2`): tier 4 is excluded on benchmark questions (`doc_type_scope`,
  #179 / ADR-015). Form ADV Part 1A `MS-ADV1A-2026#1` (13,000 employees performing investment advisory
  functions, a Form ADV label): doc type `adv` is excluded outside fee questions. Both are registered
  in `metric_definitions.yaml` (`see_also`, `note`) but never reach the map.
- The same holds for SCHW (`SCHW-ADV1A-2026#1`, 4,127; `SCHW-10K-2025#18` Financial Consultants, not
  in the a1-a4 pools of Q11) and BAC / Merrill (`MER-ADV1A-2026#1`).

**Q11 definitions.** The map labels were right: MS, EDJ and SCHW publish no written definition. What
the answer lacked is each firm's registered definition passage or its closest disclosed text
(`MS-SUPP-2020Q4#3` note, `SCHW-10K-2025#18`, the Form ADV figures) as matrix items, so the reduce
could say "no written definition; reports X as Y" with a citation.

**Q24 populations.** Part 1 derived RJF `1,730.6 / 8,943` and MS `3,999 / 15,950`: each pair has the
same normalised scope string, so `derive()` accepted it. `RJF-SUPP-2025Q3#9` is firm-wide client assets
under administration (RCS assets included); the 8,943 count excludes RCS advisors
(`RJF-10K-2025#228`). MS "Total client assets" spans advisor-led, self-directed and workplace
(`MS-SUPP-2025Q4#36` notes f, i); "Wealth Management representatives" are the advisors of the
advisor-led channel (`MS-SUPP-2020Q4#3` note e). A scope label cannot catch this; the population must
come from config.

**Q19 gap rows.** 58 gap rows: 13 aspects x competitor / research cells. Aspects a7-a13 were planned
for EDJ only; `planner._aspect_firms` widens a list equal to the named firms to "all" on a home-firm
market question ("competitors kept", Q19), so MS / SCHW / MER / RJF / research cells exist for
"How does Edward Jones management describe ..." and each empty one gets a gap. The planner's own subset
is in the saved plan (`firms: ["EDJ"]`), so no planner call is needed.

**Duplicates and why-lines.** Q19 C5 = C12, C6 = C13, C7 = C11: the same research item (one chunk)
under two aspects, word for word. Q26 C3 holds C1 and C2 (same chunk, same figures). Q23 has 16
why-lines on a non-recency series ("the same table also shows 20,309"); Q26's restate the claim ("the
source reports the addition totals $18.7 billion"). The reduce sees only the matrix items, never the
passage around them, so it has no stated context to give.

## 1. Q24: input populations (TL item 1)
**Config** (`config/metric_definitions.yaml`, new top-level list `populations`; `definitions` and the
registered metric keys are unchanged, so `metric_keys()`, the planner schema and every plan cache key
stay as they are):
```yaml
populations:   # #247 part 2: what each ratio input covers, per firm; equal `key` = the same population
  - entity: MS
    input: client_assets            # client_assets | advisor_headcount
    key: ms_wm_all_channels
    covers: Wealth Management total client assets: advisor-led, self-directed and workplace accounts
    match: ["total client assets"]  # phrases, case-insensitive, found in the item's quote or text
    scope: ""                       # optional: the item's normalised scope must equal it
    quote: "..."                    # verbatim from chunk_id (tests/test_metric_definitions.py)
    chunk_id: MS-SUPP-2025Q4#36
```
Entries to write (each quote read in the database at build; anything not stated in a chunk is marked
`TODO-verify` and gets no key, so code treats it as unregistered):
| Firm | Input | Key | Match | Source |
|---|---|---|---|---|
| EDJ | client_assets | edj_firm | "client assets under care", scope whole firm | EDJ-10Q-2026Q2#59 |
| EDJ | advisor_headcount | edj_firm / edj_us / edj_canada | "financial advisors (actual)", by scope | EDJ-10K-2025#130, #148 |
| MS | client_assets | ms_wm_all_channels | "total client assets" | MS-SUPP-2025Q4#36 (f, i) |
| MS | client_assets | ms_wm_advisor_led | "advisor-led client assets" | MS-SUPP-2026Q3#38 (f) |
| MS | advisor_headcount | ms_wm_advisor_led | "Wealth Management representatives" | MS-SUPP-2020Q4#3 (e) |
| RJF | client_assets | rjf_aua_incl_rcs | "client assets under administration", "AUA" | RJF-10K-2025#228 |
| RJF | advisor_headcount | rjf_advisors_excl_rcs | "financial advisors", "total advisors" | RJF-10K-2025#228 |
| BAC | client_assets | bac_gwim | "client balances" (GWIM) | TODO-verify at build |
| BAC | advisor_headcount | bac_gwim_and_consumer | "total wealth advisors" | BAC-SUPP-2023Q4#2 |
| SCHW | client_assets | schw_all_clients | "total client assets" | TODO-verify at build |

Each entry also has `valid_from` (the period end of the document whose `quote` states the
population, e.g. `2025-12-31` for `MS-SUPP-2025Q4#36`): the population statement is dated (review
blocking 2c). `tests/test_metric_definitions.py` checks the quote is verbatim in `chunk_id` and that
`valid_from` equals that document's `period_end` (or its `published_at` when it has none).

**The population source is retrieved and cited** (review blocking 2a, 2b). The `populations` chunk ids
of a firm join that firm's pins (section 2) for every sub-question of an aspect with a registered
metric or a proxy aspect, under the same SQL filters, so whenever a derivation proposal can use an
input, the chunk stating its population is in the cell's retrieved set (`plan.pools`). A population
entry whose chunk did not reach the cell's pool (a filter dropped it) is treated as unregistered for
that item: no key, so code never applies a population it cannot cite.

**Carried through the map facts.** `Item.population: str = ""` (code-set, logged in `to_log`).
`matrix.tag_populations(m)` runs first in `finish()`: each counting item of a firm cell gets the key of
the one `populations` entry of its firm (BAC for MER, as `metric_definition`) whose `match` phrase is in
the item's quote or text and whose `scope`, when set, equals `normalize_scope(item.scope)`; none or
more than one -> `""`. 0 calls; the map prompt and `EXTRACT_VERSION` are unchanged, so map cache keys
are unchanged.

**`derive()` (rule 2 within-firm, extended).** A `ratio` is accepted only when, besides today's checks:
- both inputs have a population key and the keys are equal; else rejected with `why` =
  "populations differ: <numerator covers> (<chunk>) vs <denominator covers> (<chunk>)", or
  "population of <input> not registered";
- neither value is approximate or a bound; else rejected with "<input> is approximate". The markers
  are matched **next to the figure only** (review note 1): the item's `value` field, or the word or
  words directly before the figure in its quote ("approximately", "about", "around", "nearly", "close
  to", "more than", "over", "at least", "roughly", "~", ">", "<") and "+" or "K" directly after it.
  A marker elsewhere in the quote ("increased over the prior year") does not count.
Sum and difference keep today's rules plus the same population check. Rejected proposals stay on the
cell (`ok: false`, `why`), as now.

**What the answer says per firm.** For every cell with a derivation proposal (accepted or rejected),
the reduce input shows the inputs, each with its population entry's own `quote`, the entry's chunk id
and its `valid_from`, and, for a rejection, code's `why`. `covers` is a config label for logs and tests
only; it never reaches an answer text. Prompt v5.1: "For each firm with a computation line, write one
claim saying whether the figure is computable, citing both inputs and the population sources shown."
Code check `check_computability`: a claim with that cell id (or a sub-question id of the aspect, for the
firm) citing every input chunk and every population source chunk; missing -> code adds the claim in
standard wording, flag `code_computability`, citing the two inputs **and** the population source
chunks (all in `plan.pools`, so in the retrieved set):
- `COMPUTED` = "<Firm>: <aspect>: computed by code from two figures that cover the same population:
  <formula_text> (<period>). <source label>: \"<quote>\"" (one quoted source per distinct population
  chunk).
- `NOT_COMPUTED` = "<Firm>: <aspect>: not computed: the inputs cover different populations.
  <numerator source label>: \"<quote>\" <denominator source label>: \"<quote>\"", or "...: not computed:
  <input> is approximate." / "...: the population of <input> is not stated in the documents searched."
- **Dated populations** (blocking 2c): when an input's period ends before its entry's `valid_from`, the
  source label says the date: "per the 4Q2025 supplement note (dated 2025-12-31)"; the input keeps its
  own period in the text.
The values in both texts are the items' values as printed and the quotes are verbatim from their cited
chunks (the number check and the quote check pass them; a computed value passes through the existing
`computed` rule). A firm with no proposal keeps its cell gap.

Expected on a 0-call re-derive of part 1's logged Q24 matrix (test fixture built from
`ev247\real-reduce\report.json`): EDJ accepted (`edj_firm` both), MS rejected (all channels vs
advisor-led), RJF rejected (AUA incl. RCS vs advisors excl. RCS).

## 2. Q23 / Q11 coverage (TL item 2)
Two retrieval passes after the main sub-question searches (in `planner.search_subquestions`; the main
loop is unchanged, so every main chunk list stays identical; both passes exclude every chunk kept so far
and add on top of the sub-question budget):
- **Per-period sub-search** (series aspects with asked periods, `matrix.asked_periods(question, as_of)`,
  moved to a shared helper so retrieval can call it): one FTS search per asked period with the
  sub-question's words and every SQL filter, plus a new hard filter on `documents.period_end` inside the
  period (`fts.Query.period_range`, `filters_sql`), `PERIOD_K = 3` passages, `MAX_PER_DOC` 3. Every
  chunk kept so far is excluded **in the SQL pool, before the `PERIOD_K` cut** (review note 2; the
  `exclude` set leaves the pool as in `fts.search` today), so the cut picks among new chunks only. A period
  with no document of that period end returns nothing (EDJ 2024Q4, 2026Q3). Expected for Q23 a1.EDJ:
  2025Q4 -> `EDJ-10K-2025#130`, `#142`, `#148`. Hits: `origin = "period"`, `part_id` = the sub-question.
- **Registered-definition pin** (aspects with a registered `metric`; plus the `populations` chunks,
  section 1): the firm's `metric_definitions` entry `chunk_id`, its `see_also` ids and its
  `populations` chunk ids (at most `PIN_MAX = 8`), fetched by ID under the sub-question's SQL filters:
  entity / segment (so "same firm" means "passes the SQL entity filter": BAC ids pinned for MER only when
  segment GWIM / Merrill; `BAC-DECK-2025-investor-day#13/#34`, segment NULL, are dropped), window and
  date range (so Q26's 90-day window drops the RJF ids), and the doc-type scope **except the `adv`
  exclusion** (D1, narrowed: the tier-4 exclusion stays for pinned ids too, so a trade `see_also` could
  never enter a benchmark question). Hits: `origin = "pinned"`. Expected per question (review note 4):
  - Q11 a1-a4 (all `advisor_headcount`): `MS-SUPP-2020Q4#1/#3`, `MS-ADV1A-2026#1` (and the other MS
    `see_also` ids), `SCHW-ADV1A-2026#1`, `SCHW-10K-2025#18/#23`, `BAC-SUPP-2023Q4#2`,
    `BAC-10K-2025#246`, `BAC-DECK-2025-investor-day#9`, `MER-ADV1A-2026#1`, `EDJ-10K-2025#130/#148`,
    `EDJ-10Q-2026Q2#60`, `RJF-10K-2025#228/#227/#24`;
  - Q23 a1 (`advisor_headcount`, series): the same ids, plus the period pass;
  - Q24 a3 (`advisor_headcount`, proxy) the same ids; a2 (proxy, client assets) the `populations`
    client-asset chunks (e.g. `MS-SUPP-2025Q4#36`, `EDJ-10Q-2026Q2#59`); a1 and a4 nothing;
  - Q22 a1 (`net_new_assets`, series; no asked periods, "by quarter"): `EDJ-10Q-2026Q2#60`,
    `EDJ-10K-2025#130`, `MS-10K-2025#166/#165`, `MS-SUPP-2025Q4#34`, `SCHW-10K-2025#119`,
    `SCHW-MONTHLY-2026-01#8`, `BAC-10K-2025#249`, `BAC-SUPP-2025Q4#58`, `RJF-10K-2025#224`,
    `RJF-SUPP-2025Q4#8` (each only if it passes the filters; a2 the definitions aspect, if registered);
  - Q26 a7 / a8 (registered metrics, 90-day window): nothing passes the window; Q1, Q3, Q19: no
    registered metric, nothing.
  The exact lists come from the mock 35 and the 0-call count, and are written in the Progress log.
- Both are added to `plan.pools[sq.id]` (the map's retrieved-set check) and logged per sub-question in
  `plan.searched` (`period_hits`, `pinned`). The eval's retrieval scoring includes them (they are
  retrieval); the record adds `added_chunk_ids` by origin.
- Trade press stays out of benchmark questions (D2): the MS "close to 15,000" figures remain unseen;
  MS's gap says no count after 4Q2020 was found, and the pinned Form ADV figure arrives as a
  `different_quantity` item (adjacent).

## 3. Basis break inside a series (TL item 3)
`matrix.basis_breaks(m)` (in `finish`, after `tag_populations`): for each holding cell of a `series`
aspect or a registered-metric `fact` aspect, group its counting items by (normalised scope, population
key). For a flow series (Q22 net new assets) every population key is `""` (populations cover only ratio
inputs), so only the scope splits it (review note 5); the same scope at different periods is one
group. More than one group -> a code caveat (standard wording `BASIS_BREAK`): "<Firm> - <aspect>: the
figures cover different bases and are not one series: <whole firm: 2025Q2, 2025Q3, 2026Q2>; <U.S.:
2025Q1, 2026Q1>; <Canada: 2025Q1, 2026Q1>. The break is flagged, not smoothed." The cell gets flag
`basis_break`; the reduce input prints the caveat under the cell ("state each basis with its periods;
never join them"); the caveat is inserted by code like the comparability caveat. Expected on part 1's
Q23 matrix: EDJ flagged; MS, RJF, MER as their items show.

## 4. Noise (TL item 4)
- **Duplicate claims** (`reduce.dedupe_claims`, after `check_parts`; review note 6: after the dedupe
  `check_comparisons` and `check_computability` run again on the reduced list, so a removed claim can
  never take the comparison or computability claim away silently: if it did, the code gap / code claim
  fires. Nothing else after the dedupe reads part coverage; the eval's `part_coverage` is computed on
  the final answer):
  two claims citing the same chunk-id set are duplicates when their texts without the why-line and the
  "<Firm>: " prefix are equal after normalising, or when every figure of one is in the other and the
  word 5-gram overlap of the shorter with the longer is >= `fts.DUP_JACCARD` (0.6). The longer is
  kept (ties: the first); the other is removed and logged (`duplicates_removed`: text, part id, kept
  index). Citations are never lost: the kept claim cites the same set. Expected on part 1: Q19 3 pairs,
  Q26 C1 and C2 into C3. The reduce input also marks an item that appears in several cells ("also under
  <aspect>: write it once").
- **Gap rows only inside an aspect's firm scope** (Q19): `Aspect.asked_firms` (new, not in any cache
  key): the planner's validated subset before the home-firm "competitors kept" widening. `build_gaps`
  writes per-cell gaps only for cells whose firm is in `asked_firms` (when set) and for research cells
  only when `asked_firms` is empty. Cells with `role == "competitor"` (set only through
  `q.theme_peers` on a home-firm market question, planner.py `firm_scope`) of an aspect without a
  subset that hold nothing (`not_found` / `not_disclosed`) are folded into one gap per aspect (D3):
  "Competitors (<names>) - <aspect>: not found in the documents searched." A competitor cell that holds
  anything is shown as now. `named` cells are never folded: on benchmark questions (Q11, Q22-Q24)
  each firm keeps its own gap, the honest "which do not". Expected on part 1's Q19 matrix (0-call replay): about 16 gap rows instead of 58.
- **Why-lines only for recency / window, with stated context**: prompt v5.1 keeps the why-line rule for
  recency aspects and window questions only and says "never on other items". The reduce input shows,
  for every item of a recency aspect or a window question, `context:` = the cited passage around the
  quote (up to 600 characters, cut at word boundaries; code-built from the chunk text). The why sentence
  must state what the source says about why the item matters (a reason, a first, a record, a change,
  management's stated purpose), not the item again. Code:
  - a why-line on an item outside recency / window is removed (flag `why_line_removed`, text logged);
  - `why_line_restates`: the why sentence adds no content word or figure beyond the claim's own text
    (content words = lower-case words minus a stop list and the firm's names; restates when >= 80% of
    them and every figure are in the claim body) -> replaced with `WHY_UNSAID`, flag
    `why_line_restated`, the model's sentence kept in the log (D4).
  - Before the paid run (review note 7, TL D4): the 0-call replay of part 1's saved Q26 (and Q19, Q23)
    reduce output through the new checks reports how many why-lines would be restated / removed; the
    Q26 count goes in the Progress log and to the TL before the run.

## 5. Review items (TL item 5)
- **Re-sort only recency items** (`order_newest_first`): with the question's own window, the whole
  answer as now (Q26); with recency aspects and no window, only the claims and adjacent items of those
  aspects are re-sorted, in place (the slots they occupy keep their positions), so Q19's aspect grouping
  stays.
- `docs/RUN.md` (Windows and Mac blocks): the `--max-calls` of the real run is the number the 0-call
  count gives (round 1 + the re-extraction bound + reduce), never a fixed number; the example becomes a
  placeholder `<cap from the count>`.

## 6. Prompt and reduce input
`prompt.REDUCE_VERSION = "v5.1"`, `SYSTEM_PROMPT_V5` revised in place (the reduce key hashes the
prompt text): computation lines (section 1), basis-break caveats (section 3), "write an item listed
under several aspects once", why-lines only for recency / window with the context line (section 4).
v4.1 unchanged. No question text, no `passes_if` text (the 6-word-run test).

## Files to change
- `config/metric_definitions.yaml` - `populations` list and its header comment.
- `src/cee/answer/matrix.py` - `Item.population`, `tag_populations`, `derive` population and
  approximate rules, `basis_breaks`, `BASIS_BREAK`, `build_gaps` scope rule and competitor fold,
  `asked_periods` callable from retrieval.
- `src/cee/retrieve/planner.py` - `Aspect.asked_firms`; `search_subquestions(..., as_of=None)` per-period
  and pin passes, `plan.pools`, `plan.searched` fields.
- `src/cee/retrieve/fts.py` - `Query.period_range` and its `filters_sql` clause; `fetch_pinned(q, ids)`
  (by ID, the same entity / segment / window / date-range filters and the doc-type scope except the
  `adv` exclusion: tier 4 stays excluded); `Hit.origin`
  values `period`, `pinned`.
- `src/cee/answer/reduce.py` - rendering (computation lines, basis breaks, context lines, repeated
  items), `check_computability`, why-line scope and restating checks, `dedupe_claims`, the recency-only
  re-sort, log fields.
- `src/cee/answer/prompt.py` - v5.1, `COMPUTED`, `NOT_COMPUTED`, `BASIS_BREAK`, `COMPETITORS_GAP`.
- `src/cee/ask.py` - `as_of` into `search_subquestions` (today), log fields.
- `src/cee/app/views/ask_page.py`, `specs/ui.md` - chip labels: `code_computability`, `basis_break`,
  `why_line_removed`, `why_line_restated`.
- `scripts/eval_run.py` - `as_of` into retrieval, records (`added_chunk_ids`, reduce info:
  `duplicates_removed`, `why_line_removed`, `why_line_restated`, `code_computability`, `basis_breaks`).
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-answer.md` - only if an asserted
  line changes (checked at build; stated in the PR either way).
- Tests: `tests/test_matrix.py`, `tests/test_reduce.py`, `tests/test_subquestions.py`,
  `tests/test_fts_window.py` (period filter), `tests/test_metric_definitions.py` (populations quotes),
  `tests/test_planner.py` (`asked_firms`), `tests/test_eval_run.py`, `tests/test_prompt.py`.
- `specs/answer-citations.md`, `specs/retrieval.md`, `specs/filings.md` (the `populations` fields),
  `docs/DECISIONS.md` (ADR-021 amendment, #247 part 2: populations in derivation with dated, cited
  sources, pinned definitions past the `adv` exclusion only (amends ADR-015 for registered ids),
  per-period retrieval,
  basis-break caveat, gap scope; **ADR text, so the PR is escalated to the TL for the merge**),
  `docs/RUN.md`.
- `docs/results/0247-reduce-2-check.md`, `docs/results/0247b-raw/` (raw records of the real run).
- Not committed: `D:\ALLPROJECTS\EDJ\cache\ev247b\run-real.ps1` and `run-real.sh` (gated wrapper), the
  diagnosis scripts.

## Steps
1. Config `populations` (quotes read in the database), `tag_populations`, `derive` rules; tests; the
   0-call re-derive of part 1's Q24 matrix (expected section 1).
2. `fts.period_range`, `fetch_pinned`, the two retrieval passes, `asked_firms`; tests; 0-call re-run of
   `diag_series.py`: Q23 a1.EDJ now holds `EDJ-10K-2025#130`; Q26's lists unchanged.
3. `basis_breaks`, gap scope and competitor fold; tests; 0-call replay of part 1's Q19 and Q23 matrices
   (gap count, the EDJ break).
4. Reduce v5.1: rendering, `check_computability`, why-line checks, dedupe (then the comparison and
   computability checks again), recency-only re-sort; tests; 0-call replay of part 1's eight saved
   reduce outputs through the new post-call code (duplicates, why-lines removed / restated, re-sort
   counts), reported, nothing re-run; Q26's restated count to the Progress log.
5. ask / eval / app wiring, chips; tests; full pytest.
6. Mock 35-question run against main c4ba303 (section 8).
7. verify-cee; specs, ADR amendment, RUN.md.
8. Seed the cache, 0-call count (with per-call passages and tokens), the cap in the Progress log; the
   real run of the eight questions (section 9); raw records
   saved; blind-in prepared; **stop before scoring** (the TL starts the blind scorer).
9. After the TL's scoring: `docs/results/0247-reduce-2-check.md`, `/finish-task`, PR "Part of #247" or
   "Closes #247" only if all eight pass blind (section Acceptance), `gh pr checks` green.

## Tests (0 real calls; `tests/conftest.py` blocks every client)
- **Populations**: RJF-shaped (AUA incl. RCS / advisors excl. RCS) -> rejected, `why` names both;
  MS total client assets / WM representatives -> rejected; MS advisor-led / WM representatives at one
  period -> accepted; EDJ firm / firm -> accepted; EDJ firm assets / U.S. count -> rejected; an input
  with no matching entry -> "not registered"; ">15K", "more than 20,000", "approximately 9,000" ->
  "approximate"; **negative**: an EDJ-shaped quote "... $2,647 ... increased over the prior year ..."
  is not approximate and the ratio is accepted (review note 1); two entries matching one item -> no
  key; an entry whose chunk is not in the cell's pool -> no key. Every `populations` quote verbatim in
  its chunk and `valid_from` equal to its document's period end (database test, skipped without one).
- **Computability**: a matrix with one accepted and one rejected proposal and a fake reduce output
  without their claims -> two code claims (`COMPUTED`, `NOT_COMPUTED`) citing both inputs and the
  population source chunks, quoting the entries' `quote` verbatim (no `covers` text), flagged
  `code_computability`, no `number_not_found`, no `quote_not_found`; an input dated before its entry's
  `valid_from` -> the dated source label; with the model's own claims citing inputs and sources -> none
  added. **Citation test** (blocking 2d): through `search_subquestions` with fake searches and a fake
  pin fetch, every chunk id a code computability claim cites is in `plan.pools` of its sub-question and
  the claim passes `check_citations` (no `unmatched_citation`, no `outside_matrix`).
- **Per-period search**: a Q23-shaped fake search: one call per asked period with `period_range`, the
  sub-question's filters kept, kept chunks excluded, main lists unchanged; a question without asked
  periods or a window question -> no period call. `filters_sql` emits the `period_end` clause.
- **Pins**: registered ids fetched for registered-metric aspects only (and population ids for
  registered-metric or proxy aspects); only ids passing the SQL entity / segment filter (a MER
  sub-question gets BAC ids with segment GWIM, not segment NULL ones); window filter applied (a
  Q26-shaped window drops them); the `adv` exclusion not applied, the tier-4 exclusion applied (a trade
  `see_also` id on a benchmark question is dropped); already-kept ids not repeated; `plan.pools`
  includes them (the map accepts their citation).
- **Per-period exclusion before the cut**: a fake pool whose top three for a period are already kept ->
  the period search returns the next three (the EDJ #130 case).
- **Basis break**: Q23 EDJ-shaped items (whole firm, U.S., Canada) -> one caveat listing each basis
  with its periods, `basis_break` on the cell; one basis -> none; a Q22-shaped flow series with the
  same scope at different periods (population keys all `""`) -> none; MS Wealth Management vs firm
  scope in one cell -> a caveat; a recency aspect -> none.
- **Gap scope**: Q19-shaped plan (`asked_firms = [EDJ]` widened by the home-firm rule) -> no gaps for
  competitor or research cells of those aspects; aspects without a subset -> one competitors gap for the
  `role == "competitor"` cells, named and research cells as before; a competitor cell holding a
  different quantity keeps its own gap. **Q11 / Q23 / Q24-shaped** matrices (all cells `named`, no
  theme peers) -> one gap per firm per empty cell, nothing folded. `validate_plan` records
  `asked_firms`.
- **Dedupe**: Q19-shaped exact repeats -> one kept; Q26-shaped subsumed claims -> the longer kept;
  different chunk sets with equal text -> both kept; part coverage unchanged; a duplicate pair where the
  removed one was the comparison claim -> the comparison check re-runs and the kept claim (same aspect)
  still counts, or the code gap fires; the same for a computability claim.
- **Why-lines**: a non-recency claim with a why-line -> removed, flagged; a restating why -> replaced
  with `WHY_UNSAID`, flagged, logged; a why with a new fact or reason -> kept; the context line is
  rendered only for recency / window items and is cut at 600 characters.
- **Re-sort**: Q19-shaped (one recency aspect, no window) -> only its items move, the other aspects keep
  order; Q26-shaped window -> whole answer as before.
- **Prompt**: v5.1, the 6-word-run test; reduce key changes with the prompt text.
- `test_no_paid_calls` green.

## Acceptance
- [ ] Q24 (real): no ratio on inputs of different populations (RJF, MS total client assets refused, or
      accepted only on advisor-led / WM representatives at one period); per firm with a proposal one
      claim saying computable or not, citing both inputs; the comparison claim; EDJ computed.
- [ ] Q23 (real): EDJ 4Q24 and 4Q25 points from `EDJ-10K-2025#130`; the EDJ basis break flagged by
      code; MS states the last count (2020) and the closest current firm-filed figure as adjacent;
      period gaps named; no why-lines.
- [ ] Q11 (real): each firm's definition quoted, or "no written definition" with what the firm reports,
      cited (pinned definitions in the matrix); differences named.
- [ ] Q19 (real, regression): blind PASS kept; no gap row outside an aspect's firm scope; no duplicate
      claims; why-lines only on a12; the other aspects keep their order.
- [ ] Q26 (real, regression): blind PASS kept; why-lines carry stated context (0 `why_line_restated`
      left unreplaced), newest first, no duplicates.
- [ ] Q22 (real, regression; issue acceptance "Q1, Q3, Q22 keep PASS"): blind PASS kept; pinned
      definitions per firm; no must-not chunk (`MS-PR-2026-04-15-01#15`, `SCHW-10Q-2026Q2#56`) cited as
      a fact; every basis-break caveat it gets listed and checked against its items.
- [ ] Q1 and Q3 (real, regression): blind PASS kept under v5.1 (maps reused; only the reduce changes).
- [ ] The outcome is the issue's acceptance: "Closes #247" only if every target and every regression
      question passes blind; otherwise "Part of #247" with the open items. No regression check is
      dropped.
- [ ] Tests listed above; 0 real calls in tests.
- [ ] Mock 35: every main chunk list identical to main; only `pinned` / `period` additions, each listed;
      recall not lower; forbidden hits from additions reported; mock answers pass every code check.
- [ ] pytest, verify-cee and `gh pr checks` green.
- [ ] ADR-015 / ADR-021 amendments in the PR -> escalated to the TL for the merge.

## 8. Mock 35-question check (0 calls)
`eval_run.py` (mock) at the branch head vs main c4ba303 (a detached worktree): per question every main
sub-question chunk list identical; additions only with origin `pinned` / `period` (listed per question;
expected on questions whose rule plan has a registered metric or a series with asked periods: Q11,
Q22 (net new assets: its five firms' NNA definitions pinned, review blocking 1), Q23, Q24, Q28 and any
other with "advisor headcount" / "net new assets" in its text; none on Q1, Q3, Q19, Q26); recall
@pool / @final not lower; forbidden / `must_not_return` hits among the additions reported; refusal 8/8
unchanged; mock answers: 0 `outside_matrix`, 0 `part_gap`, 0 comparison claims missing, 0 why-lines
missing, behavior = matrix behavior. Evidence `D:\ALLPROJECTS\EDJ\cache\ev247b\mock-*`.

## 9. Real check (last, after every mock check passes)
- **Why the mock cannot show it**: whether v5.1 states per-firm computability and basis breaks in words
  a strategist would forward, writes why-lines from the stated context, and whether the added passages
  give Q11 / Q23 their missing points needs the real model. Q19, Q26, Q22, Q1 and Q3 guard against
  regressions: v5.1 changes every reduce, and Q22's map inputs change through the definition pins
  (review blocking 1, TL ruling).
- **Questions, one run each**: Q11, Q23, Q24 (targets); Q19, Q26, Q22, Q1, Q3 (regression; the issue's
  "Q1, Q3, Q22 keep PASS" and part 1's Q19 / Q26 PASS). No re-rolls: an invalid output, a failed call or
  a wrong answer is a finding. A ProviderStop or a 400 stops the run (the part-1 `allow()` rule); the
  rest waits for the TL.
- **Settings** (pinned and printed by the wrapper `ev247b\run-real.ps1` / `.sh`): `LLM_PROVIDER=deepseek`,
  `deepseek-v4-pro`, `/beta` strict tools, thinking on, `MAP=on`, `MAP_CONCURRENCY=6`,
  `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1.1, prompt v5.1, request version
  `ds-strict-1-think-on-a64000-p64000`, `--as-of 2026-11-17`, snapshot `corpus-2026-11-19`. Code gate:
  `git status` clean, `src scripts config` identical to the mock-run sha. `.env` copied in from the main
  repo inside `try` and removed in `finally` (trap on Mac); never read or printed.
- **Reuse** (saved plans and maps wherever the inputs are unchanged): the plan-v3.1 records
  (`docs/results/0246-map-raw/Q{11,19,23,24,26}-plan-*`, `docs/results/0247-raw/Q{1,3,22}-plan-*`) and
  every part-1 map / re-map record (`docs/results/0247-raw/`) are seeded into the worktree's
  `.eval-runs/cache`. Planner: 0 calls (the plan key holds `metric_keys()`, unchanged: populations are a
  separate list). Map: Q19, Q26, Q1 and Q3 inputs do not change (no registered metric outside a window,
  no series with asked periods), so their map keys should match part 1 (0 calls); Q11, Q23, Q24 and Q22
  inputs change (pins, periods), so they are mapped again. Reduce: v5.1 changes every key: 8 calls.
- **Expected calls** (upper bounds; re-extraction bound = firms):
  | Q | Planner | Map round 1 | Re-extraction (at most) | Reduce | At most |
  |---|---|---|---|---|---|
  | Q11 | 0 | 5 | 5 | 1 | 11 |
  | Q23 | 0 | 5 | 5 | 1 | 11 |
  | Q24 | 0 | 5 | 5 | 1 | 11 |
  | Q22 | 0 | 5 | 5 | 1 | 11 |
  | Q19 | 0 | 0 (4 if its key changed) | 0 (5) | 1 | 1 (10) |
  | Q26 | 0 | 0 (1) | 0 (1) | 1 | 1 (3) |
  | Q1 | 0 | 0 (map reused) | 0 | 1 | 1 |
  | Q3 | 0 | 0 (map reused) | 0 | 1 | 1 |
  | **Total** | **0** | | | **8** | **48 with the expected reuse; ceiling 59** |
  The ceiling 59 (TL ruling) covers Q19 and Q26 being re-mapped too; it assumes the Q1 and Q3 maps are
  reused. If the count shows a Q1 or Q3 map record not reused, or a total above 59, the plan is amended
  before any call.
- **0-call count first**: `eval_run.py --real --map-only --max-calls 0 --questions
  Q11,Q23,Q24,Q22,Q19,Q26,Q1,Q3 --as-of 2026-11-17 --out ...\ev247b\real-count` (seeded cache, no key in
  the environment): prints the exact round-1 list and which records are reused, and, per map call, the
  passage count and estimated input tokens against the per-call input limit (`extract.input_limit`;
  review note 3: Q23 a1.MS already keeps 66 passages and a1.RJF 68; eight periods x 3 plus pins add
  about 30 per firm). The run's cap = round 1 + the re-extraction bound of those firms + 8, written in
  the Progress log with the per-firm counts before the run; a call over the input limit is a finding
  reported before the run (never trimmed).
- **Before the run (0 calls)**: the replay of part 1's saved reduce outputs (step 4) gives the
  `why_line_restated` / `why_line_removed` counts for Q26, Q19 and Q23 and the duplicates per question;
  Q26's count is written in the Progress log and reported to the TL (TL D4, review note 7).
- **Run**: `eval_run.py --real --max-calls <cap> --questions Q11,Q23,Q24,Q22,Q19,Q26,Q1,Q3 --as-of
  2026-11-17 --out D:\ALLPROJECTS\EDJ\cache\ev247b\real-run` in the background. Mac: the same with
  `.venv/bin/python` and `../cache/ev247b/...`. Raw records copied to `docs/results/0247b-raw/`.
- **Stop before scoring**: prepare `D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in\` as part 1 (an answers dump
  of the eight answers, the eight questions from `evals/questions.yaml`, part 1's verdict rule with the
  Q24 superseded behavior line) and `blind-in-hashes.txt`; report to the TL, who starts a fresh blind
  scorer. Baseline: part 1 blind (Q1, Q3, Q19, Q22, Q26 PASS; Q11, Q23, Q24 FAIL).
- **Reported** (in the check doc and the PR): per question the matrix summary, the added passages by
  origin, the derivations (accepted / rejected and why), basis breaks, gap rows before / after,
  duplicates removed, why-lines removed / restated, calls by type, tokens, wall time, cost with the
  per-1M rates and their source (as part 1).

## Decisions (TL rulings on review round 1, issuecomment-7037522138)
- **D1 - Pins bypass only the `adv` exclusion** (narrowed): the tier-4 exclusion stays for pinned ids;
  window, date range, entity and segment filters apply; "same firm" means the chunk passes the SQL
  entity filter. ADR-015 amendment, escalated to the TL.
- **D2 - Trade press stays out of benchmark questions.** MS's answer is the last firm-filed count
  (4Q2020), the Form ADV figure as adjacent, and the named gap.
- **D3 - Fold empty competitor cells** into one gap per aspect, for `role == "competitor"` cells only;
  `named` cells on Q11 / Q22-Q24 keep one gap per firm (tested).
- **D4 - A restating why-line is replaced by code** with `WHY_UNSAID`, the model's sentence kept in the
  log; Q26's restated count from the 0-call replay reported before the paid run.
- **D5 - Computability claims added by code when the reduce omits them**, citing the inputs and the
  population sources and quoting the sources (blocking 2).
- The ADR-015 / ADR-021 amendments in the PR are escalated to the TL for the merge.

## Risks
- Pins and periods add passages: about 30 more per firm on Q23 (on top of 60-70 for MS / RJF / MER);
  the 0-call count gives every call's passages and tokens against the input limit before the run;
  cost reported.
- Q22's pins and basis-break caveats can change a passing answer; it is in the real run for that reason.
- Population matching by phrase can miss an item worded differently: it then reads as unregistered and
  the ratio is refused (safe side); the 0-call re-derive and the real run report every refusal reason.
- The restating test is lexical; a why sentence with one new word passes. The scorer judges the rest.
- Removing duplicates after the part check may leave a cell with no claim of its own: its content is in
  the kept claim; logged.

## Progress log
- 2026-11-20 - plan written (worktree `D:\ALLPROJECTS\EDJ\wt-247b`, branch `tl/247-reduce-2` from
  origin/main c4ba303). Diagnosis (0 calls, `ev247b\diag\`): Q23 a1.EDJ hit the per-document cap
  (`EDJ-10K-2025#130` 4th in the 10-K, 3 kept, 4,588 of 40,000 tokens used); no firm-filed MS count after
  4Q2020, the later figures are tier-4 trade press and Form ADV (both outside the benchmark scope);
  Q24's two inconsistent ratios trace to equal scope strings over different populations; Q19's 58 gap
  rows come from the home-firm widening of EDJ-only aspects.
- 2026-11-20 - plan review round 1: PLAN CHANGES REQUESTED (issuecomment-7037522138), 2 blocking, 7
  non-blocking; TL rulings adopted in full. Blocking 1: Q22, Q1, Q3 added to the real run as regression
  questions (saved plans and maps reused where inputs are unchanged), acceptance "Q1, Q3, Q22 blind PASS
  kept", "Closes #247" only if all eight pass; ceiling 59, exact cap from the 0-call count. Blocking 2:
  population chunks pinned with the definitions, `valid_from` per entry, computability claims cite and
  quote the population sources (no `covers` text in answers), dated labels for older inputs, a test
  that code claims cite only `plan.pools` chunks. Notes 1-7: approximate markers next to the figure
  only (negative test), kept chunks excluded before the period cut, per-call input size from the count,
  pinned aspects named per question, `basis_breaks` on flow series, comparison / computability checks
  re-run after the dedupe, Q26 restated count reported before the run. D1 narrowed to the `adv`
  exclusion; D2-D5 as ruled.
- 2026-11-20 - plan review round 2 (7037650142): 2 blocking, 4 non-blocking; TL approved at 238b3d1 with
  conditions, written into "TL approval conditions" before any code (population chunk ids citable and
  in `m.hits`, code claims checked by `check_citations`; population pins only on matching metric or
  proxy aspects, Q22 none; `fetch_pinned` keeps tier 4; Q24 replay rebuilds pools; pin order; dated
  label both ways). Build starts.
- 2026-11-20 - build (746c8d0 .. 715adda): populations config and tagging, `derive()` population /
  approximate rules with `population_chunk_ids` citable, per-period sub-search and pins
  (`fetch_pinned`: entity / segment / window / date range, doc-type scope except `adv`), `asked_firms`,
  gap scope and competitor fold (model gaps outside the scope dropped, part coverage `out_of_scope` /
  `competitors_gap`), basis breaks, reduce v5.1 (computation lines and code claims before the citation
  check, context lines, why-line removal / restating replacement, dedupe by content containment then the
  comparison and computability checks again, recency-only re-sort), chips, eval fields (`added_chunk_ids`,
  per-call `passages` / `input_tokens_est`, reduce info), plan cache key kept stable (the new
  retrieval-only Query fields). New tests: `tests/test_populations.py`, `tests/test_series_coverage.py`,
  `tests/test_reduce_noise.py`. pytest 957 passed (0 real calls).
- 2026-11-20 - mock 35 (0 calls; main c4ba303 in `wt-247b-main` vs 715adda, `ev247b\mock-compare2.txt`):
  every main sub-question list identical, additions only `pinned` (Q1 2, Q11 12, Q22 5, Q23 17; the mock
  rule plan has no series aspect, so no period pass), recall not lower (Q11 @final 0.4 -> 1.0, Q22 0.75 ->
  0.875), no new forbidden hit, statuses and refusal unchanged (33 PASS / 2 FAIL); mock answers: 0
  outside the matrix, 0 part gaps, 0 why-lines missing, 0 comparison claims missing, behavior = matrix.
- 2026-11-20 - verify-cee at 9f66be3 (`.verify-runs/20261120-064407-9f66be3`): VERIFY PASS; ask-answer,
  ask-progress, gap-path, invalid-chunk, coverage, filters, feedback PASS; open-citation and
  download-document UNREACHABLE (no raw files in data/raw, as in part 1). No recipe line changed.
- 2026-11-20 - 0-call replay of part 1 (`ev247b\diag\replay_part1.txt`; part 1's logged matrices and saved
  reduce outputs, pools rebuilt with the new passes, TL condition 3.2): **Q24** EDJ accepted (edj_firm /
  edj_firm, sources EDJ-10Q-2026Q2#59, EDJ-10K-2025#130), MS refused (ms_wm_all_channels vs
  ms_wm_advisor_led), RJF refused (rjf_aua_incl_rcs vs rjf_advisors_excl_rcs, RJF-10K-2025#228); three code
  computability claims, 0 outside the matrix. **Q26**: 27 of 30 why-lines would be replaced as restating
  (part 1's why-lines), 2 duplicates removed. Q19: gap rows 58 -> 16, 12 duplicates, 1 why-line
  restated, 3 re-sorted (a12 only). Q23: 25 why-lines removed (not recency), EDJ and RJF basis breaks,
  `EDJ-10K-2025#130` reached by the 2025Q4 period search. Q11: 4 duplicates. Q1, Q3, Q22: unchanged.
- 2026-11-20 06:52 - 0-call count (`ev247b\real-count`, no key, `--max-calls 0`, code gate 715adda): 8
  plans reused (0 planner calls). Map records reused: Q1, Q3, Q19 (4 + 3 re-extractions), Q26 (1 + 1),
  Q22 SCHW / EDJ / MER / RJF. Round 1 to call: Q11 5, Q22 1 (MS: a pinned NNA chunk), Q23 5, Q24 5 =
  **16**. Re-extraction bound (firms re-mapped): Q11 5, Q22 1, Q23 5, Q24 5 = 16. Reduce 8. **Cap 40**
  (ceiling 59). Largest map inputs (estimated tokens / passages): Q24 RJF 72,337 / 221, Q24 MS 71,528 / 212,
  Q11 SCHW 71,308 / 230, Q11 MS 69,482 / 220, Q24 SCHW 67,996 / 221, Q23 MS 31,086 / 92; all under the
  DeepSeek input limit (1,000,000 - 64,000). Refusal flags on Q11 / Q22 / Q24 are the same must-not
  retrievals as part 1 (main search, not the additions).
- 2026-11-20 07:50 - real run (cap 40, code gate 715adda, run at 6a3825a, `ev247b\real-run`): **26 calls**
  (16 map, 2 re-extraction, 8 reduce), 24 records reused, about $1.36 (off-peak). No ProviderStop, no 400,
  no invalid output; **Q3's reduce call failed** (`APIConnectionError`), saved as `failed_call`, not re-run.
  Raw records in `docs/results/0247b-raw/`. Findings (Q24 RJF refusal reason, Q23 RJF basis-break noise,
  Q19 duplicate comparison gap) in `docs/results/0247-reduce-2-check.md`. Blind inputs prepared in
  `ev247b\blind-in\` with `ev247b\scorer-prompt.txt`; **stopped before scoring** (the TL starts the scorer).
- 2026-11-20 07:57 - **TL decision: 1 transport retry** of Q3's reduce call (the APIConnectionError returned no
  model output): one call, same inputs and settings, valid answer (23 claims). Failed record kept as
  `docs/results/0247b-raw/Q3-reduce-ec259fc6b468c54a5288cdfa.failed-1.json`, the retry next to it. **Total
  27 calls, about $1.38.** The wrapper's output folder variable was shadowed, so the retry overwrote
  `ev247b\real-run\report.json`; the eight-question report was rebuilt with 0 calls (`ev247b\real-run-final`),
  the seven other answers identical. Blind inputs rebuilt with Q3's answer; hashes updated. No code change.

## Revision after scoring (TL, after blind 5/8; plan amended before any code)
Blind part 2: Q1, Q3 PASS; Q19, Q22, Q24 PASS (borderline); Q26 FAIL (s, borderline); Q11, Q23 FAIL. Q24
moved FAIL -> PASS, **Q26 regressed PASS -> FAIL**: under the acceptance this PR does not merge with it.

**R1 - Q26 why-lines (the regression).** ADR-021 rule 5 allows a why-line that is either the source's own
stated context or verifiable factual background with a citation. v5.1 told the reduce to write "the source
does not say" whenever the item's own context gave no reason; the model did so on 11 of 31 items (8 of them
from one article, `RJF-TRADE-2026-10-29-WM-01#1`), and code replaced none (`why_line_restated` 0).
**Why the 0-call replay showed 27 replacements and the run 0**: the replay ran part 1's v5 output (restating
why-lines) through the new check; v5.1's own output had no restating lines. Its 11 "does not say" lines were
written by the model, and the check leaves those alone. Change (prompt v5.2, `REDUCE_VERSION = "v5.2"`):
- The why sentence is either what the item's own passage says about why it matters, or factual background
  from another passage in the matrix (same firm or the same theme: an earlier period's figure, a stated
  target, a firm statement on the same subject), cited by adding its chunk id to the claim. "The source does
  not say" only when no passage in the matrix gives either; never the default.
- The reduce input lists, under each recency / window item, up to 3 "related" matrix items of the same firm
  (or research row) sharing content words with it (chunk ids and one-line text), so the model can cite
  background.
- Code (`clean_why_lines`): a restating why-line is replaced with "the source does not say" **only** when the
  claim cites nothing besides the item's own chunk(s); a why-line citing an extra chunk is kept (its figures
  go through the number check over all cited chunks). Code never writes "does not say" otherwise. A new count
  `why_line_unsaid` (model-written) is logged next to `why_line_restated`.
- Tests: a Q26-shaped item whose own passage has no reason, with a related item in the matrix -> a fake
  output citing the related chunk passes with no flag; a restatement citing only its own chunk is replaced;
  one citing an extra chunk is kept; the related-items lines are rendered for recency / window items only.

**R2 - Finding 1 (Q24 RJF reason) and EDJ "definition unverified".**
- `tag_populations`: when no match phrase stands before the figure, the whole quote and the item text are
  read (the RJF 8,943 item quotes "We had 8,943 employee and independent contractor financial advisors ..."),
  so the item gets `rjf_advisors_excl_rcs` and the refusal reads "populations differ", quoting
  `RJF-10K-2025#228`. Test with that quote.
- EDJ: `derive()` marks a derived cell `definition_unverified`, and `mark_comparability` marks the ratio
  aspect `unverified`, because the ratio aspect itself has no registered `metric` (EDJ's registered entries
  are for the inputs, not the ratio). Change: a derived cell whose two inputs carry registered populations is
  not `definition_unverified`, and the aspect mark is `none` when every derived cell is so (the computation
  claim already quotes both population sources). Test.

**R3 - Finding 2 (basis break from items with no population).** In a cell where some items carry a
population, an item without one joins the group of its scope when that scope already has a group, and counts
as a basis of its own only when it is a dated series point (`period` set) under another scope. Q23 RJF: the
employee / independent split items join "whole firm"; the undated "approximately 9,000" (PCG) and FID 940
items make no basis -> no caveat. EDJ U.S. 1Q26 (dated, scope U.S.) keeps the EDJ break. Flow series (no
population anywhere) unchanged. Tests.

**R4 - Finding 3 and Q19 gap contradictions.** `check_comparisons` adds `COMPARISON_MISSING` only when that
aspect has no such gap yet (the re-check after the dedupe never doubles it). A normative comparison aspect
(its text is normative) is covered by the hand-off sentence in an `answer_with_boundary` answer. Gap
contradictions: `place_gaps` drops a model gap (logged as `gap_contradicts_claim`) whose part id is a cell that
holds, or an aspect with `asked_firms` whose asked firms' cells all hold (the Q19 a7-a12 lines "Morgan
Stanley, Schwab, Merrill, Raymond James and Industry research - how Edward Jones management describes ...:
not found"). Tests.

**R5 - Q22 (non-blocking): definition wording across one firm's filings.** For a registered-metric aspect,
when one firm's items quote definitions (`definition`) that differ after normalising, from different
documents, code adds the caveat `DEFINITION_CHANGED` = "<Firm> - <metric>: the definition wording differs
between <doc A> ('<cut 160>') and <doc B> ('<cut 160>'); figures are listed as each document states them."
(EDJ net new assets: the 10-K 2025 without "including fees and commissions", the 2026 10-Qs with it.) Test.

**Not changed (findings, TL item 3): Q11 and Q23.** Classification with 0 calls (SQL on `cee`):
- Corpus gaps (to the NEXT list; they do not block this PR):
  - MS advisor count after 4Q2020: 0 count lines in every MS 10-K, 10-Q, supplement and press release with a
    period end from 2024Q4 (`MS-SUPP-2025Q4` .. `MS-SUPP-2026Q3` have no "Wealth Management
    representatives" line); later figures exist only as tier-4 trade press and Form ADV (pinned, adjacent).
  - RJF quarterly headcount: the only counts with a period end in 2024Q4-2026Q3 are the FY2025 10-K (8,943;
    split 3,878 / 5,065; `RJF-10K-2025#24`, `#227`) and the 3Q25 call (8,943); trade press says RJF "no
    longer reports advisor headcount" (tier 4).
  - Merrill / BAC count after 4Q2023: only award lists and the investor-day ">15K Wealth Advisors" (3Q25,
    approximate); no count in BAC 10-K, 10-Q, supplements or press releases 2024-2026.
  - EDJ 3Q26 10-Q not in the corpus (the 2026Q3 gap).
  - Q11 definitions: MS and EDJ publish no written definition; BAC's latest is the 2023 supplement footnote;
    Schwab publishes no advisor count (its registered figure is Form ADV).
- Answer problems (not corpus): Q11 "differences not named" (no comparison aspect in the saved plan; the
  comparability caveat lists the definitions cut at 160 characters) and Schwab shown as a gap rather than "no
  count published; the closest firm-filed figure is Form ADV"; Q23 no plain statement per firm of where its
  series stops. Candidates for a follow-up issue; not in this revision.

**Real re-check (after every mock check passes).** New reduce calls only for **Q26, Q24, Q19, Q22**, one run
each; plans and maps reused (the revision changes no retrieval and no map prompt). 0-call count with the
current code (`ev247b\recheck-count`, `--max-calls 0`, no key): all 4 plans and all 20 map / re-extraction
records reused, 0 calls; the reduce keys change with v5.2 and the rendered matrix. **Bound: 4 calls (4
reduce; 0 planner, 0 map, 0 re-extraction).** The count is repeated after the build; any other call means
the plan is amended first. Q1, Q3, Q11 and Q23 keep their part-2 answers (their reduce is not re-run; their
verdicts stand). A fresh blind scorer then scores Q19, Q22, Q24, Q26 (inputs in `ev247b\blind-in-r2\`).
Acceptance for the merge: Q26 back to PASS; Q19, Q22, Q24 stay PASS; Q11 and Q23 stay open as findings
(corpus gaps to NEXT).

- 2026-11-20 - blind part 2: 5/8 (hash fbde54a7... committed alone in 2cfd92b; table in b025cf6). Revision
  after scoring written (R1-R5, Q11 / Q23 classification, re-check bound 4); no code yet.
