"""#56: tier-1 questions carry concrete expected_doc_ids that exist in the manifest."""
import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = yaml.safe_load((ROOT / "evals/questions.yaml").read_text())["questions"]
MANIFEST = {r["doc_id"] for r in csv.DictReader((ROOT / "data/manifest.csv").open())}
TIER1 = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q11", "Q13", "Q17", "Q20", "Q22", "Q23",
         "Q25", "Q26", "Q27", "Q28", "Q29", "Q30"]


def by_id():
    return {q["id"]: q for q in QUESTIONS}


def test_tier1_set_matches_issue():
    assert sorted(q["id"] for q in QUESTIONS if q["tier"] == 1) == sorted(TIER1)


def test_every_tier1_question_has_doc_ids():
    qs = by_id()
    for qid in TIER1:
        ids = qs[qid].get("expected_doc_ids")
        assert ids, f"{qid} has no expected_doc_ids"
        assert len(ids) == len(set(ids)), f"{qid} lists a doc_id twice"
        assert qs[qid].get("expected_sources"), f"{qid} lost its expected_sources patterns"


def test_every_doc_id_is_in_manifest():
    missing = {q["id"]: [d for d in q.get("expected_doc_ids", []) if d not in MANIFEST] for q in QUESTIONS}
    assert not {k: v for k, v in missing.items() if v}


def test_bank_size_and_gap_share_unchanged():
    assert len(QUESTIONS) >= 30
    hard = [q for q in QUESTIONS if q["expected_behavior"] in ("gap_with_adjacent", "refuse")]
    assert len(hard) >= 5
    assert {q["id"] for q in QUESTIONS if q["trap"]} >= {"Q4", "Q27", "Q30"}
