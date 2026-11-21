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
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: hits)

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
    assert d["decompose"] == "Decomposing the question (rules, no model call): 1 aspect x 1 firm = 1 sub-question: a1.MER"
    assert d["search"] == "Searching 1 sub-question: 3 passages from 2 documents"
    assert d["extract"] == "Map step off (MAP=off): no extraction calls; legacy single answer call"
    assert d["research"] == "Re-search: map step off (MAP=off)"
    assert d["synthesize"] == "Writing the answer (mock, one legacy call): 2 claims"
    assert d["check"] == "Checking citations: 2 citations matched, 1 claim flagged"
    assert d["caveats"] == "Adding caveats and gaps: 0 caveats, 0 gaps"
    assert calls == ["mock"]                                                # exactly one model call


def test_no_passages_skips_the_model(monkeypatch):
    result, events, calls = run(monkeypatch, [])
    assert calls == []
    assert ("synthesize", "skipped", "No passages found: no model call") in events
    assert ("extract", "skipped", "No passages found: no extraction call") in events
    assert ("research", "skipped", "Re-search: no passages found") in events
    assert done(events)["caveats"] == "Adding caveats and gaps: 0 caveats, 1 gap"
    assert not result.answer.llm_called


def test_failed_stage_is_reported_then_raised(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))

    def broken(q, plan, **kw):
        raise RuntimeError("database is down")
    monkeypatch.setattr(pipeline, "search_subquestions", broken)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", log=False, progress=lambda *e: events.append(e))
    assert events[-1] == ("search", "failed", "Searching 1 sub-question: failed (RuntimeError: database is down)")


def test_no_callback_behaves_as_before(monkeypatch):
    monkeypatch.setattr(pipeline, "generate", lambda q, h, p, plan=None, window=None: Answer(answerable=True, behavior="answer"))
    answer, raw = pipeline.answer_for("q", Query(question="q", entities=["MER"]), HITS, "mock")
    assert raw is not None and answer.behavior == "answer"


def test_failed_query_log_is_its_own_failed_step(monkeypatch):
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: [])

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
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: seen.append(plan) or HITS)

    def fake_generate(question, h, provider, plan=None, window=None):
        calls.append("answer")
        return Answer(answerable=True, behavior="answer", llm_called=True,
                      claims=[{"text": "a", "chunk_ids": ["BAC-10K-2025#244"]}])
    monkeypatch.setattr(pipeline, "generate", fake_generate)
    events = []
    result = pipeline.ask("q", provider="anthropic", log=False, progress=lambda *e: events.append(e))
    d = done(events)
    assert calls == ["planner", "answer"] and len(calls) <= 2
    assert d["decompose"] == "Decomposing the question (anthropic, one call): 2 aspects x 2 firms = 2 sub-questions: p1 MS; p2 MER"
    assert d["search"].startswith("Searching 2 sub-questions: ") and seen[0] is result.plan
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
    assert pipeline.plan_text(plan) == ("Decomposing the question (anthropic, one call): output not usable (planner "
                                        "output cut at max_tokens), using the rule plan: 1 aspect x 2 firms = 2 sub-questions: a1.MS; a1.MER")
    assert isinstance(plan, Plan)


def test_mock_logs_zero_calls(monkeypatch):
    result, events, calls = run(monkeypatch, HITS)
    logged = pipeline.log_filters(result)
    assert logged["llm_calls"] == {"planner": 0, "map": 0, "remap": 0, "answer": 0} and logged["plan"]["source"] == "rules"
    assert logged["cost"]["calls"] == 0 and logged["cost"]["usd"] == 0 and logged["cost"]["rows"] == []   # #248


def test_map_off_is_the_legacy_single_call(monkeypatch):
    """#247 (TL D3): MAP=off keeps the legacy v4.1 answer call: no extraction, logged off."""
    import cee.answer.extract as extract
    monkeypatch.setenv("MAP", "off")
    monkeypatch.setattr(extract, "run_map", lambda *a, **k: pytest.fail("map ran"))
    result, events, calls = run(monkeypatch, HITS)
    assert ("extract", "skipped", "Map step off (MAP=off): no extraction calls; legacy single answer call") in events
    assert result.matrix is None and pipeline.log_filters(result)["map"] == {"off": True} and calls == ["mock"]


def test_map_and_reduce_run_by_default_on_the_mock(monkeypatch):
    """#247: MAP on by default: the matrix, then the mock reduce (0 paid calls), no legacy call."""
    result, events, calls = run(monkeypatch, HITS)
    d = done(events)
    assert d["extract"] == ("Extracting from 1 firm (mock, no model call): 1 cell: 1 fact; behavior by code: answer")
    assert d["research"] == "Re-search: every sub-question has evidence; nothing re-searched"
    assert d["synthesize"] == ("Synthesizing the answer from the evidence matrix (mock, one call): 1 claim")
    assert list(d) == list(pipeline.STAGES[:-1])   # #248: extract is reported done twice (round 1, final)
    assert calls == []                                       # the legacy generate() is not called
    logged = pipeline.log_filters(result)
    assert logged["map"]["behavior"] == "answer" and logged["map"]["cells"]["a1.MER"]["label"] == "fact"
    assert logged["llm_calls"] == {"planner": 0, "map": 0, "remap": 0, "answer": 0}   # the mock is not a paid call
    assert logged["reduce"]["version"] == "v5.2" and logged["reduce"]["outside_matrix"] == 0
    assert result.answer.behavior == "answer" and result.answer.claims[0].part_id == "a1.MER"
    assert result.answer.claims[0].chunk_ids == ["BAC-10K-2025#244"] and not result.answer.claims[0].flags


def test_corrective_hits_join_the_answer_hits_and_the_log(monkeypatch):
    """#247 B1: a claim citing a corrective re-search hit is linked, unflagged and logged."""
    from dataclasses import replace

    import cee.answer.extract as extract
    from cee.answer.matrix import Cell, EvidenceMatrix, Item, finish
    from cee.retrieve.planner import Aspect

    new = replace(hit("BAC-10Q-2026Q3#9", "BAC-10Q-2026Q3"), part_id="a1.MER", origin="corrective")

    def fake_map(q, plan, hits, provider, as_of=None, on_research=None, on_call=None):
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

# --- #248: the re-search stage and the logged cost --------------------------------------------

def _research_matrix(q, hits, provider):
    from cee.answer.matrix import Cell, EvidenceMatrix, finish
    from cee.retrieve.planner import Aspect
    m = EvidenceMatrix(q.question, rows=["MER"], aspects=[Aspect("a1", "Merrill profitability.")],
                       cells={"a1.MER": Cell("a1.MER", "MER", "a1", "named", "not_found")},
                       calls=[{"id": "map.MER", "round": 1, "provider": provider, "usage": None},
                              {"id": "remap.MER", "round": 2, "provider": provider, "usage": None}],
                       research=[{"id": "a1.MER", "words": ["x"], "hits": 2, "chunk_ids": ["A#1", "A#2"]}])
    return finish(m, q, hits)


def test_research_stage_runs_between_extract_and_synthesize(monkeypatch):
    import cee.answer.extract as extract
    seen = []

    def fake_map(q, plan, hits, provider, as_of=None, on_research=None, on_call=None):
        on_research()
        seen.append("research started")
        return _research_matrix(q, hits, provider)
    monkeypatch.setattr(extract, "run_map", fake_map)
    result, events, calls = run(monkeypatch, HITS)
    i = events.index(("extract", "done", "Extracting from 1 firm: round 1 done"))
    assert events[i + 1] == ("research", "running", "Re-searching sub-questions with no evidence")
    d = done(events)
    assert d["research"] == ("Re-searching sub-questions with no evidence: 1 re-searched, 1 with new passages, "
                             "1 re-extraction (mock, no model call)")
    assert d["extract"].startswith("Extracting from 1 firm (mock, no model call): 1 cell")
    assert seen == ["research started"]


def test_a_failing_re_search_marks_the_research_stage(monkeypatch):
    import cee.answer.extract as extract
    events = []
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)

    def fake_map(q, plan, hits, provider, as_of=None, on_research=None, on_call=None):
        on_research()
        raise RuntimeError("search down")
    monkeypatch.setattr(extract, "run_map", fake_map)
    with pytest.raises(RuntimeError):
        pipeline.ask("q", provider="mock", log=False, progress=lambda *e: events.append(e))
    assert events[-1] == ("research", "failed",
                          "Re-searching sub-questions with no evidence: failed (RuntimeError: search down)")


def test_real_calls_are_logged_with_tokens_and_cost(monkeypatch):
    """#248: the planner and the (legacy) answer call of a real provider are priced from their usage
    and offset-aware completion times (anthropic: flat $2 / $10 per 1M)."""
    from cee.retrieve.planner import Part, Plan
    monkeypatch.setenv("MAP", "off")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5-5")
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))

    def fake_plan(query, provider):
        return Plan.from_parts([Part("p1", "a", ["MER"], "x")], source="model", provider=provider,
                               model="claude-sonnet-5-5", calls=1,
                               usage={"input_tokens": 100_000, "output_tokens": 10_000},
                               finished_at="2026-11-20T02:00:00+00:00")
    monkeypatch.setattr(pipeline, "plan_question", fake_plan)
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    monkeypatch.setattr(pipeline, "generate", lambda *a, **k: Answer(
        answerable=True, behavior="answer", llm_called=True, usage={"input_tokens": 500_000, "output_tokens": 50_000},
        claims=[{"text": "a", "chunk_ids": ["BAC-10K-2025#244"]}]))
    result = pipeline.ask("q", provider="anthropic", log=False)
    cost = pipeline.log_filters(result)["cost"]
    assert cost["by_type"]["plan"] == 1 and cost["by_type"]["answer"] == 1 and cost["calls"] == 2
    assert cost["input_tokens"] == 600_000 and cost["output_tokens"] == 60_000
    assert cost["usd"] == pytest.approx(0.2 + 0.1 + 1.0 + 0.5) and cost["new"] == 2
    assert all(r["period"] == "flat" and r["tz"] == "record offset" for r in cost["rows"])


# --- #272: progressive Ask page events ------------------------------------------------------------

def test_plan_then_evidence_events_in_order(monkeypatch):
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    seen = []
    result = pipeline.ask("Merrill profitability?", provider="mock", log=False,
                          progress=lambda s, st, t: seen.append(("stage", s, st)),
                          on_event=lambda kind, data: seen.append((kind, data)))
    kinds = [e[0] for e in seen if e[0] in ("plan", "evidence")]
    assert kinds == ["plan", "evidence"]
    plan_at = next(i for i, e in enumerate(seen) if e[0] == "plan")
    ev_at = next(i for i, e in enumerate(seen) if e[0] == "evidence")
    synth_at = next(i for i, e in enumerate(seen) if e[:2] == ("stage", "synthesize"))
    assert plan_at < ev_at < synth_at                                     # plan, evidence, then the answer
    assert seen[plan_at][1]["text"].startswith("Decomposing the question (rules, no model call)")
    lines = seen[ev_at][1]["lines"]
    assert seen[ev_at][1]["call"] == "map.a1.MER" and len(lines) == 1
    assert lines[0]["chunk_ids"] == ["BAC-10K-2025#244"] and lines[0]["hits"][0].chunk_id == "BAC-10K-2025#244"
    assert result.answer.behavior == "answer"


def test_evidence_lines_only_cite_checked_retrieved_chunks():
    from cee.answer.extract import CellSpec, MapSpec
    from cee.answer.matrix import Cell, Item
    h = HITS[0]
    spec = MapSpec("map.a1.MER", 1, "MER", False, [CellSpec("a1.MER", "MER", None, "named", "t")],
                   {"a1.MER": [h]}, {"a1.MER": {h.chunk_id}})
    fact = Cell("a1.MER", "MER", "a1", "named", "fact", items=[
        Item("cited", "q", [h.chunk_id]),
        Item("rejected only", "q", [], rejected_ids=["NOT-RETRIEVED#1"])])
    nf = Cell("a2.MER", "MER", "a2", "named", "not_found")
    lines = pipeline.evidence_lines(spec, [fact, nf])
    assert [(x["text"], x["chunk_ids"]) for x in lines] == [("cited", [h.chunk_id])]
