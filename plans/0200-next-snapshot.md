# 0200 - Next snapshot: Form ADV, trade press, speaker-turn transcripts

Issue: #200    Role: TL    Spec: docs/DASHBOARD.md section 8 (snapshot checklist), docs/RUN.md
section 4, docs/ARCHITECTURE.md, docs/DECISIONS.md (ADR-006 snapshots, ADR-009 vectors)

## Goal
One new snapshot, built from clean `main`, holds all 219 manifest documents (the 137 of
`corpus-2026-11-16` plus 5 Form ADV brochures, #55/PR #178, and 77 trade-press articles,
#57/PR #186) with earnings-call transcripts chunked by speaker turn (#107/PR #150). It passes the
DASHBOARD section 8 / RUN section 4 checks, is published through the `snapshots/LATEST.json` PR
(merging it is the sync note), and its mock eval is committed as the new baseline under
`evals/baselines/<snapshot>/`. Gate 4 (#121) is scored on it. 0 paid calls.

**Name.** `build-snapshot` stamps the local build date: `corpus-2026-11-17` if it runs today,
`corpus-2026-11-18` if after midnight. Below, `SNAP` = whatever `COMMENT ON TABLE documents`
says after the build; it is announced as is (no renaming: that would break the sha256 in
`LATEST.json`). The branch slug is date-neutral for that reason.

## Facts (read-only, 2026-11-17 22:25, origin/main 960b742)
- `origin/main` = 960b742 (includes #192/#181 budget by firm count, #193/#166 #190 rank floor,
  #196/#179 ADV only for fee questions, #178 Form ADV, #186 trade press, #150 speaker turns).
  Main checkout `D:\ALLPROJECTS\EDJ\repo`: on `main` = 960b742, working tree clean.
- `data/manifest.csv`: **219 rows** (52 pdf, 41 htm, 118 txt, 8 html; doc types: trade 77,
  transcript 32, press 25, research 25, 10-Q 20, supplement 12, deck 12, monthly 6, 10-K 5,
  adv 5); 0 rows with empty `published_at`. Last manifest commits: fd35161 (#186), 5873e08 (#178).
- **Build inputs** (`scripts/build-snapshot.ps1/.sh`):
  - Raw: `CORPUS_SHARE_PATH` in `repo\.env` = Box Drive `C:\Users\14370\Box\EDJ` (value not
    printed). `raw/` holds 219 files; sha256 of all 219 checked by the TL before this issue.
  - The 82 files in the Box folder root (5 `*-ADV-2026.pdf`, 77 `*-TRADE-*.txt`) are the upload
    copies; each is byte-identical to its `raw/` file (`cmp`, 82/82, 0 differ). Nothing is left
    to move into `raw/`; cleaning the root is out of scope.
  - Parse cache `parsed/` (keyed by sha256): docling 2.131.0 `-v2` for **52/52 PDFs** (incl. the
    5 brochures) and edgartools 5.59.1 `-v1` for **41/41 filings**. Installed in `repo\.venv`:
    docling 2.131.0, edgartools 5.59.1; `PARSER_VERSION = 2`, `HTML_PARSER_VERSION = 1`. So the
    build runs no docling and no edgartools parse; txt (118) are read directly, the 8 research
    html pages are parsed live by `webpage.article_text`.
  - Container `cee-db` mounts `repo\snapshots` as `/snapshots` and `repo\db\*.sql` as init
    scripts, and `build-snapshot` refuses a branch other than `main` (`-AllowBranch` names the
    dump `...-test`, not publishable). So the build **runs in the main checkout on `main`**; the
    worktree `D:\ALLPROJECTS\EDJ\wt-snap` (no `.env`, no `.venv`) holds only the commits.
- Database `cee` = `corpus-2026-11-16`, 137 documents, 18,497 chunks. Other databases:
  `cee_84`, `cee_84_rev` (not touched). `sync-db.ps1 -Check` and `sync-db.sh --check` (Git Bash)
  both: exit 0 "up to date: corpus-2026-11-16".
- Expected result from PR #150's scratch DB B (same code as `main` for the corpus, 219 docs):
  **21,143 chunks**, of them 2,852 transcript chunks (longest 1,198 characters), 14 GWIM-tagged
  transcript chunks, `BAC-TR-2026Q2#63` its own GWIM chunk (901 characters); the 18,291
  non-transcript chunks identical to the main-code build.
- `pytest -q` on 960b742 (repo `.venv`): **479 passed** = the floor.
- Baseline convention: `evals/baselines/<snapshot>/report.json` + `report.md` from a mock
  `eval_run.py` run at k=20; one folder at a time (5f43156 replaced `corpus-2026-10-18` with
  `corpus-2026-10-22`). `corpus-2026-11-16` (#120) kept its runs in `cache\ev120` only, so the
  committed baseline is still `corpus-2026-10-22`. This PR replaces it with `SNAP`.
- Open: #199 (C2, transcript slots: doc recall down on Q6/Q11/Q13/Q27 after #150). Measured on
  this snapshot, fixed there, not here. Only open PR: #194 (C1, W9 score, docs).

## Preconditions (checked right before step 2)
- P1: `repo` on `main`, `git status` clean, `git pull --ff-only`, HEAD = `origin/main`. If `main`
  moved past 960b742: list the commits; anything touching `src/cee/ingest/`, `config/`, `db/` or
  `data/manifest.csv` -> re-check the facts above (counts, parse cache) before building, and
  name it in the Progress log.
- P2: no other session uses `repo` or database `cee` during steps 2-3 (the build runs
  `DROP DATABASE cee WITH (FORCE)`). `docker compose down -v` is **not** run.
- P3: Box Drive running; `raw/`, `parsed/`, `snapshots/` available offline.
- P4: this plan reviewed through `/tl-review` on #200 (verdict posted on GitHub) before step 1.

## Files to change
- `plans/0200-next-snapshot.md` - this plan, Progress log, findings.
- `snapshots/LATEST.json` - copied from the build (name, sha256, counts, built_at, notes).
- `evals/baselines/SNAP/report.json`, `report.md` - new mock baseline; `git rm -r
  evals/baselines/corpus-2026-10-22` (as 5f43156 did).
- `README.md` - Status section only (snapshot name, counts, latest retrieval check line).

No code, config, manifest, answer-key or question change. No new script (no .ps1/.sh pair);
compare scripts stay as scratch files in the evidence folder. Raw files and dumps never
committed. `docs/PROGRESS.md` only through the PR's Progress line.

## Steps
Evidence folder `EV` = `D:\ALLPROJECTS\EDJ\cache\ev200` (every log, report and scratch script).
`PY` = `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe`. Every command runs from `repo` on
`main` (the code there = this branch minus this plan), mock provider, vectors off, temp on D:,
no `PYTHONPATH` (so `repo\src` = `main` is used):
```
$env:PYTHONUTF8="1"; $env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; $env:LLM_PROVIDER="mock"; Remove-Item Env:CEE_VECTORS,Env:PYTHONPATH -ErrorAction SilentlyContinue
```
```
export PYTHONUTF8=1 LLM_PROVIDER=mock; unset CEE_VECTORS PYTHONPATH
```
`ASOF` = the build date (`SNAP`'s date), fixed before step 1 and used by every eval run.

1. **Baseline on `corpus-2026-11-16`** (DB `cee`, before the build replaces it), same code:
   - `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`, snapshot `corpus-2026-11-16`.
   - `PY scripts/eval_run.py --as-of ASOF --out EV/base-ASOF` and
     `PY scripts/eval_run.py --as-of 2026-10-29 --out EV/base-1029` (the README's comparison date).
2. **Build** in `repo`:
   - P1-P3; record `git rev-parse HEAD`.
   - DASHBOARD 8 pre-checks: no empty `published_at` (scratch count -> 0); Box root uploads all
     have identical `raw/` copies (re-run the `cmp` loop; any file without one -> stop, ask TL).
   - Notes (no links), written into the Progress log before the build: "219 documents, 82 more
     than corpus-2026-11-16: Form ADV Part 2A brochures for the core five (#55), 90 days of
     trade press for the five (#57). Earnings-call transcripts chunked by speaker turn (#107);
     answer key already remapped. Retrieval since the freeze: budget by firm count with Merrill
     counted once (#181), rank floor (#166), Form ADV only for fee questions (#179)."
   - `powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "<notes>" *> EV\build.log`
     (Mac: `bash scripts/build-snapshot.sh --notes "<notes>" 2>&1 | tee EV/build.log`).
   - Log checks: `219 files OK`; `Select-String -Path EV\build.log -Pattern "parsing with docling|parsing with edgartools"`
     (Mac: `grep -cE "parsing with (docling|edgartools)" EV/build.log`) -> no match;
     `parse cache hit` lines = 93 (52 + 41); `4/7 Embedding skipped`; `Dumping SNAP.dump`;
     `Copying to Box`.
   - If 4/7 says `Embedding every chunk` (`CEE_VECTORS=on` in `repo\.env`): let it finish
     (local, no paid call), then the DASHBOARD 8 vector check
     `docker exec cee-db psql -At -U cee -d cee -c "SELECT count(*) FROM chunks c WHERE NOT EXISTS (SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id)"`
     -> `0`; evals still run with vectors off. Embedding failure or non-zero -> stop, report.
   - A build failure: stop, keep `EV\build.log`, report to the TL; `cee` is then rebuilt by
     `sync-db` (`corpus-2026-11-16` is still `LATEST.json` on `main`).
3. **Snapshot checks** (DB `cee` = `SNAP`):
   - `obj_description('documents'::regclass)` = `SNAP`; documents = 219 and the doc_id set =
     the manifest's 219 (scratch compare); `adv` = 5, `trade` = 77 documents; every document has
     >= 1 chunk.
   - Chunks: total recorded (expected 21,143); transcript chunks = 2,852; GWIM-tagged transcript
     chunks = 14; `BAC-TR-2026Q2#63` tagged GWIM. Non-transcript chunks of the 137 old documents
     identical to `corpus-2026-11-16` (md5 over chunk_id, segment, section, page, text, compared
     against a scratch restore of `corpus-2026-11-16.dump` into `cee_prev_200`, dropped after).
     Any difference -> explained in the findings before publishing.
   - `PY -m cee.smoke` -> PASS; `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`.
   - `PY scripts/page_sweep.py > EV\page_sweep.txt`: all 52 PDFs listed, `MISPLACED 0` on every
     line (always exits 0, so the output is the check).
   - sha256 of `C:\Users\14370\Box\EDJ\snapshots\SNAP.dump` = sha256 of `repo\snapshots\SNAP.dump`
     = `sha256` in `repo\snapshots\LATEST.json`; `docker exec cee-db pg_restore --list /snapshots/SNAP.dump`
     exits 0.
   - Restore test (instead of `docker compose down -v`, which would delete `cee_84`,
     `cee_84_rev`): create `cee_restore_200`, `pg_restore` the **Box** copy into it, `PY -m cee.smoke`
     with `DATABASE_URL=postgresql://cee:cee@localhost:5432/cee_restore_200` -> PASS, drop only
     `cee_restore_200`.
   - `powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1 -Check` and
     `bash scripts/sync-db.sh --check` -> both exit 0, "up to date: SNAP" (they compare with
     `repo\snapshots\LATEST.json`, which the build just wrote).
4. **Mock eval on `SNAP`**:
   - `PY scripts/eval_run.py --as-of ASOF --out EV/snap-ASOF` (no `--baseline`: this is the file
     committed as the baseline, so it carries no local path).
   - `PY scripts/eval_run.py --as-of ASOF --baseline EV/base-ASOF/report.json --out EV/snap-ASOF-vs`
     and `PY scripts/eval_run.py --as-of 2026-10-29 --baseline EV/base-1029/report.json --out EV/snap-1029-vs`.
   - Determinism: `PY scripts/eval_run.py --as-of ASOF --baseline EV/snap-ASOF/report.json --out EV/snap-ASOF-rerun`
     -> 30 UNCHANGED.
   - `PY -m pytest -q` -> all pass, count >= 479.
   - **Stop rule:** any forbidden hit or refusal accuracy below `base-ASOF` -> stop, do not open
     the PR, report to the TL (the dump stays in Box unannounced, named in the report).
5. **Eval delta** (scratch `EV\compare.py` over `base-*` and `snap-*` report.json): per question
   status change, tier-1 doc/passage recall, chunks lost/gained and the document (new ADV,
   trade, re-chunked transcript, or old document). Every PASS -> FAIL and every recall drop
   classified: (a) new document is real evidence -> answer-key extension (C1);
   (b) ranking crowd-out -> S1; (c) document should not answer this question -> C2/C3 tagging;
   (t) transcript re-chunk -> #199 if it is Q6/Q11/Q13/Q27, otherwise a note on #199.
   Q18: report whether ADV chunks are retrieved and the pattern coverage. Findings table goes
   into this plan and the PR; each new class becomes an issue draft (filed after TL approval).
   No fix in this PR.
6. **verify-cee**: `PY scripts/verify_cee.py run` (all features) on `SNAP` -> `VERIFY PASS`;
   evidence folder named in the PR. One re-run on a clearly environmental failure.
7. **Publish**:
   - Copy `repo\snapshots\LATEST.json` to `wt-snap\snapshots\LATEST.json`; in `repo` run
     `git restore snapshots/LATEST.json` -> `git status` clean on `main` (the dump in
     `repo\snapshots\` is git-ignored).
   - In `wt-snap`: copy `EV\snap-ASOF\report.json` and `report.md` to `evals/baselines/SNAP/`,
     `git rm -r evals/baselines/corpus-2026-10-22`; README Status (snapshot, 219 documents,
     chunk count, the latest retrieval check line, Form ADV and speaker-turn sentences updated).
   - Commit, push, open the PR (`Closes #200`), `/finish-task`. Merging it is the sync note;
     hand the TL one chat line: "New snapshot SNAP: run /sync-db". Comment on #121 and #199
     with the snapshot name.
8. Progress log, `/finish-task`.

**Paid calls: none.** Everything runs on the mock provider; the real 30-question run belongs to
#121.

## Acceptance
- [ ] P1: build from clean `main` in `repo`, HEAD = `origin/main` (sha recorded); no empty
      `published_at`; Box root uploads all identical to `raw/`.
- [ ] Build log: `219 files OK`, 0 `parsing with docling|edgartools`, 93 `parse cache hit`,
      `Embedding skipped` (or vector check -> 0), `SNAP.dump` copied to Box.
- [ ] `obj_description` = `SNAP`; documents = 219, doc_id set = manifest; adv 5, trade 77;
      chunk count in LATEST.json and README (expected 21,143, difference explained);
      transcript chunks 2,852; `BAC-TR-2026Q2#63` GWIM; old non-transcript chunks unchanged.
- [ ] `cee.smoke` PASS; `verify_cee.py doctor` DOCTOR PASS; `verify_cee.py run` VERIFY PASS.
- [ ] `EV\page_sweep.txt`: 52 PDFs, `MISPLACED 0` on every line.
- [ ] sha256 Box dump = local dump = LATEST.json; `pg_restore --list` exit 0; scratch restore
      `cee_restore_200` smoke PASS, dropped.
- [ ] `sync-db.ps1 -Check` and `sync-db.sh --check` both exit 0 "up to date: SNAP".
- [ ] Mock eval `snap-ASOF` vs `base-ASOF` (and at 2026-10-29): 0 forbidden hits; refusal
      accuracy >= baseline; PASS/FAIL, tier-1 recall reported; every PASS -> FAIL and recall
      drop classified; rerun 30 UNCHANGED; saved as `evals/baselines/SNAP/`.
- [ ] `pytest -q` all pass (>= 479).
- [ ] `snapshots/LATEST.json` on the branch = the build's; `repo` clean on `main`; README
      Status updated; PR merged = sync note; #121, #199 told the snapshot name.
- [ ] 0 real calls.

## Progress log
- 2026-11-17 22:30 - plan written on `tl/200-next-snapshot` (worktree `D:\ALLPROJECTS\EDJ\wt-snap`)
  from origin/main 960b742. Facts above checked read-only: manifest 219 rows, 0 empty
  `published_at`; parse cache v2 52/52, edgartools v1 41/41; Box root uploads 82/82 identical
  to `raw/`; `cee` = corpus-2026-11-16 (137 docs, 18,497 chunks); both `sync-db` checks exit 0;
  `pytest -q` 479 passed. No file other than this plan changed. Not reviewed yet.
