"""Split an earnings-call transcript into speaker turns (#107). Owner: C2 (Mingmin Kong).

Input: the .txt written by scripts/convert_transcript_pdfs.py or scripts/convert_transcript_web.py.
Line 1 is "<Company> - <call label> - <date>", line 2 names the source, then one paragraph per
block: a speaker's label is a paragraph of its own, followed by what they said.

Four layouts, told apart by the source line:
- S&P Global: "Call Participants" list (EXECUTIVES / ANALYSTS); a label is a list entry
  ("Alastair M. Borthwick Executive VP & CFO"), sometimes split over two paragraphs.
- MarketBeat (Quartr): the same list; in the call a label may add " at <firm>".
- Bloomberg: "Company Participants" / "Other Participants" name lines; bare names, or "Q - Name"
  and "A - Name" in the Q&A.
- Roic.ai: no list; bare names.

A paragraph starts a turn if it is "Operator"/"Moderator", a Bloomberg "Q - "/"A - " label, a list
label (exact, with " at <firm>", split over two paragraphs, or a Bloomberg bare name), or looks like
a label (short, capitalised, no sentence punctuation) and recurs, ends in a title or firm word, or
the file has no list. A list name run into the first sentence ("Kartik Sharma Thank you...") is
split off. Headings ("Presentation", "Question and Answer") and short operator hand-offs ride along
with the next turn. Leftover PDF page headers ("... EARNINGS CALL ...") are dropped.
Pure functions; chunk.chunk_sections packs the turns.
"""
from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field

HEADINGS = {"Presentation", "Question and Answer", "Questions And Answers", "Questions and Answers",
            "Q&A", "MD&A"}
LIST_HEADS = {"Call Participants", "Company Participants", "Other Participants", "EXECUTIVES", "ANALYSTS"}
OPERATORS = {"Operator", "Moderator"}
HANDOFF_MAX = 300   # an operator turn this short ("Next is Gerard Cassidy with RBC.") joins the next turn
BBG_QA = re.compile(r"^[QA] - [A-Z]")
NAMEISH = re.compile(r"^[A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*){1,3}$")   # 2-4 capitalised words
LABELISH = re.compile(r"^(?:[A-Z]\.? )?[A-Z][\w'’-]+(?: [A-Z]\.?)?(?: [A-Z][\w'’-]+){1,2}"
                      r"(?: (?:[A-Z&][\w.,&'’-]*|of|and|for|the|at|de))*$")
TITLE_TAIL = re.compile(r"(Research Division|LLP|LLC|Inc\.?|Officer|CEO|CFO|Director|President|Relations|"
                        r"Chairman|Chair|Partners|Research|Securities|Board|Organization)$")
SENTENCE_END = re.compile(r"[?!:;\-—\]\)]$|(?<!Inc)(?<! [A-Z])\.$")
LABEL_AT_END = re.compile(r"[.?!,;:\-—\]\)]\"?$")
PAGE_HEADER = re.compile(r"EARNINGS CALL|Earnings Call, [A-Z][a-z]{2} \d{1,2}, \d{4}$")


@dataclass
class Turn:
    speaker: str | None                              # the label as printed; None for the preamble
    paras: list[str] = field(default_factory=list)   # what the speaker said
    lead: list[str] = field(default_factory=list)    # heading / operator hand-off carried in front


def _layout(source_line: str) -> str:
    for key, name in (("Roic", "roic"), ("MarketBeat", "marketbeat"), ("Bloomberg", "bloomberg")):
        if key in source_line:
            return name
    return "sp"


def _participants(paras: list[str], layout: str) -> tuple[set[str], list[str]]:
    """(labels from an S&P/MarketBeat list, Bloomberg name lines)."""
    labels: set[str] = set()
    if layout in ("sp", "marketbeat") and "Call Participants" in paras:
        group = False
        for p in paras[paras.index("Call Participants") + 1:]:
            if p in HEADINGS:
                break
            if p in ("EXECUTIVES", "ANALYSTS"):
                group = True
            elif group and not PAGE_HEADER.search(p):
                labels.add(p)
    lines: list[str] = []
    if layout == "bloomberg" and {"Company Participants", "Presentation"} <= set(paras):
        i, k = paras.index("Company Participants"), paras.index("Presentation")
        lines = [p for p in paras[i + 1:k] if p not in LIST_HEADS]
    return labels, lines


def _label(paras: list[str], i: int, labels: set[str], name_lines: list[str], counts: collections.Counter,
           layout: str) -> tuple[str | None, int, str | None]:
    """(speaker label, paragraphs used, text run into the label) for a turn start at i, else (None, 1, None)."""
    p = paras[i]
    if p in OPERATORS:
        return p, 1, None
    if BBG_QA.match(p) and len(p) < 80:
        return p, 1, None
    if p in labels:
        return p, 1, None
    if len(p) <= 220 and not LABEL_AT_END.search(p) and any(p.startswith(l + " at ") for l in labels):
        return p, 1, None
    if layout == "bloomberg" and NAMEISH.match(p) and any(p in line for line in name_lines):
        return p, 1, None
    if i + 1 < len(paras) and f"{p} {paras[i + 1]}" in labels:
        return f"{p} {paras[i + 1]}", 2, None
    if (len(p) <= 150 and not SENTENCE_END.search(p) and LABELISH.match(p)
            and (counts[p] >= 2 or TITLE_TAIL.search(p) or layout == "roic")):
        return p, 1, None
    for l in labels:
        name = l.split(" at ")[0]
        if NAMEISH.match(name) and p.startswith(name + " ") and len(p) > len(name) + 40:
            return name, 1, p[len(name) + 1:]
    return None, 1, None


def split_turns(text: str) -> list[Turn]:
    """[preamble, turn, turn, ...]. The preamble holds the two header lines and the participant
    list; every later paragraph belongs to exactly one turn (page-header leftovers excepted)."""
    head, _, body = text.partition("\n\n")
    source = head.split("\n")[1] if "\n" in head else ""
    layout = _layout(source)
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    labels, name_lines = _participants(paras, layout)
    counts = collections.Counter(paras)
    start = next((paras.index(h) for h in ("Presentation", "MD&A") if h in paras), 0)
    preamble = Turn(None, [head.strip(), *paras[:start]] if head.strip() else paras[:start])
    turns: list[Turn] = [preamble]
    lead: list[str] = []
    i = start
    while i < len(paras):
        p = paras[i]
        if PAGE_HEADER.search(p) and len(p) < 120:
            i += 1
            continue
        if p in HEADINGS:
            lead.append(p)
            i += 1
            continue
        speaker, used, rest = _label(paras, i, labels, name_lines, counts, layout)
        if speaker:
            turns.append(Turn(speaker, [rest] if rest else [], lead))
            lead = []
        elif lead or len(turns) == 1:
            turns.append(Turn(None, [p], lead))    # text before any label: keep it, unnamed
            lead = []
        else:
            turns[-1].paras.append(p)
        i += used
    if lead:
        turns[-1].paras.extend(lead)
    return _merge_handoffs([t for t in turns if t.paras or t.lead or t is preamble])


def _merge_handoffs(turns: list[Turn]) -> list[Turn]:
    """A short operator turn ("Our next question comes from ...") rides in front of the next turn."""
    out: list[Turn] = []
    carry: list[str] = []
    for t in turns:
        t.lead = carry + t.lead
        carry = []
        size = len("\n\n".join(t.paras))
        if t.speaker in OPERATORS and size < HANDOFF_MAX and t is not turns[-1]:
            carry = [*t.lead, t.speaker, *t.paras]
            continue
        out.append(t)
    return out


def turn_pieces(text: str, pack, max_chars: int) -> list[tuple[str, str, bool]]:
    """[(chunk text, text to tag, continues the previous chunk's turn)]: each turn packed on its
    own with pack(body, max_chars); every chunk of a turn starts with the speaker label; the tagger
    sees the turn's words without the label (an analyst's firm, "RBC Capital Markets", is not a
    business line)."""
    out = []
    for t in split_turns(text):
        if t.speaker is None and not t.lead:
            out += [(piece, piece, False) for piece in pack("\n\n".join(t.paras), max_chars)]
            continue
        label = t.speaker or ""
        lead = "\n\n".join(t.lead)
        room = max_chars - len(label) - len(lead) - 4
        pieces = pack("\n\n".join(t.paras), max(room, max_chars // 2)) or [""]
        for n, piece in enumerate(pieces):
            parts = ([lead] if n == 0 and lead else []) + ([label] if label else []) + ([piece] if piece else [])
            out.append(("\n\n".join(parts), piece or lead, n > 0))
    return out
