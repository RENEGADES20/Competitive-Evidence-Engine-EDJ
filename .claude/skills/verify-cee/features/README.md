# Feature map: Competitive Evidence Engine

The maintained source for verifying user-facing behavior. Read this index, then the
feature file you need. Drivers live in `scripts/verify_cee.py` (`DRIVERS`).

## Baseline preconditions

- Docker is running and `cee-db` holds a restored snapshot (`doctor` shows chunks > 0).
- The script copies `cee` to `cee_verify` and starts its own app on port 8599 with the
  mock provider. Every recipe starts from the question page of that app.
- Questions used: answerable = "What does Edward Jones's 10-K say about its number of
  financial advisors?"; no evidence = the same question for LPL Financial (an expansion
  firm with nothing stored; Morgan Stanley was used until its filings arrived in #36). When
  the corpus gains LPL documents, change the no-evidence question.

## Driving conventions

- Find elements by role and visible name (textbox "Question", button "Ask"), not by CSS.
- Wait for a text only the finished page has, then for Streamlit to finish running (status
  widget gone); never a fixed sleep. After Ask: the meta line "LLM called:". Source page:
  "Stored passage" or the not-in-corpus error. The status widget alone can be gone before the
  rerun starts, so the old page is read (#83). A timeout is reported as "... did not render".
- Citation links open in a new browser tab.

## Proof

- Every step saves a screenshot and the page text; `steps.jsonl` has action, expected,
  actual and result.
- State changes are read back from the database (`query_log`, `chunks`, `documents`).

## Feature entry contract

Each file: an H1, one paragraph of user-visible behavior, then exactly these H2s:
`Sub-features`, `How to get to it (user POV)`, `Driving it`, `Gotchas`.

## Features

- [ask-answer](ask-answer.md): ask a question, get cited claims, query is logged.
- [open-citation](open-citation.md): open the stored passage behind a citation.
- [gap-path](gap-path.md): no evidence is reported honestly.
- [invalid-chunk](invalid-chunk.md): unknown chunk IDs fail clearly.
- [download-document](download-document.md): download the stored source file.

Not mapped yet (not built): coverage view, filters, PDF page view, feedback buttons
(specs/ui.md, W3+). Add a file here in the PR that builds each one.
