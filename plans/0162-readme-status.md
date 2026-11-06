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
- [x] Linked questions: Q15, Q19, Q29 are named as the current retrieval-check failures, matching
      the step 5 re-run (checked against `evals/questions.yaml` IDs).
- [x] `grep -n -E "68 documents|14,682|Week 5" README.md` -> no line presents them as current.
- [x] Every number in the new Status appears in a command output in the Progress log below
      (manifest count, DB counts, eval run summary).
- [x] The retrieval check and the Gate 4 score are named as two different things in the Status text.
- [x] Links resolve: `docs/PROGRESS.md` (relative), the `exp/hybrid` report (`git ls-tree
      origin/exp/hybrid` shows the file; GitHub URL uses that path).
- [x] No sponsor company, platform or network named: grep the diff for the sponsor's names
      -> 0 hits in prose (public repo).
- [x] `git diff --stat origin/main` lists only `README.md` and this plan.
- [x] 0 real calls (eval run with mock, no `--real`).

## Progress log
- 2026-11-05 21:06 - plan written on `tl/162-readme-status` (worktree `wt-162`, from origin/main 9dc4c9b).
- 2026-11-05 21:07 - plan approved by the reviewer agent (issue comment 6675788107) with notes: state Gate 4 in full, name the freeze source, log the snapshot comment, never write the sponsor-name pattern, do not word the hybrid result as decided while ADR-010 (#161) is open.
- 2026-11-05 21:08 - step 1: `PYTHONPATH=<wt-162>\src`; `python -c "import cee;print(cee.__file__)"` -> `D:\ALLPROJECTS\EDJ\wt-162\src\cee\__init__.py`.
- 2026-11-05 21:08 - step 2: one-off `csv.DictReader` over `data/manifest.csv` (main 9dc4c9b) -> 121 rows; doc_type: transcript 32, research 22, 10-Q 20, press 16, supplement 12, deck 8, monthly 6, 10-K 5; source_tier: 3 -> 58, 2 -> 41, 5 -> 22; tier 5 = 22 research reports, 16 distinct publishers.
- 2026-11-05 21:08 - step 3: `docker exec cee-db psql -At` with `SET default_transaction_read_only=on`: `SELECT count(*) FROM documents` -> 111; `SELECT count(*) FROM chunks` -> 17183; `SELECT obj_description('public.documents'::regclass)` -> `corpus-2026-10-29`. The 10 manifest rows not in the snapshot were merged after 10-29 (e.g. #147).
- 2026-11-05 21:09 - step 4: `gh pr diff` on `data/manifest.csv`: #152 (OPEN, "Second FINRA report, theme gaps, date fixes (#81)") +6/-3 lines = 3 new research rows (FINRA-OVERSIGHT-2026, CERULLI-MASS-AFFLUENT-2026, WEALTHTENDER-ADVISOR-SEARCH-2025) + 3 edited rows; #146 (OPEN, "Investor-day decks and Merrill newsroom release (#48)") +5 = 4 decks (MS, SCHW, BAC, RJF) + 1 MER press release. Neither touched.
- 2026-11-05 21:09 - freeze date 2026-11-11 from issue #120 "[W8][TL] Corpus freeze 11/11, snapshot, Gate 3 (>= 18/30) and an internal cold test" (OPEN).
- 2026-11-05 21:09 - step 5: `LLM_PROVIDER=mock python scripts/eval_run.py --as-of 2026-10-29 --out <scratchpad>\eval162` on this branch -> `{'PASS': 27, 'FAIL': 3, 'NOT_EVALUATED': 0} | tier-1 recall 0.796 | refusal gap 4/5 | real calls 0`; FAIL = Q15 (coverage 0.2), Q19 (coverage 0.25), Q29 (refusal FAIL, 1 must-not chunk). report.md: "Tier-1 recall: documents 0.796". Matches the issue's numbers.
- 2026-11-05 21:09 - step 6: `git ls-tree origin/exp/hybrid evals/hybrid-eval/corpus-2026-10-29/` and `gh api .../contents/...report.md?ref=exp/hybrid` -> file exists. Numbers taken from ONE table of the report, "At each mode's default before #126" (`exp/hybrid` code, fts `d784e30`): fts 28 / 2, search median 0.342 s; hybrid-norerank 28 / 2, median 0.363 s; hybrid with the cross-encoder 27 / 3, median 8.186 s. So "ties" holds for hybrid without the reranker. The 28/30 is `exp/hybrid`'s code; `main`'s retrieval check today is 27/30; README names the source of each. The report says the default-mode decision is #127; README uses the tech lead's wording (kept as optional, re-evaluated later), no decision language, since ADR-010 (#161) is open. (Corrected 21:25 after PR #163 review; the first version mixed the tuned-constants table.)
- 2026-11-05 21:10 - step 7-8: Status rewritten (corpus / retrieval check / gate score / retrieval / log pointer); Gate 4 stated in full from docs/BRIEF.md line 92 and the acceptance bar (line 68-70); `grep -n -E "68|14,682|Week 5|X/30" README.md` -> no output. No other README line stated the old numbers.
- 2026-11-05 21:10 - step 9 checks: links: `docs/PROGRESS.md`, `docs/BRIEF.md` exist; report URL path confirmed above. Sponsor-name grep on the diff: 0 hits in prose (the only match is the repository's own name inside the #126 report URL, as in the existing URL in `src/cee/ingest/check_sources.py`). `git diff --stat origin/main` -> README.md, plans/0162-readme-status.md. Docs only: verify-cee skipped. 0 real calls.
- 2026-11-05 21:25 - PR #163 review (changes requested, 3 blocking) fixed: (1) hybrid line now names its source (#126 comparison, `exp/hybrid` code, each mode at its default before tuning) and uses only the defaults table (28/30 each; 0.363 s vs 0.342 s); step 6 line corrected. (2) "tier-1 document recall" reworded as document recall on the 9 tier-1 questions (the 18 due by Gate 3, `evals/questions.yaml` line 14) that have an answer key (eval report.md: "mean over the 9 of 18 tier-1 questions with an answer key"). (3) Gates: Gate 3 (week 8, at the 11/11 freeze, #120: >= 18/30 at acting quality, citations resolve) and Gate 4 (week 11: >= 21/30 and one unsupervised use by the project lead) both named, from docs/BRIEF.md lines 91-92. Re-checked: `grep -n -E "68|14,682|Week 5|X/30" README.md` -> no output; sponsor-name grep on the diff -> 0 hits in prose (repo name in the report URL only); diff still README.md + this plan.
