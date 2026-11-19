# 0215 - Every asked part answered or named as a gap: code check and prompt v4

Issue: #215    Role: TL    Spec: specs/answer-citations.md (S2; owner review waived, TL decision
2026-11-17, #187). Also touches specs/ui.md (U1, one line: the gap box shows code flags; same
waiver) and ADR-020 (one sentence; the reviewer escalates the PR to the TL for the merge).
Depends on #214 (PR #223) and #224 (PR #226), both on `main`.

## Goal
The answer call sees the planner's parts: the evidence is grouped under each part (prompt v4),
and every claim, adjacent item and gap names the part it answers. After the answer, code checks
that every planned part has a cited claim, a cited adjacent item or a gap; a part with none gets a
code-built gap with a flag. A comparison grid takes its dimensions from the question and its parts,
and a grid cell the model wrote without a citation is moved to `gaps` by code. FTS only, `main`;
no new model, no new call (still at most 2 calls per question, ADR-012 / ADR-020).

## Facts (2026-11-19, read only)
- Base: `main` bdc6523 (#224 merged in PR #226 at aaf7b4f). DB `cee` = `corpus-2026-11-17`
  (`sync-db.ps1 -Check`: up to date). Branch `tl/215-part-gaps`.
- Mock baseline: `evals/baselines/corpus-2026-11-17/report.json`: 29 PASS / 1 FAIL (Q19), refusal
  gap 5/5, keyed 22/22, 0 forbidden; #224's mock reproduced it exactly (30/30 chunk lists).
- Hits already carry `part_id` (`p1..pn`, `research`, `peers`; `planner.search_parts`). The answer
  call does not see parts: `llm.build_user_message(question, hits)` lists chunks in hit order;
  `ask.answer_for` has no plan argument; ADR-020 says "The answer prompt is unchanged (v3, no part
  labels; the per-part answer check is #215)".
- `eval_run.cache_key` = (id, text, `PROMPT_VERSION`, snapshot, provider, model, chunk ids
  [, max_tokens when not 8000]). A prompt-version bump misses every saved answer. Saved v3 raw
  answers parse into `Answer` today; new fields must default so they still do.
- Planner cache (`.eval-runs/cache/*-plan-*.json`): plan-v2 outputs exist for Q3, Q7, Q12, Q25,
  Q28 (#224 real run, 2026-11-19 02:45-02:48, claude-sonnet-5-5, corpus-2026-11-17, cap 4); none for
  Q1, Q22, Q26, Q30 (they have never been planned with a model; Gate 4 ran before the planner).
- #224 real plans (plan-v2): Q3 4 Schwab parts (strategy, competition / losing ground, metrics,
  offerings); Q7 3 parts, one per firm, each "recruiting and retention, including compensation,
  training, and reported results"; Q12 4 parts (2 Schwab, EDJ current acquisition, "How Edward
  Jones could replicate ..."); Q25 2 model parts (MS + Schwab; EDJ) + code part p3 MER, RJF (whole
  question); Q28 3 parts (EDJ attrition, MER attrition, closest disclosed headcount change for both).
- #224 real answers (prompt v3): Q3 11 claims, 2 adjacent, **0 gaps** (no competition / concession
  gap); Q7 dimensions Recruiting, Retention, Advisor pay (**no training dimension**), 6 gaps, no
  uncited claim; Q25 behavior **`answer`** (bank: `gap_with_adjacent`), 7 gaps (payout "not public"
  for MS, EDJ, SCHW, MER; RJF ranges), and two **cited** claims that state an absence ("Disclosed
  pay structure - Schwab: not found in the evidence provided ..." citing `SCHW-10K-2025#50`).
- Gate 4 Q7 raw (`D:\ALLPROJECTS\EDJ\cache\ev121\r2-real\raw\Q7-7d3df04b429fd2d3d8d310ac.json`, v3):
  three uncited cells ("Recruiting - Morgan Stanley: no advisor-recruiting statement ... (see
  gaps)", "Retention - Morgan Stanley: ...", "Retention - Merrill: ...", each flagged
  `no_citation`) and model gaps "Morgan Stanley - recruiting: not found ...", "Morgan Stanley -
  retention: ...", "Merrill - retention: ..." for the same cells.
- Gate 4 failures this issue targets (`docs/results/gate4-report.md`, class s): Q3 (no concession,
  no gap naming it), Q7 (two dimensions, three uncited cells), Q12 (no Edward Jones cost
  structure), Q28 (net headcount vs attrition missing). Gate 4 PASS kept as regression: Q1, Q22,
  Q26, Q30.
- `fts.search(..., exclude=kept)` drops a chunk an earlier part or the research pass already kept
  (`fts.py` lines 995, 999), but `PoolTrace` records the candidates **before** that exclusion, and
  `search_parts` stores their count per part as `plan.searched[i]["pool"]`. So a part can have no
  hits of its own while its search did find passages (they sit under an earlier part).
- Leak check today (`tests/test_prompt._grams`, 6-word runs, run offline on v3 `SYSTEM_PROMPT`):
  against `passes_if` only Q28 / Q30 standard wording (exempt, as today); against **question text**
  one run, "since the start of the year", in v3's recency example
  (`Questions about recent change ("what's new", "since the start of the year"): newest first.`),
  shared with Q27's text.
- CI (`.github/workflows/tests.yml`) installs `requirements.txt` only, with no Postgres and no
  model SDK credentials, so a test that reaches the DB or differs from the local `.venv` can pass
  here and fail there.
- The Ask page renders `gaps` with `components.gap_box(what, suggested_source)` (no flags); claim
  flags render as chips (`claim_card`).

## Design

### Answer schema (`schema.py`), backwards compatible
- `Claim.part_id: str = ""` (model-written; `Adjacent` inherits it).
- `Gap.part_id: str = ""` (model-written), `Gap.flags: list[str] = []` (code-owned),
  `Gap.claim_text: str = ""` (code-owned: the model's text of an uncited grid cell moved here, kept
  for review in `query_log`, never shown).
- `llm_output_schema()`: `part_id` (string) added to claim, adjacent and gap, listed in `required`
  (OpenAI strict mode needs every property required; "" allowed). Code-owned fields stay out.
- A saved v3 raw (no `part_id`) parses unchanged: test on the Gate 4 Q7 raw and the #224 Q25 raw.

### Prompt v4 (`prompt.py`, `llm.py`)
`PROMPT_VERSION = "v4"`. User message (`build_user_message(question, hits, parts)`):
```
Question: <question>

Parts of the question (from the search plan; every claim, adjacent item and gap gives the
part_id it answers):
- p1 [Morgan Stanley]: <part text>
- p2 [Merrill]: <part text>

Evidence chunks, grouped by the part they were found for:
Part p1 [Morgan Stanley]: <part text>
<chunk id=... source=...> ... </chunk>
Part p2 [Merrill]: <part text>
(no passages were found for this part)            <- part's candidate pool was 0
Part p3 [Raymond James]: <part text>
(no further passages; the passages found for this part are listed under an earlier part)
                                                  <- pool > 0, every candidate kept earlier
Research passages (found for the whole question):
...
Peer firms on the question's theme:
...
```
The empty-part line is chosen from the part's candidate pool before exclusion
(`plan.searched[i]["pool"]`), never from its own hits (Facts: `exclude=kept`). Without
`plan.searched` (passage mode, or a plan not searched by `search_parts`), a part with no hits
gets the neutral second line. Within a group the hits keep their order (Q26's newest-first order
holds inside each group). With no parts given (`parts=None`: a direct `generate` call, tests) the message has one part p1 = the
question and every chunk under it. Firm labels are config short names.

System prompt changes (the rest of v3 stays word for word except the two rewordings named below;
final wording may tighten, it must pass the leak test):
- **Recency example reworded** (leak, Facts): v3's `Questions about recent change ("what's new",
  "since the start of the year"): newest first.` becomes `Questions about recent change (what is
  new, what changed since a given date): newest first.` Same rule, no bank wording. Its check is
  the Q26 real run (items newest first); the PR names this rewording.
- **Parts** (replaces v3's "Every part" rule, keeps its home-firm sentence and "what a question of
  its type needs"): "The user message lists the parts of the question (p1, p2, ...) and groups the
  evidence under the part it was found for. Give every claim, adjacent item and gap the part_id of
  the part it answers. Every part gets at least one cited claim, or a gap that names what is
  missing for that part; a part with no passages under it is a gap. A chunk listed under one part
  may also answer another part: cite it there with that part's id. Research and peer passages
  belong to no part: cite them under the part they answer."
- **Comparison grid** (dimensions from the question, NEXT item 4): v3's sentence "Take the
  dimensions from the question's own terms and from what the evidence covers for at least one of
  the firms; fix a short list of them first and use the same dimensions for every firm." is
  **replaced** (it contradicts the new rule) by: "Fix the dimensions from the
  question and its parts before reading the evidence: each dimension a part names (a part asking
  about 'pay, training and results' names three), or each part when the parts are dimensions. Do
  not drop an asked dimension because the evidence is thin, and do not add one only because the
  evidence offers it. Use the same dimensions for every firm." The v3 cell rules stay ("<Dimension> - <Firm>:", every firm under every
  dimension, firm's own terms); added: "An empty cell is only a gap, never a claim: a claim always
  has chunk_ids."
- **Behavior for disclosure questions** (Q25, TL note 2026-11-19): one sentence added under
  "Partial or missing disclosure": "A question about what firms disclose on a topic is answered by
  the disclosures, but the behavior follows the specifics the topic is about (rates, formulas,
  grids, amounts): when those are not disclosed for most of the firms asked about, choose
  gap_with_adjacent, with the disclosures as claims and each firm's undisclosed specifics as a gap
  that names the firm." v3's "most of the firms" sentence and every standard wording stay verbatim.
- Tests: the prompt names no question ID; no 6-word run shared with any bank `passes_if` (standard
  wording exempt, as today: Q28, Q30) **or any question text**, checked on the **whole** v4 prompt
  with no exception (the recency example is reworded above; the offline check on the planned v4
  sentences found no other run). This is the #224 planner test's check, now applied to the answer
  prompt too.

### Behavior choice: prompt, not a code rule
Code does not derive the behavior from per-part coverage. Reasons:
1. Q25 would not trigger it: in #224's answer every part has cited disclosures (10-K pay text, ADV
   brochures); the undisclosed asks (payout grid, formula) sit inside parts, so per-part coverage
   reads "all covered".
2. Per-part coverage depends on how the planner split the question (per firm or per dimension),
   so the same evidence could flip the behavior with the split.
3. A coverage rule would also act on Q11 and Q23 (most firms lack a headcount figure), which is
   NEXT item 5, out of scope.
**NEXT item 5 is not touched**: v3's "most of the firms" sentence is unchanged; the new sentence
only applies it to "what has been disclosed" questions. Q11 and Q23 already choose
`gap_with_adjacent` under v3, so v4 cannot move them toward `answer`; they are not run, the bank is
not changed, and item 5's decision stays open (said in the PR).

### Code check (`validate.py`; ground rules 1, 3, 6)
1. **Uncited grid cells move to gaps** (`move_uncited_cells`, first step of `check_citations` after
   `withhold_normative` / `ensure_handoff`): a claim with **no** `chunk_ids` whose text starts
   "<Dimension> - <Firm>:" (Firm = a configured entity name or alias, `fts._mentions` rules) leaves
   `claims` and becomes `Gap(what="<Firm> - <Dimension>: no cited evidence in this answer.",
   part_id=<claim's>, flags=["uncited_cell"], claim_text=<model text>)`. The text is true by
   construction: code knows only that the model gave no citation, not that the evidence lacks the
   fact (a model can drop `chunk_ids` on a true cell), so it never says "not found in the
   evidence". No uncited model statement is shown; the model text stays in `claim_text` for review.
   When a model gap already starts "<Firm> - <Dimension>:" (case and spacing ignored; Gate 4 Q7 has
   all three), no second gap is added: that gap keeps its own text and gets the flag and
   `claim_text`. A claim whose citations are
   all unmatched is **not** moved (CLAUDE.md: unmatched citations are flagged, never dropped);
   any other uncited claim keeps the `no_citation` flag as today.
2. **Every part covered** (`check_parts(answer, plan, hits)`, called in `ask.answer_for` after
   `check_citations`, before `insert_caveats`): part P is covered by
   - a claim or adjacent item with `part_id == P` and at least one citation in the retrieved set;
   - a gap with `part_id == P`;
   - fallback when the item's `part_id` is empty or not a plan part id (v3 outputs, the mock, a
     model that omits it): a claim or adjacent item citing a hit whose `hit.part_id == P`; in a
     one-part plan every gap covers p1. The hand-off sentence added by code (`ensure_handoff`,
     cites every chunk) is excluded from the fallback;
   - in an `answer_with_boundary` answer, a part whose text `is_normative` (Q12 p4 "How Edward Jones
     could replicate ...") is covered by the hand-off sentence (that part is the strategist's).
   An uncovered part gets `Gap(part_id=P, flags=["part_gap"], suggested_source=<the part firms'
   registry sources>)` with `what`:
   - "No evidence retrieved for: <part>" when P's candidate pool before exclusion was empty
     (`plan.searched[i]["pool"] == 0`; the issue's wording);
   - "Not answered from the evidence retrieved for: <part>" otherwise: P's search found
     passages (kept under P, or kept earlier under another part or `research` because of
     `exclude=kept`), but no claim, adjacent item or gap covers P. Also used when the plan has no
     `searched` record (no pool count known), so code never claims "no evidence" it cannot prove.
     **Deviation from the issue's single wording**: with passages retrieved, "No evidence
     retrieved" would be a false statement made by code. The pool, not `hit.part_id`, decides,
     because a chunk P found can sit under an earlier part.
   Suggested sources: `check_parts` fills `suggested_source` through `suggested_sources()` ->
   `registry_lookup` (DB); its tests swap in a fake `registry_lookup` (as `test_validate.py` does
   today), so they make no DB call and run on CI.
   `<part>` = the part text, plus " (<firm short names>)" when the text equals the question (rule
   plan parts all repeat the question). If the label `is_normative`, it becomes "part P (<firms>)"
   (ground rule 6: code never prints a "should"). Behavior, claims and model gaps are not changed.
   No plan (callers that pass none) or empty retrieval (`empty_retrieval_answer`): no part check.
3. `part_coverage(answer, plan, hits) -> {part_id: "model" | "citation" | "handoff" | "code_gap"}`
   for the eval record and the PR table.

### Mock
`llm._mock` is unchanged in what it cites (the top 3 hits); each claim gets `part_id` = its hit's
`part_id` when that is a plan part (`p<n>`), else "". So `check_parts` runs on mock answers too:
one-part questions are always covered (no change); a rule-plan multi-firm question whose top 3 hits
all come from p1 gets a code gap "Not answered from the evidence retrieved for: <question> (<firm>)"
for each other part. This is honest (the mock did not use those passages) and lets verify-cee show
the code gap in the app without a paid call. The mock eval scores retrieval only, so its numbers
cannot change.

### Ask page and trace (user-visible)
- `components.gap_box(what, suggested_source, flags)`: code flags as chips, like claim flags
  (`part_gap`, `uncited_cell`). `ask_page.show_answer` passes `g.flags`. Gaps stay always visible.
- Trace: the check line adds ", N empty cells moved to gaps" when N > 0; the caveats line adds
  " (K added by code for unanswered parts)" when K > 0.
- No part headings on the Ask page (the grouping is in the model's input; showing parts in the UI is
  not asked by the issue).

### Eval (`scripts/eval_run.py`)
- `RealRunner.answer(q, query, hits, plan)` passes the plan to `answer_for` (fresh and cached).
- `cache_key(..., parts=None)`: `{"parts": [[id, text, firms], ...]}` joins the key only when
  parts are given (the user message now depends on them); without parts the key is byte-identical
  to today's (test with today's literal), so saved v3 outputs keep their keys and still parse.
- Real records get `part_coverage`; `report.md` unchanged.

## Files to change
- `src/cee/answer/schema.py` - `part_id` on claims / gaps, `Gap.flags`, `Gap.claim_text`, schema.
- `src/cee/answer/prompt.py` - v4 (parts rule, grid dimensions, disclosure-behavior sentence).
- `src/cee/answer/llm.py` - `build_user_message(..., parts)`, `generate(..., parts)`, requests,
  mock `part_id`.
- `src/cee/answer/validate.py` - `move_uncited_cells`, `check_parts`, `part_coverage`, wording
  constants.
- `src/cee/ask.py` - `answer_for(..., plan=None)`, `ask` passes the plan, trace texts.
- `src/cee/app/components.py`, `src/cee/app/views/ask_page.py` - gap flags as chips.
- `scripts/eval_run.py` - plan into `answer`, `cache_key` parts, `part_coverage` in records.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-answer.md` - `ask-part-gap`.
- `tests/test_schema.py`, `tests/test_prompt.py`, `tests/test_validate.py` (or new
  `tests/test_part_check.py`), `tests/test_llm_openai.py`, `tests/test_eval_run.py`,
  `tests/test_ask_progress.py` / `tests/test_ask_page_trace.py`, `tests/test_components.py` -
  as needed.
- `tests/data/answer_v3_q7_gate4.json`, `tests/data/answer_v3_q25_0224.json` (new; the `raw` of the
  two saved v3 outputs named in Facts, for compatibility and cell tests; `.eval-runs/` and the cache
  folder are not in git).
- `specs/answer-citations.md` - prompt v4, part check, moved cells, wording, behavior sentence.
- `specs/ui.md` - gap box shows code flags (one phrase).
- `docs/ARCHITECTURE.md` - Answer JSON: `part_id`, gap `flags`.
- `docs/DECISIONS.md` - ADR-020: the answer prompt is v4 with part labels; the per-part check is
  code (#215).
- `plans/0215-part-gaps.md` (this file).
Not changed: retrieval (`fts.py`, `planner.py`), `config/`, `evals/questions.yaml`,
`evals/expected_chunks.yaml`, the mock baseline, `MAX_TOKENS` (8000).

## Steps
1. **Schema + tests.** New fields, `llm_output_schema`, the two v3 fixtures parse. `pytest -q`.
2. **Code check + tests** (0 calls): `move_uncited_cells` (Gate 4 Q7 raw: 3 cells leave `claims`,
   the 3 matching model gaps get `uncited_cell` + `claim_text`, no new gap text; a synthetic
   uncited cell with no matching gap becomes "<Firm> - <Dimension>: no cited evidence in this
   answer."; a claim with an unmatched citation stays, flagged; an uncited non-grid claim stays,
   `no_citation`); `check_parts` (a part with no claim and no gap gets the code gap, both wordings
   chosen by the pool; **two parts sharing a chunk**: p2's only candidate was kept by p1, so p2 has
   no hits, pool 1, and gets "Not answered from the evidence retrieved for", never "No evidence
   retrieved"; no `searched` record -> "Not answered ..."; covered by part_id, by citation
   fallback, by gap, by adjacent; one-part plan; boundary + normative part; normative label
   replaced; code hand-off not counted; behavior unchanged); `part_coverage`. Fake
   `registry_lookup` in every `check_parts` test (no DB).
3. **Prompt v4 + user message + mock** and tests (grouping; empty-part line by pool: pool 0 -> "no
   passages were found", pool > 0 with no hits -> "listed under an earlier part"; research / peers
   groups; order kept; leak test over `passes_if` and question text on the whole prompt; recency
   example reworded; v3 grid-dimension sentence gone; version; mock part ids).
4. **Ask / eval / UI wiring** + tests (`answer_for` with plan; trace texts; `cache_key` without
   parts equals today's literal, with parts differs; gap chips).
5. **Offline replay (0 calls)**, scratch `D:\ALLPROJECTS\EDJ\cache\ev215\replay.py` (not committed),
   output `replay.txt`: (a) the #224 plan-v2 plans + v3 answers for Q3, Q7, Q12, Q25, Q28 through
   `check_citations` + `check_parts` (hits rebuilt with `search_parts` from the saved plan, as
   #224's replay did): which parts v3 left uncovered and which code gaps would be added; (b) the
   Gate 4 Q7 raw through `move_uncited_cells`; (c) the v4 user message for Q7 and Q25 written to
   `ev215\user-message-Q7.txt` / `-Q25.txt` for reading. `replay.txt` states that v3 gaps carry
   no `part_id` and the gap fallback covers only one-part plans, so on these v3 answers code gaps
   are added next to model gaps that already name the part (e.g. Q25, Q28): a v3-only over-count,
   not what a v4 answer gets.
6. **Mock eval**: `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0215-mock`; scratch diff: 30/30
   chunk lists identical (same order), 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22, 0
   forbidden, no PASS -> FAIL. Any difference stops the work.
7. **Docs**: spec, ui spec line, ARCHITECTURE, ADR-020 sentence.
8. **verify-cee** (port 8599 checked free; never touches `wt-212` / `wt-213`): all features PASS,
   incl. the new `ask-part-gap` steps.
9. **Real runs last** (paid-call plan), judged; tables in `...\ev215\real-table.txt`.
10. `/finish-task`: PR "Closes #215" (or "Part of #215" with the missed items) with the part table,
    replay, mock diff, verify-cee run, real calls and model (actual `real_calls` / `reused` from the
    report, not the expected 13 / 5), the TL pre-approval comments quoted, the recency rewording
    named, and the Q7 / Q25 results marked in-sample. **`gh pr checks <PR#>` all green on the PR
    head** before `/finish-task` completes (CI: `requirements.txt` only, no Postgres, no SDK
    credentials).

## Paid-call plan (CLAUDE.md "Paid API calls"; TL pre-approval comments on #215, 2026-11-18/19)
TL pre-approval, quoted (issue #215 comments): 2026-11-18 "Real calls planned in each approved
ExecPlan (question IDs, why the mock cannot show it, runs of each) are approved"; 2026-11-19 "One
more real run (Q25, 1 run) is planned for this issue." Together with the issue's "8 runs, 16 calls"
that is 9 runs, at most 18 calls, so the `--max-calls 18` note (more than 10 calls) is covered by
these comments; the PR quotes them.
Last, on finished code after every mock check, the replay and verify-cee pass: **9 questions, one
run each, planner + answer = up to 2 calls each, at most 18 calls**: Q3, Q7, Q12, Q28, Q25
(targets) and Q1, Q22, Q26, Q30 (regression). Model `claude-sonnet-5-5`, prompt v4, planner
plan-v2, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; .venv\Scripts\python.exe
scripts\eval_run.py --real --max-calls 18 --questions Q1,Q3,Q7,Q12,Q22,Q25,Q26,Q28,Q30 --as-of
2026-11-17 --baseline evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0215-real`.
**Expected reuse**: the 5 plan-v2 outputs of Q3, Q7, Q12, Q25, Q28 (same planner version, snapshot,
model, cap and resolved query as #224) are reused, so those questions search exactly #224's parts
and differ only in the answer prompt; Q1, Q22, Q26, Q30 have no saved plan: 4 planner calls. The
v4 prompt and the parts in the key miss every saved answer: 9 answer calls. **Expected 13 calls,
reused 5**; the report's actual `real_calls` / `reused` are quoted (if the planner reuse misses,
up to 18 calls, still inside the cap). Raw outputs (planner and answer,
request meta, `stop_reason`) in the run's `raw/`, copied to `D:\ALLPROJECTS\EDJ\cache\ev215\real`.
Why the mock cannot show it: the mock never reads the prompt and always cites its top 3 passages,
so it cannot show whether the model answers each part, takes grid dimensions from the parts, writes
part ids, or chooses `gap_with_adjacent` for Q25; the code check and moved cells are proven offline
(tests on saved real outputs, the replay), but only a model call shows how often the model itself
covers each part and whether the regression questions keep their quality with v4 and a planner.
One run each, no re-runs. A truncated / invalid output is `INVALID_OUTPUT` (a finding); a failed
planner call falls back to the rule plan (counted, a finding). A missed acceptance item is reported,
not re-rolled. No other call path.

## Risks
- **Regression attribution**: Q1, Q22, Q26, Q30 run with a planner for the first time (Gate 4 had
  none), so a change there may come from plan-v2's parts, not prompt v4. The PR says which (their
  retrieval status and chunk lists vs the baseline and Gate 4); no extra call to separate them.
- **Code gaps hide model misses**: the issue's "every part has a claim or gap" holds by
  construction once code adds gaps, so the real table separates parts covered by the model (by
  `part_id` or by citation) from parts covered by a code gap; the code-gap count is the measure.
- **Citation fallback is lenient**: a claim without a part id that cites a chunk found for P covers
  P even if it answers another part. Used only for items without a valid part id; the table
  counts how many parts were covered that way in the real run.
- **Longer answers**: part ids and more gaps add output; `MAX_TOKENS` 8000 kept; a truncated answer
  is a finding (`stop_reason` saved), not a re-run.
- **Mock gaps on multi-firm questions**: a two-firm mock answer now shows a code gap for the part
  the mock did not cite. Intended (honest), stated in the recipe.
- **In-sample prompt**: Q7 and Q25 drove the grid and disclosure sentences (the grid example "pay,
  training and results" paraphrases Q7's dimensions; "rates, formulas, grids, amounts" mirrors
  Q25); Q3, Q12, Q28 drove the parts rule. They pass the 6-word check, but the PR marks the Q7 and
  Q25 results (and Q3, Q12, Q28) as in-sample; Q1, Q22, Q26, Q30 are the check. NEXT item 4 also
  names Q8 as a grid check; only Q22 runs, matching the issue's list.
- **Recency rewording**: the v3 example changes wording only; Q26 (newest first) is its check.
- **Known W10 findings not in scope** (TL decision on #224): Q25's bare "payout" still retrieves its
  `must_not_return` deck chunks, so Q25's retrieval status / refusal check may stay FAIL; Q7's RJF
  part lacks training and pay words, so an RJF training cell may be a gap for retrieval reasons.
  Judged on the answer, reported, not fixed here.
- **Cited absence claims** (#224 Q25 "... Schwab: not found in the evidence provided" with a
  citation) are not moved by code (they cite something); the v4 grid sentence asks for gaps instead.
  Counted in the real table.

## Acceptance
- [ ] Tests (0 calls, fake `registry_lookup`, no DB): a part with no claim and no gap gets the code
  gap ("No evidence retrieved for: <part>" when its candidate pool `plan.searched[i]["pool"]` is 0;
  "Not answered from the evidence retrieved for: <part>" when the pool is > 0 or unknown), flag
  `part_gap`, the part's id and a suggested source; two parts sharing a chunk (p2's only candidate
  kept by p1): p2 gets "Not answered ...", not "No evidence retrieved"; covered parts (by part id,
  citation fallback, gap, adjacent, boundary hand-off for a normative part) get none; behavior and
  model items unchanged; a normative part label is replaced.
- [ ] Tests: an uncited grid cell with no matching model gap becomes a gap "<Firm> - <Dimension>:
  no cited evidence in this answer." with flag `uncited_cell` and the model text in `claim_text`;
  on the Gate 4 Q7 raw the 3 uncited cells leave `claims` and their 3 matching model gaps keep
  their own text and carry the flag and `claim_text` (no duplicate gap); an unmatched-citation
  claim stays flagged; an uncited non-grid claim keeps `no_citation`.
- [ ] Tests: saved v3 raws (Gate 4 Q7, #224 Q25) parse; `cache_key` without parts equals today's;
  `PROMPT_VERSION == "v4"`; the user message groups chunks by part, with the empty-part line chosen
  by pool (0 -> "no passages were found", > 0 -> "listed under an earlier part"); the whole v4
  prompt names no question ID and shares no 6-word run with any question text (no exception; the
  recency example is reworded) or `passes_if` (standard wording exempt: Q28, Q30, as today); the
  v3 grid-dimension sentence is gone; the mock's claims carry their hit's part id.
- [ ] Replay (0 calls) tabled: per part of Q3, Q7, Q12, Q25, Q28 under #224's v3 answers, covered
  or code gap; Gate 4 Q7 cells moved.
- [ ] Mock (`.eval-runs/0215-mock`): 30/30 chunk lists identical to the baseline, refusal gap 5/5,
  keyed 22/22, 0 forbidden, no PASS -> FAIL.
- [ ] `pytest -q` passes; verify-cee all PASS, incl. `ask-part-gap`: the two-firm mock question shows
  every `part_gap` gap of its logged answer with the `part_gap` chip, and the logged gaps are
  exactly one per plan part not covered by the mock's claims (both read from the newest
  `query_log` row: `filters->plan` parts and `answer` claims / gaps; not hard-coded, since the
  mock's top 3 passages decide which parts it cites); the one-part question likewise shows exactly
  its logged `part_gap` gaps (expected none: the mock cites p1 passages there).
- [ ] Real (`.eval-runs/0215-real`, <= 18 calls, claude-sonnet-5-5): in Q3, Q7, Q12, Q28 every
  planned part has a cited claim, cited adjacent item or a gap (table in the PR: per part, covered
  by model part id / citation / hand-off / code gap); no uncited grid cell left in `claims` (moved
  by code); any other uncited claim stays flagged `no_citation` and is counted in the table. Judged
  against `passes_if` and reported (not required to pass): Q3 names competition and where Schwab
  concedes ground, or a gap for it; Q7 uses recruiting posture, payout philosophy, training
  pipeline and retention results for all three firms, empty cells in gaps; Q12 shows Edward Jones's
  cost structure or a gap for it, then the hand-off; Q28 states the adjacent net headcount change
  and how it differs from attrition.
- [ ] Real Q25 (TL note 2026-11-19): every undisclosed part per firm is named as a gap (payout grid
  / formula for MS, Merrill, Edward Jones; Schwab's advisor pay; RJF's full grid behind its
  published ranges), no trade-press payout-grid claim (trade press only in `adjacent`), behavior
  `gap_with_adjacent`.
- [ ] Real: Q1, Q22, Q26, Q30 keep their Gate 4 verdicts (PASS) judged against `passes_if`, and
  their expected behavior.
- [ ] Specs, ARCHITECTURE and ADR-020 updated; verify-cee recipe and driver updated in this PR.
- [ ] `gh pr checks <PR#>` all green on the PR head before `/finish-task` completes.

## Progress log
- 2026-11-19 03:04 - plan written. Branch `tl/215-part-gaps` from `main` bdc6523; DB
  `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`). Read: issue + 3 TL comments (Q25 added,
  depends on #224), specs/answer-citations.md, specs/retrieval.md planner section via plan 0224,
  CLAUDE.md, ADR-012/019/020, NEXT items 3-5, the answer and planner code, eval_run, verify-cee
  ask-answer / gap-path, Gate 4 Q3 / Q7, the #224 real plans and answers (Q3, Q7, Q25), the
  plan-v2 cache entries (5 reusable), the Gate 4 Q7 raw with its 3 uncited cells.
- 2026-11-19 03:30 - plan revised after review (issuecomment-7004788998, 1st blocking return):
  (1) leak: v3's recency example "since the start of the year" shares a 6-word run with Q27's
  text (confirmed offline with `_grams`); reworded (option a), the question-text check covers the
  whole v4 prompt with no exception, Q26 is the rewording's check. (2) Code gap and empty-part line
  chosen from the part's candidate pool before exclusion (`plan.searched[i]["pool"]`), with a
  shared-chunk test. (3) Moved uncited cell text "<Firm> - <Dimension>: no cited evidence in this
  answer." (true by construction); a matching model gap keeps its own text. (4) `gh pr checks` all
  green in step 10 and Acceptance; `check_parts` tests use a fake `registry_lookup`. Non-blocking:
  Q7 #224 has 6 gaps; v3 grid-dimension sentence replaced; Q7 / Q25 in-sample in the PR; replay
  over-count note; TL pre-approval quoted, actual `real_calls` / `reused` reported. Re-read: the
  verify-cee part-gap check and the real "no uncited claim" line made derivable / reportable so
  they cannot fail on correct code.
