"""#244 (ADR-021 rule 8): superseded expected behaviors and the gap / refuse share.

The bank is append-only; evals/behavior_supersede.yaml records a changed expectation without
rewriting a question. CLAUDE.md keeps the share of gap_with_adjacent + refuse questions at least
where it was (5/30), on the bank's own expected_behavior (raw) and after the supersede file
(effective).
"""
from fractions import Fraction
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = yaml.safe_load((ROOT / "evals/questions.yaml").read_text(encoding="utf-8"))["questions"]
SUPERSEDE = yaml.safe_load((ROOT / "evals/behavior_supersede.yaml").read_text(encoding="utf-8"))["supersedes"]
BEHAVIORS = {"answer", "answer_with_boundary", "gap_with_adjacent", "refuse"}
HARD = {"gap_with_adjacent", "refuse"}
FLOOR = Fraction(5, 30)


def _bank():
    return {q["id"]: q for q in QUESTIONS}


def _effective():
    eff = {q["id"]: q["expected_behavior"] for q in QUESTIONS}
    eff.update({s["id"]: s["expected_behavior"] for s in SUPERSEDE})
    return eff


def test_entries_are_unique_and_in_the_bank():
    ids = [s["id"] for s in SUPERSEDE]
    assert len(ids) == len(set(ids))
    assert set(ids) <= set(_bank())


def test_entries_match_the_bank_and_change_the_behavior():
    bank = _bank()
    for s in SUPERSEDE:
        assert s["bank_expected"] == bank[s["id"]]["expected_behavior"], s["id"]
        assert s["expected_behavior"] in BEHAVIORS, s["id"]
        assert s["expected_behavior"] != s["bank_expected"], s["id"]
        assert "ADR-021" in s["rule"], s["id"]
        assert s["reason"].strip(), s["id"]


def test_no_trap_is_superseded():
    bank = _bank()
    assert not [s["id"] for s in SUPERSEDE if bank[s["id"]]["trap"]]


def test_raw_gap_share_at_least_five_of_thirty():
    hard = [q for q in QUESTIONS if q["expected_behavior"] in HARD]
    assert Fraction(len(hard), len(QUESTIONS)) >= FLOOR


def test_effective_gap_share_at_least_five_of_thirty():
    eff = _effective()
    hard = [qid for qid, b in eff.items() if b in HARD]
    assert Fraction(len(hard), len(eff)) >= FLOOR, sorted(hard)
