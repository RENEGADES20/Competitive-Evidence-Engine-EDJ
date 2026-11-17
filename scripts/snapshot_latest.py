"""snapshots/LATEST.json: the newest corpus snapshot, as committed to the repo (#129).

The dump itself stays on Box (ADR-006/ADR-007); this file names it and carries its sha256, row
counts, build time and notes. Shared by build-snapshot.ps1/.sh (write) and sync-db.ps1/.sh
(show, locate), so both twins read and write exactly the same format. Standard library only.

  python scripts/snapshot_latest.py write --out snapshots/LATEST.json --dump snapshots/corpus-X.dump \
      --documents 111 --chunks 17183 --notes "What changed (#108)" [--built-at 2026-10-29T22:32:13Z]
  python scripts/snapshot_latest.py show --file snapshots/LATEST.json [--field name]
  python scripts/snapshot_latest.py locate --file snapshots/LATEST.json --search DIR [DIR ...] [--depth 6]

Exit codes: 0 ok; 1 bad input (missing file, bad field, bad notes); 2 (locate) the dump is
missing or every copy found differs from the sha256 in the file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("name", "sha256", "documents", "chunks", "built_at", "notes")
REPO = Path(__file__).resolve().parents[1]


class Problem(Exception):
    """A message for the user; exit code 1 unless it says otherwise."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def render(data: dict) -> str:
    """The exact file text: fixed field order, 2-space indent, LF, trailing newline."""
    return json.dumps({k: data[k] for k in FIELDS}, indent=2, ensure_ascii=False) + "\n"


def build(dump: Path, documents: int, chunks: int, notes: str, built_at: str | None = None) -> dict:
    notes = (notes or "").strip()
    if not notes:
        raise Problem("Notes are empty: say what changed and the issue numbers.")
    if "box.com" in notes.lower():
        raise Problem("Notes contain a Box link; the repo is public, so leave links out of the notes.")
    if not dump.is_file():
        raise Problem(f"Dump not found: {dump}")
    if dump.suffix != ".dump":
        raise Problem(f"Not a .dump file: {dump}")
    if built_at:
        try:
            parsed = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
        except ValueError:
            raise Problem(f"--built-at is not an ISO 8601 time: {built_at}") from None
        if parsed.tzinfo is None:
            raise Problem(f"--built-at needs a time zone (e.g. ...Z): {built_at}")
        built_at = utc_iso(parsed)
    else:
        built_at = utc_iso(datetime.now(timezone.utc))
    return {"name": dump.stem, "sha256": sha256_of(dump), "documents": int(documents),
            "chunks": int(chunks), "built_at": built_at, "notes": notes}


def write(out: Path, data: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:  # no BOM, LF
        f.write(render(data))


def read(path: Path) -> dict:
    if not path.is_file():
        raise Problem(f"{path} not found. Nobody has published a snapshot through the repo yet; "
                      "use the restore script (docs/RUN.md) or ask the tech lead.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise Problem(f"{path} is not valid JSON: {e}") from None
    missing = [k for k in FIELDS if k not in data]
    if missing:
        raise Problem(f"{path} lacks {', '.join(missing)}")
    return data


def candidates(name: str, roots: list[Path], depth: int):
    """Every file called exactly <name>.dump under the roots, root order first, up to depth levels."""
    target = f"{name}.dump"
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        base = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root):
            here = Path(dirpath)
            if len(here.parts) - base >= depth:
                dirnames[:] = []
            dirnames.sort()
            if target in filenames:
                p = here / target
                key = os.path.normcase(str(p.resolve()))
                if key not in seen:
                    seen.add(key)
                    yield p


def locate(data: dict, roots: list[Path], depth: int = 6) -> Path:
    name, want = data["name"], data["sha256"].lower()
    download = (f"Download {name}.dump from the Box snapshots folder (team link) into "
                f"{REPO / 'snapshots'}, then run sync-db again.")
    differ: list[Path] = []
    for p in candidates(name, roots, depth):
        if p.stat().st_size == 0:
            sha256_of(p)  # reading a 0-byte Box placeholder makes Box fetch the file; then look again
        if p.stat().st_size and sha256_of(p) == want:
            return p
        differ.append(p)
    if differ:
        listed = "\n".join(f"  {p}" for p in differ)
        raise Problem(f"Found {name}.dump, but it differs from the snapshot in LATEST.json "
                      f"(old, incomplete or still downloading):\n{listed}\n{download}", code=2)
    raise Problem(f"{name}.dump is not on this computer. {download}", code=2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--out", required=True, type=Path)
    w.add_argument("--dump", required=True, type=Path)
    w.add_argument("--documents", required=True, type=int)
    w.add_argument("--chunks", required=True, type=int)
    w.add_argument("--notes", required=True)
    w.add_argument("--built-at")
    s = sub.add_parser("show")
    s.add_argument("--file", required=True, type=Path)
    s.add_argument("--field", choices=FIELDS)
    lo = sub.add_parser("locate")
    lo.add_argument("--file", required=True, type=Path)
    lo.add_argument("--search", nargs="+", default=[], type=Path)
    lo.add_argument("--depth", type=int, default=6)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "write":
            data = build(a.dump, a.documents, a.chunks, a.notes, a.built_at)
            write(a.out, data)
            print(f"Wrote {a.out}: {data['name']} ({data['documents']} documents, {data['chunks']} chunks)")
        elif a.cmd == "show":
            data = read(a.file)
            if a.field:
                print(data[a.field])
            else:
                print(f"{data['name']} ({data['documents']} documents, {data['chunks']} chunks, "
                      f"built {data['built_at']}): {data['notes']}")
        else:
            print(locate(read(a.file), [p for p in a.search if str(p)], a.depth))
    except Problem as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
