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
    mock_delay_s: float = 0.0  # verify-cee only: the mock waits like a real model would (#80)
    planner: bool = True        # question planner (#214, ADR-020): off = the rule plan, no planner call
    # Sub-question decomposition (#245, ADR-021 rule 6, ADR-019 amendment): token budget of each
    # SubQuestion(entity, aspect); the question's total grows with its decomposition. No part cap.
    subquestion_tokens: int = 40000
    # DeepSeek (#242): OpenAI-SDK compatible; strict function tools need the /beta base URL.
    deepseek_model: str = "deepseek-v4-pro"
    deepseek_base_url: str = "https://api.deepseek.com/beta"
    deepseek_thinking: bool = True
    # Map-reduce (#246, #247, ADR-021): per-firm extraction calls, the evidence matrix and the reduce
    # call. On by default since #247; MAP=off keeps the legacy single answer call (prompt v4.1) for
    # comparison only (TL D3). The eval maps unless --legacy.
    map_on: bool = True
    map_concurrency: int = 24    # parallel extraction calls (#272: one per firm x aspect cell)
    # #272: DeepSeek effort per stage (off | low | high | max; off = thinking disabled), the map's model
    # (empty = deepseek_model), streaming (on | off | nothink) and the map's input ceiling per call.
    deepseek_effort_plan: str = "off"
    deepseek_effort_map: str = "low"
    deepseek_effort_reduce: str = "low"
    deepseek_model_map: str = ""
    deepseek_stream: str = "on"
    map_call_tokens: int = 60000
    # #283: the map's shared prefix per firm (one byte-identical firm block, the cell's instruction last) up to
    # this many estimated input tokens, above it the per-cell layout; the leader-first gate (first_chunk | done |
    # off) and the followers' extra wait after it opens.
    map_prefix: str = "off"   # #283: off (default; the #272 map request) | firm (not adopted, kept for experiments)
    map_prefix_tokens: int = 150000
    map_prefix_gate: str = "first_chunk"
    map_prefix_wait_s: float = 5.0
    # #275: a streamed DeepSeek call with no chunk for this many seconds is aborted and saved as failed
    # (no automatic retry); the reduce system prompt version (v5.2 | v5.3: v5.3 adds "state each fact once").
    deepseek_idle_s: float = 120.0
    reduce_prompt: str = "v5.2"
    # #277 verify-cee only: while this file names a stage (map | reduce), the mock call of that stage fails
    # (extract.mock_failure). Empty (the default): never. Never read for a real provider.
    mock_fail_file: str = ""


# DEEPSEEK_THINKING default (#242): on, chosen by the plan's fixed rule from the real check on Q1, Q22,
# Q24: valid outputs 6/6 on vs 5/6 off (docs/results/0242-deepseek-check.md).
DEEPSEEK_THINKING_DEFAULT = True
ON_WORDS = ("on", "true", "1", "yes")
OFF_WORDS = ("off", "false", "0", "no")


def deepseek_thinking() -> bool:
    """DEEPSEEK_THINKING: on|true|1|yes -> on; off|false|0|no -> off; empty -> the default;
    anything else stops with a clear error (#242)."""
    raw = os.getenv("DEEPSEEK_THINKING", "").strip().strip('"').strip().lower()
    if not raw:
        return DEEPSEEK_THINKING_DEFAULT
    if raw in ON_WORDS:
        return True
    if raw in OFF_WORDS:
        return False
    raise ValueError(f"DEEPSEEK_THINKING={raw!r} is not understood; use on or off")


# SUBQUESTION_TOKENS default (#245): picked from the mock grid {12000, 20000, 40000} by the plan's
# fixed rule (plans/0245-decompose.md; ADR-019 amendment): only 40000 was eligible (12000 and 20000
# lose recall@final against corpus-2026-11-19); at 40000 the 30 baseline lists keep their recall.
SUBQUESTION_TOKENS_DEFAULT = 40000
MAP_CONCURRENCY_DEFAULT = 24  # #272: one call per firm x aspect cell (was 6: five firms + research, #246)
# #272: the input ceiling of one map call; a cell over it is split into batches. 60000 = SUBQUESTION_TOKENS (40000)
# plus room for the prompt, schema and pool passages listed for a sibling, so a normal cell is one call
# (at 40000 the mock run with the #250 plans batched Q17's whole-corpus cells, 2026-11-21).
MAP_CALL_TOKENS_DEFAULT = 60000
# #272: DeepSeek effort per stage, from test A by the plan's fixed rule (plans/0272-latency.md step 10): C1 = plan
# off, map low, reduce low, the only config with 0 cut and 0 invalid outputs on Q5, Q10, Q19, Q21, Q24, Q26 (C2, map
# off: 1 invalid; C3, map on deepseek-flash: 3 invalid); critical path p50 209 s vs 415 s in #250.
EFFORTS = ("off", "low", "high", "max")
EFFORT_DEFAULTS = {"plan": "off", "map": "low", "reduce": "low"}
STREAM_MODES = ("on", "off", "nothink")


def _choice(name: str, allowed: tuple, default: str) -> str:
    """A setting from a fixed list; empty -> the default; anything else stops with a clear error."""
    raw = os.getenv(name, "").strip().strip('"').strip().lower()
    if not raw:
        return default
    if raw not in allowed:
        raise ValueError(f"{name}={raw!r} is not understood; use one of {', '.join(allowed)}")
    return raw


def _positive_int(name: str, default: int | None) -> int | None:
    """An integer setting > 0; empty -> the default; anything else stops with a clear error."""
    raw = os.getenv(name, "").strip().strip('"').strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r} is not a whole number") from None
    if value <= 0:
        raise ValueError(f"{name}={raw!r} must be greater than 0")
    return value


# #283 (plans/0283-prefix-cache.md): the firm block ceiling (estimate from the #272 test B map records: map cache-hit
# share about 0.73 at 150000, largest call about 147k tokens; 0.90 with no ceiling but calls up to 372k), and the
# leader-first gate (both only with MAP_PREFIX=firm). MAP_PREFIX_GATE is pinned from the Q10 probe by the plan's fixed
# rule (TL condition B4): Q10 on
# 2026-11-22, 25 followers, cache-hit share of their prefix 0.929 >= 0.50 -> first_chunk (docs/results/w13-prefix-cache/).
# TL ruling after review (PR #286): the layout is NOT adopted (adjudicated 23/30 < 24, latency acceptance unmet, cell
# regressions), so MAP_PREFIX defaults to off; firm turns the whole #283 request on (extract-v1.3, -pf map version).
MAP_PREFIX_MODES = ("off", "firm")
MAP_PREFIX_TOKENS_DEFAULT = 150000
MAP_PREFIX_GATES = ("first_chunk", "done", "off")
MAP_PREFIX_GATE_DEFAULT = "first_chunk"
MAP_PREFIX_WAIT_S_DEFAULT = 5.0


def _nonneg_float(name: str, default: float) -> float:
    """A number setting >= 0 (seconds); empty -> the default; anything else stops with a clear error."""
    raw = os.getenv(name, "").strip().strip('"').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r} is not a number") from None
    if value < 0:
        raise ValueError(f"{name}={raw!r} must be 0 or more")
    return value


DEEPSEEK_IDLE_S_DEFAULT = 120.0   # #275: seconds without a streamed chunk before a call is aborted
REDUCE_PROMPTS = ("v5.2", "v5.3")
REDUCE_PROMPT_DEFAULT = "v5.2"


def _positive_float(name: str, default: float) -> float:
    """A number setting > 0 (seconds); empty -> the default; anything else stops with a clear error."""
    raw = os.getenv(name, "").strip().strip('"').strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{name}={raw!r} is not a number") from None
    if value <= 0:
        raise ValueError(f"{name}={raw!r} must be greater than 0")
    return value


def settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "postgresql://cee:cee@localhost:5432/cee"),
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-5-5"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5"),
        corpus_share_path=os.getenv("CORPUS_SHARE_PATH", "").strip(),
        edgar_identity=os.getenv("EDGAR_IDENTITY", "").strip(),
        mock_delay_s=float(os.getenv("MOCK_DELAY_S", "0") or 0),
        planner=os.getenv("PLANNER", "on").strip().strip('"').strip().lower() not in ("off", "false", "0", "no"),
        subquestion_tokens=_positive_int("SUBQUESTION_TOKENS", SUBQUESTION_TOKENS_DEFAULT),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "").strip() or "deepseek-v4-pro",
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "").strip() or "https://api.deepseek.com/beta",
        deepseek_thinking=deepseek_thinking(),
        map_on=os.getenv("MAP", "on").strip().strip('"').strip().lower() not in OFF_WORDS,
        map_concurrency=_positive_int("MAP_CONCURRENCY", MAP_CONCURRENCY_DEFAULT),
        deepseek_effort_plan=_choice("DEEPSEEK_EFFORT_PLAN", EFFORTS, EFFORT_DEFAULTS["plan"]),
        deepseek_effort_map=_choice("DEEPSEEK_EFFORT_MAP", EFFORTS, EFFORT_DEFAULTS["map"]),
        deepseek_effort_reduce=_choice("DEEPSEEK_EFFORT_REDUCE", EFFORTS, EFFORT_DEFAULTS["reduce"]),
        deepseek_model_map=os.getenv("DEEPSEEK_MODEL_MAP", "").strip(),
        deepseek_stream=_choice("DEEPSEEK_STREAM", STREAM_MODES, "on"),
        map_call_tokens=_positive_int("MAP_CALL_TOKENS", MAP_CALL_TOKENS_DEFAULT),
        map_prefix=_choice("MAP_PREFIX", MAP_PREFIX_MODES, "off"),
        map_prefix_tokens=_positive_int("MAP_PREFIX_TOKENS", MAP_PREFIX_TOKENS_DEFAULT),
        map_prefix_gate=_choice("MAP_PREFIX_GATE", MAP_PREFIX_GATES, MAP_PREFIX_GATE_DEFAULT),
        map_prefix_wait_s=_nonneg_float("MAP_PREFIX_WAIT_S", MAP_PREFIX_WAIT_S_DEFAULT),
        deepseek_idle_s=_positive_float("DEEPSEEK_IDLE_S", DEEPSEEK_IDLE_S_DEFAULT),
        reduce_prompt=_choice("REDUCE_PROMPT", REDUCE_PROMPTS, REDUCE_PROMPT_DEFAULT),
        mock_fail_file=os.getenv("MOCK_FAIL_FILE", "").strip(),
    )


VECTORS_ON = ("on", "true", "1", "yes")
VECTORS_OFF = ("", "off", "false", "0", "no")


def vectors_enabled() -> bool:
    """CEE_VECTORS (environment or .env): the optional vectors module (ADR-009), off by default.

    on|true|1|yes -> on; empty, off|false|0|no -> off; anything else stops with a clear error.
    The scripts parse it the same way (scripts/_common.*).
    """
    raw = os.getenv("CEE_VECTORS", "").strip().strip('"').strip().lower()
    if raw in VECTORS_ON:
        return True
    if raw in VECTORS_OFF:
        return False
    raise ValueError(f"CEE_VECTORS={raw!r} is not understood; use on or off")


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
