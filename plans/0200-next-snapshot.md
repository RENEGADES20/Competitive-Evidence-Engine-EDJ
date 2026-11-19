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
  `eval_run.py` run; one folder at a time (5f43156 replaced `corpus-2026-10-18` with
  `corpus-2026-10-22`). `corpus-2026-11-16` (#120) kept its runs in `cache\ev120` only, so the
  committed baseline is still `corpus-2026-10-22` (run at k=20). This PR replaces it with
  `SNAP`. Since #181 `eval_run.py` without `--k` uses the app's budget by firm count (meta
  `"k": "by question"`), so the new baseline is "app budget (no `--k`)", not k=20; every run
  here (base and snap) uses that same default.
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
`ASOF` = **2026-11-17**, fixed at step 1 (the planned build date) and recorded in the Progress
log. Every eval run uses it, whatever `SNAP` ends up being called (if the build crosses
midnight, `SNAP` is `corpus-2026-11-18` and `ASOF` stays 2026-11-17).

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
     against a scratch restore into `cee_prev_200` of the local
     `repo\snapshots\corpus-2026-11-16.dump`, the file `LATEST.json` on `main` names, sha256
     checked against it first; dropped after). Any difference -> explained in the findings
     before publishing. First suspect: #150 added BAC `mention_excludes: "acquisition of
     Merrill"` in `config/entities.yaml`, applied by the segment tagger to every BAC chunk, so
     a non-transcript BAC chunk with that phrase could change segment; also #179/#117/#46/#55
     config changes since 8f92cb1.
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
     chunk count, the latest retrieval check line, Form ADV and speaker-turn sentences updated,
     and the "Gate scores" sentence: Gate 3 scored 16/30 on `corpus-2026-11-16`, #120 / PR
     #195; Gate 4 not scored yet).
   - Commit, push, open the PR (`Closes #200`), `/finish-task`. Merging it is the sync note;
     hand the TL one chat line: "New snapshot SNAP: run /sync-db". Comment on #121 and #199
     with the snapshot name.
8. Progress log, `/finish-task`.

**Paid calls: none.** Everything runs on the mock provider; the real 30-question run belongs to
#121.

## Findings (2026-11-17, snapshot corpus-2026-11-17, mock, 0 paid calls)
Evidence: `D:\ALLPROJECTS\EDJ\cache\ev200\` (`build.log`, `snapcheck.py`/`.txt`, `page_sweep.txt`,
`sha256.txt`, `smoke.txt`, `restore_smoke.txt`, `doctor-*.txt`, `base-1117`, `base-1029`,
`snap-1117`, `snap-1117-vs`, `snap-1029-vs`, `snap-1117-rerun`, `compare.py`, `cmp-1117.txt`,
`cmp-1029.txt`, `recall-drops.txt`, `pytest.txt`, `verify.log`); verify-cee
`D:\ALLPROJECTS\EDJepo\.verify-runs61117-223554-960b742`.

**Build.** `SNAP` = `corpus-2026-11-17` (built 2026-11-18T04:32:08Z = 22:32 local, so the name
and `ASOF` agree). Main checkout on `main` 960b742 = origin/main, clean. Log: `219 files OK`,
0 `parsing with docling|edgartools`, 93 `parse cache hit`, `4/7 Embedding skipped`,
`5/7 Dumping corpus-2026-11-17.dump`, `6/7 Copying to Box`. sha256
`47c1ffca0e755a799abab0b5be99d5b998653d846b49213c9dc587aa939bfae1` for the Box dump, the local
dump and `LATEST.json`.

**Contents.** 219 documents = the manifest's 219 doc_ids (adv 5, trade 77, transcript 32, ...),
0 documents without chunks; **21,143 chunks** (= PR #150's scratch DB B); transcript chunks
2,852 (was 1,689), longest 1,198 characters; 14 GWIM transcript chunks; `BAC-TR-2026Q2#63` GWIM,
901 characters. The 16,808 non-transcript chunks of `corpus-2026-11-16` (restored from the local
`corpus-2026-11-16.dump`, sha256 = `LATEST.json` on main) are all present and identical (md5 over
id, segment, section, page, prefix, text): 0 differ, so the `mention_excludes` suspect did not
fire on any non-transcript chunk.

**Mock eval** (app budget, no `--k`; same code 960b742 on both snapshots):

| Run | PASS / FAIL | FAIL IDs | Tier-1 doc / passage recall | Refusal (gap / all keyed) | Forbidden |
|---|---|---|---|---|---|
| base-1117 (`corpus-2026-11-16`, as of 11-17) | 27 / 3 | Q15, Q19, Q26 | 0.625 / 0.424 | 5/5 / 19/19 | 0 |
| snap-1117 (`corpus-2026-11-17`, as of 11-17) = new baseline | 28 / 2 | Q15, Q19 | 0.547 / 0.420 | 5/5 / 19/19 | 0 |
| base-1029 (`corpus-2026-11-16`, as of 10-29) | 28 / 2 | Q15, Q19 | 0.646 / 0.456 | 5/5 / 19/19 | 0 |
| snap-1029-vs (`corpus-2026-11-17`, as of 10-29) | 28 / 2 | Q15, Q19 | 0.573 / 0.453 | 5/5 / 19/19 | 0 |

Stop rule not hit: 0 forbidden hits, refusal unchanged. No PASS -> FAIL. Rerun on `SNAP`:
30 UNCHANGED. Passage recall on the base side is not comparable for transcript rows: the answer
key on `main` already uses #150's new transcript `chunk_id`s, which on `corpus-2026-11-16` name
different passages; document recall is not affected by that.

- **Q26** FAIL -> PASS (as of 11-17): 15 RJF trade-press chunks inside the 90-day window
  (before, no RJF passage in the window).
- **Q18**: all five `<firm>:adv` patterns hit (one brochure chunk each); coverage 1.0.
  `THEME:regulatory` still 0 hits. Q25 (gap_with_adjacent) now also gets 7 ADV chunks
  (compensation disclosure), refusal still ok.
- **Q4 / Q28**: passage recall up (Q4 0.143 -> 0.571; Q28 doc 0.667 -> 0.833, passage 0.5 -> 0.75),
  the speaker-turn chunks doing what #107 meant.

**Tier-1 document recall drop 0.625 -> 0.547** (as of 11-17), seven questions:

| Q | Doc recall | Expected document lost | Took the slots | Class |
|---|---|---|---|---|
| Q2 | 0.444 -> 0.333 | `RJF-TR-2025Q4` | 3 RJF trade chunks (ranks 1, 8, 15) | b (trade), maybe a |
| Q5 | 0.833 -> 0.667 | `MS-TR-2026Q1` | 5 MS trade chunks (rank 3 first) | b (trade) |
| Q6 | 0.833 -> 0.5 | `RJF-10Q-2026Q2`, `RJF-TR-2025Q2` | 4 RJF trade chunks + re-cut transcripts | t (#199) + b |
| Q11 | 0.875 -> 0.75 | `SCHW-TR-2026Q1` | other transcript turns (`SCHW-TR-2025Q4#5`), no trade | t (#199) |
| Q13 | 0.667 -> 0.5 | `MS-TR-2026Q3` | 3 MS trade chunks + re-cut transcripts | t (#199) + b |
| Q27 | 0.444 -> 0.333 | `BAC-TR-2026Q3` | 3 MER trade chunks at ranks 1-3 | t (#199) + b |
| Q30 (gap) | 1.0 -> 0.5 | `BAC-PR-2026-01-14-01` | 2 MER trade chunks; refusal still ok | b (trade) |

Q6, Q11, Q13, Q27 are #199's questions (reported there by #150 on the same corpus). New here:
the trade press (tier 3, 77 documents) ranks high in single-firm questions and pushes out
primary sources (Q2, Q5, Q30, and part of Q6/Q13/Q27). #179 kept trade press out of benchmark
questions only.

Issue draft (filed only after TL approval, dispatch rule; no fix in this PR):
- **S1 - trade press crowds out primary sources in single-firm questions.** Evidence: Q2, Q5,
  Q30 (and Q6, Q13, Q27 together with #199) above, `cache\ev200ecall-drops.txt`. Check: mock
  eval on `corpus-2026-11-17` with the fix -> tier-1 doc recall back to >= 0.625 on those
  questions, Q26 still PASS, 0 forbidden. C1 to decide per row whether a trade article is an
  accepted alternative in `evals/expected_chunks.yaml` (class a, Q2).

## Acceptance
- [x] P1: build from clean `main` in `repo`, HEAD = `origin/main` (sha recorded); no empty
      `published_at`; Box root uploads all identical to `raw/`.
- [x] Build log: `219 files OK`, 0 `parsing with docling|edgartools`, 93 `parse cache hit`,
      `Embedding skipped` (or vector check -> 0), `SNAP.dump` copied to Box.
- [x] `obj_description` = `SNAP`; documents = 219, doc_id set = manifest; adv 5, trade 77;
      chunk count in LATEST.json and README (expected 21,143, difference explained);
      transcript chunks 2,852; `BAC-TR-2026Q2#63` GWIM; old non-transcript chunks unchanged.
- [x] `cee.smoke` PASS; `verify_cee.py doctor` DOCTOR PASS; `verify_cee.py run` VERIFY PASS.
- [x] `EV\page_sweep.txt`: 52 PDFs, `MISPLACED 0` on every line.
- [x] sha256 Box dump = local dump = LATEST.json; `pg_restore --list` exit 0; scratch restore
      `cee_restore_200` smoke PASS, dropped.
- [x] `sync-db.ps1 -Check` and `sync-db.sh --check` both exit 0 "up to date: SNAP".
- [x] Mock eval `snap-ASOF` vs `base-ASOF` (and at 2026-10-29): 0 forbidden hits; refusal
      accuracy >= baseline; PASS/FAIL, tier-1 recall reported; every PASS -> FAIL and recall
      drop classified; rerun 30 UNCHANGED; saved as `evals/baselines/SNAP/` (app budget, no
      `--k`).
- [x] `pytest -q` all pass (>= 479).
- [x] `snapshots/LATEST.json` on the branch = the build's; `repo` clean on `main`; README
      Status updated (incl. Gate 3 = 16/30); PR merged = sync note (on merge); one team-chat line handed
      to the TL ("New snapshot SNAP: run /sync-db"); #121, #199 told the snapshot name.
- [x] 0 real calls.

## Progress log
- 2026-11-17 22:30 - plan written on `tl/200-next-snapshot` (worktree `D:\ALLPROJECTS\EDJ\wt-snap`)
  from origin/main 960b742. Facts above checked read-only: manifest 219 rows, 0 empty
  `published_at`; parse cache v2 52/52, edgartools v1 41/41; Box root uploads 82/82 identical
  to `raw/`; `cee` = corpus-2026-11-16 (137 docs, 18,497 chunks); both `sync-db` checks exit 0;
  `pytest -q` 479 passed. No file other than this plan changed. Not reviewed yet.
- 2026-11-17 22:30 - plan reviewed on #200 ("Reviewed 4e415e1"): **PLAN APPROVED** (reviewer
  agent), https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/200#issuecomment-6969062523 ;
  0 blocking, 6 non-blocking. Notes 1-5 applied (baseline = app budget, not k=20; `ASOF` fixed
  at step 1; chat line in Acceptance; `mention_excludes` first suspect and `cee_prev_200` source;
  README Gate 3 sentence). Note 6 (plan file name) kept as is.
- 2026-11-17 22:31 - `ASOF` fixed = 2026-11-17. Evidence folder `D:\ALLPROJECTS\EDJ\cache\ev200`.
- 2026-11-17 22:40 - step 1 done (`corpus-2026-11-16`, code 960b742): doctor PASS; mock
  `base-1117` 27 PASS / 3 FAIL, tier-1 doc recall 0.625, gap 5/5; `base-1029` 28 / 2, 0.646, 5/5.
  Pre-build: `repo` on `main` = origin/main 960b742, clean; Box root uploads 82/82 identical to
  `raw/`. Build notes (published in LATEST.json): "219 documents, 82 more than
  corpus-2026-11-16: Form ADV Part 2A brochures for the core five (#55), 90 days of trade press
  for the five (#57). Earnings-call transcripts chunked by speaker turn (#107); answer key
  already remapped. Retrieval since the freeze: budget by firm count with Merrill counted once
  (#181), rank floor (#166), Form ADV only for fee questions (#179)."
- 2026-11-17 22:32 - step 2: build on `main` 960b742 -> `corpus-2026-11-17`, exit 0 (log checks
  above).
- 2026-11-17 22:45 - steps 3-6 done, all checks pass (Findings). `cee_prev_200` and
  `cee_restore_200` dropped; `cee`, `cee_84`, `cee_84_rev` kept. verify-cee VERIFY PASS (9
  features). `pytest -q` 479 passed. `LATEST.json` copied to this branch, `git restore` in
  `repo` -> clean on `main`. Baseline `evals/baselines/corpus-2026-11-17/` replaces
  `corpus-2026-10-22`; README Status updated. 0 real calls.
