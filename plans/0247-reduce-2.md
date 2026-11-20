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
- neither value is approximate or a bound ("approximately", "about", "around", "nearly", "close to",
  "more than", "over", "at least", "roughly", "~", ">", "<", "+" after a figure); else rejected with
  "<input> is approximate".
Sum and difference keep today's rules plus the same population check. Rejected proposals stay on the
cell (`ok: false`, `why`), as now.

**What the answer says per firm.** For every cell with a derivation proposal (accepted or rejected),
the reduce input shows the inputs with their `covers` text and chunk ids and, for a rejection, code's
`why`. Prompt v5.1: "For each firm with a computation line, write one claim saying whether the figure is
computable, citing both inputs." Code check `check_computability`: a claim with that cell id (or a
sub-question id of the aspect, for the firm) citing every input chunk; missing -> code adds the claim
in standard wording, cited to both inputs, flag `code_computability`:
- `COMPUTED` = "<Firm>: <aspect>: computed by code from two figures that cover the same population:
  <formula_text> (<period>)."
- `NOT_COMPUTED` = "<Firm>: <aspect>: not computed: <why>."
The values in both texts are the items' values as printed (the number check passes them; a computed
value passes through the existing `computed` rule). A firm with no proposal keeps its cell gap.

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
  period (`fts.Query.period_range`, `filters_sql`), `PERIOD_K = 3` passages, `MAX_PER_DOC` 3. A period
  with no document of that period end returns nothing (EDJ 2024Q4, 2026Q3). Expected for Q23 a1.EDJ:
  2025Q4 -> `EDJ-10K-2025#130`, `#142`, `#148`. Hits: `origin = "period"`, `part_id` = the sub-question.
- **Registered-definition pin** (aspects with a registered `metric`): the firm's `metric_definitions`
  entry `chunk_id` and its same-firm `see_also` ids (at most `PIN_MAX = 6`), fetched by ID under the
  sub-question's entity / segment, window and date-range filters (so Q26's 90-day window drops them);
  the doc-type scope is **not** applied to pinned ids (D1). Hits: `origin = "pinned"`. Expected: Q11 /
  Q23 / Q24 a3 get `MS-SUPP-2020Q4#1/#3`, `MS-ADV1A-2026#1`, `SCHW-ADV1A-2026#1`, `SCHW-10K-2025#18`,
  `BAC-SUPP-2023Q4#2`, `MER-ADV1A-2026#1` (via BAC), `EDJ-10K-2025#130/#148`, `RJF-10K-2025#228/#227`.
- Both are added to `plan.pools[sq.id]` (the map's retrieved-set check) and logged per sub-question in
  `plan.searched` (`period_hits`, `pinned`). The eval's retrieval scoring includes them (they are
  retrieval); the record adds `added_chunk_ids` by origin.
- Trade press stays out of benchmark questions (D2): the MS "close to 15,000" figures remain unseen;
  MS's gap says no count after 4Q2020 was found, and the pinned Form ADV figure arrives as a
  `different_quantity` item (adjacent).

## 3. Basis break inside a series (TL item 3)
`matrix.basis_breaks(m)` (in `finish`, after `tag_populations`): for each holding cell of a `series`
aspect or a registered-metric `fact` aspect, group its counting items by (normalised scope, population
key). More than one group -> a code caveat (standard wording `BASIS_BREAK`): "<Firm> - <aspect>: the
figures cover different bases and are not one series: <whole firm: 2025Q2, 2025Q3, 2026Q2>; <U.S.:
2025Q1, 2026Q1>; <Canada: 2025Q1, 2026Q1>. The break is flagged, not smoothed." The cell gets flag
`basis_break`; the reduce input prints the caveat under the cell ("state each basis with its periods;
never join them"); the caveat is inserted by code like the comparability caveat. Expected on part 1's
Q23 matrix: EDJ flagged; MS, RJF, MER as their items show.

## 4. Noise (TL item 4)
- **Duplicate claims** (`reduce.dedupe_claims`, after `check_parts`, so part coverage is unchanged):
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
  only when `asked_firms` is empty. Competitor cells of an aspect without a subset that hold nothing
  (`not_found` / `not_disclosed`) are folded into one gap per aspect (D3): "Competitors (<names>) -
  <aspect>: not found in the documents searched." A competitor cell that holds anything is shown as
  now. Expected on part 1's Q19 matrix (0-call replay): about 16 gap rows instead of 58.
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
    `why_line_restated`, the model's sentence logged (D4).

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
  (by ID, the same entity / segment / window / date-range filters, no doc-type scope); `Hit.origin`
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
  `docs/DECISIONS.md` (ADR-021 amendment, #247 part 2: populations in derivation, pinned definitions
  across the doc-type scope (amends ADR-015's scope for registered ids only), per-period retrieval,
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
4. Reduce v5.1: rendering, `check_computability`, why-line checks, dedupe, recency-only re-sort; tests;
   0-call replay of part 1's eight saved reduce outputs through the new post-call code (duplicates,
   why-lines removed / restated, re-sort counts), reported, nothing re-run.
5. ask / eval / app wiring, chips; tests; full pytest.
6. Mock 35-question run against main c4ba303 (section 8).
7. verify-cee; specs, ADR amendment, RUN.md.
8. Seed the cache, 0-call count, the cap in the Progress log; the real run (section 9); raw records
   saved; blind-in prepared; **stop before scoring** (the TL starts the blind scorer).
9. After the TL's scoring: `docs/results/0247-reduce-2-check.md`, `/finish-task`, PR "Part of #247" or
   "Closes #247" as the verdicts show, `gh pr checks` green.

## Tests (0 real calls; `tests/conftest.py` blocks every client)
- **Populations**: RJF-shaped (AUA incl. RCS / advisors excl. RCS) -> rejected, `why` names both;
  MS total client assets / WM representatives -> rejected; MS advisor-led / WM representatives at one
  period -> accepted; EDJ firm / firm -> accepted; EDJ firm assets / U.S. count -> rejected; an input
  with no matching entry -> "not registered"; ">15K", "more than 20,000", "approximately 9,000" ->
  "approximate"; two entries matching one item -> no key. Every `populations` quote verbatim in its
  chunk (database test, skipped without one).
- **Computability**: a matrix with one accepted and one rejected proposal and a fake reduce output
  without their claims -> two code claims (`COMPUTED`, `NOT_COMPUTED`) citing both inputs, flagged
  `code_computability`, no `number_not_found`; with the model's own claims citing both -> none added.
- **Per-period search**: a Q23-shaped fake search: one call per asked period with `period_range`, the
  sub-question's filters kept, kept chunks excluded, main lists unchanged; a question without asked
  periods or a window question -> no period call. `filters_sql` emits the `period_end` clause.
- **Pins**: registered ids fetched for registered-metric aspects only, same-firm `see_also` only, BAC
  entry for MER, window and entity filters applied (a Q26-shaped window drops them), doc-type scope not
  applied, already-kept ids not repeated, `plan.pools` includes them (the map accepts their citation).
- **Basis break**: Q23 EDJ-shaped items (whole firm, U.S., Canada) -> one caveat listing each basis
  with its periods, `basis_break` on the cell; one basis -> none; a recency aspect -> none.
- **Gap scope**: Q19-shaped plan (`asked_firms = [EDJ]` widened by the home-firm rule) -> no gaps for
  competitor or research cells of those aspects; aspects without a subset -> one competitors gap, named
  and research cells as before; a competitor cell holding a different quantity keeps its own gap.
  `validate_plan` records `asked_firms`.
- **Dedupe**: Q19-shaped exact repeats -> one kept; Q26-shaped subsumed claims -> the longer kept;
  different chunk sets with equal text -> both kept; part coverage unchanged.
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
- [ ] Tests listed above; 0 real calls in tests.
- [ ] Mock 35: every main chunk list identical to main; only `pinned` / `period` additions, each listed;
      recall not lower; forbidden hits from additions reported; mock answers pass every code check.
- [ ] pytest, verify-cee and `gh pr checks` green.
- [ ] ADR-021 amendment in the PR -> escalated to the TL for the merge.

## 8. Mock 35-question check (0 calls)
`eval_run.py` (mock) at the branch head vs main c4ba303 (a detached worktree): per question every main
sub-question chunk list identical; additions only with origin `pinned` / `period` (listed per question;
expected on questions whose rule plan has a registered metric or a series with asked periods); recall
@pool / @final not lower; forbidden / `must_not_return` hits among the additions reported; refusal 8/8
unchanged; mock answers: 0 `outside_matrix`, 0 `part_gap`, 0 comparison claims missing, 0 why-lines
missing, behavior = matrix behavior. Evidence `D:\ALLPROJECTS\EDJ\cache\ev247b\mock-*`.

## 9. Real check (last, after every mock check passes)
- **Why the mock cannot show it**: whether v5.1 states per-firm computability and basis breaks in words
  a strategist would forward, writes why-lines from the stated context, and whether the added passages
  give Q11 / Q23 their missing points needs the real model; Q19 and Q26 guard against regressions.
- **Questions, one run each**: Q11, Q23, Q24 (targets), Q19, Q26 (regression). No re-rolls: an invalid
  output, a failed call or a wrong answer is a finding. A ProviderStop or a 400 stops the run (the
  part-1 `allow()` rule); the rest waits for the TL.
- **Settings** (pinned and printed by the wrapper `ev247b\run-real.ps1` / `.sh`): `LLM_PROVIDER=deepseek`,
  `deepseek-v4-pro`, `/beta` strict tools, thinking on, `MAP=on`, `MAP_CONCURRENCY=6`,
  `SUBQUESTION_TOKENS=40000`, plan-v3.1, extract-v1.1, prompt v5.1, request version
  `ds-strict-1-think-on-a64000-p64000`, `--as-of 2026-11-17`, snapshot `corpus-2026-11-19`. Code gate:
  `git status` clean, `src scripts config` identical to the mock-run sha. `.env` copied in from the main
  repo inside `try` and removed in `finally` (trap on Mac); never read or printed.
- **Reuse**: the five plan-v3.1 records (`docs/results/0246-map-raw/Q{11,19,23,24,26}-plan-*`) and every
  part-1 map / re-map record (`docs/results/0247-raw/`) are seeded into the worktree's `.eval-runs/cache`.
  Planner: 0 calls. Map: Q19 and Q26 inputs do not change (no registered metric outside a window, no
  series), so their map keys should match part 1 (0 calls); Q11, Q23, Q24 inputs change (pins, periods),
  so they are mapped again. Reduce: v5.1 changes every key: 5 calls.
- **Expected calls** (upper bounds; re-extraction bound = firms):
  | Q | Planner | Map round 1 | Re-extraction (at most) | Reduce | At most |
  |---|---|---|---|---|---|
  | Q11 | 0 | 5 | 5 | 1 | 11 |
  | Q23 | 0 | 5 | 5 | 1 | 11 |
  | Q24 | 0 | 5 | 5 | 1 | 11 |
  | Q19 | 0 | 0 (4 if its key changed) | 0 (5) | 1 | 1 (10) |
  | Q26 | 0 | 0 (1) | 0 (1) | 1 | 1 (3) |
  | **Total** | **0** | | | **5** | **35 (46 if no map record is reused)** |
- **0-call count first**: `eval_run.py --real --map-only --max-calls 0 --questions Q11,Q23,Q24,Q19,Q26
  --as-of 2026-11-17 --out ...\ev247b\real-count` (seeded cache, no key in the environment): prints the
  exact round-1 list and which records are reused. The run's cap = round 1 + the re-extraction bound of
  those firms + 5, written in the Progress log before the run; if it exceeds 46 the plan is amended
  first.
- **Run**: `eval_run.py --real --max-calls <cap> --questions Q11,Q23,Q24,Q19,Q26 --as-of 2026-11-17
  --out D:\ALLPROJECTS\EDJ\cache\ev247b\real-run` in the background. Mac: the same with
  `.venv/bin/python` and `../cache/ev247b/...`. Raw records copied to `docs/results/0247b-raw/`.
- **Stop before scoring**: prepare `D:\ALLPROJECTS\EDJ\cache\ev247b\blind-in\` as part 1 (an answers dump
  of the five answers, the five questions from `evals/questions.yaml`, part 1's verdict rule with the
  Q24 superseded behavior line) and `blind-in-hashes.txt`; report to the TL, who starts a fresh blind
  scorer. Baseline: part 1 blind (Q19, Q26 PASS; Q11, Q23, Q24 FAIL).
- **Reported** (in the check doc and the PR): per question the matrix summary, the added passages by
  origin, the derivations (accepted / rejected and why), basis breaks, gap rows before / after,
  duplicates removed, why-lines removed / restated, calls by type, tokens, wall time, cost with the
  per-1M rates and their source (as part 1).

## Decisions for the plan reviewer / TL
- **D1 - Pinned definitions bypass the doc-type scope** (not the window, entity or segment filters).
  Recommended: the registered ids are curated by C1 for exactly these questions (SCHW's only registered
  figure is its Form ADV Part 1A). Alternative: honour the scope; then SCHW / MS / MER Form ADV figures
  stay out and only filing chunks are pinned.
- **D2 - Trade press stays out of benchmark questions.** The MS "close to 15,000" figures are not
  brought in (rounded, tier 4, ADR-015). Alternative: a tier-4 fallback search for a firm whose series
  covers no asked period, its items forced adjacent and never a derivation input.
- **D3 - Fold empty competitor cells into one gap per aspect.** Beyond the TL's minimum (no gaps
  outside the aspect's subset); recommended for Q19's a1-a6 noise. Alternative: per-cell gaps kept for
  aspects without a subset.
- **D4 - A restating why-line is replaced by code** with `WHY_UNSAID` (flagged, logged). Alternative:
  flag only.
- **D5 - Computability claims added by code when the reduce omits them** (standard wording, cited).
  Alternative: a gap ("No claim states whether <Firm>'s figure is computable") as for comparisons.

## Risks
- Pins and periods add passages: map inputs grow (Q23 up to ~120 passages over five firms); within the
  input limit checked per call; cost reported.
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
