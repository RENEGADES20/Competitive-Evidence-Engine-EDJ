"""Ask page trace: collapsed after the answer, failed stage marked and its error shown (#80)."""
from streamlit.testing.v1 import AppTest

from cee import ask as pipeline
from cee.retrieve.fts import Query


def page():
    from cee.app.views.ask_page import ask_with_trace
    ask_with_trace("What is Merrill's standalone profitability?")


def trace_text(at) -> str:
    return " ".join(m.value for m in at.markdown if "cee-trace" in m.value)


def test_trace_stays_collapsed_after_the_answer(monkeypatch):
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: [])
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 1)
    at = AppTest.from_function(page).run()
    assert not at.exception and not at.error
    box = at.get("status")[0]
    assert box.label.startswith(f"How this answer was built: {len(pipeline.STAGES)} steps")   # #248: 9
    assert "No passages found: no model call" in trace_text(at)


def test_failed_stage_is_marked_and_error_shown(monkeypatch):
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))

    def broken(q, plan, **kw):
        raise RuntimeError("database is down")
    monkeypatch.setattr(pipeline, "search_subquestions", broken)
    at = AppTest.from_function(page).run()
    assert at.get("status")[0].label == "Searching 1 sub-question: failed (RuntimeError: database is down)"
    assert 'class="failed"' in trace_text(at)
    assert "database is down" in at.error[0].value


def test_plan_and_evidence_show_before_the_answer_trace(monkeypatch):
    """#272: the plan line and the evidence cards are drawn during the build (mock, 0 calls)."""
    from tests.test_ask_progress import HITS
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 1)
    at = AppTest.from_function(page).run()
    assert not at.exception and not at.error
    texts = [m.value for m in at.markdown]
    plan_i = next(i for i, t in enumerate(texts) if t.startswith("**Plan:**"))
    ev_i = next(i for i, t in enumerate(texts) if "EVIDENCE - Merrill" in t)
    assert plan_i < ev_i and "BAC-10K-2025#244" in texts[ev_i]
