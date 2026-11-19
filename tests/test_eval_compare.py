"""scripts/eval_compare.py: the three-mode report from tiny fake runs. No DB, no model, no network."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "eval_compare.py"
spec = importlib.util.spec_from_file_location("eval_compare", SCRIPT)
ec = importlib.util.module_from_spec(spec)
sys.modules["eval_compare"] = ec
spec.loader.exec_module(ec)


def _q(qid, status, found, chunk_ids, ranks=None, refusal_ok=True, behavior="answer"):
    return {"id": qid, "status": status, "expected_behavior": behavior, "coverage": 1.0, "hit_patterns": 1,
            "available_patterns": 1, "chunk_ids": chunk_ids, "ranks": ranks or [0.5] * len(chunk_ids),
            "forbidden": [], "misleading": [], "refusal_ok": refusal_ok, "search_s": 0.1,
            "recall": {"passages_found": found, "passages": 2}}


def _report(mode, floor, qs):
    acc = {"ok": 1, "of": 1, "accuracy": 1.0}
    return {"meta": {"snapshot": "corpus-test", "as_of": "2026-10-29", "k": 20, "min_coverage": 0.5, "commit": "abc",
                     "run_id": mode, "constants": {"FLOOR": floor, "MAX_PER_DOC": 3, "DUP_JACCARD": 0.6},
                     "warmup_s": 1.0, "cpu": "test cpu", "real_calls": 0, "mode": "mock"},
            "summary": {"tier1_doc_recall": 0.5, "tier1_passage_recall": 0.25, "refusal_gap": acc, "refusal_all": acc,
                        "median_search_s": 0.1, "p90_search_s": 0.1, "max_search_s": 0.1,
                        "dup_pairs_trigram_over": 0, "dup_max_trigram": 0.3, "dup_pairs_5gram_over": 0,
                        "dup_max_5gram": 0.1},
            "questions": qs}


def _runs():
    fts = _report("fts", 0.3, [_q("Q1", "PASS", 1, ["A#1"]), _q("Q29", "PASS", 1, ["MS-10K-2025#153"],
                                                                  behavior="gap_with_adjacent")])
    plain = _report("hybrid-norerank", 0.2, [_q("Q1", "PASS", 2, ["A#1", "A#2"]),
                                             _q("Q29", "PASS", 1, ["MS-10K-2025#170"], behavior="gap_with_adjacent")])
    rerank = _report("hybrid", 0.2, [_q("Q1", "PASS", 1, ["A#1"]),
                                     _q("Q29", "FAIL", 0, ["MS-10K-2025#702"], [0.95], behavior="gap_with_adjacent")])
    return {"fts": fts, "hybrid-norerank": plain, "hybrid": rerank}


def test_report_has_every_mode_and_the_q29_note():
    runs = _runs()
    grid = {"rule": "the rule", "points": [{"floor": 0.2, "max_per_doc": 3, "summary": runs["hybrid"]["summary"]
                                            | {"pass": 1, "forbidden_hits": 0}}],
            "choice": {"pick": {"floor": 0.2, "max_per_doc": 3}, "reason": "eligible 1 of 1", "not_eligible": {}}}
    diag = {"Q29": {"pool_size": 50, "top5": [["MS-10K-2025#702", 0.95]],
                    "watch": [{"chunk": "MS-10K-2025#153", "role": "must_return", "kw_rank_in_firm": 12,
                               "vec_rank_in_firm": None, "in_pool": True, "sigmoid": 0.0, "pool_rank": 47,
                               "in_hybrid_hits": False}]}}
    text, summary = ec.build(runs, runs, {"hybrid": grid}, diag, "Hand-written finding.")
    for mode in ec.MODES:
        assert f"`{mode}`" in text
    assert "Hand-written finding." in text and "the rule" in text
    assert "hybrid: PASS -> FAIL" in text                                  # Q29 change vs fts
    assert "`MS-10K-2025#702` returned" in text and "not on Q29's `must_not_return` list" in text
    assert "sigmoid 0.0, pool rank 47 of 50" in text
    assert summary["rerank_vs_norerank"] == {"rerank_more_passages": 0, "rerank_fewer_passages": 2, "same_passages": 0}
    assert summary["per_question"]["hybrid"]["Q29"] == "FAIL"
    assert [r["real_calls"] for r in summary["chosen"]] == [0, 0, 0]


def test_main_writes_report_and_summary(tmp_path):
    paths = {}
    for mode, report in _runs().items():
        paths[mode] = tmp_path / f"{mode}.json"
        paths[mode].write_text(json.dumps(report), encoding="utf-8")
    args = [a for m in ec.MODES for a in ("--chosen", f"{m}={paths[m]}")] + ["--out", str(tmp_path / "out")]
    assert ec.main(args) == 0
    assert (tmp_path / "out" / "report.md").is_file()
    assert json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))["chosen"][0]["mode"] == "fts"


def test_reranker_ablation_uses_the_same_constants():
    runs = _runs()
    point = lambda r, f, m: {"floor": f, "max_per_doc": m, "summary": r["summary"] | {"pass": 1}}  # noqa: E731
    grids = {m: {"rule": "r", "points": [point(runs[m], 0.4, 4)],
                 "choice": {"pick": {"floor": 0.4, "max_per_doc": 4}, "reason": "x", "not_eligible": {}}}
             for m in ("hybrid", "hybrid-norerank")}
    same = _report("hybrid-norerank", 0.4, [_q("Q1", "PASS", 1, ["A#1"]),
                                            _q("Q29", "FAIL", 0, ["MS-10K-2025#702"], behavior="gap_with_adjacent")])
    text, summary = ec.build(runs, {}, grids, None, None, same)
    assert "| 0.4 | 4 | 1 / 1 |" in text                     # both modes at the same grid point
    assert summary["rerank_vs_norerank"] == {"rerank_more_passages": 0, "rerank_fewer_passages": 0, "same_passages": 2}


def test_report_names_its_rebuild_command_and_uses_lf(tmp_path):
    paths = {}
    for mode, report in _runs().items():
        paths[mode] = tmp_path / f"{mode}.json"
        paths[mode].write_text(json.dumps(report), encoding="utf-8")
    args = [a for m in ec.MODES for a in ("--chosen", f"{m}={paths[m]}")] + ["--out", str(tmp_path / "out")]
    ec.main(args)
    raw = (tmp_path / "out" / "report.md").read_bytes()
    assert b"\r" not in raw and b"\r" not in (tmp_path / "out" / "summary.json").read_bytes()
    assert "## How this report was built" in raw.decode("utf-8")
    assert "python scripts/eval_compare.py --chosen fts=" in raw.decode("utf-8")


# --- #211: --run comparison and the #212 decision -------------------------------------------------

def _retest(passages, gap=(5, 5), keyed=(22, 22), forbidden=0, stage="none"):
    r = _report("x", 0.3, [{**_q("Q7", "PASS", 0, ["B#1"]), "recall_pool": 0.0, "recall_final": 0.0,
                            "passage_recall": 0.0, "pool_size": 40,
                            "recall": {"passages_found": 0, "passages": 1,
                                       "rows": [{"ids": ["MS-10K-2025#153"], "stage": stage}]}}])
    r["questions"][0]["forbidden"] = ["X#1"] * forbidden
    r["summary"] |= {"tier1_passage_recall": passages, "recall_pool": 0.5, "recall_final": 0.4,
                     "tier1_recall_pool": 0.6, "tier1_recall_final": passages, "with_rows": 1, "tier1_with_rows": 1,
                     "passages": 20, "tokens_est": 100,
                     "refusal_gap": {"ok": gap[0], "of": gap[1], "accuracy": gap[0] / gap[1]},
                     "refusal_all": {"ok": keyed[0], "of": keyed[1], "accuracy": keyed[0] / keyed[1]}}
    return r


def test_decision_needs_all_four_conditions():
    fts = ec.run_row("fts", _retest(0.597))
    assert ec.decide(fts, ec.run_row("hybrid-norerank", _retest(0.627)))["runs_212"] is True   # exactly +0.03
    no = ec.decide(fts, ec.run_row("hybrid-norerank", _retest(0.626)))
    assert no["runs_212"] is False and "closed as not planned" in no["line"] and "A" in no["line"]
    for kw, cond in (({"gap": (4, 5)}, "B"), ({"keyed": (21, 22)}, "C"), ({"forbidden": 1}, "D")):
        d = ec.decide(fts, ec.run_row("hybrid-norerank", _retest(0.7, **kw)))
        assert d["runs_212"] is False and not d["checks"][cond]["ok"]


def test_retest_report_has_both_recall_columns_gate4_stages_and_the_decision(tmp_path):
    fts, plain = tmp_path / "fts.json", tmp_path / "plain.json"
    fts.write_text(json.dumps(_retest(0.597)), encoding="utf-8")
    found = _retest(0.6, stage="final")
    found["questions"][0] |= {"recall_pool": 1.0, "recall_final": 1.0}
    plain.write_text(json.dumps(found), encoding="utf-8")
    assert ec.main(["--run", f"fts={fts}", "--run", f"hybrid-norerank={plain}", "--out", str(tmp_path / "out")]) == 0
    text = (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    summary = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert "Tier-1 recall@pool" in text and "Tier-1 recall@final" in text and "not like-for-like" in text
    assert "**Decision: #212 is closed as not planned** (condition A not met)." in text
    assert "1-2 passages" in text and "ADR-010" in text
    q7 = next(g for g in summary["gate4_missed"] if g["q"] == "Q7")
    assert q7["stage"] == {"fts": "not in pool", "hybrid-norerank": "retrieved"}
    assert summary["modes"]["fts"]["mean_pool_size"] == 40 and summary["differs"] == ["Q7"]
    assert b"\r\n" not in (tmp_path / "out" / "report.md").read_bytes()
