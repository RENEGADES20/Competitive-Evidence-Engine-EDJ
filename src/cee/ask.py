"""End-to-end: resolve -> retrieve -> one LLM call (or none) -> validate -> log.

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

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


def ask(question: str, provider: str | None = None, log: bool = True) -> Result:
    provider = provider or settings().llm_provider
    query = resolve(question)
    hits = search(query)
    if hits:
        answer = check_citations(generate(question, hits, provider), hits)
    else:
        answer = empty_retrieval_answer(query)
    result = Result(query, hits, answer)
    if log:
        result.query_id = _log(result, provider)
    return result


def _log(r: Result, provider: str) -> int:
    s = settings()
    model = {"anthropic": s.llm_model, "openai": s.openai_model}.get(provider, provider)
    with connect() as conn:
        snap = conn.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
        row = conn.execute(
            """INSERT INTO query_log (question, mode, filters, chunk_ids, answer, snapshot, model)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING query_id""",
            (r.query.question, r.query.mode, Jsonb(asdict(r.query)), [h.chunk_id for h in r.hits],
             Jsonb(r.answer.model_dump()), snap, model)).fetchone()
    return row["query_id"]
