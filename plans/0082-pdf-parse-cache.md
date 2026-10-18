# 0082 - Cache parsed PDFs so rebuilds do not re-run docling

Issue: #82    Role: TL    Spec: docs/DECISIONS.md ADR-005, ADR-006

## Goal
A PDF whose bytes have not changed is parsed by docling once. Later `cee.ingest.load` runs and
`build-snapshot.ps1` reuse the stored parse, and the chunks are identical to a fresh parse.

## Files to change
- `src/cee/ingest/pdf.py` - `PARSER_VERSION` constant; `parse_pdf` looks up / writes
  `<write_root()>/parsed/<sha256>-v<PARSER_VERSION>.json` around the docling parse. Only
  docling output is cached (the pymupdf fallback takes seconds). A corrupt cache file is a miss.
- `src/cee/ingest/load.py` - `--no-pdf-cache` flag (forces a fresh parse, still writes the cache),
  passed through `load_all` -> `load_document` -> `parse_file`.
- `scripts/pdf_chunk_dump.py` - identity check: dump every PDF chunk (chunk_id, section, page,
  text) from the DB to JSON, and compare two dumps.
- `tests/test_pdf_cache.py` - hit, miss, version bump, changed file, corrupt file, fallback not
  cached; docling is replaced by a fake, no DB.
- `.gitignore` - `data/parsed/` (cache location when `CORPUS_SHARE_PATH` is empty).
- `docs/DECISIONS.md` - short note in ADR-005.

## Steps
1. Baseline: dump the PDF chunks of the current DB (corpus-2026-10-18, built from main with no
   cache) with `scripts/pdf_chunk_dump.py dump`.
2. Implement the cache in `pdf.py` and the flag in `load.py`; unit tests.
3. Cold load (`python -m cee.ingest.load`, timed): every PDF is a miss, docling runs, cache written.
   Dump PDF chunks, compare with the baseline.
4. Warm load (timed, must be under 2 minutes): every PDF is a hit. Dump, compare with cold and
   baseline.
5. Version bump: run one PDF doc with `PARSER_VERSION` raised in-process; it must re-parse (miss),
   the other PDFs stay hits; remove the extra cache file afterwards.
6. `build-snapshot.ps1 -AllowBranch`: log shows cache hits for all 16 PDFs. Do not publish it.
7. `pytest -q`; `scripts/verify_cee.py run` (mock).
8. ADR-005 note; PR.

## Acceptance
- [ ] Linked questions: none (infrastructure)
- [ ] Second `python -m cee.ingest.load` on the full manifest takes under 2 minutes (both timed)
- [ ] `pdf_chunk_dump.py compare`: text, section and page of every PDF chunk identical with and
      without the cache
- [ ] Version bump or changed file re-parses that file only (unit tests + one real run)
- [ ] `build-snapshot.ps1 -AllowBranch` log shows the cache in use
- [ ] `pytest -q` passes; `verify_cee.py run` all PASS; 0 real calls (`LLM_PROVIDER=mock`)

## Progress log
- 2026-10-18 - plan written; branch tl/82-pdf-parse-cache. Manifest now has 68 rows (16 PDFs);
  local DB holds corpus-2026-10-18 (built after the last `pdf.py` change), used as baseline.
