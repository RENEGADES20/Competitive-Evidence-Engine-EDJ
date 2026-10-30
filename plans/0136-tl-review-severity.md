# 0136 - /tl-review: return only for blocking findings

Issue: #136    Role: TL    Spec: docs/DASHBOARD.md 3b

## Goal
`/tl-review` returns a plan or PR only for blocking findings. Non-blocking findings are listed
in the APPROVED comment (plus a follow-up issue if worth doing) and the PR still merges, so
reviews of low-risk PRs converge instead of ending in a third-return escalation (as on #132).

## Files to change
- .claude/commands/tl-review.md - new section "Blocking vs non-blocking" with examples (from
  #132 and #134); both verdict formats (plan and PR) list "Blocking" and "Non-blocking"
  findings; a return happens only if there is at least one blocking finding; a later round
  re-checks only the earlier blocking items plus anything new in the diff since the last round.
- .claude/commands/tl-run.md - the return limits ("at most 2 returns", "a third escalates",
  "Stop and ask": third return) count blocking returns only; an APPROVED verdict with
  non-blocking notes is not a return.
- docs/DASHBOARD.md section 3b (the issue's spec) - "Up to 2 returns" -> "Up to 2 blocking
  returns" in steps 2 and 4, and "a third return" -> "a third blocking return", so the
  dashboard does not contradict tl-run.md. Wording only; nothing else in the file.
- plans/0136-tl-review-severity.md - this plan.

Not touched: the "Never merge; escalate to the tech lead instead" list in tl-review.md and the
"Stop and ask the tech lead" items other than the return count (Out of scope: escalation
rules); teammate PR review; CLAUDE.md.

## Steps
1. tl-review.md: add "Blocking vs non-blocking" after "Read first".
   - Blocking (return): code or a stated fact is wrong in a way that changes what the PR does
     or whether a check/acceptance item holds; an issue acceptance item has no check or is not
     met; a CLAUDE.md rule or architecture invariant is broken; a required check fails or was
     not run; pytest / verify-cee / eval regress; a Windows/Mac twin (.ps1/.sh, RUN.md block)
     is missing; `Closes #N` while an acceptance item is open; `.env`/dump/raw data in the diff.
   - Non-blocking (note, still approve): Progress-log times off by minutes; wording, formatting,
     typos; provenance or clarity notes that do not change any check's outcome; suggestions
     outside the PR's scope (e.g. #134's CLAUDE.md note).
   - Rule of thumb: "Would merging this as-is leave something wrong or unchecked?" Yes ->
     blocking. Unsure -> blocking (keeps "be strict" for real risk).
   - Worked examples from #132 (rounds 1-3) and #134 (round 1), one line each.
2. tl-review.md: plan-mode criteria 1-6 are the blocking checks for plans; verdict text for
   both modes becomes "Blocking: <numbered fixes or none>" and "Non-blocking: <notes or none>";
   APPROVED may carry non-blocking notes; non-blocking notes worth doing -> follow-up issue
   (`gh issue create`, label role:tl) or "noted, no issue".
3. tl-review.md: "Later rounds" paragraph - re-check each earlier blocking item and review only
   what changed in the diff since the last reviewed commit (`git diff <last>..HEAD`); re-run the
   checks; do not raise new findings on unchanged lines unless blocking.
4. tl-run.md: stages 2 and 4 and "Stop and ask" say blocking returns; an APPROVED-with-notes
   verdict ends the stage.
5. DASHBOARD 3b wording (Files to change).
6. Re-read #132 round 3 under the new rules; write the classification in the PR body.
7. pytest; `/finish-task`.

Risk: "non-blocking" becomes a way to wave through real errors. Mitigation: the blocking list
names any wrong fact that changes an outcome, and "unsure -> blocking".

## Acceptance
- [ ] Issue: blocking examples listed -> check: `grep -n -i "blocking" .claude/commands/tl-review.md`
  shows the section, and it names all six: code or stated fact wrong; acceptance item has no
  check or not met; CLAUDE.md rule or invariant broken; check fails or not run;
  tests/verify-cee/eval regress; Windows/Mac twin missing.
- [ ] Issue: non-blocking examples listed -> same section names Progress-log times off by
  minutes, wording, formatting, suggestion outside the PR's scope.
- [ ] Issue (Deliverable): verdict format lists both -> plan-mode and PR-mode verdict lines in
  tl-review.md each show "Blocking:" and "Non-blocking:".
- [ ] Issue (Deliverable): later round re-checks only earlier blocking items plus new diff ->
  "Later rounds" paragraph present in tl-review.md.
- [ ] Issue (Deliverable): tl-run.md return limits count blocking returns only -> every
  "return" limit in tl-run.md (stages 2, 4, "Stop and ask") says blocking; `grep -n "return" .claude/commands/tl-run.md`.
- [ ] Issue: #132 round-3 re-read classifies both findings as non-blocking -> stated in the PR
  body: fix 1 (log start time 22:55 vs 23:17) = Progress-log time off by minutes; fix 2
  (verify-cee run noted as on the uncommitted tree, HEAD ab70a01) = provenance note, the check
  ran and passed on the same content, outcome unchanged.
- [ ] Issue: escalation list unchanged -> `git diff main -- .claude/commands/tl-review.md`
  shows no change inside "Never merge; escalate to the tech lead instead"; tl-run.md "Stop and
  ask" keeps all three items (only "third return" gains "blocking").
- [ ] Out of scope respected -> `git diff --stat main` lists only the four files above.
- [ ] `.venv\Scripts\python.exe -m pytest -q` -> all pass (222 on main). verify-cee and eval
  skipped: commands/docs only. 0 paid calls.

## Progress log
- 2026-10-30 00:29 - plan written; branch tl/136-tl-review-severity from main; waiting for the reviewer agent's plan review
