# ExecPlans

An ExecPlan is a one-page plan written before you change anything. It keeps a task small,
reviewable, and tied to the question bank. The idea is borrowed from OpenAI's Codex
ExecPlans, simplified for this team.

## When to write one

- Every delivery issue that changes code or behavior gets one.
- Tiny config-only or data-only tasks (e.g. add an alias, add rows to the manifest) may skip it.
- Experiment issues (`type:experiment`, see CLAUDE.md "Two tracks") write an experiment note
  instead (below).

## Keep it to one page

About 80 lines at most. The plan says what changes and how it is checked; it is not the design
document. Longer material (baselines, measurements, design options, decisions) goes in
`docs/results/<slug>.md` or an ADR in `docs/DECISIONS.md`, and the plan links to it. The PR
description links to the plan and the results doc instead of copying their tables.

## How

1. Run `/start-task <issue#>` in Claude Code. It switches to plan mode and drafts the plan
   with you.
2. Save it as `plans/NNNN-slug.md` (NNNN = issue number padded to 4 digits,
   e.g. `plans/0014-synonyms.md`).
3. Commit it on your branch with the first change. Update the Progress log as you go.
4. Link it in the PR.

## Template

Copy everything below the line.

---

```markdown
# NNNN - <short title>

Issue: #N    Role: <C1|C2|C3|S1|S2|U1|TL>    Spec: specs/<file>.md    Design: <results doc / ADR, or none>

## Goal
One or two sentences: what will be true when this is done, in plain language.

## Files to change
- path/to/file - what changes and why

## Steps
1. ...
2. ...
(Small steps, each one testable. Note anything you are unsure about.)

## Acceptance
- [ ] Linked questions: Q.. (what the retrieval/answer should now do)
- [ ] Spec acceptance items this covers: ...
- [ ] Check to run: <command or manual check> -> expected result
- [ ] verify-cee: <features to run>, or "not run: <why the app cannot show this change>"

## Paid calls
0, or: question IDs, why the mock cannot show it, runs of each (CLAUDE.md "Paid API calls").

## Progress log
- YYYY-MM-DD HH:MM - plan written
- YYYY-MM-DD HH:MM - <what happened, what surprised you, what changed in the plan>
```

## Experiment note

For `type:experiment` issues, on branch `exp/<issue#>-<slug>`. Write it as the top of
`docs/results/<slug>.md` before the first paid call, then fill in the results below it. The
code on the branch is never merged; only the results doc goes to `main` (a docs-only PR,
reviewed for: numbers trace to saved raw outputs, call count matches the note). If the result
wins, open a delivery issue that builds the change properly.

```markdown
# <slug> - <the question this experiment settles>

Issue: #N    Branch: exp/<issue#>-<slug>    Baseline: <results doc and config it compares with>

## Hypothesis and decision rule
<What we expect, and the rule fixed before any call, e.g. "adopt if >= 24/30 adjudicated and
reduce p50 < 80 s; otherwise reject".>

## Setup
<Config / code changed on the branch, in a few bullets.>

## Paid calls
Question IDs, why, runs of each, expected call count (CLAUDE.md "Paid API calls"). Raw outputs
saved in <evidence folder>.

## Results
<Filled in after the run: the numbers, the decision, and the follow-up issue if adopted.>
```
