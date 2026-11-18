"""PDF parser interface (ADR-005): docling first, pymupdf fallback.

Skeleton placeholder, owner: TL (Yueyang Du).
parse_pdf(path) -> [(section, page, text)]; every item keeps its page number.

docling takes minutes per PDF, so its output is cached twice (#82, #84, cee.ingest.parse_cache):
- parsed/<sha256>-docling<version>-doc.json: docling's own DoclingDocument. Its name does not hold
  our pipeline options (do_ocr=False in _convert); a change to them needs a new name (e.g. -doc2),
  or the old docling output would be reused.
- parsed/<sha256>-docling<version>-v<PARSER_VERSION>.json: our (section, page, text) list made from it.
A PARSER_VERSION bump re-runs doc_items on the cached DoclingDocument (seconds), not docling.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from cee.ingest import parse_cache

# Bump whenever doc_items (or table_blocks) would produce different output for the same file.
# v2 (#84): an item whose provenance covers two pages is split at the page break.
PARSER_VERSION = 2


def doc_cache_tag() -> str:
    return f"docling{parse_cache.version('docling')}-doc"


def parse_pdf(path: Path, engine: str = "auto", use_cache: bool = True,
              cache_dir: Path | None = None) -> list[tuple[str, int, str]]:
    """use_cache=False parses again but still refreshes both cache files. Only docling output is
    cached; the pymupdf fallback takes seconds."""
    if engine in ("auto", "docling"):
        try:
            cache_file = parse_cache.cache_path(path, parse_cache.tag("docling", PARSER_VERSION), cache_dir)
            cached = parse_cache.read(cache_file, lambda r: [(s, int(p), t) for s, p, t in r]) if use_cache else None
            if cached is not None:
                print(f"  {path.name}: parse cache hit ({cache_file.name})", flush=True)
                return cached
            doc_file = parse_cache.cache_path(path, doc_cache_tag(), cache_dir)
            items = _parse_docling(path, doc_file, use_cache)
        except ImportError:  # also docling's version lookup when it is not installed
            if engine == "docling":
                raise
        else:
            parse_cache.write(cache_file, path, items)
            return items
    return _parse_pymupdf(path)


def _parse_docling(path: Path, doc_file: Path | None = None, use_cache: bool = True) -> list[tuple[str, int, str]]:
    """Items from the cached DoclingDocument when there is one, else from a fresh docling run
    (stored in doc_file)."""
    doc = parse_cache.read(doc_file, _load_doc) if doc_file and use_cache else None
    if doc is not None:
        print(f"  {path.name}: docling output cache hit ({doc_file.name})", flush=True)
    else:
        print(f"  {path.name}: parsing with docling (cache {'miss' if use_cache else 'off'})", flush=True)
        doc = _convert(path)
        if doc_file:
            parse_cache.write(doc_file, path, doc.export_to_dict())
    items, fallbacks = doc_items(doc, _is_table)
    if fallbacks:
        print(f"  {path.name}: {fallbacks} multi-page item(s) without usable charspans kept whole "
              "on their main page", flush=True)
    return items


def _convert(path: Path) -> Any:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=False)  # investor decks are born-digital
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    return conv.convert(str(path)).document


def _load_doc(data: Any) -> Any:
    from docling_core.types.doc import DoclingDocument

    return DoclingDocument.model_validate(data)


def _is_table(item: Any) -> bool:
    from docling_core.types.doc import TableItem

    return isinstance(item, TableItem)


def page_parts(item: Any, text: str) -> tuple[list[tuple[int, str]], bool]:
    """[(page, text)] for one item: one part per run of provenance entries on the same page, cut
    at the charspan where the page changes (#84: SCHW-DECK-2026Q1 p4 [4,4,4,5]). Spans that do
    not fit the text keep the whole item on the page with the most characters; the bool says so."""
    prov = item.prov
    if len({p.page_no for p in prov}) == 1:
        return [(prov[0].page_no, text)], False
    cuts, pages = [], [prov[0].page_no]
    for prev, p in zip(prov, prov[1:]):
        if p.page_no != prev.page_no:
            cuts.append(p.charspan[0])
            pages.append(p.page_no)
    bounds = [0, *cuts, len(text)]
    if prov[-1].charspan[1] != len(text) or any(a >= b for a, b in zip(bounds, bounds[1:])):
        chars: dict[int, int] = {}
        for p in prov:
            chars[p.page_no] = chars.get(p.page_no, 0) + max(0, p.charspan[1] - p.charspan[0])
        return [(max(chars, key=lambda pg: (chars[pg], -pg)), text)], True
    return [(pg, text[a:b].strip()) for pg, a, b in zip(pages, bounds, bounds[1:])], False


def doc_items(doc: Any, is_table: Callable[[Any], bool]) -> tuple[list[tuple[str, int, str]], int]:
    """(items, fallbacks): [(section, page, text)] in reading order; neighbouring text of the same
    section and page joined."""
    out: list[tuple[str, int, str]] = []
    section = "Document"
    fallbacks = 0
    # Slide text that docling groups under a picture (SCHW decks) is only reached this way.
    for item, _level in doc.iterate_items(traverse_pictures=True):
        table = is_table(item)
        if table:
            # Tables have no .text; without this, a supplement loses most of its figures.
            text = "\n\n".join(table_blocks(item.export_to_markdown(doc=doc)))
        else:
            text = getattr(item, "text", "") or ""
        if not text.strip() or not item.prov:
            continue
        label = str(getattr(item, "label", ""))
        if "section_header" in label or "title" in label:
            section = text.strip()[:200]
            continue
        if table:  # table rows carry no page; a table stays on its first page
            parts = [(item.prov[0].page_no, text)]
        else:
            parts, fell_back = page_parts(item, text)
            fallbacks += fell_back
        for page, part in parts:
            if not part:
                continue
            if out and out[-1][0] == section and out[-1][1] == page:
                out[-1] = (section, page, out[-1][2] + "\n\n" + part)
            else:
                out.append((section, page, part))
    return out, fallbacks


def table_blocks(md: str, limit: int = 1400) -> list[str]:
    """Split a markdown table into blocks of whole rows, each under `limit` characters and each
    starting with the header rows, so a chunk of a long table still says what its columns are."""
    # docling pads cells for alignment; the padding would fill most of a chunk.
    lines = [re.sub(r"-{3,}", "---", re.sub(r" {2,}", " ", l.strip())) for l in md.strip().splitlines() if l.strip()]
    head, rows = lines[:2], lines[2:]
    if not rows:
        return ["\n".join(head)] if head else []
    blocks, cur = [], list(head)
    for row in rows:
        if len(cur) > len(head) and len("\n".join(cur + [row])) > limit:
            blocks.append("\n".join(cur))
            cur = list(head)
        cur.append(row)
    blocks.append("\n".join(cur))
    return blocks


def _parse_pymupdf(path: Path) -> list[tuple[str, int, str]]:
    import pymupdf

    out = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                out.append((f"Page {i}", i, text))
    return out
