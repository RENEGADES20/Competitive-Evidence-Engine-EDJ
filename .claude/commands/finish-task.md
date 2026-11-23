---
description: Check proof of work, push the branch and open a pull request
---

Finish the current task. Explain each step to the user in plain language. Do not skip a
failed check; report it and ask the user how to proceed.

1. **Confirm the branch.** `git rev-parse --abbrev-ref HEAD` must not be `main`. Extract the
   issue number from the branch name (`<role>/<issue#>-<slug>`).
2. **Verify in the running app.** If a user could see the change in the app (UI, answer
   content or behavior, retrieval results, the database or the corpus), run the `verify-cee`
   skill (`scripts/verify_cee.py run`) on the final head. If the app cannot show it (request
   assembly, cache keys, logging, scripts, eval tooling) or it is docs or plans only, skip it
   and write one line in the PR saying why; pytest and the mock eval are the proof then
   (CLAUDE.md "Verification"). On FAIL, open the screenshots, fix, and run it again; if
   the same feature also fails on `main`, it is an existing problem: say so in the PR, do
   not hide it. Keep the evidence folder name and the head it ran on for the PR; the reviewer
   relies on it instead of re-running. A green test run alone is not proof.
3. **Proof of work self-check.** Go through each item and report pass/fail:
   - [ ] Every acceptance item in the spec that this issue covers is met (quote them).
   - [ ] The ExecPlan in `plans/` has an updated Progress log and ticked Acceptance items.
   - [ ] Linked eval questions: run them (or the retrieval check) and record the result:
         which chunks came back, and whether the answer behavior matches `expected_behavior`.
   - [ ] Verification evidence from step 2 (feature results + one screenshot, with the head
         it ran on), or the one-line reason it was not run plus the pytest and eval results.
   - [ ] No ground rule in `CLAUDE.md` is broken (citations, no invented figures, nothing normative).
   - [ ] Nothing secret or bulky is staged: no `.env`, no `data/raw/`, `data/interim/`,
         `data/processed/`, no `*.dump`. Check with `git status` and `git diff --cached --stat`.
   - [ ] New documents have rows in `data/manifest.csv` with `published_at` filled.
   - [ ] One progress line ready for the PR description (`What landed | Blockers | Next`).
         Do not edit `docs/PROGRESS.md`; a bot logs the line when the PR is merged. If the
         branch already changed it, restore it: `git checkout origin/main -- docs/PROGRESS.md`.
4. **Commit** remaining changes with a clear message referencing the issue (`#N`).
5. **Push:** `git push -u origin <current-branch>`.
6. **Open the PR:** fill every section of `.github/pull_request_template.md` (including
   `Closes #N` when every acceptance item of the issue is done, or `Part of #N` plus the
   items still open) into a temporary file outside the repo. Link the plan and any results doc
   rather than copying their tables. Then:
   `gh pr create --title "<short title> (#N)" --body-file <filled template>`.
7. **Board:** tell the user "Move issue #N to **Done**. The tech lead will review; after merging the PR
   they set it to Approved."
