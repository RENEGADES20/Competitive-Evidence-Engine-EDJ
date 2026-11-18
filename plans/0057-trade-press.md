# 0057 - Ingest 90 days of trade press for the five

Issue: #57    Role: C3 (reassigned from C2 on 2026-11-05)    Spec: specs/transcripts-ir.md

## Goal
Articles about EDJ, MS, SCHW, MER and RJF published 2026-08-18 to 2026-11-16 (90 days back from the
start date) on free trade-press sites in the source matrix are stored as tier 4 `trade` documents with
outlet, headline, page date and full text, so Q2, Q4, Q7, Q26 and Q29 can cite them ("indicative only";
the app already labels tier 4 that way). The freeze was 11/11, so this goes to the next snapshot.

## Files to change
- `scripts/collect_trade_press.py` (new) - `discover` lists candidate article URLs per outlet (no article
  text yet); `fetch` downloads approved pages with a per-site delay (>= 5 s, honest user agent, as in
  C2's `convert_press_web.py`); `convert` writes `<doc_id>.txt` with header lines (headline, outlet, date,
  URL, tier note) and the article body; `register` adds manifest rows. Re-runs skip URLs already in the
  manifest.
- `tests/test_collect_trade_press.py` (new) - offline, on saved fixture HTML: date taken from the page,
  alias counting, entity choice, MER for Merrill, no duplicate on re-run.
- `data/manifest.csv` - one row per article: `doc_type=trade`, `source_tier=4`, entity per article,
  `publisher` = outlet, `published_at` = page date.
- `docs/source_matrix.csv` - `last_checked` and notes on the tier 4 rows used or tried.
- `plans/0057-trade-press.md` - this plan.
- Raw `.txt` files go in `data/raw/` (gitignored) and are uploaded to the team Box through the upload
  link; only `data/manifest.csv` goes into git.

## Outlets
InvestmentNews (per-company pages) end to end first; then WealthManagement.com (monthly archive
sitemaps), RIABiz (per-company tag pages), AdvisorHub (RSS only: its tag pages answer 403 to an honest
user agent, so its 90-day coverage is partial; stated in the PR).

## Which firm an article is about
- Count mentions with the aliases in `config/entities.yaml`, but not the bare tickers (MS, SCHW, RJF):
  "MS" collides with the title "Ms." and with other words. Whole-word, case-sensitive matching.
- Keep an article if a firm's alias is in the headline or the body mentions it at least 3 times.
- `entity_id` = the firm named in the headline (first one if several), else the most-mentioned firm.
- Merrill (aliases "Merrill", "Merrill Lynch", ...) -> MER. An article that names only "Bank of America"
  is not kept. This also drops GWIM-wide stories without Merrill; it is the safer side for the Merrill
  trap questions (Q4, Q27), which must not mix BAC and Merrill.
- Limitation: one entity per document. The manifest and the retrieval filter (`d.entity_id = ...` in
  `src/cee/retrieve/fts.py`) take one firm, so a move story "from Morgan Stanley to Raymond James" is
  filed under one firm and an entity-filtered search for the other misses it (Q2, Q7). The header lists
  every firm mentioned, so full-text search still sees the names; the gap is stated in the PR.

## Steps
1. Collector + tests; `discover` for InvestmentNews; show the user the list (counts per firm and outlet,
   headlines) before any article text is downloaded.
2. With approval: fetch, convert, register, load InvestmentNews; check dates and entities.
3. Repeat for the other three outlets.
4. Q2, Q26 retrieval; full mock eval with vs without the trade documents (lesson from #55); verify-cee.

## Acceptance
- [x] Articles for each firm over the last 90 days: 77 (EDJ 4, MS 16, SCHW 25, MER 11, RJF 21); per outlet in the PR
- [x] `published_at` = article date from the page (2026-08-18..2026-11-16, all date_basis source)
- [x] Merrill articles stored as MER (11)
- [x] Q26 retrieval returns trade chunks from the last 90 days (FAIL -> PASS); tier 4 label "trade press (indicative only)" comes from TIER_LABELS
- [x] Re-running adds no duplicates (second register run: 0 new); `pytest -q` 374 passed, 9 new offline tests
- [x] Q2 and Q26 PASS; `verify_cee.py run` PASS (open-citation UNREACHABLE: raw MS supplement PDF not local, same on main)

## Progress log
- 2026-11-16 - plan written with the user's review (Box upload, one-entity limitation, alias counting
  and the Bank of America rule); branch c3/57-trade-press from main 8f92cb1.
- 2026-11-16 - InvestmentNews: 88 listed, fetched with approval, 38 kept. First body selector matched
  nothing: each paragraph is its own div.wrapper--detail__body, so all matches are joined in page order.
- 2026-11-16 - WealthManagement (26, slug filter on archive sitemaps), RIABiz (11, tag pages; no EDJ tag),
  AdvisorHub (RSS only, 2 of 10). RIABiz bylines print the UTC date, so its dates are read in UTC; all
  other outlets' computed dates equal their printed date lines.
- 2026-11-16 - Totals: 77 trade documents (EDJ 4, MS 16, SCHW 25, MER 11, RJF 21), 327 chunks.
- 2026-11-16 - Full mock eval without vs with trade (ADV brochures removed from the local DB to match
  main): 27/3 -> 26/4, tier-1 recall 0.626 -> 0.567. Gains: trade patterns hit in Q2, Q4 (0 forbidden),
  Q7, Q29; Q26 FAIL -> PASS on recent news. Losses: Q23 (MS supplement, SCHW 10-K, RJF press pushed out),
  Q24 (SCHW 10-K pushed out). Same mechanism as #55 (#179): retrieval needs doc-type limits per question
  type (benchmark questions should not take tier 4). Flagged for the TL and S1.
