"""Entity questions that name a theme also get tier 5 research on that theme (#116): topic
parsing without a database, and the research quota on fixture rows in a throwaway schema of the
local Postgres (skipped if it is down)."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts
from cee.retrieve.fts import resolve, search

TODAY = date(2026, 10, 27)
Q19 = "How should the preferences of younger investors shape Edward Jones's offerings?"


def test_firm_and_topic_is_entity_plus_theme():
    q = resolve(Q19, TODAY)
    assert (q.entities, q.themes, q.mode) == (["EDJ"], ["younger_investors"], "entity+theme")


def test_firm_without_topic_stays_entity():
    q = resolve("What is Morgan Stanley's net new assets strategy?", TODAY)
    assert (q.themes, q.mode) == ([], "entity")


@pytest.mark.parametrize("question", [
    "Advisor headcount over the last eight quarters across the five.",               # Q23
    "What is Edward Jones's advisor attrition rate compared to Merrill's?",          # Q28
])
def test_several_firms_and_topic_stay_entity(question):
    # research slots pushed Q23's headcount figures out; per-firm theme quotas are #117
    q = resolve(question, TODAY)
    assert (q.themes, q.mode) == (["advisor_recruiting"], "entity")


def test_topic_without_firm_stays_theme():
    q = resolve("What evidence is there about how clients under 40 choose a financial advisor?", TODAY)
    assert q.mode == "theme" and "younger_investors" in q.themes


def test_sub_topic_word_alone_names_no_theme():
    # "trillion" is a transfer_estimates keyword, but only counts next to its parent (rule 2)
    assert resolve("How many trillion in client assets does Edward Jones hold?", TODAY).themes == []


# --- research quota on fixture rows ---------------------------------------------------

SCHEMA = "test_retrieval_themes"
WORDS = "younger investors prefer digital advice and mobile offerings"
DOCS = [  # doc_id, entity_id, doc_type, tier, topic, chunks
    # 3 per document (MAX_PER_DOC), two types so the pool (POOL_PER_GROUP) can fill 16 slots
    *[(f"EDJ-{t}-{i}", "EDJ", t, 2, None, 3) for t in ("10-K", "10-Q") for i in range(4)],
    ("MS-10K", "MS", "10-K", 2, None, 3),                         # another firm: never returned
    ("SURVEY-A", None, "research", 5, "younger_investors", 4),
    ("SURVEY-B", None, "research", 5, "younger_investors", 4),
    ("FEES-STUDY", None, "research", 5, "fees_pricing", 3),       # research on another topic
]


@pytest.fixture(scope="module")
def theme_db():
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
        for doc_id, entity, doc_type, tier, topic, n in DOCS:
            conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES (%s, %s, %s, %s, %s, 'source', NULL)",
                         (doc_id, entity, doc_type, tier, date(2026, 3, 1)))
            for i in range(n):
                cid = f"{doc_id}#{i}"
                # distinct words per chunk, so near-duplicate removal keeps every row
                conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, %s, 'Document', NULL, NULL, '', %s)",
                             (cid, doc_id, i, WORDS + " " + " ".join(f"{cid.lower()}w{j}" for j in range(12))))
                if topic:
                    conn.execute(f"INSERT INTO {SCHEMA}.chunk_topics VALUES (%s, %s)", (cid, topic))
        yield lambda: psycopg.connect(url, row_factory=dict_row, options=f"-c search_path={SCHEMA}")
        conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")


def _hits(question, theme_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", theme_db)
    return search(resolve(question, TODAY), k=20)


def test_q19_gets_research_on_its_topic_and_keeps_the_entity_filter(theme_db, monkeypatch):
    hits = _hits(Q19, theme_db, monkeypatch)
    research = [h for h in hits if h.entity_id is None]
    assert {h.entity_id for h in hits} == {"EDJ", None}                  # no MS chunk
    assert len(research) == fts.THEME_K and len(hits) == 20               # firm keeps the rest
    assert {h.doc_id for h in research} == {"SURVEY-A", "SURVEY-B"}       # never FEES-STUDY
    assert all(sum(h.doc_id == d for h in research) <= fts.THEME_MAX_PER_DOC for d in ("SURVEY-A", "SURVEY-B"))


def test_firm_question_without_topic_gets_no_research(theme_db, monkeypatch):
    hits = _hits("What do Edward Jones filings say about digital advice and mobile offerings?", theme_db, monkeypatch)
    assert {h.entity_id for h in hits} == {"EDJ"}
