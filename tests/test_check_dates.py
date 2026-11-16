"""scripts/check_dates.py: detectors, cross-check, fail rules, NOTES, exit codes. No network, no DB, no PDFs."""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_dates.py"
spec = importlib.util.spec_from_file_location("check_dates", SCRIPT)
cd = importlib.util.module_from_spec(spec)
sys.modules["check_dates"] = cd
spec.loader.exec_module(cd)

D = dt.date.fromisoformat
TODAY = D("2026-11-03")
UNDATED = """Advisor Development Program
Merrill advisor recruiting page - content as of 2026-10-30
Source: https://www.ml.com/adp.html (fetched 2026-10-30)
Content as of: 2026-10-30 (date basis: retrieved; the page prints no date)
Date check (ADR-007 T-09): printed date none; page metadata none; HTTP Last-Modified none; earliest Wayback capture 2019-04-02 (dates the URL, not this text).

Become a financial advisor with Merrill. Our program trains new advisors.
"""


def row(doc_id="X-TR-2026Q1", doc_type="transcript", published="2026-04-15", period_end="2026-03-31",
        basis="source", added="2026-10-16", path=None, url="", entity="X"):
    ext = {"deck": "pdf", "transcript": "txt"}.get(doc_type, "htm")
    return {"doc_id": doc_id, "entity_id": entity, "doc_type": doc_type, "published_at": published,
            "date_basis": basis, "period_end": period_end, "url": url, "added_at": added,
            "storage_path": path or f"raw/{doc_id}.{ext}"}


def verdict(r, texts, meta=None, today=TODAY):
    res, problems = cd.detect(r, texts, meta)
    return cd.judge(r, res, problems, today), res


# ---- detectors ----

def test_deck_page1_and_case_insensitive():
    r = cd.detect_deck(["Bank of America\n1Q26 Financial Results\nApril\xa015, 2026\n"], None, D("2026-04-15"))
    assert (r["date"], r["source"], r["evidence"]) == (D("2026-04-15"), "page", "p1 'April 15, 2026'")
    assert cd.detect_deck(["JUNE 5, 2025\n2025 Analyst & Investor Day"], None, D("2025-06-05"))["date"] == D("2025-06-05")


def test_deck_investor_day_prefers_as_of_in_first_10_pages():
    pages = ["2026\nInstitutional\nInvestor Day", "agenda", "Data as of March 31, 2026", "x", "x",
             "This presentation speaks only as of May 14, 2026."]
    r = cd.detect_deck(pages, None, D("2026-05-14"))
    assert (r["date"], r["evidence"]) == (D("2026-05-14"), "p6 'speaks only as of May 14, 2026'")
    pages = ["Investor Day", *["x"] * 9, "speaks only as of May 14, 2026"]  # page 11: out of range
    assert cd.detect_deck(pages, None, D("2026-05-14"))["date"] is None


def test_deck_metadata_fallback():
    r = cd.detect_deck(["no date here"], D("2026-04-14"), D("2026-04-15"))
    assert (r["date"], r["source"]) == (D("2026-04-15"), "metadata")
    assert cd.detect_deck(["no date here"], D("2026-04-10"), D("2026-04-15"))["date"] is None
    assert cd.pdf_date("D:20260415085109") == D("2026-04-15") and cd.pdf_date(None) is None


def test_press_datelines():
    ms = "Morgan Stanley Reports Net Revenues of $20.6 Billion NEW YORK, April 15, 2026 – Morgan Stanley today"
    r = cd.detect_press_html(ms)
    assert (r["date"], r["evidence"]) == (D("2026-04-15"), "dateline 'NEW YORK, April 15, 2026 –'")
    schw = "SCHWAB REPORTS RECORD RESULTS WESTLAKE, Texas, April 16, 2026 – The Charles Schwab"
    assert cd.detect_press_html(schw)["date"] == D("2026-04-16")
    rjf = "Document October 22, 2025 FOR IMMEDIATE RELEASE Media Contact: ... as of September 30, 2025"
    r = cd.detect_press_html(rjf)
    assert (r["date"], r["source"]) == (D("2025-10-22"), "page")
    assert cd.detect_press_html("bac09302026ex991 3Q26 Financial Highlights")["date"] is None


def test_transcript_header_url_footer_weak():
    text = "Bank of America - Q4 2025 earnings call - 2026-01-14\nTranscript source: MarketBeat.\n"
    r = cd.detect_transcript(text, "https://www.marketbeat.com/earnings/reports/2026-1-14-bank-of-america-co-stock/")
    assert (r["source"], r["weak"]) == ("header + URL", False)
    sp = "Bank of America - Q1 2026 earnings call - 2026-04-15\n...\nBank of America Corporation, Q1 2026 Earnings Call, Apr 15, 2026\n"
    assert cd.detect_transcript(sp, "S&P transcript")["source"] == "header + page"
    r = cd.detect_transcript("Morgan Stanley - Q2 2026 earnings call - 2026-07-15\n", "S&P transcript")
    assert (r["date"], r["source"], r["weak"]) == (D("2026-07-15"), "header", True)
    assert verdict(row(published="2026-07-15", period_end="2026-06-30"), ["Morgan Stanley - Q2 - 2026-07-15\n"])[0] == "OK (weak)"


def test_transcript_url_disagrees_is_mismatch():
    r = row(published="2026-01-14", period_end="2025-12-31",
            url="https://www.marketbeat.com/earnings/reports/2026-1-15-x-stock/")
    v, _ = verdict(r, ["X - Q4 2025 earnings call - 2026-01-14\n"])
    assert v.startswith("MISMATCH") and "2026-01-15" in v


def test_newsroom_line2_month_only():
    text = "Merrill Launches New Services\nMerrill press release - 2026-09-15\nSource: Newsroom.\n"
    url = "https://newsroom.bankofamerica.com/content/newsroom/press-releases/2026/09/merrill.html"
    r = cd.detect_newsroom(text, url)
    assert (r["date"], r["source"], r["weak"]) == (D("2026-09-15"), "header", True)
    assert "agrees (month only)" in r["evidence"]
    mer = row("MER-PR-2026-09-15-01", "press", "2026-09-15", "", path="raw/MER-PR-2026-09-15-01.txt", url=url)
    assert verdict(mer, [text])[0] == "OK (weak)"
    assert verdict(mer | {"url": url.replace("/09/", "/08/")}, [text])[0].startswith("MISMATCH")


# ---- undated pages ----

def test_undated_header_good():
    r = row("MER-PR-web-adp", "press", "2026-10-30", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    v, res = verdict(r, [UNDATED])
    assert (v, res["source"]) == ("OK", "retrieved")
    assert res["evidence"] == ("Content as of 2026-10-30; T-09: printed none, metadata none, "
                               "Last-Modified none, Wayback first 2019-04-02")


def test_undated_header_date_differs_from_published():
    r = row("MER-PR-web-adp", "press", "2026-10-29", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    v, _ = verdict(r, [UNDATED])
    assert v.startswith("BASIS") and "header date 2026-10-30 != published_at" in v


def test_undated_header_missing_t09_line():
    text = "\n".join(l for l in UNDATED.splitlines() if not l.startswith("Date check"))
    r = row("MER-PR-web-adp", "press", "2026-10-30", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    v, _ = verdict(r, [text])
    assert v.startswith("BASIS") and "no T-09 line" in v


def test_undated_basis_rules():
    r = row("MER-PR-web-adp", "press", "2026-10-30", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    assert "printed date found" in verdict(r, [UNDATED + "Last updated: October 1, 2026\n"])[0]
    assert verdict(r, ["A normal page with no header\n"])[0].startswith("BASIS")  # retrieved, no header
    v, _ = verdict(r | {"date_basis": "source"}, [UNDATED])  # source-dated row, undated header
    assert v.startswith("BASIS") and "undated-page header" in v


def test_undated_award_citation_is_not_a_page_date():
    # MER becoming page: Barron's list date in parentheses, not a date for the page itself.
    r = row("MER-PR-web-adp", "press", "2026-10-30", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    award = 'Named to the "Top 100 Women Advisors" list (Published on July 18, 2025. Rankings as of March 31, 2025.)\n'
    assert verdict(r, [UNDATED + award])[0] == "OK"


def test_undated_header_contract_gaps():
    r = row("MER-PR-web-adp", "press", "2026-10-30", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    no_line2 = "\n".join(l for l in UNDATED.splitlines() if "recruiting page - content as of" not in l)
    assert "no '... content as of <date>' line 2" in verdict(r, [no_line2])[0]
    meta = UNDATED.replace("page metadata none", "page metadata 2025-06-01")
    assert "T-09 metadata 2025-06-01 comes before the retrieved date" in verdict(r, [meta])[0]
    no_wb = UNDATED.replace("earliest Wayback capture 2019-04-02", "earliest Wayback capture none")
    assert "names no earliest Wayback capture" in verdict(r, [no_wb])[0]


def test_note_on_printed_date_leaves_header_rules_on(monkeypatch):
    r = row("MER-PR-web-adp", "press", "2026-10-29", "", basis="retrieved", added="2026-11-03",
            path="raw/MER-PR-web-adp.txt")
    text = UNDATED + "Last updated: October 1, 2026\n"
    monkeypatch.setattr(cd, "NOTES", {(r["doc_id"], "PRINTED"): "footer date of a quoted report"})
    v, _ = verdict(r, [text])  # header date 2026-10-30 != published_at 2026-10-29 still fails
    assert v.startswith("BASIS (header date 2026-10-30 != published_at)") and "printed" not in v


def test_real_converter_header_parses():
    pytest.importorskip("bs4")  # the converter needs bs4 (requirements-ingest.txt); CI installs requirements.txt only
    spec2 = importlib.util.spec_from_file_location(
        "convert_undated_web", SCRIPT.parent / "convert_undated_web.py")
    cw = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(cw)
    for doc_id, entity, url, copy, as_of, earliest, title, _ in cw.PAGES:
        text = cw.header(doc_id, entity, url, copy, as_of, earliest, title) + "Some page text.\n"
        r = row(doc_id, "press", as_of, "", basis="retrieved", added="2026-11-03", path=f"raw/{doc_id}.txt")
        assert verdict(r, [text])[0] == "OK", doc_id


# ---- fail rules ----

@pytest.mark.parametrize("published,period_end,added,label", [
    ("2026-04-16", "2026-03-31", "2026-10-16", "MISMATCH"),
    ("2014-12-31", "", "2026-10-16", "IMPLAUSIBLE (before 2015)"),
    ("2026-04-15", "2026-03-31", "2026-04-01", "IMPLAUSIBLE (after added_at"),
    ("2026-04-15", "2026-04-30", "2026-10-16", "IMPLAUSIBLE (before period_end"),
])
def test_fail_rules(published, period_end, added, label):
    text = f"X - Q1 call - {published}\n" if label != "MISMATCH" else "X - Q1 call - 2026-04-15\n"
    v, _ = verdict(row(published=published, period_end=period_end, added=added), [text])
    assert label in v and cd.is_fail(v)


def test_after_today_undated_and_late_warn():
    v, _ = verdict(row(published="2026-12-01", period_end="2026-09-30", added="2026-12-02"), ["X - 2026-12-01\n"])
    assert "IMPLAUSIBLE (after today 2026-11-03)" in v
    v, _ = verdict(row("X-PR-1", "press"), ["no date printed anywhere"])
    assert v.startswith("UNDATED") and cd.is_fail(v)
    v, _ = verdict(row(published="2026-09-01", period_end="2026-03-31"), ["X - 2026-09-01\n"])
    assert v == "WARN (154 days after period_end)" and not cd.is_fail(v)


def test_note_downgrades_only_its_rule(monkeypatch):
    r = row(published="2014-06-01", period_end="", added="2014-01-01")  # before 2015 and after added_at
    text = ["X - 2014-06-01\n"]
    monkeypatch.setattr(cd, "NOTES", {(r["doc_id"], "BEFORE_2015"): "old filing on purpose"})
    v, _ = verdict(r, text)
    assert v.startswith("IMPLAUSIBLE (after added_at") and "before 2015" not in v and cd.is_fail(v)
    monkeypatch.setattr(cd, "NOTES", {(r["doc_id"], "BEFORE_2015"): "old filing on purpose",
                                      (r["doc_id"], "AFTER_ADDED"): "added_at typo"})
    assert verdict(r, text)[0] == "OK (note: old filing on purpose; added_at typo)"


# ---- BAC cross-check ----

def bac_rows():
    return [row("BAC-PR-2026-10-14-01", "press", "2026-10-14", "2026-09-30", entity="BAC"),
            row("BAC-DECK-2026Q3", "deck", "2026-10-14", "2026-09-30", entity="BAC"),
            row("BAC-TR-2026Q3", "transcript", "2026-10-14", "2026-09-30", entity="BAC")]


def bac_loader(r):
    return {"BAC-PR-2026-10-14-01": (["bac09302026ex991 3Q26 Financial Highlights"], None),
            "BAC-DECK-2026Q3": (["Bank of America\n3Q26 Financial Results\nOctober 14, 2026\n"], None),
            "BAC-TR-2026Q3": (["Bank of America - Q3 2026 earnings call - 2026-10-14\n"], None)}[r["doc_id"]]


def test_bac_cross_check_with_sibling():
    out = {l["doc_id"]: l for l in cd.check_rows(bac_rows(), bac_loader, TODAY)}
    pr = out["BAC-PR-2026-10-14-01"]
    assert (pr["source"], pr["verdict"]) == ("cross-check", "OK (cross-check)")
    assert pr["evidence"] == "none printed; BAC-DECK-2026Q3 p1 2026-10-14"


def test_bac_cross_check_without_sibling():
    rows = bac_rows()[:1]
    out = cd.check_rows(rows, bac_loader, TODAY)
    assert out[0]["verdict"].startswith("UNDATED")
    rows = [bac_rows()[0], bac_rows()[2]]  # only a weak transcript sibling: still dated, but weak
    assert cd.check_rows(rows, bac_loader, TODAY)[0]["verdict"] == "OK (weak)"


# ---- main() ----

def write_manifest(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_main_exit_codes(tmp_path, capsys):
    m = tmp_path / "manifest.csv"
    rows = bac_rows() + [row("EDJ-10K-2025", "10-K", "2026-03-13", "2025-12-31", entity="EDJ")]
    write_manifest(m, rows)
    out = tmp_path / "report.md"
    assert cd.main(["--manifest", str(m), "--today", "2026-11-03", "--out", str(out)], load=bac_loader) == 0
    text = out.read_text()
    assert "do not edit by hand" in text and "rows: 3" in text and "EDJ-10K" not in text
    assert "- OK (cross-check): 1" in text and "- header + cross-check: 1" in text  # transcript backed by the deck
    assert cd.main(["--manifest", str(m), "--today", "2026-11-03", "--out", str(out)], load=bac_loader) == 0
    assert out.read_text() == text  # stable rerun

    write_manifest(m, [rows[1] | {"published_at": "2026-10-15"}])
    assert cd.main(["--manifest", str(m), "--today", "2026-11-03"], load=bac_loader) == 1

    def missing(r):
        raise FileNotFoundError(r["storage_path"])
    write_manifest(m, rows)
    assert cd.main(["--manifest", str(m), "--today", "2026-11-03"], load=missing) == 2
    assert cd.main(["--manifest", str(m), "--today", "2026-11-03", "--skip-missing"], load=missing) == 0
    assert "NO FILE" in capsys.readouterr().out


def test_bac_cross_check_sibling_disagrees_is_mismatch():
    rows = bac_rows()
    rows[0]["published_at"] = "2026-10-15"
    pr = {l["doc_id"]: l for l in cd.check_rows(rows, bac_loader, TODAY)}["BAC-PR-2026-10-14-01"]
    assert pr["verdict"].startswith("MISMATCH") and "BAC-DECK-2026Q3" in pr["evidence"]


def test_weak_transcript_corroborated_by_same_quarter_deck():
    rows = bac_rows()[1:]  # deck + S&P/Bloomberg transcript with only our line-1 date
    tr = {l["doc_id"]: l for l in cd.check_rows(rows, bac_loader, TODAY)}["BAC-TR-2026Q3"]
    assert (tr["source"], tr["verdict"]) == ("header + cross-check", "OK")
    assert tr["evidence"] == "line 1 2026-10-14; BAC-DECK-2026Q3 p1 2026-10-14"
    alone = cd.check_rows(rows[1:], bac_loader, TODAY)[0]
    assert alone["verdict"] == "OK (weak)"
