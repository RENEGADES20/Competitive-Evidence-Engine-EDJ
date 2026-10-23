"""The Ask trace reports what each stage really did, and adds no model call (#80)."""
import pytest

from cee import ask as pipeline
from cee.answer.schema import Answer
from cee.retrieve.fts import Hit, Query


def hit(cid: str, doc: str) -> Hit:
    return Hit(chunk_id=cid, doc_id=doc, entity_id="MER", segment="GWIM", doc_type="10-K", source_tier=2,
               published_at="2026-02-25", period_end="2025-12-31", section="Item 7", page=None, rank=1.0,
               text="Net income for GWIM increased.")


HITS = [hit("BAC-10K-2025#244", "BAC-10K-2025"), hit("BAC-10K-2025#246", "BAC-10K-2025"),
        hit("BAC-10Q-2026Q2#85", "BAC-10Q-2026Q2")]


def run(monkeypatch, hits, generate=None):
    calls, events = [], []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search", lambda q: hits)

    def fake_generate(question, h, provider):
        calls.append(provider)
        return Answer(answerable=True, behavior="answer", claims=[
            {"text": "a", "chunk_ids": ["BAC-10K-2025#244"]},
            {"text": "b", "chunk_ids": ["BAC-10K-2025#246", "NOT-RETRIEVED#1"]}])
    monkeypatch.setattr(pipeline, "generate", generate or fake_generate)
    result = pipeline.ask("Merrill profitability?", provider="mock", log=False,
                          progress=lambda *e: events.append(e))
    return result, events, calls


def done(events):
    return {stage: text for stage, state, text in events if state != "running"}


def test_stages_in_order_with_facts_from_their_output(monkeypatch):
    result, events, calls = run(monkeypatch, HITS)
    assert events[0] == ("resolve", "running", "Reading the question")   # first line before any work
    order = [stage for stage, state, _ in events if state != "running"]
    assert order == list(pipeline.STAGES[:-1])                             # log=False: no "log" stage
    d = done(events)
    assert d["resolve"] == "Reading the question: firms MER; mode entity"
    assert d["search"] == "Searching the corpus: 3 passages from 2 documents"
    assert d["model"] == "Asking the model (mock, one call): 2 claims"
    assert d["check"] == "Checking citations: 2 citations matched, 1 claim flagged"
    assert d["caveats"] == "Adding caveats and gaps: 0 caveats, 0 gaps"
    assert calls == ["mock"]                                                # exactly one model call


def test_no_passages_skips_the_model(monkeypatch):
    result, events, calls = run(monkeypatch, [])
    assert calls == []
    assert ("model", "skipped", "No passages found: no model call") in events
    assert done(events)["caveats"] == "Adding caveats and gaps: 0 caveats, 1 gap"
    assert not result.answer.llm_called


def test_failed_stage_is_reported_then_raised(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))

    def broken(q):
        raise RuntimeError("database is down")
    monkeypatch.setattr(pipeline, "search", broken)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", log=False, progress=lambda *e: events.append(e))
    assert events[-1] == ("search", "failed", "Searching the corpus: failed (RuntimeError: database is down)")


def test_no_callback_behaves_as_before(monkeypatch):
    monkeypatch.setattr(pipeline, "generate", lambda q, h, p: Answer(answerable=True, behavior="answer"))
    answer, raw = pipeline.answer_for("q", Query(question="q", entities=["MER"]), HITS, "mock")
    assert raw is not None and answer.behavior == "answer"


def test_failed_query_log_is_its_own_failed_step(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search", lambda q: [])

    def broken(r, p):
        raise RuntimeError("insert failed")
    monkeypatch.setattr(pipeline, "_log", broken)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", progress=lambda *e: events.append(e))
    assert events[-1] == ("log", "failed", "Saving the query: failed (RuntimeError: insert failed)")
