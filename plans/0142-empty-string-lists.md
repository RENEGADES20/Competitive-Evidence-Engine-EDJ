# 0142 - Answer list fields sent as strings must not crash

Issue: #142    Role: TL    Spec: specs/answer-citations.md

## Goal
When the model sends `claims`, `adjacent`, `gaps` or `caveats` as an empty string or as a
JSON-encoded list, the answer is still built; any other malformed value still fails loudly.

## Files to change
- `src/cee/answer/schema.py` - `mode="before"` validator on the four list fields of `Answer`
- `tests/test_schema.py` - new: empty string, JSON-encoded list, other strings still fail

## Steps
1. Add the validator: not a string -> unchanged; blank -> `[]`; `json.loads` gives a list -> that
   list; otherwise unchanged so pydantic raises.
2. Add the tests (no model call: the bad input is written by hand).
3. Full pytest on mock; verify-cee on mock.

## Acceptance
- [x] Linked questions: Q20 - the 2026-10-30 real run crashed here; the same input now gives `claims == []`
- [x] `claims='[{"text": "x", "chunk_ids": ["MS-10K-2025#1"]}]'` parses into one Claim
- [x] `claims="not a list"` and `claims='{"text": "x"}'` still raise `ValidationError`
- [x] Check to run: `python -m pytest tests` (LLM_PROVIDER=mock) -> all pass
- [x] Check to run: `scripts/verify_cee.py run` (mock) -> ask features PASS

## Paid calls
0. The crash is reproduced with a hand-written input; asking Q20 again would only re-roll the model.

## Progress log
- 2026-10-30 10:40 - real run of 30 questions crashed at Q20 (`claims=""`); fix and tests written
  in a worktree before the issue existed (out of order: plan written after the code)
- 2026-10-30 10:45 - pytest on mock: 231 passed, 1 skipped
- 2026-10-30 11:00 - issue #142 opened, branch renamed `tl/142-empty-string-lists`, plan saved
- 2026-10-30 10:57 - verify-cee (mock): all features PASS except open-citation UNREACHABLE (no
  CORPUS_SHARE_PATH in the worktree, raw PDF precondition); re-run with it set: PASS
  (`.verify-runs/20261030-105712-f8ffa0d`, `.verify-runs/20261030-105959-f8ffa0d`)
