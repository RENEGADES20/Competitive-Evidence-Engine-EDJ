"""The system's modules, for the Architecture page and the README diagram (#270).

One source of text: `views/architecture_page.py` draws these modules, and
`tests/test_architecture_page.py` checks that the README mermaid nodes carry the same labels
(`label<br/>sub`). Change a module here, then the README and docs/ARCHITECTURE.md diagrams.
No firm figures here: the page explains how the system works, it is not evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

KINDS = {"data": "Data", "code": "Code step", "ai": "AI step", "ai+code": "AI + code step"}
PRINCIPLE = "AI reads and writes; code decides and checks."


@dataclass(frozen=True)
class Module:
    id: str      # also the mermaid node id
    label: str   # first line of the node
    sub: str     # second line of the node
    kind: str    # a key of KINDS
    stage: str   # offline | online
    does: str    # what it does
    who: str     # who does it: the model, code, or both (and which file)
    rule: str    # the rule it enforces

    @property
    def node_text(self) -> str:
        """The node text in the README mermaid block."""
        return f"{self.label}<br/>{self.sub}"


MODULES: tuple[Module, ...] = (
    Module("S", "Public sources", "filings, decks, calls, press, research", "data", "offline",
           "SEC filings, Form ADV brochures, supplements, investor decks, call transcripts, press "
           "releases, trade press and research reports, collected ahead of time.",
           "Collected by scripts; each document gets a row in data/manifest.csv.",
           "Every document is traceable: a manifest row with its source and tier."),
    Module("I", "Ingest", "parse, chunk, tag firm, segment, date", "code", "offline",
           "Parses each document, cuts it into passages inside its sections, and tags each passage "
           "with firm, segment and date.",
           "Code (src/cee/ingest/).",
           "Chunks never cross a section boundary; PDF passages keep their page number."),
    Module("DB", "Postgres", "documents, chunks, manifest; dated snapshots", "data", "offline",
           "Stores the documents and passages. The team shares one dated snapshot, so everyone "
           "answers from the same corpus. Embeddings (pgvector) are optional.",
           "Data (db/schema.sql; snapshots via scripts/restore and build-snapshot).",
           "An answer may only cite a passage stored here."),
    Module("Q", "Question", "plain language", "data", "online",
           "The strategist's question, typed on the Ask page, with optional firm, date and keyword "
           "filters.",
           "The user.",
           "The answer hands any 'should' back to the strategist: nothing normative."),
    Module("R", "Resolve firms", "aliases, segments, time window", "code", "online",
           "Finds the firms, segments and time window the question is about, from aliases in "
           "config/entities.yaml.",
           "Code (src/cee/retrieve/fts.py, resolve).",
           "Firms and windows come from rules and config, not from the model."),
    Module("P", "Plan sub-questions", "aspects x firms", "ai+code", "online",
           "The planner names the aspects the question asks about; code expands firms x aspects "
           "into sub-questions.",
           "AI names the aspects (one planner call); code builds the sub-questions "
           "(src/cee/retrieve/planner.py).",
           "Model calls follow the decomposition, no fixed number; every sub-question keeps the "
           "SQL filters."),
    Module("F", "Search", "per sub-question, filters in SQL", "code", "online",
           "Searches the stored passages for each sub-question: full-text search on main, hybrid "
           "(keyword + embeddings) on the exp/hybrid branch.",
           "Code (src/cee/retrieve/fts.py, search).",
           "Hard filters live in SQL: firm, segment and time window are WHERE clauses, not prompt "
           "instructions."),
    Module("X", "Extract per firm", "fact, not disclosed, not found, other figure", "ai", "online",
           "Reads the retrieved passages of one firm and fills one cell per sub-question: a fact, "
           "not disclosed, not found, or a different quantity.",
           "AI, one call per firm with a strict schema (src/cee/answer/extract.py); code then checks "
           "each cell.",
           "Each item cites retrieved passages; code rejects other ids and flags quotes and figures "
           "not found in the cited passage."),
    Module("C", "Re-search", "empty cells, one round", "ai+code", "online",
           "For a cell left 'not found', searches once more with wider words, then extracts again "
           "from the new passages.",
           "Code re-searches; AI re-extracts (src/cee/answer/extract.py, run_map).",
           "One round only, with the same SQL filters; passages already used are excluded."),
    Module("M", "Evidence matrix", "behavior, definitions, caveats", "code", "online",
           "Puts the cells in a firm x aspect matrix and decides the answer's behavior, the metric "
           "definitions, what may be computed, the caveats and the named gaps.",
           "Code (src/cee/answer/matrix.py; config/metric_definitions.yaml, config/entities.yaml).",
           "Code decides; the model never picks the behavior or a definition."),
    Module("W", "Write the answer", "from the matrix only", "ai", "online",
           "Writes the cited answer from the evidence matrix, for the behavior code decided. A "
           "refusal or an empty matrix is written by code with no call.",
           "AI, one reduce call (src/cee/answer/reduce.py), or code.",
           "Cites only passages in the matrix; never reads raw passages."),
    Module("K", "Check", "citations, numbers, caveats, gaps", "code", "online",
           "Checks every citation and figure, inserts the caveats and names each gap with the "
           "source that would fill it.",
           "Code (src/cee/answer/validate.py, reduce.py).",
           "Citations only to retrieved chunk IDs; unmatched ones are flagged, never silently "
           "dropped. Caveats are inserted by code."),
    Module("U", "Streamlit app", "answer, sources, coverage", "code", "online",
           "Shows the answer with source labels and tiers, opens each cited passage in the source "
           "viewer, and shows what the corpus covers. Every query is logged.",
           "Code (src/cee/app/).",
           "Every citation opens the stored passage; caveats and gaps are never hidden."),
)

EDGES: tuple[tuple[str, str], ...] = (
    ("S", "I"), ("I", "DB"),
    ("Q", "R"), ("R", "P"), ("P", "F"), ("DB", "F"), ("F", "X"), ("X", "C"), ("C", "M"),
    ("M", "W"), ("W", "K"), ("K", "U"),
)


def by_id() -> dict[str, Module]:
    return {m.id: m for m in MODULES}
