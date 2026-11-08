"""scripts/chunk_dump.py remap (#84): old chunk IDs -> new IDs after a re-parse. No DB."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "chunk_dump.py"
spec = importlib.util.spec_from_file_location("chunk_dump", SCRIPT)
cd = importlib.util.module_from_spec(spec)
sys.modules["chunk_dump"] = cd
spec.loader.exec_module(cd)


def c(text, page=1):
    return {"section": "S", "page": page, "text": text}


OLD = {"D#0": c("cover"), "D#1": c("Sustaining Momentum Our Through Clients Eyes Strategy continues"),
       "D#2": c("Client Assets grew 15 percent"), "E#2": c("Client Assets grew 15 percent")}
NEW = {"D#0": c("cover"), "D#1": c("Sustaining Momentum", 4), "D#2": c("Our Through Clients Eyes Strategy continues", 5),
       "D#3": c("Client Assets grew 15 percent"), "E#2": c("Client Assets grew 15 percent")}


def test_unchanged_and_shifted_chunks_keep_their_text():
    m = cd.remap_ids(OLD, NEW, ["D#0", "D#2", "E#2"])
    assert m == {"D#0": ["D#0"], "D#2": ["D#3"], "E#2": ["E#2"]}


def test_split_chunk_maps_to_both_parts_best_first():
    assert cd.remap_ids(OLD, NEW, ["D#1"]) == {"D#1": ["D#2", "D#1"]}


def test_other_documents_are_never_matched():
    old = {"D#5": c("only in another document")}
    new = {"E#5": c("only in another document"), "D#0": c("cover")}
    assert cd.remap_ids(old, new, ["D#5"]) == {"D#5": []}


def test_chunk_that_gained_a_moved_part_keeps_its_match():
    old = {"D#7": c("3Q26 vs. 3Q25 Core Net New Assets $190B")}
    new = {"D#6": c("Schwab is leading today", 4),
           "D#7": c("Our strategy continues to drive record results.\n\n3Q26 vs. 3Q25 Core Net New Assets $190B", 5),
           "D#20": c("Core Net New Assets definition")}
    assert cd.remap_ids(old, new, ["D#7"]) == {"D#7": ["D#7"]}
