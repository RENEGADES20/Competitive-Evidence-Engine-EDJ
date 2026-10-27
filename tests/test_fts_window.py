"""Time windows in SQL (#49): phrase parsing without a database, and dated fixture rows
around each window edge in a throwaway schema of the local Postgres (skipped if it is down)."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts
from cee.retrieve.fts import _search_terms, resolve, search, window_filter

TODAY = date(2026, 10, 21)
Q26 = "What's new on Raymond James in the last 90 days?"
Q27 = "What has changed at Merrill since the start of the year?"


@pytest.mark.parametrize("question, window", [
    (Q26, (date(2026, 7, 23), TODAY)),
    ("Anything from Schwab over the past 30 days?", (date(2026, 9, 21), TODAY)),
    ("Morgan Stanley news in the last 2 weeks", (date(2026, 10, 7), TODAY)),
    ("Edward Jones in the past 3 months", (date(2026, 7, 21), TODAY)),
    ("Raymond James over the last 1 month", (date(2026, 9, 21), TODAY)),
    (Q27, (date(2026, 1, 1), TODAY)),
    ("What has Schwab said since the beginning of the year?", (date(2026, 1, 1), TODAY)),
    ("Morgan Stanley net new assets year to date", (date(2026, 1, 1), TODAY)),
    ("Morgan Stanley NNA YTD", (date(2026, 1, 1), TODAY)),
])
def test_time_phrase_sets_the_window(question, window):
    assert resolve(question, today=TODAY).window == window


def test_month_window_keeps_a_valid_day():
    assert resolve("Schwab in the last 1 month", today=date(2026, 3, 31)).window == (date(2026, 2, 28), date(2026, 3, 31))


@pytest.mark.parametrize("question", [
    "What is Morgan Stanley's strategy to increase their net new assets?",   # Q1
    "How does Raymond James's affiliation-choice model work commercially?",  # Q14
    "Five things Raymond James said about recruiting this year",
])
def test_no_time_phrase_no_window(question):
    assert resolve(question, today=TODAY).window is None


def test_time_phrase_is_not_a_search_term():
    assert _search_terms(resolve(Q26, today=TODAY)).split() == ["What", "new", "on", "in", "the", "?"]
    assert "year" not in _search_terms(resolve(Q27, today=TODAY))


def test_no_window_no_filter():
    assert window_filter(None) == ("TRUE", {})


def test_window_filter_leaves_out_retrieved_dates():
    sql, params = window_filter((date(2026, 1, 1), TODAY))
    assert "d.date_basis = 'source'" in sql
    assert params == {"w_from": date(2026, 1, 1), "w_to": TODAY}


# --- dated fixture rows ----------------------------------------------------------------

SCHEMA = "test_fts_window"
DOCS = [  # doc_id, entity_id, published_at, date_basis, segment
    ("RJF-OLD-91D", "RJF", date(2026, 7, 22), "source", None),       # 91 days before TODAY
    ("RJF-EDGE-90D", "RJF", date(2026, 7, 23), "source", None),      # exactly 90 days
    ("RJF-IN-89D", "RJF", date(2026, 7, 24), "source", None),
    ("RJF-TODAY", "RJF", TODAY, "source", None),
    ("RJF-RETRIEVED", "RJF", date(2026, 10, 1), "retrieved", None),  # inside, but only a download date
    ("MER-DEC31", "MER", date(2025, 12, 31), "source", None),
    ("MER-JAN1", "MER", date(2026, 1, 1), "source", None),
    ("MER-RETRIEVED", "MER", date(2026, 6, 1), "retrieved", None),
    ("BAC-GWIM", "BAC", date(2026, 3, 2), "source", "GWIM"),
    ("BAC-CONSUMER", "BAC", date(2026, 3, 2), "source", "Consumer Banking"),
]


@pytest.fixture(scope="module")
def dated_db():
    url = settings().database_url
    try:
        conn = psycopg.connect(url, connect_timeout=2, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not reachable")
    with conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.execute(f"CREATE SCHEMA {SCHEMA}")
        conn.execute(f"""CREATE TABLE {SCHEMA}.documents (
            doc_id text PRIMARY KEY, entity_id text, doc_type text NOT NULL, source_tier int NOT NULL,
            published_at date NOT NULL, date_basis text NOT NULL, period_end date)""")
        conn.execute(f"""CREATE TABLE {SCHEMA}.chunks (
            chunk_id text PRIMARY KEY, doc_id text NOT NULL, seq int NOT NULL, section text,
            segment text, page int, prefix text NOT NULL, text text NOT NULL,
            tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', prefix || ' ' || text)) STORED)""")
        for doc_id, entity, published, basis, segment in DOCS:
            conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES (%s, %s, 'press', 3, %s, %s, NULL)",
                         (doc_id, entity, published, basis))
            conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, 0, 'Document', %s, NULL, '', %s)",
                         (f"{doc_id}#0", doc_id, segment, "The firm changed its plan and has a new advisor program. "
                          # distinct words per document, so near-duplicate removal (#106) keeps every row
                          + " ".join(f"{doc_id.lower()}w{i}" for i in range(12))))
        yield lambda: psycopg.connect(url, row_factory=dict_row, options=f"-c search_path={SCHEMA}")
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def _docs(question, dated_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", dated_db)
    return sorted(h.doc_id for h in search(resolve(question, today=TODAY), k=20))


def test_q26_returns_nothing_older_than_90_days(dated_db, monkeypatch):
    assert _docs(Q26, dated_db, monkeypatch) == ["RJF-EDGE-90D", "RJF-IN-89D", "RJF-TODAY"]


def test_q27_returns_nothing_before_1_january(dated_db, monkeypatch):
    # MER-JAN1 on the edge; BAC only where the segment is GWIM; nothing dated by download
    assert _docs(Q27, dated_db, monkeypatch) == ["BAC-GWIM", "MER-JAN1"]


def test_no_time_phrase_returns_every_date(dated_db, monkeypatch):
    assert _docs("What's new on Raymond James?", dated_db, monkeypatch) == [
        "RJF-EDGE-90D", "RJF-IN-89D", "RJF-OLD-91D", "RJF-RETRIEVED", "RJF-TODAY"]
