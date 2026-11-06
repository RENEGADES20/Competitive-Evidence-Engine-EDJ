"""Ask page filters (#63): firms, date range and keywords narrow retrieval in SQL."""
from __future__ import annotations

from datetime import date

from cee.retrieve import fts
from cee.retrieve.fts import Query, apply_filters, filters_sql, resolve, search
from tests.test_fts_window import TODAY, dated_db  # noqa: F401  (fixture)


def _docs(question, dated_db, monkeypatch, **filters):
    monkeypatch.setattr(fts, "connect", dated_db)
    q = apply_filters(resolve(question, today=TODAY), **filters)
    return sorted(h.doc_id for h in search(q, k=20))


def test_no_filters_no_sql():
    assert filters_sql(apply_filters(Query("q"))) == ("TRUE", {})


def test_filters_are_where_clauses_not_prompt_text():
    q = apply_filters(Query("advisor program"), date_range=(date(2026, 1, 1), TODAY), keywords=["new advisor"])
    sql, params = filters_sql(q)
    assert "published_at BETWEEN %(r_from)s AND %(r_to)s" in sql and "phraseto_tsquery" in sql
    assert params == {"r_from": date(2026, 1, 1), "r_to": TODAY, "kw0": "new advisor"}
    assert "new advisor" not in q.question  # nothing added to the question the model reads


def test_firm_filter_picks_firms_when_none_named():
    q = apply_filters(resolve("advisor program", today=TODAY), firms=["RJF"])
    assert (q.entities, q.mode) == (["RJF"], "entity")


def test_firm_filter_intersects_named_firms():
    q = apply_filters(resolve("What's new on Raymond James and Merrill?", today=TODAY), firms=["MER"])
    assert q.entities == ["MER"]


def test_company_filter_returns_no_other_entity(dated_db, monkeypatch):
    assert _docs("advisor program", dated_db, monkeypatch, firms=["RJF"]) == [
        "RJF-EDGE-90D", "RJF-IN-89D", "RJF-OLD-91D", "RJF-RETRIEVED", "RJF-TODAY"]


def test_merrill_filter_keeps_only_gwim_bac(dated_db, monkeypatch):
    assert _docs("advisor program", dated_db, monkeypatch, firms=["MER"]) == [
        "BAC-GWIM", "MER-DEC31", "MER-JAN1", "MER-RETRIEVED"]


def test_firm_filter_excluding_named_firm_returns_nothing(dated_db, monkeypatch):
    assert _docs("What's new on Raymond James?", dated_db, monkeypatch, firms=["MER"]) == []


def test_date_range_returns_nothing_outside(dated_db, monkeypatch):
    # both ends inclusive; a document dated only by its download is left out
    got = _docs("advisor program", dated_db, monkeypatch, date_range=(date(2026, 1, 1), date(2026, 7, 22)))
    assert got == ["BAC-CONSUMER", "BAC-GWIM", "MER-JAN1", "RJF-OLD-91D"]


def test_keywords_must_all_match(dated_db, monkeypatch):
    assert _docs("advisor program", dated_db, monkeypatch, keywords=["rjf-todayw3"]) == ["RJF-TODAY"]
    assert _docs("advisor program", dated_db, monkeypatch, keywords=["rjf-todayw3", "mer-jan1w0"]) == []
