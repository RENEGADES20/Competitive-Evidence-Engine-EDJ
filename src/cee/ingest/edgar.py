"""Fetch a filing from EDGAR, store the raw file, and record it in the manifest.

Skeleton placeholder, owner: C1 (Jingran Fang).
Usage: python -m cee.ingest.edgar --entity EDJ --form 10-K
       python -m cee.ingest.edgar --entity MS --form 10-Q --count 4
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from cee.config import MANIFEST_PATH, entity_by_id, settings, write_root
from cee.ingest.manifest import read_manifest, sha256_file, upsert_row

FORM_CODES = {"10-K": "10K", "10-Q": "10Q", "8-K": "8K"}


def doc_id_for(entity_id: str, form: str, period: str) -> str:
    """10-K: one per year (EDJ-10K-2025). 10-Q: calendar quarter of period_end (MS-10Q-2026Q2).
    Other forms: the full period date (BAC-8K-2026-04-15), since a year can hold many."""
    code = FORM_CODES.get(form, form.replace("-", ""))
    if form == "10-K":
        return f"{entity_id}-{code}-{period[:4]}"
    if form == "10-Q":
        return f"{entity_id}-{code}-{period[:4]}Q{(int(period[5:7]) - 1) // 3 + 1}"
    return f"{entity_id}-{code}-{period[:10]}"


def store_filing(entity_id: str, form: str, filing, added_by: str = "TL",
                 manifest_path: Path = MANIFEST_PATH) -> dict | None:
    """Write one filing's HTML and its manifest row. Returns None if the doc_id is already there."""
    period = str(filing.period_of_report)
    doc_id = doc_id_for(entity_id, form, period)
    if any(r["doc_id"] == doc_id for r in read_manifest(manifest_path)):
        return None
    storage_path = f"raw/{doc_id}.htm"
    target = write_root() / storage_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(filing.html(), encoding="utf-8", newline="")
    row = {
        "doc_id": doc_id, "entity_id": entity_id, "doc_type": form, "source_tier": 2,
        "published_at": str(filing.filing_date), "period_end": period,
        "url": filing.document.url, "storage_path": storage_path,
        "sha256": sha256_file(target), "added_by": added_by,
        "added_at": dt.date.today().isoformat(),
    }
    upsert_row(row, manifest_path)
    return row


def fetch(entity_id: str, form: str = "10-K", count: int = 1, added_by: str = "TL") -> list[dict]:
    """Store the latest `count` filings of `form`. Filings already in the manifest are skipped."""
    from edgar import Company, set_identity  # heavy import; ingestion only

    identity = settings().edgar_identity
    if not identity:
        raise SystemExit("Set EDGAR_IDENTITY in .env (SEC requires a name and email).")
    set_identity(identity)

    entity = entity_by_id(entity_id)
    cik = str(entity.get("cik") or "") if entity else ""
    if not cik or cik.startswith("TODO"):
        raise SystemExit(f"{entity_id}: CIK not verified in config/entities.yaml.")

    latest = Company(cik).get_filings(form=form).latest(count)
    filings = [latest] if count == 1 else list(latest)
    stored = []
    for filing in filings:
        row = store_filing(entity_id, form, filing, added_by)
        if row is None:
            print(f"skip {doc_id_for(entity_id, form, str(filing.period_of_report))}: already in the manifest")
        else:
            stored.append(row)
    return stored


def fetch_latest(entity_id: str, form: str = "10-K", added_by: str = "TL") -> dict | None:
    rows = fetch(entity_id, form, 1, added_by)
    return rows[0] if rows else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", default="EDJ")
    ap.add_argument("--form", default="10-K")
    ap.add_argument("--count", type=int, default=1, help="how many of the latest filings")
    args = ap.parse_args()
    for r in fetch(args.entity, args.form, args.count):
        print(f"stored {r['doc_id']} -> {r['storage_path']} sha256={r['sha256'][:12]}...")
