"""PDF parser interface (ADR-005): docling first, pymupdf fallback.

Skeleton placeholder, owner: TL (Yueyang Du).
parse_pdf(path) -> [(section, page, text)]; every item keeps its page number.
"""
from __future__ import annotations

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

    opts = PdfPipelineOptions(do_ocr=False)  # investor decks are born-digital
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    doc = conv.convert(str(path)).document
    out: list[tuple[str, int, str]] = []
    section = "Document"
    for item, _level in doc.iterate_items():
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


def _parse_pymupdf(path: Path) -> list[tuple[str, int, str]]:
    import pymupdf

    out = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                out.append((f"Page {i}", i, text))
    return out
