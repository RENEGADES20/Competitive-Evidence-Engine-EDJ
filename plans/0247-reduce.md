# 0247 - Reduce step: synthesis prompt v5 over the evidence matrix, wired into ask and the app

Issue: #247    Role: TL    Spec: specs/answer-citations.md (also specs/ui.md for the Ask page and the
trace, specs/retrieval.md for nothing new; specs/filings.md untouched)

Owners (TL takeover, as #246): `src/cee/answer/*` and `specs/answer-citations.md` are S2's;
`src/cee/app/views/ask_page.py`, `design_page.py` and `specs/ui.md` are U1's; the rest TL.

Binding: ADR-021 rules 0-8 and its #246 amendment, CLAUDE.md ground rules and "Paid API calls". Builds
on #246 (merged, PR #256: `EvidenceMatrix`, `matrix.finish`, `extract.run_map`, the map cache) and #245
(sub-questions, `Plan.parts` = one part per sub-question). #248 (per-call cache for every call type,
cost table, app stage names, the scorer reading `evals/behavior_supersede.yaml`) builds on this.

## Goal
One **reduce** (synthesis) call writes the cited Answer from the evidence matrix only, for the behavior
code decided. `ask()`, `answer_for` and the app run plan -> sub-question search -> map -> corrective
re-search -> reduce -> validation by default (`MAP` flips to on). Code, not the prompt, enforces: the
behavior, citations only to matrix chunk ids, a comparison claim per comparison aspect (rule 4), a
why-line on every recency item (rule 5), newest-first order in window questions, adjacent only for
different quantities (rule 3), computed figures only from cited same-basis inputs (rule 2), and the
gaps and caveats. The interim answer input guard (#245) goes. The bar is the DeepSeek baseline
(`docs/results/w11-deepseek-baseline.md`, 15/30 like-for-like): Q11, Q19, Q23, Q24 and Q26 failed there
on shape, Q3 on a missing concession leg.

## TL approval conditions (issuecomment after review round 2; binding, written in before any code)
1. **Window rule**: a time window (a publication-date filter) gives **no asked periods**. Recency
   questions (Q26, Q27) are judged by the newest-first and why-line rules, never by period gaps.
2. **Years rule**: "last / past N years" counts **complete** years only (the unfinished current year
   never counts: at 2026-11-17, "past 3 years" = 2023, 2024, 2025), matched **by year**: any item whose
   period falls in that year (`YYYY-MM-DD`, `YYYYQn`, `YYYY`, `FYYYYY` by its year) covers it.
3. **Tests**: Q26-shaped (window, a 10-Q published in the window with an earlier period: no period
   gap), years-shaped (a year-end reporter with `YYYY-12-31` items: no Q1-Q3 gaps, no gap for the
   current year), Q23-shaped (unchanged: the named quarters). Word numbers parse ("eight").
4. **Round-2 notes adopted**: (a) the eval's `part_coverage` reads the union of hits (scoring fields
   stay retrieval-only); (b) code-built answers (refuse, undecided, empty citable set) go through the
   comparison check and the B3 part coverage too, so Q19's a13 gets no false part gap; (c) the
   `incomplete_note` also shows on an `answer_with_boundary` (and any behavior) as a warning box above
   the claims on the Ask page (`st.warning`), asserted in the B2 test; (d) in a "last N quarters" ask a
   `YYYY` item covers no quarter (only a years ask counts it).

## Industry terms used
Map-reduce (this issue = reduce), constrained decoding (strict tool schema with enums), grounded
generation over a structured context (the matrix, not raw passages), post-hoc attribution check.

## 1. What the reduce reads and writes

### 1a. Input: the matrix rendered (`reduce.reduce_message(question, matrix, window)`)
No raw passages: the reduce sees the matrix only, so its input is small (#246 matrices: 5-65 cells).
```
Question: <question>
Behavior (decided by code; write the answer for it): answer | answer_with_boundary | gap_with_adjacent
  Why: <behavior_reason>
Time window: <from> to <to> (only passages dated in it were searched). Order newest first.   # when set
Firms: Edward Jones (EDJ), Morgan Stanley (MS), ...                                            # row order

Aspects (part ids):
- a1 [fact]: <aspect text>
- a2 [fact, proxy: a stand-in, adjacent only]: <aspect text>
- a4 [comparison]: <aspect text>  -> needs one comparison claim, part_id a4
- a3 [recency] ...                -> every item needs a why-line

Evidence matrix, aspect by aspect (cell id = part_id):
Aspect a1: <aspect text>
  Comparability (code): different_basis | same_basis (shared periods 2026-06-30, ...) | unverified | none
  a1.EDJ  derived (computed by code): total client assets $2,647 billion / 20,514 financial advisors
          = about $129.0 million per financial advisor; period 2026-06-26; scope whole firm;
          definition unverified; cite EDJ-10Q-2026Q2#59, EDJ-10Q-2026Q2#60
  a1.RJF  not_disclosed; a ratio was proposed and rejected by code: scopes differ (whole firm vs
          Private Client Group)
  a1.MS   fact
    a1.MS#0 "<item text>" value 15,950 | unit Wealth Management representatives | period 2020-12-31 |
            scope Wealth Management | definition "<quoted>" | quote "<quote>" | cite MS-SUPP-2020Q4#1
            [flags shown in words, e.g. "figure not found in its passage: do not state it",
             "quote not verbatim: do not put it in quotation marks"]
  a1.SCHW different_quantity (adjacent only): differs because "<differs_because>"; items as above
  a1.MER  not_found (code gap below)
  ...
Research row: a1.research ... (when present)

Gaps added by code (do not repeat them): <gap id>: <what>
Caveats added by code (do not repeat them): <caveat>
(no incomplete note: an undecided matrix makes no reduce call, section 3)

Sources (every chunk id you may cite; cite no other):
<chunk id="EDJ-10Q-2026Q2#59" source="EDJ 10-Q, period 2026-06-26, published 2026-08-05, Item 2, p.31"/>
...
```
- Items show only their **valid** chunk ids (rejected ids are not rendered, handover #246 item 3).
- **Derived cells** (review note 2) are rendered with a user-facing formula: each input's aspect words
  and value as printed, the computed value from `derivation.value_text` with its unit, never the cell
  ids (`matrix.derive` keeps the id formula for the log; a new `derivation.formula_text` holds the
  user-facing one, built by code). The mock writes `formula_text`.
- **Rejected derivations** (review note 3) are rendered with code's `why` (e.g. "scopes differ: whole
  firm vs Private Client Group"), so the comparison claim has its reasons. Each aspect with a registered
  metric also lists each firm's registered definition (`metric_definitions.yaml` quote, cut to 160
  characters, its chunk id) as context. Those definition chunk ids are citable only when they are also
  matrix items (the enum); otherwise the definition reaches the answer through the code-inserted
  comparability caveat, not a claim. The prompt says so.
- **Uncovered periods** (B4): a cell's code gap naming the asked periods it does not cover (section
  6 item 4) is listed with the other code gaps; the reduce states only the periods its items have.
- The source lines are `llm._chunk`'s header without the text (dates, doc type, segment, page), so
  claims can be dated ("The 2Q26 10-Q (period ended June 26, 2026) states ...") without the passage.
- `number_not_found`, `quote_not_found` and `period_unparsed` flags are rendered as plain instructions on
  the item (the reduce must keep flagged figures out of its text; code checks it anyway, section 4).
- Proxy cells and `different_quantity` cells are marked "adjacent only" (rule 3).
- Comparability marks: only `same_basis`, `different_basis` and the metric-aspect `unverified` (section
  6 item 2) are printed; the caveat texts themselves are code-inserted.

### 1b. Output: the existing Answer schema, constrained (`reduce.reduce_schema(matrix, strict)`)
`llm_output_schema()` with three enums (strict on every provider, as #246; constrained decoding):
- `behavior`: `enum: [<matrix.behavior>]` (one value: the model cannot change it); `answerable` stays a
  boolean, code sets it from the behavior after the call.
- `part_id` (claims, adjacent, gaps): `enum` = every sub-question id, every research cell id, every
  aspect id (for a claim that spans firms: the comparison claim, a recency ordering note), and `""`.
- `chunk_ids.items`: `enum` = `matrix.chunk_ids()` (the valid cited ids; derivation inputs are among
  them). A citation outside the matrix cannot be generated on a strict provider; the code check
  (section 4) still runs for the mock, fakes and replays.
- **Enum limits** (review note 5): OpenAI structured outputs allow at most 1000 enum values across the
  whole schema and 15,000 characters in total for an enum with more than 250 values; duplicates count
  (`chunk_ids` appears twice: claims and adjacent; `part_id` three times). Q19 comes to about 576 values
  (chunk ids x 2 + part ids x 3 + behavior). DeepSeek's strict-mode guide and Anthropic's
  structured-output limits are re-read at build and their numbers written in the PR. The schema
  builder counts values and characters per provider; over a limit, that field falls back to a plain
  string on that path (D7), the code check is the guard there, and the run log says which field fell
  back. A Q19-sized schema test (65 sub-questions, 13 aspects, 200 chunk ids) checks the count and the
  fallback.
- **The enum is never empty** (B2): when `matrix.chunk_ids()` is empty no reduce call is made (section
  3), so no schema with `enum: []` is ever sent.

## 2. Prompt v5 (`prompt.REDUCE_VERSION = "v5"`, `prompt.SYSTEM_PROMPT_V5`)
v4.1 stays (`PROMPT_VERSION = "v4.1"`) for the legacy single-call path (`MAP=off`, section 5). The v5
system prompt draft (final wording at build, same rules; no question ID, no question text, no
`passes_if` text: the 6-word-run test covers it; the standard wording is exempt as today):
```
You write the answer to a question about wealth-management firms from an evidence matrix that code
built from stored documents. Code has already decided the behavior; write the answer for it. Prompt
version: v5.

Evidence only
- Every claim states what a cited item says, a figure code computed (a "derived" cell), or the
  comparison an aspect asks for. Cite only chunk ids listed under Sources; cite the ids of the items
  you use. Never use what you know from elsewhere; never estimate, convert, round or combine figures;
  never compute a figure yourself. Write nothing about what any firm should or could do.
- Date every claim from its source line ("The 2Q26 10-Q (period ended June 26, 2026) states ...",
  "On the 3Q26 earnings call (October 2026), management said ..."). Attribute strategy, priorities
  and intent to the firm or its management in their own words. Use each firm's own terms.
- Never write cell ids, aspect ids or part ids in the text.

What goes where (rule 3)
- A fact cell (in full or in part: some periods, a narrower group or sample) is a claim; say what it
  covers (period, scope, sample) when it is partial.
- A different_quantity cell and every cell marked "adjacent only" go in adjacent, never in claims, each
  with differs_because from the cell (in your words, the same meaning).
- A derived cell is a claim that states the computed figure with its formula as shown in the cell and
  cites both inputs; say the definition is unverified when the cell is marked so.
- State only the periods an item has. Code names the asked periods a firm does not cover (its gaps).
- Cells with code gaps get no claim; code adds their gap. Add a gap of your own only for something the
  code gaps do not name.

Comparison aspects (rule 4)
- For each aspect marked comparison, write exactly one claim with that aspect's part_id that answers
  the comparison itself: whether it can be made on the evidence (valid, valid only for some firms or
  periods, or not valid) and why, citing the items it rests on (definitions, the figures compared).
  Compare or rank figures across firms only when the aspect is marked same_basis, and only at its
  shared periods; otherwise say they are not comparable and why (different definitions, units,
  periods or scopes, unverified definitions, a ratio code rejected and its reason). A registered
  definition listed under an aspect is context: cite it only when its chunk id is under Sources.

Recency (rule 5) and order
- For every item in an aspect marked recency, and in any answer whose question has a time window, end the claim with
  "Why it might matter: " and one sentence stating only what a cited source says about it, or a fact a
  cited source states (a figure, a first, a change against an earlier period). If no cited source says
  why it matters, write "Why it might matter: the source does not say." Never your own judgement.
- With a time window, order claims and adjacent items newest first across the whole answer.
  (Code re-checks and enforces the order.)

Shape
- Several firms: aspect by aspect in the order listed, firms in the order listed, each claim starting
  "<Firm>: ". One firm: aspect by aspect.
- Positions about the future (others' views): group by position, attributed and dated; report
  disagreement as disagreement; no forecast of your own.
- answer_with_boundary: the evidence half only; code adds the hand-off sentence.
- gap_with_adjacent: no cell holds the asked quantity, so write no claim for it; give the adjacent
  items, each labelled with differs_because; the code gaps say what the database does not support.
Return the answer by calling the submit_answer tool.
```
- Standard wording kept and used verbatim where it applies (constants in `prompt.py`): GWIM / Merrill
  (`GWIM_DIFFERS`, `MERRILL_GAP`), advisor pay (`PAYOUT_GAP`, `PAYOUT_RANGES_PUBLISHED`,
  `COMPENSATION_DIFFERS`, `TRADE_PRESS_NOTE`), `HEADCOUNT_DIFFERS`. `ATTRITION_GAP` is **not** in v5
  (handover: the Q28 row; see section 8): Q28 is superseded to `answer`, its gaps are the matrix's
  per-firm cell gaps.
- The trade-press rule moves from "always adjacent" to the matrix label: a trade-press item is a fact
  when the map labelled it so; its claim says "trade press reports" (attributed); the `TRADE_PRESS_NOTE`
  stays for adjacent trade-press items. (Q26's items are RJF trade press.)

## 3. Which answers call the model, and which code builds (`reduce.answer_from_matrix`)
| Matrix behavior | Reduce call | Answer |
|---|---|---|
| `answer`, `answer_with_boundary`, `gap_with_adjacent` | **1 call** (mock: deterministic, 0) | the model's claims / adjacent / gaps + code checks (section 4) |
| `refuse` (rule 1c: no fact, no related quantity) | **0** | code-built: `answerable` false, no claims, the matrix gaps (incl. "The database does not support this today: ...") with suggested sources |
| `refuse` (rule 1e: a forecast request) | **0** | code-built: one gap, new standard wording `FORECAST_REFUSAL` = "This asks for a forecast of the engine's own; the engine reports only positions others hold, attributed and dated." |
| undecided (`None`, D5) | **0** | code-built: behavior **`incomplete`** (D2 below), the `incomplete_note`, the different-quantity cells as adjacent items (deterministic, as the mock), every matrix gap; never `refuse`, never "does not support" |
| any behavior with an **empty citable set** (`matrix.chunk_ids() == []`, B2) | **0** | code-built. In practice only rule 1e reaches it (a normative question whose cells are all `not_found` / `failed`; 1a and 1b imply a cited item). Behavior `answer_with_boundary`, `answerable` false; no evidence claim; the hand-off sentence as the last claim with no chunk ids (the citation check exempts exactly `BOUNDARY_HANDOFF` from `no_citation`, since it is standard wording, not evidence); every matrix gap, including "The database does not support this today: ..." where it applies; and the `incomplete_note` when any cell failed. `matrix.decide_behavior` now also sets `incomplete_note` under rule 1e when a cell failed (today it does not), so the failure is shown. Never an empty `chunk_ids` enum. |
| no hits (empty retrieval) | 0 | unchanged: `validate.empty_retrieval_answer` |

## 4. Code after the reduce call (`reduce.finish_answer`, then the existing checks)
In this order, all flags shown as chips on the Ask page (never dropped silently):
1. **Behavior** set by code: `answer.behavior = matrix.behavior`, `answerable` = behavior in (`answer`,
   `answer_with_boundary`); a model value that differs (only possible off the strict schema) is logged
   as `model_behavior`. `withhold_normative` may still re-judge `answer` -> `answer_with_boundary`
   (existing ground-rule-6 code, unchanged).
2. **Matrix-only citations** (`check_matrix_citations`): `check_citations` runs over the hits of
   `matrix.chunk_ids()` only (not every retrieved passage), so an id outside the matrix is
   `unmatched_citation` plus the new flag `outside_matrix`. `EvidenceMatrix.hits` (new, not logged:
   every `Hit` the matrix may cite, re-search hits included) gives the passages for the number and date
   checks and source labels.
3. **Number check with computed figures** (rule 2, issue "Validation"): `check_numbers(answer, hits,
   derived=...)` also accepts a claim figure that equals (same match rule) an accepted derivation's
   value whose `input_chunk_ids` are all cited by that claim; such a claim gets the info flag
   `computed`. A computed figure without both inputs cited stays `number_not_found`. Cross-firm
   computations are never accepted (derivations are within-firm by construction).
4. **Rule 3 placement** (`check_adjacent`): an adjacent item whose `part_id` is a holding cell of a
   non-proxy aspect gets `adjacent_is_fact` (a partially covered asked quantity must be a claim); a
   claim whose `part_id` is a `different_quantity` cell or a proxy cell gets `claim_from_adjacent`.
5. **Comparison claim** (rule 4, `check_comparisons`): each `kind=comparison` aspect needs at least one
   claim with `part_id` = the aspect id or one of its sub-question ids that cites a matrix chunk. Missing:
   code adds the gap `COMPARISON_MISSING` = "No cited claim answers the comparison asked: <aspect>."
   flagged `comparison_missing`, with the aspect id as `part_id`.
6. **Why-lines** (rule 5, `check_why_lines`): only for the **question's own** time window
   (`query.window`, not the Ask-page date filter; review note 4) or a recency aspect: every claim and
   adjacent item of a recency aspect (or every item, when the question has its own window) must contain
   "Why it might matter: " followed by text; missing -> flag `why_line_missing`. The why sentence is
   covered by the claim's citations, the number check and `withhold_normative` like the rest.
7. **Newest first** (`order_newest_first`, D4): only when the question has its own window or a recency
   aspect (an Ask-page date filter alone keeps the aspect-by-firm shape; stated in specs/ui.md), claims
   and adjacent items are re-sorted by code, newest first by the latest **published** date of their
   cited documents (the date the window filters on; review note 4), stable for ties; the hand-off
   sentence stays last; `reordered` (count) is logged.
8. **Gaps and caveats**: the matrix gaps (`matrix.gaps`, standard wording, `part_id` = cell or aspect
   id, `suggested_source` from the matrix; uncovered-period gaps included, B4) are appended by code
   after the model's gaps. **Duplicates** (review note 9): a model gap whose normalised text (lower case,
   whitespace collapsed, final period dropped) equals a code gap's, or that starts with the same
   "<Firm> - <aspect>:" head for the same part id, is not added twice: the code gap is kept and gets the
   flag `model_also_named`, the model's text kept in its `claim_text` (logged, not shown). Then the
   matrix caveats (comparability, GWIM), `insert_caveats` over the cited hits, `fill_suggested_sources`,
   `coverage_note`.
   **Part coverage** (B3; `check_parts` / `part_coverage` gain a matrix-aware rule, used only with a
   matrix): a sub-question of a **comparison** aspect is covered by any claim whose `part_id` is the
   aspect id or one of the aspect's sub-question ids and that cites a matrix chunk, or by the
   `COMPARISON_MISSING` gap of that aspect (state `comparison`); a sub-question of a **proxy** aspect is
   covered by any adjacent item (or claim) on that aspect, or, when its cell holds nothing, counts as
   covered by design (the asked aspect carries the gap; state `proxy_by_design`). Every other part keeps
   the existing rule, and the matrix gaps cover non-holding cells, so a remaining `part_gap` means the
   reduce skipped a holding cell.
9. `llm.check_output` (cut at the cap, empty output) runs on the model's own output before 1-8, as
   today; invalid outputs raise `ModelOutputError` (section 5).

## 5. Wiring: `ask()`, `answer_for`, the app, the mock
- **The hits of an answer are retrieval + corrective re-search** (B1). `run_map` returns the
  re-search hits on `EvidenceMatrix.hits`; `ask()` sets `Result.hits` = the retrieval hits, then each
  re-search hit not already there, in order, no duplicates. Each re-search `Hit` keeps its
  sub-question's `part_id` and gets `origin = "corrective"` (new optional `Hit` field, default
  `"search"`). Every reader uses that union: the Ask page's citation chips and source links
  (`ask_page.show_answer`), `_check_text`, `coverage_note`, `insert_caveats`, the reduce's checks and
  `query_log.chunk_ids` (the union, retrieval first); `log_filters.chunk_origin` maps each re-search
  chunk id to `"corrective"` (with its sub-question), so the log says where each came from. This keeps
  the invariant "citations point only at chunk ids in the retrieved set": the retrieved set is the
  union. **The eval's retrieval scoring** (recall, statuses, forbidden, `must_not_return`) keeps the
  retrieval hits only, so the mock 35 check against main stays like for like; the record adds
  `corrective_chunk_ids`.
- **`MAP` default flips to on** (`Settings.map_on = True`, `.env.example` `MAP=on`, comment updated).
  **Existing `.env` files are never touched** (review note 1): `.env.example` on main says `MAP=off`,
  and `load_dotenv` does not override, so a teammate's copied `.env` keeps the map off. The verify
  driver sets `MAP=on` in the app's environment, the eval maps unless `--legacy` (section 7) and prints
  `MAP` in its run meta, `docs/RUN.md` (Windows and Mac blocks) tells users to delete the `MAP=off` line
  from their own `.env` or set `MAP=on`, and the PR body says so for the TL to pass on.
  `MAP=off` keeps the **legacy** path (plan -> search -> one v4.1 answer call) for comparison only
  (D3), without the input guard: an input over the provider's window is reported by the provider (a
  failed stage), never trimmed.
- **`ask()`**: resolve -> plan -> search -> map (stage `map`) -> reduce (stage `model`, text "Asking the
  model to write the answer from the evidence matrix (<provider>, one call)"; mock "(mock, one call)";
  code-built answers: "No model call: the answer is built by code (<behavior or incomplete>)") -> check
  -> caveats -> log. `STAGES` unchanged (8; #248 renames them). `Result.matrix` always set when there
  are hits and `MAP=on`.
- **`answer_for(question, query, hits, provider, raw=None, trace=None, plan=None, matrix=None)`**: with
  a matrix: the reduce path (`raw` = a saved reduce output for the eval's reuse); without: the legacy
  path; no hits: the empty-retrieval answer (no map, no reduce, as today).
- **Interim guard removed** (handover, #245 D5): `llm.answer_input_limit`, `GUARD_ROUND`,
  `validate.fit_input`, `GUARD_NOTE`, `ask.guard_input`, `Result.input_guard`, `log_filters.input_guard`,
  `Settings.answer_input_max_tokens`, `ANSWER_INPUT_MAX_TOKENS` in `.env.example`, the eval's
  `interim_input` / `input_guard` record fields, `guard_provider` / `answer_input_limit` run meta and the
  guard part of `cache_key` (keys made without a trim are unchanged; none of the cached answers was
  trimmed). `llm.CONTEXT_WINDOW` stays (the map's per-call input check uses it; the reduce gets the
  same no-trim pre-check: an input over window - cap is not sent and the stage fails with "input over
  the model's limit"). `tests/test_input_guard.py` is deleted with the guard (its cases no longer apply);
  the spec section "Interim answer input guard" is removed.
- **`log_filters`**: `map` = `matrix.to_log()`; new `reduce` = {version, provider, model, code_built
  (bool), model_behavior, behavior_rejudged (withhold_normative), reordered, flags count by name,
  outside_matrix count, `stop_reason`, `usage` (ADR-021 rule 7; review note 11; also in the logged
  Answer dump)}; `chunk_origin` (B1); `llm_calls.answer` = 1 for a real reduce call, 0 for mock /
  code-built.
- **App (`src/cee/app/views/ask_page.py`, `design_page.py`, specs/ui.md)**: `BEHAVIOR_TEXT` /
  `BEHAVIOR_HELP` gain `incomplete` ("Incomplete" / the `incomplete_note`), and the design page shows
  the `incomplete` header next to the other four (review note 7); the answer otherwise renders as today (claims,
  adjacent, gaps, caveats, flags as chips). The new flags get chip labels: `outside_matrix` "cited
  outside the evidence matrix", `computed` "computed by code from cited inputs", `why_line_missing`,
  `adjacent_is_fact`, `claim_from_adjacent`, `comparison_missing`.
- **Schema**: `Behavior` gains `incomplete` for code-built answers only; `llm_output_schema()` lists the
  four model behaviors explicitly (not `get_args(Behavior)`), so no model schema offers `incomplete`;
  `Answer.incomplete_note: str = ""` (code-owned).
- **Mock reduce** (`reduce.mock_reduce(matrix)`, 0 calls, honours `MOCK_DELAY_S`; also the code-built
  renderer for undecided): per aspect in plan order, per row: a holding fact cell -> one claim from its
  first counting item (`text`, its chunk ids, `part_id` = cell id); a derived cell -> one claim
  "<Firm>: <aspect>: <formula>." citing the inputs; a different_quantity or proxy cell -> one adjacent
  item with `differs_because` (cell text, else "a different quantity"); a derived cell's claim uses
  `formula_text` (no ids); a comparison aspect -> one claim
  "<aspect>: compared only on the same basis; code marks it <status>." citing the chunk ids of that
  aspect's holding cells, else none (the code gap then fires); recency items end "Why it might matter:
  the source does not say."; behavior = the matrix's. It proves the wiring and every code check, not
  answer quality (CLAUDE.md).

## 6. Handover items owned here (issue comments)
1. **Stale "20000 / 2000" wording**: the spec text was corrected by #246; the stale phrase remains in
   the `llm.py` comment above `DEEPSEEK_MAX_TOKENS` ("off keeps the project's 20000 / 2000"): fixed to
   "off: answer 20000, planner 8000 (#245; was 2000)". Grep for the phrase over `src specs docs` (not
   results) returns nothing after the fix.
2. **Interim `ANSWER_INPUT_MAX_TOKENS` guard removed**: section 5.
3. **Old Q28 standard-wording row** (`specs/answer-citations.md`): relabelled "Advisor attrition (Q28,
   v4.1 legacy only)"; a new row "Advisor attrition (Q28, v5)": EDJ's disclosed rate is a claim with its
   period and definition; Merrill's cell gap is the matrix wording ("Merrill - <aspect>: not disclosed in
   the documents searched."); net headcount change stays adjacent with `HEADCOUNT_DIFFERS`. ADR-021's
   bank-audit row for Q28 names Merrill's 26% attrition reduction (`BAC-DECK-2025-investor-day#34`) as
   the adjacent figure (the chunk is read in the database at build before the text is written; if it
   does not say that, the row says what it says).
4. **Q23 MS-2020 labelled partial coverage, not `different_quantity`** (ADR-021 rule 3; the #246
   finding: a figure of the asked quantity for other periods): fixed at the source, **extract-v1.1**
   (`EXTRACT_VERSION`), one sentence added to the `fact` label: "The asked quantity for periods other
   than those asked (older or later) is also a fact, for the periods it covers: the item's period says
   which; it is never different_quantity." and to `different_quantity`: "A different period of the
   asked quantity is not a different quantity." (TL D1: re-map accepted under the cap.) The reduce
   writes it as a claim stating only the periods it has. **Code names the uncovered periods** (B4,
   option b; `matrix.period_gaps`, part of `build_gaps`):
   - **Asked periods** (`matrix.asked_periods(question, as_of)`, deterministic): "last / past N
     quarters" in the question (N a digit or a word) -> the N most recent calendar quarters ending before
     `as_of` (Q23 at 2026-11-17: 2024Q4-2026Q3); "last / past N years" -> the N most recent complete
     years, matched by year (approval condition 2); a time window gives **none** (condition 1); else
     none (e.g. Q22 "by quarter" names no range: no period gap, the reduce lists what each firm has).
   - **Applies to** aspects of kind `series`, and `fact` aspects with a registered metric, when asked
     periods exist; not to recency, comparison or proxy aspects.
   - **Per holding cell** (fact / derived, research excluded): its counting items' periods mapped to
     calendar quarters (`YYYY-MM-DD` -> its quarter, `YYYYQn` as is; `YYYY`, `FYYYYY` and unparsed
     periods cover no quarter, condition 4d), or, for a years ask, to years. Uncovered =
     asked - covered. When non-empty, a code gap "<Firm> - <aspect>: not found for <2024Q4, 2025Q4,
     2026Q3> in the documents searched." (all asked periods uncovered: "not found for the asked periods
     (2024Q4-2026Q3) in the documents searched; figures for other periods are listed."), label
     `period_gap`, the cell id as part id, the firm's suggested source.
   - `run_map` passes `as_of` to `matrix.finish`. Expected on the 0-call re-check (step 1, Q23 with
     extract-v1): EDJ 2024Q4, 2025Q4, 2026Q3 uncovered; RJF every asked quarter but 2025Q3.
   - Tests: a Q23-shaped matrix (EDJ partial, MS 2020 only, a fiscal-year item) gives exactly the named
     gaps; a Q22-shaped question gives none; a recency aspect gives none.
5. **Unverified mark only on metric aspects** (`matrix.mark_comparability`): `unverified` only when the
   aspect is a metric aspect: kind `series`, or a proxy, or it holds a `derived` cell (a registered
   metric gets `same_basis` / `different_basis` instead). Recency, comparison and plain `fact` aspects
   whose items happen to carry a figure get `none`. Expected on the 0-call re-check of #246's records:
   Q19 a1 / a5 / a11 and Q26 a1, a2, a4-a6 lose the mark; Q24 a1 (derived) and a2 (proxy) keep it, a4
   (comparison) loses it.
6. **Cite only matrix ids**: schema enum (section 1b) + code check (section 4.2) + rendering only valid
   ids (section 1a). Test: a fake reduce output citing a retrieved-but-not-matrix chunk, a rejected id
   and an invented id: each flagged `outside_matrix` + `unmatched_citation`, none dropped.
7. **A 400 stops after the round, via `allow()`**: `RealRunner.map.allow` returns a skip reason once
   `self.bad_request` is set, so after a 400 in round 1 the round's other calls finish, the corrective
   re-search (database only) may run, but **no round-2 call is made** and no reduce call follows; the run
   then stops with every record saved (today it stops only after the question's whole map step).
   `extract.run_round`'s `allow` may return `True` or a reason string; a string is the skipped call's
   `error` ("not run: --max-calls reached" or "not run: the run stopped after a 400"). A 400 on the
   reduce call: saved as a counted `failed_call` record, the run stops. **Test** (missing in #246): fake
   calls, one round-1 call raising a 400-status error, a re-search that finds new chunks: zero round-2
   calls, the record saved with `bad_request`, `SystemExit` with the stop message, no reduce call.
8. **Planner `loads_object` flags**: the eval's planner re-check path (`RealRunner.plan`, a saved invalid
   plan re-parsed with stray closing braces) passes a `flags` list; the record gets `plan_parse_flags`
   and `plan_origin` names `trailing_braces`. Test.
9. **Scope labels normalised** (`matrix.normalize_scope`, used by `derive` wherever scopes are
   compared): lower case, whitespace collapsed, punctuation stripped, a leading "the" and a trailing
   "segment", "business segment", "reportable segment", "business" or "division" removed. "Wealth
   Management segment" == "Wealth Management"; "Private Client Group" != "" (whole firm) stays a real
   difference. Expected on the re-check: Q24 MS ratio accepted (derived), RJF still rejected.
10. Cost report rates (PR #256 note 3, #248 owns the cost table): `0247-reduce-check.md` states the
   per-1M token rates it used and their source.

## 7. `scripts/eval_run.py`
- **The eval maps unless `--legacy`** (review note 1; it does not follow `MAP`, so a teammate's old
  `.env` cannot turn it off): with `--real`, plan -> search -> map -> reduce (cached); `--map-only`
  unchanged (no reduce); `--legacy` (new) runs the v4.1 single answer call with no map; `--map` stays
  accepted (a no-op, so #246's commands still run). The run meta prints `map` and the `MAP` setting
  seen. Mock runs build the matrix and the mock reduce (0 calls) for every searched question.
- **Reduce cache** (`reduce_cache_key`): question id and text, `REDUCE_VERSION`, snapshot, provider,
  model, the reduce cap (`llm.answer_max_tokens`), `llm.request_version`, a sha256 of the v5 system
  prompt text (review note 6: a wording edit without a version bump never reuses an output), a sha256 of the rendered
  reduce user message (it carries the behavior, the window, every cell, mark, gap and source line, so
  any change to the matrix makes a new key) and of the schema (its enums). File
  `<Q>-reduce-<key>.json` in the cache, copied to the run's `raw/`. Saved record: meta, `stop_reason`,
  `usage`, timing, DeepSeek `reasoning_content`, `raw` (the tool input) or `invalid: true, error,
  raw_payload`; a failed call `invalid: true, failed_call: true, error, bad_request`.
- **Reuse**: a saved valid record goes through `check_output` and every code check (section 4) like a
  new one; a saved invalid one is `INVALID_OUTPUT` (with the #246 stray-brace re-parse, flagged); a
  failed one is reported; none is ever called again. Code-built answers make no call and write no file.
- **Call cap**: the reduce call is reserved like a map call (`self.calls`), counted as made when sent;
  over the cap -> `NOT_EVALUATED` "not run: --max-calls reached", no file.
- **Records** gain: `reduce` (version, code_built, model_behavior, behavior_rejudged, flags by name,
  outside_matrix, reordered, comparison claims found / missing, why-lines missing, part gaps on
  comparison / proxy parts), `behavior` = the answer's (the matrix behavior, or `answer_with_boundary`
  when `withhold_normative` re-judged an `answer`, review note 8: recorded, never an error),
  `map_behavior`, `expected_behavior_effective`, `part_coverage`, `corrective_chunk_ids` (B1). `report.md`: one line per
  question: behavior vs effective expected, claims / adjacent / gaps, flags, calls by type.
- The 400 and planner-flag items: section 6 items 7, 8.

## 8. Specs, ADR, docs
- `specs/answer-citations.md`: Purpose and Behavior table (current code = map-reduce); a "Reduce step
  (#247)" section (input, schema enums, prompt v5 rules, code-built answers, the post-call checks and
  flags, the eval cache); Standard wording rows: Q28 (handover 3), `FORECAST_REFUSAL`,
  `COMPARISON_MISSING`, the why-line form, `incomplete`; the number-check section: computed figures
  (rule 2); the map section: "off by default" removed, extract-v1.1 sentence, scope normalisation, the
  unverified-mark rule; the interim-guard section removed.
- `specs/ui.md`: the `incomplete` header, the new chips, the model-stage line.
- `docs/DECISIONS.md`: **ADR-021 amendment (#247)**: code-built answers for refuse and undecided (0
  calls), the `incomplete` behavior value (code-only), the reduce schema enums, part ids, why-line form,
  code ordering newest first, the rule-3 flags, extract-v1.1, the unverified-mark rule, scope
  normalisation, `MAP` default on with `MAP=off` legacy, the guard removed, the Q28 bank-audit adjacent
  figure. **ADR text, so the PR is escalated to the TL for the merge.**
- `docs/ARCHITECTURE.md` (flow box), `docs/RUN.md` (the real check, Windows and Mac blocks), README
  only if it describes the answer flow (de-identified, as now).
- `.claude/skills/verify-cee/features/ask-progress.md`, `ask-answer.md`; `scripts/verify_cee.py`
  (section 10).

## Files to change
- `src/cee/answer/reduce.py` (new) - `REDUCE_VERSION` import, `reduce_message`, `reduce_schema`,
  requests for anthropic / openai / deepseek, `call_reduce` (invalid outputs as `llm._deepseek`
  etc., reusing `deepseek_tool_request`, `deepseek_create`, `deepseek_tool_call`, `loads_object`,
  `check_output`), `mock_reduce`, `code_answer` (refuse / forecast / incomplete), `finish_answer` and the
  checks of section 4.
- `src/cee/answer/prompt.py` - `REDUCE_VERSION`, `SYSTEM_PROMPT_V5`, `FORECAST_REFUSAL`,
  `COMPARISON_MISSING`, `WHY_LINE` prefix; v4.1 unchanged.
- `src/cee/answer/schema.py` - `incomplete` behavior (code-only), explicit model enum,
  `incomplete_note`.
- `src/cee/answer/validate.py` - `check_numbers(..., derived=)` and the `computed` flag; guard removed.
- `src/cee/answer/llm.py` - guard removed; the stale comment; a small shared helper for the three
  providers' tool-call parsing only if `reduce.py` would otherwise copy it (rename-free addition).
- `src/cee/answer/matrix.py` - `normalize_scope`, the unverified rule, `EvidenceMatrix.hits`,
  `derivation.formula_text`, `asked_periods` / `period_gaps` (B4), `incomplete_note` under rule 1e (B2),
  `finish(as_of=)`.
- `src/cee/retrieve/fts.py` - optional `Hit.origin` (default `"search"`; B1). S1's file: one field.
- `src/cee/answer/validate.py` (also) - the matrix-aware part coverage (B3), the hand-off exempt from
  `no_citation` (B2), the gap dedupe (note 9).
- `src/cee/app/views/design_page.py` - the `incomplete` header (note 7).
- `src/cee/answer/extract.py` - `extract-v1.1` sentences; `run_map` fills `m.hits`; `run_round` skip
  reason from `allow`.
- `src/cee/ask.py` - flow, stage texts, `answer_for(matrix=)`, guard removed, `log_filters.reduce`.
- `src/cee/config.py`, `.env.example` - `MAP` default on; `ANSWER_INPUT_MAX_TOKENS` removed.
- `src/cee/app/views/ask_page.py` - `incomplete` header and note; chip labels.
- `scripts/eval_run.py` - section 7, handover 7 and 8, guard fields removed.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md`, `ask-answer.md`.
- Tests: new `tests/test_reduce.py`; edits `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`
  (if the line texts are asserted), `tests/test_eval_run.py`, `tests/test_matrix.py`,
  `tests/test_extract.py`, `tests/test_validate.py`, `tests/test_schema.py`, `tests/test_prompt.py`,
  `tests/test_llm_deepseek.py`, `tests/test_part_check.py` (if affected); `tests/test_input_guard.py`
  deleted.
- `specs/answer-citations.md`, `specs/ui.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/RUN.md`.
- `docs/results/0247-reduce-check.md`, `docs/results/0247-raw/` (raw records of the real check).
- Not committed: the gated wrapper `D:\ALLPROJECTS\EDJ\cache\ev247\run-real-reduce.ps1` and
  `run-real-reduce.sh` (as #246).

## Steps
1. Matrix fixes (scope normalisation, unverified rule, `EvidenceMatrix.hits`), `run_round` skip reason,
   the eval's `allow()` 400 stop and planner flags; tests. Then the **0-call re-check of #246's 33
   records** under the new matrix code, with `EXTRACT_VERSION` still `extract-v1` (records seeded from
   `docs/results/0246-map-raw/` into the worktree's `.eval-runs/cache`; no key in the environment;
   `--real --map-only --max-calls 0`): expected Q24 MS derived, marks as in section 6 item 5, every other
   label unchanged. Evidence `D:\ALLPROJECTS\EDJ\cache\ev247\recheck-246`.
2. `schema.py`, `prompt.py` v5, `reduce.py` (render, schema enums with the provider limits re-checked,
   requests, `call_reduce` with fake clients for the three providers, mock, code answers, checks);
   tests.
3. `validate.check_numbers` computed figures; guard removal (`llm`, `validate`, `ask`, `config`,
   `.env.example`, eval fields); tests.
4. `ask()` / `answer_for` wiring, `MAP` on, stage texts, `log_filters`; app `incomplete`; tests.
5. `eval_run.py` reduce cache, reuse, failed calls, cap, `--legacy`, records and report; tests.
6. `extract-v1.1` (D1), its prompt tests.
7. Mock 35-question run (section 9) against main `a32eb64`.
8. pytest (full), verify-cee, specs / ADR / docs.
9. Real check phase A and the 0-call count (section 11); the count and the phase-B cap in the Progress
   log before phase B.
10. Real check phase B (last). Blind scoring (section 11). `docs/results/0247-reduce-check.md`.
11. `/finish-task`, PR (ADR-021 amendment: escalated to the TL), `gh pr checks` green.

## Tests (0 real calls; `tests/conftest.py` blocks every client)
- **Synthesis cannot cite outside the matrix**: the schema's `chunk_ids` enum equals
  `matrix.chunk_ids()` (rejected ids absent); a fake output citing a retrieved non-matrix chunk, a
  rejected id and an invented id -> each claim flagged `outside_matrix` + `unmatched_citation`, kept;
  the rendered input lists only matrix ids in Sources.
- **Comparison claim required**: a matrix with a comparison aspect and a fake output without its claim
  -> the `COMPARISON_MISSING` gap with `comparison_missing`; with the claim (part_id = aspect id, or a
  sub-question id, citing a matrix id) -> no gap; a claim citing nothing -> still missing.
- **Invalid reduce outputs saved as invalid** (fake clients, three providers): no tool call, cut at the
  cap, refusal, DeepSeek bad `finish_reason`, not JSON, stray braces (accepted, flagged), not a valid
  Answer, empty -> `ModelOutputError`; the eval saves `invalid: true`, reuses it on the next run with 0
  calls; a failed call (timeout, 500) is saved as `failed_call`, never re-called; a 400 stops the run.
- **Behavior by code**: the schema offers one behavior; a fake output with another (non-strict path) is
  overridden and logged; refuse (1c), forecast refuse and undecided make **no call** and build the
  code answers (`incomplete` with the note, never `refuse`, never "does not support").
- **Rule 3 flags**: adjacent citing a holding non-proxy cell -> `adjacent_is_fact`; a claim on a
  different_quantity or proxy cell -> `claim_from_adjacent`.
- **Computed figure**: a claim stating the derived value citing both inputs -> `computed`, no
  `number_not_found`; citing one input -> `number_not_found`; a cross-firm ratio -> `number_not_found`.
- **Why-lines and order**: a window question: a claim without "Why it might matter: " ->
  `why_line_missing`; claims given oldest first are re-sorted newest first, hand-off last, `reordered`
  logged.
- **Gaps and caveats placed**: every matrix gap appears once with its part id and suggested source; the
  comparability and GWIM caveats appear; `check_parts` adds no gap when every holding cell has a claim.
- **Handover**: scope normalisation cases; unverified only on metric aspects (Q19- and Q26-shaped
  matrices -> none; Q24-shaped -> a1, a2); the 400 stop via `allow()` (section 6 item 7); planner
  re-check flags; extract-v1.1 text present in both prompts; the stale phrase gone.
- **Re-search hits are part of the answer's hits** (B1): a fake matrix whose claim cites a corrective
  re-search hit: the chip is linked on the Ask page (`show_answer` with a fake `Result`), no
  `outside_matrix` / `unmatched_citation`, the id is in `query_log.chunk_ids` (via `_log`'s parameters)
  and in `chunk_origin` as `corrective`, no duplicate when retrieval also had it; the eval's recall uses
  the retrieval hits only.
- **Empty citable set** (B2): an all-`not_found` normative matrix -> 0 calls (a fake client that
  fails if called), `answer_with_boundary`, the hand-off last with no `no_citation` flag, the "does not
  support" gaps; the same with one failed cell -> the `incomplete_note` shown, no "does not support"
  gap for that aspect; no reduce schema is built.
- **Comparison and proxy parts** (B3): a Q24-shaped matrix through the mock reduce -> no `part_gap` on
  `a4.*` or on a not-found proxy cell; a comparison aspect with no claim -> the `COMPARISON_MISSING` gap
  covers its parts (no part gap besides).
- **Uncovered periods** (B4): section 6 item 4 tests; `asked_periods` cases ("last eight quarters",
  "past 3 years", a window, none).
- **Duplicate gaps** (note 9): a model gap repeating a code gap -> one gap, flag `model_also_named`.
- **Formula text** (note 2): the rendered input and the mock claim carry no cell id; the id formula
  stays in the log.
- **Enum size** (note 5): the Q19-sized schema's value count and character total per provider; over a
  limit -> the per-field fallback, logged.
- **UI** (note 7): `show_answer` renders an `incomplete` answer (header "Incomplete" and the note)
  without a KeyError; the design page lists the header.
- **Why-lines and order scope** (note 4): an Ask-page date filter alone triggers neither the why-line
  check nor the re-sort; the sort key is the published date.
- **Prompt**: no 6-word run of any question text or `passes_if` in v5 (standard wording exempt).
- **Schema**: the reduce schema passes `_strict_problems` (DeepSeek / OpenAI) and
  `anthropic.transform_schema` leaves it unchanged; `incomplete` not in any model schema.
- **ask / app**: stage order; default `MAP` on: mock run builds the matrix and the mock reduce with 0
  paid calls (`llm_calls` all 0), the model line "(mock, one call)", `log_filters.map` a matrix and
  `log_filters.reduce` present; `MAP=off` runs the legacy path; empty retrieval: no map, no reduce, the
  empty-retrieval answer; `test_no_paid_calls` green.
- **Eval**: reduce key changes with the matrix (one cell label), the window, the version, the cap, the
  thinking mode; `--max-calls` exact with the reduce reservation; `--map-only` makes no reduce call;
  `--legacy` makes the v4.1 call and no map.

## 9. Mock 35-question check (0 calls)
`eval_run.py` (mock, map on by default) at the branch head vs main `a32eb64` with `--map` (a temporary
detached worktree, as #246): chunk lists, statuses, recall@pool / @final, coverage and forbidden hits
identical for all 35 (the reduce never touches retrieval; refusal 8/8). Plus, per question: the mock
answer validates; 0 `outside_matrix`; every comparison aspect has a claim or the code gap; every recency
item has a why-line; behavior = matrix behavior (or the documented re-judge); **0 `part_gap` on
comparison and proxy parts, Q24 included** (B3); every claim citing a corrective re-search chunk links
to it (B1); 0 empty `chunk_ids` enums (no reduce schema built for an empty citable set, B2); 0 paid
calls. Evidence `D:\ALLPROJECTS\EDJ\cache\ev247\
mock-*`.

## 10. verify-cee
Recipe and driver updated in this PR (CLAUDE.md "A changed user feature updates its recipe"):
- `ask-progress`: the map line is now "Extracting per firm (mock, no model call): N cells: ...; behavior
  by code: answer"; the model line "Asking the model to write the answer from the evidence matrix (mock,
  one call): N claims"; the early check waits for "Asking the model"; `llm_calls` on the mock still
  `{"map": 0, "remap": 0, "answer": 0, "planner": 0}`; the `query_log` row's `filters.map` is a matrix
  (not `{"off": true}`) and `filters.reduce` is present.
- The driver starts the verify app with `MAP=on` in its environment (review note 1), next to
  `LLM_PROVIDER`, `MOCK_DELAY_S` and `DATABASE_URL`.
- `ask-answer`: new step: the shown behavior equals `filters.map.behavior` of the newest `query_log`
  row, or is `answer_with_boundary` with `filters.reduce.behavior_rejudged` true (review note 8); every
  cited chunk id is in the matrix's cited ids (0 `outside_matrix`) and in the row's `chunk_ids`, and
  every citation chip on the page is linked (B1; if the verify question has no corrective chunk, the
  step says so and the B1 case is covered by pytest).
- `gap-path` (no evidence): unchanged (no map, no reduce).
Run on Windows (the TL's machine); the Mac block stays in the recipe. Known: the open-citation read-back
render race (#248).

## 11. Real check (last, after every mock check passes)
- **Why the mock cannot show it**: the mock writes item texts verbatim and a fixed comparison and
  why-line; whether v5 answers the comparison (Q24), writes sourced why-lines newest first (Q26), states
  partial disclosures as claims with each firm's definition and named gaps (Q11, Q23), cites competitor
  moves or names the leg as a gap (Q19), and keeps Q1 / Q3 / Q22 passing needs the real model.
- **Settings** (pinned and printed by the wrapper): DeepSeek `deepseek-v4-pro`, `/beta` strict tools,
  thinking on, `MAP=on`, `MAP_CONCURRENCY=6`, `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1.1
  (D1), prompt v5, request version `ds-strict-1-think-on-a64000-p64000`, `--as-of 2026-11-17`, snapshot
  `corpus-2026-11-19`. Code gate: `git status` clean, `src scripts config` identical to the mock-run
  sha. `.env` copied in for each phase and removed in `finally` (trap on Mac). Each phase in the
  background. Evidence to `D:\ALLPROJECTS\EDJ\cache\ev247\real-*`.
- **Plans**: the five targets reuse their #246 plan-v3.1 records (`docs/results/0246-map-raw/Q*-plan-*`,
  seeded into the worktree cache; same key: planner version, request version, resolved query, as-of):
  0 calls. Q1, Q3 and Q22 have no plan-v3.1 record: **3 planner calls**.
- **Map**: with extract-v1.1 no #246 map record matches (the version is in the key), so all eight
  questions are mapped once. Round 1 for the targets is known from #246's count (same plans, same
  retrieval): Q11 5, Q19 4, Q23 5, Q24 5, Q26 1 = 20. The regression questions are bounded by firms
  (entity mode has no research row; the bound allows one anyway): Q1 <= 2, Q3 <= 2, Q22 <= 6.
- **Expected calls**:
  | Q | Planner | Map round 1 | Re-extraction (at most) | Reduce | At most |
  |---|---|---|---|---|---|
  | Q11 | 0 (cached) | 5 | 5 | 1 | 11 |
  | Q19 | 0 | 4 | 5 | 1 | 10 |
  | Q23 | 0 | 5 | 5 | 1 | 11 |
  | Q24 | 0 | 5 | 5 | 1 | 11 |
  | Q26 | 0 | 1 | 1 | 1 | 3 |
  | Q1 | 1 | <= 2 | 1 | 1 | 5 |
  | Q3 | 1 | <= 2 | 1 | 1 | 5 |
  | Q22 | 1 | <= 6 | 5 | 1 | 13 |
  | **Total** | **3** | **<= 30** | **<= 28** | **8** | **<= 69** |
  **Call cap: 69 in total.** #246's targets made 8 re-extractions of a bound 21, so the real number is
  likely ~45. A reduce for a code-built answer (refuse / undecided) is not made, so the reduce count
  may be below 8.
- **Phases** (one gated wrapper `run-real-reduce.ps1` / `.sh`, parameter `-Phase A|count|B -Cap N`):
  - **A, planner (3 calls)**: `eval_run.py --real --plan-only --max-calls 3 --questions Q1,Q3,Q22
    --as-of 2026-11-17 --out ...\ev247\real-plan`.
  - **Count (0 calls)**: `eval_run.py --real --map-only --max-calls 0 --questions
    Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 ... --out ...\real-count`: plans from the cache, every map call over
    the cap, so the exact round-1 list is printed. The Progress log records it and the phase-B cap =
    round 1 + the re-extraction bound for those firms + 8; if it differs from the table, the table is
    amended first.
  - **B, map + reduce (<= 66 calls)**: `eval_run.py --real --max-calls <B cap> --questions ... --out
    ...\real-reduce` (plans reused, 0 planner calls).
  Mac: the same commands with `.venv/bin/python` and `../cache/ev247/...`.
- **No re-runs**: an invalid output, a failed call or a wrong answer is a finding, reported, never
  re-run. A 400 stops the run after the round (section 6 item 7); the rest waits for the TL.
- **Scoring**: a fresh scorer agent reads only the eight answers (an answers dump, as #243), the bank's
  `passes_if` and #243's verdict rule (PASS only if the project lead would forward it; no half credit),
  blind, and writes `verdicts-blind.json` (sha256 in the Progress log before any comparison); then a
  second read against #217's / #243's like-for-like bar. Baseline for each: #243 like-for-like (Q1 PASS,
  Q3 **FAIL**, Q22 PASS; Q11, Q19, Q23, Q24, Q26 FAIL). So "Q1, Q3, Q22 keep PASS" means Q1 and Q22 stay
  PASS and Q3 must move to PASS (it passed under #217 / Claude).
- **Reported** in `docs/results/0247-reduce-check.md` and the PR: per question the matrix summary, the
  answer (claims, adjacent, gaps, caveats, flags), the code checks (comparison claim, why-lines, order,
  outside-matrix, computed figures), behavior vs effective expected, the verdicts, Q22's must-not chunks
  (`MS-PR-2026-04-15-01#15`, `SCHW-10Q-2026Q2#56`: cited or not, label), calls by type, tokens (input,
  cache hits, output, reasoning), wall time, cost in CNY with the per-1M rates used and their source
  (peak / off-peak by Beijing time, as #246). Raw records copied to `docs/results/0247-raw/`.

## Acceptance
- [ ] Real: Q11 / Q23 behavior `answer`, each firm's definition or series stated as claims (partial
      coverage with its periods, Q23 MS included), the comparability caveat, and named gaps.
- [ ] Real: Q24 one cited comparison claim (valid or not, and why) and the EDJ ratio stated from the
      derived cell with both inputs cited (`computed`, no `number_not_found`).
- [ ] Real: Q26 a sourced why-line on every item, newest first, nothing older than the window.
- [ ] Real: Q19 cites competitor moves or names the competitor leg as a gap per firm; hand-off last.
- [ ] Real: Q1 and Q22 keep PASS; Q3 PASS (FAIL in the DeepSeek baseline); Q22 cites no must-not chunk
      as a fact.
- [ ] Tests: synthesis cannot cite outside the matrix; comparison claim required; invalid reduce outputs
      saved as invalid; the 400 stop via `allow()`; behavior by code; 0 real calls.
- [ ] Handover items 1-10 (section 6) done, each with its test or check.
- [ ] Review 1 blocking items: B1 (union of hits, origin tagged, test), B2 (empty citable set, 0 calls,
      tests), B3 (no false part gaps on comparison / proxy parts, test and mock line), B4 (code names
      uncovered periods, test); non-blocking notes 1-11 adopted.
- [ ] Mock 35-question run: retrieval identical to main `a32eb64`; mock answers pass every code check.
- [ ] pytest, verify-cee and `gh pr checks` green.
- [ ] The PR carries the ADR-021 amendment -> escalated to the TL for the merge.

## Risks (review note 10)
- **Enum size per provider**: Q19-sized schemas near OpenAI's limits; the per-field fallback leaves only
  the code check on that path (logged, stated in the PR).
- **Cost and latency for app users** now that `MAP` is on: a five-firm question makes 1 planner + up to
  6 map + up to 6 re-extraction + 1 reduce calls, minutes of wall time (#246: ~48 min for 33 calls at 6
  in parallel); visible in the trace and the log; #248 owns cost.
- **extract-v1.1 label drift**: the added sentence may move labels on other questions (more `fact`,
  fewer `different_quantity` for other-period figures); the real check reports every label change on the
  five targets against #246's matrices.
- **D4 sort key**: published date orders a 10-Q by filing date, not by its period; claims about the
  same period from two documents may separate.
- **Asked-period parsing** (B4) covers "last / past N quarters / years" and windows only; other
  phrasings get no period gap (the reduce states the periods it has).

## Decisions (TL, plan review 1, issuecomment-7033895178)
D1-D7 below stand as decided: D1 extract-v1.1 with the re-map under the cap of 69; D2 code-built
refuse / undecided, `incomplete`; D3 `MAP=off` legacy kept; D4 code re-sorts; D5 why-line inside the
claim; D6 unverified on series / proxy / derived; D7 strict enums with per-field fallback. B1-B4 as
written in sections 3-6 and Tests.

## Open decisions as first proposed (settled above)
- **D1 - Q23 fix at the map (extract-v1.1, recommended) or at the reduce.** (a) extract-v1.1 fixes the
  label where rule 3 says it is enforced, but changes the map cache key: the five targets are mapped
  again (20 round-1 + <= 21 re-extractions; #246 made 28, ~19 CNY at peak), cap 69. (b) Keep extract-v1:
  the targets reuse all 28 #246 map records (0 map calls for them), and v5 tells the reduce to write a
  `different_quantity` cell whose items are the asked quantity for other periods as a claim with its
  period; the map's gap for that cell ("a different quantity is listed as adjacent") would then
  contradict the claim, and the fix rests on the prompt. Cap under (b): 3 + 10 + 7 + 8 = **28**.
- **D2 - Code-built answers** for refuse (1c, forecast) and undecided, 0 calls; undecided shown with
  the new code-only behavior value `incomplete` (the app header "Incomplete", the eval counts it as a
  behavior mismatch).
- **D3 - `MAP=off` keeps the legacy v4.1 path** (no guard) for comparison; #248 decides whether to
  drop it. Alternative: remove the legacy path now.
- **D4 - Newest-first enforced by code** (re-sort by cited document date) rather than only checked.
- **D5 - Why-line form**: inside the claim ("... Why it might matter: <sourced sentence>"), with "the
  source does not say" allowed; one claim per item keeps order and citations together.
- **D6 - Unverified mark rule** as section 6 item 5 (series, proxy or derived).
- **D7 - Strict enums on `behavior`, `part_id` and `chunk_ids`** in the reduce schema, with a per-field
  fallback to plain strings if a provider limit is exceeded (stated in the PR).

## Progress log
- 2026-11-20 01:49 - plan written (worktree `D:\ALLPROJECTS\EDJ\wt-247`, branch `tl/247-reduce` from
  `origin/main` a32eb64, which includes #246 at b8c1242; database up to date `corpus-2026-11-19`).
  Checked: `matrix.chunk_ids()` holds valid ids only, but re-search hits are not in the hits `ask()`
  passes on, so the reduce's checks need `EvidenceMatrix.hits`; the stale "20000 / 2000" phrase is only
  in the `llm.py` comment (the spec was fixed by #246); `wt-246` is gone, #246's 33 raw records are in
  `docs/results/0246-map-raw/` (the seed for the plan cache and the step-1 re-check); Q1 / Q3 / Q22
  have only older planner records in the main repo cache (not plan-v3.1), so they need 3 planner calls.
- 2026-11-20 - plan review 1: PLAN CHANGES REQUESTED (issuecomment-7033895178), 4 blocking, 11
  non-blocking; TL decisions D1-D7 recorded. Revised: B1 `Result.hits`, the Ask page, the coverage note,
  the checks and `query_log.chunk_ids` use the union of retrieval and corrective re-search hits (no
  duplicates, `Hit.origin = "corrective"`, `log_filters.chunk_origin`), eval scoring keeps retrieval
  hits; B2 an empty citable set is code-built with 0 calls (normative: `answer_with_boundary`, the
  hand-off exempt from `no_citation`, the gaps, the incomplete note when a cell failed; rule 1e now
  sets the note), never an empty enum; B3 comparison parts covered by the aspect's comparison claim or
  its `COMPARISON_MISSING` gap, proxy parts by an adjacent item or by design, mock line "0 part_gap on
  comparison / proxy parts, Q24 included"; B4 code names uncovered asked periods (`asked_periods`,
  `period_gaps`), the reduce states only the periods it has. Notes 1-11 adopted: `.env` never touched,
  `.env.example` `MAP=on`, verify driver sets `MAP=on`, the eval maps unless `--legacy`, RUN.md and the
  PR body tell users to flip `MAP=off` in their own `.env`; formula text without ids; rejected
  derivations with their why and registered definitions rendered; enum limits written and a Q19-sized
  test; system-prompt sha in the reduce key; `incomplete` UI test and design page; re-judged behavior
  allowed in the eval and verify; gap dedupe; owners and Risks; `stop_reason` / `usage` in
  `log_filters.reduce`. Call cap unchanged: **69** (phase B <= 66); B2 can only lower the reduce count.
- 2026-11-20 - plan review 2 (issuecomment-7033988541) and TL approval at d8b273d with conditions,
  written in before any code (section "TL approval conditions"): a window gives no asked periods;
  "last N years" by complete years, matched by year; Q26-, years- and Q23-shaped tests; round-2 notes
  adopted (eval part_coverage on the union, code-built answers through the comparison and part checks,
  incomplete_note shown as a warning on any behavior, a YYYY item covers no quarter). Cap 69. Build starts.
- 2026-11-20 - step 1 (a41fcf8): scope normalisation, unverified mark on metric aspects, uncovered-period
  gaps, corrective hits on the matrix, the 400 stop via `allow()` (test), planner re-check flags (test).
  0-call re-check of #246's 33 records under extract-v1 (`ev247\recheck-246`, no key, `--max-calls 0`): 0
  calls, 33 reused; Q24 a1.MS now derived ($3,999 billion / 15,950 at 2020-12-31; scopes "Wealth Management
  segment" vs "Wealth Management" normalised), RJF still rejected (whole firm vs Private Client Group);
  marks: Q19 a1 / a5 / a11 and Q26 a1, a2, a4-a6 and Q24 a4 lose `unverified`, Q24 a1 / a2 keep it; Q23
  period gaps EDJ 2024Q4, 2025Q4, 2026Q3 and RJF all but 2025Q3 (as expected); every other label and
  behavior unchanged.
- 2026-11-20 - build (b6e0f02, docs af344ee): reduce.py (render, strict enums with the OpenAI limits,
  three provider paths, mock, code-built answers, every post-call check), prompt v5, `incomplete`,
  computed figures in the number check, the matrix-aware part coverage, `ask()` / `answer_for` wiring
  with the union of hits, `MAP` on, the interim guard removed (`tests/test_input_guard.py` deleted with
  it), the Ask page (`incomplete`, the warning, flag labels), the eval (reduce cache, failed / invalid
  records, `--legacy`, maps unless `--legacy`), extract-v1.1, verify driver and recipes, specs, ADR-021
  amendment. DeepSeek's tool-call guide (read 2026-11-20) states no enum limit: OpenAI's numbers apply
  to every provider. Not done: no label mapping for older flags (they keep their names as before).
  pytest 901 passed.
- 2026-11-20 - mock 35 (0 calls; main a32eb64 with `--map` in a detached worktree vs b6e0f02):
  chunk lists, statuses, recall@pool / @final, coverage, forbidden and refusal identical for all 35 (33
  PASS / 2 FAIL, refusal 8/8, as main). The mock reduce answered all 35: 0 `outside_matrix`, 0
  `part_gap`, 0 why-lines missing, 0 comparison claims missing, behavior = matrix behavior everywhere,
  0 code-built (the mock map gives a fact wherever it retrieves). The mock rule plan has no comparison
  or proxy aspect, so "no part gap on comparison / proxy parts, Q24 included" is shown on the mock by
  Q24's 0 part gaps and on a Q24-shaped matrix with a comparison and proxies by
  `tests/test_reduce.py::test_comparison_and_proxy_parts_get_no_false_part_gap_q24_shaped`. Evidence
  `ev247\mock-compare.txt`.
- 2026-11-20 - verify-cee at af344ee (`.verify-runs/20261120-023815-af344ee`): ask-answer PASS (new
  step: `answer|answer|false|0|0`, no unlinked chip), gap-path, invalid-chunk, coverage, filters,
  feedback PASS, open-citation PASS, download-document UNREACHABLE (no raw files); ask-progress FAIL on
  one step: the driver took the map line ("... no model call") for the model line. Fixed in the driver
  (7b9a5b4); re-run of ask-progress, ask-answer, open-citation (`20261120-024102-7b9a5b4`): ask-progress
  PASS (map line "Extracting per firm (mock, no model call): 1 cell: 1 fact; behavior by code: answer",
  model line "Asking the model to write the answer from the evidence matrix (mock, one call): 1 claim"),
  ask-answer PASS; open-citation read-back FAIL once (passed in the first run): the known #248 render
  race. Code-gate sha for the real runs: 7b9a5b4 (its src / scripts / config diff from the mock-run sha
  b6e0f02 is `scripts/verify_cee.py` only).
