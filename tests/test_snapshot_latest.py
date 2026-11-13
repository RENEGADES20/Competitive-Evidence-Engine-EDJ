"""scripts/snapshot_latest.py: LATEST.json format, notes rules, and finding the right dump (#129)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "snapshot_latest.py"
spec = importlib.util.spec_from_file_location("snapshot_latest", SCRIPT)
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


def make_dump(folder: Path, name: str = "corpus-2026-10-29", data: bytes = b"PGDMP fake dump") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{name}.dump"
    p.write_bytes(data)
    return p


def write_latest(tmp_path: Path, dump: Path, **kw) -> Path:
    out = tmp_path / "LATEST.json"
    args = ["write", "--out", str(out), "--dump", str(dump), "--documents", "111", "--chunks", "17183",
            "--notes", kw.get("notes", "21 transcripts (#108)")]
    if "built_at" in kw:
        args += ["--built-at", kw["built_at"]]
    assert sl.main(args) == 0
    return out


def test_write_fields_and_exact_format(tmp_path):
    dump = make_dump(tmp_path / "d")
    out = write_latest(tmp_path, dump, built_at="2026-10-29T17:32:13-05:00")
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw and raw.endswith(b"}\n")
    data = json.loads(raw)
    assert list(data) == ["name", "sha256", "documents", "chunks", "built_at", "notes"]
    assert data["name"] == "corpus-2026-10-29"
    assert data["sha256"] == hashlib.sha256(b"PGDMP fake dump").hexdigest()
    assert (data["documents"], data["chunks"]) == (111, 17183)
    assert data["built_at"] == "2026-10-29T22:32:13Z"  # converted to UTC
    assert raw.decode() == json.dumps(data, indent=2) + "\n"


def test_write_default_built_at_is_utc_now(tmp_path):
    data = json.loads(write_latest(tmp_path, make_dump(tmp_path / "d")).read_text())
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", data["built_at"])


@pytest.mark.parametrize("notes", ["", "   ", "see https://wustl.app.box.com/folder/1"])
def test_write_refuses_empty_notes_and_box_links(tmp_path, notes, capsys):
    out = tmp_path / "LATEST.json"
    rc = sl.main(["write", "--out", str(out), "--dump", str(make_dump(tmp_path / "d")),
                  "--documents", "1", "--chunks", "1", "--notes", notes])
    assert rc == 1 and not out.exists()
    assert "ERROR" in capsys.readouterr().err


def test_write_refuses_naive_time_and_missing_dump(tmp_path):
    with pytest.raises(sl.Problem):
        sl.build(make_dump(tmp_path / "d"), 1, 1, "x", "2026-10-29T10:00:00")
    with pytest.raises(sl.Problem):
        sl.build(tmp_path / "nope.dump", 1, 1, "x")


def test_show(tmp_path, capsys):
    out = write_latest(tmp_path, make_dump(tmp_path / "d"))
    capsys.readouterr()
    assert sl.main(["show", "--file", str(out), "--field", "name"]) == 0
    assert capsys.readouterr().out.strip() == "corpus-2026-10-29"
    assert sl.main(["show", "--file", str(tmp_path / "missing.json")]) == 1


def test_locate_exact_name_first_matching_root(tmp_path, capsys):
    good = b"the right bytes"
    dump = make_dump(tmp_path / "src", data=good)
    latest = write_latest(tmp_path, dump)
    local, box = tmp_path / "snapshots", tmp_path / "Box"
    make_dump(local, "corpus-2026-10-29-test", good)           # other name: ignored
    (local / "corpus-2026-10-29 (1).dump").write_bytes(good)   # Box rename: ignored
    found = make_dump(box / "EDJ" / "snapshots", data=good)
    capsys.readouterr()
    assert sl.main(["locate", "--file", str(latest), "--search", str(local), str(box)]) == 0
    assert Path(capsys.readouterr().out.strip()) == found
    first = make_dump(local, data=good)
    assert sl.main(["locate", "--file", str(latest), "--search", str(local), str(box)]) == 0
    assert Path(capsys.readouterr().out.strip()) == first


def test_locate_depth_limit(tmp_path):
    latest = write_latest(tmp_path, make_dump(tmp_path / "src"))
    deep = tmp_path / "Box" / "a" / "b" / "c"
    make_dump(deep)
    assert sl.main(["locate", "--file", str(latest), "--search", str(tmp_path / "Box"), "--depth", "2"]) == 2
    assert sl.main(["locate", "--file", str(latest), "--search", str(tmp_path / "Box"), "--depth", "3"]) == 0


def test_locate_mismatch_and_missing(tmp_path, capsys):
    latest = write_latest(tmp_path, make_dump(tmp_path / "src", data=b"new"))
    old = make_dump(tmp_path / "snapshots", data=b"old")
    assert sl.main(["locate", "--file", str(latest), "--search", str(tmp_path / "snapshots")]) == 2
    err = capsys.readouterr().err
    assert str(old) in err and "differs" in err and "Download corpus-2026-10-29.dump" in err
    assert sl.main(["locate", "--file", str(latest), "--search", str(tmp_path / "empty")]) == 2
    assert "Download corpus-2026-10-29.dump from the Box snapshots folder" in capsys.readouterr().err


def test_gitignore_tracks_latest_only():
    if not shutil.which("git") or not (REPO / ".git").exists():
        pytest.skip("no git checkout")

    def ignored(path: str) -> bool:
        return subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO).returncode == 0

    assert not ignored("snapshots/LATEST.json")
    assert ignored("snapshots/corpus-2026-10-29.dump")
    assert ignored("snapshots/LATEST-test.json")


def test_compose_keeps_default_container_and_port():
    text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert "container_name: ${CEE_DB_CONTAINER:-cee-db}" in text
    assert '"${CEE_DB_PORT:-5432}:5432"' in text
