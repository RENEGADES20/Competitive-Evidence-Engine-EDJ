# 0003 - Source feasibility matrix: transcripts, IR, trade press

Issue: #3    Role: C2    Spec: specs/transcripts-ir.md (supplement rows: specs/filings.md, owner C1)

## Goal
One table lists every tier 3 (IR) and tier 4 (trade press) candidate source for the core
five (MS, SCHW, EDJ, MER/BAC, RJF): can we get it, what it costs, what the terms let us do
(scrape, store full text, show excerpts), and does the URL resolve. Terms questions go to
the ADR-000 owners (#9). A small manual checker re-tests the URLs monthly (feed rot).
Nothing is ingested. Split with #4: #3 = every row exists, URLs checked, terms researched,
unknowns listed; #4 = TL review, remaining TODO-verify, pick the first 3 transcripts.

## Files to change
- `docs/source_matrix.csv` (new) - one row per (entity, segment, doc_type, source). In docs/,
  not data/, because CLAUDE.md keeps only manifest.csv in data/.
- `docs/SOURCE_MATRIX.md` (new) - how to read it; coverage of every tier 3-4 pattern in the
  question bank; publisher terms table (quoted clauses, keyed T-01...); ADR-000 questions;
  considered-and-rejected list; monthly re-check instructions and log.
- `src/cee/ingest/check_sources.py` (new, owner C2) - URL checker,
  `python -m cee.ingest.check_sources [--update]`. Stdlib only. CSV path from cee.config.REPO_ROOT.
- `tests/test_check_sources.py` (new) - checker logic with a fake fetcher; no network.
- `tests/test_source_matrix.py` (new) - offline validation of the real CSV (runs in CI).
- `specs/transcripts-ir.md` - Open questions: link to the matrix and the T-xx questions.
- `docs/PROGRESS.md` - one status line.

## CSV columns
source_id, tier, entity_id, segment, doc_type, source_name, publisher, owner, url,
sample_url, url_pattern, format, access, cost, terms_url, terms_read_on, scraping,
full_text_storage, excerpts, adr000_ref, robots, rss_url, expected_cadence,
earliest_available, date_field, notes, manual_check_on, last_checked, url_status, sample_status

- source_id: unique, e.g. `MS-IR-TRANSCRIPT`, `T4-ADVISORHUB`.
- entity_id: an id from config/entities.yaml, or ALL (trade press: MS, SCHW, EDJ, MER, RJF;
  BAC only for GWIM items). segment: e.g. GWIM, else empty.
- doc_type: one per row, a key of `SOURCE_NAMES` in src/cee/answer/validate.py
  (transcript, deck, supplement, press, trade, monthly). Earnings slides = deck.
- source_name: human text, reusable as the "which source would answer" gap text.
- owner: C2, or C1 for supplements. format: html | pdf | xlsx | audio-only | rss.
- access: free | free-registration | metered | paywall | licensed | library | unknown.
- cost: as published (source in the terms table), "free", or "not published".
- scraping / full_text_storage / excerpts: allowed | forbidden | silent | unclear.
  The clause is quoted in SOURCE_MATRIX.md under adr000_ref/publisher. silent and unclear
  always have an adr000_ref. Silence is not permission.
- robots: result for the path we would fetch, with the date.
- expected_cadence: daily | weekly | monthly | quarterly | annual | ad hoc.
- earliest_available: oldest date reachable (recency: Q26 needs 90 days, Q27 needs 2026-01-01).
- date_field: where the real published date sits on the page, or "none" (then not ingestible:
  published_at is NOT NULL and the download date is forbidden).
- MER vs BAC: a BofA newsroom item is MER only when it is about Merrill / Merrill Wealth
  Management; GWIM-wide items are BAC with segment GWIM; decided per document at ingestion.
- manual_check_on: date a "blocked" URL was opened by hand in a browser.
- last_checked / url_status / sample_status: written only by the checker.
- Unknown facts: TODO-verify (CLAUDE.md). Unknown terms: unclear.

## Steps
1. Branch `c2/3-source-matrix`; save this plan with the first Progress log line.
2. Candidate list (show to the user before research): CSV rows with id, entity, segment,
   doc_type, source_name, publisher, url only. Per firm: earnings release, earnings slides,
   transcript, webcast replay, investor day / business update, conference presentations,
   monthly metrics (SCHW; check RJF), supplement (owner C1), newsroom press releases
   (BofA newsroom for MER; MS incl. Morgan Stanley at Work / E*TRADE for Q13; Schwab
   incl. Advisor Services and IMPACT for Q3; RJF recruiting announcements for Q2/Q6; EDJ
   newsroom, its only tier 3 path - no earnings calls). Wire services and IR RSS feeds.
   Free third-party transcript sites (tier label is a T-xx question). Tier 4: the 8 outlets
   in BRIEF.md plus FA-IQ, Financial Advisor magazine, Advisor Perspectives, general business
   press, WashU library databases (Factiva / ProQuest / Nexis Uni), RSS/Google News as a
   metadata-only route. 8-K Exhibit 99 copies go in notes as an alternative path (tier 2, C1).
   Firm-published surveys -> handed to C3 (#5), no rows. Anything left out goes in the
   considered-and-rejected list with a reason.
3. Research, trade press first (parallel agents per source group): access, cost (with its
   source), terms verdicts with quoted clauses and terms_url + terms_read_on, robots, rss,
   cadence, earliest_available, date_field, sample_url; for transcripts, who owns the text
   (a vendor copyright notice makes it licensed content -> ADR-000).
   No claim without a quote and URL; no legal conclusions.
4. Verify: every "allowed" or "forbidden" verdict gets two independent agents that try to
   refute it from the terms page; if either succeeds it becomes "unclear".
5. As soon as the trade-press terms are done: T-xx questions into SOURCE_MATRIX.md and, with
   the user's OK, a comment on #9 so the ADR-000 memo can use them. Ask TL whether they also
   want a separate DECISIONS.md-only PR.
6. Checker + tests. Sequential, one request per unique URL (rows sharing a URL are checked
   once), at least 1 s between requests to the same host, 15 s timeout. HEAD, then GET (read
   at most 64 KB) when HEAD fails. Status: ok (2xx) | moved (redirect to the site's front
   page, another host or a login page) | blocked (401/403/Cloudflare-style challenge;
   expected when access is paywall/metered) | error (5xx, 429, timeout, SSL; retried once) |
   dead (404/410/no such domain only) | skipped (sec.gov without EDGAR_IDENTITY).
   User-Agent: fixed, honest, names the repo; sec.gov uses settings().edgar_identity; the UA
   is never printed. Offline guard: if most results are connection/DNS errors, stop with exit
   2 and write nothing. Exit 0 = no dead, 1 = dead found, 2 = usage/CSV error or offline.
   `--update` writes only last_checked/url_status/sample_status, via a temp file +
   os.replace, keeping column and row order; refuses duplicate source_ids. Read utf-8-sig,
   write UTF-8 with LF; ASCII console output. Tests: status rules incl. 503 not dead, paywall
   403 ok, front-page redirect = moved; HEAD->GET fallback; offline stop writes nothing;
   unchanged file round-trips byte for byte; sec.gov UA; a guard that fails any real network call.
7. test_source_matrix.py: enums valid; entity_id known or ALL; doc_type in SOURCE_NAMES;
   unique source_id; silent/unclear rows have adr000_ref; date_field filled; at least one
   MER press row; every tier 3-4 expected_sources pattern in evals/questions.yaml has at least
   one row (for `*`: at least one row for that entity/segment).
8. Run the checker; replace or explain dead URLs; open "blocked" ones by hand and set
   manual_check_on; run with `--update`.
9. Write SOURCE_MATRIX.md: summary per firm x doc type, coverage table, terms table,
   T-xx questions, rejected list, re-check instructions (Windows and Mac commands) and log.
10. Link from specs/transcripts-ir.md; PROGRESS.md line; tick Acceptance; `/finish-task`
    (linked questions, row counts and manifest rows: N/A - nothing ingested; show the
    coverage table and checker output instead). PR also lists suggestions for C1
    (e.g. BAC expected_sources has no `trade`) and for TL (ARCHITECTURE.md doc_type list
    lacks `monthly`), and offers the CSV header to C3 for tier 5.

Unsure: IR-site terms may forbid stored copies (flag, do not decide); some sites block
scripts (hence blocked + manual check); trade-press prices are often not published;
recruiting web pages are often undated (date_field "none").

## Acceptance
- [x] Candidate list fixed in step 2; every candidate has a row, or is in the
      considered-and-rejected list with a reason. (100 rows, 74 rejected with reasons.)
- [x] Every row has access, cost and the three terms verdicts; each allowed/forbidden
      verdict has a quoted clause (terms table) that survived two refutation attempts;
      silent/unclear rows have an adr000_ref. (5 verdicts did not survive and are unclear.)
- [ ] Terms questions T-xx listed in SOURCE_MATRIX.md and handed to the ADR-000 owners
      (comment on #9); ADR-000 Status untouched. (Listed T-01..T-64; the #9 comment waits
      for the user's OK. DECISIONS.md not touched.) PARTLY MET.
- [ ] URLs: `.\.venv\Scripts\python.exe -m cee.ingest.check_sources` (Mac:
      `.venv/bin/python -m cee.ingest.check_sources`) -> 0 unexplained dead on <date>;
      every blocked row has manual_check_on; output pasted in the PR. PARTLY MET: second run
      2026-10-05, 196 URL cells (168 unique): 124 ok, 55 blocked, 17 error, 0 moved, 0 dead.
      The manual browser check of the 57 unique blocked/error URLs was deferred to #4 by the
      user (Claude in Chrome was not connected).
- [x] Linked questions Q1-Q6, Q26 (plus Q13, Q27 from the spec) and every other tier 3-4
      pattern in the bank (24 patterns, e.g. MS:transcript, BAC:transcript#GWIM, MER:press,
      SCHW:monthly, RJF:deck, RJF:*, MER:*, BAC:*#GWIM): at least one feasible row, or the
      matrix says why not. Checked by tests/test_source_matrix.py; table in SOURCE_MATRIX.md.
- [x] Recency: RJF rows reach back at least 90 days before the check date (Q26; on
      2026-10-03 that is 2026-07-05); MER and BAC#GWIM rows to 2026-01-01 (Q27); or the
      matrix says why not. (RJF newsroom from 2010, recruiting releases from 2022-12; Merrill
      items on the BofA newsroom from 2022-10.)
- [ ] Every row has date_field (or "none"); never the download date (spec). PARTLY MET: 81
      rows locate the date; 19 say TODO-verify (behind paywalls or bot walls), carried to #4.
- [x] Merrill press is entity MER, not BAC; the assignment rule is written down (spec, Q4/Q27).
- [x] Re-check monthly: command, runner (C2), log table in SOURCE_MATRIX.md. No cron, no alerts.
- [x] All tests pass (`python -m pytest -q`), offline.
- [x] Nothing ingested; manifest.csv unchanged; no .env, data/raw/, *.dump staged.

## Progress log
- 2026-10-01 22:29 - plan written (start-task #3); reviewed by a second agent, which moved
  the ADR-000 questions out of DECISIONS.md, reshaped the CSV to one doc_type per row and
  added the offline CSV test
- 2026-10-03 - Step 2: seven discovery agents plus a completeness critic found 118 candidates;
  merged duplicates and same-page sub-series, moved undated recruiting pages, a regulatory
  statement, BAC-wide news and Business Wire copies to the rejected list -> 100 rows, 74
  rejected. User decisions: keep all 7 third-party transcript sites and all tier 4 candidates;
  leave out the Canadian subsidiaries. TRADE-8 agent failed; the critic re-found the 8 outlets.
- 2026-10-03 - Step 6-7: check_sources.py (stdlib) + tests; tests/test_source_matrix.py checks
  the real CSV, including coverage of every tier 3-4 pattern in the bank.
- 2026-10-03 - Recency acceptance reworded to "90 days before the check date" (the date moved).
- 2026-10-04 - Steps 3-4: 11 research agents read the terms of 55 sites; two refuters per
  allowed/forbidden verdict (12 refuters hit a session limit and were re-run 2026-10-05).
  5 verdicts refuted -> unclear. Surprises: no core firm offers a free transcript archive
  (only BAC posts its own, from 1Q26); no site explicitly allows our use; Edward Jones's own
  site forbids robots and building a database without written permission; most trade press
  forbids storage and many forbid excerpts.
- 2026-10-05 - Step 8: checker run, 200 URLs: 137 ok, 43 blocked, 20 error, 0 moved, 0 dead.
  raymondjames.com never answers scripts, so the checker now skips a site after two URLs in a
  row with no answer. Library rows had text in sample_url: moved to notes, test added.
  Claude in Chrome was not connected; the user deferred the manual browser check to #4.
- 2026-10-05 - Step 9: SOURCE_MATRIX.md generated from the CSV and the research notes; general
  questions T-01..T-09, per-site T-10..T-64. Final review run (code, acceptance audit, and two
  refuters each for the key "BAC terms are silent" claims).
- 2026-10-05 - Final review: the two refuters per site confirmed that the Bank of America IR site
  and newsroom terms are silent (the business.bofa.com client terms are not linked from them).
  Code review fixes: GET only (a HEAD 200 hid bot-challenge pages, e.g. Citywire), bad CSV and
  odd URLs exit 2 instead of crashing, temporary DNS failure is error not dead, skipped sites
  count toward the offline guard, shared-hosting hosts compared in full. Audit fixes: joint
  Merrill + Private Bank items go to BAC#GWIM only (the BAC newsroom note said both rows),
  Kaltura terms added to BAC's Investor Day replay, stale notes and rejected entries corrected,
  legal conclusions reworded as questions, coverage table ignores repost sites and routes.
  Second URL check: 196 cells (168 unique), 124 ok, 55 blocked, 17 error, 0 dead; 57 unique
  URLs need the manual check in #4. 19 rows still have TODO-verify in date_field (#4).
