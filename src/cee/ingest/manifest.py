"""data/manifest.csv: one row per stored document, the source of truth for rebuilds.

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from cee.config import MANIFEST_PATH, resolve_path

FIELDS = ["doc_id", "entity_id", "doc_type", "source_tier", "published_at", "period_end",
          "url", "storage_path", "sha256", "added_by", "added_at"]


class ManifestError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def upsert_row(row: dict, path: Path = MANIFEST_PATH) -> None:
    rows = [r for r in read_manifest(path) if r["doc_id"] != row["doc_id"]]
    rows.append({k: row.get(k, "") for k in FIELDS})
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def check_files(rows: list[dict], share_path: str | None = None) -> list[tuple[dict, Path]]:
    """Every manifest row must resolve to a file whose sha256 matches. Raises otherwise."""
    problems, resolved = [], []
    for r in rows:
        try:
            p = resolve_path(r["storage_path"], share_path)
        except FileNotFoundError as e:
            problems.append(f"{r['doc_id']}: missing ({e})")
            continue
        actual = sha256_file(p)
        if actual != r["sha256"]:
            problems.append(f"{r['doc_id']}: sha256 mismatch at {p} "
                            f"(manifest {r['sha256'][:12]}..., file {actual[:12]}...)")
            continue
        resolved.append((r, p))
    if problems:
        raise ManifestError("Manifest check failed:\n  " + "\n  ".join(problems))
    return resolved
