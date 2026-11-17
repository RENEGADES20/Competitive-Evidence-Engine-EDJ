# 0117 - Entity+theme mode for several firms (Q12, Q21)

Issue: #117    Role: S1    Spec: specs/retrieval.md (+ specs/answer-citations.md for the coverage line,
specs/thematic.md for the new topic)

## Goal
When a question names several firms and a theme, every firm gets its own share of the 20 slots,
filled first with its chunks on that theme; tier 5 research keeps up to 4 slots (as in #116).
A firm with nothing on the theme is reported as a theme gap by code, not left to the model.

## Files to change
- `config/entities.yaml` - "these five" joins the `core_five` peer phrases (Q21 resolved no firm).
- `config/topics.yaml` - new top-level topic `client_acquisition` (Q12 named no topic). C3's file:
  flagged in the PR.
- `src/cee/retrieve/fts.py`
  - `resolve()`: two or more firms + a theme -> `entity+theme` (#116 allowed one firm only).
  - `search()` / `select()`: firm slots (k minus research) split evenly across the named firms;
    inside a firm, chunks whose text carries the theme (`tag_text`, the tagger's own rules; firm
    chunks have no `chunk_topics` rows) take the firm's slots first, then the rest by rank.
  - `theme_gaps(q, hits)`: named firms with no on-theme hit.
- `src/cee/answer/validate.py` - `coverage_note`: one line "No passages on <theme> for X." (S2 area).
- `scripts/eval_run.py` - theme gaps in the report.
- `config/entities.yaml` - `metric_phrases: ["advisor headcount"]` (added after the Q23 finding, see log).
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-answer.md` - Q21 theme-gap step.
- `tests/test_eval_run.py` - fake queries carry `themes`.
- `tests/test_retrieval_themes.py`, `tests/test_fts_synonyms.py` - resolve, per-firm quota, gaps.
- `specs/retrieval.md` - per-firm theme quota.

## Steps
1. "Before" eval on current code: snapshot corpus-2026-10-29, `--as-of 2026-10-27`.
2. Config changes + `resolve()`; tests.
3. Per-firm quota + `theme_gaps`; tests.
4. Coverage line + eval report column.
5. "After" eval: against the "before" run and `--baseline evals/baselines/corpus-2026-10-22/report.json`.
6. pytest, verify-cee. 0 real calls.

Risk: several firms + a theme also changes Q7, Q10, Q11, Q23, Q28. Q23's headcount tables may not
carry recruiting words, so on-theme-first could push them out. Any PASS -> FAIL: stop and ask
(fallbacks: fewer research slots, or the mode only where it does not hurt).

## Acceptance
- [x] Q12: chunks from SCHW and EDJ on client acquisition, or the firm without one listed as a theme gap
- [x] Q21: chunks from all five firms on the wealth transfer (BAC from GWIM only) plus research;
      a firm without one listed as a theme gap
- [x] `eval_run.py` vs the corpus-2026-10-22 baseline: no question PASS -> FAIL
- [x] pytest passes; verify-cee PASS; 0 real calls

Out of scope: prompt or answer wording (S2).

## Progress log
- 2026-11-16 13:28 - plan written and approved; branch `s1/117-entity-theme-per-firm`
- 2026-11-16 13:35 - DB already holds corpus-2026-10-29 (111 docs, 17183 chunks). "Before" eval
  (`.eval-runs/0117-before`, as of 2026-10-27): PASS 28 | FAIL 2 (Q15, Q19). Q12 EDJ slots are
  off-topic (liquidity, rate risk); Q21 resolved no firm (theme mode, coverage 0.667).
- 2026-11-16 - decision: Q12's theme lives in a new S1 list `firm_themes` in config/entities.yaml
  (adding it to C3's topics.yaml would require tier 5 sources from 2 publishers, test_source_matrix).
- 2026-11-16 - first try (on-theme chunks first, 4 research slots for several firms): Q12 PASS
  (SCHW 10 / EDJ 8 on theme), Q21 0.667 -> 1.0, but **Q11 and Q23 PASS -> FAIL**. Changed to
  THEME_FIRST = 1 (each firm's best on-theme chunk is sure of a slot, then rank order). Sweep
  THEME_FIRST {1,2} x research slots {0,2,4}: Q23 FAILs in every setting (0.714 -> 0.429): each
  firm has 4 slots and the 4th holds MS's supplement / RJF's press release. Q11 and Q23 are themed
  only by "advisor headcount" (a metric, not a theme). Stopped to ask.
- 2026-11-17 - user decision: S1 `metric_phrases: ["advisor headcount"]` in config/entities.yaml;
  a metric phrase never makes a question themed. Q11, Q23 back to entity mode. One research quota
  (THEME_K = 4) for one or several firms (2 and 4 slots measured the same).
- 2026-11-17 - coverage line (validate.py), eval report `themes` / `theme_gaps`, tests (pytest 372
  passed, 1 skipped), spec. "After" eval (`.eval-runs/0117-after`, vs corpus-2026-10-22 baseline):
  PASS 28 | FAIL 2 (Q15, Q19, both FAIL before); no PASS -> FAIL; tier-1 recall 0.646, refusal 5/5.
  vs "before": only Q21 IMPROVED (0.667 -> 1.0, THEME:research + BAC GWIM transcript) and Q10
  REGRESSED (1.0 -> 0.8, still PASS: a research slot took the BAC GWIM transcript). Q1, Q7, Q14
  lower than the 10-22 baseline but identical in "before" (corpus drift).
  Theme gaps: Q12 none (SCHW 10 / EDJ 8 chunks on client acquisition); Q21 MS, RJF (0 chunks in the
  whole corpus with a wealth-transfer keyword; SCHW 7, EDJ 3); Q7, Q28 MER; Q10 all but SCHW; Q19 EDJ.
- 2026-11-17 - verify-cee (`.verify-runs/20261117-171614-8f92cb1`, uncommitted tree on 8f92cb1):
  VERIFY PASS; ask-answer (incl. new Q21 theme-gap step), ask-progress, gap-path, invalid-chunk,
  coverage, filters, feedback PASS; open-citation and download-document UNREACHABLE (raw files not
  in data/raw/, same as #116). 0 real calls.
