# 0083 - verify-cee: wait for the answer before reading the page

Issue: #83    Role: TL    Spec: CLAUDE.md "Verification"

## Goal
verify-cee reads a page only after it has rendered, so a slow answer is a clear timeout
("did not render within N s"), never a wrong FAIL ("no citation links").

## Cause
`wait_idle()` waits for network idle and for Streamlit's status widget to be gone. Streamlit
talks over a websocket, so the network is idle at once, and right after a click the status
widget may not have appeared yet: the wait returns before the rerun starts and the driver reads
the old page. On the 68-document corpus this fails about once per run (runs on 2026-10-19,
main and #90's branch).

## Files to change
- tests/test_verify_wait.py - the timeout message, with a fake page
- scripts/verify_cee.py - `wait_for_text(page, texts, what)`: wait until the page shows a text
  that only the finished render has, then `wait_idle`; used by `ask()` ("LLM called:", the meta
  line every answer behavior ends with), the source page ("Stored passage" or the not-in-corpus
  error) and the download page (the button or the "not found locally" note). A timeout raises
  `RenderTimeout` with that message.
- .claude/skills/verify-cee/features/README.md - the driving convention says what to wait for

## Steps
1. Change the waits.
2. `verify_cee.py run` 5 times in a row on corpus-2026-10-18.

## Acceptance
- [x] `verify_cee.py run` passes 5 runs in a row on the current snapshot (summary lines in the PR)
- [x] A timeout reports "answer did not render within N s" instead of "no citation links"
- [x] `pytest -q` passes

## Progress log
- 2026-10-19 - plan written; branch tl/83-verify-wait created
- 2026-10-19 - wait_for_text in ask(), source, invalid-chunk and download pages; recipe README
  convention updated; 2 tests for the timeout message (fake page). pytest 110 passed.
- 2026-10-19 - verify_cee.py run x5 in a row on corpus-2026-10-18 (68 documents): all 5 features
  PASS every time (42-52 s each). Before the fix, 4 of 6 runs that day had a FAIL.
