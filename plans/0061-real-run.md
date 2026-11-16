# 0061 - Real-model run of Q19, Q24, Q25, Q28, Q29 on prompt v1 (capped)

Issue: #61    Role: S2    Spec: specs/answer-citations.md

## Goal
Each of the five remaining boundary and gap questions is answered once by the real model and
judged against its `passes_if` (`evals/questions.yaml`); failures become fixes verified on the
mock, or issues. Prompt v1 is judged, not rewritten (issue scope).

## Paid-call plan (written before the first call)
| Q | Why the mock cannot show it | Calls |
|---|---|---|
| Q19 | `answer_with_boundary`: does the model cross into "should"? | 1 |
| Q24 | `gap_with_adjacent`: does it decline an invalid cross-firm comparison? | 1 |
| Q25 | `gap_with_adjacent`: disclosed vs undisclosed compensation | 1 |
| Q28 | standard attrition wording and `differs_because` | 1 |
| Q29 | "Payout grids are not public." and the code-filled registry source (#51) | 1 |
| spare | one re-check per fixed question | <= 2 |
Cap `--max-calls 7`; one run; outputs cached in `.eval-runs/cache/`; no loops, no re-rolls.

## Files to change
- `plans/0061-real-run.md` (this file). Judgement table in the PR. Reports and raw outputs in
  `.eval-runs/` (git-ignored). Fixes found here land in their own PRs/issues (below).

## Steps
1. Free: mock retrieval run of the five questions.
2. Paid: `LLM_PROVIDER=anthropic scripts/eval_run.py --real --max-calls 7 --questions Q19,Q24,Q25,Q28,Q29`
   (provider set for that command only; `.env` keeps mock).
3. Judge each answer against `passes_if`; check cited chunks support each claim; quote any
   normative sentence; run the #52 number check on the cached outputs.
4. Fix or file what fails.

## Acceptance
- [x] Exactly the 5 remaining questions, one call each; cap `--max-calls 7` (5 used)
- [x] Per question: expected vs got behavior, cited chunks support each claim, normative sentences quoted (none)
- [x] Q30 shows the code-inserted GWIM caveat (#106)
- [x] Fixes verified on the mock first; re-checks used saved outputs (0 extra calls)
- [x] PR states calls used and model

## Progress log
- 2026-11-05 - plan approved by S2; Anthropic, `LLM_MODEL` from `.env`
- 2026-11-05 14:20 - mock run: no forbidden hits; Q19 coverage 0.25 (THEME docs in entity mode, S1),
  Q29 refusal FAIL on must-not MS-10K-2025#696 (known). `.eval-runs/s2-61-mock`
- 2026-11-05 14:25 - first paid attempt failed before any request: the repo `.env` had an empty
  ANTHROPIC_API_KEY (0 calls). S2 filled it
- 2026-11-05 14:27 - paid run: 5 real calls, 0 reused. All five got the expected behavior; no
  normative sentence; hand-off verbatim on Q19; GWIM caveat on Q24 and Q28. `.eval-runs/s2-61-real-v1`
- 2026-11-05 14:45 - number check (#52) on the cached answers flagged 3 classes of correct figures
  (table header in another chunk, 12/31/2025, Item 11). Fixed on the #52 branch (PR #154, commit
  3d0fc3f): 44 figures, 0 flagged, 0 new calls
- 2026-11-05 15:20 - filed #155 (S2: Q29 A4 misdates the MS 3Q26 release as "September 2025") and
  #156 (C1: Q28 passes_if says neither firm discloses attrition; EDJ 10-Qs do). Spare calls unused
