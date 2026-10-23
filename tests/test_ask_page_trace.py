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
    monkeypatch.setattr(pipeline, "search", lambda q: [])
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 1)
    at = AppTest.from_function(page).run()
    assert not at.exception and not at.error
    box = at.get("status")[0]
    assert box.label.startswith("How this answer was built: 6 steps")
    assert "No passages found: no model call" in trace_text(at)


def test_failed_stage_is_marked_and_error_shown(monkeypatch):
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))

    def broken(q):
        raise RuntimeError("database is down")
    monkeypatch.setattr(pipeline, "search", broken)
    at = AppTest.from_function(page).run()
    assert at.get("status")[0].label == "Searching the corpus: failed (RuntimeError: database is down)"
    assert 'class="failed"' in trace_text(at)
    assert "database is down" in at.error[0].value
