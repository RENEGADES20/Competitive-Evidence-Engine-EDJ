# Run page

How to install, start and check the prototype on a Windows laptop. Two routes:
**teammates** (download the weekly snapshot by hand) and the **tech lead** (Box Drive,
builds the snapshots). Commands are for Windows PowerShell, run from the repo folder.

## 1. Install once (teammates and tech lead)

| Tool | Get it | Check |
|---|---|---|
| Docker Desktop | https://www.docker.com/products/docker-desktop/ (turn on virtualization in BIOS first if it asks; accept WSL 2; restart) | `docker --version` |
| Python 3.11 | https://www.python.org/downloads/ (3.11.x, tick "Add python.exe to PATH" or use the `py` launcher) | `py -3.11 --version` |
| Git | https://git-scm.com/download/win | `git --version` |
| GitHub CLI | https://cli.github.com/ then `gh auth login` | `gh --version` |

Then, in PowerShell:

```powershell
gh repo clone RENEGADES20/Competitive-Evidence-Engine-EDJ
cd Competitive-Evidence-Engine-EDJ
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
```

Open `.env` in a text editor. Leave `LLM_PROVIDER=mock` (offline, free) unless you are told
to test with a real model; then set `LLM_PROVIDER=anthropic` and your `ANTHROPIC_API_KEY`.
Teammates leave `CORPUS_SHARE_PATH` empty. Never commit `.env`.

Corpus owners who ingest documents (tech lead, C1, C2) also install
`pip install -r requirements-ingest.txt` (large: docling pulls in PyTorch) and set
`EDGAR_IDENTITY` to their name and email.

## 2. Daily use (teammates)

1. Start Docker Desktop and wait until it says "Engine running".
2. Get the newest snapshot: open the **team Box link** (pinned in the team chat, never in
   this repo), go to `snapshots/`, download the newest `corpus-YYYY-MM-DD.dump` into the
   repo's `snapshots\` folder.
3. Load it (replaces your local database):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\restore.ps1
   ```
4. Check everything works:
   ```powershell
   .\.venv\Scripts\python.exe -m cee.smoke
   ```
   Expect five `[ok]` lines and `PASS`.
5. Start the app and open http://localhost:8501:
   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run src\cee\app\streamlit_app.py
   ```

To download a raw document from the source view, the file must be in `data\raw\` (download it
from the Box link's `raw/` folder). The source view always shows the stored passage itself.

## 3. Adding a raw document (from W3)

Name the file `<doc_id>.<ext>` before uploading (e.g. `MS-TR-2025Q2.pdf`); Box renames
duplicates, which breaks the manifest. Upload through the **team Box upload link** (team
chat), add the manifest row in your PR, and the tech lead moves the file into `raw/`.

## 4. Tech lead route

- Box Drive syncs the team folder to `C:\Users\<you>\Box\EDJ`; set that path as
  `CORPUS_SHARE_PATH` in `.env`. Layout: `raw\<doc_id>.<ext>` (flat) and `snapshots\`.
- Right-click `raw` and `snapshots` -> **Make available offline**, so scripts never wait on
  cloud-only placeholders.
- Fetch a filing (writes straight into Box `raw\` and appends to `data\manifest.csv`):
  `.\.venv\Scripts\python.exe -m cee.ingest.edgar --entity EDJ --form 10-K`
- Load the manifest into the local database: `powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1`
- Weekly snapshot, from a clean `main`:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1
  ```
  It checks every manifest file (exists, sha256 matches), rebuilds the database, dumps
  `corpus-YYYY-MM-DD.dump`, and copies it into Box `snapshots\`. `-AllowBranch` skips the
  clean-main check for testing only; its dump is named `...-test` and must not be shared.
- Checklist: [DASHBOARD.md section 8](DASHBOARD.md#8-weekly-snapshot-checklist-tech-lead).

## 5. When it breaks

| Symptom | Fix |
|---|---|
| `running scripts is disabled on this system` | Run scripts as shown: `powershell -ExecutionPolicy Bypass -File scripts\...` |
| `failed to connect to the docker API` / `Starting the database failed` | Start Docker Desktop, wait for "Engine running", run again |
| Docker asks for WSL 2 or virtualization | Install WSL (`wsl --install`), restart; enable virtualization (VT-x/SVM) in BIOS |
| `port is already allocated` on 5432 | Another Postgres is running. Stop it (Services -> postgresql -> Stop) or change `5432:5432` to `5433:5432` in docker-compose.yml and the port in `DATABASE_URL` |
| `connection timeout expired` from Python | The container stopped: `docker compose up -d`, then `docker ps` should show `cee-db` healthy |
| `python` opens the wrong Python / `Permission denied` | Another tool's Python is first on PATH. Always use `.\.venv\Scripts\python.exe`; create the venv with `py -3.11 -m venv .venv` |
| `No snapshot found` | Download the newest `.dump` from the team Box link into `snapshots\` |
| smoke says `0 chunks` | Restore a snapshot (section 2, step 3) |
| `... not found locally. Download it from the team Box link` | The raw file is not in `data\raw\`; download it, or ignore if you only need the passage |
| `sha256 mismatch` in build-snapshot | The file in Box changed or Box renamed it (e.g. `name (1).htm`). Restore the right file or fix the manifest row via PR |
| build-snapshot hangs on a file | Box Drive has it cloud-only; mark the folder "Make available offline" |
| `pytest` PermissionError on a temp folder | Already handled: tests use `.pytest_tmp\` in the repo |

## 6. Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
No database or API key needed; the paid providers are tested with fake clients.
