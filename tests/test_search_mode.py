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


# --- #214 / #240 planner on exp/hybrid: every mode plans as main; hybrid searches the parts ----

def test_fts_with_a_plan_is_mains_search_parts(monkeypatch):
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    plan = planner.Plan(parts=[planner.Part("p1", "q", ["MS"]), planner.Part("p2", "q", ["RJF"])])
    seen = []
    monkeypatch.setattr(planner, "search_parts",
                        lambda q, p, trace=None, part_pools=None: seen.append((p, part_pools)) or [])
    pools = {}
    assert modes.search(Query(question="q", entities=["MS", "RJF"]), mode="fts", plan=plan, part_pools=pools) == []
    assert seen == [(plan, pools)]


def test_every_mode_plans_with_the_planner(monkeypatch):
    # #240 (T1): plan_for calls planner.plan_question with the same arguments in every mode
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    seen = []
    monkeypatch.setattr(planner, "plan_question", lambda q, provider=None: seen.append((q, provider)) or "plan")
    q = Query(question="Compare MS and RJF", entities=["MS", "RJF"])
    assert [modes.plan_for(q, "anthropic", m) for m in ("fts", "hybrid", "HYBRID-NORERANK")] == ["plan"] * 3
    assert seen == [(q, "anthropic")] * 3
    with pytest.raises(ValueError, match="unknown retrieval mode"):
        modes.plan_for(q, "anthropic", "vector")


def test_hybrid_with_a_plan_is_hybrid_search_parts(monkeypatch):
    # #240 (T2): a plan and k None -> hybrid.search_parts with the plan, rerank by mode and the pools
    from cee.retrieve import hybrid, modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setenv("CEE_VECTORS", "on")
    plan = planner.Plan(parts=[planner.Part("p1", "q", ["MS"]), planner.Part("p2", "q", ["RJF"])])
    seen = []
    monkeypatch.setattr(hybrid, "search_parts", lambda q, p, rerank=True, trace=None, part_pools=None:
                        seen.append((p, rerank, part_pools)) or [])
    monkeypatch.setattr(hybrid, "search", lambda q, k, trace=None, rerank=True: seen.append(("search", k, rerank)) or [])
    pools = {}
    q = Query(question="q", entities=["MS", "RJF"])
    modes.search(q, mode="hybrid-norerank", plan=plan, part_pools=pools)
    modes.search(q, mode="hybrid", plan=plan, part_pools=pools)
    modes.search(q, k=12, mode="hybrid-norerank", plan=plan)   # explicit k: one search, passage rule
    assert seen == [(plan, False, pools), (plan, True, pools), ("search", 12, False)]


def test_hybrid_with_vectors_off_raises_before_import(monkeypatch):
    import sys
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setenv("CEE_VECTORS", "off")
    monkeypatch.setitem(sys.modules, "cee.retrieve.hybrid", None)
    plan = planner.Plan(parts=[planner.Part("p1", "q", ["MS"])])
    with pytest.raises(modes.HybridUnavailable):
        modes.search(Query(question="q", entities=["MS"]), mode="hybrid-norerank", plan=plan)