# 0162 - README status: current corpus, retrieval check vs. gate score, hybrid on exp/hybrid

Issue: #162    Role: TL    Spec: README.md, docs/BRIEF.md (Gates)

## Goal
`README.md` "Status" describes the project as of 2026-11-05 with numbers anyone can re-check,
and names the automated retrieval check and the human-scored Gate 4 score as two different things.

## Files to change
- `README.md` - "Status" section rewritten (short, plain language); any other line that presents
  68 documents / 14,682 passages / "Week 5" as current is updated. Nothing else in the README moves.
- `plans/0162-readme-status.md` - this plan and its Progress log (evidence for every number).

Not touched: `docs/PROGRESS.md` (bot-written log and C1's score table), `docs/BRIEF.md`, code,
config, corpus files, ADR-010 / PR #161, branch `exp/hybrid`, open PRs #152 / #146 / #161.

## Steps
1. **Worktree check.** In `D:\ALLPROJECTS\EDJ\wt-162`, `export PYTHONPATH="$(cygpath -w $PWD/src)"`;
   log `python -c "import cee;print(cee.__file__)"` (must point at `wt-162\src`).
2. **Manifest numbers (main).** A short Python one-off (not committed) over `data/manifest.csv`:
   total documents; counts by `doc_type`; research reports (tier 5 / research doc types) and their
   distinct `publisher` values. Log the command and output.
3. **Snapshot numbers (DB, read-only).** Against container `cee-db` (restored snapshot
   `corpus-2026-10-29`): `SELECT count(*) FROM documents; SELECT count(*) FROM chunks;`
   (read-only `psql`). Expected 111 / 17,183 per the issue; log the actual output. Note the
   difference, if any, between `main`'s manifest count and the snapshot count (documents merged
   after 10-29 are not in the snapshot yet).
4. **Open corpus PRs.** `gh pr view 152` / `gh pr view 146` (read only): title, state and how many
   documents each adds, from the PR diff of `data/manifest.csv`. Log it. Not merged, not edited.
5. **Retrieval check re-run.** `LLM_PROVIDER=mock python scripts/eval_run.py --as-of 2026-10-29
   --out <scratch folder>` on this branch (mock, 0 real calls). Expected PASS 27 / FAIL 3
   (Q15, Q19, Q29), tier-1 doc recall 0.796, refusal gap 4/5. Log the summary lines. If the
   numbers differ, the README uses the re-run numbers and the log says why.
6. **Hybrid link.** Confirm `evals/hybrid-eval/corpus-2026-10-29/report.md` exists on
   `origin/exp/hybrid` (`git ls-tree`) and build the GitHub link
   `https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/exp/hybrid/evals/hybrid-eval/corpus-2026-10-29/report.md`.
   Read the report's headline only to describe it in one clause; no numbers from it unless logged.
7. **Rewrite "Status"** (about 10-15 lines, 3-4 short paragraphs or bullets):
   - *Corpus:* N documents in `main`'s manifest; latest snapshot `corpus-2026-10-29`
     (111 documents / 17,183 passages); research reports and publishers on `main`; in review:
     #152 (research) and #146 (decks); corpus freeze 2026-11-11.
   - *Retrieval check:* what it measures (does search return the expected passages and refuse on
     gap questions, scored by `scripts/eval_run.py` with the mock model); latest result with date,
     snapshot and `--as-of`; failures Q15, Q19, Q29; it is **not** the gate score.
   - *Gate score:* Gate 4 (>= 21/30, `docs/BRIEF.md`) is the human-scored "would the project lead
     forward this answer" score, recorded in `docs/PROGRESS.md` after the freeze; not yet scored.
     (Fixes the "21 FAIL" vs. ">= 21/30" mix-up by naming each number.)
   - *Retrieval:* Postgres full-text search is the default on `main`; a hybrid mode (keyword +
     embeddings) is kept as an optional component on branch `exp/hybrid`, evaluated in #126
     (link to the report), not merged.
   - Pointer: weekly log in `docs/PROGRESS.md`.
8. **Sweep the rest of README.md** for `68`, `14,682`, `Week 5` and other stale "current" claims
   (`grep -n`); fix only lines that state them as current.
9. **Checks** (see Acceptance), then `/finish-task`. Docs only: verify-cee skipped, 0 real calls.

Unsure: whether `main`'s manifest has more rows than the 10-29 snapshot (e.g. #147 merged after
it). The README will state both numbers with their source rather than pick one.

## Acceptance
- [ ] Linked questions: Q15, Q19, Q29 are named as the current retrieval-check failures, matching
      the step 5 re-run (checked against `evals/questions.yaml` IDs).
- [ ] `grep -n -E "68 documents|14,682|Week 5" README.md` -> no line presents them as current.
- [ ] Every number in the new Status appears in a command output in the Progress log below
      (manifest count, DB counts, eval run summary).
- [ ] The retrieval check and the Gate 4 score are named as two different things in the Status text.
- [ ] Links resolve: `docs/PROGRESS.md` (relative), the `exp/hybrid` report (`git ls-tree
      origin/exp/hybrid` shows the file; GitHub URL uses that path).
- [ ] No sponsor company, platform or network named: grep the diff for the sponsor's names
      -> no hits (public repo).
- [ ] `git diff --stat origin/main` lists only `README.md` and this plan.
- [ ] 0 real calls (eval run with mock, no `--real`).

## Progress log
- 2026-11-05 21:06 - plan written on `tl/162-readme-status` (worktree `wt-162`, from origin/main 9dc4c9b).
