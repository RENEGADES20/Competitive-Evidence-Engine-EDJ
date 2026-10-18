"""PDF parser interface (ADR-005): docling first, pymupdf fallback.

Skeleton placeholder, owner: TL (Yueyang Du).
parse_pdf(path) -> [(section, page, text)]; every item keeps its page number.
"""
from __future__ import annotations

import re
from pathlib import Path


def parse_pdf(path: Path, engine: str = "auto") -> list[tuple[str, int, str]]:
    if engine in ("auto", "docling"):
        try:
            return _parse_docling(path)
        except ImportError:
            if engine == "docling":
                raise
    return _parse_pymupdf(path)


def _parse_docling(path: Path) -> list[tuple[str, int, str]]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import TableItem

    opts = PdfPipelineOptions(do_ocr=False)  # investor decks are born-digital
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = conv.convert(str(path)).document
    out: list[tuple[str, int, str]] = []
    section = "Document"
    # Slide text that docling groups under a picture (SCHW decks) is only reached this way.
    for item, _level in doc.iterate_items(traverse_pictures=True):
        if isinstance(item, TableItem):
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
        page = item.prov[0].page_no
        if out and out[-1][0] == section and out[-1][1] == page:
            out[-1] = (section, page, out[-1][2] + "\n\n" + text)
        else:
            out.append((section, page, text))
    return out


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
