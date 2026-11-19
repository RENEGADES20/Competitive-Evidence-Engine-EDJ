"""The pool trace (#210) records every candidate pool search() fetches and changes nothing: the same
hits in the same order with or without it. Fixture rows from test_retrieval_themes (a throwaway
schema of the local Postgres, skipped if it is down)."""
import pytest

from cee.retrieve import fts
from cee.retrieve.fts import PoolTrace, resolve, search
from tests.test_retrieval_themes import Q12_LIKE, Q19, TODAY, theme_db  # noqa: F401 (fixture)


@pytest.mark.parametrize("question", [
    Q19,                                                       # entity+theme with research and peers
    Q12_LIKE,                                                  # two firms on a firm theme
    "How do Schwab and Raymond James acquire client data?",    # entity mode
])
def test_trace_changes_no_hit(theme_db, monkeypatch, question):  # noqa: F811
    monkeypatch.setattr(fts, "connect", theme_db)
    plain = search(resolve(question, TODAY))
    trace = PoolTrace()
    traced = search(resolve(question, TODAY), trace=trace)
    assert [h.chunk_id for h in traced] == [h.chunk_id for h in plain]
    assert traced == plain
    assert {h.chunk_id for h in traced} <= trace.ids()       # every final hit was a candidate


def test_trace_records_each_pool(theme_db, monkeypatch):  # noqa: F811
    monkeypatch.setattr(fts, "connect", theme_db)
    trace = PoolTrace()
    search(resolve(Q19, TODAY), trace=trace)
    assert trace.firm and all(c.startswith("EDJ-") for c in trace.firm)
    assert trace.research and all(c.startswith("SURVEY-") for c in trace.research)
    assert trace.peers and "BAC-PR-GWIM#0" in trace.peers
    assert "BAC-PR-CONSUMER#0" not in trace.ids()              # the segment filter holds in the pool too
    assert trace.ids() == {*trace.firm, *trace.research, *trace.on_theme, *trace.peers, *trace.answers}


def test_no_pool_when_search_returns_early():
    q = resolve("What is Fidelity's advisor headcount?", TODAY)   # known firm, no documents held
    trace = PoolTrace()
    if q.unmapped and not q.entities:
        assert search(q, trace=trace) == [] and trace.ids() == set()
    else:
        pytest.skip("Fidelity resolves to a covered firm in this config")
