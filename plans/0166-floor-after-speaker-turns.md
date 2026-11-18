# 0166 - Rank floor and per-document cap after speaker-turn chunking; theme slot below the floor

Issue: #166 (and #190; one PR closes both)    Role: TL (S1 issue, taken over by the TL)
Spec: `specs/retrieval.md` (S1; owner review waived by TL decision 2026-11-17,
[#187 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/187#issuecomment-6964392200))

## Goal
`select()` in `src/cee/retrieve/fts.py` keeps a firm's relevant evidence when one very strong
chunk raises that firm's rank floor, so that with PR #150's speaker-turn transcript chunks Q28
passes again and no question goes PASS -> FAIL (#166), and a firm's best chunk on the theme takes
its theme slot even when it ranks below the floor, so Q21 no longer reports Morgan Stanley as a
theme gap while `MS-DECK-2026-strategic-update#22` is on the theme (#190). The plain freeze corpus
must not regress. FTS only; no model, no new dependency; mock eval only, 0 real calls.

## Background (re-measured in step 1; numbers below predate #181)
- #150 cuts transcripts at speaker turns (1,689 -> 2,852 transcript chunks). The Merrill answer
  `BAC-TR-2026Q2#63` ranks 10.64 for Q28, lifts the Merrill floor (0.3 x best) to 3.19 and drops
  `BAC-10K-2025#246` (2.88): Q28 coverage 0.667 -> 0.333, PASS -> FAIL. The #150 review on
  `corpus-2026-11-16` also saw recall drops on Q4, Q6, Q11, Q13, Q27.
- Since #181 (ADR-013, on main) BAC GWIM/Merrill chunks share MER's quota and floor
  (`quota_firms`), so Q28's Merrill side now has one floor base; the delta must be re-measured.
- #190: in entity+theme the floor is applied while the tiers are built, before the THEME_FIRST
  slot, so a firm's only on-theme chunk below 0.3 x its best is never a candidate (Q21, MS deck
  #22 at 2.32 vs MS best 11.66).

## Files to change
- `src/cee/retrieve/fts.py` (S1-owned; waiver above) - `select()`:
  - #190: the on-theme tier (`tiers[0]`, used only for the THEME_FIRST turns) is built from every
    on-theme pool chunk of the firm, not only those above the floor (planned default: no floor
    for the theme slot; a lower theme floor such as 0.1 only if step 3 shows the bypass pulling
    in junk). The rank-order tier (`tiers[1]`) keeps the floor. `theme_gaps()` is unchanged.
  - #166: the smallest rule from the step-3 grid that brings Q28 back on the #150 DB with no
    PASS -> FAIL on either DB. Candidates, tried in this order (simplest first):
    a. `FLOOR` lower (0.25, 0.2);
    b. floor base = the firm's 2nd- (or 3rd-) best rank instead of its best, so one outlier
       chunk cannot lift the floor for the whole firm;
    c. `MAX_PER_DOC` per document type: transcripts (speaker turns, ~1.7x as many chunks) get 4
       (or 5), other types keep 3;
    d. a combination of the above only if no single rule meets the acceptance.
    (a) is a floor for the firm part only: `search()` passes the floor explicitly for the research
    part, which keeps 0.3 (research selection unchanged). (b) needs a pre-pass over the pool
    (`best` is set while streaming today); a firm with fewer chunks than the rank used falls back
    to its lowest chunk's rank (i.e. no chunk is dropped), and for MER the base is taken over MER
    and BAC GWIM/Merrill chunks together (`firm_of`). (c) targets the transcript-slot drops
    (Q11-type) more than Q28's floor problem; the PR says which rule fixes which question.
    The constants stay module-level so a scratch grid driver can swap them (as `BUDGET_RULE` in
    #181). Window questions keep `floor=0` and `WINDOW_MAX_PER_DOC`; the research part keeps
    `THEME_MAX_PER_DOC`.
- `tests/test_retrieval_quotas.py` - fixture pool, no database: a firm whose best chunk is an
  outlier keeps a relevant lower chunk (the Q28 shape) under the chosen rule; a chunk far below
  the floor still gets no slot (the floor still works); the per-type `MAX_PER_DOC` if (c) is
  chosen.
- `tests/test_retrieval_themes.py` - fixture pool: a firm whose only on-theme chunk ranks below
  the floor still gets that chunk in its theme slot and `theme_gaps()` does not report it; its
  off-theme chunks below the floor still get no slot.
- `specs/retrieval.md` (S1-owned; waiver above) - interface sketch: the floor rule as chosen,
  and the #190 decision ("the THEME_FIRST slot is not subject to the rank floor" or the lower
  theme floor), with the reason.
- `docs/DECISIONS.md` - only if the chosen #166 rule changes the shape of the floor (b or c),
  not for a constant change: a short ADR-014 with the grid result.
- `plans/0166-floor-after-speaker-turns.md` (this file)

Out of scope: chunking changes and merging PR #150 (C2, #107; the TL merges it after this);
answer-key edits (C1); hybrid retrieval / embeddings (ADR-010, #182); the budget rule (#181).
The EJ-10 "don't change ranking" note is for portability refactors; this change is for answer
quality and the PR says so.

## How each run picks its code, key and DB
- Every command runs with `PYTHONUTF8=1` and `PYTHONPATH=<worktree>/src` (the shared venv has
  `cee` installed editable from `repo/src`); before each step,
  `python -c "import cee; print(cee.__file__)"` must print the worktree's path.
- Runs on `cee` (freeze): from `wt-166`, default `DATABASE_URL` (`cee`), main's answer key.
- Runs on `cee_166` after step 1: also from `wt-166` (this branch's retrieval code), with
  `DATABASE_URL=postgresql://.../cee_166` and `--keys D:\ALLPROJECTS\EDJ\wt-166-150\evals\expected_chunks.yaml`
  (#150's remapped key; `eval_run.py` already accepts `--keys`). The chunks in `cee_166` come
  from #150's code; retrieval never reads the chunker, so no re-merge is needed per run.
  Step 5 also runs once from `wt-166-150` re-merged with this branch's final commit, as the
  exact post-merge code.
- The grid driver imports `cee.retrieve.fts` from `wt-166/src` (same PYTHONPATH check) and sets
  the constants before calling `eval_run.main()` in the same process.

## Steps
1. **Baselines on current main, no code change** (this branch before any edit, `6316494`).
   - Confirm `cee` is at `corpus-2026-11-16` (`sync-db.ps1 -Check`), note its `chunks` /
     `documents` row counts.
   - DB `cee` (freeze `corpus-2026-11-16`, read only): mock
     `eval_run.py --as-of 2026-10-29 --out D:\ALLPROJECTS\EDJ\cache\ev166\main-cee`.
   - Scratch DB `cee_166`: `CREATE DATABASE cee_166`, `pg_restore -d cee_166` (directly, not
     the restore script, whose target is `cee`) from `snapshots/corpus-2026-11-16.dump`, then all 32 transcripts re-ingested with #150's code
     (scratch worktree `D:\ALLPROJECTS\EDJ\wt-166-150` = this branch merged with
     `origin/c2/107-speaker-turns`, local only, never pushed; raw transcripts from
     `C:\Users\14370\Box\EDJ\`, as in PR #150's body and review; `DATABASE_URL` set explicitly
     to `cee_166` for the re-ingest). Check the reproduction:
     2,852 transcript chunks, 14 GWIM transcript chunks, `BAC-TR-2026Q2#63` tagged GWIM.
   - On `cee_166`, from `wt-166-150` (main code + #150 chunking + #150's remapped answer key),
     `DATABASE_URL=.../cee_166`: mock eval `--as-of 2026-10-29 --out ...\ev166\main-150`.
   - Record per question: PASS/FAIL, coverage, doc and passage recall, forbidden hits. Confirm
     whether Q28 still fails on `cee_166` after #181 and why (rank, floor, slot that drops it).
2. **#190 fix** (the theme slot ignores the floor) + its fixture test. Mock eval on both DBs
   (`--baseline` the step-1 runs). Check Q7, Q10, Q12, Q19, Q21, Q28 and all Q1-Q30; Q21's
   coverage note no longer names Morgan Stanley when `MS-DECK-2026-strategic-update#22` is in
   the pool.
3. **#166 grid.** Scratch driver (in `D:\ALLPROJECTS\EDJ\cache\ev166`, not committed) that sets
   the candidate constants/rule and runs the mock eval on both DBs, on top of step 2:
   FLOOR {0.3, 0.25, 0.2} x floor base {best, 2nd best, 3rd best} x transcript MAX_PER_DOC
   {3, 4, 5} (prune: stop growing a dimension once it meets the acceptance). Table per cell:
   PASS count, PASS -> FAIL list, Q28 coverage, total doc/passage recall, forbidden hits,
   refusal accuracy on gap questions (Q24, Q25, Q28-Q30), passages per question. Pick the
   smallest change that meets the acceptance on both DBs; ties go to the one that changes the
   fewest questions on `cee`.
4. **Implement the chosen rule** in `select()`, fixture tests, spec text (and ADR-014 if the
   rule changes shape).
5. **Final runs.** Mock eval on `cee` from this branch and on `cee_166` from `wt-166-150`
   (re-merged with this branch's final commit), both with `--baseline` the step-1 runs;
   `pytest -q`; `python scripts/verify_cee.py run` on `cee`.
6. **Clean up.** Drop `cee_166`; remove `wt-166-150` and the scratch branch. `cee` never modified
   (row counts of `chunks` / `documents` checked before and after).
7. `/finish-task`: PR body with the per-question eval delta on both DBs, the grid table, why the
   change is needed (EJ-10 note), "Closes #166" and "Closes #190".

## Acceptance
- [ ] #166: on `cee_166` (freeze + #150's transcripts, #150's answer key), mock `--as-of
      2026-10-29`: **Q28 PASS**, and no PASS -> FAIL vs. main's code on the same DB
      (`ev166\main-150`). Other recall changes listed and explained in the PR.
- [ ] #166: on `cee` (freeze `corpus-2026-11-16`, main's answer key), mock `--as-of 2026-10-29`:
      no PASS -> FAIL vs. `ev166\main-cee`; forbidden hits stay 0; refusal accuracy on the gap
      questions unchanged.
- [ ] #166: the #150 review's recall drops (Q4, Q6, Q11, Q13, Q27) re-checked: final
      `cee_166` run compared with `ev166\main-cee` (the review's comparison: main code + key on
      the freeze vs. #150 code + key on the #150 DB) and with `ev166\main-150`; each drop listed
      as fixed or explained. Note: as-of 2026-10-29 here, 2026-10-30 in the review.
- [ ] #190: decision recorded in `specs/retrieval.md` (the floor applies to the on-theme slot
      or not, and why).
- [ ] #190: on `cee`, Q21 retrieves `MS-DECK-2026-strategic-update#22` (or another MS chunk on
      the theme) and its coverage note no longer reports Morgan Stanley as a theme gap; Q7, Q10,
      Q12, Q19, Q21, Q28 and all others: no PASS -> FAIL vs. main.
- [ ] Fixture tests: Q28 shape (outlier best chunk does not drop a relevant chunk) and #190
      shape (on-theme chunk below the floor keeps its theme slot, no gap reported).
- [ ] `pytest -q` passes; `python scripts/verify_cee.py run` PASS; 0 real calls.
- [ ] `cee` unchanged; `cee_166` dropped and `wt-166-150` removed at the end.
- [ ] PR closes both #166 and #190.

## Progress log
- 2026-11-17 18:36 - plan written (branch `tl/166-floor-after-speaker-turns` from `origin/main`
  `6316494`, after #181). #166 and #190 done together: both change how the per-firm floor
  meets the slots in `select()`.
