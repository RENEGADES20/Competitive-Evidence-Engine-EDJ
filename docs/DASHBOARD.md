# Dashboard and weekly routines

How the tech lead sets up the GitHub Projects v2 board (one time, manual), and the weekly
checks. Rules for branches: [CLAUDE.md, Branch and PR rules](../CLAUDE.md#branch-and-pr-rules).

## 1. Create the project

GitHub -> your org/profile -> Projects -> New project -> Board. Name it
"Competitive Evidence Engine". Link it to this repo (Project settings -> Manage access / Repositories).

## 2. Fields

| Field | Type | Values |
|---|---|---|
| Status | Single select (built in) | Todo, In Progress, In Review, Done |
| Iteration | Iteration | 1-week iterations, 12 of them (W1-W12), starting 2026-09-28 |
| Role | Single select | C1, C2, C3, S1, S2, U1, TL |
| Firm | Single select | MS, SCHW, EDJ, MER, RJF, THEME, ALL |
| Eval Qs | Text | e.g. `Q4, Q27, Q30` |
| Size | Single select | S (< half day), M (1-2 days), L (split it) |

## 3. Views

| View | Layout | Setup |
|---|---|---|
| Current week | Board | Group by Status; filter `iteration:@current` |
| By person | Table | Group by Assignee; show Role, Status, Iteration, Eval Qs |
| Roadmap | Roadmap | Date field = Iteration; group by Role |
| Review queue | Table | Filter `status:"In Review"`; sort by updated |

## 4. Labels (repo -> Issues -> Labels)

- `role:c1` `role:c2` `role:c3` `role:s1` `role:s2` `role:u1` `role:tl`
- `firm:ms` `firm:schw` `firm:edj` `firm:mer` `firm:rjf` `firm:theme`
- `type:feature` `type:bug` `type:corpus` `type:eval` `type:docs`
- `blocked`

## 5. Built-in workflows (Project -> ... -> Workflows)

Turn on: **Auto-add to project** (filter `is:issue,pr is:open`), **Item closed -> Done**,
**Pull request merged -> Done**. Moving to In Progress / In Review is manual (the
`/start-task` and `/finish-task` commands remind people).

## 6. Weekly X/30 (from W6)

1. Each person scores their 5 questions against the current snapshot.
2. C1 totals the passes and adds a row to [PROGRESS.md](PROGRESS.md): date, snapshot, X/30, failing IDs.
3. C1 posts the same line as a comment on the pinned issue "Weekly score".

## 7. Main-branch safety (soft protection)

The repo is GitHub Free private, so branch protection is not available. Protection is:
the rule in CLAUDE.md, the hook `.claude/hooks/guard-main.py` (blocks commit/push on main in
Claude Code), and this weekly check by the tech lead:

```
git fetch origin
git log origin/main --no-merges --since="8 days ago" --format="%h %an %s"
```

Any line here is a direct commit to main (PR merges are merge commits and do not appear;
if the repo uses squash-merge, compare against the list of merged PRs instead). Talk to the
author, and revert or re-land through a PR if needed.

## 8. Weekly snapshot checklist (tech lead)

- [ ] `git switch main && git pull`
- [ ] All corpus PRs for the week merged; `data/manifest.csv` has no rows with missing `published_at`
- [ ] Raw files for every manifest row exist in the shared folder (sha256 matches)
- [ ] Run `build-snapshot` (rebuilds the database from main, see plans/0001)
- [ ] Upload `snapshots/corpus-YYYY-MM-DD.dump` to the shared folder
- [ ] Test `restore` on a clean machine or container
- [ ] Post the snapshot name in PROGRESS.md and the team chat
