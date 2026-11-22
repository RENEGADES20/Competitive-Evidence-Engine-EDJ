"""#272: scripts/latency_report.py on fake raw records (0 calls)."""
import json

from scripts import latency_report as L


def _rec(path, wall, out=100, reasoning=50, ttft=None, stop="tool_calls"):
    rec = {"wall_s": wall, "stop_reason": stop, "usage": {"output_tokens": out, "reasoning_tokens": reasoning}}
    if ttft is not None:
        rec["ttft_s"] = ttft
    path.write_text(json.dumps(rec), encoding="utf-8")


def test_critical_path_first_evidence_and_stages(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    _rec(raw / "Q5-plan-aa11.json", 10)
    _rec(raw / "Q5-map.a1.MS-bb22.json", 30, ttft=2.0)
    _rec(raw / "Q5-map.a2.MS.b1-cc33.json", 50, ttft=4.0)
    _rec(raw / "Q5-remap.a1.MS-dd44.json", 5)
    _rec(raw / "Q5-reduce-ee55.json", 20, stop="length")
    _rec(raw / "Q10-plan-ff66.json", 1)
    _rec(raw / "Q10-map.EDJ-0a0a.json", 3)          # a W11 per-firm id reads the same
    _rec(raw / "Q10-reduce-1b1b.json", 2)
    (raw / "notes.txt").write_text("not a record", encoding="utf-8")
    rows = L.load(raw)
    qs = {q["q"]: q for q in L.per_question(rows)}
    assert qs["Q5"]["critical_s"] == 10 + 50 + 5 + 20 and qs["Q5"]["first_evidence_s"] == 40
    assert qs["Q5"]["map_calls"] == 2 and qs["Q5"]["remap_calls"] == 1 and qs["Q5"]["cut"] == 1
    assert qs["Q10"]["critical_s"] == 6 and list(qs) == ["Q5", "Q10"]
    stages = {s["stage"]: s for s in L.per_stage(rows)}
    assert stages["map"]["calls"] == 3 and stages["map"]["ttft_p50"] == 3.0 and stages["map"]["wall_max"] == 50
    assert stages["plan"]["reasoning_share"] == 0.5
    s = L.summary(list(qs.values()))
    assert s["critical_p50"] == (6 + 85) / 2 and s["cut"] == 1
    assert L.main([str(tmp_path), "--questions", "Q10", "--json", str(tmp_path / "o.json")]) == 0
    assert "| Q10 |" in capsys.readouterr().out and json.loads((tmp_path / "o.json").read_text())["summary"]["questions"] == 1


def test_percentiles_interpolate():
    assert L.pct([1, 2, 3, 4], 50) == 2.5 and L.pct([5], 90) == 5 and L.pct([], 50) is None
    assert L.pct([None, 10, 20], 100) == 20


def test_retrieval_times_from_the_report(tmp_path, capsys):
    """#272 (exp/hybrid): search_s and embed_s per question from the run's report.json."""
    raw = tmp_path / "raw"
    raw.mkdir()
    _rec(raw / "Q5-plan-aa11.json", 10)
    _rec(raw / "Q5-map.a1.MS-bb22.json", 30)
    _rec(raw / "Q5-reduce-ee55.json", 20)
    (tmp_path / "report.json").write_text(json.dumps({"questions": [
        {"id": "Q5", "search_s": 9.5, "embed_s": 0.4, "embed_calls": 3}]}), encoding="utf-8")
    assert L.main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Retrieval (search_s): p50 9.5 s" in out and "| Q5 | 9.5 | 0.4 | 10 |" in out
    q = L.per_question(L.load(raw), L.load_retrieval(tmp_path / "report.json"))[0]
    assert q["with_retrieval_s"] == 69.5 and q["first_with_retrieval_s"] == 49.5 and q["embed_calls"] == 3


def test_no_report_keeps_the_old_table(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    _rec(raw / "Q5-plan-aa11.json", 10)
    assert L.main([str(raw)]) == 0
    assert "Retrieval" not in capsys.readouterr().out
