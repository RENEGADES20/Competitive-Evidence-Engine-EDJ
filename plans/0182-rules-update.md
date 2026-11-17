# 0182 - Rules: portability spec no longer binds main; real calls up to 5 per question

Issue: #182    Role: TL    Spec: CLAUDE.md; docs/DECISIONS.md

## Goal
Every rule document states the two tech-lead decisions of 2026-11-16 (issue comment on #182):
(1) the sponsor portability spec (EJ-10 and the rest of `ej-portability` v1.0) is no longer a
rule for `main` and survives only as history; the one rule kept is that work needing a model
besides the single answer LLM call is developed on a branch, not `main`; (2) real API calls:
at most 5 per question in a task, planned before the first call, without asking the tech lead;
more than 10 calls in one task and the 30-question scored Gate 3 run still need the tech lead.
Docs only; no code changes; 0 real calls.

## Files to change
Found with `git grep -n -i -E "EJ-[0-9]+|portability|sponsor spec|don't change ranking"` and
`git grep -n -i -E "real call|paid|10 calls|more than 10|10 or fewer|Gate 3"` over the repo
(outside `plans/`, `evals/`, `docs/PROGRESS.md`) at 44c8af0.

- `CLAUDE.md`
  - "Architecture invariants" (after line 32, "One LLM call per answer by default"): add the
    branch rule, stated once: work that needs a model besides the single answer LLM call
    (embeddings, rerankers, any local or hosted model in retrieval or validation) is developed
    on a branch (today `exp/hybrid`), not on `main`; see ADR-011.
  - "Paid API calls (money)" step 2, lines 95-98: replace "Use the fewest questions that prove the
    point (usually 1-5). More than 10 calls in one task: ask the user first." with: fewest
    questions that prove the point; at most 5 real calls per question in a task, planned before
    the first call; more than 10 calls in one task: ask the user (tech lead) first; the
    30-question scored run (Gate 3) needs an explicit tech-lead go-ahead.
  - No other line changes (steps 1, 3, 4 "No loops / do not re-roll", 5 stay).
- `docs/DECISIONS.md`
  - ADR-010 Status line 180: becomes "Accepted (tech lead decision 2026-11-05, #127); its EJ-10
    parts superseded by ADR-011: the EJ-10 reason in Context, the ranking limit, the 'Scope of
    EJ-10 here' bullet, the sponsor-agreement revisit trigger and the Consequences
    'meets EJ-10' line". ADR-010's body (lines 181-241, incl. the EJ-10 mentions at 182,
    224-227, 233-234, 237) stays as written: it is history, and the ADR template (line 10) says
    "do not edit history".
  - New `## ADR-011: Sponsor portability spec no longer binds main; model-based work on a branch`
    appended after ADR-010 (next free number; ADR-008 was reserved and never used, see ADR-010
    line 190, so it is not reused). Status: Accepted (tech lead decision 2026-11-16, #182).
    Context: ADR-010 gave EJ-10 as a reason `main` stays FTS-only and applied EJ-10 Tier 2 item 3
    / spec section 4 ("Don't change ranking") to any `fts` constant change. Decision: the
    portability spec is not a requirement of this project and is not a reason to refuse a
    change; the "Don't change ranking" limit is lifted (a ranking change is an ordinary S1
    issue with its own eval); ADR-010's outcome stands (`main` FTS-only, hybrid code stays on
    `exp/hybrid`), now because of the branch rule in CLAUDE.md "Architecture invariants";
    ADR-010's "Scope of EJ-10 here" bullet, its Consequences "that path meets EJ-10" and its
    sponsor-agreement revisit trigger (line 233) no longer apply;
    moving model-based work to `main` now needs a tech-lead decision recorded in a new ADR that
    lifts the CLAUDE.md branch rule, not sponsor agreement (ADR-010's other two revisit
    triggers stay as evidence such an ADR would cite); ADR-009 is unchanged.
    Consequences: what gets easier/harder.
    Status `Accepted` in the same PR, not `Proposed`: the ADR template (DECISIONS.md lines 7-10)
    starts ADRs as Proposed, but the decision is already taken by the tech lead (#182 comment)
    and the issue asks for one PR. The PR body says so, so the PR reviewer does not flag it.
- `specs/retrieval.md` line 71: "`main` stays FTS-only (ADR-010, sponsor spec EJ-10)" ->
  "`main` stays FTS-only (ADR-010; model-based retrieval stays on a branch, ADR-011)". Line 4
  "Decisions: ADR-001, ADR-004, ADR-010" gains ADR-011.
  **Owner: S1 (Corylus0602)** (CLAUDE.md spec table; the file's own `**Owner:** S1`). S1 is
  named as reviewer on the PR for this file (`gh pr edit --add-reviewer Corylus0602`). The tech
  lead may approve this hunk in S1's place, as was done for U1's files on #172.
- `.claude/commands/tl-review.md`
  - "Paid API calls" section, lines 66-73: allowed without the tech lead when planned with
    question IDs, why the mock cannot show it, at most 5 calls per question and 10 or fewer in
    the task; escalate when a question is planned or called more than 5 times, more than 10
    calls in the task, unplanned calls, calls the reviewer would need, or a 30-question scored
    run (Gate 3) without a tech-lead go-ahead on the issue.
  - Worked examples, lines 75-80: keep the 3-call example; add "Q12 planned 6 times (e.g. six
    prompt versions): escalate (more than 5 for one question)"; add "Q1 and Q12 planned 5 times
    each (10 calls): passes"; keep 11 calls -> escalate; keep unplanned -> escalate; add the
    Gate 3 run example.
  - Plan check 5, line 97: "count of 10 or fewer" -> "at most 5 per question and 10 or fewer in
    the task; no 30-question scored run without a tech-lead go-ahead".
  - "Never merge" line 132: add "more than 5 for one question" and the Gate 3 run.
- `.claude/commands/tl-run.md`
  - "Stop and ask" line 41: escalation list adds "more than 5 for one question" and the Gate 3
    run.
  - "Rules" lines 47-48: "(question IDs, why, 10 or fewer; CLAUDE.md)" -> "(question IDs, why,
    at most 5 per question, 10 or fewer in the task; CLAUDE.md)"; tech lead also for the
    30-question scored run.
- `docs/DASHBOARD.md` section 3b, lines 76-79: escalation list adds "more than 5 for one
  question" and "the 30-question scored run (Gate 3) without a tech-lead go-ahead".

Checked, no change needed:
- `PLANS.md`: states no call limit (only the Acceptance template).
- `.claude/commands/dispatch.md` line 74-75: "names the question IDs and a call cap, and points to
  'Paid API calls' in CLAUDE.md": still true; the cap comes from CLAUDE.md.
- `.github/pull_request_template.md` line 17: points to CLAUDE.md; still true.
- `docs/DECISIONS.md` ADR-009 (lines 155-177; "The sponsor asked" at 160): unchanged by order of
  the issue.
- `docs/ARCHITECTURE.md` line 178, `README.md` lines 100-104: describe `exp/hybrid` as a fact,
  no EJ-10 rule; unchanged.
- `plans/`, `evals/`, `docs/PROGRESS.md`: history; unchanged.
- Code built for the portability spec (vectors module, `CEE_VECTORS`): out of scope, stays.

## Steps
1. CLAUDE.md: add the branch rule to "Architecture invariants"; rewrite "Paid API calls" step 2.
   Check: `git diff CLAUDE.md` shows only those two hunks.
2. DECISIONS.md: ADR-010 Status line; append ADR-011. Check: ADR-010 body unchanged
   (`git diff` touches line 180 only inside ADR-010); ADR-009 untouched.
3. specs/retrieval.md lines 4 and 71.
4. tl-review.md (Paid API calls section, worked examples, plan check 5, Never merge),
   tl-run.md (Stop and ask, Rules), DASHBOARD.md 3b. Same wording for the limits everywhere:
   "at most 5 per question, 10 or fewer in the task, Gate 3 scored run needs the tech lead".
5. Run the acceptance greps and `pytest -q`; log results in the Progress log.
6. `/finish-task`: PR "Closes #182", Verification "0 real calls"; S1 (Corylus0602) added as
   reviewer for `specs/retrieval.md`; PR body says ADR-011 lands as `Accepted` in the same PR
   because the tech lead already decided (#182 comment) and the issue asks for one PR; the PR
   says it goes to the tech lead (ADR, CLAUDE.md invariant, teammate-owned file).

Risks / unsure:
- "Up to 5 per question" sits next to step 4 "do not re-roll a wrong answer". They do not
  conflict: the 5 are planned before the first call (e.g. different prompt versions or
  models); re-calling the same prompt because the answer was wrong stays forbidden. Step 4 is
  not changed; the CLAUDE.md step 2 wording says "planned before the first call" to make this
  clear.
- This PR adds an ADR, changes a CLAUDE.md invariant and changes a teammate-owned file
  (`specs/retrieval.md`, S1), so `/tl-review pr` must escalate it to the tech lead per "Never
  merge" (lines 131 and 134). That is expected and is the right outcome; the tech-lead decision
  on #182 is the input, the merge is still the tech lead's. The tech lead may approve the
  `specs/retrieval.md` hunk in S1's place (as on #172 for U1's files).
- The acceptance grep will still match ADR-010's body (history) and ADR-011 (history/the
  supersession); both are allowed by the issue. Any match outside DECISIONS.md, `plans/`,
  `evals/` or `docs/PROGRESS.md` is a failure.
- Acceptance greps match short phrases on one line. While editing, each grepped phrase ("on a
  branch", "per question", "more than 10", "Gate 3", "tech lead") is kept unbroken by line
  wrapping, so the checks give no false failures.
- `docs/PROGRESS.md` is history (bot-written). It is excluded from the item 1 grep (0 matches
  today), and the PR's `## Progress line` avoids the words "EJ-" / "portability spec" /
  "sponsor spec" so the bot copy adds no new match.
- `sync-db -Check` cannot run in this worktree (no `.venv`); irrelevant for a docs-only task.

## Acceptance
- [x] Linked questions: none (docs only).
- [x] Issue item 1 (spec only as history): `git grep -n -i -E "EJ-[0-9]+|portability spec|sponsor spec" -- . ':!plans/' ':!evals/' ':!docs/PROGRESS.md'`
      -> matches only in `docs/DECISIONS.md`, inside ADR-010's body (history), ADR-010's Status
      line (naming the superseded parts) and ADR-011 (which records that the spec no longer
      binds); no match in CLAUDE.md, `.claude/`, `specs/`, DASHBOARD.md, PLANS.md, README.md;
      no line presents it as a current rule or a reason to refuse a change (reviewer reads each
      match). `git grep -n -i "EJ-" -- docs/PROGRESS.md` -> 0 matches.
- [x] Issue item 1, ADR-010 leftovers: `git grep -n -i "sponsor agrees" -- docs/DECISIONS.md`
      -> only ADR-010's historical revisit-trigger line (line 233 at 44c8af0; it may shift if the Status line wraps). `git grep -n -i -E "scope of EJ-10|meets EJ-10|sponsor-agreement|ranking" -- docs/DECISIONS.md`
      -> the ADR-010 Status line and ADR-011 name each of: the Context reason, the ranking limit,
      the "Scope of EJ-10 here" bullet, the sponsor-agreement revisit trigger and the
      Consequences "meets EJ-10" line as superseded; ADR-011 says moving model-based work to
      `main` needs a tech-lead decision / new ADR lifting the branch rule, not sponsor agreement.
- [x] Issue item 2 (branch rule once): `git grep -n -i "on a branch" -- CLAUDE.md` ->
      exactly 1 line, in "Architecture invariants"; that bullet names embeddings, rerankers,
      local/hosted models (reviewer reads the bullet). `git grep -n "ADR-011" -- docs/DECISIONS.md`
      -> ADR-011 heading, ADR-010 Status line; ADR-011 text references the CLAUDE.md branch rule
      and keeps `exp/hybrid`.
- [x] Issue item 3 (CLAUDE.md step 2): `git grep -n -i -E "per question|more than 10|gate 3" -- CLAUDE.md`
      -> hits only in "Paid API calls" step 2, which says (reviewer reads the step): at most 5
      real calls per question in a task, planned before the first call; more than 10 calls in
      one task asks the user first; the 30-question scored run (Gate 3) needs the tech lead.
- [x] Issue item 4 (same in TL docs): `git grep -n -i -E "per question|more than 5" -- .claude/commands/tl-review.md .claude/commands/tl-run.md docs/DASHBOARD.md`
      -> hits in tl-review "Paid API calls", worked examples, plan check 5 and "Never merge";
      tl-run "Stop and ask" and "Rules"; DASHBOARD 3b. `git grep -n "10 or fewer" -- .claude/ docs/DASHBOARD.md`
      -> each hit's sentence also states the per-question limit (reviewer reads it).
      `git grep -n -i "gate 3" -- .claude/commands/ docs/DASHBOARD.md`
      -> tl-review, tl-run, DASHBOARD each say it needs the tech lead. `git grep -n "6 times" -- .claude/commands/tl-review.md`
      -> the worked example "one question planned 6 times -> escalate".
- [x] Issue item 5 (no other rule changes; ADR-009 unchanged): `git diff origin/main --stat`
      -> only CLAUDE.md, docs/DECISIONS.md, specs/retrieval.md, .claude/commands/tl-review.md,
      .claude/commands/tl-run.md, docs/DASHBOARD.md, plans/0182-rules-update.md;
      `git diff origin/main -- docs/DECISIONS.md` -> no hunk inside ADR-009 (lines 155-177)
      and inside ADR-010 only the Status line.
- [x] Issue item 6: `pytest -q` (repo venv, `PYTHONPATH=<worktree>/src`) -> all pass, same count
      as on `origin/main`.
- [x] 0 real calls (docs only).

## Progress log
- 2026-11-16 17:14 - plan written on `tl/182-rules-update` from origin/main 44c8af0. Greps for
  EJ/portability found rule text only in specs/retrieval.md:71 and ADR-010 (history); paid-call
  limits in CLAUDE.md, tl-review.md, tl-run.md, DASHBOARD.md 3b. `sync-db -Check` not runnable
  in the worktree (no `.venv`); not needed for docs only.
- 2026-11-16 17:18 - reviewer: PLAN CHANGES REQUESTED on e528566 (2 blocking, 4 non-blocking).
- 2026-11-16 17:19 - revised (commit 775cd27; this line first said 17:24, a guessed time, corrected here): blocking 1, `specs/retrieval.md` is S1-owned -> S1 named as PR
  reviewer, tech lead may approve in S1's place (as on #172), "teammate-owned file" added to the
  escalation reasons; blocking 2, ADR-010 Status names all its EJ-10 parts, ADR-011 replaces the
  sponsor-agreement trigger with a tech-lead decision / new ADR, new `sponsor agrees` grep check (new text says "sponsor-agreement" so only line 233 matches).
  Non-blocking 1: greps use short phrases kept on one line; 2: PR body explains ADR-011 lands as
  Accepted; 4: item 1 grep excludes `docs/PROGRESS.md`, plus a 0-match check on it. Note 3
  (eval_run.py has no per-question cap): no change, code out of scope.
- 2026-11-16 17:20 - reviewer: PLAN APPROVED on 775cd27 (non-blocking: record the actual line of
  the "sponsor agrees" history line).
- 2026-11-16 17:22 - implemented. CLAUDE.md: branch rule bullet after line 32 (now line 33),
  "Paid API calls" step 2 (lines 99-103). DECISIONS.md: ADR-010 Status line 180 kept on one line,
  so the body does not shift; ADR-011 appended (lines 243-270). specs/retrieval.md lines 4 and
  71; tl-review.md (Paid API calls 66-75, worked examples 77-83, plan check 5 line 101, Never
  merge line 136); tl-run.md lines 41 and 47-49; DASHBOARD.md 3b lines 77-78. In CLAUDE.md the
  bullet's second "on a branch" was reworded ("is built and tested there") so the phrase occurs
  once.
- 2026-11-16 17:22 - acceptance checks on the working tree, all as expected:
  item 1 grep -> only docs/DECISIONS.md (ADR-010 Status 180, ADR-010 body 182, 224-227, 237,
  ADR-011 243-254); docs/PROGRESS.md "EJ-" -> 0. `sponsor agrees` -> only line 233 (ADR-010's
  revisit trigger, history; same line number as at 44c8af0). Item 2: "on a branch" in CLAUDE.md
  -> 1 line (33). Item 3: CLAUDE.md 101-103. Item 4: per-question limit in tl-review 67, 72, 81,
  101, 136; tl-run 41, 47-48; DASHBOARD 77; every "10 or fewer" line (tl-review 67, 101; tl-run
  47) also states "at most 5 per question"; Gate 3 in tl-review 74, 83, 101, 136, tl-run 41,
  49, DASHBOARD 78; "6 times" example tl-review 81. Item 5: diff vs origin/main = the 7 planned
  files; DECISIONS.md hunks only @@ -180 and the append after 241 (ADR-009 untouched).
  Item 6: `pytest -q` -> 380 passed (no code or test file changed, so the same tests as
  origin/main). verify-cee not run: docs only. 0 real calls.
- 2026-11-16 - tech-lead change after review: no per-task total. The only call limit is at most
  5 real calls per question in a task (plus the Gate 3 go-ahead). Removed "more than 10 calls in
  one task" from CLAUDE.md step 2, tl-review.md (Paid API calls, worked examples, plan check 5,
  Never merge), tl-run.md (Stop and ask, Rules) and DASHBOARD.md 3b; the "11 planned calls"
  example became "4 questions x 5 calls (20 calls): passes". Earlier lines of this plan that
  mention 10 per task are history.
