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


# --- #214 planner on exp/hybrid: fts plans as main, hybrid modes search the whole question ------

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


def test_hybrid_plan_is_one_whole_question_part_without_a_call(monkeypatch):
    from cee.retrieve import modes, planner
    from cee.retrieve.fts import Query
    monkeypatch.setattr(planner, "plan_question", lambda *a, **k: pytest.fail("no planner in hybrid modes"))
    q = Query(question="Compare MS and RJF", entities=["MS", "RJF"])
    for mode in ("hybrid", "hybrid-norerank"):
        plan = modes.plan_for(q, "anthropic", mode)
        assert [(p.id, p.firms) for p in plan.parts] == [("p1", ["MS", "RJF"])] and plan.calls == 0
