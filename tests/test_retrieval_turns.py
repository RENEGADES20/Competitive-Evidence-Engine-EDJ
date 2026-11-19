"""Answer turn with its question turn (#203, ADR-017): an analyst's question turn on a call brings
management's next turn, which the hard filters still screen."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts
from cee.retrieve.fts import Hit, is_question_turn, resolve, search, select

TODAY = date(2026, 11, 17)
QUESTION = ("Operator\n\nYour next question comes from the line of Steven Chubak with Wolfe Research.\n\n"
            "Steven Joseph Chubak Wolfe Research, LLC\n\nSo certainly appreciate the mix shift across the "
            "different affiliation options.")
ANSWER = ("Paul Marone Shoukry CEO & Director\n\nYes. No, we're actually seeing pretty good uptick in the "
          "employee option as well.")


def _hit(cid, text, doc_type="transcript", rank=1.0, entity="RJF"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type=doc_type,
               source_tier=3, published_at="2026-04-22", period_end=None, section="Document", page=None,
               rank=rank, text=text)


def test_question_turn_is_an_operator_hand_off_or_an_analyst_asking():
    assert is_question_turn(_hit("T#45", QUESTION))
    assert is_question_turn(_hit("T#47", "Steven Joseph Chubak Wolfe Research, LLC\n\nIs that something you'd do?"))
    assert not is_question_turn(_hit("T#46", ANSWER))
    # management handing over to a colleague is not a question (BAC-TR-2026Q2 #6)
    assert not is_question_turn(_hit("T#6", "Brian Thomas Moynihan Chairman & CEO\n\nAlastair?"))
    assert not is_question_turn(_hit("D#1", QUESTION, doc_type="10-K"))   # transcripts only


def _pool():
    # one firm, two document types; the question turn ranks first, its answer is not in the pool
    return [_hit("T#45", QUESTION, rank=10), _hit("K#1", "10-K text one", "10-K", 9),
            _hit("U#3", "another call turn", rank=8), _hit("K#2", "10-K text two", "10-K", 7)]


def test_attach_keeps_the_answer_right_after_its_question(monkeypatch):
    monkeypatch.setattr(fts, "PAIR_TURNS", "attach")
    kept = select(_pool(), k=4, floor=0, answers={"T#45": _hit("T#46", ANSWER, rank=10)})
    assert [h.chunk_id for h in kept] == ["T#45", "T#46", "K#1", "U#3"]


def test_replace_keeps_the_answer_in_place_of_its_question(monkeypatch):
    monkeypatch.setattr(fts, "PAIR_TURNS", "replace")
    kept = select(_pool(), k=3, floor=0, answers={"T#45": _hit("T#46", ANSWER, rank=10)})
    assert [h.chunk_id for h in kept] == ["T#46", "K#1", "U#3"]


def test_no_rule_and_full_list_leave_the_answer_out(monkeypatch):
    answers = {"T#45": _hit("T#46", ANSWER, rank=10)}
    monkeypatch.setattr(fts, "PAIR_TURNS", None)
    assert "T#46" not in [h.chunk_id for h in select(_pool(), k=4, floor=0, answers=answers)]
    monkeypatch.setattr(fts, "PAIR_TURNS", "attach")
    assert [h.chunk_id for h in select(_pool(), k=1, floor=0, answers=answers)] == ["T#45"]   # k holds


def test_answer_counts_against_max_per_doc(monkeypatch):
    monkeypatch.setattr(fts, "PAIR_TURNS", "attach")
    pool = [_hit("T#45", QUESTION, rank=10), _hit("T#9", "same call other turn one", rank=9),
            _hit("T#8", "same call other turn two", rank=8)]
    kept = select(pool, k=10, floor=0, max_per_doc=2, answers={"T#45": _hit("T#46", ANSWER, rank=10)})
    assert [h.chunk_id for h in kept] == ["T#45", "T#46"]


# --- answer turns screened by the hard filters, on fixture rows ---------------------------

SCHEMA = "test_retrieval_turns"
ROWS = [  # chunk_id, doc_id, entity, segment, seq, text
    ("BAC-TR#4", "BAC-TR", "BAC", "GWIM", 4, "Operator\n\nNext question.\n\nAnalyst Firm, LLC\n\n"
     "How is the advisor pipeline going?"),
    ("BAC-TR#5", "BAC-TR", "BAC", "Consumer Banking", 5, "Alastair M. Borthwick Executive VP & CFO\n\n"
     "Consumer deposits grew."),                                    # Merrill question: never
    ("BAC-TR#8", "BAC-TR", "BAC", "GWIM", 8, "Operator\n\nNext question.\n\nOther Analyst Research\n\n"
     "And the advisor pipeline next year?"),
    ("BAC-TR#9", "BAC-TR", "BAC", "GWIM", 9, "Alastair M. Borthwick Executive VP & CFO\n\n"
     "Trainee classes are full."),                                  # no question words: comes with #8
]


@pytest.fixture(scope="module")
def turns_db():
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
        conn.execute(f"CREATE TABLE {SCHEMA}.chunk_topics (chunk_id text, topic_id text)")
        conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES ('BAC-TR', 'BAC', 'transcript', 3, %s, 'source', NULL)",
                     (date(2026, 7, 15),))
        for cid, doc, _, seg, seq, text in ROWS:
            conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, %s, 'Document', %s, NULL, '', %s)",
                         (cid, doc, seq, seg, text))
        yield lambda: psycopg.connect(url, row_factory=dict_row, options=f"-c search_path={SCHEMA}")
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def test_answer_turn_keeps_the_merrill_segment_filter(turns_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", turns_db)
    monkeypatch.setattr(fts, "PAIR_TURNS", "attach")
    ids = [h.chunk_id for h in search(resolve("How is Merrill building its advisor pipeline?", TODAY), k=20)]
    assert "BAC-TR#9" in ids                 # GWIM answer turn, no question word, comes with #8
    assert "BAC-TR#5" not in ids             # consumer answer turn: the segment filter holds
