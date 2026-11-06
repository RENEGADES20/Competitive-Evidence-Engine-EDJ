# 0159 - Q29 on main: search 'pay' only through its synonyms

Issue: #159    Role: TL    Spec: specs/retrieval.md (S1), ADR-001, ADR-009, ADR-010

## Goal
On `main`, the bare word `pay` in a question is no longer a full-text search word; it is searched
only through its synonyms (`compensation`, `payout`). Q29 ("What does Morgan Stanley pay its
financial advisors?") then returns the advisor-payout passage `MS-10K-2025#153` and none of its
must-not chunks (clearing-guarantee notes such as `MS-10K-2025#696`), and every other question
returns exactly the chunks it returns today. The code is a verbatim port of the `synonym_only`
part of #125 (PR #158 on `exp/hybrid`, 3449cc5): same lines, same names, so later one-way merges of
`main` into `exp/hybrid` stay clean. No hybrid, no mode switch, no vectors on `main` (ADR-010,
sponsor spec EJ-10).

## Facts (read-only, 2026-11-05)
- `origin/main` = 20c59cd. Merge base of `main` and `exp/hybrid` = 9dc4c9b. Since 9dc4c9b `main`
  changed none of `src/cee/retrieve/fts.py`, `config/entities.yaml`, `tests/test_fts_synonyms.py`
  (only `specs/retrieval.md`, ADR-010 wording), so the #125 hunks apply to `main` unchanged.
- `git merge-tree --write-tree origin/exp/hybrid origin/main` today: exit 0 (clean), tree 31a8a51.
- Q29 diagnosis (`plans/0125-hybrid-retrieval.md` on `exp/hybrid`, Facts): terms `pay financial
  advisors`, synonyms of `pay` = `compensation`, `payout`. `MS-10K-2025#696` (FICC clearing
  guarantees, must-not) contains "pay any net liquidation amount" and `payout` -> rank 9.80; the
  answer chunk `MS-10K-2025#153` ("formulaic payouts ... compensation") -> 8.52. `pay` occurs in no
  other question of `evals/questions.yaml` (checked again on 20c59cd: only line 442, Q29).
- #125 evidence for the same change on 9dc4c9b (`p125r-fts-main` vs `p125r-fts-after`): identical
  chunk_ids on 29/30, only Q29 differs, Q29 FAIL -> PASS, PASS 28 / FAIL 2 (Q15, Q19), refusal gap
  4/5 -> 5/5. Expected again here, to be measured, not assumed.
- Hunks of `fts.py` on `exp/hybrid` (`git diff 9dc4c9b 3449cc5 -- src/cee/retrieve/fts.py`):

  | # | Hunk | Belongs to | Port? |
  |---|---|---|---|
  | 1 | module docstring "Three retrieval modes ..." (4 lines) | mode switch | no |
  | 2 | `from cee.config import entities_config, settings, vectors_enabled` | mode switch | no |
  | 3 | new `synonym_only_words()`, new `keyword_terms(q)`, `_tsquery_sql(terms, synonyms=None)` | `synonym_only` | **yes** |
  | 4 | `select(..., dup_jaccard=None)` + docstring + `dup_jaccard` default line | hybrid (#126) | no |
  | 5 | `> dup_jaccard` in `select()` loop | hybrid (#126) | no |
  | 6a | `MODES`, `HybridUnavailable`, `HYBRID_NEEDS_VECTORS`, `search(q, k, mode)`, rename to `fts_search` | mode switch | no |
  | 6b | in the search body: `terms = _search_terms(q)` / `if q.window: terms += RECENCY_TERMS` / `_tsquery_sql(terms)` -> `terms, synonyms = keyword_terms(q)` / `_tsquery_sql(terms, synonyms)` | `synonym_only` | **yes** (stays in `search()` on main; no rename) |

  `_search_terms` itself is not changed on `exp/hybrid`; the new `keyword_terms` wraps it.
  `rank_sql` then sees the terms without `pay` and the same synonym phrases, as on `exp/hybrid`.
- Dry run (scratch worktree from 20c59cd, deleted afterwards, nothing pushed): hunks 3 + 6b of
  `fts.py`, plus the `config/entities.yaml` and `tests/test_fts_synonyms.py` hunks of 3449cc5 ->
  diff +44 / -6 in 3 files; `tests/test_fts_synonyms.py` 15 passed; `git merge-tree --write-tree
  origin/exp/hybrid <dry commit>` exit 0, tree 31a8a51 = the same tree as merging today's `main`:
  the port adds nothing that `exp/hybrid` does not already have.

## Files to change
- `config/entities.yaml` (synonyms section: S1 reviews, C1 FYI) - append the 5-line
  `synonym_only: [pay]` block of 3449cc5 verbatim (comment says "#125", kept as is).
- `src/cee/retrieve/fts.py` (S1) - hunks 3 and 6b above, verbatim. No other line; no constant
  (`K`, `FLOOR`, `MAX_PER_DOC`, `DUP_JACCARD`, `WINDOW_MAX_PER_DOC`, `THEME_K`, `THEME_MAX_PER_DOC`,
  `POOL_PER_GROUP`, `DENSITY_WEIGHT`, `RECENCY_TERMS`) changes.
- `tests/test_fts_synonyms.py` (S1) - append the two tests of 3449cc5 verbatim
  (`test_synonym_only_word_is_searched_through_its_synonyms`,
  `test_question_without_a_synonym_only_word_keeps_its_terms`).
- `specs/retrieval.md` (S1) - one comment line in the interface sketch, under
  `expand_synonyms(terms)`; not the `exp/hybrid` "Retrieval modes" section (that one describes the
  modes and stays on `exp/hybrid`). Text:
  `    # synonym_only (config/entities.yaml, #159): "pay" is searched only through its synonyms;`
  `    #   the bare word leaves the FTS words (Q29: "pay any net liquidation amount" is not advisor pay)`
- `plans/0159-q29-synonym-only.md` - this plan, Progress log.

No other file. No recipe or `scripts/verify_cee.py` change: no user feature changes (retrieval
output for one question).

## Steps
Shell setup for every step (Windows PowerShell / macOS bash), from the repo root, core venv,
vectors off, mock provider:
```
$env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; $env:LLM_PROVIDER="mock"; Remove-Item Env:CEE_VECTORS -ErrorAction SilentlyContinue; $env:PYTHONPATH="$PWD\src"
```
```
export LLM_PROVIDER=mock PYTHONPATH="$PWD/src"; unset CEE_VECTORS
```
`PY` = `.venv\Scripts\python.exe` (Windows) / `.venv/bin/python` (macOS). Check first that the
local DB holds `corpus-2026-10-29` (`PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`).

1. **Baseline on fresh `main`** (this branch before any code edit = 20c59cd + this plan):
   `PY scripts/eval_run.py --as-of 2026-10-29 --out .eval-runs/p159-main` and `PY -m pytest -q`.
   Log PASS/FAIL counts, Q29 line, refusal gap, pytest count (the floor) in the Progress log.
2. **Port config + tests** verbatim:
   `git diff 9dc4c9b 3449cc5 -- config/entities.yaml tests/test_fts_synonyms.py | git apply`.
   `git diff --stat` -> those two files only, +5 and +15.
3. **Port `fts.py` hunks 3 and 6b** by hand edit, copying the lines from
   `git show 3449cc5:src/cee/retrieve/fts.py`. Check: `git diff 3449cc5 -- src/cee/retrieve/fts.py`
   lists only hunks 1, 2, 4, 5, 6a (reversed) and the `search`/`fts_search` name; nothing from
   hunks 3 or 6b. `PY -m pytest -q tests/test_fts_synonyms.py` -> all pass.
4. **Spec line** in `specs/retrieval.md` (text above).
5. **Merge check**: commit, then `git merge-tree --write-tree --name-only origin/exp/hybrid HEAD`
   -> exit 0, no conflicted file.
6. **Eval after**: `PY scripts/eval_run.py --as-of 2026-10-29 --baseline .eval-runs/p159-main/report.json --out .eval-runs/p159-after`.
   Compare chunk_ids per question with a scratch script (not committed) reading both
   `report.json` files. If any question other than Q29 changes, or any PASS -> FAIL: stop, log
   the numbers, bring the plan back for review.
7. **Full checks**: `PY -m pytest -q`; `PY scripts/verify_cee.py run` (all features).
8. Progress log, then `/finish-task` (PR: `Closes #159`, S1 named as reviewer for `fts.py`, the
   synonyms section and the spec line; Progress line; 0 real calls).

## Acceptance
- [x] Q29 (`p159-after`): refusal `ok`, `MS-10K-2025#153` among the hits, no chunk from its
      `must_not_return` list (`MS-10K-2025#574, #687, #690, #692, #693, #694, #696, #699`).
- [x] `p159-main` vs `p159-after`: identical chunk_ids in the same order on 29/30 questions; only
      Q29 differs; no PASS -> FAIL (`--baseline` status column: no REGRESSED).
- [x] `pytest -q`: all pass, count >= the step-1 count on `main` (+2 expected).
- [x] `verify_cee.py run` -> PASS (evidence folder named in the PR).
- [x] `git merge-tree --write-tree origin/exp/hybrid HEAD` -> exit 0 (main stays mergeable into
      `exp/hybrid`).
- [x] `git diff origin/main -- src/cee/retrieve/fts.py`: only hunks 3 and 6b; no constant changed;
      no `mode`, `hybrid`, `vectors_enabled`, `settings` or `dup_jaccard` on `main`.
- [x] Spec: the `synonym_only` line in `specs/retrieval.md`.
- [ ] S1 review (requested on the PR) on the PR (owner of `fts.py`, the synonyms section and the spec).
- [x] Mock only, 0 paid calls.

## Risks / unsure
- The spec line is new text on `main` that `exp/hybrid` does not have; its place (interface
  sketch) is 10 lines from `exp/hybrid`'s inserted section, so the merge stays clean (step 5
  checks it). `exp/hybrid` will then mention the rule twice; fine for an experimental branch.
- The config comment says "(#125)", kept verbatim on purpose (identical lines = clean merge).
- Q29 may still be FAIL for another reason (coverage of `MS-10K-2025#128`/`#170`); the issue's
  bar is refusal ok + `#153` + no must-not chunk, which is what Acceptance checks.
- S1 may later rename `synonym_only`; then both branches change together.

## Progress log
- 2026-11-05 21:37 - plan written on `tl/159-q29-synonym-only` from origin/main 20c59cd. Hunk map
  and dry run (scratch worktree under `D:\ALLPROJECTS\EDJ\cache\tmp`, removed; nothing committed
  to any branch) as in Facts. No file other than this plan changed.
- 2026-11-05 21:39 - plan approved (reviewer comment on #159 at e2076b0, no blocking). Step 1 on
  this branch at e2076b0 (= main 20c59cd + this plan file, identical code): `p159-main` PASS 27 /
  FAIL 3 (Q15, Q19, Q29), tier-1 recall 0.796, refusal gap 4/5; Q29 refusal FAIL, misleading
  [`MS-10K-2025#696`], `#153` not returned. `pytest -q` 277 passed (the floor). `DOCTOR PASS`,
  corpus-2026-10-29, 17183 chunks.
- 2026-11-05 21:40 - steps 2-4 (b150f62): `git apply` of the 3449cc5 config + test hunks (+5, +15);
  `fts.py` hunks 3 and 6b copied from 3449cc5 (+24 / -6); `git diff 3449cc5 -- fts.py` shows only
  hunks 1, 2, 4, 5, 6a and the `search` name. Spec line added. Step 5: `git merge-tree --write-tree
  origin/exp/hybrid HEAD` exit 0, no conflicted file.
- 2026-11-05 21:41 - step 6: `p159-after` (baseline `p159-main`): PASS 28 / FAIL 2 (Q15, Q19),
  tier-1 recall 0.796, passages 0.402, refusal gap 5/5. Scratch compare of both report.json files:
  identical chunk_ids (same order) on 29/30, only Q29 differs; PASS -> FAIL none; Q29 PASS, refusal
  ok, misleading [], `MS-10K-2025#153` returned (also `#128`, `#170`), no must-not chunk.
- 2026-11-05 21:46 - step 7: `pytest -q` 279 passed (+2). `verify_cee.py run`: first run
  (`.verify-runs/20261105-214144-b150f62`) open-citation and download-document FAIL with
  `database "cee_verify" does not exist` mid-run (another agent's concurrent verify run shares and
  drops `cee_verify`; not this change). Re-run `.verify-runs/20261105-214441-b150f62`: all 8
  features PASS, VERIFY PASS.
- 2026-11-05 21:48 - origin/main moved to 8fbf35f (#157: `docs/PROGRESS.md`, `plans/0061-real-run.md`
  only); merged into this branch (no rebase). No retrieval/config file touched, so no eval re-run.
