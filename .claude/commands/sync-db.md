---
description: Bring the local database to the newest corpus snapshot (snapshots/LATEST.json)
---

Sync this laptop's database to the snapshot named in `snapshots/LATEST.json` (#129). Explain each
step to the user in plain language. Never print or open `.env`. Never restore by hand.

1. **Docker.** `docker info` must work. If not, ask the user to start Docker Desktop and wait for
   "Engine running", then continue.
2. **Run the script for this OS** from the repo folder (it pulls `main`, installs requirements,
   starts the database, finds the dump, checks its sha256, restores it and runs the smoke test):
   - Windows: `powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1`
   - macOS: `bash scripts/sync-db.sh`
3. **Report in plain words**, by exit code:
   - `0` and "Already up to date": say the database already has that snapshot; nothing changed.
   - `0` and "Synced to ...": say which snapshot is loaded, quote the "What is new" line (the
     `notes`), and say the smoke test passed.
   - `2`: the dump is not on this laptop, or the copy found is old or incomplete. The database was
     not changed. Ask the user to open the **team Box link** (pinned in the team chat, never in
     this repo), download the file the message names into the repo's `snapshots` folder, and say
     "done"; then run step 2 again.
   - `1`: quote the error line. "git pull failed": `main` has local changes or commits; ask the
     user what to do with them. "smoke test FAILED": show the `[FAIL]` lines. A warning that the
     branch is not `main` means the sync used this branch's `LATEST.json`; suggest switching to
     `main` when the user is ready.
4. Optional: start the app (`docs/RUN.md` section 2) and check the footer shows the snapshot name.
