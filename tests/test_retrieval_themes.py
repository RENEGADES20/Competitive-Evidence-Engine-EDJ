"""Entity questions that name a theme also get tier 5 research on that theme (#116), and with
several firms every firm's chunks on the theme are sure of a slot or the firm is a gap (#117):
topic parsing without a database, quotas on fixture rows in a throwaway schema of the local
Postgres (skipped if it is down)."""
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from cee.config import settings
from cee.retrieve import fts
from cee.retrieve.fts import Hit, Query, apply_filters, resolve, search, theme_gaps

TODAY = date(2026, 10, 27)
Q19 = "How should the preferences of younger investors shape Edward Jones's offerings?"


def test_firm_and_topic_is_entity_plus_theme():
    q = resolve(Q19, TODAY)
    assert (q.entities, q.themes, q.mode) == (["EDJ"], ["younger_investors"], "entity+theme")


def test_firm_without_topic_stays_entity():
    q = resolve("What is Morgan Stanley's net new assets strategy?", TODAY)
    assert (q.themes, q.mode) == ([], "entity")


FIVE = ["MS", "SCHW", "EDJ", "MER", "RJF"]


@pytest.mark.parametrize("question, entities, themes", [
    ("What do we know about the generational wealth transfer, and how are these five preparing for it?",
     FIVE, ["wealth_transfer"]),                                                    # Q21
    ("How does Schwab utilize its scale to cheaply acquire new clients and how could Edward Jones "
     "replicate a similar strategy?", ["SCHW", "EDJ"], ["client_acquisition"]),      # Q12, firm theme
    ("What is Edward Jones's advisor attrition rate compared to Merrill's?",
     ["EDJ", "MER"], ["advisor_recruiting"]),                                       # Q28
])
def test_several_firms_and_a_theme_are_entity_plus_theme(question, entities, themes):
    q = resolve(question, TODAY)
    assert (q.entities, q.themes, q.mode) == (entities, themes, "entity+theme")


@pytest.mark.parametrize("question", [
    "Advisor headcount over the last eight quarters across the five.",               # Q23
    "How does each of the five define and report advisor headcount -- and what does each "
    "definition include or exclude?",                                                # Q11
])
def test_metric_phrase_names_no_theme(question):
    # "advisor headcount" is an advisor_recruiting keyword, but asks for a figure: theme slots
    # pushed Q23's supplement and press release out (config metric_phrases)
    q = resolve(question, TODAY)
    assert (q.themes, q.mode) == ([], "entity")


def _hit(entity_id, on_theme, segment=None):
    return Hit(chunk_id=f"{entity_id}-X#1", doc_id=f"{entity_id}-X", entity_id=entity_id, segment=segment,
               doc_type="transcript", source_tier=2, published_at="2026-01-01", period_end=None,
               section=None, page=None, rank=1.0, text="x", on_theme=on_theme)


def test_theme_gaps_are_firms_without_a_chunk_on_the_theme():
    q = Query(question="q", entities=["MS", "SCHW", "MER"], themes=["wealth_transfer"], mode="entity+theme")
    hits = [_hit("MS", True), _hit("SCHW", False), _hit("BAC", True, "GWIM"), _hit(None, False)]
    assert theme_gaps(q, hits) == ["SCHW"]               # Merrill counts through BAC GWIM
    assert theme_gaps(Query(question="q", entities=["SCHW"], mode="entity"), hits) == []


def test_topic_without_firm_stays_theme():
    q = resolve("What evidence is there about how clients under 40 choose a financial advisor?", TODAY)
    assert q.mode == "theme" and "younger_investors" in q.themes


def test_sub_topic_word_alone_names_no_theme():
    # "trillion" is a transfer_estimates keyword, but only counts next to its parent (rule 2)
    assert resolve("How many trillion in client assets does Edward Jones hold?", TODAY).themes == []


# --- research quota on fixture rows ---------------------------------------------------

SCHEMA = "test_retrieval_themes"
WORDS = "younger investors prefer digital advice and mobile offerings"
DOCS = [  # doc_id, entity_id, doc_type, tier, topic, chunks[, words]
    # 3 per document (MAX_PER_DOC), two types so the pool (POOL_PER_GROUP) can fill 16 slots
    *[(f"EDJ-{t}-{i}", "EDJ", t, 2, None, 3) for t in ("10-K", "10-Q") for i in range(4)],
    ("MS-10K", "MS", "10-K", 2, None, 3),                         # another firm: never returned
    ("SURVEY-A", None, "research", 5, "younger_investors", 4),
    ("SURVEY-B", None, "research", 5, "younger_investors", 4),
    ("FEES-STUDY", None, "research", 5, "fees_pricing", 3),       # research on another topic
    # #117: Schwab's chunk on client acquisition ranks below its other 10-Q chunks (same document
    # type, so only the theme can lift it); Raymond James has none
    *[(f"SCHW-10Q-{i}", "SCHW", "10-Q", 2, None, 1, "acquire client data on new systems") for i in range(3)],
    ("SCHW-10Q-NEW", "SCHW", "10-Q", 2, None, 1, "we won new clients"),
    *[(f"RJF-10Q-{i}", "RJF", "10-Q", 2, None, 1, "acquire client data on new systems") for i in range(3)],
]
Q12_LIKE = "How do Schwab and Raymond James acquire new clients?"


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
        for doc_id, entity, doc_type, tier, topic, n, *words in DOCS:
            conn.execute(f"INSERT INTO {SCHEMA}.documents VALUES (%s, %s, %s, %s, %s, 'source', NULL)",
                         (doc_id, entity, doc_type, tier, date(2026, 3, 1)))
            for i in range(n):
                cid = f"{doc_id}#{i}"
                # distinct words per chunk, so near-duplicate removal keeps every row
                conn.execute(f"INSERT INTO {SCHEMA}.chunks VALUES (%s, %s, %s, 'Document', NULL, NULL, '', %s)",
                             (cid, doc_id, i, (words or [WORDS])[0] + " "
                              + " ".join(f"{cid.lower()}w{j}" for j in range(12))))
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


def test_ask_page_filters_also_narrow_the_research_part(theme_db, monkeypatch):
    # #63 + #116: the research query gets the same date/keyword WHERE clauses
    monkeypatch.setattr(fts, "connect", theme_db)
    inside = search(apply_filters(resolve(Q19, TODAY), date_range=(date(2026, 1, 1), date(2026, 6, 30))), k=20)
    assert {h.entity_id for h in inside} == {"EDJ", None}
    assert search(apply_filters(resolve(Q19, TODAY), date_range=(date(2026, 4, 1), date(2026, 6, 30))), k=20) == []


def test_firm_filter_drops_the_research_part(theme_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", theme_db)
    hits = search(apply_filters(resolve(Q19, TODAY), firms=["EDJ"]), k=20)
    assert {h.entity_id for h in hits} == {"EDJ"}


def test_each_firm_s_chunk_on_the_theme_is_sure_of_a_slot(theme_db, monkeypatch):
    # #117: two slots each; Schwab's only on-theme chunk ranks last but takes its first turn
    monkeypatch.setattr(fts, "connect", theme_db)
    q = resolve(Q12_LIKE, TODAY)
    assert (q.entities, q.themes, q.mode) == (["SCHW", "RJF"], ["client_acquisition"], "entity+theme")
    hits = search(q, k=4)
    assert [h.entity_id for h in hits].count("SCHW") == 2 and [h.entity_id for h in hits].count("RJF") == 2
    assert [h.doc_id for h in hits if h.on_theme] == ["SCHW-10Q-NEW"]
    assert theme_gaps(q, hits) == ["RJF"]                # reported, not padded away


def test_without_a_theme_rank_order_decides(theme_db, monkeypatch):
    monkeypatch.setattr(fts, "connect", theme_db)
    hits = search(resolve("How do Schwab and Raymond James acquire client data?", TODAY), k=4)
    assert "SCHW-10Q-NEW" not in {h.doc_id for h in hits} and not any(h.on_theme for h in hits)
