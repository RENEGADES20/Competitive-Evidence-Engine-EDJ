# Run page

How to install, start and check the prototype on a Windows or Mac laptop. Two routes:
**teammates** (download the weekly snapshot by hand) and the **tech lead** (Box Drive,
builds the snapshots). Every step has a **Windows** block (PowerShell) and a **Mac** block
(Terminal); run them from the repo folder. Each `scripts\*.ps1` has a `scripts/*.sh` twin
that does the same thing; Mac users never run the `.ps1` files.

## 1. Install once (teammates and tech lead)

| Tool | Get it | Check |
|---|---|---|
| Tool | Windows | Mac | Check |
|---|---|---|---|
| Docker Desktop | https://www.docker.com/products/docker-desktop/ (turn on virtualization in BIOS first if it asks; accept WSL 2; restart) | Same link; pick Apple chip or Intel chip | `docker --version` |
| Python 3.11 | https://www.python.org/downloads/ (3.11.x, tick "Add python.exe to PATH" or use the `py` launcher) | Same link, macOS installer 3.11.x | Win `py -3.11 --version` / Mac `python3.11 --version` |
| Git | https://git-scm.com/download/win | Already there (type `git`, accept the Command Line Tools prompt) | `git --version` |
| GitHub CLI | https://cli.github.com/ then `gh auth login` | Same link (or `brew install gh`) then `gh auth login` | `gh --version` |

Then:

Windows (PowerShell)
```powershell
gh repo clone RENEGADES20/Competitive-Evidence-Engine-EDJ
cd Competitive-Evidence-Engine-EDJ
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
if (-not (Test-Path .env)) { Copy-Item .env.example .env }   # never overwrites an existing .env
```

Mac (Terminal)
```bash
gh repo clone RENEGADES20/Competitive-Evidence-Engine-EDJ
cd Competitive-Evidence-Engine-EDJ
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
[ -f .env ] || cp .env.example .env   # never overwrites an existing .env
```

Open `.env` in a text editor. Leave `LLM_PROVIDER=mock` (offline, free) unless you are told
to test with a real model; then set `LLM_PROVIDER=anthropic` and your `ANTHROPIC_API_KEY`.
Teammates leave `CORPUS_SHARE_PATH` empty. Never commit `.env`.

`requirements.txt` includes `fastembed` (embeddings, #124; no PyTorch). On an Intel Mac it needs
macOS 13 or newer (`onnxruntime` 1.23.2 is the last version with Intel Mac builds).

Corpus owners who ingest documents (tech lead, C1, C2) also install
`pip install -r requirements-ingest.txt` (large: docling pulls in PyTorch) and set
`EDGAR_IDENTITY` to their name and email.

### Database image update (#123, once)

The database now runs on `pgvector/pgvector:0.8.1-pg16-trixie` (Postgres 16 with vector
search). After `git pull`, start Docker Desktop and run this once; Docker downloads the new
image (about 150 MB) and keeps your data. Then restore the snapshot as in section 2.

```powershell
docker compose up -d --wait
```
```bash
docker compose up -d --wait
```

### Embedding model (#124, once)

Questions are turned into vectors on your laptop with a small model (`BAAI/bge-small-en-v1.5`,
about 70 MB). The corpus vectors are already inside the snapshot. The model downloads by itself
the first time it is used, into `.cache/fastembed` in the repo (or the folder you set as
`FASTEMBED_CACHE_PATH` in `.env`). Check it (expect `384 dims`):
```powershell
.\.venv\Scripts\python.exe -m cee.retrieve.embed --query "test"
```
```bash
.venv/bin/python -m cee.retrieve.embed --query "test"
```
No HuggingFace access (the check fails with a download error)? Open the team Box link, download
the folder `models/models--Qdrant--bge-small-en-v1.5-onnx-Q`, and unzip it so the repo has
`.cache/fastembed/models--Qdrant--bge-small-en-v1.5-onnx-Q/refs` and `.../snapshots`; then run
the check again. Once the model is there, it works with the network off.
```powershell
Test-Path .cache\fastembed\models--Qdrant--bge-small-en-v1.5-onnx-Q\refs\main   # True
efsmain   # True
```
```bash
test -f .cache/fastembed/models--Qdrant--bge-small-en-v1.5-onnx-Q/refs/main && echo True
```

## 2. Daily use (teammates)

1. Start Docker Desktop and wait until it says "Engine running".
2. Get the newest snapshot: open the **team Box link** (pinned in the team chat, never in
   this repo), go to `snapshots/`, download the newest `corpus-YYYY-MM-DD.dump` into the
   repo's `snapshots` folder.
3. Load it (replaces your local database):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\restore.ps1
   ```
   ```bash
   bash scripts/restore.sh
   ```
4. Check everything works:
   ```powershell
   .\.venv\Scripts\python.exe -m cee.smoke
   ```
   ```bash
   .venv/bin/python -m cee.smoke
   ```
   Expect five `[ok]` lines and `PASS`.
5. Start the app and open http://localhost:8501:
   ```powershell
   .\.venv\Scripts\python.exe -m streamlit run src\cee\app\streamlit_app.py
   ```
   ```bash
   .venv/bin/python -m streamlit run src/cee/app/streamlit_app.py
   ```

In each pair, the first block is Windows (PowerShell), the second is Mac (Terminal).

To download a raw document from the source view, the file must be in `data\raw\` (download it
from the Box link's `raw/` folder). The source view always shows the stored passage itself.

## 3. Adding a raw document (from W3)

Name the file `<doc_id>.<ext>` before uploading (e.g. `MS-TR-2025Q2.pdf`); Box renames
duplicates, which breaks the manifest. Upload through the **team Box upload link** (team
chat), add the manifest row in your PR, and the tech lead moves the file into `raw/`.

## 4. Tech lead route

- Box Drive syncs the team folder to `C:\Users\<you>\Box\EDJ` (Windows) or
  `~/Library/CloudStorage/Box-Box/EDJ` (Mac); set that path as `CORPUS_SHARE_PATH` in `.env`.
  Layout: `raw/<doc_id>.<ext>` (flat), `snapshots/` and `models/` (embedding model, #124).
- Right-click `raw` and `snapshots` -> **Make available offline**, so scripts never wait on
  cloud-only placeholders.
- Fetch a filing (writes straight into Box `raw/` and appends to `data/manifest.csv`):
  ```powershell
  .\.venv\Scripts\python.exe -m cee.ingest.edgar --entity EDJ --form 10-K
  ```
  ```bash
  .venv/bin/python -m cee.ingest.edgar --entity EDJ --form 10-K
  ```
- Load the manifest into the local database (one document: add `-Doc <doc_id>` / `--doc <doc_id>`):
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1
  ```
  ```bash
  bash scripts/ingest.sh
  ```
- Weekly snapshot, from a clean `main`:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1
  ```
  ```bash
  bash scripts/build-snapshot.sh
  ```
  It checks every manifest file (exists, sha256 matches), rebuilds the database, embeds every
  chunk (#124; about 20 minutes on a laptop CPU; the build stops if a chunk has no vector), dumps `corpus-YYYY-MM-DD.dump`, copies
  it into Box `snapshots/`, and puts the embedding model into Box `models/` if it is not there
  yet. `-AllowBranch` / `--allow-branch` skips the clean-main check for testing only; its dump is named `...-test`
  and must not be shared.
- Checklist: [DASHBOARD.md section 8](DASHBOARD.md#8-weekly-snapshot-checklist-tech-lead).

## 5. When it breaks

| Symptom | Fix |
|---|---|
| `running scripts is disabled on this system` | Run scripts as shown: `powershell -ExecutionPolicy Bypass -File scripts\...` |
| `failed to connect to the docker API` / `Starting the database failed` | Start Docker Desktop, wait for "Engine running", run again |
| Docker asks for WSL 2 or virtualization | Install WSL (`wsl --install`), restart; enable virtualization (VT-x/SVM) in BIOS |
| `port is already allocated` on 5432 | Another Postgres is running. Stop it (Services -> postgresql -> Stop) or change `5432:5432` to `5433:5432` in docker-compose.yml and the port in `DATABASE_URL` |
| `connection timeout expired` from Python | The container stopped: `docker compose up -d`, then `docker ps` should show `cee-db` healthy |
| `python` opens the wrong Python / `Permission denied` | Another tool's Python is first on PATH. Always use `.\.venv\Scripts\python.exe` (Mac: `.venv/bin/python`); create the venv with `py -3.11 -m venv .venv` (Mac: `python3.11 -m venv .venv`) |
| Mac: `pwsh: command not found` or a `.ps1` opens as text | Use the `.sh` twin: `bash scripts/<name>.sh` |
| Mac: `permission denied: scripts/restore.sh` | Run it through bash as shown (`bash scripts/restore.sh`), or `chmod +x scripts/*.sh` once |
| `Upgrading the schema failed` / `extension "vector" is not available` | Your container still runs the old image: `docker compose up -d --wait`, then restore again |
| `collation version mismatch` | The image's operating system differs from the one that created your data. Start clean: `docker compose down -v`, `docker compose up -d --wait`, then restore the snapshot |
| `pip install` fails on `onnxruntime` (Intel Mac) | It needs macOS 13 or newer (Apple menu -> About This Mac). Update macOS, or ask the tech lead |
| `cee.retrieve.embed` fails with a connection or download error | HuggingFace is blocked or you are offline: copy the Box `models/` folder into `.cache/fastembed` (section 1, "Embedding model") |
| `Embedding ... failed` in build-snapshot | Read the line above it; a chunk without a vector stops the build. Run `python -m cee.retrieve.embed --missing` again (it continues where it stopped) |
| `No snapshot found` | Download the newest `.dump` from the team Box link into `snapshots/` |
| smoke says `0 chunks` | Restore a snapshot (section 2, step 3) |
| `... not found locally. Download it from the team Box link` | The raw file is not in `data\raw\`; download it, or ignore if you only need the passage |
| `sha256 mismatch` in build-snapshot | The file in Box changed or Box renamed it (e.g. `name (1).htm`). Restore the right file or fix the manifest row via PR |
| build-snapshot hangs on a file | Box Drive has it cloud-only; mark the folder "Make available offline" |
| `pytest` PermissionError on a temp folder | Already handled: tests use `.pytest_tmp\` in the repo |

## 6. Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
```bash
.venv/bin/python -m pytest -q
```
No database or API key needed; the paid providers are tested with fake clients.
