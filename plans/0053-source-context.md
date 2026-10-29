# 0053 - Source page: passage in context, PDF at the right page

Issue: #53    Role: U1    Spec: specs/ui.md

## Goal
From a citation, the reader sees the cited passage inside its section, can tell exactly which
passage was cited, and for a PDF sees the cited page. Without the raw file locally the passage
and metadata still show.

## Files to change
- src/cee/app/views/source_page.py - replace the #53 placeholder: neighbouring chunks of the same section and the PDF page view
- src/cee/app/components.py - `context_passages` (neighbours plus the cited chunk, marked) and `pdf_page`
- requirements.txt - add pymupdf (already pinned in requirements-ingest.txt) so the app can render a page
- src/cee/app/views/design_page.py, docs/DESIGN.md - sample and description of the two components
- scripts/verify_cee.py, .claude/skills/verify-cee/features/open-citation.md - new sub-features cite-context, cite-page

## Steps
1. Query chunks of the same doc_id and section with seq within 2 of the cited chunk; show them in order, the cited one marked CITED.
2. PDF (chunks.page set, file is a .pdf): render page `chunks.page` (1-based, as stored) with pymupdf and show it with its page number.
3. Raw file missing: keep passage, context and metadata; replace the page view with the "not found locally" note. Download stays optional.
4. Update the verify driver and recipe; run `verify_cee.py run open-citation download-document`, then the full run.

## Acceptance
- [x] Linked questions: Q26 (links resolve), Q30 (caveat visible); mock pipeline only
- [x] HTML filings: neighbouring chunks of the same section shown, cited chunk clearly distinguishable
- [x] PDFs: page shown matches chunks.page (5 citations from decks/supplements, incl. MS-SUPP-2026Q3#16 p.8 and SCHW-DECK-2026Q2 p.29)
- [x] Without the raw file locally, passage and metadata still show
- [x] `verify_cee.py run open-citation download-document` PASS; screenshots of an HTML and a PDF citation
- [x] 0 real model calls

## Progress log
- 2026-10-27 - plan written
- 2026-10-27 - implemented (source_page, context_passages, pdf_page, pymupdf in requirements.txt)
- 2026-10-27 - verify-cee all 7 features PASS (run 20261027-183442-8a7e313); open-citation checks 5 PDF pages (words of the chunk found on page N: 94-100%); without raw files the passage and context still show, page step UNREACHABLE (run 20261027-183510-8a7e313); pytest 208 passed; 0 real model calls
