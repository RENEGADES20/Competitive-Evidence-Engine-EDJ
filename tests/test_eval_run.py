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

    def generate(question, hits, provider):
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
    from cee.retrieve import fts, modes

    seen = []
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: seen.append(today) or query())
    monkeypatch.setattr(modes, "search", lambda q, k=None, mode=None, trace=None: [])
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q26", "--as-of", "2026-01-15", "--out", str(tmp_path)])
    assert seen == [dt.date(2026, 1, 15)] * 2  # untimed warm-up + the timed run


def test_mode_and_search_time_are_recorded(monkeypatch, tmp_path):
    import json
    from cee.retrieve import fts, modes

    seen_modes = []
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: query())
    monkeypatch.setattr(modes, "search", lambda q, k=None, mode=None, trace=None: seen_modes.append(mode) or [])
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q26,Q29", "--mode", "hybrid", "--out", str(tmp_path)])
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert seen_modes == ["hybrid"] * 3
    assert report["meta"]["retrieval_mode"] == "hybrid" and report["meta"]["mode"] == "mock"
    assert report["meta"]["warmup_s"] is not None
    assert all(isinstance(q["search_s"], float) for q in report["questions"])
    assert report["summary"]["median_search_s"] is not None
    assert "retrieval hybrid | median search" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_ranks_are_recorded_per_hit(monkeypatch, tmp_path):
    import json
    from cee.retrieve import fts

    h = fts.Hit(chunk_id="MS-10K-2025#1", doc_id="MS-10K-2025", entity_id="MS", segment=None, doc_type="10-K",
                source_tier=1, published_at="2026-01-01", period_end=None, section=None, page=None,
                rank=0.123456, text="x")
    from cee.retrieve import modes
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: query(["MS"]))
    monkeypatch.setattr(modes, "search", lambda q, k=None, mode=None, trace=None: [h])
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q29", "--mode", "fts", "--out", str(tmp_path)])
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["questions"][0]["ranks"] == [0.1235]


# --- #126: third mode, constants, grid, selection rule, duplicate measure ------------------------

def _fake_bank(monkeypatch, seen=None):
    from cee.retrieve import fts, hybrid, modes

    def search(q, k=None, mode=None, trace=None):
        if seen is not None:
            seen.append((mode, fts.FLOOR, fts.MAX_PER_DOC, dict(hybrid.FLOOR), dict(hybrid.MAX_PER_DOC)))
        return []
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: query())
    monkeypatch.setattr(modes, "search", search)
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)


def _baseline(tmp_path):
    import json
    path = tmp_path / "ref.json"
    path.write_text(json.dumps({"questions": [], "summary": {"refusal_gap": {"ok": 0, "of": 0, "accuracy": None},
                                                            "refusal_all": {"ok": 0, "of": 0, "accuracy": None}}}),
                    encoding="utf-8")
    return str(path)


def test_hybrid_norerank_mode_is_accepted(monkeypatch, tmp_path):
    import json
    seen = []
    _fake_bank(monkeypatch, seen)
    er.main(["--questions", "Q29", "--mode", "hybrid-norerank", "--out", str(tmp_path)])
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert {s[0] for s in seen} == {"hybrid-norerank"}
    assert report["meta"]["retrieval_mode"] == "hybrid-norerank"
    from cee.retrieve import hybrid
    assert report["meta"]["constants"]["FLOOR"] == hybrid.FLOOR["hybrid-norerank"]
    assert report["meta"]["constants"]["MAX_PER_DOC"] == hybrid.MAX_PER_DOC["hybrid-norerank"]
    assert "logical CPUs" in report["meta"]["cpu"]


def test_no_option_leaves_constants_untouched(monkeypatch, tmp_path):
    from cee.retrieve import fts
    seen = []
    _fake_bank(monkeypatch, seen)
    er.main(["--questions", "Q29", "--mode", "fts", "--out", str(tmp_path)])
    assert {(s[1], s[2]) for s in seen} == {(0.3, 3)}
    assert (fts.FLOOR, fts.MAX_PER_DOC, fts.DUP_JACCARD) == (0.3, 3, 0.6)


def test_constants_map_per_mode_and_are_restored(monkeypatch, tmp_path):
    from cee.retrieve import fts, hybrid
    before = (dict(hybrid.FLOOR), dict(hybrid.MAX_PER_DOC))
    seen = []
    _fake_bank(monkeypatch, seen)
    er.main(["--questions", "Q29", "--mode", "fts", "--floor", "0.4", "--max-per-doc", "2", "--out", str(tmp_path / "a")])
    assert seen[-1][1:3] == (0.4, 2) and seen[-1][3] == before[0]
    er.main(["--questions", "Q29", "--mode", "hybrid", "--floor", "0.2", "--max-per-doc", "5",
             "--out", str(tmp_path / "b")])
    mode, floor, mpd, hf, hm = seen[-1]
    assert (floor, mpd) == (0.3, 3)  # fts untouched in a hybrid run
    assert hf["hybrid"] == 0.2 and hm["hybrid"] == 5
    assert (hf["hybrid-norerank"], hm["hybrid-norerank"]) == tuple(
        b["hybrid-norerank"] for b in before)
    # restored after the run
    assert (fts.FLOOR, fts.MAX_PER_DOC, fts.DUP_JACCARD) == (0.3, 3, 0.6)
    assert (dict(hybrid.FLOOR), dict(hybrid.MAX_PER_DOC)) == before


def test_dup_jaccard_option_is_gone(monkeypatch, tmp_path):
    # #211: DUP_JACCARD is fts.DUP_JACCARD in every mode; the #126 option was removed
    _fake_bank(monkeypatch)
    with pytest.raises(SystemExit):
        er.main(["--questions", "Q29", "--mode", "hybrid", "--dup-jaccard", "0.5", "--out", str(tmp_path)])


def test_grid_needs_a_baseline(monkeypatch, tmp_path, capsys):
    _fake_bank(monkeypatch)
    with pytest.raises(SystemExit):
        er.main(["--questions", "Q29", "--mode", "fts", "--floor", "0.2,0.3", "--out", str(tmp_path)])
    assert "--baseline" in capsys.readouterr().err


def test_grid_writes_one_folder_per_point_and_a_pick(monkeypatch, tmp_path):
    import json
    seen = []
    _fake_bank(monkeypatch, seen)
    er.main(["--questions", "Q29", "--mode", "hybrid-norerank", "--floor", "0,0.2", "--max-per-doc", "2,3",
             "--baseline", _baseline(tmp_path), "--out", str(tmp_path / "grid")])
    names = sorted(p.name for p in (tmp_path / "grid").iterdir() if p.is_dir())
    assert names == ["f0.0-m2", "f0.0-m3", "f0.2-m2", "f0.2-m3"]
    grid = json.loads((tmp_path / "grid" / "grid.json").read_text(encoding="utf-8"))
    assert len(grid["points"]) == 4 and grid["rule"] == er.SELECTION_RULE
    # all points tie: the mode's default (0/3) wins
    assert grid["choice"]["pick"]["floor"] == 0.0 and grid["choice"]["pick"]["max_per_doc"] == 3
    assert "Pick" in (tmp_path / "grid" / "grid.md").read_text(encoding="utf-8")
    assert len(seen) == 1 + 4  # one warm-up, then one search per point and question


def _point(floor, mpd, passages=0.4, docs=0.8, n_pass=28, gap=(5, 5), all_=(10, 10), forbidden=0):
    acc = lambda ok, of: {"ok": ok, "of": of, "accuracy": round(ok / of, 3)}  # noqa: E731
    return {"floor": floor, "max_per_doc": mpd, "run": er.point_name(floor, mpd),
            "summary": {"tier1_passage_recall": passages, "tier1_doc_recall": docs, "pass": n_pass,
                        "refusal_gap": acc(*gap), "refusal_all": acc(*all_), "forbidden_hits": forbidden}}


REF = {"refusal_gap": {"ok": 5, "of": 5, "accuracy": 1.0}, "refusal_all": {"ok": 10, "of": 10, "accuracy": 1.0}}


def test_choose_eligibility():
    pts = [_point(0.2, 2, passages=0.9, forbidden=1), _point(0.3, 2, passages=0.8, gap=(4, 5)),
           _point(0.4, 2, passages=0.7, all_=(9, 10)), _point(0.4, 3, passages=0.5)]
    c = er.choose(pts, REF, "fts")
    assert c["pick"]["floor"] == 0.4 and c["pick"]["max_per_doc"] == 3
    assert set(c["not_eligible"]) == {"f0.2-m2", "f0.3-m2", "f0.4-m2"}
    assert er.choose(pts[:3], REF, "fts")["pick"] is None


def test_choose_tie_breaks_in_order():
    pick = lambda pts, mode="fts": (lambda c: (c["pick"]["floor"], c["pick"]["max_per_doc"]))(er.choose(pts, REF, mode))  # noqa: E731
    assert pick([_point(0.2, 2, passages=0.41), _point(0.3, 3, passages=0.4)]) == (0.2, 2)          # passages
    assert pick([_point(0.2, 2, docs=0.81), _point(0.3, 3)]) == (0.2, 2)                              # doc recall
    assert pick([_point(0.2, 2, n_pass=29), _point(0.3, 3)]) == (0.2, 2)                              # PASS
    assert pick([_point(0.4, 2), _point(0.3, 3)]) == (0.3, 3)                                          # default
    assert pick([_point(0.2, 3), _point(0.4, 3)], "hybrid") == (0.4, 3)                               # higher FLOOR
    assert pick([_point(0.2, 4), _point(0.2, 2)], "hybrid") == (0.2, 2)                               # smaller MAX
    assert pick([_point(0.0, 2), _point(0.0, 3)], "hybrid") == (0.0, 3)                               # hybrid default


def test_trigrams_follow_pg_trgm():
    assert er.trigrams("Cat") == {"  c", " ca", "cat", "at "}
    assert er.trigrams("a-b") == {"  a", " a ", "  b", " b "}
    assert er.trigram_similarity("cat", "cat") == 1.0
    assert er.trigram_similarity("", "cat") == 0.0
    assert er.trigram_similarity("word", "cord") == pytest.approx(2 / 8)  # "ord", "rd " shared; pg_trgm gives 0.25


def test_duplicate_measure_counts_pairs_over_the_limit():
    base = "net new assets rose in the quarter as advisors joined the firm from competitors"
    d = er.duplicates([base, base + " today", "something else entirely about bank deposits and rates"])
    assert d["pairs_trigram_over"] == 1 and d["max_trigram"] > 0.9
    assert d["pairs_5gram_over"] == 1 and d["max_5gram"] > 0.9
    assert er.duplicates(["only one"]) == {"max_trigram": 0.0, "pairs_trigram_over": 0, "max_5gram": 0.0,
                                           "pairs_5gram_over": 0}
def test_k_defaults_to_the_app_budget_and_is_recorded(monkeypatch, tmp_path):
    # #181: without --k each question gets fts.budget(q); the record carries k, passages and chars
    import json

    from cee.retrieve import fts

    seen = []
    five = ["MS", "SCHW", "EDJ", "MER", "RJF"]
    monkeypatch.setattr(fts, "resolve", lambda text, today=None: query(five))
    monkeypatch.setattr(fts, "search", lambda q, k, trace=None: seen.append(k) or real_hits())
    monkeypatch.setattr(er, "corpus_types", lambda: (set(), "test", {}))
    monkeypatch.setattr(er, "substitutes", lambda: SUBS)
    er.main(["--questions", "Q22", "--out", str(tmp_path / "budget")])
    er.main(["--questions", "Q22", "--k", "20", "--out", str(tmp_path / "fixed")])
    # each run: one untimed warm-up search (#126), then the question
    assert seen == [fts.budget(query(five))] * 2 + [20, 20] and seen[0] == 30
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
    hits = [types.SimpleNamespace(text="x" * 10), types.SimpleNamespace(text="y" * 7)]
    assert er.prompt_size(20, hits) == {"k": 20, "passages": 2, "chars": 17, "tokens_est": 4}


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
