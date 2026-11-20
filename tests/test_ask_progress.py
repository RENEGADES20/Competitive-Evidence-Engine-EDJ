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
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan: hits)

    def fake_generate(question, h, provider, plan=None, window=None):
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
    monkeypatch.setenv("MAP", "off")   # #247: the legacy single answer call (prompt v4.1)
    result, events, calls = run(monkeypatch, HITS)
    assert events[0] == ("resolve", "running", "Reading the question")   # first line before any work
    order = [stage for stage, state, _ in events if state != "running"]
    assert order == list(pipeline.STAGES[:-1])                             # log=False: no "log" stage
    d = done(events)
    assert d["resolve"] == "Reading the question: firms MER; mode entity"
    assert d["plan"] == "Planning the search (rules, no model call): 1 aspect x 1 firm = 1 sub-question: a1.MER"
    assert d["search"] == "Searching the corpus: 3 passages from 2 documents in 1 sub-question"
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

    def broken(q, plan):
        raise RuntimeError("database is down")
    monkeypatch.setattr(pipeline, "search_subquestions", broken)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", log=False, progress=lambda *e: events.append(e))
    assert events[-1] == ("search", "failed", "Searching the corpus: failed (RuntimeError: database is down)")


def test_no_callback_behaves_as_before(monkeypatch):
    monkeypatch.setattr(pipeline, "generate", lambda q, h, p, plan=None, window=None: Answer(answerable=True, behavior="answer"))
    answer, raw = pipeline.answer_for("q", Query(question="q", entities=["MER"]), HITS, "mock")
    assert raw is not None and answer.behavior == "answer"


def test_failed_query_log_is_its_own_failed_step(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan: [])

    def broken(r, p):
        raise RuntimeError("insert failed")
    monkeypatch.setattr(pipeline, "_log", broken)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", progress=lambda *e: events.append(e))
    assert events[-1] == ("log", "failed", "Saving the query: failed (RuntimeError: insert failed)")


# --- question planner (#214, ADR-020) ---------------------------------------------------------

def test_plan_stage_and_at_most_two_calls(monkeypatch):
    """A real provider: one planner call, one answer call (counting fakes), both logged."""
    from cee.retrieve import planner
    from cee.retrieve.planner import Part, Plan

    calls = []
    monkeypatch.setenv("MAP", "off")   # #247: the legacy single answer call
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MS", "MER"]))

    def fake_plan(query, provider):
        calls.append("planner")
        return Plan.from_parts([Part("p1", "a", ["MS"], "payout grid"), Part("p2", "b", ["MER"], "recruiting")],
                    source="model", provider=provider, calls=1)
    monkeypatch.setattr(pipeline, "plan_question", fake_plan)
    seen = []
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan: seen.append(plan) or HITS)

    def fake_generate(question, h, provider, plan=None, window=None):
        calls.append("answer")
        return Answer(answerable=True, behavior="answer", llm_called=True,
                      claims=[{"text": "a", "chunk_ids": ["BAC-10K-2025#244"]}])
    monkeypatch.setattr(pipeline, "generate", fake_generate)
    events = []
    result = pipeline.ask("q", provider="anthropic", log=False, progress=lambda *e: events.append(e))
    d = done(events)
    assert calls == ["planner", "answer"] and len(calls) <= 2
    assert d["plan"] == "Planning the search (anthropic, one call): 2 aspects x 2 firms = 2 sub-questions: p1 MS; p2 MER"
    assert d["search"].endswith("in 2 sub-questions") and seen[0] is result.plan
    logged = pipeline.log_filters(result)
    assert logged["llm_calls"] == {"planner": 1, "map": 0, "remap": 0, "answer": 1}   # MAP off (#246)
    assert [p["keyword_query"] for p in logged["plan"]["parts"]] == ["payout grid", "recruiting"]
    assert logged["entities"] == ["MS", "MER"]                       # the query fields stay
    assert planner.Plan  # imported module in use


def test_fallback_plan_line(monkeypatch):
    from cee.retrieve.planner import Plan, rules_plan

    q = Query(question="q", entities=["MS", "MER"])
    plan = rules_plan(q)
    plan.source, plan.provider, plan.error, plan.calls = "fallback", "anthropic", "planner output cut at max_tokens", 1
    assert pipeline.plan_text(plan) == ("Planning the search (anthropic, one call): output not usable (planner "
                                        "output cut at max_tokens), using the rule plan: 1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.MER")
    assert isinstance(plan, Plan)


def test_mock_logs_zero_calls(monkeypatch):
    result, events, calls = run(monkeypatch, HITS)
    logged = pipeline.log_filters(result)
    assert logged["llm_calls"] == {"planner": 0, "map": 0, "remap": 0, "answer": 0} and logged["plan"]["source"] == "rules"


def test_map_off_is_the_legacy_single_call(monkeypatch):
    """#247 (TL D3): MAP=off keeps the legacy v4.1 answer call: no extraction, logged off."""
    import cee.answer.extract as extract
    monkeypatch.setenv("MAP", "off")
    monkeypatch.setattr(extract, "run_map", lambda *a, **k: pytest.fail("map ran"))
    result, events, calls = run(monkeypatch, HITS)
    assert ("map", "skipped", "Map step off (MAP=off): no extraction calls; legacy single answer call") in events
    assert result.matrix is None and pipeline.log_filters(result)["map"] == {"off": True} and calls == ["mock"]


def test_map_and_reduce_run_by_default_on_the_mock(monkeypatch):
    """#247: MAP on by default: the matrix, then the mock reduce (0 paid calls), no legacy call."""
    result, events, calls = run(monkeypatch, HITS)
    d = done(events)
    assert d["map"] == ("Extracting per firm (mock, no model call): 1 cell: 1 fact; behavior by code: answer")
    assert d["model"] == ("Asking the model to write the answer from the evidence matrix (mock, one call): 1 claim")
    assert calls == []                                       # the legacy generate() is not called
    logged = pipeline.log_filters(result)
    assert logged["map"]["behavior"] == "answer" and logged["map"]["cells"]["a1.MER"]["label"] == "fact"
    assert logged["llm_calls"] == {"planner": 0, "map": 0, "remap": 0, "answer": 0}   # the mock is not a paid call
    assert logged["reduce"]["version"] == "v5" and logged["reduce"]["outside_matrix"] == 0
    assert result.answer.behavior == "answer" and result.answer.claims[0].part_id == "a1.MER"
    assert result.answer.claims[0].chunk_ids == ["BAC-10K-2025#244"] and not result.answer.claims[0].flags


def test_corrective_hits_join_the_answer_hits_and_the_log(monkeypatch):
    """#247 B1: a claim citing a corrective re-search hit is linked, unflagged and logged."""
    from dataclasses import replace

    import cee.answer.extract as extract
    from cee.answer.matrix import Cell, EvidenceMatrix, Item, finish
    from cee.retrieve.planner import Aspect

    new = replace(hit("BAC-10Q-2026Q3#9", "BAC-10Q-2026Q3"), part_id="a1.MER", origin="corrective")

    def fake_map(q, plan, hits, provider, as_of=None):
        a = Aspect("a1", "Merrill profitability.")
        m = EvidenceMatrix(q.question, rows=["MER"], aspects=[a], cells={"a1.MER": Cell(
            "a1.MER", "MER", "a1", "named", "fact", items=[Item("t", "q", ["BAC-10Q-2026Q3#9"])])})
        m.hits = {h.chunk_id: h for h in [*hits, new]}
        m.corrective = [new]
        return finish(m, q, [*hits, new])
    monkeypatch.setattr(extract, "run_map", fake_map)
    result, events, calls = run(monkeypatch, HITS)
    assert [h.chunk_id for h in result.hits] == [*(h.chunk_id for h in HITS), "BAC-10Q-2026Q3#9"]
    c = result.answer.claims[0]
    assert c.chunk_ids == ["BAC-10Q-2026Q3#9"] and not c.flags and c.source_label
    logged = pipeline.log_filters(result)
    assert logged["chunk_origin"] == {"BAC-10Q-2026Q3#9": {"origin": "corrective", "subquestion": "a1.MER"}}