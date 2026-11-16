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
still those frozen by 11/11: the last manifest change on `main` is 822ead2 (#151, 2026-11-05);
since then `main` changed only `config/source_registry.csv` (#115, registry names, seeded into
the snapshot) and docs. Forcing `-11-11` would mean editing the script or renaming the dump and
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
  | #116 tier-5 docs in entity questions | S1 | closed, merged as PR #148 (2026-11-04) | yes (code, already on main) |
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
10. **Scoring pack**: from the saved outputs, without new calls: per question expected vs got
    behavior, citations resolve (every cited `chunk_id` was retrieved and exists in the DB), the
    #52 number check, normative sentences quoted, and a provisional verdict against
    `passes_if`, marked "provisional (Claude)". The Gate 3 X/30 is the human score (DASHBOARD
    section 6: each person scores their 5, C1 posts X/30 in PROGRESS "Weekly score" with
    snapshot `corpus-2026-11-16`; Q18 noted as scored without fee documents).
11. Progress log, `/finish-task`.

## Acceptance
- [ ] P1 check before the build: PR #178 `OPEN`, PR #150 `OPEN`,
      `git log 822ead2..HEAD -- data/manifest.csv` empty; `repo` HEAD = `origin/main` (8f92cb1
      or a later sha whose changes are listed and touch no ingest/config/db file).
- [ ] Build: `EV\build.log` shows `137 files OK`, 0 lines `parsing with docling|edgartools`,
      88 `parse cache hit`, `Embedding skipped` (or the vector check -> 0), dump
      `corpus-2026-11-16.dump` copied to Box.
- [ ] `SELECT obj_description('documents'::regclass)` -> `corpus-2026-11-16`; documents = 137,
      doc_id set = manifest's 137; chunk count recorded in LATEST.json and README.
- [ ] `python -m cee.smoke` -> PASS; `verify_cee.py doctor` -> DOCTOR PASS;
      `verify_cee.py run` -> VERIFY PASS (all features).
- [ ] `EV\page_sweep.txt`: 47 PDFs, `MISPLACED 0` on every line.
- [ ] Box dump sha256 = `snapshots/LATEST.json` sha256; `pg_restore --list` exit 0;
      `sync-db.ps1 -Check` -> exit 0 "up to date: corpus-2026-11-16";
      scratch restore into `cee_restore_120` -> smoke PASS, then dropped.
- [ ] Mock eval `freeze-1029` vs `base-1029`: 0 forbidden hits; refusal accuracy >= baseline
      (5/5 gap questions); PASS/FAIL counts, tier-1 doc/passage recall reported.
- [ ] Q24: cause named (which pattern/must_return chunk dropped, which new document took the
      slot, rank at k=40) and classified a/b/c; same for every question whose retrieval changed
      (expected at least Q1, Q10, Q11, Q22, Q23) and for the recall drop (per-question recall
      before/after). One W9 issue draft per class.
- [ ] `pytest -q` -> all pass, count = step-1 floor.
- [ ] `snapshots/LATEST.json` on this branch = the build's file; `git status` in `repo` clean
      after `git restore snapshots/LATEST.json`; README Status updated; #169, #178, #150 told
      the snapshot name.
- [ ] Paid calls: 0 until the TL approves step 8; then exactly one run, <= 30 calls; one raw
      file per question with hits in `EV\real-30\raw\` (expected 30), calls + reused + no_call
      = 30; calls/model/`main` sha in the PR.
- [ ] Scoring pack for all 30 (behavior, citations resolve, number check, provisional verdict).
- [ ] Open, not done by this task (PR says `Part of #120`): Gate 3 human score X/30 posted in
      PROGRESS (C1/scorers); cold test by two teammates outside S1/S2 (5 new questions each, no
      help) and one issue per failure; TL decision "sixth firm yes/no" (BRIEF: expansion only
      after gates 1-3 pass cleanly); #169 re-point; W9 fix issues filed after TL approval;
      #55/#107 in the next snapshot.

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
- Gate 3 cannot be declared by Claude: acting quality is a human judgement; the real run only
  makes the answers available, and its cost needs TL approval.

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
