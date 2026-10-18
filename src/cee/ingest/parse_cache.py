"""Parse cache (#82): slow parser output stored once per file content and parser version.

Owner: TL (Yueyang Du). docling takes minutes per PDF and edgartools seconds per filing, so their
output is kept in <write_root()>/parsed/<sha256>-<tag>.json (next to raw/ on Box Drive, data/parsed/
otherwise). A changed file has a new sha256; the tag names the library version and our own parser
version; a change to either gives a new name, so that file is parsed again. Old files are never
read again and may be deleted.
"""
from __future__ import annotations

import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable

from cee.config import write_root


def tag(library: str, parser_version: int) -> str:
    return f"{library}{version(library)}-v{parser_version}"


def cache_path(path: Path, tag: str, cache_dir: Path | None = None) -> Path:
    return (cache_dir or write_root() / "parsed") / f"{sha256(path)}-{tag}.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(cache_file: Path, convert: Callable[[Any], Any] = lambda r: r) -> Any | None:
    """The stored result passed through `convert`, or None when there is no usable file."""
    try:
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        if data["tag"] != cache_file.stem.split("-", 1)[1]:
            return None
        return convert(data["result"])
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError, IndexError) as e:  # half-written or hand-edited
        print(f"  ignoring unreadable parse cache {cache_file.name}: {e}", flush=True)
        return None


def write(cache_file: Path, source: Path, result: Any) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_file.with_suffix(".tmp")
    # ensure_ascii keeps any odd character (e.g. a lone surrogate from a PDF) round-tripping exactly.
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"tag": cache_file.stem.split("-", 1)[1], "source": source.name, "result": result}, f)
    os.replace(tmp, cache_file)  # a reader never sees a half-written file
