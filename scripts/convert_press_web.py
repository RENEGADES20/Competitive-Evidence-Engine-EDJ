"""Fetch Merrill press releases from the Bank of America newsroom and convert them to <doc_id>.txt (#48).

Merrill has no newsroom of its own; its releases sit in the "Global Wealth and Investment Management"
category of newsroom.bankofamerica.com (source matrix row MER-BOFANEWS-PRESS, ADR-007 T-08). Only
releases about Merrill itself are entity MER; GWIM-wide, Private Bank and joint items are BAC#GWIM
(source matrix, Merrill vs Bank of America split) and are not listed here.
RELEASES records, per release, the page, doc_id and release date; convert stops if the page prints
another date (ADR-007 T-09: the date line "September 15, 2026 at 9:00 AM Eastern" above the headline).

The page holds the release twice (mobile and desktop layouts) and spells every abbreviation twice
(a screen-reader "T E T" next to "TET"). Keeps one copy: headline, key points, body, sub-headings and
the FAQ, one paragraph per block. Stops at the "Bank of America" company boilerplate; drops press
contacts, disclosures, category tags, related releases and the site chrome.

  python scripts/convert_press_web.py fetch <html folder> [doc_id ...]
  python scripts/convert_press_web.py convert <html folder> <output folder> [doc_id ...]
"""
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

NEWSROOM = "https://newsroom.bankofamerica.com/content/newsroom/press-releases/"
USER_AGENT = "CEE-student-prototype/0.1 (internal non-commercial research)"
DELAY = 5  # seconds between requests (ADR-007 T-08: be polite)

# url, doc_id, release date (YYYY-MM-DD). Window for #48: 2026-08-01 to 2026-10-30.
RELEASES = [
    (NEWSROOM + "2026/09/merrill-launches-new-services-to-support-portfolio-transitions-a.html",
     "MER-PR-2026-09-15-01", "2026-09-15"),
]

DATE_LINE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4}) at \d{1,2}:\d{2} [AP]M Eastern")
BLOCKS = ["p", "li", "h2", "h3", "h4"]
STOP = {"bank of america", "reporters may contact", "important disclosures", "categories"}
LEFTOVER = ("reporters may contact", "important disclosures", "cookie", "share this", "related press releases")
SPELLED = re.compile(r"\b[A-Z](?: [A-Z]){2,}\b")  # a screen-reader spelling left behind, e.g. "T E T"


def text(el) -> str:
    return " ".join(el.get_text("").split())


def blocks(root) -> list[str]:
    """Text of the outermost p/li/h* elements under root, in page order."""
    out = []
    for el in root.find_all(BLOCKS):
        if el.find_parent(BLOCKS) is not None:
            continue
        t = text(el)
        if t:
            out.append(t)
    return out


def release_date(soup) -> tuple[str, str]:
    """(YYYY-MM-DD, the printed date line)."""
    for p in soup.select("section.press-release p"):
        m = DATE_LINE.search(" ".join(p.get_text(" ").split()))
        if m:
            return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d"), m.group(0)
    raise ValueError("no date line on the page")


def convert(page: str) -> tuple[str, str, str]:
    """(headline, body, printed date line). Body: key points, then the release up to the boilerplate."""
    soup = BeautifulSoup(page, "lxml")
    for t in soup.select(".sr-only"):
        t.decompose()
    desktop = soup.select_one("section.press-release.d-lg-block")
    keys = soup.select_one("section.v2-Custom-rte.d-lg-block")
    if desktop is None or keys is None:
        raise ValueError("press-release layout not found")
    headline = text(desktop.select_one("h1"))
    body_root = next((r for r in desktop.select("div.richtext") if text(r)), None)
    if not headline or body_root is None:
        raise ValueError("headline or release body not found")
    out = ["Key points"] + [f"- {t}" for t in blocks(keys) if t.lower() != "key points"]
    for t in blocks(body_root):
        if t.lower() in STOP:
            break
        out.append(t)
    else:
        raise ValueError("company boilerplate heading not found; check where the release ends")
    _, line = release_date(soup)
    return headline, "\n\n".join(out), line


def selected(only: list[str]) -> list[tuple]:
    unknown = set(only) - {r[1] for r in RELEASES}
    if unknown:
        raise SystemExit(f"not in RELEASES: {', '.join(sorted(unknown))}")
    return [r for r in RELEASES if not only or r[1] in only]


def fetch(folder: Path, only: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for url, doc_id, _ in selected(only):
        target = folder / f"{doc_id}.html"
        if target.exists():
            print(f"{doc_id}: skip (already fetched)")
            continue
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        if b"pressreleasearticle" not in body:
            raise SystemExit(f"{doc_id}: no press release on {url}")
        target.write_bytes(body)
        print(f"{doc_id}: {len(body):,} bytes")
        time.sleep(DELAY)


def convert_all(folder: Path, out: Path, only: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for url, doc_id, date in selected(only):
        page = (folder / f"{doc_id}.html").read_text(encoding="utf-8")
        found, line = release_date(BeautifulSoup(page, "lxml"))
        assert found == date, f"{doc_id}: page says {found}, RELEASES says {date}"
        headline, body, _ = convert(page)
        low = body.lower()
        assert "<" not in body and not any(s in low for s in LEFTOVER), doc_id
        assert not SPELLED.search(body), f"{doc_id}: screen-reader spelling left: {SPELLED.search(body).group(0)}"
        head = (f"{headline}\n"
                f"Merrill press release - {date}\n"
                f"Source: Bank of America Newsroom, Global Wealth and Investment Management category.\n\n")
        (out / f"{doc_id}.txt").write_text(head + body + "\n", encoding="utf-8", newline="\n")
        print(f"{doc_id}: {len(body):,} chars, {body.count(chr(10) * 2) + 1} paragraphs | date basis: '{line}'")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        fetch(Path(sys.argv[2]), sys.argv[3:])
    elif len(sys.argv) >= 4 and sys.argv[1] == "convert":
        convert_all(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
