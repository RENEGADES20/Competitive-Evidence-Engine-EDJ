# 0081 - Ingest institutional research (tier 5)

Issue: #81    Role: C3    Spec: specs/thematic.md
Depends on: PR #92 (#5 matrix rows); this branch starts from `c3/5-thematic-matrix`.

## Goal
The local corpus holds 20+ dated, publisher-attributed tier 5 research documents from 8+
publishers (2+ each from McKinsey, Goldman Sachs, FINRA, BofA). Each is chunked and every chunk
carries at least one topic, so theme questions (Q16-Q21) can cite institutional research.

## Files to change
- `data/manifest.csv` - new `publisher` column (issue #81: "add a publisher column ... tell the
  TL"), and one row per document: `doc_type=research`, `source_tier=5`, `entity_id` empty,
  `published_at` from the document, `added_by=C3`.
- `src/cee/ingest/manifest.py` (TL) - add `publisher` to `FIELDS`. Without it `upsert_row` drops
  the column on every write.
- `tests/test_manifest.py` - run it to confirm the `FIELDS` comparison (line 73) still holds;
  edit only if it fails.
- `src/cee/ingest/topics.py` (new) - `seed_topics(conn)` loads `config/topics.yaml` into
  `topics`; `tag_topics(text) -> set[str]` matches keywords as whole words (case-insensitive);
  `tag_document(conn, doc_id)` writes `chunk_topics`.
- `src/cee/ingest/load.py` (TL) - call `seed_topics` next to `seed_entities` on every load
  (`chunk_topics.topic_id` references `topics`, so topics go in first), and `tag_document`
  after each tier 5 document.
- `config/topics.yaml` (C3) - keyword additions for thin themes (see Risks), no id changes.
- `tests/test_topics.py` (new) - offline tests of the tagging rules.
- `docs/source_matrix.csv` - a row for every publisher used or tried, with the access route, cost
  and date checked (#81 deliverable). Most exist from #5 (`T5-*`). Update `last_checked` and notes
  on the rows used; add rows for any new publisher; record failed routes (BCG, PwC, McKinsey bot
  walls) in notes.
- `plans/0081-institutional-research.md` - this plan.
- Raw files go in `data/raw/<doc_id>.<ext>` locally (gitignored). The user uploads them through
  the team Box upload link. The TL moves them to `raw/` and rebuilds the snapshot.

## Tagging rules
1. Keyword match, whole words, case-insensitive (so "ai" never matches inside "said").
2. A sub-topic is tagged only if its parent also matches in the same chunk. This keeps generic
   sub-topic words such as "trillion" or "deployed" from tagging on their own.
3. A chunk tagged with a sub-topic is also tagged with its parent (topics.yaml header).
4. Fallback: a chunk with no match gets the document's most frequent top-level topic. This is a
   trade-off to meet the acceptance rule "every chunk has at least one topic": disclaimers and
   tables of contents get a topic too. The share of fallback chunks is reported by the tagger,
   in the tests and in the PR. A high share means the keyword list needs work.

Topic tags do not change retrieval today: `src/cee/retrieve` does not read `chunk_topics` (only
`smoke.py` checks the table exists). Whether Q16/Q19 retrieve these documents depends on their
text alone.

## Who downloads
Claude downloads, but first lists each file (doc_id, source URL, size) and waits for the user's
yes. McKinsey (both documents), BCG and PwC refuse scripted requests and the built-in browser
(403 / Access Denied, 2026-10-20). The user saves those in their own browser to Downloads, and
Claude copies them in.

## Documents (draft; x = expected theme from title and summary, checked after tagging)

| doc_id | Publisher | Date | af | ai | fp | yi | as | wt | ar | ma |
|---|---|---|---|---|---|---|---|---|---|---|
| MCK-ADVISOR-SHORTAGE | McKinsey | TODO | x | | | | | | x | x? |
| MCK-SIGNAL-SELLOFF | McKinsey | 2026-04-08 | x | x | | | | | | x? |
| GSAM-RETIREMENT-2025 | Goldman Sachs AM | 2025-10 | x | | | x | x? | | | |
| GSAM-ALTERNATIVES-2025 | Goldman Sachs AM | 2025-10 | | | | x | | x | | |
| FINRA-SNAPSHOT-2026 | FINRA | 2026-06-01 | | | | | | | x | |
| FINRAF-INVESTORS-2025 | FINRA Foundation | 2025-12-04 | x | | | x | x | | | |
| FINRAF-FINFLUENCERS-2026 | FINRA Foundation | 2026-04 | | | | x | x | | | |
| BOFA-PB-STUDY-2024 | BofA Private Bank | 2024-06 | | x | | x | | x | | |
| BOFA-PB-STUDY-2026 | BofA Private Bank | 2026-06 | | x | | x | | x | | |
| CERULLI-GWT-2025 | Cerulli | 2025-10 | | | | | | x | | |
| CERULLI-AFFLUENT-PAY | Cerulli | TODO | | | x | | x | | | x |
| CERULLI-AFFLUENT-FEE | Cerulli | TODO | | | x | | | | | x |
| CAPGEMINI-WWR-2026 | Capgemini | 2026-06 | x | x | | x | | x | | |
| BCG-GWR-2025 | BCG | 2025-06 | x | x | x | | | | | |
| ACCENTURE-GENAI | Accenture | TODO | | x | | | | | | |
| CFPB-MISINFO-2025 | CFP Board | 2025-06 | | x | | x | x | | | |
| VANGUARD-VALUE-2025 | Vanguard | 2025-06 | x | | x | | x | | | |
| JPM-GTR-2026 | J.P. Morgan AM | 2026-02-26 | | | | | | x? | | x? |
| UBS-NEXTGEN-2026 | UBS | 2026 | | | | x | | x | | |
| PWC-AWM-2025 | PwC | 2025 | x | | x | | | | | |
| KITCES-WELLBEING-2023 | Kitces | 2023-12 | | | | | | | x | |
| NM-PP-2026 | Northwestern Mutual | 2026-03 | | | | x | x | | | |
| FED-SCF-2023 | Federal Reserve | 2023-10 | | | | | | x | | x? |
| FIDELITY-III-2025 | Fidelity | 2025 | | | x | x | x | x | | |
| DELOITTE-AGENTIC-2026 | Deloitte | 2026 | | x | | | | | x | |

af advice_future, ai ai_advice, fp fees_pricing, yi younger_investors, as advisor_selection,
wt wealth_transfer, ar advisor_recruiting, ma mass_affluent. 25 candidates, 19 publishers.

## Risks
- mass_affluent is the weakest theme. Most reports are about HNW clients, and the keywords are
  narrow. Counting only firm expectations: Cerulli x2 (one publisher) plus McKinsey (if
  "affluent households" matches). Mitigation: add keywords ("affluent households", "affluent
  investors", "middle market", "emerging affluent" already in) and keep both Cerulli press
  releases. If tagging still shows fewer than 2 publishers, add another source before ingest
  closes (candidates: J.D. Power, a Fidelity or Schwab affluent study).
- advisor_selection relies on phrases. Mitigation: add "find a financial advisor", "hire a
  financial advisor", "work with a financial advisor", "referral".
- McKinsey (2 required) is reachable only through the user's own browser. If the user cannot
  download it, the "2 McKinsey" acceptance item stays open.
- Goldman: two GSAM survey PDFs, both reachable (200, 2026-10-20). The firm-in-competitive-set
  rule applies (tier 5, entity empty).
- Several dates are TODO until the document is read; `published_at` must come from the document
  (ADR-007 T-09), never from the download date.
- BofA PB 2024/2026 are newsroom press releases (html). The full 2024 study PDF found is a
  third-party copy, so the official release is used instead.

## Acceptance
- [x] >= 2 stored reports each from McKinsey, Goldman Sachs, FINRA and BofA (2023+ where available): McKinsey 2, Goldman 2 (GSAM), FINRA 3 (1 FINRA + 2 FINRA Foundation), BofA 2 (Private Bank)
- [x] >= 20 institutional research documents, >= 8 publishers: 22 documents, 16 publishers
- [x] `published_at` and `publisher` 100% filled for these rows (all date_basis source)
- [x] Every chunk of these documents has >= 1 topic; fallback share reported: 871 of 1,348 chunks (65%) by fallback
- [x] Each of the 8 seed themes: >= 3 documents from >= 2 publishers, by keyword matches alone (fewest: advisor_recruiting 5 docs / 4 publishers; advisor_selection 5 / 5)
- [x] Reports by Goldman, BofA, Morgan Stanley, J.P. Morgan, UBS, Wells Fargo keep `entity_id` empty
- [ ] `scripts/eval_run.py --questions Q16,Q17,Q18,Q19,Q20,Q21`: Q16 and Q19 retrieve >= 1 of these documents. Q16 yes (Vanguard, Kitces); **Q19 no**: the question names Edward Jones, so retrieval runs in entity mode and filters SQL to EDJ, excluding all tier 5 documents. Retrieval is out of scope for #81 (S1)
- [x] `verify_cee.py run` after ingest: PASS (.verify-runs/20261020-095943-d202939; download-document UNREACHABLE as expected)
- [x] `pytest -q` passes (129); 0 paid API calls (mock only)

## Progress log
- 2026-10-20 - plan written with user review (source_matrix deliverable, downloader, theme coverage
  risks, tagging rules 3-4, FK order, retrieval note); branch c3/81-institutional-research created
  from c3/5-thematic-matrix
- 2026-10-20 - 21 files downloaded with the user's approval. Dates taken from each document (cover date,
  PDF metadata or page datePublished; a printed date wins over metadata). Loaded one document at a time
  with `cee.ingest.load --doc` (other raw files are not on this laptop).
- 2026-10-20 - Plan change: HTML press releases parsed with all menus and cookie banners. Added
  `src/cee/ingest/webpage.py` (article body only) and a 3-line branch in `load.parse_file` for
  research web pages.
- 2026-10-20 - First tagging: advice_future matched 0 documents, advisor_recruiting 2, FED-SCF-2023 none
  (no theme words). Keywords broadened in topics.yaml; FED-SCF-2023 dropped (not stored; matrix note).
  Fallback share 66%: sampled fallback chunks are mostly charts, tables, endnotes and off-theme sections
  (retirement maths, market structure, regional HNW statistics). More keywords would over-tag. Question
  for the TL: an explicit "none/general" topic instead of the fallback?
- 2026-10-20 - eval_run Q16-Q21 (mock): Q18, Q20 PASS; Q16 hits THEME:research but THEME:regulatory and
  THEME:survey count as "not in corpus" (doc_type is research for all tier 5, so the eval cannot tell
  kinds apart); Q19 gets EDJ-only chunks (entity mode). Both are for S1 / TL.
- 2026-10-20 - McKinsey: user downloaded both official PDFs (DOWNLOADS > Article) in Chrome; a first
  print-to-PDF copy of the advisor-shortage page was blank after page 2 and was not used. Loaded
  MCK-ADVISOR-SHORTAGE-2025 (2025-02-10) and MCK-SIGNAL-SELLOFF-2026 (2026-04-08). Totals: 22 documents,
  16 publishers, 1,348 chunks, 0 untagged, 65% fallback. eval_run unchanged (Q18, Q20 PASS; Q19 still
  EDJ-only by entity mode). verify-cee PASS, pytest 129 passed.
