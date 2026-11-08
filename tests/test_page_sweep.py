"""scripts/page_sweep.py scoring (#84): OK / PASS-SAMEPAGE / MISPLACED on fake page texts. No DB, no PDF."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "page_sweep.py"
spec = importlib.util.spec_from_file_location("page_sweep", SCRIPT)
ps = importlib.util.module_from_spec(spec)
sys.modules["page_sweep"] = ps
spec.loader.exec_module(ps)

PAGES = {4: ps.compact("Sustaining Momentum Delivering for Clients"),
         5: ps.compact("Our Through Clients' Eyes Strategy continues to drive growth. Bank Lending1 (EOP)"),
         6: ps.compact("Disclosures")}


def test_chunk_on_its_page_is_ok_even_with_fused_words():
    assert ps.score("Bank Lending (EOP) growth", 5, PAGES)[0] == "OK"
    assert ps.score("requirewealth managers", 1, {1: ps.compact("require wealthmanagers")})[0] == "OK"


def test_chunk_mostly_on_the_next_page_is_misplaced():
    status, own, best = ps.score("Sustaining Our Through Clients Eyes Strategy continues to drive growth", 4, PAGES)
    assert status == "MISPLACED" and best == 5 and own < 0.9


def test_chunk_below_90_with_no_better_page_passes_samepage():
    status, own, best = ps.score("Disclosures footnote glossary text", 6, PAGES)
    assert status == "PASS-SAMEPAGE" and best == 6 and own < 0.9
