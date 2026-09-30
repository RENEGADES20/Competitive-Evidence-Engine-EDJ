"""Fetch a filing from EDGAR, store the raw file, and record it in the manifest.

Skeleton placeholder, owner: C1 (Jingran Fang).
Usage: python -m cee.ingest.edgar --entity EDJ --form 10-K
"""
from __future__ import annotations

import argparse
import datetime as dt

from cee.config import entity_by_id, settings, write_root
from cee.ingest.manifest import sha256_file, upsert_row

FORM_CODES = {"10-K": "10K", "10-Q": "10Q", "8-K": "8K"}


def fetch_latest(entity_id: str, form: str = "10-K", added_by: str = "TL") -> dict:
    from edgar import Company, set_identity  # heavy import; ingestion only

    identity = settings().edgar_identity
    if not identity:
        raise SystemExit("Set EDGAR_IDENTITY in .env (SEC requires a name and email).")
    set_identity(identity)

    entity = entity_by_id(entity_id)
    cik = str(entity.get("cik") or "") if entity else ""
    if not cik or cik.startswith("TODO"):
        raise SystemExit(f"{entity_id}: CIK not verified in config/entities.yaml.")

    filing = Company(cik).get_filings(form=form).latest(1)
    period = str(filing.period_of_report)
    doc_id = f"{entity_id}-{FORM_CODES.get(form, form)}-{period[:4]}"
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
    upsert_row(row)
    return row


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", default="EDJ")
    ap.add_argument("--form", default="10-K")
    args = ap.parse_args()
    r = fetch_latest(args.entity, args.form)
    print(f"stored {r['doc_id']} -> {r['storage_path']} sha256={r['sha256'][:12]}...")
