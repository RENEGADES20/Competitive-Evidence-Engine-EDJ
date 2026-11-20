"""Search mode switch (#128): plain labels, default from RETRIEVAL_MODE, no internal words in the UI."""
import re

import pytest

from cee.app.views import ask_page
from cee.app.views.ask_page import MODE_HELP, MODE_LABELS, SMART_OFF, default_mode, mode_label


@pytest.mark.parametrize("env, want", [("fts", "fts"), ("hybrid", "hybrid"), ("hybrid-norerank", "hybrid")])
def test_default_follows_retrieval_mode(env, want, monkeypatch):
    monkeypatch.setattr(ask_page, "settings", lambda: type("S", (), {"retrieval_mode": env})())
    assert default_mode() == want


def test_only_two_modes_offered():
    assert list(MODE_LABELS) == ["fts", "hybrid"]


def test_labels_are_plain():
    assert (mode_label("fts"), mode_label("hybrid"), mode_label("hybrid-norerank")) == (
        "Exact match", "Smart search", "Smart search")


def test_no_internal_words_in_ui_text():
    text = " ".join([*MODE_LABELS.values(), *MODE_HELP.values(), SMART_OFF])
    assert not re.search(r"hybrid|rerank|\bFTS\b|vector", text, re.IGNORECASE)


# --- #245 / #249 sub-questions on exp/hybrid: every mode runs main's loop; hybrid passes its search ----

def _loop_spy(monkeypatch):
    from cee.retrieve import planner
    seen = []
    monkeypatch.setattr(planner, "search_subquestions", lambda q, p, **kw: seen.append((p, kw)) or [])
    return seen


def test_fts_with_a_plan_is_mains_search_subquestions(monkeypatch):
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    q = Query(question="q", entities=["MS", "RJF"])
    plan, seen, pools = planner.rules_plan(q), _loop_spy(monkeypatch), {}
    assert modes.search(q, mode="fts", plan=plan, part_pools=pools, as_of="d") == []
    # main's defaults: no search_fn / research_fn / pin_fn passed
    assert seen == [(plan, {"trace": None, "part_pools": pools, "as_of": "d"})]
    assert modes.search_fn("fts") is None


@pytest.mark.parametrize("mode, rerank", [("hybrid-norerank", False), ("hybrid", True)])
def test_hybrid_with_a_plan_passes_hybrid_search_to_the_shared_loop(monkeypatch, mode, rerank):
    import cee.db
    from cee.retrieve import fts, hybrid, modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setenv("CEE_VECTORS", "on")
    checks = []
    monkeypatch.setattr(cee.db, "connect", lambda: type("C", (), {"__enter__": lambda s: s,
                                                                  "__exit__": lambda s, *a: False})())
    monkeypatch.setattr(hybrid, "check_vectors", lambda conn: checks.append(1))
    q = Query(question="q", entities=["MS", "RJF"])
    plan, seen, pools = planner.rules_plan(q), _loop_spy(monkeypatch), {}
    modes.search(q, mode=mode, plan=plan, part_pools=pools, as_of="d")
    (p, kw), = seen
    assert p is plan and kw["part_pools"] is pools and kw["as_of"] == "d" and checks == [1]
    assert kw["pin_fn"] is fts.fetch_pinned   # registered chunks by id, the same in every mode (gap 2)
    for name, fn in (("search_fn", hybrid.search), ("research_fn", hybrid.research_pass)):
        assert kw[name].func is fn and kw[name].keywords == {"rerank": rerank, "checked": True}
    sf = modes.search_fn(mode)   # the map's corrective re-search
    assert sf.func is hybrid.search and sf.keywords == {"rerank": rerank, "checked": False}


def test_hybrid_with_an_explicit_k_is_one_search(monkeypatch):
    from cee.retrieve import hybrid, modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setenv("CEE_VECTORS", "on")
    seen = []
    monkeypatch.setattr(hybrid, "search", lambda q, k, trace=None, rerank=True: seen.append((k, rerank)) or [])
    q = Query(question="q", entities=["MS"])
    modes.search(q, k=12, mode="hybrid-norerank", plan=planner.rules_plan(q))   # passage rule
    assert seen == [(12, False)]


def test_hybrid_with_vectors_off_raises_before_import(monkeypatch):
    import sys
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setenv("CEE_VECTORS", "off")
    monkeypatch.setitem(sys.modules, "cee.retrieve.hybrid", None)
    q = Query(question="q", entities=["MS"])
    with pytest.raises(modes.HybridUnavailable):
        modes.search(q, mode="hybrid-norerank", plan=planner.rules_plan(q))
    with pytest.raises(modes.HybridUnavailable):
        modes.search_fn("hybrid")