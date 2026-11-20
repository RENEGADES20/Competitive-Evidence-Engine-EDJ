"""Interim answer input guard (#245; temporary until #247 wires the reduce step): the one answer
call reads every sub-question's passages unless their estimated input passes the model's limit;
then code keeps research first, then round-robin over the sub-questions, best rank first, and says
so (trace, coverage note, log). No database, no paid call."""
import pytest

from cee import ask as pipeline
from cee.answer import llm
from cee.answer.schema import Answer
from cee.answer.validate import GUARD_NOTE, fit_input
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Part, Plan


def h(cid, part, rank, n=400, entity="MS"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-02-19", period_end="2025-12-31", section="Item 7", page=None,
               rank=rank, text="word " * n, part_id=part)


PLAN = Plan.from_parts([Part("a1.MS", "Morgan Stanley: pay", ["MS"]), Part("a1.RJF", "Raymond James: pay", ["RJF"])])
HITS = [h("MS-A#0", "a1.MS", 9), h("MS-A#1", "a1.MS", 8), h("MS-A#2", "a1.MS", 7),
        h("RJF-A#0", "a1.RJF", 5, entity="RJF"), h("RJF-A#1", "a1.RJF", 4, entity="RJF"),
        h("SURVEY#0", "research", 1, entity=None)]
QUERY = Query(question="q", entities=["MS", "RJF"])


def test_fit_input_research_first_then_round_robin_best_rank_first():
    cost = lambda x: 100  # noqa: E731
    kept, dropped = fit_input(HITS, PLAN, limit=350, base=0, cost=cost)
    assert [x.chunk_id for x in kept] == ["MS-A#0", "RJF-A#0", "SURVEY#0"]       # original order kept
    assert dropped == ["MS-A#1", "MS-A#2", "RJF-A#1"]
    kept, _ = fit_input(HITS, PLAN, limit=10_000, base=0, cost=cost)
    assert len(kept) == len(HITS)


def test_fit_input_skips_a_passage_that_does_not_fit_and_goes_on():
    costs = {"MS-A#0": 50, "MS-A#1": 500, "MS-A#2": 50, "RJF-A#0": 50, "RJF-A#1": 50, "SURVEY#0": 50}
    kept, dropped = fit_input(HITS, PLAN, limit=260, base=0, cost=lambda x: costs[x.chunk_id])
    assert "MS-A#1" in dropped and {"MS-A#2", "RJF-A#1"} <= {x.chunk_id for x in kept}


@pytest.fixture
def model(monkeypatch):
    seen = []

    def generate(question, hits, provider, plan=None, window=None):
        seen.append([x.chunk_id for x in hits])
        return Answer(answerable=True, behavior="answer", llm_called=True,
                      claims=[{"text": "a", "chunk_ids": ["MS-A#0"], "part_id": "a1.MS"},
                              {"text": "b", "chunk_ids": ["MS-A#2"], "part_id": "a1.MS"}])
    monkeypatch.setattr(pipeline, "generate", generate)
    return seen


def test_no_trim_under_the_limit(model, monkeypatch):
    monkeypatch.setenv("ANSWER_INPUT_MAX_TOKENS", "900000")
    guard: dict = {}
    answer, _ = pipeline.answer_for("q", QUERY, HITS, "anthropic", plan=PLAN, guard=guard)
    assert model[-1] == [x.chunk_id for x in HITS] and guard == {}
    assert "trimmed" not in (answer.coverage_note or "")
    assert not any(c.flags for c in answer.claims)


def test_mock_has_no_guard_by_default():
    assert llm.answer_input_limit("mock") is None
    assert pipeline.guard_input("q", QUERY, HITS, "mock", PLAN) == (HITS, None)


def test_default_limit_is_the_context_window_minus_cap_and_overhead():
    lim = llm.answer_input_limit("deepseek")
    assert lim % 1000 == 0 and 900_000 < lim < 1_000_000 - llm.answer_max_tokens("deepseek")


def test_trim_over_the_limit_is_logged_noted_and_checked(model, monkeypatch):
    base = llm.input_tokens("q", [], PLAN)
    one = llm.chunk_tokens(HITS[0])
    monkeypatch.setenv("ANSWER_INPUT_MAX_TOKENS", str(int(base + 3 * one + 5)))
    events, guard = [], {}
    trace = pipeline._Trace(lambda *e: events.append(e))
    answer, raw = pipeline.answer_for("q", QUERY, HITS, "anthropic", plan=PLAN, trace=trace, guard=guard)
    assert model[-1] == ["MS-A#0", "RJF-A#0", "SURVEY#0"]                        # research + round-robin
    assert guard["kept"] == 3 and guard["total"] == 6 and guard["after"] <= guard["limit"] < guard["before"]
    assert set(guard["dropped"]) == {"MS-A#1", "MS-A#2", "RJF-A#1"}
    done = {s: t for s, st, t in events if st == "done"}
    assert "input over the model's limit: kept 3 of 6 passages" in done["model"]
    assert GUARD_NOTE.format(kept=3, total=6) in answer.coverage_note
    flagged = [c for c in answer.claims if c.chunk_ids == ["MS-A#2"]][0]
    assert flagged.flags                                                         # dropped: not in what it read


def test_ask_logs_the_trim_and_keeps_the_full_retrieved_list(model, monkeypatch):
    base = llm.input_tokens("q", [], PLAN)
    monkeypatch.setenv("ANSWER_INPUT_MAX_TOKENS", str(int(base + 3 * llm.chunk_tokens(HITS[0]) + 5)))
    monkeypatch.setattr(pipeline, "resolve", lambda q: QUERY)
    monkeypatch.setattr(pipeline, "plan_question", lambda q, p: PLAN)
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan: list(HITS))
    result = pipeline.ask("q", provider="anthropic", log=False)
    assert [x.chunk_id for x in result.hits] == [x.chunk_id for x in HITS]          # retrieval: full list
    logged = pipeline.log_filters(result)
    assert logged["input_guard"]["kept"] == 3 and len(logged["input_guard"]["dropped"]) == 3
    monkeypatch.setenv("ANSWER_INPUT_MAX_TOKENS", "900000")
    assert "input_guard" not in pipeline.log_filters(pipeline.ask("q", provider="anthropic", log=False))
