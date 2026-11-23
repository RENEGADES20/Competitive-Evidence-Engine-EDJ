Closes #
<!-- Use "Part of #N" instead if some acceptance items of the issue are still open; list them under Scope. -->

## What changed
<!-- Plain language, 2-5 bullets. -->

## Spec
<!-- e.g. specs/retrieval.md - which acceptance items this covers -->

## ExecPlan
<!-- plans/NNNN-slug.md, or "skipped: config/data-only", or "experiment: docs/results/<slug>.md".
Link the plan and any results doc; do not copy their tables here. -->

## Verification
<!-- What you actually ran and what happened. One bullet per check, e.g.
- verify-cee: ask-answer PASS, open-citation PASS, gap-path PASS (.verify-runs/20261010-2132-abc1234)
- pytest: 42 passed
State the number of paid API calls and why ("0 real calls" when none; rules in CLAUDE.md).
Say how strong each claim is: 1 said so, 2 pointed at the line, 3 reasoned it through,
4 ran a script, 5 reproduced in the running app. Attach 1-2 screenshots that prove it. -->

## Proof of work
- [ ] Spec acceptance items met (listed above)
- [ ] ExecPlan progress log updated
- [ ] Linked questions run; results below
- [ ] verify-cee run on the final head (evidence folder + head named), or not run with the reason (docs only, or the app cannot show this change)
- [ ] No `.env`, raw data or `*.dump` committed
- [ ] New documents in `data/manifest.csv` with `published_at`
- [ ] Progress line filled in below; `docs/PROGRESS.md` not edited
- [ ] Ground rules in CLAUDE.md respected

## Progress line
<!-- One line: What landed | Blockers | Next. A bot adds it to docs/PROGRESS.md on merge. -->


## Eval delta
<!-- Question IDs affected, before -> after (e.g. Q26: fail -> pass; retrieval hit 2/4 -> 4/4). Snapshot used. -->
