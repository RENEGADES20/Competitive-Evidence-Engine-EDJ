"""Manifest pre-check and file lookup order (ADR-006). Uses temp folders only."""
import pytest

from cee import config
from cee.ingest.manifest import ManifestError, check_files, sha256_file


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    share, local = tmp_path / "box", tmp_path / "data"
    (share / "raw").mkdir(parents=True)
    (local / "raw").mkdir(parents=True)
    monkeypatch.setattr(config, "LOCAL_DATA_DIR", local)
    return share, local


def row(doc_id, sha):
    return {"doc_id": doc_id, "storage_path": f"raw/{doc_id}.htm", "sha256": sha}


def test_share_path_wins_over_local(dirs):
    share, local = dirs
    (share / "raw" / "A.htm").write_text("box")
    (local / "raw" / "A.htm").write_text("local")
    assert config.resolve_path("raw/A.htm", str(share)) == share / "raw" / "A.htm"


def test_falls_back_to_local_and_skips_empty_share(dirs):
    share, local = dirs
    (local / "raw" / "A.htm").write_text("local")
    assert config.resolve_path("raw/A.htm", str(share)) == local / "raw" / "A.htm"
    assert config.candidate_paths("raw/A.htm", "") == [local / "raw" / "A.htm"]


def test_missing_file_points_to_box_link(dirs):
    share, _ = dirs
    with pytest.raises(FileNotFoundError, match="team Box link"):
        config.resolve_path("raw/NOPE.htm", str(share))


def test_check_files_rejects_sha_mismatch_and_missing(dirs):
    share, _ = dirs
    f = share / "raw" / "A.htm"
    f.write_text("content")
    good = row("A", sha256_file(f))
    assert len(check_files([good], str(share))) == 1
    with pytest.raises(ManifestError, match="sha256 mismatch"):
        check_files([row("A", "0" * 64)], str(share))
    with pytest.raises(ManifestError, match="missing"):
        check_files([row("B", "0" * 64)], str(share))
