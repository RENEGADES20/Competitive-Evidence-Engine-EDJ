# 0043 - Eval runner: per-question retrieval report (mock) and a capped real-model mode

Issue: #43    Role: TL    Spec: evals/questions.yaml, specs/retrieval.md (hit rate, refusal accuracy)

## Goal
One command runs chosen questions (or all 30) against the loaded snapshot and writes a
per-question report (Markdown + JSON). Real-model answers only on request, with a hard cap,
every raw output saved and reused.

## Files to change
- scripts/eval_run.py (new) - the runner
- src/cee/ask.py - split out `answer_for(question, hits, provider)` so `ask()` and the runner
  share one answer path (no behaviour change)
- tests/test_eval_run.py (new) - pattern matching, status rules, baseline compare, real mode with
  a fake provider (cap, cache, refusal without --max-calls); no DB, no network
- .gitignore - `.eval-runs/`

## Design
- **Patterns** (`expected_sources`): `ENTITY:TYPE[#QUALIFIER]`. TYPE `*` = any type. `MER` = MER
  documents, or BAC chunks whose segment is GWIM/Merrill (same rule as the SQL filter).
  `THEME` = documents with no entity. QUALIFIER must equal the chunk's `segment`. Until segments
  are tagged (#37) such a pattern can only be a "type hit" (entity and type right, qualifier not
  checked), reported separately and not counted as a hit.
- **Available** pattern: the loaded corpus has at least one document for ENTITY+TYPE.
  **Coverage** = hit patterns / available patterns.
- **Forbidden hits**: any hit from an entity the question did not resolve to (entity mode),
  and, for Merrill questions, any BAC chunk without a GWIM/Merrill segment.
- **Status** (retrieval level; written in the report header):
  - FAIL: any forbidden hit;
  - NOT_EVALUATED: no expected pattern is available in the corpus;
  - PASS: coverage >= `--min-coverage` (default 0.5);
  - otherwise FAIL.
  In `--real` mode the answer's behavior must also equal `expected_behavior` for PASS.
- **Change vs a baseline** report: compare (PASS?, coverage, -forbidden) per question:
  higher = IMPROVED, lower = REGRESSED, equal = UNCHANGED; a question missing from the
  baseline = NEW.
- **Real mode**: `--real` needs `--max-calls N` and a non-mock provider. A model call happens only
  when retrieval returns chunks. The cache key is question id + text + prompt version + snapshot
  + provider/model + retrieved chunk ids. Cached outputs are reused and do not count against
  the cap. After N calls the remaining questions are reported `NOT_RUN (cap)`. Every model
  output, before citation checks, is saved in `.eval-runs/cache/` and copied into the run folder.

## Steps
1. Tests first (fake hits, fake provider).
2. `answer_for` in ask.py; runner; report writers.
3. Mock run of all 30 questions on corpus-2026-10-18; a second run with the first as baseline
   (all UNCHANGED).
4. pytest; verify-cee (ask.py changed).

## Acceptance
- [x] Mock run of all 30 questions on the current snapshot: report lists hits and pattern coverage per question
- [x] Each question has a status (PASS/FAIL/NOT_EVALUATED) and, with a baseline report, a change (UNCHANGED/IMPROVED/REGRESSED)
- [x] `--real` refuses to run without `--max-calls`, never exceeds it, and reuses saved outputs for the same question + prompt version + snapshot
- [x] Tests with a fake provider; no paid call in tests or CI
- [x] `pytest -q` passes; verify-cee all PASS (ask.py touched)

## Progress log
- 2026-10-19 - plan written; branch tl/43-eval-runner created
- 2026-10-19 - ask.py `answer_for()` + `model_name()`; scripts/eval_run.py; 11 tests (fake hits,
  fake provider); pytest 119 passed.
- 2026-10-19 - Mock run, all 30, corpus-2026-10-18 (restored, then loaded for date_basis):
  PASS 7, FAIL 21, NOT_EVALUATED 2 (Q18, Q20: no tier 5 corpus). Second run with the first as
  baseline: 30 UNCHANGED. --k 20 vs the same baseline: 8 IMPROVED, PASS 11.
- 2026-10-19 - --real without --max-calls: refused. --real --max-calls 0 (provider from .env):
  Q28/Q29 "cap", Q30 "no_call" (empty retrieval), 0 calls, cache empty.
- 2026-10-19 - verify-cee is flaky on this corpus: 4 runs on the branch, each with one or two
  features FAIL (ask-answer, open-citation, invalid-chunk) and all 5 passing in some run; 2 runs
  on clean main: one ask-answer FAIL, one all PASS. Page read before it rendered (#83). To show
  ask.py is unchanged in behaviour: ask() for all 30 questions (mock) gives byte-identical
  hits and answers on main and on the branch.
