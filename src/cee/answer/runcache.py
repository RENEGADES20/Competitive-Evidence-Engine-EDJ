"""#277: the Ask page's run cache: every call of one question's attempts, so Retry reuses what finished.

One RunCache per question + filters, held in the Streamlit session (in memory; Ask starts a new one, only
Retry reuses it, so asking again never silently replays an old answer). Each call of an attempt is recorded
with a status:

- `ok`: a valid finished output (a usable plan, a valid map extraction, a reduce output that passed every
  code check). Only these are ever returned by `get`, so a retry reuses them and pays nothing for them.
- `invalid` | `cut` | `failed` | `idle` | `cancelled` | `skipped`: kept for the run log, never returned by
  `get`, so a failure is never replayed as an answer; the retry makes the call again (one click, one attempt).
- `reused`: this attempt took the output of an earlier `ok` record (no call made).

Keys follow the eval's cache keys (scripts/eval_run.py) without the snapshot: the call's version, provider,
model, cap, request version and the exact input (cells and chunk ids for a map call; sha256 of the system
prompt, the rendered matrix and the schema for the reduce), so a changed input is never served an old output.
Thread-safe: map calls record from executor threads.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass, field

OK, REUSED = "ok", "reused"
FAILED_STATUSES = ("invalid", "cut", "failed", "idle", "cancelled", "skipped")


def _sha(obj) -> str:
    text = obj if isinstance(obj, str) else json.dumps(obj, default=str, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class Record:
    stage: str          # plan | map | remap | reduce
    id: str             # the call id (map.<cell>, remap.<cell>, plan, reduce)
    key: str
    status: str
    attempt: int
    provider: str | None = None
    model: str | None = None
    usage: dict | None = None
    finished_at: str | None = None
    error: str | None = None
    started: bool = True   # False: queued behind the Stop click, never sent
    output: object = field(default=None, repr=False)   # kept in memory only, never logged

    def to_log(self) -> dict:
        out = {"stage": self.stage, "id": self.id, "status": self.status, "attempt": self.attempt}
        if self.error:
            out["error"] = self.error[:300]
        if not self.started:
            out["started"] = False
        return out


class RunCache:
    def __init__(self, question: str = "", filters: dict | None = None) -> None:
        self.question, self.filters = question, dict(filters or {})
        self.attempt = 0
        self.records: list[Record] = []
        self.query_ids: list[int] = []   # the query_log row of each attempt, when written
        self._ok: dict[str, Record] = {}
        self._lock = threading.Lock()

    def new_attempt(self) -> int:
        with self._lock:
            self.attempt += 1
            return self.attempt

    def get(self, key: str):
        """A copy of the output of a valid finished call with this key, else None (never a failure)."""
        with self._lock:
            r = self._ok.get(key)
            return None if r is None else copy.deepcopy(r.output)

    def record(self, stage: str, id_: str, key: str, status: str, output=None, attempt: int | None = None,
               **info) -> Record:
        r = Record(stage, id_, key, status, self.attempt if attempt is None else attempt,
                   output=copy.deepcopy(output) if status == OK else None, **info)
        with self._lock:
            self.records.append(r)
            if status == OK:
                self._ok[key] = r
        return r

    def last_query_id(self) -> int | None:
        with self._lock:
            return self.query_ids[-1] if self.query_ids else None

    def summary(self, attempt: int | None = None) -> dict:
        """One attempt's calls for query_log.filters.run: reused and made counts by stage, the statuses."""
        a = self.attempt if attempt is None else attempt
        with self._lock:
            rs = [r for r in self.records if r.attempt == a]
        reused: dict[str, int] = {}
        made: dict[str, int] = {}
        status: dict[str, int] = {}
        for r in rs:
            status[r.status] = status.get(r.status, 0) + 1
            if r.status == REUSED:
                reused[r.stage] = reused.get(r.stage, 0) + 1
            elif r.started:   # sent to the provider (a cancelled one was cut mid-way)
                made[r.stage] = made.get(r.stage, 0) + 1
        return {"attempt": a, "reused": reused, "made": made, "status": status,
                "records": [r.to_log() for r in rs]}

    def made_records(self, attempt: int | None = None) -> list[Record]:
        """The calls this attempt sent (any status but reused / never started), for the cost of a stopped row."""
        a = self.attempt if attempt is None else attempt
        with self._lock:
            return [r for r in self.records if r.attempt == a and r.status != REUSED and r.started]


# --- keys ------------------------------------------------------------------------------------------

def plan_key(query, provider: str) -> str:
    from dataclasses import asdict

    from cee.answer.llm import request_version
    from cee.retrieve.planner import PLANNER_VERSION, metric_keys, model_for, planner_max_tokens
    q = {k: v for k, v in asdict(query).items() if not (k in ("period_range", "exclude_ids") and not v)}
    return "plan-" + _sha([PLANNER_VERSION, provider, model_for(provider, "plan"), planner_max_tokens(provider),
                           request_version(provider, "plan"), list(metric_keys()), q])[:24]


def map_key(question: str, spec, provider: str, window=None) -> str:
    from cee.answer.extract import extract_max_tokens, extract_version
    from cee.answer.llm import request_version
    from cee.retrieve.planner import model_for
    cells = [[c.id, c.text, c.aspect.kind, c.aspect.metric, bool(getattr(c.aspect, "proxy", False))]
             for c in spec.cells]
    model = "mock" if provider == "mock" else model_for(provider, "map")
    parts = [question, extract_version(), provider, model,
             extract_max_tokens(provider) if provider != "mock" else None,
             request_version(provider, "map"), spec.id, cells,
             [h.chunk_id for h in spec.hits],
             [str(w) for w in window] if window else None]
    prefix = getattr(spec, "prefix", None)
    if prefix is not None:   # #283 MAP_PREFIX=firm: the shared firm block is part of the request
        parts.append([[c.id, c.text] for c in prefix.cells] + [h.chunk_id for h in prefix.hits])
    return f"{spec.id}-" + _sha(parts)[:24]


def reduce_key(question: str, matrix, query, provider: str) -> str:
    from cee.answer import reduce as R
    from cee.answer.llm import request_version
    from cee.retrieve.planner import model_for
    schema, _ = R.reduce_schema(matrix)
    model = "mock" if provider == "mock" else model_for(provider, "reduce")
    return "reduce-" + _sha([question, R.prompt_version(matrix, query), provider, model,
                             R.max_tokens(provider) if provider != "mock" else None,
                             request_version(provider, "reduce"), _sha(R.system_prompt(matrix, query)),
                             _sha(R.reduce_message(question, matrix, query)), _sha(schema)])[:24]
