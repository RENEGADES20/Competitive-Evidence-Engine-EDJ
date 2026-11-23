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
Each line: command -> expected result (run on the PR head; `git grep -c` prints `file:count`).
- [ ] CLAUDE.md: `git grep -c -E "\*\*Two tracks\.\*\*|A plan is one page|carries risk|any change a user could see|\*\*Each check has one owner\.\*\*|or the experiment note" -- CLAUDE.md` -> `CLAUDE.md:6`.
- [ ] CLAUDE.md scope: `git diff origin/main -- CLAUDE.md | grep "^@@"` -> hunks only in "Branch and PR
      rules", "Verification" and paid-call step 2; `git diff origin/main -- CLAUDE.md | grep -E "^-" | grep -c -E "Every claim cites|Never compose|No evidence|No figure|traceable to where|Nothing normative|Hard filters|Time windows|Citations point|Caveats are inserted|question bank"` -> `0`.
- [ ] PLANS.md: `git grep -c -E "## Keep it to one page|^- \[ \] verify-cee:|^## Paid calls|^## Experiment note" -- PLANS.md` -> `PLANS.md:5` (Paid calls appears in both templates).
- [ ] tl-run.md: `git grep -c -E "## Experiment issues|only when the plan carries risk" -- .claude/commands/tl-run.md` -> `2`.
- [ ] tl-review.md: `git grep -c -E "Each check has one owner|\*\*Docs-only PRs\*\*|^7\. One page" -- .claude/commands/tl-review.md` -> `3`; `git grep -c -i "teammate" -- .claude/commands/tl-review.md .claude/commands/tl-run.md` -> no `teammate-owned` / `teammate file` (only "Teammate PRs" lines remain).
- [ ] finish-task.md: `git grep -c -E "If a user could see the change|rather than copying" -- .claude/commands/finish-task.md` -> `2`.
- [ ] start-task.md: `git grep -c -E "one page|type:experiment" -- .claude/commands/start-task.md` -> `2`.
- [ ] DASHBOARD.md: `git grep -c -E "Only when the plan carries risk|Experiment issues|type:experiment" -- docs/DASHBOARD.md` -> `3`.
- [ ] PR template: `git grep -c -E "experiment: docs/results|verify-cee run on the final head" -- .github/pull_request_template.md` -> `2`.
- [ ] Stale wording: `git grep -n -E "teammate-owned|re-runs pytest|any change to .src/" -- '*.md' ':!plans' ':!docs/results' ':!.dispatch'` -> no hits.
- [ ] `git diff origin/main --stat` -> only the 8 files above plus this plan.
- [ ] `gh label list --search experiment` -> `type:experiment`.
- [ ] `gh pr checks` green.
- [ ] verify-cee: not run - docs and workflow files only; the app cannot show this change.

## Merge
CLAUDE.md changes only Branch and PR rules, Verification and one paid-call sentence (checked above);
no ground rule, invariant or ADR changes, so per `tl-review.md` it is not an escalation item. The PR
reviewer merges on approval; the tech lead asked for this issue and PR in this session.

## Risks
- This PR is reviewed under the old rules (main), so its review still re-runs evidence in full; the
  new rules apply from the next issue.
- Old-flow wording outside the 8 files: `git grep` over `docs/WORKFLOW-SETUP.md` and
  `.claude/skills/verify-cee/SKILL.md` finds only "use before /finish-task" and "/finish-task checks
  the work in the app" (line 146), both still true for app-visible changes. No change, no follow-up.
- `type:experiment` does not exist yet: step 3 creates it before the PR, and nothing uses it before then.

## Paid calls
0.

## Progress log
- 2026-11-22 21:56 - plan written; the 8-file edit was drafted before the issue (branch first named
  `tl/workflow-lean`) and is committed after plan review.
- 2026-11-22 22:05 - plan review round 1 (issuecomment-7091163469): CHANGES REQUESTED, 3 blocking.
  TL ruling (one review round): fixed in place - one command per acceptance item, a Merge section
  (CLAUDE.md scope check, no escalation), a Risks section. Non-blocking 3 (git grep form) taken.
