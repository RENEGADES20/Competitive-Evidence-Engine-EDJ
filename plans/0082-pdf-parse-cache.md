# 0082 - Cache parsed PDFs so rebuilds do not re-run docling

Issue: #82    Role: TL    Spec: docs/DECISIONS.md ADR-005, ADR-006

## Goal
A file whose bytes have not changed is parsed once. Later `cee.ingest.load` runs and
`build-snapshot.ps1` reuse the stored parse, and the chunks are identical to a fresh parse.

## Files to change
- `src/cee/ingest/parse_cache.py` (new) - sha256, cache path
  `<write_root()>/parsed/<sha256>-<library><version>-v<N>.json`, read (a corrupt or mislabelled
  file is a miss), atomic write.
- `src/cee/ingest/pdf.py` - `PARSER_VERSION`; `parse_pdf` reads/writes the cache around the
  docling parse. The pymupdf fallback (seconds) is not cached.
- `src/cee/ingest/load.py` - `HTML_PARSER_VERSION` and `html_text` (cached edgartools text; the
  10-K/10-Q splitter still runs after it); `--no-parse-cache` flag passed through `load_all` ->
  `load_document` -> `parse_file`.
- `scripts/chunk_dump.py` (new) - identity check: dump chunks (chunk_id, section, page, text) from
  the DB to JSON (`--all` for every chunk, else PDF chunks), and compare two dumps.
- `tests/test_parse_cache.py` (new) - hit, version bump, library upgrade, changed file, no-cache,
  corrupt file, fallback, HTML; docling and edgartools replaced by fakes, no DB.
- `.gitignore` - `data/parsed/` (cache location when `CORPUS_SHARE_PATH` is empty).
- `docs/DECISIONS.md` - short note in ADR-005.

## Steps
1. Baseline: dump the PDF chunks of the current DB (corpus-2026-10-18, built from main, no cache).
2. Implement the PDF cache and the flag; unit tests.
3. Cold load (timed): every PDF a miss. Compare PDF chunks with the baseline.
4. Warm load (timed, target under 2 minutes). Compare.
5. If the warm load is still slow, find where the time goes and cache that step too.
6. Version bump on a real run: one PDF and one filing re-parse, the rest stay hits.
7. `build-snapshot.ps1 -AllowBranch`: log shows cache hits. Do not publish it.
8. `pytest -q`; `scripts/verify_cee.py run` (mock). ADR-005 note; PR.

## Acceptance
- [x] Linked questions: none (infrastructure)
- [x] Second `python -m cee.ingest.load` on the full manifest under 2 minutes: 10.5 s (68 docs)
- [x] `chunk_dump.py compare`: section, page and text of every chunk identical with and without
      the cache (1,063 PDF chunks vs the main-built snapshot; all 14,682 chunks vs a no-HTML-cache load)
- [x] Version bump or changed file re-parses that file only (unit tests + real bump run)
- [x] `build-snapshot.ps1 -AllowBranch` uses the cache: 57 hits, 0 parses, 15 s
- [x] `pytest -q` 106 passed; `verify_cee.py run` 5/5 PASS; 0 real calls (`LLM_PROVIDER=mock`)

## Progress log
- 2026-10-18 13:25 - plan written; branch tl/82-pdf-parse-cache. Manifest now has 68 rows (16 PDFs,
  41 EDGAR .htm, 11 text); local DB holds corpus-2026-10-18 (built after the last `pdf.py`
  change), used as baseline (1,063 PDF chunks).
- 2026-10-18 14:18 - cold load 47m58s (16 docling misses), PDF chunks identical to baseline. Warm
  load 3m00s: PDFs now 0.1 s, but edgartools `parse_html` on the 41 filings takes 164 s. The issue's
  2-minute target was set for 52 docs; the manifest has 68.
- 2026-10-18 14:30 - widened the cache to the edgartools text (same mechanism, moved into
  `parse_cache.py`), library version added to the cache name (pins are exact, so a pin bump
  re-parses). Re-keyed the 16 docling files from the first run (docling 2.131.0, content checked
  equal) instead of a second 48-minute parse. HTML-cold load 2m31s, warm load 10.5 s; all
  14,682 chunks identical.
- 2026-10-18 14:33 - real bump run (both versions +1 in-process): RJF-SUPP-2026Q1 re-parsed by
  docling in 259 s, EDJ-10K-2025 by edgartools in 4 s; fresh output equal to the v1 cache; v2
  files deleted. build-snapshot -AllowBranch 15 s, 57 hits; the -test dump was deleted from Box
  and snapshots/. pytest 106 passed; verify_cee 5/5 PASS.
