# 0292 - Reduce prompt v7 / v8: direct answer plus short cited synthesis

Issue: #292    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: docs/results/w13-reduce-synthesis.md

## Goal
Outside window questions, the answer reads as a direct answer plus a short cited synthesis instead of one claim per
evidence card. Reduce prompt **v7** (done: not adopted, results doc), then **v8** (below), behind `REDUCE_PROMPT`.

## Form rule (one helper)
`reduce.list_form(aspects, query, version)`, read by the reduce, the streamed answer and the final answer on the Ask
page. **List**: the question's own window, or (v5.2 / v5.3, #291) any recency aspect, or (v7 / v8) every aspect
recency; then v5.2 exactly (prompt, message, mock, label, cache key: Q26, Q27). Else **synthesis**. ADR-021 rule 5
amendment (why-lines in list-form answers only): approved by the user 2026-11-23.

## v7 (done)
Built, checked and run (4 calls); not adopted. Files, checks and results: `docs/results/w13-reduce-synthesis.md`.

## v8 amendment (TL decision 2026-11-23: "time too long; the answer need not include or list everything")
- **Prompt v8** (synthesis form; list form stays v5.2): claim 1 answers the question directly and MUST cite the items
  it rests on; at most 5 sentences in total; each short (aim <= 35 words), no list of items inside a sentence; pick
  the most important evidence, not all: the evidence list under the answer (#291) shows every item. Comparison
  aspects keep their one comparison sentence (within the 5); a derived figure, if stated, cites both inputs;
  adjacent items, gaps and standard wording as v7; no why-lines. The message keeps each cell's "computation (code)"
  line as context (the model may state the verdict in a sentence), but the prompt does not ask for a computation
  claim: code writes it (next bullet).
- **Code (v8 only; v5.2 / v7 unchanged):** `P.SYNTHESIS_VERSIONS` += v8 with a `brief` flag. In the brief synthesis
  form a holding cell the answer does not cite is not a `part_gap` (`part_coverage` state `evidence_list`); cells
  with no fact and code gaps still show their gaps. Citation, number, date, normative, outside_matrix, comparison
  (`comparison_missing`) and caveat checks unchanged. Mock v8: claim 1 + one short sentence per aspect from its
  first holding item, at most 5 claims.
- **Computability statements, kept (ADR-021 #247 commitment, TL D5):** under v8 code writes, for every derivation
  proposal with cited inputs, the existing `COMPUTED` / `NOT_COMPUTED` statement (formula or why not, both inputs and
  every population source cited and quoted) into a new code-owned list `Answer.computations` (same item shape as a
  claim), not into `answer.claims`, so it is outside the 5 sentences and the 45-word rule. The citation, number and
  date checks run on it like on a claim. The Ask page draws it as a "Computability" box next to the caveats, with
  footnotes into the evidence list (#291 mapping; a cited chunk without a card gets a SOURCE card). A model sentence
  that already states the verdict does not remove the box. v5.2 / v7 keep `check_computability` as today.
- **Files:** `prompt.py` (`SYSTEM_PROMPT_V8`), `config.py`, `schema.py` (`Answer.computations`), `reduce.py`,
  `validate.py`, `ask_page.py` (+ `components.py` if the box needs a helper) for the Computability box, tests; spec:
  the #292 block and the "Computation claims" section (`specs/answer-citations.md`, v8: a code box, not a claim);
  verify-cee `ask-layout.md` + `scripts/verify_cee.py` (box step); results doc; `run-synthesis.ps1` / `.sh`
  (`-EffortReduce` / `EFFORT_REDUCE`); `cmp_mock.py` / `analyze.py` (count `computations`).
- **Checks before calls:** pytest, including: every holding cell the v8 answer does not cite has its items in the #291
  evidence list (`ask_page.evidence_cards` lines); the Q24-shaped matrix under v8 gives a `NOT_COMPUTED` (or
  `COMPUTED`) entry in `computations` citing both inputs and the population sources. Mock fts Q1-Q30 (rule + #272
  plans): v5.2 = main, v8 list-form identical, no new flag kind, part_gap / comparison_missing / outside_matrix /
  number_not_found / no_citation not above v5.2, and Q24 (#272 plans) shows its computability entries with their
  population sources wherever v5.2 has `code_computability` or a computation claim. verify-cee on mock with
  `REDUCE_PROMPT=v8` (ask-answer, ask-layout incl. the box on Q24 when present, ask-progress).
- **Paid calls (8):** Q5, Q8, Q22, Q24 with `REDUCE_PROMPT=v8`, one reduce each at the current reduce effort
  (`low`, cap 128000) and one each at `DEEPSEEK_EFFORT_REDUCE=off` (thinking off, streamed cap 64000). The effort is
  in the request version, so 4 new keys per run. Two runs (`g-v8-low`, `g-v8-off`), each after its own count phase
  (0 calls) that must show exactly 4 new reduce keys and 42 reused plan / map records, else stop and report;
  `--max-calls 4` each, 8 in total. Same settings, cache (`ev292\cache`) and gate rule as v7, off-peak.
- **Cost:** low at most v7's $0.221; off is about input only (57k tokens, about $0.04) plus a short answer; total
  <= $0.30 off-peak, <= $0.60 peak (about CNY 4; balance about CNY 95 after v7).
- **Pass rule (per question, per effort):** sentence 1 cited and answers the question; <= 5 sentences; no list
  sentence (none over 45 words, none with 3 or more items joined by ";" or listing 4 or more figures); no new flag
  kind against v5.2; part_gap, comparison_missing and number_not_found not above v5.2; not invalid or cut. For a
  question with a derivation proposal or a comparison aspect (Q24 certainly; Q8 has a comparison aspect): the
  computability / invalidity statement reaches the user (the box, or the comparison sentence) with both inputs and
  the population sources cited, and Q24's answer says where the comparison is invalid and why (cited).
  Reported next to v5.2 and v7: wall time, output and reasoning tokens, cost, tokens/s.
- **Default:** v8 becomes the default if all four pass at `low`. Effort off: if all four also pass at `off`, the PR
  proposes reduce effort off for synthesis-form calls as a TL decision (effort is a global stage setting, and a
  switch would also change list-form v5.2 calls, which this run does not test); not switched in #292. Else v8 stays
  behind the flag and the results doc says why. If the default switches, the PR proposes the 30-question run (Gate 3).

## Acceptance
- [x] v7: pytest, mock eval (Q26, Q27 byte-identical), 4 real calls compared, verify-cee on mock, default rule applied.
- [ ] v8: pytest green (CI), mock checks above, verify-cee on mock with v8, 8 real calls compared, pass rule applied.

## Progress log
- 2026-11-23 17:30 - plan written; local DB at corpus-2026-11-19.
- 2026-11-23 - plan approved (issue comment 7117074418); notes applied (trim, one form helper, PR to the TL).
- 2026-11-23 - code + 10 tests (6d821a9). Mock rule and #272 plans: v5.2 = main 30/30; v7: Q26, Q27 identical, worse 0.
  verify-cee v7: part-gap step fixed for aspect-id sentences (787514a); then PASS.
- 2026-11-23 23:43 UTC - count at gate 8e5172c: 42 reused, 4 new reduce keys (= plan).
- 2026-11-23 23:50-23:59 UTC - paid run g-v7: 4 calls, $0.221 off-peak. Default rule fails on Q5, Q22, Q24; v7 stays
  behind the flag. PR #294 opened, CI green.
- 2026-11-23 - TL decision: v8 on the same branch (shorter, no full coverage, effort off tested); ADR-021 rule 5
  amendment approved by the user. v8 amendment written; no v8 call before the plan review.
- 2026-11-23 - plan review CHANGES REQUESTED (issue #292 comment 7118136034): computability statements kept as a
  code box (`Answer.computations`), Q24 pass item, false evidence-list text removed, spec section and tests added,
  v7 block shortened to a link.
- 2026-11-24 - v8 amendment approved (issue #292 comment 7118166000). v8 code + 7 tests (1718230); pytest 1217 pass.
  Mock rule and #272 plans: v5.2 = main 30/30; v8: Q26, Q27 identical, worse 0. No mock matrix (and none of the four
  real #272 matrices) has a derivation proposal, so the Computability box is proven by tests, not drivable on mock.
  verify-cee v8 and default: ask-answer, ask-layout, ask-progress PASS.
- 2026-11-24 00:50 UTC - count at gate 1718230: low 42 reused + 4 new; off 42 reused + 4 new (= plan). Paid runs held
  until the 04:00 UTC off-peak window (peak 01:00-04:00).
