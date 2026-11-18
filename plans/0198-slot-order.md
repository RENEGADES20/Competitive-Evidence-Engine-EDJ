# 0198 - Slot order inside a firm: trade press last, a new document before a second chunk

Issues: #198, #199, #197 (one PR closes all three; refs #107, see Acceptance)    Role: TL
Spec: `specs/retrieval.md` (S1; owner review waived by TL decision 2026-11-17,
[#187 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/187#issuecomment-6964392200))

## Goal
Inside a firm's share of the passage budget, tier 4 trade press no longer takes turns ahead of
filings, supplements, transcripts and IR documents (#198), and a document type gives its next
slot to a document it has not used yet before a second chunk of an already used one, so the
speaker-turn transcripts of one call stop crowding out the other calls (#199). The spec sketch
and the `doc_type_scope()` docstring name the final doc-type scope terms (#197). Measured on the
final snapshot `corpus-2026-11-17` (DB `cee`, read-only). FTS only; no model, no new dependency,
no config, corpus, answer-key or question change.

As of: every eval runs with a fixed `--as-of`: **2026-10-29** (the #198/#199 acceptance date and
the README comparison date) and **2026-11-17** (the committed baseline's date and the snapshot's
build date).

Baselines (named, all mock, app budget, no `--k`):
- **B-1117** = committed `evals/baselines/corpus-2026-11-17/report.json` (`corpus-2026-11-17`,
  as of 2026-11-17, 28/2, tier-1 doc recall 0.547). Re-run on this branch before any edit:
  `D:\ALLPROJECTS\EDJ\cache\ev198\main-2026-11-17` (28/2, 0.547, same).
- **B-1029** = this branch before any edit, as of 2026-10-29:
  `D:\ALLPROJECTS\EDJ\cache\ev198\main-2026-10-29` (28/2, tier-1 doc recall 0.573).
- **No-trade reference** (#198's bar): `corpus-2026-11-16`, `D:\ALLPROJECTS\EDJ\cache\ev200\base-1029`
  (0.646) and `...\ev200\base-1117` (0.625).
- **Pre-#150 reference** (#199's bar and #107's check, as of 2026-10-29):
  `D:\ALLPROJECTS\EDJ\cache\rev150b\main-2026-10-29\report.json` (main before #150, commit
  b203d46, length-cut transcripts): Q6 0.667, Q11 0.875, Q13 0.667, Q27 0.444 (issue #199 table).

#107 state: #107 is **already closed** (2026-11-17 22:19 local, reason COMPLETED, no PR
reference) by the board automation that closes an issue when its card moves to Approved, while
its last acceptance item ("Mock eval for all 30: no forbidden hits, no regressions") is still
unchecked. A PR keyword cannot decide a closed issue's state, so the close-out is manual
(step 9): item holds -> tick it on #107 with the eval evidence, the issue stays closed, the PR
says `Refs #107`; item fails -> reopen #107 with a comment naming the open item.

## Files to change
- `src/cee/retrieve/fts.py` (S1; waiver above) -
  - `select()`: two slot-order rules inside a firm's turn, both off for the time-window path
    (`search()` passes the window options; Q26 reads everything inside its 90 days, newest first,
    as today) and for the tier 5 research `select()` call (unchanged). They apply to the rank
    turns (`take_from(1, ...)`) and the theme turns (`take_from(0, ...)`, `THEME_FIRST`) alike:
    the theme turn still gives the firm's best on-theme chunk regardless of the floor (#190),
    but a trade on-theme chunk only when the firm has no other on-theme chunk, and a new
    document before a second chunk of a used one:
    - **Tier 4 last** (#198): a firm's document types whose chunks are tier 4 take a turn only
      when no other document type of that firm can give a chunk this turn (variant "cap N":
      at most N tier 4 chunks per firm; chosen in step 3).
    - **New document first** (#199): when a document type takes its turn, it gives its
      best-ranked chunk from a document not yet in the list; only when it has none left does it
      give a second chunk of a used document (`MAX_PER_DOC` still caps at 3). Optional variant
      (step 3): among the type's unused documents whose best chunk ranks within `NEWEST_BAND`
      (0.95 or 0.9) of the type's best unused chunk, the newest `published_at` wins (recurring
      disclosures: Q11 `SCHW-TR-2025Q4#5` 6.64 vs `SCHW-TR-2026Q1#48` 6.31).
    - Module-level switches (`TIER_LAST`, `NEW_DOC_FIRST`, `NEWEST_BAND`) so the step-3 grid
      can swap them from a scratch driver, the way `BUDGET_RULE` is swapped (#181); committed
      values = the chosen cell. Floor, `THEME_FIRST`, near-duplicate removal, firm turns and
      `MAX_PER_DOC` keep their meaning.
  - Module docstring and `select()` docstring: the two rules with their question IDs.
  - `doc_type_scope()` docstring (#197): adv terms incl. "brochures" and "compensation" (Q25);
    benchmark questions Q11, Q22-Q24, Q28 ("attrition rate"). No code change in that function.
- `tests/test_retrieval_quotas.py` - fixture pools, no database:
  - tier 4 last: a firm with a trade type ranked first and a 10-K/transcript type gives the
    non-trade chunks first; trade gets a slot once the others have nothing above the floor;
    a window call (floor 0 path) keeps today's order.
  - new document first: a transcript type with 3 chunks of call A ranked above 1 chunk of call B
    gives A, B before A's second chunk; with the newest band (if chosen), a slightly lower-ranked
    newer call wins over an older one, and a call far below the band does not.
  - entity+theme pool: a firm whose best on-theme chunk is trade and next is a 10-K chunk gives
    the 10-K chunk in its theme slot (`THEME_FIRST`); with only a trade on-theme chunk, that
    chunk still takes the theme slot, below the floor too (#190 unchanged).
  - The existing tests stay green unchanged; if one encodes the old order, it is updated with a
    one-line reason in the test and named in the PR.
- `specs/retrieval.md` (S1; waiver above) - interface sketch: the slot-order rules (#198,
  #199, ADR-016) under the quota lines; the doc-type scope comment names "brochures",
  "compensation" (Q25), "attrition rate" and Q11, Q22-Q24, Q28 (#197).
- `docs/DECISIONS.md` - **ADR-016** "Slot order inside a firm: trade press last, a new document
  before a second chunk" (context: #57 trade press and #150 speaker turns on `corpus-2026-11-17`;
  the grid and the chosen cell; consequences). New ADR, TL-approved per the task brief (the
  ADR-013/014/015 retrieval changes each got one).
- `plans/0198-slot-order.md` (this file).

Out of scope: config (`doc_type_scope`, synonyms), the answer key and question bank (a key row
that looks wrong is reported, not changed), `FLOOR`/`MAX_PER_DOC`/`K`/budget values, answer
wording, new sources, `exp/hybrid`. Gate 4 itself (#121).

## Paid-call plan
**0 real calls.** Every acceptance item is a retrieval check the mock eval shows (which chunks
and documents are retrieved, status, refusal, forbidden). Whether the recovered passages turn
Gate 3's "not in evidence" answers into passes is scored by the Gate 4 run (#121) on the merged
code, not here.

## Steps
Evidence folder `EV` = `D:\ALLPROJECTS\EDJ\cache\ev198`. Worktree `D:\ALLPROJECTS\EDJ\wt-198`,
`PY` = `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe`, environment for every run:
```
$env:PYTHONPATH="D:\ALLPROJECTS\EDJ\wt-198\src"; $env:PYTHONUTF8="1"; $env:LLM_PROVIDER="mock"; $env:TMP="D:\ALLPROJECTS\EDJ\cache\tmp"; $env:TEMP=$env:TMP; Remove-Item Env:CEE_VECTORS -ErrorAction SilentlyContinue
```
```
export PYTHONPATH=/d/ALLPROJECTS/EDJ/wt-198/src PYTHONUTF8=1 LLM_PROVIDER=mock; unset CEE_VECTORS
```
DB `cee` = `corpus-2026-11-17`, read-only (no ingest, no write). No new committed script.

1. **Baselines** (done before the plan, no code change): `verify_cee.py doctor` -> DOCTOR PASS;
   `eval_run.py --as-of 2026-11-17 --out EV/main-2026-11-17` (= B-1117: 28/2, 0.547) and
   `--as-of 2026-10-29 --out EV/main-2026-10-29` (B-1029: 28/2, 0.573).
2. **Gate 3 retrieval misses.** From `D:\ALLPROJECTS\EDJ\cache\ev120\scoring\Q11|Q13|Q17|Q22|Q23|Q25.md`
   and plan 0120 "Gate 3 score", list per question the passage the answer said was missing and
   find its `chunk_id` in `cee` (Q11 MS/BAC supplement advisor counts; Q13 the Workplace ->
   advisor-led conversion figure in MS-TR-2024Q4/2026Q1; Q17 MS LeadIQ, BAC AI tools for
   advisers; Q22 by-quarter NNA rows for MS, SCHW, EDJ and SCHW/RJF definitions; Q23 EDJ 10-Q
   and MS/BAC/RJF supplement counts; Q25 RJF affiliation payout ranges, MS 10-K formulaic payout).
   For each: in the pool? rank, and what holds the slot at B-1029 / B-1117 -> `EV\gate3-misses.txt`.
3. **Grid** (scratch driver `EV\grid.py` swaps the module switches, then runs `eval_run.main()`;
   both as-of dates, `--baseline` = B-1029 / B-1117). Cells: tier 4 {off, last, cap1, cap2} x
   new document first {off, on} x newest band {off, 0.95, 0.9} (band only with new-document-first
   on). Per cell: PASS/FAIL, tier-1 doc/passage recall, refusal gap/all, forbidden, REGRESSED IDs,
   #199's four questions, Q4 `BAC-TR-2026Q2#63`, Q26 trade chunks, the step-2 chunks.
   **Choice:** the simplest cell (fewest rules on) that meets every Acceptance item at both dates;
   ties -> higher tier-1 doc recall at 2026-10-29, then fewer REGRESSED questions. A pre-plan probe
   (Progress log) suggests "tier 4 last + new document first", with the newest band if Q11 needs it.
   **Fallback:** if no cell meets every item at both dates, take the cell meeting the most items
   (ties as above), report the unmet items, and the PR says `Part of #198` / `Part of #199` for
   the issue(s) with an open item, listing them (CLAUDE.md PR rules); #197 still closes.
4. **Implement** the chosen cell in `fts.py` with the tests above; `PY -m pytest -q` -> all pass.
5. **Docs**: spec sketch, `fts.py` docstrings (#197 and the new rules), ADR-016 with the grid
   table and the chosen cell.
6. **Final evals on the committed code** (no driver):
   `eval_run.py --as-of 2026-10-29 --baseline EV/main-2026-10-29/report.json --out EV/final-1029`,
   `--as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-17/report.json --out EV/final-1117`,
   plus the no-trade comparison `--as-of 2026-10-29 --baseline D:\ALLPROJECTS\EDJ\cache\ev200\base-1029\report.json --out EV/final-1029-vs-notrade`.
   Determinism: rerun `final-1117` with itself as baseline -> 30 UNCHANGED.
   Per-question diff (`EV\diff-*.txt`): every question whose chunk list changed, with the chunks
   lost and gained; every lost chunk named in the PR.
   #107 check (scratch `EV\pre150.py`): for every question with a key (`doc_recall` not null in
   both reports), `doc_recall` in `EV\final-1029\report.json` vs
   `D:\ALLPROJECTS\EDJ\cache\rev150b\main-2026-10-29\report.json` -> `EV\diff-pre150.txt`
   (one line per question: before, after, OK / LOWER). Document level only: #150 changed the
   transcript chunk IDs, so passage recall and `--baseline` REGRESSED labels against that report
   compare different passages and are not the measure.
7. **Verify**: `verify_cee.py run` -> VERIFY PASS (retrieval change; no user feature changes, so
   no recipe update). `pytest -q` count >= main's.
8. **Baseline file**: the committed baseline is not replaced (the snapshot did not change; the
   PR shows the new numbers against it). Decision recorded in the Progress log.
9. Progress log, `/finish-task` (PR: `Closes #198`, `Closes #199`, `Closes #197` (or `Part of`
   per the step-3 fallback), `Refs #107`; area: retrieval). The PR says in one line that #197's
   "no code or config change" means no change to `doc_type_scope()` code or `config/`; the
   `select()` change belongs to #198/#199. #107 close-out (it is already closed): if
   `EV\diff-pre150.txt` has no LOWER line and forbidden is 0 in all 30, after the PR merges tick
   #107's last item with a comment citing `EV\final-1029`, `EV\final-1117` and
   `EV\diff-pre150.txt`; otherwise `gh issue reopen 107` with a comment naming the open item and
   the LOWER questions.

## Acceptance
#198 (trade press):
- [ ] Mock eval on `corpus-2026-11-17` (= corpus-2026-11-16 + ADV + trade + speaker turns):
      tier-1 doc recall >= the no-trade reference at both dates (>= 0.646 at 2026-10-29,
      >= 0.625 at 2026-11-17); doc recall at 2026-10-29: Q2 >= 0.444, Q5 >= 0.833, Q30 >= 1.0
      (no-trade values), Q6 >= 0.667 (#199's bar; its no-trade value 0.833 is reported only, not a
      bar). Check: `EV\final-1029`, `EV\final-1117` summaries.
- [ ] No PASS -> FAIL vs B-1029 and B-1117; refusal 5/5 gap and 19/19 all keyed (unchanged);
      forbidden 0 in all 30 at both dates.
- [ ] Q26 (as of 2026-11-17) still PASS with trade chunks inside the 90-day window (count of
      `*TRADE*` chunk_ids in `final-1117` Q26 >= 1, all dated within the window).
#199 (transcript slots), as of 2026-10-29:
- [ ] Doc recall Q6 >= 0.667, Q11 >= 0.875, Q13 >= 0.667, Q27 >= 0.444 (`EV\final-1029`).
- [ ] Q4 retrieves `BAC-TR-2026Q2#63` (in `final-1029` and `final-1117` Q4 `chunk_ids`), or
      the PR states the rank and what holds the slot.
#197 (docs):
- [ ] `specs/retrieval.md` doc-type scope comment names "compensation" (Q25) and
      "attrition rate" (Q28); `fts.doc_type_scope()` docstring names Q11, Q22-Q24, Q28 as
      benchmark questions; no change to `doc_type_scope()` code or `config/entities.yaml`
      (`git diff origin/main -- config/` empty).
Gate 3 retrieval misses (best effort, no regression):
- [ ] For Q11, Q13, Q17, Q22, Q23, Q25: each step-2 passage reported as now retrieved or not
      (with rank and what holds the slot); none of the six loses doc recall vs B-1029/B-1117.
#107 (already closed with its last item open; item "Mock eval for all 30: no forbidden hits,
no regressions"):
- [ ] `EV\diff-pre150.txt`: for every keyed question, `doc_recall` in `EV\final-1029` >=
      `doc_recall` in `D:\ALLPROJECTS\EDJ\cache\rev150b\main-2026-10-29\report.json` (document
      level only, see step 6), 0 LOWER lines; forbidden 0 in all 30. Holds -> item ticked on #107
      with that evidence, PR says `Refs #107`. Fails -> #107 reopened naming the open item (step 9).
Common:
- [ ] `PY -m pytest -q` -> all pass (count >= main's); new tests for both slot rules pass.
- [ ] `verify_cee.py run` -> VERIFY PASS.
- [ ] ADR-016 in `docs/DECISIONS.md` with the grid and the chosen cell; spec sketch updated.
- [ ] 0 real calls (PR Verification says so).

## Risks / unsure
- "Tier 4 last" can starve trade press where it is the only news (window questions keep it, the
  rule is off there); single-firm questions that expect a `*:trade` source (Q2, Q4, Q5, Q7, Q17,
  Q29 per ADR-015) are watched in the coverage column; "cap N" is the fallback cell.
- The newest band trades rank for recency; it can drop an older but better call (probe: Q6
  0.833 -> 0.667, still at #199's bar). Kept only if the grid needs it for Q11.
- Doc recall is measured against `expected_doc_ids`; a question can gain documents and still
  lose a key passage. Passage recall and the per-question diff are reported too.
- Gate 3's misses are partly answer-side (the model said "not in evidence" for a retrieved
  chunk); step 2 separates those from retrieval misses.

## Progress log
- 2026-11-17 22:54 - plan written on `tl/198-slots` from origin/main 1d592c3. Baselines run
  (step 1): B-1117 = committed baseline (28/2, 0.547), B-1029 28/2, 0.573; doctor PASS on
  `corpus-2026-11-17`. Pre-plan probe (scratch `EV\probe\`, monkeypatched `select()`, as of
  2026-10-29, tier-1 doc recall): main 0.573; new-doc-first 0.651; tier4-last 0.625; both 0.710
  (Q4 #63 retrieved; Q6 0.833, Q13 0.833, Q27 0.556, Q11 still 0.75; Q30 1.0; Q2 0.556; Q5 1.0;
  Q26 PASS at 11-17; 0.693 at 11-17); both + newest band 0.9: 0.742 (Q11 1.0, Q6 0.667). No PASS
  -> FAIL, refusal 5/5, in any probe cell. The probe only shaped the grid; step 3 decides.
- 2026-11-17 23:00 - plan review round 1: CHANGES REQUESTED
  ([#198 comment](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/issues/198#issuecomment-6969534618)).
  Fixed: #107 is already closed by the board automation with its last item open -> manual
  close-out (tick or reopen), PR says `Refs #107`; #107 check made concrete (pre-#150 report
  `rev150b\main-2026-10-29`, `doc_recall` per keyed question, `EV\diff-pre150.txt`, document
  level only); Q6 bar = 0.667 (#199), 0.833 reported only. Non-blocking taken: #197 one-liner in
  the PR; both rules apply to theme turns too (+ entity+theme fixture test); step-3 fallback
  (`Part of` with open items).
