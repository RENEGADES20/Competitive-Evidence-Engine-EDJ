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


def _prefix_rec(path, wall, role, inp, hit, wait=None, cached=None, pchars=900, rchars=1000):
    path.write_text(json.dumps({"wall_s": wall, "stop_reason": "tool_calls", "prefix_role": role,
                                "gate_wait_s": wait, "leader_cached": cached, "prefix_chars": pchars,
                                "request_chars": rchars, "usage": {"output_tokens": 10, "input_tokens": inp,
                                                                   "cache_hit_tokens": hit}}), encoding="utf-8")


def test_gate_wait_joins_the_critical_path_and_the_cache_table(tmp_path):
    """#283: map time = gate wait + wall; cache-hit share per stage and role; the B4 probe rule."""
    raw = tmp_path
    _rec(raw / "Q10-plan-aa.json", 2)
    _prefix_rec(raw / "Q10-map.a1.EDJ-b1.json", 30, "leader", 1000, 0, wait=0)
    for n in range(2, 8):
        _prefix_rec(raw / f"Q10-map.a{n}.EDJ-b{n}.json", 20, "follower", 1000, 800, wait=12)
    _rec(raw / "Q10-reduce-cc.json", 10)
    rows = L.load(raw)
    q = L.per_question(rows)[0]
    assert q["map_max_s"] == 32 and q["critical_s"] == 2 + 32 + 10 and q["first_evidence_s"] == 2 + 30
    cache = {c["group"]: c for c in L.cache_table(rows)}
    assert cache["map"]["share"] == round(4800 / 7000, 3) and cache["map follower"]["gate_wait_p50"] == 12
    p = L.probe_rule(rows)
    assert p["followers"] == 6 and p["share"] == round(4800 / 5400, 3) and p["gate"] == "first_chunk"
    for n in range(2, 8):   # low share -> done
        _prefix_rec(raw / f"Q10-map.a{n}.EDJ-b{n}.json", 20, "follower", 1000, 100, wait=12)
    assert L.probe_rule(L.load(raw))["gate"] == "done"
    for n in range(2, 8):   # leader reused: followers do not count -> inconclusive -> done
        _prefix_rec(raw / f"Q10-map.a{n}.EDJ-b{n}.json", 20, "follower", 1000, 900, wait=0, cached=True)
    p = L.probe_rule(L.load(raw))
    assert p["followers"] == 0 and p["gate"] == "done" and p["why"].startswith("inconclusive")
