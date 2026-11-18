# 0179 - Search Form ADV brochures only for fee and pricing questions; no trade press for benchmarks

Issue: #179 (with the trade-press extension from the #179 comments, PR #186)    Role: TL (S1 issue, taken over by the TL)
Spec: `specs/retrieval.md` (S1; owner review waived by TL decision 2026-11-17,
[#187 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/187#issuecomment-6964392200))

## Goal
Retrieval searches `doc_type = adv` (Form ADV Part 2A brochures, PR #178) only when the question
is about fees or pricing, and never for a question with a time window (recency mode, Q26 / Q27);
benchmark questions (a reported metric across firms, Q22-Q24) do not search tier 4 trade press
(PR #186). With #178's brochures loaded (and with #178 + #186), Q18 keeps all five `*:adv` hits,
Q23 and Q24 pass, Q26 / Q27 use no brochure chunk, and tier-1 recall is back to the level of
the corpus without the brochures. Corpora without `adv` / tier 4 documents (the freeze `cee`)
get exactly the same passages as today. FTS only, a hard SQL filter; mock eval only, 0 real calls.

## Background (numbers in #179 / #178 / #186 predate #181 and #166/#190; re-measured in step 1)
- `search()` has no doc-type limit: brochures (1,156 chunks) entered 29 of 30 retrievals in the
  PR #178 measurement; trade press (77 documents) entered all 30 in PR #186's.
- PR #178 review (freeze `corpus-2026-11-16` + brochures, `--as-of 2026-11-16`, before #181):
  25 / 5 -> 25 / 5, tier-1 recall 0.608 -> 0.577, Q23 PASS -> FAIL, Q26 FAIL -> PASS (spurious,
  RJF brochure chunks fill the 90-day window).
- `resolve()` today (checked on this branch): Q18 is theme mode with theme `fees_pricing` and the
  `fee structures` synonyms; Q25 ("advisor compensation structures", entity mode, the five, no
  theme) also lists `MS:adv`, `EDJ:adv`, `RJF:adv` in `evals/questions.yaml`; Q29 (MS advisor pay)
  expands to `compensation` / `payout`; Q26 / Q27 have a window; Q22-Q24 name the five and a
  metric (Q23's "advisor headcount" is already a `metric_phrase`).
- `cee` (freeze) has no `adv` and no tier 4 documents (doc types checked: 10-K, 10-Q, deck,
  monthly, press, research, supplement, transcript).

## Files to change
- `src/cee/retrieve/fts.py` (S1-owned; waiver above):
  - new `doc_type_scope(q) -> (excluded doc types, excluded tiers)` read from config:
    - `adv` excluded unless the question is on fees / pricing (planned: `fees_pricing` or one of
      its sub-topics in `q.themes`, or a config fee term in the question, or a question that
      names the brochure itself: "Form ADV", "ADV", "brochure"; whether Q25-type
      compensation questions also open `adv` is decided by the step-3 grid) - and always
      excluded when `q.window` is set;
    - tier 4 excluded for benchmark questions (planned: two or more covered firms and a
      config benchmark phrase in the question, e.g. "advisor headcount", "net new assets",
      "assets per advisor"; exact list from step 3).
  - `search()` adds the exclusion as a hard SQL clause (`d.doc_type <> ALL(...)`,
    `d.source_tier <> ALL(...)`) to every pass (firm pool, on-theme pool, research pool) via
    `filters_sql`-style fragment, so `rank_sql`, quotas, floor and budget are untouched. With no
    exclusion the clause is `TRUE` (same SQL as today).
- `config/entities.yaml` - new S1 block (next to `metric_phrases`): `doc_type_scope` with the
  `adv` rule (themes / terms, `never_in_window: true`) and the tier 4 rule (benchmark phrases,
  minimum firm count). Only the S1 part of the file; no C1 field (entities, CRDs) changes
  (C1-owned file; owner review waived by the same TL decision).
- `tests/test_retrieval_doc_scope.py` (new, no database) - `resolve()` + `doc_type_scope()` on
  the question texts: Q18 opens `adv`; Q23, Q24, Q22, Q1, Q7 do not; Q26 / Q27 never (window),
  also a fee question with "in the last 90 days"; Q22-Q24 exclude tier 4; Q2, Q4, Q7, Q26, Q29
  keep tier 4; Q25 per the step-3 decision; a question naming the brochure without a fee term
  ("What does Merrill's Form ADV say about conflicts of interest?") opens `adv`, but not with a
  window. Plus the SQL fragment: `TRUE` when nothing is
  excluded.
- `specs/retrieval.md` (S1-owned; waiver above) - interface sketch: doc-type scope rule and why
  (brochures and trade press crowding, #179 / #178 / #186).
- `docs/DECISIONS.md` - ADR-015: doc-type limits per question type (adv only for fee questions,
  never in a window; no tier 4 for benchmarks), with the step-3 grid result.
- `plans/0179-adv-fee-only.md` (this file)

Out of scope: merging PR #178 / #186 (the TL merges them after this PR) and their answer keys
(neither PR changes `evals/expected_chunks.yaml`); quota / budget / floor constants (#181, #166);
chunking; hybrid retrieval. No new committed script (Windows/Mac pair not needed).

## How each run picks its code, key and DB
- Every command: `PYTHONUTF8=1`, `PYTHONPATH=<worktree>/src`, venv
  `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe`; before each step
  `python -c "import cee; print(cee.__file__)"` must print the worktree's path.
  `DATABASE_URL` always set explicitly per command (never left to `.env`).
- Answer key: main's `evals/expected_chunks.yaml` for every run (#178 and #186 do not touch it).
- `--as-of`: every baseline and final run is done twice, **`--as-of 2026-10-29`** (comparable
  with ADR-013 / ADR-014 and PROGRESS) and **`--as-of 2026-11-17`** (today: every brochure and
  trade article, e.g. `MER-ADV-2026` 2026-10-30, `MS-ADV-2026` 2026-11-04, trade up to
  2026-11-16, falls inside Q26's 90 days / Q27's year-to-date window, so the recency items are
  really tested). Comparisons are always within one as-of date.
- Scratch DBs (never `cee`): `cee_179a` = freeze + the five brochures ("main + #178");
  `cee_179b` = freeze + the five brochures + the 77 trade documents ("main + #178 + #186").
  Each: `CREATE DATABASE`, `pg_restore` from `snapshots/corpus-2026-11-16.dump` (directly, not
  the restore script, whose target is `cee`), then the extra documents loaded with
  `python -m cee.ingest.load --doc <id>` from a local-only scratch worktree
  `D:\ALLPROJECTS\EDJ\wt-179-data` (`origin/main` merged with `origin/c3/55-adv-brochures` and
  `origin/c3/57-trade-press`, never pushed), raw files copied from `C:\Users\14370\Box\EDJ\`
  root into its `data/raw/` (gitignored) and checked against the manifest sha256. Expected:
  1,156 `adv` chunks (EDJ 138 / MS 286 / SCHW 90 / MER 520 / RJF 122, as in the #178 review);
  77 tier 4 `trade` documents. Retrieval code for eval runs always comes from `wt-179`
  (main code = this branch before any edit, `7a70f40`).

## Steps
1. **Baselines, main code (`7a70f40`), no edit.** `sync-db -Check` confirms `cee` at
   `corpus-2026-11-16`; note `chunks` / `documents` counts (18,497 / 137). Build `cee_179a` and
   `cee_179b` (above), check chunk counts. Mock `eval_run.py` (all 30), output under
   `D:\ALLPROJECTS\EDJ\cache\ev179\`, at both as-of dates:
   - `B0` = `cee` ("without the brochures"; restored scratch DBs start from the same dump),
   - `B1` = `cee_179a` (main + #178), `B2` = `cee_179b` (main + #178 + #186).
   Record per question: PASS/FAIL, coverage, doc / passage recall, forbidden hits, refusal on
   gap questions (Q24, Q25, Q28-Q30), number of `adv` and `trade` chunks in each list. Confirm
   the crowding on B1 / B2 (which questions lose which expected hits to `adv` / tier 4).
2. **Implement the scope filter** with the planned default (adv: `fees_pricing` theme or fee
   term, never in a window; tier 4: off for benchmark questions) + `tests/test_retrieval_doc_scope.py`.
3. **Grid on `cee_179a` / `cee_179b`** (scratch driver in `D:\ALLPROJECTS\EDJ\cache\ev179`, not
   committed, swaps the config values in-process before `eval_run.main()`), both as-of dates:
   adv trigger {fees_pricing theme only; + fee terms; + compensation terms (Q25, Q29)} x tier 4
   rule {off; benchmark phrases (Q22-Q24 shape); benchmark phrases incl. Q11's "define and
   report advisor headcount"}. Table per cell: PASS count, PASS -> FAIL list vs B0 and vs
   B1 / B2, Q18 adv patterns, Q23 / Q24 status, adv / trade chunks in Q26 / Q27, Q25 adv
   coverage, total doc / passage recall, forbidden, refusal. Pick the smallest rule that meets
   the acceptance; ties go to the one that changes fewer questions vs B1 / B2.
4. **Finalise** the chosen rule in config + code, tests, spec text, ADR-015.
5. **Final runs** from `wt-179`: `F0` on `cee`, `F1` on `cee_179a`, `F2` on `cee_179b`, both
   as-of dates, each with `--baseline` its B run. `pytest -q`. `python scripts/verify_cee.py run`
   on `cee`, and `verify_cee.py run --source-db cee_179b` (corpus with brochures and trade).
   Raw outputs kept in `D:\ALLPROJECTS\EDJ\cache\ev179\`.
6. **Clean up.** Drop `cee_179a` and `cee_179b`; remove `wt-179-data` and its local branch.
   `cee` row counts checked unchanged (18,497 / 137).
7. `/finish-task`: PR with the per-question delta (B0 / B1 / B2 vs F0 / F1 / F2, both as-of
   dates), the grid table, the scratch-DB method, "Closes #179". Note for the TL: the
   acceptance is measured on "main + #178" (and + #186), so it holds once #178 merges after
   this PR.

## Acceptance
Issue items (each checked on F1 = this branch on `cee_179a`, and F2 = on `cee_179b`, at both
as-of dates unless stated):
- [x] Q18 hits all five `*:adv` patterns (`MS:adv`, `SCHW:adv`, `EDJ:adv`, `MER:adv`, `RJF:adv`)
      and stays PASS.
- [x] Q23 and Q24 PASS (vs. FAIL on B1 / B2 where the crowding reproduces; if either already
      passes on B1 after #181, it still passes and its `MS:supplement` / `RJF:press` hits stay).
- [x] Q26 and Q27: zero `adv` chunks in the retrieved list (recency mode never searches `adv`);
      their PASS/FAIL and coverage equal what B0 gives plus any tier 4 trade chunks (trade stays
      allowed in recency); a Q26 PASS that came only from RJF brochure chunks on B1 is reported
      as gone.
- [x] Tier-1 recall (documents and passages) on F1 >= B0 at the same as-of date (the level
      without the brochures; #179 quoted 0.626 on an older DB).
- [x] `pytest -q` passes; mock only, 0 real calls.
Trade-press extension (#179 comment, PR #186):
- [x] Q23 and Q24 PASS on F2 (brochures + trade press loaded).
- [x] On F2 no `trade` chunk in Q22, Q23, Q24; Q2, Q4, Q7, Q26 and Q29 keep at least the
      `*:trade` hits they have on B2.
- [x] F2 tier-1 recall >= B2; no PASS -> FAIL on F2 vs B0; every per-question recall drop vs B0
      listed in the PR with its cause.
No harm elsewhere:
- [x] `cee` (no `adv` / tier 4): F0 retrieved lists identical to B0 for all 30 questions
      (same chunk ids, same order), at both as-of dates.
- [x] F1 vs B1 and F2 vs B2: no PASS -> FAIL; forbidden hits stay 0; refusal accuracy on the gap
      questions unchanged; Q25's `*:adv` coverage not lower than on B1 unless the PR explains why
      (the step-3 compensation decision).
- [x] `tests/test_retrieval_doc_scope.py` (no DB) covers Q18 / Q23 / Q24 / Q26 / Q27 (and the
      tier 4 cases) and fails on `7a70f40`'s code.
- [x] `python scripts/verify_cee.py run` PASS on `cee`; `--source-db cee_179b` run reported.
- [x] `cee` unchanged (18,497 chunks / 137 documents before and after); `cee_179a`, `cee_179b`
      dropped and `wt-179-data` removed at the end.
- [x] Spec text and ADR-015 updated; PR closes #179.

## Risks
- A fee question worded without any configured fee term or theme keyword loses the brochures
  (silent: no eval question shows it). Mitigation: the theme keywords plus the ADV / brochure
  terms; the rule lives in config, so a missed phrase is a one-line addition.
- The benchmark detector is phrase-based: a benchmark question worded differently still gets
  trade press (today's behavior, no worse).
- Trade press inside a window (Q26 / Q27) stays allowed and may still crowd filings there;
  reported, not fixed here.
- Numbers depend on the as-of date (window questions only); both dates are reported.
- The acceptance is measured on main + #178 (+ #186) before those PRs merge; if they change
  their manifest rows before merging, the numbers need a re-run.

## Progress log
- 2026-11-17 19:45 - plan written (branch `tl/179-adv-fee-only` from `origin/main` `7a70f40`,
  after #181 / #166 / #190). Scope includes the trade-press extension the TL added to #179
  (PR #186). Raw files for both PRs are in the Box root (5 `*-ADV-2026.pdf`, 77 `*-TRADE-*.txt`).
- 2026-11-17 20:05 - reviewer of record: PLAN APPROVED on `6011994`
  ([#179 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/179#issuecomment-6966569365));
  TL approved ADR-015 and the trade-press part on #179. Non-blocking notes taken: "Form ADV" /
  "ADV" / "brochure" open `adv` (never in a window) with a test case; Risks list added; the PR
  states how `eval_run.py` treats documents dated after `--as-of`. Starting step 1.
- 2026-11-17 20:10 - step 1. `cee` 18,497 / 137, at corpus-2026-11-16. `cee_179a`: +5 brochures,
  1,156 `adv` chunks (138 / 286 / 90 / 520 / 122), 19,653 / 142. `cee_179b`: + 77 trade documents
  (327 chunks), 19,980 / 219. Raw sha256 all match. Merging #178 and #186 into `wt-179-data`
  conflicted only on appended manifest rows (union kept). Baselines (as-of 10-29 / 11-17):
  B0 28 / 27 PASS, recall 0.646 / 0.625; B1 28 / 28, 0.601 / 0.577 (adv in 29 / 30 questions,
  Q26 PASS at 11-17 only through 8 RJF brochure chunks); B2 27 / 27, 0.533 / 0.505 (Q28 FAIL).
  After #181, Q23 and Q24 already PASS on B1 / B2, but Q24 coverage drops 1.0 -> 0.8 / 0.6
  and Q22 1.0 -> 0.857.
- 2026-11-17 20:20 - step 2. `doc_type_scope()` + `doc_type_scope_sql()` in `fts.py`, ANDed into
  `filters` in `search()` (a separate fragment, so `filters_sql` and its test are unchanged);
  config block; 29 no-DB tests (fail on `7a70f40`: the function does not exist).
- 2026-11-17 20:40 - step 3 grid (`cache\ev179\grid`). Theme + ADV terms: Q25 `*:adv` coverage
  1.0 -> 0.625 (lost its brochures). + "compensation": Q25 back to 1.0. + "pay": only adds
  brochures to Q29 (not expected there) - dropped. Benchmark Q22-Q24 phrases: Q22-Q24 free of
  trade, but Q28 (EDJ vs Merrill attrition) still FAIL on `cee_179b` as on B2; Q11-excluded
  variant identical otherwise. + "attrition rate": Q28 PASS. Chosen: theme + ADV terms +
  "compensation"; benchmark phrases + "attrition rate". Outside the planned grid by one cell
  (the attrition phrase), still the same rule shape.
- 2026-11-17 20:50 - step 4/5. Final runs F0 / F1 / F2 identical to the chosen grid cell (30/30
  lists). F0 = B0 (30/30 identical lists, both dates). F1: 28 / 27 PASS, recall 0.646 / 0.481 and
  0.625 / 0.451 (= B0); F2: 28 / 28 PASS, 0.593 / 0.457 and 0.569 / 0.425 (B2 0.533 / 0.505).
  Q26 at 11-17 on F1 FAIL like B0 (the brochure-only PASS is gone); on F2 PASS through 15 RJF
  trade chunks (news). F1 lists differ from B0 on 18 questions with equal metrics: the rank's
  IDF counts every chunk in the corpus, brochures included. ADR-015 written.
- 2026-11-17 20:40 - step 5. pytest 455 passed. verify-cee on `cee` (commit `eebd1ff`): all 9
  PASS (`.verify-runs/20261117-203203-eebd1ff`). On `cee_179b`: ask-answer FAIL at the Q21 step
  (it expects Raymond James as a wealth-transfer theme gap; with #186's trade press RJF has an
  on-theme trade chunk); `main` code (`7a70f40`) fails the same step on `cee_179b`
  (`.verify-runs/20261117-203625-7a70f40`), so it is #186's corpus, not this change; the
  recipe needs updating when #186 merges. The other 8 features PASS.
- 2026-11-17 20:42 - step 6. `cee_179a` / `cee_179b` dropped; `wt-179-data` (and its local
  branch) and the baseline worktree `wt-179-base` removed; `cee` still 18,497 / 137. Evidence
  kept in `D:\ALLPROJECTS\EDJ\cache\ev179\`.
