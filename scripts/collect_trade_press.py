"""Collect 90 days of trade-press articles about the five and store them as tier 4 `trade` documents (#57).

Owner: C3. Plan: plans/0057-trade-press.md. Spec: specs/transcripts-ir.md (trade_press_item).
ADR-007: full text may be stored (T-06), scraping is allowed with a polite delay and an honest user
agent (T-08); trade press stays tier 4, "indicative only". Dates come from the article page (T-09):
JSON-LD datePublished, else article:published_time; never the download date.

Three steps, so the article list can be reviewed before any article text is downloaded:

  python scripts/collect_trade_press.py discover <outlet> [--since YYYY-MM-DD --until YYYY-MM-DD]
      list candidate article URLs from the outlet's listing pages -> data/interim/trade_press/<outlet>.json
  python scripts/collect_trade_press.py fetch <outlet>
      download the listed articles (cached in data/interim/trade_press/html/, one request per DELAY seconds)
  python scripts/collect_trade_press.py convert <outlet> [--register]
      keep articles about the five, write data/raw/<doc_id>.txt; --register adds manifest rows

Which firm an article is about: aliases from config/entities.yaml, whole words, case-sensitive, without
the bare tickers (MS, SCHW, RJF, BAC, MSWM collide with "Ms." and other words). Kept if a firm is named in
the headline or mentioned >= MIN_MENTIONS times in the body. entity_id = first firm in the headline,
else the most-mentioned firm. Merrill -> MER. An article naming only Bank of America is not kept: BAC
is not one of the five, and keeping GWIM-wide stories out avoids mixing BAC and Merrill (Q4, Q27).
One entity per document (the manifest and the retrieval filter take one); every firm mentioned is
listed in the file header.
Re-runs skip any URL already in data/manifest.csv, so they add no duplicates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cee.config import entities_config  # noqa: E402
from cee.ingest.manifest import read_manifest, sha256_file, upsert_row  # noqa: E402

FIVE = ["EDJ", "MS", "SCHW", "MER", "RJF"]
TICKER = re.compile(r"^[A-Z*]{2,5}$")  # bare tickers are not counted
MIN_MENTIONS = 3
USER_AGENT = "CEE-student-prototype/0.1 (internal non-commercial research)"
DELAY = 5  # seconds between requests to the same site (ADR-007 T-08)
WORK = REPO / "data" / "interim" / "trade_press"
RAW = REPO / "data" / "raw"
EASTERN = ZoneInfo("America/New_York")
SINCE, UNTIL = "2026-08-18", "2026-11-16"  # 90 days back from 2026-11-16 (#57)


# --- which firm an article is about -------------------------------------------------------------

def alias_patterns() -> dict[str, re.Pattern]:
    out = {}
    for e in entities_config()["entities"]:
        if e["id"] not in FIVE:
            continue
        names = sorted((a for a in e.get("aliases", []) + [e["name"]] if not TICKER.match(a)),
                       key=len, reverse=True)
        out[e["id"]] = re.compile(r"(?<![\w*])(?:" + "|".join(re.escape(n) for n in names) + r")(?![\w*])")
    return out


def mentions(text: str, patterns: dict[str, re.Pattern] | None = None) -> dict[str, int]:
    patterns = patterns or alias_patterns()
    return {eid: len(p.findall(text)) for eid, p in patterns.items() if p.search(text)}


def choose_entity(headline: str, body: str, patterns: dict[str, re.Pattern] | None = None) -> str | None:
    """First firm named in the headline, else the most-mentioned firm with >= MIN_MENTIONS, else None."""
    patterns = patterns or alias_patterns()
    in_head = [(p.search(headline).start(), eid) for eid, p in patterns.items() if p.search(headline)]
    if in_head:
        return min(in_head)[1]
    counts = mentions(body, patterns)
    best = [eid for eid, n in counts.items() if n >= MIN_MENTIONS]
    if not best:
        return None
    first = {eid: patterns[eid].search(body).start() for eid in best}
    return min(best, key=lambda eid: (-counts[eid], first[eid]))


# --- pages ----------------------------------------------------------------------------------------

def canonical(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme or "https", p.netloc.lower(), p.path.rstrip("/"), "", ""))


def page_date(page: str, tz: ZoneInfo | timezone = EASTERN) -> str:
    """Article date (YYYY-MM-DD) from JSON-LD datePublished, else article:published_time, read in the
    time zone the outlet prints its date line in (checked per outlet against the printed date)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page, "lxml")
    found = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                if d.get("datePublished"):
                    found.append(d["datePublished"])
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
            elif isinstance(d, list):
                stack.extend(d)
    meta = soup.find("meta", property="article:published_time")
    if not found and meta and meta.get("content"):
        found.append(meta["content"])
    if not found:
        raise ValueError("no datePublished or article:published_time on the page")
    stamp = datetime.fromisoformat(found[0].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        return stamp.date().isoformat()
    return stamp.astimezone(tz).date().isoformat()


def article(page: str, outlet: "Outlet") -> tuple[str, str]:
    """(headline, body text) from every element matching the outlet's body selector, in page order
    (InvestmentNews wraps each paragraph in its own body div); one paragraph per block."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page, "lxml")
    h1 = soup.find("h1")
    headline = " ".join(h1.get_text(" ").split()) if h1 else ""
    roots = [r for r in soup.select(outlet.body_selector) if r.find_parent(class_=None) is not None]
    roots = [r for r in roots if not any(p in roots for p in r.parents)]  # outermost matches only
    if not headline or not roots:
        raise ValueError("headline or article body not found")
    blocks = []
    for root in roots:
        for t in root.select("script, style, figure, aside, form, iframe, .ad, [class*=newsletter], [class*=related]"):
            t.decompose()
        for el in root.find_all(["p", "h2", "h3", "li", "blockquote"]):
            if el.find_parent(["p", "li", "blockquote"]) is not None:
                continue
            t = " ".join(el.get_text(" ").split())
            if t and t not in blocks[-1:]:
                blocks.append(t)
    body = "\n\n".join(blocks)
    if len(body.split()) < 80:
        raise ValueError(f"article body too short ({len(body.split())} words): paywall or layout change")
    return headline, body


# --- outlets ----------------------------------------------------------------------------------------

@dataclass
class Outlet:
    key: str        # command-line name and file prefix
    code: str       # doc_id part
    publisher: str  # manifest publisher
    body_selector: str
    date_tz: ZoneInfo | timezone = EASTERN  # zone of the printed date line (RIABiz prints the UTC date)


# Body selectors and date zones checked on the fetched pages (2026-11-16): the computed date equals the
# printed date line on every InvestmentNews (div.article-detail__date), WealthManagement and AdvisorHub
# page; RIABiz bylines print the UTC date of article:published_time.
INVESTMENTNEWS = Outlet("investmentnews", "IN", "InvestmentNews", "div.wrapper--detail__body, div.article-content")
WEALTHMANAGEMENT = Outlet("wealthmanagement", "WM", "WealthManagement.com", "div.ContentModule-Wrapper")
RIABIZ = Outlet("riabiz", "RB", "RIABiz", "div.ArticleBody-wrapper", timezone.utc)
ADVISORHUB = Outlet("advisorhub", "AH", "AdvisorHub", "div.blog-content-wrapper")
OUTLETS = {o.key: o for o in [INVESTMENTNEWS, WEALTHMANAGEMENT, RIABIZ, ADVISORHUB]}

# InvestmentNews company pages, newest first, ?page=N. Merrill has no page of its own: its stories are
# listed under Bank of America and kept only when they name Merrill.
IN_COMPANIES = {
    "EDJ": "https://www.investmentnews.com/companies/edward-jones/262941",
    "MS": "https://www.investmentnews.com/companies/morgan-stanley/262940",
    "SCHW": "https://www.investmentnews.com/companies/charles-schwab/257314",
    "MER": "https://www.investmentnews.com/companies/bank-of-america/262904",
    "RJF": "https://www.investmentnews.com/companies/raymond-james/263040",
}
IN_ITEM_DATE = re.compile(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) (\d{1,2}), (20\d\d)\b")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def in_listing(page: str, base: str) -> list[tuple[str, str, str]]:
    """[(url, listing date YYYY-MM-DD, title)] from one InvestmentNews company page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page, "lxml")
    out = []
    for item in soup.select("div.tool-sublist__item"):
        a = item.select_one("a.tool-sublist__item__title")
        when = item.select_one(".tool-sublist__item__date")
        m = IN_ITEM_DATE.search(" ".join(when.get_text(" ").split())) if when else None
        if a is None or not a.get("href") or m is None:
            continue
        d = datetime.strptime(" ".join(m.groups()), "%b %d %Y").date().isoformat()
        title = " ".join(a.get_text(" ").split())
        out.append((canonical(urljoin(base, a["href"])), d, title))
    return out


def discover_investmentnews(since: str, until: str) -> list[dict]:
    seen, out = set(), []
    for listed_under, base in IN_COMPANIES.items():
        for n in range(1, 50):
            items = in_listing(get(base if n == 1 else f"{base}?page={n}"), base)
            time.sleep(DELAY)
            if not items:
                break
            for url, d, title in items:
                if since <= d <= until and url not in seen:
                    seen.add(url)
                    out.append({"url": url, "listing_date": d, "title": title, "listed_under": listed_under})
            if min(d for _, d, _ in items) < since:
                break
    return out


def discover_wealthmanagement(since: str, until: str) -> list[dict]:
    """Monthly archive sitemaps. The sitemap has no titles, so only URLs whose slug names one of the
    five are listed (fetching ~600 articles a quarter to find body-only mentions is not polite)."""
    slug = re.compile(r"edward-jones|morgan-stanley|e-?trade|schwab|merrill|raymond-james", re.I)
    months = sorted({since[:7], until[:7]} | {f"{since[:4]}-{m:02d}" for m in range(int(since[5:7]), int(until[5:7]) + 1)})
    out = []
    for ym in months:
        name = datetime.strptime(ym, "%Y-%m").strftime("%B").lower()
        xml = get(f"https://www.wealthmanagement.com/article/archive/{ym[:4]}/{name}.xml")
        time.sleep(DELAY)
        for url, mod in re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", xml):
            if since <= mod[:10] <= until and slug.search(url):
                out.append({"url": canonical(url), "listing_date": mod[:10], "title": url.rsplit("/", 1)[-1],
                            "listed_under": "slug"})
    return out


RIABIZ_TAGS = {"SCHW": "charles-schwab-co", "MS": "morgan-stanley", "MER": "merrill-lynch",
               "RJF": "raymond-james"}  # no Edward Jones tag on RIABiz (2026-11-16)
RIABIZ_URL_DATE = re.compile(r"/a/(\d{4})/(\d{1,2})/(\d{1,2})/")


def discover_riabiz(since: str, until: str) -> list[dict]:
    seen, out = set(), []
    for listed_under, tag in RIABIZ_TAGS.items():
        for n in range(1, 20):
            page = get(f"https://riabiz.com/tags/{tag}/page/{n}")
            time.sleep(DELAY)
            hrefs = list(dict.fromkeys(re.findall(r'href="(/a/\d{4}/\d{1,2}/\d{1,2}/[^"#?]+)"', page)))
            if not hrefs:
                break
            dates = []
            for h in hrefs:
                y, m, d = RIABIZ_URL_DATE.search(h).groups()
                day = f"{y}-{int(m):02d}-{int(d):02d}"
                dates.append(day)
                url = canonical("https://riabiz.com" + h)
                if since <= day <= until and url not in seen:
                    seen.add(url)
                    out.append({"url": url, "listing_date": day, "title": h.rsplit("/", 1)[-1][:120],
                                "listed_under": listed_under})
            if max(dates) < since:
                break
    return out


def discover_advisorhub(since: str, until: str) -> list[dict]:
    """RSS only (10 latest items): the tag pages answer 403 to an honest user agent (2026-11-16)."""
    from email.utils import parsedate_to_datetime

    rss = get("https://www.advisorhub.com/feed/")
    out = []
    for item in re.findall(r"<item>(.*?)</item>", rss, re.S):
        link = re.search(r"<link>([^<]+)</link>", item).group(1)
        title = re.sub(r"<!\[CDATA\[|\]\]>", "", re.search(r"<title>(.*?)</title>", item, re.S).group(1)).strip()
        day = parsedate_to_datetime(re.search(r"<pubDate>([^<]+)</pubDate>", item).group(1)).astimezone(EASTERN).date().isoformat()
        if since <= day <= until:
            out.append({"url": canonical(link), "listing_date": day, "title": title, "listed_under": "rss"})
    return out


DISCOVER = {"investmentnews": discover_investmentnews, "wealthmanagement": discover_wealthmanagement,
            "riabiz": discover_riabiz, "advisorhub": discover_advisorhub}


# --- steps ----------------------------------------------------------------------------------------

def stored_urls() -> set[str]:
    return {canonical(r["url"]) for r in read_manifest() if r.get("url")}


def html_path(url: str) -> Path:
    return WORK / "html" / (hashlib.sha256(url.encode()).hexdigest()[:20] + ".html")


def next_doc_id(entity: str, day: str, code: str, taken: set[str]) -> str:
    n = 1
    while f"{entity}-TRADE-{day}-{code}-{n:02d}" in taken:
        n += 1
    return f"{entity}-TRADE-{day}-{code}-{n:02d}"


def header(headline: str, outlet: Outlet, day: str, url: str, counts: dict[str, int]) -> str:
    firms = ", ".join(f"{e} ({n})" for e, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return (f"{headline}\n"
            f"{outlet.publisher} trade press - {day} (tier 4, indicative only)\n"
            f"Source: {url}\n"
            f"Firms mentioned (alias count): {firms}\n\n")


def discover(outlet: Outlet, since: str, until: str) -> None:
    items = DISCOVER[outlet.key](since, until)
    known = stored_urls()
    fresh = [i for i in items if i["url"] not in known]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{outlet.key}.json").write_text(json.dumps(fresh, indent=1), encoding="utf-8")
    print(f"{outlet.key}: {len(items)} listed in {since}..{until}, {len(items) - len(fresh)} already stored, "
          f"{len(fresh)} new -> {WORK / (outlet.key + '.json')}")


def fetch(outlet: Outlet) -> None:
    items = json.loads((WORK / f"{outlet.key}.json").read_text(encoding="utf-8"))
    (WORK / "html").mkdir(parents=True, exist_ok=True)
    for i in items:
        target = html_path(i["url"])
        if target.exists():
            continue
        try:
            target.write_text(get(i["url"]), encoding="utf-8")
            print(f"fetched {i['url']}")
        except Exception as e:  # noqa: BLE001 - report and continue with the rest
            print(f"FAILED {i['url']}: {e}")
        time.sleep(DELAY)


def convert(outlet: Outlet, register: bool) -> None:
    items = json.loads((WORK / f"{outlet.key}.json").read_text(encoding="utf-8"))
    patterns, known = alias_patterns(), stored_urls()
    taken = {r["doc_id"] for r in read_manifest()}
    kept = skipped = 0
    for i in items:
        if i["url"] in known:
            continue
        path = html_path(i["url"])
        if not path.exists():
            print(f"not fetched: {i['url']}")
            continue
        page = path.read_text(encoding="utf-8")
        try:
            day = page_date(page, outlet.date_tz)
            headline, body = article(page, outlet)
        except ValueError as e:
            print(f"SKIP {i['url']}: {e}")
            skipped += 1
            continue
        if not SINCE <= day <= UNTIL:
            print(f"SKIP {i['url']}: page date {day} outside {SINCE}..{UNTIL}")
            skipped += 1
            continue
        entity = choose_entity(headline, body, patterns)
        if entity is None:
            print(f"SKIP {i['url']}: not about the five ({mentions(headline + ' ' + body, patterns)})")
            skipped += 1
            continue
        doc_id = next_doc_id(entity, day, outlet.code, taken)
        taken.add(doc_id)
        counts = mentions(headline + "\n" + body, patterns)
        out = RAW / f"{doc_id}.txt"
        out.write_text(header(headline, outlet, day, i["url"], counts) + body + "\n", encoding="utf-8", newline="\n")
        kept += 1
        print(f"{doc_id}: {headline[:80]} | {counts}")
        if register:
            upsert_row({"doc_id": doc_id, "entity_id": entity, "doc_type": "trade", "source_tier": "4",
                        "published_at": day, "date_basis": "source", "period_end": "", "url": i["url"],
                        "storage_path": f"raw/{doc_id}.txt", "sha256": sha256_file(out), "added_by": "C3",
                        "added_at": date.today().isoformat(), "publisher": outlet.publisher})
            known.add(i["url"])
    print(f"{outlet.key}: kept {kept}, skipped {skipped}{' (registered)' if register else ''}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=["discover", "fetch", "convert"])
    ap.add_argument("outlet", choices=sorted(OUTLETS))
    ap.add_argument("--since", default=SINCE)
    ap.add_argument("--until", default=UNTIL)
    ap.add_argument("--register", action="store_true", help="convert: add manifest rows")
    a = ap.parse_args(argv)
    outlet = OUTLETS[a.outlet]
    if a.step == "discover":
        discover(outlet, a.since, a.until)
    elif a.step == "fetch":
        fetch(outlet)
    else:
        convert(outlet, a.register)


if __name__ == "__main__":
    main()
