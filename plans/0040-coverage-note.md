# 0040 - Coverage note on every answer

Issue: #40    Role: S2    Spec: specs/answer-citations.md (also specs/ui.md, verify-cee)

## Goal
Every answer, whatever its behavior, carries a code-built coverage note saying which firms were
searched and which document types and periods the retrieved passages come from. The app shows
it, always visible. The note describes only this question's retrieved passages, not the whole
corpus (decided with S2; corpus-wide holdings overlap #51).

## Files to change
- `src/cee/answer/schema.py` - code-owned `Answer.coverage_note`; the model's output schema is unchanged
- `src/cee/answer/validate.py` - `coverage_note(query, hits)`
- `src/cee/ask.py` (TL) - call it in `answer_for` on both the hits and the no-hits path; trace line
- `src/cee/app/components.py`, `src/cee/app/views/ask_page.py` (U1) - an always-visible coverage box
- `.claude/skills/verify-cee/features/ask-answer.md`, `scripts/verify_cee.py` - ask-answer checks the note
- `tests/test_validate.py` - fixture tests for every behavior

## Steps
1. Tests first: answer, boundary, gap and refuse all carry a note naming firms, document types and
   period; a Merrill question with BAC GWIM hits.
2. Schema field and `coverage_note()`.
3. Wire into `ask.answer_for` (trace text unchanged; see Progress log).
4. Coverage box on the Ask page, after caveats and gaps.
5. Recipe and driver; run pytest, smoke, `verify_cee.py run`.

## Acceptance
- [x] Q24, Q30: every behavior carries a coverage note naming entities, document types and period covered
- [x] The app shows caveats and the note, never collapsed; `verify_cee.py run ask-answer` checks the note
- [x] `pytest -q` passes; still one LLM call per answer (call logic untouched)
- [x] `verify_cee.py run` all PASS; mock only, 0 real calls
- Out of scope: number check (#52), registry-based gaps (#51), prompt changes.

## Progress log
- 2026-10-28 - plan approved by S2: note covers retrieved passages only
- 2026-10-28 16:45 - steps 1-4 done: `coverage_note()` in validate.py, `Answer.coverage_note`, wired into both `answer_for` paths, coverage box on the Ask page. A trace-text change ("coverage note" on the caveats line) broke two exact-string tests in tests/test_ask_progress.py; reverted it instead of editing those tests. pytest 214 passed
- 2026-10-28 16:52 - verify-cee (mock, 0 real calls): all 7 features PASS, ask-answer reads "Coverage: searched Edward Jones. 12 passages from 5 documents: EDJ 10-K (2025-12-31); EDJ 10-Q (2025-06-27 to 2026-06-26)."; gap-path page shows "Coverage: searched all documents (no covered firm named). No documents in the corpus for LPL Financial." open-citation needs raw PDFs: run with CORPUS_SHARE_PATH pointed at the Box folder for that run only. Smoke PASS on corpus-2026-10-27. Evidence: .verify-runs/20261028-165224-6a29065
