"""PDF parse cache (#82): docling runs once per file content and parser version.
docling is replaced by a fake that counts calls. No network, no DB."""
from __future__ import annotations

import json

import pytest

from cee.ingest import pdf

ITEMS = [("Document", 1, "Cover text"), ("Wealth Management", 2, "| a | b |\n| --- | --- |\n| 1 | 2 |"),
         ("Wealth Management", 3, "café — 😀 \"quoted\"\n\nline")]


@pytest.fixture
def fake_docling(monkeypatch):
    calls = []

    def parse(path):
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
    assert [f.name for f in cache.iterdir()] == [f"{pdf._sha256(a)}-v{pdf.PARSER_VERSION}.json"]


def test_version_bump_reparses(fake_docling, files, monkeypatch):
    a, _, cache = files
    pdf.parse_pdf(a, cache_dir=cache)
    monkeypatch.setattr(pdf, "PARSER_VERSION", pdf.PARSER_VERSION + 1)
    pdf.parse_pdf(a, cache_dir=cache)
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


@pytest.mark.parametrize("content", ["{\"parser_version\": 1, \"items\": [[\"S\", 1", "not json", "{}"])
def test_unreadable_cache_file_is_a_miss(fake_docling, files, content):
    a, _, cache = files
    cache.mkdir()
    (cache / f"{pdf._sha256(a)}-v{pdf.PARSER_VERSION}.json").write_text(content, encoding="utf-8")
    assert pdf.parse_pdf(a, cache_dir=cache)[0][0] == "Document"
    assert fake_docling == ["A.pdf"]
    assert json.loads((cache / f"{pdf._sha256(a)}-v{pdf.PARSER_VERSION}.json").read_text())["items"]


def test_pymupdf_fallback_is_not_cached(files, monkeypatch):
    a, _, cache = files

    def no_docling(path):
        raise ImportError("docling not installed")

    monkeypatch.setattr(pdf, "_parse_docling", no_docling)
    monkeypatch.setattr(pdf, "_parse_pymupdf", lambda path: [("Page 1", 1, "plain")])
    assert pdf.parse_pdf(a, cache_dir=cache) == [("Page 1", 1, "plain")]
    assert not cache.exists()
