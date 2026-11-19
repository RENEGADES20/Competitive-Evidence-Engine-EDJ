"""Retrieval mode switch (experimental branch exp/hybrid; #125, #126, #128, #211).

`main` has one mode, `fts` (ADR-010). On this branch `search(q, mode=...)` picks one of three:
  fts              - keyword search, `cee.retrieve.fts.search` (unchanged from `main`)
  hybrid           - keyword + vector legs, RRF, local cross-encoder order (`cee.retrieve.hybrid`)
  hybrid-norerank  - the same candidates as hybrid, final order by the RRF score, no reranker
None -> RETRIEVAL_MODE (environment or .env), default fts. Both hybrid modes need the optional
vectors module (CEE_VECTORS=on, ADR-009); `hybrid` is imported only then, so fts mode never loads
a model. The switch lives here (not in fts.py) so that fts.py stays byte-equal to `main` (#211).

Question planner (#214, ADR-020; hybrid since #240): every mode plans the same way (`plan_for` ->
`planner.plan_question`: at most one planner call, the rule plan on mock). fts searches a plan
exactly as `main` (`planner.search_parts`); the hybrid modes search it with `hybrid.search_parts`,
the same loop (research once, each part under its share of the token budget with every hard SQL
filter, earlier chunks excluded, peers once), so fts and hybrid differ only in how candidates are
found and ranked.
"""
from __future__ import annotations

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


def plan_for(q: Query, provider: str | None = None, mode: str | None = None) -> Plan:
    """The question's plan (#214, #240): planner.plan_question (main's rule, at most one planner
    call) in every mode; `mode` is only checked, so the plan never depends on the retrieval mode."""
    resolve_mode(mode)
    return planner.plan_question(q, provider)


def search(q: Query, k: int | None = None, mode: str | None = None,
           trace: PoolTrace | None = None, plan: Plan | None = None,
           part_pools: dict[str, set[str]] | None = None) -> list[Hit]:
    """Retrieve for one request. k: passages for the named firms and the research part; None =
    the app default, passed on as None so each mode applies the same rule (the theme peers' slots
    come on top, as in fts.search): the token budget (budget_tokens(q), #213, ADR-019), or
    budget(q) - peer_slots(q) passages when TOKEN_BUDGET is None. trace (#210): filled with the
    candidate pools before select(), recording only.
    plan (#214, ADR-020): with a plan and k None, fts -> planner.search_parts(q, plan) exactly as
    `main`; hybrid modes -> hybrid.search_parts(q, plan) (#240), the same loop. part_pools gets
    each part's candidate ids."""
    mode = resolve_mode(mode)
    if mode == "fts":
        if plan is not None and k is None:
            return planner.search_parts(q, plan, trace=trace, part_pools=part_pools)
        return fts.search(q, k, trace=trace)
    if not vectors_enabled():  # checked before the import: vectors off never loads hybrid
        raise HybridUnavailable(HYBRID_NEEDS_VECTORS)
    from cee.retrieve import hybrid  # imported late: fts mode never loads a model
    rerank = mode == "hybrid"
    if plan is not None and k is None:
        return hybrid.search_parts(q, plan, rerank=rerank, trace=trace, part_pools=part_pools)
    hits = hybrid.search(q, k, trace=trace, rerank=rerank)
    if plan is not None:
        for h in hits:
            h.part_id = "p1"
    return hits