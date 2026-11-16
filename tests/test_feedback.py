"""Feedback (#62): one row per query; a second send replaces the first. Throwaway schema in the
local Postgres (skipped if it is down)."""
import psycopg
import pytest
from psycopg.rows import dict_row

from cee import feedback
from cee.config import settings
from cee.feedback import HELPFUL, NOT_HELPFUL, save_feedback

SCHEMA = "test_feedback"


@pytest.fixture()
def db(monkeypatch):
    url = settings().database_url
    try:
        conn = psycopg.connect(url, connect_timeout=2, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("local Postgres not reachable")
    with conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.execute(f"CREATE SCHEMA {SCHEMA}")
        conn.execute(f"CREATE TABLE {SCHEMA}.query_log (query_id serial PRIMARY KEY, question text)")
        conn.execute(f"""CREATE TABLE {SCHEMA}.query_feedback (query_id int REFERENCES {SCHEMA}.query_log,
                         rating int, comment text, created_at timestamptz DEFAULT now())""")
        conn.execute(f"INSERT INTO {SCHEMA}.query_log (question) VALUES ('a'), ('b')")
        connect = lambda: psycopg.connect(url, row_factory=dict_row, options=f"-c search_path={SCHEMA}")
        monkeypatch.setattr(feedback, "connect", connect)
        yield lambda: connect().execute(
            "SELECT query_id, rating, comment FROM query_feedback ORDER BY query_id").fetchall()
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def test_first_send_writes_one_row(db):
    assert save_feedback(1, HELPFUL, "  clear  ") == "saved"
    assert db() == [{"query_id": 1, "rating": 1, "comment": "clear"}]


def test_second_send_replaces_not_duplicates(db):
    save_feedback(1, HELPFUL, "clear")
    assert save_feedback(1, NOT_HELPFUL, "") == "updated"
    assert db() == [{"query_id": 1, "rating": -1, "comment": None}]


def test_other_queries_are_untouched(db):
    save_feedback(1, HELPFUL)
    save_feedback(2, NOT_HELPFUL, "wrong firm")
    save_feedback(1, NOT_HELPFUL)
    assert [(r["query_id"], r["rating"]) for r in db()] == [(1, -1), (2, -1)]


def test_bad_rating_is_refused():
    with pytest.raises(ValueError):
        save_feedback(1, 5)
