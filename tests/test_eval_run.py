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
    return types.SimpleNamespace(entities=list(entities), unmapped=[], mode=mode, themes=[])


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


def test_forbidden_allows_research_only_with_a_named_theme():
    # #116: tier 5 research (no firm) belongs to entity+theme; another firm still leaks
    hits = [hit("r", None, "research"), hit("x", "RJF", "10-K")]
    assert er.forbidden(query(["EDJ"], mode="entity+theme"), hits, SUBS) == ["x"]
    assert er.forbidden(query(["EDJ"]), hits, SUBS) == ["r", "x"]


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

    def generate(question, hits, provider, plan=None, window=None):
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
    answer, how = runner.answer(q("Q9", []), types.SimpleNamespace(entities=[], unmapped=["VGD"], mode="theme", themes=[],
                                                                 question="Vanguard?"), [])
    assert how == "no_call" and answer["behavior"] in ("refuse", "gap_with_adjacent") and not fake_model


def test_real_mode_refuses_mock_provider(tmp_path):
    with pytest.raises(SystemExit, match="mock"):
        er.RealRunner("mock", 1, "snap", tmp_path)


@pytest.fixture
def flaky_model(monkeypatch):
    """First question: an invalid paid output (ModelOutputError); every other question: valid."""
    from cee import ask
    from cee.answer import llm
    from cee.answer.schema import Answer

    calls, state = [], {"error": None}

    def generate(question, hits, provider, plan=None, window=None):
        calls.append(question)
        if len(calls) == 1:
            raise state["error"]
        return Answer(answerable=True, behavior="answer",
                      claims=[{"text": "x", "chunk_ids": [hits[0].chunk_id]}], llm_called=True)

    state["error"] = llm.ModelOutputError("bad", {"answer": "yes"}, "anthropic")
    monkeypatch.setattr(ask, "generate", generate)
    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    return calls, state


def saved(folder):
    import json
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.iterdir())]


def test_real_invalid_output_is_saved_counted_and_run_continues(flaky_model, tmp_path):
    calls, _ = flaky_model
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    a, how_a = runner.answer(q("Q25", []), query(["RJF"]), real_hits())
    b, how_b = runner.answer(q("Q29", []), query(["MS"]), real_hits())
    assert (a, how_a) == (None, "invalid") and how_b == "called" and b["behavior"] == "answer"
    assert runner.calls == 2 and len(calls) == 2           # the failed call still counts
    bad = [s for s in saved(tmp_path / "cache") if s.get("invalid")]
    assert len(bad) == 1 and bad[0]["raw_payload"] == {"answer": "yes"} and bad[0]["question_id"] == "Q25"
    assert "raw" not in bad[0] and bad[0]["error"] == "bad"
    assert saved(tmp_path / "run" / "raw") == saved(tmp_path / "cache")
    # a new run reuses the invalid output: reported again, never re-called
    again = er.RealRunner("anthropic", 5, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    c, how_c = again.answer(q("Q25", []), query(["RJF"]), real_hits())
    assert (c, how_c) == (None, "invalid") and again.calls == 0 and again.reused == 1 and len(calls) == 2
    assert again.last_file.startswith("Q25-") and list((tmp_path / "run2" / "raw").iterdir())


def test_real_invalid_no_tool_call_is_saved(flaky_model, tmp_path):
    """The payload _anthropic builds from a response with only a text block (SDK-like object)."""
    from cee.answer import llm

    calls, state = flaky_model

    class TextBlock:
        type, text = "text", "The answer is yes."

        def model_dump(self, mode="python"):
            return {"type": self.type, "text": self.text}

    client = types.SimpleNamespace(messages=types.SimpleNamespace(
        create=lambda **kw: types.SimpleNamespace(content=[TextBlock()], stop_reason="end_turn")))
    with pytest.raises(llm.ModelOutputError) as e:
        llm._anthropic("q?", real_hits(), client=client)
    state["error"] = e.value
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    a, how_a = runner.answer(q("Q25", []), query(["RJF"]), real_hits())
    b, how_b = runner.answer(q("Q29", []), query(["MS"]), real_hits())
    assert (a, how_a) == (None, "invalid") and how_b == "called" and runner.calls == 2
    bad = [s for s in saved(tmp_path / "cache") if s.get("invalid")]
    assert bad[0]["raw_payload"] == [{"type": "text", "text": "The answer is yes."}]
    assert "did not call" in bad[0]["error"]
    assert saved(tmp_path / "run" / "raw") == saved(tmp_path / "cache")


def test_real_save_never_crashes_on_an_odd_payload(flaky_model, tmp_path):
    from cee.answer import llm

    _, state = flaky_model
    state["error"] = llm.ModelOutputError("bad", {"when": dt.date(2026, 1, 2)}, "anthropic")
    runner = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert runner.answer(q("Q25", []), query(["RJF"]), real_hits())[1] == "invalid"
    assert saved(tmp_path / "cache")[0]["raw_payload"] == {"when": "2026-01-02"}


def test_invalid_output_status_keeps_retrieval_status(tmp_path):
    r = {"status": "FAIL", "expected_behavior": "answer"}
    out = er.apply_real(dict(r), None, "invalid", "Q25-abc.json")
    assert out["status"] == "INVALID_OUTPUT" and out["behavior"] is None
    assert out["note"] == "retrieval FAIL; model output invalid, see raw/Q25-abc.json"
    assert "INVALID_OUTPUT" in er.STATUSES


def test_report_counts_invalid_output(tmp_path):
    import json
    corpus = {("MS", "10-K")}
    r = er.evaluate(q("Q29", ["MS:10-K"]), query(["MS"]), [hit("a", "MS", "10-K")], corpus, SUBS, 0.5)
    r = er.apply_real(r, None, "invalid", "Q29-abc.json")
    meta = {"run_id": "t", "snapshot": "s", "commit": "c", "k": 20, "min_coverage": 0.5, "as_of": "2026-11-17",
            "mode": "real", "baseline": None, "real_calls": 1, "reused": 0, "max_calls": 1}
    er.write_reports(tmp_path, meta, [r])
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "INVALID_OUTPUT 1**" in md and "retrieval PASS; model output invalid, see raw/Q29-abc.json" in md
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["questions"][0]["status"] == "INVALID_OUTPUT"


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
    monkeypatch.setattr(fts, "search", lambda q, k=None, trace=None: [])
    _fake_plan(monkeypatch)
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q26", "--as-of", "2026-01-15", "--out", str(tmp_path)])
    assert seen == [dt.date(2026, 1, 15)]


def test_k_defaults_to_the_app_budget_and_is_recorded(monkeypatch, tmp_path):
    # #181: without --k each question gets fts.budget(q); the record carries k, passages and chars
    import json

    from cee.retrieve import fts

    seen = []
    five = ["MS", "SCHW", "EDJ", "MER", "RJF"]
    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)   # the passage rule (#213 made tokens the default)
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: query(five))
    monkeypatch.setattr(fts, "search", lambda q, k=None, trace=None: seen.append(k) or real_hits())
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q22", "--out", str(tmp_path / "budget")])
    er.main(["--questions", "Q22", "--k", "20", "--out", str(tmp_path / "fixed")])
    # #213: without --k the app's own path (k=None); the record still carries the passage budget
    assert seen == [None, 20]
    rec = json.loads((tmp_path / "budget" / "report.json").read_text(encoding="utf-8"))
    assert rec["meta"]["k"] == "by question"
    assert {k: rec["questions"][0][k] for k in ("k", "passages", "chars")} == {"k": 30, "passages": 1, "chars": 1}
    assert "| 30 | 1 | 1 |" in (tmp_path / "budget" / "report.md").read_text(encoding="utf-8")


# --- #210: recall by stage (candidate pool vs final set), estimated tokens ----------------------

def test_rows_get_a_stage_and_pool_recall():
    key = {"must_return": [["MS-10K-2025#153"], ["SCHW-10K-2025#27"], ["RJF-PR-web-affiliation-options"],
                           ["EDJ-10K-2025#88"]], "must_not_return": []}
    hits = [khit("MS-10K-2025#153", "MS")]
    pool = {"MS-10K-2025#153", "SCHW-10K-2025#27", "RJF-PR-web-affiliation-options#1", "EDJ-10K-2025#87"}
    s = er.score_key(key, hits, forbidden_ids=[], pool_ids=pool)
    assert [r["stage"] for r in s["rows"]] == ["final", "pool", "pool", "none"]   # DOC row: any chunk of it
    assert s["rows"][2]["pool"] == ["RJF-PR-web-affiliation-options#1"]
    assert (s["passages_in_pool"], s["recall_pool"], s["recall_final"]) == (3, 0.75, 0.25)
    assert s["recall_final"] == s["passage_recall"]


def test_pool_recall_counts_final_hits_without_a_trace():
    key = {"must_return": [["MS-10K-2025#153"], ["SCHW-10K-2025#27"]], "must_not_return": []}
    s = er.score_key(key, [khit("MS-10K-2025#153", "MS")], forbidden_ids=[])
    assert [r["stage"] for r in s["rows"]] == ["final", "none"] and s["recall_pool"] == 0.5


def test_pool_recall_uses_the_window_rows():
    key = {"must_return": [["RJF-10Q-2026Q2"], ["RJF-PR-2026-07-22-01#4"]], "must_not_return": [],
           "window_days": 90}
    dates = {"RJF-10Q-2026Q2": "2026-08-05", "RJF-PR-2026-07-22-01": "2026-07-22"}
    s = er.score_key(key, [], forbidden_ids=[], as_of=dt.date(2026, 10, 21), doc_dates=dates,
                     pool_ids={"RJF-PR-2026-07-22-01#4", "RJF-10Q-2026Q2#245"})
    assert s["passages"] == 1 and s["recall_pool"] == 1.0 and s["recall_final"] == 0.0


def test_tokens_are_characters_over_four():
    hits = [types.SimpleNamespace(chunk_id="a#1", text="x" * 10), types.SimpleNamespace(chunk_id="b#1", text="y" * 7)]
    size = er.prompt_size(20, hits)
    assert {k: size[k] for k in ("k", "passages", "chars", "tokens_est")} == {"k": 20, "passages": 2, "chars": 17,
                                                                             "tokens_est": 4}
    assert size["budgeted_chars"] == 17 and size["peer_passages"] == 0 and size["fill"] is None


def test_summary_recall_by_stage_and_totals():
    recs = [{"id": "Q1", "tier": 1, "recall_pool": 1.0, "recall_final": 0.5, "passages": 20, "tokens_est": 100},
            {"id": "Q7", "tier": 2, "recall_pool": 0.0, "recall_final": 0.0, "passages": 20, "tokens_est": 50},
            {"id": "Q2", "tier": 1, "recall_pool": None, "recall_final": None, "passages": 30, "tokens_est": 10}]
    s = er.summarize(recs)
    assert (s["recall_pool"], s["recall_final"], s["with_rows"]) == (0.5, 0.25, 2)
    assert (s["tier1_recall_pool"], s["tier1_recall_final"], s["tier1_with_rows"]) == (1.0, 0.5, 1)
    assert (s["passages"], s["tokens_est"]) == (70, 160)


def test_report_shows_stage_columns_and_summary_row(tmp_path):
    corpus = {("MS", "10-K")}
    key = {"must_return": [["MS-10K-2025#153"], ["MS-10K-2025#9"]], "must_not_return": []}
    r = er.evaluate(dict(q("Q7", ["MS:10-K"]), tier=2), query(["MS"]), [khit("MS-10K-2025#153", "MS")], corpus,
                    SUBS, 0.5, key=key, pool_ids={"MS-10K-2025#9", "MS-10K-2025#153"})
    assert (r["recall_pool"], r["recall_final"], r["pool_size"]) == (1.0, 0.5, 2)
    r |= {"k": 20, "passages": 1, "chars": 8, "tokens_est": 2}
    meta = {"run_id": "t", "snapshot": "s", "commit": "c", "k": 20, "min_coverage": 0.5, "as_of": "2026-11-17",
            "mode": "mock", "baseline": None}
    er.write_reports(tmp_path, meta, [r])
    md = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "| 1/2 | 2/2 |" in md and "recall@pool 1.0, recall@final 0.5" in md
    assert "missing (in pool, lost in select: MS-10K-2025#9)" in md
    assert md.count("| **All** |") == 1


# --- home-firm theme peers (#205, ADR-018): checked on the text, not on search()'s flag ---------

YOUNG = "Gen Z investors make up a third of new accounts"
OFF = "net interest revenue rose on higher balances"


def peer_hit(chunk_id, entity, text, segment=None, on_theme=True):
    return types.SimpleNamespace(chunk_id=chunk_id, entity_id=entity, doc_type="transcript", segment=segment,
                                 text=text, on_theme=on_theme)


def peer_query(peers=("MS", "SCHW", "MER", "RJF")):
    return types.SimpleNamespace(entities=["EDJ"], unmapped=[], mode="entity+theme", themes=["younger_investors"],
                                 theme_peers=list(peers))


def test_forbidden_allows_a_peer_hit_on_the_theme():
    hits = [peer_hit("s", "SCHW", YOUNG), peer_hit("g", "BAC", YOUNG, "GWIM")]
    assert er.forbidden(peer_query(), hits, SUBS) == []


def test_forbidden_peer_hit_off_theme_text_even_if_flagged_on_theme():
    assert er.forbidden(peer_query(), [peer_hit("s", "SCHW", OFF, on_theme=True)], SUBS) == ["s"]


def test_forbidden_bac_non_gwim_hit_with_mer_peer():
    assert er.forbidden(peer_query(), [peer_hit("b", "BAC", YOUNG, segment=None)], SUBS) == ["b"]


def test_forbidden_non_peer_firm_on_theme_hit():
    assert er.forbidden(peer_query(peers=["MS", "MER", "RJF"]), [peer_hit("s", "SCHW", YOUNG)], SUBS) == ["s"]


def test_forbidden_without_theme_peers_unchanged():
    hits = [peer_hit("r", None, YOUNG), peer_hit("s", "SCHW", YOUNG), peer_hit("e", "EDJ", OFF),
            peer_hit("g", "BAC", YOUNG, "GWIM")]
    no_peers = peer_query(peers=[])
    plain = types.SimpleNamespace(entities=["EDJ"], unmapped=[], mode="entity+theme", themes=["younger_investors"])
    assert er.forbidden(no_peers, hits, SUBS) == er.forbidden(plain, hits, SUBS) == ["s", "g"]


# --- #213: token budget, theme peers outside it, search time, max_tokens in the cache key ------

def _tok_hit(cid, entity, n_chars):
    from cee.retrieve.fts import Hit
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-02-19", period_end=None, section=None, page=None,
               rank=1.0, text="x" * n_chars)


def _fake_plan(monkeypatch):
    """#214: token mode searches the question's plan; a one-part rule plan through the faked
    fts.search (k=None, the app's path), so these tests keep seeing what search() was asked."""
    from cee.retrieve import fts, planner

    monkeypatch.setattr(planner, "plan_question",
                        lambda q, provider, **kw: planner.Plan.from_parts([planner.Part("p1", "", list(q.entities))]))
    monkeypatch.setattr(planner, "search_subquestions",
                        lambda q, plan, trace=None, part_pools=None: fts.search(q, trace=trace))


def _fake_eval(monkeypatch, entities, hits, peer_ids=(), unattached=()):
    from cee.retrieve import fts

    seen = []

    def search(q, k=None, trace=None):
        seen.append(k)
        if trace is not None:
            trace.peers += list(peer_ids)
            trace.unattached += list(unattached)
        return hits

    qry = types.SimpleNamespace(entities=list(entities), unmapped=[], mode="entity", themes=[], theme_peers=[])
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: qry)
    monkeypatch.setattr(fts, "search", search)
    _fake_plan(monkeypatch)
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    return seen, qry


def _record(folder):
    import json
    return json.loads((folder / "report.json").read_text(encoding="utf-8"))


def test_token_mode_searches_with_k_none_and_records_the_budget(monkeypatch, tmp_path):
    from cee.retrieve import fts

    five = ["MS", "SCHW", "EDJ", "MER", "RJF"]
    seen, qry = _fake_eval(monkeypatch, five, [_tok_hit("MS-10K-2025#1", "MS", 40000)])
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 20000)
    er.main(["--questions", "Q22", "--out", str(tmp_path / "tok")])
    er.main(["--questions", "Q22", "--k", "20", "--out", str(tmp_path / "fixed")])
    assert seen == [None, 20]
    rep = _record(tmp_path / "tok")
    r = rep["questions"][0]
    assert r["k"] is None and r["budget_tokens"] == fts.budget_tokens(qry) == 30000
    assert r["fill"] == round(40000 / (4 * 30000), 3) and r["tokens_budgeted"] == 10000
    assert isinstance(r["search_s"], float) and r["unattached"] == []
    assert rep["meta"]["token_budget"] == 20000 and rep["meta"]["pool_per_group"] == fts.POOL_PER_GROUP
    assert rep["summary"]["tokens_median"] == 10000 and rep["summary"]["search_s_max"] is not None
    fixed = _record(tmp_path / "fixed")
    assert fixed["questions"][0]["k"] == 20 and fixed["questions"][0]["budget_tokens"] is None
    assert fixed["meta"]["token_budget"] is None
    assert "token budget 20000" in (tmp_path / "tok" / "report.md").read_text(encoding="utf-8")


def test_passage_mode_records_are_unchanged(monkeypatch, tmp_path):
    from cee.retrieve import fts

    monkeypatch.setattr(fts, "TOKEN_BUDGET", None)
    seen, _ = _fake_eval(monkeypatch, ["MS"], [_tok_hit("MS-10K-2025#1", "MS", 400)])
    er.main(["--questions", "Q1", "--out", str(tmp_path / "p")])
    r = _record(tmp_path / "p")["questions"][0]
    assert seen == [None]
    assert {k: r[k] for k in ("k", "passages", "chars", "tokens_est")} == {"k": 20, "passages": 1, "chars": 400,
                                                                          "tokens_est": 100}
    assert r["budget_tokens"] is None and r["fill"] is None


def test_theme_peers_do_not_count_toward_fill(monkeypatch, tmp_path):
    # Q19-like: the home firm's hits are budgeted, the theme peers' hits come on top (#205)
    from cee.retrieve import fts

    hits = [_tok_hit("EDJ-10K-2025#1", "EDJ", 8000), _tok_hit("EDJ-10K-2025#2", "EDJ", 2000),
            _tok_hit("SCHW-TR-2026Q3#11", "SCHW", 6000), _tok_hit("MS-10K-2025#9", "MS", 4000)]
    _fake_eval(monkeypatch, ["EDJ"], hits, peer_ids=["SCHW-TR-2026Q3#11", "MS-10K-2025#9", "RJF-X#1"],
               unattached=["EDJ-TR-2026Q1#4"])
    monkeypatch.setattr(fts, "TOKEN_BUDGET", 2000)
    er.main(["--questions", "Q19", "--out", str(tmp_path / "q19")])
    rep = _record(tmp_path / "q19")
    r = rep["questions"][0]
    assert r["budget_tokens"] == 2000
    assert (r["budgeted_chars"], r["tokens_budgeted"], r["max_hit_chars"]) == (10000, 2500, 8000)
    assert (r["peer_passages"], r["peer_chars"], r["peer_tokens"]) == (2, 10000, 2500)
    assert r["fill"] == 1.25                                  # firm hits only, peers not counted
    assert (r["passages"], r["chars"], r["tokens_est"]) == (4, 20000, 5000)   # all hits: what the model reads
    assert r["unattached"] == ["EDJ-TR-2026Q1#4"] and rep["summary"]["peer_tokens"] == 2500


def test_cache_key_takes_max_tokens_only_when_not_8000():
    import hashlib
    import json
    qq = q("Q24", [])
    args = ("v3", "snap", "anthropic", "m", ["a#1"])
    today = hashlib.sha256(json.dumps(["Q24", "text Q24", *args]).encode()).hexdigest()[:24]
    assert er.cache_key(qq, *args) == er.cache_key(qq, *args, 8000) == today   # saved outputs keep their key
    assert er.cache_key(qq, *args, 16000) != today


def test_max_tokens_change_gets_a_fresh_call(flaky_model, monkeypatch, tmp_path):
    from cee.answer import llm

    calls, state = flaky_model
    state["error"] = llm.ModelOutputError("cut", {"behavior": "answer"}, "anthropic", "max_tokens",
                                          {"output_tokens": 20000})
    first = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert first.answer(q("Q24", []), query(["MS"]), real_hits())[1] == "invalid"
    assert first.last_stop == ("max_tokens", 20000)
    bad = saved(tmp_path / "cache")[0]
    assert bad["stop_reason"] == "max_tokens" and bad["max_tokens"] == llm.MAX_TOKENS == 20000
    assert bad["usage"] == {"output_tokens": 20000}
    # same setting: the saved invalid output is reported, never re-called
    again = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert again.answer(q("Q24", []), query(["MS"]), real_hits())[1] == "invalid" and again.calls == 0
    # the planned run at 16000 is a different request: a fresh call, saved with its setting
    monkeypatch.setattr(llm, "MAX_TOKENS", 16000)
    wider = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run3", cache_dir=tmp_path / "cache")
    a, how = wider.answer(q("Q24", []), query(["MS"]), real_hits())
    assert how == "called" and wider.calls == 1 and len(calls) == 2
    assert sorted(s["max_tokens"] for s in saved(tmp_path / "cache")) == [16000, 20000]


def test_anthropic_error_carries_stop_reason():
    from cee.answer import llm

    block = types.SimpleNamespace(type="tool_use", name=llm.TOOL_NAME, input={"claims": "cut off"})
    client = types.SimpleNamespace(messages=types.SimpleNamespace(
        create=lambda **kw: types.SimpleNamespace(content=[block], stop_reason="max_tokens")))
    with pytest.raises(llm.ModelOutputError) as e:
        llm._anthropic("q?", real_hits(), client=client)
    assert e.value.stop_reason == "max_tokens"
    assert llm.anthropic_request("q?", real_hits())["max_tokens"] == llm.MAX_TOKENS == 20000


# --- #230: stop_reason and usage on every real output; empty saved outputs are invalid -------------

def test_valid_output_saves_stop_reason_and_usage(monkeypatch, tmp_path):
    from cee import ask
    from cee.answer.schema import Answer

    def generate(question, hits, provider, plan=None, window=None):
        return Answer(answerable=True, behavior="answer", claims=[{"text": "x", "chunk_ids": [hits[0].chunk_id]}],
                      llm_called=True, stop_reason="tool_use",
                      usage={"input_tokens": 100, "output_tokens": 4321, "blocks": ["thinking", "tool_use"]})

    monkeypatch.setattr(ask, "generate", generate)
    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    runner = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    a, how = runner.answer(q("Q22", []), query(["MS"]), real_hits())
    assert how == "called" and runner.last_stop == ("tool_use", 4321)
    rec = saved(tmp_path / "cache")[0]
    assert rec["stop_reason"] == "tool_use" and rec["usage"]["output_tokens"] == 4321
    assert rec["raw"]["stop_reason"] == "tool_use" and a["stop_reason"] == "tool_use"
    again = er.RealRunner("anthropic", 0, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert again.answer(q("Q22", []), query(["MS"]), real_hits())[1] == "cached"
    assert again.last_stop == ("tool_use", 4321)


def test_saved_empty_output_is_invalid_on_reuse(fake_model, tmp_path):
    """The #229 Q22 shape, saved as a valid record before #230: reported INVALID_OUTPUT, no call."""
    import json
    runner = er.RealRunner("anthropic", 5, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    hits = real_hits()
    key = er.cache_key(q("Q22", []), runner.prompt_version, "snap-1", "anthropic", "fake-model",
                       [h.chunk_id for h in hits], runner.max_tokens, None, None, runner.request_version)
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / f"Q22-{key}.json").write_text(json.dumps({"raw": {
        "answerable": True, "behavior": "answer", "claims": [], "adjacent": [], "gaps": [], "caveats": [],
        "coverage_note": "", "withheld": [], "llm_called": True}}), encoding="utf-8")
    a, how = runner.answer(q("Q22", []), query(["MS"]), hits)
    assert (a, how) == (None, "invalid") and runner.calls == 0 and runner.reused == 1 and fake_model == []


def test_cache_key_takes_the_window_only_when_given():
    import hashlib
    import json
    qq = q("Q26", [])
    args = ("v4.1", "snap", "anthropic", "m", ["a#1"])
    today = hashlib.sha256(json.dumps(["Q26", "text Q26", *args]).encode()).hexdigest()[:24]
    assert er.cache_key(qq, *args, 8000, None, None) == er.cache_key(qq, *args) == today
    win = (dt.date(2026, 8, 19), dt.date(2026, 11, 17))
    assert er.cache_key(qq, *args, 8000, None, win) != today
    assert er.cache_key(qq, *args, 8000, None, win) != er.cache_key(qq, *args, 8000, None,
                                                                     (dt.date(2026, 8, 20), win[1]))


def test_answer_gets_the_query_window(monkeypatch):
    from cee import ask

    seen = []
    monkeypatch.setattr(ask, "generate", lambda q, h, p, plan=None, window=None: seen.append(window) or
                        __import__("cee.answer.schema", fromlist=["Answer"]).Answer(
                            answerable=True, behavior="answer", claims=[{"text": "x", "chunk_ids": ["MS-10K-2025#1"]}]))
    w = (dt.date(2026, 8, 19), dt.date(2026, 11, 17))
    base = types.SimpleNamespace(entities=["MS"], unmapped=[], mode="entity", themes=[], question="q",
                                 window=None, date_range=None, firm_filter=[], keywords=[], theme_peers=[])
    for window, date_range, want in [(None, None, None), (w, None, w),
                                     (w, (dt.date(2026, 9, 1), dt.date(2026, 12, 31)), (dt.date(2026, 9, 1), w[1]))]:
        qry = types.SimpleNamespace(**{**vars(base), "window": window, "date_range": date_range})
        assert ask.answer_window(qry) == want
        try:
            ask.answer_for("q", qry, real_hits(), "anthropic")
        except Exception:
            pass   # only the window passed to the model matters here
        assert seen[-1] == want


# --- #214: question planner in the eval (plan cache, call count, parts per expected row) ---------

Q7_TEXT = "How do Morgan Stanley, Merrill and Raymond James each approach advisor recruiting and retention?"


def _planner_calls(monkeypatch, outcome):
    """A fake planner provider call: returns `outcome` or raises it; records each call."""
    from cee.retrieve import planner

    calls = []

    def call(query, provider, client=None, meta=None):
        calls.append(query.question)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    monkeypatch.setattr(planner, "call_planner", call)
    monkeypatch.setattr(planner, "model_for", lambda p: "fake-model")
    return calls


def test_plan_is_cached_and_never_called_twice(monkeypatch, tmp_path):
    from cee import ask
    from cee.retrieve import planner
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    raw = {"aspects": [{"id": "a", "text": "payout", "keyword_query": "payout grid", "firms": [], "metric": "", "kind": "fact"}]}
    calls = _planner_calls(monkeypatch, raw)
    question = {"id": "Q7", "text": Q7_TEXT}
    qry = resolve(Q7_TEXT, dt.date(2026, 11, 17))
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    plan = runner.plan(question, qry)
    assert plan.source == "model" and plan.calls == 1 and runner.calls == 1 and len(calls) == 1
    files = list((tmp_path / "cache").iterdir())
    assert len(files) == 1 and files[0].name.startswith("Q7-plan-")
    rec = saved(tmp_path / "cache")[0]
    assert rec["raw"] == raw and rec["planner_version"] == planner.PLANNER_VERSION and rec["max_tokens"] == 8000
    assert rec["stop_reason"] is None and rec["usage"] is None   # the fake fills no meta
    assert saved(tmp_path / "run" / "raw") == saved(tmp_path / "cache")
    again = er.RealRunner("anthropic", 5, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    plan2 = again.plan(question, qry)
    assert again.calls == 0 and again.reused == 1 and len(calls) == 1      # reused, not re-called
    assert [p.keyword_query for p in plan2.parts] == [p.keyword_query for p in plan.parts]


def test_failed_planner_call_is_cached_fallback(monkeypatch, tmp_path):
    from cee import ask
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    calls = _planner_calls(monkeypatch, ConnectionError("network down"))
    question = {"id": "Q7", "text": Q7_TEXT}
    qry = resolve(Q7_TEXT, dt.date(2026, 11, 17))
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    plan = runner.plan(question, qry)
    assert plan.source == "fallback" and plan.calls == 1 and runner.calls == 1
    assert saved(tmp_path / "cache")[0]["failed_call"] is True
    again = er.RealRunner("anthropic", 5, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert again.plan(question, qry).source == "fallback" and again.calls == 0 and len(calls) == 1


def test_planner_call_counts_against_max_calls(monkeypatch, tmp_path):
    from cee import ask
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    calls = _planner_calls(monkeypatch, {"parts": []})
    runner = er.RealRunner("anthropic", 0, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert runner.plan({"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17))) is None
    assert calls == [] and runner.calls == 0


def test_planner_record_saves_stop_reason_and_usage(monkeypatch, tmp_path):
    # #230: bookkeeping only; the planner's output and key are unchanged.
    from cee import ask
    from cee.retrieve import planner
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    monkeypatch.setattr(planner, "model_for", lambda p: "fake-model")
    raw = {"aspects": [{"id": "a", "text": "payout", "keyword_query": "payout grid", "firms": [], "metric": "", "kind": "fact"}]}

    def call(query, provider, client=None, meta=None):
        meta.update(stop_reason="tool_use", usage={"input_tokens": 900, "output_tokens": 300})
        return raw
    monkeypatch.setattr(planner, "call_planner", call)
    runner = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    runner.plan({"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17)))
    rec = saved(tmp_path / "cache")[0]
    assert rec["stop_reason"] == "tool_use" and rec["usage"]["output_tokens"] == 300 and rec["raw"] == raw


def test_call_planner_fills_meta():
    from cee.retrieve import planner
    from cee.retrieve.fts import Query

    block = types.SimpleNamespace(type="tool_use", name=planner.PLAN_TOOL, input={"parts": []})
    usage = types.SimpleNamespace(input_tokens=900, output_tokens=300)
    client = types.SimpleNamespace(messages=types.SimpleNamespace(
        create=lambda **kw: types.SimpleNamespace(content=[block], stop_reason="tool_use", usage=usage)))
    meta = {}
    assert planner.call_planner(Query(question="q", entities=["MS"]), "anthropic", client=client, meta=meta) == {"parts": []}
    assert meta == {"stop_reason": "tool_use", "usage": {"input_tokens": 900, "output_tokens": 300, "blocks": ["tool_use"]}}
    assert planner.call_planner(Query(question="q", entities=["MS"]), "anthropic", client=client) == {"parts": []}


def test_plan_cache_key_unchanged_by_230():
    import hashlib
    import json

    from cee.retrieve.planner import PLANNER_MAX_TOKENS, PLANNER_VERSION, metric_keys
    want = hashlib.sha256(json.dumps(["Q7", "t", PLANNER_VERSION, "s", "anthropic", "m", PLANNER_MAX_TOKENS,
                                      list(metric_keys()), {"entities": ["MS"]}],
                                     default=str, sort_keys=True).encode()).hexdigest()[:24]
    assert er.plan_cache_key({"id": "Q7", "text": "t"}, "s", "anthropic", "m", {"entities": ["MS"]}) == want


def test_cache_key_of_a_plan_differs_by_query_and_model():
    a = er.plan_cache_key({"id": "Q7", "text": "t"}, "s", "anthropic", "m", {"entities": ["MS"]})
    assert a != er.plan_cache_key({"id": "Q7", "text": "t"}, "s", "anthropic", "m2", {"entities": ["MS"]})
    assert a != er.plan_cache_key({"id": "Q7", "text": "t"}, "s", "anthropic", "m", {"entities": ["RJF"]})


def test_part_stages_name_the_parts():
    hits = [khit("MS-10K-2025#153", "MS")]
    hits[0].part_id = "p2"
    key = {"must_return": [["MS-10K-2025#153"], ["SCHW-10K-2025#27"], ["EDJ-10K-2025#88"]], "must_not_return": []}
    s = er.score_key(key, hits, forbidden_ids=[], pool_ids={"SCHW-10K-2025#27"})
    er.part_stages(s, hits, {"p1": {"SCHW-10K-2025#27"}, "p2": {"MS-10K-2025#153"}, "research": set()})
    assert [(r["parts_pool"], r["parts_final"]) for r in s["rows"]] == [
        (["p2"], ["p2"]), (["p1"], []), ([], [])]


def test_mock_record_has_plan_and_zero_calls(monkeypatch, tmp_path):
    from cee.retrieve import fts, planner

    hits = real_hits()
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: fts.Query(question=text, entities=["MS", "RJF"]))
    seen = []

    def fake_parts(q, plan, trace=None, part_pools=None):
        seen.append(plan)
        hits[0].part_id = "p1"
        return hits
    monkeypatch.setattr(planner, "search_subquestions", fake_parts)
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q7", "--out", str(tmp_path)])
    r = _record(tmp_path)["questions"][0]
    assert r["parts"] == 2 and [p["firms"] for p in r["plan"]["parts"]] == [["MS"], ["RJF"]]
    assert r["llm_calls"] == {"planner": 0, "answer": 0} and r["plan"]["source"] == "rules"
    assert _record(tmp_path)["meta"]["planner_version"] == planner.PLANNER_VERSION and seen[0].source == "rules"


# --- #232: the strict Anthropic request has its own cache keys ------------------------------------

def test_request_version_joins_the_answer_key_only_when_given():
    import hashlib
    import json
    qq = q("Q22", [])
    args = ("v4.1", "snap", "anthropic", "m", ["a#1"])
    today = hashlib.sha256(json.dumps(["Q22", "text Q22", *args]).encode()).hexdigest()[:24]
    assert er.cache_key(qq, *args, 8000, None, None, None) == er.cache_key(qq, *args) == today
    strict = er.cache_key(qq, *args, 8000, None, None, "strict-1")
    want = hashlib.sha256(json.dumps(["Q22", "text Q22", *args, {"request": "strict-1"}]).encode()).hexdigest()[:24]
    assert strict == want != today


def test_request_version_joins_the_plan_key_only_when_given():
    import hashlib
    import json

    from cee.retrieve.planner import PLANNER_MAX_TOKENS, PLANNER_VERSION, metric_keys
    base = ["Q7", "t", PLANNER_VERSION, "s", "openai", "m", PLANNER_MAX_TOKENS, list(metric_keys()), {"entities": ["MS"]}]
    want = hashlib.sha256(json.dumps(base, default=str, sort_keys=True).encode()).hexdigest()[:24]
    args = ({"id": "Q7", "text": "t"}, "s", "openai", "m", {"entities": ["MS"]})
    assert er.plan_cache_key(*args) == er.plan_cache_key(*args, None) == want        # OpenAI keys unchanged
    assert er.plan_cache_key(*args, "strict-1") != want


def test_anthropic_runner_does_not_reuse_a_non_strict_output(fake_model, tmp_path):
    """A record saved under the pre-#232 key (no request version) is not reused by an Anthropic run;
    an OpenAI run keeps today's key."""
    import json
    hits = real_hits()
    old = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run0", cache_dir=tmp_path / "cache")
    assert old.request_version == "strict-1"
    pre = er.cache_key(q("Q22", []), old.prompt_version, "snap-1", "anthropic", "fake-model",
                       [h.chunk_id for h in hits], old.max_tokens, None)
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / f"Q22-{pre}.json").write_text(json.dumps({"invalid": True, "error": "old",
                                                                     "raw_payload": {"answer": None}}), encoding="utf-8")
    a, how = old.answer(q("Q22", []), query(["MS"]), hits)
    assert how == "called" and old.calls == 1 and old.reused == 0 and len(fake_model) == 1
    rec = [s for s in saved(tmp_path / "cache") if not s.get("invalid")][0]
    assert rec["request_version"] == "strict-1"
    oa = er.RealRunner("openai", 0, "snap-1", tmp_path / "run1", cache_dir=tmp_path / "cache")
    assert oa.request_version is None


def test_strict_invalid_output_is_saved_and_never_recalled(flaky_model, tmp_path):
    """A response with the #230 Q22 input under the strict request: saved invalid, reported again."""
    from cee.answer import llm

    calls, state = flaky_model
    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **kw: types.SimpleNamespace(
        content=[types.SimpleNamespace(type="tool_use", name=llm.TOOL_NAME, input={"answer": None})],
        stop_reason="tool_use", usage=types.SimpleNamespace(input_tokens=102835, output_tokens=4223))))
    with pytest.raises(llm.ModelOutputError) as e:
        llm._anthropic("q?", real_hits(), client=client)
    state["error"] = e.value
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert runner.answer(q("Q22", []), query(["MS"]), real_hits()) == (None, "invalid")
    bad = saved(tmp_path / "cache")[0]
    assert bad["invalid"] and bad["raw_payload"] == {"answer": None} and bad["request_version"] == "strict-1"
    assert bad["stop_reason"] == "tool_use" and bad["usage"]["output_tokens"] == 4223
    again = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert again.answer(q("Q22", []), query(["MS"]), real_hits()) == (None, "invalid")
    assert again.calls == 0 and len(calls) == 1


def test_plan_record_carries_the_request_version(monkeypatch, tmp_path):
    from cee.retrieve import fts, planner
    from cee.retrieve.fts import Query

    monkeypatch.setattr(fts, "searchable", lambda q: True)
    monkeypatch.setattr(fts, "budget_tokens", lambda q: 40000)
    monkeypatch.setattr(planner, "call_planner", lambda *a, **k: {"aspects": [
        {"id": "a", "text": "t", "keyword_query": "net new assets", "firms": [], "metric": "net_new_assets",
         "kind": "fact"}]})
    runner = er.RealRunner("anthropic", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    plan = runner.plan({"id": "Q1", "text": "t"}, Query(question="t", entities=["MS"]))
    assert plan.source == "model" and runner.calls == 1
    rec = saved(tmp_path / "cache")[0]
    assert rec["request_version"] == "strict-1"



# --- DeepSeek (#242) --------------------------------------------------------------------------

@pytest.fixture
def deepseek_model(monkeypatch):
    """A deepseek generate that returns a valid answer carrying reasoning, or raises `state['error']`."""
    from cee import ask
    from cee.answer.schema import Answer

    calls, state = [], {"error": None}

    def generate(question, hits, provider, plan=None, window=None):
        calls.append(provider)
        if state["error"] is not None:
            raise state["error"]
        a = Answer(answerable=True, behavior="answer", claims=[{"text": "x", "chunk_ids": [hits[0].chunk_id]}],
                   llm_called=True, stop_reason="tool_calls", usage={"output_tokens": 400, "reasoning_tokens": 300})
        a._provider_payload = {"reasoning_content": "secret thoughts", "content": None}
        return a

    monkeypatch.setattr(ask, "generate", generate)
    return calls, state


def test_deepseek_records_carry_version_caps_reasoning_and_timing(deepseek_model, monkeypatch, tmp_path):
    import json

    monkeypatch.setenv("DEEPSEEK_THINKING", "off")
    runner = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert runner.model == "deepseek-v4-pro" and runner.max_tokens == 20000
    a, how = runner.answer(q("Q1", []), query(["MS"]), real_hits())
    assert how == "called"
    rec = saved(tmp_path / "cache")[0]
    assert rec["request_version"] == "ds-strict-1-think-off-a20000-p8000" and rec["max_tokens"] == 20000
    assert rec["reasoning_content"] == "secret thoughts"
    assert rec["wall_s"] >= 0 and "tokens_per_s" in rec
    assert "secret thoughts" not in json.dumps(rec["raw"]) and "secret thoughts" not in json.dumps(a)
    # thinking on is another request: its key differs, so nothing is reused
    monkeypatch.setenv("DEEPSEEK_THINKING", "on")
    on = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert on.max_tokens == 64000 and on.request_version == "ds-strict-1-think-on-a64000-p16000"
    assert on.answer(q("Q1", []), query(["MS"]), real_hits())[1] == "called" and on.calls == 1
    assert len(deepseek_model[0]) == 2 and len(list((tmp_path / "cache").iterdir())) == 2


def test_deepseek_plan_record_saves_reasoning_and_cap(monkeypatch, tmp_path):
    from cee import ask
    from cee.retrieve import planner
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    monkeypatch.setenv("DEEPSEEK_THINKING", "on")
    raw = {"aspects": [{"id": "a", "text": "payout", "keyword_query": "payout grid", "firms": [], "metric": "", "kind": "fact"}]}

    def call(query, provider, client=None, meta=None):
        meta.update(stop_reason="tool_calls", usage={"output_tokens": 900}, reasoning_content="plan thoughts")
        return raw
    monkeypatch.setattr(planner, "call_planner", call)
    runner = er.RealRunner("deepseek", 1, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    runner.plan({"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17)))
    rec = saved(tmp_path / "cache")[0]
    assert rec["max_tokens"] == 16000 and rec["request_version"] == "ds-strict-1-think-on-a64000-p16000"
    assert rec["reasoning_content"] == "plan thoughts" and rec["raw"] == raw and rec["wall_s"] >= 0


def test_deepseek_invalid_answer_is_saved_and_never_recalled(deepseek_model, tmp_path):
    from cee.answer import llm

    calls, state = deepseek_model
    state["error"] = llm.ModelOutputError("cut", {"reasoning_content": "r"}, "deepseek", "length",
                                          {"output_tokens": 20000})
    runner = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    assert runner.answer(q("Q1", []), query(["MS"]), real_hits())[1] == "invalid"
    rec = saved(tmp_path / "cache")[0]
    assert rec["invalid"] and rec["stop_reason"] == "length" and rec["raw_payload"] == {"reasoning_content": "r"}
    assert rec["tokens_per_s"] is not None or rec["wall_s"] == 0
    state["error"] = None
    again = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    assert again.answer(q("Q1", []), query(["MS"]), real_hits())[1] == "invalid" and again.calls == 0
    assert len(calls) == 1


def test_deepseek_provider_stop_saves_nothing_and_exits(deepseek_model, monkeypatch, tmp_path):
    from cee.answer import llm
    from cee.retrieve import planner
    from cee.retrieve.fts import resolve

    calls, state = deepseek_model
    state["error"] = llm.ProviderStop("DeepSeek: insufficient balance (402); top up")
    runner = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    with pytest.raises(SystemExit, match="insufficient balance"):
        runner.answer(q("Q1", []), query(["MS"]), real_hits())
    assert not (tmp_path / "cache").exists() and runner.calls == 1

    def refuse(*a, **kw):
        raise llm.ProviderStop("DeepSeek: rate limit reached (429)")
    monkeypatch.setattr(planner, "call_planner", refuse)
    with pytest.raises(SystemExit, match="rate limit"):
        runner.plan({"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17)))
    assert not (tmp_path / "cache").exists()


def test_other_answer_errors_propagate_save_nothing_and_count(deepseek_model, tmp_path):
    """Review 2 NB2 (D14): a timeout / 500 on the answer path aborts the run; nothing saved; counted."""
    import httpx2
    import openai

    calls, state = deepseek_model
    state["error"] = openai.APITimeoutError(request=httpx2.Request("POST", "http://127.0.0.1:9/chat/completions"))
    runner = er.RealRunner("deepseek", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    with pytest.raises(openai.APITimeoutError):
        runner.answer(q("Q1", []), query(["MS"]), real_hits())
    assert runner.calls == 1 and len(calls) == 1
    assert not (tmp_path / "cache").exists() and not (tmp_path / "run" / "raw").exists()


def test_timing_helper():
    import time

    t = er.timing(time.monotonic() - 2.0, {"output_tokens": 100})
    assert 1.9 <= t["wall_s"] and 40 <= t["tokens_per_s"] <= 52
    assert er.timing(time.monotonic(), None)["tokens_per_s"] is None


# --- #245: plan-only real runs, the 400 stop, the interim input guard in the answer key --------

def _plan_only_env(monkeypatch, outcome, cache):
    from cee import ask
    from cee.retrieve import fts, planner

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    monkeypatch.setattr(planner, "model_for", lambda p: "fake-model")
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: fts.Query(question=text, entities=["MS", "RJF"]))
    monkeypatch.setattr(fts, "searchable", lambda q: True)
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    monkeypatch.setattr(er, "CACHE", cache)   # never the repo's own cache
    monkeypatch.setattr(er.RealRunner.__init__, "__defaults__", (cache,))
    monkeypatch.setattr(ask, "generate", lambda *a, **k: pytest.fail("no answer call in --plan-only"))
    calls = _planner_calls(monkeypatch, outcome)

    def fake_parts(q, plan, trace=None, part_pools=None):
        plan.searched = [{"id": s.id, "budget": 1000, "tokens": 250, "pool": 3} for s in plan.subquestions]
        hits = real_hits()
        hits[0].part_id = plan.subquestions[0].id
        return hits
    monkeypatch.setattr(planner, "search_subquestions", fake_parts)
    return calls


def test_plan_only_makes_planner_calls_and_no_answer_call(monkeypatch, tmp_path):
    raw = {"aspects": [{"id": "a", "text": "pay", "keyword_query": "payout grid", "firms": ["RJF"], "metric": "",
                        "kind": "fact"},
                       {"id": "b", "text": "hiring", "keyword_query": "recruiting", "firms": [], "metric": "",
                        "kind": "fact"}]}
    calls = _plan_only_env(monkeypatch, raw, tmp_path / "cache")
    er.main(["--questions", "Q7", "--real", "--plan-only", "--max-calls", "1", "--out", str(tmp_path / "run")])
    rep = _record(tmp_path / "run")
    r = rep["questions"][0]
    assert len(calls) == 1 and rep["meta"]["real_calls"] == 1 and rep["meta"]["plan_only"] is True
    assert r["llm_calls"] == {"planner": 1, "answer": 0} and r["model"] == "plan_only"
    assert [s["id"] for s in r["plan"]["subquestions"]] == ["a2.MS", "a1.RJF", "a2.RJF"]
    assert r["aspects"] == 2 and r["subquestions"] == 3
    assert r["budget_tokens"] == 3000 and r["fill"] == 0.25                  # sum of sub-question budgets
    assert r["interim_input"]["tokens"] > 0 and r["interim_input"]["would_drop"] == 0
    assert rep["meta"]["subquestion_tokens"] and "max_parts" not in rep["meta"]


def test_plan_only_needs_real(tmp_path):
    with pytest.raises(SystemExit):
        er.main(["--questions", "Q7", "--plan-only", "--out", str(tmp_path)])


class _BadRequest(Exception):
    status_code = 400


def test_a_400_on_a_planner_call_stops_the_run(monkeypatch, tmp_path):
    from cee import ask
    from cee.retrieve.fts import resolve

    monkeypatch.setattr(ask, "model_name", lambda p: "fake-model")
    calls = _planner_calls(monkeypatch, _BadRequest("schema rejected"))
    runner = er.RealRunner("deepseek", 9, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    with pytest.raises(SystemExit, match="400"):
        runner.plan({"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17)))
    rec = saved(tmp_path / "cache")[0]
    assert rec["bad_request"] is True and rec["failed_call"] is True and runner.calls == 1 and len(calls) == 1
    # a 500 is a counted fallback, as before
    _planner_calls(monkeypatch, ConnectionError("down"))
    plan = er.RealRunner("deepseek", 9, "snap-2", tmp_path / "r2", cache_dir=tmp_path / "c2").plan(
        {"id": "Q7", "text": Q7_TEXT}, resolve(Q7_TEXT, dt.date(2026, 11, 17)))
    assert plan.source == "fallback"


def test_guard_trim_joins_the_answer_key(fake_model, monkeypatch, tmp_path):
    from cee.retrieve.fts import Hit
    hits = [Hit(chunk_id=f"MS-10K-2025#{i}", doc_id="MS-10K-2025", entity_id="MS", segment=None, doc_type="10-K",
                source_tier=2, published_at="2026-02-19", period_end="2025-12-31", section="Item 7", page=None,
                rank=10.0 - i, text="word " * 400) for i in range(6)]
    args = (q("Q1", []), "v4.1", "snap", "anthropic", "m", [h.chunk_id for h in hits])
    plain = er.cache_key(*args)
    trimmed = er.cache_key(*args, 8000, None, None, None, {"limit": 5000, "dropped": ["MS-10K-2025#5"]})
    assert trimmed != plain != er.cache_key(*args, 8000, None, None, None, {"limit": 6000, "dropped": ["MS-10K-2025#5"]})
    runner = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run", cache_dir=tmp_path / "cache")
    runner.answer(q("Q1", []), query(["MS"]), hits)
    assert runner.last_guard is None
    from cee.answer import llm
    base = llm.input_tokens("text Q1", hits[:0])
    monkeypatch.setenv("ANSWER_INPUT_MAX_TOKENS", str(base + 1200))
    again = er.RealRunner("anthropic", 2, "snap-1", tmp_path / "run2", cache_dir=tmp_path / "cache")
    a, how = again.answer(q("Q1", []), query(["MS"]), hits)
    assert how == "called" and again.last_guard and again.last_guard["dropped"]       # not the untrimmed output
    rec = [s for s in saved(tmp_path / "cache") if s.get("input_guard")][0]
    assert rec["input_guard"]["limit"] == base + 1200
