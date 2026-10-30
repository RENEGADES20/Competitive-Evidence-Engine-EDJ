---
description: Tech lead only - run a TL issue end to end with an implementer agent and an independent reviewer agent
argument-hint: <issue#>
---

Run TL issue #$ARGUMENTS from start to merge. You are the **coordinator**: you start agents and
pass numbers between them; you do not write the code or the review yourself. Tell the tech lead
in one line when each stage starts and ends.

Only for issues labelled `role:tl`. Check first: `gh issue view $ARGUMENTS` (label, Depends on
merged). If not, stop and say why.

## Stages
1. **Plan.** Start an **implementer** agent: "Do steps 1-3 and 5-6 of `.claude/commands/start-task.md`
   for #$ARGUMENTS: read the issue and spec, branch `tl/$ARGUMENTS-<slug>` from fresh `main`, write the
   ExecPlan `plans/<NNNN>-<slug>.md`, commit and push it. Do not change any other file. Report the branch."
2. **Plan review.** Start a **new reviewer** agent (never reuse one, never pass the implementer's
   report): "Run `.claude/commands/tl-review.md` with `plan $ARGUMENTS`."
   - CHANGES REQUESTED: send the issue comment's numbered fixes to the implementer (same agent, it
     keeps context), then a new reviewer again. At most **2 returns**; a third escalates.
3. **Build.** Implementer: "The plan is approved (issue comment). Implement it on the branch, keep
   the Progress log current, then do every step of `.claude/commands/finish-task.md`. Report the PR number."
4. **PR review.** New reviewer: "Run `.claude/commands/tl-review.md` with `pr <PR#>`." It merges on approval.
   - CHANGES REQUESTED: implementer fixes on the same branch and pushes; new reviewer. At most **2 returns**.
5. **Close out.** Report to the tech lead: PR link, merged or not, what stays open (`Part of`),
   and the board move (Done -> Approved, done by the merge).

## Stop and ask the tech lead
- A third return at either review stage.
- The reviewer posts ESCALATED TO TL (ADR, paid call, deleted data, ground rules, teammate file, a check it could not run).
- The implementer is blocked or the issue is unclear.

## Rules
- Agents run one after another in the same checkout; never two writers at once.
- The reviewer's only inputs are issue/plan/PR numbers and the repo. That is what makes it independent.
- Paid API calls: 0 unless the plan already planned them and the tech lead agreed (CLAUDE.md).
- Teammate PRs are not reviewed this way; they stay with the tech lead.
