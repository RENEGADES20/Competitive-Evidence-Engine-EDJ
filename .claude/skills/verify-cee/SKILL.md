---
name: verify-cee
description: Prove that the Competitive Evidence Engine works by driving the real Streamlit app in a browser, the way a user does, and keeping screenshots and step logs as evidence. Use before /finish-task, when asked to "verify", "check it in the app", "prove it works", or to reproduce a bug a teammate reported. Windows and macOS.
---

# verify-cee

"It compiles" and "tests pass" are not evidence that a user gets a correct, cited answer.
This skill launches the app on a private copy of the database, drives each feature in a
real browser, and saves what happened. Explain each step to the user in plain language.

All commands run from the repo root with the project venv. `PY` below means:
- Windows: `.venv\Scripts\python.exe`
- macOS: `.venv/bin/python`

## Doctor (run first, and again after anything surprising)

`PY scripts/verify_cee.py doctor` -> six `[ok]` lines and `DOCTOR PASS`.

| FAIL line | Fix |
|---|---|
| python | Use the venv Python above, not `python` |
| docker | Start Docker Desktop, wait for "Engine running" |
| database / corpus | `docker compose up -d --wait`, then restore the newest snapshot (docs/RUN.md section 2) |
| browser | `PY -m pip install -r requirements-verify.txt` then `PY -m playwright install chromium` |
| port | Something else uses 8599. Stop it, or add `--port 8600` to every command |

Never drive an app instance this script did not start.

## Launch, drive, clean up

One command does all three and always cleans up:

`PY scripts/verify_cee.py run` (all features) or `PY scripts/verify_cee.py run <feature> ...`

What it does:
- **Launch:** copies database `cee` to `cee_verify` (your own data is never written), starts
  Streamlit on port 8599 with `LLM_PROVIDER=mock`, waits for `/_stcore/health`.
- **Drive:** Playwright (headless Chromium) follows each recipe in `features/`.
- **Evidence:** `.verify-runs/<time>-<commit>/` (git-ignored): one folder per feature with a
  screenshot and page text per step, plus `steps.jsonl`, `summary.json` and `app.log`.
- **Cleanup:** stops only the app it started, drops `cee_verify`, keeps the evidence.

Step by step, when you need to look around in between: `launch`, then `drive <feature>`
(repeat), then `cleanup`. Always run `cleanup` after a failed attempt.

## Features

The map in [features/README.md](features/README.md) is the source of truth: one file per
user-facing feature, how a user reaches it, how the script drives it, what proves it works.

| ID | Proves |
|---|---|
| `ask-answer` | A question returns an answer with citation links; the query is logged |
| `open-citation` | A citation opens the stored passage, and it matches the database |
| `gap-path` | A question with no stored evidence says so, with no invented citation |
| `invalid-chunk` | An unknown chunk ID shows a clear error |
| `download-document` | The stored document downloads with the right sha256 |

## Reading the result

- `PASS`: every step met its expected result.
- `FAIL`: a step did not. Open that feature's screenshots before guessing; suspect the
  recipe or the environment first, then the product. Re-run the same feature on `main`
  (`git switch main`, run, `git switch -`) to tell an old problem from a new regression.
- `UNREACHABLE`: a precondition is missing (e.g. the raw file is not in `data/raw/`).
  Report it with the precondition. It is not a pass, and never report a skipped path as
  verified through another path.

## Proof standards

- Drive the real user path (text box, button, link), not internal functions.
- Record the action and the resulting state, not only the final screen.
- Check side effects too (the `query_log` row, the stored passage, the file hash).
- The mock provider only proves the pipeline and the UI. It always answers when retrieval
  finds something, so it says nothing about answer quality.

## When you change the app

A change that adds or alters a user-facing feature must update its file in `features/`
and the matching driver in `scripts/verify_cee.py` in the same PR, then run it once
end to end. A recipe that was never run is a draft.

## Reporting in a PR

In the PR's `## Verification` section, list each feature run with its result and the
evidence folder name, and say which level of proof each claim reached:
1 said so, 2 pointed at the line, 3 reasoned it through, 4 ran a script, 5 reproduced in
the running app. Attach one or two screenshots that prove the change.
