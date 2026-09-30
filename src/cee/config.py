"""Settings, entity config and file-path resolution.

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

MANIFEST_PATH = REPO_ROOT / "data" / "manifest.csv"
LOCAL_DATA_DIR = REPO_ROOT / "data"
ENTITIES_PATH = REPO_ROOT / "config" / "entities.yaml"


@dataclass(frozen=True)
class Settings:
    database_url: str
    llm_provider: str
    llm_model: str
    openai_model: str
    corpus_share_path: str
    edgar_identity: str


def settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "postgresql://cee:cee@localhost:5432/cee"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5"),
        corpus_share_path=os.getenv("CORPUS_SHARE_PATH", "").strip(),
        edgar_identity=os.getenv("EDGAR_IDENTITY", "").strip(),
    )


@lru_cache(maxsize=1)
def entities_config() -> dict:
    with open(ENTITIES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def entity_by_id(entity_id: str) -> dict | None:
    for e in entities_config()["entities"]:
        if e["id"] == entity_id:
            return e
    return None


class FileNotAvailable(FileNotFoundError):
    pass


def candidate_paths(storage_path: str, share_path: str | None = None) -> list[Path]:
    """Where a stored file may live, in lookup order (ADR-006).

    1. $CORPUS_SHARE_PATH/<storage_path>  (skipped when CORPUS_SHARE_PATH is empty)
    2. <repo>/data/<storage_path>          (local cache for teammates)
    """
    share = settings().corpus_share_path if share_path is None else share_path.strip()
    paths = []
    if share:
        paths.append(Path(share) / storage_path)
    paths.append(LOCAL_DATA_DIR / storage_path)
    return paths


def resolve_path(storage_path: str, share_path: str | None = None) -> Path:
    for p in candidate_paths(storage_path, share_path):
        if p.is_file():
            return p
    name = Path(storage_path).name
    raise FileNotAvailable(
        f"{name} not found locally. Download it from the team Box link "
        f"into data/{Path(storage_path).parent.as_posix()}/ (see docs/RUN.md)."
    )


def write_root(share_path: str | None = None) -> Path:
    """Folder new raw files are written to: the Box Drive folder if set, else data/."""
    share = settings().corpus_share_path if share_path is None else share_path.strip()
    return Path(share) if share else LOCAL_DATA_DIR
