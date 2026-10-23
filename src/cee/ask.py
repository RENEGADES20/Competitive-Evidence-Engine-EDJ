"""End-to-end: resolve -> retrieve -> one LLM call (or none) -> validate -> log.

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from psycopg.types.json import Jsonb

from cee.answer.llm import generate
from cee.answer.schema import Answer
from cee.answer.validate import check_citations, empty_retrieval_answer
from cee.config import settings
from cee.db import connect
from cee.retrieve.fts import Hit, Query, resolve, search


@dataclass
class Result:
    query: Query
    hits: list[Hit]
    answer: Answer
    query_id: int | None = None


Progress = Callable[[str, str, str], None]
"""progress(stage, state, text) for the Ask page trace (#80). stage is one of STAGES; state is
"running", "done", "skipped" or "failed"; text says what the stage really did."""

STAGES = ("resolve", "search", "model", "check", "caveats")


class _Trace:
    def __init__(self, progress: Progress | None):
        self.report = progress or (lambda stage, state, text: None)

    @contextmanager
    def stage(self, stage: str, running: str) -> Iterator[None]:
        """Report the stage as running; if it raises, report it failed with the error, re-raise."""
        self.report(stage, "running", running)
        try:
            yield
        except Exception as e:
            self.report(stage, "failed", f"{running}: failed ({type(e).__name__}: {e})")
            raise


def _n(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def describe_query(q: Query) -> str:
    firms = ", ".join([*q.entities, *(f"{f} (no documents)" for f in q.unmapped)]) or "none named"
    return f"firms {firms}; mode {q.mode}"


def ask(question: str, provider: str | None = None, log: bool = True,
        progress: Progress | None = None) -> Result:
    provider = provider or settings().llm_provider
    t = _Trace(progress)
    with t.stage("resolve", "Reading the question"):
        query = resolve(question)
    t.report("resolve", "done", f"Reading the question: {describe_query(query)}")
    with t.stage("search", "Searching the corpus"):
        hits = search(query)
    docs = len({h.doc_id for h in hits})
    t.report("search", "done", f"Searching the corpus: {_n(len(hits), 'passage')} from {_n(docs, 'document')}")
    answer, _raw = answer_for(question, query, hits, provider, trace=t)
    result = Result(query, hits, answer)
    if log:
        result.query_id = _log(result, provider)
    return result


def answer_for(question: str, query: Query, hits: list[Hit], provider: str,
               raw: Answer | None = None, trace: _Trace | None = None) -> tuple[Answer, Answer | None]:
    """(checked answer, the model's output before checks). No hits: answered in code, no call.
    Pass a saved `raw` to reuse it instead of calling the model (scripts/eval_run.py, #43)."""
    t = trace or _Trace(None)
    if not hits:
        t.report("model", "skipped", "No passages found: no model call")
        t.report("check", "skipped", "Checking citations: nothing to check")
        with t.stage("caveats", "Adding caveats and gaps"):
            answer = empty_retrieval_answer(query)
        t.report("caveats", "done", _caveats_text(answer))
        return answer, None
    if raw is None:
        with t.stage("model", f"Asking the model ({provider}, one call)"):
            raw = generate(question, hits, provider)
        t.report("model", "done", f"Asking the model ({provider}, one call): "
                                  f"{_n(len(raw.claims) + len(raw.adjacent), 'claim')}")
    else:
        t.report("model", "skipped", "Reusing the saved model output: no model call")
    with t.stage("check", "Checking citations"):
        answer = check_citations(raw.model_copy(deep=True), hits)
    t.report("check", "done", _check_text(answer, hits))
    t.report("caveats", "done", _caveats_text(answer))
    return answer, raw


def _check_text(a: Answer, hits: list[Hit]) -> str:
    ids = {h.chunk_id for h in hits}
    cited = [c for claim in [*a.claims, *a.adjacent] for c in claim.chunk_ids]
    matched = sum(c in ids for c in cited)
    flagged = sum(bool(claim.flags) for claim in [*a.claims, *a.adjacent])
    return f"Checking citations: {matched} matched, {flagged} flagged"


def _caveats_text(a: Answer) -> str:
    return f"Adding caveats and gaps: {_n(len(a.caveats), 'caveat')}, {_n(len(a.gaps), 'gap')}"


def model_name(provider: str) -> str:
    s = settings()
    return {"anthropic": s.llm_model, "openai": s.openai_model}.get(provider, provider)


def _log(r: Result, provider: str) -> int:
    model = model_name(provider)
    with connect() as conn:
        snap = conn.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
        row = conn.execute(
            """INSERT INTO query_log (question, mode, filters, chunk_ids, answer, snapshot, model)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING query_id""",
            (r.query.question, r.query.mode, Jsonb(asdict(r.query)), [h.chunk_id for h in r.hits],
             Jsonb(r.answer.model_dump()), snap, model)).fetchone()
    return row["query_id"]
