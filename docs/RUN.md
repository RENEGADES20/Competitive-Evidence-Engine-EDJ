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
to test with a real model; then set `LLM_PROVIDER=anthropic` and your `ANTHROPIC_API_KEY`
(or `LLM_PROVIDER=deepseek` and `DEEPSEEK_API_KEY`, section 7).
Teammates leave `CORPUS_SHARE_PATH` empty. Never commit `.env`.

Corpus owners who ingest documents (tech lead, C1, C2) also install
`pip install -r requirements-ingest.txt` (large: docling pulls in PyTorch) and set
`EDGAR_IDENTITY` to their name and email.

The default setup needs no database extension, no embedding model and no download: search is
Postgres full-text search (ADR-001), and vectors are an optional module that is **off** by
default (`CEE_VECTORS=off` in `.env`, ADR-009). Skip the next section unless the tech lead asks
you to turn vectors on.

### Vectors (optional, off by default)

Turning vectors on adds embeddings in their own table `chunk_embeddings`. Five steps, once:

1. Install the vectors extra (`fastembed`, `onnxruntime`; no PyTorch). On an Intel Mac it needs
   macOS 13 or newer (`onnxruntime` 1.23.2 is the last version with Intel Mac builds).
   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-vectors.txt
   ```
   ```bash
   .venv/bin/python -m pip install -r requirements-vectors.txt
   ```
2. Get the model (`BAAI/bge-small-en-v1.5`, about 70 MB). It is never downloaded by itself.
   It goes into `FASTEMBED_CACHE_PATH` from `.env` (empty = `.cache/fastembed` in the repo).
   Either download it once:
   ```powershell
   .\.venv\Scripts\python.exe -m cee.retrieve.embed --fetch
   ```
   ```bash
   .venv/bin/python -m cee.retrieve.embed --fetch
   ```
   or, without HuggingFace access, copy the folder `models/models--Qdrant--bge-small-en-v1.5-onnx-Q`
   from the shared corpus folder (team link) into the cache folder, so it has
   `models--Qdrant--bge-small-en-v1.5-onnx-Q/refs` and `.../snapshots`:
   ```powershell
   Test-Path .cache\fastembed\models--Qdrant--bge-small-en-v1.5-onnx-Q\refs\main   # True
   ```
   ```bash
   test -f .cache/fastembed/models--Qdrant--bge-small-en-v1.5-onnx-Q/refs/main && echo True
   ```
   Check it works offline (expect `384 dims`):
   ```powershell
   .\.venv\Scripts\python.exe -m cee.retrieve.embed --query "test"
   ```
   ```bash
   .venv/bin/python -m cee.retrieve.embed --query "test"
   ```
3. Set `CEE_VECTORS=on` in `.env`.
4. Apply the optional SQL (`db/optional/vectors.sql`: pgvector extension + `chunk_embeddings`;
   an older database's `chunks.embedding` column is moved into it). The restore script does
   this when vectors are on, so restoring a snapshot (section 2) is enough:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\restore.ps1
   ```
   ```bash
   bash scripts/restore.sh
   ```
5. Embed every chunk that has no vector yet (also applies the optional SQL; continues where it
   stopped; prints `0 still missing` when done):
   ```powershell
   .\.venv\Scripts\python.exe -m cee.retrieve.embed --missing
   ```
   ```bash
   .venv/bin/python -m cee.retrieve.embed --missing
   ```

To turn vectors off again, set `CEE_VECTORS=off`; the core ignores `chunk_embeddings`.

## 2. Daily use (teammates)

The newest snapshot is named in `snapshots/LATEST.json` (name, sha256, row counts, what
changed). When the tech lead merges a new one, sync your database; no message with steps is
sent any more.

1. Start Docker Desktop and wait until it says "Engine running".
2. In Claude Code type `/sync-db`. Or run the script yourself:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1
   ```
   ```bash
   bash scripts/sync-db.sh
   ```
   It pulls `main`, installs the requirements, starts the database, finds the dump in
   `snapshots/` (or in Box Drive if you have it), checks its sha256, loads it (replaces your
   local database) and runs the smoke test. It ends with `Synced to corpus-... Smoke PASS.`, or
   `Already up to date` when there is nothing to do. It needs no embedding model.
3. If it says `Download corpus-YYYY-MM-DD.dump from the Box snapshots folder ...`: open the
   **team Box link** (pinned in the team chat, never in this repo), go to `snapshots/`,
   download that file into the repo's `snapshots` folder, and run step 2 again. Your database
   was not changed.
4. Start the app and open http://localhost:8501:
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
- Weekly snapshot, from a clean `main`, with notes on what changed (issue numbers, no links):
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "21 transcripts (#108); source context (#111)"
  ```
  ```bash
  bash scripts/build-snapshot.sh --notes "21 transcripts (#108); source context (#111)"
  ```
  It checks every manifest file (exists, sha256 matches), rebuilds the database, dumps
  `corpus-YYYY-MM-DD.dump`, writes `snapshots/LATEST.json` (name, sha256, row counts, build
  time, notes) and copies the dump into Box `snapshots/`. Then publish `LATEST.json` through a
  PR (the script prints the `git switch -c ...` commands); merging it is the notice to the
  team, who run `/sync-db`. No txt with steps is needed. With vectors off (the default)
  steps 4/7 and 7/7 print `skipped (CEE_VECTORS is off)`. With `CEE_VECTORS=on` it also embeds
  every chunk (about 20 minutes on a laptop CPU; the build stops if a chunk has no vector) and
  puts the embedding model into Box `models/` if it is not there yet. `-AllowBranch` / `--allow-branch` skips the clean-main check for testing only; its dump is named `...-test`
  and must not be shared; it writes `snapshots/LATEST-test.json` (never committed) instead of
  `LATEST.json`, and `-Notes` / `--notes` is optional.
- Checklist: [DASHBOARD.md section 8](DASHBOARD.md#8-weekly-snapshot-checklist-tech-lead).

## 5. When it breaks

| Symptom | Fix |
|---|---|
| `running scripts is disabled on this system` | Run scripts as shown: `powershell -ExecutionPolicy Bypass -File scripts\...` |
| `failed to connect to the docker API` / `Starting the database failed` | Start Docker Desktop, wait for "Engine running", run again |
| Docker asks for WSL 2 or virtualization | Install WSL (`wsl --install`), restart; enable virtualization (VT-x/SVM) in BIOS |
| `port is already allocated` on 5432 | Another Postgres is running. Stop it (Services -> postgresql -> Stop), or set `CEE_DB_PORT=5433` in `.env` and change the port in `DATABASE_URL` to `5433` too |
| `connection timeout expired` from Python | The container stopped: `docker compose up -d`, then `docker ps` should show `cee-db` healthy |
| `python` opens the wrong Python / `Permission denied` | Another tool's Python is first on PATH. Always use `.\.venv\Scripts\python.exe` (Mac: `.venv/bin/python`); create the venv with `py -3.11 -m venv .venv` (Mac: `python3.11 -m venv .venv`) |
| Mac: `pwsh: command not found` or a `.ps1` opens as text | Use the `.sh` twin: `bash scripts/<name>.sh` |
| Mac: `permission denied: scripts/restore.sh` | Run it through bash as shown (`bash scripts/restore.sh`), or `chmod +x scripts/*.sh` once |
| `Applying db/optional/vectors.sql ... failed` / `extension "vector" is not available` | Only with `CEE_VECTORS=on`: the database image needs pgvector. Run `docker compose up -d --wait` (the image in docker-compose.yml has it), then restore again; or set `CEE_VECTORS=off` |
| `collation version mismatch` | The image's operating system differs from the one that created your data. Start clean: `docker compose down -v`, `docker compose up -d --wait`, then restore the snapshot |
| `pip install -r requirements-vectors.txt` fails on `onnxruntime` (Intel Mac) | It needs macOS 13 or newer (Apple menu -> About This Mac). Update macOS, or leave vectors off |
| `Embedding model ... is not in ...` from `cee.retrieve.embed` | The model is never downloaded by itself: run `python -m cee.retrieve.embed --fetch`, or copy `models/` from the shared corpus folder (section 1, "Vectors") |
| `No module named 'fastembed'` / `vectors extra is not installed` | Only needed with vectors on: `pip install -r requirements-vectors.txt` |
| `Vectors are off (CEE_VECTORS)` | `--missing` only runs with `CEE_VECTORS=on` in `.env` |
| `CEE_VECTORS='...' is not understood` | Use `CEE_VECTORS=on` or `CEE_VECTORS=off` in `.env` |
| `Embedding ... failed` in build-snapshot (vectors on) | Read the line above it; a chunk without a vector stops the build. Run `python -m cee.retrieve.embed --missing` again (it continues where it stopped) |
| `No snapshot found` | Download the newest `.dump` from the team Box link into `snapshots/` |
| sync-db: `... is not on this computer. Download ...` | Download that exact file from the team Box link `snapshots/` into the repo's `snapshots` folder, run sync-db again |
| sync-db: `Found ..., but it differs from the snapshot in LATEST.json` | The file is old, renamed or still downloading. Download it again (wait until Box finishes), run sync-db again. Your database was not changed |
| sync-db: `git pull failed` | `main` has local changes or commits. Commit them on a branch or ask the tech lead; then run sync-db again |
| sync-db: `You are on '<branch>': not pulling` | The sync used your branch's `snapshots/LATEST.json`. Switch to `main` (`git switch main`) and run it again for the newest one |
| sync-db: `snapshots/LATEST.json not found` | No snapshot has been published through the repo yet: put the newest dump in `snapshots/` and run `scripts\restore.ps1` (Mac: `bash scripts/restore.sh`) |
| smoke says `0 chunks` | Sync a snapshot (section 2, step 2) |
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

## 7. Results: ask with the real model and reproduce the Gate 4 run

The current snapshot is `corpus-2026-11-19` (224 documents: `corpus-2026-11-17` plus five
advisor-headcount sources, #216). Gate 4 was scored **21/30** on `corpus-2026-11-17`
(2026-11-18, scored by the TL agent). The report has all 30 answers with their citations, the
scores and the known gaps: [docs/results/gate4-report.md](results/gate4-report.md). What to
build next: [docs/NEXT.md](NEXT.md).

W11 (map-reduce, ADR-021) was scored on `corpus-2026-11-19` with DeepSeek (#250, adjudicated):
**18/30** with full-text search on `main` ([docs/results/w11-report.md](results/w11-report.md)) and
**22/30** with `hybrid-norerank` on `exp/hybrid`
([report](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/4d656d8/evals/hybrid-eval/corpus-2026-11-19/deepseek/report.md)).
How the pipeline works: [ARCHITECTURE.md, Pipeline](ARCHITECTURE.md#pipeline), or the app's
Architecture page.

**How many calls one question makes** (ADR-021: the calls follow the question): one planner call
(none when the plan is reused), one extraction call per firm, at most one re-extraction per firm
with a re-searched cell, and at most one reduce call (none when code writes the answer). A
one-firm question is 2 to 4 calls; a five-firm question 7 to 12. Every call is
logged with tokens and cost.

**Run each retrieval mode.** The engine is chosen by `RETRIEVAL_MODE` (app) or `--mode` (eval);
the firm, segment and time filters are the same SQL in every mode. The commands below are free
(mock provider, 0 calls); add `--real --max-calls <n>` and a provider as in the blocks further
down for model answers.

Full-text search (`fts`) on `main`, the default:
```powershell
git switch main
.\.venv\Scripts\python.exe -m streamlit run src\ceepp\streamlit_app.py
.\.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17
```
```bash
git switch main
.venv/bin/python -m streamlit run src/cee/app/streamlit_app.py
.venv/bin/python scripts/eval_run.py --as-of 2026-11-17
```
Hybrid without the reranker (`hybrid-norerank`) on `exp/hybrid`. It needs vectors on and every
chunk embedded (section 1, "Vectors"); `hybrid` (with the reranker) also needs the reranker model
(`exp/hybrid` RUN.md, "Hybrid retrieval"). The app reads `RETRIEVAL_MODE` from the environment or
`.env`; the eval takes `--mode fts | hybrid | hybrid-norerank`:
```powershell
git switch exp/hybrid
$env:CEE_VECTORS="on"; $env:RETRIEVAL_MODE="hybrid-norerank"
.\.venv\Scripts\python.exe -m streamlit run src\ceepp\streamlit_app.py
.\.venv\Scripts\python.exe scripts\eval_run.py --mode hybrid-norerank --as-of 2026-11-17
```
```bash
git switch exp/hybrid
export CEE_VECTORS=on RETRIEVAL_MODE=hybrid-norerank
.venv/bin/python -m streamlit run src/cee/app/streamlit_app.py
.venv/bin/python scripts/eval_run.py --mode hybrid-norerank --as-of 2026-11-17
```
Switch back with `git switch main` (and unset both variables, or open a new terminal).

**Ask a question with the real model** (paid: the calls above, planner, extraction per firm,
re-extraction and reduce; CLAUDE.md "Paid API calls"). Put your `ANTHROPIC_API_KEY` in `.env` and set the provider for this session only, so
`.env` stays on mock:
```powershell
$env:LLM_PROVIDER="anthropic"; .\.venv\Scripts\python.exe -m streamlit run src\cee\app\streamlit_app.py
```
```bash
LLM_PROVIDER=anthropic .venv/bin/python -m streamlit run src/cee/app/streamlit_app.py
```
Open http://localhost:8501, type a question, and click a citation to see the stored passage.
The model is `LLM_MODEL` in `.env` (Gate 4 used `claude-sonnet-5-5`).

**Ask with DeepSeek** (#242; paid, the same calls per question). Put `DEEPSEEK_API_KEY` in `.env`
and keep `DEEPSEEK_BASE_URL=https://api.deepseek.com/beta`; strict tool schemas need the `/beta`
URL. `DEEPSEEK_MODEL` defaults to `deepseek-v4-pro`. Each stage has its own reasoning effort (#272):
`DEEPSEEK_EFFORT_PLAN`, `DEEPSEEK_EFFORT_MAP`, `DEEPSEEK_EFFORT_REDUCE`, each `off | low | high | max`
(`off` = no thinking); leave them empty for the defaults set by the #272 test A (`plans/0272-latency.md`).
`DEEPSEEK_MODEL_MAP` sends only the map calls to another model; `DEEPSEEK_STREAM` (`on | nothink | off`)
streams the calls, so the time to the first token is logged next to the wall time. `DEEPSEEK_THINKING`
is only for the legacy single answer call (`MAP=off`). The Ask page shows the plan first, then each
extraction call's cited evidence as it lands, then the answer.
```powershell
$env:LLM_PROVIDER="deepseek"; .\.venv\Scripts\python.exe -m streamlit run src\cee\app\streamlit_app.py
```
```bash
LLM_PROVIDER=deepseek .venv/bin/python -m streamlit run src/cee/app/streamlit_app.py
```
Planned real runs of a few questions (CLAUDE.md "Paid API calls"):
```powershell
$env:LLM_PROVIDER="deepseek"; .\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --max-calls 6 --questions Q1,Q22,Q24 --as-of 2026-11-17
```
```bash
LLM_PROVIDER=deepseek .venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --max-calls 6 --questions Q1,Q22,Q24 --as-of 2026-11-17
```
If DeepSeek answers 402 (balance used up), 429 (rate limit) or 401 (key rejected), the question
stops with that message and nothing is saved. Top up, wait or fix the key, then run again; saved
outputs are reused.

**Answer latency** (#272, free: reads saved records). `scripts/latency_report.py` prints, per question,
the critical path (plan + slowest extraction call + slowest re-extraction + reduce) and the time to the
first cited evidence, and per stage the wall time, time to first token and tokens (p50 / p90 / max):
```powershell
.\.venv\Scripts\python.exe scripts\latency_report.py <run folder>\raw --title "my run"
```
```bash
.venv/bin/python scripts/latency_report.py <run folder>/raw --title "my run"
```
The #272 runs use `docs/results/w12-latency/run-latency.*` (one phase `plan | count | run`, every setting
pinned; paid except `count`) and `run-mock.*` (0 calls). Run them from a clean worktree at the commit
under test; the key file is copied in and removed again:
```powershell
powershell -File docs\results\w12-latency\run-latency.ps1 -Wt <worktree> -Out a-c1 -Cache <cache dir> -MaxCalls 0 -Phase count -GateSha <commit> -Questions Q5,Q10 -EffortPlan off -EffortMap low -EffortReduce low
powershell -File docs\results\w12-latency\run-mock.ps1 -Wt <worktree> -Out mock-fts
```
```bash
WT=<worktree> OUT=a-c1 CACHE=<cache dir> MAXCALLS=0 PHASE=count GATE_SHA=<commit> QUESTIONS=Q5,Q10 EFFORT_PLAN=off EFFORT_MAP=low EFFORT_REDUCE=low ENV_FILE=<repo>/.env bash docs/results/w12-latency/run-latency.sh
WT=<worktree> OUT=mock-fts bash docs/results/w12-latency/run-mock.sh
```

**Check only the question planner** (#245; paid: one planner call per question, no answer call).
`--plan-only` makes the planner calls, then searches each plan for free and reports the aspects,
the sub-questions (firm x aspect) and how many tokens the answer call would read:
```powershell
$env:LLM_PROVIDER="deepseek"; .\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 9 --questions Q19,Q11,Q23,Q24,Q1,Q3,Q22,Q12,Q15 --as-of 2026-11-17
```
```bash
LLM_PROVIDER=deepseek .venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 9 --questions Q19,Q11,Q23,Q24,Q1,Q3,Q22,Q12,Q15 --as-of 2026-11-17
```
If the provider rejects the planner request itself (HTTP 400), the run stops after that one call.

**`MAP` in your own `.env`** (#247): the map-reduce flow is now the default (`MAP=on`). A `.env`
copied from `.env.example` before #247 says `MAP=off`, which keeps the old single answer call. Delete
that line or set `MAP=on` (Windows: `notepad .env`; Mac: `open -e .env`). The eval and the verify-cee
driver set it themselves; the app reads your `.env`.

**Check the reduce step** (#247: one call writes the answer from the evidence matrix). Free on the
mock (the eval maps and reduces unless `--legacy`); paid with `--real`: planner calls for plans not
yet cached, the map calls, then one reduce call per question (none when code builds the answer).
Plan first, count the map calls for free, then run:
```powershell
.\.venv\Scripts\python.exe scripts\eval_run.py --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
$env:LLM_PROVIDER="deepseek"
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 3 --questions Q1,Q3,Q22 --as-of 2026-11-17
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 0 --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --max-calls <cap from the count> --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
```
```bash
.venv/bin/python scripts/eval_run.py --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
export LLM_PROVIDER=deepseek
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 3 --questions Q1,Q3,Q22 --as-of 2026-11-17
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 0 --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --max-calls <cap from the count> --questions Q11,Q19,Q23,Q24,Q26,Q1,Q3,Q22 --as-of 2026-11-17
```
The cap of the last command is the number the 0-call count gives: its round-1 map calls, plus at
most one re-extraction per firm with a re-searched cell, plus one reduce call per question; write it
down before the run (#247 part 2: never a fixed number from an earlier run).
Every reduce call is saved in `.eval-runs/cache/` (`<Q>-reduce-<key>.json`: valid, invalid or failed)
and never made again; a 400 stops the run. `--legacy` runs the old single answer call instead.

**Cost per question, resuming a run and sharing plans** (#248; all free: 0 calls). Every call of the
flow (plan, map per firm, re-extraction, reduce) is saved in the cache and reused, so a stopped run is
resumed by running the same command again: only the calls not yet saved are made, within
`--max-calls`. Each question in `report.json` has `cost`: calls by type, new and reused, tokens
(including DeepSeek's cache-hit tokens), `usd` (every call the answer used), `usd_new` (spent in
this run), `usd_peak` (all at the peak price) and peak / off-peak calls; `summary.cost` has the run
total, and `report.md` a cost line and column. Prices and their source: `config/pricing.yaml`.
DeepSeek is cheaper off-peak; a call is priced by the time it finished, in UTC.

Records written before #248 store a time without a UTC offset. They were all written in
America/Chicago (UTC-6 in November), so a DeepSeek run over a cache holding them needs
`--naive-tz America/Chicago`; without it the run stops before any call (exit 2). New records carry
their offset. To price a folder of saved records (a run's `raw/`, the cache, a results folder):
```powershell
.\.venv\Scripts\python.exe scripts\eval_cost.py docs\results\0242-deepseek-raw --naive-tz America/Chicago
```
```bash
.venv/bin/python scripts/eval_cost.py docs/results/0242-deepseek-raw --naive-tz America/Chicago
```
A fixed offset works too (`--naive-tz=-06:00`; write it with `=`, because it starts with a minus).
`--cache <folder>` reads records from another folder (e.g. a copy, for a 0-call replay with
`--max-calls 0`). `--reuse-plans PROVIDER:MODEL` takes every plan from the saved planner records and
never calls the planner, so two runs (e.g. fts on main and hybrid on exp/hybrid) answer from the same
plans; a missing plan stops the run before any search:
```powershell
$env:LLM_PROVIDER="deepseek"
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --max-calls 0 --reuse-plans deepseek:deepseek-v4-pro --questions Q1,Q3 --as-of 2026-11-17
```
```bash
LLM_PROVIDER=deepseek .venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --max-calls 0 --reuse-plans deepseek:deepseek-v4-pro --questions Q1,Q3 --as-of 2026-11-17
```

**Check the map step** (#246: extraction per firm, corrective re-search, evidence matrix; on in the
app since #247). Free on the mock; paid with `--real --map-only` (planner calls for
plans not yet cached, then one extraction call per firm plus research, and at most one re-extraction
per firm; no answer call). Plan first, count for free, then map:
```powershell
.\.venv\Scripts\python.exe scripts\eval_run.py --map --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
$env:LLM_PROVIDER="deepseek"; $env:MAP="on"
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 5 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 0 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
.\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 43 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
```
```bash
.venv/bin/python scripts/eval_run.py --map --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
export LLM_PROVIDER=deepseek MAP=on
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --plan-only --max-calls 5 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 0 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
.venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --map-only --max-calls 43 --questions Q11,Q19,Q23,Q24,Q26 --as-of 2026-11-17
```
The `--max-calls 0` run makes no call and lists, per question, the extraction calls it would make
(`map_capped_calls`); a call skipped at the cap writes no cache file. Every call is saved in
`.eval-runs/cache/` (valid, invalid or failed) and never made again.

**Check retrieval for all 30 questions, free** (mock provider, no calls; compares with the
committed baseline of the current snapshot):
```powershell
.\.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json
```
```bash
.venv/bin/python scripts/eval_run.py --as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-19/report.json
```
Expected (35 questions since #244, sub-questions since #245): 33 PASS / 2 FAIL. Q19 is a
pattern-coverage check (its expected competitor press is not on the theme in this corpus); Q33's
expected sources are research reports, which a five-firm question without a theme does not search.
Refusal 5/5 on the baseline's keyed gap questions (8/8 with Q31-Q35).
The Gate 4 baseline stays in `evals/baselines/corpus-2026-11-17/` (same result on that snapshot).

**Reproduce the Gate 4 answers** (paid: up to 30 calls; needs the tech lead's OK). Gate 4 ran on
`corpus-2026-11-17`, so load that snapshot first. Put `corpus-2026-11-17.dump` in the repo's
`snapshots/` folder (teammates: download it from the team Box link; the tech lead copies it from
Box `snapshots/`), then restore it:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 snapshots\corpus-2026-11-17.dump
```
```bash
bash scripts/restore.sh snapshots/corpus-2026-11-17.dump
```
Every output is saved under `.eval-runs\cache\` and reused, so a second run of unchanged code
costs nothing:
```powershell
$env:LLM_PROVIDER="anthropic"; .\.venv\Scripts\python.exe scripts\eval_run.py --real --naive-tz America/Chicago --max-calls 30 --as-of 2026-11-17
```
```bash
LLM_PROVIDER=anthropic .venv/bin/python scripts/eval_run.py --real --naive-tz America/Chicago --max-calls 30 --as-of 2026-11-17
```
The run writes `report.md` and `report.json` in its run folder. The model is not deterministic,
so new answers can differ in wording from the report; the score is a human (or agent) reading of
each answer against `passes_if` in `evals/questions.yaml`, not a number the script prints.
When you are done, run `/sync-db` to return to the current snapshot `corpus-2026-11-19`.
