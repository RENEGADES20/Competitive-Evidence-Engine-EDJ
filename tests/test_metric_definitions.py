"""config/metric_definitions.yaml (#46, Q11): structure offline; chunk IDs and verbatim quotes
against the local Postgres (skipped if it is down)."""
import csv
import re

import psycopg
import pytest
import yaml

from cee.config import MANIFEST_PATH, REPO_ROOT, settings

FIRMS = {"EDJ", "MS", "SCHW", "BAC", "RJF"}
METRICS = {"advisor_headcount", "net_new_assets"}
STATUSES = {"quoted", "closest_metric", "not_disclosed"}


def definitions():
    return yaml.safe_load((REPO_ROOT / "config" / "metric_definitions.yaml").read_text())["definitions"]


def manifest_ids():
    with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
        return {r["doc_id"] for r in csv.DictReader(f)}


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


def test_five_firms_by_two_metrics():
    pairs = [(d["entity"], d["metric"]) for d in definitions()]
    assert len(pairs) == len(set(pairs))
    assert set(pairs) == {(e, m) for e in FIRMS for m in METRICS}


@pytest.mark.parametrize("d", definitions(), ids=lambda d: f"{d['entity']}-{d['metric']}")
def test_entry_is_complete(d):
    assert d["status"] in STATUSES
    assert d.get("valid_from")
    if d["status"] == "not_disclosed":
        assert d.get("looked_in"), "say where you looked"
    else:
        assert d.get("quote") and d.get("chunk_id")
    if d.get("chunk_id"):
        assert d["chunk_id"].startswith(d["doc_id"] + "#")
    if d["metric"] == "advisor_headcount" and d["status"] != "not_disclosed":
        assert "includes" in d and "excludes" in d


def test_doc_ids_are_in_the_manifest():
    known = manifest_ids()
    cited = set()
    for d in definitions():
        cited.add(d["doc_id"])
        cited.update(c.split("#")[0] for c in d.get("see_also", []))
    assert cited - known == set()


@pytest.fixture(scope="module")
def chunks():
    ids = set()
    for d in definitions():
        ids.update([d["chunk_id"], *d.get("see_also", [])] if d.get("chunk_id") else d.get("see_also", []))
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            rows = conn.execute("SELECT chunk_id, text FROM chunks WHERE chunk_id = ANY(%s)", (list(ids),)).fetchall()
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not rows:
        pytest.skip("no corpus loaded")
    return ids, dict(rows)


def test_chunk_ids_exist_and_quotes_are_verbatim(chunks):
    ids, found = chunks
    assert ids - found.keys() == set()
    for d in definitions():
        if d.get("quote"):
            assert squash(d["quote"]) in squash(found[d["chunk_id"]]), d["chunk_id"]
