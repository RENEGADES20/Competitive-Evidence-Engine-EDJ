"""Demo mode (#299): the prepared fixture, fuzzy matching, and the Ask page replay (no call to cee.ask.ask)."""
import time

import pytest
from streamlit.testing.v1 import AppTest

from cee.app.demo import replay as R

FX = R.load_fixture()
STATS = {"snapshot": "corpus-2026-11-19", "firms": 5, "docs": 10, "chunks": 100, "latest": "2026-11-01"}


# ---------- the fixture ----------

def test_fixture_has_the_30_questions():
    assert [e["id"] for e in FX["questions"]] == [f"Q{i}" for i in range(1, 31)]
    assert FX["snapshot"] == "corpus-2026-11-19"


@pytest.mark.parametrize("entry", FX["questions"], ids=lambda e: e["id"])
def test_every_citation_resolves_to_a_card(entry):
    assert entry["cards"], "every prepared answer has evidence cards"
    assert R.cited_numbers(entry["answer_md"]), "the answer cites its cards"
    assert R.bad_citations(entry) == []


@pytest.mark.parametrize("entry", FX["questions"], ids=lambda e: e["id"])
def test_every_number_in_the_answer_is_in_the_cards(entry):
    assert R.unmatched_numbers(entry) == []


@pytest.mark.parametrize("entry", FX["questions"], ids=lambda e: e["id"])
def test_replay_takes_five_seconds_or_less(entry):
    from cee.ask import STAGES
    assert [s["stage"] for s in entry["stages"]] == list(STAGES)
    assert sum(s["seconds"] for s in entry["stages"]) <= R.MAX_REPLAY_S


def test_traps_and_gap_questions_keep_their_expected_behavior():
    by_id = {e["id"]: e for e in FX["questions"]}
    for qid in ("Q24", "Q25", "Q28", "Q29", "Q30"):
        assert by_id[qid]["behavior"] == "gap_with_adjacent"
    for qid in ("Q12", "Q19"):
        assert by_id[qid]["behavior"] == "answer_with_boundary"
    assert any("GWIM is not Merrill" in c for c in by_id["Q30"]["caveats"])


def test_number_check_flags_a_figure_not_in_the_cards():
    entry = {"text": "q", "cards": [{"text": "Assets were $4.4 trillion in 2025.", "label": "", "quote": "",
                                     "passage": "", "source_label": ""}],
             "answer_md": "Assets were $4.4 trillion in 2025 [1], up 12% [1].", "caveats": [], "gaps": []}
    assert R.unmatched_numbers(entry) == ["12"]
    assert R.bad_citations({**entry, "answer_md": "x [2]"}) == [2]


# ---------- matching ----------

def test_match_by_id_exact_and_fuzzy():
    q4 = next(e for e in FX["questions"] if e["id"] == "Q4")
    assert R.match("q4", FX)["id"] == "Q4"
    assert R.match(q4["text"], FX)["id"] == "Q4"
    assert R.match("whats merrills advisor growth strategy and how did it change", FX)["id"] == "Q4"
    assert R.match("Merrill standalone profitability", FX)["id"] == "Q30"


def test_no_match_for_an_unprepared_question():
    assert R.match("What is the weather in Paris tomorrow?", FX) is None
    assert R.match("", FX) is None


def test_demo_default_from_query_or_environment(monkeypatch):
    monkeypatch.delenv("CEE_DEMO", raising=False)
    assert R.demo_default({"demo": "1"}) and not R.demo_default({})
    monkeypatch.setenv("CEE_DEMO", "1")
    assert R.demo_default({})


def test_answer_footnotes_link_to_the_cards():
    html = R.answer_html("Fact one [1, 2]. Costs $5 [3].")
    assert 'href="#cee-ev-1"' in html and 'href="#cee-ev-2"' in html and 'href="#cee-ev-3"' in html
    assert "$" not in html


# ---------- the Ask page ----------

def page():
    import streamlit as st

    from cee.app.views import ask_page
    st.session_state.setdefault("demo_mode", True)
    ask_page.render()


@pytest.fixture
def demo_app(monkeypatch):
    from cee import ask as pipeline
    from cee.app import components as ui
    from cee.app.views import ask_page

    def boom(*a, **k):
        raise AssertionError("demo mode must not call cee.ask.ask")
    monkeypatch.setattr(pipeline, "ask", boom)
    monkeypatch.setattr(ask_page, "ask", boom)
    monkeypatch.setattr(ask_page, "ask_with_trace", boom)
    monkeypatch.setattr(ui, "corpus_stats", lambda: STATS)
    return AppTest.from_function(page, default_timeout=30)


def _md(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_pick_and_ask_replays_cards_then_answer(demo_app, monkeypatch):
    monkeypatch.setattr(R, "_sleep", lambda s: None)
    at = demo_app.run()
    assert not at.exception
    assert at.toggle(key="demo_mode").value is True
    at.selectbox(key="demo_pick").select("Q4").run()
    entry = R.match("Q4", FX)
    assert at.text_input(key="demo_question").value == entry["text"]
    at.button[0].click().run()
    assert not at.exception and not at.error
    md = _md(at)
    assert "**Plan:**" in md and 'id="cee-ev-1"' in md and 'href="#cee-ev-1"' in md
    assert f'id="cee-ev-{len(entry["cards"])}"' in md
    assert at.session_state["last_answer_demo"][0] == "Q4"
    assert at.get("status")[0].label.startswith("How this answer was built: 9 steps")
    at.run()   # a rerun redraws the answer from session state, no replay
    assert not at.exception and 'href="#cee-ev-1"' in _md(at) and not at.get("status")


def test_unprepared_question_gets_the_polite_message(demo_app):
    at = demo_app.run()
    at.text_input(key="demo_question").input("What is the weather in Paris tomorrow?").run()
    at.button[0].click().run()
    assert not at.exception
    assert at.info and at.info[0].value == R.NO_MATCH_TEXT
    assert at.session_state["last_answer_demo"] is None


def test_replay_finishes_within_five_seconds(demo_app):
    at = demo_app.run()
    at.text_input(key="demo_question").input("Q30").run()
    t0 = time.perf_counter()
    at.button[0].click().run()
    took = time.perf_counter() - t0
    assert not at.exception
    assert at.session_state["last_answer_demo"][1] <= R.MAX_REPLAY_S
    assert took <= R.MAX_REPLAY_S + 2.0   # AppTest overhead on top of the replay itself


def test_toggle_off_is_the_live_page(monkeypatch):
    from cee.app import components as ui
    monkeypatch.setattr(ui, "corpus_stats", lambda: STATS)

    def live():
        import streamlit as st

        from cee.app.views import ask_page
        st.session_state.setdefault("demo_mode", False)
        ask_page.render()
    at = AppTest.from_function(live).run()
    assert not at.exception
    assert not at.selectbox and at.text_input[0].label == "Question"
    assert "No question yet" in _md(at)


# ---------- the builder (fake client, fake chunk rows: no database, no paid call) ----------

class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Usage:
    input_tokens, output_tokens = 5000, 700


class _Resp:
    stop_reason = "end_turn"
    usage = _Usage()

    def __init__(self, text):
        self.content = [_Block(text)]

    def to_dict(self):
        return {"content": [{"type": "text", "text": self.content[0].text}]}


def test_builder_writes_the_fixture_with_one_call_per_question(monkeypatch, tmp_path):
    import importlib.util
    from pathlib import Path

    from cee.answer import llm
    spec = importlib.util.spec_from_file_location(
        "build_demo_fixture", Path(__file__).resolve().parents[1] / "scripts" / "build_demo_fixture.py")
    B = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(B)

    def rows(ids):
        return {i: {"chunk_id": i, "doc_id": i.split("#")[0], "entity_id": "MS", "segment": None, "doc_type": "10-K",
                    "source_tier": 2, "published_at": "2026-01-01", "period_end": None, "section": "s", "page": None,
                    "text": "Stored passage text.", "date_basis": "source"} for i in ids}
    sent = []

    class Client:
        class messages:
            @staticmethod
            def create(**req):
                sent.append(req)
                return _Resp("In short, the documents say this [1].\n\n### Caveats and gaps\nLittle else [2].")
    monkeypatch.setattr(B, "chunk_rows", rows)
    monkeypatch.setattr(B, "RUN_DIR", tmp_path)
    monkeypatch.setattr(llm, "anthropic_client", lambda: Client())
    out = tmp_path / "fixture.json"
    with pytest.raises(SystemExit):   # the cap is checked before the first call
        B.build("anthropic", None, "demo-t", 29, out)
    assert not sent
    assert B.build("anthropic", None, "demo-t", 30, out) == 0
    assert len(sent) == 30 and {r["model"] for r in sent} == {"claude-opus-5-5"}
    fx = R.load_fixture(out)
    assert len(fx["questions"]) == 30 and fx["model"] == "claude-opus-5-5"
    assert all(len(e["cards"]) <= B.CARD_CAP.get(e["id"], B.MAX_CARDS) for e in fx["questions"])
    assert len(list((tmp_path / "raw").glob("*-demo-t.json"))) == 30
    assert B.build("anthropic", None, "demo-t", 0, out) == 0 and len(sent) == 30   # saved outputs reused
    assert B.build("anthropic", ["Q4"], "demo-u", 1, out) == 0 and len(sent) == 31   # one re-run
