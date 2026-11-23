# Spec: Answer and citations

**Owner:** S2
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-002, ADR-003, ADR-012, ADR-020, ADR-021 in [DECISIONS.md](../docs/DECISIONS.md).

## Purpose

Turn retrieved chunks into a cited answer through the ADR-021 map-reduce flow (since #247, `MAP=on` by
default): one planner call, one extraction call per firm x aspect cell (#272; plus research) with a corrective
re-search, an evidence matrix built by code, then one reduce call that writes the answer from the
matrix (or an answer built by code with no call); calls follow the sub-question decomposition, with
no fixed number. Then check it in code: every citation resolves to the matrix, every number appears
in a cited chunk (or follows from cited same-basis inputs), caveats are inserted, gaps are named
with a source that would fill them, and the answer never crosses into "should". `MAP=off` keeps the
legacy single answer call (prompt v4.1, planner 1 + answer 1) for comparison only.

## Reference projects

- [bt4103-team8-sec-filing-assistant](https://github.com/niclow236/bt4103-team8-sec-filing-assistant): Pydantic answer templates, citation format.
- [Grounded-Rag-Analyst](https://github.com/Monesh76/Grounded-Rag-Analyst): citation validator, insufficient-evidence gate.
- [agentic-sec-rag](https://github.com/mr-j90/agentic-sec-rag): coverage note computed before the LLM call.
- [sec-edgar-rag](https://github.com/ankankisku-lab/sec-edgar-rag): numeric check.

## Interface draft (sketch)

```
answer(question, hits, query) -> Answer      # see Answer JSON in docs/ARCHITECTURE.md
    behavior in {"answer", "answer_with_boundary", "gap_with_adjacent", "refuse"}

validate(answer, hits) -> Answer
    for claim in claims + adjacent:
        unknown = claim.chunk_ids not in hits  -> claim.flag = "unmatched_citation"  # flag, never drop
        numbers in claim.text not found in cited chunk text -> claim.flag = "number_not_found"
    source_label built by code from documents (entity, doc_type, date, segment, tier label)
    date for an undated web page (date_basis = retrieved, ADR-007 T-09): "page content as of <date>" in
    source_label, coverage_note (own group) and the model's chunk source line, never "published"

insert_caveats(answer, hits, entities_config) -> Answer
    if any cited chunk is a substitute (e.g. BAC GWIM for MER, equivalence: partial):
        append entity.caveat to answer.caveats          # code, not prompt

coverage_note(query) -> "Corpus holds for MER: 12 BAC 10-K GWIM chunks (2019-2025), 0 transcripts..."

suggest_sources(query) -> [source]
    = expected sources in source_registry for the entity - sources actually ingested
```

## Behavior values

| Value | Meaning | Questions |
|---|---|---|
| `answer` | Normal answer, every claim cited. ADR-021 rule 1 (code from #246): any asked firm x aspect holds the asked quantity (or a same-basis derivation of it); every missing cell is a named gap | most, incl. Q4, Q26, Q27, Q31. Q24, Q25, Q28: bank `gap_with_adjacent`, superseded to `answer` (`evals/behavior_supersede.yaml`, ADR-021 rule 8); current code (prompt v4.1) may still choose `gap_with_adjacent` for them |
| `answer_with_boundary` | Evidence half, then an explicit hand-off of the normative part to the strategist | Q12, Q19 |
| `gap_with_adjacent` | "Not available / not disclosed" + adjacent data labeled as different + which source would fill it. ADR-021 (#246): no firm holds the asked quantity, a different related quantity exists; the answer also says the database does not support the asked quantity today | Q29, Q30, Q33, Q34, Q35 |
| `refuse` | Nothing in the corpus. ADR-021 (#246): also when no firm holds the asked quantity and no related quantity exists, with the gap "The database does not support this today: ..."; a request for the system's own forecast | Q32 |
| `incomplete` | Code-only (#247, ADR-021 #246 D5): no firm holds the asked quantity and an extraction failed; the answer says so plainly (`incomplete_note`), never `refuse`; no model schema offers it | none in the bank |

**Legacy path (prompt v4.1, `MAP=off` only).** The two paragraphs below describe the legacy single
answer call. ADR-021 rules 1 and 3 (after them) decide the behavior in the default flow since #247.

Partial or missing disclosure (prompt v3, #204): if the asked quantity is not disclosed for most
of the firms asked about, the behavior is `gap_with_adjacent` (answerable=false), with what is
disclosed reported as claims and each firm's missing disclosure as a gap. If the evidence covers
part of the asked population, cohort or period (a survey of an overlapping or narrower group,
some of the quarters), the behavior is `answer`: each finding with its source, sample and date as
printed, the group it covers, and the missing parts as gaps. A wider unit that contains the one
asked about (a parent company, a segment such as GWIM) is not partial evidence; it stays adjacent.
Disclosure questions (prompt v4, #215): a question about what firms disclose on a topic is answered
by the disclosures, but the behavior follows the specifics the topic is about (rates, formulas,
grids, amounts): not disclosed for most firms asked about -> `gap_with_adjacent`, the disclosures
as claims, each firm's undisclosed specifics as a gap naming the firm. Code does not derive the
behavior from per-part coverage (plans/0215: a coverage rule would not fire on Q25, would flip with
the planner's split, and would touch Q11 / Q23, NEXT item 5, which stays open).

**ADR-021 rules 1 and 3 (#246 / #247).** The map extraction call (extract-v1, #246) labels each firm x
aspect cell `fact`, `not_disclosed`, `not_found` or `different_quantity`; code aggregates the labels:
any `fact` (or a same-firm, same-basis derivation) -> `answer`, every other cell a named gap, an aspect
no firm holds gets "The database does not support this today: <aspect> (<firms>)."; no fact but a
`different_quantity` -> `gap_with_adjacent` (the same "does not support" statement, then the labelled
adjacent figure); neither -> `refuse`. A forecast request -> `refuse` first; a normative part ->
`answer_with_boundary` next. A partially covered asked quantity (some firms, quarters or a narrower
sample) is always a claim; adjacent is only for a different quantity or a wider unit.

## Definitions and comparability (ADR-021 rule 2, #246)

Source: `config/metric_definitions.yaml`. #246 adds per definition `period` (point in time, quarter or
year), `unit` and `basis` (a key naming the definition; equal keys = the same basis).

| Case | What the answer does |
|---|---|
| Within one firm (a ratio, sum, per-advisor value) | Computed only when the inputs share period or date, entity / segment scope and compatible units; the formula and both cited inputs shown; the number check (#247) holds the result to its inputs |
| Across firms, same `basis`, period and unit | Compared or computed |
| Across firms, different or unknown basis | Each firm's figure listed with its own definition; code inserts the comparability caveat (Standard wording); never ranked, combined or averaged |
| Metric not in the file (e.g. client assets) | Within-firm computation allowed with the "definition unverified" mark; never compared across firms |

## Map step and evidence matrix (#246; ADR-021 rules 1-3, 6, 7)

Plan: `plans/0246-map.md`. Code: `src/cee/answer/extract.py` (calls), `src/cee/answer/matrix.py`
(rules). **On by default since #247**: `ask()` builds and logs the matrix (`query_log.filters.map`),
and the reduce step (below) writes the answer from it. The eval maps unless `--legacy`.

- **Calls (map-reduce, map side).** Round 1 (#272): one structured extraction call per sub-question (firm x
  aspect cell, `map.<cell id>`), plus `map.research` for the research passages, in parallel
  (`MAP_CONCURRENCY`, default 24). The firm's call spec is built as before, then split per cell: a cell call
  lists the cell's own passages and, apart ("Also in this sub-question's search pool"), the firm's input
  passages in the cell's search pool that are listed under a sibling cell; the cell may cite exactly the set
  it could cite in the firm call (own | pool & firm input). A cell with nothing it may cite, like a firm with
  no passage, gets the code cell `not_found` ("no passages retrieved", flag `no_passages`), no call. A cell
  whose input is over `MAP_CALL_TOKENS` (default 60000) is split in input order into batches
  `map.<cell id>.b<n>`, merged per cell: items joined (a repeated citation dropped); label `fact` if any batch
  has one, else `different_quantity`, else `not_disclosed`, else `not_found`; a failed batch with no fact
  makes the cell `failed` (a failed batch next to a fact adds the flag `batch_failed`). The merged cells have
  the per-firm shape, so the matrix and the reduce input are unchanged. Prompt `extract-v1.2` (#272: the pool
  passages line; otherwise `extract-v1.1`).
  `extract-v1.1` (#247 added one rule-3 sentence: the asked quantity for periods other than
  those asked is a fact for the periods it covers, never `different_quantity`); tool `submit_extraction`, strict on anthropic / openai / deepseek (every property
  required, no extra properties, `""` for none, `minItems` only on Anthropic; DeepSeek strict mode
  supports the object / integer / enum types used, guide checked 2026-11-20).
- **Cell** (one per sub-question; research: one per aspect, `<aspect>.research`): `label` `fact` |
  `not_disclosed` | `not_found` | `different_quantity`; `items` (text, verbatim quote, chunk ids,
  value as printed, unit, period `YYYY-MM-DD` / `YYYYQn` / `FYYYYY` / `YYYY`, scope, definition);
  `differs_because`; `reason`; `derivation` (operation `ratio` / `sum` / `difference` and input items).
  Code labels: `derived` (an accepted derivation), `failed` (invalid output or failed call).
- **Proxy rule (one text, `extract.PROXY_RULE`, in the firm and research prompts).** A sub-question
  of a `proxy` aspect (plan-v3.1: the closest disclosed figure, a numerator or denominator) names a
  stand-in figure; that figure as the firm reports it is a fact; a different measure (all employees,
  full-time equivalents, compensation expense, client firms on a platform) is `different_quantity`.
  Code never lets a proxy aspect fire rule (a); its cells feed the adjacent side and may be derivation
  inputs.
- **Retrieved set of a cell** (code, after every call): the passages its sub-question kept, plus the
  chunks in its own candidate pool that a sibling sub-question of the same firm kept (a chunk is kept
  once, under its first sub-question), plus its re-search hits in round 2; research cells: the
  research passages. Answer turns enter a pool only after the exclude filter, so a sibling-kept answer
  turn cannot be cited by a later sub-question. A chunk id outside the set is rejected: removed from
  `chunk_ids`, kept in `rejected_ids`, flag `unmatched_citation`. A fact / different quantity with no
  cited item left reads `not_found`. Other flags: `quote_not_found`, `number_not_found` (the number
  check rules below), `period_unparsed`; a missing cell is `not_found` (`missing_cell`).
- **Invalid map outputs** (saved, never re-rolled; the cells become `failed`): no tool call; cut at
  the cap; Anthropic refusal; DeepSeek `finish_reason` other than `tool_calls` / `stop`; not JSON; not a
  valid extraction; no cells. JSON parsing (TL decision on #246 Q24; every DeepSeek / OpenAI argument
  parse, map, planner and answer, `llm.loads_object`): a complete object followed only by whitespace
  and stray `}` / `]` is accepted with the flag `trailing_braces`; any other trailing text is invalid;
  the object is still validated and checked in full. **Failed calls** (timeout, 5xx, connection, a 401 / 429 that is not
  DeepSeek's `ProviderStop`, a 400): the call's cells `failed`, the round goes on; the eval saves a
  counted `failed_call` record, reused and never called again; a 400 stops the eval run after the
  round. A `ProviderStop` stops the question; calls not started are cancelled.
- **Corrective re-search (CRAG)**: once per `not_found` sub-question (not for failed, research or
  comparison cells) through `planner.corrective_search`, every chunk already retrieved excluded, words
  widened by `extract.widen_words` (the firm's metric definition entry: quote, includes, the
  full-text search phrases in `looked_in`; adjacent quarters as words; the SQL window never widens).
  Round 2: one re-extraction per re-searched sub-question that found new chunks (`remap.<cell id>`, #272;
  batched like round 1), over only those chunks; final. A re-extraction's derivation can use only its own cells (its input
  holds no round-1 item), so derivations are proposed in round 1.
- **Behavior (rule 1), by code, first match wins**: a request for the system's own forecast ->
  `refuse`; a normative question (a modal with the home firm as subject, or "how should <x> shape
  <home firm>"; in the bank Q12 and Q19) -> `answer_with_boundary`; a cell that holds the asked quantity
  (`fact` or `derived`, not a comparison or proxy aspect, research included) -> `answer`; no fact and a
  failed extraction -> **undecided** (`behavior` None, `incomplete_note` "This answer is incomplete:
  ...", shown as incomplete, never as `refuse`, no "does not support" gap for that aspect; TL decision
  D5); a `different_quantity` cell or a proxy fact -> `gap_with_adjacent`; else `refuse`.
- **Derivation (rule 1d, rule 2 within-firm)**: the model proposes, code accepts only inputs that are
  cited fact items of the same firm with the same non-empty period and scope (the same unit for a sum
  or difference), no `number_not_found`, values that parse; code computes the value and the formula
  (`formula` with cell ids for the log, `formula_text` without ids for the answer, #247). Scopes are
  compared normalised (#247, `matrix.normalize_scope`: lower case, punctuation stripped, a leading
  "the" and a trailing "segment" / "business segment" / "reportable segment" / "business" / "division"
  removed: "Wealth Management segment" = "Wealth Management"; "Private Client Group" is not the whole
  firm). An unregistered metric's derived cell is flagged `definition_unverified`.
- **Comparability marks (rule 2)**, per aspect over the firms holding it: registered metric, same
  `basis` and `unit` -> `same_basis` (+ shared periods); different -> `different_basis` and the
  comparability caveat (Standard wording; each firm's definition = its entry's quote cut to 160
  characters and its chunk id; Merrill reads BAC's entry); unregistered metric with a figure on a
  **metric aspect** (kind `series`, a proxy, or one holding a derived cell; #247, TL D6) ->
  `unverified` and the unverified mark; qualitative, recency, comparison and plain fact aspects that
  happen to carry a figure -> none.
- **Uncovered asked periods (code, #247 B4; TL approval conditions)**: when the question itself asks
  for "last / past N quarters" (N in digits or words) the asked periods are the N most recent
  calendar quarters that ended before the as-of date; "last / past N years" -> the N most recent
  complete years (the unfinished current year never counts), matched by year; a time window (a
  publication-date filter) gives **no** asked periods (recency questions are judged by the why-line
  and newest-first rules); no stated range gives none. For series aspects and registered-metric fact
  aspects (never recency, comparison or proxy; research excluded), each holding cell whose items do
  not cover every asked period gets a code gap "<Firm> - <aspect>: not found for <2024Q4, 2025Q4> in
  the documents searched." (none covered: "... not found for the asked periods (<first>-<last>) in the
  documents searched; figures for other periods are listed."). Item periods map `YYYY-MM-DD` to its
  calendar quarter and `YYYYQn` as is; a `YYYY` or `FYYYYY` item covers no quarter (only a year). Config caveats of cited substitutes
  (GWIM) are added as by `insert_caveats`.

## Reduce step (#247; ADR-021 rules 0-5)

#275 (plans/0275-reduce-speed.md): **streamed claims, idle timeout, prompt v5.3.**
- The DeepSeek reduce streams; `reduce.StreamItems` parses the tool-argument deltas and returns each object of
  the top-level `claims` / `adjacent` arrays once complete. A claim is shown before the final answer only when
  `reduce.check_item` passes it: a one-item Answer (behavior `answer`, hits = the matrix's citable hits) through
  the why-line clean-up, `check_citations` (normative withheld, uncited cell moved to gaps, hand-off, numbers,
  dates), outside-matrix, rule 3 and the why-line check; shown only if it is still the one claim with the same
  text, nothing withheld, no gap, cited, and `flags == []`. Adjacent items are never shown early. Only at the
  end: cut / empty / not-JSON output, duplicates, newest-first order, comparison and computability claims,
  hand-off, part coverage, gaps, caveats, behavior. The mock streams its output through the same parser.
- `DEEPSEEK_IDLE_S` (default 120): a streamed call with no chunk (a delta, finish_reason or usage) for that long
  is aborted (watchdog; the streamed read timeout is the same plus 5 s) and fails with `llm.StreamIdle`; the
  eval saves it as a failed call with `partial`, `output_seen`, `ttft_s`; never retried automatically.
- Reduce effort `off` with streaming has a 64000-token cap (`ds-strict-2-reduce-off-c64000-s1`): the whole
  answer is output. `REDUCE_PROMPT` = `v5.2` | `v5.3`; v5.3 adds "state each fact once ... every cell that
  holds a fact keeps at least one claim of its own". The version and system text join the reduce cache key.

#277 (plans/0277-stop-retry.md): **Stop and Retry on the Ask page.**
- Cancel token (`cee.answer.cancel`): `ask(..., token=...)` makes it active in a context variable; every model call
  checks it first (planner, map, reduce, legacy answer, `llm.deepseek_create`), `ask()` checks it at each stage
  boundary and `run_map` before the re-search and round 2. `extract.run_round` runs each call in its own copy of
  the context, starts no call once it is set, cancels the queued ones (no wait for them) and lets running ones end;
  the DeepSeek stream watchdog closes an open stream when it is set. A stop raises `cancel.Cancelled`, a
  `BaseException`, so no generic error handler turns it into a failed call, a failed stage (the trace marks the
  running stage "stopped") or the planner's rule-plan fallback. Not cut: non-streamed requests and the wait for a
  stream's first byte; they end, are billed, and a valid output is kept. User-stop map records read
  `cancelled: stopped by the user` (`CallResult.cancelled`), apart from a ProviderStop's "cancelled after the
  provider stopped the run".
- Run cache (`cee.answer.runcache`, Ask page only, in the session): every call of a question's attempts with a
  status `ok | invalid | cut | failed | idle | cancelled | skipped | reused`. Only `ok` is ever served: a valid map
  extraction, a usable model plan, a reduce output that passed `finish_answer`. A valid output that lands after
  the stop is still `ok`. Keys as the eval's (no snapshot). The eval keeps its own never-re-call cache.
- Run log: with the cache, every attempt writes a `query_log` row. A finished one adds `filters.run` (attempt,
  retry_of, status `done`, reused / made counts by stage, status counts, records). A stopped or failed one writes
  `answer` NULL with `filters.run` (also `stage`, `reason` stop | page, `error`, `stop_s` from the click to the
  worker's end) and `filters.cost` of the calls it sent; a cut stream has no usage (`no_usage`, cost unknown).
- `MOCK_FAIL_FILE` (verify-cee only): while that file names `map` or `reduce`, the mock call of that stage fails.
  The mock map call k waits `MOCK_DELAY_S x min(k + 1, 3)` (evidence lands card by card); every mock wait is cut by
  a stop.

Plan: `plans/0247-reduce.md`. Code: `src/cee/answer/reduce.py`; prompt `prompt.SYSTEM_PROMPT_V5`
(`REDUCE_VERSION = "v5"`). One synthesis call writes the Answer from the evidence matrix only, for the
behavior code decided; it cannot change it.

- **Input** (`reduce_message`): the question, the decided behavior and its reason, the question's own
  time window (with "order newest first") or the Ask-page date filter (without), the firms in row
  order, the aspects (kind, metric, proxy = "adjacent only", comparison = "needs exactly one comparison
  claim", recency = "every item needs a why-line"), then aspect by aspect: the comparability mark, each
  firm's registered definition (context; citable only when its chunk is a matrix item), every cell
  (label in words; derived cells with `formula_text`, period, scope and input chunk ids; rejected
  derivations with code's reason) and every counting item (text, value, unit, period, scope,
  definition, quote, valid chunk ids; flags written as instructions). Then the code gaps and caveats
  ("do not repeat them") and one source line per citable chunk (no passage text). No raw passages.
- **Output**: the existing Answer schema, strict on every provider, with enums: `behavior` = the one
  decided value; `part_id` = every cell id, every aspect id (a claim that spans firms, e.g. the
  comparison claim) and `""`; `chunk_ids` items = `matrix.chunk_ids()` (valid cited ids only). Enum
  limits (OpenAI's numbers, applied to every provider; DeepSeek's guide states none): at most 1000
  values across the schema, and 15,000 characters for an enum over 250 values; over them a field falls
  back to a plain string (logged as `schema_fallback`) and the code check below is the guard.
- **Prompt v5 rules**: evidence only (no outside knowledge, no own computation, nothing about what a
  firm should do); claims dated from their source line and attributed; no ids in the text; a fact
  cell (also partial) is a claim stating what it covers and only the periods it has; "adjacent only"
  cells go in adjacent with `differs_because`; a derived cell is a claim with its formula citing both
  inputs; one comparison claim per comparison aspect (valid or not, and why; cross-firm comparison only
  at `same_basis` shared periods); a "Why it might matter: " sentence on every recency item (only what
  a cited source says, or "Why it might matter: the source does not say."); newest first with a window;
  the standard wording below.
- **Answers built by code, 0 calls** (`code_answer`): `refuse` (rule 1c: the matrix gaps with
  suggested sources); a forecast request (rule 1e: the gap `FORECAST_REFUSAL`); undecided (behavior
  `incomplete` with the `incomplete_note`, different-quantity cells as adjacent items, every matrix gap;
  never "does not support"); any matrix with an **empty citable set** (in practice a normative question
  with no fact: `answer_with_boundary`, `answerable` false, the hand-off sentence with no chunk ids, the
  matrix gaps, the `incomplete_note` when a cell failed). No reduce schema is built for an empty set.
- **Code after the call** (`finish_answer`, flags shown as chips, never dropped): the behavior set by
  code (a different model value logged as `model_behavior`; `withhold_normative` may still re-judge
  `answer` -> `answer_with_boundary`, logged `behavior_rejudged`); `check_citations` over the matrix's
  hits only, so an id outside the matrix is `unmatched_citation` + `outside_matrix`; the number check
  accepts a figure equal to an accepted derivation's value only when the claim cites all its input
  chunks (`computed`); rule 3: an adjacent item on a holding non-proxy cell -> `adjacent_is_fact`, a
  claim on a different-quantity or proxy cell -> `claim_from_adjacent`; rule 4: a comparison aspect
  with no cited claim (part id the aspect or one of its cells) gets the gap `COMPARISON_MISSING`
  (`comparison_missing`); rule 5: with the question's own window every item, else every recency item,
  without "Why it might matter: " + text -> `why_line_missing`; with the question's own window or a
  recency aspect, claims and adjacent items are re-sorted newest first by the latest published date of
  their cited documents (the hand-off last; `reordered` logged; an Ask-page date filter alone changes
  nothing); the matrix gaps placed after the model's (a model gap repeating one is merged into it,
  `model_also_named`); the matrix caveats, `insert_caveats`, `fill_suggested_sources`, `coverage_note`;
  `check_parts` with the matrix (a comparison part is covered by its aspect's comparison claim or the
  `COMPARISON_MISSING` gap; a proxy part by any item on its aspect, or by design when its cell holds
  nothing). Code-built answers go through the same checks.
- **Hits** (#247 B1): the passages an answer may cite are the retrieval hits plus the map step's
  corrective re-search hits (`Hit.origin = "corrective"`, no duplicates): the Ask page chips, the
  checks, the coverage note and `query_log.chunk_ids` use that union; `filters.chunk_origin` names each
  re-search chunk's sub-question. The eval's retrieval scoring keeps the retrieval hits only.
- **Invalid outputs** as the answer call's table below (no tool call, cut, refusal, a DeepSeek
  `finish_reason` other than `tool_calls` / `stop`, not JSON, not a valid Answer, empty); stray closing
  braces accepted with `trailing_braces`. No trim: an input over the provider's window minus the output
  cap is not sent (the stage fails). The eval caches each reduce call (`<Q>-reduce-<key>.json`; the key
  holds the version, the cap, the request version and sha256 of the v5 system prompt, the rendered
  input and the schema); invalid and failed calls are saved and never re-called; a 400 stops the run.
- `query_log.filters.reduce`: version, provider, model, `code_built`, `model_behavior`,
  `behavior_rejudged`, `outside_matrix`, `comparison_missing`, `why_line_missing`, `reordered`,
  `gaps_merged`, `part_gaps`, flags by name, `stop_reason`, `usage` (ADR-021 rule 7).

### Reduce part 4 (#247 part 4, post-call code; plans/0247-reduce-4.md)
- `LAST_REPORTED` (code caveat, after `SERIES_SPAN`): "{firm} - {metric}: latest count found in the {doc_words}:
  {date} ({chunk}); no count found in the {doc_words} read since ({docs})." One per firm row and registered
  metric whose registry entry has a counted `contrast.count_date`, when the question has an aspect of that metric.
  - Latest count: the latest dated item that counts the metric (unit names advisors / representatives, not
    employees, USD or client assets) in the firm's fact, derived or different-quantity cells of those aspects,
    or the registry `count_date` when its chunk was read; its document type T.
  - Old: before the first day of the first asked period ("last eight quarters"), else before the as-of date
    minus one year.
  - Later documents read: documents of type T with a chunk in the map's hits under one of the firm's
    sub-questions of that metric (not the candidate pools), dated (`period_end`, else `published_at`) after the
    latest count, none cited by a counting item. Both hold -> the caveat; the documents are listed, oldest first.
  - The same-document-type rule, not the age test, keeps an annual reporter out (Raymond James's 10-K count
    2025-09-30 is older than as-of minus one year, but no later 10-K was read).
  - It never says "discontinued", "last reported", "no longer" or "current": a stored count of another document
    type can be later (Merrill: `BAC-DECK-2025-investor-day#9`, ">15K"), and the map read passages, not whole
    documents. Doc-type words: supplement -> "quarterly financial supplements", 10-K / 10-Q -> "Form 10-K annual
    reports" / "Form 10-Q quarterly reports", deck -> "investor presentations".

### Reduce part 3 (#247 part 3, post-call code only; plans/0247-reduce-3.md)
- `DEFINITION_CONTRAST`: when an aspect with a registered metric asks for its definition (define / include /
  exclude) and the metric has `contrast_dimensions`, one caveat per dimension places every firm row, grouped by
  value, with the registry's verbatim text and chunk id (one block per metric; all-not-stated dimensions
  skipped). A row whose entry belongs to its parent names it ("Merrill (Bank of America Corporation)"), here
  and in `DEFINITIONS_BY_FIRM`. `DEFINITIONS_BY_FIRM` prints only verbatim text with the chunk that says it (the
  entry's quote; what a count includes / excludes from the entry's `contrast` cells) or fixed phrases ("not
  stated: <dimension labels>"); the registry's free-text includes / excludes / not_stated lists are not printed
  (tested: outside quotes only fixed words and firm names; every quote verbatim in its cited chunk).
- `closest_metric` wording: "defines a related metric instead" when the entry's unit equals the quoted
  entries' unit; otherwise "publishes no count of this metric; reports a related figure instead".
- Quarter holes: a "by quarter" series aspect with no asked range gets a `period_gap` per holding firm cell
  naming runs of at most 4 uncovered quarters with a covered quarter on both sides, only quarters another
  holding firm covers (`QUARTER_HOLES`). `SERIES_SPAN` reports the latest segment (split at runs of more than
  4 missing quarters) and names earlier points as a separate segment.
- Dedupe: bare and fiscal years are stated periods ("fiscal 2024" -> `fy2024`; "$2,024" is not a year).
- Gap sources: a gap on one firm's cell gets only that firm's `suggested_sources`; a firm reported inside a
  parent with nothing of its own missing gets the parent's list ("Not yet in the corpus (parent ...): ..."),
  also on the empty-retrieval path; aspect-level and research gaps keep the joined list.
- Basis breaks: an undated item never opens a group; parts of one count at the same (normalised) dates are a
  split, not a break (a scoped group within a whole-firm group of the same or no population key; with no
  whole-firm group, same-key groups with identical periods); groups of two keys never merge.

### Reduce part 2 (#247 part 2, prompt v5.2; plans/0247-reduce-2.md)
Revision after blind scoring (prompt v5.2; plan "Revision after scoring", R1-R6):
- Why-lines: the item's own stated context, or cited factual background from another matrix passage (the
  input lists up to 3 "related" items per recency / window item); "the source does not say" only when no
  passage gives either. Code replaces a restating why-line only when the claim cites no more than one
  item's chunks; model-written "does not say" lines are counted (`why_line_unsaid`).
- Populations: when no match phrase stands before the figure, the whole quote is read; a derivation over
  two registered populations is not "definition unverified".
- Basis breaks: an item without a population joins its scope's group; an undated one makes no basis.
- `COMPARISON_MISSING` is added once per aspect; a normative comparison aspect is covered by the hand-off; a
  model gap where the matrix holds the evidence is dropped (logged `gaps_contradicting`).
- Code caveats: `DEFINITIONS_BY_FIRM` (each firm's definition, includes / excludes / not stated, or that it
  publishes none; replaces the comparability caveat of that metric), `DEFINITION_CHANGED` (one firm's
  wording differs across documents), `SERIES_SPAN` (where each firm's series starts and stops); a
  different-quantity cell's gap names the closest disclosed figure.

First version (prompt v5.1):
- **Populations of ratio inputs** (rule 2): `matrix.tag_populations` gives each item of a ratio-input
  aspect (metric `client_assets` / `advisor_headcount`, or a proxy aspect matched by its words) the key
  of the `populations` entry whose phrase stands nearest before its figure (no phrase before it: the whole
  quote and the item text), only when the entry's chunk
  is in that cell's pool. `derive()` computes a ratio only on equal keys and exact figures ("about",
  "more than", ">", "+", "K" next to the figure refuse it), and records `populations` and
  `population_chunk_ids` on every proposal; those ids are citable (`EvidenceMatrix.chunk_ids()`).
- **Computation claims**: the reduce input shows a "computation (code)" line per proposal (computable
  or not, why, the inputs, each population source quoted, dated when an input falls in another quarter
  than the source's `valid_from`). One claim per firm must cite both inputs and the sources; missing ->
  code adds it before the citation check: `COMPUTED` / `NOT_COMPUTED` (standard wording), flag
  `code_computability`.
- **Basis breaks**: `matrix.basis_breaks` flags a holding cell of a series / registered-metric fact
  aspect whose items cover more than one (scope, population); the caveat `BASIS_BREAK` lists each basis
  with its periods and is inserted by code; the input tells the reduce to keep the bases apart.
- **Gap scope**: per-cell gaps only inside the aspect's planned firm subset (`asked_firms`); empty
  `competitor` cells fold into `COMPETITORS_GAP` per aspect; a model gap outside the scope is dropped,
  one on a folded cell merges into the fold; part coverage counts these cells as `out_of_scope` /
  `competitors_gap`.
- **Why-lines**: only on recency / window items; the input shows each such item's `context:` (the cited
  passage around its quote, up to 600 characters). Code removes a why-line elsewhere
  (`why_line_removed`) and replaces one that restates its claim (its figures and >= 80% of its content
  words already in the claim) with "Why it might matter: the source does not say."
  (`why_line_restated`); the model's sentences are in the log.
- **Duplicates**: after the part check, claims citing the same chunk set whose shorter text is held in
  the longer are removed (logged as `duplicates_removed`): outside quoted text, its figures and stated
  periods (dates, quarter labels) all in the longer, and >= 85% of its content words (PR #261 review: a
  quoted table row carries every period's figure, so quoted text is not compared); the comparison and
  computability checks run again.
- **Order**: with the question's own window the whole answer is sorted newest first; with recency
  aspects only, only their items move, inside their own slots.

## Answer shape (prompt v4, #215; v3 #204)

General rules in the prompt; no question ID, no `passes_if` text and no question text (a test
checks 6-word runs, lower case, punctuation stripped, against every `passes_if` and every question
text; the standard wording below is exempt from the `passes_if` check because the bank quotes it).
v4 reworded v3's recency example (it shared a run with a question's text).

The user message (prompt v4) lists the plan's parts (`p1 [firms]: text`, ADR-020) and groups the
evidence under the part it was found for, in hit order; research and peer passages follow under
their own headings. A part with no passages of its own says why, from its candidate pool before
exclusion (`plan.searched[i]["pool"]`): pool 0 "(no passages were found for this part)", else
"(no further passages; the passages found for this part are listed under another part or the
research passages)". No plan: one part p1, the whole question. The model writes `part_id` on
every claim, adjacent item and gap ("" when none applies). Since #245 (ADR-021 rule 6) every part is
one sub-question, `SubQuestion(entity, aspect)`: id `<aspect>.<firm>` (e.g. `a2.EDJ`; `a1.all` in
theme mode), text "<Firm>: <aspect>"; a competitor sub-question the floor across competitors
emptied (`floor_emptied`, Q19) reads as pool 0 ("no passages were found").

| Rule | When | What the answer does |
|---|---|---|
| Comparison grid | the question names two or more firms, or "each of" / "across" a set | Dimensions fixed from the question and its parts before reading the evidence (each dimension a part names, or each part when the parts are dimensions); an asked dimension is never dropped because the evidence is thin, none added only because the evidence offers it (v4; v3 also took dimensions from the evidence); the same list for every firm, every firm with a claim or a gap under every dimension (no dimension for one firm only); claims dimension by dimension (all firms for one dimension, then the next), each starting "<Dimension> - <Firm>:", each firm in its own terms; an empty cell is a gap "<Firm> - <dimension>: not found in the evidence provided." with a suggested source; never an inference, an adjacent figure or another firm's fact in a cell; an empty cell is only a gap, never a claim (v4). |
| Comparison claim (ADR-021 rule 4, prompt v5, #247) | a sub-question of `kind=comparison` | One cited claim answers the comparison itself (valid or not, and why), cited to its inputs; code checks it is present (else the `COMPARISON_MISSING` gap). |
| Why-it-might-matter line (ADR-021 rule 5, prompt v5, #247) | recency items; every item when the question has its own window | The claim ends "Why it might matter: <one sentence>" stating only what a cited source says or a checkable fact, or "the source does not say"; never our judgement (ground rule 6); code flags a missing one (`why_line_missing`). |
| Positions | where something is heading, the future, the range of views | Claims grouped by position (not by firm or source), each starting with the position, then who holds it and when; every claim attributed; two sources that disagree are reported as disagreeing; no forecast or synthesis of its own. |
| Parts | always | Every claim, adjacent item and gap carries the `part_id` of the plan part it answers; every part gets at least one cited claim or a gap naming what is missing for it; a part with no passages is a gap; a chunk listed under one part may be cited for another; within a part, what a question of its type needs (e.g. headwinds or risks the firm itself names) is covered (v4; v3 split the question itself). A question setting the home firm against a peer, or asking how it could act, shows the home firm's figures on the same dimension from its own filings. |

Time windows (prompt v4.1, #230): in a question about recent change or with a time window, claims
and adjacent items run newest first across the whole answer (by the date of what each reports),
not part by part; each keeps its `part_id`; gaps follow. The grouping of the evidence by part is
how it is listed, not the answer's order. When the resolved query has a window or an Ask page date
range (both SQL filters; their overlap when both are set), the user message adds one line after the
question: "Time window: <from> to <to> (only passages dated in it were searched). Order the answer
newest first across all parts."

The Ask page lists gaps under the claims, with code flags as chips. Answers can be longer: the
Anthropic output cap is 20000 tokens for every answer call (`llm.MAX_TOKENS`, ADR-019 amendment
#230; was 8000), under the SDK's non-streaming limit (21,333). Thinking, when the model runs it,
shares the cap.

## Invalid model outputs (code, #187, #230)

A paid output that cannot be trusted as an answer raises `ModelOutputError`; it is never shown,
scored or re-rolled. The eval saves it (`INVALID_OUTPUT`, the provider payload kept); the Ask page
shows "The answer could not be built" with the reason. Checked by `llm.check_output` on the model's
own output, before code adds part gaps or caveats, and again when the eval reuses a saved output:

| Output | Result |
|---|---|
| No `submit_answer` call, or a tool input that is not a valid Answer | invalid (#187) |
| Cut at the output cap (Anthropic `stop_reason` `max_tokens`, OpenAI `finish_reason` `length`), even when the partial input validates | invalid; every content block kept |
| No claims, no adjacent items and no gaps, unless behavior `refuse` with `answerable` false | invalid; the tool input as sent kept (a misnamed key shows) |
| API `stop_reason` `refusal` (Anthropic, #232), even with a tool input that validates | invalid; every content block kept. Not the model's own answer `behavior: refuse` with `answerable` false, which is a valid answer (row above) |
| DeepSeek (#242): `finish_reason` other than `tool_calls` / `stop` (`length` = cut, `content_filter`, `insufficient_system_resource`, `aborted`) | invalid; the whole message kept (content, `reasoning_content`, tool calls) |
| DeepSeek: tool arguments that are not JSON or not a JSON object (the API warns they may not be valid JSON) | invalid; the arguments string kept |

Every real answer records `stop_reason` and `usage` (input and output tokens; Anthropic also the
content block types, e.g. `thinking`, `tool_use`), code-owned fields of the Answer, so they reach
`query_log.answer` and the eval's saved outputs. A tool answer normally stops with `tool_use`. The
real clients are built with `max_retries=0` (TL, #230): a timeout or transport error is reported,
never a second paid request.

Strict tool input (#232): on Anthropic the `submit_answer` tool is sent with `strict: true` (the
planner's `submit_plan` too, ADR-020), so the API itself enforces `llm_output_schema()` on the tool
input (grammar-constrained); the schema already meets strict mode's rules (every object
`additionalProperties: false`, every property required, no array limits), checked offline by a test
and by the SDK's `anthropic.transform_schema`. `tool_choice` stays `auto` (claude-sonnet-5-5 rejects
forced tool choice), so a response without a tool call is still possible and stays invalid (first
row). The OpenAI request was already strict. The eval's cache keys carry the Anthropic request
version `strict-1` (`llm.request_version`); `PROMPT_VERSION` stays v4.1 (prompt text unchanged).
DeepSeek (#242) sends `submit_answer` and `submit_plan` as strict function tools (`strict: true`
on the `https://api.deepseek.com/beta` base URL), with an explicit `max_tokens`: answer 20000 /
planner 8000 with thinking off, 64000 / 64000 with thinking on (reasoning shares the cap; the planner
caps were 2000 off and 16000 on before #245). The map step's extraction calls (#246) use the answer
caps (`extract.extract_max_tokens`). Thinking off forces the
named function; thinking on uses `tool_choice` auto (a forced choice is a 400 there). A 401 / 402 /
429 stops the question with a plain message (`ProviderStop`), with no fallback and nothing saved.
Its request version (`ds-strict-1-think-{on|off}-a{cap}-p{cap}`) joins the eval's cache keys.
`usage` also records cache hit / miss and reasoning tokens.

## Every part answered or named as a gap (code, #215)

Ground rules 1, 3 and 6, enforced in `src/cee/answer/validate.py` after the model, never left to
the prompt. Behavior, claims and the model's own gaps are not changed.

- **Uncited grid cells** (`move_uncited_cells`, in `check_citations`): a claim with **no**
  `chunk_ids` whose text starts "<Dimension> - <Firm>:" (Firm = a configured name or alias) leaves
  `claims`. It becomes a gap "<Firm> - <Dimension>: no cited evidence in this answer." (true by
  construction: code knows only that no citation was given), flag `uncited_cell`, the model's text
  kept in `claim_text` (logged, not shown). When the model already wrote a gap starting
  "<Firm> - <Dimension>:", that gap keeps its own text and gets the flag and `claim_text`. A claim
  with citations, even unmatched ones, is never moved (flagged as before); any other uncited claim
  keeps `no_citation`.
- **Every part covered** (`check_parts`, in `ask.answer_for` after the citation check, when a plan
  is given): part P is covered by a claim or adjacent item with `part_id` P and a citation in the
  retrieved set, or by a gap with `part_id` P. Items with no or an unknown `part_id` (v3 outputs,
  the mock) count by citation: they cover the parts whose search found a passage they cite (in a
  one-part plan, every passage but research / peers; every gap). The hand-off sentence code adds
  covers no part by citation; in an `answer_with_boundary` answer it covers a part whose text is
  normative (e.g. "how could Edward Jones replicate ..."). An uncovered part gets a gap flagged
  `part_gap`, with the part's firms' suggested sources:

| Part's candidate pool before exclusion | Gap (`gaps[].what`) |
|---|---|
| 0 (its search found nothing) | "No evidence retrieved for: <part>" |
| > 0 (passages may sit under another part or research), or unknown | "Not answered from the evidence retrieved for: <part>" |

  `<part>` = the part text (+ " (<firms>)" when it repeats the question, as rule-plan parts do);
  a normative part text is printed as "part pN (<firms>)" instead (ground rule 6).
- `part_coverage()` gives each part's state (model / citation / handoff / code_gap) for the eval.
- Mock: its claims carry their passage's plan part, so the check runs on mock answers too: a
  two-firm mock answer whose top 3 passages are all one firm's gets a part gap for the other part,
  with the pool-chosen wording above.

## Standard wording

The prompt lives in `src/cee/answer/prompt.py` (`PROMPT_VERSION`), which holds these sentences
as constants. Keep the two in sync. Caveats remain code-owned; this wording does not replace them.

| Case | Questions | Gap (`gaps[].what`) | Adjacent `differs_because` |
|---|---|---|---|
| Merrill standalone results | Q30 | "Merrill does not report standalone results." | "GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's." |
| Advisor attrition (Q28, v4.1 legacy path only) | Q28 | "Neither firm discloses advisor attrition on a comparable basis." | "Net advisor headcount change is not attrition: it nets hires against departures." |
| Advisor attrition (Q28, v5, #247; Q28 superseded to `answer`) | Q28 | EDJ's disclosed rate is a claim with its period and definition; Merrill's cell gap is the matrix wording, e.g. "Merrill - <aspect>: not disclosed in the documents searched." | "Net advisor headcount change is not attrition: it nets hires against departures." |
| Forecast request (ADR-021 rule 1e, code, #247) | none in the bank | "This asks for a forecast of the engine's own; the engine reports only positions others hold, attributed and dated." | - |
| Comparison claim missing (ADR-021 rule 4, code, #247) | Q24 | "No cited claim answers the comparison asked: <aspect>." | - |
| Uncovered asked periods (code, #247 B4) | Q23 | "<Firm> - <aspect>: not found for <periods> in the documents searched." / "... not found for the asked periods (<first>-<last>) in the documents searched; figures for other periods are listed." | - |
| Why-it-might-matter (prompt v5, #247) | Q26 | Claim ending "Why it might matter: <sentence>" or "Why it might matter: the source does not say." | - |
| Database does not support it (ADR-021 rule 1, #247) | Q32-Q35; any aspect no firm holds | "The database does not support this today: <aspect> (<firms>)." | - |
| Comparability caveat (ADR-021 rule 2, code-inserted, #246 / #247) | Q11, Q22, Q23, Q24, Q31 | Caveat: "<Metric>: the firms define it differently (<firm>: <definition>; ...); figures are listed side by side and not compared or combined (reporting risk)." | - |
| Unregistered metric (ADR-021 rule 2, #246 / #247) | Q24 (client assets) | Mark: "<Metric> is not in the metric definitions file; its definition is unverified." | - |
| Map cell gaps (code, #246; #247 places them) | any firm x aspect cell that does not hold its quantity | "<Firm> - <aspect>: not disclosed in the documents searched." / "... not found in the documents searched." (+ " A second search with wider words found nothing new.") / "... not disclosed; a different quantity is listed as adjacent." / "... not extracted (the model output for this firm was invalid or the call failed)." | - |
| Incomplete (code, #246, TL decision D5; #247 shows it as a warning on any behavior, also a boundary answer) | no fact and a failed extraction | "This answer is incomplete: the evidence for <firms> could not be extracted (the model output was invalid or the call failed). Nothing is concluded about what <firms> disclose." | - |
| Advisor pay (decided per firm, prompt v2, #167; v3 #204) | Q25, Q29 | Firm with nothing published: "Payout grids are not public." (multi-firm answers name the firm first). Firm whose cited chunks publish payout ranges (RJF recruiting pages, #151): the ranges are claims dated "page content as of <date>", and the gap is "Headline payout ranges are published (company recruiting page, as of <date>); the full payout grid is not public." (multi-firm answers name the firm first, v3). Never "not public" for a firm whose evidence shows ranges. | "Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid." Trade press: "Trade-press reporting is indicative, not authoritative." |

Boundary hand-off (`answer_with_boundary`, Q12, Q19): the evidence half first, then this
sentence as the last claim:

> The evidence above only provides objective context for the strategic question asked.
> Whether or how Edward Jones should act is a judgment for the strategy team to make, beyond
> the scope of this evidence engine.

## Acceptance

- 100% of claims carry at least one `chunk_id` from the retrieved set, or are flagged.
- Q30: answer says Merrill does not report standalone results and the GWIM caveat appears
  (inserted by code; test with the prompt's caveat instruction removed).
- Q12, Q19: behavior `answer_with_boundary`, no sentence recommending action.
- Q28, Q29: adjacent data carries `differs_because`; a named `suggested_source` appears.
- Number check catches a planted wrong figure.
- Every answer includes a coverage note.
- Works with `LLM_PROVIDER=anthropic`, `LLM_PROVIDER=openai` and `LLM_PROVIDER=deepseek` (#242).

## Linked questions

Q12, Q19, Q24, Q25, Q28, Q29, Q30 (primary); Q11, Q23, Q26, Q31-Q35 (ADR-021); every question.

## Number check

`check_numbers()` in `src/cee/answer/validate.py` (#52) runs after the citation check. Every
number in a claim or adjacent item is compared with the numbers in the chunks that claim cites
(not other retrieved chunks). No match: the claim gets the flag `number_not_found`; it is never
dropped, and the app shows the flag next to the claim.

A claim figure matches a chunk figure when either:
1. it is within 0.1% of the chunk figure; or
2. it shows at least one decimal place and equals the chunk figure rounded half up to the
   claim's shown precision and scale.

| Claim | Cited chunk | Result | Why |
|---|---|---|---|
| 20,425 | 20,425 | match | equal |
| 30,020 | 30,000 | match | 0.07% apart |
| 20.4 thousand | 20,425 | match | one decimal, rounded |
| $1.2 billion | $1,234 million | match | one decimal, rounded |
| 2.9% | 2.88% | match | one decimal, rounded |
| $7.9 billion | 7,912 under "($ in millions)" | match | table unit header applied |
| nearly 21 | 21 million | match | a figure written without a unit may match the digits shown |
| $1,875 million | "$ 1,875" (table header in another chunk) | match | a figure with a unit may match the same digits written without one |
| $1 billion | $1.4 billion | `number_not_found` | no decimal, 29% apart |
| 20,000 | 20,425 | `number_not_found` | no decimal, 2% apart |
| 21% | 20.8% | `number_not_found` | no decimal, 1% apart |
| 21 thousand | 21 million | `number_not_found` | wrong unit |
| 21,000 (planted) | 20,425 | `number_not_found` | not in the chunk |

Scale words: thousand, k, million, mn, billion, bn, trillion. Not checked: years 1990-2099,
quarter and form labels (Q3, 3Q26, 10-K), section labels (Item 11, Note 4), dates (December 31,
12/31/2025), numbers written as words. Derived figures (sums, ratios, per-advisor values) are not in the chunk and are flagged.
ADR-021 rule 2 (#247, built): a computed figure is allowed only with all its cited inputs: a claim
figure that matches (the same two rules) the value of an accepted derivation whose input chunks the
claim all cites gets the flag `computed` instead of `number_not_found`; with an input missing, or for a
cross-firm figure (derivations are within one firm), it stays `number_not_found`.

Limits: a small figure with one decimal can pass rule 2 with a large relative error ("$0.1
billion" vs $0.14 billion). The check proves a figure is in the cited text, not that it came from
the right table column (MS-SUPP-2026Q3 p.8: a docling cell shift put 2.88% under the wrong
column); PDF source labels keep the page so the reader can open it.

## Date check

`check_dates()` in `src/cee/answer/validate.py` (#155) runs after the number check. A claim that
dates itself with a month and year is compared with the documents it cites; no match flags the
claim `date_mismatch` (flagged, never dropped, shown next to the claim). Found in the #61 real run:
Q29 called the MS 3Q26 release (`period_end` 2026-09-30) "the quarter ended September 2025".

| Claim says | Compared with | Result |
|---|---|---|
| "quarter / period / year / months / fiscal year ended <Month> [day,] YYYY", "as of <Month> [day,] YYYY" | a cited document's `period_end` or `published_at` (year and month) | no match: `date_mismatch` |
| "published [in/on] <Month> [day,] YYYY" | a cited document's `published_at` (year and month) | no match: `date_mismatch` |
| the same month and year in a cited chunk's text (a comparative column) | chunk text | match |
| several cited documents | any one matching is enough | |

Not checked: quarter shorthand ("3Q26", "fiscal 3Q25"), because fiscal and calendar quarters
differ (Raymond James's fiscal year ends in September); bare years; days of the month.

## Boundary

Ground rule 6 is enforced by code as well as by the prompt (#118). `withhold_normative()` and
`ensure_handoff()` in `src/cee/answer/validate.py` run at the start of `check_citations`.

- A claim or adjacent item that tells the home firm what to do is **withheld**: it is not shown;
  the Ask page shows "Withheld: A sentence was withheld because it recommended an action for
  Edward Jones (ground rule 6). That decision belongs to the strategy team." in its place. The
  claim is kept in `Answer.withheld` (and so in `query_log`) for review, never silently dropped.
  A shown recommendation, even flagged, has already reached the reader; that is why it is
  withheld rather than flagged.
- An answer with a withheld claim and behavior `answer` is re-judged `answer_with_boundary`.
- Every `answer_with_boundary` answer ends with the hand-off sentence; code adds it, citing the
  answer's chunks, when the model left it out.

| Withheld | Not withheld |
|---|---|
| "Edward Jones should build a similar channel" (EJ, EDJ, aliases, "the home firm"; should, ought to, would benefit from, might/may want to, could replicate/adopt/copy/emulate/consider/learn from/follow) | the hand-off sentence itself |
| "The home firm must / needs to ..." | "Edward Jones must maintain minimum net capital" (a filing duty) |
| "We / I (would) recommend / suggest / advise ..." | text in quotation marks: a firm's or analyst's own words |
| "It would be wise / advisable / prudent ..."; "It is recommended ..." | "we should expect" in a transcript ("we" / "you" are the speaker, not the home firm) |
| "recommend(s/ed) / suggest(s/ed) / advise(s/d) (that) Edward Jones ..." | "advisors recommend products suited to each client"; "should market conditions worsen" |

## Open questions

- Trade-press claims: allowed only as `adjacent` / labeled indicative? (Q29 suggests labeled)
- ~~How strict is the number check with rounding and units?~~ Settled in "Number check" (#52).
