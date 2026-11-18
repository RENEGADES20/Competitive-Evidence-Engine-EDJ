"""Document-type scope per question (#179, ADR-015): Form ADV brochures only for fee and pricing
questions and never inside a time window; no trade press (tier 4) for benchmark questions.
No database: resolve() and doc_type_scope() on the question bank's own texts."""
from datetime import date
from pathlib import Path

import pytest
import yaml

from cee.retrieve.fts import Query, doc_type_scope, doc_type_scope_sql, resolve

TODAY = date(2026, 11, 17)
BANK = {q["id"]: q["text"] for q in yaml.safe_load(
    (Path(__file__).resolve().parents[1] / "evals" / "questions.yaml").read_text(encoding="utf-8"))["questions"]}


def scope(text: str) -> tuple[list[str], list[int]]:
    return doc_type_scope(resolve(text, today=TODAY))


@pytest.mark.parametrize("qid", ["Q18", "Q25"])
def test_fee_and_compensation_questions_search_the_brochures(qid):
    assert "adv" not in scope(BANK[qid])[0]


@pytest.mark.parametrize("qid", ["Q1", "Q7", "Q11", "Q22", "Q23", "Q24", "Q28", "Q29", "Q30"])
def test_other_questions_leave_the_brochures_out(qid):
    assert "adv" in scope(BANK[qid])[0]


@pytest.mark.parametrize("qid", ["Q26", "Q27"])
def test_window_questions_never_search_the_brochures(qid):
    assert "adv" in scope(BANK[qid])[0]


def test_a_fee_question_inside_a_window_leaves_the_brochures_out():
    assert "adv" not in scope("How have fee structures changed?")[0]
    assert "adv" in scope("How have Raymond James's fee structures changed in the last 90 days?")[0]


def test_a_question_naming_the_brochure_searches_it():
    assert "adv" not in scope("What does Merrill's Form ADV say about conflicts of interest?")[0]
    assert "adv" not in scope("What does the Schwab brochure say about conflicts of interest?")[0]
    assert "adv" in scope("What does Merrill's Form ADV say about conflicts of interest so far this year?")[0]


@pytest.mark.parametrize("qid", ["Q22", "Q23", "Q24", "Q28"])
def test_benchmark_questions_leave_trade_press_out(qid):
    assert 4 in scope(BANK[qid])[1]


@pytest.mark.parametrize("qid", ["Q2", "Q4", "Q5", "Q7", "Q17", "Q26", "Q27", "Q29"])
def test_trade_press_stays_for_other_questions(qid):
    assert scope(BANK[qid])[1] == []


def test_a_one_firm_metric_question_keeps_trade_press():
    assert scope(BANK["Q1"])[1] == []  # "net new assets" for one firm is a strategy question


def test_scope_sql():
    assert doc_type_scope_sql(resolve(BANK["Q18"], today=TODAY)) == ("TRUE", {})
    sql, params = doc_type_scope_sql(resolve(BANK["Q23"], today=TODAY))
    assert sql == "d.doc_type <> ALL(%(scope_types)s) AND d.source_tier <> ALL(%(scope_tiers)s)"
    assert params == {"scope_types": ["adv"], "scope_tiers": [4]}
    assert doc_type_scope_sql(Query("q"))[0] == "d.doc_type <> ALL(%(scope_types)s)"
