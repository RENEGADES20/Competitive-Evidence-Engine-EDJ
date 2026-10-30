# 0139 - /tl-review: planned real-model calls as final acceptance; reviewed sha; check rule

Issue: #139    Role: TL    Spec: CLAUDE.md "Paid API calls (money)", docs/DASHBOARD.md 3b

## Goal
A TL task whose approved ExecPlan plans up to 10 real-model calls (per CLAUDE.md "Paid API
calls") can run them as its last acceptance step and still pass `/tl-review` without the tech
lead; the reviewer never pays for a call itself. Every reviewer verdict names the commit it
reviewed, and the rule for "check not run" (blocking) vs "check the reviewer cannot run"
(escalate) is stated once, without overlap.

## Files to change
- .claude/commands/tl-review.md
  - New short section "Paid API calls" (after "Blocking vs non-blocking"): allowed when the
    approved ExecPlan planned them (question IDs, why the mock cannot show it, count <= 10);
    run once, after every mock check passed; raw outputs saved in the run's evidence folder;
    count reported in the PR's Verification. The reviewer itself never makes a paid call: it
    re-uses the saved outputs. Worked example: a plan with 3 planned real calls for Q1, Q12, Q26
    passes plan check 5 without escalation; 11 planned calls, or calls not in the plan, escalate.
  - Plan-mode check 5: "Paid calls: 0, or planned per CLAUDE.md (question IDs, why the mock
    cannot show it, count <= 10, run last after mock checks)".
  - PR-mode step 3: "Mock only. Never make a paid call during review" kept and extended: planned
    real calls -> check the saved raw outputs in the evidence folder and the count in the PR
    against the plan; do not re-run them.
  - Escalation list: "Any paid API call in the change or needed to verify it" replaced by
    "Paid API calls: more than 10, not in the approved plan, or ones the reviewer would need to
    make to verify the change".
  - Check rule, stated once, under a new heading `## Check rule` (after "Blocking vs
    non-blocking"): a check the reviewer can run and that fails, or that the author skipped,
    is blocking (the reviewer runs it itself in PR step 3); a check the reviewer cannot run is
    an escalation. The blocking bullet "A required check fails or was not run" and the
    escalation bullet "A check you could not run" are rewritten to say "see Check rule" and no
    longer restate it.
  - Both verdict formats (plan and PR) gain a first line "Reviewed <sha>" (the branch head the
    reviewer read); "Later rounds" uses that sha for `git diff <sha>..HEAD`.
- .claude/commands/tl-run.md
  - Stage 3 (Build): planned real calls run last, once, after every mock check passes, with
    raw outputs saved in the evidence folder.
  - "Stop and ask" paid-call wording and Rules line "Paid API calls" aligned with the new
    escalation rule (planned <= 10 no longer needs the tech lead).
- docs/RUN.md - delete the stray line `efsmain   # True` (line 84, left by PR #140; a
  non-blocking note on that review). Approved by the tech lead as an extra item for this issue;
  one-line deletion, nothing else in the file. The PR body states that the deletion came from
  the #140 reviewer's non-blocking note and was approved by the tech lead in chat.
- docs/DASHBOARD.md section 3b (the issue's spec) - the escalation sentence (lines 76-78) says
  the tech lead is asked for "a paid API call" and "a check that could not run". After this
  change both are wrong, so in that sentence only: "a paid API call" -> "paid API calls that
  are unplanned, more than 10, or ones the reviewer would need to make"; "a check that could
  not run" -> "a check the reviewer cannot run". Nothing else in the file.
- plans/0139-tl-review-paid-calls.md - this plan.

Not touched: CLAUDE.md (its "Paid API calls" section already allows planned calls and asks the
user for > 10); teammate rules; the eval runner.

## Steps
1. tl-review.md: add the "Paid API calls" section with the Q1/Q12/Q26 worked example and the
   11-call / unplanned-call counter-examples; state "The reviewer never makes a paid API call".
2. tl-review.md: update plan check 5, PR step 3, and the escalation bullet (step 1 rule).
3. tl-review.md: one check rule (can run + fails/skipped -> blocking; cannot run -> escalate);
   rewrite the two overlapping bullets to reference it.
4. tl-review.md: "Reviewed <sha>" in both verdict formats; "Later rounds" diff from that sha.
5. tl-run.md: stage 3 order for planned real calls; align "Stop and ask" and Rules wording.
6. docs/RUN.md: delete line 84 `efsmain   # True`.
7. docs/DASHBOARD.md 3b: rewrite the paid-call and check items of the escalation sentence
   (Files to change) so 3b matches tl-review.md and tl-run.md.
8. pytest; `/finish-task`. 0 paid calls in this task.

Risks: (a) the reviewer reads "planned" loosely -> mitigated by requiring the plan to name
question IDs, the reason, and the count, and by the 11-call counter-example; (b) the new rule
contradicts CLAUDE.md -> it only restates CLAUDE.md steps 2-5 for review, and CLAUDE.md stays
unchanged (checked below).

## Acceptance
- [x] Issue: 3 planned real calls for Q1, Q12, Q26 pass the plan checklist without escalation ->
  `grep -n "Q1, Q12" .claude/commands/tl-review.md` shows the worked example, stating it passes
  plan check 5 and is not escalated.
- [x] Issue: 11 planned calls, or calls not in the plan, escalate -> the same section and the
  "Never merge; escalate" list both name "more than 10" and "not in the approved plan";
  `grep -n -i "more than 10\|not in the approved plan" .claude/commands/tl-review.md`.
- [x] Issue: reviewer never calls a paid API (stated) -> `grep -n -i "never make" .claude/commands/tl-review.md`
  shows it in the Paid API calls section and in PR step 3; the escalation list includes calls
  the reviewer would need to make.
- [x] Issue: "Reviewed <sha>" in both verdict formats -> `grep -n "Reviewed <sha>" .claude/commands/tl-review.md`
  returns at least 2 lines (plan-mode verdict and PR-mode verdict).
- [x] Issue: check-not-run vs cannot-run rule stated once, no overlap -> `grep -n "^## Check rule" .claude/commands/tl-review.md`
  returns exactly 1 line and the rule text sits under that heading;
  `grep -n -i "could not run\|cannot run\|not run" .claude/commands/tl-review.md` shows the
  blocking and escalation bullets only pointing to "Check rule", not restating it.
- [x] Issue (Deliverable): tl-run.md build stage says planned real calls run last, after mock
  checks pass -> `grep -n -i "real calls" .claude/commands/tl-run.md` shows it in stage 3.
- [x] Issue: CLAUDE.md unchanged -> `git diff main --stat -- CLAUDE.md` prints nothing.
- [x] Extra (TL-approved): stray line gone -> `grep -c "efsmain" docs/RUN.md` prints 0, and
  `git diff main -- docs/RUN.md` shows exactly one deleted line.
- [x] DASHBOARD 3b matches the new rules -> `grep -n -i "a paid API call," docs/DASHBOARD.md`
  prints nothing; `grep -n -i "more than 10\|reviewer cannot run" docs/DASHBOARD.md` shows the
  rewritten escalation sentence in 3b; `git diff main -- docs/DASHBOARD.md` touches only that sentence.
- [x] Scope -> `git diff --stat main` lists only tl-review.md, tl-run.md, docs/RUN.md,
  docs/DASHBOARD.md and this plan.
- [x] `.venv\Scripts\python.exe -m pytest -q` (Mac: `.venv/bin/python -m pytest -q`) -> all pass,
  same count as main (227 passed, 1 skipped on main and on this branch). verify-cee and eval
  skipped: commands/docs only. 0 paid calls.

## Progress log
- 2026-10-30 10:11 - plan written; branch tl/139-tl-review-paid-calls from main (8639f20); extra item from the tech lead: delete stray `efsmain   # True` in docs/RUN.md; waiting for the reviewer agent's plan review
- 2026-10-30 10:14 - reviewer returned the plan (issue comment 6526171054). Blocking fix 1 applied: docs/DASHBOARD.md 3b escalation sentence added to Files to change, step 7, a grep check, and the Scope line. Non-blocking notes applied: the check rule gets its own heading `## Check rule` (acceptance check greps it); the PR body will state that the RUN.md deletion came from the #140 reviewer's note, approved by the tech lead in chat. Waiting for re-review
- 2026-10-30 10:16 - plan approved by the reviewer agent (round 2, reviewed 8539312; note: the Check rule grep also matches the rule text under the heading - the bullets only point to "Check rule", explained in the PR). Implemented: tl-review.md (Check rule, Paid API calls with Q1/Q12/Q26 worked example, plan check 5, PR step 3, Reviewed <sha> in both verdicts, Later rounds, escalation list), tl-run.md (stage 3 order, Stop and ask, Rules), DASHBOARD 3b sentence, RUN.md stray line. All acceptance greps as expected; pytest 227 passed, 1 skipped (same as main); next: PR
