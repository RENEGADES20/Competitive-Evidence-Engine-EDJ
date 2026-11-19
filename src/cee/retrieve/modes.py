"""Retrieval mode switch (experimental branch exp/hybrid; #125, #126, #128, #211).

`main` has one mode, `fts` (ADR-010). On this branch `search(q, mode=...)` picks one of three:
  fts              - keyword search, `cee.retrieve.fts.search` (unchanged from `main`)
  hybrid           - keyword + vector legs, RRF, local cross-encoder order (`cee.retrieve.hybrid`)
  hybrid-norerank  - the same candidates as hybrid, final order by the RRF score, no reranker
None -> RETRIEVAL_MODE (environment or .env), default fts. Both hybrid modes need the optional
vectors module (CEE_VECTORS=on, ADR-009); `hybrid` is imported only then, so fts mode never loads
a model. The switch lives here (not in fts.py) so that fts.py stays byte-equal to `main` (#211).

Question planner (#214, ADR-020): fts mode plans and searches exactly as `main` (`plan_for` ->
`planner.plan_question`, `search(..., plan=...)` -> `planner.search_parts`). The hybrid modes do
not split the question: `plan_for` returns the one-part whole-question plan with no planner call,
and `search` runs one `hybrid.search` on the whole question (every hit's part_id "p1"), as before
#214. Per-part hybrid retrieval would need hybrid's candidate counts tuned for token shares; not
done on this branch.
"""
from __future__ import annotations

from cee.config import settings, vectors_enabled
from cee.retrieve import fts, planner
from cee.retrieve.fts import Hit, PoolTrace, Query
from cee.retrieve.planner import Part, Plan

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
    """The question's plan (#214): fts -> planner.plan_question (main's rule, at most one planner
    call); hybrid modes -> one whole-question part, no planner call."""
    if resolve_mode(mode) == "fts":
        return planner.plan_question(q, provider)
    return Plan(parts=[Part("p1", q.question, list(q.entities))])


def search(q: Query, k: int | None = None, mode: str | None = None,
           trace: PoolTrace | None = None, plan: Plan | None = None,
           part_pools: dict[str, set[str]] | None = None) -> list[Hit]:
    """Retrieve for one request. k: passages for the named firms and the research part; None =
    the app default, passed on as None so each mode applies its own rule (the theme peers' slots
    come on top, as in fts.search): fts -> fts.search's rule, the token budget (budget_tokens(q),
    #213, ADR-019) or budget(q) - peer_slots(q) passages when TOKEN_BUDGET is None; hybrid modes ->
    budget(q) - peer_slots(q) passages (hybrid stays on the passage budget: its candidate counts
    scale with k, RERANK_N x k / K, and are not tuned for a token budget). trace (#210): filled with
    the candidate pools before select(), recording only.
    plan (#214, ADR-020): fts with a plan and k None -> planner.search_parts(q, plan) exactly as
    `main` (part_pools filled per part); hybrid modes ignore the plan's parts and search the whole
    question once (part_id "p1")."""
    mode = resolve_mode(mode)
    if mode == "fts":
        if plan is not None and k is None:
            return planner.search_parts(q, plan, trace=trace, part_pools=part_pools)
        return fts.search(q, k, trace=trace)
    k = fts.budget(q) - fts.peer_slots(q) if k is None else k
    if not vectors_enabled():  # checked before the import: vectors off never loads hybrid
        raise HybridUnavailable(HYBRID_NEEDS_VECTORS)
    from cee.retrieve import hybrid  # imported late: fts mode never loads a model
    hits = hybrid.search(q, k, trace=trace, rerank=mode == "hybrid")
    if plan is not None:
        for h in hits:
            h.part_id = "p1"
    return hits
