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

## Goal
The post-call code fixes the answer problems the part-2 blind scorers named, with no new model output:
Q11 names how the five headcount definitions differ, side by side, by code; a `closest_metric` firm is said to
define a related metric (not "no definition"); a "by quarter" series names the quarters missing inside a firm's
own series; the dedupe treats bare and fiscal years as stated periods; a Merrill gap row suggests only
Merrill's (its parent's) missing sources; an undated item never makes a basis of its own.

## 1. Q11 code-built contrast of the definitions (TL item 1; findings 3 / 8)
**Today**: `matrix.definitions_by_firm` (R6a) writes one long caveat that lists each firm's quote, includes,
excludes and not-stated items one firm after another. The r3 scorer: "differences are listed per firm in a
caveat but never contrasted explicitly".

**Design**: a new code caveat per contrast dimension, built from the registry only (no model text, no new fact).
- Registry (`config/metric_definitions.yaml`): a top-level `contrast_dimensions` map, today only for
  `advisor_headcount`, an ordered list of `{key, label}`:
  `written_definition` ("Written definition"), `independents` ("Independent contractor advisors"),
  `trainees` ("Trainees"), `business_lines` ("Business lines in the count"), `last_count` ("Last published
  count"). Each `advisor_headcount` entry gets a `contrast` map `key -> {value, text, chunk_id}`:
  - `value` in `stated | counted | excluded | not_stated | none`; `text` a short phrase (the firm's own words
    where it has them); `chunk_id` required for every value except `not_stated`, and it must be the entry's
    `chunk_id` or one of its `see_also` ids (the passages already verified for that entry). No new chunk
    reaches `see_also`, so **no pin and no map input changes** (the replay depends on it, section 7).
  - Values (all from the existing entries' quote / includes / excludes / not_stated / note):

    | Dimension | MS | Schwab | EDJ | Merrill (BAC) | RJF |
    |---|---|---|---|---|---|
    | written_definition | none: a count, no written definition (MS-SUPP-2020Q4#1) | none: no advisor count; closest Form ADV advisory employees (SCHW-ADV1A-2026#1) | none: a count "Financial advisors (actual)", no written definition (EDJ-10K-2025#130) | stated: footnote "Includes advisors across all wealth management businesses in GWIM and Consumer Banking" (BAC-SUPP-2023Q4#2) | stated: "Advisors in our RCS division are not included in our financial advisor metric ..." (RJF-10K-2025#228) |
    | independents | not_stated | excluded: independent RIAs are clients, not staff (SCHW-10K-2025#23) | not_stated | not_stated | counted: employees and independent contractors (RJF-10K-2025#227) |
    | trainees | not_stated | not_stated | not_stated | not_stated | counted once moved into production roles (RJF-10K-2025#228) |
    | business_lines | Wealth Management representatives (MS-SUPP-2020Q4#1) | n/a: no count | U.S. and Canada advisors (EDJ-10K-2025#148) | GWIM and Consumer Banking, wider than Merrill (BAC-SUPP-2023Q4#2) | excludes the RCS division (RJF-10K-2025#228) |
    | last_count | 2020-12-31, 4Q2020 supplement (MS-SUPP-2020Q4#1) | none | (not set: current) | 2023-12-31, 4Q2023 supplement (BAC-SUPP-2023Q4#2) | (not set: current) |

    The exact wording is fixed in the yaml; EDJ "independents" stays `not_stated` (the registry has no passage
    saying all EDJ advisors are employees).
- Code (`matrix.definitions_contrast(m) -> list[str]`): runs only when the question has an aspect whose
  `metric` has `contrast_dimensions` **and** whose text asks for a definition (`\bdefin|\binclud|\bexclud`),
  with >= 2 firm rows. One caveat per dimension, firms grouped by value, in row order:
  `DEFINITION_CONTRAST = "Advisor headcount, how the definitions differ - {label}: {parts}."`, e.g.
  "... - Independent contractor advisors: counted by Raymond James Financial (employees and independent
  contractors, RJF-10K-2025#227); excluded by The Charles Schwab Corporation (independent RIAs are clients,
  not staff, SCHW-10K-2025#23); not stated by Morgan Stanley, Edward Jones, Merrill." A dimension where every
  firm is `not_stated` is skipped. Placed in `build_caveats` right after the `DEFINITIONS_BY_FIRM` caveat
  (which stays: it carries the quotes).
- Which questions: Q11 only (a1 "How each firm defines ...", a3 / a4 "... includes / excludes", metric
  `advisor_headcount`). Q23 a1, Q24 a3 and Q26 a7 have the metric but no definition words; Q24 a4 has the words
  but no metric; Q22 a2 has no metric and `net_new_assets` gets no dimensions in this part.
- Tests (`tests/test_series_coverage.py`, `tests/test_metric_definitions.py`):
  - a Q11-shaped matrix (five firm rows, metric aspects a1-a4) gets one caveat per non-empty dimension, in
    the dimension order, each naming every firm once (grouped), with the chunk ids;
  - a Q23-shaped (series, no definition words) and a Q24-shaped matrix get none; one firm row gets none;
  - registry: every `contrast` value is in the allowed set; every value except `not_stated` has a
    `chunk_id` that is the entry's `chunk_id` or in its `see_also`; every `contrast` key is a listed
    dimension; `text` is a plain `str`.

## 2. `closest_metric` wording (TL item 2; findings 2 / 6)
**Today**: `definitions_by_firm` heads a `closest_metric` entry with "publishes no definition of this metric;
closest metric '<quote>'". Wrong for Schwab NNA (it defines core NNA, `SCHW-10K-2025#119`) and BAC NNA (net
client AUM flows, `BAC-10K-2025#249`).
**Design**: the head becomes "defines a related metric instead: '<quote>' (<chunk_id>)" (the registry's own
meaning of `closest_metric`, header line 10). `not_disclosed` keeps "publishes no definition or count".
Schwab headcount (also `closest_metric`, Form ADV Item 5.B(1)) then reads "defines a related metric instead:
'perform investment advisory functions (including research)? 4127'"; that is the Form ADV metric, and the
section-1 contrast says Schwab publishes no advisor count. (If the reviewer prefers "reports a related
figure instead" for an entry whose `unit` differs from the asked unit, that is one extra line; I keep the TL
wording unless told.)
**Tests**: update `test_r6a_definitions_by_firm_named_without_a_comparison_aspect` (line 249 asserts the old
words); new: a Q22-shaped Schwab NNA entry reads "defines a related metric instead" and never "publishes no
definition".
**Answers changed**: every answer with a `DEFINITIONS_BY_FIRM` caveat that names Schwab or BAC: Q11, Q22, Q23,
Q24.

## 3. Missing quarters inside a "by quarter" series with no range (TL item 3; finding 7)
**Today**: Q22 asks "by quarter" with no range, so `asked_periods` is None and `period_gaps` adds nothing; EDJ
reports Q4 only inside its 10-K year figures, so 2024Q4 and 2025Q4 are neither listed nor marked.
**Design** (`matrix.quarter_holes(m, source)`, called from `build_gaps` after `period_gaps`):
- Applies when `asked_periods(question)` is None, the aspect is `kind == "series"` and the aspect or question
  text says `by quarter | each quarter | per quarter | quarterly`.
- For each holding firm cell (no research cell, no non-holding cell): its quarters = `_covers(period,
  "quarter")` of its valued counting items (a year or FY item covers no quarter). Reference = the quarters
  covered by at least one **other** holding firm cell of the same aspect. Missing = reference quarters inside
  the firm's own first..last quarter that the firm does not cover. None missing -> no gap.
- Gap (label `period_gap`, `periods` listed, `suggested_source` as other period gaps):
  `QUARTER_HOLES = "{firm} - {aspect}: not found for {periods} in the documents searched (inside its series
  {first}-{last}; other firms report these quarters)."`
- Q22 (from the replayed matrix, 0 calls): EDJ 2024Q2..2026Q2 -> **2024Q4, 2025Q4**; MS (stray 2019Q4-2020Q4
  points, then 2024Q3..2026Q3) -> **2024Q2** (EDJ and RJF report it); Schwab and RJF none; Merrill is a
  different-quantity cell (not holding) -> none. Q23 has asked periods (its existing period gaps stay); no
  other replayed question has a series aspect.
- No figure is inferred (no Q4 = year minus nine months: ground rule 4).
**Tests** (`tests/test_series_coverage.py`): the Q22 EDJ shape -> one gap naming 2024Q4, 2025Q4; a firm whose
own span has holes no other firm covers -> none; quarters outside the firm's span -> not named; an
asked-periods question ("last eight quarters") -> no `quarter_holes` gap (only `period_gaps`); a fact aspect
-> none; a year-only cell -> none.

## 4. Dedupe: bare and fiscal years are stated periods (TL item 4; PR #261 round 2 non-blocking 1)
**Today**: `reduce._stated_periods` reads dates and quarter labels only, so "$17 billion for fiscal 2024" and
"$17 billion for fiscal 2025, the table shows" are one claim to the dedupe.
**Design**: `_stated_periods` also adds, outside quotes (it already gets the outside-quotes text), every
year: `fiscal 2024`, `fiscal year 2024`, `FY2024`, `FY 2024` -> `fy2024`; a bare `2024` -> `2024` (a year
inside a matched date is added too; both claims of a pair are read the same way). This only makes the dedupe
keep more, never remove more.
**Tests** (`tests/test_reduce_noise.py`): the reviewer's fiscal 2024 / fiscal 2025 pair -> both kept; "in 2024"
vs "in 2025" -> both kept; an exact repeat with the same year -> still removed; the existing three dedupe
tests unchanged.
**Expected in the replay**: no removal changes. A 0-call check of the eight replayed answers' removals with
the new year rule (each removed claim against the kept claims) found no pair whose year sets differ: Q11 2,
Q19 4, Q26 1, the others 0, the same claims as `replay-final`.

## 5. Merrill gap rows list only Merrill's sources (TL item 5; PR #261 round 2 non-blocking 2)
**Cause** (0 calls, registry on `cee`): every MER registry doc type (`adv`, `press`, `trade`) is ingested,
so `suggested_sources("MER")` returns "", the code gap keeps an empty `suggested_source`, and
`fill_suggested_sources` fills it with all five firms' missing sources ("Morgan Stanley Form 8-K ...").
**Design** (`src/cee/answer/validate.py`):
- `suggested_sources(entity)`: when the firm's own missing list is empty and the entity has a `parent` in
  `config/entities.yaml` (MER -> BAC, `reported_as: GWIM`), return the parent's missing list ("Not yet in
  the corpus: Bank of America Form 8-K current report (SEC EDGAR); Bank of America Proxy statement (SEC
  EDGAR)"). No parent and nothing missing -> "".
- `fill_suggested_sources`: a gap whose `part_id` ends in `.<entity>` of a configured firm gets only that
  firm's `suggested_sources` (empty stays empty); aspect-level and research gaps (`a4`, `a3.research`) keep
  today's all-firms fill, so Q19 / Q26 rows do not change.
**Tests** (`tests/test_validate.py`, fake `registry_lookup`): MER with nothing missing -> BAC's list; a
`.MER` gap with an empty source is never filled with another firm's sources; an aspect-level gap still gets
the joined list (the existing Q28 test unchanged); a firm with nothing missing and no parent -> "".
**Answers changed**: the `.MER` rows of Q11 (a4.MER), Q22 (a1.MER, a2.MER), Q23 (a1.MER), Q24 (a1.MER).

## 6. An undated item never makes a basis (TL item 6; finding 1)
**Today**: R3 drops an undated item only when it has no population; R2's whole-quote fallback tagged the
undated RJF "approximately 9,000" PCG items (`rjf_advisors_excl_rcs`, scopes "domestic wealth management
businesses" and "Financial Institutions Division"), so Q23 gets an RJF `BASIS_BREAK` caveat ("... period not
stated").
**Design** (`matrix.basis_breaks`): an item with no period never opens a group: it joins an existing dated
group with its key (adds no period), else it is skipped. A cell whose items are all undated has no break.
**Tests** (`tests/test_series_coverage.py`): the Q23 RJF shape (three dated whole-firm items + two undated
keyed items with other scopes) -> no break; a dated two-basis cell still breaks (the existing Q23 EDJ-shaped
and parametrised cases); the existing R3 test adjusted where it expects "period not stated".
**Answers changed**: Q23 (RJF break caveat gone) and Q11 (the a2.MER break "Merrill and Private Bank ...:
period not stated" is gone too: the ">15K" item is undated; the scope difference stays in the section-1
contrast, business lines). Q11's a2.EDJ break (whole firm / U.S. / Canada, all 2026Q2) is a split, not a
basis change; it is **not** in the six items and stays (noted for the TL, Risks).

## 7. Replay method (0 calls) and its guard
- Seed the run cache of this worktree, `wt-247c\.eval-runs\cache\`, with **only** the committed records:
  copy `docs/results/0247b-raw/*.json` (not the verdict files, not the `.failed-1` record). No record comes
  from another worktree.
- Script `D:\ALLPROJECTS\EDJ\cache\ev247c\diag\replay_part3.py` = part 2's `replay_final.py` with the same
  eight scored reduce keys (Q1 f838663112cf225554f12a4b, Q3 ec259fc6b468c54a5288cdfa, Q11
  5dbbeb66472889c98d524e8e, Q19 69b98fa4852035ea030220f3, Q22 603b706048ab5e01f5dd9962, Q23
  523be48cb96f26a1243000a7, Q24 1d076b546886900b14903e07, Q26 cbf122e21a570a271289cb24); it asserts each
  file exists and pins `eval_run.reduce_cache_key` to it; plans and maps hit the cache by their own keys.
  Wrappers `replay.ps1` / `replay.sh` (Windows and Mac) set the part-2 run settings (`LLM_PROVIDER=deepseek`,
  `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_THINKING=on`, `PLANNER=on`,
  `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=6`, `PYTHONPATH=<wt>\src`), **set
  `DEEPSEEK_API_KEY` to empty**, and run `eval_run.py --real --max-calls 0 --questions
  Q1,Q3,Q11,Q19,Q22,Q23,Q24,Q26 --as-of 2026-11-17 --out ev247c\replay`.
- **0-call guard** (all must hold, else stop and report; no retry with a key):
  1. `--max-calls 0` (the runner refuses any call over the cap) and no key in the environment, no `.env` in
     the worktree (checked before and after);
  2. code gate: `git status` clean and the run's commit recorded;
  3. after the run: `meta.real_calls == 0`, `meta.reused == 50`, every question logs "model cached";
  4. `docs/results/0247b-raw/` unchanged (`git status` clean there) and every file in `ev247c\replay\raw\`
     byte-identical to its `0247b-raw` record (no new record).
- Then: `dump247b.py` (copied to `ev247c\`) writes `ev247c\replay\answers-dump.txt`; split per question and
  diff against the scored dumps (`ev247b\blind-in\` for Q1 / Q3, `ev247b\blind-in-r3\` for Q11, Q22, Q23,
  Q24, `ev247b\blind-in-r2\` for Q19 / Q26). A limitation, as in part 2: the model wrote its text without
  seeing the new caveats and gaps; code attaches them after the call.

## 8. Expected changes per question

| Q | Changes | By item |
|---|---|---|
| Q1 | none (byte-identical to `blind-in`) | - |
| Q3 | none (byte-identical to `blind-in`) | - |
| Q11 | contrast caveats (5 dimensions at most); Schwab "defines a related metric instead"; a4.MER source = BAC's; a2.MER break caveat gone | 1, 2, 5, 6 |
| Q19 | none (byte-identical to `blind-in-r2`) | (4: removals unchanged) |
| Q22 | Schwab and Merrill NNA "defines a related metric instead"; gaps EDJ 2024Q4, 2025Q4 and MS 2024Q2; a1.MER / a2.MER source = BAC's | 2, 3, 5 |
| Q23 | Schwab "defines a related metric instead"; RJF break caveat gone; a1.MER source = BAC's | 2, 5, 6 |
| Q24 | Schwab "defines a related metric instead"; a1.MER source = BAC's | 2, 5 |
| Q26 | none (byte-identical to `blind-in-r2`) | (4: removal unchanged) |

Claims are unchanged in every question (no item adds or removes a claim; item 4 changes no removal). Any
difference from this table is reported and explained before the re-score.

## 9. Blind re-score inputs (0 API calls)
- `D:\ALLPROJECTS\EDJ\cache\ev247c\blind-in\`: `answers-dump.txt` with **only the changed answers** (expected
  Q11, Q22, Q23, Q24, as replayed), `questions.yaml` (copied from `evals/questions.yaml`), `verdict-rule.txt`
  (r3's rule, question list updated; Q24 against `answer` per `behavior_supersede.yaml`, as r3). Nothing
  else: no earlier verdicts, no plan, no diff. Hashes in `ev247c\blind-in-hashes.txt`.
- `ev247c\scorer-prompt.txt` (r3's prompt, paths changed) for a fresh scorer agent that writes
  `ev247c\verdicts-blind.json`. The TL starts the scorer; I prepare the inputs and stop.
- After scoring: copy to `docs/results/0247c/verdicts-blind.json`; commit its sha256 alone in the results doc
  first, then the verdicts and the comparison. Unchanged answers keep their part-2 verdicts (Q1, Q3, Q19, Q26
  PASS).

## Files to change
- `src/cee/answer/matrix.py` - `definitions_contrast` + `DEFINITION_CONTRAST` (1); `closest_metric` head (2);
  `quarter_holes` + `QUARTER_HOLES`, called in `build_gaps` (3); `basis_breaks` undated rule (6).
- `src/cee/answer/reduce.py` - `_stated_periods` years (4).
- `src/cee/answer/validate.py` - `suggested_sources` parent fallback, `fill_suggested_sources` per firm (5).
- `config/metric_definitions.yaml` - `contrast_dimensions` and the five `advisor_headcount` `contrast` maps;
  header lines for the new fields (1).
- `tests/test_series_coverage.py`, `tests/test_reduce_noise.py`, `tests/test_validate.py`,
  `tests/test_metric_definitions.py` - the tests above.
- `specs/answer-citations.md` - "Reduce part 3" lines (1-6); `specs/filings.md` - the `contrast` fields (1).
- `docs/results/0247-reduce-3-check.md` - checks, replay diff, scoring (new); `docs/results/0247c/` - verdicts.
- `plans/0247-reduce-3.md` - this plan, Progress log.
- ADR-021 is not amended (these are code caveats / gaps under its rules 2-3, described in the spec). Not
  touched: `scripts/eval_run.py`, `src/cee/app/*`, `scripts/verify_cee.py` (#248).

## Steps
1. Plan (this file), reviewed. 2. Items 6, 4, 2 (small), with tests. 3. Item 5, with tests. 4. Item 3, with
tests. 5. Item 1 registry + code, with tests. 6. Full pytest; mock 35 vs main 2f568c4 (`compare_mock.py`);
verify-cee. 7. Replay (section 7) and its guard; diff; the results doc. 8. Prepare the blind inputs (section 9)
and stop for the TL's scorer. 9. Commit the verdict hash alone, then verdicts and comparison;
`/finish-task`.

## Acceptance
- [ ] pytest passes (count before and after recorded); `gh pr checks` green.
- [ ] Mock 35 vs main 2f568c4: every chunk list identical (no retrieval change), statuses and refusal
      unchanged, mock answer code checks 0.
- [ ] verify-cee VERIFY PASS (open-citation / download-document may be UNREACHABLE without raw files, as in
      part 2).
- [ ] Replay guard 1-4 holds: **0 API calls**, 50 records reused, no new raw record.
- [ ] Q1, Q3, Q19, Q26 answers byte-identical to their scored dumps; Q11, Q22, Q23, Q24 change only as in
      section 8; dedupe removals as in `replay-final` (Q11 2, Q19 4, Q26 1).
- [ ] Q11: the answer has the code contrast (each dimension, every firm placed, chunk ids) and the
      "related metric" wording. **Aim: PASS** on the fresh blind re-score. A FAIL is reported with the
      scorer's reason, and what is corpus (no written MS / EDJ definition, no Schwab count; section 5 of the
      part-2 doc) and what is answer is stated.
- [ ] Q23: RJF break caveat gone, Merrill row sources. It **stays a corpus gap** (MS after 4Q2020, RJF
      quarterly, BAC after 4Q2023, EDJ 3Q26) unless the re-score passes it; a FAIL of class c is expected
      and is not a regression.
- [ ] **No PASS -> FAIL** on the re-score (Q22, Q24 keep PASS). A PASS -> FAIL stops the merge and goes to
      the TL with the scorer's reason; nothing is re-rolled.
- [ ] Linked questions: Q11, Q22, Q23, Q24 (changed); Q1, Q3, Q19, Q26 (unchanged).

## Risks
- Item 3 names MS 2024Q2 because MS's stray 2019-2020 points stretch its own span; the gap is true of the
  documents searched. Not filtering stray points (out of scope).
- Item 2's wording reads oddly for Schwab headcount (a Form ADV metric); the contrast says Schwab publishes no
  count (section 2 note).
- Item 6 also removes Q11's a2.MER break; the scope difference stays in the contrast's business-lines line.
- Q11 a2.EDJ "basis break" (whole firm / U.S. / Canada splits, one period) is noise but not in the six items:
  noted for the TL, not changed.
- Q11 may still fail on "five definitions, quoted": MS and EDJ publish none, Schwab no count (corpus, section 5
  of the part-2 doc); the contrast says so per firm.

## Progress log
- 2026-11-20 09:55 - plan written (0 calls). Diagnosis with 0 calls: the replay inputs (`replay-final`
  matrices), the dedupe removals under the year rule, the MER registry (`suggested_sources("MER") == ""`).
