# 0292 - Reduce prompt v7: direct answer plus short cited synthesis

Issue: #292    Role: TL    Spec: specs/answer-citations.md, ADR-021    Design: docs/results/w13-reduce-synthesis.md (written in step 8)

## Goal
Outside window questions, the answer paragraph reads as a direct answer plus a short cited synthesis instead of one
claim per evidence card. New reduce prompt **v7** behind `REDUCE_PROMPT` (name `v6` is taken by #284's removed code).
It becomes the default only if the acceptance below passes.

## Rules of v7 (prompt) and how code picks the form
- **Form, decided by code** (`reduce.list_form(m, query)`, also read by `ask_page.list_form`): **list** when the question
  has its own window (`own_window(query)`: Q26, Q27) or every aspect is `recency`; else **synthesis**. Under v5.2 / v5.3
  the rule stays #291's (own window or any recency aspect), so those versions are unchanged. Why not #291's rule under v7:
  15/30 #272 plans have a recency aspect (Q5 among them), so Q5 would never reach v7.
- **List form under v7** = v5.2 exactly: v5.2 system prompt, message, mock and version label `v5.2`, so its cache keys and
  outputs stand (Q26, Q27 byte-identical).
- **Synthesis form** (system prompt v7; matrix message without the recency why-line notes and `context` / `related` lines):
  1. Sentence 1 answers the question directly (the asked firms, the headline fact or verdict), cited.
  2. Then 2-4 synthesis sentences: a comparison across firms, a pattern, a tension or a gap between items. Never one
     sentence per item restating it; a sentence may cite several cells (one claim = one sentence).
  3. Every sentence cites matrix chunk ids. Every cell that holds a fact is cited by at least one sentence whose
     part_id is that cell or its aspect; more than 4 synthesis sentences only to meet this.
  4. Asked figures are never dropped: a series / metric aspect states each firm's value and period (one sentence per
     firm at most); each firm keeps its own terms (no merged business models, Q8).
  5. Kept from v5.2: dating, attribution, no outside facts or computing, one comparison claim per comparison aspect,
     the computation claim per "computation" line, adjacent items unchanged, standard wording. No why-lines.
  6. part_id: the cell, or the aspect for a sentence spanning firms (sentence 1 spanning aspects: the first aspect).

## Files to change
- `src/cee/answer/prompt.py` - `SYSTEM_PROMPT_V7`, `REDUCE_PROMPTS["v7"]`; v5.2 / v5.3 text untouched.
- `src/cee/config.py` - `REDUCE_PROMPTS` accepts `v7` (default switched here only per the rule below).
- `src/cee/answer/reduce.py` - `list_form`; `prompt_version(m, query)` / `system_prompt(m, query)` per form;
  `reduce_message` synthesis variant; mock v7; the check changes below.
- `src/cee/answer/validate.py` - `part_coverage`: an aspect-id claim covers each cell of that aspect it cites.
- `src/cee/answer/runcache.py`, `scripts/eval_run.py` - reduce key and record use the per-question version.
- `src/cee/app/views/ask_page.py` - `list_form` calls `reduce.list_form` (no layout change).
- `tests/test_reduce_synthesis.py` (new); `specs/answer-citations.md` (#292 block); `docs/DECISIONS.md` (ADR-021
  rule 5 amendment: why-lines in list-form answers only); `.claude/skills/verify-cee/features/ask-layout.md` +
  `scripts/verify_cee.py` (form rule under v7); results doc + `docs/results/w13-reduce-synthesis/` (run-synthesis
  `.ps1` + `.sh`, raw copies). Schema unchanged: `reduce.part_ids` already offers aspect ids (verified).

## Checks: what changes, what stays
- **Change (synthesis form only).** Coverage: a claim with an aspect part_id counts for every holding cell of that aspect
  whose counting-item or derivation-input chunk ids it cites. `check_computability`: an aspect-id claim citing all
  inputs and population chunks counts; a code claim goes after the last claim of that aspect (cell or aspect id).
  `dedupe_claims`: sentence 1 is never removed. `check_adjacent`: an aspect-id claim citing only chunks of
  different-quantity / proxy cells gets `claim_from_adjacent`. Why-lines: `clean_why_lines` removes any
  (`why_line_removed`), `check_why_lines` / `order_newest_first` do not run.
- **Unchanged.** Citation, `outside_matrix`, number, date, normative / hand-off, `check_comparisons` (already accepts the
  aspect id), `place_gaps` / `contradicts` (already read aspect ids), caveats, streaming checks; all of list form.

## Mock reduce v7 (0 calls, deterministic)
Sentence 1: the question's subject + the first holding cell's first counting item, part_id its aspect. Then per
non-proxy, non-comparison aspect one sentence citing the first counting item of every holding cell (firm-prefixed
item texts joined), part_id the aspect, skipped when its chunk set equals sentence 1's; derived cells, comparison
claims and adjacent items as v5.2.

## Steps
1. Prompt, config, `list_form`, per-form version; v5.2 default request byte-identical (test asserts prompt + schema).
2. Synthesis message, mock v7, check changes; tests (coverage across cells, computability by aspect id, sentence 1
   kept, Q26/Q27-style list form = v5.2, `ask_page.list_form` agrees).
3. Mock eval fts Q1-Q30 (rule plans, and #272 plans via `--reuse-plans`), `REDUCE_PROMPT=v5.2` vs `v7` and v5.2 vs
   main: v5.2 identical to main; under v7 list-form questions byte-identical, the rest no new flag kind and no higher
   part_gap / comparison_missing / outside_matrix / number_not_found / no_citation count.
4. verify-cee on mock with `REDUCE_PROMPT=v7`: ask-answer, ask-layout (paragraph for Q5, list for Q26), ask-progress.
5. Count phase (0 calls), then the paid run below. 6. Results doc, spec, ADR line, default per rule. 7. PR.

## Paid calls
- **Why the mock cannot show it:** whether a model writes a direct first sentence and synthesis that stays cited.
- **Setup:** deepseek, current defaults (`deepseek-v4-pro` `/beta`, effort plan off / map low / reduce low, stream on,
  MAP_PREFIX off), fts, as-of 2026-11-17, `corpus-2026-11-19` (local DB up to date, checked 2026-11-23), off-peak UTC.
- **Questions:** Q5, Q8, Q22, Q24, one full answer flow each, `REDUCE_PROMPT=v7`. Full flow per ADR-021 rule 7:
  Q5 6 (plan 1, map 4, reduce 1), Q8 6, Q22 12 (map 10), Q24 22 (map 20) = 46 calls, 0 re-maps in #272.
- **Reuse:** cache = copy of `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a` into `ev292\cache`. Since gate 1c9aca2 (#284's
  count reused all 454 map and 30 plan records) only reduce / prompt / config code changed, so plan and map keys match:
  **expected new calls 4** (the v7 reduces), 42 reused. The count phase must show exactly 4 new keys; if more, the
  reason goes in the Progress log and `--max-calls` is raised to the count only if the estimate stays under CNY 30.
- **v5.2 comparison:** saved records in `docs/results/w12-latency/b-fts/raw/` (#272 test B, same settings, 2026-11-21
  off-peak), `Q5|Q8|Q22|Q24-reduce-*.json`. v5.2 is not called again.
- **Cost (balance CNY 97):** v5.2's four reduces were 56.8k input / 74.6k output tokens = $0.19 off-peak. v7 at 0.7-1.5x
  output: $0.13-0.30 off-peak, at most $0.60 peak (about CNY 4). Worst case, all 46 calls new: $1.21 off-peak, $2.42 peak
  (about CNY 18). Run cap `--max-calls 4`.
- **Evidence:** raw records (question, version, model, usage, reasoning, output) in `ev292\` and committed copies in
  `docs/results/w13-reduce-synthesis/`.

## Acceptance
- [ ] pytest green (CI `gh pr checks`).
- [ ] Mock eval (step 3) as stated; Q26, Q27 byte-identical to v5.2.
- [ ] Real: 4 calls; per question in the results doc, v5.2 vs v7 text, output / reasoning tokens, cost, wall time and
      tokens/s. Every shown sentence cited (no_citation 0, outside_matrix 0); sentence 1 answers the question;
      no item-by-item restatement (sentences <= 5 + comparison + computation + per-firm figure sentences, and each read).
- [ ] verify-cee on mock (step 4): answer paragraph above evidence, footnotes resolve.
- [ ] **Default rule:** v7 becomes the default only if every real item above passes on all four and no question has
      more part_gap / comparison_missing / number_not_found than its v5.2 record and none is invalid or cut. Else it
      stays behind `REDUCE_PROMPT=v7` and the results doc says why. Cost is reported, not a gate. If switched, the PR
      proposes the 30-question scored run (Gate 3, TL go-ahead); it is not part of #292.

## Progress log
- 2026-11-23 17:30 - plan written; local DB at corpus-2026-11-19; plan review needed (paid calls, ADR-021 rule 5 line).
