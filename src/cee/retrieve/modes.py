"""Retrieval mode switch (experimental branch exp/hybrid; #125, #126, #128, #211).

`main` has one mode, `fts` (ADR-010). On this branch `search(q, mode=...)` picks one of three:
  fts              - keyword search, `cee.retrieve.fts.search` (unchanged from `main`)
  hybrid           - keyword + vector legs, RRF, local cross-encoder order (`cee.retrieve.hybrid`)
  hybrid-norerank  - the same candidates as hybrid, final order by the RRF score, no reranker
None -> RETRIEVAL_MODE (environment or .env), default fts. Both hybrid modes need the optional
vectors module (CEE_VECTORS=on, ADR-009); `hybrid` is imported only then, so fts mode never loads
a model. The switch lives here (not in fts.py) so that fts.py stays byte-equal to `main` (#211).
"""
from __future__ import annotations

from cee.config import settings, vectors_enabled
from cee.retrieve import fts
from cee.retrieve.fts import Hit, PoolTrace, Query

MODES = ("fts", "hybrid", "hybrid-norerank")


class HybridUnavailable(RuntimeError):
    """Hybrid mode asked for while the optional vectors module is off (ADR-009)."""


HYBRID_NEEDS_VECTORS = (
    "Hybrid retrieval needs the optional vectors module: set CEE_VECTORS=on, install "
    "requirements-vectors.txt and fill the vectors (docs/RUN.md, 'Hybrid retrieval'), or use "
    "RETRIEVAL_MODE=fts.")


def search(q: Query, k: int | None = None, mode: str | None = None,
           trace: PoolTrace | None = None) -> list[Hit]:
    """Retrieve for one request. k: passages for the named firms and the research part; None =
    budget(q) - peer_slots(q), the app default (the theme peers' slots come on top, as in
    fts.search). trace (#210): filled with the candidate pools before select(), recording only."""
    mode = (mode or settings().retrieval_mode).strip().lower()
    if mode not in MODES:
        raise ValueError(f"unknown retrieval mode {mode!r}; use one of {', '.join(MODES)}")
    k = fts.budget(q) - fts.peer_slots(q) if k is None else k
    if mode == "fts":
        return fts.search(q, k, trace=trace)
    if not vectors_enabled():  # checked before the import: vectors off never loads hybrid
        raise HybridUnavailable(HYBRID_NEEDS_VECTORS)
    from cee.retrieve import hybrid  # imported late: fts mode never loads a model
    return hybrid.search(q, k, trace=trace, rerank=mode == "hybrid")
