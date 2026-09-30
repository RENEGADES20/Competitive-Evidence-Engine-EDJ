"""Split a parsed document into chunks that never cross a section boundary.

Skeleton placeholder, owner: C1 (Jingran Fang) / C2 (Mingmin Kong).
Prefix format (built by code, no LLM): [entity|segment|doc_type|period]
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 1500
ITEM_HEADING = re.compile(r"(?m)^[ \t]*ITEM[ \t]+(\d+[A-C]?)\.?[^\n]*$")


@dataclass
class Chunk:
    chunk_id: str
    seq: int
    section: str
    segment: str | None
    page: int | None
    prefix: str
    text: str


def make_prefix(entity_id: str, segment: str | None, doc_type: str, period: str) -> str:
    return f"[{entity_id}|{segment or ''}|{doc_type}|{period}]"


def split_10k_sections(text: str) -> list[tuple[str, str]]:
    """Return [(section, body)]; text before the first ITEM heading is 'Cover'."""
    matches = list(ITEM_HEADING.finditer(text))
    if not matches:
        return [("Document", text)]
    sections = [("Cover", text[: matches[0].start()])]
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((f"Item {m.group(1)}", text[m.start():end]))
    return sections


def pack_paragraphs(body: str, max_chars: int = MAX_CHARS) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    out, cur = [], ""
    for p in paras:
        while len(p) > max_chars:  # very long paragraph: hard split on a sentence end
            cut = p.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            if cur:
                out.append(cur)
                cur = ""
            out.append(p[:cut].strip())
            p = p[cut:].strip()
        if cur and len(cur) + len(p) + 2 > max_chars:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


def chunk_sections(doc_id: str, entity_id: str, doc_type: str, period: str,
                   sections: list[tuple[str, str, int | None]],
                   segment_for=lambda section, text: None) -> list[Chunk]:
    """sections: [(section, text, page)]. Page is None for HTML."""
    chunks: list[Chunk] = []
    for section, body, page in sections:
        for piece in pack_paragraphs(body):
            seg = segment_for(section, piece)
            n = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{doc_id}#{n}", seq=n, section=section, segment=seg, page=page,
                prefix=make_prefix(entity_id, seg, doc_type, period), text=piece))
    return chunks
