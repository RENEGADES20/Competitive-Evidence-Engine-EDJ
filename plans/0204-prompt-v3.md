# 0204 - Prompt v3: comparison grid, positions, every asked part, behavior choice

Issue: #204    Role: TL    Spec: `specs/answer-citations.md` (S2 area; owner review waived by TL
decision 2026-11-17, #187 comment). Read only: `plans/0121-gate4.md` on `tl/121-gate4` (R1 table,
triage, run ledger), R1 scoring pack `D:\ALLPROJECTS\EDJ\cache\ev121\r1-scoring\`, R1 raw outputs
`D:\ALLPROJECTS\EDJ\cache\ev121\r1-real-30\raw\`, `evals/questions.yaml` (`passes_if`, never
copied into the prompt), ADR-012 (`docs/DECISIONS.md`).

## Goal
The answer prompt (v3) gains four general rules, with no question-specific text: (1) a question
about several firms is answered on one grid, dimension by dimension, with an empty cell named as a
gap for that firm; (2) a question about where something is heading or the spread of views is
grouped by position, each claim attributed and dated; (3) every part the question asks for, or
implies by its type, is covered by a claim or named in `gaps`; (4) the behavior choice: the asked
quantity undisclosed for most firms -> `gap_with_adjacent` with what is disclosed reported as
claims; evidence for part of the asked population -> `answer` with the missing parts as gaps.
The `Answer` schema does not change. The real check is #121's combined R2.

## Facts (2026-11-18 00:40, read-only)
- Branch `tl/204-prompt-v3` from `origin/main` a886741 in `D:\ALLPROJECTS\EDJ\wt-204`. DB `cee` =
  `corpus-2026-11-17` (`sync-db.ps1 -Check` in `repo`: up to date).
- `src/cee/answer/prompt.py`: `PROMPT_VERSION = "v2"`, `SYSTEM_PROMPT` with sections Citations,
  Writing claims, Choosing the behavior, Standard gap wording. `PROMPT_VERSION` is read by
  `scripts/eval_run.py` (cache key, report meta) and asserted in `tests/test_prompt.py`.
- The mock provider (`llm._mock`) does not read the prompt, so mock eval statuses cannot move.
- R1 (prompt v2, `claude-sonnet-5-5`) failures this issue targets, from the scoring pack:
  - Q7: claims grouped by firm, no common dimensions; payout absent for all three firms; MS only
    as adjacents; two gaps (MS, Merrill), none per dimension.
  - Q16: six claims, one per firm/source; no grouping by position.
  - Q3: framing and priorities, the 10-K competitor list, but no pressure management concedes and
    no gap saying so. The question text does not ask for it; a strategy question implies it.
  - Q12: Schwab scale and acquisition, EDJ strategy and digital-cost risk, but no EDJ cost
    structure set alongside and no gap saying it is missing.
  - Q25: behavior `answer` with RJF's Corporate RIA range as the first claim; four of five firms
    "Payout grids are not public." (the RJF ranges gap line does not name the firm).
  - Q20: `gap_with_adjacent`, 0 claims; UBS next-generation findings (79%, women 90%) only as
    adjacent. The age-split passages (`UBS-NEXTGEN-2026#81/#119`) were not retrieved (#203).
- R1 output size: largest raw answer 8.6k characters (Q14, 14 claims), about 2.2k tokens;
  `anthropic_request` caps output at `max_tokens` 4000. A five-firm grid with a gap per empty cell
  (Q22, Q24, Q25 shapes: up to 20 cells plus adjacents) can come close to that cap, and a cut-off
  tool call is an `INVALID_OUTPUT` (#187) that would waste the one R2 run of that question.
- The Answer schema can carry a grid without a new field: each claim text starts with the
  dimension and the firm, claims are ordered dimension by dimension, and each empty cell is a gap
  "<Firm> - <dimension>: ...". The Ask page lists gaps under the claims, so empty cells are
  visible. A `dimension` field would touch `schema.py`, `llm_output_schema()`, the strict OpenAI
  schema, `validate.py` and the UI; not needed for `passes_if`, so not done (noted for NEXT).

## Files to change
- `src/cee/answer/prompt.py` - `PROMPT_VERSION = "v3"` with a v3 comment line; new section
  "Shaping the answer" with rules 1-3; rule 4 in "Choosing the behavior"; two wording edits
  below. All rules are written in general terms (firms, dimensions, positions, parts, population),
  with no question ID, firm-specific topic or `passes_if` phrase.
  - Rule 1, comparison grid: when the question names two or more firms, or says "each of" /
    "across the five", take the dimensions from the question's own terms and from what the
    retrieved evidence covers for at least one of the firms (no fixed default list); use the same
    dimensions for every firm; write the claims
    dimension by dimension, each claim text starting "<Dimension> - <Firm>:"; each firm's cell in
    its own terms (do not force one firm's business model onto another); a dimension with no
    evidence for a firm is a gap "<Firm> - <dimension>: not found in the evidence provided."
    with a suggested source; never fill a cell with an inference, an adjacent figure presented as
    the cell, or a statement about a different firm.
  - Rule 2, positions: when the question asks where something is heading, what the future looks
    like or what the range of views is, group claims by position (start each claim with the
    position in a few words), list who holds it and when, and keep firm statements, research and
    trade press attributed, saying whose statement each claim is; when two sources disagree on the
    same point, report both and say that they disagree; offer no forecast or synthesis of your own.
  - Rule 3, every part: split the question into its parts (each "and", each named firm, each
    named metric, "how has it changed"); cover every part the question asks for, or that a
    question of its type needs, such as headwinds or risks the firm itself names; when the
    question sets the home firm against a peer or asks how it could act, the evidence half shows
    the home firm's figures on the same dimension, from its own filings. Each part gets at least
    one claim or a gap that names the part.
  - Rule 4, behavior choice (added to "Choosing the behavior"): if the asked quantity is not
    disclosed for most of the firms asked about, choose `gap_with_adjacent`, answerable=false;
    report what is disclosed as claims, each firm's missing disclosure as a gap. If evidence
    covers part of the asked population, cohort or period (a survey of an overlapping or
    narrower group, some of the quarters), choose `answer`, report each finding with its source,
    sample and date as printed in the chunk, say which group it covers, and list the missing
    parts as gaps. A wider unit that contains the one asked about (a parent company, a segment)
    is not partial evidence: it stays adjacent. (Plan note only, never in the prompt: this keeps
    the Q30 trap unchanged; the question-ID test would catch it.)
  - Wording edits: in a multi-firm answer the published-ranges gap also names the firm first
    (PROGRESS.md 2026-11-17 note: "RJF gap line to name the firm at the next prompt change"); the
    "answer" bullet points to rule 4 for the partial case.
  - Unchanged: the citation rules, every standard wording constant, the boundary hand-off text
    and its placement, "Never recommend", the GWIM attribution rule. Caveats, source labels,
    flags, withholding and the hand-off insertion stay code-owned (`validate.py`, not touched).
- `src/cee/answer/llm.py` - `anthropic_request` `max_tokens` 4000 -> 8000 (comment: grid answers
  with a gap per empty cell, #204). OpenAI request has no cap; unchanged. No other change.
- `tests/test_prompt.py` - `PROMPT_VERSION == "v3"`; new tests: each of rules 1-4 appears (key
  phrases, whitespace-normalised as in the existing pay test); the prompt holds no question ID
  (`\bQ\d{1,2}\b`) and no 6-word run of any `passes_if` text from `evals/questions.yaml`, both
  sides tokenised lower-case with punctuation stripped (`re.findall(r"[a-z0-9']+", s.lower())`);
  a helper test feeds the round-1 plan's rule-3 strategy clause (commit 6976a04: "a strategy
  question also covers how the firm frames the business, its stated priorities and the
  competitive pressure management acknowledges, including where it concedes ground") to the same
  check and asserts it is caught, so the check is shown to work; every
  standard wording constant still appears; the boundary hand-off still appears verbatim and the
  prompt still says "Never recommend"; the published-ranges gap line names the firm;
  `anthropic_request(...)["max_tokens"] == 8000`.
- `tests/test_validate.py` - one offline test: a hand-made grid-shaped `Answer` (three firms, two
  dimensions, two empty cells as gaps, a GWIM-cited claim; fake hits, no DB) goes through
  `check_citations` / `insert_caveats` unchanged in shape: claims keep their order and
  "<Dimension> - <Firm>:" text, gaps are kept, the GWIM caveat is inserted by code, a claim citing
  an unretrieved chunk is flagged. Shows the grid needs no schema or validator change.
- `specs/answer-citations.md` - new section "Answer shape (prompt v3, #204)" with the four
  rules in plain words and the grid convention; the behavior table gains the v3 choice rule; the
  advisor-pay row notes that the ranges gap names the firm.
- `docs/PROGRESS.md` - not edited by hand; the PR's `## Progress line` (prompt v3, 0
  bank-question calls, probe calls) is copied in by the bot at merge.
- Not changed: `schema.py`, `validate.py`, `fts.py`, `config/`, `evals/`, the corpus, the UI.
  No ADR: prompt rules are not an architecture decision; the call count stays one (ADR-012).

## Paid calls (planned before the first call)
- **0 real calls on bank questions** (#121 run ledger). The real check of Q3, Q7, Q12, Q16, Q20,
  Q25 and the sentinels Q4, Q8, Q21, Q24, Q27, Q30 is #121's combined R2 after this merges.
- **Probe run (pre-approved by the TL): 4 non-bank questions, one call each,** to check before
  merging that the model follows the new rules at all (the mock cannot show wording, grouping or
  behavior choice). Texts checked against Q1-Q30 (no match). Mock retrieval of each, 2026-11-18
  (0 calls), gives the evidence spread named below.

  | Probe | Question | Rule | Mock pool | Pass if (written before the call) |
  |---|---|---|---|---|
  | P1 | How do Edward Jones, Morgan Stanley and Raymond James each approach succession planning for retiring advisors? | 1 grid, 3 every part | EDJ 7, RJF 7, MS 6, uneven on topic | Same dimensions for all three firms; claims ordered by dimension and prefixed "<Dimension> - <Firm>:"; at least one empty cell named as a firm + dimension gap; no cell filled with another firm's or an adjacent fact |
  | P2 | Where is the industry heading on alternative investments for individual clients? | 2 positions | theme, 7 groups (BofA study, MS, SCHW, MER, trade press) | Claims grouped by position, not by firm; each attributed and dated; no forecast of its own |
  | P3 | What has each of the five disclosed about client retention rates? | 4 undisclosed for most | all five firms, talent/attrition text, no client retention rates seen | `gap_with_adjacent`, answerable=false; a gap per firm with no disclosure; anything disclosed as a claim; associate/advisor retention labelled adjacent |
  | P4 | What evidence is there about how women investors choose a financial advisor? | 4 partial population | UBS next-generation survey with a women split, Cerulli | `answer`; the UBS finding reported with source, sample/group and date, its group stated (next-generation women, not all women); missing groups as gaps |

  Run once, together, after every mock and unit check passes, with a scratch driver
  `D:\ALLPROJECTS\EDJ\cache\ev204\probe.py` (`resolve` -> `search` -> `answer_for`,
  `LLM_PROVIDER=anthropic` set for that command only; `.env` stays on mock) that refuses to run
  more than the 4 texts above and saves per probe: question, prompt version, model, chunk_ids,
  raw model output and checked answer, to `D:\ALLPROJECTS\EDJ\cache\ev204\probe-v3\`.
  A miss is a finding, reported in the PR. At most one prompt revision may follow, kept general
  and passed through the fixed leak test and the hand check; only the probes whose rule was
  revised are run once more (`probe-v3b\`): at most 8 probe calls in total.
  The probes are template-adjacent to bank questions (P1 ~ Q7, P2 ~ Q18, P3 ~ Q25, P4 ~ Q20; P4
  shares Q20's UBS pool); "no match" is an exact-text check only. They check rule-following, not
  scores, and the PR says so.
- Model = `LLM_MODEL` in `.env`, recorded in each saved file. The PR's Verification section gives
  the call count (0 bank, N probe), the model, and why.

## Steps
1. **Prompt v3.** Edit `prompt.py` as in "Files to change". Hand check, beside the n-gram test:
   every rule's wording is read against the `passes_if` of every linked and sentinel question
   (Q3, Q7, Q12, Q16, Q20, Q25; Q4, Q8, Q21, Q24, Q27, Q30) and of Q18, for paraphrase as well as
   wording (a rule may not restate a rubric's list of items, e.g. Q7's four dimensions or Q3's
   strategy items); the result is written in the progress log. Read the rendered prompt once in full
   for contradictions with v2 rules (the "answer" bullet vs rule 4; the pay rule vs rule 1 in a
   multi-firm pay answer: the pay rule's wording wins inside the cell, rule 1 decides the layout).
2. **llm.py cap.** `max_tokens` 8000.
3. **Tests.** `tests/test_prompt.py`, `tests/test_validate.py` as above; `pytest -q` PASS.
4. **Offline re-validation of R1.** Scratch script `cache\ev204\revalidate_r1.py`: every
   `r1-real-30\raw\*.json` `raw` field through `Answer(**raw)` and, with that question's hits
   rebuilt from the saved `chunk_ids` (DB `cee`, read-only), `check_citations` + `insert_caveats`
   on this branch. Expect 30/30 parse, flags and caveats identical to R1 (`r1-scoring\summary.csv`):
   shows the schema and validators are unchanged and the stored outputs still load. 0 calls.
5. **Mock checks.** `python -m cee.smoke` PASS; mock eval
   `scripts/eval_run.py --as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-17/report.json --out D:\ALLPROJECTS\EDJ\cache\ev204\mock`
   -> 28 PASS / 2 FAIL (Q15, Q19), no status change, 0 forbidden, refusal 5/5 and 19/19 (the
   prompt does not touch retrieval). Mac: same commands with `PYTHONPATH=src`.
6. **Probe run** (P1-P4, 4 calls) as in "Paid calls"; judge each against its pass line; at most
   one revision + re-run of the revised probes.
7. **Spec and docs.** `specs/answer-citations.md`; check `docs/ARCHITECTURE.md` and README do not
   name the prompt version (grep at plan time: only PROGRESS.md and the spec do).
8. **App check.** `scripts/verify_cee.py run` (mock answer path still renders) only when the TL
   says `cee_verify` and its port are free (shared with the #203 worktree); `/finish-task`, PR
   with "Closes #204" only if that run has passed; otherwise "Part of #204" with the verify item
   open, or wait for the run.

## Acceptance
- [ ] Rendered-prompt tests: rules 1-4 appear; no question ID and no 6-word run of any
      `passes_if` in the prompt; `PROMPT_VERSION` = v3 ("Prompt version: v3" rendered); every
      standard wording constant and the hand-off sentence still in the prompt.
- [ ] Leak check proven: the lower-case, punctuation-stripped 6-word test fails when fed the old
      rule-3 strategy clause (commit 6976a04) against Q3's `passes_if`, and passes on the v3 prompt.
- [ ] Hand check logged: every rule read against the `passes_if` of Q3, Q7, Q12, Q16, Q20, Q25,
      Q4, Q8, Q21, Q24, Q27, Q30 and Q18 for paraphrase; no rubric list restated.
- [ ] Ground rules held (tests): caveats inserted by code (grid test, GWIM caveat), hand-off text
      unchanged, a citation outside the retrieved set is still flagged; `validate.py` and
      `schema.py` unchanged in the diff.
- [ ] R1 re-validation: 30/30 raw outputs load and validate with the same flags and caveats.
- [ ] Mock eval on `corpus-2026-11-17`: no status change against
      `evals/baselines/corpus-2026-11-17/report.json` (28/2, Q15, Q19); smoke PASS.
- [ ] `pytest -q` PASS; `verify_cee.py run` VERIFY PASS (when the TL frees `cee_verify`).
- [ ] Probes P1-P4: each pass line met, or the miss reported in the PR; <= 8 probe calls; 0 calls
      on bank questions.
- [ ] Expected in #121's R2 (not checkable here; written down so R2 can be read against it):
  - Q7: one grid, the same dimensions for MS, Merrill, RJF, taken from the question's terms and
    the evidence; each empty cell a firm + dimension gap.
  - Q16: claims grouped by position, each attributed and dated, no forecast of its own.
  - Q3: headwinds or competition the firm itself names as claims, or a gap naming that part.
  - Q12: EDJ's disclosed cost figures set alongside Schwab's (if retrieved), or a gap naming EDJ's
    cost structure; hand-off last; still `answer_with_boundary`.
  - Q25: `gap_with_adjacent`; RJF's published ranges as a claim; four firms "<Firm>: Payout grids
    are not public."; RJF's ranges gap names the firm; no trade-press reconstruction as a claim.
  - Q20: `answer` with survey findings, source, sample and date, the group each covers, missing
    age groups as gaps (needs #203's passages; with R1's pool, the UBS next-generation findings
    as claims with their group named).
  - Sentinels unchanged: Q4, Q27 Merrill-only `answer`; Q30 `gap_with_adjacent` with the Merrill
    gap and GWIM adjacent; Q24 `gap_with_adjacent` naming where the comparison is invalid; Q8
    each firm's own terms, custody vs affiliation kept apart inside the grid; Q21 two halves
    (estimates with source and vintage; each firm's actions) kept apart.

## Risks / unsure
- Rule 3's strategy-question parts and rule 1's per-dimension gaps add gaps to answers that
  passed in R1 (Q1, Q4, Q5, Q18, Q26 are not in R2). Wording keeps them additive (a gap, not a
  new behavior), but only #121's R3 shows it. Q18 ("where is the industry heading") falls under
  rule 2 and is not an R2 sentinel. Rule 2 groups by position and keeps each claim attributed,
  but it does not restate Q18's labelling rubric (round-2 review), so whether Q18 keeps its R1
  labelling under the new grouping is shown only by R3; flagged to #121 as an R3 risk.
- Rule 4's two branches can conflict (Q24: inputs disclosed for some firms). The rule decides by
  "most of the firms asked about" for a quantity and keeps a wider unit adjacent; Q24 in R2 is the
  check.
- Q12 and Q20 depend on retrieval (#203) as much as on the prompt; the prompt only makes the
  missing part a named gap.
- Probe answers are one sample each; a pass does not prove R2. They catch a rule the model
  ignores or misreads before the one R2 run is spent.
- Longer answers cost more output tokens per call (cap 8000); no change in call count.

## Progress log
- 2026-11-18 00:45 - plan written on `tl/204-prompt-v3` (from origin/main a886741) in
  `wt-204`; DB `cee` = `corpus-2026-11-17` (sync check up to date); R1 pack and raw outputs read;
  probe questions P1-P4 picked from mock retrieval (0 calls). 0 real calls so far.
- 2026-11-18 01:00 - plan review round 1 (CHANGES REQUESTED, #204 comment 6971295493). Fixed:
  (1) rule 3's strategy clause reworded in general terms (headwinds or risks the firm itself
  names), with no frames/priorities/pressure/concedes chain; the leak test lower-cases and strips
  punctuation before 6-word runs; new acceptance line that the test catches the old rule-3 text;
  (2) rule 1's four-item default dimension list dropped (dimensions from the question's terms and
  what the evidence covers for at least one firm); hand check of every rule against the
  `passes_if` of all linked and sentinel questions (and Q18) for paraphrase, in step 1 and
  acceptance. Non-blocking 1-5 taken: home-firm clause reworded ("the home firm's figures on the
  same dimension, from its own filings"); a rule-2 labelling clause was added here and removed
  in round 2 (it restated Q18's `passes_if`); probes noted as template-adjacent (P1~Q7, P2~Q18, P3~Q25, P4~Q20), and a
  revision must pass the leak test and the hand check; "Part of #204" if verify has not run by PR
  time; "(Q30 trap unchanged)" marked as a plan note, never prompt text.
- 2026-11-18 01:15 - plan review round 2 (CHANGES REQUESTED, #204 comment 6971351346). Fixed:
  rule 2's labelling clause dropped (it restated Q18's `passes_if` list and phrase); rule 2 keeps
  "keep firm statements, research and trade press attributed", now with "saying whose statement
  each claim is"; Risks bullet and the 01:00 line updated, Q18 still named as an R3 risk.
  Non-blocking 1 taken (Risks: "rule 1's per-dimension gaps"). Leak check run before pushing
  (reviewer's `scratchpad\leak.py`, rules 1-4 from this plan, without the rule-4 plan note, vs
  all 30 `passes_if`, lower-case, punctuation stripped): 6-word runs 0, 5-word 0, 4-word one
  (Q20 "source sample and date", generic evidence practice the issue asks for, kept). Control:
  the old 6976a04 rule-3 clause vs Q3 gives 7 six-word runs, so the check catches it.
  Hand check for paraphrase, every rule against all 30 `passes_if`:
  - Rule 1 vs Q7: same dimensions for every firm, a gap per empty cell, no filled cell. This is
    the issue's own grid goal; Q7's four dimensions are not named. Kept. Vs Q22 ("never quietly
    substituted with a near-neighbour metric"): "never fill a cell with ... an adjacent figure"
    repeats v2's "Never present a substitute ... as the thing asked about". Kept. Vs Q9 ("says
    plainly where a firm does not disclose"): v2 already says it. Kept.
  - Rule 1 vs Q8 (seen and kept): "each firm's cell in its own terms (do not force one firm's
    business model onto another)" is close to Q8's "each firm's own language ... rather than
    flattening two different business models". Kept because it is a general principle, not a
    rubric list; v2 already had "Use each firm's own terms ... do not merge two business models
    into one statement"; and Q8 is a sentinel the plan wants unchanged inside the new grid.
  - Rule 2 vs Q16: grouped by position, attributed and dated, no forecast of its own. This is the
    issue's goal 2 itself (accepted in round 1). Kept. Vs Q20 ("two surveys that disagree"):
    generic, accepted in round 1. Kept. Vs Q18: no category list, no "for what it is". Vs Q10,
    Q17, Q21, Q26: no overlap.
  - Rule 3 vs Q3: one general example ("headwinds or risks the firm itself names"), not Q3's
    chain. Vs Q12: "the home firm's figures on the same dimension, from its own filings" is the
    general comparison principle (round-1 non-blocking 1). Kept. Vs Q1, Q2, Q4, Q19, Q21: no item
    lists restated (Q2's pitch list, Q4's pipeline/headcount/sourcing list, Q19's cohort/competitor
    pair are not in any rule).
  - Rule 4 vs Q25: "report what is disclosed as claims, each firm's missing disclosure as a gap"
    is the issue's goal 4 wording; Q25's "far less than people assume" and trade-press clause are
    not in it. Kept. Vs Q20: "source, sample and date" (above). Vs Q24, Q28, Q29, Q30: no new
    overlap; the wider-unit sentence repeats v2's GWIM/substitute rule.
  - Wording edit (ranges gap names the firm) vs Q25/Q29: standard wording only. No other
    question touched.
