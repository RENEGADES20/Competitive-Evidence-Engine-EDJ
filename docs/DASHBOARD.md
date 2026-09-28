# Dashboard and weekly routines

How the tech lead sets up the GitHub Projects v2 board (one time, manual), and the weekly
checks. Rules for branches: [CLAUDE.md, Branch and PR rules](../CLAUDE.md#branch-and-pr-rules).

## 1. The project

Board: https://github.com/users/RENEGADES20/projects/3 ("Competitive Evidence Engine", linked to this repo).
Shared corpus folder (Box, invite-only): https://wustl.box.com/s/m4xze7zodjcqno1rmxla0kmj4kfbke1v
(`raw/` for raw documents, `snapshot/` for weekly database dumps; see ADR-006).

## 2. Fields (already created)

| Field | Type | Values |
|---|---|---|
| Status | Single select | Todo, In Progress, Done (finished, PR open, waiting for review), Approved (TL reviewed and merged) |
| Week | Iteration | W2-W12, 1 week each, W2 starts 2026-09-28. W1 tasks were folded into W2 |
| Role | Single select | C1, C2, C3, S1, S2, U1, TL |
| Firm | Single select | MS, SCHW, EDJ, MER, RJF, THEME, ALL |
| Eval Qs | Text | e.g. `Q4, Q27, Q30` |
| Size | Single select | S (< half day), M (1-2 days), L (split it) |

Status meaning: **Done** = the owner says it is finished and the PR is open. Only the tech
lead moves a card to **Approved**, after reviewing and merging the PR.

## 3. Views (created by hand in the web UI; the API cannot create views)

| View | Layout | Setup | Who |
|---|---|---|---|
| TL - By area | Table | Group by Role; sort by Status descending; filter `-status:Approved`. Each area shows Done on top, then In Progress, then Todo | Tech lead |
| Approved | Table | Filter `status:Approved`; group by Role | Tech lead (archive) |
| My tasks | Board | Columns = Status (Todo, In Progress, Done, Approved); filter `assignee:@me` | Every teammate |
| This week | Board | Columns = Status; filter `week:@current`; group by Role | Everyone |

GitHub keeps one option order per field for all views, so Approved cannot sit at the bottom
of the TL view; it is filtered out of that view instead and lives in "Approved".

Tech lead review loop: open "TL - By area" -> review the Done cards at the top of each
area -> merge the PR -> set Status to Approved (or let the merge workflow do it) -> the card
leaves the view.

## 4. Labels (repo -> Issues -> Labels)

- `role:c1` `role:c2` `role:c3` `role:s1` `role:s2` `role:u1` `role:tl`
- `firm:ms` `firm:schw` `firm:edj` `firm:mer` `firm:rjf` `firm:theme`
- `type:feature` `type:bug` `type:corpus` `type:eval` `type:docs`
- `blocked`

## 5. Built-in workflows (Project -> ... -> Workflows)

Turn on: **Auto-add to project** (filter `is:issue is:open`), **Item closed -> Approved**,
**Pull request merged -> Approved**. Moving to In Progress / Done is manual (the
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
