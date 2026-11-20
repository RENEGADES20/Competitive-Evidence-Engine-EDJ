# 0247 - Reduce part 4: "latest count found" note, RJF investor-day count for Q23

Issue: #247 (part 4, "Part of #247": NEXT item 11, the headcount corpus gaps, stays open)    Role: TL
Spec: specs/answer-citations.md (item 9), specs/retrieval.md (item 10); also specs/filings.md for the new
registry field in `config/metric_definitions.yaml`

Scope: `docs/NEXT.md` items 9 and 10 only, as recorded in the TL comment on #247 after PR #263
("Items 9-10 are planned as #247 part 4 before the #250 scored runs"). Background:
`docs/results/0247-reduce-3-check.md` sections 9-11. Item 11 (ingestion) is out of scope; the corpus snapshot
stays `corpus-2026-11-19`. Branch `tl/247-reduce-4` from origin/main e15ccf8 (= faf5d1d plus the PROGRESS
line). Owners (TL takeover): `src/cee/answer/*`, `specs/answer-citations.md` S2; `src/cee/retrieve/*`,
`specs/retrieval.md` S1; `config/metric_definitions.yaml`, `specs/filings.md` C1. Binding: ADR-021 rules 0-8 and
its #246 / #247 amendments, CLAUDE.md ground rules and "Paid API calls".

Not touched: `exp/hybrid` (#249 works there), `scripts/eval_run.py`, `src/cee/app/*`, `scripts/verify_cee.py`,
`.claude/skills/verify-cee/*`. If an item turns out to need one of them, I stop and ask.

**API calls**: item 9 is code only (0 calls, proved by replaying the saved records in `docs/results/0247b-raw/`).
Item 10 changes Q23's retrieval for Raymond James only, so Q23 needs **at most 3 real DeepSeek calls** (1 map,
at most 1 re-extraction, 1 reduce; expected 2). Every other question: 0 calls. Bound from a 0-call count,
section 3. `.env` is never read, printed or committed.

## Goal
Two things are true when this is done. (1) When a firm's registered advisor count is old and later documents of
the same type were read with no count, the answer says so by code, scoped to that document type and to what was
found and read: "{firm} - {metric}: latest count found in the {doc_words}: {date} ({chunk}); no count found in
the {doc_words} read since ({docs})", never "discontinued" or "last reported" (Q11, Q23, Q24: Morgan Stanley's
supplements 4Q2020, Merrill / Bank of America's supplements 4Q2023). (2) Q23 retrieves
`RJF-DECK-2025-investor-day#43` (8,731 Raymond James advisors at 2025-03-31), the one Q23 retrieval miss.

## Plan review round 1 (issuecomment-7047263496): TL rulings, written in before any code
- Blocking 1 adopted: the `series_pins` curation rule ("a chunk of an undated document that states a count of
  the metric with its date") is in section 2, `specs/filings.md` and the registry header; the corpus scan's SQL
  and result are recorded (section 2); the DB test asserts a date pattern in every pin's text.
- Blocking 2 adopted with the reviewer's template, scoped to the document type and saying "found" / "read":
  "{firm} - {metric}: latest count found in the {doc_words}: {date} ({chunk}); no count found in the {doc_words}
  read since ({docs})." Goal, sections 1 and 5, Acceptance, the spec line and the tests updated.
- Non-blocking 1-5 adopted: deck -> "investor presentations"; the unstored "**" footnote of #43 noted, and any
  basis-break caveat reported with its groups, never suppressed; the one-year reference date and the same-type
  rule stated in the spec; `pool43.txt` / `pin_sim.txt` saved in `ev247d\diag\`; the MS note read next to the MS
  span caveat in the final Q23.

## 0-call diagnosis (done for this plan; scripts and output in `D:\ALLPROJECTS\EDJ\cache\ev247d\diag\`)
- **Item 10, why Q23 misses #43** (`pool43.py` -> `pool43.txt`; `pin_sim.py` -> `pin_sim.txt`; retrieval only, the committed Q23 / Q11 / Q24 plan records,
  `--as-of 2026-11-17`): #43 **is in Q23's a1.RJF candidate pool** (190 ids) but **lost in `select()`**: the
  deck already gives three higher-ranked chunks (`#69`, `#126`, `#110`) and `MAX_PER_DOC = 3`. The per-period
  pass cannot reach it: `RJF-DECK-2025-investor-day` has `period_end` NULL (deck, tier 3, published
  2025-06-05), and the pass filters on `documents.period_end`. Q11 keeps it under a4.RJF (other words). The
  branch replay reproduces the scored Q23 selection (91 RJF passages, the same ids as `ev247c\replay`).
- **Item 10, blast radius of the fix** (`pin_sim.py`: pin #43 for RJF `series` aspects of
  `advisor_headcount`, compare every sub-question's hits and pools with and without it, the eight replayed
  questions): **only Q23 a1.RJF changes** (+#43, nothing removed). Q1, Q3, Q11, Q19, Q22, Q24, Q26: hits and
  pools identical. RJF is the last sub-question of Q23, so no other firm's exclusions change.
- **Item 9, what the rule sees** (`later_hits.py` / `later_hits.txt`, the map's own hits per sub-question; the
  `ev247c\replay` matrices): MS's latest dated count is 15,950 at 2020-12-31 (`MS-SUPP-2020Q4#1`) in Q11, Q23 and
  Q24, and the MS sub-questions read MS-SUPP-2025Q4, 2026Q1, 2026Q2, 2026Q3 with no count from them. Merrill's
  latest dated count is 18,916 at 2023-12-31 (`BAC-SUPP-2023Q4#2`, a fact cell in Q11, a different-quantity cell
  in Q23 and Q24), and the Merrill sub-questions read BAC-SUPP-2025Q4..2026Q3 with no count. RJF: latest
  2025-09-30 (`RJF-10K-2025#227`), no later 10-K in the corpus. EDJ: latest 2026-06-26 (10-Q 2Q26). Schwab: no
  count (`count_date: none`). The 2025-26 MS / BAC / RJF supplements hold no advisor count
  (`docs/results/0247-reduce-3-check.md` section 9b, SQL).

## 1. Item 9: "latest count found ... none found since" note by code (`matrix.last_reported`)
**Design** (code caveat; no model text, no new fact; `src/cee/answer/matrix.py`):
- Applies per firm row and registered metric M whose registry entry has a `contrast.count_date` with value
  `counted` (today only `advisor_headcount`; NNA has no `count_date`), when the question has an aspect with
  metric M. **One note per firm per metric**, however many aspects carry M (Q11 has four).
- **Latest count**: over the firm's cells of the M aspects (labels `fact`, `derived` or `different_quantity`;
  no research cell), the valued counting items with a parseable period (`_period_key`), plus the registry
  `count_date` (date, chunk) when its chunk is in `m.hits` (it was read). The latest date wins; on a tie the
  registry chunk, else the first item in cell order. Its chunk = the item's first chunk id (or the registry
  chunk); its **document type** T = that chunk's `Hit.doc_type` (from `m.hits`).
- **Old**: the latest date is before the reference date: the first day of the first asked period when the
  question asks periods (`asked_periods`, Q23: 2024-10-01), else the as-of date minus one year (Q11, Q24:
  2025-11-17). The as-of date comes from `finish(..., as_of)` (today when None).
- **Later documents read**: the documents of type T, of the same firm, with at least one chunk in `m.hits`
  whose `part_id` is one of the firm's M sub-questions (what the map read for that firm), dated after the latest
  count (`period_end`, else `published_at`). Not one of their chunks is cited by a valued counting item of the
  firm's M cells (otherwise a count was found there and the note is not true).
- Both hold, and at least one later document -> the caveat (review blocking 2, TL ruling)
  `LAST_REPORTED = "{firm} - {metric}: latest count found in the {doc_words}: {date} ({chunk}); no count found
  in the {doc_words} read since ({docs})."` with `{firm}` = `firm_label` (Merrill names its parent:
  "Merrill (Bank of America Corporation)"), `{metric}` the metric's label ("Advisor headcount"), `{doc_words}`
  a fixed plural per doc type (`supplement` -> "quarterly financial supplements", `10-K` -> "Form 10-K annual
  reports", `10-Q` -> "Form 10-Q quarterly reports", `deck` -> "investor presentations" (review nb 1: the same
  sub-questions read quarterly earnings decks too), else the doc type), `{docs}` the later document ids, oldest
  first. Example: "Morgan Stanley - Advisor headcount: latest count found in the quarterly financial
  supplements: 2020-12-31 (MS-SUPP-2020Q4#1); no count found in the quarterly financial supplements read since
  (MS-SUPP-2025Q4, MS-SUPP-2026Q1, MS-SUPP-2026Q2, MS-SUPP-2026Q3)."
- **Why the scope to the document type** (review blocking 2): the note never claims the firm's last count
  overall. For Merrill the same answers hold a later stored count of another document type and scope,
  `BAC-DECK-2025-investor-day#9` ">15K Wealth Advisors" (published 2025-11-05, "as of 3Q25" in the registry
  note), so "last reported count 2023-12-31" would be false against a stored chunk; "latest count found in the
  quarterly financial supplements" is true. And "read" (not "searched"): the map read the retrieved passages of
  those documents, not every page.
- Never "discontinued", "stopped", "no longer", "ceased", "current" or "last reported": the note states what
  the documents read hold, as the existing "not found ... in the documents searched" gaps do. Ground rule 4
  holds: no figure is inferred; the date and chunk are those of a cited count.
- **Reference date** (review nb 3, stated in the spec): the first asked period's first day, else the as-of date
  minus one year. For an annual reporter the age test alone would fire (RJF's 10-K count 2025-09-30 is older than
  2025-11-17); it is the same-document-type rule (no later 10-K read) that keeps RJF out. EDJ is out on age
  (latest 2026-06-26).
- Placed in `build_caveats` after `series_spans` (so in Q23 it follows the MS span caveat "... no figure after
  2020-12-31 was found"). It enters the reduce message's "Caveats added by code" list (as every part-3 caveat);
  for the replayed answers the reduce output is pinned (section 4), so this is 0 calls.
- **Expected** (from the diagnosis): MS and Merrill notes in Q11, Q23 and Q24; none for EDJ, RJF, Schwab; none in
  Q1, Q3, Q19, Q22, Q26 (no `advisor_headcount` cell outside Q26's RJF a7, whose latest point is 2026-10-16).
**Tests** (`tests/test_reduce_part4.py`, fake matrices and hits):
- the Q23 MS shape (series, items 2019-12-31..2020-12-31 from MS-SUPP-2020Q4#1, later supplements read) -> one
  note equal to the exact template text: "Morgan Stanley - Advisor headcount: latest count found in the
  quarterly financial supplements: 2020-12-31 (MS-SUPP-2020Q4#1); no count found in the quarterly financial
  supplements read since (MS-SUPP-2025Q4, MS-SUPP-2026Q1, MS-SUPP-2026Q2, MS-SUPP-2026Q3).";
- the Merrill shape with a later undated deck item of another type (">15K", `BAC-DECK-2025-investor-day#9`) ->
  the note still names the supplements only (the deck is another document type, the item is undated);
- doc-type words: `deck` -> "investor presentations";
- the Merrill different-quantity shape -> a note headed "Merrill (Bank of America Corporation)";
- the Q11 shape (four M aspects, MS a fact on a2 only) -> exactly one note per firm;
- RJF shape (latest 2025-09-30 from a 10-K, no later 10-K read, later 10-Qs read) -> none (other doc type);
- EDJ shape (latest 2026Q2) -> none (not old); Q23 RJF after item 10 (latest inside the asked window) -> none;
- a later same-type document that holds a cited valued count -> none; no later document read -> none;
- a firm with `count_date: none` (Schwab) -> none; an aspect with no registered metric -> none;
- no note contains `discontinu|stopped|no longer|ceased|current|last reported` (regex over every note the tests
  build).

## 2. Item 10: pin the RJF investor-day count for series aspects (`series_pins`)
**Design**:
- Registry (`config/metric_definitions.yaml`): a new optional field on a definition entry, `series_pins`.
  **Curation rule** (review blocking 1; the same text in the registry header and `specs/filings.md`): a
  `series_pins` id is a chunk of the firm's document with `period_end` NULL that states a count of the metric,
  on the entry's population, together with its date in the chunk text, and that the per-period pass therefore
  cannot reach. Pinned only for `series` aspects of that metric. The field is filled by the corpus scan below,
  rerun when a document with `period_end` NULL is ingested, not by the chunk one question missed. RJF `advisor_headcount`:
  `series_pins: [RJF-DECK-2025-investor-day#43]` (the slide's own words: "Mar. 31, 2025** ... FINANCIAL ADVISORS
  ... 8,011 8,787 8,731"; its FY2024 8,787 equals `RJF-10K-2025#227`'s 2024-09-30 total, so it is the same
  count). Header comment for the field. Not added to `see_also` (that would pin it for Q11 and Q24 fact aspects
  too and change no answer for the better; the simulation shows it would leave their hits unchanged in Q11, but
  it is not needed).
- **Corpus scan** (0 calls, `cee` on `corpus-2026-11-19`; `ev247d\diag\series_pins_scan.sql` -> `series_pins_scan.txt`):
  ```sql
  SELECT c.chunk_id, d.doc_type, d.source_tier, d.published_at, substr(c.text, 1, 300)
  FROM chunks c JOIN documents d USING (doc_id)
  WHERE d.period_end IS NULL AND d.source_tier BETWEEN 1 AND 3
    AND d.entity_id IN ('MS','SCHW','EDJ','MER','BAC','RJF') AND d.doc_type <> 'transcript'
    AND c.text ~* '(financial|wealth)\s+advis|advisors'
    AND c.text ~ '\d[\d,]{2,}|\d+\s*K\y'
  ORDER BY c.chunk_id;
  ```
  82 rows, each read. **Only `RJF-DECK-2025-investor-day#43` qualifies** (advisor count 8,731 with "Mar. 31,
  2025" in the chunk). Not qualifying:
  - `RJF-DECK-2025-investor-day#30` ("8,731 PCG advisors") and `#126` ("approximately 9,000 employee and
    independent financial advisors"): no date in the chunk.
  - `BAC-DECK-2025-investor-day#9` / `#13` (">15K Wealth Advisors", Merrill and Private Bank): no date in the
    chunk; already in BAC `see_also`.
  - `BAC-DECK-2025-investor-day#76` ("Private Client Advisors 482 | 545 | 700" under "2019 | 3Q25 | Medium-Term
    Targets"), `#34` ("2.4K Advisor trainees"), `#77` (Pathway Program participants): counts of other
    populations (a role subset, trainees, program participants), not the metric on the entry's population.
  - `BAC-DECK-2025-investor-day#18`, `#50`, `#64`, `#68`; `RJF-DECK-2025-investor-day#45`, `#93`;
    `SCHW-DECK-2026-investor-day#172`, `#307`; `MER-PR-2026-09-15-01#0`: no advisor count (percentages, assets,
    revenue, rankings, product text).
  - Form ADV brochures (`*-ADV-2026#*`) and recruiting pages (`*-PR-web-*`): legal, fee or recruiting text, no
    advisor count.
  The scan and its result go into the results doc too.
- Code (`src/cee/retrieve/planner.py`, `pinned_ids`): after the definition chunk and `see_also`, append the
  entry's `series_pins` when `aspect.kind == "series"`; dedupe; `PIN_MAX = 8` unchanged (RJF: 4 ids). Fetched by
  `fts.fetch_pinned` under every hard filter of the sub-question, like every pin (`origin = "pinned"`).
- **Considered and not chosen** (0-call reasons): (a) let the per-period pass date an undated document by
  `published_at` - it changes the period hits of all five firms in Q23 (up to 5 maps + 5 re-extractions + 1
  reduce) and would place this slide in 2025Q2, not at its 2025-03-31 count; (b) raise `MAX_PER_DOC` for decks -
  a global selection change for every question. The pin is the narrowest change: one firm, one sub-question.
**Tests** (`tests/test_reduce_part4.py`; registry tests in the same file):
- `pinned_ids("RJF", series headcount aspect)` ends with `RJF-DECK-2025-investor-day#43`; a `fact` headcount
  aspect (Q11 / Q24 shape) does not get it; PIN_MAX holds;
- registry (no DB): `series_pins` ids are not in `see_also`, their doc ids are in `data/manifest.csv`;
- registry (DB up, skipped otherwise, as the `quote` test): for **every** `series_pins` chunk: it exists, its
  document has `period_end` NULL, and its text (whitespace collapsed) matches a date pattern (a month name or
  abbreviation with day and year, an ISO date, or a quarter label such as "3Q25" / "2025Q1") and a count
  (`\d[\d,]{2,}`); plus the #43 literals "8,731" and "Mar. 31, 2025".
- **#43's "**" footnote** (review nb 2): the slide's "Mar. 31, 2025**" footnote text is not stored in any chunk of
  the deck (page 39). The answer cannot explain the asterisk; the results doc says so.

## 3. Paid calls (CLAUDE.md "Paid API calls"; pre-approved by the user; no re-rolls)
- **Why the mock cannot show it**: whether the model extracts 8,731 at 2025-03-31 from the slide and whether
  Q23's answer lists it are answer quality. Item 9 needs no call (code caveat, replay).
- **0-call count** (done before the plan for retrieval, `pin_sim.py`; repeated on the finished code): only Q23's
  RJF map input changes. On the finished branch, the same seeded-cache run of Q23 with `--max-calls 0` must show
  exactly one capped map (`a1.RJF`) and the reduce at the cap, and every other Q23 record (plan, MS, SCHW, EDJ,
  MER maps) reused. Any other miss -> stop and report before any call.
- **Bound**:

  | Q | Planner | Map | Re-extraction (at most) | Reduce | At most | Expected |
  |---|---|---|---|---|---|---|
  | Q23 | 0 (reused) | 1 (RJF) | 1 (RJF, only if its cell is `not_found`) | 1 | **3** | 2 |
  | Q1, Q3, Q11, Q19, Q22, Q24, Q26 | 0 | 0 | 0 | 0 (reduce pinned, section 4) | 0 | 0 |

  `--max-calls 3`. One run of Q23 (the full answer flow, ADR-021); no second run, no re-roll. An invalid output,
  a failed call or a wrong answer is a finding. A ProviderStop or a 400 stops the run.
- **Settings** (the part-2/3 run settings, printed by the wrapper `ev247d\run-real.ps1` / `run-real.sh`):
  `LLM_PROVIDER=deepseek`, `DEEPSEEK_MODEL=deepseek-v4-pro`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_THINKING=on`,
  `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=6`, `PYTHONPATH=<wt>\src`, the main repo's
  `.venv`; `eval_run.py --real --max-calls 3 --questions Q23 --as-of 2026-11-17 --naive-tz America/Chicago
  --out ev247d\real-q23`. Cache `<wt>\.eval-runs\cache\` seeded only from `docs/results/0247b-raw/*.json` (not
  the verdicts, not `.failed-1`). Code gate: `git status` clean, the commit recorded, `src scripts config`
  identical to the commit of the 0-call count. The key: `.env` copied in from the main repo inside `try` and
  removed in `finally` (trap on Mac), never read or printed; checked absent after.
- **Saved**: every new record (`Q23-map.RJF-*`, any `Q23-remap.RJF-*`, `Q23-reduce-*`) copied to
  `docs/results/0247d-raw/` and committed; the PR states the call count, model and why.

## 4. Replays (0 calls), the baseline, and the guard
- Script `ev247d\diag\replay_part4.py` = part 3's `replay_part3.py` (same eight pinned reduce keys: Q1
  f838663112cf225554f12a4b, Q3 ec259fc6b468c54a5288cdfa, Q11 5dbbeb66472889c98d524e8e, Q19
  69b98fa4852035ea030220f3, Q22 603b706048ab5e01f5dd9962, Q23 523be48cb96f26a1243000a7, Q24
  1d076b546886900b14903e07, Q26 cbf122e21a570a271289cb24), `--naive-tz America/Chicago`, wrappers
  `replay.ps1` / `replay.sh` (key empty, `--max-calls 0`, cache seeded only from `docs/results/0247b-raw/`).
- **Baseline**: a detached worktree of main e15ccf8 (`D:\ALLPROJECTS\EDJ\wt-247d-base`) -> `ev247d\replay-base`.
  Expected identical to part 3's final `ev247c\replay` (main = the merged part 3); any difference is reported.
- **Branch replay, item 9** (`ev247d\replay`): all eight. Q23's RJF map is capped there (item 10 changes its
  input), so this run's Q23 is the 0-call count of section 3, not an answer; Q23's answer comes from the real run.
- **Guard** (every 0-call run; all must hold, else stop and report, no retry with a key): `--max-calls 0`, key
  empty, no `.env` in the worktree before and after; `git status` clean and the commit recorded;
  `meta.real_calls == 0`; reused = 50 on the baseline, 49 on the branch (Q23's RJF map not reused, capped);
  `docs/results/0247b-raw/` unchanged and every `<out>\raw\` file byte-identical (CRLF -> LF) to its record.
- **After the real run**, a final 0-call replay (`ev247d\replay-final`) with Q23's reduce pinned to the new
  record and the new records in the seed: guard as above (reused = all records, 0 calls); Q23 identical to the
  real run's answer.
- Limitation (as part 3): for Q11 and Q24 the model wrote its text against the reduce message without the new
  caveat; code attaches it. Q23's reduce sees it (real call).

## 5. Expected changes (branch vs baseline, final replay)

| Q | Changes | By item |
|---|---|---|
| Q1, Q3, Q19, Q22, Q26 | none (byte-identical) | - |
| Q11 | two `LAST_REPORTED` caveats in the reviewed template: MS "latest count found in the quarterly financial supplements: 2020-12-31 (MS-SUPP-2020Q4#1); no count found in the quarterly financial supplements read since (MS-SUPP-2025Q4, ..., MS-SUPP-2026Q3)"; Merrill (Bank of America Corporation) the same with 2023-12-31 (BAC-SUPP-2023Q4#2) and BAC-SUPP-2025Q4..2026Q3; claims unchanged | 9 |
| Q24 | the same two caveats; claims unchanged | 9 |
| Q23 | new answer from the real run: RJF cell with 8,731 at 2025-03-31 (`RJF-DECK-2025-investor-day#43`) expected; RJF period gaps lose 2025Q1; the two `LAST_REPORTED` caveats (the MS one right after the MS span caveat "... no figure after 2020-12-31 was found": checked that the two read well together, review nb 5); any RJF basis-break caveat reported with its groups, never suppressed (review nb 2); claim text is new model output | 9, 10 |

Any other difference is reported and explained before the blind inputs are built.

## 6. Blind re-score inputs (0 API calls; the TL starts the scorer)
- `D:\ALLPROJECTS\EDJ\cache\ev247d\blind-in\`: `answers-dump.txt` with only the answers that differ from the
  baseline (expected Q11, Q23, Q24; Q23 from the real run, Q11 / Q24 from the final replay), `questions.yaml`
  (copied from `evals/questions.yaml`), `verdict-rule.txt` (part 3's r3 rule, question list updated; Q24 against
  `answer` per `evals/behavior_supersede.yaml`). No earlier verdicts, plan or diff. Hashes in
  `ev247d\blind-in-hashes.txt`; `ev247d\scorer-prompt.txt` (part 3's prompt, paths changed, writes
  `ev247d\verdicts-blind.json`). **I stop here, before scoring.**
- After scoring (TL): copy to `docs/results/0247d/verdicts-blind.json`; commit its sha256 alone in the results
  doc first, then the verdicts and the comparison. Unchanged answers keep their part-3 verdicts (Q1, Q3, Q19, Q22,
  Q26 PASS).

## Files to change
- `src/cee/answer/matrix.py` - `last_reported` + `LAST_REPORTED` + doc-type words; `build_caveats` takes
  `as_of` from `finish` (item 9).
- `src/cee/retrieve/planner.py` - `pinned_ids` appends `series_pins` for series aspects (item 10).
- `config/metric_definitions.yaml` - RJF `advisor_headcount` `series_pins`; header comment for the field with the
  curation rule (10).
- `tests/test_reduce_part4.py` - new: the tests of sections 1 and 2.
- `specs/answer-citations.md` - "Reduce part 4" line for the note: the exact template, the reference date (first
  asked period, else as-of minus one year) and the same-document-type rule (9); `specs/retrieval.md` - the pins
  paragraph names `series_pins` (10); `specs/filings.md` - the registry field and its curation rule (10).
- `docs/results/0247-reduce-4-check.md` - checks, the `series_pins` scan (SQL and result), the unstored #43
  footnote, count, real run, replays, diffs, blind inputs, later scoring (new); `docs/results/0247d-raw/` - the new raw records; `docs/results/0247d/` - verdicts (after scoring).
- `docs/NEXT.md` - rows 9 and 10: built in #247 part 4, with the outcome.
- `plans/0247-reduce-4.md` - this plan, Progress log.
- ADR-021 is not amended (a code caveat under rule 0 / ground rule 3 and a retrieval pin under the part-2 pin
  rule, both described in the specs).

## Steps
1. Plan (this file), reviewed. 2. Item 10 (registry, `pinned_ids`), with tests. 3. Item 9 (`last_reported`),
with tests. 4. Full pytest (count before / after); mock 35 vs main e15ccf8 (`compare_mock.py`); verify-cee.
5. Baseline replay (main), branch replay (item 9 diffs; Q23 count = 1 capped map), guards. 6. Real run of Q23
(at most 3 calls), records into `docs/results/0247d-raw/`; final replay; diffs; results doc. 7. Blind inputs;
stop for the TL's scorer. 8. After scoring: hash commit alone, then verdicts and comparison; `/finish-task`.

## Acceptance
- [ ] pytest passes (count before and after; DB tests run with `cee-db` up, not skipped); `gh pr checks` green.
- [ ] Mock 35 vs main e15ccf8: every chunk list identical (the mock's rule plan has no series aspect), statuses
      and refusal unchanged; caveat differences only in Q11, Q23, Q24 (the note).
- [ ] verify-cee VERIFY PASS (open-citation / download-document may be UNREACHABLE without raw files, as before).
- [ ] 0-call guard holds on every replay; branch vs baseline: Q1, Q3, Q19, Q22, Q26 byte-identical; Q11, Q24 differ
      only by the two `LAST_REPORTED` caveats.
- [ ] 0-call count on the finished code: exactly Q23 `a1.RJF` map capped; **real calls <= 3** (expected 2), all
      saved in `docs/results/0247d-raw/`, count and model in the PR.
- [ ] Q23 (item 10): `RJF-DECK-2025-investor-day#43` in Q23's retrieved set (pinned, a1.RJF) and in the RJF map
      input; the answer lists RJF 8,731 at 2025-03-31 with that source. If the model does not, it is reported as
      a finding with the RJF cell's label and items; nothing is re-rolled.
- [ ] Item 9: Q11, Q23 and Q24 carry the note in the exact template ("latest count found in the quarterly
      financial supplements: <date> (<chunk>); no count found in the quarterly financial supplements read since
      (<docs>)") for MS 2020-12-31 (`MS-SUPP-2020Q4#1`) and Merrill (Bank of America Corporation) 2023-12-31
      (`BAC-SUPP-2023Q4#2`), listing the later supplements read; no note for EDJ, RJF, Schwab; no answer text by
      code says "discontinued", "stopped", "no longer", "ceased" or "last reported".
- [ ] Item 10 registry: the `series_pins` curation rule is in the registry header and `specs/filings.md`; the
      scan (SQL and result: only #43) is in the results doc; the DB test asserts a date and a count in every pin.
- [ ] **No PASS -> FAIL** on the fresh blind re-score of the changed answers (Q11, Q24 keep PASS). A PASS -> FAIL
      stops the merge and goes to the TL with the scorer's reason; nothing is re-rolled. Q23 may stay FAIL on the
      corpus gaps (NEXT item 11: MS after 4Q2020, BAC after 4Q2023, RJF quarterly, EDJ 3Q26); that is not a
      regression, and the PR stays "Part of #247".
- [ ] Linked questions: Q23 (items 9, 10), Q11 and Q24 (item 9); Q1, Q3, Q19, Q22, Q26 unchanged.

## Risks
- The Q23 reduce is a new model output (the reduce message changed in parts 3 and 4), so Q23's claim text
  changes beyond RJF; it is read as a whole by the blind scorer. Q23 is FAIL today, so no PASS -> FAIL risk there.
- The new RJF item could form a basis break with the 10-K points. The R3 / split rules should keep one basis (a
  whole-firm "financial advisors" item takes the 10-K key `rjf_advisors_excl_rcs`, and the slide's 8,787 equals
  the 10-K's FY2024 total). If the model scopes the item "PCG" or "domestic", the 10-K points may split by
  scope into a break caveat: it is reported with its groups and never suppressed (review nb 2).
- "Read" means the documents whose passages the map read for that firm, not every page of them; the note says
  "found" and "read" and lists the documents so a reader can check.
- `series_pins` is a hand-registered id, like `see_also`, filled by the stated rule and corpus scan (section 2);
  the DB test limits it to chunks of undated documents that state a count with a date.
- Q11 and Q24's model text was written without the new caveat (section 4 limitation).

## Progress log
- 2026-11-20 12:10 - plan written (0 calls). Diagnosis with 0 calls (`ev247d\diag\`): #43 is in Q23's a1.RJF pool
  but cut by `MAX_PER_DOC = 3` (deck; `period_end` NULL, so no period pass); a series-only pin changes only
  Q23 a1.RJF among the eight; MS / Merrill latest counts 2020-12-31 / 2023-12-31 with later supplements read in
  Q11, Q23, Q24.
- 2026-11-20 12:45 - plan review round 1 RETURN (issuecomment-7047263496); TL rulings adopted: blocking 1 (the
  `series_pins` curation rule, the corpus scan `series_pins_scan.sql` / `.txt`: 82 rows read, only #43 qualifies;
  DB test asserts a date in every pin), blocking 2 (the note scoped to the document type, "found" / "read"),
  non-blocking 1-5. `pool43.txt` and `pin_sim.txt` saved. Amended: Goal, sections 1, 2, 5, Files, Acceptance,
  Risks.
