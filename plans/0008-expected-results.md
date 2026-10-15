# 0008 - Expected retrieval results for 5 Tier-1 questions

Issue: #8    Role: S1    Spec: specs/retrieval.md

## Goal
For Q1, Q4, Q11, Q22 and Q26, write down by hand which documents and sections retrieval
should return, and which it must not return, so later retrieval changes can be scored
against it ("hit rate vs expected sources", specs/retrieval.md).

## Files to change
- `evals/expected_results.md` (new) - one section per question: expected documents and
  sections, must-not-return list, corpus status, what retrieval returns today.
- `plans/0008-expected-results.md` (new) - this plan.
- Not changed: `evals/questions.yaml` (append-only, owned by C1). `docs/PROGRESS.md` is
  filled by the bot from the PR's `## Progress line` (CLAUDE.md).

## Steps
1. One block per question with target documents, named by the doc_id conventions in
   `specs/filings.md` (`<ENTITY>-<FORM>-<PERIOD>`) and `specs/transcripts-ir.md`
   (`MS-TR-2025Q2`, `...-DECK-...`, `...-PR-YYYY-MM-DD-NN`), following `expected_sources`.
2. Name the sections that must come back.
3. Must-not-return list (trap Q4: BAC chunks without a GWIM/Merrill segment; Q26: older
   than 90 days).
4. Check against the real corpus (corpus-2026-09-30): which expected chunks exist, and what
   `resolve()` + `search()` return today.
5. Mark documents not yet loaded; section names and dates not checked -> `TODO-verify`.

## Acceptance
- [x] All 5 questions (Q1, Q4, Q11, Q22, Q26) list concrete expected documents.
- [x] Trap included: Q4, with a must-not-return list for BAC chunks without GWIM/Merrill.
- [x] Each document marked in corpus / not loaded; EDJ entries checked with real queries.
- [x] No invented entity facts; unknowns marked `TODO-verify`.
- [x] `git diff main -- evals/questions.yaml` -> empty.
- [x] `.venv/bin/python -m pytest -q` -> all pass (no code changed).

## Progress log
- 2026-10-01 - plan written and approved.
- 2026-10-15 - branch s1/8-expected-results from main (47 commits newer). Rules changed:
  PROGRESS.md now filled by bot from PR "Progress line"; verify-cee only for src/config/db.
- 2026-10-15 - Corpus still one document (EDJ-10K-2025, 335 chunks). Found EDJ targets:
  #130 (highlights table: NNA + advisor count, footnote (2) defines NNA), #131, #148, #29.
- 2026-10-15 - Surprise: EDJ-10K-2025 gives "Financial advisors (actual)" but no
  include/exclude definition. Recorded as TODO-verify for C1 (Q11), not guessed.
- 2026-10-15 - Ran today's retrieval: Q11/Q22 resolve to no entities ("each of the five"
  is not mapped) and Q11 misses #130; Q26 has no time window in Query. Logged as findings
  for follow-up retrieval issues, not fixed here (out of scope).
