# Workflow setup (executed by Claude Code)

This file is run by a teammate's Claude Code, started from a prompt the tech lead sends in
the team chat. The teammate does not need to read or understand it. The goal: this laptop
can prove changes in the running app (`verify-cee`) and reports that it is ready.

## Rules for this run

- Talk to the teammate in the language of their prompt, in short plain sentences. Do not
  explain internals. Only speak up when you need them to do something, and then give one
  exact action at a time ("click this link", "type your Mac password in the window").
- **Check before you change.** Every step starts with a check; skip what is already done.
  The run must be safe to repeat.
- Never read, print or edit `.env` (only test that it exists). Never commit or push.
  This setup changes no tracked file.
- Only the teammate can: type an administrator password, approve a Windows "Do you want to
  allow" prompt, log in to GitHub in the browser, click the Box link. Everything else you do.
- On a failure: try the listed fix once. If it still fails, record the exact error line,
  continue with the steps that do not depend on it, and put it in the report.
- Use long timeouts for installs, the Chromium download and the restore.

## Background you need

- Every laptop runs its **own** Postgres in Docker at `localhost:5432` (`cee-db`). The
  address is the same everywhere, but the data is separate: it is whatever snapshot that
  laptop restored. `query_log` and feedback rows stay on that laptop.
- The tech lead publishes a weekly snapshot `corpus-YYYY-MM-DD.dump` in the team Box
  folder. Results (scores, verification) are only comparable on the same snapshot, so the
  report records the snapshot name.
- Raw documents are not needed; without them `download-document` reports UNREACHABLE.

## 0. Platform and repo

1. Platform: `uname -s` prints `Darwin` on macOS; otherwise Windows. Use:

   | | Windows | macOS |
   |---|---|---|
   | `PY` | `.venv\Scripts\python.exe` | `.venv/bin/python` |
   | Base Python | `py -3.11` | `python3.11` |
   | Restore | `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1` | docker commands in step 4 |

   On macOS never run `scripts/*.ps1`.
2. Repo: if the current folder has `CLAUDE.md` and `git remote -v` shows
   `Competitive-Evidence-Engine-EDJ`, use it. Otherwise look for a folder of that name in
   the home folder, `~/Projects`, `~/Documents`, `~/Desktop` (2 levels deep). Not found:
   clone it into `~/Projects` with `gh repo clone RENEGADES20/Competitive-Evidence-Engine-EDJ`
   (after step 1 has `gh`). Run every later command from the repo folder.
3. `git status --short`. If there are uncommitted changes, ask the teammate whether to
   keep them aside: on yes, `git stash push -u -m "before workflow setup"` and say so in
   the report; on no, stop.
4. `git switch main` and `git pull`. Confirm `.claude/skills/verify-cee/SKILL.md` exists.

## 1. Tools

Check each; install only what is missing.

| Tool | Check | Windows (run it; the teammate clicks "Yes" if asked) | macOS |
|---|---|---|---|
| Git (+ Git Bash on Windows) | `git --version`; Windows also `bash --version` | `winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements` | `xcode-select --install` (teammate clicks Install) |
| GitHub CLI | `gh auth status` says logged in | `winget install -e --id GitHub.cli ...` (same flags) | `brew install gh` |
| Python 3.11 | Win `py -3.11 --version`; Mac `python3.11 --version` | `winget install -e --id Python.Python.3.11 ...` | `brew install python@3.11` |
| Docker Desktop | `docker --version` | `winget install -e --id Docker.DockerDesktop ...` then restart the laptop (ask first) | `brew install --cask docker` |

- macOS without Homebrew (`brew` missing): ask the teammate to open the Terminal app, paste
  `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`,
  type their Mac password when asked, then paste the two "Next steps" lines it prints. Then
  run `eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"` here and continue.
- `gh` not logged in: run `gh auth login --hostname github.com --git-protocol https --web`.
  Show the teammate the one-time code it prints and ask them to finish in the browser.
  They must have accepted the repo invitation (email) first.
- After a Windows install, a new tool may not be on PATH in this session: use its full
  path (e.g. `C:\Program Files\GitHub CLI\gh.exe`) or ask the teammate to restart Claude Code
  and paste the same prompt again (the run resumes, because every step checks first).

## 2. Docker running

1. `docker info` succeeds? Done.
2. Otherwise start it yourself: macOS `open -a Docker`; Windows
   `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`. First start may show a
   license or WSL screen: ask the teammate to accept it.
3. Re-check `docker info` every 10 seconds, up to 3 minutes.
4. `docker compose up -d --wait`

## 3. Project environment

1. No `.venv`: `<base python> -m venv .venv`.
2. `PY -m pip install -r requirements.txt`
3. `PY -m pip install -e .`
4. `PY -m pip install -r requirements-verify.txt`
5. `PY -m playwright install chromium` (about 150 MB).
6. `.env` exists? Test only. If missing, copy `.env.example` to `.env` and do not open it.

## 4. Newest snapshot in the database

1. Loaded snapshot: `docker exec cee-db psql -qtA -U cee -d cee -c "SELECT obj_description('public.documents'::regclass)"`
   (empty or an error means none).
2. Find the newest `corpus-YYYY-MM-DD.dump` (ignore `-test`), in this order:
   - the repo's `snapshots/` folder;
   - Box Drive, if installed: macOS `~/Library/CloudStorage/Box-Box*/**/snapshots/`,
     Windows `~/Box/**/snapshots/` (2 levels deep). A file of 0 bytes is a cloud
     placeholder: on macOS run `cat <file> > /dev/null` to make Box download it, then check
     the size again;
   - the Downloads folder.
   Copy the newest one into the repo's `snapshots/` folder.
3. None found, or the tech lead's prompt names a newer one: ask the teammate to open the
   **Box link from the prompt** and download that `.dump` file (default download folder),
   then say "done". Find it in Downloads and copy it into `snapshots/`.
4. If the loaded snapshot equals the newest file name without `.dump`, skip to step 5.
   Otherwise restore (this replaces this laptop's local database only):
   - Windows: `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1`
   - macOS (real file name in place of `corpus-YYYY-MM-DD.dump`):
     ```
     docker exec cee-db psql -q -U cee -d postgres -c "DROP DATABASE IF EXISTS cee WITH (FORCE);" -c "CREATE DATABASE cee;"
     docker exec cee-db pg_restore -U cee -d cee --no-owner /snapshots/corpus-YYYY-MM-DD.dump
     ```

## 5. Health checks

1. `PY -m cee.smoke` -> five `[ok]` lines and `PASS`.
2. `PY -m pytest -q` -> all passed.
3. Main-branch guard blocks (same command on both platforms):
   ```
   PY -c "import json,subprocess,sys; r=subprocess.run([sys.executable,'.claude/hooks/guard-main.py'],input=json.dumps({'tool_input':{'command':'git push origin main'}}),capture_output=True,text=True); print(r.returncode, r.stderr.strip())"
   ```
   Expected `2 Blocked: ...`. (Do not test by piping text from PowerShell: it adds a
   byte-order mark and the guard lets the command through.)

## 6. Prove it in the app

1. `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`. Fix FAIL lines with the table in
   `.claude/skills/verify-cee/SKILL.md`, then re-run.
2. `PY scripts/verify_cee.py run`
3. Expected: `ask-answer`, `open-citation`, `gap-path`, `invalid-chunk` PASS;
   `download-document` PASS or UNREACHABLE. On FAIL, read that feature's page text in
   `.verify-runs/<run>/<feature>/` and put the failing step in the report. Do not edit the
   script or the app.

## 7. Report and finish

1. Fill in:
   ```
   Workflow setup report - <GitHub login>
   OS: <...>   Claude Code: <claude --version>   Python: <3.11.x>   Repo: main @ <short SHA>
   Tools: git ok | gh ok | docker ok | Git Bash ok/n.a. | guard blocks ok
   Snapshot loaded: <corpus-YYYY-MM-DD>   smoke: PASS   pytest: <N> passed
   verify-cee: ask-answer <> | open-citation <> | gap-path <> | invalid-chunk <> | download-document <>
   Stashed changes: <none / stash name>
   Problems: <none, or each with the exact error line>
   ```
2. Post it: `gh issue list --search "Workflow setup check-in in:title" --state open`, then
   `gh issue comment <number> --body "<report>"`. The teammate's prompt already authorizes
   this one comment. Post nothing else (no evidence files, no `.env` values).
3. Tell the teammate, in three lines at most: setup is done (or what is still open); from
   now on `/finish-task` checks the work in the app automatically; nothing else changes.
