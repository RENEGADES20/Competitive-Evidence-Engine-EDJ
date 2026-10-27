"""scripts/eval_run.py: patterns, status, baseline, and --real with a fake provider. No DB, no network."""
from __future__ import annotations

import datetime as dt
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


# --- #60: recall against the hand-written key, refusal accuracy ---------------------------------

def khit(chunk_id, entity, published="2026-08-01", segment=None, doc_type="10-K"):
    return types.SimpleNamespace(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], entity_id=entity,
                                 doc_type=doc_type, segment=segment, published_at=published)


def test_recall_by_document_and_passage():
    key = {"must_return": [["MS-TR-2026Q2#3"], ["MS-TR-2026Q2#13", "MS-TR-2026Q2#15"], ["MS-10K-2025#125"],
                           ["MS-SUPP-2026Q3"]],
           "must_not_return": []}
    hits = [khit("MS-TR-2026Q2#15", "MS"), khit("MS-SUPP-2026Q3#40", "MS"), khit("MS-10K-2025#1", "MS")]
    s = er.score_key(key, hits, forbidden_ids=[])
    # passages: #13/#15 row found, whole-document row found; #3 and #125 not
    assert (s["passages_found"], s["passages"], s["passage_recall"]) == (2, 4, 0.5)
    # documents: TR-2026Q2, SUPP-2026Q3 and 10K-2025 all have a retrieved chunk
    assert (s["docs_found"], s["docs"], s["doc_recall"]) == (3, 3, 1.0)
    assert s["rows"][0]["found"] == [] and s["rows"][1]["found"] == ["MS-TR-2026Q2#15"]
    assert s["refusal_ok"] is True


def test_refusal_must_not_list_and_forbidden():
    key = {"must_return": [], "must_not_return": ["BAC-10K-2025#18", "BAC-DECK-2026Q1"]}
    clean = er.score_key(key, [khit("BAC-10K-2025#246", "BAC", segment="GWIM")], forbidden_ids=[])
    assert clean["refusal_ok"] is True and clean["misleading"] == [] and clean["doc_recall"] is None
    trap = er.score_key(key, [khit("BAC-10K-2025#18", "BAC"), khit("BAC-DECK-2026Q1#55", "BAC")], forbidden_ids=[])
    assert trap["refusal_ok"] is False and trap["misleading"] == ["BAC-10K-2025#18", "BAC-DECK-2026Q1#55"]
    leak = er.score_key(key, [khit("RJF-10K-2025#1", "RJF")], forbidden_ids=["RJF-10K-2025#1"])
    assert leak["refusal_ok"] is False and leak["misleading"] == ["RJF-10K-2025#1"]


def test_window_drops_old_rows_and_flags_old_hits():
    key = {"must_return": [["RJF-10Q-2026Q2"], ["RJF-PR-2026-07-22-01#4"]], "must_not_return": [],
           "window_days": 90}
    dates = {"RJF-10Q-2026Q2": "2026-08-05", "RJF-PR-2026-07-22-01": "2026-07-22"}
    hits = [khit("RJF-10Q-2026Q2#245", "RJF", "2026-08-05"), khit("RJF-10K-2025#351", "RJF", "2025-11-25")]
    # as of 2026-10-19 both rows are inside the window (from 2026-07-21)
    s = er.score_key(key, hits, forbidden_ids=[], as_of=dt.date(2026, 10, 19), doc_dates=dates)
    assert (s["passages"], s["passages_found"]) == (2, 1)
    assert s["outside_window"] == ["RJF-10K-2025#351"] and s["refusal_ok"] is False
    assert s["window"] == {"from": "2026-07-21", "to": "2026-10-19"}
    # two days later the release has left the window: only the 10-Q is expected
    later = er.score_key(key, hits[:1], forbidden_ids=[], as_of=dt.date(2026, 10, 21), doc_dates=dates)
    assert (later["passages"], later["passages_found"], later["refusal_ok"]) == (1, 1, True)


def test_key_falls_back_to_expected_doc_ids():
    assert er.key_for({"id": "Q2"}, {}) is None
    from_56 = er.key_for({"id": "Q2", "expected_doc_ids": ["RJF-10K-2025", "RJF-TR-2026Q2"]}, {})
    assert from_56 == {"must_return": [["RJF-10K-2025"], ["RJF-TR-2026Q2"]], "must_not_return": [], "source": "#56"}
    hand = {"Q2": {"must_return": [["RJF-10K-2025#1"]], "must_not_return": []}}
    assert er.key_for({"id": "Q2", "expected_doc_ids": ["X"]}, hand)["must_return"] == [["RJF-10K-2025#1"]]


def test_refusal_failure_fails_the_question():
    corpus = {("BAC", "10-K")}
    key = {"must_return": [], "must_not_return": ["BAC-10K-2025#18"]}
    qq = dict(q("Q30", ["BAC:10-K#GWIM"], "gap_with_adjacent"), tier=1)
    good = er.evaluate(qq, query(["MER"]), [khit("BAC-10K-2025#246", "BAC", segment="GWIM")], corpus, SUBS, 0.5,
                       key=key)
    assert good["status"] == "PASS" and good["refusal_ok"] is True     # labelled GWIM substitute is fine
    bad = er.evaluate(qq, query(["MER"]), [khit("BAC-10K-2025#246", "BAC", segment="GWIM"),
                                          khit("BAC-10K-2025#18", "BAC", segment="GWIM")], corpus, SUBS, 0.5, key=key)
    assert bad["status"] == "FAIL" and bad["misleading"] == ["BAC-10K-2025#18"]
    nokey = er.evaluate(qq, query(["MER"]), [], corpus, SUBS, 0.5)
    assert nokey["refusal_ok"] is None and nokey["doc_recall"] is None


def test_summary_tier1_recall_and_refusal_accuracy():
    recs = [{"id": "Q1", "tier": 1, "expected_behavior": "answer", "doc_recall": 0.5, "passage_recall": 0.25,
             "refusal_ok": True},
            {"id": "Q4", "tier": 1, "expected_behavior": "answer", "doc_recall": 0.0, "passage_recall": 0.0,
             "refusal_ok": True},
            {"id": "Q2", "tier": 1, "expected_behavior": "answer", "doc_recall": None, "passage_recall": None,
             "refusal_ok": None},
            {"id": "Q30", "tier": 1, "expected_behavior": "gap_with_adjacent", "doc_recall": None,
             "passage_recall": None, "refusal_ok": False},
            {"id": "Q24", "tier": 3, "expected_behavior": "gap_with_adjacent", "doc_recall": None,
             "passage_recall": None, "refusal_ok": True}]
    s = er.summarize(recs)
    assert s["tier1_doc_recall"] == 0.25 and s["tier1_passage_recall"] == 0.125
    assert (s["tier1_with_key"], s["tier1_total"]) == (2, 4)
    assert s["refusal_gap"] == {"ok": 1, "of": 2, "accuracy": 0.5}
    assert s["refusal_all"] == {"ok": 3, "of": 4, "accuracy": 0.75}


def test_answer_key_ids_are_in_the_manifest():
    import csv
    root = SCRIPT.parents[1]
    docs = {r["doc_id"] for r in csv.DictReader((root / "data" / "manifest.csv").open(encoding="utf-8"))}
    keys = er.load_keys(root / "evals" / "expected_chunks.yaml")
    assert {"Q1", "Q4", "Q11", "Q22", "Q26", "Q24", "Q25", "Q28", "Q29", "Q30"} <= set(keys)
    for qid, key in keys.items():
        ids = [i for row in key["must_return"] for i in row] + key["must_not_return"]
        missing = sorted({i.split("#")[0] for i in ids} - docs)
        assert not missing, f"{qid}: not in data/manifest.csv: {missing}"


def test_as_of_reaches_the_retrieval_window(monkeypatch, tmp_path):
    # --as-of must end the window retrieval uses, not only the one scoring uses (Q26)
    from cee.retrieve import fts

    seen = []
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: seen.append(today) or query())
    monkeypatch.setattr(fts, "search", lambda q, k: [])
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q26", "--as-of", "2026-01-15", "--out", str(tmp_path)])
    assert seen == [dt.date(2026, 1, 15)]
