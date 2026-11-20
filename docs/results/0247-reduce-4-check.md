# #247 part 4 checks: "latest count found" note (item 9), RJF investor-day pin for Q23 (item 10)

Plan: `plans/0247-reduce-4.md` (approved at 95a704f after review rounds 1-2; round-2 non-blocking 1-6 written in at
53009f7). Code at `2d5f25b`; raw records of the real run at `6215d58`. Snapshot `corpus-2026-11-19`,
`--as-of 2026-11-17`. Evidence folder `D:\ALLPROJECTS\EDJ\cache\ev247d\`. **2 real DeepSeek calls** (Q23 only:
map.RJF and the reduce; `deepseek-v4-pro`, thinking on; $0.129 new); every other question 0 calls. `.env` never read
or printed (copied into the worktree for the real run inside `try`, removed in `finally`; absent before and after).
**Blind scoring: not done yet** (inputs in section 6; the TL starts the scorer).

## 1. Zero-call checks
- **pytest**: 1033 passed on main e15ccf8 before any change; 1048 at 2d5f25b (15 new in `tests/test_reduce_part4.py`;
  the DB pin test ran against `cee-db`, not skipped).
- **Mock 35** (`run-mock.ps1` / `.sh`; main e15ccf8 in `wt-247d-base` vs the branch; `diag\mock_direct.py` ->
  `mock-direct.txt`): every question's chunk lists, sub-question lists, status and refusal identical (the mock's rule
  plan has no series aspect, so the series pin never fires); claims and gaps identical everywhere; caveats differ
  only in Q11 (MS and Merrill notes) and Q23 (MS note). The mock's Q23 / Q24 Merrill rows hold no dated count, so
  there is no Merrill note there in the mock.
- **verify-cee** (`.verify-runs/20261120-124117-2d5f25b`): VERIFY PASS. ask-answer, ask-progress, gap-path,
  invalid-chunk, coverage, filters, feedback PASS; open-citation and download-document UNREACHABLE (no raw files in
  `data/raw/`, as in parts 2-3).

## 2. Item 10: why Q23 missed #43, and the `series_pins` scan
- `diag\pool43.txt`: `RJF-DECK-2025-investor-day#43` is in Q23's a1.RJF candidate pool (190 ids), but `select()`
  drops it: the deck already gives `#69`, `#126`, `#110` and `MAX_PER_DOC = 3`. The per-period pass cannot reach it:
  the deck has `period_end` NULL. Q11 keeps it under a4.RJF.
- `diag\pin_sim.txt`: pinning #43 for RJF `series` aspects of `advisor_headcount` changes only Q23 a1.RJF (+#43)
  among the eight replayed questions.
- **The rule** (registry header, `specs/filings.md`): a `series_pins` id is a chunk of the firm's tier 1-3 document
  with `period_end` NULL that states a count of the metric, on the entry's population, together with the count's
  own date in the chunk text (not a page header, capture, retrieval or publication date).
- **The scan** (`diag\series_pins_scan.sql`; full text in `series_pins_scan_full.txt`; reasons in
  `series_pins_scan_reasons.tsv`):
  ```sql
  SELECT c.chunk_id, d.doc_type, d.source_tier, d.published_at, regexp_replace(c.text, '\s+', ' ', 'g') AS text
  FROM chunks c JOIN documents d USING (doc_id)
  WHERE d.period_end IS NULL AND d.source_tier BETWEEN 1 AND 3
    AND d.entity_id IN ('MS','SCHW','EDJ','MER','BAC','RJF') AND d.doc_type <> 'transcript'
    AND c.text ~* '(financial|wealth)\s+advis|advisors|representatives|adviser'
    AND c.text ~ '\d[\d,]{2,}|\d+\s*K\y'
  ORDER BY c.chunk_id;
  ```
  It returns 120 rows. **Only `RJF-DECK-2025-investor-day#43` qualifies.** The 120 rows break down as follows:
  - 1 qualifies.
  - 4 are counts without their own date.
  - 5 are counts of another population.
  - 3 are Form ADV Item 5 employee counts (`*-ADV1A-2026#1`). They count employees, not the metric, and are already
    pinned through MS / BAC `see_also` and the SCHW definition chunk.
  - 3 are Form ADV headers.
  - 104 hold no advisor count.

  Tier-4 trade press is outside the rule: `RJF-TRADE-2026-11-05-IN-01#0` ("8,943 advisors" with a header date)
  would not qualify. `MER-PR-web-becoming-a-merrill-lynch-advisor#1` ("2,112 advisors named to Forbes 2025
  Best-in-State") counts ranked advisors, another population.
- **#43's "**" footnote**: the slide reads "Mar. 31, 2025**", but the footnote text is in no stored chunk of the
  deck (page 39 holds only #43), so an answer cannot explain the asterisk.

<details><summary>Scan rows, one reason each (120)</summary>

| Chunk | Type | Tier | Reason |
|---|---|---|---|
| `BAC-DECK-2025-investor-day#13` | deck | 3 | count without its own date: '>15K' / '>6K' Wealth Advisors (Merrill / Private Bank; already in BAC see_also) |
| `BAC-DECK-2025-investor-day#18` | deck | 3 | no advisor count: 546 offices |
| `BAC-DECK-2025-investor-day#34` | deck | 3 | another population: 2.4K advisor trainees, 1.6K specialized advisor practice roles |
| `BAC-DECK-2025-investor-day#50` | deck | 3 | no advisor count: no figure next to an advisor word |
| `BAC-DECK-2025-investor-day#64` | deck | 3 | no advisor count: Barron's Top 100 ranking names |
| `BAC-DECK-2025-investor-day#68` | deck | 3 | no advisor count: no figure next to an advisor word |
| `BAC-DECK-2025-investor-day#76` | deck | 3 | another population: Private Client Advisors 482 / 545 / 700 (2019, 3Q25, target), a role subset |
| `BAC-DECK-2025-investor-day#77` | deck | 3 | another population: Pathway Program participants (400, 60) |
| `BAC-DECK-2025-investor-day#9` | deck | 3 | count without its own date: '>15K Wealth Advisors' (Merrill and Private Bank; already in BAC see_also) |
| `EDJ-ADV-2026#1` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#114` | adv | 2 | no advisor count: FINRA review of 65,000 reports |
| `EDJ-ADV-2026#116` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#117` | adv | 2 | no advisor count: rule / section numbers ['203', '204'] (Form ADV legal or fee text) |
| `EDJ-ADV-2026#118` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#32` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#54` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#59` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#6` | adv | 2 | no advisor count: no figure next to an advisor word |
| `EDJ-ADV-2026#7` | adv | 2 | no advisor count: discretionary / non-discretionary assets in dollars |
| `MER-ADV1A-2026#0` | adv | 2 | Form ADV header: CRD number |
| `MER-ADV1A-2026#1` | adv | 2 | Form ADV Item 5 employees (unit employees), not the metric; already pinned (BAC see_also) |
| `MER-ADV-2026#0` | adv | 2 | no advisor count: addresses and phone numbers |
| `MER-ADV-2026#144` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#23` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#27` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#321` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#385` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MER-ADV-2026#386` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MER-ADV-2026#387` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MER-ADV-2026#388` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MER-ADV-2026#389` | adv | 2 | no advisor count: approximately 1,500 advisory accounts |
| `MER-ADV-2026#406` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#409` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#467` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#468` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#476` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#493` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#510` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MER-ADV-2026#511` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-ADV-2026#7` | adv | 2 | no advisor count: address |
| `MER-ADV-2026#92` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MER-PR-2026-09-15-01#0` | press | 3 | no advisor count: no figure next to an advisor word |
| `MER-PR-web-advisor-development-program#0` | press | 3 | no advisor count: no figure next to an advisor word |
| `MER-PR-web-advisor-development-program#1` | press | 3 | no advisor count: no figure next to an advisor word |
| `MER-PR-web-becoming-a-merrill-lynch-advisor#1` | press | 3 | another population: '2,112 advisors named to Forbes 2025 Best-in-State' (ranked advisors), no count date |
| `MER-PR-web-becoming-a-merrill-lynch-advisor#3` | press | 3 | no advisor count: no figure next to an advisor word |
| `MER-PR-web-becoming-a-merrill-lynch-advisor#4` | press | 3 | no advisor count: Barron's Top 100 list |
| `MER-PR-web-becoming-a-merrill-lynch-advisor#5` | press | 3 | no advisor count: no figure next to an advisor word |
| `MS-ADV1A-2026#0` | adv | 2 | Form ADV header: CRD number |
| `MS-ADV1A-2026#1` | adv | 2 | Form ADV Item 5 employees (unit employees), not the metric; already pinned (MS see_also) |
| `MS-ADV-2026#0` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#125` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#14` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#142` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#150` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#153` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#187` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#214` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#218` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#219` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#220` | adv | 2 | no advisor count: approximately 600 advisory accounts (SEC order) |
| `MS-ADV-2026#221` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MS-ADV-2026#222` | adv | 2 | no advisor count: rule / section numbers ['203'] (Form ADV legal or fee text) |
| `MS-ADV-2026#224` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MS-ADV-2026#225` | adv | 2 | no advisor count: rule / section numbers ['203', '206'] (Form ADV legal or fee text) |
| `MS-ADV-2026#226` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#230` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#239` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `MS-ADV-2026#248` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#72` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#75` | adv | 2 | no advisor count: no figure next to an advisor word |
| `MS-ADV-2026#83` | adv | 2 | no advisor count: phone number |
| `RJF-ADV-2026#0` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#100` | adv | 2 | no advisor count: rule / section numbers ['204'] (Form ADV legal or fee text) |
| `RJF-ADV-2026#116` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#117` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#121` | adv | 2 | no advisor count: rule / section numbers ['206'] (Form ADV legal or fee text) |
| `RJF-ADV-2026#13` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#2` | adv | 2 | no advisor count: SEC file number |
| `RJF-ADV-2026#27` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#33` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#42` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#56` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#59` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#73` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#74` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#75` | adv | 2 | no advisor count: 529 savings plans |
| `RJF-ADV-2026#77` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#78` | adv | 2 | no advisor count: FINRA Rule 4530 |
| `RJF-ADV-2026#81` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#84` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#94` | adv | 2 | no advisor count: no figure next to an advisor word |
| `RJF-ADV-2026#99` | adv | 2 | no advisor count: phone number / CRD |
| `RJF-DECK-2025-investor-day#126` | deck | 3 | count without its own date: 'approximately 9,000 employee and independent financial advisors' (biography) |
| `RJF-DECK-2025-investor-day#30` | deck | 3 | count without its own date: '8,731 PCG advisors' |
| `RJF-DECK-2025-investor-day#43` | deck | 3 | QUALIFIES: advisor count 8,731 with its own date 'Mar. 31, 2025' (FY2024 8,787 = RJF-10K-2025#227) |
| `RJF-DECK-2025-investor-day#45` | deck | 3 | no advisor count: no figure next to an advisor word |
| `RJF-DECK-2025-investor-day#93` | deck | 3 | no advisor count: no figure next to an advisor word |
| `RJF-PR-web-advisor-select#0` | press | 3 | no advisor count: Wayback capture timestamp / year ['20260311101214'] (recruiting page) |
| `RJF-PR-web-affiliation-options#0` | press | 3 | no advisor count: Wayback capture timestamp / year ['20260421065839'] (recruiting page) |
| `RJF-PR-web-affiliation-options#2` | press | 3 | no advisor count: no figure next to an advisor word |
| `RJF-PR-web-bank-and-credit-union-advisors#0` | press | 3 | another population: 940 Financial Institutions Division advisors; the date is the page capture date, not the count's |
| `RJF-PR-web-bank-and-credit-union-advisors#3` | press | 3 | no advisor count: no figure next to an advisor word |
| `RJF-PR-web-independent-advisor#0` | press | 3 | no advisor count: Wayback capture timestamp / year ['202', '20260519072648'] (recruiting page) |
| `RJF-PR-web-independent-advisor#2` | press | 3 | no advisor count: no figure next to an advisor word |
| `RJF-PR-web-independent-ria-custody-services#2` | press | 3 | no advisor count: no figure next to an advisor word |
| `RJF-PR-web-traditional-employee-advisor#0` | press | 3 | no advisor count: Wayback capture timestamp / year ['202', '20260516231525'] (recruiting page) |
| `SCHW-ADV1A-2026#0` | adv | 2 | Form ADV header: CRD number |
| `SCHW-ADV1A-2026#1` | adv | 2 | Form ADV Item 5 employees (unit employees), not the metric; already pinned (SCHW definition chunk) |
| `SCHW-ADV-2026#1` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#3` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#54` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#71` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#72` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#76` | adv | 2 | no advisor count: rule / section numbers ['204'] (Form ADV legal or fee text) |
| `SCHW-ADV-2026#85` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#88` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-ADV-2026#89` | adv | 2 | no advisor count: no figure next to an advisor word |
| `SCHW-DECK-2026-investor-day#172` | deck | 3 | no advisor count: no figure next to an advisor word |
| `SCHW-DECK-2026-investor-day#307` | deck | 3 | no advisor count: no figure next to an advisor word |
</details>

## 3. Replays (0 calls) and the count
All runs use `replay.ps1` (twin `replay.sh`):
- the run cache is emptied and seeded only from the committed `docs/results/0247b-raw/` (plus `0247d-raw/` after the
  real run);
- the reduce keys are pinned to the scored records (`diag\replay_part4.py`);
- `--max-calls 0`, key empty, no `.env`, clean tree;
- guard `diag\guard4.py`, logged in `head-log.txt`.

| Run | Commit | Guard |
|---|---|---|
| `replay-base` (8 questions) | main e15ccf8 (`wt-247d-base`) | OK: real_calls 0, reused 50, 50 raw records identical to the committed blobs |
| `replay` (8 questions) | branch 2d5f25b | OK: real_calls 0, reused 49 (Q23 map.RJF capped), 49 identical |
| `count-q23` (Q23, reduce key not pinned) | branch 2d5f25b | OK: real_calls 0, reused 5 (plan, MS, SCHW, EDJ, MER maps); **map.RJF capped and the reduce at the cap**, the only misses |
| `replay-final` (8 questions, Q23 pinned to the new reduce) | 6215d58 | OK: real_calls 0, reused 50, 50 identical (0247b-raw or 0247d-raw) |

The baseline equals part 3's final replay (`ev247c\replay`) for all eight questions.

## 4. The real run (Q23, `--max-calls 3`)
`run-real.ps1` (twin `run-real.sh`), commit 2d5f25b, out `ev247d\real-q23`.
- **2 real calls**: map.RJF (`Q23-map.RJF-44a0731d9503112c16bd07f8`) and the reduce
  (`Q23-reduce-3dafb1bf33f0af1c52191014`). No re-extraction. 5 records reused.
- Both new records are committed in `docs/results/0247d-raw/` (6215d58).
- Behavior `answer`; model output valid.
- The RJF cell is a fact. It holds:
  - 8,731 at 2025-03-31 (`RJF-DECK-2025-investor-day#43`);
  - the 10-K points (2023-2025 year-ends, with the employee / independent-contractor split);
  - 8,011 with no period (the slide's FY 2019 column).
- The answer has **C9 "Raymond James shows 8,731 financial advisors as of March 31, 2025"**, citing #43.
- RJF's period gap no longer names 2025Q1. It now lists 2024Q4, 2025Q2, 2025Q4 and 2026Q1-Q3.
- **No basis-break caveat** for RJF (the matrix has none).
- The MS note follows the MS span caveat ("... no figure after 2020-12-31 was found"). The two read together without
  contradiction: the note adds which document type and which later documents were read.

## 5. Branch vs baseline (final replay)
| Q | Answer | What changed |
|---|---|---|
| Q1, Q3, Q19, Q22, Q26 | identical | - |
| Q11 | changed | + "Morgan Stanley - Advisor headcount: latest count found in the quarterly financial supplements: 2020-12-31 (MS-SUPP-2020Q4#1); no count found in the quarterly financial supplements read since (MS-SUPP-2025Q4, MS-SUPP-2026Q1, MS-SUPP-2026Q2, MS-SUPP-2026Q3)." and the same for Merrill (Bank of America Corporation) 2023-12-31 (BAC-SUPP-2023Q4#2; BAC-SUPP-2025Q4..2026Q3); claims unchanged |
| Q24 | changed | the same two caveats; claims unchanged |
| Q23 | changed | new answer from the real run (section 4) with the two caveats; 22 claims and 12 adjacent items, the same counts as before, in new model text |

No answer has a note for EDJ, RJF or Schwab. No code text says "discontinued", "stopped", "no longer", "ceased" or
"last reported". Limitation (plan section 4): the model wrote Q11's and Q24's text without seeing the new caveat.

## 6. Blind inputs (prepared; scoring not started)
`D:\ALLPROJECTS\EDJ\cache\ev247d\blind-in\` holds:
- `answers-dump.txt`: Q11, Q23 and Q24 from `replay-final`; Q23 is byte-identical to the real run's dump.
- `questions.yaml`: from `evals/questions.yaml`, unchanged since part 3.
- `verdict-rule.txt`: part 3's rule, with the run list updated.

The scorer prompt is `ev247d\scorer-prompt.txt`; it writes `ev247d\verdicts-blind.json`. Hashes
(`ev247d\blind-in-hashes.txt`):
- answers-dump.txt c685204ca1a61d3ef4189f54f53c6db2974b5353bf4b48e46ad781178c5fbe31
- questions.yaml 0f9400be52aca221bbbde8c404ab04335a0b4537593c767434ffd3ee59e89a5b
- verdict-rule.txt f3dc76af2bdf10a46800a3ecb920f0ef76ded0499206267b706f182769dc6a90
- scorer-prompt.txt 064f43a8de66a0d0aeb8f7d0bd111b783984ef7456ea77e767d94b105684c1be

Unchanged answers keep their part-3 verdicts (Q1, Q3, Q19, Q22, Q26 PASS). Acceptance: no PASS -> FAIL (Q11, Q24);
Q23 may stay FAIL on the corpus gaps (NEXT item 11).

verdicts-blind.json sha256 509c7499179fad5c7d2808a315a16e043278a8ac5507f2aa172b68401b849b89 (part 4 re-check, Q11 / Q23 / Q24, fresh scorer agent, 0 API calls; committed alone before any comparison).

## 7. Blind re-score (part 4) and the comparison
**1/3 PASS** on the three changed answers (Q24 PASS; Q11, Q23 FAIL). Fresh scorer agent, inputs only
`ev247d\blind-in\` (hashes in section 6); file `docs/results/0247d/verdicts-blind.json` (hash above, committed alone
in 163437a).

| Q | Part 3 final (r2) | **Part 4** | Class | Borderline | Reason (scorer, short) |
|---|---|---|---|---|---|
| Q11 | PASS (borderline) | **FAIL** | s, r | yes | differences named explicitly; but only RJF and Merrill get a quoted written definition: MS only a 2020 count label (gaps on define / include / exclude), EDJ a metric label plus "employees or partners", Merrill's footnote from 2023 |
| Q23 | FAIL (r, s) | **FAIL** | r, c | no | series incomplete: EDJ eight quarters; MS 2019-20, Merrill 2022-23 (GWIM + Consumer Banking), RJF four points, Schwab none |
| Q24 | PASS | **PASS** | | no | EDJ ratio from one 10-Q; comparison stated invalid with each firm's reason |

**Q11 is a PASS -> FAIL flip on a borderline question.** Under the plan's acceptance this stops the merge; it goes to
the TL (the PR stays a draft; nothing is re-rolled).

**What differs in Q11 between the two scored answers** (0 calls; `diff ev247c\blind-in-r2\answers-dump.txt.Q11`
against the Q11 block of `ev247d\blind-in\answers-dump.txt`): **exactly two added lines, nothing else**. The two lines
are the code caveats:
- "Morgan Stanley - Advisor headcount: latest count found in the quarterly financial supplements: 2020-12-31
  (MS-SUPP-2020Q4#1); no count found in the quarterly financial supplements read since (MS-SUPP-2025Q4,
  MS-SUPP-2026Q1, MS-SUPP-2026Q2, MS-SUPP-2026Q3)."
- "Merrill (Bank of America Corporation) - Advisor headcount: latest count found in the quarterly financial
  supplements: 2023-12-31 (BAC-SUPP-2023Q4#2); no count found in the quarterly financial supplements read since
  (BAC-SUPP-2025Q4, BAC-SUPP-2026Q1, BAC-SUPP-2026Q2, BAC-SUPP-2026Q3)."

Claims, adjacent items, gaps and every other caveat are byte-identical.

**The part-4 reason's facts were all in the part-3 answer**, and the part-3 scorer named most of them:
- *MS has no written definition, only a 2020 count label.* Part 3 already had the same gaps G [a1.MS], [a3.MS],
  [a4.MS] ("not found in the documents searched"), claims C5-C7 (MS-SUPP-2020Q4, 2019-2020 points) and the by-firm
  caveat quoting 'Wealth Management representatives 15,950 ...'. The part-3 scorer: "the Morgan Stanley definition is
  a gap and its only count comes from a 2020 supplement".
- *EDJ is a label plus "employees or partners".* Part 3 already had C1 (the "Financial advisors (actual)" label) and
  the contrast quoting EDJ-10K-2025#35. The part-3 scorer: "EDJ label plus employees/partners".
- *Merrill's footnote dates from 2023.* Part 3 already had C2 and C22 (BAC-SUPP-2023Q4) and the same contrast quote.
  The part-3 scorer did not name the date; the part-4 scorer does. The new Merrill note states that date in words.

The part-3 scorer named one thing missing: the MS count is "flagged by date but not as possibly discontinued". The
new MS note addresses exactly that, within ground rule 4: it says no count was found in the later supplements, never
"discontinued". The two scorers read the same evidence on the same bar ("five definitions, quoted"), and the borderline
moved the other way. One reading is that the note puts the age of the MS and Merrill bases in plain words, and so
weakens the reading of "five definitions quoted". The other is scorer variance on a borderline. This document cannot
tell the two apart: the TL's adjudicating read of both versions decides.

**Q23**: FAIL before and after. RJF 2025Q1 is now in the answer (the r miss of part 3 is fixed). The scorer still
lists r: "Raymond James four annual/scattered points" names no passage the corpus holds. The section 9b SQL of part 3
found no other RJF count in 2024Q4-2026Q3 in tier 1-3. The rest is the corpus gap of NEXT item 11 (c).
**Q24**: PASS, unchanged.

Final for the eight, pending the TL's decision on Q11: Q1, Q3, Q19, Q22, Q24, Q26 PASS (kept or re-scored); Q11 FAIL
(borderline, flip); Q23 FAIL.
