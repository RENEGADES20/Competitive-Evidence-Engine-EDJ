"""Fetch the undated advisor recruiting pages and convert them to <doc_id>.txt (#58, ADR-007 T-09).

Merrill's two careers pages are fetched live. raymondjames.com blocks scripts, so its six affiliation
pages come from the latest Wayback Machine capture with HTTP 200, as original bytes (the "id_" form,
no archive toolbar). None of the pages prints a date, carries date metadata or sends Last-Modified,
so each is dated by the stored copy (date_basis = retrieved). PAGES records, per page, the copy used
and the earliest Wayback capture (which dates the URL, not this text).

Every file starts with the same 5-line header (scripts/check_dates.py reads it), a blank line, then
the page text, one paragraph per block. Kept: headings, copy, the option tiles and the RJ comparison
table (one paragraph per row). Dropped: menus, the recruiter contact block, division director cards,
the "News and Recent Joins" press list, video transcript buttons, exit pop-ups, legal footers.

  python scripts/convert_undated_web.py fetch <html folder> [doc_id ...]
  python scripts/convert_undated_web.py convert <html folder> <output folder> [doc_id ...]
"""
import re
import sys
import time
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cee.ingest.webpage import DROP  # noqa: E402

USER_AGENT = "CEE-student-prototype/0.1 (internal non-commercial research)"
DELAY = 5  # seconds between requests (ADR-007 T-08: be polite)
MER = "https://careers.bankofamerica.com/en-us/"
RJ = "https://www.raymondjames.com/advisor-opportunities/affiliation-options"

# doc_id, entity, url, copy ("live" or Wayback timestamp), content as of, earliest Wayback capture,
# title (the page's h1), a phrase the converted text must keep
PAGES = [
    ("MER-PR-web-advisor-development-program", "MER", MER + "career-development/advisor-development-program",
     "live", "2026-11-03", "2024-09-11", "Advisor Development Program",
     "Path A: Advisor Development Program Client Associate (ADP CA)"),
    ("MER-PR-web-becoming-a-merrill-lynch-advisor", "MER", MER + "becoming-a-merrill-lynch-advisor",
     "live", "2026-11-03", "2026-04-11", "Accelerate your business growth at Merrill",
     "Infrastructure that supports lead generation through Bank of America's global bank"),
    ("RJF-PR-web-affiliation-options", "RJF", RJ, "20260421065839", "2026-04-21", "2017-04-20",
     "Raymond James Affiliation options", "70-80% gross payout"),
    ("RJF-PR-web-traditional-employee-advisor", "RJF", RJ + "/traditional-employee-advisor",
     "20260516231525", "2026-05-16", "2025-03-27", "Traditional Employee Advisor",
     "Book ownership is just the beginning."),
    ("RJF-PR-web-independent-advisor", "RJF", RJ + "/independent-advisor",
     "20260519072648", "2026-05-19", "2017-06-06", "Independent Advisor",
     "When you affiliate with Raymond James as an independent contractor"),
    ("RJF-PR-web-independent-ria-custody-services", "RJF", RJ + "/independent-ria-custody-services",
     "20260712025837", "2026-07-12", "2025-07-25", "Independent RIA & Custody Services",
     "Raymond James RIA & Custody Services (RCS)"),
    ("RJF-PR-web-bank-and-credit-union-advisors", "RJF", RJ + "/bank-and-credit-union-advisors",
     "20260517053909", "2026-05-17", "2017-09-28", "Bank and Credit Union Advisors",
     "The Raymond James Financial Institutions Division (FID)"),
    ("RJF-PR-web-advisor-select", "RJF", RJ + "/advisor-select",
     "20260311101214", "2026-03-11", "2020-04-01", "Raymond James Advisor Select®",
     "an employee affiliation option for advisors who want to lead a team"),
]
FIRM = {"MER": "Merrill", "RJF": "Raymond James"}
# T-09 step 1: a date the page prints for itself ("Last updated: May 1, 2026"). Dates in parentheses
# cite someone else's list ("(Published on July 18, 2025. ...)") and do not date the page.
PAGE_DATE = re.compile(r"(?<!\()\b(?:last updated|updated|published|posted)\s*(?:on|:)?\s*"
                       r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}", re.I)

# Per site: page root, elements removed before reading, lines that end the text, lines dropped.
SITES = {
    "MER": dict(root="body",
                remove=[".interstitial", ".uc-media-transcript", "header", "footer"],
                stop=["Investment products offered through MLPF&S", "Alternative investments are intended",
                      "You are now leaving a Bank of America website", "Investment and insurance products:"],
                drop=["Explore opportunities", "I am not licensed", "What would you like the power to do?",
                      "Interested in exploring other roles at Merrill or Bank of America?",
                      "Merrill and Bank of America Careers", "Transcript", "Skip to main content",
                      "Interested in exploring other roles", "at Merrill or Bank of America?"],
                drop_prefix=["I am licensed (", "Hear why this top advisor"]),
    "RJF": dict(root="main#main-content",
                remove=[".mega-menu-mobile", ".yb5", ".yearbook-five", ".mc-container", ".contact-cta-section", ".footer-content",
                        ".subcat-cta", ".billboard-cta-wrapper", ".skip-link", "#onetrust-consent-sdk"],
                stop=["Welcome, I'm", "Welcome, I’m", "News and Recent Joins", "Legal Disclosures"],
                drop=["Talk to a consultant", "See More", "Skip to main content", "Learn more", "Read more"],
                drop_prefix=[]),
}
BLOCK = {"p", "div", "section", "article", "main", "ul", "ol", "li", "table", "tr", "td", "th", "h1", "h2",
         "h3", "h4", "h5", "h6", "blockquote", "figure", "figcaption", "dl", "dt", "dd", "header", "footer"}
ROW = "\u2063"  # (not whitespace) joins the lines of one table row or tile list inside one paragraph
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w")
PHONE = re.compile(r"\(?\b\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")
LEFTOVER = ("web.archive.org", "wayback machine", "wm-ipp", "cookie", "skip to", "share this",
            "you are now leaving", "news and recent joins", "welcome, i")
DATE_META = re.compile(r"modified|updated|published|lastmod|(?<![a-z])date", re.I)


def clean(s: str) -> str:
    return " ".join(s.replace("﻿", "").split())


def copy_url(url: str, copy: str, raw: bool = False) -> str:
    """The page URL (live) or its Wayback copy; raw=True gives the original bytes (id_)."""
    return url if copy == "live" else f"https://web.archive.org/web/{copy}{'id_' if raw else ''}/{url}"


def prepare_rj(root) -> None:
    """Option tiles -> "Title: copy"; comparison table -> caption, then one paragraph per row with
    "Heading: data" lines; h1 "<strong>Title</strong> tagline" -> title and tagline apart."""
    soup = BeautifulSoup("", "lxml")
    for strong in root.select("h1 > strong"):
        strong.insert_after("\n")
    for tile in root.select(".callout-item"):  # title: the tile heading, else its button unless generic
        heads = [clean(h.get_text(" ")) for h in tile.select(".callout-heading")]
        cta, copy = tile.select_one(".callout-cta"), tile.select_one(".callout-copy-wrapper")
        title = " ".join(h for h in heads if h) or (clean(cta.get_text(" ")) if cta else "")
        if title.lower() in ("learn more", "read more"):
            title = ""
        if title and copy is not None:
            p = soup.new_tag("p")
            p.string = f"{title}: {clean(copy.get_text(' '))}"
            tile.replace_with(p)
    for table in root.select("table"):
        rows = []
        for tr in table.select("tbody tr") or table.select("tr")[1:]:
            cells = []
            for c in tr.find_all(["th", "td"]):
                h, d = c.select_one(".dynamic-table-cell-heading"), c.select_one(".dynamic-table-cell-data")
                cells.append(f"{clean(h.get_text(' '))}: {clean(d.get_text(' '))}" if h and d
                             else clean(c.get_text(" ")))
            rows.append(ROW.join(x for x in cells if x))
        box, cap = soup.new_tag("div"), table.find("caption")
        for child in list(cap.children) if cap else []:
            box.append(child.extract())
        p = soup.new_tag("p")
        p.string = "\n".join(rows)  # each row its own line, made a paragraph below
        box.append(p)
        table.replace_with(box)


def body_text(page: str, entity: str) -> list[str]:
    """Paragraphs of the page, cut per SITES."""
    site = SITES[entity]
    soup = BeautifulSoup(page, "lxml")
    root = soup.select_one(site["root"])
    if root is None:
        raise ValueError(f"root {site['root']} not found")
    for sel in site["remove"]:
        for tag in root.select(sel):
            tag.decompose()
    if entity == "RJF":
        prepare_rj(root)  # before DROP: the tile titles are <button>s
    for tag in root(DROP):
        tag.decompose()
    for sup in root.find_all("sup"):  # footnote numbers -> [n]; keep ® and ™
        t = clean(sup.get_text(""))
        if t.isdigit():
            sup.replace_with(f" [{t}]")
    for br in root.find_all("br"):
        br.replace_with("\n")
    for tag in root.find_all(BLOCK):
        tag.insert_before("\n")
        tag.insert_after("\n")
        if tag.name == "li":
            tag.insert(0, "- ")
    lines, prev = [], None
    for raw in root.get_text("").split("\n"):
        line = clean(raw)
        if not line or line == prev:
            continue
        prev = line
        if any(line.startswith(s) for s in site["stop"]):
            break
        if line in site["drop"] or any(line.startswith(s) for s in site["drop_prefix"]) or line == "-":
            continue
        lines.append(line)
    paras = []  # consecutive list items stay in one paragraph
    for line in lines:
        if line.startswith("- ") and paras and paras[-1].split("\n")[-1].startswith("- "):
            paras[-1] += "\n" + line
        else:
            paras.append(line)
    return [p.replace(ROW, "\n") for p in paras]


def date_metadata(page: str) -> list[str]:
    """T-09 step 2: date-like <meta> tags and JSON-LD date fields (expected: none)."""
    soup = BeautifulSoup(page, "lxml")
    found = [str(m) for m in soup.find_all("meta")
             if DATE_META.search(" ".join(str(v) for k, v in m.attrs.items() if k != "content"))]
    for s in soup.find_all("script", type="application/ld+json"):
        found += re.findall(r'"date\w*"\s*:\s*"[^"]*"', s.get_text())
    return found


def header(doc_id: str, entity: str, url: str, copy: str, as_of: str, earliest: str, title: str) -> str:
    source = (f"{url} (fetched {as_of})" if copy == "live"
              else f"{copy_url(url, copy)} (Wayback Machine copy {copy})")
    return (f"{title}\n"
            f"{FIRM[entity]} advisor recruiting page - content as of {as_of}\n"
            f"Source: {source}\n"
            f"Content as of: {as_of} (date basis: retrieved; the page prints no date)\n"
            f"Date check (ADR-007 T-09): printed date none; page metadata none; HTTP Last-Modified none; "
            f"earliest Wayback capture {earliest} (dates the URL, not this text).\n\n")


def selected(only: list[str]) -> list[tuple]:
    unknown = set(only) - {p[0] for p in PAGES}
    if unknown:
        raise SystemExit(f"not in PAGES: {', '.join(sorted(unknown))}")
    return [p for p in PAGES if not only or p[0] in only]


def fetch(folder: Path, only: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for doc_id, _, url, copy, *_ in selected(only):
        target = folder / f"{doc_id}.html"
        if target.exists():
            print(f"{doc_id}: skip (already fetched)")
            continue
        src = copy_url(url, copy, raw=True)
        req = urllib.request.Request(src, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as r:
            body, final, lm = r.read(), r.geturl(), r.headers.get("Last-Modified")
            lm = lm if copy == "live" else r.headers.get("x-archive-orig-last-modified")
        if copy != "live" and f"/{copy}id_/" not in final:
            raise SystemExit(f"{doc_id}: Wayback redirected to another capture: {final}")
        if lm:
            raise SystemExit(f"{doc_id}: Last-Modified {lm}; T-09 step 3 dates this page, not 'retrieved'")
        if b"wm-ipp" in body or b"web.archive.org" in body:
            raise SystemExit(f"{doc_id}: not a clean original copy (archive markup found)")
        target.write_bytes(body)
        print(f"{doc_id}: {len(body):,} bytes from {src}")
        time.sleep(DELAY)


def check(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def convert_all(folder: Path, out: Path, only: list[str]) -> None:
    """HTML from fetch() (which refuses a page with Last-Modified) -> <doc_id>.txt with the header."""
    out.mkdir(parents=True, exist_ok=True)
    for doc_id, entity, url, copy, as_of, earliest, title, must in selected(only):
        page = (folder / f"{doc_id}.html").read_text(encoding="utf-8")
        check(not date_metadata(page), f"{doc_id}: date metadata {date_metadata(page)[:3]} (T-09 step 2)")
        paras = body_text(page, entity)
        check(bool(paras) and paras[0] == title, f"{doc_id}: first block {paras[:1]}, PAGES says {title!r}")
        body = "\n\n".join(paras[1:])
        low = body.lower()
        check("<" not in body and not any(s in low for s in LEFTOVER), f"{doc_id}: markup or leftover")
        check(not EMAIL.search(body), f"{doc_id}: e-mail address left in the text")
        check(not PHONE.search(body), f"{doc_id}: phone number left in the text")
        check(not PAGE_DATE.search(body), f"{doc_id}: page date {PAGE_DATE.search(body) and PAGE_DATE.search(body).group(0)!r} (T-09 step 1)")
        check(must in body, f"{doc_id}: must-have phrase missing: {must!r}")
        check(len(body) >= 500, f"{doc_id}: only {len(body)} chars")
        text = header(doc_id, entity, url, copy, as_of, earliest, title) + body + "\n"
        (out / f"{doc_id}.txt").write_text(text, encoding="utf-8", newline="\n")
        print(f"{doc_id}: {len(body):,} chars, {len(paras) - 1} paragraphs | content as of {as_of} "
              f"(copy {copy}), earliest capture {earliest}")


def main() -> None:
    if len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        fetch(Path(sys.argv[2]), sys.argv[3:])
    elif len(sys.argv) >= 4 and sys.argv[1] == "convert":
        convert_all(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
