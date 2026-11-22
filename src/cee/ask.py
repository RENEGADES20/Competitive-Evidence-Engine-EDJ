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
from cee.retrieve.modes import resolve_mode, search, search_fn
from cee.retrieve.planner import Plan, describe_plan, plan_question, rules_plan


@dataclass
class Result:
    query: Query
    hits: list[Hit]
    answer: Answer
    query_id: int | None = None
    plan: Plan | None = None
    matrix: object = None             # #246: the evidence matrix (MAP=on), else None
    reduce: dict = field(default_factory=dict)   # #247: what the reduce step did (log_filters.reduce)
    retrieval_mode: str = "fts"       # exp/hybrid (#125, #126, #249): the mode that searched


def union_hits(hits: list[Hit], matrix) -> list[Hit]:
    """#247 B1: the passages an answer may cite: the retrieval hits, then each corrective re-search hit
    of the map step not already there (origin "corrective"), in order, no duplicates."""
    if matrix is None:
        return list(hits)
    seen = {h.chunk_id for h in hits}
    return [*hits, *[h for h in getattr(matrix, "corrective", []) or [] if h.chunk_id not in seen]]


Progress = Callable[[str, str, str], None]
# #272: on_event(kind, data) for the progressive Ask page: ("plan", {"text", "plan"}) once the plan is made,
# ("evidence", {"call", "lines"}) as each map call lands (lines: evidence_lines), in the calling thread.
# #275: ("claim", {"n", "claim", "hits"}) for each reduce claim that passed the per-claim checks
# (reduce.check_item) while the reduce streams, before the final answer; adjacent items are not sent early.
Event = Callable[[str, dict], None]
"""progress(stage, state, text) for the Ask page trace (#80). stage is one of STAGES; state is
"running", "done", "skipped" or "failed"; text says what the stage really did."""

# #248: the W11 flow's stages (ADR-021): decompose / search N sub-questions / extract k firms /
# re-search / synthesize, between reading the question and the code checks
STAGES = ("resolve", "decompose", "search", "extract", "research", "synthesize", "check", "caveats", "log")


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
        mode: str | None = None, on_event: Event | None = None) -> Result:
    """filters: optional Ask page filters (#63), keys firms, date_range, keywords; applied in SQL.
    mode: retrieval mode, "fts" | "hybrid" | "hybrid-norerank" (#125, #126); None -> RETRIEVAL_MODE (default fts).
    Every mode plans the question the same way; the hybrid modes search its sub-questions through main's
    loop with hybrid.search, and the map's re-search uses the same search (cee.retrieve.modes, #249).
    on_event (#272): the plan, then each map call's cited evidence, as they are ready; #275: then each checked
    claim of the reduce as it streams."""
    provider = provider or settings().llm_provider
    mode = resolve_mode(mode)
    t = _Trace(progress)
    with t.stage("resolve", "Reading the question"):
        query = apply_filters(resolve(question), **(filters or {}))
    t.report("resolve", "done", f"Reading the question: {describe_query(query)}")
    with t.stage("decompose", "Decomposing the question"):
        plan = plan_question(query, provider)
    t.report("decompose", "done", plan_text(plan))
    if on_event is not None:
        on_event("plan", {"text": plan_text(plan), "plan": plan})
    searching = f"Searching {_n(len(plan.subquestions), 'sub-question')}"
    with t.stage("search", searching):
        hits = search(query, mode=mode, plan=plan, as_of=dt.date.today())
    docs = len({h.doc_id for h in hits})
    t.report("search", "done", f"{searching}: {_n(len(hits), 'passage')} from {_n(docs, 'document')}"
                               + ("" if mode == "fts" else f" ({mode})"))
    matrix = map_step(query, plan, hits, provider, t, mode, on_event)
    every = union_hits(hits, matrix)
    info: dict = {}
    answer, _raw = answer_for(question, query, every, provider, trace=t, plan=plan, matrix=matrix, info=info,
                              on_event=on_event)
    result = Result(query, every, answer, plan=plan, matrix=matrix, reduce=info, retrieval_mode=mode)
    if log:
        with t.stage("log", "Saving the query"):
            result.query_id = _log(result, provider)
        t.report("log", "done", f"Saving the query: query #{result.query_id}")
    return result


def _firms(matrix) -> int:
    """Firms (rows) the map extracted from; the research row is not a firm."""
    return len([r for r in matrix.rows if r != "research"])


def extract_running(plan: Plan) -> str:
    firms = {s.entity for s in plan.subquestions if s.entity}
    return f"Extracting from {_n(len(firms), 'firm')}" if firms else "Extracting from the passages"


def map_text(matrix, provider: str) -> str:
    """The extract stage's trace line (#246, #248): round-1 calls, cells, labels, behavior by code."""
    first = [c for c in matrix.calls if c["round"] == 1 and not c.get("skipped")]
    who = ("mock, no model call" if provider == "mock"
           else f"{provider}, {_n(len(first), 'call')}" + (" in parallel" if len(first) > 1 else ""))
    labels = matrix.counts()["labels"]
    order = ("fact", "derived", "not_disclosed", "not_found", "different_quantity", "failed")
    shown = ", ".join(f"{labels[k]} {k.replace('_', ' ')}" for k in order if labels.get(k))
    return (f"Extracting from {_n(_firms(matrix), 'firm')} ({who}): {_n(len(matrix.cells), 'cell')}"
            + (f": {shown}" if shown else "") + f"; behavior by code: {matrix.behavior or 'undecided'}")


RESEARCH_RUNNING = "Re-searching sub-questions with no evidence"


def research_text(matrix, provider: str) -> tuple[str, str]:
    """(state, line) of the re-search stage (#248): the corrective re-search and re-extraction (#246)."""
    if not matrix.research:
        return "skipped", "Re-search: every sub-question has evidence; nothing re-searched"
    found = sum(bool(r.get("hits")) for r in matrix.research)
    remaps = [c for c in matrix.calls if c["round"] == 2 and not c.get("skipped")]
    who = "mock, no model call" if provider == "mock" else f"{provider}, {_n(len(remaps), 'call')}"
    return "done", (f"{RESEARCH_RUNNING}: {len(matrix.research)} re-searched, {found} with new passages, "
                    f"{_n(len(remaps), 're-extraction')} ({who})")


def evidence_lines(spec, cells) -> list[dict]:
    """#272: one line per cited item of a map call's fact cells, for the Ask page while the answer is built.
    Only items whose chunk ids passed the map's code check (parse_output keeps ids inside the cell's
    retrieved set; others are in rejected_ids), so every line cites a stored, retrieved passage (rule 1)."""
    by_id = {h.chunk_id: h for h in spec.hits}
    out = []
    for c in cells:
        if c.effective_label != "fact":
            continue
        for i in c.items:
            hits = [by_id[x] for x in i.chunk_ids if x in by_id]
            if not hits:
                continue
            out.append({"cell": c.id, "entity": c.entity, "aspect": c.aspect_id,
                        "text": " ".join(str(i.text or i.quote).split()), "value": i.value,
                        "chunk_ids": [h.chunk_id for h in hits], "hits": hits})
    return out


def map_step(query: Query, plan: Plan, hits: list[Hit], provider: str, t: _Trace, mode: str = "fts",
             on_event: Event | None = None):
    """#246: the map step (on by default since #247): extraction per firm, corrective re-search, the
    evidence matrix the reduce step writes the answer from. MAP=off: the legacy single answer call.
    #248: two trace stages, extract (round 1) and research (corrective re-search and round 2)."""
    if not settings().map_on:
        t.report("extract", "skipped", "Map step off (MAP=off): no extraction calls; legacy single answer call")
        t.report("research", "skipped", "Re-search: map step off (MAP=off)")
        return None
    if not hits:
        t.report("extract", "skipped", "No passages found: no extraction call")
        t.report("research", "skipped", "Re-search: no passages found")
        return None
    import datetime as dt

    from cee.answer.extract import run_map
    running = extract_running(plan)
    state = {"stage": "extract"}

    def on_research() -> None:   # round 1 is done; the corrective re-search starts
        t.report("extract", "done", f"{running}: round 1 done")
        t.report("research", "running", RESEARCH_RUNNING)
        state["stage"] = "research"

    t.report("extract", "running", running)
    try:
        def on_call(spec, cells) -> None:   # #272: each map call's evidence, as it lands
            lines = evidence_lines(spec, cells)
            if lines and on_event is not None:
                on_event("evidence", {"call": spec.id, "lines": lines})

        # exp/hybrid (#249): the re-search searches as the mode does; fts passes nothing (main's default)
        fn = search_fn(mode)
        matrix = run_map(query, plan, hits, provider, as_of=dt.date.today(), on_research=on_research,
                         on_call=on_call, **({"search_fn": fn} if fn is not None else {}))
    except Exception as e:
        stage = state["stage"]
        text = running if stage == "extract" else RESEARCH_RUNNING
        t.report(stage, "failed", f"{text}: failed ({type(e).__name__}: {e})")
        raise
    t.report("extract", "done", map_text(matrix, provider))
    t.report("research", *research_text(matrix, provider))
    return matrix


def answer_for(question: str, query: Query, hits: list[Hit], provider: str,
               raw: Answer | None = None, trace: _Trace | None = None,
               plan: Plan | None = None, matrix=None, info: dict | None = None,
               on_event: Event | None = None) -> tuple[Answer, Answer | None]:
    """(checked answer, the model's output before checks). No hits: answered in code, no call.
    Pass a saved `raw` to reuse it instead of calling the model (scripts/eval_run.py, #43).
    `matrix` (#247): the reduce step writes the answer from the evidence matrix (one call, or an
    answer built by code; `hits` = retrieval + corrective re-search hits, B1); `info` (a dict, when
    passed) gets what the reduce did, for log_filters.reduce. No matrix: the legacy single answer call
    (prompt v4.1, MAP=off), with `plan` for the part grouping and the part check (#215)."""
    t = trace or _Trace(None)
    if not hits:
        t.report("synthesize", "skipped", "No passages found: no model call")
        t.report("check", "skipped", "Checking citations: nothing to check")
        with t.stage("caveats", "Adding caveats and gaps"):
            answer = empty_retrieval_answer(query)
            answer.coverage_note = coverage_note(query, hits)
        t.report("caveats", "done", _caveats_text(answer))
        return answer, None
    if matrix is not None:
        return _reduce_for(question, query, hits, provider, raw, t, plan, matrix, info, on_event)
    if raw is None:
        with t.stage("synthesize", f"Writing the answer ({provider}, one legacy call)"):
            raw = generate(question, hits, provider, plan=plan, window=answer_window(query))
        if info is not None:   # #248: the legacy call's usage and completion time, for the cost
            info.update(usage=raw.usage, finished_at=dt.datetime.now().astimezone().isoformat(), provider=provider,
                        model=model_name(provider) if provider != "mock" else "mock")
        t.report("synthesize", "done", f"Writing the answer ({provider}, one legacy call): "
                                       f"{_n(len(raw.claims) + len(raw.adjacent), 'claim')}")
    else:
        t.report("synthesize", "skipped", "Reusing the saved model output: no model call")
    with t.stage("check", "Checking citations"):
        answer = check_parts(check_citations(raw.model_copy(deep=True), hits), plan, hits, question)
    t.report("check", "done", _check_text(answer, hits))
    with t.stage("caveats", "Adding caveats and gaps"):
        answer = insert_caveats(answer, query, hits)
        answer = fill_suggested_sources(answer, query)
        answer.coverage_note = coverage_note(query, hits)
    t.report("caveats", "done", _caveats_text(answer))
    return answer, raw


REDUCE_RUNNING = "Synthesizing the answer from the evidence matrix"


def _reduce_for(question, query, hits, provider, raw, t, plan, matrix, info, on_event=None):
    """#247: the reduce step and every code check after it (cee.answer.reduce). #275: with on_event, each claim
    that passes the per-claim checks is sent as ("claim", ...) while the reduce streams (DeepSeek and the mock)."""
    from cee.answer import reduce as R
    code_built = not R.needs_call(matrix)
    finished_at = None
    early = None
    if on_event is not None and not code_built and raw is None:
        by_id = {h.chunk_id: h for h in hits}

        def show(claim) -> None:
            on_event("claim", {"n": len(early.shown), "claim": claim,
                               "hits": [by_id[c] for c in claim.chunk_ids if c in by_id]})
        early = R.EarlyClaims(matrix, query, show)
    if code_built:
        raw = R.code_answer(matrix, query)
        t.report("synthesize", "skipped", f"No model call: the answer is built by code "
                                          f"({matrix.behavior or 'incomplete'})")
    elif raw is None:
        with t.stage("synthesize", f"{REDUCE_RUNNING} ({provider}, one call)"):
            if provider == "mock":
                raw = R.raw_answer(matrix, query, provider, on_item=early)
            else:
                meta: dict = {}
                out = R.call_reduce(question, matrix, query, provider, meta=meta, on_item=early)
                finished_at = dt.datetime.now().astimezone().isoformat()   # #248: for the cost
                raw = R.to_answer(out, provider, meta)
        t.report("synthesize", "done", f"{REDUCE_RUNNING} ({provider}, one call): "
                                       f"{_n(len(raw.claims) + len(raw.adjacent), 'claim')}")
    else:
        t.report("synthesize", "skipped", "Reusing the saved model output: no model call")
    with t.stage("check", "Checking citations"):
        answer, done = R.finish_answer(raw.model_copy(deep=True), matrix, query, plan, hits, question,
                                       code_built=code_built)
    if info is not None:
        info.update(done, provider=provider, model=model_name(provider) if provider != "mock" else "mock")
        if early is not None:   # #275: first checked claim, shown / held, early claims not in the final answer
            info["stream_items"] = early.stats(answer)
        if finished_at:   # #248: a new reduce call's usage and completion time, for the logged cost
            info.update(usage=getattr(raw, "usage", None), finished_at=finished_at)
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
        return f"Decomposing the question (rules, no model call): {describe_plan(plan)}"
    head = f"Decomposing the question ({plan.provider}, one call)"
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
                         "remap": sum(c["round"] == 2 for c in made), "answer": int(bool(r.answer.llm_called))},
           "retrieval_mode": r.retrieval_mode}
    if r.reduce:   # #247: what the reduce step did (code checks, flags, stop_reason, usage; rule 7)
        out["reduce"] = r.reduce
    out["cost"] = question_cost(r, plan, made)
    if m is not None and getattr(m, "corrective", None):   # #247 B1: where each re-search chunk came from
        out["chunk_origin"] = {h.chunk_id: {"origin": "corrective", "subquestion": h.part_id} for h in m.corrective}
    return out


def question_cost(r: Result, plan: Plan, made: list[dict]) -> dict:
    """#248 (ADR-021 rule 7, CLAUDE.md "every call is logged with tokens and cost"): every paid call of
    the question (planner, map, re-extraction, reduce or the legacy answer), priced from its usage and
    completion time with config/pricing.yaml (cee.answer.cost); totals plus one row per call."""
    from cee.answer import cost as C
    rows: list[dict] = []

    def add(kind: str, provider: str, model, usage, finished_at) -> None:
        try:
            c = C.price_call(provider, model, usage, finished_at=finished_at)
        except C.CostError as e:   # never breaks the answer; the row says why it has no price
            c = {**C.price_call(provider, model, None), "status": "error", "error": str(e)}
        rows.append({"type": kind, "new": True, "cost": c})

    if plan.calls and plan.provider not in ("rules", "mock"):
        add("plan", plan.provider, plan.model, plan.usage, plan.finished_at)
    for c in made:
        add("map" if c["round"] == 1 else "remap", c["provider"], c.get("model"), c.get("usage"),
            c.get("finished_at"))
    red = r.reduce or {}
    if red.get("finished_at") and red.get("provider") not in (None, "mock"):
        add("reduce" if r.matrix is not None else "answer", red["provider"], red.get("model"),
            red.get("usage"), red["finished_at"])
    return {**C.summarize(rows), "rows": [{"type": x["type"], **x["cost"]} for x in rows]}


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
