"""End-to-end (ADR-021): resolve -> plan (at most one planner call; sub-question decomposition, #245)
-> retrieve each sub-question -> map (one extraction call per firm, corrective re-search, evidence
matrix, #246) -> reduce (one synthesis call from the matrix, or an answer built by code, #247) ->
validate -> log. Calls follow the decomposition (rule 7). MAP=off keeps the legacy single answer call
(prompt v4.1) for comparison only (TL D3).

Skeleton placeholder, owner: TL (Yueyang Du).
"""
from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

from psycopg.types.json import Jsonb

from cee.answer.llm import generate
from cee.answer.schema import Answer
from cee.answer.validate import (check_citations, check_parts, coverage_note, empty_retrieval_answer,
                                 fill_suggested_sources, insert_caveats)
from cee.config import settings
from cee.db import connect
from cee.retrieve.fts import Hit, Query, apply_filters, resolve
from cee.retrieve.planner import Plan, describe_plan, plan_question, rules_plan, search_subquestions


@dataclass
class Result:
    query: Query
    hits: list[Hit]
    answer: Answer
    query_id: int | None = None
    plan: Plan | None = None
    matrix: object = None             # #246: the evidence matrix (MAP=on), else None
    reduce: dict = field(default_factory=dict)   # #247: what the reduce step did (log_filters.reduce)


def union_hits(hits: list[Hit], matrix) -> list[Hit]:
    """#247 B1: the passages an answer may cite: the retrieval hits, then each corrective re-search hit
    of the map step not already there (origin "corrective"), in order, no duplicates."""
    if matrix is None:
        return list(hits)
    seen = {h.chunk_id for h in hits}
    return [*hits, *[h for h in getattr(matrix, "corrective", []) or [] if h.chunk_id not in seen]]


Progress = Callable[[str, str, str], None]
"""progress(stage, state, text) for the Ask page trace (#80). stage is one of STAGES; state is
"running", "done", "skipped" or "failed"; text says what the stage really did."""

STAGES = ("resolve", "plan", "search", "map", "model", "check", "caveats", "log")


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
        progress: Progress | None = None, filters: dict | None = None) -> Result:
    """filters: optional Ask page filters (#63), keys firms, date_range, keywords; applied in SQL."""
    provider = provider or settings().llm_provider
    t = _Trace(progress)
    with t.stage("resolve", "Reading the question"):
        query = apply_filters(resolve(question), **(filters or {}))
    t.report("resolve", "done", f"Reading the question: {describe_query(query)}")
    with t.stage("plan", "Planning the search"):
        plan = plan_question(query, provider)
    t.report("plan", "done", plan_text(plan))
    with t.stage("search", "Searching the corpus"):
        hits = search_subquestions(query, plan, as_of=dt.date.today())
    docs = len({h.doc_id for h in hits})
    t.report("search", "done", f"Searching the corpus: {_n(len(hits), 'passage')} from {_n(docs, 'document')}"
                               f" in {_n(len(plan.subquestions), 'sub-question')}")
    matrix = map_step(query, plan, hits, provider, t)
    every = union_hits(hits, matrix)
    info: dict = {}
    answer, _raw = answer_for(question, query, every, provider, trace=t, plan=plan, matrix=matrix, info=info)
    result = Result(query, every, answer, plan=plan, matrix=matrix, reduce=info)
    if log:
        with t.stage("log", "Saving the query"):
            result.query_id = _log(result, provider)
        t.report("log", "done", f"Saving the query: query #{result.query_id}")
    return result


def map_text(matrix, provider: str) -> str:
    """The map stage's trace line (#246)."""
    made = [c for c in matrix.calls if not c.get("skipped")]
    remaps = sum(c["round"] == 2 for c in made)
    who = "mock, no model call" if provider == "mock" else f"{provider}, {_n(len(made) - remaps, 'call')} in parallel"
    extra = []
    if matrix.research:
        extra.append(f"{len(matrix.research)} re-searched")
    if remaps:
        extra.append(_n(remaps, "re-extraction"))
    labels = matrix.counts()["labels"]
    order = ("fact", "derived", "not_disclosed", "not_found", "different_quantity", "failed")
    shown = ", ".join(f"{labels[k]} {k.replace('_', ' ')}" for k in order if labels.get(k))
    return (f"Extracting per firm ({who}{''.join(', ' + e for e in extra)}): {_n(len(matrix.cells), 'cell')}"
            + (f": {shown}" if shown else "") + f"; behavior by code: {matrix.behavior or 'undecided'}")


def map_step(query: Query, plan: Plan, hits: list[Hit], provider: str, t: _Trace):
    """#246: the map step (on by default since #247): extraction per firm, corrective re-search, the
    evidence matrix the reduce step writes the answer from. MAP=off: the legacy single answer call."""
    if not settings().map_on:
        t.report("map", "skipped", "Map step off (MAP=off): no extraction calls; legacy single answer call")
        return None
    if not hits:
        t.report("map", "skipped", "No passages found: no extraction call")
        return None
    import datetime as dt

    from cee.answer.extract import run_map
    with t.stage("map", "Extracting per firm"):
        matrix = run_map(query, plan, hits, provider, as_of=dt.date.today())
    t.report("map", "done", map_text(matrix, provider))
    return matrix


def answer_for(question: str, query: Query, hits: list[Hit], provider: str,
               raw: Answer | None = None, trace: _Trace | None = None,
               plan: Plan | None = None, matrix=None, info: dict | None = None) -> tuple[Answer, Answer | None]:
    """(checked answer, the model's output before checks). No hits: answered in code, no call.
    Pass a saved `raw` to reuse it instead of calling the model (scripts/eval_run.py, #43).
    `matrix` (#247): the reduce step writes the answer from the evidence matrix (one call, or an
    answer built by code; `hits` = retrieval + corrective re-search hits, B1); `info` (a dict, when
    passed) gets what the reduce did, for log_filters.reduce. No matrix: the legacy single answer call
    (prompt v4.1, MAP=off), with `plan` for the part grouping and the part check (#215)."""
    t = trace or _Trace(None)
    if not hits:
        t.report("model", "skipped", "No passages found: no model call")
        t.report("check", "skipped", "Checking citations: nothing to check")
        with t.stage("caveats", "Adding caveats and gaps"):
            answer = empty_retrieval_answer(query)
            answer.coverage_note = coverage_note(query, hits)
        t.report("caveats", "done", _caveats_text(answer))
        return answer, None
    if matrix is not None:
        return _reduce_for(question, query, hits, provider, raw, t, plan, matrix, info)
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


REDUCE_RUNNING = "Asking the model to write the answer from the evidence matrix"


def _reduce_for(question, query, hits, provider, raw, t, plan, matrix, info):
    """#247: the reduce step and every code check after it (cee.answer.reduce)."""
    from cee.answer import reduce as R
    code_built = not R.needs_call(matrix)
    if code_built:
        raw = R.code_answer(matrix, query)
        t.report("model", "skipped", f"No model call: the answer is built by code "
                                     f"({matrix.behavior or 'incomplete'})")
    elif raw is None:
        with t.stage("model", f"{REDUCE_RUNNING} ({provider}, one call)"):
            if provider == "mock":
                raw = R.raw_answer(matrix, query, provider)
            else:
                meta: dict = {}
                out = R.call_reduce(question, matrix, query, provider, meta=meta)
                raw = R.to_answer(out, provider, meta)
        t.report("model", "done", f"{REDUCE_RUNNING} ({provider}, one call): "
                                  f"{_n(len(raw.claims) + len(raw.adjacent), 'claim')}")
    else:
        t.report("model", "skipped", "Reusing the saved model output: no model call")
    with t.stage("check", "Checking citations"):
        answer, done = R.finish_answer(raw.model_copy(deep=True), matrix, query, plan, hits, question,
                                       code_built=code_built)
    if info is not None:
        info.update(done, provider=provider, model=model_name(provider) if provider != "mock" else "mock")
    t.report("check", "done", _check_text(answer, hits))
    t.report("caveats", "done", _caveats_text(answer))
    return answer, (None if code_built else raw)

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
    return {"anthropic": s.llm_model, "openai": s.openai_model,
            "deepseek": s.deepseek_model}.get(provider, provider)


def log_filters(r: Result) -> dict:
    """What query_log.filters stores: the resolved query, the plan (#214, ADR-020) and the LLM
    calls of the question. llm_calls counts paid provider calls (anthropic / openai / deepseek): the rule plan
    and the mock answer are 0, so a mock row reads 0 / 0 although the trace names the mock's
    answer step "(mock, one call)"."""
    plan = r.plan or rules_plan(r.query)
    m = r.matrix
    made = [c for c in (m.calls if m is not None else []) if not c.get("skipped") and not c.get("cached")
            and c.get("provider") != "mock"]
    out = {**asdict(r.query), "plan": plan.to_log(),
           "map": (m.to_log() if m is not None else {"off": True} if not settings().map_on
                   else {"skipped": "no passages"}),
           "llm_calls": {"planner": plan.calls, "map": sum(c["round"] == 1 for c in made),
                         "remap": sum(c["round"] == 2 for c in made), "answer": int(bool(r.answer.llm_called))}}
    if r.reduce:   # #247: what the reduce step did (code checks, flags, stop_reason, usage; rule 7)
        out["reduce"] = r.reduce
    if m is not None and getattr(m, "corrective", None):   # #247 B1: where each re-search chunk came from
        out["chunk_origin"] = {h.chunk_id: {"origin": "corrective", "subquestion": h.part_id} for h in m.corrective}
    return out


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
