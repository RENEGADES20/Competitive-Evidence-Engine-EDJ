# 0184 - Rules: up to 5 LLM calls per question (ADR-012); paid-call budget per question run

Issue: #184    Role: TL    Spec: CLAUDE.md; docs/DECISIONS.md

## Goal
The rule documents state the tech-lead decision of 2026-11-16 (issue #184): (1) one user
question may use 0 to 5 LLM calls, one by default, more only when the question splits into
parts (comparisons across firms first), recorded in a new ADR-012 that supersedes ADR-003's
single-call default; (2) the extra calls use the same answer model and provider, so the work is
on `main` and ADR-011's branch rule now says "besides the answer LLM calls"; (3) the paid-call
test budget counts by question run: one run of a planned question through the full answer flow
(up to 5 calls) needs no tech-lead approval, re-running the same question is planned before the
first call, there is no per-task total, the Gate 3 scored run still needs the tech lead.
Docs only; no code change; 0 real calls.

## Files to change
Found with `git grep -n -i -E "one llm call|single (answer )?llm call|5 real calls per question|more than 5 for one question|llm call|real call|per question|multi-call|ADR-003|gate 3"`
over CLAUDE.md, `.claude/`, `docs/DASHBOARD.md`, `docs/DECISIONS.md`, `PLANS.md`, `.github/`
at origin/main 0c69153. Line numbers below are at 0c69153.

- `CLAUDE.md`
  - "Architecture invariants" line 32. Replace
    `- **One LLM call per answer by default.** Multi-call designs need a new ADR.`
    with
    `- **Up to 5 LLM calls per user question; one by default.** More only when the question splits`
    `  into parts (e.g. a comparison across firms); every part keeps the SQL filters. See ADR-012.`
  - Branch-rule bullet line 34: `besides the single answer LLM call (embeddings, rerankers, any local or hosted model in`
    -> `besides the answer LLM calls (embeddings, rerankers, any local or hosted model in`
    (lines 33 and 35 unchanged).
  - "Paid API calls (money)" step 2, lines 99-102. Replace the whole step with:
    ```
    2. **Plan before the first call.** Write down which question IDs, why the mock cannot show it,
       and how many runs of each. Use the fewest questions that prove the point.
       One run of a planned question through the full answer flow (up to 5 real calls, ADR-012)
       needs no tech-lead approval. Running the same question again (e.g. a second prompt version)
       is planned in the ExecPlan before the first call. There is no per-task total.
       The 30-question scored run (Gate 3) needs an explicit go-ahead from the tech lead.
    ```
    The text "At most 5 real calls per question in a task" is gone. Steps 1, 3, 4 ("No loops",
    "do not re-roll"), 5 unchanged.
- `docs/DECISIONS.md`
  - ADR-003 Status line 53: `Status: Accepted` ->
    `Status: Accepted; its single-call default and its "multi-call design needs a new ADR" rule are superseded by ADR-012 (up to 5 LLM calls per user question, one by default). "Retrieval is deterministic" stands.`
    (one line, so the body does not shift). ADR-003's heading and body (lines 52, 54-57) are not
    edited: history.
  - New ADR-012 appended after line 270 (end of ADR-011), status `Accepted` in the same PR
    (as ADR-011 on #182: the tech lead already decided, the issue asks for one PR; the PR body
    says so). Exact text:
    ```
    ## ADR-012: Up to 5 LLM calls per user question
    Status: Accepted (tech lead decision 2026-11-16, #184); supersedes ADR-003's single-call default
    Context: ADR-003 set a single-call default per answer and asked for a new ADR before any
    multi-call design. Some questions split into parts: a comparison ("How do Edward Jones and Morgan Stanley
    price advice?") needs evidence per firm, and one retrieval and one call over all firms can let
    one firm crowd out the other. On 2026-11-16 the tech lead decided an answer may use more than
    one call when the question splits into parts.
    Decision:
    - One user question uses 0 to 5 LLM calls. One is the default; 0 when the system refuses
      before calling. More only when the question splits into parts; comparisons across firms are
      the first case (one part per firm, each retrieved separately, then a final call writes the
      answer from the parts). The rule that decides when to split belongs to the feature issue and
      is measured by eval, not assumed.
    - Unchanged invariants: entity, segment and time filters stay in SQL for every part;
      citations point only at `chunk_id`s retrieved for that question; caveats are built by code;
      every call is logged; the mock provider covers every call, so tests and CI make 0 real calls.
    - The extra calls use the configured answer model and provider (`LLM_PROVIDER`), so this is
      not model-based work: it is developed on `main`. ADR-011's branch rule does not apply; it
      now reads "besides the answer LLM calls" (CLAUDE.md "Architecture invariants").
    - Paid-call testing counts by question run: one run of a planned question through the full
      answer flow (up to 5 real calls) needs no tech-lead approval; re-running the same question
      is planned before the first call; no per-task total; the 30-question scored run (Gate 3)
      needs the tech lead (CLAUDE.md "Paid API calls").
    Consequences: Cost and latency per question can grow up to 5x for split questions. Answers
    must stay reproducible on the mock provider. More calls mean more to log and debug per
    answer. README, `docs/ARCHITECTURE.md`, `specs/answer-citations.md`, `specs/ui.md` and code
    docstrings still describe the one-call code until the feature issue changes them.
    ```
    ADR-011's body (line 258-259, "the single / answer LLM call") is history and not edited;
    ADR-012 records the new wording. ADR-010 untouched.
- `.claude/commands/tl-review.md`
  - "Paid API calls" lines 66-74. Replace lines 66-69 ("Allowed without the tech lead" bullet)
    with:
    ```
    - **Allowed without the tech lead** when the approved ExecPlan planned them: question IDs, why the
      mock cannot show it, and how many runs of each. One run of a question goes once through the full
      answer flow (up to 5 calls, ADR-012); a second run of the same question must be in the plan.
      No per-task total. They run last, after every mock check passed, with the planned questions
      run together in one run (CLAUDE.md step 3); every raw output (question,
      prompt version, model, output) is saved in the run's evidence folder; the PR's Verification
      states the count, the model and why.
    ```
    Lines 70-71 unchanged. Replace lines 72-74 ("Escalate") with:
    ```
    - **Escalate** when calls are not in the approved plan (including a re-run of a question the plan
      did not list), calls the reviewer would need to make to verify the change, or a 30-question
      scored run (Gate 3) without a tech-lead go-ahead on the issue.
    ```
  - Worked examples lines 77-84. Replace with:
    ```
    - A plan with Q1, Q12, Q26 each run once, one call each (IDs, why the mock cannot judge the
      wording): passes plan check 5, no escalation. In PR review: 3 saved raw outputs, "3 real calls"
      in the PR -> fine; the reviewer makes 0 calls.
    - A plan with 4 planned questions, each run once, where the comparison question makes 4 calls
      (7 calls in all): passes, no escalation.
    - A plan that runs Q12 twice, once per prompt version, both listed in the plan: passes.
    - A PR where a question was re-run with a second prompt version that the plan did not list:
      escalate (unplanned).
    - A plan for the 30-question scored run (Gate 3) with no tech-lead go-ahead on the issue: escalate, even at 1 call per question.
    - A PR that made calls not in the approved plan (e.g. 3 planned, 5 made, or none planned): escalate.
    ```
  - Plan check 3, line 99: `(hard filters in SQL, one LLM call, citations only to retrieved chunks, caveats by code, question bank append-only)`
    -> `(hard filters in SQL for every part, at most 5 LLM calls per user question (ADR-012), citations only to retrieved chunks, caveats by code, question bank append-only)`.
  - Plan check 5, line 101 -> `5. Paid calls: 0, or planned per CLAUDE.md (question IDs, why the mock cannot show it, how many runs of each question, a re-run of a question listed before the first call, run last after the mock checks; no 30-question scored run (Gate 3) without a tech-lead go-ahead); see "Paid API calls".`
  - "Never merge" line 136 -> `- Paid API calls: not in the approved plan (including an unplanned re-run of a question), ones the reviewer would need to make, or a 30-question scored run (Gate 3) without a tech-lead go-ahead (see "Paid API calls").`
- `.claude/commands/tl-run.md`
  - Stage 3, line 27: `they run last, once, after every mock` -> `they run last, together, after every mock`
    (planned re-runs of a question are allowed, so "once" no longer fits; line 28 unchanged).
  - "Stop and ask" line 41: `paid calls that are unplanned, more than 5 for one question, needed by the reviewer or a Gate 3 scored run without a tech-lead go-ahead`
    -> `paid calls that are unplanned (including an unplanned re-run of a question), needed by the reviewer or a Gate 3 scored run without a tech-lead go-ahead`.
  - "Rules" lines 47-49 -> 
    ```
    - Paid API calls: 0 unless the approved plan planned them (question IDs, why, runs of each question;
      one run = the full answer flow, up to 5 calls; no per-task total; CLAUDE.md). Unplanned calls or
      re-runs need the tech lead, and so does the 30-question scored run (Gate 3). The reviewer never makes a paid call.
    ```
- `docs/DASHBOARD.md` section 3b lines 77-78: `change, paid API calls that are unplanned, more than 5 for one question, or ones the reviewer would need to make,`
  -> `change, paid API calls that are unplanned (including an unplanned re-run of a question) or ones the reviewer would need to make,`
  (line 78 Gate 3 unchanged).

Checked, no change needed:
- `PLANS.md`: states no call limit.
- `.claude/commands/dispatch.md` line 74: "names the question IDs and a call cap, and points to
  'Paid API calls' in CLAUDE.md": not in the issue's Inputs; still true (the cap is the planned
  runs, each up to 5 calls, from CLAUDE.md). Left as is.
- `.github/pull_request_template.md` line 17: points to CLAUDE.md; still true.
- `.claude/skills/verify-cee/features/*` "LLM called:" lines: describe today's UI; code-facing,
  out of scope.
- `docs/DECISIONS.md` line 187 (ADR-010 "ADR-003 is unaffected ... not an LLM call"): history.
- README, `docs/ARCHITECTURE.md`, `specs/answer-citations.md`, `specs/ui.md`, code docstrings:
  out of scope by the issue (change with the feature issue).
- `plans/`, `evals/`, `docs/PROGRESS.md`: history.

## Steps
1. CLAUDE.md: invariant line 32, branch-rule line 34, "Paid API calls" step 2. Check:
   `git diff CLAUDE.md` shows only those three hunks.
2. DECISIONS.md: ADR-003 Status line 53; append ADR-012. Check: `git diff` touches ADR-003 only
   on its Status line and otherwise only appends after line 270.
3. tl-review.md (Paid API calls, worked examples, plan checks 3 and 5, Never merge), tl-run.md
   (stage 3 line 27, Stop and ask, Rules), DASHBOARD.md 3b, with the wording above.
4. Run the acceptance greps and `pytest -q`; log results in the Progress log.
5. `/finish-task`: PR "Closes #184", Verification "0 real calls"; the PR body says ADR-012 lands
   as `Accepted` because the tech lead already decided (#184) and that the PR goes to the tech
   lead (new ADR, CLAUDE.md invariant change).

Risks / unsure:
- The PR adds an ADR and changes a CLAUDE.md invariant, so `/tl-review pr` must escalate it to
  the tech lead ("Never merge", tl-review.md line 135). Expected.
- No teammate-owned file is changed (all files are TL-owned per the CLAUDE.md spec table).
- Greps match one line at a time. New text keeps "Up to 5 LLM calls per user question",
  "answer LLM calls", "no per-task total"/"no tech-lead approval", "Gate 3" on one line each, and
  avoids the issue's grep phrases in every planned new text, ADR-012 and the ADR-003 Status line
  included (they say "single-call default"). Checked by running the issue's grep pattern over
  this plan: every hit is a quote of old text, a check command or this log, none is planned new
  text. Step 1-3 edits are re-checked with the item 5 grep after editing.
- Step 4 of "Paid API calls" ("do not re-roll") and a planned re-run do not conflict: a re-run
  with a different prompt version is planned before the first call; re-calling because the
  answer was wrong stays forbidden.
- "Up to 5 calls" per run is a property of the answer flow (ADR-012), not a review count;
  plan check 3 now names it, so a design that makes more than 5 calls per question is blocking.

## Acceptance
- [ ] Linked questions: none (docs only).
- [ ] Issue item 1 (ADR-012, ADR-003 Status): `git grep -n "^## ADR-012" -- docs/DECISIONS.md`
      -> 1 line, after ADR-011; reviewer reads ADR-012 and finds each issue point: up to 5 per
      question, 1 default, split only into parts with comparisons first, split rule decided by
      the feature issue and measured by eval; filters in SQL for every part, citations only to
      retrieved `chunk_id`s, caveats by code, every call logged, mock covers every call (0 real
      calls in tests/CI); same answer model so on `main`, ADR-011 branch rule does not apply;
      Consequences: up to 5x cost and latency, reproducible on mock.
      `git grep -n "ADR-012" -- docs/DECISIONS.md` -> ADR-003 Status line names the superseded
      part. `git diff origin/main -- docs/DECISIONS.md` -> hunks only at ADR-003's Status line
      (@@ -53) and the append after line 270; ADR-003 lines 52, 54-57 unchanged.
- [ ] Issue item 2 (CLAUDE.md invariant and branch rule): `git grep -n -i "up to 5 llm calls per user question" -- CLAUDE.md`
      -> 1 line in "Architecture invariants", and that bullet says "See ADR-012";
      `git grep -n "answer LLM calls" -- CLAUDE.md` -> the branch-rule bullet.
- [ ] Issue item 3 (CLAUDE.md step 2): `git grep -n "At most 5 real calls per question" -- CLAUDE.md` -> 0;
      `git grep -n -i -E "no tech-lead approval|per-task total|planned in the ExecPlan before|gate 3" -- CLAUDE.md`
      -> hits only in "Paid API calls" step 2 (reviewer reads the step: one run through the full
      answer flow up to 5 calls needs no approval; re-running the same question is planned
      before the first call; no per-task total; Gate 3 needs the tech lead).
- [ ] Issue item 4 (TL docs say the same): `git grep -n -i -E "re-run|per-task total|gate 3" -- .claude/commands/tl-review.md .claude/commands/tl-run.md docs/DASHBOARD.md`
      -> tl-review "Paid API calls", worked examples, plan check 5, "Never merge"; tl-run "Stop
      and ask" and "Rules"; DASHBOARD 3b. `git grep -n -E "comparison question makes 4 calls|second prompt version that the plan did not list|Gate 3\) with no tech-lead go-ahead" -- .claude/commands/tl-review.md`
      -> the three worked examples. `git grep -n -i "one llm call" -- .claude/commands/tl-review.md` -> 0
      (plan check 3 rewritten). `git grep -n -E "run last, once|run last, together" -- .claude/commands/tl-run.md`
      -> 1 hit, "run last, together" (stage 3); `git grep -n "in one run" -- .claude/commands/tl-review.md`
      -> the "Allowed without the tech lead" bullet.
- [ ] Issue item 5: `git grep -n -i -E "one llm call|single (answer )?llm call|5 real calls per question|more than 5 for one question" -- CLAUDE.md .claude/ docs/DASHBOARD.md docs/DECISIONS.md`
      -> exactly 2 hits, `docs/DECISIONS.md` lines 52 and 55 (ADR-003 heading and body, history);
      no hit in ADR-012, CLAUDE.md, `.claude/` or DASHBOARD.md.
- [ ] Issue item 6 (no code change): `git diff origin/main --stat` -> only CLAUDE.md,
      docs/DECISIONS.md, .claude/commands/tl-review.md, .claude/commands/tl-run.md,
      docs/DASHBOARD.md, plans/0184-multicall-rules.md; README, docs/ARCHITECTURE.md, specs/,
      src/ untouched.
- [ ] Issue item 7: `pytest -q` (repo venv, `PYTHONPATH=<worktree>/src`, `cee.__file__` in the
      worktree) -> all pass, same count as origin/main.
- [ ] 0 real calls (docs only).

## Progress log
- 2026-11-16 18:44 - plan written on `tl/184-multicall-rules` from origin/main 0c69153. Greps
  found the one-call rule in CLAUDE.md 32 and ADR-003 (52-57), "single answer LLM call" in
  CLAUDE.md 34 and ADR-011 258-259 (history, split over two lines so the issue grep does not
  match it), the per-question test limit in CLAUDE.md 101, tl-review 66-84, 99, 101, 136,
  tl-run 41, 47-49, DASHBOARD 77. Baseline `pytest -q` on 0c69153 in the worktree (`cee.__file__`
  in wt-184/src): 380 passed. `sync-db -Check` not needed for docs only.
- 2026-11-16 18:48 - reviewer: PLAN CHANGES REQUESTED on 396d4d8 (1 blocking, 2 non-blocking).
  Blocking 1: the planned ADR-012 Context said "ADR-003 allowed one LLM call per answer", which
  the issue's grep matches. Reworded to "ADR-003 set a single-call default per answer"; ran the
  issue's grep pattern over this plan: every remaining hit quotes old text or is a check command,
  none is planned new text; item 5 now expects exactly 2 hits (DECISIONS.md 52, 55); Risks note
  updated. Non-blocking taken: tl-run.md line 27 "run last, once" -> "run last, together"
  (added to Files to change, Step 3 and item 4); tl-review.md "Allowed" bullet names running the
  planned questions together in one run (CLAUDE.md step 3).
