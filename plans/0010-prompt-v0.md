# 0010 - Prompt v0 and gap/boundary wording

Issue: #10    Role: S2    Spec: specs/answer-citations.md

## Goal
A versioned first prompt (v0) and fixed standard wording for honest-miss / gap answers
(Q28-Q30) and the normative boundary (Q12, Q19), kept in one module and documented in the spec.

## Files to change
- `src/cee/answer/prompt.py` (new) - `PROMPT_VERSION`, `SYSTEM_PROMPT`, standard wording constants
- `src/cee/answer/llm.py` - import the prompt from `prompt.py`; call logic unchanged (one LLM call)
- `specs/answer-citations.md` - new "Standard wording" section
- `tests/test_prompt.py` (new) - prompt carries the rules and wording; both providers use it
- `docs/PROGRESS.md` - one status line

## Steps
1. Write prompt v0: evidence-only, every claim cites chunk_ids, numbers verbatim from the cited
   chunk, how to pick each behavior, gaps carry `what` + `suggested_source`, adjacent data
   carries `differs_because`, no normative sentence. Caveats stay code-owned (not in the prompt).
2. Standard wording:
   - Q30: "Merrill does not report standalone results." GWIM figures go to `adjacent` with
     differs_because "GWIM includes both Merrill and Bank of America Private Bank; the two have
     different reporting scopes, so GWIM figures are not Merrill's."
   - Q28: "Neither firm discloses advisor attrition on a comparable basis." Net headcount change
     goes to `adjacent` (net change is not attrition).
   - Q29: "Payout grids are not public." Aggregate compensation expense goes to `adjacent`;
     a named `suggested_source`; trade press is indicative, not authoritative.
   - Q12, Q19: evidence first, then: "The evidence above only provides objective context for the
     strategic question asked. Whether or how Edward Jones should act is a judgment for the
     strategy team to make, beyond the scope of this evidence engine."
3. Point `llm.py` at the new module; run pytest.
4. Add `tests/test_prompt.py`.
5. Update the spec and `docs/PROGRESS.md`.
6. Run `verify-cee` (mock) and smoke.

## Acceptance
- [x] Prompt v0 lives in `prompt.py` with a version; Anthropic and OpenAI requests both use it.
- [x] Gap wording for Q28, Q29, Q30 and boundary wording for Q12, Q19 are in the prompt and the spec.
- [x] Wording obeys ground rule 6: the hand-off contains no recommendation.
- [x] `.venv\Scripts\python.exe -m pytest -q` -> all pass.
- [x] `.venv\Scripts\python.exe scripts\verify_cee.py run` -> pass; `-m cee.smoke` -> PASS.
- Out of scope: real-model quality on Q28-Q30 (corpus holds only the EDJ 10-K today);
  code-inserted caveats, code-inserted boundary sentence and the number check (W3+).

## Progress log
- 2026-10-13 - plan written and approved; wording revised per S2 (Q30 differs_because, Q12/Q19 hand-off)
- 2026-10-13 22:45 - steps 1-5 done: prompt.py (v0), llm.py imports it, spec wording table, tests/test_prompt.py, PROGRESS line; pytest 19 passed
- 2026-10-13 22:50 - verify-cee run (mock): all five features PASS (download-document after copying EDJ-10K-2025.htm from Box into data/raw/); smoke PASS. Evidence: .verify-runs/20261013-224846-f9682e3, .verify-runs/20261013-224949-f9682e3
