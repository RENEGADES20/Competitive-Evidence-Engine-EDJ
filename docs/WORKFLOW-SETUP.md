# Workflow setup (for Claude Code to execute)

**Teammate:** open Claude Code in the repo folder and type:
`Read docs/WORKFLOW-SETUP.md and do it with me.`
That is all you need to do; Claude will walk you through the rest.

**Claude:** you are setting up this teammate's laptop so they can prove their work in the
running app before opening a PR (the `verify-cee` skill). Follow the steps in order.

## Rules for this run

- Talk to the teammate in the language they write in, in plain words; they are not a
  software engineer. Before each step, say in one sentence what it does and why.
- **Check before you change.** Every step starts with a check; skip what is already done.
- Never read, print or edit `.env` (only test that it exists). Never commit or push
  anything during this setup; it changes no tracked file.
- Anything that needs an administrator password, a GUI installer, a login or the team
  Box link: give the teammate exact instructions and wait for them to say "done".
- On any failure: show the exact error line, try the fix listed here once, and if it still
  fails, stop and add it to the report (step 9). Do not improvise workarounds that touch
  `main`, the hook, or `.claude/settings.json`.
- Run long commands (installs, Chromium download, restore) with a long timeout.

## 0. Detect the platform

Run `uname -s` (macOS prints `Darwin`); on Windows also check `$env:OS` or `ver`.
Use these names below:

| | Windows | macOS |
|---|---|---|
| `PY` (project Python) | `.venv\Scripts\python.exe` | `.venv/bin/python` |
| Base Python to create the venv | `py -3.11` | `python3.11` |
| Package installer | download links below, or `winget` | `brew` (Homebrew) |
| Restore a snapshot | `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1` | the three `docker` commands in step 5 |

On macOS never run the `scripts/*.ps1` files.

## 1. Repo is current

1. `git status --short` and `git rev-parse --abbrev-ref HEAD`.
2. If there are uncommitted changes, stop and ask the teammate what to do with them.
3. `git switch main` then `git pull`. Confirm `.claude/skills/verify-cee/SKILL.md` exists.

## 2. Tools

Check each; install only what is missing.

| Tool | Check | Windows install | macOS install |
|---|---|---|---|
| Git | `git --version` | https://git-scm.com/download/win (includes Git Bash, which Claude Code needs) | `xcode-select --install` or `brew install git` |
| GitHub CLI | `gh auth status` shows "Logged in" | `winget install GitHub.cli`, then `gh auth login` | `brew install gh`, then `gh auth login` |
| Python 3.11 | Windows `py -3.11 --version`; macOS `python3.11 --version` | https://www.python.org/downloads/ 3.11.x, tick "Add python.exe to PATH" | `brew install python@3.11` |
| Docker Desktop | `docker info` succeeds | https://www.docker.com/products/docker-desktop/ (accept WSL 2, restart) | `brew install --cask docker`, then open Docker once |
| Claude Code | `claude --version` | already installed (you are running in it) | same |

`gh auth login`: choose GitHub.com, HTTPS, "Login with a web browser". The teammate must
have accepted the repo invitation first.

Homebrew missing on macOS: the teammate runs the command from https://brew.sh in Terminal,
then the two "Next steps" lines it prints. Then retry.

## 3. Project environment

1. If `.venv` does not exist: `<base python> -m venv .venv`.
2. `PY -m pip install -r requirements.txt`
3. `PY -m pip install -e .`
4. `PY -m pip install -r requirements-verify.txt`
5. `PY -m playwright install chromium` (downloads a browser, about 150 MB).
6. `.env` exists? Test only (`Test-Path .env` / `test -f .env`). If missing, copy
   `.env.example` to `.env`. Do not open it. Default `LLM_PROVIDER=mock` costs nothing.

## 4. The main-branch guard works

The hook in `.claude/settings.json` blocks commits and pushes to `main`. Prove it blocks:

Run (same on both platforms; `PY` from step 0):

```
PY -c "import json,subprocess,sys; r=subprocess.run([sys.executable,'.claude/hooks/guard-main.py'],input=json.dumps({'tool_input':{'command':'git push origin main'}}),capture_output=True,text=True); print(r.returncode, r.stderr.strip())"
```

Expected: `2 Blocked: never commit or push to main ...`. Do not test by piping text from
PowerShell; it adds a byte-order mark and the guard then lets the command through.
On Windows also check `bash --version` works (Claude Code runs hooks with Git Bash).

## 5. Database with the newest snapshot

1. Docker Desktop is running (`docker info`). If not, ask the teammate to open it and wait
   for "Engine running".
2. `docker compose up -d --wait`
3. Find the newest `snapshots/corpus-YYYY-MM-DD.dump` (ignore names ending in `-test`).
   None there: ask the teammate to download the newest one from the **team Box link
   (pinned in the team chat)** into the repo's `snapshots` folder. On macOS, if it comes
   from Box Drive, the file must show as downloaded (not a cloud placeholder) and must not
   be 0 bytes. Wait for "done".
4. Is it already loaded? `docker exec cee-db psql -qtA -U cee -d cee -c "SELECT obj_description('public.documents'::regclass)"`
   prints the loaded snapshot name (e.g. `corpus-2026-09-30`). If it equals the newest file
   name without `.dump`, skip to step 6.
5. Restoring replaces the local database. Tell the teammate, then:
   - Windows: `powershell -ExecutionPolicy Bypass -File scripts\restore.ps1`
   - macOS (put the real file name in place of `corpus-YYYY-MM-DD.dump`):
     ```
     docker exec cee-db psql -q -U cee -d postgres -c "DROP DATABASE IF EXISTS cee WITH (FORCE);" -c "CREATE DATABASE cee;"
     docker exec cee-db pg_restore -U cee -d cee --no-owner /snapshots/corpus-YYYY-MM-DD.dump
     ```

## 6. Health checks

1. `PY -m cee.smoke` -> five `[ok]` lines and `PASS`.
2. `PY -m pytest -q` -> all passed.

## 7. Prove it in the app (verify-cee)

1. `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`. Fix FAIL lines with the table in
   `.claude/skills/verify-cee/SKILL.md`.
2. `PY scripts/verify_cee.py run`
3. Expected: `ask-answer`, `open-citation`, `gap-path`, `invalid-chunk` = PASS.
   `download-document` = UNREACHABLE is normal when the raw files are not in `data/raw/`.
   Any FAIL: open that feature's screenshots in `.verify-runs/<run>/`, compare with the
   recipe in `.claude/skills/verify-cee/features/`, and report it; do not edit the script
   or the app during setup.
4. Show the teammate one screenshot from the run (path), so they see what the evidence is.

## 8. Explain the new way of working (2 minutes)

Tell the teammate, in plain words:

1. Same flow as before: `/start-task <issue#>` -> agree the plan -> say "go" -> work.
2. New: before `/finish-task`, Claude runs `verify-cee`. It opens the app in a hidden
   browser, clicks through it like a user, and saves screenshots. `/finish-task` now does
   this for them.
3. The PR has a **Verification** section: what was actually run, the result, and how
   strong each claim is (1 said so ... 5 reproduced in the running app). "Tests pass"
   alone does not count.
4. If their change adds or changes something a user sees, the recipe in
   `.claude/skills/verify-cee/features/` changes in the same PR.
5. Use `Part of #N` instead of `Closes #N` when only part of the issue is done.

## 9. Report

Print this block, filled in:

```
Workflow setup report
OS: <Windows 11 / macOS 15 ...>   Claude Code: <version>   Python: <3.11.x>
Repo at: <commit short SHA on main>
Tools:   git <ok>  gh <ok, logged in as ...>  docker <ok>  bash/hook <ok>
Snapshot: <corpus-YYYY-MM-DD>   smoke: <PASS/FAIL>   pytest: <N passed>
verify-cee: ask-answer <..> open-citation <..> gap-path <..> invalid-chunk <..> download-document <..>
Evidence folder: .verify-runs/<run-id>
Problems / open items: <none, or each with the exact error>
```

Then ask the teammate: "Post this report on the GitHub issue 'Workflow setup check-in' so
the tech lead knows you are ready?" Only on yes: find it with
`gh issue list --search "Workflow setup check-in in:title" --state open`, then
`gh issue comment <number> --body "<report>"`. Never post evidence files, `.env` values or
anything else.
