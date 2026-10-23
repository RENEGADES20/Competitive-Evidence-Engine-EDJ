# 0080 - Ask: progress bar and live step trace

Issue: #80    Role: U1 (done by TL)    Spec: specs/ui.md

## Goal
From the moment "Ask" is clicked, the page shows a progress bar and one line per pipeline
stage, each line stating what that stage really did. After the answer shows, the trace stays
on the page, collapsed, and can be opened. A failed stage is shown as failed with its error.

## Files to change
- `src/cee/ask.py` - optional `progress` callback in `ask()` and `answer_for()`; each stage
  reports running/done/skipped/failed with facts from its own output. Default `None`: eval
  runner and tests unchanged, no extra LLM call.
- `src/cee/app/views/ask_page.py` - progress bar + `st.status` trace around `ask()`; error shown.
- `src/cee/app/components.py` - `trace_lines()` component and its CSS.
- `tests/test_ask_progress.py` - stage order and facts, gap path skips the model, failure is
  reported then re-raised, one model call.
- `.claude/skills/verify-cee/features/ask-progress.md`, `features/README.md`,
  `scripts/verify_cee.py` - new `ask-progress` feature and driver.

## Steps
1. Callback in `ask()`/`answer_for()`, tests first.
2. Trace component and Ask page.
3. Recipe + driver: progress bar and first step seen before the answer (DOM observer),
   trace collapsed after, lines match the footer; gap question shows the model step skipped.
4. `verify_cee.py run`, screenshots for the PR.

Unsure: a mock answer is fast, so "mid-run" is proven by the order the browser saw elements
in, not by a screenshot caught mid-run.

## Acceptance
- [ ] Linked questions: Q26, Q30 (trace shows firms, counts and whether the model was called)
- [ ] specs/ui.md acceptance: progress bar and trace appear at once, advance with the stages,
      lines from real output, failed stage shown, no extra LLM call
- [ ] `pytest -q` passes; `verify_cee.py run` all PASS including `ask-progress`

## Progress log
- 2026-10-22 - plan written
- 2026-10-22 - callback + tests; trace on the Ask page; AppTest covers the failed-stage path
- 2026-10-22 - verify: a fast mock merges "show bar" and "remove bar" into one Streamlit update, so the bar never drew. Added MOCK_DELAY_S (default 0, verify app 1.5 s) to catch the page mid-run; ask-progress PASS 3 of 3
