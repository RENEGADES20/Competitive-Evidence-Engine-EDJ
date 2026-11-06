"""Hybrid retrieval (#125): RRF, (firm, doc type) pool, rerank floor, filters in both legs, vectors
gate, cache-only reranker, mode switch. No database, no network; the real-reranker test runs only
when fastembed is installed and the model is already cached."""
import subprocess
import sys
import types
from datetime import date
from pathlib import Path

import pytest

from cee.retrieve import fts, hybrid
from cee.retrieve.fts import Hit, Query

REPO = Path(__file__).resolve().parents[1]


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


def test_take_turns_over_firm_and_document_type():
    fused = [("MS-TR#1", 0.9), ("MS-TR#2", 0.8), ("MS-SUPP#1", 0.3), ("RJF-TR#1", 0.1), (None, 0.0)][:4]
    group = {"MS-TR#1": ("MS", "transcript"), "MS-TR#2": ("MS", "transcript"),
             "MS-SUPP#1": ("MS", "supplement"), "RJF-TR#1": ("RJF", "transcript")}
    # each (firm, type) group gets a turn before any group gets a second place (Q24: tables)
    assert hybrid.take_turns(fused, group, 3) == ["MS-TR#1", "MS-SUPP#1", "RJF-TR#1"]
    assert hybrid.take_turns(fused, group, 10) == ["MS-TR#1", "MS-SUPP#1", "RJF-TR#1", "MS-TR#2"]


def test_take_turns_gives_firms_a_place_in_theme_questions():
    # Q21: research (no firm) fills the top of the fused list; firm chunks still reach the pool
    fused = [(f"R#{i}", 1 - i / 100) for i in range(10)] + [("MS#1", 0.01), ("EDJ#1", 0.005)]
    group = {**{f"R#{i}": (None, "research") for i in range(10)}, "MS#1": ("MS", "10-K"), "EDJ#1": ("EDJ", "10-K")}
    assert hybrid.take_turns(fused, group, 3) == ["R#0", "MS#1", "EDJ#1"]


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
FILTERED = Query(question="What is Morgan Stanley's advisor strategy?", entities=["MS"], firm_filter=["MS"],
                 date_range=(date(2026, 1, 1), date(2026, 6, 30)), keywords=["net new assets"])
ENTITY_THEME = Query(question="What does Edward Jones say about younger investors?", entities=["EDJ"],
                     themes=["client_segments"], mode="entity+theme")


@pytest.mark.parametrize("q", [MER, WINDOW, THEME, FILTERED], ids=["MER", "window", "theme", "ask-filters"])
def test_both_legs_carry_the_fts_hard_filters(q):
    where, wparams = fts.entity_filter(q.entities)
    window, _ = fts.window_filter(q.window)
    filters, fparams = fts.filters_sql(q)
    kw_sql, kw_params = hybrid.keyword_leg_sql(None, q)
    vec_sql, vec_params = hybrid.vector_leg_sql(q, "[0.0]")
    for sql, params in ((kw_sql, kw_params), (vec_sql, vec_params)):
        assert where in sql and window in sql and filters in sql
        assert all(params[k] == v for k, v in {**wparams, **fparams}.items())
        assert "PARTITION BY" in sql and "entity_id" in sql.split("PARTITION BY", 1)[1].split(")")[0]
    assert "JOIN chunk_embeddings e USING (chunk_id)" in vec_sql and "e.embedding <=>" in vec_sql
    if q is MER:  # Merrill: BAC chunks only inside GWIM / Merrill segments
        assert "c.segment = ANY(%(s0)s)" in vec_sql and vec_params["s0"] == ["GWIM", "Merrill"]
    if q is WINDOW:
        assert "d.published_at BETWEEN %(w_from)s AND %(w_to)s" in vec_sql
        assert "TRUE" in kw_sql.split("WHERE", 1)[1].split("AND", 1)[0]  # window: words only rank
    if q is FILTERED:
        assert "BETWEEN %(r_from)s AND %(r_to)s" in vec_sql and "phraseto_tsquery('english', %(kw0)s)" in vec_sql


def test_research_part_uses_the_theme_filter_in_both_legs():
    themes, tparams = fts.theme_filter(ENTITY_THEME.themes)
    where, _ = fts.entity_filter(ENTITY_THEME.entities)
    for sql, params in (hybrid.keyword_leg_sql(None, ENTITY_THEME, research=True),
                        hybrid.vector_leg_sql(ENTITY_THEME, "[0.0]", research=True)):
        assert themes in sql and where not in sql and params["themes"] == ["client_segments"]


def test_gap_path_returns_nothing_without_model_or_database(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no model or database for the gap path")
    monkeypatch.setattr(hybrid, "cross_encoder_scores", boom)
    monkeypatch.setitem(sys.modules, "cee.db", None)  # importing cee.db would fail
    assert hybrid.search(Query(question="What is LPL's strategy?", unmapped=["LPL"])) == []
    assert hybrid.search(Query(question="What is Morgan Stanley's strategy?", firm_filter=["RJF"])) == []


class _Result:
    def __init__(self, one=None, many=None):
        self.one, self.many = one, many

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


def test_missing_table_or_vectors_raise_a_clear_error():
    class NoTable:
        def execute(self, sql, *a):
            return _Result({"ok": False})
    with pytest.raises(hybrid.MissingVectors, match="chunk_embeddings.*embed --missing"):
        hybrid.check_vectors(NoTable())

    class Gaps:
        def execute(self, sql, *a):
            return _Result({"ok": True} if "to_regclass" in sql else {"n": 7})
    with pytest.raises(hybrid.MissingVectors, match="7 chunks have none"):
        hybrid.check_vectors(Gaps())


class FakeConn:
    """Answers the hybrid SQL: table checks, rank_sql IDF counts, keyword leg, vector leg, rows."""
    def __init__(self, kw, vec, rows, research_kw=(), research_vec=()):
        self.kw, self.vec, self.rows = kw, vec, rows
        self.research_kw, self.research_vec = list(research_kw), list(research_vec)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        if "to_regclass" in sql:
            return _Result({"ok": True})
        if "NOT EXISTS" in sql and "chunk_embeddings" in sql:
            return _Result({"n": 0})
        if "unnest(to_tsvector" in sql:
            return _Result(many=[{"lexeme": "advisor"}])
        if "n_all" in sql:
            return _Result({"n_all": 100, **{k: 1 for k in (params or {})}})
        if "chunk_id = ANY" in sql:
            return _Result(many=[r for r in self.rows if r["chunk_id"] in params["ids"]])
        research = "chunk_topics" in sql
        if "e.embedding <=>" in sql:
            return _Result(many=self.research_vec if research else self.vec)
        return _Result(many=self.research_kw if research else self.kw)


def _row(cid, entity, published="2026-01-01", doc_type="10-K"):
    return {"chunk_id": cid, "doc_id": cid.split("#")[0], "entity_id": entity, "segment": None,
            "doc_type": doc_type, "source_tier": 1, "published_at": published, "period_end": None,
            "section": None, "page": None, "text": f"passage {cid} " * 4, "prefix": "[x]"}


def _leg(*cids, entity="MS", doc_type="10-K"):
    return [{"chunk_id": c, "entity_id": entity, "doc_type": doc_type} for c in cids]


def _patch(monkeypatch, conn):
    import cee.db
    import cee.retrieve.embed as embed
    monkeypatch.setattr(cee.db, "connect", lambda: conn)
    monkeypatch.setattr(embed, "embed_query", lambda q: [0.0] * embed.DIM)


def test_search_reranks_floors_and_uses_no_relative_floor(monkeypatch):
    rows = [_row(c, "MS") for c in ("MS-A#1", "MS-B#1", "MS-C#1")]
    _patch(monkeypatch, FakeConn(_leg("MS-A#1", "MS-B#1"), _leg("MS-C#1", "MS-A#1"), rows))
    monkeypatch.setattr(hybrid, "RERANK_FLOOR", 0.01)
    scores = {"MS-A#1": -6.0, "MS-B#1": 4.0, "MS-C#1": -3.0}  # sigmoid: 0.0025, 0.982, 0.047
    seen = []

    def scorer(question, passages):
        seen.append(question)
        return [scores[next(c for c in scores if c in p)] for p in passages]
    hits = hybrid.search(Query(question="MS advisor pay?", entities=["MS"]), scorer=scorer)
    assert seen == ["MS advisor pay?"]
    # MS-A#1 is below RERANK_FLOOR; MS-C#1 (0.047 < 0.3 x 0.982) stays: select() runs with floor=0
    assert [h.chunk_id for h in hits] == ["MS-B#1", "MS-C#1"]
    assert hits[0].rank == pytest.approx(hybrid.sigmoid(4.0))


def test_window_has_no_floor_and_comes_back_newest_first(monkeypatch):
    rows = [_row("RJF-A#1", "RJF", "2026-08-01"), _row("RJF-B#1", "RJF", "2026-10-01")]
    _patch(monkeypatch, FakeConn(_leg("RJF-A#1", "RJF-B#1", entity="RJF"), [], rows))
    monkeypatch.setattr(hybrid, "RERANK_FLOOR", 0.5)
    hits = hybrid.search(WINDOW, scorer=lambda q, ps: [-9.0 if "RJF-B" in p else 3.0 for p in ps])
    assert [h.chunk_id for h in hits] == ["RJF-B#1", "RJF-A#1"]  # weak but kept; newest first


def test_entity_theme_adds_the_research_part(monkeypatch):
    rows = [_row("EDJ-10K#1", "EDJ"), _row("R-STUDY#1", None, doc_type="research")]
    conn = FakeConn(_leg("EDJ-10K#1", entity="EDJ"), [], rows,
                    research_kw=_leg("R-STUDY#1", entity=None, doc_type="research"))
    _patch(monkeypatch, conn)
    hits = hybrid.search(ENTITY_THEME, scorer=lambda q, ps: [1.0] * len(ps))
    assert [h.chunk_id for h in hits] == ["EDJ-10K#1", "R-STUDY#1"]


def test_mode_switch(monkeypatch):
    calls = []
    monkeypatch.setattr(fts, "fts_search", lambda q, k: calls.append("fts") or [])
    monkeypatch.setattr(hybrid, "search", lambda q, k: calls.append("hybrid") or [])
    monkeypatch.setenv("CEE_VECTORS", "on")
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


def test_hybrid_with_vectors_off_stops_before_importing_hybrid():
    code = ("import sys; sys.modules['fastembed'] = None; sys.modules['onnxruntime'] = None\n"
            "from cee.retrieve import fts\n"
            "try:\n"
            "    fts.search(fts.Query(question='x', entities=['MS']), mode='hybrid')\n"
            "except fts.HybridUnavailable as e:\n"
            "    print('refused', 'CEE_VECTORS=on' in str(e))\n"
            "print('cee.retrieve.hybrid' in sys.modules, sys.modules.get('fastembed') is not None)\n")
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO / "src"), "CEE_VECTORS": "off"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=REPO, env=env).stdout.split()
    assert out == ["refused", "True", "False", "False"]


def test_fts_mode_never_imports_hybrid():
    code = ("import sys; from cee.retrieve import fts; fts.fts_search = lambda q, k: []; "
            "fts.search(fts.Query(question='x'), mode='fts'); "
            "print('cee.retrieve.hybrid' in sys.modules, 'fastembed' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=REPO).stdout.split()
    assert out == ["False", "False"]


def _fake_fastembed(monkeypatch, calls):
    class TextCrossEncoder:
        def __init__(self, model_name, cache_dir, local_files_only=False):
            calls.append((model_name, local_files_only))
    mod = types.ModuleType("fastembed.rerank.cross_encoder")
    mod.TextCrossEncoder = TextCrossEncoder
    monkeypatch.setitem(sys.modules, "fastembed", types.ModuleType("fastembed"))
    monkeypatch.setitem(sys.modules, "fastembed.rerank", types.ModuleType("fastembed.rerank"))
    monkeypatch.setitem(sys.modules, "fastembed.rerank.cross_encoder", mod)


def test_reranker_not_cached_never_downloads(monkeypatch, tmp_path):
    calls = []
    _fake_fastembed(monkeypatch, calls)
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(missing))
    hybrid.reranker.cache_clear()
    with pytest.raises(hybrid.RerankerNotCached, match=r"FASTEMBED_CACHE_PATH.*hybrid --fetch"):
        hybrid.reranker(hybrid.DEFAULT_RERANK_MODEL)
    assert calls == [] and not missing.exists()


def test_cached_reranker_loads_local_files_only(monkeypatch, tmp_path):
    calls = []
    _fake_fastembed(monkeypatch, calls)
    name = hybrid.DEFAULT_RERANK_MODEL
    (tmp_path / hybrid.model_folder(name) / "snapshots" / "abc" / "onnx").mkdir(parents=True)
    (tmp_path / hybrid.model_folder(name) / "snapshots" / "abc" / "onnx" / "model.onnx").write_bytes(b"x")
    monkeypatch.setenv("FASTEMBED_CACHE_PATH", str(tmp_path))
    hybrid.reranker.cache_clear()
    hybrid.reranker(name)
    hybrid.reranker.cache_clear()
    assert calls == [(name, True)]


def test_unknown_rerank_model_is_refused(monkeypatch):
    monkeypatch.setenv("RERANK_MODEL", "some/other-model")
    with pytest.raises(ValueError, match="RERANK_MODEL"):
        hybrid.rerank_model_name()


def test_check_without_reranker_prints_one_line_and_exits_1(monkeypatch, capsys):
    import cee.retrieve.embed as embed
    monkeypatch.setattr(embed, "embed_query", lambda q: [0.0] * embed.DIM)

    def missing(*a, **k):
        raise hybrid.RerankerNotCached("Reranker x is not in y. ... `python -m cee.retrieve.hybrid --fetch` ...")
    monkeypatch.setattr(hybrid, "cross_encoder_scores", missing)
    assert hybrid.main(["--check"]) == 1
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith("ERROR: Reranker") and "--fetch" in err[0]


def _reranker_cached() -> bool:
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    return hybrid.reranker_cached(hybrid.DEFAULT_RERANK_MODEL)


@pytest.mark.skipif(not _reranker_cached(), reason="fastembed or the reranker not available (never downloaded by tests)")
def test_real_reranker_prefers_advisor_pay_over_a_guarantee(monkeypatch):
    monkeypatch.delenv("RERANK_MODEL", raising=False)
    hybrid.reranker.cache_clear()
    s = hybrid.cross_encoder_scores("What does the firm pay its financial advisors?",
                                    ["Advisor compensation is a formulaic payout tied to the revenue they produce.",
                                     "The Firm guarantees the prompt and full payment of its clients' obligations."])
    assert s[0] > s[1]
