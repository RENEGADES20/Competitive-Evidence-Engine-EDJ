"""scripts/collect_trade_press.py (C3, #57): offline checks on small HTML fixtures. No network."""
import json
import sys

import pytest

from cee.config import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import collect_trade_press as ctp  # noqa: E402


def page(date_published=None, meta_time=None, headline="Headline", body="word " * 100):
    ld = f'<script type="application/ld+json">{json.dumps({"@type": "NewsArticle", "datePublished": date_published})}</script>' \
        if date_published else ""
    meta = f'<meta property="article:published_time" content="{meta_time}">' if meta_time else ""
    return (f"<html><head>{ld}{meta}</head><body><h1>{headline}</h1>"
            f'<div class="article-content"><p>{body}</p><aside><p>Related: Schwab Schwab Schwab</p></aside></div>'
            "</body></html>")


def test_date_comes_from_the_page_in_eastern_time():
    pytest.importorskip("bs4")  # page parsing needs bs4 (requirements-ingest.txt); CI installs requirements.txt only
    # 2026-09-26 01:30 UTC is still 2026-09-25 in New York.
    assert ctp.page_date(page(date_published="2026-09-26T01:30:00Z")) == "2026-09-25"
    assert ctp.page_date(page(meta_time="2026-10-01T14:56:29+00:00")) == "2026-10-01"
    with pytest.raises(ValueError):
        ctp.page_date(page())  # no page date: never fall back to the download date


def test_bare_tickers_are_not_counted():
    p = ctp.alias_patterns()
    assert "MS" not in ctp.mentions("Ms. Lee said MS shares rose.", p)
    assert ctp.mentions("Morgan Stanley and E*TRADE; Morgan Stanley again.", p) == {"MS": 3}


def test_entity_is_the_first_firm_in_the_headline():
    p = ctp.alias_patterns()
    assert ctp.choose_entity("Team leaves Morgan Stanley for Raymond James", "", p) == "MS"
    assert ctp.choose_entity("Raymond James lands team from Morgan Stanley", "", p) == "RJF"


def test_merrill_is_mer_and_bank_of_america_alone_is_dropped():
    p = ctp.alias_patterns()
    assert ctp.choose_entity("Merrill Lynch to pay settlement", "", p) == "MER"
    body = "Bank of America said ... Bank of America ... Bank of America ... BofA"
    assert ctp.choose_entity("Treasury fines BofA", body, p) is None


def test_body_needs_three_mentions_when_the_headline_names_no_firm():
    p = ctp.alias_patterns()
    assert ctp.choose_entity("Wirehouses lose advisors", "Edward Jones once. Schwab twice, Schwab.", p) is None
    assert ctp.choose_entity("Wirehouses lose advisors", "Schwab, Schwab and Charles Schwab.", p) == "SCHW"


def test_article_body_skips_asides_and_needs_real_text():
    pytest.importorskip("bs4")  # page parsing needs bs4 (requirements-ingest.txt); CI installs requirements.txt only
    headline, body = ctp.article(page(headline="Schwab news", body="word " * 100), ctp.INVESTMENTNEWS)
    assert headline == "Schwab news" and "Related" not in body
    with pytest.raises(ValueError):
        ctp.article(page(body="short paywall teaser"), ctp.INVESTMENTNEWS)


def test_listing_keeps_url_date_and_title():
    pytest.importorskip("bs4")  # page parsing needs bs4 (requirements-ingest.txt); CI installs requirements.txt only
    html = ('<div class="tool-sublist__item"><a class="tool-sublist__item__img" href="/x/a/1"></a>'
            '<span class="tool-sublist__item__date">NOV 12, 2026</span>'
            '<a class="tool-sublist__item__title" href="/x/a/1">Edward Jones news</a></div>')
    assert ctp.in_listing(html, "https://www.investmentnews.com/companies/edward-jones/262941") == [
        ("https://www.investmentnews.com/x/a/1", "2026-11-12", "Edward Jones news")]


def test_rerun_adds_no_duplicates(monkeypatch):
    stored = [{"doc_id": "EDJ-TRADE-2026-11-12-IN-01", "url": "https://www.investmentnews.com/x/a/1/"}]
    monkeypatch.setattr(ctp, "read_manifest", lambda: stored)
    assert ctp.canonical("https://WWW.investmentnews.com/x/a/1?utm=x#top") in ctp.stored_urls()
    assert ctp.next_doc_id("EDJ", "2026-11-12", "IN", {stored[0]["doc_id"]}) == "EDJ-TRADE-2026-11-12-IN-02"


def test_riabiz_dates_follow_its_utc_byline():
    pytest.importorskip("bs4")  # page parsing needs bs4 (requirements-ingest.txt); CI installs requirements.txt only
    # RIABiz prints "October 7, 2026" for an article stamped 2026-10-07T01:01Z (Oct 6 in New York).
    assert ctp.page_date(page(date_published="2026-10-07T01:01:55Z"), ctp.RIABIZ.date_tz) == "2026-10-07"
    assert ctp.page_date(page(date_published="2026-10-07T01:01:55Z")) == "2026-10-06"
