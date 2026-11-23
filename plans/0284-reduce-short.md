# 0284 - Shorter reduce output: the model picks matrix items by id, code renders them

Issue: #284    Role: TL    Spec: specs/answer-citations.md (reduce), specs/ui.md (streamed claims), ADR-021    Design: below; measurements in `docs/results/w13-reduce-short.md` (step 8)

## Goal
A new reduce prompt `v6` (behind `REDUCE_PROMPT`, effort stays `low`) in which a claim names matrix items by id and code
writes its text (source, date, item text, scope) from the matrix. Reduce output tokens p50 <= 11,187 (50% of #272's
22,375), reduce wall p50 <= 70 s, adjudicated >= 24/30, with 0 uncited claims and 0 figures outside the matrix.

## Design (fixed before any call; baseline = #272 test B fts records, 0 calls)
- **Why refs.** #272 reduce p50: 22,375 output tokens = 13,302 reasoning + 6,260 answer. The reasoning drafts each claim's
  full sentence (Q4: date phrase + the map item's text + scope, nearly word for word). The item text is already in the
  matrix, so code can write it; the model keeps choice, order, grouping, comparisons and why-lines.
  **Main risk:** answer tokens are only 28% of the output, so the 50% target needs the reasoning to shrink too (by
  about a third). No zero-call way to measure that; the first 6 calls show it (Paid calls).
- **Schema v6** (strict, enums from the matrix): claim / adjacent = `{part_id, items: [ref], text, chunk_ids, why}`
  (+ `differs_because` on adjacent); gaps unchanged. `ref` = `<cell id>/<n>` (item n as numbered in the message) or
  `<cell id>/derived`. `text` is empty for a plain item claim; it carries the model's words only for a comparison
  claim, a computation claim, a position label, or an item code may not render (below). `chunk_ids` holds only extra
  ids (why-line background, comparison inputs, a text claim's citations). `why` = one short sentence, recency / window
  items only. Ref enum counts toward the enum limits; over them it falls back to a plain string (as chunk ids do).
- **Code rendering** (`render_output`, before `to_answer`, so every check after it is unchanged): claim text =
  `<Firm>: ` (multi-firm, `_firm_prefix`) + `<text>: ` (when given) + per ref `Per the <source label> (<date>): <item
  text>` + ` (scope: <scope>)` when the scope is not in the text + ` Why it might matter: <why>` when given; chunk ids
  = the refs' chunk ids + `chunk_ids`. Derived ref -> the cell's formula text (as `mock_reduce`), its input ids.
  Quotes are not rendered (no new `quote_not_found` path). An unknown ref is dropped with flag `unknown_ref`; a claim
  left with no ref and no ids takes today's uncited path (`no_citation`, `move_uncited_cells` -> gap; rule 1).
- **Items code does not render:** an item flagged `figure not found in its passage` has no ref (listed "no ref"); the
  model may state it in `text` without the figure, as v5.2 asks. Its figure can then reach the answer only through
  model text, which the number check covers as today.
- **Prompt v6** = v5.2's rules, with "What goes where" and "Shape" restated for refs, plus: "write no figure, date or
  quote yourself in a claim that has items; code adds them". Message: items listed as `item a1.MER/3: ...` instead of
  `item 3`; everything else as v5.2. v5.2 and v5.3 unchanged (their keys and records stand).
- **Streaming:** `EarlyClaims` renders each streamed claim with the same function before `check_item`; mock v6 streams
  refs. **Mock v6:** `mock_reduce` output expressed as refs (first counting item per holding cell, derived ref,
  comparison as text), so the mock exercises rendering with the same chunk ids as v5.2.
- **Options not chosen** (written up in the results doc): v5.3's length rule at `low` - cuts about 15% (the repeats,
  `w12-reduce.md`), cannot reach 50%, and the model still copies every figure; plan step + parallel per-part writers -
  1 + parts calls, the matrix sent per part, comparisons and newest-first span parts, more streaming changes. Either
  can follow if v6 misses the speed target.
- **Adoption rule (fixed now):** `REDUCE_PROMPT` default becomes `v6` only if output p50 <= 11,187, wall p50 <= 70 s,
  0 cut / invalid, adjudicated >= 24/30, tier 1 >= 12/18 (#272 adjudicated), and the rule checks below hold. Otherwise
  the default stays v5.2 and the doc records the finding. A miss is not re-rolled.

## Files to change
- `src/cee/answer/reduce.py` - v6 message lines, schema, `render_output`, mock v6, `EarlyClaims` render. `prompt.py` - `SYSTEM_PROMPT_V6`.
- `src/cee/config.py` (`REDUCE_PROMPT` choice), `scripts/eval_run.py` (raw v6 output + rendered output in the record).
- Tests (fake clients only): `tests/test_reduce*.py`, `tests/test_eval_run.py`, the Ask streaming tests.
- `specs/answer-citations.md`, `.env.example`, `docs/RUN.md` (both OS blocks); verify-cee recipe + `scripts/verify_cee.py` only if a check reads claim text.
- `docs/results/w13-reduce-short.md` + `docs/results/w13-reduce-short/` (`run-short.ps1` / `.sh` copied from `w13-prefix-cache/run-prefix.*` with `-ReducePrompt v6`, checks, tables, verdicts).

## Steps
1. Mock baseline from clean `main` (0 calls): mock Q1-Q30 fts, rule plans and #272 plans.
2. Schema, message, prompt, rendering, mock v6; tests: render of a fact / derived / multi-ref / scope claim; unknown
   ref -> `unknown_ref` and the uncited gap path; flagged item has no ref; enum fallback; v5.2 request bytes unchanged.
3. Streaming: rendered early claims, held when a ref is unknown or a check flags; Ask page tests with mock v6.
4. Mock compare: default v5.2 30/30 identical to step 1; `REDUCE_PROMPT=v6` equal in status, behavior, cell labels and
   chunk ids per claim (text differs by design). pytest green.
5. **Render check (0 calls)** on the #272 fts matrices (count phase, cache copy of `ev272\cache-a` in `ev284\cache`,
   reduce hooked to mock v6): 0 `no_citation`, 0 `outside_matrix`, 0 `number_not_found` on rendered claims; ref enum
   fallback per question listed. Count phase: 0 plan / map / re-map calls new, exactly 30 new reduce keys.
6. verify-cee on mock with `REDUCE_PROMPT=v6`: ask-answer, ask-progress, ask-stop-retry, screenshots.
7. Real run (below) from a clean worktree at the gate commit, off-peak.
8. Blind scoring inputs (#272 method), results doc, `/finish-task`. Scoring and adjudication by the coordinator.

## Acceptance
- [ ] pytest green locally and `gh pr checks` green; step 2-3 tests present.
- [ ] Mock compare (step 4) as stated; render check (step 5) all zeros.
- [ ] Real run, fts Q1-Q30, reduce only: output tokens p50 <= 11,187; wall p50 <= 70 s, p90 and max reported; 0 cut;
  first claim on the page p50 reported.
- [ ] Rule checks from the records: 0 shown claims without a citation; 0 `outside_matrix`; `number_not_found` and
  `unknown_ref` counts reported (number_not_found <= #272's).
- [ ] Scoring inputs in `ev284\blind-in-fts\` (dump in 4 parts as #272, `questions.yaml`, `verdict-rule.txt`, hashes);
  adjudicated >= 24/30, tier 1 >= 12/18 (scored by the coordinator) -> adoption rule applied.
- [ ] verify-cee ask-answer, ask-progress, ask-stop-retry PASS (mock, v6), evidence in `ev284\verify\`.

## Paid calls
30 `deepseek-v4-pro` reduce calls (effort `low`, `/beta`), one per question Q1-Q30, fts, every plan / map / re-map
record reused from #272 test B (C1, `PYTHONHASHSEED=0`, as-of 2026-11-17, snapshot corpus-2026-11-19). No re-maps
(the design changes no map). Why the mock cannot show it: output length, reasoning length and answer quality.
Order: Q5, Q10, Q19, Q21, Q24, Q26 first (6 calls); stop and report if any shown claim is uncited or outside the
matrix; else the other 24 (`--max-calls` pinned per stage). Gate 3 go-ahead: TL 2026-11-22. Off-peak (not UTC 01-04,
06-10 Mon-Fri); each call's tier from `cost.py`, $ reported at off-peak like for like with #272. Raw outputs in
`ev284\`. No repeats, no retries.

## Progress log
- 2026-11-23 - plan written on `tl/284-reduce-short` (from main b32d1f2, after #286 merged); worktree `wt-284`.
