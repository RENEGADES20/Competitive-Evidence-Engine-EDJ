"""docs/source_matrix.csv (C2, #3): valid values, and every tier 3-4 source the question bank
expects is covered by at least one row. Reads files only; no network, no database."""
import csv
import re

import pytest
import yaml

from cee.answer.validate import SOURCE_NAMES
from cee.config import REPO_ROOT, entities_config

MATRIX = REPO_ROOT / "docs" / "source_matrix.csv"
NOTES = REPO_ROOT / "docs" / "SOURCE_MATRIX.md"
QUESTIONS = REPO_ROOT / "evals" / "questions.yaml"

COLUMNS = ["source_id", "tier", "entity_id", "segment", "doc_type", "source_name", "publisher",
           "owner", "url", "sample_url", "url_pattern", "format", "access", "cost", "terms_url",
           "terms_read_on", "scraping", "full_text_storage", "excerpts", "adr000_ref", "robots",
           "rss_url", "expected_cadence", "earliest_available", "date_field", "notes",
           "manual_check_on", "last_checked", "url_status", "sample_status"]
TIER34_TYPES = {"transcript", "deck", "supplement", "press", "trade", "monthly"}
ALL_MEANS = {"MS", "SCHW", "EDJ", "MER", "RJF"}     # trade-press rows (entity ALL); BAC only via GWIM
ENUMS = {
    "tier": {"3", "4"},
    "owner": {"C1", "C2"},
    "format": {"html", "pdf", "xlsx", "audio-only", "rss"},
    "access": {"free", "free-registration", "metered", "paywall", "licensed", "library", "unknown"},
    "scraping": {"allowed", "forbidden", "silent", "unclear"},
    "full_text_storage": {"allowed", "forbidden", "silent", "unclear"},
    "excerpts": {"allowed", "forbidden", "silent", "unclear"},
    "expected_cadence": {"daily", "weekly", "monthly", "quarterly", "annual", "ad hoc"},
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PARTIAL_DATE = re.compile(r"^(\d{4}(-\d{2}(-\d{2})?)?|TODO-verify)$")


@pytest.fixture(scope="module")
def rows():
    raw = MATRIX.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "save without BOM (edit in a text editor, not Excel)"
    assert b"\r\n" not in raw, "LF line endings only"
    with open(MATRIX, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return list(reader)


def test_values_are_valid(rows):
    entities = {e["id"]: e for e in entities_config()["entities"]}
    problems = []
    for r in rows:
        sid = r["source_id"]
        if not re.fullmatch(r"[A-Z0-9]+(-[A-Z0-9]+)+", sid):
            problems.append(f"{sid}: source_id must be UPPER-CASE-WITH-HYPHENS")
        for col, allowed in ENUMS.items():
            if r[col] not in allowed:
                problems.append(f"{sid}: {col}={r[col]!r} not in {sorted(allowed)}")
        if r["entity_id"] not in entities and r["entity_id"] != "ALL":
            problems.append(f"{sid}: unknown entity_id {r['entity_id']!r}")
        if r["doc_type"] not in SOURCE_NAMES or r["doc_type"] not in TIER34_TYPES:
            problems.append(f"{sid}: doc_type {r['doc_type']!r} is not a tier 3-4 type in validate.SOURCE_NAMES")
        if (r["tier"] == "4") != (r["doc_type"] == "trade"):
            problems.append(f"{sid}: tier 4 if and only if doc_type is trade")
        segments = entities.get(r["entity_id"], {}).get("segment_aliases") or {}
        if r["segment"] and r["segment"] not in segments:
            problems.append(f"{sid}: segment {r['segment']!r} not in entities.yaml for {r['entity_id']}")
        if not r["url"].startswith(("https://", "http://")):
            problems.append(f"{sid}: url missing")
        if r["sample_url"] and not r["sample_url"].startswith(("https://", "http://")):
            problems.append(f"{sid}: sample_url must be a URL or empty (explain in notes)")
        for col in ("url", "sample_url"):
            if not r[col].isascii() or any(ch.isspace() for ch in r[col]):
                problems.append(f"{sid}: {col} must be ASCII with no spaces (percent-encode it)")
        if not r["date_field"]:
            problems.append(f"{sid}: date_field empty (write 'none' if the page has no date)")
        if not PARTIAL_DATE.match(r["earliest_available"]):
            problems.append(f"{sid}: earliest_available {r['earliest_available']!r} not YYYY[-MM[-DD]] or TODO-verify")
        if not DATE.match(r["terms_read_on"]):
            problems.append(f"{sid}: terms_read_on must be the date the terms were read (YYYY-MM-DD)")
        verdicts = [r["scraping"], r["full_text_storage"], r["excerpts"]]
        if any(v in ("silent", "unclear") for v in verdicts) and not re.fullmatch(r"T-\d{2}", r["adr000_ref"]):
            problems.append(f"{sid}: silent/unclear terms need an adr000_ref like T-01")
    assert not problems, "\n".join(problems)


def test_source_ids_are_unique(rows):
    ids = [r["source_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_adr000_refs_are_explained_in_the_notes(rows):
    notes = NOTES.read_text(encoding="utf-8")
    missing = sorted({r["adr000_ref"] for r in rows if r["adr000_ref"]} - set(re.findall(r"T-\d{2}", notes)))
    assert not missing, f"explain these in docs/SOURCE_MATRIX.md: {missing}"


def test_merrill_press_is_entity_mer(rows):
    """specs/transcripts-ir.md: Merrill press releases are stored as entity MER, not BAC (Q4, Q27)."""
    assert any(r["entity_id"] == "MER" and r["doc_type"] == "press" for r in rows)


def _expected_patterns():
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    patterns = {}
    for q in questions:
        for p in q.get("expected_sources", []):
            entity, rest = p.split(":", 1)
            doc_type, _, segment = rest.partition("#")
            if doc_type in TIER34_TYPES or doc_type == "*":
                patterns.setdefault(p, []).append(q["id"])
    return patterns


def _serves(row, pattern):
    entity, rest = pattern.split(":", 1)
    doc_type, _, segment = rest.partition("#")
    if row["entity_id"] != entity and not (row["entity_id"] == "ALL" and entity in ALL_MEANS):
        return False
    if doc_type != "*" and row["doc_type"] != doc_type:
        return False
    return not segment or row["segment"] == segment


def test_every_tier34_pattern_in_the_question_bank_is_covered(rows):
    patterns = _expected_patterns()
    assert patterns, "no tier 3-4 expected_sources found in evals/questions.yaml"
    uncovered = {p: qs for p, qs in patterns.items() if not any(_serves(r, p) for r in rows)}
    assert not uncovered, f"no matrix row for: {uncovered}"
