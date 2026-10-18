"""Quarterly earnings releases from EDGAR: exhibit 99.1 of each Item 2.02 8-K (ADR-007 T-03).

Owner: C2 (Mingmin Kong). The release, not the 8-K cover page, is stored; tier 2, doc_type press.
Usage: python -m cee.ingest.releases --entity RJF --count 4
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import types
from pathlib import Path

from cee.config import MANIFEST_PATH, entity_by_id, settings, write_root
from cee.ingest.manifest import read_manifest, sha256_file, upsert_row

EARNINGS_ITEM = "2.02"      # 8-K Item 2.02: Results of Operations and Financial Condition
RELEASE_EXHIBIT = "EX-99.1"
SCAN = 40                   # latest 8-Ks searched for earnings ones (a firm files ~4-25 a year)


class MissingRelease(Exception):
    """An earnings 8-K without exhibit 99.1: no row is written, the reason is reported."""


def release_doc_id(entity_id: str, filed: str) -> str:
    """Spec form <ENTITY>-PR-<date>-NN; one earnings release per firm per day, so -01."""
    return f"{entity_id}-PR-{filed}-01"


def quarter_end_before(filed: str) -> str:
    """Last calendar quarter-end before the filing date: the quarter the release reports."""
    day = dt.date.fromisoformat(filed)
    quarter_start = dt.date(day.year, (day.month - 1) // 3 * 3 + 1, 1)
    return (quarter_start - dt.timedelta(days=1)).isoformat()


def is_earnings_8k(filing) -> bool:
    return EARNINGS_ITEM in [i.strip() for i in str(filing.items or "").split(",")]


INDEX_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
INDEX_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
INDEX_HREF = re.compile(r'href="([^"]+)"', re.I)


def parse_index(page: str) -> list[tuple[str, str]]:
    """(document type, absolute URL) for each row of an EDGAR filing index page."""
    out = []
    for row in INDEX_ROW.findall(page):
        cells = INDEX_CELL.findall(row)
        href = INDEX_HREF.search(row)
        if len(cells) >= 4 and href:
            doc_type = re.sub(r"<[^>]+>|\s+", " ", cells[3]).strip()
            url = href.group(1)
            out.append((doc_type, url if url.startswith("http") else f"https://www.sec.gov{url}"))
    return out


def index_attachments(filing) -> list:
    """Fallback when edgartools lists no attachments. Seen for MS 2026-01-15: its full-text
    submission was cut off mid-download while SEC was throttling us, and edgartools' HTTP cache
    keeps /Archives files forever, so every re-run parsed the same truncated bundle. The
    filing's EDGAR index page still lists the exhibits."""
    from edgar.httprequests import download_text

    return [types.SimpleNamespace(document_type=t, document=u.rsplit("/", 1)[-1], url=u,
                                  download=lambda u=u: download_text(u))
            for t, u in parse_index(download_text(filing.homepage_url) or "")]


def store_release(entity_id: str, filing, added_by: str = "C2",
                  manifest_path: Path = MANIFEST_PATH) -> dict | None:
    """Write one release's HTML and its manifest row. Returns None if the doc_id is already there."""
    filed = str(filing.filing_date)
    doc_id = release_doc_id(entity_id, filed)
    if any(r["doc_id"] == doc_id for r in read_manifest(manifest_path)):
        return None
    attachments = list(filing.attachments) or index_attachments(filing)
    exhibit = next((a for a in attachments if a.document_type == RELEASE_EXHIBIT), None)
    if exhibit is None:
        raise MissingRelease(f"{doc_id}: earnings 8-K filed {filed} has no {RELEASE_EXHIBIT}")
    html = exhibit.download()
    if not html:
        raise MissingRelease(f"{doc_id}: {RELEASE_EXHIBIT} ({exhibit.url}) downloaded empty")
    # A single-document download is not checked for completeness upstream, and a transfer cut
    # off by SEC throttling can be cached as if whole: never store half a release.
    if not html.rstrip().lower().endswith("</html>"):
        raise MissingRelease(f"{doc_id}: {RELEASE_EXHIBIT} ({exhibit.url}) looks cut off "
                             f"(no closing </html>); delete its edgartools cache entry and re-run")
    storage_path = f"raw/{doc_id}.htm"
    target = write_root() / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8", newline="")
    row = {
        "doc_id": doc_id, "entity_id": entity_id, "doc_type": "press", "source_tier": 2,
        "published_at": filed, "period_end": quarter_end_before(filed),
        "url": exhibit.url, "storage_path": storage_path,
        "sha256": sha256_file(target), "added_by": added_by,
        "added_at": dt.date.today().isoformat(),
    }
    upsert_row(row, manifest_path)
    return row


def fetch(entity_id: str, count: int = 4, added_by: str = "C2",
          manifest_path: Path = MANIFEST_PATH) -> dict[str, list]:
    """Store the releases of the latest `count` earnings 8-Ks. Returns stored rows, skipped
    doc_ids (already in the manifest) and missing (doc_id, reason) pairs."""
    from edgar import Company, set_identity  # heavy import; ingestion only

    identity = settings().edgar_identity
    if not identity:
        raise SystemExit("Set EDGAR_IDENTITY in .env (SEC requires a name and email).")
    set_identity(identity)

    entity = entity_by_id(entity_id)
    cik = str(entity.get("cik") or "") if entity else ""
    if not cik or cik.startswith("TODO"):
        raise SystemExit(f"{entity_id}: CIK not verified in config/entities.yaml.")

    earnings = [f for f in Company(cik).get_filings(form="8-K").latest(SCAN) if is_earnings_8k(f)]
    result: dict[str, list] = {"stored": [], "skipped": [], "missing": []}
    for filing in earnings[:count]:
        try:
            row = store_release(entity_id, filing, added_by, manifest_path)
        except MissingRelease as e:
            result["missing"].append((release_doc_id(entity_id, str(filing.filing_date)), str(e)))
            continue
        if row is None:
            result["skipped"].append(release_doc_id(entity_id, str(filing.filing_date)))
        else:
            result["stored"].append(row)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", required=True)
    ap.add_argument("--count", type=int, default=4, help="how many of the latest earnings releases")
    args = ap.parse_args()
    res = fetch(args.entity, args.count)
    for r in res["stored"]:
        print(f"stored {r['doc_id']} -> {r['storage_path']} period_end={r['period_end']} sha256={r['sha256'][:12]}...")
    for d in res["skipped"]:
        print(f"skip {d}: already in the manifest")
    for d, reason in res["missing"]:
        print(f"MISSING {d}: {reason}")
