"""Split a parsed document into chunks that never cross a section boundary.

Skeleton placeholder, owner: C1 (Jingran Fang) / C2 (Mingmin Kong).
Prefix format (built by code, no LLM): [entity|segment|doc_type|period]
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 1500
# "ITEM 1. BUSINESS" (EDJ, RJF) and "Item 1. Business" (BAC, SCHW).
ITEM_HEADING = re.compile(r"(?im)^[ \t]*ITEM[ \t]+(\d{1,2}[A-C]?)\b\.?[^\n]*$")
# Table-of-contents entry: a column gap ("Item 1.      Business") or a page number at the end.
TOC_LINE = re.compile(r"\S[ \t]{3,}\S|[ \t]{2,}(?:\d{1,3}|page)$", re.I)
TOC_GAP = 2000      # max non-space chars between two entries of the same table of contents
HEADING_MAX = 200   # longer lines are prose that happens to start with "Item"
# Cross-reference table of contents (MS): "Risk Factors        1A 13", "Business   I   1 5".
XREF_ROW = re.compile(
    r"(?m)^[ \t]*(\S.*?\S)[ \t]{2,}(?:(?:I|II|III|IV)[ \t]+)?((?:1[0-6]|[1-9])[A-C]?)[ \t]+\d{1,3}[ \t]*$")
XREF_GAP_LINES = 80  # rows of one table of contents sit this close together


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


def item_headings(text: str) -> list[tuple[int, str]]:
    """[(offset, item)] for "Item N." heading lines, skipping the table of contents and
    running page headers ("Item 1. Business, continued")."""
    cands = []
    for m in ITEM_HEADING.finditer(text):
        line = m.group(0).strip()
        if len(line) > HEADING_MAX or line.lower().endswith("continued"):
            continue
        cands.append((m, bool(TOC_LINE.search(line))))
    # An entry just before a table-of-contents entry is one too, even without a page number
    # (BAC 10-Q: "Item 2. Management's Discussion ..." heads a list of sub-entries).
    toc = [is_toc for _, is_toc in cands]
    for i in range(len(cands) - 2, -1, -1):
        between = text[cands[i][0].end():cands[i + 1][0].start()]
        if toc[i + 1] and len("".join(between.split())) < TOC_GAP:
            toc[i] = True
    return [(m.start(), m.group(1).upper()) for (m, _), is_toc in zip(cands, toc) if not is_toc]


def _norm(s: str) -> str:
    """Compare titles without case, spacing or a trailing "(Unaudited)"-style note."""
    return re.sub(r"\s*\([^)]*\)$", "", " ".join(s.split())).casefold()


def xref_headings(text: str) -> list[tuple[int, str]]:
    """[(offset, item)] for filers whose table of contents maps titles to Items (MS) and whose
    body prints only the titles. Each title is found as a whole line after the table, in
    table order; a title with no heading line falls back to the next table row's title."""
    rows, last_line = [], None
    for m in XREF_ROW.finditer(text):
        line_no = text.count("\n", 0, m.start())
        if last_line is not None and line_no - last_line > XREF_GAP_LINES:
            break  # past the table of contents
        rows.append(m)
        last_line = line_no
    if len(rows) < 3:
        return []
    toc_end = rows[-1].end()
    lines, pos = [], toc_end
    for raw in text[toc_end:].splitlines(keepends=True):
        lines.append((pos, _norm(raw)))
        pos += len(raw)
    out, i = [], 0
    for m in rows:
        titles = [_norm(m.group(1))]
        nxt = text[m.end():].lstrip("\n").split("\n", 1)[0]
        if nxt.strip():
            titles.append(_norm(re.split(r"[ \t]{2,}", nxt.strip())[0]))
        for title in titles:
            j = next((k for k in range(i, len(lines)) if lines[k][1] == title), None)
            if j is not None:
                out.append((lines[j][0], m.group(2)))
                i = j + 1
                break
    return out if len(out) >= 3 else []


def split_10k_sections(text: str) -> list[tuple[str, str]]:
    """Return [(section, body)]; text before the first Item heading is 'Cover'.
    No Item headings and no cross-reference table of contents -> one 'Document' section."""
    heads = item_headings(text) or xref_headings(text)
    if not heads:
        return [("Document", text)]
    sections = [("Cover", text[: heads[0][0]])]
    for i, (start, item) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        sections.append((f"Item {item}", text[start:end]))
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


class SegmentTagger:
    """segment_for for chunk_sections (#37). A segment starts at a line that is only one of its
    aliases and ends at a line that is only a stop heading (another segment's name), another
    alias, or at the next section. Names come from config/entities.yaml, never from code.

    Call once per chunk, in order. A chunk takes the segment in force at its first line, so a
    chunk that ends with a heading still belongs to the segment before it.

    Pass the document's sections to skip section titles on pages that carry titles of two or
    more segments: a slide with one column per segment, where the parser hangs one column's
    heading over another column's text (BAC-DECK-2026Q1 p19). Untagged beats mis-tagged.

    Flat documents (one "Document" section: transcripts, press releases) have no headings, so
    there a chunk is tagged by mentions instead: it names one segment (`segment_mentions`, e.g.
    "Merrill") and that segment's words (mentions plus `mention_signals`, e.g. "advisers") occur
    at least twice as often as other businesses' words (`mention_stops`). BAC-TR-2026Q3 #13
    ("Merrill added about 4,200 net new households") is GWIM; BAC-TR-2026Q2 #13, mostly about
    consumer banking with one GWIM sentence at the end, stays untagged."""

    def __init__(self, segment_aliases: dict[str, list[str]], segment_stops: list[str] = (),
                 sections: list[tuple[str, str, int | None]] = (),
                 segment_mentions: dict[str, list[str]] | None = None, mention_stops: list[str] = (),
                 mention_excludes: list[str] = (), mention_signals: dict[str, list[str]] | None = None):
        self.headings = {_heading_key(a): seg
                         for seg, names in (segment_aliases or {}).items() for a in names}
        for stop in segment_stops or ():
            self.headings.setdefault(_heading_key(stop), None)
        self.mentions = {seg: [_mention_pattern(m) for m in names]
                         for seg, names in (segment_mentions or {}).items()}
        self.signals = {seg: [_mention_pattern(m) for m in names]
                        for seg, names in (mention_signals or {}).items()}
        self.mention_stops = [_mention_pattern(s) for s in mention_stops or ()]
        self.mention_excludes = [_mention_pattern(s) for s in mention_excludes or ()]
        titles: dict[int, set[str]] = {}
        for section, _, page in sections:
            name = self._section_heading(section)
            if page is not None and name is not None:
                titles.setdefault(page, set()).add(name)
        self.mixed_pages = {page for page, names in titles.items() if len(names) > 1}
        self.section = None
        self.current = None

    def __call__(self, section: str, text: str, page: int | None = None) -> str | None:
        if (section, page) != self.section:
            # Deck slides and supplement tables are their own sections: the title is the heading
            # ("Global Wealth & Investment Management Key Indicators").
            name = None if page in self.mixed_pages else self._section_heading(section)
            self.section, self.current = (section, page), self.headings.get(name)
        lines = [l for l in text.splitlines() if l.strip()]
        tag, mixed = None, False
        for i, line in enumerate(lines):
            key = _heading_key(line)
            if key in self.headings:
                # A heading of another segment with text after it inside this chunk: the chunk
                # holds two segments (BAC-10K-2025 segment note, GWIM then Global Banking).
                if i > 0 and i < len(lines) - 1 and self.headings[key] != tag:
                    mixed = True
                self.current = self.headings[key]
            if i == 0:
                tag = self.current
        if mixed:
            return None
        if tag is None and section == FLAT_SECTION:
            return self._mentioned(text)
        return tag

    def _mentioned(self, text: str) -> str | None:
        for pattern in self.mention_excludes:   # "Merrill Edge" is Consumer Banking, not GWIM
            text = pattern.sub(" ", text)
        found = {seg for seg, patterns in self.mentions.items() if any(p.search(text) for p in patterns)}
        if len(found) != 1:
            return None
        seg = found.pop()
        own = _count([*self.mentions[seg], *self.signals.get(seg, [])], text)
        return seg if own >= 2 * _count(self.mention_stops, text) else None

    def _section_heading(self, section: str) -> str | None:
        """The alias or stop heading a section title starts with, longest first."""
        key = _heading_key(section)
        for name in sorted(self.headings, key=len, reverse=True):
            if key == name or key.startswith(name + " "):
                return name
        return None


def _heading_key(line: str) -> str:
    return " ".join(line.split()).casefold()


FLAT_SECTION = "Document"  # load.parse_file: transcripts, press releases and other unsplit text


def _mention_pattern(phrase: str) -> re.Pattern:
    words = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(rf"(?<![\w]){words}(?![\w])", re.IGNORECASE)


def _count(patterns: list[re.Pattern], text: str) -> int:
    return sum(len(p.findall(text)) for p in patterns)


def chunk_sections(doc_id: str, entity_id: str, doc_type: str, period: str,
                   sections: list[tuple[str, str, int | None]],
                   segment_for=lambda section, text, page=None: None) -> list[Chunk]:
    """sections: [(section, text, page)]. Page is None for HTML."""
    chunks: list[Chunk] = []
    for section, body, page in sections:
        for piece in pack_paragraphs(body):
            seg = segment_for(section, piece, page)
            n = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{doc_id}#{n}", seq=n, section=section, segment=seg, page=page,
                prefix=make_prefix(entity_id, seg, doc_type, period), text=piece))
    return chunks
