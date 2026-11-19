"""Hybrid retrieval (#125): RRF, (firm, doc type) pool, rerank floor, filters in both legs, vectors
gate, cache-only reranker, mode switch. No database, no network; the real-reranker test runs only
when fastembed is installed and the model is already cached."""
import subprocess
import sys
import types
from datetime import date
from pathlib import Path

import pytest

from cee.retrieve import fts, hybrid, modes
from cee.retrieve.fts import Hit, PoolTrace, Query

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
        assert "PARTITION BY" in sql
    assert "JOIN chunk_embeddings e USING (chunk_id)" in vec_sql and "e.embedding <=>" in vec_sql
    if q is MER:  # Merrill: BAC chunks only inside GWIM / Merrill segments; one quota firm (#211 R3)
        assert "c.segment = ANY(%(s0)s)" in vec_sql and vec_params["s0"] == ["GWIM", "Merrill"]
        for sql, params in ((kw_sql, kw_params), (vec_sql, vec_params)):
            assert "WHEN d.entity_id = %(qf_entity0)s THEN %(qf_firm0)s" in sql
            assert (params["qf_entity0"], params["qf_firm0"]) == ("BAC", "MER")
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
    def __init__(self, kw, vec, rows, research_kw=(), research_vec=(), theme_kw=(), theme_vec=(),
                 peer_kw=(), peer_vec=(), answers=()):
        self.kw, self.vec, self.rows = kw, vec, rows
        self.research_kw, self.research_vec = list(research_kw), list(research_vec)
        self.theme_kw, self.theme_vec = list(theme_kw), list(theme_vec)
        self.peer_kw, self.peer_vec = list(peer_kw), list(peer_vec)
        self.answers = list(answers)
        self.sql = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.sql.append((sql, params or {}))
        if "to_regclass" in sql:
            return _Result({"ok": True})
        if "NOT EXISTS" in sql and "chunk_embeddings" in sql:
            return _Result({"n": 0})
        if "unnest(to_tsvector" in sql:
            return _Result(many=[{"lexeme": "advisor"}])
        if "n_all" in sql:
            return _Result({"n_all": 100, **{k: 1 for k in (params or {})}})
        if "question_ids" in (params or {}):  # fts.ANSWER_SQL
            return _Result(many=[a for a in self.answers if a["question_id"] in params["question_ids"]])
        if "chunk_id = ANY" in sql:
            return _Result(many=[r for r in self.rows if r["chunk_id"] in params["ids"]])
        vec = "e.embedding <=>" in sql
        if "chunk_topics" in sql:
            return _Result(many=self.research_vec if vec else self.research_kw)
        if "peer_e0" in (params or {}):
            return _Result(many=self.peer_vec if vec else self.peer_kw)
        if "on_theme" in (params or {}):
            return _Result(many=self.theme_vec if vec else self.theme_kw)
        return _Result(many=self.vec if vec else self.kw)


def _row(cid, entity, published="2026-01-01", doc_type="10-K"):
    return {"chunk_id": cid, "doc_id": cid.split("#")[0], "entity_id": entity, "segment": None,
            "doc_type": doc_type, "source_tier": 1, "published_at": published, "period_end": None,
            "section": None, "page": None, "text": f"passage {cid} " * 4, "date_basis": "source", "prefix": "[x]"}


def _leg(*cids, entity="MS", doc_type="10-K", qfirm=None):
    return [{"chunk_id": c, "entity_id": entity, "doc_type": doc_type, "qfirm": qfirm or entity} for c in cids]


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
    monkeypatch.setattr(fts, "search", lambda q, k, trace=None: calls.append("fts") or [])
    monkeypatch.setattr(hybrid, "search", lambda q, k, trace=None, rerank=True: calls.append("hybrid") or [])
    monkeypatch.setenv("CEE_VECTORS", "on")
    q = Query(question="x", entities=["MS"])
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    modes.search(q)
    modes.search(q, mode="hybrid")
    modes.search(q, mode="FTS")
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    modes.search(q)
    assert calls == ["fts", "hybrid", "fts", "hybrid"]
    with pytest.raises(ValueError, match="unknown retrieval mode"):
        modes.search(q, mode="vector")


def test_fts_py_has_no_mode_switch():
    # #211: fts.py equals main; the switch lives in cee.retrieve.modes
    assert not hasattr(fts, "MODES") and not hasattr(fts, "HybridUnavailable")
    assert hybrid.HybridUnavailable is modes.HybridUnavailable


def _vectors_off_code(mode):
    return ("import sys; sys.modules['fastembed'] = None; sys.modules['onnxruntime'] = None\n"
            "from cee.retrieve import fts, modes\n"
            "try:\n"
            f"    modes.search(fts.Query(question='x', entities=['MS']), mode='{mode}')\n"
            "except modes.HybridUnavailable as e:\n"
            "    print('refused', 'CEE_VECTORS=on' in str(e))\n"
            "print('cee.retrieve.hybrid' in sys.modules, sys.modules.get('fastembed') is not None)\n")


@pytest.mark.parametrize("mode", ["hybrid", "hybrid-norerank"])
def test_hybrid_with_vectors_off_stops_before_importing_hybrid(mode):
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO / "src"), "CEE_VECTORS": "off"}
    out = subprocess.run([sys.executable, "-c", _vectors_off_code(mode)], capture_output=True, text=True,
                         check=True, cwd=REPO, env=env).stdout.split()
    assert out == ["refused", "True", "False", "False"]


def test_fts_mode_never_imports_hybrid():
    code = ("import sys; from cee.retrieve import fts, modes; fts.search = lambda q, k, trace=None: []; "
            "modes.search(fts.Query(question='x'), mode='fts'); "
            "print('cee.retrieve.hybrid' in sys.modules, 'fastembed' in sys.modules)")
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO / "src")}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         cwd=REPO, env=env).stdout.split()
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


# --- #126: hybrid-norerank, RRF gate, per-mode constants -----------------------------------------

def test_gate_drops_below_floor_share_of_the_firm_best():
    rrf = {"MS#1": 2 / 61, "MS#2": 1 / 61, "MS#3": 1 / 160, "RJF#1": 1 / 100, "RJF#2": 1 / 400}
    group = {c: (c.split("#")[0], "10-K") for c in rrf}
    ids = list(rrf)
    assert hybrid.gate(ids, rrf, group, 0.0) == ids
    # MS best 0.0328: 0.3 x -> 0.0098 keeps MS#1, MS#2; RJF best 0.01 -> 0.003 keeps RJF#1 only
    assert hybrid.gate(ids, rrf, group, 0.3) == ["MS#1", "MS#2", "RJF#1"]
    assert hybrid.gate(ids, rrf, group, 0.6) == ["MS#1", "RJF#1"]


def _boom(*a, **k):
    raise AssertionError("hybrid-norerank never calls the reranker")


def test_norerank_orders_by_rrf_and_never_scores(monkeypatch):
    rows = [_row(c, "MS") for c in ("MS-A#1", "MS-B#1", "MS-C#1")]
    # MS-A#1: kw 1 + vec 2 = 1/61 + 1/62; MS-C#1: vec 1 = 1/61; MS-B#1: kw 2 = 1/62
    _patch(monkeypatch, FakeConn(_leg("MS-A#1", "MS-B#1"), _leg("MS-C#1", "MS-A#1"), rows))
    monkeypatch.setattr(hybrid, "cross_encoder_scores", _boom)
    monkeypatch.setattr(hybrid, "reranker", _boom)
    hits = hybrid.search(Query(question="MS advisor pay?", entities=["MS"]), scorer=_boom, rerank=False)
    assert [h.chunk_id for h in hits] == ["MS-A#1", "MS-C#1", "MS-B#1"]
    assert hits[0].rank == pytest.approx(1 / 61 + 1 / 62)


def test_both_hybrid_modes_share_the_gated_candidates(monkeypatch):
    cids = [f"MS-D{i}#1" for i in range(6)]
    rows = [_row(c, "MS") for c in cids]
    _patch(monkeypatch, FakeConn(_leg(*cids), _leg(*cids[:2]), rows))
    monkeypatch.setitem(hybrid.FLOOR, "hybrid", 0.6)
    monkeypatch.setitem(hybrid.FLOOR, "hybrid-norerank", 0.6)
    scored = []
    q = Query(question="MS advisor pay?", entities=["MS"])
    reranked = hybrid.search(q, scorer=lambda qq, ps: scored.extend(ps) or [0.0] * len(ps))
    plain = hybrid.search(q, rerank=False)
    # best: D0 (kw 1 + vec 1 = 2/61); 0.6 x 0.0328 = 0.0197 keeps D0, D1 (both legs) only
    assert {h.chunk_id for h in plain} == {h.chunk_id for h in reranked} == {"MS-D0#1", "MS-D1#1"}
    assert len(scored) == 2


def test_norerank_window_has_no_floor(monkeypatch):
    rows = [_row("RJF-A#1", "RJF", "2026-08-01"), _row("RJF-B#1", "RJF", "2026-10-01")]
    # A: kw 1 + vec 1; B: kw 2 only -> B is far below 0.99 x A's score, but a window has no floor
    _patch(monkeypatch, FakeConn(_leg("RJF-A#1", "RJF-B#1", entity="RJF"), _leg("RJF-A#1", entity="RJF"), rows))
    monkeypatch.setitem(hybrid.FLOOR, "hybrid-norerank", 0.99)
    hits = hybrid.search(WINDOW, rerank=False)
    assert [h.chunk_id for h in hits] == ["RJF-B#1", "RJF-A#1"]  # weak B kept; newest first


@pytest.mark.parametrize("mode", ["hybrid", "hybrid-norerank"])
@pytest.mark.parametrize("cap", [2, 4])
def test_per_mode_max_per_doc_leaves_window_and_research_caps(monkeypatch, mode, cap):
    monkeypatch.setitem(hybrid.MAX_PER_DOC, mode, cap)
    rerank = mode == "hybrid"
    scorer = (lambda q, ps: [1.0] * len(ps)) if rerank else _boom
    # firm part: one document with 10 chunks -> cap chunks
    firm = [f"MS-DOC#{i}" for i in range(10)]
    _patch(monkeypatch, FakeConn(_leg(*firm), [], [_row(c, "MS") for c in firm]))
    hits = hybrid.search(Query(question="MS advisor pay?", entities=["MS"]), scorer=scorer, rerank=rerank)
    assert len(hits) == cap
    # window: the window cap (8) applies, not the per-mode cap
    win = [f"RJF-DOC#{i}" for i in range(10)]
    _patch(monkeypatch, FakeConn(_leg(*win, entity="RJF"), [], [_row(c, "RJF", "2026-08-01") for c in win]))
    assert len(hybrid.search(WINDOW, scorer=scorer, rerank=rerank)) == fts.WINDOW_MAX_PER_DOC == 8
    # entity+theme research part: the research cap (2) applies
    res = [f"R-STUDY#{i}" for i in range(5)]
    _patch(monkeypatch, FakeConn([], [], [_row(c, None, doc_type="research") for c in res],
                                 research_kw=_leg(*res, entity=None, doc_type="research")))
    assert len(hybrid.search(ENTITY_THEME, scorer=scorer, rerank=rerank)) == fts.THEME_MAX_PER_DOC == 2


@pytest.mark.parametrize("mode", ["hybrid", "hybrid-norerank"])
def test_near_duplicates_use_the_fts_constant(monkeypatch, mode):
    # #211: no per-mode DUP_JACCARD; select() uses fts.DUP_JACCARD (0.6, the #126 pick for both modes)
    assert not hasattr(hybrid, "DUP_JACCARD") and fts.DUP_JACCARD == 0.6
    rows = [_row("MS-A#1", "MS"), _row("MS-B#1", "MS")]
    for r in rows:
        r["text"] = "the same boilerplate sentence about advisors repeats in every filing word for word"
    rerank = mode == "hybrid"
    scorer = (lambda q, ps: [1.0] * len(ps)) if rerank else _boom
    _patch(monkeypatch, FakeConn(_leg("MS-A#1", "MS-B#1"), [], rows))
    q = Query(question="MS advisor pay?", entities=["MS"])
    assert len(hybrid.search(q, scorer=scorer, rerank=rerank)) == 1


def test_mode_switch_routes_hybrid_norerank(monkeypatch):
    calls = []
    monkeypatch.setattr(hybrid, "search", lambda q, k, trace=None, rerank=True: calls.append(rerank) or [])
    monkeypatch.setenv("CEE_VECTORS", "on")
    q = Query(question="x", entities=["MS"])
    modes.search(q, mode="hybrid")
    modes.search(q, mode="hybrid-norerank")
    modes.search(q, mode="HYBRID-NORERANK")
    assert calls == [True, False, False]


# --- #211: every rule of main's fts.search() in hybrid (R1-R11 of plans/0211-hybrid-retest.md) --------

def _parts(conn):
    """SQL of the leg queries a search sent (keyword and vector legs only)."""
    return [(sql, p) for sql, p in conn.sql if "PARTITION BY" in sql]


@pytest.mark.parametrize("rerank", [True, False])
def test_r1_doc_type_scope_in_every_leg_and_answer_turns(monkeypatch, rerank):
    # Q1-like question: no fee words -> Form ADV brochures are left out of every SQL pass (ADR-015)
    q = Query(question="What is Edward Jones's strategy for younger investors?", entities=["EDJ"],
              themes=["client_segments"], mode="entity+theme", theme_peers=["MS"])
    scope, params = fts.doc_type_scope_sql(q)
    assert "scope_types" in params and params["scope_types"] == ["adv"]
    conn = FakeConn(_leg("EDJ-10K#1", entity="EDJ"), [], [_row("EDJ-10K#1", "EDJ")])
    _patch(monkeypatch, conn)
    hybrid.search(q, scorer=lambda qq, ps: [1.0] * len(ps), rerank=rerank)
    legs = _parts(conn)
    assert len(legs) == 8  # firm, on-theme, research, peers x keyword, vector
    assert all(scope in sql and p["scope_types"] == ["adv"] for sql, p in legs)
    # benchmark question: no tier 4
    bench = Query(question="Advisor headcount across Morgan Stanley and Raymond James", entities=["MS", "RJF"])
    assert "scope_tiers" in fts.doc_type_scope_sql(bench)[1]
    for sql, p in (hybrid.keyword_leg_sql(None, bench), hybrid.vector_leg_sql(bench, "[0.0]")):
        assert "d.source_tier <> ALL(%(scope_tiers)s)" in sql and p["scope_tiers"] == [4]


def test_r2_k_defaults_to_the_budget_and_scales_the_candidates(monkeypatch):
    five = Query(question="Net new assets for each of the five", entities=["MS", "SCHW", "EDJ", "MER", "RJF"])
    assert fts.budget(five) == 30
    seen = []
    real = hybrid.candidates

    def spy(conn, q, qvec, n, research=False, part=None, rank=None):
        seen.append((part, n))
        return real(conn, q, qvec, n, research, part, rank)
    monkeypatch.setattr(hybrid, "candidates", spy)
    _patch(monkeypatch, FakeConn([], [], []))
    hybrid.search(five, rerank=False)
    hybrid.search(Query(question="MS pay?", entities=["MS"]), rerank=False)
    assert seen == [("firm", 75), ("firm", 50)]  # RERANK_N x k / K: 50 x 30 / 20, 50 x 20 / 20


def test_r3_merrill_and_bac_gwim_form_one_ranked_list(monkeypatch):
    # the legs partition by the quota firm: BAC GWIM rows come back with qfirm MER, in one list
    kw = [{"chunk_id": "BAC-10K#1", "entity_id": "BAC", "doc_type": "10-K", "qfirm": "MER"},
          {"chunk_id": "MER-PR#1", "entity_id": "MER", "doc_type": "press_release", "qfirm": "MER"},
          {"chunk_id": "BAC-10K#2", "entity_id": "BAC", "doc_type": "10-K", "qfirm": "MER"}]
    assert hybrid._per_firm(kw) == [["BAC-10K#1", "MER-PR#1", "BAC-10K#2"]]
    fused = dict(hybrid.rrf(hybrid._per_firm(kw)))
    assert sorted(fused.values(), reverse=True) == pytest.approx([1 / 61, 1 / 62, 1 / 63])  # one rank 1
    rows = [_row("BAC-10K#1", "BAC"), _row("MER-PR#1", "MER", doc_type="press_release"), _row("BAC-10K#2", "BAC")]
    conn = FakeConn(kw, [], rows)
    _patch(monkeypatch, conn)
    seen = []
    real = fts.select
    monkeypatch.setattr(fts, "select", lambda pool, k, **kw_: seen.append(kw_.get("firm_of")) or real(pool, k, **kw_))
    hits = hybrid.search(MER, rerank=False)
    assert seen[0] == {"BAC": "MER"}  # select() counts Merrill once
    assert {h.chunk_id for h in hits} == {"BAC-10K#1", "MER-PR#1", "BAC-10K#2"}
    assert all("(CASE WHEN d.entity_id = %(qf_entity0)s THEN %(qf_firm0)s ELSE d.entity_id END)" in sql
               for sql, _ in _parts(conn))


def test_r4_norerank_floor_from_the_second_best(monkeypatch):
    # X: both legs (2/61); Y: kw 2 (1/62); Z: vec 30 (1/90); W: kw 60 (1/120). FLOOR 0.4:
    # base = 2nd best (Y, 0.0161) -> 0.0065 keeps all; the old base (X, 0.0328) -> 0.0131 dropped Z, W
    kw = _leg("X#1", "Y#1", *[f"P{i}#1" for i in range(57)], "W#1")
    vec = _leg("X#1", *[f"V{i}#1" for i in range(28)], "Z#1")
    keep = {"X#1", "Y#1", "Z#1", "W#1"}
    rows = [_row(c["chunk_id"], "MS") for c in kw + vec]
    _patch(monkeypatch, FakeConn(kw, vec, rows))
    monkeypatch.setattr(hybrid, "RERANK_N", 200)
    hits = hybrid.search(Query(question="MS advisor pay?", entities=["MS"]), k=200, rerank=False)
    assert keep <= {h.chunk_id for h in hits}
    assert hybrid.gate(["X#1", "Y#1", "Z#1"], {"X#1": 2 / 61, "Y#1": 1 / 62, "Z#1": 1 / 90},
                       {c: ("MS", "10-K") for c in ("X#1", "Y#1", "Z#1")}, 0.4, 2) == ["X#1", "Y#1", "Z#1"]


def test_r5_on_theme_scores_merge_below_the_firm_part():
    group = {"EDJ#1": ("EDJ", "10-K"), "EDJ#2": ("EDJ", "10-K"), "EDJ#T": ("EDJ", "10-Q"), "EDJ#U": ("EDJ", "10-Q")}
    ids, score = hybrid.merge_theme(["EDJ#1", "EDJ#2"], {"EDJ#1": 0.032, "EDJ#2": 0.030},
                                    ["EDJ#T", "EDJ#2", "EDJ#U"], {"EDJ#T": 1 / 61, "EDJ#2": 1 / 62, "EDJ#U": 1 / 63},
                                    group)
    assert ids == ["EDJ#1", "EDJ#2", "EDJ#T", "EDJ#U"]
    assert score["EDJ#2"] == 0.030                                   # in both parts: firm-part score
    assert score["EDJ#T"] < 0.030 and score["EDJ#U"] < score["EDJ#T"]  # strictly below, order kept
    assert score["EDJ#T"] == pytest.approx(0.99 * 0.030)
    ranks = sorted(score.values(), reverse=True)
    assert ranks[1] == 0.030  # the 2nd-best floor base is unchanged


def test_r5_on_theme_only_chunk_takes_the_theme_slot_below_the_floor(monkeypatch):
    rows = [_row("EDJ-A#1", "EDJ"), _row("EDJ-B#1", "EDJ"), _row("EDJ-T#1", "EDJ", doc_type="10-Q")]
    conn = FakeConn(_leg("EDJ-A#1", "EDJ-B#1", entity="EDJ"), _leg("EDJ-A#1", "EDJ-B#1", entity="EDJ"), rows,
                    theme_kw=_leg("EDJ-T#1", entity="EDJ", doc_type="10-Q"))
    _patch(monkeypatch, conn)
    monkeypatch.setitem(hybrid.FLOOR, "hybrid-norerank", 0.999)
    hits = hybrid.search(ENTITY_THEME, rerank=False)
    by_id = {h.chunk_id: h for h in hits}
    assert by_id["EDJ-T#1"].on_theme and by_id["EDJ-T#1"].rank < min(by_id[c].rank for c in ("EDJ-A#1",))
    assert fts.theme_gaps(ENTITY_THEME, hits) == []


def _turn_row(cid, text, entity="RJF"):
    r = _row(cid, entity, doc_type="transcript")
    r["text"] = text
    return r


def test_r6_answer_turn_follows_its_question_turn(monkeypatch):
    q_text = "Jim Smith, Analyst\n\nHow is the affiliation mix shifting?"
    a = {**_turn_row("RJF-TR#46", "Paul Shoukry, CEO\n\nThe mix has shifted toward independence."),
         "question_id": "RJF-TR#45"}
    a.pop("prefix")
    rows = [_turn_row("RJF-TR#45", q_text), _row("RJF-10K#1", "RJF")]
    conn = FakeConn(_leg("RJF-TR#45", "RJF-10K#1", entity="RJF"), [], rows, answers=[a])
    _patch(monkeypatch, conn)
    trace = PoolTrace()
    hits = hybrid.search(Query(question="RJF affiliation mix?", entities=["RJF"]), rerank=False, trace=trace)
    ids = [h.chunk_id for h in hits]
    assert ids.index("RJF-TR#46") == ids.index("RJF-TR#45") + 1
    assert trace.answers == ["RJF-TR#46"]
    answer_sql = next(sql for sql, p in conn.sql if "question_ids" in p)
    assert fts.doc_type_scope_sql(Query(question="RJF affiliation mix?", entities=["RJF"]))[0] in answer_sql


def test_r7_theme_peers_come_on_top_two_each(monkeypatch):
    q = Query(question="What is Edward Jones doing for younger investors?", entities=["EDJ"],
              themes=["client_segments"], mode="entity+theme", theme_peers=["MS", "SCHW"])
    assert fts.peer_slots(q) == 4
    peers_ms = [f"MS-P{i}#1" for i in range(4)]
    rows = [_row("EDJ-A#1", "EDJ"), *[_row(c, "MS") for c in peers_ms], _row("SCHW-P#1", "SCHW")]
    conn = FakeConn(_leg("EDJ-A#1", entity="EDJ"), [], rows,
                    peer_kw=_leg(*peers_ms, entity="MS") + _leg("SCHW-P#1", entity="SCHW"))
    _patch(monkeypatch, conn)
    monkeypatch.setitem(hybrid.FLOOR, "hybrid-norerank", 0.0)
    hits = hybrid.search(q, rerank=False)
    peer_hits = [h for h in hits if h.entity_id in ("MS", "SCHW")]
    assert hits[0].chunk_id == "EDJ-A#1" and hits[-len(peer_hits):] == peer_hits
    assert sum(h.entity_id == "MS" for h in peer_hits) == 2 and sum(h.entity_id == "SCHW" for h in peer_hits) == 1
    assert all(h.on_theme for h in peer_hits)
    peer_sql = [sql for sql, p in _parts(conn) if "peer_e0" in p]
    assert len(peer_sql) == 2 and all("c.text ~* %(on_theme)s" in sql for sql in peer_sql)


def test_r8_slot_order_flags_reach_select(monkeypatch):
    calls = []
    real = fts.select
    monkeypatch.setattr(fts, "select", lambda pool, k, **kw: calls.append(kw) or real(pool, k, **kw))
    rows = [_row("EDJ-A#1", "EDJ"), _row("R-S#1", None, doc_type="research")]
    _patch(monkeypatch, FakeConn(_leg("EDJ-A#1", entity="EDJ"), [], rows,
                                 research_kw=_leg("R-S#1", entity=None, doc_type="research")))
    hybrid.search(ENTITY_THEME, rerank=False)
    research, firm = calls
    assert research["trade_last"] is False and research["new_doc_first"] is False and research["floor_base"] == 1
    assert "trade_last" not in firm and "new_doc_first" not in firm  # fts.select defaults: trade last, new doc first
    calls.clear()
    _patch(monkeypatch, FakeConn(_leg("RJF-A#1", entity="RJF"), [], [_row("RJF-A#1", "RJF", "2026-08-01")]))
    hybrid.search(WINDOW, rerank=False)
    assert calls[0]["trade_last"] is False and calls[0]["floor"] == 0  # window: as fts mode


def test_r10_date_basis_is_read(monkeypatch):
    row = _row("RJF-WEB#1", "RJF")
    row["date_basis"] = "retrieved"
    _patch(monkeypatch, FakeConn(_leg("RJF-WEB#1", entity="RJF"), [], [row]))
    hits = hybrid.search(Query(question="RJF pay?", entities=["RJF"]), rerank=False)
    assert hits[0].date_basis == "retrieved" and "d.date_basis" in hybrid.ROWS_SQL


@pytest.mark.parametrize("rerank", [True, False])
def test_r11_trace_records_the_pools_and_changes_nothing(monkeypatch, rerank):
    rows = [_row("EDJ-A#1", "EDJ"), _row("EDJ-B#1", "EDJ"), _row("EDJ-T#1", "EDJ"),
            _row("R-S#1", None, doc_type="research")]

    def conn():
        return FakeConn(_leg("EDJ-A#1", "EDJ-B#1", entity="EDJ"), [], rows,
                        research_kw=_leg("R-S#1", entity=None, doc_type="research"),
                        theme_kw=_leg("EDJ-T#1", entity="EDJ"))
    scorer = lambda qq, ps: [float(len(p) % 7) for p in ps]  # noqa: E731
    _patch(monkeypatch, conn())
    plain = hybrid.search(ENTITY_THEME, scorer=scorer, rerank=rerank)
    _patch(monkeypatch, conn())
    trace = PoolTrace()
    traced = hybrid.search(ENTITY_THEME, scorer=scorer, rerank=rerank, trace=trace)
    assert [h.chunk_id for h in traced] == [h.chunk_id for h in plain]
    assert trace.firm == ["EDJ-A#1", "EDJ-B#1"] and trace.on_theme == ["EDJ-T#1"] and trace.research == ["R-S#1"]
    assert trace.ids() >= {h.chunk_id for h in traced}


def test_modes_search_passes_budget_and_trace(monkeypatch):
    seen = []
    monkeypatch.setattr(hybrid, "search", lambda q, k, trace=None, rerank=True: seen.append((k, trace, rerank)) or [])
    monkeypatch.setenv("CEE_VECTORS", "on")
    q = Query(question="x", entities=["EDJ"], themes=["client_segments"], mode="entity+theme", theme_peers=["MS"])
    t = PoolTrace()
    modes.search(q, mode="hybrid-norerank", trace=t)
    assert seen == [(fts.budget(q) - fts.peer_slots(q), t, False)] and seen[0][0] == 20


# --- hard filters against the real database (needs CEE_VECTORS=on and every chunk embedded) -------

def _vectors_ready() -> bool:
    import os
    if os.getenv("CEE_VECTORS", "").strip().lower() != "on":
        return False
    try:
        from cee.db import connect
        with connect() as c:
            if not c.execute("SELECT to_regclass('chunk_embeddings') IS NOT NULL AS ok").fetchone()["ok"]:
                return False
            return c.execute("SELECT count(*) AS n FROM chunks c WHERE NOT EXISTS (SELECT 1 FROM chunk_embeddings e "
                             "WHERE e.chunk_id = c.chunk_id)").fetchone()["n"] == 0
    except Exception:
        return False


@pytest.mark.skipif(not _vectors_ready(), reason="needs CEE_VECTORS=on and chunk_embeddings filled")
@pytest.mark.parametrize("rerank", [False, True])
def test_hard_filters_in_hybrid_mode_on_the_database(rerank):
    if rerank and not hybrid.reranker_cached(hybrid.rerank_model_name()):
        pytest.skip("reranker not cached")
    today = date(2026, 11, 17)
    merrill = fts.resolve("What is Merrill's advisor growth strategy, and how has it changed?", today=today)
    hits = hybrid.search(merrill, rerank=rerank)
    assert hits
    assert all(h.entity_id == "MER" or (h.entity_id == "BAC" and h.segment in ("GWIM", "Merrill")) for h in hits)
    window = fts.resolve("What's new on Raymond James in the last 90 days?", today=today)
    hits = hybrid.search(window, rerank=rerank)
    assert hits
    lo, hi = window.window
    assert all(h.date_basis == "source" and lo.isoformat() <= h.published_at <= hi.isoformat() for h in hits)
    assert all(h.doc_type != "adv" for h in hits)
