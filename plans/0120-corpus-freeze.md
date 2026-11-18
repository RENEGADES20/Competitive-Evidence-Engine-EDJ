# 0120 - Corpus freeze: snapshot corpus-2026-11-16, mock check, Q24/recall, real 30-question run

Issue: #120    Role: TL    Spec: docs/ARCHITECTURE.md, docs/DECISIONS.md (ADR-006 snapshots),
docs/RUN.md section 4, docs/DASHBOARD.md section 8 (snapshot checklist) and 6 (X/30 scoring),
docs/BRIEF.md (Gates), evals/questions.yaml, evals/expected_chunks.yaml

## Goal
The frozen corpus exists as one named snapshot, `corpus-2026-11-16`, built from `main` as it is
when `build-snapshot` runs (TL rule, 2026-11-16: with the #84 PDF-page parser, the #115 registry
names and all 137 manifest documents; without #55/PR #178 and #107/PR #150), checked (smoke,
doctor, verify-cee, mock eval against the `corpus-2026-10-29` baseline, with Q24 and the tier-1
recall drop explained), published through the `snapshots/LATEST.json` PR (the sync note; the
dump itself goes to Box during the build), and - only after the tech lead approves the paid
calls - answered once by the real model on all 30 questions so the team can score Gate 3
(>= 18/30 at acting quality). The cold test and the sixth-firm decision stay open (teammates /
TL), so the PR is `Part of #120`.

**Name.** The issue says `corpus-2026-11-11`. `build-snapshot` stamps the build date
(`Get-Date` / `date`), and the build runs on 2026-11-16, so the snapshot is `corpus-2026-11-16`.
It differs from 11-11 because the build waited for the plan review and for the TL's W7 decision
of 2026-11-16 (#55 and #107 out, #115 in); nothing was built on 11/11. The corpus documents are
still those frozen by 11/11: no manifest change since 822ead2 (#151, 2026-11-05). Since 4236f14
(the round-1 review) `main` changed only `config/source_registry.csv` (#115, registry names,
seeded into the snapshot) and docs. Forcing `-11-11` would mean editing the script or renaming the dump and
its stamp by hand, which breaks the sha256 in `LATEST.json`. If the build runs on another day or
crosses midnight, the stamped name is used and announced (whatever `COMMENT ON TABLE documents`
says is the name); every `corpus-2026-11-16` below then means that name.

## Facts (read-only; 2026-11-12 20:30, re-checked on 8f92cb1 2026-11-16 16:00)
- `origin/main` = 8f92cb1 (includes #168/#84 PDF provenance pages, #171 LATEST.json + /sync-db,
  #164 Q29 synonym-only, #173/#115 registry names). This branch = 8f92cb1 (merged in, 9b03d94)
  + this plan. `git diff --stat 4236f14 8f92cb1`: `config/source_registry.csv` (5 rows'
  `source_name`), `docs/PROGRESS.md`, `plans/0115-registry-names.md`; no manifest, ingest or
  retrieval change.
- `data/manifest.csv` on 8f92cb1: **137 rows** (47 pdf, 41 htm, 41 txt, 8 html); last change
  822ead2; 0 rows with empty `published_at`. Current snapshot `corpus-2026-10-29` (DB `cee`,
  re-checked 11-16): 111 docs, 17,183 chunks. `cee_84` (#168 review): 126 docs, 18,396 chunks.
  The 11 manifest rows not in `cee_84`: CERULLI-MASS-AFFLUENT-2026, MER-PR-2026-09-15-01,
  MER-PR-web-advisor-development-program, MER-PR-web-becoming-a-merrill-lynch-advisor,
  RJF-PR-web-advisor-select, RJF-PR-web-affiliation-options,
  RJF-PR-web-bank-and-credit-union-advisors, RJF-PR-web-independent-advisor,
  RJF-PR-web-independent-ria-custody-services, RJF-PR-web-traditional-employee-advisor,
  WEALTHTENDER-ADVISOR-SEARCH-2025. So the freeze adds 26 documents over `corpus-2026-10-29`,
  11 more than the #168 review measured.
- **Build inputs and where they are** (`scripts/build-snapshot.ps1/.sh`, `cee.config.resolve_path`,
  `cee.ingest.parse_cache`):
  - Raw files: `$CORPUS_SHARE_PATH/raw/<doc_id>.<ext>`. `CORPUS_SHARE_PATH` is set in
    `D:\ALLPROJECTS\EDJ\repo\.env` and points at Box Drive `C:\Users\14370\Box\EDJ` (checked
    by path comparison, value not printed). `check_files` on the 137 rows (8f92cb1):
    **137 files OK** (exist, sha256 matches); Box `raw/` holds 137 files.
  - Parse cache: `$CORPUS_SHARE_PATH/parsed/`. docling 2.131.0 tag `docling2.131.0-v2` (the #84
    parser, `PARSER_VERSION = 2`): **47/47 PDFs cached**; edgartools 5.59.1 tag
    `edgartools5.59.1-v1` (`HTML_PARSER_VERSION = 1`): **41/41 filings cached**. Installed
    versions in `repo\.venv` match the tags, so the build runs no docling and no edgartools
    parse. txt (41) are read directly; the 8 research html pages are parsed live by
    `webpage.article_text` (fast, no cache, no log line).
  - Database and dump folder: container `cee-db` mounts `D:\ALLPROJECTS\EDJ\repo\snapshots` as
    `/snapshots` and `repo\db\schema.sql`, `repo\db\upgrade.sql` as init scripts. So the build
    **must run from the main checkout `D:\ALLPROJECTS\EDJ\repo`** (the script also refuses any
    branch but `main` unless `-AllowBranch`, which names the dump `...-test` and must not be
    published). `wt-120` has no `.env` and no `.venv`; it is not used for the build.
  - `D:\ALLPROJECTS\EDJ\repo` is on `tl/159-q29-synonym-only` (merged as #164), working tree
    clean. Box `snapshots/` holds the six earlier dumps up to `corpus-2026-10-29.dump`.
  - Missing inputs: **none found**. Not verifiable from here: whether `CEE_VECTORS` is on in
    `repo\.env` (not read); the build log line 4/7 shows it (expected "skipped"; see step 2).
- **Q24 / recall (from #168 review, `D:\ALLPROJECTS\EDJ\cache\ev84-review\`)**: with 126 docs,
  mock eval `--as-of 2026-10-29` goes PASS 28 / FAIL 2 -> 27 / 3; tier-1 document recall
  0.796 -> 0.753; refusal accuracy stays 5/5. Q24 FAIL is pattern coverage 2/5 < 0.5
  (`RJF:supplement`, `SCHW:10-K`, `BAC:supplement#GWIM` not hit; passage recall 0/4,
  `refusal_ok` true, no forbidden hit), not a wrong-firm hit. Q1, Q10, Q11, Q22, Q23 changed
  retrievals; every changed chunk is from one of the 15 then-new documents.
- `sync-db -Check` (start-task step 2): DB `cee` is stamped `corpus-2026-10-29` = `LATEST.json`
  name, i.e. up to date (the script itself cannot run from `wt-120`, no `.venv`).
- Open PRs that touch the freeze: **#178** (C3, #55 Form ADV Part 2A brochures: adds corpus
  documents), **#150** (C2, #107 transcripts cut by speaker turn: re-chunks all 32 transcripts,
  changes transcript `chunk_id`s), **#172** (S2, withhold normative claims: answer code, not
  corpus; it changes real answers), **#169** (C1, metric definitions quoting `chunk_id`s: must
  re-point against the freeze after this build, out of scope here).

## Preconditions (checked or decided before step 2)
- P1 - W7 state and TL decision (issue #120 comment, 2026-11-16). Rule: the freeze contains what
  is merged on `main` when `build-snapshot` runs; nothing is held back by date.

  | W7 issue | Owner | State | In this freeze? |
  |---|---|---|---|
  | #115 registry names in gap answers | C1 | closed, merged as PR #173 (dd92ca7, on 8f92cb1) | **yes** (registry seeded into the snapshot) |
  | #116 tier-5 docs in entity questions | S1 | closed, merged as PR #148 (2026-11-03 local, 11-04 UTC) | yes (code, already on main) |
  | #55 Form ADV Part 2A brochures (Q18) | C3 | open, PR #178 open | **no, on purpose**: lowers mock eval 27/3 -> 26/4 (`adv` searched for every question) until S1's follow-up; merges right after the build, next snapshot. **Q18 is scored without fee-schedule documents in this snapshot** (accepted by the TL) |
  | #107 speaker-turn chunking | C2 | open, PR #150 open | **no, on purpose**: Q28 fails without #166; merges right after the build, next snapshot |

  **Check right before the build** (step 2, in `repo` after `git pull`):
  `gh pr view 178 --json state -q .state` -> `OPEN` and `gh pr view 150 --json state -q .state`
  -> `OPEN` (neither merged); `git log --oneline 822ead2..HEAD -- data/manifest.csv` -> empty
  (no manifest change since 822ead2). Any other result: stop, do not build, report to the TL.
- P2 (TL decision): whether #172 merges before the real run (step 9). It does not change the
  snapshot; the real run records the `main` sha it ran on.
- P3: no other session uses the `D:\ALLPROJECTS\EDJ\repo` checkout or database `cee` during
  steps 2-3: the build runs `DROP DATABASE cee WITH (FORCE)`. `cee_84`, `cee_84_rev` and other
  databases are not touched. `docker compose down -v` is **not** run (it would delete them).
- P4: Box Drive running, `raw/` and `parsed/` available offline (re-checked by step 2's 1/7).
- P5: this plan approved by the reviewer agent's verdict on #120 (`/tl-review`) before step 1.

## Files to change
- `plans/0120-corpus-freeze.md` - this plan, Progress log, findings.
- `snapshots/LATEST.json` - copied from the build (name, sha256, counts, built_at, notes): the
  sync note; merging the PR tells the team to run `/sync-db`.
- `README.md` - Status section only: snapshot name, document/passage counts, latest retrieval
  check line (follow-up named by #162's progress line).

No code, config, answer-key or question change (freeze: fixes go to W9 issues). No new script,
so no new .ps1/.sh pair; comparison scripts stay as scratch files under
`D:\ALLPROJECTS\EDJ\cache\ev120\` and are not committed. Raw files and the dump are never
committed. `docs/PROGRESS.md` is updated only by the bot from the PR's Progress line.

## Steps
Shell setup (Windows PowerShell / macOS bash). `PY` = `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe`
(macOS: `.venv/bin/python`). Mock provider, vectors off, temp on D:. Evidence folder
`EV` = `D:\ALLPROJECTS\EDJ\cache\ev120` (every report, log and raw output goes there).
```
$env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; $env:LLM_PROVIDER="mock"; Remove-Item Env:CEE_VECTORS -ErrorAction SilentlyContinue; $env:PYTHONPATH="D:\ALLPROJECTS\EDJ\wt-120\src"
```
```
export LLM_PROVIDER=mock PYTHONPATH="<wt-120>/src"; unset CEE_VECTORS
```
Steps run from `wt-120` use this `PYTHONPATH` (absolute). Steps run from `repo` (2, the page
sweep and sync checks in 3, 9) clear it first (`Remove-Item Env:PYTHONPATH` / `unset PYTHONPATH`),
so the `repo` code (= `main`) is used.

1. **Baseline on `corpus-2026-10-29`** (DB `cee`, before the build replaces it), code = main
   8f92cb1, from `wt-120`:
   - `PY -m pytest -q` -> count = the floor.
   - `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`, snapshot `corpus-2026-10-29`.
   - `PY scripts/eval_run.py --as-of 2026-10-29 --out EV/base-1029` (expected 28 PASS / 2 FAIL
     Q15, Q19; recall 0.796; refusal 5/5).
   - `PY scripts/eval_run.py --as-of 2026-11-16 --out EV/base-1116` (window questions on the
     build date).
2. **Build** in `D:\ALLPROJECTS\EDJ\repo`:
   - `git switch main; git pull --ff-only`; record `git rev-parse HEAD` (expected 8f92cb1; if
     `main` moved, list what changed and stop if anything touches `src/cee/ingest/`, `config/`
     or `db/` without TL say-so).
   - P1 check (above): PR #178 and PR #150 both `OPEN`; no manifest commit since 822ead2.
   - DASHBOARD section 8 pre-checks: no manifest row with empty `published_at`; no files waiting
     from the Box upload link to move into `raw/` (any found: stop and ask the TL; they are not
     in the manifest).
   - Then `powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "<notes>" *> EV\build.log`
     (Mac: `bash scripts/build-snapshot.sh --notes "<notes>" 2>&1 | tee EV/build.log`).
     Notes (no links), draft: "Corpus freeze (#120): 137 documents (+26: decks and a Merrill
     release #146, research #152, supplements and Schwab monthly #147, dated web pages #151,
     ...). PDF passages carry the page of every docling span (#84). Registry names cleaned
     (#115). Not in this snapshot: Form ADV brochures (#55) and speaker-turn transcripts
     (#107)." The exact list is taken from `git log` over the 26 manifest rows not in `cee`;
     the final text is written into the Progress log before the build runs (it is published in
     LATEST.json).
   - Log checks: `137 files OK`; "no parser ran" =
     `Select-String -Path EV\build.log -Pattern "parsing with docling|parsing with edgartools"`
     (Mac: `grep -cE "parsing with (docling|edgartools)" EV/build.log`) -> no match, and
     `parse cache hit` lines = 88 (47 PDFs + 41 filings); `4/7 Embedding skipped`;
     `Dumping corpus-2026-11-16.dump`; `Copying to Box`.
   - If 4/7 says `Embedding every chunk` (`CEE_VECTORS=on` in `repo\.env`): let it finish (it is
     local, no paid call), then run the DASHBOARD 8 vector check
     `docker exec cee-db psql -At -U cee -d cee -c "SELECT count(*) FROM chunks c WHERE NOT EXISTS (SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id)"`
     -> `0`, note it in the Progress log, and run the evals with vectors off as planned. If
     embedding fails or the count is not 0: stop, report to the TL; do not publish.
3. **Snapshot checks** (DB `cee` is now the freeze):
   - `COMMENT` on `documents` = `corpus-2026-11-16`; `SELECT count(*) FROM documents` = 137 and
     the doc_id set equals the manifest's 137 doc_ids (scratch compare); no doc_id of PR #178.
   - `PY -m cee.smoke` -> PASS. `PY scripts/verify_cee.py doctor` -> `DOCTOR PASS`.
   - `PY scripts/page_sweep.py > EV\page_sweep.txt`, run from `repo` (it finds raw PDFs through
     `CORPUS_SHARE_PATH` in `repo\.env`; it always exits 0, so the check is the output): every
     PDF line `MISPLACED 0`, all 47 PDFs listed (as #168: 3,568/3,568), proving the v2 parse
     cache was used.
   - sha256 of `C:\Users\14370\Box\EDJ\snapshots\corpus-2026-11-16.dump` = `sha256` in
     `repo\snapshots\LATEST.json`; `docker exec cee-db pg_restore --list /snapshots/corpus-2026-11-16.dump`
     exits 0. Restore test (instead of DASHBOARD 8's `docker compose down -v`, deliberately
     skipped: it would delete `cee_84`, `cee_84_rev` and other sessions' databases): create
     scratch DB `cee_restore_120`, `pg_restore` the Box copy into it, run `PY -m cee.smoke` with
     `DATABASE_URL=postgresql://cee:cee@localhost:5432/cee_restore_120` -> PASS, then drop only
     `cee_restore_120`.
   - `scripts\sync-db.ps1 -Check` in `repo` -> exit 0, "Database is up to date: corpus-2026-11-16".
4. **Mock eval on the freeze**, from `wt-120`:
   - `PY scripts/eval_run.py --as-of 2026-10-29 --baseline EV/base-1029/report.json --out EV/freeze-1029`
   - `PY scripts/eval_run.py --as-of 2026-11-16 --baseline EV/base-1116/report.json --out EV/freeze-1116`
   - `PY -m pytest -q` -> all pass, count = floor.
5. **Q24 and recall analysis** (scratch script in `EV`, reads the report.json files of
   `base-1029`, `ev84-review/eval` (126 docs) and `freeze-1029`):
   - per question: chunk_ids lost and gained, the document of each gained chunk, and whether it
     is one of the 26 new documents (and of those, the 11 not in `cee_84`);
   - Q24 and each must_return chunk that dropped out of a tier-1 key: still in the DB? its rank
     with `--k 40 --questions <id>` (mock, free);
   - classify each change: (a) new document is real evidence for the question -> answer-key
     extension (C1, `evals/expected_chunks.yaml`); (b) crowd-out by ranking (`FLOOR`,
     `MAX_PER_DOC`) -> S1; (c) document should not answer this question (wrong firm or scope)
     -> C2/C3 tagging. Findings table goes into this plan and the PR; each class becomes one W9
     issue draft (filed after TL approval, dispatch rule). No fix in this PR.
   - Q18: note in the findings that it is scored without fee-schedule documents (P1).
   - **Stop rule:** any forbidden hit (wrong firm, BAC outside GWIM for Merrill) or refusal
     accuracy below the baseline -> stop, do not open the LATEST.json PR, report to the TL.
     "Publishing" here means the LATEST.json PR: the team syncs only through it. The dump is
     already in Box `snapshots/` after step 2; a stopped freeze leaves that dump there,
     unannounced (named in the report so the TL can delete or keep it).
6. **verify-cee**: `PY scripts/verify_cee.py run` (all features) on the freeze -> `VERIFY PASS`;
   evidence folder named in the PR. Re-run once on a clearly environmental failure
   (shared `cee_verify`), as in #159.
7. **Publish** (= the LATEST.json PR): copy `repo\snapshots\LATEST.json` to
   `wt-120\snapshots\LATEST.json`, then in `repo` run `git restore snapshots/LATEST.json`, so
   the main checkout stays clean on `main` (otherwise the next `git pull --ff-only` /
   `build-snapshot` there can refuse). Update README Status, commit on this branch, push, open
   the PR (`Part of #120`, open items below). Merging it is the sync note (DASHBOARD section 8).
   Hand the TL a one-line team-chat message (in chat, not a file): "New snapshot
   corpus-2026-11-16: run /sync-db". Comment on #169 with the snapshot name so C1 re-points its
   chunk_ids, and on #178 / #150 that the freeze is built and they may merge. `repo` stays on
   `main`, clean; switch it back to another branch only if the TL asks.
8. **Paid-call plan - needs tech-lead approval (more than 10 calls). Not run without the TL's
   explicit go-ahead.**

   | Questions | Why the mock cannot show it | Calls |
   |---|---|---|
   | Q1-Q30 (all 30 of `evals/questions.yaml`) | Gate 3 scores acting quality: wording, the behavior choice (answer / gap_with_adjacent / refuse / answer_with_boundary), and whether each claim matches its cited passage. The mock always answers from what retrieval finds, so it shows none of this. | 30 |

   At most 30 calls, one per question, cap `--max-calls 30`, one run, no re-rolls, no retries
   inside a loop; a wrong answer is a finding. Saved outputs are reused first: the eval cache
   key includes the snapshot, so no earlier output matches the new snapshot (expected 30 new
   calls). A question with no retrieved chunk makes no call and writes no raw file (`no_call`);
   the #168 mock reports have none, so 30 is expected. Model = `LLM_MODEL` in `repo\.env`
   (recorded by the run).
9. **Real run** (last, once, only after steps 1-7 pass and the TL approves), from
   `D:\ALLPROJECTS\EDJ\repo` on `main` (it has the `.env` key; the provider is set for this one
   command, `.env` stays on mock):
   `$env:LLM_PROVIDER="anthropic"; PY scripts/eval_run.py --real --max-calls 30 --as-of 2026-11-16 --out EV/real-30`
   (Mac: `LLM_PROVIDER=anthropic PY scripts/eval_run.py --real --max-calls 30 --as-of 2026-11-16 --out EV/real-30`).
   `--as-of 2026-11-16` = the build date, same windows as the `freeze-1116` mock check.
   eval_run writes each output to `EV\real-30\raw\` (and `repo\.eval-runs\cache\`). Check: one
   raw file per question with hits (expected 30), and calls + reused + no_call = 30. Record
   `main` sha, model, calls used.
10. (TL 2026-11-17: the X/30 is scored by the TL agent, see Progress log.) **Scoring pack**: from the saved outputs, without new calls: per question expected vs got
    behavior, citations resolve (every cited `chunk_id` was retrieved and exists in the DB), the
    #52 number check, normative sentences quoted, and a provisional verdict against
    `passes_if`, marked "provisional (Claude)". The Gate 3 X/30 is the human score (DASHBOARD
    section 6: each person scores their 5, C1 posts X/30 in PROGRESS "Weekly score" with
    snapshot `corpus-2026-11-16`; Q18 noted as scored without fee documents).
11. Progress log, `/finish-task`.

## Findings (2026-11-16, snapshot corpus-2026-11-16, mock, 0 paid calls)
Evidence: `D:\ALLPROJECTS\EDJ\cache\ev120\` (`build.log`, `page_sweep.txt`, `restore_smoke.txt`,
`base-1029`, `base-1116`, `freeze-1029`, `freeze-1116`, `freeze-1029-k40`, `cmp-1029.txt`,
`compare.py`, `verify.log`).

**Mock eval, freeze vs baseline** (`--k 20`; tier-1 recall is now over all 18 tier-1 questions,
since #170 gave every one a key, so it is not comparable with #168's 0.796/0.753 over 9):

| Run | PASS / FAIL | FAIL IDs | Tier-1 doc / passage recall | Refusal (gap / all keyed) | Forbidden |
|---|---|---|---|---|---|
| base-1029 (`corpus-2026-10-29`, as of 10-29) | 28 / 2 | Q15, Q19 | 0.646 / 0.449 | 5/5 / 19/19 | 0 |
| freeze-1029 (`corpus-2026-11-16`, as of 10-29) | 26 / 4 | Q15, Q19, Q22, Q24 | 0.629 / 0.460 | 5/5 / 19/19 | 0 |
| base-1116 (`corpus-2026-10-29`, as of 11-16) | 27 / 3 | Q15, Q19, Q26 | 0.626 / 0.417 | 5/5 / 19/19 | 0 |
| freeze-1116 (`corpus-2026-11-16`, as of 11-16) | 25 / 5 | Q15, Q19, Q22, Q24, Q26 | 0.608 / 0.428 | 5/5 / 19/19 | 0 |

Stop rule not hit: 0 forbidden hits, refusal accuracy unchanged. Q26 at as-of 11-16 fails on
both snapshots (no RJF passage inside the 90-day window ending 11-16; window behavior, not the
freeze). Q15 and Q19 failed before the freeze; Q19's chunks are identical, its coverage
denominator grew 4 -> 5 because `MER:press` now exists in the corpus.

**What changed.** 28 of 30 questions return different chunks (`cmp-1029.txt`). Every gained
chunk is from one of the 26 new documents, except 10 chunks of documents already in the corpus
(rank shuffles, mostly the neighbour of the chunk they replace; Q15, Q17, Q20, Q21, Q22, Q24). The
11 documents not in `cee_84` (the three Merrill pages/release, six RJF web pages, Cerulli,
Wealthtender) appear in 20 questions.

**Cause of Q24, Q22 and the recall drop: Merrill now fills two firm groups.** Until this
snapshot Merrill was served only by BAC chunks in GWIM; the freeze adds the first documents with
`entity_id = MER` (MER-PR-2026-09-15-01, MER-PR-web-advisor-development-program,
MER-PR-web-becoming-a-merrill-lynch-advisor). In every five-firm question the 20 slots were
4 x 5 firms; now they are MS 3-4, SCHW 3-4, EDJ 3-4, RJF 3-4, BAC 3 **plus MER 3** (Q10, Q11, Q22,
Q23, Q24 counted). Merrill gets ~6 slots, and the 4th-ranked chunk of other firms falls out at
the k=20 cut. With `--k 40` all five questions PASS (`freeze-1029-k40`):

| Q | Status | Dropped chunk (base rank -> rank at k=40) | Took the slot | Class |
|---|---|---|---|---|
| Q24 | PASS -> FAIL (coverage 3/5 -> 1/5) | `MS-SUPP-2026Q1#14` (8 -> 21, `MS:supplement`), `SCHW-10K-2025#42` (16 -> 25, `SCHW:10-K`), `EDJ-10K-2025#267` (14 -> 28) | `MS-DECK-2026-strategic-update#28`, `SCHW-DECK-2026-investor-day#25`, `SCHW-MONTHLY-2026-04#6`, MER pages `MER-PR-2026-09-15-01#2`, `MER-PR-web-becoming-a-merrill-lynch-advisor#3/#4` | b |
| Q22 | PASS -> FAIL (4/6 -> 3/7) | `RJF-PR-2026-01-28-01#1` (18 -> 21, `RJF:press`), `MS-10K-2025#165` (17 -> 26), `EDJ-10K-2025#182` (19 -> 22) | MER pages and release, `MS-DECK-2026-strategic-update#31` | b |
| Q11 | PASS, doc recall 0.875 -> 0.625 | `BAC-10K-2025#246` (20 -> out of 40, must_return), `BAC-SUPP-2026Q1#44` (15 -> out) | three MER chunks, MS deck/supplement | b |
| Q10 | PASS, coverage 1.0 -> 0.8 | `BAC-TR-2026Q3#13` (20 -> out, `BAC:transcript#GWIM`), `BAC-10K-2025#249` (5 -> out) | `BAC-DECK-2025-investor-day#8/#9/#12`, MER page | b |
| Q23 | PASS, doc recall 0.35 -> 0.30 | `MS-SUPP-2026Q1#14` (19 -> out, must_return) | MER pages, BAC deck, RJF web page | b |
| Q1, Q28 | PASS, doc recall 0.667 -> 0.556, 0.833 -> 0.667 | MS supplements/10-Q; BAC transcripts | MS deck and MS-SUPP-2025Q4; BAC deck and MER pages | a (Q1), b (Q28) |
| Q2, Q3, Q13, Q27 | PASS, recall unchanged | one must_return doc each (`RJF-PR-2026-04-22-01`, `SCHW-DECK-2026Q3`, `MS-SUPP-2026Q3`, `BAC-SUPP-2026Q1`) | a newer same-firm document that is also in the key (`RJF-PR-web-traditional-employee-advisor`, `SCHW-DECK-2026-investor-day`, `MS-DECK-2026-strategic-update`, `MER-PR-2026-09-15-01`) | a |

Q24's must_return passages (`EDJ-10K-2025#130`, `RJF-10K-2025#227/#228`, the MS-SUPP
advisor-led-assets rows) were not retrieved on the baseline either (passage recall 0/4 before and
after, not in the top 40); that is older than the freeze. Q24 still refuses correctly
(`refusal_ok`, no must_not chunk).

Classes and W9 issue drafts (filed after TL approval, dispatch rule; no fix in this PR):
- (b) **S1 - Merrill counted as one firm in the per-firm pool**: `MER` and `BAC`-in-GWIM
  should share one quota (Merrill = `entity=MER` or `entity=BAC` and segment GWIM/Merrill), so
  five-firm questions keep 4 slots per firm. Evidence: Q10, Q11, Q22, Q23, Q24, Q28 above;
  check: freeze mock eval at k=20 back to Q22/Q24 PASS without a new forbidden hit.
- (a) **C1 - answer keys for documents new in the freeze**: Q1, Q2, Q3, Q13, Q27 now return a
  newer same-firm document for a fact the key ties to an older one; C1 decides per row whether
  the new document is an accepted alternative (`evals/expected_chunks.yaml`, never the questions).
- (c) **C2 - generic Merrill/RJF career web pages** (`MER-PR-web-*`, `RJF-PR-web-*`, undated,
  #151) rank in benchmark and NNA questions (Q16, Q20, Q22, Q24, Q25) where they carry no
  figure; C2 checks their segment/doc_type tagging. Lower priority than (b), which removes most
  of the effect.
- Q18 (P1): scored without fee-schedule documents; mock PASS on pattern coverage only.

## Gate 3 score (2026-11-17): 16/30, scored by the TL agent (Claude)

Run: `D:\ALLPROJECTS\EDJ\cache\ev120\real-30` (snapshot `corpus-2026-11-16`, code `main` 54a8775,
as of 2026-11-16, model `claude-sonnet-5-5`, prompt v2, 29 real calls, 0 reused, 1 no_call (Q26),
0 INVALID_OUTPUT). Scoring pack: `D:\ALLPROJECTS\EDJ\cache\ev120\scoring\` (one `Q<n>.md` per
question with every claim, its cited passages from the DB, flags, gaps, caveats; `summary.csv`).
Each answer was read against the question's `passes_if` (four axes, one verdict: would the
project lead forward it to the CSO? No half credit). This is the TL agent's judgement, not a
teammate's score; it replaces the per-person scoring of DASHBOARD section 6 (TL decision
2026-11-17).

Checks over all 29 answers: 303 citations, 0 cite a chunk outside the retrieved set or missing
from the DB; 0 normative claims withheld; Q12 and Q19 hand the "should" back explicitly. Code's
#52 number check flagged 2 claims: Q17 (an adjacent McKinsey item; no figure in the claim text that
matters) and Q22 (the RJF NNA row; the values 12,969 / 14,020 / 8,830 / 11,651 / 17,930 and 4.0 /
4.0 / 2.6 / 3.4 / 5.0 % were checked by hand against `RJF-SUPP-2025Q3#9` and are correct, so a
checker false positive).

| Q | Tier | Expected -> got | Verdict | Reason |
|---|---|---|---|---|
| Q1 | 1 | answer -> answer | PASS | Channels management credits (Workplace "most exciting", advisor channel, self-directed, IPO flows ~half of NNA), in management's words, every claim dated 3Q25-3Q26. |
| Q2 | 1 | answer -> answer | PASS | RJF's own pitch (affiliation choice, Advisor Select "higher rate on production", "no quotas", book ownership, platform/tech) from its pages and calls, plus recruiting results (recruiting comp $107M, NNA driven by recruiting). |
| Q3 | 1 | answer -> answer | FAIL | Frames Advisor Services and its priorities, but no competitive pressure management acknowledges and nothing on where it concedes ground; only the 10-K competitor list and "#1 in RIA custody". |
| Q4 (trap) | 1 | answer -> answer | PASS | No BAC consumer or BAC-wide hiring presented as Merrill; GWIM labelled as Merrill + Private Bank; ADP pipeline from Merrill's pages; the "change" is honestly marked as inferred. Headcount trajectory missing but marked as a gap. |
| Q5 | 1 | answer -> answer | PASS | Named platforms with stated purpose (LeadIQ, E*TRADE Pro, Carta, Zero Hash; DevGen/Parable marked not advisor-facing); spend only qualitative and no estimate. |
| Q6 | 1 | answer -> answer | PASS | Options as RJF describes them (payout ranges per model) and the mix shift toward independent recruiting quoted from the April 2026 call; no quantified mix, said so. |
| Q7 | 2 | answer -> answer | FAIL | No common grid: dimensions differ by firm (RJF posture/retention, Merrill training pipeline, MS only client-migration adjacents); empty cells (Merrill payout, MS/RJF training) not shown as empty. |
| Q8 | 2 | answer -> answer | PASS | Each firm in its own language; explicitly keeps custody (Schwab) and affiliation (RJF) distinct. |
| Q9 | 3 | answer -> answer | PASS | MS tiers (HNW/UHNW) with "no thresholds disclosed" said plainly; Merrill $250K advisory threshold and GWIM bands, with the source conflict named. |
| Q10 | 3 | answer -> answer | PASS | Judgment made legible: only GWIM uses "mass affluent" (dated slide), basis stated, Schwab "affluent" and Cerulli kept as adjacent. Thin, but meets passes_if. |
| Q11 | 1 | answer -> answer | FAIL | Two of five definitions (EDJ, RJF); MS, Schwab and Merrill marked "not in the evidence" though MS and BAC supplements report advisor counts (retrieval miss). |
| Q12 | 3 | answer_with_boundary -> same | FAIL | Boundary held (explicit hand-off), but the evidence half is not complete: no Edward Jones cost structure set alongside and little on Schwab's acquisition economics. |
| Q13 | 1 | answer -> answer | FAIL | Channel pieces and dated participant figures, but not end to end, and the disclosed conversion figure (Workplace -> advisor-led migration, cited in Q7 from MS-TR-2024Q4/2026Q1) is missing. |
| Q14 | 3 | answer -> answer | PASS | Each option's economics for the advisor (payouts, benefits, entry minimums) from RJF's own page and 10-K; firm side via payout split, advisor loans and NNA attribution; channel profitability marked undisclosed. |
| Q15 | 3 | answer -> answer | FAIL | Only Schwab's revenue mix; the advisor-led side is missing (gap), so no mechanism comparison. |
| Q16 | 3 | answer -> answer | FAIL | Organised by source/firm, not by position; no spread of positions synthesised. |
| Q17 | 1 | answer -> answer | FAIL | The "who claims most" verdict says MS and EDJ make no advice-delivery AI claims (from MS's 10-K only) and the gap names Merrill and EDJ as silent, leaving out MS LeadIQ (Q5) and BAC's AI tools for advisers (Q4), both in the corpus. |
| Q18 | 3 | answer -> answer | PASS | Pricing changes (lower AUM pricing, Merrill no added fee), research (McKinsey), survey (Wealthtender) and management commentary each labelled. No regulatory item; scored without fee-schedule documents (TL decision, P1). |
| Q19 | 3 | answer_with_boundary -> same | FAIL | Stops at "should" correctly, but competitor moves aimed at the cohort are missing (e.g. Schwab "built to win across generations", Gen Z share of new accounts) and EDJ's own next-gen platform is not mentioned. |
| Q20 | 1 | answer -> gap_with_adjacent | FAIL | Behavior mismatch; UBS findings given without sample, Wealthtender study not used; no under-40 finding reported. |
| Q21 | 2 | answer -> answer | PASS | Two halves separate: Cerulli (Oct 2025) and UBS (Apr 2026) estimates with source and vintage; firm actions (EDJ, Schwab, MS adjacent) with RJF/Merrill gaps. |
| Q22 | 1 | answer -> answer | FAIL | Honest (GWIM flows labelled, no substitution), but the by-quarter table is not there for 3 of 5: MS 2 quarters, Schwab 2, EDJ percentages only; Schwab and RJF definitions missing. |
| Q23 | 1 | answer -> gap_with_adjacent | FAIL | Behavior mismatch; no series for any firm though EDJ 10-Qs and MS/BAC/RJF supplements carry the counts. |
| Q24 | 3 | gap_with_adjacent -> same | PASS | Declines the bad comparison, names why it is invalid (asset definitions differ: self-directed, workplace, PCG only, GWIM not Merrill); no table. Says EDJ headcount absent (retrieval), but no wrong figure. |
| Q25 | 1 | gap_with_adjacent -> answer | FAIL | Behavior mismatch; says the "only range" is 81-90% for Corporate RIA (RJF's page also lists 50% and 70-80%), and says MS discloses nothing on comp structure (MS 10-K: formulaic payout, Q29). |
| Q26 | 1 | answer -> gap_with_adjacent (no call) | FAIL | No RJF passage published 2026-08-18..11-16 in the snapshot; honest gap, but no answer (corpus gap). |
| Q27 (trap) | 1 | answer -> answer | PASS | Merrill items only (Merrill WM highlights, MER release); GWIM figures only as labelled adjacents. |
| Q28 | 1 | gap_with_adjacent -> same | PASS | EDJ rate with period and its definition, cited to the 10-Qs; Merrill only qualitative; net headcount as adjacent with "not attrition" stated. |
| Q29 | 1 | gap_with_adjacent -> same | PASS | "Payout grids are not public", aggregate comp expense labelled as a different quantity, suggested source with "trade press indicative only". |
| Q30 (trap) | 1 | gap_with_adjacent -> same | PASS | "Merrill does not report standalone results", GWIM figures with explicit "GWIM is not Merrill, includes the Private Bank". |

**16/30 (tier 1: 9/18). Gate 3 target >= 18/30: not met.**
Failing IDs: Q3, Q7, Q11, Q12, Q13, Q15, Q16, Q17, Q19, Q20, Q22, Q23, Q25, Q26.
Borderline (could move with another scorer): fail side Q3, Q12, Q13, Q19; pass side Q2, Q10, Q14, Q18, Q24. The PR review (`Reviewed 6b234bd`) put the range at 15-16 (Q2 the likeliest to move: its gap says payout ranges are not in the recruiting pages, though the RJF affiliation page with ranges is in the corpus, cited in Q14).

Why they fail: retrieval did not bring a passage the corpus has (Q11, Q13, Q17, Q22, Q23, Q25:
answers then state "not in the evidence" and contradict other answers); corpus gap (Q15 advisor-led
revenue, Q20 under-40 surveys, Q26 no RJF document in the 90-day window); answer shape (Q7 no common
grid, Q16 not organised by position, Q3/Q12/Q19 a required element missing). Behavior mismatch:
Q20, Q23 (gap instead of answer), Q25 (answer instead of gap), Q26 (no call). All three traps pass
(Q4, Q27, Q30); no citation outside the retrieved set.

## Acceptance
- [x] P1 check before the build: PR #178 `OPEN`, PR #150 `OPEN`,
      `git log 822ead2..HEAD -- data/manifest.csv` empty; `repo` HEAD = `origin/main` (8f92cb1
      or a later sha whose changes are listed and touch no ingest/config/db file).
- [x] Build: `EV\build.log` shows `137 files OK`, 0 lines `parsing with docling|edgartools`,
      88 `parse cache hit`, `Embedding skipped` (or the vector check -> 0), dump
      `corpus-2026-11-16.dump` copied to Box.
- [x] `SELECT obj_description('documents'::regclass)` -> `corpus-2026-11-16`; documents = 137,
      doc_id set = manifest's 137; chunk count recorded in LATEST.json and README.
- [x] `python -m cee.smoke` -> PASS; `verify_cee.py doctor` -> DOCTOR PASS;
      `verify_cee.py run` -> VERIFY PASS (all features).
- [x] `EV\page_sweep.txt`: 47 PDFs, `MISPLACED 0` on every line.
- [x] Box dump sha256 = `snapshots/LATEST.json` sha256; `pg_restore --list` exit 0;
      `sync-db.ps1 -Check` -> exit 0 "up to date: corpus-2026-11-16";
      scratch restore into `cee_restore_120` -> smoke PASS, then dropped.
- [x] Mock eval `freeze-1029` vs `base-1029`: 0 forbidden hits; refusal accuracy >= baseline
      (5/5 gap questions); PASS/FAIL counts, tier-1 doc/passage recall reported.
- [x] Q24: cause named (which pattern/must_return chunk dropped, which new document took the
      slot, rank at k=40) and classified a/b/c; same for every question whose retrieval changed
      (expected at least Q1, Q10, Q11, Q22, Q23) and for the recall drop (per-question recall
      before/after). One W9 issue draft per class.
- [x] `pytest -q` -> all pass, count = step-1 floor.
- [x] `snapshots/LATEST.json` on this branch = the build's file; `git status` in `repo` clean
      after `git restore snapshots/LATEST.json`; README Status updated; #169, #178, #150 told
      the snapshot name.
- [x] Paid calls (step 8 approved by the TL 2026-11-17): one run, 29 calls (cap 30),
      `claude-sonnet-5-5`, prompt v2, `main` 54a8775; 29 raw files in `EV\real-30\raw\` = the
      29 questions with hits; calls 29 + reused 0 + no_call 1 (Q26) = 30; 0 INVALID_OUTPUT, no
      re-run.
- [x] Scoring pack for all 30 (`EV\scoring\`: behavior, citations resolve 303/303, number-check
      flags, verdict per question); Gate 3 X/30 = 16/30 (tier 1: 9/18) scored by the TL agent (section above).
- [ ] Open, not done by this task (PR says `Part of #120`): Gate 3 not met (16/30 < 18): fix
      issues for the failure classes above, after TL approval; TL decision "sixth firm yes/no"
      (BRIEF: expansion only after gates 1-3 pass cleanly); #169 re-point; W9 fix issues from
      the freeze findings; #55/#107 in the next snapshot; Gate 4 (#121). Cold test dropped
      (TL, 2026-11-17).

## Risks / unsure
- The 11 documents added since the #168 review may change more retrievals than the 5 seen
  there; step 5 measures, not assumes.
- The build drops `cee` (P3). If another session is using it, its run breaks; restore is
  `/sync-db` to the freeze afterwards.
- Name `corpus-2026-11-16` differs from the issue's deliverable `corpus-2026-11-11` (see Name).
- Q18 has no fee-schedule documents in this snapshot (TL-accepted); its Gate 3 score reflects
  that.
- If #178, #150 or a retrieval fix lands after the freeze, Gate 3 answers and #169 chunk_ids
  refer to this snapshot; changes go to the next snapshot.
- Gate 3 acting quality is a judgement call; by the TL decision of 2026-11-17 the TL agent
  (Claude) scores it, labelled as such, with a reason per question and the borderline
  questions named so the tech lead can overrule any verdict.

## Progress log
- 2026-11-12 20:33 - plan written on `tl/120-corpus-freeze` from origin/main 4236f14. Facts
  above checked read-only (manifest 137 rows; Box raw 137/137 sha OK; parse cache docling v2
  47/47 and edgartools v1 41/41; `cee` = corpus-2026-10-29 111 docs; `cee_84` 126 docs). No
  file other than this plan changed.
- 2026-11-12 20:35 - informal self-check: a subagent I started myself read the plan and
  suggested edits (absolute PYTHONPATH, DASHBOARD 8 pre-checks, fixed build notes, scratch-DB
  restore instead of `down -v`, fixed `--as-of`, raw-file check); applied. This was **not** the
  `/tl-review` verdict and approves nothing. Committed 389721a (20:37).
- 2026-11-12 20:40 - reviewer agent on #120 ("Reviewed 389721a"): **PLAN CHANGES REQUESTED**,
  2 blocking items: (1) W7 issues #55, #115 (and #107) not handled; (2) the Progress log line
  claiming an approval with no verdict behind it. 6 non-blocking notes.
- 2026-11-16 15:56 - TL decision on #120: freeze = what is merged on `main` at build time; #115
  in (PR #173 merged), #55 (PR #178) and #107 (PR #150) left out on purpose, merge right after
  the build; Q18 scored without fee documents; name by build date (`corpus-2026-11-16`).
- 2026-11-16 16:00 - fixes: merged origin/main 8f92cb1 into this branch (9b03d94, no
  force-push); facts re-checked on 8f92cb1 (137 rows, last manifest change 822ead2, Box raw
  137/137 OK, `cee` still corpus-2026-10-29); P1 now lists every W7 issue with the TL decision
  and the pre-build check (PR #178 and #150 open, no manifest change since 822ead2); name
  `corpus-2026-11-16` with the reason; the false approval line replaced by this history.
  Non-blocking notes 1-4 taken: raw-file count rule for no-hit questions; `git restore
  snapshots/LATEST.json` in `repo` after the copy; "publishing" = the LATEST.json PR (dump
  already in Box); exact "no parser ran" grep and the `CEE_VECTORS=on` path. Awaiting the
  reviewer's verdict (P5); nothing built.
- 2026-11-16 16:01 - reviewer agent on #120 ("Reviewed 980f094f"): **PLAN APPROVED** for steps
  1-7 and 10; steps 8-9 (30-call real run) **not approved**: 0 paid calls in this task, listed
  as open. Two non-blocking notes applied (the "since 822ead2" sentence; #148 local date).
- 2026-11-16 16:03 - P1 checks: PR #178 OPEN, PR #150 OPEN, `git log 822ead2..origin/main --
  data/manifest.csv` empty. `repo` switched from `tl/159-q29-synonym-only` (clean, squashed into
  main as #164) to `main`, `git pull --ff-only` -> 8f92cb1 = origin/main; 0 empty `published_at`.
  Box root holds 5 loose files `EDJ/MER/MS/RJF/SCHW-ADV-2026.pdf` (Nov 16 15:30): exactly the 5
  manifest rows of PR #178, which the TL left out of this freeze on purpose, so not moved into
  `raw/` and not a reason to stop (the build reads only manifest rows; they go in with #178).
- 2026-11-16 16:03 - step 1 baseline on corpus-2026-10-29 (code 8f92cb1 + this plan): pytest 366
  passed (floor); DOCTOR PASS; base-1029 PASS 28 / FAIL 2 (Q15, Q19), tier-1 doc recall 0.646
  (18 keyed questions since #170), refusal 5/5; base-1116 27 / 3 (Q15, Q19, Q26).
- 2026-11-16 16:04 - step 2 build notes (final, in LATEST.json): "Corpus freeze (#120): 137
  documents, 26 more than corpus-2026-10-29: investor-day and strategy decks and a Merrill release
  (#146), last-four supplements and six Schwab monthly reports (#147), FINRA and research reports
  (#152), dated advisor web pages (#151). PDF passages carry the page of every docling span (#84).
  Registry names cleaned (#115). Not in this snapshot: Form ADV brochures (#55) and speaker-turn
  transcripts (#107)." Build 16:04:02-16:04:40, exit 0: 137 files OK; 88 `parse cache hit`, 0
  `parsing with`; embedding skipped (CEE_VECTORS off); `corpus-2026-11-16.dump` 4.5 MB in Box;
  137 documents, 18,497 chunks; sha256 df1baea3cf8efbd9225fd74519154c330cd38af581f65810d61b1273a0d05602.
- 2026-11-16 16:05 - step 3: stamp `corpus-2026-11-16`, 137 docs = manifest doc_ids, no
  `*-ADV-2026`; smoke PASS; DOCTOR PASS; Box and local dump sha256 = LATEST.json; `pg_restore
  --list` exit 0; `sync-db.ps1 -Check` and `sync-db.sh --check` exit 0 "up to date"; scratch
  restore `cee_restore_120` smoke PASS, dropped (cee, cee_84, cee_84_rev kept); page sweep 47
  PDFs, 3,568/3,568 chunks on their page, MISPLACED 0.
- 2026-11-16 16:05 - step 4: freeze-1029 26 / 4 (Q15, Q19, Q22, Q24), recall 0.629, refusal 5/5,
  0 forbidden; freeze-1116 25 / 5 (+Q26); pytest 366 passed. Stop rule not hit.
- 2026-11-16 16:07 - step 5: Findings above (cause: first `entity_id = MER` documents give
  Merrill a second firm group in five-firm questions; k=40 run passes Q10/Q11/Q22/Q23/Q24).
- 2026-11-16 16:08 - step 6: `verify_cee.py run` VERIFY PASS, 7 features PASS, open-citation and
  download-document UNREACHABLE (`.verify-runs/20261116-160728-980f094`): `wt-120` has no
  `.env`, so no `CORPUS_SHARE_PATH` for raw files (environment). Re-run of those two with
  `CORPUS_SHARE_PATH` set in the shell (`.verify-runs/20261116-160855-980f094`): both PASS
  (incl. PDF page checks on 5 PDFs, one from the new RJF investor-day deck).
- 2026-11-16 16:09 - step 7: LATEST.json copied to this branch; `git restore
  snapshots/LATEST.json` in `repo` -> clean on `main`. README Status updated. Steps 8-9 not run
  (not approved; 0 paid calls); step 10 needs their outputs, so open.
- 2026-11-16 16:10 - #169, #178, #150 told the snapshot name (PR comments). /finish-task.
- 2026-11-17 19:20 - **Tech-lead decisions (the user, 2026-11-17)**, recorded on #120 before any
  call; branch `tl/120-gate3-score` from origin/main 54a8775 (worktree `wt-120g`):
  1. Step 8 **approved by the TL**: the 30-question real run, one run, `--max-calls 30`; every
     real call it needs is pre-approved. Up to 3 runs of the same question are acceptable if a
     run is lost (e.g. an INVALID_OUTPUT, now saved by #187); any re-run is recorded here with
     its reason.
  2. The internal cold test (two teammates, 5 new questions each) is **dropped**.
  3. The TL has taken over all teammate work, including the Gate 3 human scoring (#15,
     DASHBOARD section 6): the X/30 is produced from the saved outputs against each question's
     `passes_if`, labelled "scored by the TL agent (Claude)", with a reason per question. This
     replaces step 10's "provisional (Claude)" + per-person scoring.
  4. Run on current `main` against the frozen DB `corpus-2026-11-16`. **The code differs from
     the freeze build** (8f92cb1 + #180): `main` 54a8775 also has #181/#192 (retrieval budget by
     firm count, Merrill counted once, ADR-013), #166/#190 (#193, rank floor from a firm's
     2nd-best chunk, theme slot ignores the floor, ADR-014), #187/#191 (INVALID_OUTPUT kept) and
     ADR-012 (up to 5 calls per question). Why: these are the retrieval fixes for the freeze
     findings (class b: Q22/Q24 back to PASS in the #181 mock) and the team ships what is on
     `main`; the snapshot (data) is unchanged, so the score is "code 54a8775 on
     corpus-2026-11-16". `sync-db.ps1 -Check` in `repo` -> exit 0 "up to date: corpus-2026-11-16".
- 2026-11-17 19:21 - free pre-check, mock on `main` 54a8775 as of 11-16
  (`EV\mock-54a8775-1116`): PASS 27 / FAIL 3 (Q15, Q19, Q26), refusal 5/5, 0 forbidden.
- 2026-11-17 19:21-19:29 - step 9 from `repo` on `main` 54a8775 (`LLM_PROVIDER=anthropic` for
  this one command, `.env` unchanged): `eval_run.py --real --max-calls 30 --as-of 2026-11-16
  --out EV\real-30` (log `EV\real-30.log`). 29 calls, 0 reused, Q26 no_call (no RJF passage in
  the window 2026-08-18..11-16), 0 INVALID_OUTPUT, no re-run; model `claude-sonnet-5-5`, prompt
  v2. Automatic status PASS 24 / FAIL 6 (Q15, Q19 coverage; Q20, Q23, Q25 behavior; Q26),
  refusal 5/5. 29 raw files, one per question with hits.
- 2026-11-17 19:32 - step 10: scoring pack `EV\scoring\` (`gate3\pack.py`, no calls), every
  answer read against `passes_if`: **16/30, scored by the TL agent (Claude)** (section above).
  Gate 3 target not met. Same 16/30 as C1's provisional W9 interim on #15 (other code, other
  run), with a different failing set.
- 2026-11-17 19:34 - TL decision: the TL performs C1's role, so the Gate 3 row goes into the
  "Weekly score" table of `docs/PROGRESS.md` in this PR (C1's table per DASHBOARD section 6).
  The Status log is not edited (the bot adds the Progress line on merge). Score posted on #15.
- 2026-11-17 19:39 - PR #195 review (Reviewed 6b234bd): CHANGES REQUESTED, 1 blocking: tier-1
  sub-score is 9/18, not 10/18 (fixed here, in the PR body and the #15 comment). Non-blocking
  taken: log times aligned with the raw files and commits; Q17 reason reworded; Q2 added to the
  borderline list (range 15-16); note on #15 that this 16/30 is the Gate 3 record and C1's 17/30
  line is a different run.
