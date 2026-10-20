# Source feasibility matrix: transcripts, IR, trade press (tiers 3-4) and thematic research (tier 5)

Owner: C2 (Mingmin Kong). Issue #3; ExecPlan [plans/0003-source-matrix.md](../plans/0003-source-matrix.md); spec [specs/transcripts-ir.md](../specs/transcripts-ir.md). Ground rules: [CLAUDE.md](../CLAUDE.md).

Data: [source_matrix.csv](source_matrix.csv), 100 rows, one per (entity, segment, doc_type, source). Researched 2026-10-03 to 2026-10-05 from the live sites (Wayback captures where a site blocks scripts; noted per site). **Nothing has been ingested.**

This page records what each source is, whether we can reach it, what it costs and what its terms say, with the clause quoted. It does **not** decide what we may do: every open point is a question (T-01 to T-64) for the ADR-000 owners (tech lead, C1; memo draft in #9). "silent" means no clause was found; silence is not permission.

## Summary

- **No source explicitly allows what the prototype would do.** Across 55 sites, no terms grant permission to
  script-fetch, store full text and show quotes for a use like ours. The verdicts are "silent" (no clause),
  "unclear" (mostly: allowed only for personal / non-commercial use, see T-01) or "forbidden". Deciding is
  ADR-000's job; the questions are below.
- **Bank of America is the only firm whose IR site and newsroom are silent on all three points**
  (T-16 (investor.bankofamerica.com), T-17 (newsroom.bankofamerica.com)). That covers BAC releases, slides,
  supplements, the 2025 Investor Day deck (its video replay is on Kaltura, whose terms are unclear, T-23 (kaltura.com)),
  BAC's own earnings-call transcripts (from 1Q26) and 2026 conference transcripts, and the Merrill releases on the BofA newsroom (back to 2022, enough for Q27).
- **Morgan Stanley, Schwab and Raymond James IR sites** allow use only for personal / non-commercial purposes
  (T-10 (morganstanley.com), T-12 (aboutschwab.com), T-19 (raymondjames.com)). Schwab's terms also bar automated downloads
  without written approval, and raymondjames.com and aboutschwab.com block scripts. Many of the same documents are
  also 8-K exhibits on EDGAR (T-03).
- **Edward Jones's own site forbids robots and building a database from it** without written permission
  (T-21 (edwardjones.com)), and PR Newswire, which carries the same releases, forbids it too (T-18 (prnewswire.com)).
  Q17 needs EDJ press; asking for written permission is T-02.
- **Earnings-call transcripts are the biggest gap** (T-04). No core firm offers a free text archive: Morgan Stanley
  and Schwab post webcast replays only, Raymond James keeps a 30-day replay, and every free third-party transcript
  site owns or licenses the text (storage forbidden or unclear). BAC's own 2026 transcripts are the only ones
  whose terms are silent rather than restrictive (silence is not permission); this matters for #4.
- **Trade press**: 23 of 34 tier 4 rows forbid storing full text and 16 forbid excerpts; the rest are unclear or
  silent (the silent ones are small or vendor blogs). The WashU library databases forbid systematic downloading.
  Unless ADR-000 decides otherwise or permission is obtained, trade press is likely limited to metadata + link
  (T-06), and a link alone cannot support a claim (ground rule 1).
- **Coverage**: every tier 3-4 pattern the question bank expects (24) has at least one row; see the coverage table
  for the least restrictive terms per pattern.
- **Recency**: Q26 needs Raymond James items from the last 90 days. Raymond James's archives reach back years, but
  its newsroom and recruiting releases sit on raymondjames.com, which gives scripts no answer, and Business Wire
  (its other wire for advisor news) returns 403; within the window, a script can technically reach only the
  corporate releases on GlobeNewswire (T-20 (globenewswire.com)) and the 8-K copies on EDGAR (T-03). The rest must be
  opened by hand. Q27 needs Merrill and BAC GWIM items from
  2026-01-01: Merrill releases on the BofA newsroom reach back to 2022; BAC decks, releases and supplements to 2021;
  BAC's own call transcripts start with 1Q26 (the 4Q25 call is only on third-party sites).
- **Dates**: 81 rows say where the real published date sits on a document page; 19 say TODO-verify because the pages sit behind paywalls or bot walls (carried to #4). Pages with no date at all are out (T-09).
- **Verification**: every allowed/forbidden verdict was re-read by two independent checkers. Five did not survive
  and are shown as unclear (AlphaStreet storage and excerpts, Dakota storage, Business Journals and Tampa Bay Times
  excerpts).
- **URL check 2026-10-05** (`python -m cee.ingest.check_sources`, second run after the review fixes): 196 URL
  cells (168 unique URLs): 124 ok, 55 blocked, 17 error, 0 moved, 0 dead. Blocked means a paywall or a bot wall
  (Schwab IR and content.schwab.com, Seeking Alpha, Investing.com, AlphaStreet, Citywire, FA magazine, ThinkAdvisor,
  PlanAdviser, WSJ, Barron's, FT, Reuters, Business Journals); error means no answer at all (raymondjames.com,
  bloomberg.com). The 57 unique blocked or error URLs still need to be opened by hand in a browser and dated in
  `manual_check_on`: not done in #3, carried to #4.

## How to read the CSV

| Column | Meaning |
|---|---|
| `source_id` | Unique id, `<ENTITY>-<PUBLISHER>-<DOCTYPE>[-<QUALIFIER>]`; trade press `T4-<OUTLET>`. |
| tier / entity_id / segment / doc_type | Tier 3 (IR) or 4 (trade press). Entity from `config/entities.yaml`, or ALL for trade press (MS, SCHW, EDJ, MER, RJF; BAC only for GWIM items). doc_type is a key of `SOURCE_NAMES` in `src/cee/answer/validate.py`; earnings slides count as `deck`, webcast replays without text as `transcript` with format `audio-only`. |
| `segment` | GWIM when the row's documents carry GWIM-specific pages or remarks (a passing mention does not count). Ingestion still tags each chunk, not the whole document (Merrill vs Bank of America, rule 6). |
| source_name / publisher / owner | Human-readable name (reusable as the "which source would answer" gap text), who runs the site, and the team owner (C1 for supplements, C2 otherwise). |
| url / sample_url / url_pattern / rss_url | Landing page (checked monthly), one real document (checked monthly), the pattern of document URLs, and a feed if there is one. |
| format / access / cost | html, pdf, xlsx, audio-only or rss. free, free-registration, metered, paywall, licensed, library or unknown. Cost only as published by the source (link in the site section below). |
| terms_url / terms_read_on | The terms we read and the date. |
| scraping / full_text_storage / excerpts | allowed, forbidden, silent or unclear: what the terms say about automated access, keeping a full copy, and showing short quotes. Where several sites govern a row (e.g. an IR page plus its webcast host), the strictest verdict wins. Every allowed/forbidden verdict was re-read by two independent checkers; a verdict either of them refuted is shown as unclear. |
| `adr000_ref` | The site section below (T-xx) with the quotes and the open questions. |
| `robots` | robots.txt for the paths we would fetch, with the date. A technical signal, not permission. |
| expected_cadence / earliest_available | How often new items appear, and the oldest date we could actually reach (recency: Q26 needs 90 days, Q27 needs 2026-01-01). |
| `date_field` | Where the real published date sits on a document page, or `none` (then the page cannot be ingested: `published_at` is required and the download date is never used). |
| `manual_check_on` | Date a URL the checker reports as blocked was opened by hand in a browser. |
| last_checked / url_status / sample_status | Written only by the URL checker (see the last section). |

## Coverage of the question bank

Every tier 3-4 `expected_sources` pattern in [evals/questions.yaml](../evals/questions.yaml) and the rows that could serve it. "Least restrictive storage terms" is the best `full_text_storage` verdict among those rows (it is not a permission). `tests/test_source_matrix.py` fails if a pattern loses all its rows.

Access routes and sites that repost other publishers' articles are left out of that column, because the text a reader would use there is governed by the original publisher: `T4-BINGNEWS`, `T4-DIAMOND`, `T4-FACTIVA`, `T4-GOOGLENEWS`, `T4-NEWSBANK`, `T4-NEXISUNI`, `T4-PROQUEST`.

| Pattern | Questions | Rows | Least restrictive storage terms |
|---|---|---|---|
| `BAC:*#GWIM` | Q27 | BAC-IR-DECK-EARNINGS, BAC-IR-DECK-INVESTORDAY, BAC-BOFANEWS-PRESS-GWIM, BAC-IR-PRESS-EARNINGS, BAC-PRN-PRESS-GWIM, BAC-IR-SUPPLEMENT (+10 more) | silent (BAC-IR-DECK-EARNINGS) |
| `BAC:deck#GWIM` | Q9 | BAC-IR-DECK-EARNINGS, BAC-IR-DECK-INVESTORDAY | silent (BAC-IR-DECK-EARNINGS) |
| `BAC:supplement#GWIM` | Q11, Q22, Q23, Q24, Q28 | BAC-IR-SUPPLEMENT | silent (BAC-IR-SUPPLEMENT) |
| `BAC:transcript#GWIM` | Q4, Q7, Q9, Q10, Q17, Q21 | BAC-ALPHASTREET-TRANSCRIPT, BAC-FOOL-TRANSCRIPT, BAC-INVESTINGCOM-TRANSCRIPT, BAC-IR-TRANSCRIPT-CONFERENCE, BAC-IR-TRANSCRIPT-EARNINGS, BAC-IR-TRANSCRIPT-INVESTORDAY (+4 more) | silent (BAC-IR-TRANSCRIPT-CONFERENCE) |
| `EDJ:press` | Q17 | EDJ-NEWSROOM-PRESS, EDJ-PRN-PRESS | forbidden (EDJ-NEWSROOM-PRESS) |
| `MER:*` | Q27 | MER-BOFANEWS-PRESS, MER-PRN-PRESS, T4-ADVISORHUB, T4-ADVIZORPRO, T4-AMERICANBANKER, T4-BARRONS (+30 more) | silent (MER-BOFANEWS-PRESS) |
| `MER:press` | Q4, Q17, Q19 | MER-BOFANEWS-PRESS, MER-PRN-PRESS | silent (MER-BOFANEWS-PRESS) |
| `MER:trade` | Q4, Q7, Q17 | T4-ADVISORHUB, T4-ADVIZORPRO, T4-AMERICANBANKER, T4-BARRONS, T4-BARRONSADVISOR, T4-BINGNEWS (+28 more) | silent (T4-FINTRX) |
| `MS:deck` | Q1, Q5, Q9, Q13 | MS-IR-DECK | unclear (MS-IR-DECK) |
| `MS:press` | Q17, Q19, Q22 | MS-IR-PRESS-EARNINGS, MS-NEWSROOM-PRESS | unclear (MS-IR-PRESS-EARNINGS) |
| `MS:supplement` | Q1, Q11, Q22, Q23, Q24 | MS-IR-SUPPLEMENT | unclear (MS-IR-SUPPLEMENT) |
| `MS:trade` | Q5, Q7, Q17, Q29 | T4-ADVISORHUB, T4-ADVIZORPRO, T4-AMERICANBANKER, T4-BARRONS, T4-BARRONSADVISOR, T4-BINGNEWS (+28 more) | silent (T4-FINTRX) |
| `MS:transcript` | Q1, Q5, Q7, Q9, Q10, Q13, Q16, Q17, Q21 | MS-ALPHASTREET-TRANSCRIPT, MS-FOOL-TRANSCRIPT, MS-INVESTINGCOM-TRANSCRIPT, MS-IR-TRANSCRIPT-WEBCAST, MS-MARKETBEAT-TRANSCRIPT, MS-ROIC-TRANSCRIPT (+2 more) | unclear (MS-ALPHASTREET-TRANSCRIPT) |
| `RJF:*` | Q26 | RJF-IR-DECK-EARNINGS, RJF-IR-DECK-EVENTS, RJF-IR-MONTHLY, RJF-ADVISOROPP-PRESS-RECRUITING, RJF-GNW-PRESS, RJF-IR-PRESS-EARNINGS (+45 more) | silent (RJF-GNW-PRESS) |
| `RJF:deck` | Q8 | RJF-IR-DECK-EARNINGS, RJF-IR-DECK-EVENTS | unclear (RJF-IR-DECK-EARNINGS) |
| `RJF:press` | Q2, Q6, Q14, Q17, Q19, Q22, Q23 | RJF-ADVISOROPP-PRESS-RECRUITING, RJF-GNW-PRESS, RJF-IR-PRESS-EARNINGS, RJF-NEWSROOM-PRESS | silent (RJF-GNW-PRESS) |
| `RJF:supplement` | Q11, Q22, Q23, Q24 | RJF-IR-SUPPLEMENT | unclear (RJF-IR-SUPPLEMENT) |
| `RJF:trade` | Q2, Q7 | T4-ADVISORHUB, T4-ADVIZORPRO, T4-AMERICANBANKER, T4-BARRONS, T4-BARRONSADVISOR, T4-BINGNEWS (+28 more) | silent (T4-FINTRX) |
| `RJF:transcript` | Q2, Q6, Q7, Q10, Q14, Q17, Q21 | RJF-ALPHASTREET-TRANSCRIPT, RJF-FOOL-TRANSCRIPT, RJF-INVESTINGCOM-TRANSCRIPT, RJF-IR-TRANSCRIPT-INVESTORDAY, RJF-IR-TRANSCRIPT-WEBCAST, RJF-MARKETBEAT-TRANSCRIPT (+3 more) | unclear (RJF-ALPHASTREET-TRANSCRIPT) |
| `SCHW:deck` | Q3, Q8 | SCHW-IR-DECK-EARNINGS, SCHW-IR-DECK-EVENTS | unclear (SCHW-IR-DECK-EARNINGS) |
| `SCHW:monthly` | Q12, Q22 | SCHW-IR-MONTHLY, SCHW-PRESSROOM-MONTHLY | unclear (SCHW-IR-MONTHLY) |
| `SCHW:press` | Q17, Q19 | SCHW-IR-PRESS-EARNINGS, SCHW-PRESSROOM-PRESS | unclear (SCHW-IR-PRESS-EARNINGS) |
| `SCHW:supplement` | Q22 | SCHW-IR-SUPPLEMENT | unclear (SCHW-IR-SUPPLEMENT) |
| `SCHW:transcript` | Q3, Q10, Q12, Q16, Q17, Q21 | SCHW-ALPHASTREET-TRANSCRIPT, SCHW-FOOL-TRANSCRIPT, SCHW-INVESTINGCOM-TRANSCRIPT, SCHW-IR-TRANSCRIPT, SCHW-IR-TRANSCRIPT-WEBCAST, SCHW-MARKETBEAT-TRANSCRIPT (+3 more) | unclear (SCHW-ALPHASTREET-TRANSCRIPT) |

## Sources by firm (tier 3)

### Morgan Stanley (MS)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `MS-IR-DECK` | deck | pdf | free | silent / unclear / unclear | T-10 | 2001-05-02 | PDF cover date under the presenter line (e.g. 'January 15, 2026' under 'Ted Pick, Chairma… |
| `MS-IR-PRESS-EARNINGS` | press | pdf | free | silent / unclear / unclear | T-10 | 1999 | PDF page-1 dateline 'NEW YORK, July 15, 2026' under the headline; the HTML stub shows 'Ju… |
| `MS-NEWSROOM-PRESS` | press | html | free | silent / unclear / unclear | T-10 | 2005 | 'Mon D, YYYY' line directly under the headline (e.g. 'Jun 26, 2026'); RSS <pubDate> (e.g.… |
| `MS-IR-SUPPLEMENT` | supplement | pdf | free | silent / unclear / unclear | T-10 | 2001 | The PDF cover gives only the quarter ('Second Quarter 2026 Earnings Results / Quarterly F… |
| `MS-ALPHASTREET-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-28 | 2020-01-16 | Date line under the headline on current pages (e.g. 'July 14, 2026' on the BAC page). Bod… |
| `MS-FOOL-TRANSCRIPT` | transcript | html | free | forbidden / unclear / unclear | T-24 | 2018-04 | Body 'DATE' block gives the call date ('Wednesday, July 15, 2026 at 8:30 a.m. ET'); bylin… |
| `MS-INVESTINGCOM-TRANSCRIPT` | transcript | html | free | forbidden / forbidden / forbidden | T-26 | 2024-10 | 'Published Jul 15, 2026, 09:43 AM' directly under the headline, above the byline 'By Inve… |
| `MS-IR-TRANSCRIPT-WEBCAST` | transcript | audio-only | free-registration | silent / forbidden / forbidden | T-10 | 2026-04-15 | Webcast registration page: event date and time line under the title (e.g. 'Wed, July 15,… |
| `MS-MARKETBEAT-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-29 | 2024-10-16 | Date 'July 15, 2026' directly under the 'Provided by Quartr' line below the 'Morgan Stanl… |
| `MS-ROIC-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-30 | 2007-03-21 | Line 'Q2 FY2026 · Earnings Call Transcript' followed by 'July 15, 2026' above the transcr… |
| `MS-SEEKINGALPHA-TRANSCRIPT` | transcript | html | unknown | forbidden / unclear / unclear | T-25 | 2007-06 | TODO-verify on the article page (403). Available: RSS <pubDate> (e.g. 'Tue, 15 Sep 2026 1… |
| `MS-YAHOO-TRANSCRIPT` | transcript | html | paywall | forbidden / forbidden / forbidden | T-27 | TODO-verify | TODO-verify (page returned 404 to curl and WebFetch on 2026-10-04); URL and title carry o… |

### Charles Schwab (SCHW)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `SCHW-IR-DECK-EARNINGS` | deck | pdf | free | forbidden / unclear / unclear | T-12 | 2019-04 | PDF cover slide, e.g. 'Summer Business Update July 21, 2026'. Date also in the filename (… |
| `SCHW-IR-DECK-EVENTS` | deck | pdf | free | forbidden / unclear / unclear | T-12 | 2024-05-22 | Events page: date line above each event title (e.g. 'Thursday, May 14, 2026'). The Invest… |
| `SCHW-IR-MONTHLY` | monthly | pdf | free | forbidden / unclear / unclear | T-12 | 2020-02 | PDF dateline in the first paragraph: 'WESTLAKE, Texas, September 15, 2026 –'. The report… |
| `SCHW-PRESSROOM-MONTHLY` | monthly | html | free | unclear / unclear / unclear | T-13 | 2017-02-14 | <span class="module_date-text">09/15/2026</span> under the headline. The Business Wire da… |
| `SCHW-IR-PRESS-EARNINGS` | press | pdf | free | forbidden / unclear / unclear | T-12 | 2019-04-15 | PDF dateline in the first paragraph: 'WESTLAKE, Texas, July 21, 2026 –' |
| `SCHW-PRESSROOM-PRESS` | press | html | free | unclear / unclear / unclear | T-13 | 2017-01-04 | <span class="module_date-text">07/21/2026</span> under the headline. Also RSS <pubDate> (… |
| `SCHW-IR-SUPPLEMENT` | supplement | xlsx | free | forbidden / unclear / unclear | T-12 | 2019-04-15 | The workbook itself is undated; release date = the earnings date on the IR listing. The p… |
| `SCHW-ALPHASTREET-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-28 | 2025-07-18 | Body line 'Charles Schwab Corp (NYSE: SCHW) Q2 2025 Earnings Call dated Jul. 18, 2025' (c… |
| `SCHW-FOOL-TRANSCRIPT` | transcript | html | free | forbidden / unclear / unclear | T-24 | 2024-10 | Body 'DATE' block (call date and time ET) under 'Image source'; byline 'By Motley Fool Tr… |
| `SCHW-INVESTINGCOM-TRANSCRIPT` | transcript | html | free | forbidden / forbidden / forbidden | T-26 | 2026-01 | 'Published Jul 21, 2026, 09:45 AM' under the headline (publish time) |
| `SCHW-IR-TRANSCRIPT` | transcript | pdf | licensed | forbidden / forbidden / forbidden | T-12 | 2019-04-25 | Bloomberg page header 'FINAL TRANSCRIPT 2019-04-25' at the top of each page. The footer s… |
| `SCHW-IR-TRANSCRIPT-WEBCAST` | transcript | audio-only | free-registration | forbidden / unclear / unclear | T-12 | 2019-07 | ON24 page <meta name="description" content="Tuesday, July 21, 2026 at 7:30 AM Central Day… |
| `SCHW-MARKETBEAT-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-29 | 2024-10-15 | Date line under 'Provided by Quartr' below the 'Charles Schwab Q2 2026 Earnings Call Tran… |
| `SCHW-ROIC-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-30 | 2011-10-26 | Line 'Q2 FY2026 · Earnings Call Transcript' plus the call date above the transcript. Also… |
| `SCHW-SEEKINGALPHA-TRANSCRIPT` | transcript | html | unknown | forbidden / unclear / unclear | T-25 | 2023 | TODO-verify on the article page (403). RSS <pubDate>; sitemap <lastmod> 2026-07-22T03:53:… |
| `SCHW-YAHOO-TRANSCRIPT` | transcript | html | paywall | forbidden / forbidden / forbidden | T-27 | TODO-verify | TODO-verify (404 to scripts on 2026-10-04); URL and title give only the fiscal period |

### Edward Jones (EDJ)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `EDJ-NEWSROOM-PRESS` | press | html | free | forbidden / forbidden / unclear | T-21 | 2025-03 | Dateline at the start of the body after the summary bullets (e.g. 'ST. LOUIS, Mo., Sept.… |
| `EDJ-PRN-PRESS` | press | html | free | forbidden / forbidden / forbidden | T-18 | 2010-02-15 | timestamp 'Sep 30, 2026, 09:00 ET' under the headline in the 'News provided by' block; bo… |

### Bank of America, GWIM (BAC)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `BAC-IR-DECK-CONFERENCE` | deck | pdf | free | silent / silent / silent | T-16 | 2021-09-13 | PDF cover page 1 date (e.g. 'November 7, 2024' under 'BancAnalysts Association of Boston… |
| `BAC-IR-DECK-EARNINGS` | deck | pdf | free | silent / silent / silent | T-16 | 2021-04-15 | PDF cover page 1: 'July 14, 2026' under 'Bank of America / 2Q26 Financial Results'; also… |
| `BAC-IR-DECK-INVESTORDAY` | deck | pdf | free | silent / silent / silent | T-16 | 2025-11-05 | PDF page 1 footer line 'Bank of America Investor Day November 5, 2025' |
| `BAC-BOFANEWS-PRESS-GWIM` | press | html | free | silent / silent / silent | T-17 | 2022-02 | line 'September 15, 2026 at 9:00 AM Eastern' above the headline, below the category tag;… |
| `BAC-IR-PRESS-EARNINGS` | press | pdf | free | silent / silent / silent | T-16 | 2021-04-15 | No dateline in the PDF. The p.1 headline gives only the period ('Bank of America Reports… |
| `BAC-PRN-PRESS-GWIM` | press | html | free | forbidden / forbidden / forbidden | T-18 | 2010-01-04 | timestamp 'Oct 01, 2026, 09:00 ET' under the headline in the 'News provided by Bank of Am… |
| `BAC-IR-SUPPLEMENT` | supplement | pdf | free | silent / silent / silent | T-16 | 2021-04-15 | PDF cover 'Supplemental Information / Second Quarter 2026' (period only, no release date)… |
| `BAC-ALPHASTREET-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-28 | 2020-01-15 | Date line 'July 14, 2026' under the headline. Body line 'Bank of America Corporation (NYS… |
| `BAC-FOOL-TRANSCRIPT` | transcript | html | free | forbidden / unclear / unclear | T-24 | 2017-10 | Body 'DATE' block gives the call date ('Tuesday, July 14, 2026 at 8:30 a.m. ET' on the Ya… |
| `BAC-INVESTINGCOM-TRANSCRIPT` | transcript | html | free | forbidden / forbidden / forbidden | T-26 | 2025-04 | 'Published Jul 14, 2026, 09:47 AM' under the headline (publish time; same day as the call) |
| `BAC-IR-TRANSCRIPT-CONFERENCE` | transcript | pdf | free | silent / silent / silent | T-16 | 2026-02-10 | PDF cover page 1 date ('September 14, 2026' under the conference name); also the filename… |
| `BAC-IR-TRANSCRIPT-EARNINGS` | transcript | pdf | free | silent / silent / silent | T-16 | 2026-04-15 | PDF cover page 1: 'July 14, 2026' under 'Second Quarter 2026 Earnings Announcement' (repe… |
| `BAC-IR-TRANSCRIPT-INVESTORDAY` | transcript | audio-only | free | unclear / unclear / unclear | T-16 | 2025-11-05 | none in the player; event date 'Nov 5, 2025' on the past-events list (the GWIM deck p.1 a… |
| `BAC-MARKETBEAT-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-29 | 2024-10-15 | Date 'July 14, 2026' under the 'Provided by Quartr' line. The report table has a 'Confere… |
| `BAC-ROIC-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-30 | 2007-07-19 | Line 'Q2 FY2026 · Earnings Call Transcript' plus the call date above the transcript. Also… |
| `BAC-SEEKINGALPHA-TRANSCRIPT` | transcript | html | unknown | forbidden / unclear / unclear | T-25 | 2007-07 | TODO-verify on the article page (403). RSS <pubDate>; sitemap <lastmod> 2026-07-15T04:41:… |
| `BAC-YAHOO-TRANSCRIPT` | transcript | html | paywall | forbidden / forbidden / forbidden | T-27 | TODO-verify | Quartr page: TODO-verify (404 to scripts). Fool copy on Yahoo: byline <time datetime="202… |

### Merrill (MER)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `MER-BOFANEWS-PRESS` | press | html | free | silent / silent / silent | T-17 | 2022-10 | line 'September 15, 2026 at 9:00 AM Eastern' above the headline, below the 'Global Wealth… |
| `MER-PRN-PRESS` | press | html | free | forbidden / forbidden / forbidden | T-18 | 2022-10-04 | timestamp 'Sep 15, 2026, 09:00 ET' under the headline in the 'News provided by Bank of Am… |

### Raymond James (RJF)

| source_id | doc_type | format | access | scraping / storage / excerpts | terms | earliest | date field |
|---|---|---|---|---|---|---|---|
| `RJF-IR-DECK-EARNINGS` | deck | pdf | free | silent / unclear / unclear | T-19 | 2020-01-22 | Cover slide, under the title (e.g. 'Fiscal 2Q26 Results / April 22, 2026'); also rjf{yyyy… |
| `RJF-IR-DECK-EVENTS` | deck | pdf | free | silent / unclear / unclear | T-19 | 2019-03 | Cover slide, above the title (e.g. 'JUNE 5, 2025 / 2025 Analyst & Investor Day'); the fil… |
| `RJF-IR-MONTHLY` | monthly | pdf | free | silent / unclear / unclear | T-19 | 2020-11-24 | Date line at top-left of page 1, above 'FOR IMMEDIATE RELEASE' (e.g. 'June 24, 2026'); al… |
| `RJF-ADVISOROPP-PRESS-RECRUITING` | press | html | free | silent / unclear / unclear | T-19 | 2022-12-06 | Date line directly above the headline, below the Media Contact block (e.g. 'May 26, 2026'… |
| `RJF-GNW-PRESS` | press | html | free | unclear / silent / silent | T-20 | 2021-05-20 | Line under the headline 'July 22, 2026 16:17 ET \| Source: Raymond James Financial'; date… |
| `RJF-IR-PRESS-EARNINGS` | press | pdf | free | silent / unclear / unclear | T-19 | 2019-01-23 | Date line at top-left of page 1, above 'FOR IMMEDIATE RELEASE' (e.g. 'April 22, 2026'); a… |
| `RJF-NEWSROOM-PRESS` | press | html | free | silent / unclear / unclear | T-19 | 2010-01 | Date line directly above the headline, below the Media/Investor Contact block (e.g. 'Marc… |
| `RJF-IR-SUPPLEMENT` | supplement | pdf | free | silent / unclear / unclear | T-19 | 2020-01-22 | Cover shows the fiscal quarter only ('Quarterly Financial Supplement / Fiscal first quart… |
| `RJF-ALPHASTREET-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-28 | 2020-04-30 | Body line '... Earnings Call dated Mon. D, YYYY' (the oldest page reads 'Raymond James Fi… |
| `RJF-FOOL-TRANSCRIPT` | transcript | html | free | forbidden / unclear / unclear | T-24 | 2018-10 | Body 'DATE' block (call date and time ET); byline 'By Motley Fool Transcribing – {date} a… |
| `RJF-INVESTINGCOM-TRANSCRIPT` | transcript | html | free | forbidden / forbidden / forbidden | T-26 | 2025-04 | 'Published Jul 22, 2026, 06:18 PM' under the headline (publish time; same day as the call) |
| `RJF-IR-TRANSCRIPT-INVESTORDAY` | transcript | audio-only | free | unclear / unclear / unclear | T-19 | 2025-06-05 | None on the Kaltura player; the event date is in the IR presentations list (e.g. '6/5/202… |
| `RJF-IR-TRANSCRIPT-WEBCAST` | transcript | audio-only | free-registration | forbidden / forbidden / unclear | T-19 | TODO-verify | None in the Q4 page HTML (JavaScript app); the call date is in the IR presentations list… |
| `RJF-MARKETBEAT-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-29 | 2024-10-23 | Date line under 'Provided by Quartr' below the 'Raymond James Q3 2026 Earnings Call Trans… |
| `RJF-ROIC-TRANSCRIPT` | transcript | html | free | unclear / unclear / unclear | T-30 | 2008-01-25 | Line 'Q3 FY2026 · Earnings Call Transcript' plus the call date above the transcript. Also… |
| `RJF-SEEKINGALPHA-TRANSCRIPT` | transcript | html | unknown | forbidden / unclear / unclear | T-25 | 2008-01 | TODO-verify on the article page (403). RSS <pubDate>; sitemap <lastmod> 2026-07-23T14:30:… |
| `RJF-YAHOO-TRANSCRIPT` | transcript | html | paywall | forbidden / forbidden / forbidden | T-27 | TODO-verify | TODO-verify (404 to scripts on 2026-10-04); URL and title give only the fiscal period ('Q… |

## Trade press and access routes (tier 4)

| source_id | publisher | access | cost | scraping / storage / excerpts | terms |
|---|---|---|---|---|---|
| `T4-ADVISORHUB` | AdvisorHub | free | free | silent / unclear / unclear | T-31 |
| `T4-ADVIZORPRO` | AdvizorPro | free | free (public blog) | unclear / unclear / unclear | T-43 |
| `T4-AMERICANBANKER` | Arizent (American Banker) | metered | not published | silent / forbidden / forbidden | T-34 |
| `T4-BARRONS` | Dow Jones (Barron's) | paywall | Individual 'Unlimited Barron’s Standard Digital Access': li… | forbidden / forbidden / forbidden | T-38 |
| `T4-BARRONSADVISOR` | Dow Jones (Barron's) | paywall | Same Barron's subscription as T4-BARRONS (https://www.barro… | forbidden / forbidden / forbidden | T-38 |
| `T4-BINGNEWS` | Microsoft Bing | free | free | unclear / unclear / unclear | T-59 |
| `T4-BLOOMBERG` | Bloomberg L.P. | paywall | not published | forbidden / forbidden / forbidden | T-54 |
| `T4-BUSINESSINSIDER` | Business Insider (Axel Springer) | paywall | not published | forbidden / forbidden / forbidden | T-57 |
| `T4-CITYWIRERIA` | Citywire | unknown | not published | forbidden / forbidden / forbidden | T-39 |
| `T4-CNBC` | CNBC (Versant Media, LLC) | free | free | forbidden / forbidden / forbidden | T-56 |
| `T4-DAKOTA` | Dakota | free | free (public blog) | forbidden / unclear / unclear | T-46 |
| `T4-DIAMOND` | Diamond Consultants | free | free | silent / silent / silent | T-44 |
| `T4-FACTIVA` | Dow Jones (Factiva) | library | not published | forbidden / forbidden / forbidden | T-60 |
| `T4-FAIQ` | FT Specialist (Financial Times) | free-registration | not published (subscription price quoted by F.T. Specialist… | forbidden / forbidden / forbidden | T-42 |
| `T4-FAMAG` | Financial Advisor Magazine | free | free | forbidden / forbidden / forbidden | T-41 |
| `T4-FAMILYWEALTHREPORT` | ClearView Financial Media | free-registration | not published (prices from ClearView sales per T&C 6.2) | silent / unclear / forbidden | T-48 |
| `T4-FINANCIALPLANNING` | Financial Planning (Arizent) | metered | not published | silent / forbidden / forbidden | T-33 |
| `T4-FINTRX` | FINTRX | free | free (public blog) | silent / silent / silent | T-47 |
| `T4-FT` | Financial Times | paywall | not published | forbidden / forbidden / unclear | T-55 |
| `T4-GOOGLENEWS` | Google News | free | free | forbidden / unclear / unclear | T-58 |
| `T4-INVESTMENTNEWS` | InvestmentNews | metered | $19.99 per month (published on site footer/promo, https://w… | silent / forbidden / forbidden | T-32 |
| `T4-NEWSBANK` | NewsBank | library | not published | forbidden / forbidden / unclear | T-62 |
| `T4-NEXISUNI` | LexisNexis (Nexis Uni) | library | not published | forbidden / forbidden / unclear | T-61 |
| `T4-PLANADVISER` | PLANADVISER | free | free | forbidden / forbidden / unclear | T-40 |
| `T4-PROQUEST` | ProQuest (Clarivate) | library | not published | forbidden / forbidden / unclear | T-63 |
| `T4-REUTERS` | Thomson Reuters | unknown | not published | forbidden / forbidden / forbidden | T-53 |
| `T4-RIABIZ` | RIABiz | free | free | unclear / silent / silent | T-36 |
| `T4-STLBJ` | American City Business Journals | paywall | $210 for 52 weeks (Digital Only Premium), per Wayback 2025-… | forbidden / forbidden / unclear | T-49 |
| `T4-STLTODAY` | St. Louis Post-Dispatch (Lee Enterprises) | metered | not published | forbidden / forbidden / forbidden | T-50 |
| `T4-TAMPABAYTIMES` | Tampa Bay Times | metered | not published | silent / forbidden / unclear | T-51 |
| `T4-THINKADVISOR` | ThinkAdvisor | free-registration | not published (subscribe page blocked; TODO-verify) | silent / unclear / unclear | T-35 |
| `T4-WEALTHMANAGEMENT` | WealthManagement.com | free | free | silent / forbidden / unclear | T-37 |
| `T4-WSJ` | Dow Jones | paywall | not published | forbidden / forbidden / forbidden | T-52 |
| `T4-WSR` | Wealth Solutions Report | free-registration | free | silent / silent / silent | T-45 |

## Merrill vs Bank of America

Merrill has no newsroom of its own (the press pages on ml.com and merrill.com return 404). Merrill releases are
published on the Bank of America newsroom, inside the "Global Wealth and Investment Management" category, and on
PR Newswire under "Bank of America Corporation". The same category also holds Bank of America Private Bank items,
BofA research and market-president appointments. So the entity is decided **per document** when it is ingested,
in line with the CLAUDE.md invariant (Merrill = `entity=MER` or `entity=BAC` with segment GWIM/Merrill) and the
spec rule that Merrill press releases are stored as MER, not BAC (Q4, Q27 are traps):

1. The release is about Merrill (Merrill Wealth Management, Merrill advisors, Merrill Lynch): `entity_id=MER`.
2. The release is about GWIM as a whole or about Bank of America Private Bank: `entity_id=BAC`, segment GWIM.
3. A joint "Merrill and Bank of America Private Bank" release covers more than Merrill: `entity_id=BAC`, segment
   GWIM, so the "GWIM is not Merrill" caveat is inserted by code. TODO-verify with C1, who owns the tagging rules.
4. Merrill Edge (self-directed investing) is reported in Consumer Banking, not GWIM (`config/entities.yaml`, C1 to
   verify): not MER and not GWIM, so out of scope.
5. Other Bank of America corporate items listed in the GWIM category (e.g. market-president appointments): not
   ingested.
6. BAC earnings material (release, slides, supplement, transcripts): `entity_id=BAC`; only the GWIM pages and
   remarks carry segment GWIM (segment tagging at chunk time, C1).

Rows: `MER-BOFANEWS-PRESS` and `MER-PRN-PRESS` (rule 1), `BAC-BOFANEWS-PRESS-GWIM` and `BAC-PRN-PRESS-GWIM`
(rules 2-3) read the same listings and split them with this rule.

## Terms questions for ADR-000

General questions first; then one section per site with the quoted clauses. Quotes are copied from the page on the date shown; terms change, so re-read before relying on one.

### General

#### T-01 How the prototype's use is classified

Almost every site limits copying, downloading or storing to "personal", "personal, non-commercial" or "internal" use, or bars "commercial" use: for example T-10 (morganstanley.com), T-12 (aboutschwab.com), T-19 (raymondjames.com), T-24 (fool.com), T-31 (advisorhub.com). What we would do: seven WashU students build a prototype for Edward Jones's Chief Strategy Office (a WashU project lead stands in for the CSO); full copies sit in a private Postgres database and a private Box folder; a handful of people see answers that quote short passages with a link; nothing is republished, sold or advertised.

1. Does that count as personal, non-commercial or internal use under these terms, or as commercial use because the work is done for Edward Jones (a broker-dealer and competitor of the firms concerned)?
2. If it does not count, do we ask the sites for written permission (T-02), or keep those sources as metadata + link only (T-06)?

#### T-02 Who asks for written permission, and whom

Many terms allow storage or automated access with the publisher's prior written consent and name a contact (e.g. T-18 (prnewswire.com), T-26 (investing.com), T-28 (alphastreet.com), T-32 (investmentnews.com)). Edward Jones's own site forbids robots and compiling a database from it without written permission (T-21 (edwardjones.com)), although Edward Jones is the project's client.

1. Who sends permission requests (tech lead, project lead, the Edward Jones sponsor), and for which sources is it worth asking this term?
2. Can the Edward Jones sponsor give written permission for edwardjones.com (EDJ press releases, Q17) before we fetch it by script?

#### T-03 SEC EDGAR copies instead of IR sites

Several IR documents are also furnished to the SEC as 8-K exhibits (Ex. 99): confirmed for Raymond James (earnings releases, monthly operating data, the 2026 Analyst & Investor Day deck); Morgan Stanley's releases and the 4Q25 Strategic Update say the release and supplement are included in a Form 8-K; TODO-verify for Schwab and Bank of America. EDGAR is tier 2 (C1) and its copies are not fetched from the IR sites, while the IR sites limit or block scripts (Schwab's terms bar automated downloads without written approval, T-12 (aboutschwab.com); raymondjames.com sits behind Akamai, T-19 (raymondjames.com)).

1. Should tier 3 documents that also exist on EDGAR be fetched from EDGAR, keeping their doc_type (press, deck, supplement, monthly), with the IR site used only for what EDGAR lacks?
2. Do the firms' own copyright terms still reach the EDGAR copies, or does fetching from EDGAR settle the terms question for these documents?
3. Who owns that fetch, C1 (EDGAR) or C2 (IR material)?

#### T-04 Where earnings-call transcripts can come from

No core firm offers a free text transcript archive on its own site. Morgan Stanley posts webcast replays only, and each call carries the notice that recording, rebroadcast or other use without Morgan Stanley's written consent is prohibited (T-11 (webcasts.com)). Schwab has posted none since the Spring 2019 Business Update, which carries Bloomberg's notice (T-15 (bloomberg.com)); its replays are on ON24 behind registration (T-14 (event.on24.com)). Raymond James keeps a 30-day replay only, on a platform whose terms forbid copying or storing (T-22 (events.q4inc.com)). Bank of America posts its own transcripts from 1Q26 and 2026 conference transcripts, with terms that are silent (T-16 (investor.bankofamerica.com)). Every free third-party transcript site found (Motley Fool, Seeking Alpha, Investing.com, Yahoo Finance, AlphaStreet, MarketBeat/Quartr, Roic.ai) owns or licenses the text and limits it to personal use or forbids storage. Edward Jones holds no earnings calls.

1. Which route for transcripts (needed by Q1, Q2, Q3, Q5, Q6, Q13 and others): (a) a third-party site with written permission, (b) our own transcription of webcast audio with the firm's permission, or (c) no transcripts this term, relying on releases, decks, supplements, 10-K/10-Q and BAC's own transcripts, and answering gaps honestly?
2. #4 picks the first three transcripts to ingest in W3. Until this is answered, are BAC's own 1Q26/2Q26 transcripts the only candidates?

#### T-05 Tier label for third-party transcripts

Tier 3 is IR material published by the firm. Third-party transcripts carry management's words but the text is produced and owned by the vendor (some say it is AI-generated with editor review). They are labelled tier 3 in the CSV for now.

1. Keep them as tier 3, give them their own label, or treat them like licensed (tier 1) content under ADR-000?

#### T-06 Trade press as metadata + link only

ADR-000 already expects that trade press may be stored as "metadata + excerpt + link only". The research found that most trade outlets forbid storing full text, and many also forbid excerpts, without permission (see the trade-press table). Headline, date and link are available from the outlets' RSS feeds and from Google News / Bing News RSS (T-58 (news.google.com), T-59 (bing.com)), whose own terms also limit reuse. Ground rule 1 still applies: a claim must cite a stored document, so a headline + link can point a reader to coverage but cannot support a claim on its own.

1. Is storing headline + date + link (no article text) acceptable for each trade outlet and for the news-search routes?
2. If trade press can only be a pointer, how do Q2, Q4, Q5 and Q7 (which name trade press as evidence) get scored?
3. May the WashU library databases (Factiva, Nexis Uni, ProQuest, NewsBank) be used to read articles by hand, given that their licences forbid systematic downloading and storing (T-60 (factiva.com), T-61 (lexisnexis.com), T-63 (proquest.com), T-62 (newsbank.com))?

#### T-07 Sending stored passages to an LLM API

Each answer sends the retrieved passages to one LLM call (Anthropic or OpenAI, ADR-002/003). Some terms restrict AI uses, for example PR Newswire bars using content "for the development of any software program, including ... training a machine learning or artificial intelligence (AI) system" (T-18 (prnewswire.com)); most terms are silent on AI.

1. Does sending stored passages to an LLM API at answer time count as a use these terms restrict, as opposed to training a model?

#### T-08 Bot walls and robots.txt

Several sites refuse scripts outright (Akamai on raymondjames.com and aboutschwab.com; Cloudflare, DataDome or Incapsula on ThinkAdvisor, Citywire, Reuters, Barron's, Seeking Alpha, Business Journals), and some robots.txt files disallow the paths we would fetch (e.g. morganstanley.com /content/, webcasts.com everything). The URL checker uses an honest user agent and does not imitate a browser.

1. Do we treat a bot wall or a robots.txt disallow as "no automated access" even where the terms are silent?
2. May a team member download such documents by hand instead, and does that change the storage question?

#### T-09 Undated firm web pages

Recruiting and affiliation pages (Merrill Advisor Development Program, "becoming a Merrill advisor", Raymond James affiliation options) describe exactly what Q2, Q4 and Q6 ask about, but they carry no date and fit no doc_type, so they are in "Considered and rejected".

1. Should such pages get a doc_type with an "as of" date? specs/transcripts-ir.md forbids using the download date as published_at, so this would need a spec change by the tech lead.

### Per site

#### T-10 morganstanley.com (Morgan Stanley (Investor Relations and Media Relations, www.morganstanley.com))

Rows: `MS-IR-DECK`, `MS-IR-PRESS-EARNINGS`, `MS-NEWSROOM-PRESS`, `MS-IR-SUPPLEMENT`, `MS-IR-TRANSCRIPT-WEBCAST`

- Terms: <https://www.morganstanley.com/terms>, read 2026-10-04 (live page)
- Scraping: **silent**. "You may not use this web site in any manner that could damage, disable, overburden, or impair any Morgan Stanley site or service or interfere with any other party's use and enjoyment of any Morgan Stanley site or service."
- Full-text storage: **unclear**. "Unless otherwise specified, this web site is for your personal and non-commercial use only and you may print, copy and download any information or portion of this web site for your personal use only."
- Excerpts: **unclear**. "You may not modify, copy, distribute, transmit, display, perform, reproduce, publish, license, frame, create derivative works from, transfer, or otherwise use in any other way for commercial or public purposes in whole or in part any information"
- Other clauses: The Terms have no robots/spider/scraper/crawler, text-and-data-mining or AI clause. The only automated-access wording is the 'overburden' clause above, plus 'password mining', which is about hacking. The excerpts sentence continues: '...software, products or services obtained from this web site, except for the purposes expressly provided herein, without Morgan Stanley's prior written approval.' So consent can be requested. Ownership: 'All right, title and interest in this web site and any content contained herein is the exclusive property of Morgan Stanley, except as otherwise stated.' Notices: 'If you copy or download any information or software from this web site, you agree that you will not remove or obscure any copyright or other notices or legends contained in any such information.' Scope: 'Certain sections of or pages on this web site may contain separate terms and conditions, which are in addition to these Terms of Use.' I found no separate terms for IR or the newsroom. Governing law: 'These Terms of Use shall be governed by and construed in accordance with the laws of the state of New York, without regard to conflicts of laws provisions.' Claims must be brought within 1 year. Per-call notice on IR call pages (https://www.morganstanley.com/about-us-ir/morgan-stanley-third-quarter-2026-investor-conference-call): 'This presentation by Morgan Stanley is copyrighted and proprietary, and all rights are reserved. Any recording, rebroadcast or other use of this presentation, in whole or in part, without the prior written consent of Morgan Stanley is strictly prohibited.' The 'Disclaimers' page (https://www.morganstanley.com/disclaimers/terms) is NOT the site terms. It covers e-mail and other electronic messages (relevant if we subscribe to IR e-mail alerts): 'Electronic messages may not be reproduced, redistributed or disseminated, without the prior written consent of Morgan Stanley.' Contacts: DMCA agent internetadmin@morganstanley.com (listed in the Terms); IR investorrelations@morganstanley.com (mailto on /about-us-ir/request_information). The presentations page warns: 'You should not rely on the continued accuracy of any presentation at this site beyond the date it was made.'
- Text owner: Morgan Stanley. The Terms say content is 'the exclusive property of Morgan Stanley, except as otherwise stated', and every page footer reads '© 2026 Morgan Stanley. All rights reserved.' The sample PDFs I checked (4Q25 Strategic Update, 2Q26 earnings release, 2Q26 financial supplement) have no separate copyright notice and no third-party vendor notice. The webcasts are MS's own: 'This presentation by Morgan Stanley is copyrighted and proprietary'.
- Access / cost: free; free (<https://www.morganstanley.com/about-us-ir>)
- robots.txt: https://www.morganstanley.com/robots.txt (2026-10-04), User-agent *. Allowed (no matching Disallow): /about-us-ir/*, /about-us-newsroom, /press-releases/{slug}, /press-releases.msfeed.xml. Allowed explicitly: /content/dam/msdotcom/, where all IR PDFs and XLSX files sit; this 'Allow' outranks 'Disallow: /content/'. Disallowed: the rest of /content/, including /content/msdotcom/en/press-releases/{slug}.html, which is the form of the links inside the RSS feed. Also disallowed: /pub/ (except /pub/content/dam/msdotcom/), /auth/, /etc/, /capital-markets, /iris. Named AI agents (GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, Claude-Web, Google-Extended, PerplexityBot, etc.) each get 'Allow: /'. Sitemap: https://www.morganstanley.com/sitemapindex.xml. robots.txt is a technical signal only, not permission.
- Questions:
  1. morganstanley.com Terms of Use: the site is 'for your personal and non-commercial use only', and copying or downloading is allowed 'for your personal use only'. Does a WashU student prototype built for Edward Jones's Chief Strategy Office, which keeps full copies of MS IR PDFs and press releases in a private Postgres database and Box folder, count as personal/non-commercial use? Or do we need Morgan Stanley's 'prior written approval', e.g. from investorrelations@morganstanley.com?
  2. morganstanley.com Terms of Use forbid copying, displaying or reproducing content 'for commercial or public purposes in whole or in part' without prior written approval. Is showing short quoted passages, with attribution and a link, to a handful of project users (on behalf of Edward Jones's strategy office) a 'commercial' purpose under that clause?
  3. The MS 2Q26 financial supplement is, per the 4Q25 Strategic Update footnote, 'included in the Current Report on Form 8-K', and the earnings releases are likely 8-K exhibits too. Should we take these documents from SEC EDGAR (tier 2) instead of morganstanley.com, so the morganstanley.com personal-use clause does not apply?
  4. morganstanley.com fetch script: robots.txt disallows /content/ (except /content/dam/msdotcom/), and the newsroom RSS feed links to /content/msdotcom/en/press-releases/{slug}.html. Do we treat robots.txt as binding and rewrite those links to the allowed /press-releases/{slug}? And what fetch rate keeps us clear of the Terms' 'overburden' clause?

#### T-11 webcasts.com (GlobalMeet (Webcast Plus LLC), which hosts Morgan Stanley earnings and conference webcasts (morganstanley.webcasts.com, event.webcasts.com, cc.webcasts.com))

Rows: `MS-IR-TRANSCRIPT-WEBCAST`

- Terms: <https://www.globalmeet.com/terms-of-service/2026-02-17/>, read 2026-10-04 (live page)
- Scraping: **silent**. "These GlobalMeet Terms of Service (“Terms of Service”) govern the sale of all Services (as defined below) by GlobalMeet to a given customer (“Customer” or “you”)"
- Full-text storage: **forbidden**. "This presentation by Morgan Stanley is copyrighted and proprietary, and all rights are reserved. Any recording, rebroadcast or other use of this presentation, in whole or in part, without the prior written consent of Morgan Stanley is strictly prohibited." (<https://www.morganstanley.com/about-us-ir/morgan-stanley-third-quarter-2026-investor-conference-call>)
- Excerpts: **forbidden**. "This presentation by Morgan Stanley is copyrighted and proprietary, and all rights are reserved. Any recording, rebroadcast or other use of this presentation, in whole or in part, without the prior written consent of Morgan Stanley is strictly prohibited." (<https://www.morganstanley.com/about-us-ir/morgan-stanley-third-quarter-2026-investor-conference-call>)
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The GlobalMeet Terms of Service are a business contract between GlobalMeet and its paying Customer (here Morgan Stanley). They have no attendee, end-user, scraping, robots or AI clause, so the host's terms are silent on what we would do. The registration page (starthere.jsp) links to no terms or privacy page; it shows only a 'Webcast by GlobalMeet' logo linking to globalmeet.com. Content ownership: 'Customer warrants and represents that it is the owner or licensee of any content, information, or other intellectual property that Customer or any end user publishes, uploads, records, or otherwise transmits through the Services (“Customer Content”).' Governing law: 'The Agreement shall be governed by and construed and enforced in accordance with the laws of the State of Arizona, USA, excluding conflicts or choice of law provisions.' The storage and excerpts verdicts come from Morgan Stanley's own per-call notice, which says 'without the prior written consent', so consent can be requested from MS IR (investorrelations@morganstanley.com). An expired 2020 webcast page carries the footer '© 2020 Morgan Stanley. All rights reserved.' Registration asks for First Name, Last Name, Company and Email.
- Text owner: Morgan Stanley: 'This presentation by Morgan Stanley is copyrighted and proprietary, and all rights are reserved.' GlobalMeet only hosts the stream, as Customer Content owned by its customer, MS.
- Access / cost: free-registration; free (registration form, no price published) (<https://morganstanley.webcasts.com/starthere.jsp?ei=1746603&tp_key=86ab90b7fd>)
- robots.txt: https://morganstanley.webcasts.com/robots.txt and https://event.webcasts.com/robots.txt (2026-10-04): 'User-agent: *' then 'Disallow: /'. Only /viewer/share.jsp, /viewer/social_facebook.jsp, /viewer/social_twitter.jsp and /viewer/socialbutton.jsp are allowed, so starthere.jsp and the replay player are disallowed. https://cc.webcasts.com/robots.txt returned HTTP 500. www.webcasts.com/robots.txt redirects (302) to globalmeet.com.
- Questions:
  1. Morgan Stanley webcast notice: 'Any recording, rebroadcast or other use of this presentation, in whole or in part, without the prior written consent of Morgan Stanley is strictly prohibited.' Do we drop the MS audio webcasts entirely (no recording, no machine transcription, no quotes), or ask MS IR in writing for consent?
  2. Does the MS per-call notice ('other use of this presentation, in whole or in part') also limit our use of third-party transcripts of the same MS calls (Motley Fool, Investing.com, AlphaStreet, MarketBeat/Quartr, Yahoo)? Is quoting a passage from such a transcript an 'other use' of MS's presentation?
  3. webcasts.com (GlobalMeet): robots.txt disallows every path, and replays sit behind a registration form (name, company, email). May a team member register by hand to listen and take notes for the corpus, and if so, which name and company should they enter?

#### T-12 aboutschwab.com (The Charles Schwab Corporation, Investor Relations (www.aboutschwab.com pages; document files on content.schwab.com))

Rows: `SCHW-IR-DECK-EARNINGS`, `SCHW-IR-DECK-EVENTS`, `SCHW-IR-MONTHLY`, `SCHW-IR-PRESS-EARNINGS`, `SCHW-IR-SUPPLEMENT`, `SCHW-IR-TRANSCRIPT`, `SCHW-IR-TRANSCRIPT-WEBCAST`

- Terms: <https://www.schwab.com/legal/terms>, read 2026-10-04 (live page (schwab.com/legal/terms, 'Schwab Online Services Agreement', version code 0225-M8PR). aboutschwab.com has no terms link of its own (only Privacy and Regulatory Disclosures); its footer was read through Wayback capture 2026-09-27 because the live site returns an Akamai 403)
- Scraping: **forbidden**. "approved by Schwab in writing, you agree not to use any software, program, application or any other device to access or log on to any Schwab Service, including Schwab's computer systems, Web site or proprietary software or to automate the process of obtaining, downloading"
- Full-text storage: **unclear**. "no materials from the Schwab Services or any site owned, operated, licensed or controlled by Schwab may be copied, reproduced, republished, uploaded, posted, transmitted, or distributed in any way. You may download material displayed on the Schwab Services for non-commercial, personal use."
- Excerpts: **unclear**. "You may not use, distribute, modify, transmit, or post the content of the Schwab Services for public or commercial purposes, including any text, images, audio, or video without Schwab's written permission."
- Verification: scraping 'forbidden': 2/2 checkers confirmed.
- Other clauses: Scraping is forbidden unless Schwab gives approval in writing, so consent can be requested. The terms are not linked from aboutschwab.com, but they reach 'any site owned, operated, licensed or controlled by Schwab'. Scope: 'Schwab Services may be offered on the Schwab.com domain as well as on other Internet domains operated by our agents or alliance partners.' Licence: 'Schwab grants you a single, non-exclusive, non-transferable and limited personal license to access and use the Schwab Services.' Commercial use: 'You will not use any Schwab Service for any commercial purpose not expressly approved by Schwab in writing.' Market information (Edward Jones is a broker-dealer): 'If you are a securities broker, dealer, banker, or investment advisor, you agree not to use Market Information provided by Schwab for any purpose related to your business.' There is no AI, machine-learning or text-and-data-mining clause. Governing law: 'will be governed by the law of the state of California' (courts of the City and County of San Francisco). aboutschwab.com footer (Wayback 2026-09-27): '© 2026 Charles Schwab & Co., Inc, All rights reserved. Member SIPC. Unauthorized access is prohibited. Usage will be monitored.' No permissions contact is named. The copyright agent listed at https://www.schwab.com/legal/copyright is 'Legal Department', trademarkandcopyright@schwab.com, 312 517-3100. The IR contact on the Aug 2026 monthly release is Kartik Sharma, 817-662-7648.
- Text owner: Charles Schwab & Co., Inc. / The Charles Schwab Corporation (footer '© 2026 Charles Schwab & Co., Inc, All rights reserved.'). The 2026 Investor Day deck also carries third-party notices, e.g. '©2000-2026 Rocket Mortgage, LLC. All rights reserved.' Exception: the 2019 transcript belongs to Bloomberg (see bloomberg.com entry).
- Access / cost: free; free (<https://www.aboutschwab.com/financial-reports>)
- robots.txt: www.aboutschwab.com/robots.txt returned an Akamai 403 to curl on 2026-10-04. Wayback capture 2026-10-03: User-agent * disallows /core/, /profiles/, /admin/, /search/, /node, /card/, /user/*, /resource-center/insights/ and /active-trader/insights/. /financial-reports and /schwabevents are not disallowed, but the live pages return 403 to scripts. content.schwab.com/robots.txt (live, 2026-10-04): User-agent * disallows about 60 marketing paths (e.g. /web/ns/, /web/retail/public/bank, /web/retail/public/apple). /web/retail/public/about-schwab/ and /about-schwab/excels/ are not disallowed. PDF and XLSX files there returned 200 to curl.
- Questions:
  1. Schwab's terms (schwab.com/legal/terms) are not linked from aboutschwab.com, but they cover 'any site owned, operated, licensed or controlled by Schwab'. Do we treat them as governing the aboutschwab.com pages and the content.schwab.com IR files?
  2. Schwab's terms forbid automated downloading except with software 'approved by Schwab in writing'. Do we ask Schwab IR in writing for approval to script downloads from content.schwab.com, or use the SEC EDGAR copies (8-K Ex. 99.1) for earnings releases and download the rest by hand?
  3. Schwab's terms allow downloads only 'for non-commercial, personal use'. Does storing full copies of Schwab IR PDFs and XLSX files in our private Postgres and Box for the Edward Jones CSO prototype qualify?
  4. Schwab's terms forbid use 'for public or commercial purposes' without written permission. Does showing short quoted passages, with links, to a handful of WashU and Edward Jones users count as public or commercial use?
  5. Schwab's terms bar 'any commercial purpose not expressly approved by Schwab in writing' and bar brokers, dealers and advisers from using Schwab 'Market Information' for their business. Does either clause apply because the end user is Edward Jones, a broker-dealer competitor?
  6. www.aboutschwab.com returns an Akamai 403 to scripts even though its robots.txt does not disallow /financial-reports. Do we treat the 403 as a refusal (find links by hand or from Wayback captures only), or may a script send browser-like headers?
  7. Older monthly PDFs on content.schwab.com can be reached by guessing filenames (e.g. schw_jan2020_press_release.pdf), but they are not linked. Is filename-guessing acceptable, or should monthly history come only from the pressroom?

#### T-13 pressroom.aboutschwab.com (Charles Schwab pressroom (hosted on the Q4 Inc. platform))

Rows: `SCHW-PRESSROOM-MONTHLY`, `SCHW-PRESSROOM-PRESS`

- Terms: <https://www.schwab.com/legal/terms>, read 2026-10-04 (live page (schwab.com/legal/terms). The pressroom pages, read live, link no terms of use (footer links: Privacy, Other Regulatory Disclosures, RSS Feeds). The RSS Feeds page has no feed terms.)
- Scraping: **unclear**. "With the exception of applications commonly known as Web Browser software, or other applications formally promoted, endorsed or approved by Schwab in writing, you agree not to use any software, program, application or any other device to access or log on to any Schwab Service"
- Full-text storage: **unclear**. "no materials from the Schwab Services or any site owned, operated, licensed or controlled by Schwab may be copied, reproduced, republished, uploaded, posted, transmitted, or distributed in any way. You may download material displayed on the Schwab Services for non-commercial, personal use."
- Excerpts: **unclear**. "You may not use, distribute, modify, transmit, or post the content of the Schwab Services for public or commercial purposes, including any text, images, audio, or video without Schwab's written permission."
- Other clauses: Scraping is marked unclear because the terms make an exception for 'applications formally promoted' by Schwab, and the pressroom promotes RSS feeds ('sent directly to the user's news reader'). Scope covers 'other Internet domains operated by our agents or alliance partners' (Q4 runs the pressroom). The same commercial-purpose, market-information, California-law and copyright-agent clauses apply as for aboutschwab.com. There is no AI or text-and-data-mining clause. Footer: '© 2025 Charles Schwab & Co., Inc, All rights reserved.' The RSS channel element says 'Copyright Q4 Inc. All rights reserved.' Releases are distributed via Business Wire (dateline 'WESTLAKE, Texas--(BUSINESS WIRE)--').
- Text owner: Charles Schwab & Co., Inc. / The Charles Schwab Corporation (footer '© 2025 Charles Schwab & Co., Inc, All rights reserved.'). Q4 Inc. claims copyright in the RSS feed wrapper.
- Access / cost: free; free (<https://pressroom.aboutschwab.com/press-releases/default.aspx>)
- robots.txt: pressroom.aboutschwab.com/robots.txt (live, 2026-10-04): 'User-agent: * Crawl-delay: 10 Allow: /'. This allows /press-releases/, /rss/pressrelease.aspx and /feed/PressRelease.svc. Pages returned 200 to curl.
- Questions:
  1. The Schwab pressroom (pressroom.aboutschwab.com, run on Q4) links no terms. Does Schwab's Online Services Agreement apply there, and does polling the pressroom RSS feed that Schwab promotes count as an application 'formally promoted, endorsed or approved by Schwab' under its exception for access tools?
  2. May the pressroom script list releases through the unadvertised Q4 JSON endpoint /feed/PressRelease.svc/GetPressReleaseList (robots says Allow: / with Crawl-delay: 10), or only through the 10-item RSS feed and the HTML pages?
  3. Schwab press releases are issued for publication via Business Wire, but Schwab's terms allow downloads only for 'non-commercial, personal use'. May we store the full text and quote excerpts of pressroom releases, or should we take the EDGAR 8-K copy where one exists?
  4. The pressroom RSS feed says 'Copyright Q4 Inc. All rights reserved.' Does Q4 claim any rights over the feed contents beyond Schwab's?

#### T-14 event.on24.com (ON24, Inc. (webcast platform hosting Schwab Business Update and Investor Day replays))

Rows: `SCHW-IR-TRANSCRIPT-WEBCAST`, `SCHW-IR-DECK-EVENTS`

- Terms: <https://www.on24.com/terms-and-conditions/>, read 2026-10-04 (Wayback capture 2026-03-10 (https://web.archive.org/web/20260310033215/https://www.on24.com/terms-and-conditions/). www.on24.com returned 403 to curl. The on24.com footer links only these 'ON24 Universal Terms and Conditions' and the privacy policy. The Schwab event registration pages are JS-rendered, so no separate attendee terms were seen.)
- Scraping: **silent**. "Client agrees to use the Platform and Services in compliance with applicable law and shall not and shall ensure Attendees do not: (i) permit any third party to use the Platform or Services except as permitted herein or in an Agreement;" (<https://web.archive.org/web/20260310033215/https://www.on24.com/terms-and-conditions/>)
- Full-text storage: **silent**. "As between ON24 and Client, Client retains all right, title and interest in and to all materials and data it enters into the Platform or otherwise provides to ON24 under an Agreement, including slides, audio files, video files, branding elements, recordings generated from the Services" (<https://web.archive.org/web/20260310033215/https://www.on24.com/terms-and-conditions/>)
- Excerpts: **silent**. "As between ON24 and Client, Client retains all right, title and interest in and to all materials and data it enters into the Platform or otherwise provides to ON24 under an Agreement, including slides, audio files, video files, branding elements, recordings generated from the Services" (<https://web.archive.org/web/20260310033215/https://www.on24.com/terms-and-conditions/>)
- Other clauses: The Universal Terms and Conditions are a contract between ON24 and its Client (Schwab). They have no clause on robots, scraping, automated access or text-and-data mining, and no clause on attendees copying or quoting content. The quoted clauses show Schwab owns the recordings, so Schwab's own terms govern any copy. Other attendee duties run through the Client, e.g. '(iv) remove or modify any title, trademark, copyright and/or restricted rights notice or label from the Platform or Services;'. Governing law: California. '© Copyright 2026 ON24, Inc.' Replays need registration with personal data.
- Text owner: The Charles Schwab Corporation owns the recordings and slides (ON24 terms: 'Client retains all right, title and interest ... recordings generated from the Services'). ON24 owns the platform.
- Access / cost: free-registration; free (registration required: 'Please register to view the webcast replay.') (<https://www.aboutschwab.com/schwabevents>)
- robots.txt: event.on24.com/robots.txt (live, 2026-10-04): User-agent * allows /wcc/, /wcc/r/, /wcc/gateway/ and /view/eventregistration/. It disallows /clients/ (used by the Summer 2019 Schwab link), /events/, /media/, /media_prod/, /webcast/, /webcasts/, /view/ (except listed subpaths) and /event/*.pdf$. User-agent 008 is disallowed from /. www.on24.com/robots.txt returned 403.
- Questions:
  1. ON24 replays of Schwab Business Updates need registration with personal data. May team members register for the prototype, and under whose name and email?
  2. ON24's terms say Schwab owns the recordings. May we make and store our own speech-to-text transcript of Schwab webcast audio, and quote from it, without Schwab's written permission under Schwab's terms?
  3. Do the JS-rendered ON24 registration forms for Schwab events show attendee terms or consent text that we have not read?

#### T-15 bloomberg.com (Bloomberg L.P. (transcript vendor; its notice is inside the Schwab-hosted 2019 transcript PDF on content.schwab.com))

Rows: `SCHW-IR-TRANSCRIPT`

- Terms: <https://content.schwab.com/web/retail/public/about-schwab/schwab_spring_business_update_transcript_04152019.pdf>, read 2026-10-04 (live document (PDF downloaded with curl on 2026-10-04; the notice is on page 17 and in every page footer). WebFetch returned 403. bloomberg.com terms were not fetched.)
- Scraping: **silent**. "Bloomberg retains all rights to this transcript and provides it solely for your personal, non-commercial use."
- Full-text storage: **forbidden**. "All rights reserved. Any reproduction, redistribution or retransmission is expressly prohibited."
- Excerpts: **forbidden**. "All rights reserved. Any reproduction, redistribution or retransmission is expressly prohibited."
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The notice has no clause on automated access. Hosting-site rules are Schwab's terms (aboutschwab.com entry). Full notice text: 'This transcript may not be 100 percent accurate ... This transcript is provided "as is", without express or implied warranties of any kind. Bloomberg retains all rights to this transcript and provides it solely for your personal, non-commercial use.' Every page footer: '© COPYRIGHT 2026, BLOOMBERG LP. All rights reserved. Any reproduction, redistribution or retransmission is expressly prohibited.' and 'Printed on 02-27-2026'. The PDF was regenerated from Bloomberg on 2026-02-27; PDF metadata title is 'Schwab Spring 2019 Business Update transcript'. Consent contact: none in the document; it would have to come from Bloomberg (tier 1, ADR-000).
- Text owner: Bloomberg L.P.: 'Bloomberg retains all rights to this transcript'. Licensed vendor content, even though Schwab hosts it.
- Access / cost: licensed; not published (the PDF itself is a free download on content.schwab.com)
- robots.txt: Not applicable on bloomberg.com. The document sits on content.schwab.com, where /web/retail/public/about-schwab/ is not disallowed (robots.txt, 2026-10-04).
- Questions:
  1. The only Schwab IR transcript (Spring 2019 Business Update) carries Bloomberg's notice: 'solely for your personal, non-commercial use' and 'Any reproduction, redistribution or retransmission is expressly prohibited'. Do we exclude it entirely as tier-1 Bloomberg content under ADR-000, or keep metadata and a link only?
  2. Would an Edward Jones or WashU Bloomberg licence cover storing or quoting this Bloomberg transcript that Schwab hosts on content.schwab.com?

#### T-16 investor.bankofamerica.com (Bank of America Corporation - Investor Relations (PDFs served from d1io3yog0oux5.cloudfront.net; Investor Day video on cdnapisec.kaltura.com))

Rows: `BAC-IR-DECK-CONFERENCE`, `BAC-IR-DECK-EARNINGS`, `BAC-IR-DECK-INVESTORDAY`, `BAC-IR-PRESS-EARNINGS`, `BAC-IR-SUPPLEMENT`, `BAC-IR-TRANSCRIPT-CONFERENCE`, `BAC-IR-TRANSCRIPT-EARNINGS`, `BAC-IR-TRANSCRIPT-INVESTORDAY`

- Terms: <https://investor.bankofamerica.com/terms-of-use>, read 2026-10-04 (live page)
- Scraping: **silent**. "Bank of America Corporation makes no representations or warranties with respect to the information contained on this website and takes no responsibility for supplementing, updating, or correcting any such information."
- Full-text storage: **silent**. "This website and the information contained herein is provided for informational purposes only and does not constitute an offer to sell or the solicitation of an offer to buy any securities."
- Excerpts: **silent**. "© 2026 Bank of America Corporation." (<https://investor.bankofamerica.com/quarterly-earnings>)
- Other clauses: The IR Terms of Use page has no 'last updated' date. It contains only disclaimer sections: the opening sentence quoted above, No Offer or Solicitation, Forward-Looking Statements, Documentation Subject to Change, Documents Contain Dated Materials, Investment Considerations, No Liability, Non-Deposit Products. There is NO clause on robots or automated access, copying, storage, quotation, a licence, personal or non-commercial use, AI or TDM, governing law, or a consent contact. TRANSCRIPT PDFs: both the 2Q26 earnings transcript (16 pp) and the 2026-09-14 Barclays transcript (15 pp) end with 'Disclaimer' (forward-looking statements), followed by a line 'Terms of Use'. That line is only a PDF link annotation to https://investor.bankofamerica.com/terms-of-use. There is no other text under it and no vendor copyright; PDF Author = 'Bank of America'. Footer on every IR page: 'Content contained herein may have been produced by an outside party that is not affiliated with Bank of America or any of its affiliates (Bank of America).' Stock-quote widgets are QuoteMedia data under QuoteMedia's own terms (not used by us). RELATED BUT UNLINKED: a web search found business.bofa.com/en-us/content/terms-and-conditions.html, 'TERMS AND CONDITIONS FOR BANK OF AMERICA CORPORATION WEBSITES'. It says: 'These Terms and Conditions ("Terms and Conditions") are for the Bank of America Corporation ("Bank of America") website and those websites of its affiliates (collectively the "Sites")'. It forbids to 'photocopy, download or otherwise reproduce in any medium any portion of the Sites, except that Client may download into Client's internal computer system, or print a hard copy of, content on the Sites, in whole or in part' (copyright notices must be kept), and it is governed by New York law. That page is written for institutional 'Clients', is not linked from the IR site, and has no robot or scraping clause, so its scope here is an open question.
- Text owner: Bank of America Corporation: PDF Author 'Bank of America' on releases, decks, supplements and transcripts, and IR footer '© 2026 Bank of America Corporation.' The transcripts carry no third-party vendor copyright. The Investor Day replay is BAC content hosted on Kaltura (partner 58097352).
- Access / cost: free; free (<https://investor.bankofamerica.com/quarterly-earnings>)
- robots.txt: investor.bankofamerica.com/robots.txt: 'User-agent: *' with an empty 'Disallow:', so /quarterly-earnings, /events-and-presentations/* and /terms-of-use are all allowed. Explicit 'Allow: /' for GPTBot, ClaudeBot, PerplexityBot and Google-Extended, plus a pointer 'LLMS: https://investor.bankofamerica.com/llms.txt' (2026-10-04). The PDF host d1io3yog0oux5.cloudfront.net has no robots.txt (S3 403 AccessDenied) (2026-10-04). The Kaltura video host cdnapisec.kaltura.com disallows /content/, /p/*/serveFlavor/ (media files) and /api_v3/ for all agents, while the /p/{id}/embedPlaykitJs/ embed path is not disallowed (2026-10-04). robots.txt is a technical signal only, not permission.
- Questions:
  1. investor.bankofamerica.com Terms of Use contain only disclaimers and are silent on automated access, copying, storing and quoting: is that silence, plus an open robots.txt (with explicit 'Allow: /' for ClaudeBot and GPTBot), enough to fetch, store full text of and quote BAC IR PDFs (earnings releases, decks, supplements, transcripts), or do we ask BAC Investor Relations in writing?
  2. BAC IR transcript PDFs end with a 'Terms of Use' line that only links to investor.bankofamerica.com/terms-of-use: do we treat that page as the only terms for the transcript text (no third-party transcript vendor licence)?
  3. business.bofa.com 'Terms and Conditions for Bank of America Corporation Websites' (not linked from the IR site) allow reproduction only by download into a 'Client's internal computer system': do they apply to investor.bankofamerica.com at all, and if so does our private Postgres + Box store count as internal?
  4. BAC 2025 Investor Day replay is video-only on Kaltura, and Kaltura's robots.txt disallows /p/*/serveFlavor/ (media files): may we download the audio and make our own transcript, or is this source limited to manual viewing and hand-written notes?

#### T-17 newsroom.bankofamerica.com (Bank of America Newsroom (Bank of America Corporation))

Rows: `BAC-BOFANEWS-PRESS-GWIM`, `MER-BOFANEWS-PRESS`

- Terms: <not found: newsroom pages have no terms-of-use link (footer links: Privacy, Security, Social community guidelines, Site map, Advertising Practices); checked https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/09/merrill-launches-new-services-to-support-portfolio-transitions-a.html and /content/newsroom/journalist-resources/media-content-library.html>, read 2026-10-04 (not found)
- Scraping: **silent**. "© 2026 Bank of America Corporation. All rights reserved." (<https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/09/merrill-launches-new-services-to-support-portfolio-transitions-a.html>)
- Full-text storage: **silent**. "© 2026 Bank of America Corporation. All rights reserved." (<https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/09/merrill-launches-new-services-to-support-portfolio-transitions-a.html>)
- Excerpts: **silent**. "© 2026 Bank of America Corporation. All rights reserved." (<https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/09/merrill-launches-new-services-to-support-portfolio-transitions-a.html>)
- Other clauses: No terms of use, reprint, permissions or RSS terms anywhere on the newsroom. The only legal text is the copyright line above and the shared BofA footer disclaimers ('These materials are for informational purposes only.'). The Journalist resources and Media content library pages have no usage terms. The IR site footer's 'RSS News Feed' link (https://newsroom.bankofamerica.com/content/newsroom/press-releases.html/rss) returns the HTML listing page, not a feed. Unlinked related page: the business.bofa.com 'TERMS AND CONDITIONS FOR BANK OF AMERICA CORPORATION WEBSITES' (scope: 'the Bank of America Corporation ("Bank of America") website and those websites of its affiliates'). It limits reproduction to download into 'Client's internal computer system' and is governed by New York law, but it is addressed to institutional clients and its scope over the newsroom is unclear (see the investor.bankofamerica.com entry). Consent contact (not a terms clause): newsroom 'Media contacts' page /content/newsroom/journalist-resources/bank-of-america-media-contacts.
- Text owner: Bank of America Corporation ('© 2026 Bank of America Corporation. All rights reserved.'). Merrill items are issued by BofA / Merrill (MLPF&S is a wholly owned BAC subsidiary).
- Access / cost: free; free (<https://newsroom.bankofamerica.com/content/newsroom/press-releases.html?page=1&year=all&category=press-release-categories/global-wealth-and-investment-management&categTitle=Global%20Wealth%20and%20Investment%20Management>)
- robots.txt: newsroom.bankofamerica.com/robots.txt, 'User-agent: *': disallows only /content/newsroom/email-subscription-form.html, /content/newsroom/email-unsubscription-form.html and /content/dam/newsroom/*.* (DAM assets such as attached PDFs and images). It allows the listing /content/newsroom/press-releases.html and articles under /content/newsroom/press-releases/{yyyy}/{mm}/. Sitemap: /sitemap.xml, which includes /content/newsroom/press-releases.sitemap.xml (2026-10-04). Technical signal only, not permission.
- Questions:
  1. newsroom.bankofamerica.com has no terms of use, only '© 2026 Bank of America Corporation. All rights reserved.': is a copyright notice with no terms enough to store full release text and show short quoted excerpts with a link, or do we need a written OK from BofA Media Relations?
  2. Do the business.bofa.com 'Terms and Conditions for Bank of America Corporation Websites' (unlinked from the newsroom; download allowed only into a 'Client's internal computer system') govern newsroom.bankofamerica.com, and if so does a WashU prototype for Edward Jones count as such a 'Client'?
  3. Files under /content/dam/newsroom/ (attachments) are disallowed in robots.txt: do we skip release attachments and keep only the HTML release text?

#### T-18 prnewswire.com (PR Newswire Association LLC (Cision))

Rows: `EDJ-PRN-PRESS`, `BAC-PRN-PRESS-GWIM`, `MER-PRN-PRESS`

- Terms: <https://www.prnewswire.com/terms-of-use/>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "use any robot, spider, site search/retrieval application, or other manual or automatic device or process to access, search, download, retrieve, index or "data mine" any content or data from the Site"
- Full-text storage: **forbidden**. "you may not reproduce, modify, create derivative works from, display, perform, publish, distribute (including any electronic redistribution or database storage and retrieval), disseminate, broadcast or circulate to any third party"
- Excerpts: **forbidden**. "or otherwise use, any PR Newswire Materials, in full, in part, in full text or in abstract, without the express prior written consent of PR Newswire."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: TOU 'Last Updated: September 1, 2023'. It covers https://www.prnewswire.com and sister sites. In all three verdicts consent can be requested: the scrape clause reads 'reproduce, distribute, “frame,” “mirror,” “scrape,” republish or retransmit information or content provided by PR Newswire or found on the Site without the express prior written permission of PR Newswire', and storage and excerpts are allowed only with 'the express prior written consent of PR Newswire'. PERSONAL USE: 'you may access and use the PR Newswire Materials, and download or print out a single copy from the Site, solely for your personal, noncommercial use.' COMMERCIAL: the user agrees not to use the Site to 'generate revenue for any business or commercial purpose;'. AI: the user may not 'use any content from the Site, any services or activities conducted on or through the Site, or any system for the development of any software program, including, but not limited to, training a machine learning or artificial intelligence (AI) system.' OWNERSHIP: PR Newswire Materials include '(ii) news releases, photographs and other information and content issued by PR Newswire customers.' and 'are the exclusive property of PR Newswire.' (as between the user and PRN). Also, issuers 'are solely responsible for the facts and accuracy of, and for obtaining all rights to, information and content submitted by them'. CONSENT CONTACT: 'Inquiries concerning the use of PR Newswire text, photos, images, video, audio and other content should be addressed to Content Distribution Group, PR Newswire Association LLC, 200 Vesey Street, 19th Floor, New York, New York 10281.' GOVERNING LAW: 'shall be governed by and construed in accordance with the laws of the State of New York' (exclusive New York courts). RSS: /rss/ has no separate RSS terms, and feeds exist only by industry or for all news (e.g. rss/news-releases-list.rss), not per company. Footer: 'Copyright © 2026 Cision US Inc.'
- Text owner: The issuer writes the release text (EDJ pages end 'SOURCE Edward Jones'; BAC and Merrill pages end 'SOURCE Bank of America Corporation'). PRN's TOU claims news releases as 'PR Newswire Materials' that 'are the exclusive property of PR Newswire' as between the site user and PRN. Site © 2026 Cision US Inc.
- Access / cost: free; not published (reading is free; no price published for content licensing, which goes via the Content Distribution Group address in the TOU) (<https://www.prnewswire.com/terms-of-use/>)
- robots.txt: www.prnewswire.com/robots.txt, 'User-Agent: *': disallows only /templates/Blank-HTML, /templates/Multivuplayer.html, /templates/Home-page-with-spaces.html, /templates/Home-page-with-out-spaces.html, /templates/PRN_Custom_MultiVu_Recommendation, /templates/get-bitly-url.txt, /widget-landing-page.html and /multivu/. It allows /news/edward-jones/, /news/bank-of-america-corporation/ and /news-releases/*. Sitemaps: /sitemap.xml, /sitemap-news.xml, /llms.txt (2026-10-04). robots.txt allows these paths, but the TOU forbids robots, so robots.txt gives no permission here.
- Questions:
  1. PR Newswire TOU forbids any 'robot, spider ... or automatic device' and 'database storage and retrieval' of PR Newswire Materials (which include customers' news releases) without express prior written consent: do we ask PRN's Content Distribution Group (200 Vesey Street, New York) for consent, or drop EDJ-PRN-PRESS, BAC-PRN-PRESS-GWIM and MER-PRN-PRESS and use issuer copies instead (Edward Jones newsroom, BofA newsroom, 8-K Ex.99.1)?
  2. PR Newswire TOU allows a single copy 'solely for your personal, noncommercial use': does a WashU student prototype built for Edward Jones's Chief Strategy Office qualify?
  3. PR Newswire TOU bars using the Site to 'generate revenue for any business or commercial purpose' and using content 'for the development of any software program, including ... training a machine learning or artificial intelligence (AI) system': does an internal, non-revenue retrieval prototype that does no model training fall under either clause?
  4. PR Newswire TOU forbids showing PRN Materials 'in part ... or in abstract' without consent: under ADR-000's fallback, may we keep only metadata (headline, date, URL) for PRN items and link out without quoting?
  5. PRN claims customers' news releases as 'PR Newswire Materials': if the same release text is on the issuer's own site (Edward Jones or BofA newsroom), may we use the issuer copy and leave PRN out of the corpus entirely?

#### T-19 raymondjames.com (Raymond James Financial, Inc. (raymondjames.com: IR, News & Media, Advisor Opportunities))

Rows: `RJF-IR-DECK-EARNINGS`, `RJF-IR-DECK-EVENTS`, `RJF-IR-MONTHLY`, `RJF-ADVISOROPP-PRESS-RECRUITING`, `RJF-IR-PRESS-EARNINGS`, `RJF-NEWSROOM-PRESS`, `RJF-IR-SUPPLEMENT`, `RJF-IR-TRANSCRIPT-INVESTORDAY`, `RJF-IR-TRANSCRIPT-WEBCAST`

- Terms: <https://www.raymondjames.com/terms-of-use>, read 2026-10-04 (Wayback capture 2026-05-26 (web/20260526144046). Live page is blocked by Akamai for scripts, and the newest capture (2026-09-14) is an Akamai 'Access Denied' page.)
- Scraping: **silent**. "You may not use the Website or the Content in any manner that could damage, disable, overburden, or impair any Raymond James website or service or interfere with any other party’s use and enjoyment of the Website or the Content." (<https://web.archive.org/web/20260526144046/https://www.raymondjames.com/terms-of-use>)
- Full-text storage: **unclear**. "You may use the Content only for Your personal and non-commercial use. You may not modify, copy, distribute, transmit, display, perform, reproduce, publish, license, frame, create derivative works from, transfer, or otherwise use in any other way for commercial or public purposes" (<https://web.archive.org/web/20260526144046/https://www.raymondjames.com/terms-of-use>)
- Excerpts: **unclear**. "Raymond James prohibits caching, unauthorized hypertext links to the Website, and the framing of any Content available on the Website." (<https://web.archive.org/web/20260526144046/https://www.raymondjames.com/terms-of-use>)
- Other clauses: The scraping verdict is 'silent' because the terms have no robots, spider, crawler or automated-means clause; the quoted 'overburden' sentence is the closest clause. In practice Akamai blocks scripts (curl and WebFetch get timeouts or 403), and since 2026-08 Wayback captures of IR pages are 403 as well. The copy/reproduce sentence continues: 'in whole or in part any Content ... except for the purposes expressly provided herein, without Our prior written approval.' The caching sentence also matters for storage: storing full copies may count as 'caching'. License: 'We grant You ... a personal, limited, non-exclusive, revocable (at any time), non-transferable and non-sublicenseable license to access the Website and the Content'. Third-party content: 'You acknowledge that We may provide certain portions of the Content under license from Third Party Providers'. Market Information: 'You will not redistribute or facilitate the redistribution of Market Information'. No AI or text-and-data-mining clause. Governing law: 'This TOU will be governed by Florida law without giving effect to principles of conflict of law.' (Middle District of Florida or Pinellas County courts). Contacts for written approval: the copyright agent at legal.copyright@raymondjames.com (Cathy Sexton, 727.567.1000), or Media Relations (Steve Hollister, 727.567.2824, listed on releases). The same IR documents (earnings release, slides, monthly data, Investor Day deck) are also filed as SEC 8-K exhibits (tier 2), so they need not be fetched from this site (whether Raymond James's own terms still reach those copies is question 5).
- Text owner: Raymond James Financial, Inc. ('All right, title and interest in this Website and the Content is the exclusive property of Raymond James, except as otherwise expressly stated.'; footer '© 2026 Raymond James Financial, Inc. All rights reserved.')
- Access / cost: free; free (<https://www.raymondjames.com/investor-relations/financial-information/quarterly-earnings>)
- robots.txt: robots.txt read via a Wayback capture dated 2026-10-03; a live fetch on 2026-10-04 timed out because of Akamai. 'User-Agent: *' has no rule matching /investor-relations/, /-/media/rj/dotcom/files/our-company/..., /news-and-media/press-releases/ or /advisor-opportunities/press-releases/, so all are allowed. It disallows /advisorsearch/, /branches/library/, /forms/, /hov/, /newsletters/, /script/, /pdfs/legal/, /morgankeegan/, /advisorchoice/email/ and /legal-disclosures/mca-ira/. Akamai bot protection blocks scripts no matter what robots.txt says.
- Questions:
  1. raymondjames.com terms grant only a 'personal and non-commercial use' license and bar copying or reproducing Content 'for commercial or public purposes' without prior written approval. Does a WashU student prototype built for Edward Jones's Chief Strategy Office (an RJ competitor) qualify, or do we need written approval from Raymond James (legal.copyright@raymondjames.com or Media Relations)?
  2. raymondjames.com terms say 'Raymond James prohibits caching'. Does keeping full copies of RJ IR PDFs and press releases in our private Postgres and Box count as prohibited caching?
  3. raymondjames.com terms prohibit 'unauthorized hypertext links to the Website'. Is a citation link back to the RJ source document in our private answer UI an unauthorized link?
  4. raymondjames.com is behind Akamai bot protection (scripts get timeouts or 403s). Should RJ IR documents (earnings release, slides, monthly operating data, Investor Day deck) be taken only from SEC EDGAR 8-K exhibits (tier 2), with raymondjames.com limited to manual checks?
  5. Raymond James is the copyright holder of the same release text wherever it appears (GlobeNewswire, EDGAR, branch microsites). Do RJ's own terms then govern our copies even when we fetch the text from GlobeNewswire?

#### T-20 globenewswire.com (GlobeNewswire by Notified (Intrado Digital Media, LLC))

Rows: `RJF-GNW-PRESS`

- Terms: <https://portal.notified.com/terms-conditions/en>, read 2026-10-04 (Live page (portal.notified.com). No reader-facing website terms were found. The GlobeNewswire footer (in its React bundle, Wayback 2026-09-27) has only 'Legal' -> https://www.notified.com/privacy (a privacy statement, read via a Wayback capture dated 2026-10-03; live returned 403) and 'RSS Feeds' -> /rss/list (no terms text).)
- Scraping: **unclear**. "use or attempt to use any agent, engine, software, or other mechanism (including without limitation 'spiders' or 'bots') to navigate or search the Service or to gather or extract data from the Service"
- Full-text storage: **silent**. "No clause found for readers. The customer agreement covers only issuers' Releases, and the footer 'Legal' link is a privacy statement."
- Excerpts: **silent**. "No clause found for readers on GlobeNewswire or the linked Notified pages."
- Other clauses: The only terms found are the Intrado customer agreement ('govern access to and use of GlobeNewswire, including any content, functionality and services offered on or through GlobeNewswire'). The bot clause sits under 'Customer further agrees not to use the Service to:', so it binds paying issuers; it is unclear whether it binds readers. Issuer license to Intrado: 'Customer hereby grants Intrado and its affiliates a perpetual, non-exclusive, royalty-free, worldwide, sub-licensable right and license to use, distribute, redistribute, store and display any Releases'. Footer: 'GlobeNewswire is a newswire distribution network. Articles and other content published by GlobeNewswire are the legal responsibility of the author and GlobeNewswire accepts no liability for the content of such material.' and '© {year} Digital Media Innovations, LLC. All Rights Reserved.' No AI or TDM clause. The customer agreement goes to AAA arbitration, with regional governing-law sections (e.g. Ontario, Sweden, England & Wales, Singapore). Privacy contact: legal@notified.com.
- Text owner: The issuer, Raymond James Financial (page schema 'author copyrightHolder' = Raymond James Financial; RSS channel 'Copyright 2026, Raymond James Financial'). GlobeNewswire claims only the site ('© {year} Digital Media Innovations, LLC').
- Access / cost: free; free (<https://www.globenewswire.com/en/search/organization/Raymond%2520James%2520Financial>)
- robots.txt: robots.txt read via a Wayback capture dated 2026-05-05; live curl timed out on 2026-10-04. It has 'Allow: /news-release/'. /rssfeed/organization/ and /en/search/organization/ are not disallowed. It disallows */news-release/*.html?pdf=1, /newsroom/rss/, /SubscribeToRss/, /api/, /JsonData/, /StockQuote/, /JSWidget/, /Tracker?data=* and non-English language paths (/es/, /ja/, /zh-Hans/ ...).
- Questions:
  1. GlobeNewswire has no reader-facing terms; the only terms found (Intrado customer agreement at portal.notified.com/terms-conditions/en) bar 'spiders' or 'bots' for Customers. Does that clause bind us as non-customer readers, and may a script fetch /news-release/ pages and the RJF organization RSS feed (allowed by robots.txt)?
  2. GlobeNewswire marks Raymond James Financial as copyright holder of each release. Is storing full text taken from GlobeNewswire governed by RJ's own terms (personal, non-commercial only), so that we need RJ's permission even though GlobeNewswire is silent?

#### T-21 edwardjones.com (Edward Jones (Edward D. Jones & Co., L.P.; edwardjones.com))

Rows: `EDJ-NEWSROOM-PRESS`

- Terms: <https://www.edwardjones.com/us-en/terms>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "You agree that you will not use any robot, spider, other automatic device or manual process to monitor or copy our web pages, data or the content contained herein or for any other unauthorized purpose without our prior expressed written permission."
- Full-text storage: **forbidden**. "Systematic retrieval of content from the Website to create or compile, directly or indirectly, a collection, compilation, database or directory (whether through robots, spiders, automatic devices or manual processes) without the prior written permission from Edward Jones is strictly prohibited."
- Excerpts: **unclear**. "use in any other way, whether in whole or in part, any information, text, graphics, images, video clips, directories, databases, listings or software obtained from the Website for commercial or public purposes, without the prior written permission of Edward Jones."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: Both prohibitions are 'without prior written permission', so consent can be requested, and Edward Jones is the project's client. Use scope: 'All information and materials published, distributed or otherwise made available on the Website are provided for informational purposes, for your non-commercial, personal use only.' Internal use: 'Individual pages and/or sections of the Website may be printed for personal or internal use only, and provided that such printouts retain all applicable copyright or other proprietary notices.' Third-party data: 'Third party exchange data, if any, may not be downloaded, printed or redistributed for any purposes whatsoever.' No AI or TDM clause. Governing law: 'These Terms of Use shall be governed by and construed in accordance with the laws of the state of Missouri' (St. Louis County courts; jury trial waived). The terms list no consent contact.
- Text owner: Edward Jones ('Edward Jones, and its affiliates, retain all right, title and interest (including copyrights, trademarks, patents, as well as any other intellectual property or other right) in all information and content (including all text, data, graphics and logos) on the Website.')
- Access / cost: free; free (<https://www.edwardjones.com/us-en/why-edward-jones/news-media/press-releases>)
- robots.txt: Live robots.txt, 2026-10-04: /us-en/why-edward-jones/news-media/press-releases/ is not disallowed, so it is allowed. It disallows /search/, /node/*, /us-en/node/*, /admin/, /user/register/, /user/login/, /core/, /profiles/ and /cdn-cgi/. Sitemap: https://www.edwardjones.com/us-en/sitemap_index.xml
- Questions:
  1. edwardjones.com terms forbid robots and spiders, and forbid compiling a 'database' by systematic retrieval, without Edward Jones's prior written permission. Since Edward Jones is the client, can the CSO sponsor (or the WashU project lead) get that written permission for the newsroom, and who must sign it?
  2. edwardjones.com allows printing 'for personal or internal use only' and bars displaying or reproducing content 'for commercial or public purposes'. Does showing short quotes to a handful of project users count as internal use?
  3. Until written permission arrives, should EDJ newsroom releases be fetched manually (or taken from PR Newswire, if it is cleared), rather than by script?

#### T-22 events.q4inc.com (Q4 Inc. (Q4 Events platform hosting RJF earnings-call webcasts))

Rows: `RJF-IR-TRANSCRIPT-WEBCAST`

- Terms: <https://www.q4inc.com/terms-of-use>, read 2026-10-04 (live page (Effective date: December 31, 2020))
- Scraping: **forbidden**. ""Crawls," "scrapes," or "spiders" any page, data, or portion of or relating to the Services or Content (through use of manual or automated means)."
- Full-text storage: **forbidden**. "Copies or stores any significant portion of the Content;"
- Excerpts: **unclear**. "You will only use the Services for your own use, and not on behalf of or for the benefit of any third party, and only in a manner that complies with all laws that apply to you."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: The terms govern 'your use of our website(s), products, services ... (the "Services")'. 'Content' 'includes, without limitation, information, data, text, photographs, videos, audio clips ... generated, provided by Q4 or our Customers'. The restrictions are introduced by 'You represent, warrant, and agree that you will not use the Services or interact with the Services in a manner that:'. They also bar registering 'by any automated means'. Governing law: 'These Terms are governed by and will be construed under the laws of the State of New York'. Contact: privacy@q4inc.com. Attendees must register and accept the Q4 Terms of Use. No published text transcript: we would have to make our own transcription of the audio.
- Text owner: Raymond James Financial (the call content; Q4's 'Customers'); Q4 Inc. owns the platform
- Access / cost: free-registration; free (<https://events.q4inc.com/attendee/263306030>)
- robots.txt: events.q4inc.com/robots.txt (live 2026-10-04) has 'User-agent: *' with an empty 'Disallow:', so everything is allowed. The attendee page itself carries <meta name="robots" content="noindex"> and is a JavaScript app behind a registration form.
- Questions:
  1. Q4 Inc terms (events.q4inc.com) forbid crawling or scraping and 'Copies or stores any significant portion of the Content', and limit use to 'your own use, and not on behalf of ... any third party'. May the team record or transcribe RJF earnings-call webcasts at all, or should earnings-call text come only from cleared third-party transcripts or be skipped?

#### T-23 kaltura.com (Kaltura, Inc. (video host for RJF Investor Day replays, partner 1727781))

Rows: `RJF-IR-TRANSCRIPT-INVESTORDAY`, `BAC-IR-TRANSCRIPT-INVESTORDAY`

- Terms: <https://corp.kaltura.com/legal/tos/website-terms-of-use/>, read 2026-10-04 (live page (Last Updated October 3rd, 2023))
- Scraping: **unclear**. "use or launch any automated system, including without limitation, “robots,” “spiders,” “offline readers,” or similar tools, that accesses the Website, Service, or API in a manner that sends more request messages to the Kaltura servers in a given period of time than a human can reasonably produce"
- Full-text storage: **unclear**. "Content on the Website is provided to you ‘AS IS’ for your information and personal use only and may not be used, copied, reproduced, distributed, transmitted, broadcasted, displayed, sold, licensed, or otherwise exploited for any other purposes whatsoever"
- Excerpts: **unclear**. "Kaltura permits you to link to materials on the Website for personal, non-commercial purposes."
- Other clauses: The storage sentence continues: 'without the prior written consent of the respective owners of the Content' (here, Raymond James). Search-engine exception: 'Kaltura grants the operators of public search engines permission to use spiders to copy materials from the site for the sole purpose of creating publicly available searchable indices of the materials, but not caches or archives of such materials.' License: 'you use the Website only for personal, internal, noncommercial purposes (please contact commercial@kaltura.com regarding the terms of a commercial license)'. Scope: 'These Terms apply to all users of the Kaltura Website, including ... virtual event participants, and users who access the Service through partner sites'. Governing law: 'This Agreement shall be governed exclusively by the internal laws of the State of New York'. No text transcript exists; using it would require our own transcription.
- Text owner: Raymond James Financial (the content owner; Kaltura defers to 'the respective owners of the Content')
- Access / cost: free; free (<https://www.raymondjames.com/investor-relations/news-and-events/presentations-and-webcasts>)
- robots.txt: kaltura.com/robots.txt (live 2026-10-04) disallows /tiny/, /api_v3/, /content/, /p/*/serveFlavor/ and /index.php/kmc/preview/. The sample link path /tiny/3yj9n, which redirects through /api_v3/, is disallowed.
- Questions:
  1. Kaltura's terms allow content for 'personal use only' unless the content owner (Raymond James) gives prior written consent, and robots.txt disallows /tiny/ and /api_v3/. Is a one-off manual transcription of the RJF Investor Day replay allowed, or must we ask RJ for consent (or rely on the 8-K deck only)?
  2. Bank of America's 2025 Investor Day replay is also served by Kaltura: does the same consent question apply, with Bank of America as the content owner?

#### T-24 fool.com (The Motley Fool, LLC (Fool.com))

Rows: `MS-FOOL-TRANSCRIPT`, `SCHW-FOOL-TRANSCRIPT`, `BAC-FOOL-TRANSCRIPT`, `RJF-FOOL-TRANSCRIPT`

- Terms: <https://www.fool.com/legal/terms-and-conditions/fool-rules/>, read 2026-10-04 (live page (The Motley Fool's Rules - Terms of Use & Conditions of Sale, 'Last Updated: January 29, 2026'); also live https://www.fool.com/legal/stuff-we-own/)
- Scraping: **forbidden**. "Use any automated means, including, without limitation, agents, robots, scripts, or spiders, to access, monitor, copy or harvest data from any part of our sites;"
- Full-text storage: **unclear**. "You may make one copy of the Content for your personal, non-commercial use, provided that any material copied remains intact and includes the following notice: "Copyright 1995-2018 [or whatever the current year is] The Motley Fool. All rights reserved.""
- Excerpts: **unclear**. "You also may not republish, post, transmit, or distribute the Content to online bulletin and message boards, blogs, chat rooms, intranets, or anywhere else without our consent."
- Verification: scraping 'forbidden': 2/2 checkers confirmed.
- Other clauses: Scope note: the automated-means clause sits in a list introduced by "You may not use or allow others to use your Fool membership to:" (Section 8 Conduct), so its reach to non-members is ambiguous; Section 7 separately says "You further agree not to create abstracts from or scrape our Content, including CAPS ratings, for use on another website or service (including our own personal forums and blogs)." Storage: right after the one-copy permission: "Any other copying, distribution, storing, or transmission of any kind, or any commercial use of our Content, is prohibited without The Fool's prior written permission." (so written permission can be requested). Copyright page: "None of the material may be reproduced without our written permission, with the exception of downloading or printing a single copy for yourself for offline viewing." (https://www.fool.com/legal/stuff-we-own/). Access: "Unauthorized access of our sites is a breach of these Terms and Conditions and a violation of the law. You agree not to access our sites by any means other than through the interfaces we provide for use in our accessing our sites." Content definition: Content "is the property of The Motley Fool and/or providers of the content under license". No AI-training / text-and-data-mining clause found. Governing law: "governed by the laws of the United States of America and the Commonwealth of Virginia"; courts in Alexandria, VA. Contact for notices: General Counsel, The Motley Fool, LLC, 2000 Duke Street, Alexandria, VA 22314 (no specific permissions address found). Transcript footer: "Parts of this article were created using Large Language Models (LLMs) based on The Motley Fool's insights and investing approach."
- Text owner: The Motley Fool. Each transcript footer says: "This article is a transcript of this conference call produced for The Motley Fool." Byline "By Motley Fool Transcribing"; page footer "© 1995 - 2026 The Motley Fool. All rights reserved." The same text is syndicated to Yahoo Finance ("...was originally published by The Motley Fool"), AOL and Webull, so the owner stays The Motley Fool whichever copy is fetched. Vendor-produced text, so it falls under ADR-000.
- Access / cost: free; free (full transcript incl. Q&A loaded without login on 2026-10-04) (<https://www.fool.com/earnings/call-transcripts/2026/07/15/morgan-stanley-ms-q2-2026-earnings-call-transcript/>)
- robots.txt: User-agent *: no Disallow matches /earnings/call-transcripts/, /earnings-call-transcripts/ or /sitemap/ (monthly sitemaps), so allowed; disallows /feeds, /a/ (Allow /a/feeds/), /premium-reports, /quote/failed-lookup/, /api/historical/ etc.; MauiBot and Bytespider disallowed site-wide; no AI-crawler rules (2026-10-04).
- Questions:
  1. Fool.com terms allow one copy 'for your personal, non-commercial use' and prohibit 'any other copying, distribution, storing' without The Fool's prior written permission: does storing full transcripts in a shared private Postgres + Box folder for the WashU/Edward Jones prototype qualify, or must we ask The Motley Fool for written permission?
  2. Fool.com terms forbid 'any automated means, including ... robots, scripts, or spiders, to access, monitor, copy or harvest data', but the clause is listed under use of 'your Fool membership': does it bind a script that fetches free transcript pages without a membership, and should we ask Fool for consent before fetching?
  3. Fool.com terms bar distributing Content to 'intranets, or anywhere else without our consent': is showing short quoted transcript passages with a link to a handful of project users an intranet distribution that needs Fool's consent?
  4. Fool.com transcripts are 'produced for The Motley Fool' (partly LLM-written): do we treat them as vendor-owned licensed text under ADR-000 rather than tier 3?

#### T-25 seekingalpha.com (Seeking Alpha Ltd. (seekingalpha.com))

Rows: `MS-SEEKINGALPHA-TRANSCRIPT`, `SCHW-SEEKINGALPHA-TRANSCRIPT`, `BAC-SEEKINGALPHA-TRANSCRIPT`, `RJF-SEEKINGALPHA-TRANSCRIPT`

- Terms: <https://about.seekingalpha.com/terms>, read 2026-10-04 (live page (Terms of Use, 'Updated: May 2, 2021'); RSS feed terms read live from https://seekingalpha.com/api/sa/combined/MS.xml; transcript list page read via Wayback capture 2025-07-20 (live pages 403))
- Scraping: **forbidden**. "Use any robot, spider, site search/retrieval application, or other manual or automatic device or process to download, retrieve, index, "data mine", "scrape", "harvest" or in any way reproduce or circumvent the navigational structure or presentation of the Site or its contents;"
- Full-text storage: **unclear**. "You may access and use the Content, and download and/or print out copies of any content from the Site, solely for your personal, non-commercial use."
- Excerpts: **unclear**. "You may link to any content on the Site. If you are interested in reprinting, republishing or distributing content from Seeking Alpha, please contact Seeking Alpha to obtain written consent."
- Verification: scraping 'forbidden': 2/2 checkers confirmed.
- Other clauses: Section 6 User Conduct: "You may not use, copy, display, sell, license, de-compile, republish, upload, post, transmit, distribute, create derivative works or otherwise exploit Content from the Site to online bulletin boards, message boards, newsgroups, chat rooms, or in other any manner, without our prior written permission. Modification of the Content or use of the Content for any purpose other than your own personal, noncommercial use is a violation of our copyright and other proprietary rights, and can subject you to legal liability." Also forbids to '"Frame" or "mirror" any part of the Site without our prior written authorization'. Linking is explicitly allowed ("You may link to any content on the Site."). RSS feed terms (channel description of https://seekingalpha.com/api/sa/combined/{TICKER}.xml): "Use of this feed is limited to personal, non-commercial use and is governed by Seeking Alpha's Terms of Use (https://about.seekingalpha.com/terms). Publishing this feed for public or commercial use and/or misrepresentation by a third party is prohibited." No separate AI-training clause beyond 'data mine'. Governing law: "governed by and construed in accordance with the laws of the State of New York". Consent route: 'please contact Seeking Alpha to obtain written consent' (no address on the terms page).
- Text owner: Seeking Alpha. Transcripts are bylined "SA Transcripts" (RSS <sa:author_name>SA Transcripts</sa:author_name>; list page capture 2025-07-20). Terms: Content "are the property of Seeking Alpha and its third-party licensors or providers". RSS: "© seekingalpha.com". Transcript-page copyright notice not read (403).
- Access / cost: unknown; not published (pricing page https://seekingalpha.com/subscriptions/premium returned only a 'Javascript is Disabled' shell to a script; no price read) (<https://seekingalpha.com/subscriptions/premium>)
- robots.txt: User-agent *: no Disallow matches /article/ or /symbol/{T}/earnings/transcripts, so allowed; disallows /search, /authentication, /api/v3/account and other /api/v3 paths; /api/sa/combined/ (RSS) not disallowed; about 100 named agents disallowed site-wide incl. ClaudeBot, Claude-User, ChatGPT-User, CCBot, Scrapy, Diffbot, PerplexityBot-User, Meta-ExternalAgent (2026-10-04). Live article and symbol pages return 403 to curl and WebFetch anyway; sitemaps and RSS return 200.
- Questions:
  1. Seeking Alpha terms forbid any 'robot, spider ... or other manual or automatic device' to download or 'scrape', and its pages return 403 to scripts: do we drop Seeking Alpha, or ask Seeking Alpha for written consent?
  2. Seeking Alpha allows downloads 'solely for your personal, non-commercial use': would storing full transcripts for the WashU/Edward Jones prototype count as personal, non-commercial use?
  3. Seeking Alpha per-ticker RSS feeds (seekingalpha.com/api/sa/combined/{TICKER}.xml) list transcripts but are 'limited to personal, non-commercial use': may we use the feed only for discovery (title, link, pubDate) without storing article text?
  4. Seeking Alpha explicitly allows linking ('You may link to any content on the Site'): if storage and quoting are not cleared, is metadata + link only an acceptable fallback for this source?

#### T-26 investing.com (Fusion Media Limited (Investing.com))

Rows: `MS-INVESTINGCOM-TRANSCRIPT`, `SCHW-INVESTINGCOM-TRANSCRIPT`, `BAC-INVESTINGCOM-TRANSCRIPT`, `RJF-INVESTINGCOM-TRANSCRIPT`

- Terms: <https://www.investing.com/about-us/terms-and-conditions>, read 2026-10-04 (live page; the terms text is an embedded PDF https://cdn.investing.com/about-us/terms_and_conditions.pdf ('Last Modified : August 2025'), read live)
- Scraping: **forbidden**. "You are expressly forbidden from employing any automated system or software to extract data for content from this website for any purpose. This includes, but is not limited to, scraping, data mining, robot or spider programs" (<https://cdn.investing.com/about-us/terms_and_conditions.pdf>)
- Full-text storage: **forbidden**. "You may not sell, rent, lease, distribute, redistribute, license, publicly perform or display, publish, edit, create derivative works from, copy, modify, or otherwise make unauthorized use of the Platform, the Content" (<https://cdn.investing.com/about-us/terms_and_conditions.pdf>)
- Excerpts: **forbidden**. "You agree not to upload, post, reproduce or distribute any information, software or other material protected by copyright or any other intellectual property right" (<https://cdn.investing.com/about-us/terms_and_conditions.pdf>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: Section 10(b) continues: '...without the Fusion Media's prior explicit written consent (which may be given or refused at its sole discretion on a case by case basis)', so consent can be requested. Section 20 continues: '...without first obtaining the permission of the owner of such rights and the prior written consent of Fusion Media (on a case by case basis)'. Section 10(a): "Any use of the Platform shall be solely for your own personal use only. You are strictly prohibited from using any portion of the Platform for any commercial or business purposes." Section 14 defines Market Information as including 'financial market data, quotes, news, analyst opinions, research reports, graphs and data', provided 'only for your internal use and not for any commercial purpose', and says: You will not "deep-link", redistribute or facilitate the redistribution of Market Information, and must not 'copy, store, sell, license, distribute, reproduce, transmit or duplicate to any third party or to any person any Market Information or any part thereof' without prior written consent. Section 15 covers AI-generated content (disclaimer only, no TDM clause). Footer of every page: "It is prohibited to use, store, reproduce, display, modify, transmit or distribute the data contained in this website without the explicit prior written permission of Fusion Media and/or the data provider." Governing law: "These Terms and Conditions shall be governed by the laws of England and Wales".
- Text owner: Fusion Media Limited (Investing.com). Byline "By Investing.com"; page disclaimer "This article was generated with the support of AI and reviewed by an editor. For more information see our T&C."; footer "© 2007-2026 Fusion Media Limited. All Rights Reserved." Terms s.20: Content is "owned by Fusion Media, or its affiliates, or other licensors". Images credited "© Reuters."
- Access / cost: free; free (full transcript with Q&A, no paywall seen on 2026-10-04 via WebFetch; InvestingPro is a separate paid product not needed) (<https://www.investing.com/news/transcripts/earnings-call-transcript-morgan-stanley-posts-record-q2-2026-results-beats-forecasts-93CH-4793583>)
- robots.txt: User-agent *: allows /news/transcripts/ (no matching Disallow); disallows /news/press-releases, /news/pro/, /news/assorted/, /news/filings/ (except index), /pro/ (with listed exceptions), /research/, /members, /content (2026-10-04). No AI-crawler rules. Transcript pages return 403 to curl (bot challenge); robots.txt and terms page return 200.
- Questions:
  1. Investing.com terms expressly forbid 'any automated system or software to extract data ... for any purpose' and copying without Fusion Media's 'prior explicit written consent': do we request consent from Fusion Media or drop Investing.com?
  2. Investing.com terms say 'Any use of the Platform shall be solely for your own personal use only' and forbid 'commercial or business purposes': does a WashU student prototype built for Edward Jones's Chief Strategy Office count as business use?
  3. Investing.com terms forbid 'deep-link' redistribution of Market Information (which includes 'news'): may answers link directly to individual transcript article URLs?
  4. Investing.com transcripts are 'generated with the support of AI and reviewed by an editor' and the terms are governed by English law: does either point change how ADR-000 classifies this source?

#### T-27 finance.yahoo.com (Yahoo Finance LLC (Yahoo Inc.))

Rows: `MS-YAHOO-TRANSCRIPT`, `SCHW-YAHOO-TRANSCRIPT`, `BAC-YAHOO-TRANSCRIPT`, `RJF-YAHOO-TRANSCRIPT`

- Terms: <https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html>, read 2026-10-04 (live page (Yahoo Terms of Service, 'Last updated: 4 August 2026'))
- Scraping: **forbidden**. "collect data, from our Services using any automated means, devices, programs, algorithms or methodologies, including but not limited to robots, spiders, scrapers, data mining tools, or data gathering or extraction tools, for any purpose without our express, prior permission."
- Full-text storage: **forbidden**. "Unless you have explicit written permission, you must not reproduce, modify, rent, lease, sell, trade, distribute, transmit, broadcast, publicly perform, create derivative works based on, or exploit for any commercial purposes, any portion or use of, or access to, the Services"
- Excerpts: **forbidden**. "Unless you have explicit written permission, you must not reproduce, modify, rent, lease, sell, trade, distribute, transmit, broadcast, publicly perform, create derivative works based on, or exploit for any commercial purposes, any portion or use of, or access to, the Services"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The reproduce clause continues '(including content, advertisements, APIs, and software).' Scraping clause opens 'access or collect data, or attempt to access or collect data,' and ends 'without our express, prior permission' (permission can be requested). Database clause: "use any material or content from, including without limitation any data, (a) to create any database, archive, mobile application, data feed, widget or any other aggregated data source that competes with or constitutes a material substitute for the Services". Commercial use: "Unless otherwise expressly stated, you may not access or reuse the Services, or any portion thereof, for any commercial purpose." Interface: "You must not misuse or interfere with the Services or try to access them using a method other than the interface and the instructions that we provide." Entity: 'Yahoo Inc., except for Yahoo Finance which is provided by Yahoo Finance LLC.' Governing law: "governed by the laws of the State of New York"; binding arbitration (NAM) for US users. Fee-based Services governed by additional terms.
- Text owner: Third-party licensed text, not Yahoo's. (1) /quote/{T}/earnings/ pages: Quartr-provided transcripts ('Powered by Quartr' per earlier hand check; could not re-check on 2026-10-04 because these pages returned 404 to curl and WebFetch); page JSON carries a 'quartrId' per ticker. (2) Transcript articles under /markets/stocks/articles/ are syndicated Motley Fool text: "Bank of America (BAC) Q2 2026 Earnings Call Transcript was originally published by The Motley Fool", byline "Motley Fool Transcribing, The Motley Fool", provider 'Motley Fool'. Page footer: "Copyright © 2026 Yahoo. All rights reserved."
- Access / cost: paywall; Latest call free; older calls show 'Upgrade to unlock' (earlier hand check). Published plans (yearly billing): Bronze $7.95/mo, Silver $19.95/mo, Gold $39.95/mo ('Billed $479.40 yearly'). The plan page text does not say which plan unlocks historical transcripts. (<https://finance.yahoo.com/plus/select-plan/>)
- robots.txt: User-agent *: allows /quote/{T}/earnings-calls/ and /markets/stocks/articles/; disallows /quote/*/earnings/*.html but Allows /quote/*/earnings/*-*-2025-*-*.html and /quote/*/earnings/*-*-2026-*-*.html (so 2024-and-older transcript pages are disallowed); disallows /xhr (the earnings-calls list loads from /xhr/earnings-event), /quotes/*, /p/, /m/; site-wide Disallow for anthropic-ai, ClaudeBot, Claude-Web, GPTBot, ChatGPT-User, CCBot, Google-Extended, Scrapy, PerplexityBot and others (2026-10-04).
- Questions:
  1. Yahoo terms forbid collecting data 'using any automated means ... for any purpose without our express, prior permission' and robots.txt blocks /xhr plus anthropic-ai/ClaudeBot/GPTBot: do we ask Yahoo for permission or drop Yahoo Finance?
  2. Yahoo terms bar reproducing 'any portion' of the Services, including content, without explicit written permission: does that rule out both storing and quoting Yahoo-hosted transcripts unless Yahoo agrees?
  3. Yahoo's earnings-call transcripts are provided by Quartr and its transcript articles are 'originally published by The Motley Fool': whose permission would we need for each (Yahoo, Quartr, The Motley Fool), and should we fetch the Fool text from Fool.com instead?
  4. Yahoo older transcripts need a paid plan: is a paid Yahoo Finance seat in scope, and would extraction from it be the same licensed-data question as Capital IQ/Bloomberg under ADR-000?
  5. Yahoo terms say 'you may not access or reuse the Services, or any portion thereof, for any commercial purpose': does the Edward Jones-facing prototype count as commercial?

#### T-28 alphastreet.com (AlphaStreet, Inc. (news.alphastreet.com))

Rows: `MS-ALPHASTREET-TRANSCRIPT`, `SCHW-ALPHASTREET-TRANSCRIPT`, `BAC-ALPHASTREET-TRANSCRIPT`, `RJF-ALPHASTREET-TRANSCRIPT`

- Terms: <https://alphastreet.com/Termsofuse/>, read 2026-10-04 (live page. The news site's own footer link 'Terms of Service' (https://news.alphastreet.com/termsofuse/, published 2026-02-05, modified 2026-02-16) contains only a DMCA notice plus a link to https://news.alphastreet.com/disclaimer/ (no-advice and liability disclaimer only). The usage clauses quoted here come from the parent AlphaStreet, Inc. terms at https://alphastreet.com/Termsofuse/ ('Last Updated: May 23, 2023'), which use the same legal@alphastreet.com contact.)
- Scraping: **unclear**. "Unauthorized framing or linking to the website, as well as unauthorized use of any automated device on the website, will be subject to investigation and appropriate legal action, including civil, criminal, and injunctive measures."
- Full-text storage: **unclear** (first read as forbidden; refuted on re-check, see below). "Unless information is in the public domain or you have obtained written permission from AlphaStreet, you are strictly prohibited from using, reproducing, copying, modifying, publishing, transmitting, distributing, performing, displaying, downloading, licensing, entering into a database"
- Excerpts: **unclear** (first read as forbidden; refuted on re-check, see below). "However, except for the limited purpose of reviewing material on the website, electronic reproduction, adaptation, distribution, performance, or display is strictly prohibited. Commercial use of the content for profit is also prohibited."
- Verification: full_text_storage 'forbidden': 0/2 checkers confirmed; refuted because: Quote found verbatim on the live page https://alphastreet.com/Termsofuse/ ('Last Updated: May 23, 2023', HTTP 200 on 2026-10-04). It does ban 'entering into a database' without written permission, so it would block our Postgres/Box copies if it applies. The problem is scope. Those parent terms define their site as 'You are prohibited from accessing or using the www.alphastreet.com/alphastreet.io website ("Website") for any unlawful or unauthorized purposes.' and never name news.alphastreet.com (the page has no link to the news subdomain). The terms that every transcript page links to in its footer are https://news.alphastreet.com/termsofuse/ (JSON-LD datePublished 2026-02-05, dateModified 2026-02-16). Fetched live, they contain only a DMCA notice and a link to https://news.alphastreet.com/disclaimer/, which only covers no-advice and liability. Neither page has a copy, storage or database clause. So the news site's own terms are silent, and it is ambiguous whether the 2023 parent terms reach it: verdict unclear, not forbidden. If the parent terms do apply, they only allow 'retain copies of website pages for personal use only', and the database ban makes it forbidden (written permission can be requested at legal@alphastreet.com). Ownership notes: the transcript page footer reads '© 2026 Alphastreet. All rights reserved.' The MS Q1 2026 transcript text itself includes the issuer's statement 'This presentation may not be duplicated or reproduced without our consent.' (Morgan Stanley's own words, separate from AlphaStreet's terms). ADR-000 questions: (1) Do the alphastreet.com Terms of Use (2023, scoped to www.alphastreet.com/alphastreet.io) govern news.alphastreet.com, whose own 2026 Terms of Service have no use restrictions? (2) If they do, should we ask legal@alphastreet.com for written permission to store full transcripts? (3) Does Morgan Stanley's in-call 'may not be duplicated or reproduced without our consent' statement block storing the MS transcript, whoever hosts it? / I fetched the quote live from https://alphastreet.com/Termsofuse/ ('Last Updated: May 23, 2023') on 2026-10-05, and it is word for word. It is a fair excerpt that stops at 'entering into a database'; the full sentence goes on with '...in whole or in part'. If these terms govern, they clearly forbid storing full copies (copying, downloading and 'entering into a database' without written permission, with no carve-out). The problem is scope. This page limits itself to 'this website' and defines that as 'the www.alphastreet.com/alphastreet.io website ("Website")'. It never mentions news.alphastreet.com, where every transcript row (MS/SCHW/BAC/RJF-ALPHASTREET-TRANSCRIPT) lives. The news site's own footer 'Terms of Service' link goes to https://news.alphastreet.com/termsofuse/ (datePublished 2026-02-05, dateModified 2026-02-16), which I fetched live. That page has only a DMCA notice and a link to /disclaimer/, which I also fetched; the disclaimer page has no copy, storage or database clause. The only other signal on the news site is a footer line, '© 2026 Alphastreet. All rights reserved.' So the posted terms of the subdomain that hosts the documents say nothing about storage. The parent ban applies only if AlphaStreet's alphastreet.com terms cover the news subdomain, and the terms do not say that. A suggested ADR-000 question: 'AlphaStreet: do the alphastreet.com Terms of Use (which forbid entering content into a database without written permission) govern news.alphastreet.com transcripts, whose own Terms of Service page has only a DMCA notice? Should we ask legal@alphastreet.com for written permission?' Better verdict: unclear (forbidden if the parent terms apply; silent on the news site's own terms).. excerpts 'forbidden': 0/2 checkers confirmed; refuted because: Quote found verbatim on https://alphastreet.com/Termsofuse/ (live, 2026-10-04). Within those terms it does cover our use: showing quoted passages in our app is 'electronic reproduction ... or display' outside 'the limited purpose of reviewing material on the website', and the IP clause adds 'in whole or in part'. There is no carve-out for short quotations. The same parent terms also say 'Deep-linking to the website is not allowed unless specifically authorized by AlphaStreet.', and that would also hit our link back to each transcript page. Same scope problem as above, though. The parent terms define the Website as 'www.alphastreet.com/alphastreet.io'. The news site's own footer-linked Terms of Service (https://news.alphastreet.com/termsofuse/, 2026-02-05, modified 2026-02-16) and its disclaimer page say nothing about quoting, display or linking. So for news.alphastreet.com transcripts the verdict is unclear, not forbidden. Whether fair use covers short quotes is a legal question, not a terms question. ADR-000 questions: (1) Do the alphastreet.com 'no electronic reproduction or display' and 'no deep-linking unless specifically authorized' clauses govern news.alphastreet.com transcript pages? (2) If yes, should we ask AlphaStreet (legal@alphastreet.com) to authorize short quotes with deep links, or link only to the /earnings-call-transcripts/ landing page? Robots note (2026-10-04, https://news.alphastreet.com/robots.txt): it disallows /search/, /?s=, /*-earnings-call/, /*/feed/ and /*-sec-form-*. Transcript URLs like /morgan-stanley-ms-q1-2026-earnings-call-transcript/ and /earnings-call-transcripts/ do not match any of those, so they are not disallowed. / I fetched this quote live from https://alphastreet.com/Termsofuse/ on 2026-10-05, and it is word for word. If these terms govern, the verdict holds. The only right granted is 'a non-exclusive license to view the content on the website while accessing it'. Outside 'reviewing material on the website', any 'electronic reproduction... or display is strictly prohibited'. The IP clause also bans 'displaying... in whole or in part' without written permission, with no allowance for short quotes or attribution. Showing quoted passages in our app counts as electronic reproduction and display. The scope problem is the same as for storage. The page covers 'the www.alphastreet.com/alphastreet.io website ("Website")', but the transcripts sit on news.alphastreet.com. That site's own 'Terms of Service' (https://news.alphastreet.com/termsofuse/, modified 2026-02-16) and its linked /disclaimer/ page have no reproduction, display or quotation clause at all. Only a '© 2026 Alphastreet. All rights reserved.' footer appears there. Whether the ban reaches the news subdomain's transcripts is an open question for ADR-000, not settled by the text. A suggested question: 'AlphaStreet: does the alphastreet.com ban on electronic reproduction/display (beyond reviewing on the site) apply to quoting short passages of news.alphastreet.com transcripts? Should we request permission at legal@alphastreet.com?' Better verdict: unclear..
- Other clauses: Personal use: 'By accessing the website, you agree that you are authorized to visit, view, and retain copies of website pages for personal use only.' Linking: 'Deep-linking to the website is not allowed unless specifically authorized by AlphaStreet.' (Our answers link back to individual transcript URLs.) Ownership: 'All information and materials displayed on this website, except for content linked to or from external sources, are the exclusive property of AlphaStreet.' Another clause says 'Unauthorized use of the website includes using any automatic or manual conduct, device, software, or process that interferes with the operation of the website or imposes an unreasonable burden on it.' That makes the automated-access rule depend on authorization or burden, hence 'unclear'. Storage and excerpts are prohibited unless AlphaStreet gives written permission, so consent can be requested from legal@alphastreet.com or support@alphastreet.com (AlphaStreet, Inc., 44053 Fremont Blvd, Fremont, CA 94538). No AI or text-and-data-mining clause. https://news.alphastreet.com/llms.txt is an auto-generated All in One SEO post index with no permission terms. Governing law: United States and California, with AAA arbitration in San Francisco.
- Text owner: AlphaStreet. Transcript page footers say '© 2026 Alphastreet. All rights reserved.' and the parent terms claim exclusive property. No third-party transcript vendor is named. The site tagline says 'AI-powered insights, human-curated quality.' Each page ends with 'Disclaimer: This transcript is provided for informational purposes only...'
- Access / cost: free; free (transcript pages open with no login or paywall; no price published for the news site) (<https://news.alphastreet.com/transcripts/>)
- robots.txt: https://news.alphastreet.com/robots.txt (2026-10-04), User-agent *. Allows /transcripts/, /ticker/{t}/ and /{slug}-earnings-call-transcript/. Disallows /*-earnings-call/ (older 2021-22 companion URLs such as /rjf-raymond-james-financial-inc-q1-2022-earnings-call/), /*/feed/, /search/, /?s=, /*?ec_ticker=, /*-sec-form-* and /wp-admin/. Sitemaps: sitemap.xml, sitemap.rss and as-news-feed.xml. No Content-Signal line.
- Questions:
  1. AlphaStreet: the news.alphastreet.com 'Terms of Service' page is DMCA-only. Do the AlphaStreet, Inc. terms at alphastreet.com/Termsofuse/ (May 23, 2023) govern transcripts on news.alphastreet.com?
  2. AlphaStreet terms prohibit 'entering into a database' and 'electronic reproduction ... or display' without written permission. Should we ask legal@alphastreet.com for written permission before storing full transcripts or showing excerpts, or limit AlphaStreet to metadata plus link?
  3. AlphaStreet terms allow retaining copies 'for personal use only' and prohibit 'Commercial use of the content for profit'. Does a student prototype for Edward Jones's Chief Strategy Office qualify?
  4. AlphaStreet terms say 'Deep-linking to the website is not allowed unless specifically authorized by AlphaStreet'. May our answers link to individual AlphaStreet transcript URLs?
  5. AlphaStreet terms threaten action for 'unauthorized use of any automated device on the website'. Does a slow, robots-compliant fetch script need AlphaStreet's prior authorization?
  6. AlphaStreet transcripts are AlphaStreet-owned third-party text, not company IR material. Should they keep the tier 3 (IR) label or be handled like tier 4 trade press under ADR-000?

#### T-29 marketbeat.com (MarketBeat Media, LLC (transcripts 'Provided by Quartr'))

Rows: `MS-MARKETBEAT-TRANSCRIPT`, `SCHW-MARKETBEAT-TRANSCRIPT`, `BAC-MARKETBEAT-TRANSCRIPT`, `RJF-MARKETBEAT-TRANSCRIPT`

- Terms: <https://www.marketbeat.com/terms/>, read 2026-10-04 (live page (the combined terms and privacy page ends with 'Last Updated: 8/20/2025.'). Also read https://www.marketbeat.com/llms.txt ('Last updated: 2026-08-21') and robots.txt.)
- Scraping: **unclear**. "You agree not to access the Services by any means other than through the interface that is provided by MarketBeat for use in accessing the Services."
- Full-text storage: **unclear**. "No Resale. You agree not to resell, reproduce, duplicate, copy, sell, trade, resell, or exploit for any commercial purposes any content or data acquired from MarketBeat's services without first entering into a licensing agreement to do so with MarketBeat."
- Excerpts: **unclear**. "# You MUST cite MarketBeat as the source when referencing or outputting information from this site. # A hyperlink back to the original MarketBeat page is REQUIRED with each citation." (<https://www.marketbeat.com/llms.txt>)
- Other clauses: License: 'MarketBeat grants you a personal, non-transferable and non-exclusive right and license to use the Services and Software for a single user unless you have contacted MarketBeat and obtained a site-license or multiple user license'. Bulk: 'Data compiled by MarketBeat may not be redistributed in bulk (such as by CSV, Excel or database formats) to any third party.' Property clause: users may not 'modify, rent, lease, loan, sell, distribute, transmit, broadcast, publicly perform or create derivative works based on the Services'. AI: robots.txt has 'Content-Signal: search=yes, ai-input=yes, ai-train=yes'. llms.txt says '# MarketBeat allows access to all public, non-disallowed sections for LLM and AI Overviews purposes.', lists 'Allow: /earnings/', and says '# For questions or permissions, contact: contact@marketbeat.com'. The terms have no scraping, robots or text-and-data-mining clause and are silent on quotation; the only citation rule is in llms.txt. Governing law: South Dakota, with confidential AAA arbitration in Sioux Falls. Consent contact: contact@marketbeat.com (also the DMCA agent).
- Text owner: Quartr (third-party provider). Each transcript is headed 'Provided by Quartr' and links to quartr.com. The page footer says '© MarketBeat Media, LLC 2010-2026. All rights reserved.' The 'Key Takeaways' block above the transcript is marked 'AI Generated. May Contain Errors.' Quartr's own terms were not reviewed.
- Access / cost: free; free: 'These earnings transcripts are freely available to the public with no paid subscription required.' (MarketBeat All Access is a separate paid product; its price was not checked.) (<https://www.marketbeat.com/earnings/transcripts/>)
- robots.txt: https://www.marketbeat.com/robots.txt (2026-10-04), User-agent *. Has 'Content-Signal: search=yes, ai-input=yes, ai-train=yes'. No Disallow matches /earnings/reports/, /earnings/transcripts/ or /stocks/NYSE/{T}/earnings/, so they are allowed (llms.txt also lists 'Allow: /earnings/'). Disallows */terms/*, */rss-feeds/*, /scripts/, /sec/, /newsletter/, /articles/?query=* and single-letter paths (/g/, /r/, /s/ and others).
- Questions:
  1. MarketBeat ToS grants a personal license 'for a single user unless you have ... obtained a site-license or multiple user license'. Does a prototype queried by several people need a MarketBeat multi-user or site license?
  2. MarketBeat ToS bars copying content 'for any commercial purposes' without a licensing agreement. Is storing full transcripts for an Edward Jones CSO prototype a commercial purpose?
  3. MarketBeat ToS forbids access 'by any means other than through the interface that is provided by MarketBeat', while robots.txt (ai-input=yes) and llms.txt allow LLM access to /earnings/. Which governs a scripted fetch, and should we get written confirmation from contact@marketbeat.com?
  4. MarketBeat transcripts are 'Provided by Quartr'. Does MarketBeat's llms.txt permission and its cite-plus-hyperlink rule cover Quartr-owned text, or do we also need Quartr's permission?
  5. MarketBeat transcripts are Quartr-owned third-party text, not company IR material. Should they keep the tier 3 (IR) label or be handled like tier 4 trade press under ADR-000?

#### T-30 roic.ai (ROIC AI, Inc. (Roic.ai))

Rows: `MS-ROIC-TRANSCRIPT`, `SCHW-ROIC-TRANSCRIPT`, `BAC-ROIC-TRANSCRIPT`, `RJF-ROIC-TRANSCRIPT`

- Terms: <https://www.roic.ai/tos>, read 2026-10-04 (live page via curl ('Last updated: April 7, 2026'). Also read https://www.roic.ai/pricing. The repo notes say WebFetch gets HTTP 403 here; curl with a normal browser user agent returned 200, with no challenge.)
- Scraping: **unclear**. "To scrape, crawl, or harvest data beyond the access granted by your plan"
- Full-text storage: **unclear**. "Our aggregated datasets, platform design, trademarks, and trade dress may not be used in connection with any product or service without the prior written consent of ROIC AI."
- Excerpts: **unclear**. "To redistribute, resell, or sublicense data obtained from the platform without authorization"
- Other clauses: Ownership: 'The Service and its original content, features, and functionality are and will remain the exclusive property of ROIC AI and its licensors.' The scraping and redistribution bans both sit under 'You agree not to use the Service:'. Plans (pricing page): the Free API plan lists 'Earnings call transcripts: 2 quarters', while the public website shows full transcripts back to 2007. API: 'API keys are personal and non-transferable.' The terms have no explicit personal or non-commercial clause, no AI or text-and-data-mining clause, and say nothing about quoting. No llms.txt (404). Governing law: 'These Terms shall be governed and construed in accordance with the laws of the United Kingdom'. Consent contact: support@roic.ai.
- Text owner: ROIC AI and its unnamed licensors. The footer says '© 2026 ROIC AI, Inc.' and Roic does not name its transcript provider. In a 30-sentence random sample, every sentence of Roic's MS Q2 2026 transcript appeared word for word in MarketBeat's 'Provided by Quartr' text for the same call, so the upstream source is probably the same vendor (unconfirmed).
- Access / cost: free; Website transcript pages: free, with no login seen. API (as published): Free $0/month (transcripts: 2 quarters, 5 requests/minute); Individual $29/month (2 quarters); Professional $89/month (all available quarters); Enterprise: 'Contact Us'. Annual billing gives 2 months free. (<https://www.roic.ai/pricing>)
- robots.txt: https://www.roic.ai/robots.txt (2026-10-04), User-agent *: 'Allow: /'. Allows /quote/{T}/transcripts and /quote/{T}/transcripts/{yyyy}-year/{q}-quarter. Disallows only /monitoring, /rybbit/ and /api/user/crisp-identity. Sitemap: https://www.roic.ai/sitemap.xml. No Content-Signal line.
- Questions:
  1. Roic.ai ToS forbids scraping 'beyond the access granted by your plan'. The Free API plan grants only '2 quarters' of transcripts, while the website shows them back to 2007. What access does an unregistered website visitor have, and would a backfill script exceed it?
  2. Roic.ai ToS says its 'aggregated datasets ... may not be used in connection with any product or service without the prior written consent of ROIC AI'. Is our private prototype a 'product or service', and should we ask support@roic.ai for consent before storing full transcripts?
  3. Roic.ai ToS bars redistributing data 'without authorization'. Does showing short quoted passages to a handful of project users count as redistribution?
  4. Roic.ai does not name its transcript provider, and its text matches MarketBeat's Quartr-provided text word for word. Who owns the Roic transcript text, and whose permission applies?
  5. Roic.ai terms are governed by UK law. Does that change the ADR-000 analysis for this source?
  6. Roic.ai transcripts are third-party text, not company IR material. Should they keep the tier 3 (IR) label or be handled like tier 4 trade press under ADR-000?

#### T-31 advisorhub.com (AdvisorHUB LLC (AdvisorHub))

Rows: `T4-ADVISORHUB`

- Terms: <https://www.advisorhub.com/terms-of-use/>, read 2026-10-04 (live page (curl 200; /terms/ redirects here). Terms 'Last Modified: February 21, 2024')
- Scraping: **silent**. None found: the Terms of Use (sections 1-20, read in full) contain no clause on robots, spiders, scrapers, crawling, automated means or text/data mining.
- Full-text storage: **unclear**. "You shall not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store or transmit any of our material, except for your personal, non-public, and non-commercial use."
- Excerpts: **unclear**. "You shall not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store or transmit any of our material, except for your personal, non-public, and non-commercial use."
- Other clauses: Section 13 also: "You shall not access or use for any commercial purposes any part of our Sites or Services." and a 507-char sentence: "Except as expressly provided above, no portion of our Sites or Services, their contents ... may be reproduced, altered, removed, transmitted, published or distributed ... without the prior written permission of AdvisorHUB." Section 2: "The Sites or Services are offered only for your use, and not for the use or benefit of any third party." No AI / text-and-data-mining clause. No separate RSS-feed terms; the feed's channel says <copyright>All Rights Reserved.</copyright>. Governing law: Ohio, with exclusive jurisdiction in Ohio courts (s.16). Consent contact (s.1): AdvisorHub, LLC, 1707 Post Oak Blvd. #484, Houston, TX 77056, tel. (703) 282-1597. No reprints/permissions page found.
- Text owner: AdvisorHUB LLC. Footer of terms: "© 2024 AdvisorHUB LLC. All rights reserved." Terms s.13 says the contents "are owned by AdvisorHUB, its licensors or other providers of such material".
- Access / cost: free; free (no login or paywall seen; full sample article served to anonymous curl 2026-10-04; only a free newsletter signup) (<https://www.advisorhub.com/merrill-agrees-to-39m-settlement-in-cash-sweep-suit/>)
- robots.txt: robots.txt (Yoast block): 'User-agent: *' with empty 'Disallow:', so it allows all paths we would fetch (/{slug}/, /feed/, /tag/merrill-lynch/, sitemaps); Sitemap https://www.advisorhub.com/sitemap_index.xml. No AI or content-signal lines (2026-10-04).
- Questions:
  1. AdvisorHub terms allow reproducing, downloading or storing material only 'for your personal, non-public, and non-commercial use' and forbid access 'for any commercial purposes': does a WashU student prototype built for Edward Jones's Chief Strategy Office qualify, or must we get AdvisorHub's written permission ((703) 282-1597) before storing full text in Postgres/Box?
  2. AdvisorHub: does showing short attributed quotes to a handful of project users count as 'non-public' personal use, or does the clause that 'no portion ... may be reproduced ... without the prior written permission of AdvisorHUB' require consent first?
  3. AdvisorHub's RSS feed (https://www.advisorhub.com/feed/) carries full article HTML in content:encoded and has no separate feed terms: is ingesting from the feed treated any differently from fetching the pages?
  4. AdvisorHub terms say nothing about AI: may stored AdvisorHub passages be sent to a third-party LLM API (Claude/OpenAI) to produce answers?

#### T-32 investmentnews.com (InvestmentNews (KM Business Information US, Inc. / Key Media))

Rows: `T4-INVESTMENTNEWS`

- Terms: <https://www.investmentnews.com/general-terms-conditions-for-digital-subscription>, read 2026-10-04 (live page (curl 200). The footer link 'Terms & Conditions' goes to https://www.keymedia.com/terms-and-conditions (also read live). That page is Key Media's advertiser/event Insertion Order agreement and has no reader-use clauses)
- Scraping: **silent**. None found: the Digital Subscription terms and Key Media's T&C (advertiser Insertion Order agreement) contain no clause on robots, spiders, scrapers, crawling, automated means or data mining.
- Full-text storage: **forbidden**. "Use of editorial content without permission is strictly prohibited."
- Excerpts: **forbidden**. "Use of editorial content without permission is strictly prohibited."
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The prohibition is a site-wide footer notice on every page (homepage, article and terms pages), next to "Copyright © 2026 KM Business Information US, Inc." and followed by "All rights reserved". It is 'without permission', so permission can be requested. Whether the notice reaches short attributed quotes (fair use) is for the ADR-000 owners. Subscription terms: "The login details associated with your subscription must not be shared with any other person". The reader-facing terms have no AI/TDM clause and no governing-law clause. Key Media's T&C (advertisers) set the governing law as 'the location of the Key Media entity as detailed in the Insertion Order'. No reprints/permissions page: /reprints, /permissions, /copyright and /terms-of-use all 404. Contacts: customerservice@investmentnews.com (decoded from the Cloudflare-obfuscated address on the terms page), /contact-us, /customer-support.
- Text owner: KM Business Information US, Inc. (Key Media), per footer "Copyright © 2026 KM Business Information US, Inc."
- Access / cost: metered; $19.99 per month (footer promo: 'Get unlimited access to InvestmentNews' / 'Subscribe for just $19.99 per month.') (<https://www.investmentnews.com/general-terms-conditions-for-digital-subscription>)
- robots.txt: robots.txt: 'User-agent: *' disallows only /cdn-cgi/ and *__hstc=, so it allows /{section}/{slug}/{id} articles, /companies/{slug}/{id}, /rss and sitemap.xml. A separate group for Claude-User, ChatGPT-User and Perplexity-User has an empty 'Disallow:' (allow all). Sitemap https://www.investmentnews.com/sitemap.xml lists only 55 section pages, no articles (2026-10-04).
- Questions:
  1. InvestmentNews footer says 'Use of editorial content without permission is strictly prohibited.' and its 'Terms & Conditions' link is only Key Media's advertiser agreement: do we ask KM Business Information US (customerservice@investmentnews.com or /contact-us) for written permission to store full text and show quotes, or keep InvestmentNews as metadata + link only?
  2. InvestmentNews: does its blanket 'without permission' notice reach short attributed quotes shown to a handful of internal users, or do the ADR-000 owners treat those as fair use?
  3. InvestmentNews sells 'unlimited access' at $19.99/month, yet the full article text came back to an anonymous script in static HTML: may the prototype fetch it that way, or must ingestion stay within a paid subscription or the free meter?
  4. InvestmentNews robots.txt explicitly admits Claude-User/ChatGPT-User: do we treat that as a technical signal only (not permission), as ADR-000 assumes?

#### T-33 financial-planning.com (Arizent (SourceMedia LLC d/b/a Arizent): Financial Planning. Same publisher as American Banker, with shared terms)

Rows: `T4-FINANCIALPLANNING`

- Terms: <https://www.arizent.com/news/arizent-subscription-agreement>, read 2026-10-04 (live page (curl 200). It is the only terms document in the FP footer ('Subscription Agreement'). Also read the footer's 'Content Licensing/Reprints' page, https://info.wrightsmedia.com/arizent-licensing-and-reprints)
- Scraping: **silent**. None found: the Arizent Subscription Agreement has no clause on robots, spiders, scrapers, crawling, automated means or data mining (s.9 covers only security: 'any attempt to avoid user authentication or security of any host, network or account').
- Full-text storage: **forbidden**. "You may not reproduce, retransmit, distribute, store in a retrieval device, disseminate, sell, publish, broadcast or circulate the information obtained through the Service to anyone, without the express written consent of SourceMedia LLC d/b/a Arizent."
- Excerpts: **forbidden**. "You may not reproduce, retransmit, distribute, store in a retrieval device, disseminate, sell, publish, broadcast or circulate the information obtained through the Service to anyone, without the express written consent of SourceMedia LLC d/b/a Arizent."
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The prohibitions are 'without the express written consent', so consent can be requested. s.6: "You may display and print information obtained through the Service solely for your own personal, non-commercial use." s.8 says the same for third-party content ("store in a retrievable device"). s.10 RESTRICTIONS (enterprise/licensed product) limits use to Nominated Users "for the purpose of enabling the subscriber to carry on its business in the normal course". It adds: "The Licensed Product may not be reproduced, copied or resold in any format." and "Nominated Users are not permitted to store copies of the licensed product or parts thereof on any computer, PDA or network where they can be accessed by employees who are not nominated users." No AI/TDM clause. Governing law: New York, with exclusive jurisdiction in New York courts (s.13). Consent and licensing: Wright's Media offers 'Editorial Content Permissions' and 'Licensed Use of Copyrighted Material' (no prices published); Arizent customer service is help@arizent.com, 212-803-8500. Every article carries 'For reprint and licensing requests for this article, click here.' linking to Wright's Media.
- Text owner: SourceMedia LLC d/b/a Arizent. Footer: "© 2026 Arizent. All rights reserved." s.7: "the Licensed Product and the Content are and will remain the property of SourceMedia LLC d/b/a Arizent".
- Access / cost: metered; not published (the /subscribe page has no price in its HTML; offers load through the Piano script. It mentions enterprise, student/educator and gift pricing without amounts) (<https://www.financial-planning.com/subscribe>)
- robots.txt: robots.txt: 'User-agent: *' disallows /cms/, /_debug/, /search and /auth/, and allows /authors/. Paths we fetch (/news/{slug}, /list/, /opinion/, /feed?rss=true, sitemaps) are not disallowed and no crawl-delay applies to *. Amazonbot and Baiduspider/2.0 are disallowed from /; CCBot/2.0 is allowed with crawl-delay 10. Sitemaps: /sitemap.xml, /weekly-sitemap.xml, /news-sitemap.xml (2026-10-04).
- Questions:
  1. Arizent (Financial Planning and American Banker) forbids storing content 'in a retrieval device' or circulating it 'to anyone, without the express written consent of SourceMedia LLC d/b/a Arizent': do we request consent through Wright's Media (Arizent licensing/reprints) or help@arizent.com, or keep FP/AB as metadata + excerpt-free link only?
  2. Arizent's only linked terms are a Subscription Agreement between Arizent and the 'Subscriber': does it bind a script fetching metered FP/AB articles without an account, and if so does 'solely for your own personal, non-commercial use' cover the prototype?
  3. Does Edward Jones already hold an Arizent enterprise licence (s.10: Nominated Users, use 'to carry on its business in the normal course') that could cover the CSO use? If not, are the 'Nominated Users' store-copy limits compatible with a shared Postgres/Box store?
  4. FP/AB pages are metered by Piano (JSON-LD isAccessibleForFree:false, .inline-gate), but the static HTML holds the full text: is reading that HTML by script acceptable, or does it count as getting around the meter?
  5. Arizent terms say nothing about AI: may FP/AB passages be sent to a third-party LLM API for answers if consent is obtained only for internal storage?

#### T-34 americanbanker.com (Arizent (SourceMedia LLC d/b/a Arizent): American Banker. Same publisher as Financial Planning, with shared terms)

Rows: `T4-AMERICANBANKER`

- Terms: <https://www.arizent.com/news/arizent-subscription-agreement>, read 2026-10-04 (live page (curl 200). It is the same document linked as 'Subscription Agreement' in the American Banker footer; that footer also links Wright's Media 'Content Licensing/Reprints')
- Scraping: **silent**. None found: the Arizent Subscription Agreement has no clause on robots, spiders, scrapers, crawling, automated means or data mining (s.9 covers only security: 'any attempt to avoid user authentication or security of any host, network or account').
- Full-text storage: **forbidden**. "You may not reproduce, retransmit, distribute, store in a retrieval device, disseminate, sell, publish, broadcast or circulate the information obtained through the Service to anyone, without the express written consent of SourceMedia LLC d/b/a Arizent."
- Excerpts: **forbidden**. "You may not reproduce, retransmit, distribute, store in a retrieval device, disseminate, sell, publish, broadcast or circulate the information obtained through the Service to anyone, without the express written consent of SourceMedia LLC d/b/a Arizent."
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: Identical terms to Financial Planning, because one Arizent agreement covers both. Consent can be requested: Wright's Media https://info.wrightsmedia.com/arizent-licensing-and-reprints ('Editorial Content Permissions', 'Licensed Use of Copyrighted Material') or help@arizent.com, 212-803-8500. s.6 allows display and print 'solely for your own personal, non-commercial use'. s.10 enterprise restrictions apply: Nominated Users, 'carry on its business in the normal course', no stored copies reachable by non-nominated users. s.4/s.5 add a no-refund policy for American Banker Research. No AI/TDM clause. Governing law: New York (s.13). The AB sitemap also lists third-party /press-release/ pages, which are not Arizent editorial.
- Text owner: SourceMedia LLC d/b/a Arizent. Footer reads "© 2026 Arizent. All rights reserved." Some /press-release/ pages are third-party releases.
- Access / cost: metered; not published (the /subscribe page has no price in its HTML; offers load through the Piano script) (<https://www.americanbanker.com/subscribe>)
- robots.txt: robots.txt: 'User-agent: *' disallows /cms/, /_debug/, /search and /auth/, and allows /authors/. /news/{slug}, /feed?rss=true and sitemaps are not disallowed. Amazonbot and Baiduspider/2.0 are disallowed from /. Otherwise it matches financial-planning.com plus Screaming Frog and lumar groups. Sitemaps: /sitemap.xml, /news-sitemap.xml, /weekly-sitemap.xml (2026-10-04).
- Questions:
  1. American Banker shares Financial Planning's Arizent Subscription Agreement ('store in a retrieval device ... without the express written consent'): can a single Arizent consent request (via Wright's Media or help@arizent.com) cover both titles?
  2. American Banker is metered (Piano meter, isAccessibleForFree:false): without consent or a licence, is AB limited to RSS metadata (title, summary, link, date)?

#### T-35 thinkadvisor.com (ThinkAdvisor (Arc network, LLC))

Rows: `T4-THINKADVISOR`

- Terms: <https://www.arc-network.com/policies/us-terms-of-use/>, read 2026-10-04 (terms read on the live page (arc-network.com, curl 200). thinkadvisor.com returns a Cloudflare 403 challenge to scripts, so its footer link ('Terms of Service' -> arc-network.com US terms) was confirmed from a Wayback capture of the homepage dated 2026-10-04 (20261004140032))
- Scraping: **silent**. None found: the Arc US Terms of Use contain no clause on robots, spiders, scrapers, crawling, automated means or data mining. (robots.txt carries Cloudflare content signals; see robots_summary.)
- Full-text storage: **unclear**. "As a visitor to this site you may copy or transmit material on this site for your own private, non-commercial purposes only and shall not otherwise copy or transmit the site material."
- Excerpts: **unclear**. "No part of this website may be distributed, used, adapted, reproduced, translated or copied for any commercial purpose whatsoever without prior written permission from Arc network, LLC."
- Other clauses: Every article page carries 'NOT FOR REPRINT' and "© Arc, All Rights Reserved. Request academic re-use from www.copyright.com. All other uses, submit a request to TMSalesOperations@arc-network.com." (address decoded from Cloudflare email obfuscation; seen in a Wayback capture of the sample article, 20260911075145). Also links /asset-and-logo-licensing/. robots.txt preamble (Wayback 2026-05-01): "As a condition of accessing this website, you agree to abide by the following content signals". It sets search=yes and ai-train=no and leaves ai-input ("retrieval augmented generation, grounding") unset, which it says "neither grants nor restricts permission". It also says "ANY RESTRICTIONS EXPRESSED VIA CONTENT SIGNALS ARE EXPRESS RESERVATIONS OF RIGHTS UNDER ARTICLE 4 OF THE EUROPEAN UNION DIRECTIVE 2019/790". Governing law: USA, with exclusive jurisdiction in US courts. Arc's terms include an indemnity for 'unauthorized use of material obtained via this website'.
- Text owner: Arc network, LLC (site footer 'Copyright © 2026 Arc.'). Terms: "The copyright and all other rights in all of the material on this site are owned by Arc network, LLC or its related companies". arc-network.com/brands lists ThinkAdvisor as an Arc brand.
- Access / cost: free-registration; not published as far as could be verified: the subscribe page returns a Cloudflare 403. A search-engine summary of https://www.thinkadvisor.com/subscribe/?pk=TAHOME cites PRO at $60/month or $595/year plus a free account option (TODO-verify in a browser) (<https://www.thinkadvisor.com/subscribe/?pk=TAHOME>)
- robots.txt: Live robots.txt returns a Cloudflare managed-challenge 403 to curl (2026-10-04). Wayback capture 2026-05-01 (latest capture): 'User-agent: *' has 'Content-Signal: search=yes,ai-train=no' and 'Allow: /'. Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot, CloudflareBrowserRenderingCrawler, Google-Extended, GPTBot and meta-externalagent are disallowed from /. A second '*' group sets Crawl-delay 1 and disallows /*/?printer-friendly. Article paths /{yyyy}/{mm}/{dd}/{slug}/ are allowed by robots but blocked in practice by the bot challenge.
- Questions:
  1. ThinkAdvisor (Arc network, LLC) terms allow copying only 'for your own private, non-commercial purposes': does the WashU prototype for Edward Jones's CSO qualify, or must we ask Arc for written permission?
  2. ThinkAdvisor articles say 'Request academic re-use from www.copyright.com': should the WashU team request academic re-use through the Copyright Clearance Center, or send the request to TMSalesOperations@arc-network.com, given the end user is Edward Jones's strategy office?
  3. ThinkAdvisor's robots.txt makes content signals 'a condition of accessing this website' (search=yes, ai-train=no, ai-input not set): does feeding stored ThinkAdvisor passages to an LLM to answer questions (ai-input / RAG) need Arc's explicit permission?
  4. ThinkAdvisor blocks scripts with a Cloudflare challenge and gates article bodies (.paywall-content): do we limit ThinkAdvisor to metadata via T4-BINGNEWS and manual reading, or seek permission for automated access?

#### T-36 riabiz.com (RIABiz Inc.)

Rows: `T4-RIABIZ`

- Terms: <not found (no terms of use linked anywhere on the site; /terms, /terms-of-use, /terms-of-service, /tos, /legal, /copyright all return 404 on 2026-10-04; only a TermsFeed privacy policy exists: https://www.termsfeed.com/live/9ef93ae9-a78b-4f30-9d1b-a93802e040d2)>, read 2026-10-04 (not found)
- Scraping: **unclear**. "Not for commercial use. The following is summary of recent RIABiz articles for your aggergating convenience." (<https://api.riabiz.com/rss>)
- Full-text storage: **silent**. "Copyright © 2009- 2026 RIABiz Inc. All rights reserved." (<https://riabiz.com/>)
- Excerpts: **silent**. "Copyright © 2009- 2026 RIABiz Inc. All rights reserved." (<https://riabiz.com/>)
- Other clauses: No terms of use exist, so article pages have no clause on automated access, storage or quoting. The site's only usage statement is the RSS channel description (https://riabiz.com/rss redirects to https://api.riabiz.com/rss): "Not for commercial use. The following is summary of recent RIABiz articles for your aggergating convenience." That allows feed aggregation but only for non-commercial use, which is why scraping is marked unclear rather than silent. The footer reserves all rights. robots.txt blocks GPTBot, ClaudeBot, CCBot, Applebot-Extended, meta-externalagent and Bytespider from the whole site, which signals a stance against AI crawling but is not a term. The privacy policy (TermsFeed, last updated October 26, 2021) names the company as RIABiz Inc., 90 Throckmorton Avenue, Suite 28, Mill Valley, CA 94941, under California law. Permission contacts from /contact: brooke@riabiz.com (editorial) and frank@riabiz.com (CEO).
- Text owner: RIABiz Inc. (footer: "Copyright © 2009- 2026 RIABiz Inc. All rights reserved."). Staff-written journalism; RSS channel <copyright>: "Copyright (c) 2026, RIABiz".
- Access / cost: free; free (<https://riabiz.com/a/2026/7/22/rick-wurster-discloses-sweeping-schwab-plan-to-flip-up-to-31-of-its-self-directed-book-of-business-into-its-ria-schwab-wealth-advisory-calling-house-retail-clients-unmatched-conversion-funnel>)
- robots.txt: https://riabiz.com/robots.txt (2026-10-04): User-agent * Allow: / and Disallow: /admin, so /a/{yyyy}/{m}/{d}/{slug}, /archives/, /tags/ and /rss are allowed. GPTBot, ClaudeBot, Applebot-Extended, CCBot, meta-externalagent and Bytespider are each disallowed from /. Lists sitemaps such as /articles-sitemap.xml. https://api.riabiz.com/robots.txt (the RSS host) returns a server-error HTML page, not a robots file.
- Questions:
  1. RIABiz publishes no terms of use, only a copyright notice ('All rights reserved'). Since nothing permits or forbids it, may the prototype fetch and store full RIABiz articles in our private Postgres and Box and show short excerpts, or should we first ask RIABiz (frank@riabiz.com / brooke@riabiz.com) for written permission?
  2. The RIABiz RSS feed is labelled 'Not for commercial use ... for your aggergating convenience': does a WashU prototype built for Edward Jones's Chief Strategy Office count as commercial use, and may we poll the feed?
  3. RIABiz robots.txt blocks AI crawlers (GPTBot, ClaudeBot, CCBot, etc.) but allows generic agents. Is that an objection to AI use that we must respect, even though our script is a plain fetcher feeding a Q&A tool?

#### T-37 wealthmanagement.com (WealthManagement.com (Informa Connect, a division of Informa PLC))

Rows: `T4-WEALTHMANAGEMENT`

- Terms: <https://www.informa.com/generic-content/terms--conditions/>, read 2026-10-04 (live page)
- Scraping: **silent**. "You agree not to damage, interfere with or disrupt access to the Site or do anything which may interrupt or impair its functionality."
- Full-text storage: **forbidden**. "Subject to this licence, no part of the Site may be reproduced or stored in any other website or included in any public or private electronic retrieval system or service without our prior written permission."
- Excerpts: **unclear**. "You are permitted to print and download extracts from the Site for your own use on the following basis: (a) no documents or related graphics on the Site are modified in any way; (b) no graphics on the Site are used separately from the corresponding text;"
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: Scope problem: the WealthManagement.com footer link labelled 'Terms' goes to Informa's group terms, but that text says it covers "our website www.informa.com ( our “Site”)". Whether these terms bind wealthmanagement.com is therefore open. Personal-use limit: "You agree not to adapt, alter or create a derivative work from any of the material contained in this Site or use it for any other purpose than for personal, non-commercial use." Extracts licence condition: "(c) our copyright and trade mark notices and this permission notice appear in all copies." On breach you "must immediately destroy any downloaded or printed extracts". The page has no robots, scraper, crawling, TDM or AI clause, so scraping is silent; the quoted clause is the closest one and is about interference, not automated access. Monitoring clause: "We reserve the right to monitor and track your visits to the Site." Governing law: England and Wales. Consent can be requested: the footer 'Reprints' link goes to Wright's Media (https://info.wrightsmedia.com/informa-licensing-reprints-request, informa@wrightsmedia.com) for licensing and permissions. robots.txt disallows named AI crawlers (Anthropic-ai, ClaudeBot, Claude-Web, GPTBot, CCBot, etc.) from the whole site. Article JSON-LD carries "isAccessibleForFree":"True".
- Text owner: Informa PLC group. Footer: "This site is operated by a business or businesses owned by Informa PLC and all copyright resides with them." and "Copyright © 2026 Informa Connect Limited." Mostly staff-written; some items are sponsored content.
- Access / cost: free; free (<https://www.wealthmanagement.com/alternative-investments/raymond-james-launches-public-private-model-portfolios-for-hnw-clients>)
- robots.txt: https://www.wealthmanagement.com/robots.txt (2026-10-04): User-agent * disallows /search, /recipe-portal/search, /api/health, /cdn-cgi/, /live-preview/ and /my-purchases/. Article paths (/{section}/{slug}), /rss.xml and the sitemaps are allowed. One group of named AI and other bots (Amazonbot, Anthropic-ai, Applebot-Extended, Bytespider, CCBot, ClaudeBot, Claude-Web, Cohere-ai, Diffbot, GPTBot, Meta-ExternalAgent, etc.) is disallowed from /.
- Questions:
  1. The WealthManagement.com 'Terms' link goes to Informa's group terms, whose text covers 'www.informa.com'. Do these terms govern wealthmanagement.com, or should we ask Informa which terms apply?
  2. Informa's terms forbid storing any part of the site 'in any public or private electronic retrieval system or service without our prior written permission'. Do we request permission (via Wright's Media, informa@wrightsmedia.com) or keep WealthManagement.com as metadata + excerpt + link only?
  3. Informa's terms allow extracts 'for your own use' and use only 'for personal, non-commercial use'. Does showing short WealthManagement.com excerpts to the WashU team and the stand-in CSO for Edward Jones qualify?
  4. WealthManagement.com robots.txt blocks AI crawlers (Anthropic-ai, ClaudeBot, GPTBot, etc.). Does that signal an objection that applies to our AI-assisted Q&A prototype even though the written terms have no AI clause?

#### T-38 barrons.com (Dow Jones & Company, Inc. (Barron's, including Barron's Advisor))

Rows: `T4-BARRONS`, `T4-BARRONSADVISOR`

- Terms: <https://www.dowjones.com/terms-of-use/>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "You shall not access, view, retrieve, refresh, reload, scrape, text or data mine, index, process, store, harvest, or otherwise ingest the Services or any Content, whether directly or through an intermediary, using any automated means, webcrawler, spider, script"
- Full-text storage: **forbidden**. "You may not otherwise download, print, store or provide others with access to such articles except through the share features we have included in a Service or with a license obtained through the Dow Jones Reprints website at djreprints.com."
- Excerpts: **forbidden**. "Unless you have our written consent, you may not use, sell, publish, distribute, retransmit or otherwise provide access to the Content received through the Services to anyone, including, if applicable, your fellow students, coworkers, or employees"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: Terms of Use Effective Date: June 30, 2026. They name barrons.com explicitly and apply "with or without an active subscription or registration". The scraping clause in 9.4.1 continues: "...without our prior written consent", so consent can be requested. 9.1: "The Services are for your individual, personal and non-commercial use only." and "Thus, you may not access or use the Content, including without limitation, any Content made available through one of our RSS feeds, in any commercial product or service, without our express written consent." 9.3 personal storage only: "You may occasionally download, print and/or store articles from a Service for your individual, personal, and non-commercial use..." Also 9.3: "you may not use articles you have downloaded, printed or stored to develop or operate an automated trading system, or for text or data mining any information or content (including associated metadata)." 9.4.2 AI: "you may not harvest, ingest, use or incorporate any Content available through a Service for any form of artificial intelligence (“AI”), including in any generative or other form of AI for training or grounding purposes, unless you receive our prior written permission." Our retrieval-and-answer tool is AI grounding. 9.4.2 on robots: "your rights are not expanded, nor are any prohibitions modified or limited, by our use or configuration of exclusionary protocols (e.g., the Robots Exclusion Protocol as implemented through robots.txt files)." 9.4.3: permitted bots must identify themselves truthfully in the User-Agent. 9.4.5: "You are prohibited from performing text and data mining activities under Art. 4 of the EU Directive on Copyright in the Digital Single Market or similar statutes in other jurisdictions." Content is defined to include "headlines, article summaries", so even headline metadata counts as Content. Governing law: New York (section 17); binding arbitration with class-action waiver (section 15). Consent contacts: copyright@dowjones.com (robots.txt header) and djreprints.com (licences).
- Text owner: Dow Jones & Company, Inc. Terms 9.3: "The Content is our property or the property of our advertisers and licensors and is protected by copyright and other intellectual property laws." This is licensed, paywalled content.
- Access / cost: paywall; Individual digital subscription, 'Unlimited Barron’s Standard Digital Access': list '$5/week', intro offer '$2/week for 1 year Billed as $8 every 4 weeks for 1 year'. Bundles: '$2.25/week' (+MarketWatch) and '$3/week' (WSJ, MarketWatch, Barron's, IBD). An individual subscription is limited by terms 9.1 to individual, personal, non-commercial use, (whether that covers this project is question 4 and T-01). Corporate and licensing prices are not published. (<https://www.barrons.com/subscribe/ (one request on 2026-10-04, reached via redirect from https://store.barrons.com/shop/us/us/barrons/)>)
- robots.txt: https://www.barrons.com/robots.txt (2026-10-04): User-agent * Disallow: /, which covers every path we would fetch (/articles/, /advisor/, /advisor/articles/, the sitemaps). Only a named list of search, social, ad and SEO bots gets Allow: /, with exclusions for /search?*, /auth/, /public/, /documents/, /market-brief/ and others. Header comment, line breaks removed: "NOTICE: Collection of content and other data on https://www.barrons.com/ through automated means is prohibited unless you have express written permission from Dow Jones & Company, Inc." It gives copyright@dowjones.com for permission requests. Article and homepage GETs from curl return 401 (DataDome).
- Questions:
  1. Dow Jones terms (barrons.com) forbid automated access, storage, text/data mining and use of Content for AI 'training or grounding' without prior written consent. Do we ask copyright@dowjones.com for consent, or take both Barron's rows (T4-BARRONS, T4-BARRONSADVISOR) out of automated ingestion and treat them like tier-1 licensed sources blocked by ADR-000?
  2. Dow Jones terms 9.3 bar providing Content 'to anyone, including ... your fellow students, coworkers, or employees' without written consent, and they define Content to include headlines and article summaries. May we store even headline + date + link metadata for Barron's items, or show short quotes to the team?
  3. Does WashU's library access to Barron's (e.g. Factiva / ProQuest, TODO-verify) come with terms that allow storing or excerpting Barron's articles in a project database, or is it also limited to individual reading?
  4. An individual Barron's subscription is limited to 'individual, personal and non-commercial use' (terms 9.1). Does a student project for Edward Jones's Chief Strategy Office fall inside or outside that, and does anyone on the team hold a corporate Dow Jones licence?

#### T-39 citywire.com (Citywire Financial Publishers Ltd (Citywire RIA, US edition))

Rows: `T4-CITYWIRERIA`

- Terms: <https://citywire.com/ria/terms>, read 2026-10-04 (Wayback capture 2026-02-21 (https://web.archive.org/web/20260221123632/https://citywire.com/ria/terms); the live site serves scripts an Incapsula challenge)
- Scraping: **forbidden**. "perform any automated use of our Site, such as, but not limited to, using robots, spiders, scripts, service, software or manual or automatic device, tool or process designed to data mine or scrape content to create Contributions, to extract any of the content of our Site" (<https://web.archive.org/web/20260221123632/https://citywire.com/ria/terms>)
- Full-text storage: **forbidden**. "(xiii) collect information from our Site and incorporate it into your own database or products;" (<https://web.archive.org/web/20260221123632/https://citywire.com/ria/terms>)
- Excerpts: **forbidden**. "you must not copy, reproduce, modify, create derivative works from, transmit, distribute, publish, summarize, adapt, paraphrase or otherwise publicly display any Content or any portion of the Site or App without the specific written consent of a director of Citywire." (<https://web.archive.org/web/20260221123632/https://citywire.com/ria/terms>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The terms say: "This Terms & Conditions were last reviewed and updated in October 2025." Consent can be requested: excerpts need "the specific written consent of a director of Citywire", and the robots.txt legal notice gives content-licensing@citywire.com. Clause 8.1(ix): "use our Site (or any of the Content) for the purpose of building a database or to use this for your own commercial exploitation ... without obtaining the written approval of Citywire". 8.1(viii): using the service as research for a company's subscription-based service needs a written licence. 8.1(x) bars use "for any other competitive purposes". 8.1(xv) bars any ML/AI training, tuning or testing. 8.1(xvi): "employ Artificial Intelligence tools or models to produce images, text, or any other material, output, or derivative works that originate from or making use of Citywire’s Site or content." 8.1(vii) bars violating robot exclusion headers. 5.1 extends to "inclusion in services which summarize articles". Clause 6 licenses only 'Feed Content' (headlines and links) for display on your website, with a required attribution notice, a link back, and no commercialisation. 2.3: "You confirm that you are acting in a professional business capacity in entering into these Terms." 3.1 refers to an annual 'Subscription Fee' (amount not published) with 5% automatic increase. Governing law: New York, with arbitration. robots.txt legal notice, line breaks removed: "Any other uses of our content or data are not permitted, including but not limited to: machine learning or artificial intelligence purposes..."
- Text owner: Citywire Financial Publishers Ltd. Terms 5.3: "Unless otherwise noted, the Site, the App, and all Content are © Citywire Financial Publishers Ltd 2019. All rights not expressly granted herein are reserved." Footer: "© 1999 - 2026 citywire.com. All Rights Reserved."
- Access / cost: unknown; not published (terms 3.1 mention an annual 'Subscription Fee' but no amount) (<https://web.archive.org/web/20260221123632/https://citywire.com/ria/terms>)
- robots.txt: https://citywire.com/robots.txt (2026-10-04; robots.txt itself is served to curl): User-agent * disallows /search, /sign-in, /register, /redirect, /GetCommentsCount, /data-api and the returns/league tables. /ria/news/ article paths are allowed. A final * group declares 'Content-Signal: search=yes, ai-input=no, ai-train=no' with Allow: /. ClaudeBot, anthropic-ai, Claude-Web, GPTBot, Google-Extended, CCBot and others are disallowed from /. Claude-User, Claude-SearchBot, ChatGPT-User and PerplexityBot are allowed */news/* only. The header legal notice says any use beyond the Terms and Copyright Policy is not permitted, including ML/AI purposes and commercial purposes. Pages and the RSS feed return an Incapsula challenge to curl, so robots aside, the site blocks scripts.
- Questions:
  1. Citywire terms forbid automated scraping, incorporating content 'into your own database or products', copying or summarizing without a director's written consent, and using AI tools to produce output from Citywire content. Do we request a licence (content-licensing@citywire.com) or drop Citywire RIA from ingestion and keep only manually noted links?
  2. Citywire terms 8.1(x) bar use of the site 'for any other competitive purposes'. Does an Edward Jones competitive-intelligence prototype fall under that clause even if licensed otherwise?
  3. Citywire robots.txt declares 'Content-Signal: ai-input=no'. Does that rule out using Citywire text as input to the prototype's answer step even with stored excerpts?
  4. Citywire terms were read only through a Wayback capture of 2026-02-21 because the live site blocks scripts. Can someone confirm in a browser that https://citywire.com/ria/terms is unchanged, and whether Citywire RIA articles need free registration or a paid subscription?

#### T-40 planadviser.com (PLANADVISER (Asset International, Inc., part of ISS STOXX / ISS Media))

Rows: `T4-PLANADVISER`

- Terms: <https://www.iss-stoxx.com/legal/terms-of-use/>, read 2026-10-04 (live page (PLANADVISER footer link 'Privacy (including cookies), Social Media & Legal' -> https://www.issgovernance.com/privacy-legal/ -> redirects to https://www.iss-stoxx.com/legal/, which links 'Website Terms of Use'); also read https://www.planadviser.com/pa-rss/ (RSS terms) and https://www.planadviser.com/reprints-fee-schedule/)
- Scraping: **forbidden**. "You may not use any system, device or software to extract data from the website."
- Full-text storage: **forbidden**. "You may not modify, copy, distribute, transmit, display, perform, reproduce, publish, license, frame, decompile, recompile, reverse engineer, upload to, create derivative works from, transfer, or otherwise use or exploit in whole or in part any information"
- Excerpts: **unclear**. "NOTE: There is no cost associated with promoting an article from PLANADVISER.com on your website or social profile provided a link along with a two- or three-line summary or excerpt from the article is included in the promotion." (<https://www.planadviser.com/reprints-fee-schedule/>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: Scope: "By accessing this website located at iss-stoxx.com and any other domains operated by Institutional Shareholder Services Inc. and/or its subsidiaries (collectively, “ISS”), you are indicating that you have read, acknowledge and agree to be bound by these Terms of Use." Effective January 15, 2026. The storage clause continues: "...obtained from this website, except for the purposes expressly provided herein, without ISS’ prior written approval", so consent can be requested. On termination you must "promptly destroy all materials obtained via the website and any copies thereof". RSS terms (https://www.planadviser.com/pa-rss/): "PLANADVISER’s RSS Feeds are provided for individual use to view the latest headlines and news that affects the benefits industry." Also: "Without written consent, you may not: modify, translate, copy, publish, sell, upload, post, transmit, distribute or otherwise disseminate the RSS Feeds or otherwise transfer rights to the PLANADVISER RSS Feed(s). The feeds are not to be used for commercial purposes." And: "The headlines are copyrighted by Institutional Shareholder Services Inc. All rights reserved. No production or redistribution without prior authorization." RSS permission contact: Advertise@issmediasolutions.com. Reprints contact: reprints@issmediasolutions.com; the published 2023 fee schedule lists "Up to 650-word PDF without art/image: $1,325". The terms have no AI or TDM clause. Governing law: New York; venue Montgomery County, Maryland; one-year claim limit.
- Text owner: Asset International, Inc. (ISS STOXX group). PLANADVISER footer: "Copyright ©2026 Asset International, Inc. All rights reserved. No reproduction without prior authorizations." The RSS page says headlines are copyrighted by Institutional Shareholder Services Inc.
- Access / cost: free; free to read (full article text served without login). Reprints are priced separately: 'Up to 650-word PDF without art/image: $1,325' (2023 Reprints Fee Schedule). (<https://www.planadviser.com/reprints-fee-schedule/>)
- robots.txt: https://www.planadviser.com/robots.txt (2026-10-04): User-Agent * disallows only /readme.html; Googlebot allow /. Article paths (/{slug}/), /tag/, /feed/ and /news/{section}/feed/ are all allowed. Sitemap: /sitemap_index.xml. No AI-crawler blocks.
- Questions:
  1. PLANADVISER is governed by ISS STOXX terms, which say 'You may not use any system, device or software to extract data from the website' and forbid copying or reproducing 'in whole or in part' without ISS's prior written approval. Do we request approval (reprints@issmediasolutions.com) or store PLANADVISER as metadata + excerpt + link only?
  2. PLANADVISER's RSS terms limit feeds to 'individual use' and say they 'are not to be used for commercial purposes'. May the prototype poll https://www.planadviser.com/feed/ for headlines and links, and is a project for Edward Jones commercial?
  3. PLANADVISER's reprints page allows a free 'two- or three-line summary or excerpt' with a link when 'promoting an article ... on your website or social profile'. Does showing two- or three-line excerpts with links inside a private Q&A tool fit that permission?

#### T-41 fa-mag.com (Financial Advisor magazine (Charter Financial Publishing Network))

Rows: `T4-FAMAG`

- Terms: <https://www.fa-mag.com/terms>, read 2026-10-04 (Wayback capture 2026-08-13 (live /terms returns 403 Cloudflare challenge to curl and WebFetch on 2026-10-04))
- Scraping: **forbidden**. "Create abstracts from, scrape or display headlines from Fa-mag.com for use on another web site or service; or" (<https://web.archive.org/web/20260813232258/https://www.fa-mag.com/terms>)
- Full-text storage: **forbidden**. "Store, post or otherwise archive the articles or other materials from Fa-mag.com on a personal computer, local or wide area networks, online services, electronic bulletin boards or forums, World Wide Web sites or any other server that is Internet-enabled;" (<https://web.archive.org/web/20260813232258/https://www.fa-mag.com/terms>)
- Excerpts: **forbidden**. "You may, on an occasional basis, include insubstantial portions of information from Fa-mag.com in memoranda, reports and presentations, but only if such memoranda, reports and presentations are distributed in paper form, for a noncommercial purpose, to a limited number of individuals." (<https://web.archive.org/web/20260813232258/https://www.fa-mag.com/terms>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: All three bans sit under the lead-in 'Except as provided below without the prior written consent of Financial Advisor, you agree not to:'. Because they apply only without prior written consent, consent can be requested. Personal use: 'Information received through Fa-mag.com may be displayed, reformatted and printed for your personal, noncommercial use only.' Internal sharing: 'Reproduce, retransmit, distribute, sell, publicly display, publish, post to newsgroups or electronic bulletin boards, or broadcast the information received through Fa-mag.com to anyone, including to others in the same company or organization;'. The paper-only excerpt exception requires the line 'Reprinted with permission from Charter Financial Publishing Network., Copyright [year of article]'. The terms have no AI or text-and-data-mining clause. Governing law: New Jersey, with courts in Trenton, NJ. Consent and legal contact: Charter Financial Publishing Network, Attn: Legal Counsel, 499 Broad Street, Shrewsbury, NJ 07702, 732-450-8866. The reprints page (/reprints, Wayback 2025-12-15) offers hard-copy reprints, a secured PDF and plaques through 'Contact Us' and publishes no prices. The RSS feed carries <copyright>Copyright 2026 Financial Advisor Magazine</copyright> and has no separate feed terms.
- Text owner: Charter Financial Publishing Network ('the property of Financial Advisor and others'). Staff stories (e.g. the sample by Jacqueline Sergeant) are FA's. Syndicated Bloomberg and wire stories in the feed belong to their originators.
- Access / cost: free; free (sample article read in full without login) (<https://www.fa-mag.com/news/edward-jones-wins--4-8m-arbitration-award-against-ex-broker-and-ameriprise-88593.html>)
- robots.txt: robots.txt (2026-10-04) has no group for generic agents, so /news/*.html and /rss are not disallowed. Only www.integromedb.org/Crawler is disallowed /. msnbot has Crawl-delay 10 and Slurp has Crawl-delay 240. Separately, Cloudflare returns 403 to scripts on /, /news, /terms and /sitemaps/*, while article pages and /rss return 200.
- Questions:
  1. Fa-mag.com terms forbid storing or archiving articles on any server, scraping for use on another service, and redistributing to others in the same organization, all 'without the prior written consent of Financial Advisor': will we ask Charter Financial Publishing Network (Legal Counsel, 732-450-8866) for written consent, or keep FA-mag items as metadata + link only?
  2. Fa-mag.com allows 'insubstantial portions' only in paper-form, noncommercial memoranda for a limited number of people: does showing quoted passages on screen in the prototype fall outside that exception, so that excerpts also need consent?
  3. Fa-mag.com limits use to 'personal, noncommercial use only': does the prototype for Edward Jones's CSO qualify?
  4. Fa-mag.com syndicates Bloomberg and wire stories: should we exclude syndicated items, or treat them under Bloomberg/licensed (tier 1) rules?

#### T-42 financialadvisoriq.com (Financial Advisor IQ (F.T. Specialist Inc., Financial Times group))

Rows: `T4-FAIQ`

- Terms: <https://www.financialadvisoriq.com/legal>, read 2026-10-04 (live page. A plain request gets a 302 loop through login.ftspecialist-us.com; a cookie-accepting client receives 200. Also read /copyright and /reprints live.)
- Scraping: **forbidden**. "(d) Frame, harvest or scrape the Content or otherwise access the Content for similar purposes;"
- Full-text storage: **forbidden**. "(b) Making and storing electronic copies or print copies of the Content (for the avoidance of doubt, this right is limited to Users and shall not entitle Users or Customer to develop an archive of the Content);"
- Excerpts: **forbidden**. "nor shall Customer or Users publish any Content on a website, intranet, extranet, email service or in any other electronic or hard copy product or service;"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: AI clause 2.7: 'we expressly prohibit any use of our content or data (including any associated metadata) in any manner for any machine learning and/or artificial intelligence purposes, ... to generate any data or content and/or to synthesize or combine with any other data or content. We reserve all rights to license any use of our content and data for any such purposes.' Database right 2.1: 'this Agreement prevents the extraction or re-utilization of the Content.' Permitted use 2.3: 'use the Content for research and current awareness purposes in the normal course of business'. Ban 2.5(a): 'copy, cut and paste, reproduce, ... store, archive, aggregate, publicly display, redistribute, syndicate, share'. The copyright page allows downloading '(one copy only) for your personal, noncommercial use only.' The article registration form ('Enter your email to unlock access') requires ticking agreement to these /legal terms. The reprint policy says any reprint use 'must be pre-approved by F.T. Specialist Inc.' (ftsus.reprints@ft.com, 212-542-1290). Governing law: New York for F.T. Specialist Inc. Other contacts: support.ftspecialist@ft.com, and General Counsel at F.T. Specialist, Bracken House, London. The page is titled 'F.T. Specialist Inc. Corporate Services Terms and Conditions'.
- Text owner: F.T. Specialist, Inc. ('Copyright © 2026 F.T. Specialist, Inc. All rights reserved.'). Licensed trade content.
- Access / cost: free-registration; not published (T&C 6.2: the subscription price is 'quoted to Customer by F.T. Specialist's sales team') (<https://www.financialadvisoriq.com/legal>)
- robots.txt: For User-agent *: Allow / (covers /c/ article pages). Disallows /search/*, /pc/*, /printIssue/*, /media/download/*, /email-contributor/*, /emailContent/* and /jobblast/email\|print/*. GPTBot, CCBot, DataForSeoBot, trendictionbot and others are disallowed / (2026-10-04).
- Questions:
  1. FA-IQ (F.T. Specialist) terms forbid scraping, archiving and publishing Content on any intranet, and clause 2.7 bans any AI use 'to synthesize or combine with any other data or content': should FA-IQ be excluded from ingestion unless F.T. Specialist grants a written license?
  2. Does a free FA-IQ email registration bind us to the 'Corporate Services Terms and Conditions' at /legal, and does WashU or Edward Jones already hold an FA-IQ subscription whose license could cover the prototype?

#### T-43 advizorpro.com (AdvizorPro (PlanPro Solutions, LLC))

Rows: `T4-ADVIZORPRO`

- Terms: <https://advizorpro.com/terms-conditions>, read 2026-10-04 (live page)
- Scraping: **unclear**. "engage in unauthorized spidering, “scraping,” or harvesting of content or personal information, or use any other unauthorized automated means to compile information or content provided through the Services;"
- Full-text storage: **unclear**. "You may not publish, reproduce, distribute, display, perform, edit, adapt, modify, or otherwise exploit any part of the Services without Our written consent."
- Excerpts: **unclear**. "THE SERVICES AND THE CONTENT YOU ACCESS THROUGH THE SERVICES ARE PROVIDED FOR YOUR OWN (AND ANY AUTHORIZED USER’S) INTERNAL, PERSONAL USE ONLY. DO NOT SHARE THE CONTENT OR INFORMATION WITH ANYONE ELSE."
- Other clauses: Scope is the open issue. The terms say: 'These Terms of Use (“Terms”) govern your use of the app.advizorpro.com (the “Website”) and the content and services provided by PlanPro Solutions, LLC (“We,” “Us,” or “Our”) through the Website (collectively, the “Services”).' The public blog at advizorpro.com/post/ is not the app, yet these are the only terms linked from the blog footer. License: 'We only grant you, for the term of you Subscription, a paid-up, revocable, non-assignable, non-transferrable limited license to use the Services and the content provided through the Services for your own internal purposes only.' The terms have no AI clause. Separately, robots.txt (a technical signal, not permission) carries 'Content-Signal: search=yes, ai-input=yes, ai-train=no'. Governing law: Georgia, with a federal district court in Georgia.
- Text owner: PlanPro Solutions, LLC / AdvizorPro ('© 2026 AdvizorPro. All rights reserved.'). Data comes from AdvizorPro's own database.
- Access / cost: free; free (public blog; the AdvizorPro platform itself is a paid subscription with no price published on the pages read) (<https://advizorpro.com/post/advisor-moves>)
- robots.txt: User-agent * Allow / (covers /post/). GPTBot, OAI-SearchBot, ChatGPT-User, Claude-Web and Google-Extended are explicitly allowed /. 'Content-Signal: search=yes, ai-input=yes, ai-train=no'. Sitemap at /sitemap.xml (2026-10-04).
- Questions:
  1. AdvizorPro's Terms of Use govern 'app.advizorpro.com' but are the only terms linked from the public blog: do their scraping ban, 'INTERNAL, PERSONAL USE ONLY' and 'without Our written consent' clauses apply to the free /post/ Advisor Moves reports?
  2. AdvizorPro's robots.txt signals 'ai-input=yes, ai-train=no': is that enough for us to store and quote the monthly reports, or do we ask PlanPro Solutions for written permission?

#### T-44 diamond-consultants.com (Diamond Consultants (Diamond Financial Consultants, LLC))

Rows: `T4-DIAMOND`

- Terms: <https://www.diamond-consultants.com/privacy-policy/>, read 2026-10-04 (live page. The footer 'Terms of Service' link points to this combined 'Privacy Policy & Terms of Service' page (Last Edited on 2026.02.03).)
- Scraping: **silent**. "©2026 Diamond Financial Consultants, LLC t/a Diamond Consultants. All rights reserved."
- Full-text storage: **silent**. "©2026 Diamond Financial Consultants, LLC t/a Diamond Consultants. All rights reserved."
- Excerpts: **silent**. "©2026 Diamond Financial Consultants, LLC t/a Diamond Consultants. All rights reserved."
- Other clauses: The 'Privacy Policy & Terms of Service' page covers only personal data, cookies, CalOPPA and CAN-SPAM. It has no clauses on content use, scraping, copying or AI. Contact: 'questions regarding this privacy policy & terms of service, you may contact us using the information below', followed by Diamond-Consultants.com, 51 John F Kennedy Parkway, Short Hills, NJ 07078, 908-879-1002. Key caveat: 'Moves in the News' posts reproduce other publishers' articles in full. The sample shows the AdvisorHub logo and 'by Karmen Alexander', and the listing also reposts Wealth Solutions Report roundups. Diamond cannot license that text.
- Text owner: Diamond Financial Consultants, LLC for its own articles, podcast and Advisor Transition Report. 'Moves in the News' reposts belong to the original publishers (e.g. AdvisorHub, Wealth Solutions Report).
- Access / cost: free; free (<https://www.diamond-consultants.com/about-us/moves-in-the-news/>)
- robots.txt: User-agent * disallows /wp-content/uploads/wpforms/, /?s=, /page/*/?s= and /search/. Explicit Allow / for many AI agents (claudebot, claude-code, claude-user, gptbot, CCBot, google-extended, etc.). Sitemap /sitemap_index.xml (2026-10-04).
- Questions:
  1. Diamond Consultants' 'Moves in the News' posts are full reposts of AdvisorHub and Wealth Solutions Report articles: should we ingest only Diamond's own content and treat reposts under the original publisher's terms (or skip them as duplicates)?
  2. Diamond's 'Privacy Policy & Terms of Service' page is silent on content use: is silence plus 'All rights reserved' enough to store full text and show excerpts of Diamond's own articles, or do we ask Diamond in writing?

#### T-45 wealthsolutionsreport.com (Wealth Solutions Report (Finetric Media LLC))

Rows: `T4-WSR`

- Terms: <https://www.wealthsolutionsreport.com/privacy-policy/>, read 2026-10-04 (not found: no terms-of-use page linked, and /terms/, /terms-of-use/, /terms-and-conditions/ and /terms-of-service/ all return 404. Privacy policy read on the live page.)
- Scraping: **silent**. "©2026 Finetric Media LLC. All rights reserved."
- Full-text storage: **silent**. "©2026 Finetric Media LLC. All rights reserved."
- Excerpts: **silent**. "©2026 Finetric Media LLC. All rights reserved."
- Other clauses: The privacy policy refers to terms that are not published: 'enforce or apply our terms and conditions or to protect the rights, property, or safety of our business'. Article pages show an email modal ('Confirm your email and read all our content for free!'), and signing up means 'you agree to our Privacy Policy'. The terms have no AI or text-and-data-mining clause. Contact: info@wealthsolutionsreport.com.
- Text owner: Finetric Media LLC ('©2026 Finetric Media LLC. All rights reserved.')
- Access / cost: free-registration; free ('Confirm your email and read all our content for free!') (<https://www.wealthsolutionsreport.com/deals-recruiting-roundup-creative-planning-wedbush-raymond-james-and-more/>)
- robots.txt: User-agent * disallows /ghost/, /email/, /members/api/comments/counts/, /r/, /webmentions/receive/ and /.ghost/analytics/api/. Posts, /tag/deals-and-recruiting/ and /rss/ are allowed (2026-10-04).
- Questions:
  1. Wealth Solutions Report (Finetric Media) publishes no terms of use, only a privacy policy and 'All rights reserved': is silence enough to store full text and show excerpts, or do we ask info@wealthsolutionsreport.com in writing?
  2. Does confirming an email on WSR (the 'read all our content for free' modal) bind us to terms we cannot see?

#### T-46 dakota.com (Dakota)

Rows: `T4-DAKOTA`

- Terms: <https://www.dakota.com/terms-of-service>, read 2026-10-04 (live page (Last Updated: August 19, 2024))
- Scraping: **forbidden**. "(iii) shall not be submitted to, processed by, or otherwise fed into any artificial intelligence or automated processing software;"
- Full-text storage: **unclear** (first read as forbidden; refuted on re-check, see below). "You may not tokenize copies of the pages of the Services or any other content on the Services."
- Excerpts: **unclear**. "You agree that you will not duplicate, publish, modify, create derivative works from, participate in the transfer of, or in any way distribute or exploit the Services, or any portion of the Services, for any public or commercial use, without our prior express written consent."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 0/2 checkers confirmed; refuted because: The quote is on the live page word for word (INTELLECTUAL PROPERTY section). But it bans tokenizing, not keeping copies. 'Tokenize' isn't defined. It could mean NLP tokenization or blockchain/NFT tokenization. Either way it says nothing about storing full text in a database or a Box folder. The sentence that actually governs keeping copies comes just before it in the same paragraph, and it permits retention only conditionally: 'You are authorized to view and retain a copy of pages of the Services only for your own personal, non-commercial use.' The next clause, 'will not duplicate ... for any public or commercial use, without our prior express written consent', also depends on how the use is classified. So does OUR MATERIALS: the licence is 'for your personal use only', and clause (ii) bans incorporation 'into any other work ... without Dakota's prior written permission'. Whether a database counts as 'any other work' is also ambiguous. The brief says that when a clause depends on personal or non-commercial status, the verdict is unclear, so storage alone is unclear, not explicitly forbidden. Practical caveat: even if storage were allowed, the pipeline would still be blocked. Splitting stored text into passages and sending it to an LLM involves tokenization, which arguably falls under the tokenize ban, and it is plainly covered by clause (iii) (no AI or automated processing). So T4-DAKOTA can't be used as designed without Dakota's written permission. Questions for the ADR-000 owners: (1) Dakota allows retaining copies 'only for your own personal, non-commercial use': does the prototype qualify? (2) Dakota bans feeding materials into 'any artificial intelligence or automated processing software' and bans tokenizing copies: should we ask Dakota for written permission, or drop T4-DAKOTA? (3) Does keeping and chunking blog posts count as incorporating them 'into any other work' under clause (ii)? / The quote appears word for word in the INTELLECTUAL PROPERTY section of the live page (2026-10-04), but it bans tokenizing, not storing. 'Tokenize' is not defined: it could mean LLM/embedding tokenization or crypto/NFT tokenization. Keeping full copies in Postgres and Box is covered by the sentence just before it, a limited permission to 'retain a copy of pages' for 'personal, non-commercial use'. The next sentence bans duplicating 'for any public or commercial use, without our prior express written consent'. Both turn on whether the prototype is personal/non-commercial, which is the rubric's example of 'unclear', not an explicit ban on storage. The license is also 'for your personal use only', and item (ii) bars materials being 'incorporated into any other work' without written permission; whether a passage database counts as 'another work' is also unclear. In practice the pipeline is probably still blocked: item (iii)'s AI/automated-processing ban and the tokenize ban would cover splitting text into passages, embedding it and feeding it to an LLM, even if storage alone were allowed. ADR-000 questions: (1) Dakota terms allow retaining copies only for 'personal, non-commercial use' and bar duplication for 'public or commercial use': does a WashU student prototype built for Edward Jones's strategy office qualify? (2) Does Dakota's 'You may not tokenize copies' cover splitting text into passages, embedding it or sending it to an LLM? (3) Should we ask Dakota (privacy@dakota.com) for written permission, given that item (iii) bans feeding materials into AI or automated processing software?.
- Other clauses: Personal use only: 'we grant you a non-exclusive, non-transferrable, non-sublicensable right and license to use the Dakota Materials for your personal use only.' Retained copies: 'You are authorized to view and retain a copy of pages of the Services only for your own personal, non-commercial use.' Clause (ii): materials 'may not be modified, used to create a derivative work, incorporated into any other work or otherwise exploited without Dakota’s prior written permission'. Clause (iii), the AI and automated-processing ban, is quoted under scraping. The terms have no explicit robots, spider or scraper clause. Governing law: Pennsylvania, with an arbitration provision and class waiver. Copyright agent: tbrown@dakota.com.
- Text owner: Dakota (Dakota Materials 'are the property of Dakota and its licensors'). Move data comes from Dakota Marketplace.
- Access / cost: free; free (public blog) (<https://www.dakota.com/resources/blog/july-2026-financial-advisor-moves-who-changed-firms-this-month>)
- robots.txt: User-agent * Allow /. Disallows /search?, /thank-you/, /form-submit/, /_hcms/preview/, /hs/manage-preferences/, /hs/preferences-center/ and the hs_preview and hsCacheBuster params. /resources/blog/ and /resources/blog/rss.xml are allowed (2026-10-04).
- Questions:
  1. Dakota's terms say materials 'shall not be submitted to, processed by, or otherwise fed into any artificial intelligence or automated processing software' and 'You may not tokenize copies': does this rule out fetching and indexing Dakota's monthly Advisor Moves posts unless Dakota grants written permission?
  2. Dakota bars use 'for any public or commercial use, without our prior express written consent' and licenses 'personal use only': does the prototype for Edward Jones's CSO count as commercial use, and are short quoted excerpts allowed?

#### T-47 fintrx.com (FINTRX, Inc.)

Rows: `T4-FINTRX`

- Terms: <https://www.fintrx.com/terms-of-use-fintrx>, read 2026-10-04 (live page (Last Updated: August 26, 2026). Not linked from the blog footer, which links only the privacy policy; found via sitemap.xml. /terms, /terms-of-use, /terms-of-service and /terms-and-conditions all return 404.)
- Scraping: **silent**. "These Terms of Use ("Terms") govern access to and use of the FINTRX private wealth intelligence platform, including our web application, data products, APIs, and integrations,"
- Full-text storage: **silent**. "© 2026 FINTRX. ALL RIGHTS RESERVED."
- Excerpts: **silent**. "© 2026 FINTRX. ALL RIGHTS RESERVED."
- Other clauses: The only Terms of Use cover the paid platform (the 'Service') and say nothing about the public blog. The platform's scraping clause reads 'Attempt to reverse engineer, decompile, scrape, or extract the underlying models, algorithms, or datasets powering the Service, including Fin.' Platform license: 'for your internal business purposes during your subscription term'. Governing law: Delaware. No blog-specific copyright or AI clause was found.
- Text owner: FINTRX, Inc. ('© 2026 FINTRX. ALL RIGHTS RESERVED.')
- Access / cost: free; free (public blog) (<https://www.fintrx.com/blog>)
- robots.txt: User-agent * disallows /trialconfirmation, /_hcms/preview/, /hs/manage-preferences/, /help-center/, /hs/preferences-center/ and the hs_preview and hsCacheBuster params. /blog/ and /blog/rss.xml are allowed (2026-10-04).
- Questions:
  1. FINTRX's only Terms of Use cover its paid platform, not the public blog: is silence plus '© 2026 FINTRX. ALL RIGHTS RESERVED.' enough to store full text and quote the monthly RIA & Broker-Dealer Roundup, or do we ask FINTRX in writing?

#### T-48 familywealthreport.com (Family Wealth Report (ClearView Financial Media Ltd))

Rows: `T4-FAMILYWEALTHREPORT`

- Terms: <https://www.familywealthreport.com/page.php?p=termsandconditions>, read 2026-10-04 (live page)
- Scraping: **silent**. "11.1 The contents of the Subscription Service are protected by international copyright laws and other intellectual property rights. The owner of these rights is ClearView Financial Media Limited or other third party licensors."
- Full-text storage: **unclear**. "ii. download and store one copy of the Materials in machine readable form;"
- Excerpts: **forbidden**. "v. download, store, reproduce, transmit, display (including without limitation display on any intranet or extranet site), copy, distribute or use Materials other than in accordance with clause 5.3(a)above;"
- Verification: excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The terms are a subscription agreement: a 14-day trial, then an annual fee (5.1). 5.3(a) lets each User 'display the Materials electronically on a single computer' and store one machine-readable copy. 5.3(a)(iv) adds: 'you shall not be entitled to reproduce the Materials on any electronic or print media (including without limitation on any intranet or extranet) other than as permitted under this clause.' 5.5: 'Unless otherwise specified, the Materials are presented solely for your own internal business use and may not be re-sold.' 16.2: on termination 'you must immediately destroy all of your copies of the Materials.' The terms have no robots, scraping or AI clause. Governing law: English law, courts of England. Article pages offer 'Request Reprint Rights' and 'Print (subject to copyright)'.
- Text owner: ClearView Financial Media Ltd, London ('or other third party licensors'). Footer: '© 2026 Clearview Financial Media Ltd'.
- Access / cost: free-registration; not published (T&C 6.2: 'Details of our prices for full subscription ... are available from ClearView Financial Media Limited sales and customer care representatives.') (<https://www.familywealthreport.com/page.php?p=termsandconditions>)
- robots.txt: User-agent * Allow / with crawl-delay: 30. SemrushBot is disallowed /. Sitemap /sitemap.xml.php (2026-10-04).
- Questions:
  1. Family Wealth Report (ClearView) subscription terms allow one stored machine-readable copy per User but forbid display 'on any intranet or extranet site': would a shared Postgres/Box copy queried by several people breach clause 5.3(b)?
  2. Do FWR's subscription terms bind us when we read free articles without registering, and does the prototype count as 'your own internal business use' (5.5)?

#### T-49 bizjournals.com (St. Louis Business Journal (American City Business Journals))

Rows: `T4-STLBJ`

- Terms: <https://www.bizjournals.com/useragreement>, read 2026-10-04 (Wayback capture 2026-07-29 (Last Revised: August 13, 2024). The live page returns 403 (Cloudflare challenge) to curl on 2026-10-04, and WebSearch refuses the domain.)
- Scraping: **forbidden**. "use any bots, cheats, macros, scripts, or run Maillist, Listserv or any form of autoresponder, or use any other automated process, or engage in meta-searching or periodic caching of information, to access, visit and/or use the Service" (<https://web.archive.org/web/20260729015816/https://www.bizjournals.com/useragreement>)
- Full-text storage: **forbidden**. "copy, harvest, crawl, index, scrape, spider, mine, gather, extract, compile, obtain, aggregate, capture, access, store, or republish any Content on or through the Service, including by an automated or manual process or otherwise," (<https://web.archive.org/web/20260729015816/https://www.bizjournals.com/useragreement>)
- Excerpts: **unclear** (first read as forbidden; refuted on re-check, see below). "The material on this site may not be reproduced, distributed, transmitted, cached or otherwise used, except with the prior written permission of American City Business Journals." (<https://web.archive.org/web/20260729015816/https://www.bizjournals.com/useragreement>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 1/2 checkers confirmed; refuted because: The quote is word for word, but it is the generic site footer printed under the agreement (it also appears on thebusinessjournalsreprints.com and promo.bizjournals.com/reprints/faq/). It is not the clause that governs using parts of the content. That clause is in section V.B: 'copy, reproduce ... display, distribute ... or use any Content or Products obtained on or through the Service, in whole or in part, except as permitted by the Copyright Act or other law or as expressly permitted in writing by the Agreement, us or the Service'. The agreement itself therefore preserves whatever copyright law allows for partial use. For a plain short quotation with attribution and a link, the footer alone would make the verdict 'unclear', because it turns on a fair-use question we may not decide. The reprints FAQ and terms only cover purchased reprints and say nothing about quotation. The verdict is still forbidden for this project, but for a different reason: the excerpts are shown inside LLM answers grounded on stored chunks (RAG). Section V.A says 'Non-commercial use does not include use of the Service— except with prior written consent—in connection with ... grounding (including through retrieval-augmented generation (RAG))'. The excerpts also come from full copies that the storage clauses forbid. Verdict unchanged: forbidden unless ACBJ gives prior written consent. The supporting quote should be the RAG clause. Question for ADR-000 owners: if we don't scrape, would showing an attributed snippet from a non-ACBJ route (e.g., Bing News RSS metadata) fall outside this agreement, or is ACBJ consent required?.
- Other clauses: The only exception to the copy/store ban is 'indexing Content for inclusion in a Search Engine'. A 'Search Engine' must be 'a free, publicly-accessible database', which a private prototype is not. Personal use and AI: 'Unless otherwise specified, the Service is intended for your personal, non-commercial use only. You may not access, visit, use and/or store the Service or any of its Content except for personal, noncommercial use. Non-commercial use does not include use of the Service— except with prior written consent—in connection with the development, training, fine tuning, grounding (including through retrieval-augmented generation (RAG)),' ... 'of any large language model ... or any software or tool that incorporates generative artificial intelligence.' Because these uses are allowed only 'except with prior written consent', consent can be requested from ACBJ. Governing law: New York, with NAM arbitration. Footer: 'User Agreement (updated August 13, 2024)'.
- Text owner: American City Business Journals ('© 2026 American City Business Journals. All rights reserved.')
- Access / cost: paywall; $210 for 52 weeks (Digital Only 'Premium'); Premium Plus $220, Premium Elite $380 and Premium Unlimited $950 for 52 weeks. From the Wayback capture of 2025-09-28; current price TODO-verify. A WashU free account is reported in the existing row note (not re-verified). (<https://web.archive.org/web/20250928111446/https://www.bizjournals.com/stlouis/subscribe>)
- robots.txt: robots.txt is reachable (200). User-agent * does not disallow /stlouis/news/. It disallows /rss/, /search?*, /*/search?*, /search/results/*, /newssearch, /api/ (except /api/legendary-data/relay), /*.amp.html, /library/*, /login/, /*/inno/newsletter and others. Yandex, Baiduspider, cohere-ai, ia_archiver, archive.org_bot, heritrix and blp_bbot are disallowed / (2026-10-04). Articles, sitemaps and terms all return 403 (Cloudflare) to scripts.
- Questions:
  1. Bizjournals (ACBJ) User Agreement forbids bots/scripts, storing Content, and use for 'grounding (including through retrieval-augmented generation (RAG))' without prior written consent: should St. Louis Business Journal stay metadata + link only (read manually), or will we ask ACBJ for consent?
  2. Does WashU's free bizjournals account carry any license beyond the personal, non-commercial User Agreement?
  3. If the prototype's answers are composed by an LLM from retrieved passages, does that count as RAG 'grounding' under the bizjournals User Agreement even for metadata-only records?

#### T-50 stltoday.com (St. Louis Post-Dispatch (Lee Enterprises, Incorporated))

Rows: `T4-STLTODAY`

- Terms: <https://www.stltoday.com/terms/>, read 2026-10-04 (Wayback capture 2026-09-13. Live access on 2026-10-04 failed two ways: curl to /site/terms.html got 429, and WebFetch got a 302 to tollbit.stltoday.com, a bot-access gateway that was not followed.)
- Scraping: **forbidden**. "Use automated scripts to collect information from, or otherwise interact with, the Site;" (<https://web.archive.org/web/20260913010122/https://www.stltoday.com/terms/>)
- Full-text storage: **forbidden**. "This Site and Our Content may not be copied, reproduced, republished, uploaded, posted, sold, leased, licensed, sublicensed, transmitted, or distributed without our written permission, except that you may download, display, and print one copy of Our Content on a single computer" (<https://web.archive.org/web/20260913010122/https://www.stltoday.com/terms/>)
- Excerpts: **forbidden**. "The use of Our Content or other content on the Site on any other website or in any environment of networked computers is prohibited." (<https://web.archive.org/web/20260913010122/https://www.stltoday.com/terms/>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The single-copy permission continues 'for your personal, non-commercial use only.' Deep links: '"Deep-linking," "embedding," or using analogous technology with respect to Our Content or other content is strictly prohibited unless specifically authorized in writing.' This affects the plan to link back to each article. Linking to the site itself is allowed on conditions: 'you do not frame any of Our Content ... or incorporate into another website or other service any of our intellectual property.' Content is 'owned by us and third party providers'. Bot traffic is routed to TollBit (tollbit.stltoday.com), a paid bot-access gateway and possible licensing route. Governing law: Iowa, with AAA arbitration. Copyright agent: copyright@lee.net.
- Text owner: Lee Enterprises, Incorporated (St. Louis Post-Dispatch) and 'third party providers' (e.g. wire content)
- Access / cost: metered; not published (not found on pages read; the subscription page was not reachable due to 429)
- robots.txt: ClaudeBot, Claude-Web, anthropic-ai, GPTBot, ChatGPT-User, OAI-SearchBot, CCBot, Google-Extended, PerplexityBot, Scrapy, Diffbot, Bytespider, cohere-ai and others are disallowed /. For User-agent *, /news/local/business/ is not disallowed. Disallowed for *: /search/ai/, /tncms/search/, /online/feeds/, /json/, /users/, /login/, /pr/, /obituaries/ and others. Live site returns 429 to curl (2026-10-04).
- Questions:
  1. St. Louis Post-Dispatch (Lee) terms forbid automated scripts, copying beyond one personal copy, any use 'in any environment of networked computers', and deep-linking without written authorization: is even a short excerpt plus a link back allowed, or must stltoday stay out of the prototype?
  2. stltoday routes bot traffic to TollBit (tollbit.stltoday.com): do we want to explore paid licensed access through TollBit or Lee directly?
  3. Do WashU's NewsBank Access World News or Factiva licenses permit storing full text and showing excerpts of Post-Dispatch articles in the prototype?
  4. Post-Dispatch terms allow one copy 'for your personal, non-commercial use only': does the prototype qualify?

#### T-51 tampabay.com (Tampa Bay Times (Times Publishing Company))

Rows: `T4-TAMPABAYTIMES`

- Terms: <https://www.tampabay.com/resources/universal/user_agreement.html>, read 2026-10-04 (live page ('Terms, Conditions & Copyright'; no revision date shown))
- Scraping: **silent**. "The site's content is for your personal, non-commercial use."
- Full-text storage: **forbidden**. "Storing or archiving any significant portion of the content or creating a database using the content is prohibited."
- Excerpts: **unclear** (first read as forbidden; refuted on re-check, see below). "Any linking which results in display of this site's content surrounded by or included with content of another site, organization or person is prohibited."
- Verification: full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 0/2 checkers confirmed; refuted because: The quote appears word for word on the old 2011 page (https://www.tampabay.com/resources/universal/user_agreement.html). It does not fit the action, though. It is a framing/embedding clause: it bans links that cause Tampa Bay Times content to be shown inside another site. The sentence just before it explicitly allows plain hyperlinks ('You may hyperlink to TampaBay.com so long as the link does not state or imply any sponsorship or endorsement'). So our link back to the source is permitted, and a short quoted passage is copied text, not something displayed 'by linking'. The quote therefore does not support banning excerpts. On the current terms at https://www.tampabay.com/terms-of-service/ ('Last Updated: July 3__, 2026') the wording also differs ('Any linking which results in displaying the Content ... organization, or person is prohibited.'). The verdict is still 'forbidden', for a different reason. The current terms bar using the Content with AI tools to generate text 'whether for commercial or personal use'. The prototype makes each answer with one LLM call (Claude or OpenAI) over the retrieved passages (repo docs/ARCHITECTURE.md; docs/DECISIONS.md ADR-002/ADR-003). So excerpts shown in answers fall under that ban, whatever the answer to the personal/non-commercial question. A second current clause also covers display: 'You may not use, copy, reproduce, ... display, ... or otherwise exploit Content for any purpose: (i) without the prior consent of the owner of that Content'. Apart from that, the only permitted copying is 'exclusively for your personal non-commercial use'. Consent can be requested at privacy@tampabay.com, via the terms' 'click here to email your request to use any Content from the Sites' link. Question for the ADR-000 owners: Tampa Bay Times terms (July 2026) ban using Content to generate text with any AI model or tool, even for personal use, and ban building a database. Should we ask privacy@tampabay.com for written consent, or keep tampabay.com as link-only (headline and URL, no stored text, no LLM input)? / The quote appears word for word on the legacy page, but it does not support the verdict. The clause is about framing or embedding: a link that makes Tampa Bay Times content appear inside another site's content. The same bullet says 'You may hyperlink to TampaBay.com so long as the link does not state or imply any sponsorship or endorsement', so the link back to the source is allowed. It says nothing about showing short quoted passages from our own stored copy. A different clause does support 'forbidden'. The current governing terms (https://www.tampabay.com/terms-of-service/, Last Updated July 2026) list among prohibited uses 'Use the Content in connection with any machine learning and/or artificial intelligence model or tool ... (ii) to generate text ... using any such model or tool, whether for commercial or personal use'. The prototype's answers come from one Claude or OpenAI call over the stored passages (DECISIONS.md, ADR-002/ADR-003), so showing Tampa Bay Times excerpts inside generated answers falls under this ban. Because the clause says 'whether for commercial or personal use', the verdict does not hinge on the personal or non-commercial question. The better_quote stops at 282 characters; on the page the sentence continues ', whether for commercial or personal use'. Without the AI angle the excerpts verdict would be 'unclear': copies are allowed only 'exclusively for your personal non-commercial use', and 'You may not use the Content in any way not specifically provided for in these Terms without the specific written consent of the Times.' Consent can be requested by the email link on the terms page. Open questions for ADR-000: (1) Does the Tampa Bay Times AI clause, which applies 'whether for commercial or personal use', rule out putting tampabay.com passages into LLM answers unless we get written consent or a PARS license? (2) Separately, the current terms ban automated access: 'Use any automated means, including ... crawler, robot, script, spider ... to harvest, mine, compile, collect, or "scrape" any information from the Services, except for purposes of indexing for inclusion in a public search engine.' Does this rule out the fetch script for tampabay.com?.
- Other clauses: Copies: 'If you copy any material from this site, that copy must be exclusively for your personal non-commercial use and that copy must retain copyright, trademark and other ownership notices contained in the material.' Catch-all: 'You may not use the content in any way not specifically provided for in this agreement without the specific written consent of the Tampa Bay Times.' Consent can therefore be requested. The terms also prohibit 'copying other than on an isolated basis for personal use; ... displaying the content of the site'. There is no automated-access or AI clause. Governing law: Florida, with venue in Pinellas County. Privacy contact: Times Publishing Company, 490 1st Ave. S., St. Petersburg, FL 33701 (per search snippet; not re-read).
- Text owner: Tampa Bay Times / Times Publishing Company ('owned by the Tampa Bay Times')
- Access / cost: metered; not published (not found on pages read)
- robots.txt: For User-agent *, only 'Allow: /ads.txt' with no disallows, so /news/business/ and /archive/ are allowed. GPTbot, anthropic-ai, ClaudeBot, CCBot, Diffbot, Bytespider, OmigiliBot and Aolbot-News are disallowed /. Google-Extended Allow / (2026-10-04).
- Questions:
  1. Tampa Bay Times terms prohibit 'creating a database using the content' and displaying its content 'surrounded by or included with content of another site, organization or person': should Tampa Bay Times be metadata + link only, or should we request written consent from Times Publishing Company?
  2. Tampa Bay Times limits use to 'personal, non-commercial use': does the prototype qualify?

#### T-52 wsj.com (Dow Jones & Company, Inc. (The Wall Street Journal))

Rows: `T4-WSJ`

- Terms: <https://www.dowjones.com/terms-of-use/>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "You shall not access, view, retrieve, refresh, reload, scrape, text or data mine, index, process, store, harvest, or otherwise ingest the Services or any Content, whether directly or through an intermediary, using any automated means, webcrawler, spider, script, site search/retrieval application,"
- Full-text storage: **forbidden**. "You may not otherwise download, print, store or provide others with access to such articles except through the share features we have included in a Service or with a license obtained through the Dow Jones Reprints website at djreprints.com."
- Excerpts: **forbidden**. "Unless you have our written consent, you may not use, sell, publish, distribute, retransmit or otherwise provide access to the Content received through the Services to anyone, including, if applicable, your fellow students, coworkers, or employees,"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: Terms 'Effective Date: June 30, 2026'. The §9.4.1 automated-access ban ends 'without our prior written consent', so consent can be requested. §9.4.2: 'you may not harvest, ingest, use or incorporate any Content available through a Service for any form of artificial intelligence (“AI”), including in any generative or other form of AI for training or grounding purposes, unless you receive our prior written permission.' §9.4.2 also says rights are not expanded 'by our use or configuration of exclusionary protocols (e.g., the Robots Exclusion Protocol as implemented through robots.txt files).' §9.1: 'The Services are for your individual, personal and non-commercial use only. Thus, you may not access or use the Content, including without limitation, any Content made available through one of our RSS feeds, in any commercial product or service, without our express written consent.' §9.3 allows occasional storage 'for your individual, personal, and non-commercial use' only, and adds: 'In addition, you may not use articles you have downloaded, printed or stored to develop or operate an automated trading system, or for text or data mining any information or content (including associated metadata).' §9.4.3: a bot used with permission must identify itself in the User-Agent. §9.4.5 opts out of EU DSM Art. 4 text and data mining. The terms treat school-provided access as a 'Third Party Payer' arrangement, which adds no rights. Governing law: New York (§17). Consent and licensing: copyright@dowjones.com (robots.txt header) and djreprints.com, which says Wright's Media 'is the only authorized reprint and licensing group for all Dow Jones copyrighted content.' The RSS channel carries 'Copyright &#169; Dow Jones &amp; Company, Inc. All rights reserved.'
- Text owner: Dow Jones & Company, Inc. Terms §9.3: 'The Content is our property or the property of our advertisers and licensors'. The RSS feed says 'Copyright © Dow Jones & Company, Inc. All rights reserved.'
- Access / cost: paywall; not published (no price on djreprints.com; a license goes through Wright's Media) (<https://www.djreprints.com/>)
- robots.txt: www.wsj.com/robots.txt (2026-10-04): 'User-agent: * Disallow: /', so all of /finance/ and /articles/ is disallowed for generic agents. Only named search, social and ad bots get 'Allow: /'. The header comment says automated collection 'is prohibited unless you have express written permission from Dow Jones & Company, Inc.' feeds.content.dowjones.io/robots.txt returns 403 AccessDenied, so there is no robots file for the RSS host.
- Questions:
  1. WSJ/Dow Jones Terms §9.4.1 forbid access by any script, bot or AI agent without prior written consent, and §9.4.2 forbids using Content for AI 'grounding'. Do we ask for written consent (copyright@dowjones.com / Wright's Media via djreprints.com), or keep WSJ out of ingestion entirely?
  2. Dow Jones Terms §9.1 also apply the personal, non-commercial limit to RSS content. May the prototype store WSJ RSS headlines, teasers and links as metadata?
  3. Does WashU's campus WSJ.com / Factiva subscription allow putting WSJ text into a project database that teammates and the Edward Jones CSO stand-in can query, given that §9.3 bars giving 'fellow students, coworkers' access?
  4. Dow Jones Terms limit the Services to 'individual, personal and non-commercial use'. Does a student prototype built for Edward Jones's strategy office count as non-commercial?

#### T-53 reuters.com (Reuters (Thomson Reuters))

Rows: `T4-REUTERS`

- Terms: <https://www.reuters.com/info-pages/terms-of-use/>, read 2026-10-04 (Wayback capture 2026-05-11 (https://web.archive.org/web/20260511145004/https://www.reuters.com/info-pages/terms-of-use/). The live page returns 401 (DataDome), and the 2026-10-02 Wayback capture is also a 401 block page.)
- Scraping: **forbidden**. "use any robots, spiders, scripts, service, software or manual or automatic device, tool, or process designed to data mine or scrape the Content, data or information from the Service, or otherwise access or collect the Content, data or information from the Service using automated means;" (<https://web.archive.org/web/20260511145004/https://www.reuters.com/info-pages/terms-of-use/>)
- Full-text storage: **forbidden**. "cache or archive the Content (except for a public search engine's use of spiders for creating search indices);" (<https://web.archive.org/web/20260511145004/https://www.reuters.com/info-pages/terms-of-use/>)
- Excerpts: **forbidden**. "Without our prior written consent, you may not: remove, alter, forward, scrape, frame, in-line link, copy, sell, distribute, retransmit, create derivative works or otherwise make available (to third parties and/or on another website, app, blog, product, or service) the Content," (<https://web.archive.org/web/20260511145004/https://www.reuters.com/info-pages/terms-of-use/>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The capture shows 'Last updated on: 18th June 2025.' The scraping and caching items are in the same list, which opens with 'Without our prior written consent, you may not:', so consent can be requested. 'THE SERVICE AND THE CONTENT IS PROVIDED BY REUTERS AND ITS LICENSORS TO YOU ON A NON-EXCLUSIVE, LIMITED AND REVOCABLE BASIS AND FOR YOUR PERSONAL USE AND INFORMATION ONLY. YOU MAY NOT USE THE SERVICE OR THE CONTENT FOR ANY COMMERCIAL PURPOSE.' On RSS: 'You may not use the Content or Service, including without limitation, any Content made available through an RSS feed, in any commercial product or service, without our prior written consent.' On AI: 'use, directly or indirectly, the Service or Content for any purpose relating to the development and training of any machine learning ("ML") and artificial intelligence ("AI") activities and technologies,'. On robots: 'You promise to abide by exclusionary protocols (such as Robots.txt, Automated Content Access Protocol (ACAP), etc.) that may be used in connection with the Service.' Governing law: New York. Reprints: 'please refer to the Thomson Reuters Copyright page, which is part of these Terms and Conditions' (not read). Licensing contact from robots.txt: https://reutersagency.com/contact-us/enquire/
- Text owner: Reuters (Thomson Reuters) or its licensors. The terms say the Content 'is the property of Reuters or, in some cases, its licensors.'
- Access / cost: unknown; not published
- robots.txt: www.reuters.com/robots.txt (2026-10-04): the header says automated collection 'is prohibited unless you have prior written consent from Reuters'. 'User-agent: * Allow: /plus/ Disallow: /' disallows /business/, /markets/ and the /arc/outboundfeeds/ news sitemaps for generic agents. Only a named list of search, social and ad bots may crawl, and even they are blocked from /search, /site-search/ and /pf/api/. Applebot-Extended gets Disallow: /.
- Questions:
  1. Reuters terms (read through a 2026-05-11 Wayback capture because the live page returns 401) forbid automated collection and say 'cache or archive the Content' needs prior written consent, and robots.txt disallows the whole site, including /arc/outboundfeeds/, for User-agent *. Do we drop the Reuters news-sitemap metadata route?
  2. Should we ask Reuters for permission via https://reutersagency.com/contact-us/enquire/, or get Reuters text through Factiva or Nexis Uni? If the latter, do those library licenses allow storing article text in our database?
  3. Reuters terms limit use to 'PERSONAL USE AND INFORMATION ONLY' and bar 'ANY COMMERCIAL PURPOSE'. Does a WashU prototype for Edward Jones's strategy office count as commercial?
  4. Can someone read the live Reuters terms page in a browser to confirm the 18 June 2025 version is still current?

#### T-54 bloomberg.com (Bloomberg L.P.)

Rows: `T4-BLOOMBERG`

- Terms: <https://www.bloomberg.com/notices/tos/>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "You shall not use or attempt to use any “scraper,” “robot,” “bot,” “spider,” “data mining,” “computer code,” or any other automate device, program, tool, algorithm, process or methodology to access, acquire, copy, or monitor any portion of the Service,"
- Full-text storage: **forbidden**. "The Service and the information contained therein may not be used to construct a database of any kind. Nor may the Service be stored (in its entirety or in any part) in databases for access by you or any third party or to distribute any database Services containing all or part of the Service."
- Excerpts: **forbidden**. "Except as expressly permitted by Bloomberg in writing you may not copy, reproduce, recompile, decompile, disassemble, reverse engineer, distribute, publish, display, perform, modify, upload to, create derivative works from, transmit, transfer, sell, license, upload, edit post, frame, link,"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: The scraping clause ends 'without the prior express written consent of BLP', so consent can be requested. 'You agree to use the Service solely for your own noncommercial use and benefit, and not for resale or other transfer or disposition to, or use by or for the benefit of, any other person or entity.' Downloads are 'licensed to you by Bloomberg ONLY for your own personal, noncommercial use'. The Linking terms add: 'Further, you may not archive, cache, or mirror any Bloomberg.com Web page or portions of a Web page.' Permission requests go to BLP 'by writing to FEEDBACK' and must give name, company, site and the use planned. The subscription terms for organisation accounts ('Acceptable Use') say: 'Bloomberg hereby grants to Client a non-exclusive, non-transferable, non-sub-licensable license to allow its Authorized Subscribers to consume Bloomberg content for personal use and for internal work-related, research, and general awareness purposes.' I found no AI-specific clause in the bloomberg.com TOS. Governing law: New York (§13), with NAM arbitration. The RSS channel says 'Copyright 2026 BLOOMBERG L.P. ALL RIGHTS RESERVED'. Bloomberg Terminal and data licenses are separate and fall under the tier-1 part of ADR-000.
- Text owner: Bloomberg L.P. The RSS feed says 'Copyright 2026 BLOOMBERG L.P. ALL RIGHTS RESERVED', and the TOS say the content is 'owned by or licensed by Bloomberg or other third parties'. This is licensed vendor content.
- Access / cost: paywall; not published
- robots.txt: www.bloomberg.com/robots.txt (2026-10-04): User-agent * allows /news/articles/ and /feeds/ and disallows /search, /press-releases/, /account/* and /explore/. 'Disallow: /' applies to User-agents python-requests, Python-urllib and Python-http-client, so a default Python client is blocked. It also applies to CCBot, GPTBot, ClaudeBot and other AI bots. feeds.bloomberg.com/robots.txt redirects (301) to www.bloomberg.com/feeds/robots.txt, which is a 404.
- Questions:
  1. Bloomberg.com TOS say the Service 'may not be used to construct a database of any kind' and ban scrapers and bots without written consent. Is Bloomberg News excluded, including Markets RSS headlines and links, until the ADR-000 tier-1 Bloomberg answer arrives?
  2. Is there a Bloomberg.com organisation subscription at WashU or Edward Jones whose 'internal work-related, research' licence could cover this prototype, and would it allow storage in our database?
  3. Bloomberg wealth stories are often syndicated by fa-mag and Advisor Perspectives. May we use those syndicated copies, and whose terms govern them?

#### T-55 ft.com (The Financial Times Ltd)

Rows: `T4-FT`

- Terms: <https://help.ft.com/legal-privacy/terms-and-conditions/>, read 2026-10-04 (live page (T&C, plus the Copyright Policy it incorporates at https://help.ft.com/legal-privacy/copyright-policy/))
- Scraping: **forbidden**. "Use spidering technology or other datamining technologies to search and link to FT.com." (<https://help.ft.com/legal-privacy/copyright-policy/>)
- Full-text storage: **forbidden**. "Create a database in electronic or structured manual from by systematically and/or regularly downloading, caching, printing and storing all or any FT content (by spidering or otherwise)." (<https://help.ft.com/legal-privacy/copyright-policy/>)
- Excerpts: **unclear**. "By “extract” we mean 30 words copied verbatim from an FT article which are inserted into a longer original work ." (<https://help.ft.com/legal-privacy/copyright-policy/>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: T&C 7.1: 'These Terms and Conditions were published on 01 July 2026 and replace with immediate effect the Terms and Conditions previously published on 15 October 2025.' The Copyright Policy was 'published on 31 May 2023' and 'forms part of our terms and conditions'. T&C 3.5: 'we expressly prohibit any use of our content or data (including any associated metadata) in any manner for any machine learning and/or artificial intelligence purposes,' and goes on: 'or otherwise for the purposes of using or in connection with the use of such technologies, tools or models to generate any data or content and/or to synthesise or combine with any other data or content.' The Copyright Policy also says you cannot 'Frame, harvest or scrape FT content or otherwise access FT content for similar purposes.' Extracts come with conditions: attribution such as '[journalist name] at the Financial Times reported that' linked to FT.com, no 'Substitute', and 'No individual or organisation may create, republish or redistribute more than ten summaries in aggregate each day, each one sourced from a different FT article that is published on the same day you create the summary;'. On RSS: 'Download our RSS feeds and view them for your personal use. We currently publish headlines and teaser text within our RSS feeds. You may also make an RSS feed available to third parties, users within an organisation you work for or users of a website that you publish,'. The conditions are browser-only display, no paid service, headline and teaser only linked to FT.com, the attribution '© The Financial Times Limited [year]', and 'do not archive the feed or any of its content.' T&C 1.4: an organisation's subscription agreement takes precedence over these terms. T&C 8.2: US users are under New York law. Contacts: syndication@ft.com (republishing) and content.licensing@ft.com (robots.txt).
- Text owner: The Financial Times Ltd. The RSS feed says '© Copyright The Financial Times Ltd 2026.' Under T&C 3.1, FT.com and FT Content 'are owned by us, our licensors or both'.
- Access / cost: paywall; not published
- robots.txt: www.ft.com/robots.txt (2026-10-04): User-agent * allows /content/ and /financials, including ?format=rss. It disallows /search, /myft, /login, /register/ and /__. It sets 'Crawl-Delay: 1'. The header says: 'We expressly prohibit any use of our content or data for any machine learning or artificial intelligence purposes'. 'Disallow: /' applies to CCBot, GoogleOther, anthropic-ai, ClaudeBot, PerplexityBot and others.
- Questions:
  1. FT T&C 3.5 prohibit any use of FT content or metadata 'in connection with' AI tools that generate or combine content. Does that exclude FT entirely from an LLM-answer prototype, including RSS headlines?
  2. The FT Copyright Policy allows sharing RSS feeds inside an organisation but says 'do not archive the feed or any of its content'. May we store FT RSS items in Postgres, even as headline and link metadata only?
  3. FT allows 30-word extracts with attribution and a link, at most ten a day, 'inserted into a longer original work'. Do our cited answers qualify, or does the AI clause override this permission?
  4. Does WashU have an FT organisational subscription whose agreement would take precedence over these terms (T&C 1.4), and what does it say about storage and AI use?

#### T-56 cnbc.com (CNBC (Versant Media, LLC))

Rows: `T4-CNBC`

- Terms: <https://www.cnbc.com/terms/>, read 2026-10-04 (live page (CNBC Supplemental Terms, which incorporate https://www.versantmedia.com/terms and https://www.versantmedia.com/terms/prohibited-actions))
- Scraping: **forbidden**. "No Data Extraction. You may not use any software robots, spider, crawlers, or other data gathering or extraction tools, whether automated or manual, to access, acquire, copy, monitor, scrape or aggregate Content or any portion of the Versant Services." (<https://www.versantmedia.com/terms/prohibited-actions>)
- Full-text storage: **forbidden**. "You may not either directly or through the use of any device or other means copy, download, stream, capture, reproduce, duplicate, archive, distribute, upload, publish, modify, translate, broadcast, perform, display, sell, frame, transmit or retransmit the Versant Services or Content," (<https://www.versantmedia.com/terms/prohibited-actions>)
- Excerpts: **forbidden**. "reproduce, duplicate, archive, distribute, upload, publish, modify, translate, broadcast, perform, display, sell, frame, transmit or retransmit the Versant Services or Content, or any part thereof or any materials derived therefrom, unless expressly permitted by us in writing." (<https://www.versantmedia.com/terms/prohibited-actions>)
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: cnbc.com/terms: 'YOUR USE OF THE CNBC WEBSITES, EVENTS, PRODUCTS AND SERVICES ARE GOVERNED BY THE VERSANT TERMS OF SERVICE' (Supplemental Terms 'Updated April 28, 2026'). The Versant ToS ('Effective date September 30, 2025') replace the earlier NBCUniversal terms. The Versant ToS license is 'for your personal and non-commercial use only'. Prohibited Actions: 'No Commercial Use. You may not resell, redistribute or recirculate or make any other commercial use of, or create derivative works or materials utilizing any portion of the Versant Services or Content, whether for profit or for no profit.' The copy and archive ban ends 'unless expressly permitted by us in writing', so consent can be requested. The CNBC Pro and Investing Club terms each say 'You may not scrape, repackage, reproduce, republish...'. The Versant 'Artificial Intelligence' section covers only Versant's own AI tools; I found no clause on third-party AI use. Governing law: New York, with NAM arbitration. I found no specific permissions contact.
- Text owner: Versant Media, LLC (footer: '© 2026 Versant Media, LLC. All Rights Reserved.'). The Versant ToS say Versant 'owns all right, title and interest in and to the copyrights' in Content.
- Access / cost: free; free (articles open without login; CNBC Pro and CNBC+ are paid add-ons) (<https://www.cnbc.com/2026/07/15/morgan-stanley-ms-earnings-q2-2026-.html>)
- robots.txt: www.cnbc.com/robots.txt (2026-10-04): User-agent * allows /{yyyy}/{mm}/{dd}/ articles, /finance/ and /id/.../rss. It disallows /search, /preview/, /proplayer, /zephr/* and /blaize/*. GPTBot, ClaudeBot, anthropic-ai, Scrapy, news-please, trading bots and others get 'Disallow: /' (Allow /select/ only). Sitemaps include sitemap_news.xml and sitemapAll.xml.
- Questions:
  1. Versant (CNBC) terms license use 'for your personal and non-commercial use only', and the Prohibited Actions ban robots, spiders, crawlers and archiving. Does the prototype qualify, and will we ask Versant for written permission?
  2. Versant's 'No Commercial Use' clause covers redistribution 'whether for profit or for no profit'. May we show CNBC excerpts to the project team at all?
  3. Given the 'No Data Extraction' clause, may we store CNBC RSS headline, link and date metadata?

#### T-57 businessinsider.com (Business Insider (Insider Inc., Axel Springer))

Rows: `T4-BUSINESSINSIDER`

- Terms: <https://www.businessinsider.com/terms>, read 2026-10-04 (live page)
- Scraping: **forbidden**. "To monitor, scrape, index, or otherwise copy any of the material on the Sites by means of any robot, spider, or other automatic device, process, or means, regardless of whether such use may be considered a fair use under United States copyright law."
- Full-text storage: **forbidden**. "You must not reproduce, distribute, modify, create derivative works of, publicly display, publicly perform, republish, download, store or transmit any of the material on our Sites, except as incidental to normal web browsing,"
- Excerpts: **forbidden**. "(including any use of the Sites' content for training, fine tuning, or grounding the machine learning or AI system or as part of a retrieval-augmented generation)."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: 'Last updated: August 14, 2026'. 'You may access the material on the Sites only for your own personal, non-commercial use.' The full AI prohibition (§9) reads: 'To develop any software program, model, algorithm, or generative AI tool, including, but not limited to, training or using the Sites' content in connection with the development or operation of a machine learning or artificial intelligence (AI) system' and continues with the grounding and RAG wording quoted above. §5 'REPRINTS AND PERMISSIONS' links to https://www.parsintl.com/publication/business-insider/. Governing law: New York. Contact: feedback@businessinsider.com. The Atom feed carries <rights>Insider Inc. 2023</rights> and the subtitle 'All Content from Business Insider Excluding Premium'.
- Text owner: Insider Inc. (footer: 'Insider Inc. All rights reserved.'; a subsidiary of Axel Springer)
- Access / cost: paywall; not published
- robots.txt: www.businessinsider.com/robots.txt (2026-10-04): User-agent * allows /finance and article slugs. It disallows /*/rss, /*.rss, /archives, /categories, /cms/ and /author/*/date. 'Disallow: /' applies to anthropic-ai, ClaudeBot, CCBot, Scrapy, newspaper and Diffbot. /sitemap/ is open and lists monthly sitemaps from 2008-01. feeds.businessinsider.com/robots.txt returns 404.
- Questions:
  1. Business Insider terms forbid scraping 'regardless of whether such use may be considered a fair use' and any use of content for AI 'grounding' or 'retrieval-augmented generation'. Do we limit BI to Google/Bing headline and link metadata, or ask for permission through Parsintl?
  2. BI terms bar downloading and storing site material except in normal browsing. May we store BI Atom feed items (headline, link, date) as metadata?
  3. BI terms allow 'personal, non-commercial use' only. Does the prototype qualify?

#### T-58 news.google.com (Google LLC (Google News RSS))

Rows: `T4-GOOGLENEWS`

- Terms: <https://policies.google.com/terms>, read 2026-10-04 (live page (Google Terms of Service 'Effective July 30, 2026'), plus the <copyright> element in the live RSS feed)
- Scraping: **forbidden**. "using automated means to access content from any of our services in violation of the machine-readable instructions on our web pages (for example, robots.txt files that disallow crawling, training, or other activities)"
- Full-text storage: **unclear**. "This XML feed is made available solely for the purpose of rendering Google News results within a personal feed reader for personal, non-commercial use. Any other use of the feed is expressly prohibited." (<https://news.google.com/rss/search?q=%22Edward+Jones%22+advisors+when:30d&hl=en-US&gl=US&ceid=US:en>)
- Excerpts: **unclear**. "a newspaper article displayed in Google News. You may not use this content without that person or organization’s permission, or as otherwise allowed by law."
- Verification: scraping 'forbidden': 2/2 checkers confirmed.
- Other clauses: The scraping verdict rests on two things together: the Google ToS clause on automated access against robots.txt, and news.google.com/robots.txt, which disallows /rss/ for User-agent *. The feed's <copyright> element reads 'Copyright © 2026 Google. All rights reserved.', then the restriction quoted above, then 'By accessing this feed or using these results in any manner whatsoever, you agree to be bound by the foregoing restrictions.' The Google ToS also say 'You may not copy, modify, distribute, sell, or lease any part of our services or software.' Governing law: California, in Santa Clara County courts. Route and article: Google's terms govern the feed (headline, source, pubDate, encoded link). Each linked article stays under its own publisher's terms, for example InvestmentNews, AdvisorHub, Barron's (Dow Jones terms above) and PR Newswire. The feed holds no article text, so 'full text' here means only headline and source metadata.
- Text owner: Feed: '© 2026 Google'. Headlines and articles belong to the original publishers named in each item's <source url> (for example InvestmentNews, AdvisorHub, PR Newswire, Barron's).
- Access / cost: free; free (<https://news.google.com/rss/search?q=%22Edward+Jones%22+advisors+when:30d&hl=en-US&gl=US&ceid=US:en>)
- robots.txt: news.google.com/robots.txt (2026-10-04): 'User-agent: * Disallow: /' with Allow only for /, /home, /topics/, /publications/, /stories/, /swg/ and /about. That means /rss/search and /rss/articles/ (the encoded redirect links) are disallowed for generic agents. Googlebot is limited to the home paths. GPTBot, ClaudeBot, anthropic-ai and others get Disallow: /.
- Questions:
  1. Google News RSS: the feed's copyright notice limits use to 'rendering Google News results within a personal feed reader for personal, non-commercial use', robots.txt disallows /rss/ for all agents, and the Google ToS ban automated access that goes against robots.txt. May the prototype use Google News RSS at all, even as a discovery route?
  2. Resolving Google-encoded /rss/articles/ links means automated requests to a robots-disallowed path. Is that acceptable, or should we keep only headline, source and date without resolving the links?
  3. The Google ToS say content like 'a newspaper article displayed in Google News' needs the publisher's permission 'or as otherwise allowed by law'. Who decides whether short quotes from linked articles count as 'allowed by law' (fair use) for this prototype?

#### T-59 bing.com (Microsoft Corporation (Bing News RSS))

Rows: `T4-BINGNEWS`

- Terms: <https://www.microsoft.com/en-us/servicesagreement>, read 2026-10-04 (live page (Microsoft Services Agreement 'Published: July 30, 2026', 'Effective: September 30, 2026'), plus the <copyright> element in the live RSS feed)
- Scraping: **unclear**. "vi. Don’t circumvent any restrictions on access to, usage, or availability of the Services (e.g., attempting to “jailbreak” an AI system or impermissible scraping)."
- Full-text storage: **unclear**. "These XML results may not be used, reproduced or transmitted in any manner or for any purpose other than rendering Bing results within an RSS aggregator for your personal, non-commercial use. Any other use of these results requires express written permission from Microsoft Corporation." (<https://www.bing.com/news/search?q=site%3Abizjournals.com+Edward+Jones&format=rss>)
- Excerpts: **unclear**. "are for your noncommercial, personal use only. Other uses, including downloading, copying, or redistributing these materials, or using these materials or products to build your own products, are permitted only to the extent specifically authorized by Microsoft or rights holders,"
- Other clauses: The MSA does not define 'impermissible scraping', and robots.txt does not disallow /news/search, so the scraping verdict is unclear rather than forbidden. The excerpts quote comes from MSA 'f. Bing and MSN. i. Bing and MSN Materials. The articles, text, photos, maps, videos, video players, and third-party material available on Bing and MSN, including through Microsoft bots, applications and programs, ...' and ends 'or allowed by applicable copyright law.' The feed's <copyright> reads 'Copyright \xc2\xa9 2026 Microsoft. All rights reserved.' (the mis-encoded © is how it appears in the feed), followed by the restriction quoted above and 'By accessing this web page or using these results in any manner whatsoever, you agree to be bound by the foregoing restrictions.' The MSA applies to 'Microsoft consumer online products and services'. Governing law (US): 'the laws of the state where you live (or, if a business, where your principal place of business is located) govern all claims'. Route and article: Microsoft's terms govern the feed (title, about 200-character description snippet, pubDate, News:Source, apiclick link). The linked article stays under its publisher's terms, for example bizjournals.com, Reuters, FT and Bloomberg as above.
- Text owner: Feed: '2026 Microsoft'. The titles, description snippets and articles belong to the original publishers named in <News:Source> (for example The Business Journals, InvestmentNews, Financial Planning).
- Access / cost: free; free (<https://www.bing.com/news/search?q=site%3Abizjournals.com+Edward+Jones&format=rss>)
- robots.txt: www.bing.com/robots.txt (2026-10-04): User-agent * disallows /search, /Search, /results, /url, /aclick, /Proxy.ashx and /static/. It has no rule for /news/, so /news/search?...&format=rss and /news/apiclick.aspx are not disallowed. msnbot-media gets Disallow: / (except /th?).
- Questions:
  1. Bing News RSS: results may be used only for 'rendering Bing results within an RSS aggregator for your personal, non-commercial use', and any other use 'requires express written permission from Microsoft Corporation'. Does our ingest script plus Postgres storage qualify, or do we need Microsoft's permission or a licensed Microsoft route?
  2. Microsoft Services Agreement: Bing and MSN materials are 'for your noncommercial, personal use only'. Does a team prototype for Edward Jones's strategy office qualify?
  3. The MSA bans 'impermissible scraping' without defining it, and robots.txt allows /news/search. Is a once-a-day scripted fetch of a few Bing News RSS queries acceptable?

#### T-60 factiva.com (Dow Jones & Company (Factiva))

Rows: `T4-FACTIVA`

- Terms: <https://global.factiva.com/FactivaLogin/tou/default.aspx?fcpil=en>, read 2026-10-04 (live page (Factiva Terms of Use; page also shows 'Last Revised September 1, 2013'))
- Scraping: **forbidden**. "use the Information or the attached Codes in conjunction with any systems or applications that enable any program trading (including without limitation algorithmic trading programs), data mining, text mining, or trend analysis function"
- Full-text storage: **forbidden**. "(f) create or store in electronic form any shared library or archive of Information which could be used as a research application; (g) store any Information for more than 30 days"
- Excerpts: **forbidden**. "(a) reproduce, distribute, display, sell, publish, broadcast or circulate the Information to any third party, nor make the Information available for any such use"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed. excerpts 'forbidden': 2/2 checkers confirmed.
- Other clauses: Personal use only: '2.1 You may access, download and print the Information for your own personal use.' The TOU gives way to the institution's own agreement: 'unless your employer has signed an agreement covering your use of this Service (a “Corporate Agreement”), in which case the terms contained in such signed Corporate Agreement shall apply'. WashU's Dow Jones agreement is not public, so these verdicts come from the click-through TOU. Fair use is excluded by contract: 'You acknowledge that rights to use the Information in these Terms of Use are contractual and exist independently of copyright law'. Purge on termination: 'On termination of your access to the Service, you shall promptly purge all Information from the Service that you have stored.' WSJ and Barron's: 'Your access to and use of The Wall Street Journal and Barron’s shall be governed by their online terms of use'. The robots.txt notice at https://global.factiva.com/robots.txt says: 'Collection of content and other data on global.factiva.com through automated means is prohibited unless you have express written permission from Dow Jones & Company, Inc. or its affiliates (including Factiva, Inc.)'. It also says: 'We expressly prohibit any use of our content or data for any machine learning or artificial intelligence purposes'. Contact for consent: copyright@dowjones.com (named in robots.txt). The WashU TDM guide lists Factiva among publishers that 'do not permit text and data mining or require additional fees'. WashU limits Factiva to 6 concurrent users. Governing law: not reached in the sections read.
- Text owner: Licensed content. The original publishers own the text (Dow Jones for WSJ/Barron's; third-party licensors for the rest). TOU 1.3: 'The Information contained within the Service is either licensed from third party information providers or is proprietary to Dow Jones.'
- Access / cost: library; not published
- robots.txt: global.factiva.com/robots.txt: 'User-agent: * Disallow: /', plus a NOTICE banning automated collection without written permission and any ML/AI use (2026-10-04). The access route libproxy.washu.edu/robots.txt also has 'User-agent: * Disallow: /' (2026-10-04).
- Questions:
  1. Factiva (Dow Jones) TOU 2.2(c) bars using Information with data-mining or text-mining systems, and robots.txt bans automated collection without Dow Jones's written permission. Do we ask copyright@dowjones.com for permission, or keep Factiva for manual lookup only?
  2. Factiva TOU 2.2(f)/(g) forbid a stored archive and keeping any Information more than 30 days. Does WashU's signed Dow Jones agreement (which overrides the click-through TOU) say otherwise, and is metadata + link with no text acceptable for Factiva items?
  3. Factiva TOU 2.1 allows only 'your own personal use' and 2.2(a) forbids display to any third party. May the prototype show short Factiva quotes to the project lead or the Edward Jones CSO office, and does a fellow WashU teammate count as a 'third party'?
  4. Factiva robots.txt prohibits 'any use of our content or data for any machine learning or artificial intelligence purposes'. Does sending a Factiva passage to the prototype's LLM answer step count as such use?

#### T-61 lexisnexis.com (LexisNexis (Nexis Uni, RELX))

Rows: `T4-NEXISUNI`

- Terms: <https://www.lexisnexis.com/en-us/terms/general/default.page>, read 2026-10-04 (live page (LexisNexis General Terms and Conditions, 'Effective Date: June 5, 2026'; https://www.lexisnexis.com/terms/general.aspx redirects here))
- Scraping: **forbidden**. "(a)Access or use the Online Services via mechanical, programmatic, robotic, scripted or any other automated means is strictly prohibited without our express prior written permission."
- Full-text storage: **forbidden**. "(b)except under Section 1.1(d), (i)download and store Materials in a database; or (ii)store copyrighted Materials for more than ninety days;"
- Excerpts: **unclear**. "(c)excerpt or quote insubstantial portions of the Materials;"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: The quoting grant in 1.1 is conditional: 'a non-exclusive, non-transferable, limited right to access and use, in the ordinary course of your business, the Online Services and Materials as follows:' The 'you' is the subscribing customer (WashU). Whether this project falls in WashU's ordinary course is not for us to decide. AI clause 1.2(h): 'The uploading or submission of Materials into third party applications, software or websites that utilize AI Technologies is prohibited except as expressly permitted under Section 1.1(e) with respect to Compliant AI Tools.' Under 1.1(e), a Compliant AI Tool needs zero data retention and a no-training commitment, and use must not be 'systematic or bulk extraction'. 1.2(i) bars 'Agentic AI' access without written permission. Ownership: 'All right, title, and interest in the Online Services and Materials belongs to LN or its third-party suppliers of Materials.' WashU's Nexis Uni subscription agreement is not public; the GTC say they are incorporated by reference into the customer's Agreement. The WashU-mediated route is the LexisNexis API (https://libguides.wustl.edu/lexisapi/request). Its terms: 'Use of the API is limited to scholarly research projects or teaching. Personal, for-profit, non-academic research, or other uses of the API are strictly forbidden. You may not use Lexis API to train an AI model, public or private.' Eligibility: 'Masters students working on a thesis and undergraduates working on a capstone or thesis are eligible, with a faculty advisor.' The WashU TDM guide lists LexisNexis TDM coverage as 'LexisNexis Licensed News only (does not include company reports or legal materials)'.
- Text owner: Licensed content. LexisNexis and its third-party suppliers own it (the original publishers of each news title).
- Access / cost: library; not published
- robots.txt: advance.lexis.com/robots.txt (the Nexis Uni host) returns HTTP 404, so there is no robots file (2026-10-04). www.lexisnexis.com/robots.txt blocks some AI agents and internal directories only. The access route libproxy.washu.edu/robots.txt has 'User-agent: * Disallow: /' (2026-10-04).
- Questions:
  1. Nexis Uni: LexisNexis GTC 1.2(a) prohibits scripted access without written permission. The only sanctioned automated route is the WashU-mediated LexisNexis API, limited to 'scholarly research projects or teaching' for capstone/thesis students with a faculty advisor. Does this Edward Jones project qualify, and should we apply?
  2. Nexis Uni: LexisNexis GTC 1.2(b) forbids storing Materials in a database or for more than 90 days. Is metadata + an insubstantial excerpt + link acceptable for Nexis Uni items?
  3. Nexis Uni: LexisNexis GTC 1.1(c) lets us quote 'insubstantial portions', but only 'in the ordinary course of your business', where the customer is WashU. Does a student prototype delivering answers to Edward Jones fall within that?
  4. Nexis Uni: LexisNexis GTC 1.2(h)/1.1(e) allow submitting Materials only to a 'Compliant AI Tool' (zero data retention, no training) for non-systematic use. Does the prototype's LLM provider setup qualify, or must Nexis Uni text stay out of the LLM step?

#### T-62 newsbank.com (NewsBank, inc.)

Rows: `T4-NEWSBANK`

- Terms: <https://www.newsbank.com/terms-and-conditions-use>, read 2026-10-04 (live page (website Terms and Conditions of Use; the Access World News product license is not public))
- Scraping: **silent**. "you may be granted a nonexclusive, nontransferable, limited license to access for research purposes the information or materials available on Our Web Sites subject to the specific agreements, policies, instructions, statements, laws, and regulations relating to such services and such materials."
- Full-text storage: **unclear**. "you may not produce, publish, transmit, distribute, display, modify, create derivative works from, or exploit in any way, in whole or in part, any of the contents of Our Web Sites or any related software without the prior written consent of us or our content providers."
- Excerpts: **unclear**. "These Terms and Conditions do not govern services available from NewsBank (even those services that may be ordered or provided by us through Our Web Sites) to the extent that any specific terms and conditions apply to such services."
- Other clauses: The public website terms say nothing about robots or automated access. They yield to service-specific agreements, and WashU's Access World News license is not public. That is why storage and excerpts are 'unclear': the website clause prohibits reproduction or display 'in whole or in part' without consent, but may not govern the subscription product. Ownership: 'All content included on Our Web Sites and their related software is our property or the property of our content providers, and is protected by copyright law.' Consent contact on the page: webmaster@newsbank.com. Governing law: 'governed by, and will be construed in accordance with, the laws of the State of Florida'. WashU Libraries' general guidance (separate entry) also applies.
- Text owner: Licensed content. NewsBank's content providers own it (e.g. the St. Louis Post-Dispatch publisher for Post-Dispatch text).
- Access / cost: library; not published
- robots.txt: infoweb.newsbank.com/robots.txt (the product host): 'User-agent: * Disallow: /' (2026-10-04). The www.newsbank.com marketing site allows AI search agents and blocks GPTBot, ClaudeBot and Google-Extended. The access route libproxy.washu.edu/robots.txt has 'Disallow: /' (2026-10-04).
- Questions:
  1. NewsBank's public website terms defer to product-specific terms that are not published, and infoweb.newsbank.com robots.txt disallows everything. Can the library share what WashU's Access World News license says about scripted access, storing full text and quoting short passages?
  2. NewsBank website terms forbid reproducing or displaying contents 'in whole or in part' without 'prior written consent of us or our content providers'. If the AWN license is silent, do we request consent from NewsBank or from the Post-Dispatch publisher, or treat NewsBank as manual lookup only?

#### T-63 proquest.com (ProQuest LLC (part of Clarivate))

Rows: `T4-PROQUEST`

- Terms: <https://www.proquest.com/info/termsAndConditions>, read 2026-10-04 (live page (ProQuest platform Terms & Conditions with Exhibit A: Permitted Uses))
- Scraping: **forbidden**. "e. Perform automated searches against ProQuest's systems (except for non-burdensome federated search services), including automated "bots," link checkers or other scripts;"
- Full-text storage: **forbidden**. "k. Download all or parts of the Service in a systematic or regular manner or so as to create a collection of materials comprising all or a material subset of the Service, in any form."
- Excerpts: **unclear**. "Customer and its Authorized Users are permitted to display and use reasonable portions of information contained in the Service for educational or research purposes, including illustration, explanation, example, comment, criticism, teaching, or analysis."
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: Purpose limit: 'Access and use of the Service is only for the internal, research purposes of Customer and/or its Authorized Users as further described in Exhibit A.' Text mining is also restricted (Exhibit A 9): 'i. Text mine, data mine or harvest metadata from the Service;' Redistribution: 'j. Communicate or redistribute materials retrieved from the Service;' Copies are allowed only in part (Exhibit A 1b): 'a reasonable portion of articles or other works ... for its own internal or personal use as allowed under the doctrines of "fair use"'. Some content carries its own terms (s.5 Supplemental Terms). On termination for breach, the customer must 'destroy any files, information, data or software derived from any terminated Service'. Place of contract: Ann Arbor, MI (s.15). The WashU TDM guide (https://libguides.wustl.edu/textmining/tdm-resources) says: 'The following publishers do not permit text and data mining or require additional fees for access: ProQuest ( ProQuest TDM Studio available at additional cost) Factiva EBSCO'. No TDM Studio price is published on https://about.proquest.com/en/products-services/TDM-Studio.
- Text owner: Licensed content. Third-party licensors own it (the original publishers, e.g. SourceMedia dba Arizent for Financial Planning, Informa for Wealth Management). Quote: 'The content provided as part of the Service is primarily owned and supplied to ProQuest under agreement with third party licensors'.
- Access / cost: library; not published
- robots.txt: www.proquest.com/robots.txt (2026-10-04) has no blanket block for '*'. It disallows /docview/*PQ/1, /*?accountid=* (the form WashU's entry links use), /login, /openview/, /docprintview/, /runSearch and /myresearch/; /docview/{id} itself is not disallowed. GPTBot and ChatGPT-User are disallowed from /. The access route libproxy.washu.edu/robots.txt has 'Disallow: /' (2026-10-04).
- Questions:
  1. ProQuest T&C Exhibit A 9(e), (i) and (k) forbid bots and scripts, text mining and systematic downloads. The paid route is TDM Studio (no published price). Is TDM Studio in scope and budget, or is ProQuest manual lookup only?
  2. ProQuest Exhibit A 1(a) allows displaying 'reasonable portions' for 'educational or research purposes', and s.1 limits use to 'internal, research purposes'. Does the prototype that answers questions for Edward Jones's CSO office count as educational/research use under WashU's ProQuest license?

#### T-64 libguides.wustl.edu (Washington University Libraries (licensee guidance for all four databases))

Rows: `T4-FACTIVA`, `T4-NEXISUNI`, `T4-NEWSBANK`, `T4-PROQUEST`

- Terms: <https://libguides.wustl.edu/responsible-electronic-resource-use>, read 2026-10-04 (live page (Responsible Electronic Resource Use: General Terms; also read https://libguides.wustl.edu/textmining and https://libguides.wustl.edu/textmining/tdm-resources))
- Scraping: **forbidden**. "Using software or other automated tools to systematically download or retain substantial portions of information licensed content, such as robots or spiders"
- Full-text storage: **forbidden**. "Modifying, altering or creating derivatives (such as your own database of materials) without the permission of the licensor Example: Compiling portions of data from a database to create another database for a subset of researchers."
- Excerpts: **unclear**. "Use of small amounts of attributed quotes in your own works"
- Verification: scraping 'forbidden': 2/2 checkers confirmed. full_text_storage 'forbidden': 2/2 checkers confirmed.
- Other clauses: Small attributed quotes are listed under 'Permitted Use', but the guide also limits use overall: 'Each patron is responsible for ensuring they use these products solely for noncommercial, educational, scholarly or research use.' Prohibited: 'Selling or re-distributing content, or providing it to an employer (commercial use)'. AI clause: 'Authorized Users may not use any licensed content for the purpose of creating, training, enhancing, developing, maintaining, or contributing to any AI, Machine Learning System, or Large Language Model without express permission.' The TDM guide says: 'Avoid web scraping or downloading large amounts of content from databases to which the library subscribes.' It lists ProQuest and Factiva among publishers that do not permit TDM or charge extra. LexisNexis TDM is possible only via the mediated API (https://libguides.wustl.edu/lexisapi). Consequence of misuse: 'Violation may result in loss of access to these resources for the entire Washington University community.' Contacts: Digital Humanities Librarian Sarah Swanz (TDM and Lexis API guides) or the subject librarian.
- Text owner: n/a (guidance only). The vendors and original publishers own the text.
- Access / cost: library; not published
- robots.txt: libguides.wustl.edu/robots.txt (2026-10-04): 'User-agent: *' with 'Crawl-delay: 10'; disallows /az.php? and /az/databases? (the database A-Z list). Guide pages are allowed. Several named crawlers and AI agents (Amazonbot, Applebot, CCBot, ChatGPT, ChatGPT-User and others) are blocked from /. libproxy.washu.edu/robots.txt: 'User-agent: * Disallow: /'.
- Questions:
  1. WashU Libraries' responsible-use guide bars using licensed content for 'creating, ... developing, maintaining, or contributing to any AI, Machine Learning System, or Large Language Model without express permission'. Does a retrieval + LLM answer prototype fall under this, and who at the library can grant that permission?
  2. WashU Libraries' guide limits library databases to 'noncommercial, educational, scholarly or research use' and prohibits 'providing it to an employer (commercial use)'. Does showing quotes from Factiva, Nexis Uni, NewsBank or ProQuest to Edward Jones's CSO office (via the project lead) count as commercial use or providing to an employer?
  3. WashU Libraries' guide forbids creating 'your own database of materials' without licensor permission. Should library-database items be left out of ingest entirely (manual lookup + citation only), or is metadata + short excerpt + link acceptable?

## Tier 5: thematic research (C3, #5)

Owner: C3 (Jieyu Hu). Issue #5; ExecPlan [plans/0005-thematic-matrix.md](../plans/0005-thematic-matrix.md); spec [specs/thematic.md](../specs/thematic.md). Researched 2026-10-20 from the live sites and search results. **Nothing has been ingested**; ingestion is #81.

39 rows (`T5-*`): 22 research, 12 survey, 5 regulatory. Access: 32 free, 3 free-registration, 1 metered, 1 paywall (Cerulli reports), 2 licensed (Goldman and BofA client research).

How the tier 5 rows differ from tiers 3-4:

- `entity_id` is `THEME` (the pattern `THEME:research` in `evals/questions.yaml`); `doc_type` is `research`; `owner` is C3. In `data/manifest.csv` these documents keep `entity_id` empty and record the publisher (specs/thematic.md).
- `notes` starts with `Kind: research|survey|regulatory. Themes: <ids>. Questions: <ids>.` Theme ids are the seed list in `config/entities.yaml` `themes:`; `tests/test_source_matrix.py` checks them.
- For surveys, `notes` records the sample and fieldwork dates as the publisher states them, where found. "Copy at ingest" means the methodology page has to be read when the document is stored.
- Reports by firms in the competitive set (Goldman, BofA, Morgan Stanley, J.P. Morgan, UBS, Schwab, Fidelity, Edward Jones) are theme evidence only. They are never a source for that firm's own figures (ground rule 4: filings).
- `terms_read_on` is the date the terms page was located. The clauses were not quoted one by one, because ADR-007 already decides use (see T-65). `earliest_available` is `TODO-verify` throughout: the oldest edition is checked when #81 picks a source.
- `last_checked` / `url_status` / `sample_status` are left to the URL checker (next monthly run).

### Coverage by theme

A row can serve several themes. The spec target for W5 is at least 3 *documents* from at least 2 publishers per theme. These are *sources*, so the target is checked again after #81 ingests.

| Theme | Rows | Publishers | Strongest rows |
|---|---|---|---|
| advice_future | 33 | 28 | broad: most outlooks touch it |
| ai_advice | 19 | 18 | T5-ACCENTURE-WM (advisor survey), T5-EY-GWRR (client survey), T5-DELOITTE-INSIGHTS, T5-BCG-GWR (2024 GenAI edition), T5-KITCES-RESEARCH (tech use), T5-FINRA-OVERSIGHT / T5-SEC-EXAMS (regulator view) |
| fees_pricing | 15 | 14 | T5-SEC-REGBI, T5-SEC-EXAMS, T5-DOL-FIDUCIARY, T5-FINRA-OVERSIGHT (regulatory); T5-ICI-FEES, T5-MORNINGSTAR, T5-VANGUARD-RESEARCH (research) |
| younger_investors | 13 | 12 | T5-FINRAF-NFCS, T5-CFPBOARD-SURVEYS, T5-NM-PP, T5-SCHWAB-MWS, T5-BOFA-PB-STUDY, T5-UBS-NEXTGEN |
| wealth_transfer | 13 | 11 | T5-CERULLI-WP, T5-CAPGEMINI-WWR, T5-UBS-GWR (published estimates, each with its own vintage); T5-FED-SCF (primary data); T5-BOFA-PB-STUDY, T5-EDJ-AGEWAVE (surveys) |
| advisor_selection | 7 | 7 | T5-CFPBOARD-SURVEYS, T5-NM-PP, T5-FINRAF-NFCS, T5-JDPOWER-ISS, T5-FIDELITY-III |
| advisor_recruiting | 6 | 5 | T5-MCKINSEY-INSIGHTS (advisor shortage), T5-FINRA-SNAPSHOT, T5-KITCES-RESEARCH, T5-CERULLI-WP |
| mass_affluent | 4 | 4 | T5-BOFA-INSTITUTE, T5-FED-SCF, T5-JPM-GTR, T5-CERULLI-REPORTS (thin; not in Q16-Q21) |

### Coverage of Q16-Q21

| Q | Needs (passes_if) | Rows |
|---|---|---|
| Q16 | Spread of positions on future advice, attributed and dated | 29 rows; regulatory direction from T5-SEC-*, T5-DOL-FIDUCIARY, T5-FINRA-OVERSIGHT; surveys and consultancies for the rest |
| Q17 | Named deployed tools vs aspiration | 17 rows. Tier 5 gives the industry and regulator view; the firms' own claims are tier 3 (C2). T5-ACCENTURE-WM and T5-KITCES-RESEARCH are advisor-side evidence of tools in use |
| Q18 | Disclosed pricing vs regulation vs research vs opinion | 14 rows, labelled by Kind (regulatory / research / survey). Form ADV fee schedules are C1 (`*:adv`) |
| Q19 | Evidence on younger investors, then stop at "should" | 11 rows |
| Q20 | Survey findings with source, sample and date; disagreements shown | 10 rows. Surveys with different populations (all adults, investors, wealthy) are noted per row, so disagreements can be explained |
| Q21 | Published estimates (source and vintage) kept apart from what firms do | 11 rows. Estimates: T5-CERULLI-WP, T5-CAPGEMINI-WWR, T5-UBS-GWR; firm actions are tier 3 (C2) |

### Cerulli: library access

- 2026-10-20: the WashU Libraries Database Finder (<https://libguides.wustl.edu/az/databases>) returns **0 databases for "cerulli"**. No library route has been found so far.
- Free route: Cerulli white papers (`T5-CERULLI-WP`), behind a short form, incl. its wealth-transfer white paper (October 2025).
- Written answer: the tech lead decided on 2026-10-20 that no email to the library is needed. The answer on record is the Database Finder result above (no WashU subscription), and Cerulli is used through its free white papers. Paid reports stay out unless the team buys one.
- Note for any future library route: the WashU responsible-use guide (T-64) bars building "your own database of materials" from licensed content and using it with AI tools, whatever ADR-007 allows on our side.

#### T-65 Tier 5 publishers (C3): terms and ADR-007

Rows: all `T5-*`.

- ADR-007 (2026-10-14) settles use for this internal, non-commercial prototype: no permission requests (T-01, T-02), scraping allowed with a polite user agent (T-08), and "Cerulli and other library research (C3) may be stored in full". The verdict columns are therefore `unclear` (not read clause by clause), not a finding that the sites forbid or allow anything.
- Where a source's own licence binds a third party, ADR-007 cannot settle it. This applies to anything reached through a WashU library database (T-64) and to client-only research (T5-GS-GIR, T5-BOFA-GR). Those rows stay metadata only until the access question is answered.
- US federal government works (SEC, DOL, Federal Reserve) are public domain (17 U.S.C. 105). sec.gov and dol.gov answer 403 to scripts without a declared identity.
- Several sites answer 403, 202 or time out for scripts (bcg.com, pwc.com, ubs.com, ici.org, mckinsey.com, aboutschwab.com, morningstar.com, sec.gov, dol.gov, trust.cfainstitute.org). Under T-08 they are fetched in a browser or with a polite, identified user agent.

## Considered and rejected

Candidates that were looked at and left out, with the reason. Anything here can come back with a PR that adds a row.

| Candidate | Reason |
|---|---|
| MS IR earnings-call text transcript | Not posted on morganstanley.com IR: the per-call and press-release pages say only that playback will be available via webcast. Text transcripts exist only from third parties such as Seeking Alpha and GuruFocus (vendor-copyrighted, not tier 3 IR). |
| MS quarterly earnings slides | Not published as a separate deck: no quarterly earnings slides are posted after 2013, and the calls refer to the earnings release and financial supplement. The only earnings-linked deck is the annual 4Q Strategic Update (row MS-IR-DECK-STRATEGICUPDATE). |
| MS investor day | No standalone investor day or business-update event on the IR site; the January Strategic Update deck is the equivalent. |
| MS monthly metrics release | Morgan Stanley publishes no monthly operating metrics. E*TRADE's monthly activity reports (DARTs, via Business Wire, last seen May 2020) predate the acquisition. The current E*TRADE monthly Sector Rotation Study measures sentiment, not metrics, and is covered under MS-NEWSROOM-PRESS-ETRADE. |
| MS Fixed Income Investor Presentations (IR presentations page) | Quarterly decks for creditors with little that is specific to Wealth Management; noted inside MS-IR-DECK rather than given their own row. |
| Business Wire copies of MS press releases | Duplicate distribution channel for the same newsroom releases. |
| 10-K / 10-Q PDFs mirrored on the MS IR site | These are SEC filings (tier 2, owned by C1). |
| Schwab sell-side conference presentations (deck/transcript) | The IR site has no sell-side conference listings. The events page (aboutschwab.com/schwabevents) shows only Schwab-hosted events, and aboutschwab.com/events redirects to schwabjobs.com. |
| Schwab CFO Commentary (aboutschwab.com/cfo-commentary) | Still linked in the pressroom footer but now redirects to the IR overview; no longer published. |
| Schwab Trading Activity Index (STAX) monthly release | A monthly retail-trading sentiment index, not wealth-management or net-new-asset evidence. It is published on aboutschwab.com/schwab-trading-activity-index and the pressroom. |
| Pressroom tag-filtered RSS feeds (e.g. ?tags=Schwab-Advisor-Services-News) | Stale: newest items are from 2020 and recent releases carry no tags. Use the unfiltered feed plus a keyword filter instead. |
| Business Wire copies of Schwab releases (mms.businesswire.com PDFs) | Duplicate distribution of the same IR/pressroom releases; the IR/pressroom copy is the canonical source. |
| Other third-party copies of Schwab call transcripts (webull, financialfilings.com and similar) | Aggregators or re-licensed copies; the main third-party transcript sites (Motley Fool, Seeking Alpha, Investing.com, Yahoo, AlphaStreet, MarketBeat, Roic.ai) have rows. |
| BAC monthly metrics release (BAC-IR-MONTHLY) | BAC publishes no monthly operating-metrics report. The IR menu has quarterly earnings, events, presentations, annual meeting and investor day, and none of them is monthly. The nearest substitute is the quarterly supplement. |
| BAC earnings-call webcast replay (audio-only transcript row) | Text transcripts exist for 1Q26 and 2Q26. The event page 'Earnings Webcast Audio' link points to a registration-gated #register anchor. Quarters before 2026 show neither a transcript nor a replay on the IR page. |
| Merrill-specific newsroom on ml.com / merrill.com | Not found. ml.com/press-releases.html and ml.com/news.html return 404, and the 404 page links to the BAC newsroom home. Both homepages show no news links. Legacy ir.ml.com does not resolve. Merrill news goes through the BofA newsroom (MER-BOFANEWS-PRESS). |
| BofA newsroom RSS feed (newsroom.bankofamerica.com/content/newsroom/press-releases.html/rss) | The link is labelled 'RSS News Feed' but returns the HTML press-releases page (text/html, same size), not a feed. |
| BAC IR events RSS (/events-and-presentations/events/rss) and /rss | Both return 404. The only working IR feed is /events-and-presentations/presentations/rss (noted on BAC-IR-DECK-EARNINGS). |
| MER rows for supplement/deck/transcript | Merrill-split figures (Merrill Wealth Management revenue and client balances) appear only inside BAC GWIM documents. Under the MER vs BAC rule these are BAC rows with segment GWIM. |
| InvestmentNews Merrill tag (investmentnews.com/tag/merrill-lynch-wealth-management) | Seen in a search result, but curl returns 404. |
| RJF IR RSS feed | No RSS link found on raymondjames.com IR, newsroom or recruiting pages (2026 captures). IR offers only an email sign-up iframe on /investor-relations/contact-information, noted on RJF-NEWSROOM-PRESS. |
| RJF sell-side conference webcast replays (transcript, audio-only) | 2025-26 conference entries on the presentations page have no webcast or slides link (capture 2026-05-21), so there is nothing to row. The deck row covers past RJ Institutional Investors Conference PDFs. |
| RJF branch-microsite press release copies (e.g. /mobile-branch/about-us/press-releases/2026/05/20/...) | Duplicates of newsroom items on advisor branch microsites. Use RJF-NEWSROOM-PRESS instead. |
| RJF Segment Operating Results by Quarter (filings-and-reports, xlsx) | One-off FY2017-FY2018 recast with its 8-K (reporting changes effective FY2019). Not a recurring supplement. C1 territory if wanted. |
| RJF annual shareholders meeting webcast (virtualshareholdermeeting.com/RJF2026) | Governance meeting, not wealth-segment evidence. Out of scope for the question bank. |
| Raymond James Canada newsroom (raymondjames.ca/news-and-media/press-releases) | Canadian subsidiary. The core comparison is US Private Client Group recruiting and affiliation. |
| Other third-party RJF transcript or summary sites (Webull, Quartr, Stock Taper, GuruFocus) | Aggregators, AI summaries or paywalled re-licensed text (Quartr is the upstream of the Yahoo and MarketBeat rows; GuruFocus returns 403 and was not confirmed). The main third-party transcript sites have rows. |
| RJF 8-K Ex.99.1 copies (earnings, monthly operating data, investor day deck) | Tier 2 (C1). Mentioned in notes as an alternative path only. |
| S&P Capital IQ (transcripts) | tier 1 / licensed, blocked by ADR-000 |
| LSEG / Refinitiv StreetEvents | tier 1 / licensed, blocked by ADR-000 |
| FactSet CallStreet | tier 1 / licensed, blocked by ADR-000 |
| Bloomberg (BBG transcripts) | tier 1 / licensed, blocked by ADR-000 |
| AlphaSense | tier 1 / licensed, blocked by ADR-000 |
| Quartr (quartr.com event pages / app / API) | Public event pages are summaries only. Full transcripts sit behind login, a paid plan or the API (licensed). Quartr is the upstream provider of the Yahoo Finance and MarketBeat transcripts, which matters for the ToU step. |
| Nasdaq.com transcripts | Only legacy Motley Fool-syndicated transcripts through about 2022 (e.g. BAC Q1 2022). No 2026 transcripts found for MS/SCHW/BAC/RJF. Its /press-release/ pages are wire reposts, not a separate source. |
| Schwab on PR Newswire (prnewswire.com/news/charles-schwab/) | Sporadic APAC and promo items only (3 items, latest 2026-05-12). Schwab's primary wire is Business Wire. |
| Edward Jones Canada on GlobeNewswire | One release only (2024-09-13 Fredericton branch). Not an active channel; EDJ Canada uses newswire.ca. |
| Merrill on Business Wire | Legacy only (items up to about 2021). Current Merrill releases go out on PR Newswire under Bank of America Corporation. |
| Raymond James on PR Newswire (/news/raymond-james/ and /news/raymond-james-financial,-inc./) | Stale 2018-2020 items only. RJF uses GlobeNewswire (corporate) and Business Wire (PCG advisor news). |
| Stock Taper / allmind.ai / bullfincher.io | AI call summaries, not transcripts (seen in search only, not opened). |
| Advisor Perspectives (advisorperspectives.com, VettaFi) | Cloudflare returns 403 to curl and WebFetch. Content is mostly commentary plus syndicated Bloomberg pieces (e.g. 'BofA Offers Ultra-Wealthy Clients Access to PE Funds', 2025-09-04), so it adds little beyond the Bloomberg and fa-mag rows. |
| The Wealth Advisor (thewealthadvisor.com) | General advisor news and commentary. Firm items (e.g. MS 2026 comp plan) appear to recap other outlets, so it adds little. |
| WealthBriefing (wealthbriefing.com) | Focus is the UK, Europe and Asia. Its US content is covered by the Family Wealth Report row (same publisher). |
| RIA Intel (riaintel.com) | Redirects to institutionalinvestor.com; appears defunct or folded in. |
| Tampa Bay Business & Wealth (tbbwmag.com) | Small local magazine whose RJF items recap earnings releases (duplicates tier 3 material). |
| Tampa Bay / Charlotte / Dallas Business Journals (bizjournals.com) | Same 403 bot wall as the St. Louis edition. HQ coverage of RJF, BofA and Schwab is redundant with national press. Only the St. Louis edition is kept, because Edward Jones is the focus entity. |
| Charlotte Observer / Dallas Morning News | HQ papers for BofA and Schwab with little coverage specific to GWIM or Advisor Services. Redundant with national press. |
| MarketWatch (Dow Jones) | Consumer and markets focus, with little business news on wealth units. Dow Jones is already covered by the WSJ and Barron's rows. |
| Yahoo Finance / MSN / markets.businessinsider.com | Syndicate other outlets and press releases, so they duplicate other sources. |
| Motley Fool / Nasdaq.com / Zacks / Seeking Alpha news | Retail stock commentary, often auto-generated. Seeking Alpha transcripts belong to tier 3. |
| Forbes / Fortune | Mainly rankings and lists (Best-in-State, Fortune 500) with little firm-level evidence. |
| Kitces.com | Planning-practice commentary. Industry news appears only as a weekly link roundup that points to the outlets already listed. |
| Cerulli Associates | Paid research reports, not trade press. |
| J.D. Power advisor/investor satisfaction studies | Third-party survey press releases, not trade press. Could be considered as a separate evidence class later. |
| GDELT DOC API | Duplicates the Google and Bing News RSS routes. Rate-limited (HTTP 429) during the check, and weak on trade titles. |
| Ignites (FT Specialist) | Focuses on the fund industry, not advisor or wealth-unit competition. |
| St. Louis Public Radio | Only occasional, low-volume EDJ coverage. Not checked. |
| Business Wire (as a tier 4 outlet) | Returns 403 to scripts and only redistributes the firms' own releases, which have tier 3 rows (PR Newswire has rows for EDJ, BAC GWIM and MER). |
| MER-BOFACAREERS-PRESS-ADP (Merrill Advisor Development Program careers page; https://careers.bankofamerica.com/en-us/career-development/advisor-development-pro… | undated recruiting / marketing web page: no doc_type fits and no published date (published_at is NOT NULL), so it cannot be ingested; background reading only. Question for the tech lead: T-09. Q4's advisor pipeline is served by BAC GWIM transcripts and the 2025 Investor Day GWIM deck. |
| MER-BOFACAREERS-PRESS-RECRUITING (Merrill experienced-advisor recruiting page ('Become a Financial Advisor with Merrill'); https://careers.bankofamerica.com/en… | undated recruiting / marketing web page: no doc_type fits and no published date (published_at is NOT NULL), so it cannot be ingested; background reading only. Question for the tech lead: T-09. Q4's advisor pipeline is served by BAC GWIM transcripts and the 2025 Investor Day GWIM deck. |
| RJF-ADVISOROPP-PRESS-AFFILIATION (Raymond James affiliation options pages (employee, independent, RIA & custody, bank/credit union, Advisor Select); https://ww… | undated recruiting / marketing web page: no doc_type fits and no published date (published_at is NOT NULL), so it cannot be ingested; background reading only. Question for the tech lead: T-09. Q6 and Q14 are served by RJF press releases (incl. RJF-ADVISOROPP-PRESS-RECRUITING), RJF transcripts and the 10-K (C1). |
| EDJ-NEWSROOM-PRESS-MEDIAKIT (Edward Jones media kit - firm profile (facts page); https://www.edwardjones.com/us-en/why-edward-jones/news-media/media-kit/firm-p… | static facts page with no as-of date; figures belong to filings (ground rule 4). |
| MS-ATWORK-PRESS-INSIGHTS (Morgan Stanley at Work insights hub (studies, case studies, reports); https://www.morganstanley.com/atwork/insights) | business-unit marketing hub (studies, case studies, podcast), undated; its studies are also newsroom releases (MS-NEWSROOM-PRESS). Firm-published studies are tier 5 (C3, #5). |
| SCHW-ADVISORSERVICES-PRESS-BENCHMARKING (Schwab Advisor Services RIA Benchmarking Study and Independent Advisor Outlook Study pages; https://advisorservices.sc… | firm-published industry research (RIA Benchmarking Study): tier 5, handed to C3 (#5). |
| SCHW-IMPACT-TRANSCRIPT (Schwab IMPACT conference site (Schwab Advisor Services RIA conference): agenda, speakers, highlight videos; https://impact.schwab.com/i… | no IMPACT recording or transcript confirmed (agenda page and JS clips only); IMPACT news is in SCHW-PRESSROOM-PRESS. |
| EDJ-IR-SUPPLEMENT-SFC (Edward Jones financial reports page - semi-annual Statement of Financial Condition PDFs; https://www.edwardjones.com/us-en/why-edward-jo… | broker-dealer Statement of Financial Condition (SEC Rule 17a-5): a regulatory filing, tier 2, C1's area; not a supplement and serves no question. |
| BAC-BOFANEWS-PRESS (Bank of America Newsroom press releases (Corporate and Financial News); https://newsroom.bankofamerica.com/content/newsroom/press-releases.… | BAC-wide news is not eligible for any question: Merrill = entity MER, or entity BAC with segment GWIM/Merrill (CLAUDE.md architecture invariant; ADR-004 puts the filter in SQL). Replaced by BAC-BOFANEWS-PRESS-GWIM and MER-BOFANEWS-PRESS. |
| MS-BW-PRESS (Morgan Stanley releases on Business Wire (earnings, dividends, call schedule, Wealth Management news); no url) | Business Wire returns 403 to scripts and has no firm page we could open; the same text (BUSINESS WIRE dateline) is on the firm's own pressroom row. |
| SCHW-BW-PRESS (Charles Schwab releases on Business Wire (earnings, business updates, corporate news); no url) | Business Wire returns 403 to scripts and has no firm page we could open; the same text (BUSINESS WIRE dateline) is on the firm's own pressroom row. |
| SCHW-BW-MONTHLY (Schwab 'Reports Monthly Activity Highlights' releases on Business Wire; no url) | Business Wire returns 403 to scripts and has no firm page we could open; the same text (BUSINESS WIRE dateline) is on the firm's own pressroom row. |
| RJF-BW-PRESS (Raymond James Private Client Group advisor-recruiting / affiliation releases on Business Wire; no url) | Business Wire returns 403 to scripts and has no firm page we could open; the same text (BUSINESS WIRE dateline) is on the firm's own pressroom row. |
| EDJ-NEWSROOM-PRESS-CA (Edward Jones Canada newsroom - news releases; https://www.edwardjones.ca/ca-en/why-edward-jones/news-media/press-releases) | Canadian subsidiary, not one of the core five entities in config/entities.yaml (US comparison set). |
| EDJ-CISION-PRESS-CA (Edward Jones (Canada) news releases on Cision Canada / newswire.ca; https://www.newswire.ca/news/edward-jones/) | Canadian subsidiary, not one of the core five entities in config/entities.yaml (US comparison set). |
| RJF-CISION-PRESS-CA (Raymond James Ltd. (Canada) releases on Cision Canada / newswire.ca; https://www.newswire.ca/news/raymond-james-ltd/) | Canadian subsidiary, not one of the core five entities in config/entities.yaml (US comparison set). |
| Bain & Company (tier 5, C3) | No US wealth-management or advice report found for 2025-2026 (search 2026-10-20 returned private-equity reports only); bain.com answers 403 to scripts. Re-check for #81. |
| Wells Fargo Investment Institute (tier 5, C3) | Market outlooks, not advice themes; wellsfargo.com/investment-institute/ returned 404 on 2026-10-20. |
| SIFMA research and Fact Book (tier 5, C3) | Capital-markets statistics; little on the Q16-Q21 themes. |
| Broadridge insights (tier 5, C3) | broadridge.com/insights returned 404 on 2026-10-20; vendor marketing research. Re-check if a theme is thin. |

## Monthly URL re-check

The spec asks for trade-press URLs to be re-checked monthly (feed rot). C2 runs this by hand in the first week of
each month; there is no schedule and no alert (alerts are out of scope this term). From the repo folder:

```powershell
.\.venv\Scripts\python.exe -m cee.ingest.check_sources --update
```

Mac: `.venv/bin/python -m cee.ingest.check_sources --update`. Without `--update` it only prints.

It requests every unique `url` and `sample_url` once (a GET that reads only the first 64 KB, so a bot-challenge
page is recognised), waits at least one second between requests to the same site, and uses an honest user agent that names this repo. sec.gov
URLs use `EDGAR_IDENTITY` from `.env` and are skipped when it is empty. It writes only `last_checked`,
`url_status` and `sample_status`; edit the CSV in a text editor, not Excel.

| Status | Meaning | What to do |
|---|---|---|
| ok | The page answered (2xx). | Nothing. |
| moved | It answered, but only after a redirect to another site, the front page or a login page. | Find the new URL and update the row. |
| blocked | 401/403 or a bot challenge. Expected for paywalled sites and sites behind Akamai or Cloudflare. | Open it in a browser; if it loads, set `manual_check_on` to today. |
| error | 5xx, 429, timeout or SSL error (already retried once). `error not-tried`: the site gave no answer to two URLs in a row, so the rest were not requested. | Run again later; if it persists, check by hand. |
| dead | 404, 410 or the domain no longer exists. | Find the new URL, or move the row to "Considered and rejected" with the reason. |
| skipped | sec.gov without `EDGAR_IDENTITY`. | Set it in `.env` (never commit `.env`). |

Exit code 0 means no dead URL, 1 means at least one dead URL, 2 means a bad CSV or the machine looks offline
(then nothing is written). Commit the updated CSV on a branch and add a line to the log below.

| Date | Run by | URLs checked | ok | moved | blocked | error | dead | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-05 | C2 (first run, #3) | 200 cells | 137 | 0 | 43 | 20 | 0 | Superseded: this version sent HEAD first and did not look at the page body, so 200 bot-challenge pages counted as ok |
| 2026-10-05 | C2 (second run, #3) | 196 cells (168 unique) | 124 | 0 | 55 | 17 | 0 | GET with body check. raymondjames.com and bloomberg.com gave no answer; the 57 unique blocked/error URLs still need a manual browser check (carried to #4) |
