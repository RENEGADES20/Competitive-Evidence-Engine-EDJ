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
1. **Plan.** Start an **implementer** agent: "Do steps 1-6 of `.claude/commands/start-task.md` for
   #$ARGUMENTS: read the issue and spec, draft the ExecPlan from the `PLANS.md` template (Acceptance lists
   question IDs or concrete checks), branch `tl/$ARGUMENTS-<slug>` from fresh `main`, save the plan as
   `plans/<NNNN>-<slug>.md`, commit and push it. In step 4 the reviewer agent approves the plan instead of
   the user: do not wait for the user, and do not change any other file. Report the branch."
2. **Plan review.** Start a **new reviewer** agent (never reuse one, never pass the implementer's
   report): "Run `.claude/commands/tl-review.md` with `plan $ARGUMENTS`."
   - CHANGES REQUESTED (at least one blocking finding): send the issue comment's numbered blocking
     fixes to the implementer (same agent, it keeps context), then a new reviewer again. At most
     **2 blocking returns**; a third escalates.
   - APPROVED with non-blocking notes: not a return. Pass the notes to the implementer with stage 3.
3. **Build.** Implementer: "The plan is approved (issue comment). Implement it on the branch, keep
   the Progress log current, then do every step of `.claude/commands/finish-task.md`. Report the PR number."
   If the plan planned real calls (CLAUDE.md "Paid API calls"), they run last, once, after every mock
   check passes, with every raw output saved in the run's evidence folder and the count in the PR.
4. **PR review.** New reviewer: "Run `.claude/commands/tl-review.md` with `pr <PR#>`." It merges on approval.
   - CHANGES REQUESTED (at least one blocking finding): implementer fixes on the same branch and
     pushes; new reviewer. At most **2 blocking returns**.
   - APPROVED with non-blocking notes: not a return; the reviewer merges. Tell the tech lead the
     notes and any follow-up issues in stage 5.
5. **Close out.** Report to the tech lead: PR link, merged or not, what stays open.
   - `Closes #N`: the merge closes the issue and the board moves it (Done -> Approved).
   - `Part of #N`: the issue and its card stay open. The reviewer has commented the open items on
     the issue; tell the tech lead which ones and who can close them (e.g. a teammate's Mac run).

## Stop and ask the tech lead
- A third blocking return at either review stage.
- The reviewer posts ESCALATED TO TL (ADR, paid calls that are unplanned, more than 10 or needed by the reviewer, deleted data, ground rules, teammate file, a check it cannot run).
- The implementer is blocked or the issue is unclear.

## Rules
- Agents run one after another in the same checkout; never two writers at once.
- The reviewer's only inputs are issue/plan/PR numbers and the repo. That is what makes it independent.
- Paid API calls: 0 unless the approved plan planned them (question IDs, why, 10 or fewer; CLAUDE.md).
  More than 10 or unplanned calls need the tech lead. The reviewer never makes a paid call.
- Teammate PRs are not reviewed this way; they stay with the tech lead.
