"""Hybrid retrieval (#125): RRF, rerank floor, filters in both legs, mode switch. No database,
no network; the real-reranker test runs only when the model is already cached."""
import sys
from datetime import date
from pathlib import Path

import pytest

from cee.retrieve import fts, hybrid
from cee.retrieve.fts import Hit, Query


def hit(cid, rank, entity="MS", doc=None, published="2026-01-01"):
    return Hit(chunk_id=cid, doc_id=doc or cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=1, published_at=published, period_end=None, section=None, page=None, rank=rank,
               text=f"distinct passage {cid} " * 3)


def test_rrf_hand_worked_example():
    # a: 1/(60+1) + 1/(60+2); b: 1/(60+2) + 1/(60+1); c: 1/(60+3); d: 1/(60+3) -> ties by chunk_id
    fused = hybrid.rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert [cid for cid, _ in fused] == ["a", "b", "c", "d"]
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)
    assert fused[2][1] == pytest.approx(1 / 63)
    assert hybrid.rrf([["x"]], k=0)[0][1] == pytest.approx(1.0)


def test_rrf_rewards_agreement_between_legs():
    fused = dict(hybrid.rrf([["only-kw", "both"], ["only-vec", "both"]]))
    assert fused["both"] > fused["only-kw"] == fused["only-vec"]


def test_take_turns_gives_every_firm_a_place():
    fused = [("MS#1", 0.9), ("MS#2", 0.8), ("MS#3", 0.7), ("RJF#1", 0.1), ("BAC#1", 0.05)]
    firm = {"MS#1": "MS", "MS#2": "MS", "MS#3": "MS", "RJF#1": "RJF", "BAC#1": "BAC"}
    assert hybrid.take_turns(fused, firm, 4, by_firm=True) == ["MS#1", "RJF#1", "BAC#1", "MS#2"]
    assert hybrid.take_turns(fused, firm, 2, by_firm=False) == ["MS#1", "MS#2"]


def test_floor_drops_weak_hits_and_keeps_score_order():
    pool = [hit("A#1", 0.02), hit("B#1", 0.9), hit("C#1", 0.4), hit("D#1", 0.05)]
    assert [h.chunk_id for h in hybrid.apply_floor(pool, 0.05)] == ["B#1", "C#1", "D#1"]
    assert [h.chunk_id for h in hybrid.apply_floor(pool, 0.0)] == ["B#1", "C#1", "D#1", "A#1"]


def test_sigmoid_is_stable_and_monotone():
    assert hybrid.sigmoid(0) == 0.5
    assert 0 <= hybrid.sigmoid(-800) < hybrid.sigmoid(-1) < hybrid.sigmoid(3) < hybrid.sigmoid(800) <= 1


MER = Query(question="What is Merrill's advisor growth strategy?", entities=["MER"])
WINDOW = Query(question="What's new on Raymond James in the last 90 days?", entities=["RJF"],
               window=(date(2026, 7, 31), date(2026, 10, 29)))
THEME = Query(question="How are firms using AI?", mode="theme")


@pytest.mark.parametrize("q", [MER, WINDOW, THEME])
def test_both_legs_carry_the_fts_hard_filters(q):
    where, wparams = fts.entity_filter(q.entities)
    window, _ = fts.window_filter(q.window)
    kw_sql, kw_params = hybrid.keyword_leg_sql(None, q)
    vec_sql, vec_params = hybrid.vector_leg_sql(q, "[0.0]")
    for sql, params in ((kw_sql, kw_params), (vec_sql, vec_params)):
        assert where in sql and window in sql
        assert all(params[k] == v for k, v in wparams.items())
    if q is MER:  # Merrill: BAC chunks only inside GWIM / Merrill segments
        assert "c.segment = ANY(%(s0)s)" in vec_sql and vec_params["s0"] == ["GWIM", "Merrill"]
    if q is WINDOW:
        assert "d.published_at BETWEEN %(w_from)s AND %(w_to)s" in vec_sql
        assert "TRUE" in kw_sql.split("WHERE", 1)[1].split("AND", 1)[0]  # window: words only rank
    if q is THEME:
        assert "LIMIT %(leg_k)s" in vec_sql and "PARTITION BY 1" in kw_sql
    else:
        assert "PARTITION BY d.entity_id" in vec_sql and "PARTITION BY entity_id" in kw_sql


def test_unmapped_firm_only_returns_nothing_without_a_model(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no model or database for the gap path")
    monkeypatch.setattr(hybrid, "cross_encoder_scores", boom)
    monkeypatch.setitem(sys.modules, "cee.db", None)  # importing cee.db would fail
    assert hybrid.search(Query(question="What is LPL's strategy?", unmapped=["LPL"])) == []


def test_null_embeddings_raise_a_clear_error():
    class Conn:
        def execute(self, sql, *a):
            class R:
                def fetchone(self):
                    return {"e": True}
            return R()
    with pytest.raises(hybrid.MissingVectors, match="embed --missing"):
        hybrid.check_vectors(Conn())


class FakeConn:
    """Answers the hybrid SQL in order: NULL check, rank_sql IDF counts, keyword leg, HNSW
    settings, vector leg, candidate rows."""
    def __init__(self, kw, vec, rows):
        self.kw, self.vec, self.rows = kw, vec, rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        conn = self

        class R:
            def fetchone(self):
                if "EXISTS" in sql:
                    return {"e": False}
                return {"n_all": 100, **{k: 1 for k in (params or {})}}

            def fetchall(self):
                if "unnest(to_tsvector" in sql:
                    return [{"lexeme": "advisor"}]
                if "c.embedding <=>" in sql:
                    return conn.vec
                if "chunk_id = ANY" in sql:
                    return [r for r in conn.rows if r["chunk_id"] in params["ids"]]
                return conn.kw
        return R()


def _row(cid, entity, published="2026-01-01"):
    return {"chunk_id": cid, "doc_id": cid.split("#")[0], "entity_id": entity, "segment": None,
            "doc_type": "10-K", "source_tier": 1, "published_at": published, "period_end": None,
            "section": None, "page": None, "text": f"passage {cid} " * 4, "prefix": "[x]"}


def _patch(monkeypatch, conn):
    import cee.db
    import cee.retrieve.embed as embed
    monkeypatch.setattr(cee.db, "connect", lambda: conn)
    monkeypatch.setattr(embed, "embed_query", lambda q: [0.0] * embed.DIM)


def test_search_reranks_floors_and_quotas(monkeypatch):
    kw = [{"chunk_id": "MS-A#1", "entity_id": "MS"}, {"chunk_id": "MS-B#1", "entity_id": "MS"}]
    vec = [{"chunk_id": "MS-C#1", "entity_id": "MS"}, {"chunk_id": "MS-A#1", "entity_id": "MS"}]
    rows = [_row(c, "MS") for c in ("MS-A#1", "MS-B#1", "MS-C#1")]
    _patch(monkeypatch, FakeConn(kw, vec, rows))
    scores = {"MS-A#1": -5.0, "MS-B#1": 2.0, "MS-C#1": 0.0}  # sigmoid: 0.0067, 0.88, 0.5
    seen = []

    def scorer(question, passages):
        seen.append(question)
        return [scores[next(c for c in scores if c in p)] for p in passages]
    q = Query(question="MS advisor pay?", entities=["MS"])
    hits = hybrid.search(q, scorer=scorer)
    assert seen == ["MS advisor pay?"]
    assert [h.chunk_id for h in hits] == ["MS-B#1", "MS-C#1"]  # MS-A#1 is below RERANK_FLOOR
    assert hits[0].rank == pytest.approx(hybrid.sigmoid(2.0))


def test_window_has_no_floor_and_comes_back_newest_first(monkeypatch):
    kw = [{"chunk_id": "RJF-A#1", "entity_id": "RJF"}, {"chunk_id": "RJF-B#1", "entity_id": "RJF"}]
    rows = [_row("RJF-A#1", "RJF", "2026-08-01"), _row("RJF-B#1", "RJF", "2026-10-01")]
    _patch(monkeypatch, FakeConn(kw, [], rows))
    hits = hybrid.search(WINDOW, scorer=lambda q, ps: [-9.0 if "RJF-B" in p else 3.0 for p in ps])
    assert [h.chunk_id for h in hits] == ["RJF-B#1", "RJF-A#1"]  # weak but kept; newest first


def test_mode_switch(monkeypatch):
    calls = []
    monkeypatch.setattr(fts, "fts_search", lambda q, k: calls.append("fts") or [])
    monkeypatch.setattr(hybrid, "search", lambda q, k: calls.append("hybrid") or [])
    q = Query(question="x", entities=["MS"])
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    fts.search(q)
    fts.search(q, mode="hybrid")
    fts.search(q, mode="FTS")
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    fts.search(q)
    assert calls == ["fts", "hybrid", "fts", "hybrid"]
    with pytest.raises(ValueError, match="unknown retrieval mode"):
        fts.search(q, mode="vector")


def test_fts_mode_never_imports_hybrid(tmp_path):
    import subprocess
    code = ("import sys; from cee.retrieve import fts; fts.fts_search = lambda q, k: []; "
            "fts.search(fts.Query(question='x'), mode='fts'); "
            "print('cee.retrieve.hybrid' in sys.modules, 'fastembed' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=Path(__file__).resolve().parents[1]).stdout.split()
    assert out == ["False", "False"]


def _reranker_cached() -> bool:
    from cee.retrieve.embed import cache_dir
    name = hybrid.rerank_model_name().split("/")[-1]
    return any(Path(cache_dir()).glob(f"models--*{name}*/snapshots/*/onnx/model.onnx"))


@pytest.mark.skipif(not _reranker_cached(), reason="reranker not in the cache (never downloaded by tests)")
def test_real_reranker_prefers_advisor_pay_over_a_guarantee():
    s = hybrid.cross_encoder_scores("What does the firm pay its financial advisors?",
                                    ["Advisor compensation is a formulaic payout tied to the revenue they produce.",
                                     "The Firm guarantees the prompt and full payment of its clients' obligations."])
    assert s[0] > s[1]
