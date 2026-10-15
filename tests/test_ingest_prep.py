"""EDGAR doc IDs, skip-if-present, several filings per run, and the source_registry rows. No network, no DB."""
from __future__ import annotations

import sys
import types

import pytest

from cee.ingest import edgar, load
from cee.ingest.manifest import FIELDS, read_manifest


class FakeFiling:
    def __init__(self, period, filed):
        self.period_of_report, self.filing_date = period, filed
        self.document = types.SimpleNamespace(url=f"https://sec.example/{period}.htm")

    def html(self):
        return f"<html>{self.period_of_report}</html>"


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    path = tmp_path / "manifest.csv"
    path.write_text(",".join(FIELDS) + "\n", encoding="utf-8")
    monkeypatch.setattr(edgar, "write_root", lambda: tmp_path)
    monkeypatch.setattr(edgar, "MANIFEST_PATH", path)
    return path


def test_doc_ids():
    assert edgar.doc_id_for("EDJ", "10-K", "2025-12-31") == "EDJ-10K-2025"
    assert edgar.doc_id_for("MS", "10-Q", "2026-06-30") == "MS-10Q-2026Q2"
    assert edgar.doc_id_for("RJF", "10-Q", "2025-12-31") == "RJF-10Q-2025Q4"
    assert edgar.doc_id_for("BAC", "8-K", "2026-04-15") == "BAC-8K-2026-04-15"


def test_two_quarters_of_one_year_are_two_rows_and_rerun_skips(manifest):
    q1, q2 = FakeFiling("2026-03-31", "2026-05-01"), FakeFiling("2026-06-30", "2026-08-01")
    assert edgar.store_filing("MS", "10-Q", q1, manifest_path=manifest)["doc_id"] == "MS-10Q-2026Q1"
    assert edgar.store_filing("MS", "10-Q", q2, manifest_path=manifest)["doc_id"] == "MS-10Q-2026Q2"
    assert edgar.store_filing("MS", "10-Q", q2, manifest_path=manifest) is None
    rows = read_manifest(manifest)
    assert [r["doc_id"] for r in rows] == ["MS-10Q-2026Q1", "MS-10Q-2026Q2"]
    assert rows[1]["published_at"] == "2026-08-01" and rows[1]["period_end"] == "2026-06-30"


def test_fetch_count_uses_latest_n(manifest, monkeypatch):
    filings = [FakeFiling("2026-06-30", "2026-08-01"), FakeFiling("2026-03-31", "2026-05-01")]
    seen = {}

    class Company:
        def __init__(self, cik):
            seen["cik"] = cik

        def get_filings(self, form):
            seen["form"] = form
            return types.SimpleNamespace(latest=lambda n: filings[0] if n == 1 else filings[:n])

    monkeypatch.setitem(sys.modules, "edgar", types.SimpleNamespace(Company=Company, set_identity=lambda i: None))
    monkeypatch.setattr(edgar, "settings", lambda: types.SimpleNamespace(edgar_identity="Test test@example.com"))
    store = edgar.store_filing
    monkeypatch.setattr(edgar, "store_filing", lambda e, f, filing, by: store(e, f, filing, by, manifest))
    rows = edgar.fetch("MS", "10-Q", count=2)
    assert seen == {"cik": "895421", "form": "10-Q"}
    assert [r["doc_id"] for r in rows] == ["MS-10Q-2026Q2", "MS-10Q-2026Q1"]
    assert edgar.fetch("MS", "10-Q", count=2) == []



def test_registry_rows_match_csv():
    rows = load.registry_rows()
    assert len(rows) == 49
    assert len({(r[0], r[1], r[2]) for r in rows}) == 49   # primary key holds
    assert all(r[0] and r[1] and r[2] for r in rows)
