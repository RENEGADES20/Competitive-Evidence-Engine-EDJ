"""Retrieval mode switch (experimental branch exp/hybrid; #125, #126, #128, #211).

`main` has one mode, `fts` (ADR-010). On this branch `search(q, mode=...)` picks one of three:
  fts              - keyword search, `cee.retrieve.fts.search` (unchanged from `main`)
  hybrid           - keyword + vector legs, RRF, local cross-encoder order (`cee.retrieve.hybrid`)
  hybrid-norerank  - the same candidates as hybrid, final order by the RRF score, no reranker
None -> RETRIEVAL_MODE (environment or .env), default fts. Both hybrid modes need the optional
vectors module (CEE_VECTORS=on, ADR-009); `hybrid` is imported only then, so fts mode never loads
a model. The switch lives here (not in fts.py) so that fts.py stays byte-equal to `main` (#211).

Sub-questions (#245, ADR-021 rule 6; #249): every mode plans the same way (planner.plan_question in
the caller; the plan never depends on the mode) and searches the plan with main's own loop,
planner.search_subquestions. fts passes nothing (main's defaults, fts.search); the hybrid modes pass
hybrid.search / hybrid.research_pass as `search_fn` / `research_fn` (the vector leg embeds each
sub-question's text) and fts.fetch_pinned as `pin_fn` (registered chunks by id, the same in every mode).
search_fn(mode) is the same search for the map's corrective re-search (extract.run_map). There is no
hybrid copy of the loop any more (hybrid.search_parts and its source-hash pin went in #249).
"""
from __future__ import annotations

from functools import partial

from cee.config import settings, vectors_enabled
from cee.retrieve import fts, planner
from cee.retrieve.fts import Hit, PoolTrace, Query
from cee.retrieve.planner import Plan

MODES = ("fts", "hybrid", "hybrid-norerank")


class HybridUnavailable(RuntimeError):
    """Hybrid mode asked for while the optional vectors module is off (ADR-009)."""


HYBRID_NEEDS_VECTORS = (
    "Hybrid retrieval needs the optional vectors module: set CEE_VECTORS=on, install "
    "requirements-vectors.txt and fill the vectors (docs/RUN.md, 'Hybrid retrieval'), or use "
    "RETRIEVAL_MODE=fts.")


def resolve_mode(mode: str | None) -> str:
    mode = (mode or settings().retrieval_mode).strip().lower()
    if mode not in MODES:
        raise ValueError(f"unknown retrieval mode {mode!r}; use one of {', '.join(MODES)}")
    return mode


def _hybrid(mode: str):
    """The hybrid module for a hybrid mode, after the vectors switch (ADR-009): vectors off never
    imports it, so fts mode never loads a model."""
    if not vectors_enabled():  # checked before the import: vectors off never loads hybrid
        raise HybridUnavailable(HYBRID_NEEDS_VECTORS)
    from cee.retrieve import hybrid  # imported late: fts mode never loads a model
    return hybrid


def search_fn(mode: str | None = None, checked: bool = False):
    """The sub-question search for `mode` (#249): None for fts (callers keep main's default, fts.search);
    hybrid.search with rerank by mode otherwise. checked: the vectors check already ran."""
    mode = resolve_mode(mode)
    if mode == "fts":
        return None
    return partial(_hybrid(mode).search, rerank=mode == "hybrid", checked=checked)


def search(q: Query, k: int | None = None, mode: str | None = None,
           trace: PoolTrace | None = None, plan: Plan | None = None,
           part_pools: dict[str, set[str]] | None = None, as_of=None) -> list[Hit]:
    """Retrieve for one request. k: passages for the named firms and the research part; None =
    the app default, passed on as None so each mode applies the same rule (the theme peers' slots
    come on top, as in fts.search): the token budget (budget_tokens(q), #213, ADR-019), or
    budget(q) - peer_slots(q) passages when TOKEN_BUDGET is None. trace (#210): filled with the
    candidate pools before select(), recording only.
    plan (#245, #249): with a plan and k None, every mode runs planner.search_subquestions (main's
    loop); fts with main's defaults, the hybrid modes with hybrid's search and research pass and
    fts.fetch_pinned. part_pools gets each sub-question's candidate ids; as_of (the per-period pass)."""
    mode = resolve_mode(mode)
    if mode == "fts":
        if plan is not None and k is None:
            return planner.search_subquestions(q, plan, trace=trace, part_pools=part_pools, as_of=as_of)
        return fts.search(q, k, trace=trace)
    hybrid = _hybrid(mode)
    rerank = mode == "hybrid"
    if plan is not None and k is None:
        if fts.searchable(q):
            from cee.db import connect
            with connect() as conn:
                hybrid.check_vectors(conn)  # once per question, not once per sub-question
        return planner.search_subquestions(
            q, plan, search_fn=partial(hybrid.search, rerank=rerank, checked=True),
            research_fn=partial(hybrid.research_pass, rerank=rerank, checked=True),
            pin_fn=fts.fetch_pinned, trace=trace, part_pools=part_pools, as_of=as_of)
    hits = hybrid.search(q, k, trace=trace, rerank=rerank)
    if plan is not None:
        for h in hits:
            h.part_id = plan.subquestions[0].id if len(plan.subquestions) == 1 else "p1"
    return hits
