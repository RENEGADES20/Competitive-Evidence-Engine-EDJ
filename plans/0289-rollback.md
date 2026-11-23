# 0289 - Remove the unused reduce v6 (#284) and facts table (#285) code

Issue: #289    Role: TL    Spec: specs/answer-citations.md    Design: ADR-022 (Deferred), `docs/results/w13-reduce-short.md`, `docs/results/w13-facts.md`

## Goal
The two switched-off code paths are gone: `REDUCE_PROMPT=v6` (PR #287) and `FACTS=on` with its `facts` table (PR #288).
The default behaviour is byte-identical to `main`. The results docs, their evidence, the kept analysis scripts,
ADR-022 and the plans stay. #283 `MAP_PREFIX` is not touched.

## Files to change
Reversed from the two merge diffs (route: NB4 below) (`4d4b24d^1..4d4b24d`, `08799a6^1..08799a6`); nothing on `main` touched these
files after them, so each hunk goes back to its pre-PR text.
- `src/cee/config.py` - `REDUCE_PROMPTS` back to `("v5.2", "v5.3")`; `facts` setting, `FACTS_MODES`, `FACTS_DEFAULT` removed.
- `src/cee/answer/prompt.py` - `SYSTEM_PROMPT_V6` removed.
- `src/cee/answer/reduce.py` - `v6()`, item refs in the message, v6 schema, `referable` / `item_refs` / render code
  (`unknown_ref`, `ref_part_mismatch`), `mock_reduce_v6`, the `to_answer(..., m)` argument and the render log removed.
- `src/cee/answer/schema.py` - `Answer._render` removed. `src/cee/ask.py`, `scripts/eval_run.py` - `to_answer` calls
  without the matrix, as before #287.
- `src/cee/answer/extract.py` - the `run_map` facts hook removed. `src/cee/answer/matrix.py` - `EvidenceMatrix.facts`,
  `counts()` `sources` / `facts_cells` keys and the `facts` key of the dump removed; `source` comment restored.
- Deleted: `src/cee/facts.py`, `scripts/extract_facts.py`, `config/facts.yaml`, `tests/test_facts.py`,
  `tests/test_reduce_v6.py`. `tests/test_reduce_stream.py` - the invalid-version probe uses `v9` (pre-#287 it was `v6`,
  which the grep check would hit).
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-answer.md`, `ask-progress.md` - the #284 v6 step and notes removed.
- `db/schema.sql` - `facts` table and index removed. `db/upgrade.sql` - the CREATE replaced by `DROP TABLE IF EXISTS facts;`
  (idempotent; the index goes with the table).
- `docs/RUN.md` - `v6` from the `REDUCE_PROMPT` choices, the #284 reduce-only block and the facts block (PowerShell and
  bash) removed. `.env.example` - `REDUCE_PROMPT` comment back to `v5.2 | v5.3`; `FACTS=` removed.
- `specs/answer-citations.md` - the #284 v6 section and the #285 paragraph removed.
- `docs/DECISIONS.md` ADR-022 - stays Deferred; one note line "code removed by #289 (2026-11-23); a revival rebuilds from
  PR #288"; the two `FACTS=off` sentences say "(code removed by #289)" (NB2). The decision text is unchanged.
- `docs/results/w13-reduce-short.md`, `docs/results/w13-facts.md` - one line each: code removed by #289.
- `run-short.ps1` / `.sh`, `run-extract.ps1` / `.sh`: **kept, marked not runnable** (one header comment each: "not runnable
  after #289: the code it drives was removed; kept as the record of how the evidence was made"). Same for the kept
  analysis scripts that import removed code (`render_check.py`, `g0_upper_bound.py`): header line only, no other change.

## Steps
1. Reverse the src / scripts / tests hunks; delete the five files. pytest locally.
2. Schema and upgrade; run `db/upgrade.sql` twice on the local DB (`docker exec ... psql -f`), confirm `facts` is gone.
3. Docs, spec, ADR note, results-doc lines, script headers.
4. Mock compare, 0 calls: `run-mock.sh` on this branch vs a clean `main` worktree (d2c742c), fts Q1-Q30, rule plans and #272
   plans (`cache/ev284/plans-272`, `PLAN_VERSION=ds-strict-2-plan-off-c8000-s1`), compared with
   `docs/results/w12-latency/cmp_mock.py` as in `docs/results/w13-facts/mock-compare.txt`. Outputs in `cache/ev289/`;
   the summary goes in the PR.
5. Grep check; /finish-task.

## TL conditions (review round 1, PR #290 comment 7108512546; TL accepted all)
- B1: 0-call request hashes on clean `main` d2c742c and on the branch, fts Q1-Q30 mock, rule plans: sha256 of every
  DeepSeek map request (`deepseek_extract_request`: system, message, schema), and of `reduce.system_prompt()`,
  `reduce_message` and `reduce_schema` per finished matrix; 30/30 equal. Logged keys that change by design:
  `matrix.counts()` loses `sources` / `facts_cells`, `matrix.dump()` loses `facts`.
- B2: tree check `git diff 4d4b24d^1 HEAD --stat -- src tests scripts/eval_run.py db/schema.sql config .env.example`;
  record the stat in the PR and explain every file it lists.
- NB1: header also on `g0_upper_bound.py` (`cmp_mock6.py`, `coverage272.py`, `analyze.py`, `mocks.sh` import nothing removed).
- NB2: ADR-022: the two `FACTS=off` sentences say "(code removed by #289)"; the TL approves this ADR edit.
- NB3: `SELECT count(*) FROM facts` before the drop, result in the PR; `upgrade.sql` comment "remove this line if a
  facts table is revived".
- NB4: route chosen: `git revert -n -m 1` of both merges, then the kept paths (`docs/results`, `plans`,
  `docs/DECISIONS.md`, `docs/PROGRESS.md`) restored from HEAD; B2 shows the result.
- NB5: the PR says the verify-cee recipe and driver edits only delete v6-only steps.

## Acceptance
- [x] B1 request hashes 30/30 equal; B2 tree stat recorded and explained.
- [x] pytest green (CI `gh pr checks`).
- [x] Mock eval fts Q1-Q30 identical to clean `main`, rule plans and #272 plans (30/30 each, same map call counts).
- [x] `git grep -i -E "facts_cells|REDUCE_PROMPT.*v6|FACTS="` hits only `docs/results/`, `plans/` and `docs/PROGRESS.md`
      line 174 (the bot-written #287 status line: "v5.3 on v6"; PROGRESS is never edited by hand).
- [x] `db/upgrade.sql` twice on the local DB: no error, `facts` absent afterwards.
- [x] verify-cee: not run. The app shows nothing different by default: both paths were off and the mock compare proves
      the default answers identical.

## Risk (why this plan is reviewed)
Schema change: `DROP TABLE facts`. The table was never filled (no extraction was run, `config/facts.jsonl` never
existed), so no data is lost; snapshots before #285 never had it. ADR-022 gets a note only.

## Paid calls
0.

## Progress log
- 2026-11-23 - plan written; worktree `wt-289` from origin/main d2c742c.
- 2026-11-23 - review round 1 CHANGES REQUESTED; TL conditions folded in. Built via revert -n + restore; pytest 1194
  passed locally; local DB `facts` had 0 rows, `upgrade.sql` twice: exit 0, `facts` absent.
- 2026-11-23 - mock compare identical 30/30 (rule plans, 74 map calls) and 30/30 (#272 plans, 454); B1 hashes 30/30
  equal (74 map requests, 30 reduce); evidence `D:\ALLPROJECTS\EDJ\cache\ev289\`.
