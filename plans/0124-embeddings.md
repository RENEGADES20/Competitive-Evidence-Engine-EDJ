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
C: is nearly full. Every download in this task goes to D:. pip and HuggingFace use the tech
lead's shared dev cache (user env vars `PIP_CACHE_DIR=D:\DevTools\cache\pip`,
`HF_HOME=D:\DevTools\cache\huggingface`); the fastembed model cache is project-specific
(user env var `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`). Commands set all of them
explicitly because a running shell may not have the user env vars; TMP/TEMP are set per command
so pip does not unpack wheels on C::
```powershell
$env:PIP_CACHE_DIR = "D:\DevTools\cache\pip"
$env:HF_HOME = "D:\DevTools\cache\huggingface"
$env:FASTEMBED_CACHE_PATH = "D:\ALLPROJECTS\EDJ\cache\fastembed"
New-Item -ItemType Directory -Force "D:\ALLPROJECTS\EDJ\cache\tmp" | Out-Null   # must exist before TMP/TEMP point at it
$env:TMP = "D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP = $env:TMP   # pip unpacks wheels in TEMP
```
Git Bash runs use the same paths (`mkdir -p /d/ALLPROJECTS/EDJ/cache/tmp` first, then `export PIP_CACHE_DIR=/d/DevTools/cache/pip
HF_HOME=/d/DevTools/cache/huggingface FASTEMBED_CACHE_PATH=/d/ALLPROJECTS/EDJ/cache/fastembed
TMP=/d/ALLPROJECTS/EDJ/cache/tmp TEMP=/d/ALLPROJECTS/EDJ/cache/tmp`). Teammates: if
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
Results 2026-10-30, Windows 11 (i5-13420H, 16 GB), commit 37e88d0 for every check below.
- [x] **Every chunk in the new snapshot has an embedding:** after `build-snapshot.ps1 -AllowBranch`
      and again after `bash scripts/build-snapshot.sh --allow-branch` (manifest of corpus-2026-10-29,
      current main):
      `docker exec cee-db psql -At -U cee -d cee -c "SELECT count(*) FROM chunks WHERE embedding IS NULL"` -> `0`,
      and `SELECT count(*) FROM chunks` = the build's chunk count; `SELECT vector_dims(embedding) FROM chunks LIMIT 1` -> `384`.
      **Result:** ps1 build (2nd attempt, see log) `0|17183|384`, "17183 embedded, 0 still NULL (1106 s)", 19.5 min total;
      sh build `0|17183|384`, "17183 embedded, 0 still NULL (1117 s)", 19.6 min total. Both: 111 documents, 17,183 chunks
- [x] **Only NULL rows are embedded:** second `python -m cee.retrieve.embed --missing` on the built DB -> "0 embedded, 0 still NULL", runs in seconds; pytest fake-connection test asserts the `embedding IS NULL` filter.
      **Result:** "0 embedded, 0 still NULL" in 0.8 s; a stopped run also resumed (3,840 done, then the other 13,343 embedded, none twice); `test_fill_missing_embeds_only_null_rows_in_batches` passes
- [x] **The vectors survive the snapshot:** `restore.ps1` and `restore.sh` of the `-test` dump -> NULL count `0`, `chunks_embedding_idx` present, `python -m cee.smoke` PASS.
      **Result:** both `0|17183`, index present, smoke PASS (restore 17.3 s / 19 s, vs 7.8 s for corpus-2026-10-29: the HNSW index is built at restore)
- [x] **pip install, Windows:** step 1 succeeds, `pip check` -> "No broken requirements found". **Result:** as expected (10 s)
- [x] **pip install, Intel Mac and Apple Silicon (Python 3.11), resolver:** step 2 dry runs for `macosx_13_0_x86_64` and `macosx_14_0_arm64` resolve with wheels only (no sdist build).
      **Result:** win_amd64, macosx_13_0_x86_64, macosx_14_0_arm64 all exit 0 with `--only-binary=:all:`; fastembed 0.9.1, onnxruntime 1.23.2, numpy 2.4.6, tokenizers 0.23.3, mmh3 5.3.1 on all three
- [ ] **pip install on a real Mac (Intel and Apple Silicon):** open, needs a teammate; the PR says `Part of #124`
- [x] **Query embedding offline:** `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` **unset** in the shell
      (`Remove-Item Env:HF_HUB_OFFLINE, Env:TRANSFORMERS_OFFLINE -ErrorAction SilentlyContinue`; bash `unset HF_HUB_OFFLINE TRANSFORMERS_OFFLINE`),
      sockets blocked in-process, timed with `Measure-Command` / `time`:
      `python -c "import socket; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(OSError('network off')); from cee.retrieve.embed import embed_query; v=embed_query('advisor headcount'); print(len(v))"` -> `384`, no error, under 10 s.
      `embed.py` does not set `HF_HUB_OFFLINE` itself; it passes `local_files_only=True` to fastembed on the first load attempt (so a cached model needs no request), and only downloads when that fails.
      **Result:** PowerShell `384`, exit 0, 1.9 s (`HF_HUB_OFFLINE set? False`); Git Bash `384`, 2.0 s
- [x] **Offline from the Box copy:** same conditions (`HF_HUB_OFFLINE` unset, sockets blocked); `FASTEMBED_CACHE_PATH` points at a fresh folder under `D:\ALLPROJECTS\EDJ\cache\` holding only the files copied from `<CORPUS_SHARE_PATH>\models\`; the same command -> `384`, no error, under 10 s; folder deleted afterwards.
      **Result:** 6 files copied (`refs/main` + 5 snapshot files, 67 MB), `384`, exit 0, 1.9 s; folder deleted. The bash `copy_model_to_share` (`cp -RL`) was also run into a scratch folder: same 6 files, second call "already in"; deleted
- [x] **Linked questions:** none directly (issue). Q1-Q30 must not change: covered by "Retrieval unchanged" below
- [x] **Disk rule:** model files only under `D:\ALLPROJECTS\EDJ\cache\fastembed`; no `fastembed_cache` in `%TEMP%` on C:.
      **Result:** no `fastembed_cache` in the C: temp folder, no `~\.cache\huggingface`, no new pip/onnx/hf folders under `C:\Users\14370` (`AppData\Local\pip` dates from 2026-02-13); no `<repo>/.cache`. The only new files on C: are in the Box Drive folder (`CORPUS_SHARE_PATH` is on C: by design): `models/` (67 MB, kept); the test dumps were deleted
- [x] **Retrieval unchanged:** `eval_run.py --as-of 2026-10-29 --baseline .eval-runs/p123-with-vector/report.json` on the restored `-test` snapshot -> identical `chunk_ids` Q1-Q30 (27 PASS / 3 FAIL), mock provider.
      **Result:** `.eval-runs/p124-test-snapshot`: PASS 27 / FAIL 3, all 30 UNCHANGED, `chunk_ids` identical on all 30 (568 ids compared), 0 real calls
- [x] **Snapshot size reported in the PR:** **Result:** 37.6 MB (ps1) / 37.5 MB (sh) vs 4.4 MB for `corpus-2026-10-29.dump`; embedding step ~18.5 min; restore 17-19 s vs 7.8 s
- [x] `pytest -q` passes; `python scripts/verify_cee.py run` all features PASS (mock).
      **Result:** 228 passed; verify-cee all 7 features PASS on corpus-2026-10-30-test (`.verify-runs/20261030-022555-37e88d0`)
- [x] Windows/Mac twins: `_common` helper and build-snapshot steps exist in `.ps1` and `.sh`; every new RUN.md PowerShell block has a bash block
- [x] Cleanup: no `*-test.dump` in `snapshots/` or `<CORPUS_SHARE_PATH>/snapshots/`; local DB restored to `corpus-2026-10-29`.
      **Result:** 0 test dumps in both folders; `corpus-2026-10-29` restored (17,183 chunks, embeddings NULL as published), smoke PASS
- [x] Paid API calls: 0 (embedding is local ONNX; LLM only on the mock provider)

## Risks for the reviewer
- ADR-001 says "`chunks.embedding` exists but stays NULL". This task fills the column but no
  retrieval reads it, so FTS-only behavior (the decision) holds; rewording the ADR belongs with #125,
  which needs the comparison run ADR-001 asks for. This plan does not edit `docs/DECISIONS.md`.
- Pinning `onnxruntime==1.23.2` (older than latest) is deliberate for Intel Macs; Intel Macs on macOS 12
  or older cannot install it (RUN.md row).
- Snapshot grows from 4.4 MB to roughly 30 MB; restore rebuilds the HNSW index (time measured).
  Measured: 37.5 MB; restore 17-19 s instead of 7.8 s.
- A real Mac run is not available to the agent; only the resolver dry-run proves the Mac wheels.
- `fastembed` 0.9.1 was released 2026-10-24 (six days ago); if it misbehaves, fall back to 0.8.x
  with the same onnxruntime pin and log it here.

## For the PR body (reviewer notes on the plan, 2026-10-30)
- ADR-001's sentence "`chunks.embedding` exists but stays NULL" is no longer literally true after
  this merge (FTS-only retrieval still holds); #125's plan supersedes or rewords it with a new ADR.
- No published snapshot carries vectors yet (the `-test` dumps are deleted, local DB back on
  `corpus-2026-10-29`): Progress line "Next" says the first real `build-snapshot` on clean main
  publishes the first vector snapshot, which #125 needs on teammates' machines.
- `src/cee/retrieve/embed.py` sits in the retrieval package (S1 area): tag S1 for information; no
  S1 file is edited.
- Cleanup keeps Box `models/` on purpose: the `-AllowBranch` build copies the real model there and
  it is meant to stay.

## Progress log
- 2026-10-30 00:46 - plan written; branch `tl/124-embeddings` from main 9c33662. Checked fastembed 0.9.1 model table (bge-small-en-v1.5, 384, MIT, 0.067 GB) and onnxruntime wheels (Intel Mac only up to 1.23.2); nothing installed
- 2026-10-30 00:49 - TL correction: pip and HuggingFace use the shared dev cache (`PIP_CACHE_DIR=D:\DevTools\cache\pip`, `HF_HOME=D:\DevTools\cache\huggingface`), not `D:\ALLPROJECTS\EDJ\cache\`; `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed` stays project-specific. Disk rule section updated
- 2026-10-30 00:52 - plan review round 1 (CHANGES REQUESTED): both offline checks now run with `HF_HUB_OFFLINE` unset (sockets blocked, 384 / no error / under 10 s); embed.py relies on `local_files_only=True`, not the env var. Non-blocking: create `cache\tmp` before TMP/TEMP, Linked questions line added, other notes listed under "For the PR body"
- 2026-10-30 00:54 - plan approved (review round 2, Blocking: none); build started
- 2026-10-30 00:56 - `pip install -r requirements.txt` with the disk-rule variables: installed fastembed 0.9.1, onnxruntime 1.23.2, mmh3, loguru, py-rust-stemmers, flatbuffers, coloredlogs (10 s); `pip check` -> "No broken requirements found". Wheels-only dry runs for win_amd64, macosx_13_0_x86_64, macosx_14_0_arm64: all exit 0 (same versions everywhere)
- 2026-10-30 00:58 - embed.py + tests (5 passed, 1 skipped before the model existed). First `--query`: model downloaded into `D:\ALLPROJECTS\EDJ\cache\fastembed` (66.5 MB `model_optimized.onnx`, snapshot aa8f8b0), `384 dims`, 9.9 s incl. download. No `fastembed_cache` in the C: temp folder, no `~\.cache\huggingface`. The cache has a `files_metadata.json` with Windows-style paths, so the Box copy takes only `refs/` + `snapshots/` (as planned)
- 2026-10-30 01:00 - `_common` helpers, build-snapshot steps (ps1/sh), `.env.example`, `.gitignore`, RUN.md, DASHBOARD.md written; PowerShell test build running. Note: `CORPUS_SHARE_PATH` (Box Drive) is on C: by design, so the test dump and Box `models/` (~67 MB) land there through Box Drive
- 2026-10-30 01:09 - PowerShell test build #1 FAILED at step 4/7 after 3,840 of 17,183 chunks (8.7 min): ONNX Runtime could not allocate a 3.2 GB buffer for the attention layer (256 texts x 512 tokens per model call). Also slow: ~7.7 chunks/s, i.e. ~37 min for the corpus. Fix: model calls of 32 texts (`EMBED_BATCH`; commits stay per 256 rows) and chunks embedded shortest first (each batch is padded to its longest text). Resuming `--missing` on the half-built database (also tests resume); test_embed 6 passed with the real model
- 2026-10-30 01:39 - resume worked: 13,343 remaining chunks embedded, 0 still NULL, but still slow (29.7 min, ~7.5 chunks/s). A second `--missing`: "0 embedded, 0 still NULL" in 0.8 s. Benchmarked 192 random chunks (avg 1,201 chars) on the i5-13420H: batch 1 -> 15.6, 4 -> 11.1, 8 -> 9.7, 32 -> 5.9, 64 -> 5.2 chunks/s (padding dominates). Set `EMBED_BATCH = 1`: expected ~18 min for 17,183 chunks
- 2026-10-30 01:44 - PowerShell test build #2 started from scratch
- 2026-10-30 02:03 - PowerShell test build #2 PASS: 17,183 embedded in 1,106 s, 0 NULL, dump 37.6 MB, model copied to Box `models/` (19.5 min total)
- 2026-10-30 02:22 - bash test build PASS: 17,183 embedded in 1,117 s, 0 NULL, dump 37.5 MB, Box `models/` "already in" (19.6 min). Its dump replaced the ps1 one (same name); the restores below used it
- 2026-10-30 02:25 - offline checks PASS (main cache and Box copy, `HF_HUB_OFFLINE` unset, sockets blocked, ~2 s); restore.ps1/restore.sh of the test dump PASS; eval identical to p123-with-vector; pytest 228 passed; verify-cee PASS
- 2026-10-30 02:27 - cleanup: test dumps deleted from `snapshots/` and Box `snapshots/`, `corpus-2026-10-29` restored, smoke PASS; nothing new on C: outside the Box Drive folder. Open: real Mac install (teammate); first real snapshot with vectors (TL, after merge)
