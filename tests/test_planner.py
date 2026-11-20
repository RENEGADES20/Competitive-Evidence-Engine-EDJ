"""Question planner, sub-question decomposition (#245, ADR-021 rule 6; #214, #224 before): rule plan,
firm scope by code, code validation of a plan-v3 output (aspects, per-aspect firms, no cap),
provider calls with fake clients, fallback. No database, never a real API call."""
import json
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from cee.retrieve import fts, planner
from cee.retrieve.fts import Query, resolve
from tests.test_prompt import _grams, _leaks

TODAY = date(2026, 11, 17)
Q7 = "How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?"
FIVE = "Client assets per advisor across the five -- and is that comparison even valid?"
BANK = {q["id"]: q for q in yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "evals" / "questions.yaml").read_text(encoding="utf-8"))["questions"]}


def q7() -> Query:
    return resolve(Q7, TODAY)


def bank(qid: str) -> Query:
    return resolve(BANK[qid]["text"], TODAY)


def asp(text="t", words="advisor recruiting deals", firms=(), metric="", kind="fact"):
    return {"id": "x", "text": text, "keyword_query": words, "firms": list(firms), "metric": metric, "kind": kind}


def subs(plan):
    return [s.id for s in plan.subquestions]


# --- firm scope and the rule plan --------------------------------------------------------------

def test_rule_plan_one_aspect_for_every_named_firm():
    plan = planner.rules_plan(q7())
    assert subs(plan) == ["a1.MS", "a1.MER", "a1.RJF"] and plan.source == "rules" and plan.calls == 0
    a = plan.aspects[0]
    assert (a.id, a.text, a.keyword_query, a.kind, a.firms) == ("a1", Q7, None, "fact", [])
    assert [p.firms for p in plan.parts] == [["MS"], ["MER"], ["RJF"]]
    assert plan.parts[0].text == f"Morgan Stanley: {Q7}"


@pytest.mark.parametrize("qid, ids, metric, kind", [
    ("Q22", ["a1.MS", "a1.SCHW", "a1.EDJ", "a1.MER", "a1.RJF"], "net_new_assets", "fact"),  # five, no cap
    ("Q23", ["a1.MS", "a1.SCHW", "a1.EDJ", "a1.MER", "a1.RJF"], "advisor_headcount", "fact"),   # quarters: no SQL window
    ("Q16", ["a1.all"], None, "fact"),                                                       # theme mode
    ("Q26", ["a1.RJF"], None, "recency"),                                                    # window
    ("Q19", ["a1.EDJ", "a1.MS", "a1.SCHW", "a1.MER", "a1.RJF"], None, "fact"),             # competitors
])
def test_rule_plan_is_deterministic(qid, ids, metric, kind):
    plan = planner.rules_plan(bank(qid))
    assert subs(plan) == ids and plan.aspects[0].metric == metric and plan.aspects[0].kind == kind
    assert subs(planner.rules_plan(bank(qid))) == ids


def test_firm_scope_named_competitors_theme_and_filters():
    assert planner.firm_scope(bank("Q19")) == [("EDJ", "named"), ("MS", "competitor"), ("SCHW", "competitor"),
                                                ("MER", "competitor"), ("RJF", "competitor")]
    assert planner.firm_scope(bank("Q16")) == [(None, "all")]
    filtered = fts.apply_filters(bank("Q19"), firms=["EDJ"])
    assert planner.firm_scope(filtered) == [("EDJ", "named")]            # a firm filter clears competitors
    q = resolve("Edward Jones and Vanguard on fees", TODAY)
    assert planner.firm_scope(q) == [("EDJ", "named")]                    # no documents for Vanguard


def test_firm_origins_label_how_code_found_each_firm():
    assert planner.firm_origins(bank("Q15")) == [
        ("MS", 'through "an advisor-led model"'), ("SCHW", "named"), ("EDJ", 'through "an advisor-led model"'),
        ("MER", 'through "an advisor-led model"'), ("RJF", 'through "an advisor-led model"')]
    assert {how for _, how in planner.firm_origins(bank("Q22"))} == {'through "each of the five"'}
    assert planner.firm_origins(bank("Q19"))[1:] == [(f, "competitor on the theme") for f in ("MS", "SCHW", "MER", "RJF")]
    msg = planner.planner_message(bank("Q15"))
    assert "SCHW (Charles Schwab): named" in msg or "SCHW (" in msg and ": named" in msg
    assert 'through "an advisor-led model"' in msg and "Most parts" not in msg


def test_no_cap_eight_firms_by_a_hundred_aspects(monkeypatch):
    from cee import config
    cfg = config.entities_config()
    extra = [{"id": f"F{i}", "name": f"Firm {i}", "aliases": []} for i in range(3)]
    monkeypatch.setattr(planner, "entities_config", lambda: {**cfg, "entities": [*cfg["entities"], *extra]})
    q = Query(question="q", entities=["MS", "SCHW", "EDJ", "MER", "RJF", "F0", "F1", "F2"])
    aspects, notes = planner.validate_plan({"aspects": [asp(f"aspect {i}", f"words {i}") for i in range(100)]}, q)
    assert len(aspects) == 100 and [a.id for a in aspects][:3] == ["a1", "a2", "a3"] and not notes
    out = planner.subquestions(q, aspects)
    assert len(out) == 800 and out[0].id == "a1.MS" and out[100].id == "a1.SCHW"   # firm-major


def test_mock_and_planner_off_make_no_call(monkeypatch):
    monkeypatch.setattr(planner, "call_planner", lambda *a, **k: pytest.fail("called"))
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


# --- validation ---------------------------------------------------------------------------------

def test_aspects_kept_literally_no_merge_no_dedupe():
    aspects, notes = planner.validate_plan({"aspects": [asp("pay"), asp("pay"), asp("training", "training")]}, q7())
    assert [a.id for a in aspects] == ["a1", "a2", "a3"] and [a.text for a in aspects] == ["pay", "pay", "training"]
    assert not notes


def test_metric_and_kind_are_checked():
    aspects, notes = planner.validate_plan({"aspects": [
        asp(metric="advisor_headcount", kind="series"), asp(metric="client_assets", kind="opinion"), asp()]}, q7())
    assert [(a.metric, a.kind) for a in aspects] == [("advisor_headcount", "series"), (None, "fact"), (None, "fact")]
    assert "aspect 2: unknown metric client_assets" in notes and "aspect 2: unknown kind opinion, fact" in notes


def test_empty_text_and_words_and_long_words():
    aspects, notes = planner.validate_plan({"aspects": [asp("", "  "), asp("how advisors are paid", "  "),
                                                        asp("t", "word " * 200)]}, q7())
    assert aspects[0].text == Q7 and aspects[0].keyword_query == Q7
    assert aspects[1].keyword_query == "how advisors are paid"
    assert len(aspects[2].keyword_query) <= planner.MAX_QUERY_CHARS
    assert {"aspect 1: no text, the question", "aspect 2: no search words", "aspect 3: search words cut"} <= set(notes)


def test_window_and_themes_in_the_output_change_nothing():
    q = resolve("What's new on Raymond James in the last 90 days?", TODAY)
    raw = {"aspects": [asp()], "window": ["2020-01-01", "2020-12-31"], "themes": ["fees_pricing"]}
    plan = planner.from_output(q, raw, "anthropic")
    sq = planner.subquestion_query(q, plan.subquestions[0])
    assert (sq.window, sq.themes, sq.mode) == (q.window, q.themes, q.mode)
    assert sq.question == q.question and sq.terms == "advisor recruiting deals"


@pytest.mark.parametrize("raw", [None, {}, {"aspects": []}, {"aspects": "a1"}, {"aspects": ["a1"]},
                                 {"parts": [{"id": "p", "text": "t", "firms": ["MS"], "keyword_query": "w"}]}])
def test_unusable_output_falls_back_to_the_rule_plan(raw):
    plan = planner.from_output(q7(), raw, "anthropic")
    assert plan.source == "fallback" and plan.calls == 1 and plan.error
    assert subs(plan) == ["a1.MS", "a1.MER", "a1.RJF"]


def test_subquestion_query_keeps_the_whole_question_scope():
    q = resolve("Advisor headcount at Morgan Stanley and Raymond James", TODAY)
    assert fts.doc_type_scope(q)[1] == [4]                                # benchmark: no trade press
    plan = planner.rules_plan(q)
    sq = planner.subquestion_query(q, plan.subquestions[0])
    assert sq.entities == ["MS"] and fts.doc_type_scope(sq)[1] == [] and sq.scope == fts.doc_type_scope(q)
    assert "source_tier" in fts.doc_type_scope_sql(sq)[0] and sq.on_theme_only is False


# --- per-aspect firms (TL decision D3) ----------------------------------------------------------

def test_q12_restricted_aspects_are_searched_for_their_firm_only():
    q = bank("Q12")
    raw = {"aspects": [asp("how the firm uses its scale to acquire clients cheaply", "scale client acquisition cost",
                           ["SCHW"]),
                       asp("acquisition economics", "cost per new account marketing", ["Schwab"]),
                       asp("cost structure and how a similar strategy could be replicated", "cost structure expenses",
                           ["Edward Jones"])]}
    plan = planner.from_output(q, raw, "anthropic")
    assert [a.firms for a in plan.aspects] == [["SCHW"], ["SCHW"], ["EDJ"]] and not plan.corrections
    assert subs(plan) == ["a1.SCHW", "a2.SCHW", "a3.EDJ"]


def test_q15_restricted_aspects_follow_the_peer_phrase():
    q = bank("Q15")
    raw = {"aspects": [asp("how the firm earns on client assets", "net interest revenue asset management fees",
                           ["SCHW"]),
                       asp("how an advisor-led firm earns", "advisory fees asset-based fees commissions",
                           ["MS", "EDJ", "MER", "RJF"]),
                       asp("what drives the difference", "revenue mix fee rate")]}
    plan = planner.from_output(q, raw, "anthropic")
    assert [a.firms for a in plan.aspects] == [["SCHW"], ["MS", "EDJ", "MER", "RJF"], []]
    by_aspect = {a.id: sorted(s.entity for s in plan.subquestions if s.aspect.id == a.id) for a in plan.aspects}
    assert by_aspect == {"a1": ["SCHW"], "a2": ["EDJ", "MER", "MS", "RJF"], "a3": ["EDJ", "MER", "MS", "RJF", "SCHW"]}


def test_q19_named_firm_only_keeps_the_competitors():
    q = bank("Q19")
    raw = {"aspects": [asp("what younger investors prefer", "younger investors prefer", ["EDJ"]),
                       asp("offerings aimed at younger investors", "digital low minimum", ["EDJ"])]}
    plan = planner.from_output(q, raw, "anthropic")
    assert [a.firms for a in plan.aspects] == [[], []]
    assert {s.entity for s in plan.subquestions} == {"EDJ", "MS", "SCHW", "MER", "RJF"}
    assert "aspect 1: named firms only on a home-firm market question, competitors kept" in plan.corrections
    # a list naming the home firm and some competitors stays as written
    plan = planner.from_output(q, {"aspects": [asp(firms=["EDJ", "SCHW"])]}, "anthropic")
    assert subs(plan) == ["a1.EDJ", "a1.SCHW"]


def test_out_of_scope_firms_are_dropped_with_a_note():
    raw = {"aspects": [asp(firms=["MS", "SCHW", "Acme Wealth"]), asp(firms=["Vanguard"]), asp(firms=["Merrill", "RJF", "MS"])]}
    aspects, notes = planner.validate_plan(raw, q7())
    assert [a.firms for a in aspects] == [["MS"], [], []]        # all three scoped firms = empty
    assert {"aspect 1: firm SCHW not in scope", "aspect 1: firm Acme Wealth not in scope",
            "aspect 2: firm Vanguard not in scope", "aspect 2: no firm in scope, all firms"} <= set(notes)


# --- provider calls (fake clients) --------------------------------------------------------------

PLAN = {"aspects": [asp("recruiting", "recruiting experienced advisors transition packages"),
                    asp("payout", "payout grid compensation formula", metric="", kind="fact")]}


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
    plan = planner.plan_question(q7(), "anthropic", client=client)
    assert client.calls == 1 and plan.calls == 1 and plan.source == "model"
    assert [a.keyword_query for a in plan.aspects] == [a["keyword_query"] for a in PLAN["aspects"]]
    assert len(plan.subquestions) == 6
    req = client.kwargs
    assert req["max_tokens"] == planner.PLANNER_MAX_TOKENS == 8000 and req["tools"][0]["name"] == planner.PLAN_TOOL
    aspects = req["tools"][0]["input_schema"]["properties"]["aspects"]
    assert req["tools"][0]["strict"] is True and aspects["minItems"] == 1 and "maxItems" not in aspects
    item = aspects["items"]
    assert item["properties"]["metric"]["enum"] == ["", "advisor_headcount", "net_new_assets"]
    assert item["properties"]["kind"]["enum"] == list(planner.KINDS)
    assert item["properties"]["firms"] == {"type": "array", "items": {"type": "string"}}
    assert "Most parts" not in req["messages"][0]["content"] and "MER (Merrill)" in req["messages"][0]["content"]


def test_refusal_falls_back_even_with_a_valid_plan():
    plan = planner.plan_question(q7(), "anthropic", client=FakeAnthropic(stop="refusal"))
    assert plan.source == "fallback" and plan.calls == 1 and "refusal" in plan.error
    assert plan.raw[0]["input"] == PLAN


def test_truncated_output_falls_back():
    plan = planner.plan_question(q7(), "anthropic", client=FakeAnthropic(stop="max_tokens"))
    assert plan.source == "fallback" and plan.calls == 1 and "max_tokens" in plan.error


def test_no_tool_call_falls_back():
    client = FakeAnthropic(blocks=[SimpleNamespace(type="text", text="Here is a plan")], stop="end_turn")
    plan = planner.plan_question(q7(), "anthropic", client=client)
    assert plan.source == "fallback" and plan.raw == [{"type": "text", "text": "Here is a plan"}]


def test_client_exception_falls_back_and_counts():
    plan = planner.plan_question(q7(), "anthropic", client=FakeAnthropic(error=ConnectionError("network down")))
    assert plan.source == "fallback" and plan.calls == 1 and "ConnectionError" in plan.error
    assert subs(plan) == ["a1.MS", "a1.MER", "a1.RJF"]


class FakeOpenAI:
    def __init__(self, content):
        self.kwargs, self.content = None, content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def test_openai_plan_call_strict_schema():
    client = FakeOpenAI(json.dumps(PLAN))
    plan = planner.plan_question(q7(), "openai", client=client)
    rf = client.kwargs["response_format"]
    assert rf["json_schema"]["strict"] is True and plan.source == "model" and len(plan.aspects) == 2
    assert "minItems" not in json.dumps(rf["json_schema"]["schema"])
    assert planner.plan_question(q7(), "openai", client=FakeOpenAI("not json")).source == "fallback"


def test_openai_cut_plan_is_rejected_even_when_it_parses():
    """#242: finish_reason length on the OpenAI planner is a cut plan, never used."""
    client = FakeOpenAI(json.dumps(PLAN))
    client._create_orig = client._create

    def cut(**kwargs):
        resp = client._create_orig(**kwargs)
        resp.choices[0].finish_reason = "length"
        return resp
    client.chat.completions.create = cut
    plan = planner.plan_question(q7(), "openai", client=client)
    assert plan.source == "fallback" and "max_tokens" in plan.error and plan.raw == json.dumps(PLAN)


# --- DeepSeek (#242) ----------------------------------------------------------------------------

def _ds_plan_response(finish="tool_calls", args=None, name=planner.PLAN_TOOL, extra_calls=()):
    from tests.test_llm_deepseek import response, tool_call
    calls = [tool_call(name=name, arguments=json.dumps(PLAN) if args is None else args), *extra_calls]
    return response(calls=calls, finish=finish, reasoning="Two asks.")


def test_deepseek_plan_request_and_call(monkeypatch):
    from tests.test_llm_deepseek import FakeDeepSeek
    for mode, cap_tokens, choice in (("off", 8000, {"type": "function", "function": {"name": planner.PLAN_TOOL}}),
                                     ("on", 16000, "auto")):
        monkeypatch.setenv("DEEPSEEK_THINKING", mode)
        client = FakeDeepSeek(_ds_plan_response())
        meta: dict = {}
        raw = planner.call_planner(q7(), "deepseek", client=client, meta=meta)
        assert raw == PLAN and meta["stop_reason"] == "tool_calls" and meta["reasoning_content"] == "Two asks."
        assert meta["usage"]["cache_hit_tokens"] == 60
        req = client.kwargs
        fn = req["tools"][0]["function"]
        assert fn["name"] == planner.PLAN_TOOL and fn["strict"] is True
        assert fn["parameters"] == planner.plan_schema(strict=True) and "minItems" not in json.dumps(fn["parameters"])
        assert req["max_tokens"] == cap_tokens == planner.planner_max_tokens("deepseek")
        assert req["tool_choice"] == choice and "Firms (chosen by code" in req["messages"][1]["content"]
    plan = planner.plan_question(q7(), "deepseek", client=FakeDeepSeek(_ds_plan_response()))
    assert plan.source == "model" and plan.model == "deepseek-v4-pro" and plan.calls == 1


@pytest.mark.parametrize("resp, match", [
    (dict(finish="length"), "cut at max_tokens"),
    (dict(finish="aborted"), "finish_reason aborted"),
    (dict(name="other"), "did not call"),
    (dict(args="{oops"), "not a JSON object"),
    (dict(args='"text"'), "not a JSON object"),
])
def test_deepseek_unusable_plans_raise_and_fall_back(resp, match):
    from tests.test_llm_deepseek import FakeDeepSeek
    with pytest.raises(planner.PlannerOutputError, match=match) as e:
        planner.call_planner(q7(), "deepseek", client=FakeDeepSeek(_ds_plan_response(**resp)))
    assert e.value.raw is not None
    plan = planner.plan_question(q7(), "deepseek", client=FakeDeepSeek(_ds_plan_response(**resp)))
    assert plan.source == "fallback" and plan.calls == 1


def test_deepseek_first_plan_call_wins():
    from tests.test_llm_deepseek import FakeDeepSeek, tool_call
    other = tool_call(name=planner.PLAN_TOOL, arguments=json.dumps({"aspects": []}))
    meta: dict = {}
    raw = planner.call_planner(q7(), "deepseek", client=FakeDeepSeek(_ds_plan_response(extra_calls=[other])),
                               meta=meta)
    assert raw == PLAN and meta["usage"]["tool_calls"] == 2


def test_deepseek_refusal_codes_stop_the_question_not_a_fallback():
    from cee.answer import llm
    from tests.test_llm_deepseek import FakeDeepSeek, status_error
    with pytest.raises(llm.ProviderStop, match="insufficient balance"):
        planner.plan_question(q7(), "deepseek", client=FakeDeepSeek(error=status_error(402)))
    plan = planner.plan_question(q7(), "deepseek", client=FakeDeepSeek(error=status_error(500)))
    assert plan.source == "fallback" and plan.calls == 1 and "APIStatusError" in plan.error


def test_plan_log_is_json():
    plan = planner.plan_question(q7(), "anthropic", client=FakeAnthropic())
    log = json.loads(json.dumps(plan.to_log()))
    assert log["source"] == "model" and log["calls"] == 1 and log["parts"][0]["id"] == "a1.MS"
    assert log["aspects"][0]["firms"] == [] and log["subquestions"][0] == {
        "id": "a1.MS", "entity": "MS", "aspect": "a1", "role": "named"} and log["competitor_floor"] == {}


def test_describe_plan():
    assert planner.describe_plan(planner.rules_plan(q7())) == "1 aspect x 3 firms = 3 sub-questions: a1.MS; a1.MER; a1.RJF"
    assert planner.describe_plan(planner.rules_plan(bank("Q16"))) == "1 aspect x all sources = 1 sub-question: a1.all"


# --- prompt -------------------------------------------------------------------------------------

def test_planner_prompt_names_no_question_id_and_no_rubric():
    text = planner.system_prompt()
    assert not re.search(r"Q\d{1,2}", text)
    assert _leaks(text) == {}


def test_planner_version_is_v3_and_changes_the_cache_key(monkeypatch):
    import tests.test_eval_run  # noqa: F401  (loads scripts/eval_run.py as module eval_run)
    from eval_run import plan_cache_key
    assert planner.PLANNER_VERSION == "plan-v3"
    args = ({"id": "Q25", "text": BANK["Q25"]["text"]}, "corpus-2026-11-17", "anthropic", "claude-sonnet-5-5", {})
    v3 = plan_cache_key(*args)
    monkeypatch.setattr(planner, "PLANNER_VERSION", "plan-v2")
    assert plan_cache_key(*args) != v3
    monkeypatch.setattr(planner, "PLANNER_VERSION", "plan-v3")
    monkeypatch.setattr(planner, "metric_keys", lambda: ("advisor_headcount",))
    assert plan_cache_key(*args) != v3                                   # the schema's enum is in the key


def test_planner_prompt_shares_no_six_words_with_any_question_text():
    mine = _grams(planner.system_prompt())
    assert {qid: hit for qid, q in BANK.items() if (hit := mine & _grams(q["text"]))} == {}


def test_planner_prompt_v3_rules():
    text = planner.system_prompt()
    assert "List the aspects literally" in text and "Never merge two aspects" in text
    assert "do not stop at any number" in text and "Firms of an aspect" in text and "Same concept only" in text
    assert "advisor_headcount, net_new_assets" in text


# --- neighbour phrases (#224), now on aspects ---------------------------------------------------

V1_OUTPUTS = json.loads((Path(__file__).parent / "data" / "planner_v1_0214.json").read_text(encoding="utf-8"))
NEIGHBOUR_PARTS = {"Q15": 1, "Q25": 3}


@pytest.mark.parametrize("qid", ["Q3", "Q7", "Q12", "Q15", "Q25", "Q28"])
def test_neighbour_guard_on_the_saved_v1_words(qid):
    """The v1 parts' words as aspects: only the ones that said "payout ratio" change, by that phrase."""
    raw = {"aspects": [asp(p["text"], p["keyword_query"]) for p in V1_OUTPUTS[qid]["parts"]]}
    aspects, notes = planner.validate_plan(raw, bank(qid))
    expected = [p["keyword_query"].strip() for p in V1_OUTPUTS[qid]["parts"]]
    hit = NEIGHBOUR_PARTS.get(qid)
    if hit is not None:
        expected[hit] = " ".join(expected[hit].replace("payout ratio", " ").split())
        assert "ratio" not in aspects[hit].keyword_query
    assert [a.keyword_query for a in aspects] == expected
    assert [n for n in notes if "neighbour" in n or "search words" in n] == (
        [] if hit is None else [f"aspect {hit + 1}: dropped neighbour phrase payout ratio"])


def test_neighbour_phrase_named_by_the_question_is_kept():
    q = resolve("What is Raymond James's dividend payout ratio?", TODAY)
    aspects, notes = planner.validate_plan({"aspects": [asp(words="dividend payout ratio")]}, q)
    assert aspects[0].keyword_query == "dividend payout ratio" and not notes


def test_neighbour_phrase_forms_are_caught_and_empty_words_use_the_question():
    words, dropped = planner.strip_neighbours("advisor pay Payout-Ratios grid", "How are advisors paid?")
    assert words == "advisor pay grid" and dropped == ["payout ratio"]
    aspects, notes = planner.validate_plan({"aspects": [asp(words="employee turnover")]},
                                           resolve("How are Morgan Stanley advisors paid?", TODAY))
    assert aspects[0].keyword_query is None
    assert notes == ["aspect 1: dropped neighbour phrase employee turnover", "aspect 1: no search words left"]


def test_neighbour_guard_never_touches_the_rule_plan():
    plan = planner.rules_plan(bank("Q25"))
    assert all(p.keyword_query is None for p in plan.parts) and plan.corrections == []
