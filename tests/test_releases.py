"""Earnings releases from 8-K exhibit 99.1: filing choice, exhibit choice, IDs, dates, skip. No network."""
from __future__ import annotations

import sys
import types

import pytest

from cee.ingest import releases
from cee.ingest.manifest import FIELDS, read_manifest


def attachment(doc_type, name):
    return types.SimpleNamespace(
        document_type=doc_type, document=name, url=f"https://sec.example/{name}",
        download=lambda: f"<html>{doc_type} {name}</html>")


class FakeFiling:
    def __init__(self, filed, items="2.02,9.01", exhibits=("EX-99.1", "EX-99.2")):
        self.filing_date, self.items = filed, items
        self.attachments = [attachment("8-K", "cover.htm")] + [
            attachment(t, f"{t.lower()}-{filed}.htm") for t in exhibits]


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    path = tmp_path / "manifest.csv"
    path.write_text(",".join(FIELDS) + "\n", encoding="utf-8")
    monkeypatch.setattr(releases, "write_root", lambda: tmp_path)
    monkeypatch.setattr(releases, "MANIFEST_PATH", path)
    return path


def test_doc_id_and_quarter_end():
    assert releases.release_doc_id("RJF", "2026-07-22") == "RJF-PR-2026-07-22-01"
    assert releases.quarter_end_before("2026-07-22") == "2026-06-30"
    assert releases.quarter_end_before("2026-01-14") == "2025-12-31"
    assert releases.quarter_end_before("2026-10-14") == "2026-09-30"
    assert releases.quarter_end_before("2026-04-01") == "2026-03-31"


def test_only_item_202_is_an_earnings_8k():
    assert releases.is_earnings_8k(FakeFiling("2026-01-15", items="2.02,7.01,9.01"))
    assert not releases.is_earnings_8k(FakeFiling("2026-06-24", items="8.01,9.01"))
    assert not releases.is_earnings_8k(FakeFiling("2026-06-24", items="12.02"))
    assert not releases.is_earnings_8k(FakeFiling("2026-06-24", items=None))


def test_stores_exhibit_991_not_cover_or_992(manifest, tmp_path):
    row = releases.store_release("BAC", FakeFiling("2026-07-14", exhibits=("EX-99.1", "EX-99.2", "EX-99.3")),
                                 manifest_path=manifest)
    assert row["doc_id"] == "BAC-PR-2026-07-14-01" and row["entity_id"] == "BAC"
    assert row["doc_type"] == "press" and row["source_tier"] == 2
    assert row["published_at"] == "2026-07-14" and row["period_end"] == "2026-06-30"
    assert row["url"] == "https://sec.example/ex-99.1-2026-07-14.htm"
    stored = (tmp_path / row["storage_path"]).read_text(encoding="utf-8")
    assert stored == "<html>EX-99.1 ex-99.1-2026-07-14.htm</html>"
    assert read_manifest(manifest)[0]["sha256"] == row["sha256"]


def test_missing_exhibit_gives_a_reason_and_no_row(manifest):
    with pytest.raises(releases.MissingRelease, match="no EX-99.1"):
        releases.store_release("MS", FakeFiling("2026-04-15", exhibits=("EX-99.2",)), manifest_path=manifest)
    assert read_manifest(manifest) == []


INDEX_PAGE = """<table class="tableFile">
<tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th><th>Size</th></tr>
<tr><td>1</td><td>8-K</td><td><a href="/Archives/edgar/data/895421/000089542126000007/ms-20260115.htm">ms-20260115.htm</a></td><td>8-K</td><td>1</td></tr>
<tr class="evenRow"><td>2</td><td>EX-99.1</td><td><a href="/Archives/edgar/data/895421/000089542126000007/a4q25msearningsrelease.htm">a4q25msearningsrelease.htm</a></td><td>EX-99.1</td><td>2</td></tr>
<tr><td>3</td><td>EX-99.2</td><td><a href="/Archives/edgar/data/895421/000089542126000007/a4q25msfinancialsupplement.htm">x</a></td><td>EX-99.2</td><td>3</td></tr>
</table>"""


def test_parse_index_lists_types_and_absolute_urls():
    rows = releases.parse_index(INDEX_PAGE)
    assert [t for t, _ in rows] == ["8-K", "EX-99.1", "EX-99.2"]
    assert rows[1][1] == "https://www.sec.gov/Archives/edgar/data/895421/000089542126000007/a4q25msearningsrelease.htm"


def test_index_page_used_when_edgartools_sees_no_attachments(manifest, monkeypatch):
    filing = FakeFiling("2026-01-15")
    filing.attachments = []
    monkeypatch.setattr(releases, "index_attachments", lambda f: [attachment("EX-99.1", "a4q25msearningsrelease.htm")])
    row = releases.store_release("MS", filing, manifest_path=manifest)
    assert row["url"] == "https://sec.example/a4q25msearningsrelease.htm"
    assert row["period_end"] == "2025-12-31"


HOMEPAGE = "https://www.sec.gov/Archives/edgar/data/895421/0000895421-26-000007-index.html"


def fake_downloads(monkeypatch, pages):
    """Real index_attachments over a fake edgar.httprequests: each URL returns its own body."""
    module = types.ModuleType("edgar.httprequests")
    module.download_text = lambda url: pages[url]
    monkeypatch.setitem(sys.modules, "edgar.httprequests", module)


def test_index_fallback_downloads_the_exhibit_991_body(manifest, monkeypatch, tmp_path):
    base = "https://www.sec.gov/Archives/edgar/data/895421/000089542126000007/"
    fake_downloads(monkeypatch, {
        HOMEPAGE: INDEX_PAGE,
        base + "ms-20260115.htm": "<html>8-K cover</html>",
        base + "a4q25msearningsrelease.htm": "<html>MS fourth quarter release</html>",
        base + "a4q25msfinancialsupplement.htm": "<html>MS financial supplement</html>",
    })
    filing = FakeFiling("2026-01-15")
    filing.attachments, filing.homepage_url = [], HOMEPAGE
    row = releases.store_release("MS", filing, manifest_path=manifest)
    assert row["url"] == base + "a4q25msearningsrelease.htm"
    assert (tmp_path / row["storage_path"]).read_text(encoding="utf-8") == "<html>MS fourth quarter release</html>"


def test_index_page_without_exhibit_991_gives_a_reason(manifest, monkeypatch):
    fake_downloads(monkeypatch, {HOMEPAGE: INDEX_PAGE.replace("EX-99.1", "EX-99.3")})
    filing = FakeFiling("2026-01-15")
    filing.attachments, filing.homepage_url = [], HOMEPAGE
    with pytest.raises(releases.MissingRelease, match="no EX-99.1"):
        releases.store_release("MS", filing, manifest_path=manifest)
    assert read_manifest(manifest) == []


def test_cut_off_download_is_not_stored(manifest, tmp_path):
    filing = FakeFiling("2026-01-15")
    filing.attachments[1].download = lambda: "<html><body>Morgan Stanley Fourth Quarter 2025 Earn"
    with pytest.raises(releases.MissingRelease, match="cut off"):
        releases.store_release("MS", filing, manifest_path=manifest)
    assert read_manifest(manifest) == []
    assert not (tmp_path / "raw" / "MS-PR-2026-01-15-01.htm").exists()


def fake_edgar(monkeypatch, filings, seen):
    class Company:
        def __init__(self, cik):
            seen["cik"] = cik

        def get_filings(self, form):
            seen["form"] = form
            return types.SimpleNamespace(latest=lambda n: filings[:n])

    monkeypatch.setitem(sys.modules, "edgar", types.SimpleNamespace(Company=Company, set_identity=lambda i: None))
    monkeypatch.setattr(releases, "settings", lambda: types.SimpleNamespace(edgar_identity="Test test@example.com"))


def test_fetch_takes_latest_n_earnings_8ks_and_rerun_skips(manifest, monkeypatch):
    filings = [FakeFiling("2026-07-22"), FakeFiling("2026-06-24", items="8.01,9.01"),
               FakeFiling("2026-04-22"), FakeFiling("2026-01-28", exhibits=("EX-99.2",)),
               FakeFiling("2025-10-22"), FakeFiling("2025-07-23")]
    seen = {}
    fake_edgar(monkeypatch, filings, seen)
    result = releases.fetch("RJF", count=4, manifest_path=manifest)
    assert seen == {"cik": "720005", "form": "8-K"}
    assert [r["doc_id"] for r in result["stored"]] == [
        "RJF-PR-2026-07-22-01", "RJF-PR-2026-04-22-01", "RJF-PR-2025-10-22-01"]
    assert [d for d, _ in result["missing"]] == ["RJF-PR-2026-01-28-01"]
    again = releases.fetch("RJF", count=4, manifest_path=manifest)
    assert again["stored"] == [] and len(again["skipped"]) == 3
    assert len(read_manifest(manifest)) == 3
