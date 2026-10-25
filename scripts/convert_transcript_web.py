"""Fetch earnings-call transcripts from free web pages and convert them to <doc_id>.txt (#47).

Used where no S&P Global or Bloomberg PDF is at hand (scripts/convert_transcript_pdfs.py).
Sources (source matrix rows *-MARKETBEAT-TRANSCRIPT, *-ROIC-TRANSCRIPT; ADR-007 T-04, T-08):
- MarketBeat earnings report pages: the full call "Provided by Quartr", with a participant list
  and each speaker's title. Call date: the date printed under "Provided by Quartr".
- Roic.ai, only where MarketBeat has no transcript: speaker names without titles and no
  participant list. Call date: the date in the page title.
CALLS records, per call, the page, doc_id, call date and period end; convert stops if the page
gives another date (ADR-007 T-09).

Keeps every turn of the call and the speaker names (and titles) as the page gives them, written
once per turn (the pages repeat the speaker on every block of a long turn), and the participant
list under the PDF transcripts' headings. A speaker the page gives no name stays nameless and is
reported. Repairs characters the page double-encoded ("â€”" -> "—"). Drops MarketBeat's
AI-generated "Key Takeaways" box, timestamps, ads and the rest of the page.

  python scripts/convert_transcript_web.py fetch <html folder> [doc_id ...]
  python scripts/convert_transcript_web.py convert <html folder> <output folder> [doc_id ...]
"""
import html
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

MB = "https://www.marketbeat.com/earnings/reports/"
ROIC = "https://www.roic.ai/quote/"
SOURCES = {MB: "MarketBeat (transcript provided by Quartr)", ROIC: "Roic.ai"}
MARKERS = {MB: "Provided by Quartr", ROIC: "data-transcript-speaker-name"}  # a page with a transcript
USER_AGENT = "CEE-student-prototype/0.1 (internal non-commercial research)"
DELAY = 5  # seconds between requests (ADR-007 T-08: be polite)

# url, doc_id, company, call label, call date (YYYY-MM-DD), period_end
CALLS = [
    (MB + "2025-1-16-bank-of-america-co-stock/", "BAC-TR-2024Q4", "Bank of America", "Q4 2024 earnings call",
     "2025-01-16", "2024-12-31"),
    (MB + "2025-4-15-bank-of-america-co-stock/", "BAC-TR-2025Q1", "Bank of America", "Q1 2025 earnings call",
     "2025-04-15", "2025-03-31"),
    (MB + "2025-7-16-bank-of-america-co-stock/", "BAC-TR-2025Q2", "Bank of America", "Q2 2025 earnings call",
     "2025-07-16", "2025-06-30"),
    (MB + "2025-10-15-bank-of-america-co-stock/", "BAC-TR-2025Q3", "Bank of America", "Q3 2025 earnings call",
     "2025-10-15", "2025-09-30"),
    (MB + "2026-1-14-bank-of-america-co-stock/", "BAC-TR-2025Q4", "Bank of America", "Q4 2025 earnings call",
     "2026-01-14", "2025-12-31"),
    (MB + "2025-1-16-morgan-stanley-stock/", "MS-TR-2024Q4", "Morgan Stanley", "Q4 2024 earnings call",
     "2025-01-16", "2024-12-31"),
    (MB + "2025-4-11-morgan-stanley-stock/", "MS-TR-2025Q1", "Morgan Stanley", "Q1 2025 earnings call",
     "2025-04-11", "2025-03-31"),
    (MB + "2025-7-16-morgan-stanley-stock/", "MS-TR-2025Q2", "Morgan Stanley", "Q2 2025 earnings call",
     "2025-07-16", "2025-06-30"),
    (MB + "2025-10-15-morgan-stanley-stock/", "MS-TR-2025Q3", "Morgan Stanley", "Q3 2025 earnings call",
     "2025-10-15", "2025-09-30"),
    (MB + "2026-1-15-morgan-stanley-stock/", "MS-TR-2025Q4", "Morgan Stanley", "Q4 2025 earnings call",
     "2026-01-15", "2025-12-31"),
    (MB + "2024-10-23-raymond-james-stock/", "RJF-TR-2024Q3", "Raymond James Financial",
     "fiscal Q4 2024 earnings call (quarter ended September 30, 2024)", "2024-10-23", "2024-09-30"),
    (MB + "2025-1-29-raymond-james-stock/", "RJF-TR-2024Q4", "Raymond James Financial",
     "fiscal Q1 2025 earnings call (quarter ended December 31, 2024)", "2025-01-29", "2024-12-31"),
    (MB + "2025-4-23-raymond-james-stock/", "RJF-TR-2025Q1", "Raymond James Financial",
     "fiscal Q2 2025 earnings call (quarter ended March 31, 2025)", "2025-04-23", "2025-03-31"),
    (MB + "2025-7-23-raymond-james-stock/", "RJF-TR-2025Q2", "Raymond James Financial",
     "fiscal Q3 2025 earnings call (quarter ended June 30, 2025)", "2025-07-23", "2025-06-30"),
    (MB + "2025-10-22-raymond-james-stock/", "RJF-TR-2025Q3", "Raymond James Financial",
     "fiscal Q4 2025 earnings call (quarter ended September 30, 2025)", "2025-10-22", "2025-09-30"),
    (MB + "2026-1-28-raymond-james-stock/", "RJF-TR-2025Q4", "Raymond James Financial",
     "fiscal Q1 2026 earnings call (quarter ended December 31, 2025)", "2026-01-28", "2025-12-31"),
    # MarketBeat's page for this call has no transcript
    (ROIC + "SCHW/transcripts/2024-year/4-quarter", "SCHW-TR-2024Q4", "Charles Schwab", "Q4 2024 earnings call",
     "2025-01-21", "2024-12-31"),
    (MB + "2025-4-17-the-charles-schwab-co-stock/", "SCHW-TR-2025Q1", "Charles Schwab", "Q1 2025 earnings call",
     "2025-04-17", "2025-03-31"),
    (MB + "2025-7-18-the-charles-schwab-co-stock/", "SCHW-TR-2025Q2", "Charles Schwab", "Q2 2025 earnings call",
     "2025-07-18", "2025-06-30"),
    (MB + "2025-10-16-the-charles-schwab-co-stock/", "SCHW-TR-2025Q3", "Charles Schwab", "Q3 2025 earnings call",
     "2025-10-16", "2025-09-30"),
    (MB + "2026-1-21-the-charles-schwab-co-stock/", "SCHW-TR-2025Q4", "Charles Schwab", "Q4 2025 earnings call",
     "2026-01-21", "2025-12-31"),
]

BYLINE_DATE = re.compile(r"Provided by Quartr</div>\s*<div[^>]*>([^<]+)</div>")
HEADING = re.compile(r'<h4 id="([a-z-]+)"[^>]*>(.*?)</h4>', re.S)
SECTION = re.compile(r'<section class="transcript-line-(?:left|right)[^"]*">(.*?)</section>', re.S)
SPEAKER = re.compile(r'<div class="transcript-line-speaker[^"]*">\s*<div class="font-weight-bold">(.*?)</div>\s*<time', re.S)
ROLE = re.compile(r'<div class="secondary-title[^"]*">(.*?)</div>', re.S)
PARA = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
GROUP = re.compile(r'<h5 class="mt-1">(Executives|Analysts)</h5>(.*?)(?=<h5 class="mt-1">|$)', re.S)
PERSON = re.compile(r'<div class="flex-grow-1">(.*?)</div></div></li>', re.S)
ROIC_TITLE_DATE = re.compile(r"<title>[^<]*Earnings Call Transcript - ([A-Z][a-z]+ \d{1,2}, \d{4}) \|")
ROIC_TURN = re.compile(r'<p data-transcript-speaker-name="true"[^>]*>(.*?)</p>\s*<span[^>]*>(.*?)</span>', re.S)
LEFTOVER = ("ai generated", "key takeaways", "may contain errors", "click here", "edwardjones.com")
# UTF-8 that the page double-encoded through cp1252, e.g. "â€”" for an em dash: a UTF-8 lead byte, then 1-3
# continuation bytes, each shown as its cp1252 character.
_CONT = "\u0080-¿ŒœŠšŸŽžƒˆ˜–—‘-„†-•…‰‹›€™"
MOJIBAKE = re.compile(f"[Â-ß][{_CONT}]|[à-ï][{_CONT}]{{2}}|[ð-ô][{_CONT}]{{3}}")


def repair(s: str) -> str:
    """'â€”' -> '—', 'Ã©' -> 'é'; a run that does not decode as UTF-8 is left as it is."""
    def fix(m: re.Match) -> str:
        try:
            return m.group(0).encode("cp1252").decode("utf-8")
        except UnicodeError:
            return m.group(0)
    return MOJIBAKE.sub(fix, s)


def text(fragment: str) -> str:
    return " ".join(repair(html.unescape(re.sub(r"<[^>]+>", " ", fragment))).split())


def name_and_title(fragment: str, unnamed: set[str]) -> str:
    """'Ted Pick<div class="secondary-title">Chairman and CEO</div>' -> 'Ted Pick Chairman and CEO'.
    A speaker the page gives no name is kept as its title alone and collected in unnamed."""
    role = ROLE.search(fragment)
    name = text(ROLE.sub("", fragment))
    label = " ".join(filter(None, [name, text(role.group(1)) if role else ""]))
    if not name:
        unnamed.add(label)
    return label


def site(url: str) -> str:
    for base in SOURCES:
        if url.startswith(base):
            return base
    raise ValueError(f"no parser for {url}")


def call_date(page: str, base: str) -> tuple[str, str]:
    """(YYYY-MM-DD, where it was read)."""
    m = (BYLINE_DATE if base == MB else ROIC_TITLE_DATE).search(page)
    if not m:
        raise ValueError("no call date on the page")
    printed = m.group(1).strip()
    where = "under 'Provided by Quartr'" if base == MB else "page title"
    return datetime.strptime(printed, "%B %d, %Y").strftime("%Y-%m-%d"), f"{where} '{printed}'"


def add_turn(out: list[str], last: list[str], speaker: str, paras: str) -> None:
    """The pages split long turns into blocks that repeat the speaker; write the speaker once per turn."""
    if speaker != last[0]:
        out.append(speaker)
        last[0] = speaker
    out += [t for t in (text(p) for p in PARA.findall(paras)) if t]


def convert_roic(page: str, unnamed: set[str]) -> str:
    out, last = [], [None]
    for speaker, paras in ROIC_TURN.findall(page):
        label = text(speaker)
        if not label:
            raise ValueError("a transcript turn has no speaker")
        add_turn(out, last, label, paras)
    if not out or len(ROIC_TURN.findall(page)) != page.count('data-transcript-speaker-name="true"'):
        raise ValueError("transcript turns not found, or some turns not parsed")
    return "\n\n".join(out)


def convert(page: str, unnamed: set[str]) -> str:
    """Participant list (S&P headings, as in the PDF transcripts), then every turn in page order."""
    start, end = page.find('<h4 id="presentation"'), page.find('<h4 id="participants"')
    stop = page.find("</article>", end)
    if start < 0 or end < start or stop < end:
        raise ValueError("transcript or participant list not found")
    out = ["Call Participants"]
    for group, block in GROUP.findall(page[end:stop]):
        out.append(group.upper())
        out += [name_and_title(p, unnamed) for p in PERSON.findall(block)]
    body = page[start:end]
    if len(SECTION.findall(body)) != body.count("<section"):
        raise ValueError("some transcript turns were not parsed")
    items = [(m.start(), "h", m.group(2)) for m in HEADING.finditer(body)]
    items += [(m.start(), "s", m.group(1)) for m in SECTION.finditer(body)]
    last = [None]
    for _, kind, frag in sorted(items):
        if kind == "h":
            out.append(text(frag))
            last[0] = None
            continue
        speaker = SPEAKER.search(frag)
        if not speaker:
            raise ValueError("a transcript turn has no speaker")
        add_turn(out, last, name_and_title(speaker.group(1), unnamed), frag)
    return "\n\n".join(out)


def selected(only: list[str]) -> list[tuple]:
    unknown = set(only) - {c[1] for c in CALLS}
    if unknown:
        raise SystemExit(f"not in CALLS: {', '.join(sorted(unknown))}")
    return [c for c in CALLS if not only or c[1] in only]


def fetch(folder: Path, only: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for url, doc_id, *_ in selected(only):
        target = folder / f"{doc_id}.html"
        if target.exists():
            print(f"{doc_id}: skip (already fetched)")
            continue
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        if MARKERS[site(url)].encode() not in body:
            raise SystemExit(f"{doc_id}: no transcript on {url}")
        target.write_bytes(body)
        print(f"{doc_id}: {len(body):,} bytes")
        time.sleep(DELAY)


def convert_all(folder: Path, out: Path, only: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for url, doc_id, company, label, date, period in selected(only):
        raw = (folder / f"{doc_id}.html").read_text(encoding="utf-8")
        base = site(url)
        found, basis = call_date(raw, base)
        assert found == date, f"{doc_id}: page says {found}, CALLS says {date}"
        unnamed: set[str] = set()
        body = convert(raw, unnamed) if base == MB else convert_roic(raw, unnamed)
        assert "<" not in body and not any(s in body.lower() for s in LEFTOVER), doc_id
        assert not MOJIBAKE.search(body), f"{doc_id}: undecodable mojibake left"
        head = (f"{company} - {label} - {date}\n"
                f"Transcript source: {SOURCES[base]}. Speaker names as in the source.\n\n")
        (out / f"{doc_id}.txt").write_text(head + body + "\n", encoding="utf-8", newline="\n")
        print(f"{doc_id}: {len(body):,} chars, {body.count(chr(10) * 2) + 1} paragraphs | date basis: {basis}")
        for u in sorted(unnamed):
            print(f"  warning: speaker with no name on the page: {u!r}")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        fetch(Path(sys.argv[2]), sys.argv[3:])
    elif len(sys.argv) >= 4 and sys.argv[1] == "convert":
        convert_all(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
