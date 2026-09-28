---
description: Check proof of work, push the branch and open a pull request
---

Finish the current task. Explain each step to the user in plain language. Do not skip a
failed check; report it and ask the user how to proceed.

1. **Confirm the branch.** `git rev-parse --abbrev-ref HEAD` must not be `main`. Extract the
   issue number from the branch name (`<role>/<issue#>-<slug>`).
2. **Proof of work self-check.** Go through each item and report pass/fail:
   - [ ] Every acceptance item in the spec that this issue covers is met (quote them).
   - [ ] The ExecPlan in `plans/` has an updated Progress log and ticked Acceptance items.
   - [ ] Linked eval questions: run them (or the retrieval check) and record the result:
         which chunks came back, and whether the answer behavior matches `expected_behavior`.
   - [ ] UI changes: a screenshot; pipeline changes: a log excerpt or row counts.
   - [ ] No ground rule in `CLAUDE.md` is broken (citations, no invented figures, nothing normative).
   - [ ] Nothing secret or bulky is staged: no `.env`, no `data/raw/`, `data/interim/`,
         `data/processed/`, no `*.dump`. Check with `git status` and `git diff --cached --stat`.
   - [ ] New documents have rows in `data/manifest.csv` with `published_at` filled.
   - [ ] One line added to `docs/PROGRESS.md` (date | what landed | blockers | next).
3. **Commit** remaining changes with a clear message referencing the issue (`#N`).
4. **Push:** `git push -u origin <current-branch>`.
5. **Open the PR:** fill every section of `.github/pull_request_template.md` (including
   `Closes #N`) into a temporary file outside the repo, then:
   `gh pr create --title "<short title> (#N)" --body-file <filled template>`.
6. **Board:** tell the user "Move issue #N to **Done**. The tech lead will review; when the PR
   they set it to Approved."
