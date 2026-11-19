"""Question planner (#214, ADR-020): rule plan, code validation of a model plan, provider calls
with fake clients, fallback. No database, never a real API call."""
import json
import re
from datetime import date
from types import SimpleNamespace

import pytest

from cee.retrieve import fts, planner
from cee.retrieve.fts import Query, resolve
from tests.test_prompt import _leaks

TODAY = date(2026, 11, 17)
Q7 = "How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?"
Q28 = "What is Edward Jones's advisor attrition rate compared to Merrill's?"
FIVE = "Client assets per advisor across the five -- and is that comparison even valid?"


def q7() -> Query:
    return resolve(Q7, TODAY)


# --- rule plan --------------------------------------------------------------------------------

def test_rule_plan_one_part_per_named_firm():
    plan = planner.rules_plan(q7(), cap=4)
    assert [(p.id, p.firms, p.keyword_query) for p in plan.parts] == [
        ("p1", ["MS"], None), ("p2", ["MER"], None), ("p3", ["RJF"], None)]
    assert plan.source == "rules" and plan.calls == 0


@pytest.mark.parametrize("question, firms", [
    ("What is Schwab's strategy for its RIA custody business?", ["SCHW"]),    # one firm
    ("What will receiving financial advice in the future look like for clients?", []),  # theme
    (FIVE, ["MS", "SCHW", "EDJ", "MER", "RJF"]),                              # more firms than the cap
])
def test_rule_plan_whole_question_part(question, firms):
    plan = planner.rules_plan(resolve(question, TODAY), cap=4)
    assert [(p.id, p.text, p.firms, p.keyword_query) for p in plan.parts] == [("p1", question, firms, None)]


def test_mock_and_planner_off_make_no_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("no call expected")
    monkeypatch.setattr(planner, "call_planner", boom)
    assert planner.plan_question(q7(), "mock").calls == 0
    monkeypatch.setenv("PLANNER", "off")
    plan = planner.plan_question(q7(), "anthropic")
    assert plan.source == "rules" and plan.calls == 0


def test_no_planner_call_when_code_skips_search(monkeypatch):
    monkeypatch.setattr(planner, "call_planner", lambda *a, **k: pytest.fail("called"))
    q = resolve("What does LPL Financial's 10-K say about its number of financial advisors?", TODAY)
    assert not fts.searchable(q)
    assert planner.plan_question(q, "anthropic").calls == 0


def test_passage_mode_is_one_part_no_call(monkeypatch):
    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)
    monkeypatch.setattr(planner, "call_planner", lambda *a, **k: pytest.fail("called"))
    plan = planner.plan_question(q7(), "anthropic")
    assert [p.firms for p in plan.parts] == [["MS", "MER", "RJF"]] and plan.calls == 0


# --- validation -------------------------------------------------------------------------------

def part(firms, words="advisor recruiting deals", text="t"):
    return {"id": "x", "text": text, "firms": firms, "keyword_query": words}


def test_unknown_firm_dropped_resolved_firm_kept():
    parts, notes = planner.validate_plan({"parts": [part(["MS", "Acme Wealth"]), part(["Merrill"]),
                                                    part(["RJF"])]}, q7(), cap=4)
    assert [p.firms for p in parts] == [["MS"], ["MER"], ["RJF"]]          # "Merrill" -> MER by alias
    assert "unknown firm Acme Wealth" in notes


def test_asked_but_not_resolved_firm_dropped():
    parts, notes = planner.validate_plan({"parts": [part(["MS", "SCHW"]), part(["MER", "RJF"])]}, q7(), cap=4)
    assert [p.firms for p in parts] == [["MS"], ["MER", "RJF"]]
    assert "not asked: SCHW" in notes


def test_firm_without_documents_dropped():
    parts, notes = planner.validate_plan({"parts": [part(["MS", "MER", "RJF", "LPL Financial"])]}, q7(), cap=4)
    assert parts[0].firms == ["MS", "MER", "RJF"] and "no documents: LPLA" in notes


def test_dropped_resolved_firm_comes_back_as_a_part():
    parts, notes = planner.validate_plan({"parts": [part(["MS"]), part(["MS"], "payout grid")]}, q7(), cap=4)
    assert [p.firms for p in parts] == [["MS"], ["MS"], ["MER", "RJF"]]
    assert parts[2].keyword_query is None and parts[2].text == Q7       # the whole question
    assert "added firm MER, RJF" in notes


def test_dropped_resolved_firm_joins_a_part_at_the_cap():
    raw = {"parts": [part(["MS"]), part(["MS", "MER"]), part(["MS"], "training"), part(["MS"], "retention")]}
    parts, notes = planner.validate_plan(raw, q7(), cap=4)
    assert len(parts) == 4 and parts[0].firms == ["MS", "RJF"]          # the first part with fewest firms
    assert all(any(f in p.firms for p in parts) for f in ["MS", "MER", "RJF"])


def test_more_parts_than_the_cap_are_cut_then_firms_restored():
    raw = {"parts": [part(["MS"]), part(["MS"]), part(["MS"]), part(["MS"]), part(["RJF"]), part(["MER"])]}
    parts, notes = planner.validate_plan(raw, q7(), cap=4)
    assert len(parts) == 4 and "cut to 4 parts" in notes
    assert {f for p in parts for f in p.firms} == {"MS", "MER", "RJF"}
    assert [p.id for p in parts] == ["p1", "p2", "p3", "p4"]


def test_part_without_firm_gets_all_firms_and_empty_words_replaced():
    parts, notes = planner.validate_plan({"parts": [part([], "  ", "how advisors are paid")]}, q7(), cap=4)
    assert parts[0].firms == ["MS", "MER", "RJF"] and parts[0].keyword_query == "how advisors are paid"
    assert any("no search words" in n for n in notes) and any("all firms" in n for n in notes)


def test_long_search_words_cut():
    parts, notes = planner.validate_plan({"parts": [part(["MS", "MER", "RJF"], "word " * 200)]}, q7(), cap=4)
    assert len(parts[0].keyword_query) <= planner.MAX_QUERY_CHARS and "part 1: search words cut" in notes


def test_window_and_themes_in_the_output_change_nothing():
    q = resolve("What's new on Raymond James in the last 90 days?", TODAY)
    raw = {"parts": [part(["RJF"])], "window": ["2020-01-01", "2020-12-31"], "themes": ["fees_pricing"]}
    plan = planner.from_output(q, raw, "anthropic", 4)
    pq = planner.part_query(q, plan.parts[0])
    assert (pq.window, pq.themes, pq.mode) == (q.window, q.themes, q.mode)
    assert pq.question == q.question and pq.terms == "advisor recruiting deals"


@pytest.mark.parametrize("raw", [None, {}, {"parts": []}, {"parts": "p1"}, {"parts": ["p1"]}])
def test_unusable_output_falls_back_to_the_rule_plan(raw):
    plan = planner.from_output(q7(), raw, "anthropic", 4)
    assert plan.source == "fallback" and plan.calls == 1 and plan.error
    assert [p.firms for p in plan.parts] == [["MS"], ["MER"], ["RJF"]]


def test_part_query_keeps_the_whole_question_scope():
    q = resolve("Advisor headcount at Morgan Stanley and Raymond James", TODAY)
    assert fts.doc_type_scope(q)[1] == [4]                                # benchmark: no trade press
    pq = planner.part_query(q, planner.Part("p1", "t", ["MS"]))
    assert fts.doc_type_scope(pq)[1] == [] and pq.scope == fts.doc_type_scope(q)
    assert "source_tier" in fts.doc_type_scope_sql(pq)[0]


# --- provider calls (fake clients) ------------------------------------------------------------

PLAN = {"parts": [{"id": "a", "text": "recruiting", "firms": ["MS", "MER", "RJF"],
                   "keyword_query": "recruiting experienced advisors transition packages"},
                  {"id": "b", "text": "payout", "firms": ["MS", "MER", "RJF"],
                   "keyword_query": "payout grid compensation formula"}]}


class FakeAnthropic:
    def __init__(self, blocks=None, stop="tool_use", error=None):
        self.kwargs, self.calls, self.error = None, 0, error
        self.blocks = blocks if blocks is not None else [
            SimpleNamespace(type="tool_use", name=planner.PLAN_TOOL, input=PLAN)]
        self.stop = stop
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.blocks, stop_reason=self.stop)


def test_anthropic_plan_call():
    client = FakeAnthropic()
    plan = planner.plan_question(q7(), "anthropic", client=client, cap=4)
    assert client.calls == 1 and plan.calls == 1 and plan.source == "model"
    assert [p.keyword_query for p in plan.parts] == [PLAN["parts"][0]["keyword_query"], PLAN["parts"][1]["keyword_query"]]
    req = client.kwargs
    assert req["max_tokens"] == planner.PLANNER_MAX_TOKENS and req["tools"][0]["name"] == planner.PLAN_TOOL
    assert req["tools"][0]["input_schema"]["properties"]["parts"]["maxItems"] == 4
    assert "MER (Merrill)" in req["messages"][0]["content"]


def test_truncated_output_falls_back():
    client = FakeAnthropic(stop="max_tokens")
    plan = planner.plan_question(q7(), "anthropic", client=client, cap=4)
    assert plan.source == "fallback" and plan.calls == 1 and "max_tokens" in plan.error


def test_no_tool_call_falls_back():
    client = FakeAnthropic(blocks=[SimpleNamespace(type="text", text="Here is a plan")], stop="end_turn")
    plan = planner.plan_question(q7(), "anthropic", client=client, cap=4)
    assert plan.source == "fallback" and plan.raw == [{"type": "text", "text": "Here is a plan"}]


def test_client_exception_falls_back_and_counts():
    client = FakeAnthropic(error=ConnectionError("network down"))
    plan = planner.plan_question(q7(), "anthropic", client=client, cap=4)
    assert plan.source == "fallback" and plan.calls == 1 and "ConnectionError" in plan.error
    assert [p.firms for p in plan.parts] == [["MS"], ["MER"], ["RJF"]]


class FakeOpenAI:
    def __init__(self, content):
        self.kwargs, self.content = None, content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def test_openai_plan_call_strict_schema():
    client = FakeOpenAI(json.dumps(PLAN))
    plan = planner.plan_question(q7(), "openai", client=client, cap=4)
    rf = client.kwargs["response_format"]
    assert rf["json_schema"]["strict"] is True and plan.source == "model" and len(plan.parts) == 2
    assert planner.plan_question(q7(), "openai", client=FakeOpenAI("not json"), cap=4).source == "fallback"


def test_plan_log_is_json():
    plan = planner.plan_question(q7(), "anthropic", client=FakeAnthropic(), cap=4)
    log = json.loads(json.dumps(plan.to_log()))
    assert log["source"] == "model" and log["calls"] == 1 and log["parts"][0]["id"] == "p1"


# --- prompt -----------------------------------------------------------------------------------

def test_planner_prompt_names_no_question_id_and_no_rubric():
    text = planner.system_prompt(4)
    assert not re.search(r"Q\d{1,2}", text)
    assert _leaks(text) == {}
