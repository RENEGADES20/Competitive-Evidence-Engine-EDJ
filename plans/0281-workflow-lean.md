# 0281 - Leaner workflow: experiment track, one owner per check, conditional plan review and verify-cee

Issue: #281    Role: TL    Spec: CLAUDE.md, PLANS.md    Design: the issue's Why section

## Goal
The workflow keeps every protection that matters (ground rules, invariants, paid-call rules, CI,
the 24/30 floor, saved raw outputs) and drops the repeats: checks run by one owner, plan review
and verify-cee only where they prove something, one-page plans, and a short path for experiments.

## Files to change
- `CLAUDE.md` - Branch and PR rules: "Two tracks", one-page plan, conditional plan review.
  Verification: verify-cee only for app-visible changes; "Each check has one owner". Paid calls:
  "(or the experiment note)".
- `PLANS.md` - one-page rule (about 80 lines), template gains `Design:`, a verify-cee line and Paid
  calls; new experiment-note template.
- `.claude/commands/start-task.md` - one page; experiment issues write a note on `exp/`.
- `.claude/commands/finish-task.md` - verify-cee conditional, evidence names its head; link, don't copy.
- `.claude/commands/tl-run.md` - experiment path; stage 2 only on risk items; drop "teammate file".
- `.claude/commands/tl-review.md` - Check rule by owner (CI pytest, reviewer mock eval, verify-cee
  evidence re-run only when missing/failed/stale/doubtful); docs-only PR review; plan check 7
  (one page); drop teammate-file checks.
- `docs/DASHBOARD.md` - section 3b matches; label `type:experiment`.
- `.github/pull_request_template.md` - ExecPlan line (experiment, link); verify-cee checkbox.

## Steps
1. Commit and push this plan; plan review (`/tl-review plan 281`), since it changes CLAUDE.md
   rules (old flow applies until this merges).
2. Commit the 8-file edit (drafted on this branch).
3. `gh label create type:experiment --description "Data question on an exp/ branch, never merged; results doc via docs-only PR"`.
4. Run the grep check below; `/finish-task`; PR; `/tl-review pr`.

## Acceptance
- [ ] Each issue Acceptance item about file content: read the diff of that file -> item present.
- [ ] `grep -rn -E "teammate-owned|re-runs pytest|any change to .src/" --include=*.md .` excluding
      `plans/`, `docs/results/`, `.dispatch/` -> no hits.
- [ ] `git diff origin/main --stat` lists only the 8 files above plus this plan.
- [ ] `gh label list` -> `type:experiment` present.
- [ ] `gh pr checks` green.
- [ ] verify-cee: not run - docs and workflow files only; the app cannot show this change.

## Paid calls
0.

## Progress log
- 2026-11-22 21:56 - plan written; the 8-file edit was drafted before the issue (branch first named
  `tl/workflow-lean`) and is committed after plan review.
