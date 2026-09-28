---
description: Start work on a GitHub issue - read it, find the spec, write an ExecPlan, create the branch
argument-hint: <issue-number>
---

Start task for issue #$ARGUMENTS. Explain each step to the user in plain language.

Task states: **Todo -> In Progress -> Done -> Approved.** This command moves the task to In Progress;
`/finish-task` moves it to Done (waiting for review); only the tech lead moves it to Approved, by merging the PR.

1. **Read the issue.** Run `gh issue view $ARGUMENTS`. Note the role, week, goal, acceptance,
   linked question IDs and spec link. If the issue is unclear or has no acceptance items, stop
   and ask the user to clarify it on GitHub first.
2. **Check the working tree.** Run `git status` and `git switch main && git pull`. If there are
   uncommitted changes, stop and ask the user what to do with them.
3. **Find the spec.** Use the table "Which spec to read before touching what" in `CLAUDE.md`.
   Read that spec fully, plus the ground rules in `CLAUDE.md`. Read the linked questions in
   `evals/questions.yaml`.
4. **Plan.** Switch to plan mode (or, if not available, do not edit files yet). Draft an ExecPlan
   using the template in `PLANS.md`: Goal / Files to change / Steps / Acceptance / Progress log.
   Acceptance must list the linked question IDs or concrete checks. Show it to the user and
   revise until they approve. Tiny config/data-only tasks may skip the ExecPlan (say so).
5. **Create the branch.** `git switch -c <role>/$ARGUMENTS-<short-slug>` (role in lower case,
   e.g. `c2/$ARGUMENTS-rjf-transcripts`).
6. **Save the plan** as `plans/<issue number padded to 4 digits>-<slug>.md` and add the first
   Progress log line with the current date and time.
7. **Update the board.** Tell the user: "Move issue #$ARGUMENTS to **In Progress** on the project
   board." (Optionally comment on the issue with the branch name: `gh issue comment $ARGUMENTS --body "..."`.)
8. Start on step 1 of the plan only after the user says go.
