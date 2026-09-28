# ExecPlans

An ExecPlan is a one-page plan written before you change anything. It keeps a task small,
reviewable, and tied to the question bank. The idea is borrowed from OpenAI's Codex
ExecPlans, simplified for this team.

## When to write one

- Every issue that changes code or behavior gets one.
- Tiny config-only or data-only tasks (e.g. add an alias, add rows to the manifest) may skip it.

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

Issue: #N    Role: <C1|C2|C3|S1|S2|U1|TL>    Spec: specs/<file>.md

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

## Progress log
- YYYY-MM-DD HH:MM - plan written
- YYYY-MM-DD HH:MM - <what happened, what surprised you, what changed in the plan>
```
