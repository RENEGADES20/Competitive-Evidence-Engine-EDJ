"""End-to-end: resolve -> plan (at most one planner call, #214, ADR-020) -> retrieve each part ->
one answer call (or none) -> validate -> log. At most 2 LLM calls per question (ADR-012 allows 5).

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass

from psycopg.types.json import Jsonb

from cee.answer.llm import generate
from cee.answer.schema import Answer
from cee.answer.validate import (check_citations, check_parts, coverage_note, empty_retrieval_answer,
                                 fill_suggested_sources, insert_caveats)
from cee.config import settings
from cee.db import connect
from cee.retrieve.fts import Hit, Query, apply_filters, resolve
from cee.retrieve.modes import plan_for, resolve_mode, search
from cee.retrieve.planner import Plan, describe_plan, rules_plan


@dataclass
class Result:
    query: Query
    hits: list[Hit]
    answer: Answer
    query_id: int | None = None
    plan: Plan | None = None
    retrieval_mode: str = "fts"


Progress = Callable[[str, str, str], None]
"""progress(stage, state, text) for the Ask page trace (#80). stage is one of STAGES; state is
"running", "done", "skipped" or "failed"; text says what the stage really did."""

STAGES = ("resolve", "plan", "search", "model", "check", "caveats", "log")


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
    text = f"firms {firms}; mode {q.mode}"
    if q.theme_peers:
        text += f"; on the theme also {', '.join(q.theme_peers)}"
    if q.firm_filter:
        text += f"; firm filter {', '.join(q.firm_filter)}"
    if q.date_range:
        text += f"; dates {q.date_range[0]} to {q.date_range[1]}"
    if q.keywords:
        text += f"; keywords {', '.join(q.keywords)}"
    return text


def ask(question: str, provider: str | None = None, log: bool = True,
        progress: Progress | None = None, filters: dict | None = None,
        mode: str | None = None) -> Result:
    """filters: optional Ask page filters (#63), keys firms, date_range, keywords; applied in SQL.
    mode: retrieval mode, "fts" | "hybrid" | "hybrid-norerank" (#125, #126); None -> RETRIEVAL_MODE (default fts).
    Every mode plans the question the same way; hybrid modes search the plan's parts (cee.retrieve.modes, #240)."""
    provider = provider or settings().llm_provider
    mode = resolve_mode(mode)
    t = _Trace(progress)
    with t.stage("resolve", "Reading the question"):
        query = apply_filters(resolve(question), **(filters or {}))
    t.report("resolve", "done", f"Reading the question: {describe_query(query)}")
    with t.stage("plan", "Planning the search"):
        plan = plan_for(query, provider, mode)
    t.report("plan", "done", plan_text(plan))
    with t.stage("search", "Searching the corpus"):
        hits = search(query, mode=mode, plan=plan)
    docs = len({h.doc_id for h in hits})
    t.report("search", "done", f"Searching the corpus: {_n(len(hits), 'passage')} from {_n(docs, 'document')}"
                               f" in {_n(len(plan.parts), 'part')}"
                               + ("" if mode == "fts" else f" ({mode})"))
    answer, _raw = answer_for(question, query, hits, provider, trace=t, plan=plan)
    result = Result(query, hits, answer, plan=plan, retrieval_mode=mode)
    if log:
        with t.stage("log", "Saving the query"):
            result.query_id = _log(result, provider)
        t.report("log", "done", f"Saving the query: query #{result.query_id}")
    return result


def answer_for(question: str, query: Query, hits: list[Hit], provider: str,
               raw: Answer | None = None, trace: _Trace | None = None,
               plan: Plan | None = None) -> tuple[Answer, Answer | None]:
    """(checked answer, the model's output before checks). No hits: answered in code, no call.
    Pass a saved `raw` to reuse it instead of calling the model (scripts/eval_run.py, #43).
    `plan` (#215): the model sees the evidence grouped by part, and code checks every part has a
    cited claim or a gap (validate.check_parts); None: no part grouping and no part check."""
    t = trace or _Trace(None)
    if not hits:
        t.report("model", "skipped", "No passages found: no model call")
        t.report("check", "skipped", "Checking citations: nothing to check")
        with t.stage("caveats", "Adding caveats and gaps"):
            answer = empty_retrieval_answer(query)
            answer.coverage_note = coverage_note(query, hits)
        t.report("caveats", "done", _caveats_text(answer))
        return answer, None
    if raw is None:
        with t.stage("model", f"Asking the model ({provider}, one call)"):
            raw = generate(question, hits, provider, plan=plan, window=answer_window(query))
        t.report("model", "done", f"Asking the model ({provider}, one call): "
                                  f"{_n(len(raw.claims) + len(raw.adjacent), 'claim')}")
    else:
        t.report("model", "skipped", "Reusing the saved model output: no model call")
    with t.stage("check", "Checking citations"):
        answer = check_parts(check_citations(raw.model_copy(deep=True), hits), plan, hits, question)
    t.report("check", "done", _check_text(answer, hits))
    with t.stage("caveats", "Adding caveats and gaps"):
        answer = insert_caveats(answer, query, hits)
        answer = fill_suggested_sources(answer, query)
        answer.coverage_note = coverage_note(query, hits)
    t.report("caveats", "done", _caveats_text(answer))
    return answer, raw


def answer_window(query: Query):
    """(from, to) the answer call is told about (prompt v4.1, #230): the question's time window and
    the Ask page date range, both SQL filters, so their overlap when both are set; None without."""
    spans = [s for s in (getattr(query, "window", None), getattr(query, "date_range", None)) if s]
    if not spans:
        return None
    return (max(s[0] for s in spans), min(s[1] for s in spans))


def plan_text(plan: Plan) -> str:
    """The plan stage's trace line: who planned, how many calls, the parts (#214)."""
    if plan.source == "rules":
        return f"Planning the search (rules, no model call): {describe_plan(plan)}"
    head = f"Planning the search ({plan.provider}, one call)"
    if plan.source == "fallback":
        return f"{head}: output not usable ({(plan.error or '')[:120]}), using the rule plan: {describe_plan(plan)}"
    fixes = f" ({_n(len(plan.corrections), 'correction')} by code)" if plan.corrections else ""
    return f"{head}: {describe_plan(plan)}{fixes}"


def _check_text(a: Answer, hits: list[Hit]) -> str:
    ids = {h.chunk_id for h in hits}
    cited = [c for claim in [*a.claims, *a.adjacent] for c in claim.chunk_ids]
    matched = sum(c in ids for c in cited)
    flagged = sum(bool(claim.flags) for claim in [*a.claims, *a.adjacent])
    moved = sum("uncited_cell" in g.flags for g in a.gaps)
    return (f"Checking citations: {_n(matched, 'citation')} matched, {_n(flagged, 'claim')} flagged"
            + (f", {_n(moved, 'empty cell')} moved to gaps" if moved else ""))


def _caveats_text(a: Answer) -> str:
    coded = sum("part_gap" in g.flags for g in a.gaps)
    return (f"Adding caveats and gaps: {_n(len(a.caveats), 'caveat')}, {_n(len(a.gaps), 'gap')}"
            + (f" ({coded} added by code for unanswered parts)" if coded else ""))


def model_name(provider: str) -> str:
    s = settings()
    return {"anthropic": s.llm_model, "openai": s.openai_model}.get(provider, provider)


def log_filters(r: Result) -> dict:
    """What query_log.filters stores: the resolved query, the plan (#214, ADR-020) and the LLM
    calls of the question. llm_calls counts paid provider calls (anthropic / openai): the rule plan
    and the mock answer are 0, so a mock row reads 0 / 0 although the trace names the mock's
    answer step "(mock, one call)"."""
    plan = r.plan or rules_plan(r.query)
    return {**asdict(r.query), "plan": plan.to_log(),
            "llm_calls": {"planner": plan.calls, "answer": int(bool(r.answer.llm_called))},
            "retrieval_mode": r.retrieval_mode}


def _log(r: Result, provider: str) -> int:
    # Dates (window, date_range) are stored as ISO text; they failed the default JSON dump.
    model = model_name(provider)
    with connect() as conn:
        snap = conn.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
        row = conn.execute(
            """INSERT INTO query_log (question, mode, filters, chunk_ids, answer, snapshot, model)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING query_id""",
            (r.query.question, r.query.mode, Jsonb(log_filters(r), dumps=lambda o: json.dumps(o, default=str)), [h.chunk_id for h in r.hits],
             Jsonb(r.answer.model_dump()), snap, model)).fetchone()
    return row["query_id"]
