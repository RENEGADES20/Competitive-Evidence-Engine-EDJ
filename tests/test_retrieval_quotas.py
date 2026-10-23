"""Time windows, quotas, near-duplicate removal and the relevance floor (specs/retrieval.md).
No database: select() works on a ranked pool of Hits."""
import datetime as dt

from cee.retrieve import fts
from cee.retrieve.fts import Hit, _search_terms, resolve, select, window_since

TODAY = dt.date(2026, 10, 22)


def hit(cid, rank, entity="MS", doc_type="10-Q", text=None, doc=None):
    return Hit(chunk_id=cid, doc_id=doc or cid.split("#")[0], entity_id=entity, segment=None,
               doc_type=doc_type, source_tier=2, published_at="2026-01-01", period_end=None,
               section=None, page=None, rank=rank, text=text or f"unique words for {cid} " * 5)


def test_last_n_days_window():
    # Q26
    assert window_since("What's new on Raymond James in the last 90 days?", TODAY) == "2026-07-24"
    assert window_since("past 2 weeks", TODAY) == "2026-10-08"


def test_start_of_year_window():
    # Q27: calendar year of today's date (specs/retrieval.md open question, proposal: yes)
    assert window_since("What has changed at Merrill since the start of the year?", TODAY) == "2026-01-01"


def test_no_window():
    assert window_since("What is Morgan Stanley's strategy to increase their net new assets?", TODAY) is None
    assert resolve("What is Schwab's strategy for its RIA custody business?").since is None


def test_window_and_instruction_words_are_not_search_terms():
    terms = _search_terms(resolve("What's new on Raymond James in the last 90 days?", TODAY))
    assert "90" not in terms and "days" not in terms
    terms = _search_terms(resolve("Compare how Schwab and Raymond James describe their value "
                                  "proposition to independent advisors."))
    assert "Compare" not in terms and "describe" not in terms
    assert "value proposition" in terms and "independent advisors" in terms


def test_boilerplate_repeated_across_filings_is_dropped():
    # Q1: the same NNA definition in four 10-Qs took every slot.
    definition = "Net new assets represent client asset inflows including interest and dividends " * 4
    pool = [hit(f"MS-10Q-2026Q{i}#5", 10 - i, text=definition + f" period {i}") for i in range(1, 5)]
    pool.append(hit("MS-TR-2026Q2#13", 5, doc_type="transcript"))
    kept = [h.chunk_id for h in select(pool, k=20)]
    assert kept == ["MS-10Q-2026Q1#5", "MS-TR-2026Q2#13"]


def test_document_types_take_turns():
    pool = [hit(f"MS-10Q-X#{i}", 10 - i * 0.1, doc=f"MS-10Q-{i}") for i in range(6)]
    pool += [hit(f"MS-TR-X#{i}", 6 - i * 0.1, doc_type="transcript", doc=f"MS-TR-{i}") for i in range(3)]
    types = [h.doc_type for h in select(pool, k=4)]
    assert types == ["10-Q", "transcript", "10-Q", "transcript"]


def test_firms_take_turns():
    # Q7 acceptance: every named firm gets its quota; no firm fills the list.
    pool = [hit(f"MS-10Q-X#{i}", 10, doc=f"MS-{i}") for i in range(5)]
    pool += [hit(f"RJF-10Q-X#{i}", 2, entity="RJF", doc=f"RJF-{i}") for i in range(5)]
    entities = [h.entity_id for h in select(pool, k=6)]
    assert entities.count("MS") == entities.count("RJF") == 3


def test_one_document_gives_at_most_max_per_doc():
    pool = [hit(f"MS-TR-2026Q2#{i}", 10 - i, doc_type="transcript", doc="MS-TR-2026Q2") for i in range(6)]
    assert len(select(pool, k=20)) == fts.MAX_PER_DOC


def test_chunks_far_below_the_best_get_no_slot():
    pool = [hit("MS-TR-A#1", 10, doc_type="transcript"), hit("MS-SUPP-A#1", 1, doc_type="supplement")]
    assert [h.chunk_id for h in select(pool, k=20)] == ["MS-TR-A#1"]
