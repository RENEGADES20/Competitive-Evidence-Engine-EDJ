# 0036 - Latest 10-K and four latest 10-Qs for the five filers

Issue: #36    Role: C1    Spec: specs/filings.md

## Goal
EDJ, MS, SCHW, BAC and RJF each have their latest 10-K and four latest 10-Qs in
`data/manifest.csv`, the raw HTML in the team Box `raw/` folder, and all of them load into the
local database, so questions about the four peers stop ending in "no evidence".

## Files to change
- data/manifest.csv - about 24 new rows (4 x 10-K, 5 x 4 x 10-Q), written by `cee.ingest.edgar`
- plans/0036-tenk-tenq.md - this plan
- src/cee/ingest/edgar.py - fall back to the primary document when `filing.html()` is None
  (edgartools returns None for the MS 2025 10-K); tests/test_ingest_prep.py - one test for it
- scripts/verify_cee.py, .claude/skills/verify-cee/features/README.md, gap-path.md - the
  no-evidence question moves from Morgan Stanley (now stored) to LPL Financial, as the recipe's
  gotcha asks
- Raw files go to Box `raw/` (tech lead route: `CORPUS_SHARE_PATH` is the Box Drive folder, so
  the fetch writes there directly); nothing under `data/raw/` is committed.

## Steps
1. One firm end to end: `--entity MS --form 10-K`, load it, check document and chunk counts.
2. The other 10-Ks: SCHW, BAC, RJF (EDJ's is already in).
3. `--form 10-Q --count 4` for all five.
4. Re-run every fetch; expect only "skip" lines and no new rows.
5. `python -m cee.ingest.load`; document and chunk counts per entity, chunks > 0 per document.
6. Retrieval checks (no LLM): Q30 returns BAC 10-K chunks; Q23 returns 10-Q chunks from at
   least three firms.
7. `pytest -q`; `verify_cee.py run` (mock provider, 0 real calls).

Unsure: a 10-Q whose period falls in the same calendar quarter as another would collide on
doc_id (`<ENTITY>-10Q-<YYYY>Q<n>`); check the four IDs per firm are distinct.

## Acceptance
- [x] `--form 10-K` for MS, SCHW, BAC, RJF and `--form 10-Q --count 4` for all five; every new row has `published_at`
- [x] Re-running any fetch adds no rows ("skip" lines in the PR)
- [x] `python -m cee.ingest.load`: document and chunk counts per entity; chunks > 0 for every document
- [ ] (partly) Linked questions: Q30 retrieval returns BAC 10-K chunks; Q23 returns 10-Q chunks from at least three firms (Q22, Q24, Q25, Q29 retrieval recorded)
- [x] Every raw file in Box `raw/` under its exact `<doc_id>.htm` name (listed in the PR)
- [x] Nothing under `data/raw/` committed; `pytest -q` passes; `verify_cee.py run` all PASS (mock)

## Progress log
- 2026-10-15 22:16 - plan written; branch c1/36-tenk-tenq created
- 2026-10-15 22:18 - MS 10-K: `filing.html()` returned None; the primary document downloads fine.
  Added the fallback in edgar.py with a test. Fetched 4 x 10-K and 5 x 4 x 10-Q (24 rows), all
  sha256 match the files in Box `raw/`. Re-run: 24 skip lines, manifest unchanged.
- 2026-10-15 22:22 - Loaded all 25 documents (11,977 chunks, every document > 0). Finding: BAC,
  MS and SCHW chunks all land in one "Document" section: `ITEM_HEADING` in chunk.py only
  matches upper-case "ITEM" (BAC/SCHW write "Item 1."), and the MS filings have no Item
  headings at all. Out of scope here; affects #37 (GWIM tagging).
- 2026-10-15 22:24 - Retrieval: Q30 returns 0 hits, because MER only sees BAC chunks tagged
  segment GWIM and tagging is #37. Q23 top-8 covers MS and RJF 10-Qs only; top-20 adds SCHW
  and EDJ 10-Qs (per-firm quotas are #59). Q22/Q24/Q25/Q29 now return MS, RJF, BAC, EDJ chunks.
- 2026-10-15 22:27 - verify-cee gap-path failed as the recipe predicted (MS is no longer a gap);
  no-evidence question moved to LPL Financial. verify-cee all PASS; pytest 69 passed.
