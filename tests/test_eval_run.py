"""scripts/eval_run.py: patterns, status, baseline, and --real with a fake provider. No DB, no network."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_run.py"
spec = importlib.util.spec_from_file_location("eval_run", SCRIPT)
er = importlib.util.module_from_spec(spec)
sys.modules["eval_run"] = er
spec.loader.exec_module(er)

SUBS = {"MER": ("BAC", ["GWIM", "Merrill"])}


def hit(chunk_id, entity, doc_type, segment=None):
    return types.SimpleNamespace(chunk_id=chunk_id, entity_id=entity, doc_type=doc_type, segment=segment)


def query(entities=(), mode="entity"):
    return types.SimpleNamespace(entities=list(entities), unmapped=[], mode=mode)


def q(qid, sources, behavior="answer"):
    return {"id": qid, "text": f"text {qid}", "expected_sources": sources, "expected_behavior": behavior}


def test_parse_pattern():
    p = er.parse_pattern("BAC:10-K#GWIM")
    assert (p.entity, p.doc_type, p.qualifier) == ("BAC", "10-K", "GWIM")
    assert er.parse_pattern("RJF:*").doc_type is None
    assert er.parse_pattern("MS:DEF 14A").doc_type == "DEF 14A"


def test_match_qualifier_merrill_and_theme():
    p = er.parse_pattern("BAC:10-K#GWIM")
    assert er.match(p, hit("a", "BAC", "10-K", "GWIM"), SUBS) == "hit"
    assert er.match(p, hit("b", "BAC", "10-K"), SUBS) == "type"          # untagged: not a hit
    assert er.match(p, hit("c", "MS", "10-K", "GWIM"), SUBS) is None
    mer = er.parse_pattern("MER:*")
    assert er.match(mer, hit("d", "BAC", "press", "GWIM"), SUBS) == "hit"
    assert er.match(mer, hit("e", "BAC", "press"), SUBS) is None
    assert er.match(er.parse_pattern("THEME:research"), hit("f", None, "research"), SUBS) == "hit"


def test_available_follows_the_loaded_corpus():
    corpus = {("BAC", "10-K"), ("MS", "supplement")}
    assert er.available(er.parse_pattern("BAC:10-K#GWIM"), corpus, SUBS)
    assert er.available(er.parse_pattern("MER:*"), corpus, SUBS)            # via BAC
    assert not er.available(er.parse_pattern("MER:press"), corpus, SUBS)    # Merrill's own press
    assert not er.available(er.parse_pattern("MS:trade"), corpus, SUBS)


def test_forbidden_other_firm_and_merrill_outside_gwim():
    assert er.forbidden(query(["MS"]), [hit("x", "RJF", "10-K")], SUBS) == ["x"]
    hits = [hit("g", "BAC", "10-K", "GWIM"), hit("b", "BAC", "10-K", None)]
    assert er.forbidden(query(["MER"]), hits, SUBS) == ["b"]
    assert er.forbidden(query(["BAC", "MER"]), hits, SUBS) == []           # BAC asked for itself
    assert er.forbidden(query([], mode="theme"), hits, SUBS) == []


def test_status_rules():
    corpus = {("MS", "10-K"), ("MS", "supplement")}
    two = q("Q1", ["MS:10-K", "MS:supplement", "MS:trade"])
    one_hit = er.evaluate(two, query(["MS"]), [hit("a", "MS", "10-K")], corpus, SUBS, 0.5)
    assert (one_hit["coverage"], one_hit["status"]) == (0.5, "PASS")       # 1 of 2 available
    none = er.evaluate(two, query(["MS"]), [hit("b", "MS", "10-Q")], corpus, SUBS, 0.5)
    assert none["status"] == "FAIL"
    leak = er.evaluate(two, query(["MS"]), [hit("a", "MS", "10-K"), hit("c", "RJF", "10-K")], corpus, SUBS, 0.5)
    assert (leak["status"], leak["forbidden"]) == ("FAIL", ["c"])
    absent = er.evaluate(q("Q9", ["MS:trade"]), query(["MS"]), [hit("a", "MS", "10-K")], corpus, SUBS, 0.5)
    assert (absent["status"], absent["coverage"]) == ("NOT_EVALUATED", None)


def test_compare_with_baseline():
    base = {"status": "FAIL", "coverage": 0.25, "forbidden": []}
    assert er.compare({"status": "PASS", "coverage": 0.5, "forbidden": []}, base) == "IMPROVED"
    assert er.compare({"status": "FAIL", "coverage": 0.0, "forbidden": []}, base) == "REGRESSED"
    assert er.compare(dict(base), base) == "UNCHANGED"
    assert er.compare(dict(base), None) == "NEW"


def test_real_refuses_without_max_calls(capsys):
    with pytest.raises(SystemExit):
        er.main(["--real"])
    assert "--max-calls" in capsys.readouterr().err


@pytest.fixture
def fake_model(monkeypatch, tmp_path):
    """A provider that records every call; ask.answer_for and the prompt version are real."""
    from cee import ask
    from cee.answer.schema import Answer

    calls = []

    def generate(question, hits, provider):
        calls.append(question)
        return Answer(answerable=True, behavior="answer",
                      claims=[{"text": "x", "chunk_ids": [hits[0].chunk_id]}], llm_called=True)

    monkeypatch.setattr(ask, "generate", generate)
    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    return calls


def real_hits():
    from cee.retrieve.fts import Hit
    return [Hit(chunk_id="MS-10K-2025#1", doc_id="MS-10K-2025", entity_id="MS", segment=None, doc_type="10-K",
                source_tier=2, published_at="2026-02-19", period_end="2025-12-31", section="Item 7", page=None,
                rank=1.0, text="x")]


def test_real_cap_and_cache(fake_model, tmp_path):
    runner = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run1", cache_dir=tmp_path / "cache")
    a, how_a = runner.answer(q("Q1", []), query(["MS"]), real_hits())
    b, how_b = runner.answer(q("Q2", []), query(["MS"]), real_hits())
    assert (how_a, how_b) == ("called", "cap") and b is None and len(fake_model) == 1
    assert a["claims"][0]["chunk_ids"] == ["MS-10K-2025#1"] and not a["claims"][0]["flags"]
    # a new run with the same snapshot reuses the saved output: no second call, cap untouched
    again = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    c, how_c = again.answer(q("Q1", []), query(["MS"]), real_hits())
    assert how_c == "cached" and c == a and len(fake_model) == 1 and again.calls == 0
    assert list((tmp_path / "run2" / "raw").iterdir())
    # another snapshot is another input: it would call again
    other = er.RealRunner("anthropic", 0, "snap-2", tmp_path / "run3", cache_dir=tmp_path / "cache")
    assert other.answer(q("Q1", []), query(["MS"]), real_hits())[1] == "cap"


def test_real_no_hits_makes_no_call(fake_model, tmp_path):
    runner = er.RealRunner("anthropic", 0, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    answer, how = runner.answer(q("Q9", []), types.SimpleNamespace(entities=[], unmapped=["VGD"], mode="theme",
                                                                 question="Vanguard?"), [])
    assert how == "no_call" and answer["behavior"] in ("refuse", "gap_with_adjacent") and not fake_model


def test_real_mode_refuses_mock_provider(tmp_path):
    with pytest.raises(SystemExit, match="mock"):
        er.RealRunner("mock", 1, "snap", tmp_path)


def test_behavior_mismatch_fails_in_real_mode():
    r = {"status": "PASS", "expected_behavior": "gap_with_adjacent"}
    assert er.apply_real(dict(r), {"behavior": "answer"}, "called")["status"] == "FAIL"
    assert er.apply_real(dict(r), {"behavior": "gap_with_adjacent"}, "cached")["status"] == "PASS"
    assert er.apply_real(dict(r), None, "cap")["status"] == "NOT_EVALUATED"
