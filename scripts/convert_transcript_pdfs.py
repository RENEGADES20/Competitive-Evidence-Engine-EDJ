"""Convert earnings-call transcript PDFs to <doc_id>.txt for the corpus (#39).

The input is the package a teammate shared in the team chat on 2026-10-16 (S&P Global Market
Intelligence and Bloomberg transcripts, one folder per firm). CALLS records, per call, the file,
doc_id, call date, period end, source and where the date was read (ADR-007 T-09).

Keeps speaker names and roles. Drops page headers and footers, copyright lines, Bloomberg
{BIO ...<GO>} tags, the "Licensed to <e-mail>" line (personal data), the S&P consensus-estimate
cover pages (S&P estimates, not firm disclosures; ground rule 4) and the closing legal disclaimer.

  python scripts/convert_transcript_pdfs.py <package folder> <output folder>
"""
import re
import sys
from pathlib import Path

import pymupdf

# file, doc_id, company, call label, call date (YYYY-MM-DD), period_end, source, date basis
CALLS = [
    ("bac/1Q26 BofA Earnings Call Transcript.pdf", "BAC-TR-2026Q1", "Bank of America", "Q1 2026 earnings call",
     "2026-04-15", "2026-03-31", "S&P Global Market Intelligence", "PDF title 'Q1 2026 Earnings Call, Apr 15, 2026'"),
    ("bac/2Q26 BofA Earnings Call Transcript.pdf", "BAC-TR-2026Q2", "Bank of America", "Q2 2026 earnings call",
     "2026-07-14", "2026-06-30", "S&P Global Market Intelligence", "cover 'Tuesday, July 14, 2026'"),
    ("bac/3Q26 BofA Earnings Call Transcript.pdf", "BAC-TR-2026Q3", "Bank of America", "Q3 2026 earnings call",
     "2026-10-14", "2026-09-30", "Bloomberg", "page footer 'FINAL TRANSCRIPT 2026-10-14'"),
    ("ms/1Q26 Morgan Stanley Earnings Call Transcript.pdf", "MS-TR-2026Q1", "Morgan Stanley", "Q1 2026 earnings call",
     "2026-04-15", "2026-03-31", "S&P Global Market Intelligence", "cover 'Wednesday, April 15, 2026'"),
    ("ms/2Q26 Morgan Stanley Earnings Call Transcript.pdf", "MS-TR-2026Q2", "Morgan Stanley", "Q2 2026 earnings call",
     "2026-07-15", "2026-06-30", "S&P Global Market Intelligence", "cover 'Wednesday, July 15, 2026'"),
    ("ms/3Q26 Morgan Stanley Earnings Call Transcript.pdf", "MS-TR-2026Q3", "Morgan Stanley", "Q3 2026 earnings call",
     "2026-10-14", "2026-09-30", "S&P Global Market Intelligence", "cover 'Wednesday, October 14, 2026'"),
    ("rjf/1Q26 RJ Earnings Call Transcript.pdf", "RJF-TR-2026Q1", "Raymond James Financial",
     "fiscal Q2 2026 earnings call (quarter ended March 31, 2026)",
     "2026-04-22", "2026-03-31", "S&P Global Market Intelligence", "cover 'Wednesday, April 22, 2026'"),
    ("rjf/2Q26 RJ Earnings Call Transcript.pdf", "RJF-TR-2026Q2", "Raymond James Financial",
     "fiscal Q3 2026 earnings call (quarter ended June 30, 2026)",
     "2026-07-22", "2026-06-30", "S&P Global Market Intelligence", "cover 'Wednesday, July 22, 2026'"),
    ("schw/1Q26 Schwab Earnings Call Transcript.pdf", "SCHW-TR-2026Q1", "Charles Schwab", "Q1 2026 earnings call",
     "2026-04-16", "2026-03-31", "S&P Global Market Intelligence", "cover 'Thursday, April 16, 2026'"),
    ("schw/2Q26 Schwab Earnings Call Transcript.pdf", "SCHW-TR-2026Q2", "Charles Schwab", "Q2 2026 earnings call",
     "2026-07-21", "2026-06-30", "S&P Global Market Intelligence", "cover 'Tuesday, July 21, 2026'"),
    ("schw/3Q26 Schwab Earnings Call Transcript.pdf", "SCHW-TR-2026Q3", "Charles Schwab",
     "Q3 2026 earnings call (labelled 'Special Call' by S&P)",
     "2026-10-15", "2026-09-30", "S&P Global Market Intelligence", "cover 'October 15, 2026'"),
]

DROP_LINE = [
    re.compile(r"^copyright ©", re.I),
    re.compile(r"^© copyright", re.I),
    re.compile(r"^licensed to\b", re.I),
    re.compile(r"^final transcript \d{4}-\d{2}-\d{2}$", re.I),
    re.compile(r"^[A-Za-z .&,']+ \([A-Z]+ US Equity\)$"),
    re.compile(r"^[A-Z0-9 .,&'()\-]+ (EARNINGS|SPECIAL) CALL [A-Z]{3} \d{1,2}, \d{4}$"),
    re.compile(r"^\d{1,3}$"),
    re.compile(r"^Printed on \d{2}-\d{2}-\d{4} Page \d+ of \d+$"),
]
START = re.compile(r"^(Call Participants|MD&A|Company Participants|Presentation)$")
END = [re.compile(p, re.I) for p in (r"^Copyright © \d{4} by S&P Global", r"^These materials have been prepared solely",
                                      r"^This transcript may not be 100 percent accurate")]
BIO = re.compile(r"\s*\{BIO \d+ <GO>\}")


def convert(pdf: Path) -> str:
    with pymupdf.open(pdf) as d:
        blocks = [" ".join(b[4].split()) for page in d for b in page.get_text("blocks") if b[6] == 0]
    start = next((i for i, b in enumerate(blocks) if START.match(b)), 0)
    out = []
    for b in blocks[start:]:
        if any(p.match(b) for p in END):
            break
        b = BIO.sub("", b).strip()
        if not b or any(p.match(b) for p in DROP_LINE):
            continue
        out.append(b)
    return "\n\n".join(out)


def main() -> None:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for f, doc_id, company, label, date, period, source, basis in CALLS:
        body = convert(root / f)
        assert "edwardjones.com" not in body.lower() and "<GO>" not in body, doc_id
        head = f"{company} - {label} - {date}\nTranscript source: {source}. Speaker names as in the source.\n\n"
        (out / f"{doc_id}.txt").write_text(head + body + "\n", encoding="utf-8", newline="\n")
        print(f"{doc_id}: {len(body):,} chars, {body.count(chr(10)*2)+1} paragraphs | date basis: {basis}")


if __name__ == "__main__":
    main()
