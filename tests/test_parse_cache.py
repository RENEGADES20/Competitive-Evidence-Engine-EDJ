"""Parse cache (#82): docling and edgartools run once per file content and parser version.
Both are replaced by fakes that count calls (CI installs neither). No network, no DB."""
from __future__ import annotations

import json
import sys
import types
from importlib.metadata import PackageNotFoundError

import pytest

from cee.ingest import load, parse_cache, pdf

ITEMS = [("Document", 1, "Cover text"), ("Wealth Management", 2, "| a | b |\n| --- | --- |\n| 1 | 2 |"),
         ("Wealth Management", 3, "café — 😀 \"quoted\"\n\nline")]


@pytest.fixture(autouse=True)
def library_versions(monkeypatch):
    versions = {"docling": "2.0", "edgartools": "5.0"}
    monkeypatch.setattr(parse_cache, "version", lambda lib: versions[lib])
    return versions


def name(path, lib="docling", parser_version=None):
    v = pdf.PARSER_VERSION if parser_version is None else parser_version
    return f"{parse_cache.sha256(path)}-{parse_cache.tag(lib, v)}.json"


@pytest.fixture
def fake_docling(monkeypatch):
    calls = []

    def parse(path, *args):
        calls.append(path.name)
        return [(s, p, f"{t} [{path.read_bytes().decode()}]") for s, p, t in ITEMS]

    monkeypatch.setattr(pdf, "_parse_docling", parse)
    return calls


@pytest.fixture
def files(tmp_path):
    a, b = tmp_path / "A.pdf", tmp_path / "B.pdf"
    a.write_bytes(b"file a")
    b.write_bytes(b"file b")
    return a, b, tmp_path / "parsed"


def test_second_parse_reads_the_cache_and_is_identical(fake_docling, files):
    a, _, cache = files
    first = pdf.parse_pdf(a, cache_dir=cache)
    second = pdf.parse_pdf(a, cache_dir=cache)
    assert fake_docling == ["A.pdf"]
    assert second == first
    assert all(type(x) is tuple and type(x[1]) is int for x in second)
    assert [f.name for f in cache.iterdir()] == [name(a)]
    assert name(a).endswith("-docling2.0-v2.json")


def test_version_bump_reparses(fake_docling, files, monkeypatch):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    monkeypatch.setattr(pdf, "PARSER_VERSION", pdf.PARSER_VERSION + 1)
    pdf.parse_pdf(a, cache_dir=cache)
    pdf.parse_pdf(a, cache_dir=cache)
    assert fake_docling == ["A.pdf", "A.pdf"]


def test_library_upgrade_reparses(fake_docling, files, library_versions):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    library_versions["docling"] = "2.1"
    pdf.parse_pdf(a, cache_dir=cache)
    assert fake_docling == ["A.pdf", "A.pdf"]


def test_changed_file_reparses_that_file_only(fake_docling, files):
    a, b, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    pdf.parse_pdf(b, cache_dir=cache)
    b.write_bytes(b"file b, new version")
    pdf.parse_pdf(a, cache_dir=cache)
    new_b = pdf.parse_pdf(b, cache_dir=cache)
    assert fake_docling == ["A.pdf", "B.pdf", "B.pdf"]
    assert "new version" in new_b[0][2]


def test_no_cache_parses_again_and_refreshes_the_file(fake_docling, files):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    pdf.parse_pdf(a, cache_dir=cache, use_cache=False)
    assert fake_docling == ["A.pdf", "A.pdf"]
    assert pdf.parse_pdf(a, cache_dir=cache) == pdf.parse_pdf(a, cache_dir=cache, use_cache=False)


@pytest.mark.parametrize("content", ['{"tag": "docling2.0-v1", "result": [["S", 1', "not json", "{}",
                                     '{"tag": "docling2.0-v1", "result": [["S", 1]]}',
                                     '{"tag": "docling9.9-v1", "result": [["S", 1, "renamed file"]]}'])
def test_unreadable_cache_file_is_a_miss(fake_docling, files, content):
    a, _, cache = files
    cache.mkdir()
    (cache / name(a)).write_text(content, encoding="utf-8")
    assert pdf.parse_pdf(a, cache_dir=cache)[0][0] == "Document"
    assert fake_docling == ["A.pdf"]
    assert json.loads((cache / name(a)).read_text())["result"][0][2].startswith("Cover text")


def test_pymupdf_fallback_is_not_cached(files, monkeypatch):
    a, _, cache = files

    def no_docling(path, *args):
        raise ImportError("docling not installed")

    monkeypatch.setattr(pdf, "_parse_docling", no_docling)
    monkeypatch.setattr(pdf, "_parse_pymupdf", lambda path: [("Page 1", 1, "plain")])
    assert pdf.parse_pdf(a, cache_dir=cache) == [("Page 1", 1, "plain")]
    assert not cache.exists()


def test_pdf_without_docling_installed_falls_back(files, monkeypatch):
    a, _, cache = files

    def not_installed(lib):
        raise PackageNotFoundError(lib)

    monkeypatch.setattr(parse_cache, "version", not_installed)
    monkeypatch.setattr(pdf, "_parse_pymupdf", lambda path: [("Page 1", 1, "plain")])
    assert pdf.parse_pdf(a, cache_dir=cache) == [("Page 1", 1, "plain")]


@pytest.fixture
def fake_edgar(monkeypatch, tmp_path):
    calls = []
    mod = types.ModuleType("edgar.documents")
    mod.parse_html = lambda html: calls.append(html) or types.SimpleNamespace(text=lambda: f"text of {html}")
    monkeypatch.setitem(sys.modules, "edgar.documents", mod)
    monkeypatch.setattr(parse_cache, "write_root", lambda: tmp_path)
    return calls


def test_html_text_is_cached_per_file_and_edgartools_version(fake_edgar, tmp_path, library_versions):
    a, b = tmp_path / "A.htm", tmp_path / "B.htm"
    a.write_text("<p>a</p>", encoding="utf-8")
    b.write_text("<p>b</p>", encoding="utf-8")
    first = load.html_text(a)
    assert load.html_text(a) == first == "text of <p>a</p>"
    load.html_text(b)
    assert fake_edgar == ["<p>a</p>", "<p>b</p>"]
    assert (tmp_path / "parsed" / name(a, "edgartools", load.HTML_PARSER_VERSION)).is_file()
    a.write_text("<p>a, amended</p>", encoding="utf-8")
    assert load.html_text(a) == "text of <p>a, amended</p>"
    load.html_text(b, use_cache=False)
    library_versions["edgartools"] = "5.1"
    load.html_text(b)
    assert fake_edgar == ["<p>a</p>", "<p>b</p>", "<p>a, amended</p>", "<p>b</p>", "<p>b</p>"]


def test_10k_sections_are_split_after_the_cache(fake_edgar, tmp_path):
    # The splitter (chunk.py) is not cached: a splitter fix applies without a version bump.
    f = tmp_path / "X.htm"
    f.write_text("x", encoding="utf-8")
    row = {"doc_id": "X-10K-2025", "doc_type": "10-K"}
    load.parse_file(row, f)
    assert load.parse_file(row, f) == load.parse_file(row, f, use_cache=False)
    assert fake_edgar == ["x", "x"]


# ---- docling output cache (#84): a PARSER_VERSION bump re-runs our code, not docling ----

class FakeDoc:
    """Stands in for a DoclingDocument: one text item per page, round-trips through a dict."""

    def __init__(self, texts):
        self.texts = texts

    def export_to_dict(self):
        return {"texts": self.texts}

    def iterate_items(self, traverse_pictures=False):
        for i, t in enumerate(self.texts, start=1):
            prov = [types.SimpleNamespace(page_no=i, charspan=(0, len(t)))]
            yield types.SimpleNamespace(text=t, prov=prov, label="text"), 0


@pytest.fixture
def fake_converter(monkeypatch):
    calls = []

    def convert(path):
        calls.append(path.name)
        return FakeDoc([f"page one of {path.name}", "page two"])

    monkeypatch.setattr(pdf, "_convert", convert)
    monkeypatch.setattr(pdf, "_load_doc", lambda d: FakeDoc(d["texts"]))
    monkeypatch.setattr(pdf, "_is_table", lambda item: False)
    return calls


def doc_name(path):
    return f"{parse_cache.sha256(path)}-docling2.0-doc.json"


def test_version_bump_reuses_the_docling_output(fake_converter, files, monkeypatch):
    a, _, cache = files
    first = pdf.parse_pdf(a, cache_dir=cache)
    assert first == [("Document", 1, "page one of A.pdf"), ("Document", 2, "page two")]
    assert sorted(f.name for f in cache.iterdir()) == sorted([name(a), doc_name(a)])
    monkeypatch.setattr(pdf, "PARSER_VERSION", pdf.PARSER_VERSION + 1)
    assert pdf.parse_pdf(a, cache_dir=cache) == first
    assert fake_converter == ["A.pdf"]                 # docling ran once
    assert (cache / name(a)).exists()                  # the new version's item file was written


def test_no_cache_converts_again_and_refreshes_both_files(fake_converter, files):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    (cache / doc_name(a)).write_text('{"tag": "docling2.0-doc", "result": {"texts": ["stale"]}}', encoding="utf-8")
    pdf.parse_pdf(a, cache_dir=cache, use_cache=False)
    assert fake_converter == ["A.pdf", "A.pdf"]
    assert json.loads((cache / doc_name(a)).read_text())["result"]["texts"][0] == "page one of A.pdf"


def test_docling_upgrade_converts_again(fake_converter, files, library_versions):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    library_versions["docling"] = "2.1"
    pdf.parse_pdf(a, cache_dir=cache)
    assert fake_converter == ["A.pdf", "A.pdf"]
