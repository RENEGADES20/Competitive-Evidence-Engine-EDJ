"""The core needs no vectors (#144, ADR-009): no extension in core SQL, no fastembed import from
retrieval, answer or app code, CEE_VECTORS parsing. No database, no network."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

from cee import config

REPO = Path(__file__).resolve().parents[1]
CORE_SQL = [REPO / "db" / "schema.sql", REPO / "db" / "upgrade.sql"]


def _sql_code(path: Path) -> str:
    """The file without -- comments."""
    return "\n".join(line.split("--", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize("path", CORE_SQL, ids=lambda p: p.name)
def test_core_sql_has_no_vector_and_no_extension(path):
    code = _sql_code(path).lower()
    assert "create extension" not in code
    assert not re.search(r"\bvector\b", code)  # tsvector is fine
    assert "embedding" not in code


def test_optional_sql_has_table_index_and_move():
    code = _sql_code(REPO / "db" / "optional" / "vectors.sql").lower()
    assert "create extension if not exists vector" in code
    assert "create table if not exists chunk_embeddings" in code
    assert "references chunks on delete cascade" in code
    assert "using hnsw" in code
    assert "drop column embedding" in code and "raise exception" in code


def test_compose_mounts_only_core_sql():
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    mounts = [line for line in compose.splitlines() if line.strip().startswith("- ./db/")]
    assert len(mounts) == 2 and not any("optional" in m for m in mounts)


def test_core_modules_do_not_import_fastembed():
    code = (
        "import sys\n"
        "sys.modules['fastembed'] = None\n"
        "sys.modules['onnxruntime'] = None\n"
        "import cee.retrieve.fts, cee.ask, cee.app.components\n"
        "from cee.app.views import ask_page, coverage_page, design_page, source_page\n"
        "import cee.retrieve.embed\n"  # the module itself imports fastembed only when used
        "print('ok')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True,
                       env={**__import__("os").environ, "PYTHONPATH": str(REPO / "src")})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


@pytest.mark.parametrize("value, expected", [
    (None, False), ("", False), ("off", False), ("OFF", False), ("false", False), ("0", False),
    ("no", False), ("on", True), ("On", True), ("true", True), ("1", True), ("yes", True),
    ('"on"', True), (" on ", True),
])
def test_vectors_enabled_parsing(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("CEE_VECTORS", raising=False)
    else:
        monkeypatch.setenv("CEE_VECTORS", value)
    assert config.vectors_enabled() is expected


def test_vectors_enabled_rejects_unknown(monkeypatch):
    monkeypatch.setenv("CEE_VECTORS", "maybe")
    with pytest.raises(ValueError, match="CEE_VECTORS"):
        config.vectors_enabled()
