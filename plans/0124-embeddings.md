# 0124 - Embed every chunk at snapshot build (fastembed, offline-capable)

Issue: #124    Role: TL    Spec: docs/ARCHITECTURE.md (schema), ADR-001 (docs/DECISIONS.md)

## Goal
`build-snapshot` (Windows and Mac) fills `chunks.embedding` for every chunk with
`BAAI/bge-small-en-v1.5` (384 dims, matches `db/upgrade.sql`), so the vectors travel inside the
snapshot and teammates never embed the corpus. A question can be embedded on any laptop with the
network off once the model is cached. Retrieval does not change (vectors are used only by #125).

## Facts checked before planning (PyPI / GitHub / HuggingFace, 2026-10-30, nothing installed)
- `fastembed` 0.9.1 (Apache-2.0, pure-Python wheel, Python >=3.10): ONNX Runtime, no torch.
  Deps: numpy, onnxruntime, tokenizers, huggingface-hub <2.0, loguru, mmh3, py-rust-stemmers,
  pillow, requests, tqdm. The venv already has numpy 2.4.6, huggingface_hub 1.33.0, tokenizers,
  pillow, requests, tqdm; no onnxruntime yet (no conflict with docling/rapidocr).
- Model entry in `fastembed/text/onnx_embedding.py` (v0.9.1): `BAAI/bge-small-en-v1.5`, `dim=384`,
  `license="mit"`, `size_in_GB=0.067`, source HF repo `Qdrant/bge-small-en-v1.5-onnx-Q`
  (`model_optimized.onnx` + tokenizer files, MIT). Download about 70 MB.
- Cache dir: `TextEmbedding(cache_dir=...)`, else env `FASTEMBED_CACHE_PATH`, else
  `<system temp>/fastembed_cache` (C: drive on Windows; never used here, we always pass `cache_dir`).
  `local_files_only=True` loads from the cache without any network request.
- **Intel Mac risk:** onnxruntime stopped shipping macOS x86_64 wheels after **1.23.2**
  (latest 1.31.1 has only macOS arm64). 1.23.2 has cp311 wheels for win_amd64, macosx_13_0_arm64
  and macosx_13_0_x86_64, and fastembed 0.9.1 accepts it (`>=1.17,!=1.20.0,!=1.24.0,!=1.24.1`
  on 3.11). So we pin `onnxruntime==1.23.2` for everyone: same runtime on every machine (corpus
  and query vectors from the same build), and Intel Macs install a wheel. Intel Macs need macOS 13+.
  numpy 2.4.6, tokenizers 0.23.x, mmh3 5.3.x, py-rust-stemmers 0.1.8 all have Intel and Apple
  Silicon cp311 wheels.

## Disk rule (TL machine)
C: is nearly full. Every download in this task goes under `D:\ALLPROJECTS\EDJ\cache\`; commands
set the variables explicitly because a running shell may not have the user env vars (this shell has
`HF_HOME=D:\DevTools\cache\huggingface`, `PIP_CACHE_DIR=D:\DevTools\cache\pip`, no `FASTEMBED_CACHE_PATH`):
```powershell
$env:PIP_CACHE_DIR = "D:\ALLPROJECTS\EDJ\cache\pip"
$env:HF_HOME = "D:\ALLPROJECTS\EDJ\cache\huggingface"
$env:FASTEMBED_CACHE_PATH = "D:\ALLPROJECTS\EDJ\cache\fastembed"
$env:TMP = "D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP = $env:TMP   # pip unpacks wheels in TEMP
```
Git Bash runs use the same paths (`export ...=/d/ALLPROJECTS/EDJ/cache/...`). Teammates: if
`FASTEMBED_CACHE_PATH` is empty in `.env` and the environment, the model goes to
`<repo>/.cache/fastembed` (git-ignored), so it sits next to the repo, never in a system temp folder.

## Files to change
- `requirements.txt` - add `fastembed==0.9.1`, `onnxruntime==1.23.2` (comment: last version with Intel Mac wheels)
- `src/cee/retrieve/embed.py` (new) - `MODEL = "BAAI/bge-small-en-v1.5"`, `DIM = 384`;
  `cache_dir()` (env/.env `FASTEMBED_CACHE_PATH`, else `<repo>/.cache/fastembed`; sets `HF_HOME`
  to `<cache parent>/huggingface` only if unset); `model()` cached, tries `local_files_only=True`
  first and downloads only if the model is missing; `embed_texts(texts)`, `embed_query(q)`;
  `fill_missing(conn, batch=256)`: `SELECT chunk_id, prefix || ' ' || text FROM chunks WHERE
  embedding IS NULL ORDER BY chunk_id`, embed in batches, `UPDATE chunks SET embedding = %s::vector`
  with a `'[...]'` literal (no pgvector Python package), commit per batch so a stopped run resumes;
  CLI `python -m cee.retrieve.embed --missing` (prints embedded / still NULL, exit 1 if any NULL
  remains) and `--query "<text>"` (prints dim and first values; the offline check)
- `tests/test_embed.py` (new) - no DB, no network: cache-dir resolution, vector literal, `fill_missing`
  with a fake model and fake connection (selects only `embedding IS NULL`, batches, commits); one
  test with the real model, skipped unless it is already in the cache (dim 384, unit length)
- `scripts/_common.ps1`, `scripts/_common.sh` - `Set-ModelCache` / `model_cache_env`: export
  `FASTEMBED_CACHE_PATH` (from env/.env, else `<repo>/.cache/fastembed`) and `HF_HOME` if unset,
  so a shell without the user env vars never downloads to C: or a temp folder
- `scripts/build-snapshot.ps1`, `scripts/build-snapshot.sh` - new step after ingestion:
  `python -m cee.retrieve.embed --missing` (fails the build if any chunk stays NULL); a step that
  copies the cached model (`refs/` + `snapshots/`, symlinks resolved) to `<CORPUS_SHARE_PATH>/models/`
  when it is not there yet; steps renumbered 1/7..7/7
- `.env.example` - `FASTEMBED_CACHE_PATH=` with a comment (empty = `<repo>/.cache/fastembed`)
- `.gitignore` - `.cache/`
- `docs/RUN.md` - install note (fastembed is in core requirements, ~70 MB model on first use);
  "Embedding model" subsection with Windows and Mac blocks: check `python -m cee.retrieve.embed
  --query "test"`, offline route (download Box `models/` into `.cache/fastembed/`); build-snapshot
  description mentions the embedding step and Box `models/`; troubleshooting rows (Intel Mac
  onnxruntime / macOS 13, model download blocked)
- `docs/DASHBOARD.md` section 8 - one checklist line: `SELECT count(*) FROM chunks WHERE embedding IS NULL` = 0

Not changed: `db/upgrade.sql` (column and index exist, #123), `src/cee/retrieve/fts.py` and all
retrieval/answer code (#125), `scripts/ingest.*` (chunks loaded between snapshots stay NULL until
the next build; #125 must skip NULL vectors), ADR text (see Risks).

## Steps
1. Install into the venv with the disk-rule variables set:
   `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then `pip check`.
2. Cross-platform resolver check (no Mac at hand): for each of `win_amd64`, `macosx_13_0_x86_64`,
   `macosx_14_0_arm64`: `pip install --dry-run --ignore-installed --only-binary=:all: --platform <tag>
   --python-version 3.11 --target D:\ALLPROJECTS\EDJ\cache\tmp\dry -r requirements.txt`.
3. Write `embed.py` + `tests/test_embed.py`; pytest.
4. First model download into `D:\ALLPROJECTS\EDJ\cache\fastembed`; confirm nothing new on C:
   (`%TEMP%\fastembed_cache` absent, no new `~\.cache\huggingface`).
5. `_common` helpers and the build-snapshot steps (ps1 and sh, same order and messages).
6. Test build PowerShell: `build-snapshot.ps1 -AllowBranch`; NULL count; time of the embedding step;
   dump size vs `corpus-2026-10-29.dump` (4.4 MB; expected about +25-30 MB of vectors).
7. Test build bash (Git Bash): `bash scripts/build-snapshot.sh --allow-branch`; same checks.
8. Restore the `-test` dump with `restore.ps1` and `restore.sh` (HNSW index rebuilt at restore;
   note the time), `cee.smoke`, eval FTS unchanged, verify-cee.
9. Offline checks (below), Box `models/` copy check.
10. Clean up: delete `corpus-*-test.dump` from `snapshots/` and `<CORPUS_SHARE_PATH>/snapshots/`,
    delete the temporary offline cache copy, restore `corpus-2026-10-29.dump` so the local DB is
    back to the published snapshot.
11. RUN.md, DASHBOARD.md; finish-task.

Unsure: embedding speed on CPU (17,183 chunks, up to 512 tokens; guess 2-10 min); whether
fastembed's HF download writes anything outside `cache_dir` (step 4 checks); whether Git Bash
`cp -RL` of the HF cache works the same as on macOS (checked in step 7).

## Acceptance
- [ ] **Every chunk in the new snapshot has an embedding:** after `build-snapshot.ps1 -AllowBranch`
      and again after `bash scripts/build-snapshot.sh --allow-branch` (manifest of corpus-2026-10-29,
      current main):
      `docker exec cee-db psql -At -U cee -d cee -c "SELECT count(*) FROM chunks WHERE embedding IS NULL"` -> `0`,
      and `SELECT count(*) FROM chunks` = the build's chunk count; `SELECT vector_dims(embedding) FROM chunks LIMIT 1` -> `384`
- [ ] **Only NULL rows are embedded:** second `python -m cee.retrieve.embed --missing` on the built DB -> "0 embedded, 0 still NULL", runs in seconds; pytest fake-connection test asserts the `embedding IS NULL` filter
- [ ] **The vectors survive the snapshot:** `restore.ps1` and `restore.sh` of the `-test` dump -> NULL count `0`, `chunks_embedding_idx` present, `python -m cee.smoke` PASS
- [ ] **pip install, Windows:** step 1 succeeds, `pip check` -> "No broken requirements found"
- [ ] **pip install, Intel Mac and Apple Silicon (Python 3.11):** step 2 dry runs for `macosx_13_0_x86_64` and `macosx_14_0_arm64` resolve with wheels only (no sdist build). A real install on a teammate's Mac stays an open item if not done before the PR (then the PR says `Part of #124`)
- [ ] **Query embedding offline:** with sockets blocked in-process and `HF_HUB_OFFLINE=1`:
      `python -c "import socket; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(OSError('network off')); from cee.retrieve.embed import embed_query; v=embed_query('advisor headcount'); print(len(v))"` -> `384`, no error, under 10 s
- [ ] **Offline from the Box copy:** point `FASTEMBED_CACHE_PATH` at a fresh folder under `D:\ALLPROJECTS\EDJ\cache\` holding only the files copied from `<CORPUS_SHARE_PATH>\models\`; the same blocked-socket command -> `384`; folder deleted afterwards
- [ ] **Disk rule:** model files only under `D:\ALLPROJECTS\EDJ\cache\fastembed`; no `fastembed_cache` in `%TEMP%` on C:
- [ ] **Retrieval unchanged:** `eval_run.py --as-of 2026-10-29 --baseline .eval-runs/p123-with-vector/report.json` on the restored `-test` snapshot -> identical `chunk_ids` Q1-Q30 (27 PASS / 3 FAIL), mock provider
- [ ] **Snapshot size reported in the PR:** size of the `-test` dump vs 4.4 MB for `corpus-2026-10-29.dump`, plus embedding-step and restore times
- [ ] `pytest -q` passes; `python scripts/verify_cee.py run` all features PASS (mock)
- [ ] Windows/Mac twins: `_common` helper and build-snapshot steps exist in `.ps1` and `.sh`; every new RUN.md PowerShell block has a bash block
- [ ] Cleanup: no `*-test.dump` in `snapshots/` or `<CORPUS_SHARE_PATH>/snapshots/`; local DB restored to `corpus-2026-10-29`
- [ ] Paid API calls: 0 (embedding is local ONNX; LLM only on the mock provider)

## Risks for the reviewer
- ADR-001 says "`chunks.embedding` exists but stays NULL". This task fills the column but no
  retrieval reads it, so FTS-only behavior (the decision) holds; rewording the ADR belongs with #125,
  which needs the comparison run ADR-001 asks for. This plan does not edit `docs/DECISIONS.md`.
- Pinning `onnxruntime==1.23.2` (older than latest) is deliberate for Intel Macs; Intel Macs on macOS 12
  or older cannot install it (RUN.md row).
- Snapshot grows from 4.4 MB to roughly 30 MB; restore rebuilds the HNSW index (time measured).
- A real Mac run is not available to the agent; only the resolver dry-run proves the Mac wheels.
- `fastembed` 0.9.1 was released 2026-10-24 (six days ago); if it misbehaves, fall back to 0.8.x
  with the same onnxruntime pin and log it here.

## Progress log
- 2026-10-30 00:46 - plan written; branch `tl/124-embeddings` from main 9c33662. Checked fastembed 0.9.1 model table (bge-small-en-v1.5, 384, MIT, 0.067 GB) and onnxruntime wheels (Intel Mac only up to 1.23.2); nothing installed
