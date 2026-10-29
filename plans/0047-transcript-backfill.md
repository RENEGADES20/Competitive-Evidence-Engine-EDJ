# 0047 - Backfill earnings-call transcripts to eight quarters per firm

Issue: #47    Role: C2    Spec: specs/transcripts-ir.md

## Goal
MS, SCHW and BAC have eight quarters of earnings-call transcripts (2024Q4-2026Q3) and RJF eight
(2024Q3-2026Q2, calendar quarter of the period end), as listed by the tech lead on #47
(2026-10-18): 21 new `<doc_id>.txt` files with speaker names, `published_at` = call date read
from the source, one manifest row each. No gaps.

## Source
No S&P Global or Bloomberg PDF for these calls is in the team Box or on this laptop, so the
calls come from free transcript pages (ADR-007 T-04 any third-party source, T-05 tier 3, T-08
scraping allowed with a delay), fetched and converted by the new
`scripts/convert_transcript_web.py`:
- MarketBeat earnings report pages, transcript "Provided by Quartr" (20 calls; source matrix
  rows *-MARKETBEAT-TRANSCRIPT). Speaker names with titles and a participant list.
- Roic.ai for SCHW-TR-2024Q4 only: MarketBeat's page for that call has no transcript. Speaker
  names without titles, no participant list.
The saved pages stay in the git-ignored `data/interim/transcripts-web/html/`.

## Calls added (call date as printed on the page; the converter stops on a mismatch)
| doc_id | period_end | call date | source |
|---|---|---|---|
| BAC-TR-2024Q4 | 2024-12-31 | 2025-01-16 | MarketBeat |
| BAC-TR-2025Q1 | 2025-03-31 | 2025-04-15 | MarketBeat |
| BAC-TR-2025Q2 | 2025-06-30 | 2025-07-16 | MarketBeat |
| BAC-TR-2025Q3 | 2025-09-30 | 2025-10-15 | MarketBeat |
| BAC-TR-2025Q4 | 2025-12-31 | 2026-01-14 | MarketBeat |
| MS-TR-2024Q4 | 2024-12-31 | 2025-01-16 | MarketBeat |
| MS-TR-2025Q1 | 2025-03-31 | 2025-04-11 | MarketBeat |
| MS-TR-2025Q2 | 2025-06-30 | 2025-07-16 | MarketBeat |
| MS-TR-2025Q3 | 2025-09-30 | 2025-10-15 | MarketBeat |
| MS-TR-2025Q4 | 2025-12-31 | 2026-01-15 | MarketBeat |
| RJF-TR-2024Q3 | 2024-09-30 | 2024-10-23 (fiscal Q4 2024) | MarketBeat |
| RJF-TR-2024Q4 | 2024-12-31 | 2025-01-29 (fiscal Q1 2025) | MarketBeat |
| RJF-TR-2025Q1 | 2025-03-31 | 2025-04-23 (fiscal Q2 2025) | MarketBeat |
| RJF-TR-2025Q2 | 2025-06-30 | 2025-07-23 (fiscal Q3 2025) | MarketBeat |
| RJF-TR-2025Q3 | 2025-09-30 | 2025-10-22 (fiscal Q4 2025) | MarketBeat |
| RJF-TR-2025Q4 | 2025-12-31 | 2026-01-28 (fiscal Q1 2026) | MarketBeat |
| SCHW-TR-2024Q4 | 2024-12-31 | 2025-01-21 | Roic.ai |
| SCHW-TR-2025Q1 | 2025-03-31 | 2025-04-17 | MarketBeat |
| SCHW-TR-2025Q2 | 2025-06-30 | 2025-07-18 | MarketBeat |
| SCHW-TR-2025Q3 | 2025-09-30 | 2025-10-16 | MarketBeat |
| SCHW-TR-2025Q4 | 2025-12-31 | 2026-01-21 | MarketBeat |

## Files to change
- scripts/convert_transcript_web.py - new: CALLS table, `fetch` (5 s between requests) and
  `convert` (page -> `<doc_id>.txt` in the PDF transcripts' format).
- data/manifest.csv - 21 rows (transcript, tier 3, date_basis source, url = the page used).
- plans/0047-transcript-backfill.md - this plan.
- Not in git: the .txt files (local data/raw/ for loading; Box upload link for the TL) and the
  saved pages (data/interim/).

## Steps
1. Fetch the pages; one call end to end first (MS-TR-2025Q1): convert -> manifest row ->
   data/raw/ -> `python -m cee.ingest.load --doc MS-TR-2025Q1`.
2. The other 20; the converter checks each page's call date against CALLS.
3. Exact content check: after the header, participant list, headings and speaker lines, every
   file's paragraphs equal the page's transcript paragraphs; no AI summary, ads, timestamps,
   "Licensed to", `<GO>` or edwardjones.com; sha256 matches the manifest; a second conversion
   reproduces every file byte for byte.
4. Load all locally; chunk count per transcript.
5. Independent review (8 read-only agents): GWIM tags from 3 angles, one agent per firm for
   company, quarter, call date and speakers, one completeness critic.
6. Retrieval (mock): Q4, Q6, Q26, Q27 and all 30 questions against a baseline database
   restored from corpus-2026-10-22.
7. `pytest -q`; `scripts/verify_cee.py run`.
8. PR: coverage list, chunk table, GWIM-tagged chunk list, known source errors, Box upload list.

## Acceptance
- [x] 21 new rows, 8 quarters per firm, no gaps; published_at = call date printed on the page
      (the converter prints the date basis per call)
- [x] Speaker names kept (titles where the page gives them); participant list under the PDF
      transcripts' headings; doc_ids `<ENTITY>-TR-<YYYY>Q<n>` (calendar quarter of period end).
      Differences from the PDF files, for #107: no "Question and Answer" heading (the pages
      have none); SCHW-TR-2024Q4 has no titles or participant list
- [x] Q4: PASS, BAC transcript chunks from five quarters in the top-8, 0 forbidden hits
- [ ] Every GWIM-tagged chunk of a new BAC transcript read in full: 0 wrong. 5 of 6 correct;
      BAC-TR-2025Q3#24 opens with a Consumer Banking sentence (open, see the log)
- [x] Q6, Q26, Q27 PASS; all 30 questions: same statuses as the baseline, 0 forbidden hits
- [x] No AI summary, ads, timestamps, "Licensed to", `<GO>` or edwardjones.com in any file
- [x] `pytest -q` passes; `verify_cee.py run` all PASS; 0 real calls
- [x] Nothing under data/raw/, data/interim/ or *.dump committed (git status before the commit)
- [ ] The 21 .txt files uploaded through the Box upload link

## Progress log
- 2026-10-20 15:34 - baseline on corpus-2026-10-18 (mock): Q4 FAIL 0 chunks, Q6 FAIL 0.33
  (RJF-TR-2026Q1/Q2), Q26 PASS, Q27 FAIL 0 chunks; Q4/Q27 also 0 at k=25 (no BAC chunk had
  segment GWIM).
- 2026-10-23 20:53 - #37 (PR #96) and #95 (PR #106) merged. Baseline on corpus-2026-10-22
  (mock): Q4 PASS (BAC-TR-2026Q1/Q2/Q3 in the top-8), Q6 PASS 0.67, Q26 PASS, Q27 PASS;
  0 forbidden hits (.eval-runs/corpus-2026-10-22-20261023-205357). 79 of 4,783 BAC chunks
  are GWIM, one per existing BAC transcript.
- 2026-10-23 21:09 - plan approved (source: S&P/Bloomberg PDFs); branch c2/47-transcript-backfill.
- 2026-10-23 21:44 - scope narrowed by the assignee to 2025 Q1-Q3 (12 calls) because 2024Q4
  was not available as a PDF.
- 2026-10-24 - no 2025 PDFs on the laptop or in the team Box. The assignee chose the free web
  route (Route B). Back to the issue's 21 calls, since the reason for narrowing no longer
  applied. MarketBeat has 20 of them; SCHW-TR-2024Q4 comes from Roic.ai. The page dates settle
  the Roic index errors (BAC/MS 2025Q2 = 2025-07-16; RJF 2025Q1 = 2025-04-23, confirmed by
  the firm's own release).
- 2026-10-24 - the pages repeat the speaker on every block of a long turn (1,302 of 2,570
  blocks); the converter writes the speaker once per turn, as in the PDF files. Loaded 21
  transcripts: 1,154 chunks (DB = corpus-2026-10-22 + 21 local transcripts, 15,836 chunks).
- 2026-10-24 - independent review: dates, quarters and companies right for all 21. Fixed in
  the converter: 49 double-encoded characters ("â€”" -> "—"), 15 speaker labels with a
  leading space (the page gives no name), checks against silently skipped turns, S&P-style
  participant headings. Not changed (source errors, listed in the PR): mis-transcribed figures
  (e.g. MS-TR-2025Q2 "202 million" for EPS $2.02), a few turns under the wrong speaker
  (MS-TR-2025Q2 operator lines, RJF-TR-2024Q4 closing, RJF-TR-2025Q3, SCHW-TR-2025Q1), a gap
  mid-answer in SCHW-TR-2025Q3, unnamed speakers (MS-TR-2025Q4 "Company Representative",
  RJF "Analyst at Goldman Sachs").
- 2026-10-24 - GWIM: 6 chunks tagged in the new BAC transcripts; 3 reviewers all judge
  BAC-TR-2025Q3#24 wrong: it opens with Consumer Banking's "strong digital adoption and Erika
  engagement continues, and customer experience scores remain elevated" before "Turning to
  wealth management". The tag rule is #95/#106 (TL, C1), outside this plan's files.
  Misses (untagged pure-GWIM chunks, e.g. BAC-TR-2024Q4#26, BAC-TR-2025Q4#19/#20/#51) are
  input for #107.
- 2026-10-24 21:28 - all 30 questions (mock) vs a baseline DB restored from corpus-2026-10-22:
  26 PASS / 2 FAIL (Q15, Q19, as before) / 2 NOT_EVALUATED, 0 forbidden hits. Coverage dips
  within PASS: Q7 1.0 -> 0.83 (new BAC GWIM transcript chunks displace BAC-10K-2025#246),
  Q14 1.0 -> 0.67 (older RJF transcripts displace an RJF press chunk); ranking quotas are S1's
  (#59). pytest 172 passed; verify-cee all PASS (.verify-runs/20261024-212727-30512a5).
- 2026-10-24 - assignee decisions: keep all 21 calls; leave the tag rule unchanged and report
  BAC-TR-2025Q3#24 on #95 for its owners; keep source errors as the pages give them and list
  them in the PR. The 21 .txt files are staged for the Box upload link.
- 2026-10-24 21:58 - in the running app (verify_cee launch, mock): one question per firm cites a
  backfilled transcript (RJF-TR-2024Q4#4, SCHW-TR-2024Q4#0, BAC-TR-2025Q2#31, MS-TR-2025Q2#9);
  each citation opens the stored passage, equal to the database, with its call date; Q4 cites
  only GWIM-tagged BAC chunks. 14/14 steps PASS (.verify-runs/c2-47-transcripts-2). Q4 and Q6
  themselves cite their top-3 chunks, which are 2026 documents.
