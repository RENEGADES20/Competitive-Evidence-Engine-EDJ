# 0038 - Earnings releases from EDGAR 8-K exhibit 99.1 (MS, SCHW, BAC, RJF)

Issue: #38    Role: C2    Spec: specs/transcripts-ir.md (also specs/filings.md: reads EDGAR)

## Goal
The last four quarterly earnings releases for MS, SCHW, BAC and RJF (16 documents) are in
`data/manifest.csv`, each one the press release itself (8-K exhibit 99.1, not the cover page),
with the filing date as `published_at`. They load into the local database, so Q1, Q2, Q26 and
Q27 have dated management statements to cite.

## Files to change
- src/cee/ingest/releases.py (new) - find 8-Ks with Item 2.02, take the EX-99.1 attachment,
  store it and write its manifest row. Reuses `cee.ingest.manifest`; `edgar.py` (C1) is not
  changed. ADR-007 T-03: C2 owns 8-K exhibits.
- tests/test_releases.py (new) - fake EDGAR objects, no network
- data/manifest.csv - 16 new rows, `doc_type` press, `source_tier` 2
- plans/0038-earnings-releases.md - this plan
- Raw files: written to `data/raw/` (`CORPUS_SHARE_PATH` is empty on this machine), then
  uploaded through the Box upload link under their exact `<doc_id>.htm` names. Nothing under
  `data/raw/` is committed.

## Design choices
- doc_id follows the spec example: `<ENTITY>-PR-<filing date>-01`, e.g. `RJF-PR-2026-07-29-01`.
- `period_end` = the quarter the release reports: the last calendar quarter-end before the
  filing date (RJF fiscal quarters also end on calendar quarter-ends). All 16 are checked
  against the release headline and listed in the PR. Metadata only, never an answer figure.
- An Item 2.02 8-K with no EX-99.1 writes no row and prints the reason; the reason goes in the PR.

## Steps
1. Install edgartools 5.59.1 only (not docling/torch). Open one MS Item 2.02 8-K and confirm
   the attachment list and the EX-99.1 URL. Read only, nothing written.
2. Tests first: Item 2.02 filter, EX-99.1 chosen (not the cover or EX-99.2), missing exhibit
   gives a reason, doc_id format, `published_at` = filing date, re-run skips.
3. `releases.py` with CLI: `python -m cee.ingest.releases --entity MS --count 4`.
4. MS end to end; show one document's headline as proof it is the release. Then SCHW, BAC,
   RJF. Re-run all four: only "skip" lines.
5. Merrill: check whether MER (CIK 728612) files earnings 8-Ks of its own; list the result.
   BAC releases stay entity BAC.
6. Load only the 16 new documents (`python -m cee.ingest.load --doc <id>`); chunk count each.
7. Retrieval checks, no LLM: Q26 returns RJF release chunks published on or after 2026-07-17
   (90 days before 2026-10-15); Q1 returns MS release chunks.
8. `pytest -q`; `verify_cee.py run` (mock provider). 0 real model calls.

Unsure: whether SCHW files its quarterly release as Item 2.02 EX-99.1 (step 1 checks); retrieval
has no time-window filter yet (S1), so the Q26 check reads `published_at` on the hits.

## Acceptance
- [x] 16 rows (4 firms x 4 quarters) or a written reason per missing one; `published_at` = filing date
- [x] Each document is the release (EX-99.1), not the 8-K cover; one example headline in the PR
- [x] BAC releases stay entity BAC; Merrill-only releases listed (expected: none)
- [ ] Chunk counts per document in the PR; Q26 retrieval shows RJF release chunks from the last
      90 days; Q1 retrieval shows MS release chunks
      (chunk counts: done; Q1: done, top 8 and in the app; Q26: NOT met on main + this branch,
      RJF-PR-2026-07-22-01 ranks 106th; needs the SQL time window and per-source quotas, S1/#59)
- [x] `pytest -q` passes (fake EDGAR objects, no network); `verify_cee.py run` all PASS (mock)

## Progress log
- 2026-10-15 - plan drafted
- 2026-10-16 10:03 - plan approved; branch c2/38-earnings-releases created
- 2026-10-16 10:10 - Step 1: edgartools 5.59.1 installed. Every firm's earnings 8-K has items
  "2.02,..." and exactly one EX-99.1 (the release; EX-99.2/99.3 are supplement and deck).
  `attachment.download()` returns the HTML as text. Latest four filing dates: MS 2026-10-14,
  07-15, 04-15, 01-15; SCHW 2026-10-15, 07-21, 04-16, 01-21; BAC 2026-10-14, 07-14, 04-15,
  01-14; RJF 2026-07-22, 04-22, 01-28, 2025-10-22. RJF 2026-07-22 opens "RAYMOND JAMES
  FINANCIAL REPORTS FISCAL THIRD QUARTER OF 2026 RESULTS" (quarter ended June 30). MER
  (CIK 728612) has 3 8-Ks (1999, 1999, 2007), none Item 2.02: no Merrill-only releases.
- 2026-10-16 10:25 - Tests (5) and releases.py written. MS run stored 3 releases; the first
  headline reads "Morgan Stanley Third Quarter 2026 Earnings Results ... third quarter ended
  September 30, 2026". MS 2026-01-15 came back "no EX-99.1": edgartools lists 0 attachments
  for that filing, but its EDGAR index page shows EX-99.1 a4q25msearningsrelease.htm (plus
  EX-99.2 supplement and EX-99.3 strategic update). Added a fallback that reads the index page
  when edgartools sees no attachments, with 2 tests (7 pass). One MS run takes ~4 minutes.
- 2026-10-16 10:50 - SCHW, BAC, RJF: 4 each stored. Every file's own wording matches its
  period_end (SCHW "third quarter totaling", BAC "1Q26", RJF "FISCAL THIRD QUARTER OF 2026").
  MS re-run: SEC answered 403 "Access Denied" (then read timeouts) for every request,
  including a plain one: our IP is rate-limited. Stopped sending requests (ADR-007 T-08).
  MS-PR-2026-01-15-01 still to fetch once SEC answers again; 15 of 16 rows in.
- 2026-10-16 11:00 - Loaded the 15 (`load --doc`): MS 30/30/26; SCHW 69/70/58/68;
  BAC 53/53/50/56; RJF 105/103/76/109 chunks. Retrieval, no LLM, top 20:
  Q26 -> 20 RJF press chunks, 3 from RJF-PR-2026-07-22-01 (inside 90 days) but older releases
  rank first: no SQL time window yet (S1). Q1 -> 20 MS press chunks, 6 inside 90 days; the
  releases crowd out 10-K/10-Q chunks (per-source quotas, #59).
- 2026-10-16 13:40 - pytest 76 passed. verify_cee.py run: ask-answer, open-citation,
  gap-path, invalid-chunk PASS (.verify-runs/20261016-132651-b676722); download-document was
  UNREACHABLE until EDJ-10K-2025.htm was copied from Box raw/ into data/raw/, then PASS
  (.verify-runs/20261016-133802-b676722). 0 real model calls. SEC still times out at 13:45.
- 2026-10-16 15:05 - Branch fast-forwarded to main 17cae93 (#66 synonyms, #71 Item sections,
  #65 topics, #73 db wait). `load.py` uses the new Item splitting for 10-K/10-Q only, so press
  chunk counts are unchanged (database matches the 11:00 counts); the 15 raw files match their
  manifest sha256. pytest 83 passed.
- 2026-10-16 15:10 - MS-PR-2026-01-15-01, one retry: the 8-K list loaded and the 3 MS rows
  skipped, then the filing index page answered 403 Forbidden. Stopped (T-08); nothing written.
- 2026-10-16 15:12 - verify_cee.py run on 17cae93: all 5 features PASS
  (.verify-runs/20261016-151200-17cae93). Mock, 0 real model calls.
- 2026-10-16 15:15 - Retrieval on 17cae93, no LLM (90 days = published on or after 2026-07-18):
  Q1 top 8 -> 8 MS press chunks, 3 inside 90 days. Q26 top 8 -> none inside 90 days (RJF
  2026-01-28, 2025-10-22); top 20 -> 3 from RJF-PR-2026-07-22-01 (#7 call notice, #26 PCG net new
  assets table, #97 footnotes): no SQL time window yet (S1). Q2 top 20 -> 15 RJF press chunks.
  Q27 (MER) -> 0 hits: BAC press chunks carry no GWIM segment, so they stay out of Merrill.
  Table-heavy chunks (under 20% letters): SCHW about 60%, RJF about 50% of press chunks; this
  comes from the HTML-to-text step in `load.py`, outside this issue.
- 2026-10-16 15:20 - Review pass (4 reviewers, each finding challenged by a skeptic; 3 of 20
  held). (1) Real cause of the MS 2026-01-15 "no attachments": edgartools' cache holds a
  truncated copy of that filing's full-text submission (gzip ends early, 22 documents then a
  cut) and keeps /Archives files forever; a single-document download is not checked for
  completeness. `store_release` now refuses a release that does not end in `</html>` (all 15
  stored files do); docstring corrected. (2) The index-page fallback had no real test: added
  tests for the fallback body, an index page without EX-99.1, and a cut-off download; an
  injected late-binding bug and a removed completeness check now both fail the tests. pytest
  86 passed. (3) Correction to the 11:00 entry: "the releases crowd out 10-K/10-Q chunks" was
  not observed; the local database then held no MS/RJF/SCHW/BAC 10-K/10-Q, and the 11:00 and
  15:15 retrieval results describe corpus-2026-09-30 + the 15 releases only. Also noted: the
  four BAC releases are page images with a hidden white text layer; the text is chunked, but
  the stored HTML downloads as blank image frames (images not stored).
- 2026-10-16 15:22 - Raw files of the 15 releases uploaded through the Box upload link
  (done by Mingmin, not checked from here).
- 2026-10-16 15:25 - Full corpus: copied main's 24 10-K/10-Q files from Box raw/ (24 sha256
  match) and loaded all 40 manifest documents (13,053 chunks; press counts unchanged).
  Retrieval, no LLM, main + this branch: Q1 top 8 -> 1 MS press chunk (rest 10-Q/10-K), top 20
  -> 6 press (4 inside 90 days). Q2 -> 0 press in top 20 (RJF 10-K/10-Q). Q26 top 20 -> 0 RJF
  press chunks; RJF-PR-2026-07-22-01 first appears at rank 106 of 283, the first press chunk of
  any date at rank 38. With the hits filtered to published on or after 2026-07-18: 46 chunks =
  RJF-10Q-2026Q2 (37) + RJF-PR-2026-07-22-01 (9), top 8 all 10-Q. So the Q26 acceptance check
  is not met on main + this branch; it needs the SQL time window and per-source quotas (S1,
  #59). Q27 (MER) -> 0 hits: no BAC chunk (10-K, 10-Q or press) carries a segment yet (C1), so
  BAC releases stay BAC as required, and Merrill gets nothing.
- 2026-10-16 15:30 - MS-PR-2026-01-15-01: deleted the one truncated cache entry (confirmed: gzip
  never ends, no </SEC-DOCUMENT>), then one run. SEC answered; the re-downloaded bundle is whole,
  so edgartools' checked path was used. Stored: opens "Morgan Stanley Fourth Quarter and Full
  Year 2025 Earnings Results ... NEW YORK, January 15, 2026", "ended December 31, 2025"; URL
  a4q25msearningsrelease.htm (EX-99.1); ends in </html>; sha256 matches. Loaded: 31 chunks.
  16 of 16 rows in. Q1 top 8 now has 2 MS press chunks (2026-01-15, 2026-04-15). pytest 86 passed.
- 2026-10-16 15:33 - /finish-task on 41 documents: verify_cee.py run all 5 PASS
  (.verify-runs/20261016-153101-17cae93). Press path driven in the app with the script's own
  launch/cleanup (.verify-runs/20261016-153200-17cae93/press-release): Q1 cites
  MS-PR-2026-01-15-01#18 and MS-PR-2026-04-15-01#15; the source page shows the stored passage
  (matches the database), "Filed: 2026-01-15"; the downloaded release matches its sha256.
  Mock, 0 real model calls.
- 2026-10-16 15:36 - MS-PR-2026-01-15-01.htm also uploaded through the Box upload link: all 16
  raw files uploaded (done by Mingmin, not checked from here). Opening the PR as "Part of #38":
  the Q26 retrieval check stays open (S1 time window, #59 quotas).
