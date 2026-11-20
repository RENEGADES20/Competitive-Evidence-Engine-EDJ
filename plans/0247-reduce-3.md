# 0247 - Reduce part 3: definition contrast, related-metric wording, quarter holes, gap sources (0 calls)

Issue: #247 (part 3, "Part of #247" unless Q11 and Q23 both pass)    Role: TL    Spec: specs/answer-citations.md
(also specs/filings.md for the new `contrast` fields in `config/metric_definitions.yaml`)

Scope: the six items of the TL comment on #247 after PR #261 (issuecomment-7043870477), with
`docs/results/0247-reduce-2-check.md` section 6 findings 1-3 / section 8 findings 6-8 and PR #261 review
comments 7043282184 and 7043852742 (round 2 non-blocking 1-2, 4). Branch `tl/247-reduce-3` from origin/main
2f568c4. Owners (TL takeover): `src/cee/answer/*`, `specs/answer-citations.md` S2;
`config/metric_definitions.yaml`, `specs/filings.md` C1. Binding: ADR-021 rules 0-8 and its #246 / #247
amendments, CLAUDE.md ground rules and "Paid API calls".

**0 API calls.** No map, no reduce, no plan call. The answers are rebuilt by replaying the saved model outputs
in `docs/results/0247b-raw/` through the changed post-call code (as part 2's `replay-final`), and the changed
answers get a fresh blind re-score by a scorer agent (no API call). `.env` is never read or copied; no key is
needed or set.

Not touched (the #248 implementer works there in parallel): `scripts/eval_run.py`, `src/cee/app/*`,
`scripts/verify_cee.py`, `.claude/skills/verify-cee/*`. The replay imports `scripts/eval_run.py` unchanged
(from this branch, i.e. main 2f568c4). If any item turns out to need one of these files, I stop and ask.

## Plan review round 1 (issuecomment-7044195120): TL rulings, written in before any code
- Blocking 1-5 adopted exactly as the reviewer states: (1) every contrast value is a verbatim quote of its
  chunk or a fixed code phrase, with a DB test; EDJ Canada cites `EDJ-10K-2025#145` as a contrast-only id
  (DB-checked, not added to `see_also`); "Date of the registered count" replaces "last count"; the EDJ
  "(none: all advisors are employees)" text is removed; (2) unit-aware `closest_metric` wording; (3) a quarter
  hole is a run of at most 4 quarters with a covered quarter on both sides; (4) a same-date split is not a basis
  break; (5) a 0-call baseline replay on main 2f568c4, diffed against the branch replay for all 8 questions.
- Non-blocking 1-8 adopted; for 5, the same segment rule applies to `SERIES_SPAN`.

## TL approval conditions (plan approved at 9313a22 after review rounds 1-2, 7044195120 / 7044411488; TL 7044420979; written in before any code)
1. MS `business_lines` text = 'Wealth Management representatives' alone (verbatim); every `business_lines` cell
   has a `value` code from the allowed set; SCHW `independents` quotes the verbatim `SCHW-10K-2025#23` sentence
   'Through the Advisor Services segment, Schwab has become one of the largest providers of custodial,
   trading, banking, and support services to RIAs and their clients' (no gloss).
2. EDJ `independents` quotes `EDJ-10K-2025#35` 'The Partnership’s financial advisors are employees or partners
   of the Partnership.' (curly apostrophe U+2019) as a contrast-only id (DB-checked, not in `see_also`), value
   `stated`; "independents" is dropped from EDJ's `not_stated`; registry test: EDJ `not_stated` has no
   "independents".
3. Round-2 non-blocking 1-3: bare-year lookahead `(?!\d|,\d|\.\d)` with an "in 2024, ..." / "in 2025, ..." test;
   split rule: the whole-firm group is the one with an empty normalised scope, groups are never merged across
   population keys, periods compared as normalised strings; SCHW `written_definition` uses the item-2 wording
   ("publishes no count of this metric; reports a related figure instead").

## Goal
The post-call code fixes the answer problems the part-2 blind scorers named, with no new model output:
Q11 names how the five headcount definitions differ, side by side, by code, in the firms' own words; a
`closest_metric` firm is said to define a related metric (or, when the unit differs, to report a related
figure), never "no definition"; a "by quarter" series names short holes inside a firm's own series; the dedupe
treats bare and fiscal years as stated periods; a Merrill gap row suggests only Merrill's parent's missing
sources; an undated item never makes a basis, and parts of one date are not a break.

## 1. Q11 code-built contrast of the definitions (TL item 1; findings 3 / 8; review blocking 1, nb 1, nb 7)
**Today**: `matrix.definitions_by_firm` (R6a) writes one long caveat that lists each firm's quote, includes,
excludes and not-stated items one firm after another. The r3 scorer: "differences are listed per firm in a
caveat but never contrasted explicitly".

**Design**: a code caveat per contrast dimension, built from the registry only (no model text, no new fact).
- Registry (`config/metric_definitions.yaml`): a top-level `contrast_dimensions` map, today only for
  `advisor_headcount`, an ordered list of `{key, label}`: `written_definition` ("Written definition"),
  `independents` ("Independent contractor advisors"), `trainees` ("Trainees"), `business_lines` ("Business
  lines in the count"), `count_date` ("Date of the registered count"). Each `advisor_headcount` entry gets a
  `contrast` map `key -> {value, text, chunk_id, date}`:
  - `value` in `stated | counted | excluded | count_only | none | not_stated`.
  - **Text rule** (blocking 1): `text` is either a **verbatim substring** of `chunk_id` (whitespace collapsed,
    checked against the DB like `quote`; shown in single quotes in the caveat) or empty, in which case code
    prints a **fixed phrase** for the value ("states a definition", "a count with no written definition", "no
    advisor count", "counted", "excluded", "not stated"). No free paraphrase reaches the answer.
  - `chunk_id` required for every value except `not_stated`; it must be the entry's `chunk_id`, one of its
    `see_also`, or a **contrast-only id** listed in the entry's new `contrast_ids` field (DB-checked to exist;
    never added to `see_also`, so pins and map inputs do not change; the replay depends on it, section 7).
  - `count_date` carries `date` (ISO) and a verbatim `text` (the count line); rendered "<date> ('<text>',
    <chunk_id>)".
  - Values, each checked against the chunk text (the reviewer read every chunk; table in the review):

    | Dimension | MS | Schwab | EDJ | Merrill (Bank of America) | RJF |
    |---|---|---|---|---|---|
    | written_definition | count_only, 'Wealth Management representatives 15,950' (MS-SUPP-2020Q4#1) | none: "publishes no count of this metric; reports a related figure instead", 'perform investment advisory functions (including research)? 4127' (SCHW-ADV1A-2026#1) | count_only, 'Financial advisors (actual)' (EDJ-10K-2025#130) | stated, 'Includes advisors across all wealth management businesses in GWIM and Consumer Banking' (BAC-SUPP-2023Q4#2) | stated, 'Advisors in our RCS division are not included in our financial advisor metric' (RJF-10K-2025#228) |
    | independents | not_stated | none ("no advisor count"), 'Through the Advisor Services segment, Schwab has become one of the largest providers of custodial, trading, banking, and support services to RIAs and their clients' (SCHW-10K-2025#23) | stated, 'The Partnership’s financial advisors are employees or partners of the Partnership.' (EDJ-10K-2025#35, contrast-only id) | not_stated | counted, 'Independent contractors 5,065' (RJF-10K-2025#227) |
    | trainees | not_stated | not_stated | not_stated | not_stated | counted, 'new recruits and trainees that were moved into production roles' (RJF-10K-2025#228) |
    | business_lines | counted, 'Wealth Management representatives' (MS-SUPP-2020Q4#1) | none ("no advisor count") | counted, 'two operating and reportable segments based upon geographic location, the U.S. and Canada' (EDJ-10K-2025#145, contrast-only id) | counted, 'all wealth management businesses in GWIM and Consumer Banking' (BAC-SUPP-2023Q4#2) | excluded, 'Advisors in our RCS division are not included' (RJF-10K-2025#228) |
    | count_date | 2020-12-31, 'Wealth Management representatives 15,950' (MS-SUPP-2020Q4#1) | none (no advisor count) | 2025-12-31, 'At year end 20,425' (EDJ-10K-2025#130) | 2023-12-31, 'Total wealth advisors (3) 18,916' (BAC-SUPP-2023Q4#2) | 2025-09-30, 'Total advisors 8,943' (RJF-10K-2025#227) |

    No "last", "wider than Merrill" or "current" wording: those are absence or inference claims no chunk makes.
  - The EDJ `not_stated` item "independents (none: all advisors are employees)" is **removed** (TL condition
    2: `EDJ-10K-2025#35` states who EDJ advisors are, quoted in the contrast; "none" was an inference). It
    reached Q11, Q23 and Q24 through `DEFINITIONS_BY_FIRM`. Replay-safe: `not_stated` feeds neither the pins,
    nor `widen_words`, nor the reduce message. EDJ `contrast_ids: [EDJ-10K-2025#145, EDJ-10K-2025#35]`.
- **Parent named** (nb 1): when a BAC passage stands for the Merrill row, the row reads "Merrill (Bank of
  America, BAC-SUPP-2023Q4#2)", in the contrast and in `DEFINITIONS_BY_FIRM`, so a BAC footnote never reads as
  Merrill's own words.
- Code (`matrix.definitions_contrast(m) -> list[str]`): runs only when the question has an aspect whose
  `metric` has `contrast_dimensions` **and** whose text asks for a definition (`\bdefin|\binclud|\bexclud`),
  with >= 2 firm rows; **one block per metric** however many aspects match (nb 7). One caveat per dimension,
  firms grouped by value, in row order: `DEFINITION_CONTRAST = "Advisor headcount, how the definitions differ
  - {label}: {parts}."`, e.g. "... - Independent contractor advisors: counted by Raymond James Financial
  ('Independent contractors 5,065', RJF-10K-2025#227); stated by Edward Jones ('The Partnership’s financial
  advisors are employees or partners of the Partnership.', EDJ-10K-2025#35); no advisor count at The Charles
  Schwab Corporation ('Through the Advisor Services segment, Schwab has become one of the largest providers of
  custodial, trading, banking, and support services to RIAs and their clients', SCHW-10K-2025#23); not stated
  by Morgan Stanley, Merrill (Bank of America)." A dimension where every firm is
  `not_stated` is skipped. Placed in `build_caveats` right after the `DEFINITIONS_BY_FIRM` caveat (which stays:
  it carries the full quotes).
- Which questions: Q11 only (a1 "How each firm defines ...", a3 / a4 "... includes / excludes", metric
  `advisor_headcount`). Q23 a1, Q24 a3 and Q26 a7 have the metric but no definition words; Q24 a4 has the words
  but no metric; Q22 a2 has no metric and `net_new_assets` gets no dimensions in this part.
- Tests (`tests/test_series_coverage.py`, `tests/test_metric_definitions.py`):
  - a Q11-shaped matrix (five firm rows, metric aspects a1-a4) gets one caveat per non-empty dimension, in
    dimension order, each naming every firm once (grouped), with the chunk ids; **one block** although a1, a3
    and a4 all match;
  - the Merrill row names Bank of America as the source of a BAC passage (contrast and by-firm caveat);
  - a Q23-shaped (series, no definition words) and a Q24-shaped matrix get none; one firm row gets none;
  - registry (no DB): every `contrast` key is a listed dimension; every value is in the allowed set; every
    value except `not_stated` has a `chunk_id` that is the entry's `chunk_id`, in `see_also` or in
    `contrast_ids`; `contrast_ids` are not in `see_also`; `count_date.date` is an ISO date; `text` is a plain
    `str`; every `business_lines` cell has a value code; the EDJ `not_stated` list has no "independents"
    item at all (TL condition 2);
  - registry (DB up, as the `quote` test): every non-empty `text` is a verbatim substring of its `chunk_id`
    (whitespace collapsed; the EDJ #35 quote keeps U+2019); every `contrast_ids` chunk exists; MS
    `business_lines` text == 'Wealth Management representatives'.

## 2. `closest_metric` wording (TL item 2; findings 2 / 6; review blocking 2)
**Today**: `definitions_by_firm` heads a `closest_metric` entry with "publishes no definition of this metric;
closest metric '<quote>'". Wrong for Schwab NNA (core NNA, `SCHW-10K-2025#119`) and BAC NNA (net client AUM
flows, `BAC-10K-2025#249`).
**Design** (unit-aware):
- `closest_metric` entry whose `unit` equals the unit of the metric's `quoted` entries: "defines a related
  metric instead: '<quote>' (<chunk_id>)" (Schwab NNA, BAC NNA: unit USD).
- `closest_metric` entry whose `unit` differs: "publishes no count of this metric; reports a related figure
  instead: '<quote>' (<chunk_id>)" (Schwab headcount: `employees` vs `advisors`; Item 5.B(1) is the SEC's Form
  ADV question, not a Schwab definition).
- `not_disclosed` keeps "publishes no definition or count; nearest text".
**Tests**: update `test_r6a_definitions_by_firm_named_without_a_comparison_aspect` (line 249 asserts the old
words); new: a Q22-shaped Schwab NNA entry reads "defines a related metric instead" and never "publishes no
definition"; a Schwab-headcount-shaped entry (unit `employees`) reads "publishes no count of this metric;
reports a related figure instead".
**Answers changed**: every answer with a `DEFINITIONS_BY_FIRM` caveat that names Schwab or BAC: Q11, Q22, Q23,
Q24.

## 3. Holes in a "by quarter" series with no range (TL item 3; finding 7; review blocking 3, nb 5)
**Today**: Q22 asks "by quarter" with no range, so `asked_periods` is None and `period_gaps` adds nothing; EDJ
reports Q4 only inside its 10-K year figures, so 2024Q4 and 2025Q4 are neither listed nor marked.
**Design** (`matrix.quarter_holes(m, source)`, called from `build_gaps` after `period_gaps`):
- Applies when `asked_periods(question)` is None, the aspect is `kind == "series"` and the aspect or question
  text says `by quarter | each quarter | per quarter | quarterly`.
- For each holding firm cell (no research cell, no non-holding cell): its quarters = `_covers(period,
  "quarter")` of its valued counting items (a year or FY item covers no quarter).
- **Hole** = a run of consecutive quarters the firm does not cover, with a covered quarter on **both** sides,
  and the run is **at most 4 quarters** (`HOLE_MAX = 4`). A longer run separates two series segments and is not
  a hole. Only quarters that at least one other holding firm cell of the aspect covers are named (no hole
  claimed where nobody reports).
- Gap (label `period_gap`, `periods` listed, `suggested_source` as other period gaps):
  `QUARTER_HOLES = "{firm} - {aspect}: not found for {periods} in the documents searched (inside its series
  {first}-{last}; other firms report these quarters)."` where first / last are the segment's bounds.
- Q22 (replayed matrix, 0 calls): EDJ 2024Q2..2026Q2 -> **2024Q4, 2025Q4** (runs of 1); MS has 2019Q4, 2020Q3,
  2020Q4 then 2024Q3..2026Q3: the 2021Q1-2024Q2 run is 14 quarters -> no hole (no false MS 2024Q2 gap; its
  figure is in the corpus, `MS-10Q-2025Q2#56`, not in Q22's pool); 2020Q1-Q2 is a 2-quarter hole but no other
  firm covers those quarters -> not named. Schwab and RJF none; Merrill is a different-quantity cell -> none.
  Q23 has asked periods (its existing period gaps stay); no other replayed question has a series aspect.
- **`SERIES_SPAN` segments** (nb 5, TL: same rule): the span caveat reports the **latest segment** (split at
  runs of more than `HOLE_MAX` missing quarters) and names earlier points separately: "... runs from {first} to
  {last} ({n} points; earlier points {e_first}-{e_last}, {k} points, are a separate segment); no figure after
  {last} was found." Q22 MS: 2024Q3 to 2026Q3 (9 points; earlier 2019Q4-2020Q4, 3 points). Q23 spans (dated
  items mapped to quarters for the segment split only; printed periods stay as today): MS 2019-12-31..2020-12-31
  one segment; EDJ one segment; RJF fiscal year-ends (2023-09-30, 2024-09-30, 2025-09-30: 3-quarter runs) one
  segment -> Q23 span text unchanged.
- No figure is inferred (no Q4 = year minus nine months: ground rule 4).
**Tests** (`tests/test_series_coverage.py`): the Q22 EDJ shape -> one gap naming 2024Q4, 2025Q4; **the Q22 MS
shape -> no gap**; a 5-quarter run -> no gap; a hole at a series end (no covered quarter after it) -> none; a
hole no other firm covers -> not named; an asked-periods question ("last eight quarters") -> no `quarter_holes`
gap; a fact aspect -> none; a year-only cell -> none; `SERIES_SPAN` for the Q22 MS shape names the latest
segment and the earlier one; the Q23 RJF shape keeps one segment.

## 4. Dedupe: bare and fiscal years are stated periods (TL item 4; PR #261 round 2 nb 1; review nb 4)
**Today**: `reduce._stated_periods` reads dates and quarter labels only, so "$17 billion for fiscal 2024" and
"$17 billion for fiscal 2025, the table shows" are one claim to the dedupe.
**Design**: `_stated_periods` (it already gets the outside-quotes text) also adds every year: `fiscal 2024`,
`fiscal year 2024`, `FY2024`, `FY 2024` -> `fy2024`; a bare year -> `2024`. **Anchoring** (nb 4): a bare year is
`(?<![\d$.,])(?:19|20)\d{2}(?!\d|,\d|\.\d)` (TL condition 3) so "$2,024", "2,024 advisors" and "2024.5" are
not years while "in 2024, net new assets ..." is. A year
inside a matched date is added too (both claims of a pair are read the same way). This only makes the dedupe
keep more, never remove more.
**Tests** (`tests/test_reduce_noise.py`): the reviewer's fiscal 2024 / fiscal 2025 pair -> both kept; "in 2024"
vs "in 2025" -> both kept; an exact repeat with the same year -> still removed; "$2,024 million" / "2,024
advisors" give no year; "in 2024, net new assets were $5 billion" vs "in 2025, net new assets were $5
billion" -> both kept; the existing three dedupe tests unchanged.
**Expected in the replay**: no removal changes. A 0-call check of the replayed answers' removals with the year
rule found no pair whose year sets differ: Q11 2, Q19 4, Q26 1, the others 0, the same claims as
`replay-final`.

## 5. Merrill gap rows list only Merrill's sources (TL item 5; PR #261 round 2 nb 2; review nb 2)
**Cause** (0 calls, registry on `cee`): every MER registry doc type (`adv`, `press`, `trade`) is ingested,
so `suggested_sources("MER")` returns "", the code gap keeps an empty `suggested_source`, and
`fill_suggested_sources` fills it with all five firms' missing sources ("Morgan Stanley Form 8-K ...").
**Design** (`src/cee/answer/validate.py`):
- `suggested_sources(entity)`: when the firm's own missing list is empty and the entity has a `parent` in
  `config/entities.yaml` (MER -> BAC, `reported_as: GWIM`), return the parent's list with the parent named:
  "Not yet in the corpus (parent Bank of America): Bank of America Form 8-K current report (SEC EDGAR); Bank of
  America Proxy statement (SEC EDGAR)". No parent and nothing missing -> "".
- `fill_suggested_sources`: a gap whose `part_id` ends in `.<entity>` of a configured firm gets only that
  firm's `suggested_sources` (empty stays empty); aspect-level and research gaps (`a4`, `a3.research`) keep
  today's all-firms fill, so Q1 / Q19 / Q26 rows do not change. `_sources_for` handles the "(parent ...)"
  prefix when it joins several firms (one line, parent named).
- `empty_retrieval_answer` also uses `suggested_sources`, so a Merrill-only question with no retrieval gets the
  parent's list too (nb 2): stated in the spec, tested.
**Tests** (`tests/test_validate.py`, fake `registry_lookup`): MER with nothing missing -> BAC's list with the
"(parent Bank of America)" prefix; a `.MER` gap with an empty source is never filled with another firm's
sources; an aspect-level gap still gets the joined list (the existing Q28 test unchanged); a firm with nothing
missing and no parent -> ""; `empty_retrieval_answer` for a Merrill-only query names the parent's sources.
**Answers changed**: the `.MER` rows of Q11 (a4.MER), Q22 (a1.MER, a2.MER), Q23 (a1.MER), Q24 (a1.MER).

## 6. Basis breaks: undated items and same-date splits (TL item 6; finding 1; review blocking 4, nb 3)
**Today**: R3 drops an undated item only when it has no population; R2's whole-quote fallback tagged the
undated RJF "approximately 9,000" PCG items (`rjf_advisors_excl_rcs`, scopes "domestic wealth management
businesses" and "Financial Institutions Division"), so Q23 gets an RJF `BASIS_BREAK` caveat ("... period not
stated"). Q11 a2.EDJ gets a break for whole firm / U.S. / Canada, all 2026Q2: parts of one count, not a change
of basis.
**Design** (`matrix.basis_breaks`):
- An item with no period never opens a group: it joins an existing dated group with its key (adds no period),
  else it is skipped. A cell whose items are all undated has no break.
- **Same-date split** (TL ruling, blocking 4; condition 3): the whole-firm group(s) are those with an empty
  normalised scope. A group with a non-empty scope whose dated periods (normalised strings, `_period_key`
  where parseable) are all periods of a whole-firm group **with the same population key** is a split, not a
  break, and is dropped before counting groups. With no whole-firm group, groups with the same population key
  and identical period sets are a split (kept as one). Groups are never merged across population keys: two
  whole-firm groups with different keys stay a break. Only >= 2 groups left -> break.
**Tests** (`tests/test_series_coverage.py`): the Q23 RJF shape (three dated whole-firm items + two undated
keyed items with other scopes) -> no break; **the Q11 a2.EDJ shape (whole firm, U.S., Canada, all 2026Q2) -> no
break**; no whole-firm group, two scopes with the same periods -> no break; two whole-firm groups with
different population keys -> still a break; periods "2026Q2" vs "2026-06-30" compared normalised; the Q23 EDJ-shaped test (whole firm
2025Q3 and 2026Q2; U.S. and Canada 2026Q1) and the r3 `m2` case (whole firm 2026Q2; U.S. 2026Q1) **still
break**; the existing parametrised cases unchanged; the R3 test adjusted where it expects "period not stated".
**Answers changed**: Q23 (RJF break caveat gone), Q11 (a2.EDJ and a2.MER break caveats gone).
**Merrill ">15K" scope** (nb 3): the a2.MER break was the only flag on the Investor Day item
(`BAC-DECK-2025-investor-day#9`, "as of 3Q25", scope Merrill and Private Bank). After the change, the scope
difference still shows in the claim / adjacent text itself (the model's item names "Merrill and the Private
Bank"), in the "GWIM is not Merrill" config caveat, and in the contrast's business-lines line for BAC ('all
wealth management businesses in GWIM and Consumer Banking'); the results doc states where, from the replayed
answer.

## 7. Replay method (0 calls), the baseline, and the guard (review blocking 5, nb 6, nb 8)
- Seed the run cache, `<wt>\.eval-runs\cache\`, with **only** the committed records: copy
  `docs/results/0247b-raw/*.json` (not the verdict files, not the `.failed-1` record; 56 records, 50 used). No
  record comes from another worktree.
- Script `D:\ALLPROJECTS\EDJ\cache\ev247c\diag\replay_part3.py` = part 2's `replay_final.py` with the same
  eight scored reduce keys (Q1 f838663112cf225554f12a4b, Q3 ec259fc6b468c54a5288cdfa, Q11
  5dbbeb66472889c98d524e8e, Q19 69b98fa4852035ea030220f3, Q22 603b706048ab5e01f5dd9962, Q23
  523be48cb96f26a1243000a7, Q24 1d076b546886900b14903e07, Q26 cbf122e21a570a271289cb24); it asserts each
  file exists and pins `eval_run.reduce_cache_key` to it; plans and maps hit the cache by their own keys.
  Wrappers `replay.ps1` / `replay.sh` (Windows and Mac; parameter: worktree, out dir) set the part-2 run
  settings (`LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL`,
  `DEEPSEEK_THINKING=on`, `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=6`,
  `PYTHONPATH=<wt>\src`), **set `DEEPSEEK_API_KEY` to empty**, and run `eval_run.py --real --max-calls 0
  --questions Q1,Q3,Q11,Q19,Q22,Q23,Q24,Q26 --as-of 2026-11-17 --out <out>`.
- **Baseline** (blocking 5): the same wrapper, seed and guard on a detached worktree of **main 2f568c4**
  (`D:\ALLPROJECTS\EDJ\wt-247c-base`) -> `ev247c\replay-base`. The branch replay -> `ev247c\replay`. Both dumped
  with `dump247b.py` (copied to `ev247c\`), split per question and diffed **branch vs baseline for all eight**.
  Separately reported: the known part-2 differences of the baseline against the scored dumps (`blind-in` Q1:
  the a4.MS gap wording from R6b; Q24 only the trailing separator; everything else identical to
  `blind-in` / `blind-in-r2` / `blind-in-r3`).
- If #248 merges into main before the diff and changes `eval_run.py` (nb 8), the baseline is redone on the new
  main and this branch is rebased before the branch replay.
- **0-call guard** (both runs; all must hold, else stop and report; no retry with a key):
  1. `--max-calls 0` (the runner refuses any call over the cap, after the cache lookup) and no key in the
     environment, no `.env` in the worktree (checked before and after);
  2. code gate: `git status` clean and the run's commit recorded;
  3. after the run: `meta.real_calls == 0`, `meta.reused == 50`, every question logs "model cached";
  4. `docs/results/0247b-raw/` unchanged (`git status` clean there) and every file in `<out>\raw\` byte-identical
     to its `0247b-raw` record (no new record).
- Limitation, as in part 2: the model wrote its text against the old reduce message (which held the RJF and
  MER breaks and the old wording); code attaches the new caveats and gaps after the call. The diff review checks
  whether any claim text still refers to a removed break or the old "no definition" wording, and reports it
  (nb 6); claims are not edited.

## 8. Expected changes per question (branch replay vs baseline replay)

| Q | Changes | By item |
|---|---|---|
| Q1 | none | - |
| Q3 | none | - |
| Q11 | contrast caveats (5 dimensions at most, one block; EDJ independents quoted from #35); Schwab "publishes no count ...; reports a related figure instead"; Merrill rows name Bank of America; EDJ "not stated" without any independents item; a4.MER source = parent's; a2.EDJ and a2.MER break caveats gone | 1, 2, 5, 6 |
| Q19 | none | (4: removals unchanged) |
| Q22 | Schwab and Merrill NNA "defines a related metric instead" (Merrill naming Bank of America); gaps EDJ 2024Q4, 2025Q4 (no MS gap); MS `SERIES_SPAN` latest segment 2024Q3-2026Q3 + earlier segment; a1.MER / a2.MER source = parent's | 2, 3, 5 |
| Q23 | Schwab "publishes no count ...; reports a related figure instead"; Merrill naming Bank of America; EDJ "not stated" without any independents item; RJF break caveat gone; a1.MER source = parent's | 1 (registry text), 2, 5, 6 |
| Q24 | as Q23 for the by-firm caveat; a1.MER source = parent's | 1 (registry text), 2, 5 |
| Q26 | none | (4: removal unchanged) |

Claims are unchanged in every question (no item adds or removes a claim; item 4 changes no removal). Any
difference from this table is reported and explained before the re-score.

## 9. Blind re-score inputs (0 API calls)
- `D:\ALLPROJECTS\EDJ\cache\ev247c\blind-in\`: `answers-dump.txt` with **only the answers that differ from the
  baseline** (expected Q11, Q22, Q23, Q24, as replayed), `questions.yaml` (copied from `evals/questions.yaml`),
  `verdict-rule.txt` (r3's rule, question list updated; Q24 against `answer` per `behavior_supersede.yaml`, as
  r3). Nothing else: no earlier verdicts, no plan, no diff. Hashes in `ev247c\blind-in-hashes.txt`.
- `ev247c\scorer-prompt.txt` (r3's prompt, paths changed) for a fresh scorer agent that writes
  `ev247c\verdicts-blind.json`. The TL starts the scorer; I prepare the inputs and stop.
- After scoring: copy to `docs/results/0247c/verdicts-blind.json`; commit its sha256 alone in the results doc
  first, then the verdicts and the comparison. Unchanged answers keep their part-2 verdicts (Q1, Q3, Q19, Q26
  PASS).

## Files to change
- `src/cee/answer/matrix.py` - `definitions_contrast` + `DEFINITION_CONTRAST`, parent naming (1);
  unit-aware `closest_metric` head (2); `quarter_holes` + `QUARTER_HOLES` in `build_gaps`, `SERIES_SPAN`
  segments (3); `basis_breaks` undated and same-date-split rules (6).
- `src/cee/answer/reduce.py` - `_stated_periods` years, anchored (4).
- `src/cee/answer/validate.py` - `suggested_sources` parent fallback with prefix, `_sources_for`,
  `fill_suggested_sources` per firm (5).
- `config/metric_definitions.yaml` - `contrast_dimensions`, the five `advisor_headcount` `contrast` maps, EDJ
  `contrast_ids: [EDJ-10K-2025#145]`, EDJ `not_stated` text fix; header lines for the new fields (1).
- `tests/test_series_coverage.py`, `tests/test_reduce_noise.py`, `tests/test_validate.py`,
  `tests/test_metric_definitions.py` - the tests above.
- `specs/answer-citations.md` - "Reduce part 3" lines (1-6, the empty-retrieval parent list);
  `specs/filings.md` - the `contrast` / `contrast_ids` fields (1).
- `docs/results/0247-reduce-3-check.md` - checks, replay diffs, scoring (new); `docs/results/0247c/` - verdicts.
- `plans/0247-reduce-3.md` - this plan, Progress log.
- ADR-021 is not amended (these are code caveats / gaps under its rules 2-3, described in the spec). Not
  touched: `scripts/eval_run.py`, `src/cee/app/*`, `scripts/verify_cee.py` (#248).

## Steps
1. Plan (this file), reviewed. 2. Item 6, 4, 2, with tests. 3. Item 5, with tests. 4. Item 3 (+ span
segments), with tests. 5. Item 1 registry + code, with tests (DB test run locally with `cee-db` up). 6. Full
pytest; mock 35 vs main 2f568c4 (`compare_mock.py`); verify-cee. 7. Baseline replay on main, branch replay,
guards, diffs; the results doc. 8. Prepare the blind inputs (section 9) and stop for the TL's scorer. 9. Commit
the verdict hash alone, then verdicts and comparison; `/finish-task`.

## Acceptance
- [ ] pytest passes (count before and after recorded, DB tests included); `gh pr checks` green.
- [ ] Mock 35 vs main 2f568c4: every chunk list identical (no retrieval change), statuses and refusal
      unchanged, mock answer code checks 0.
- [ ] verify-cee VERIFY PASS (open-citation / download-document may be UNREACHABLE without raw files, as in
      part 2).
- [ ] Replay guard 1-4 holds on both runs: **0 API calls**, 50 records reused, no new raw record.
- [ ] Branch replay vs baseline replay: Q1, Q3, Q19, Q26 byte-identical; Q11, Q22, Q23, Q24 change only as in
      section 8; dedupe removals as in the baseline (Q11 2, Q19 4, Q26 1). Baseline vs scored dumps: only the
      known part-2 differences (Q1 a4.MS gap wording, Q24 separator).
- [ ] Every contrast `text` verbatim in its chunk (DB test) or a fixed phrase; every `business_lines` cell
      has a value code; no "last" / "wider" / "none: all advisors are employees" in any answer; EDJ
      independents shown with the `EDJ-10K-2025#35` quote, and EDJ's "not stated" list (Q11, Q23, Q24) has no
      independents item.
- [ ] Q11: the answer has the code contrast (each dimension, every firm placed, chunk ids, one block) and the
      unit-aware wording, and no a2.EDJ / a2.MER break caveat. **Aim: PASS** on the fresh blind re-score. A
      FAIL is reported with the scorer's reason, and what is corpus (no written MS / EDJ definition, no Schwab
      count; section 5 of the part-2 doc) and what is answer is stated.
- [ ] Q22: EDJ 2024Q4 / 2025Q4 holes named, no MS 2024Q2 gap, MS span by segment.
- [ ] Q23: RJF break caveat gone, Merrill row sources. It **stays a corpus gap** (MS after 4Q2020, RJF
      quarterly, BAC after 4Q2023, EDJ 3Q26) unless the re-score passes it; a FAIL of class c is expected
      and is not a regression.
- [ ] **No PASS -> FAIL** on the re-score (Q22, Q24 keep PASS). A PASS -> FAIL stops the merge and goes to
      the TL with the scorer's reason; nothing is re-rolled.
- [ ] Claim texts referring to a removed break or the old wording: counted and reported (nb 6).
- [ ] Linked questions: Q11, Q22, Q23, Q24 (changed); Q1, Q3, Q19, Q26 (unchanged).

## Risks
- `HOLE_MAX = 4` is a judgement: a longer missing run is read as two series segments, not a hole. It removes
  the false MS 2024Q2 gap (its figure is in `MS-10Q-2025Q2#56`, outside Q22's pool) and keeps EDJ's Q4 holes.
- The same-date split rule could hide a real change of basis that happens at one date; a break needs different
  periods, which is what a series break is.
- Item 6 removes Q11's a2.MER break; the Merrill / Private Bank scope still shows in the item text, the GWIM
  config caveat and the contrast (section 6).
- Q11 may still fail on "five definitions, quoted": MS and EDJ publish none, Schwab no count (corpus, section 5
  of the part-2 doc); the contrast says so per firm, in their own words.
- The model's claims were written against the old reduce message (section 7 limitation).

## Progress log
- 2026-11-20 09:55 - plan written (0 calls). Diagnosis with 0 calls: the replay inputs (`replay-final`
  matrices), the dedupe removals under the year rule, the MER registry (`suggested_sources("MER") == ""`).
- 2026-11-20 10:40 - plan review round 1 RETURN (issuecomment-7044195120); TL rulings adopted (all blocking
  1-5, non-blocking 1-8; nb 5 applied to `SERIES_SPAN`). Checked in the DB (0 calls): `EDJ-10K-2025#145` holds
  "the U.S. and Canada"; `RJF-10K-2025#227` "Independent contractors 5,065 ... Total advisors 8,943";
  `BAC-SUPP-2023Q4#2` "Total wealth advisors (3) 18,916"; `SCHW-10K-2025#23` "support services to RIAs and their
  clients". Amended: sections 1-9, Files, Steps, Acceptance, Risks.
- 2026-11-20 11:20 - plan review round 2 RETURN (7044411488); TL approved at 9313a22 on conditions
  (7044420979), written in above (TL approval conditions 1-3; sections 1, 4, 6, 8, Acceptance) before any code.
- 2026-11-20 11:10 - code at 02a57c2 (items 1-6 with the TL conditions). Tests: the new cases are in one new
  file, `tests/test_reduce_part3.py` (26 tests: contrast, wording, holes / segments, breaks, years, gap
  sources, registry shape and the DB verbatim check), instead of spreading them over `test_series_coverage.py`,
  `test_reduce_noise.py`, `test_validate.py`, `test_metric_definitions.py`; `test_series_coverage.py` has the
  one updated r6a assertion. pytest 972 -> 998 (one Streamlit timing flake in `test_ask_page_trace.py`,
  passed on re-run).
- 2026-11-20 11:30 - mock 35 vs main 2f568c4: retrieval, statuses and claims identical; verify-cee VERIFY PASS
  (`.verify-runs/20261120-111924-02a57c2`). Baseline replay (main, `wt-247c-base`) and branch replay: guard OK
  on both (0 calls, 50 reused, 8/8 cached, raw records identical to the committed blobs). Diff: Q1, Q3, Q26
  identical; Q11, Q22, Q23, Q24 as section 8; **Q19 also changed** (not in section 8): the folded competitor
  gap rows now carry Merrill's parent sources (item 5 via `COMPETITORS_GAP`), so Q19 joins the blind set.
  Blind inputs prepared (`ev247c\blind-in\`: Q11, Q19, Q22, Q23, Q24); stopped before scoring.
- 2026-11-20 11:35 - TL fix before scoring: the per-firm definitions caveat printed the registry's free-text
  includes (EDJ "U.S. and Canada ... (split in EDJ-10K-2025#148)": #148 has no "Canada"). Now it prints only
  verbatim contrast texts with their chunks (EDJ #145) or "not stated: <labels>"; free-text lists stay in the
  registry for the map's words (pins and map inputs unchanged). Two new tests (fixed words outside quotes;
  every quote verbatim in its cited chunk, DB). 22a6555: pytest 1000 passed; branch replay re-run (guard OK),
  re-diffed: only Q11 / Q23 / Q24 caveat text changed vs 02a57c2; blind inputs rebuilt.
- 2026-11-20 12:20 - blind 3/5 (hash 676eb3c, verdicts b101ab4); final 6/8, no PASS -> FAIL. Scorer claims
  checked (0 calls): RJF trainees cell overstated -> `not_stated` (one config line); 2025-26 MS / BAC / RJF
  supplements carry no advisor count (corpus gap); RJF 2025Q1 (investor-day deck #43) is a Q23 retrieval miss.
  Merged main a1341d3 (#248); baseline re-run on it (identical to the 2f568c4 baseline) and branch replay
  (guard OK): Q11 / Q23 / Q24 differ from the scored answers only by the trainees fix -> stopped before
  marking ready; blind-in-r2 (Q11, Q23, Q24) prepared. pytest 1033 passed.
