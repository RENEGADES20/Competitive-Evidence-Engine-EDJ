# 0116 - Firm questions that name a theme also retrieve tier 5 research

Issue: #116    Role: S1    Spec: specs/retrieval.md (+ topic tags from specs/thematic.md, C3)

## Goal
When a question names a firm and a topic from `config/topics.yaml`, retrieval returns the
firm's chunks plus a small quota of tier 5 research chunks tagged with that topic. The entity
hard filter still holds for firm documents: no other firm's chunks come back.

## Files to change
- `src/cee/retrieve/fts.py`
  - `Query.themes`: top-level topic ids named in the question, matched with C3's `tag_text`
    (the same keyword rules that tag chunks). Firm + topic -> mode `entity+theme` (spec rule).
  - `theme_filter()`: SQL hard filter, `entity_id IS NULL` and the chunk tagged with one of
    the topics in `chunk_topics`.
  - `search()`: in `entity+theme`, a second pass over research chunks fills up to
    `THEME_K = 4` of the 20 slots (at most 2 per document); the firm gets every other slot.
    Time windows apply to both passes.
- `scripts/eval_run.py` - `forbidden()`: in `entity+theme`, a chunk with no firm is allowed.
  Another firm's chunk is still forbidden.
- `tests/test_retrieval_themes.py` (new) - resolve, quota and filter tests on a scratch schema
  (pattern from `tests/test_fts_window.py`).
- `tests/test_eval_run.py` - forbidden() with research chunks.
- `specs/retrieval.md` - the research quota in entity+theme mode.

## Steps
1. "Before" eval on the current code, loaded snapshot corpus-2026-10-29 (the 10-22 baseline
   has no tier 5 documents, so before/after isolates the code change).
2. `Query.themes` + mode; `theme_filter`; tests.
3. Research quota in `search()`; tests.
4. `forbidden()` change; tests.
5. "After" eval: `eval_run.py --as-of 2026-10-27 --baseline evals/baselines/corpus-2026-10-22/report.json`,
   and against the "before" run.
6. pytest, verify-cee.

Other entity questions that name a topic and will change: Q7, Q10, Q11, Q23 (advisor_recruiting,
mass_affluent), Q28 (gap, attrition). If Q28 or Q23 gets worse, stop and ask before narrowing.

## Acceptance
- [x] Q19 returns at least one THEME chunk tagged `younger_investors` (4)
- [x] Q19 returns no chunk from a firm other than EDJ (entity filter holds)
- [x] `eval_run.py` against the corpus-2026-10-22 baseline: no question PASS -> FAIL;
      Q7, Q10, Q11, Q23, Q28 unchanged (several firms stay `entity`, see log)
- [x] pytest passes; verify-cee PASS; 0 real calls

Out of scope: per-firm quotas within a theme for Q12/Q21 (#117); the prompt's
"Research research" wording (S2).

## Progress log
- 2026-10-30 10:37 - plan written and approved; branch `s1/116-theme-docs-in-entity-questions`
- 2026-10-30 10:40 - "before" eval on current code, snapshot corpus-2026-10-29, as of 2026-10-27:
  PASS 27 | FAIL 3 (Q15, Q19, Q29). Q19: 0 research chunks.
- 2026-10-30 11:05 - themes + research quota in fts.py, forbidden() change, tests (234 passed).
  Also changed `tests/test_fts_synonyms.py`: "the five + recruiting/headcount" now resolves to
  entity+theme. Q19 now gets 4 research chunks (Cerulli, BofA Private Bank), EDJ only.
- 2026-10-30 11:10 - "after" eval: PASS 26 | FAIL 4. **Q23 PASS -> FAIL** (coverage 0.714 ->
  0.429): the 4 research slots (McKinsey, Kitces on advisor shortage) pushed out
  `MS-SUPP-2026Q1#14` and `RJF-PR-2025-10-22-01#2`. Q10, Q11 also lower. Q19 has a THEME:research
  hit but stays FAIL (0.25): its other expected sources are competitor press, which the EDJ filter
  excludes by design, and THEME:survey (no tier 5 doc is typed `survey`). Stopped to ask.
- 2026-11-02 - user decision: research slots only when the question names exactly one firm;
  several firms + a topic stay `entity` (left to #117). `tests/test_fts_synonyms.py` back to
  its original assertion. pytest 236 passed.
- 2026-11-02 - "after" eval, same snapshot and as-of: PASS 27 | FAIL 3 (Q15, Q19, Q29).
  vs "before": only Q19 changed (IMPROVED, THEME:research hit, coverage 0 -> 0.25).
  vs corpus-2026-10-22 baseline: no PASS -> FAIL; Q1, Q7, Q14, Q17 lower but still PASS and
  identical in the "before" run (corpus drift, not this change).
- 2026-11-02 - verify-cee (`.verify-runs/20261102-125740-3fa63a9`): VERIFY PASS; ask-answer,
  ask-progress, gap-path, invalid-chunk, coverage PASS; open-citation steps 1-4 PASS, then
  UNREACHABLE (raw PDF for MS-SUPP-2026Q3#16 not on this laptop); download-document UNREACHABLE
  (raw file not in data/raw/). Q19 through `ask()` (mock): mode entity+theme, firms EDJ + research
  only, research chunks labelled `Research research <date> [research]` by code. 0 real calls.
