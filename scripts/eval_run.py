"""Run the question bank against the loaded snapshot and write a per-question report (#43).

Default is mock: retrieval only, no model call, free. For each question it records the resolved
entities, the retrieved chunk IDs, which `expected_sources` patterns were hit, forbidden hits
(another firm's chunks; BAC chunks outside GWIM for Merrill questions) and a status.

  python scripts/eval_run.py                          # all 30, mock
  python scripts/eval_run.py --questions Q1,Q4 --k 20   # fixed k (default: the app's budget by question)
  python scripts/eval_run.py --baseline .eval-runs/<run>/report.json
  python scripts/eval_run.py --real --max-calls 5 --questions Q28,Q29,Q30
  python scripts/eval_run.py --mode hybrid         # retrieval mode (#125); default RETRIEVAL_MODE
  python scripts/eval_run.py --mode hybrid-norerank --floor 0,0.2,0.3,0.4 --max-per-doc 2,3,4 \
      --baseline .eval-runs/<fts reference>/report.json   # grid run and selection rule (#126)

Constants (#126): --floor and --max-per-doc (one value or a comma list each) set the
mode's constants for the run (fts: fts.FLOOR / fts.MAX_PER_DOC; hybrid modes: hybrid.FLOOR /
MAX_PER_DOC [mode]) and are restored afterwards; DUP_JACCARD is fts.DUP_JACCARD in every mode (#211).
More than one combination is a grid: one run folder per point (f<floor>-m<max>), the models load
once, and grid.md / grid.json hold every point and the point choose() picks (SELECTION_RULE).
Every report records the constants it ran with, the duplicate measure (pairs of hits > 0.9
similar) and search time median / p90 / max with the CPU it ran on.

Search time: every question's `search()` is timed (`search_s`); one untimed warm-up search on the
first question comes first (`warmup_s`, model loading in hybrid mode), and the median goes into
the summary and the report header.

--real calls the configured provider (LLM_PROVIDER), at most --max-calls times, and saves every
model output in .eval-runs/cache/ so the same question + prompt version + snapshot + model +
retrieved chunks is never paid for twice (CLAUDE.md "Paid API calls"). Reports go to
.eval-runs/<snapshot>-<time>/report.md and report.json.

Status (retrieval level): FAIL on any forbidden hit; NOT_EVALUATED when no expected pattern is
available in the corpus; PASS when coverage of the available patterns >= --min-coverage;
otherwise FAIL. With --real the answer's behavior must also equal expected_behavior.
INVALID_OUTPUT (--real only, #187): the model's output was not a valid Answer (e.g. a wrong field
name, or no answer tool call). The raw payload is still saved in the cache and the run's raw/
folder, the call still counts against --max-calls, the note keeps the retrieval status, and the
run moves on. A cached invalid output is reported again, never re-called.

Recall and refusal accuracy (#60), for questions with an answer key in evals/expected_chunks.yaml
(or, once #56 lands, `expected_doc_ids` in questions.yaml): document and passage recall against
must_return, and a refusal check that FAILs the question when a must_not_return chunk, a forbidden
hit or (Q26) a chunk older than the window comes back. --as-of fixes the day the window ends.

Recall by stage (#210): search() fills a PoolTrace with the chunk ids of every candidate pool
before select(); recall@pool = expected passages with a chunk in a pool, recall@final = in the
retrieved set. Each expected row is `final`, `pool` (lost in select) or `none` (never a candidate).
Estimated tokens = characters / 4.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import itertools
import json
import os
import platform
import re
import statistics
import subprocess
import time
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from cee.config import entities_config  # noqa: E402
from cee.retrieve.fts import K, _shingles, _similar, theme_gaps  # noqa: E402

RUNS = REPO / ".eval-runs"
CACHE = RUNS / "cache"
QUESTIONS = REPO / "evals" / "questions.yaml"
KEYS = REPO / "evals" / "expected_chunks.yaml"
STATUSES = ("PASS", "FAIL", "NOT_EVALUATED", "INVALID_OUTPUT")
GAP_BEHAVIORS = ("gap_with_adjacent", "refuse")
RETRIEVAL_MODES = ("fts", "hybrid", "hybrid-norerank")
DUP_LIMIT = 0.9  # specs/retrieval.md: no two hits > 90% similar
MODE_DEFAULTS = {"fts": (0.3, 3), "hybrid": (0.0, 3), "hybrid-norerank": (0.0, 3)}  # (FLOOR, MAX_PER_DOC) before #126
SELECTION_RULE = (
    "1. Eligible: forbidden hits 0 on all questions; refusal accuracy on the gap questions and on all "
    "keyed questions >= the fts reference run (--baseline). "
    "2. Among eligible points: highest tier-1 passage recall (3 decimals). "
    "3. Ties: higher tier-1 doc recall; more PASS; the mode's default before #126 (fts 0.3/3, hybrid "
    "modes 0/3); higher FLOOR; smaller MAX_PER_DOC. "
    "4. No eligible point: no tuned constants (defaults stay); the mode fails the refusal acceptance.")


# --- duplicate measure (#126) ---------------------------------------------------------------------

def trigrams(text: str) -> set[str]:
    """Character trigrams as pg_trgm builds them (Python re-implementation: pg_trgm is not installed
    in cee-db): lower case; words = runs of alphanumeric characters; each word padded with two spaces
    in front and one behind; every 3-character substring, as a set."""
    out: set[str] = set()
    for w in re.findall(r"[^\W_]+", text.lower()):
        padded = f"  {w} "
        out.update(padded[i:i + 3] for i in range(len(padded) - 2))
    return out


def trigram_similarity(a: str, b: str) -> float:
    """pg_trgm similarity(): shared trigrams / all distinct trigrams of both (0 if either is empty)."""
    ta, tb = trigrams(a), trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def duplicates(texts: list[str], limit: float = DUP_LIMIT) -> dict:
    """Every pair of hits: (a) pg_trgm-style trigram similarity, (b) word 5-gram Jaccard (select())."""
    tri = [trigrams(t) for t in texts]
    sh = [_shingles(t) for t in texts]
    max_t = max_s = 0.0
    over_t = over_s = 0
    for i, j in itertools.combinations(range(len(texts)), 2):
        t = len(tri[i] & tri[j]) / len(tri[i] | tri[j]) if tri[i] and tri[j] else 0.0
        s5 = _similar(sh[i], sh[j])
        max_t, max_s = max(max_t, t), max(max_s, s5)
        over_t += t > limit
        over_s += s5 > limit
    return {"max_trigram": round(max_t, 3), "pairs_trigram_over": over_t,
            "max_5gram": round(max_s, 3), "pairs_5gram_over": over_s}


@dataclass(frozen=True)
class Pattern:
    raw: str
    entity: str            # MS, BAC, MER, THEME, ...
    doc_type: str | None   # None = any ("*")
    qualifier: str | None  # must equal the chunk's segment


def parse_pattern(raw: str) -> Pattern:
    head, _, qual = raw.partition("#")
    entity, _, doc_type = head.partition(":")
    return Pattern(raw, entity.strip(), None if doc_type.strip() in ("", "*") else doc_type.strip(),
                   qual.strip() or None)


def substitutes() -> dict[str, tuple[str, list[str]]]:
    """Entities reported inside a parent segment: MER -> ("BAC", ["GWIM", "Merrill"]) (fts.entity_filter)."""
    return {e["id"]: (e["parent"], [e["reported_as"], e["name"]])
            for e in entities_config()["entities"] if e.get("parent") and e.get("reported_as")}


def _segment_in(hit, segments: list[str]) -> bool:
    return bool(hit.segment) and hit.segment.lower() in {s.lower() for s in segments}


def match(p: Pattern, hit, subs: dict) -> str | None:
    """'hit', 'type' (entity and type right, qualifier not met) or None."""
    if p.entity == "THEME":
        ok_entity = hit.entity_id is None
    elif p.entity in subs:
        parent, segs = subs[p.entity]
        ok_entity = hit.entity_id == p.entity or (hit.entity_id == parent and _segment_in(hit, segs))
    else:
        ok_entity = hit.entity_id == p.entity
    if not ok_entity or (p.doc_type and hit.doc_type != p.doc_type):
        return None
    if p.qualifier and not _segment_in(hit, [p.qualifier]):
        return "type"
    return "hit"


def available(p: Pattern, corpus: set[tuple[str | None, str]], subs: dict) -> bool:
    """The loaded corpus holds at least one document this pattern could match."""
    owners = [None] if p.entity == "THEME" else [p.entity]
    if p.entity in subs and p.doc_type is None:
        owners.append(subs[p.entity][0])           # MER:* lives in BAC GWIM chunks
    return any(e in owners and (p.doc_type is None or t == p.doc_type) for e, t in corpus)


def theme_text_pattern(themes: list[str]):
    """The theme's keyword pattern, rebuilt here from config/topics.yaml (top-level topics) and the
    firm themes in config/entities.yaml with the tagger's own pattern (cee.ingest.topics), so the
    eval does not trust the on_theme flag search() sets (#205)."""
    import re
    from cee.ingest.topics import _pattern, load_topics
    words = {t.topic_id: t.pattern.pattern for t in load_topics() if t.parent is None}
    words |= {t["id"]: _pattern(t["keywords"]).pattern for t in entities_config().get("firm_themes") or []}
    parts = [f"(?:{words[t]})" for t in themes if t in words]
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


def _peer_on_theme(query, hit, subs: dict) -> bool:
    """A hit of a firm the question does not name is allowed only as a home-firm theme peer
    (#205, ADR-018): its firm is in query.theme_peers (a BAC hit only for MER, through the
    GWIM/Merrill segment), and its text has one of the theme's keywords."""
    peers = getattr(query, "theme_peers", None) or []
    if not peers or hit.entity_id is None:
        return False
    if hit.entity_id not in peers:
        via_parent = [e for e in peers if e in subs and subs[e][0] == hit.entity_id]
        if not via_parent or not all(_segment_in(hit, subs[e][1]) for e in via_parent):
            return False
    pattern = theme_text_pattern(query.themes)
    return bool(pattern and pattern.search(hit.text))


def forbidden(query, hits, subs: dict) -> list[str]:
    """Hits the hard filters should never let through for this question."""
    if not query.entities:
        return []
    allowed = set(query.entities)
    bad = []
    for h in hits:
        if h.entity_id in allowed:
            continue
        if h.entity_id is None and query.mode == "entity+theme":
            continue  # tier 5 research on the named topic (fts.theme_filter, #116)
        via_parent = [e for e in query.entities if e in subs and subs[e][0] == h.entity_id]
        if via_parent and all(_segment_in(h, subs[e][1]) for e in via_parent):
            continue
        if _peer_on_theme(query, h, subs):
            continue
        bad.append(h.chunk_id)
    return bad


def load_keys(path: Path = KEYS) -> dict[str, dict]:
    """The hand-written answer key (evals/expected_chunks.yaml), normalised; {} when absent."""
    if not path.is_file():
        return {}
    keys = {}
    for qid, k in (yaml.safe_load(path.read_text(encoding="utf-8"))["questions"] or {}).items():
        keys[qid] = {"must_return": [list(r) for r in k.get("must_return") or []],
                     "must_not_return": list(k.get("must_not_return") or [])}
        if k.get("window_days"):
            keys[qid]["window_days"] = int(k["window_days"])
    return keys


def key_for(q: dict, keys: dict) -> dict | None:
    """The hand-written key, else one row per `expected_doc_ids` entry (#56), else None."""
    if q["id"] in keys:
        return keys[q["id"]]
    if q.get("expected_doc_ids"):
        return {"must_return": [[d] for d in q["expected_doc_ids"]], "must_not_return": [], "source": "#56"}
    return None


def _doc(id_: str) -> str:
    return id_.split("#")[0]


def _is(id_: str, hit) -> bool:
    """`DOC#seq` matches that chunk; `DOC` matches any chunk of the document."""
    return hit.chunk_id == id_ if "#" in id_ else hit.doc_id == id_


def _ratio(found: int, of: int) -> float | None:
    return round(found / of, 3) if of else None


def _is_chunk(id_: str, chunk_id: str) -> bool:
    """`_is` for a bare chunk id (the pool trace keeps ids only; doc_id = the part before '#')."""
    return chunk_id == id_ if "#" in id_ else chunk_id.split("#")[0] == id_


def score_key(key: dict, hits, forbidden_ids: list[str], as_of: dt.date | None = None,
              doc_dates: dict | None = None, pool_ids: set[str] | None = None) -> dict:
    """Recall against must_return (documents and passages) and the refusal check (#60).
    pool_ids (#210): chunk ids of every candidate pool before select(); each row gets a stage,
    `final` (retrieved), `pool` (a candidate, lost in select()) or `none` (never a candidate), and
    recall_pool = rows with an id in the pool / rows. recall_final is passage_recall."""
    rows, window, outside = key["must_return"], None, []
    if key.get("window_days"):
        as_of = as_of or dt.date.today()
        start, end = (as_of - dt.timedelta(days=key["window_days"])).isoformat(), as_of.isoformat()
        window = {"from": start, "to": end}
        dates = doc_dates or {}
        # a row is expected only if one of its documents is inside the window (unknown date: kept)
        rows = [r for r in rows if any(dates.get(_doc(i)) is None or start <= str(dates[_doc(i)])[:10] <= end
                                       for i in r)]
        outside = [h.chunk_id for h in hits if not start <= str(h.published_at)[:10] <= end]
    found_rows = [{"ids": r, "found": [h.chunk_id for h in hits if any(_is(i, h) for i in r)]} for r in rows]
    pool = set(pool_ids or ()) | {h.chunk_id for h in hits}   # a final hit is always a candidate
    for row in found_rows:
        row["pool"] = sorted(c for c in pool if any(_is_chunk(i, c) for i in row["ids"]))
        row["stage"] = "final" if row["found"] else "pool" if row["pool"] else "none"
    passages_in_pool = sum(bool(r["pool"]) for r in found_rows)
    docs = list(dict.fromkeys(_doc(i) for r in rows for i in r))
    got_docs = {h.doc_id for h in hits}
    misleading = [h.chunk_id for h in hits
                  if h.chunk_id in forbidden_ids or any(_is(i, h) for i in key["must_not_return"])]
    passages_found = sum(bool(r["found"]) for r in found_rows)
    docs_found = sum(d in got_docs for d in docs)
    return {"rows": found_rows, "passages": len(rows), "passages_found": passages_found,
            "passage_recall": _ratio(passages_found, len(rows)), "passages_in_pool": passages_in_pool,
            "recall_pool": _ratio(passages_in_pool, len(rows)), "recall_final": _ratio(passages_found, len(rows)),
            "expected_docs": docs, "docs": len(docs),
            "docs_found": docs_found, "doc_recall": _ratio(docs_found, len(docs)), "misleading": misleading,
            "outside_window": outside, "window": window, "refusal_ok": not misleading and not outside,
            "source": key.get("source", "expected_chunks.yaml")}


def _median(xs: list):
    if not xs:
        return None
    xs, n = sorted(xs), len(xs)
    return xs[n // 2] if n % 2 else round((xs[n // 2 - 1] + xs[n // 2]) / 2, 3)


def summarize(records: list[dict]) -> dict:
    """Tier-1 recall (mean over questions with a key) and refusal accuracy (gap questions, all keyed)."""
    tier1 = [r for r in records if r.get("tier") == 1]
    with_key = [r for r in tier1 if r.get("doc_recall") is not None]

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    def accuracy(rs):
        ok = sum(r["refusal_ok"] is True for r in rs)
        return {"ok": ok, "of": len(rs), "accuracy": _ratio(ok, len(rs))}

    keyed = [r for r in records if r.get("refusal_ok") is not None]
    staged = [r for r in records if r.get("recall_pool") is not None]   # keyed, with expected rows (#210)
    staged1 = [r for r in staged if r.get("tier") == 1]
    times = sorted(r["search_s"] for r in records if r.get("search_s") is not None)
    dups = [r["dup"] for r in records if r.get("dup")]
    return {"median_search_s": round(statistics.median(times), 3) if times else None,
            "p90_search_s": round(times[max(0, -(-9 * len(times) // 10) - 1)], 3) if times else None,
            "max_search_s": round(times[-1], 3) if times else None,
            "dup_questions_trigram_over": sum(d["pairs_trigram_over"] > 0 for d in dups),
            "dup_pairs_trigram_over": sum(d["pairs_trigram_over"] for d in dups),
            "dup_max_trigram": max((d["max_trigram"] for d in dups), default=None),
            "dup_questions_5gram_over": sum(d["pairs_5gram_over"] > 0 for d in dups),
            "dup_pairs_5gram_over": sum(d["pairs_5gram_over"] for d in dups),
            "dup_max_5gram": max((d["max_5gram"] for d in dups), default=None),
            "pass": sum(r.get("status") == "PASS" for r in records),
            "forbidden_hits": sum(len(r.get("forbidden") or []) for r in records),
            "tier1_doc_recall": mean([r["doc_recall"] for r in with_key]),
            "tier1_passage_recall": mean([r["passage_recall"] for r in with_key if r["passage_recall"] is not None]),
            "tier1_with_key": len(with_key), "tier1_total": len(tier1),
            "recall_pool": mean([r["recall_pool"] for r in staged]),
            "recall_final": mean([r["recall_final"] for r in staged]),
            "tier1_recall_pool": mean([r["recall_pool"] for r in staged1]),
            "tier1_recall_final": mean([r["recall_final"] for r in staged1]),
            "with_rows": len(staged), "tier1_with_rows": len(staged1),
            "passages": sum(r.get("passages", 0) for r in records),
            "tokens_est": sum(r.get("tokens_est", 0) for r in records),
            # #213: tokens per question (all hits, what the model reads), peers apart, search time
            "tokens_median": _median([r["tokens_est"] for r in records if "tokens_est" in r]),
            "tokens_max": max((r["tokens_est"] for r in records if "tokens_est" in r), default=None),
            "peer_tokens": sum(r.get("peer_tokens", 0) for r in records),
            "search_s_median": _median([r["search_s"] for r in records if r.get("search_s") is not None]),
            "search_s_max": max((r["search_s"] for r in records if r.get("search_s") is not None), default=None),
            "refusal_gap": accuracy([r for r in keyed if r.get("expected_behavior") in GAP_BEHAVIORS]),
            "refusal_all": accuracy(keyed)}


def evaluate(q: dict, query, hits, corpus, subs, min_coverage: float, key: dict | None = None,
             as_of: dt.date | None = None, doc_dates: dict | None = None, pool_ids: set[str] | None = None) -> dict:
    patterns = [parse_pattern(s) for s in q.get("expected_sources", [])]
    rows = []
    for p in patterns:
        found = {"hit": [], "type": []}
        for h in hits:
            m = match(p, h, subs)
            if m:
                found[m].append(h.chunk_id)
        rows.append({"pattern": p.raw, "available": available(p, corpus, subs),
                     "hits": found["hit"], "type_only": found["type"]})
    avail = [r for r in rows if r["available"]]
    hit = [r for r in avail if r["hits"]]
    coverage = round(len(hit) / len(avail), 3) if avail else None
    bad = forbidden(query, hits, subs)
    recall = score_key(key, hits, bad, as_of, doc_dates, pool_ids) if key else None
    if bad or (recall and not recall["refusal_ok"]):
        status = "FAIL"
    elif not avail:
        status = "NOT_EVALUATED"
    else:
        status = "PASS" if coverage >= min_coverage else "FAIL"
    return {"id": q["id"], "text": q["text"], "use_case": q.get("use_case"), "tier": q.get("tier"),
            "trap": q.get("trap", False), "expected_behavior": q.get("expected_behavior"), "entities": query.entities,
            "unmapped": query.unmapped, "theme_peers": getattr(query, "theme_peers", []), "mode": query.mode, "themes": query.themes,
            "theme_gaps": theme_gaps(query, hits), "chunk_ids": [h.chunk_id for h in hits],
            "ranks": [None if getattr(h, "rank", None) is None else round(float(h.rank), 4) for h in hits],  # score per hit (fts rank, RRF score or rerank sigmoid), for #126
            "patterns": rows, "available_patterns": len(avail), "hit_patterns": len(hit),
            "coverage": coverage, "forbidden": bad,
            "doc_recall": recall["doc_recall"] if recall else None,
            "passage_recall": recall["passage_recall"] if recall else None,
            "recall_pool": recall["recall_pool"] if recall else None,
            "recall_final": recall["recall_final"] if recall else None,
            "pool_size": len(set(pool_ids or ()) | {h.chunk_id for h in hits}) if pool_ids is not None else None,
            "refusal_ok": recall["refusal_ok"] if recall else None,
            "misleading": recall["misleading"] if recall else [], "recall": recall, "status": status,
            "dup": duplicates([h.text for h in hits if getattr(h, "text", None) is not None])}


def prompt_size(k: int | None, hits, budget_tokens: int | None = None, peer_ids=()) -> dict:
    """What the model is handed (#181): the budget k, passages retrieved, their characters and the
    estimated tokens, characters / 4 (#210). Token budget (#213): `budget_tokens` (None in passage
    mode); the theme peers' hits (#205, ids in `peer_ids`) are outside the budget, so they are
    counted apart and `budgeted_*`, `max_hit_chars` and `fill` cover the other hits only."""
    peer_ids = set(peer_ids)
    chars = sum(len(h.text) for h in hits)
    peers = [h for h in hits if h.chunk_id in peer_ids]
    budgeted = [h for h in hits if h.chunk_id not in peer_ids]
    b_chars = sum(len(h.text) for h in budgeted)
    p_chars = chars - b_chars
    return {"k": k, "passages": len(hits), "chars": chars, "tokens_est": round(chars / 4),
            "budget_tokens": budget_tokens, "budgeted_chars": b_chars, "tokens_budgeted": round(b_chars / 4),
            "peer_passages": len(peers), "peer_chars": p_chars, "peer_tokens": round(p_chars / 4),
            "max_hit_chars": max((len(h.text) for h in budgeted), default=0),
            "fill": round(b_chars / (4 * budget_tokens), 3) if budget_tokens else None}


def _score(r: dict) -> tuple:
    return (r["status"] == "PASS", r.get("refusal_ok") is not False, r.get("doc_recall") or 0.0,
            r.get("passage_recall") or 0.0, r["coverage"] or 0.0, -len(r["forbidden"]))


def compare(record: dict, base: dict | None) -> str:
    if base is None:
        return "NEW"
    a, b = _score(record), _score(base)
    return "IMPROVED" if a > b else "REGRESSED" if a < b else "UNCHANGED"


def cache_key(q: dict, prompt_version: str, snapshot: str, provider: str, model: str, chunk_ids: list,
              max_tokens: int = 8000, plan_parts: list | None = None, window=None) -> str:
    """max_tokens (#213) joins the key only when it is not 8000: outputs saved so far keep their
    key, and a run with another output cap never reuses one made under 8000. The window (#230)
    joins it only when the question has one (the v4.1 user message names it; --as-of moves it)."""
    parts = [q["id"], q["text"], prompt_version, snapshot, provider, model, chunk_ids]
    if max_tokens != 8000:
        parts = [*parts, {"max_tokens": max_tokens}]
    if plan_parts is not None:   # #215: the v4 user message lists the plan's parts
        parts = [*parts, {"parts": plan_parts}]
    if window:
        parts = [*parts, {"window": [str(window[0]), str(window[1])]}]
    blob = json.dumps(parts)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def parts_of(plan) -> list | None:
    """The plan's parts as the answer cache key sees them (#215): [[id, text, firms], ...]."""
    return None if plan is None else [[p.id, p.text, list(p.firms)] for p in plan.parts]


def plan_cache_key(q: dict, snapshot: str, provider: str, model: str, max_parts: int, query: dict) -> str:
    """Planner outputs (#214) are cached apart from answers: question, planner version, snapshot,
    provider, model, part cap, the planner's output cap and the resolved query."""
    from cee.retrieve.planner import PLANNER_MAX_TOKENS, PLANNER_VERSION
    parts = [q["id"], q["text"], PLANNER_VERSION, snapshot, provider, model, max_parts, PLANNER_MAX_TOKENS, query]
    return hashlib.sha256(json.dumps(parts, default=str, sort_keys=True).encode()).hexdigest()[:24]


def part_stages(recall: dict | None, hits, pools: dict[str, set[str]]) -> None:
    """Per expected row (#214): the plan parts whose candidate pool held it (`parts_pool`) and the
    part that kept it (`parts_final`; `research` / `peers` for those passes)."""
    if not recall:
        return
    by_id = {h.chunk_id: h for h in hits}
    for row in recall["rows"]:
        row["parts_pool"] = [pid for pid, ids in pools.items()
                             if any(_is_chunk(i, c) for c in ids for i in row["ids"])]
        row["parts_final"] = sorted({by_id[c].part_id or "" for c in row["found"] if c in by_id})


class RealRunner:
    """Model answers with a hard call cap; every output cached and reused (never re-rolled)."""

    def __init__(self, provider: str, max_calls: int, snapshot: str, run_dir: Path, cache_dir: Path = CACHE):
        from cee.answer import llm
        from cee.answer.prompt import PROMPT_VERSION
        from cee.ask import model_name

        if provider == "mock":
            raise SystemExit("--real needs LLM_PROVIDER=anthropic or openai; it is mock.")
        self.provider, self.max_calls, self.snapshot = provider, max_calls, snapshot
        self.model, self.prompt_version = model_name(provider), PROMPT_VERSION
        self.max_tokens = llm.MAX_TOKENS
        self.calls, self.reused, self.last_file = 0, 0, None
        self.last_stop: tuple[str | None, int | None] = (None, None)   # stop_reason, output tokens (#230)
        self.cache_dir, self.raw_dir = cache_dir, run_dir / "raw"

    def answer(self, q: dict, query, hits, plan=None) -> tuple[dict | None, str]:
        """(answer dict or None, how): how = no_call | cached | called | cap | invalid.
        invalid: the model output (new or cached) is not a valid Answer; its raw payload is in
        raw/<self.last_file> and the call still counts (#187)."""
        from cee.answer.llm import ModelOutputError, check_output
        from cee.answer.schema import Answer
        from cee.ask import answer_for, answer_window

        self.last_file, self.last_stop = None, (None, None)
        if not hits:
            answer, _ = answer_for(q["text"], query, hits, self.provider)
            return answer.model_dump(), "no_call"
        key = cache_key(q, self.prompt_version, self.snapshot, self.provider, self.model,
                        [h.chunk_id for h in hits], self.max_tokens, parts_of(plan), answer_window(query))
        path = self.cache_dir / f"{q['id']}-{key}.json"
        self.last_file = path.name
        if path.is_file():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.reused += 1
            self._copy(path)
            self.last_stop = (saved.get("stop_reason"), (saved.get("usage") or {}).get("output_tokens"))
            if saved.get("invalid"):    # a wrong output is a finding: never re-called (CLAUDE.md)
                return None, "invalid"
            raw = Answer(**saved["raw"])
            try:                        # #230: a saved cut or empty output is invalid on reuse too
                check_output(raw, saved["raw"], self.provider)
            except ModelOutputError:
                return None, "invalid"
            answer, _ = answer_for(q["text"], query, hits, self.provider, raw=raw, plan=plan)
            return answer.model_dump(), "cached"
        if self.calls >= self.max_calls:
            return None, "cap"
        self.calls += 1   # counted before the call: a failed call still cost money
        meta = {"question_id": q["id"], "question": q["text"], "prompt_version": self.prompt_version,
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model,
                "max_tokens": self.max_tokens, "chunk_ids": [h.chunk_id for h in hits], "at": dt.datetime.now().isoformat()}
        try:
            answer, raw = answer_for(q["text"], query, hits, self.provider, plan=plan)
        except ModelOutputError as e:   # paid output that is not a valid Answer: keep it (#187)
            usage = getattr(e, "usage", None) or {}
            self.last_stop = (getattr(e, "stop_reason", None), usage.get("output_tokens"))
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                              "stop_reason": getattr(e, "stop_reason", None), "usage": usage})
            return None, "invalid"
        self.last_stop = (raw.stop_reason or None, raw.usage.get("output_tokens"))
        self._save(path, {**meta, "stop_reason": raw.stop_reason, "usage": raw.usage, "raw": raw.model_dump()})
        return answer.model_dump(), "called"

    def plan(self, q: dict, query):
        """The question's plan (#214, ADR-020) from one planner call, cached like an answer: a saved
        plan (valid, invalid or a failed call) is always reused, so a re-run never calls the planner
        again. None when the call would pass --max-calls. No call when the planner is off, the
        question is not searched, or passage mode (planner.plan_question decides)."""
        from dataclasses import asdict

        from cee.config import settings
        from cee.retrieve import fts, planner

        cap = settings().planner_max_parts
        if not settings().planner or not fts.searchable(query) or fts.budget_tokens(query) is None:
            return planner.plan_question(query, self.provider, cap=cap)
        key = plan_cache_key(q, self.snapshot, self.provider, self.model, cap, asdict(query))
        path = self.cache_dir / f"{q['id']}-plan-{key}.json"
        if path.is_file():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.reused += 1
            self._copy(path)
            if saved.get("invalid"):
                return planner.from_output(query, saved.get("raw_payload"), self.provider, cap, error=saved["error"])
            return planner.from_output(query, saved["raw"], self.provider, cap)
        if self.calls >= self.max_calls:
            return None
        self.calls += 1   # counted before the call: a failed call still cost money
        meta = {"question_id": q["id"], "question": q["text"], "planner_version": planner.PLANNER_VERSION,
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model, "max_parts": cap,
                "max_tokens": planner.PLANNER_MAX_TOKENS, "query": asdict(query),
                "at": dt.datetime.now().isoformat()}
        call: dict = {}   # #230: stop_reason and usage of the call, saved with every plan record
        try:
            raw = planner.call_planner(query, self.provider, cap, meta=call)
        except planner.PlannerOutputError as e:
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                              "stop_reason": e.stop_reason, "usage": call.get("usage")})
            return planner.from_output(query, e.raw, self.provider, cap, error=str(e))
        except Exception as e:   # API / network: the rule plan, the call counted, never re-called
            err = f"{type(e).__name__}: {e}"
            self._save(path, {**meta, "invalid": True, "failed_call": True, "error": err, "raw_payload": None})
            return planner.from_output(query, None, self.provider, cap, error=err)
        self._save(path, {**meta, "stop_reason": call.get("stop_reason"), "usage": call.get("usage"), "raw": raw})
        return planner.from_output(query, raw, self.provider, cap)

    def _save(self, path: Path, record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # default=str: an unexpected payload type must never cost the paid output (#187)
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        self._copy(path)

    def _copy(self, path: Path) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def apply_real(record: dict, answer: dict | None, how: str, raw_file: str | None = None) -> dict:
    record["model"] = how
    if how == "invalid":   # the retrieval status is kept in the note (#187)
        record["note"] = (f"retrieval {record['status']}; model output invalid, see raw/{raw_file}"
                          if raw_file else f"retrieval {record['status']}; model output invalid")
        record["status"], record["behavior"] = "INVALID_OUTPUT", None
        return record
    if answer is None:
        record["status"], record["behavior"] = "NOT_EVALUATED", None
        record["note"] = "not run: --max-calls reached"
        return record
    record["behavior"] = answer["behavior"]
    record["answer"] = answer
    if record["status"] == "PASS" and answer["behavior"] != record["expected_behavior"]:
        record["status"] = "FAIL"
    return record


def corpus_types() -> tuple[set, str, dict]:
    """(entity, doc_type) pairs, snapshot name, and doc_id -> published_at (for windowed keys)."""
    from cee.db import connect

    with connect() as c:
        rows = c.execute("SELECT entity_id, doc_type, doc_id, published_at FROM documents").fetchall()
        snap = c.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
    return ({(r["entity_id"], r["doc_type"]) for r in rows}, snap or "none (built locally)",
            {r["doc_id"]: str(r["published_at"]) for r in rows})


def _frac(found, of) -> str:
    return f"{found}/{of}" if of else "-"


def _refusal(r: dict) -> str:
    if r.get("refusal_ok") is None:
        return "-"
    rec = r["recall"]
    return "ok" if r["refusal_ok"] else f"FAIL ({len(rec['misleading']) + len(rec['outside_window'])})"


def _constants_text(c: dict | None) -> str:
    return ", ".join(f"{k} {v}" for k, v in (c or {}).items()) or "-"


def write_reports(run_dir: Path, meta: dict, records: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(records)
    (run_dir / "report.json").write_text(json.dumps({"meta": meta, "summary": summary, "questions": records},
                                                    indent=2), encoding="utf-8")
    counts = {s: sum(r["status"] == s for r in records) for s in STATUSES}
    gap_ids = ", ".join(r["id"] for r in records if r.get("expected_behavior") in GAP_BEHAVIORS
                        and r.get("refusal_ok") is not None)
    rg, ra = summary["refusal_gap"], summary["refusal_all"]
    lines = [f"# Eval run {meta['run_id']}", "",
             f"Snapshot `{meta['snapshot']}` | commit `{meta['commit']}` | k={meta['k']} | "
             f"min coverage {meta['min_coverage']} | as of {meta['as_of']} | mode {meta['mode']}"
             f" | retrieval {meta.get('retrieval_mode', 'fts')}"
             + (f" | median search {summary['median_search_s']} s (p90 {summary.get('p90_search_s')} s, max "
                f"{summary.get('max_search_s')} s; warm-up {meta.get('warmup_s')} s)"
                if summary.get("median_search_s") is not None else "")
             + (f" | real calls {meta['real_calls']} of max {meta['max_calls']}, reused {meta['reused']}"
                if meta["mode"] == "real" else " | 0 real calls"),
             "", f"**PASS {counts['PASS']} | FAIL {counts['FAIL']} | NOT_EVALUATED {counts['NOT_EVALUATED']}"
             f" | INVALID_OUTPUT {counts['INVALID_OUTPUT']}**"
             + (f" (baseline `{meta['baseline']}`)" if meta.get("baseline") else ""), "",
             f"**Tier-1 recall**: documents {summary['tier1_doc_recall']}, passages "
             f"{summary['tier1_passage_recall']} (mean over the {summary['tier1_with_key']} of "
             f"{summary['tier1_total']} tier-1 questions with an answer key; the rest n/a until #56)  ",
             f"**Recall by stage** (#210, mean over the {summary['with_rows']} questions with expected passages): "
             f"recall@pool {summary['recall_pool']}, recall@final {summary['recall_final']}; tier 1 "
             f"({summary['tier1_with_rows']}): recall@pool {summary['tier1_recall_pool']}, recall@final "
             f"{summary['tier1_recall_final']}  ",
             f"**Prompt size**: {summary['passages']} passages, ~{summary['tokens_est']} tokens (characters / 4) "
             f"over {len(records)} questions; per question median {summary.get('tokens_median')}, max "
             f"{summary.get('tokens_max')}; theme peers ~{summary.get('peer_tokens', 0)} tokens (outside the budget)  ",
             f"**Settings** (#213): pool {meta.get('pool_per_group', '-')} per firm and document type, token budget "
             f"{meta.get('token_budget') or 'none (passage rule)'}; search time per question median "
             f"{summary.get('search_s_median')} s, max {summary.get('search_s_max')} s  ",
             f"**Refusal accuracy**: gap questions ({gap_ids or 'none'}) {_frac(rg['ok'], rg['of'])}; "
             f"all questions with a key {_frac(ra['ok'], ra['of'])}  ",
             f"**Constants**: {_constants_text(meta.get('constants'))}  ",
             f"**Duplicates** (pairs of hits > {DUP_LIMIT} similar): trigram (pg_trgm-style, Python) "
             f"{summary.get('dup_pairs_trigram_over')} pairs in {summary.get('dup_questions_trigram_over')} questions, "
             f"max {summary.get('dup_max_trigram')}; word 5-gram {summary.get('dup_pairs_5gram_over')} pairs in "
             f"{summary.get('dup_questions_5gram_over')} questions, max {summary.get('dup_max_5gram')}  ",
             f"**CPU**: {meta.get('cpu', '-')}", "",
             "Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the "
             "corpus; PASS when coverage of the available patterns >= min coverage"
             + ("; real mode also needs behavior == expected." if meta["mode"] == "real" else "."), "",
             "Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved "
             "chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window. "
             "Recall@pool: expected passages with a chunk in any candidate pool before select(); recall@final: "
             "in the retrieved set (= Passages). Tokens: characters / 4.", "",
             "| Q | Tier | Use case | Expected | Firms (mode) | k | Hits | Chars | Tokens | Coverage | Recall docs"
             " | Passages (final) | Pool | Refusal | Forbidden | Status" + (" | Change" if meta.get("baseline") else "")
             + (" | Behavior" if meta["mode"] == "real" else "") + " |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---" + ("|---" if meta.get("baseline") else "")
             + ("|---" if meta["mode"] == "real" else "") + "|"]
    for r in records:
        cov = "-" if r["coverage"] is None else f"{r['hit_patterns']}/{r['available_patterns']}"
        rec = r.get("recall") or {}
        firms = ", ".join(r["entities"]) or "none"
        lines.append(f"| {r['id']}{' (trap)' if r['trap'] else ''} | {r.get('tier') or '-'} | {r['use_case']} | "
                     f"{r['expected_behavior']} | {firms} ({r['mode']}) | {r.get('k', '-')} | {len(r['chunk_ids'])} | "
                     f"{r.get('chars', '-')} | {r.get('tokens_est', '-')} | {cov} | "
                     f"{_frac(rec.get('docs_found'), rec.get('docs'))} | "
                     f"{_frac(rec.get('passages_found'), rec.get('passages'))} | "
                     f"{_frac(rec.get('passages_in_pool'), rec.get('passages'))} | {_refusal(r)} | "
                     f"{len(r['forbidden'])} | {r['status']}"
                     + (f" | {r.get('change', '')}" if meta.get("baseline") else "")
                     + (f" | {r.get('behavior') or r.get('note', '')}" if meta["mode"] == "real" else "") + " |")
    lines.append(f"| **All** | | | | | | {summary['passages']} | {sum(r.get('chars', 0) for r in records)} | "
                 f"{summary['tokens_est']} | | | {summary['recall_final']} (mean) | {summary['recall_pool']} (mean) | "
                 f"{_frac(ra['ok'], ra['of'])} | {sum(len(r['forbidden']) for r in records)} | "
                 f"PASS {counts['PASS']}" + (" | " if meta.get("baseline") else "")
                 + (" | " if meta["mode"] == "real" else "") + " |")
    lines += ["", "## Per question", ""]
    for r in records:
        lines += [f"### {r['id']} - {r['status']}", "", r["text"], ""]
        if r.get("mode") == "entity+theme":  # per-firm theme quota (#117)
            lines.append(f"- Theme {', '.join(r['themes'])}: no chunk on the theme for "
                         f"{', '.join(r['theme_gaps']) or 'no firm (every named firm has one)'}")
        for p in r["patterns"]:
            state = ("hit " + ", ".join(p["hits"])) if p["hits"] else (
                ("type only (qualifier not met): " + ", ".join(p["type_only"])) if p["type_only"] else
                ("no hit" if p["available"] else "not in corpus"))
            lines.append(f"- `{p['pattern']}`: {state}")
        rec = r.get("recall")
        if rec:
            if rec["window"]:
                lines.append(f"- Window: {rec['window']['from']} to {rec['window']['to']}")
            for row in rec["rows"]:
                stage = row.get("stage")
                lines.append(f"- Expected `{', '.join(row['ids'])}`: "
                             + (f"found {', '.join(row['found'])}" if row["found"] else
                                f"missing (in pool, lost in select: {', '.join(row['pool'])})" if stage == "pool" else
                                "missing (not in pool)" if stage == "none" else "missing"))
            if rec["misleading"]:
                lines.append(f"- **Misleading (must not come back):** {', '.join(rec['misleading'])}")
            if rec["outside_window"]:
                lines.append(f"- **Outside the window:** {', '.join(rec['outside_window'])}")
        if r["forbidden"]:
            lines.append(f"- **Forbidden hits:** {', '.join(r['forbidden'])}")
        lines += [f"- Retrieved: {', '.join(r['chunk_ids']) or 'nothing'}", ""]
    (run_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--questions", help="comma-separated IDs, e.g. Q1,Q4 (default: all)")
    ap.add_argument("--k", type=int, default=None,
                    help="chunks retrieved per question (default: the app's budget by firm count, fts.budget)")
    ap.add_argument("--min-coverage", type=float, default=0.5)
    ap.add_argument("--baseline", help="report.json of an earlier run, for UNCHANGED/IMPROVED/REGRESSED")
    ap.add_argument("--real", action="store_true", help="also get model answers (paid; needs --max-calls)")
    ap.add_argument("--max-calls", type=int, help="hard cap on paid model calls in this run")
    ap.add_argument("--out", help="run folder (default .eval-runs/<snapshot>-<time>)")
    ap.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today(),
                    help="day the time windows end, YYYY-MM-DD (default today)")
    ap.add_argument("--keys", type=Path, default=KEYS, help="answer key (default evals/expected_chunks.yaml)")
    ap.add_argument("--mode", choices=RETRIEVAL_MODES, help="retrieval mode (default RETRIEVAL_MODE, else fts)")
    ap.add_argument("--floor", help="FLOOR for the mode, one value or a comma list (grid; #126)")
    ap.add_argument("--max-per-doc", help="MAX_PER_DOC for the mode, one value or a comma list (grid; #126)")
    args = ap.parse_args(argv)
    if args.real and (args.max_calls is None or args.max_calls < 0):
        ap.error("--real needs --max-calls N (CLAUDE.md 'Paid API calls'); nothing was called")
    if args.max_calls is not None and args.max_calls > 10:
        print("Note: more than 10 calls needs the user's OK first (CLAUDE.md 'Paid API calls').")

    from cee.config import settings
    from cee.retrieve.fts import resolve
    from cee.retrieve.modes import search
    from cee.retrieve.planner import PLANNER_VERSION, plan_question, rules_plan
    retrieval_mode = args.mode or settings().retrieval_mode
    if retrieval_mode not in RETRIEVAL_MODES:
        ap.error(f"unknown retrieval mode {retrieval_mode!r}")
    try:
        floors = [float(x) for x in args.floor.split(",")] if args.floor else [None]
        maxes = [int(x) for x in args.max_per_doc.split(",")] if args.max_per_doc else [None]
    except ValueError:
        ap.error("--floor takes numbers and --max-per-doc whole numbers, comma separated")
    points = list(itertools.product(floors, maxes))
    if len(points) > 1 and not args.baseline:
        ap.error("a grid needs --baseline (the fts reference run the selection rule compares refusal with)")

    bank = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    if args.questions:
        wanted = [s.strip() for s in args.questions.split(",") if s.strip()]
        unknown = set(wanted) - {q["id"] for q in bank}
        if unknown:
            ap.error(f"unknown question IDs: {', '.join(sorted(unknown))}")
        bank = [q for q in bank if q["id"] in wanted]
    corpus, snapshot, doc_dates = corpus_types()
    keys = load_keys(args.keys)
    run_id = f"{snapshot}-{dt.datetime.now():%Y%m%d-%H%M%S}"
    out_dir = Path(args.out) if args.out else RUNS / run_id
    base, base_summary = {}, None
    if args.baseline:
        base_report = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        base = {r["id"]: r for r in base_report["questions"]}
        base_summary = base_report.get("summary")
    subs = substitutes()

    warmup_s = None
    if bank:  # untimed: loads models (hybrid) and warms the database cache
        from cee.retrieve.fts import budget_tokens
        q0 = resolve(bank[0]["text"], today=args.as_of)
        # same path as the timed run: fts token mode searches a plan (the mock plan here, 0 planner
        # calls) through planner.search_parts, as on main; passage / hybrid runs search the whole question
        plan0 = (plan_question(q0, "mock") if args.k is None and retrieval_mode == "fts"
                 and budget_tokens(q0) is not None else None)
        t = time.perf_counter()
        search(q0, k=args.k, mode=retrieval_mode, plan=plan0)
        warmup_s = round(time.perf_counter() - t, 3)

    grid = []
    for floor, max_per_doc in points:
        run_dir = out_dir / point_name(floor, max_per_doc) if len(points) > 1 else out_dir
        saved = set_constants(retrieval_mode, floor, max_per_doc)
        try:
            real = RealRunner(settings().llm_provider, args.max_calls, snapshot, run_dir) if args.real else None
            records, meta = run_bank(args, bank, keys, corpus, subs, base, real, retrieval_mode, search, resolve,
                                     run_id, snapshot, warmup_s, doc_dates, plan_question, rules_plan,
                                     PLANNER_VERSION)
            meta["constants"] = current_constants(retrieval_mode)
        finally:
            restore_constants(retrieval_mode, saved)
        write_reports(run_dir, meta, records)
        summary = summarize(records)
        counts = {s: sum(r["status"] == s for r in records) for s in STATUSES}
        print(f"\n{counts} | {retrieval_mode} {_constants_text(meta['constants'])} | tier-1 recall "
              f"{summary['tier1_doc_recall']} / passages {summary['tier1_passage_recall']} | recall@pool "
              f"{summary['recall_pool']} recall@final {summary['recall_final']} (tier 1: "
              f"{summary['tier1_recall_pool']} / {summary['tier1_recall_final']}) | passages "
              f"{summary['passages']} tokens~{summary['tokens_est']} | median search "
              f"{summary['median_search_s']} s | refusal gap {summary['refusal_gap']['ok']}/"
              f"{summary['refusal_gap']['of']} | real calls {meta['real_calls']} | report: {run_dir / 'report.md'}")
        grid.append({"floor": meta["constants"]["FLOOR"], "max_per_doc": meta["constants"]["MAX_PER_DOC"],
                     "constants": meta["constants"], "run": run_dir.name, "summary": summary})
    if len(points) > 1:
        write_grid(out_dir, retrieval_mode, grid, base_summary, args.baseline)
    return 0


def point_name(floor, max_per_doc) -> str:
    return f"f{floor}-m{max_per_doc}"


def current_constants(mode: str) -> dict:
    """The constants a run of this mode uses (also when no option was given)."""
    from cee.retrieve import fts
    if mode == "fts":
        return {"FLOOR": fts.FLOOR, "MAX_PER_DOC": fts.MAX_PER_DOC, "DUP_JACCARD": fts.DUP_JACCARD,
                "WINDOW_MAX_PER_DOC": fts.WINDOW_MAX_PER_DOC, "THEME_MAX_PER_DOC": fts.THEME_MAX_PER_DOC}
    from cee.retrieve import hybrid
    return {"FLOOR": hybrid.FLOOR[mode], "MAX_PER_DOC": hybrid.MAX_PER_DOC[mode],
            "DUP_JACCARD": fts.DUP_JACCARD, "RERANK_FLOOR": hybrid.RERANK_FLOOR,
            "RERANK_N": hybrid.RERANK_N, "WINDOW_MAX_PER_DOC": fts.WINDOW_MAX_PER_DOC,
            "THEME_MAX_PER_DOC": fts.THEME_MAX_PER_DOC}


def set_constants(mode: str, floor=None, max_per_doc=None) -> dict:
    """Set the mode's FLOOR / MAX_PER_DOC for one run; returns what restore needs.
    fts: fts.FLOOR, fts.MAX_PER_DOC; hybrid modes: hybrid.FLOOR[mode], hybrid.MAX_PER_DOC[mode].
    None = leave as is. DUP_JACCARD is never set (fts.DUP_JACCARD in every mode, #211)."""
    from cee.retrieve import fts
    values = {k: v for k, v in (("FLOOR", floor), ("MAX_PER_DOC", max_per_doc))
              if v is not None}
    if mode == "fts":
        saved = {k: getattr(fts, k) for k in values}
        for k, v in values.items():
            setattr(fts, k, v)
        return saved
    from cee.retrieve import hybrid
    saved = {k: getattr(hybrid, k)[mode] for k in values}
    for k, v in values.items():
        getattr(hybrid, k)[mode] = v
    return saved


def restore_constants(mode: str, saved: dict) -> None:
    from cee.retrieve import fts
    if mode == "fts":
        for k, v in saved.items():
            setattr(fts, k, v)
        return
    from cee.retrieve import hybrid
    for k, v in saved.items():
        getattr(hybrid, k)[mode] = v


def _acc(block: dict | None) -> float | None:
    return None if not block or block.get("accuracy") is None else block["accuracy"]


def choose(points: list[dict], reference: dict | None, mode: str) -> dict:
    """The selection rule (SELECTION_RULE), fixed in plans/0126-hybrid-eval.md before any grid run.
    points: [{"floor", "max_per_doc", "summary"}]; reference: the fts reference run's summary."""
    ref_gap, ref_all = _acc((reference or {}).get("refusal_gap")), _acc((reference or {}).get("refusal_all"))
    default = MODE_DEFAULTS.get(mode)
    eligible, why_not = [], {}
    for p in points:
        s, reasons = p["summary"], []
        if s.get("forbidden_hits"):
            reasons.append(f"forbidden hits {s['forbidden_hits']}")
        if ref_gap is not None and (_acc(s.get("refusal_gap")) or 0) < ref_gap:
            reasons.append(f"refusal gap {s['refusal_gap']['ok']}/{s['refusal_gap']['of']} < fts")
        if ref_all is not None and (_acc(s.get("refusal_all")) or 0) < ref_all:
            reasons.append(f"refusal all {s['refusal_all']['ok']}/{s['refusal_all']['of']} < fts")
        if reasons:
            why_not[point_name(p["floor"], p["max_per_doc"])] = reasons
        else:
            eligible.append(p)
    if not eligible:
        return {"pick": None, "reason": "no eligible point: defaults stay; the mode fails the refusal acceptance",
                "not_eligible": why_not}

    def key(p):
        s = p["summary"]
        return (round(s.get("tier1_passage_recall") or 0.0, 3), round(s.get("tier1_doc_recall") or 0.0, 3),
                s.get("pass", 0), (p["floor"], p["max_per_doc"]) == default, p["floor"], -p["max_per_doc"])
    ranked = sorted(eligible, key=key, reverse=True)
    best = ranked[0]
    reason = (f"eligible {len(eligible)} of {len(points)}; best tier-1 passage recall "
              f"{best['summary'].get('tier1_passage_recall')}")
    if len(ranked) > 1:
        names = ("passage recall", "doc recall", "PASS", "default", "higher FLOOR", "smaller MAX_PER_DOC")
        k0, k1 = key(best), key(ranked[1])
        decided = next((n for n, a, b in zip(names, k0, k1) if a != b), "identical keys (first in grid order)")
        reason += f"; beats the runner-up {point_name(ranked[1]['floor'], ranked[1]['max_per_doc'])} on {decided}"
    return {"pick": {"floor": best["floor"], "max_per_doc": best["max_per_doc"], "run": best.get("run")},
            "reason": reason, "not_eligible": why_not}


def write_grid(out_dir: Path, mode: str, grid: list[dict], reference: dict | None, baseline: str | None) -> dict:
    choice = choose(grid, reference, mode)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "grid.json").write_text(json.dumps({"mode": mode, "rule": SELECTION_RULE, "reference": baseline,
                                                   "reference_summary": reference, "choice": choice,
                                                   "points": grid}, indent=2), encoding="utf-8")
    lines = [f"# Grid {mode}", "", f"Reference (fts): `{baseline}`", "", f"Selection rule: {SELECTION_RULE}", "",
             "| FLOOR | MAX_PER_DOC | PASS | tier-1 docs | passages | refusal gap | refusal all | forbidden "
             "| dup pairs > 0.9 (trigram / 5-gram) | median s | p90 s | run |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in grid:
        s = p["summary"]
        lines.append(f"| {p['floor']} | {p['max_per_doc']} | {s.get('pass')} | {s['tier1_doc_recall']} | "
                     f"{s['tier1_passage_recall']} | {_frac(s['refusal_gap']['ok'], s['refusal_gap']['of'])} | "
                     f"{_frac(s['refusal_all']['ok'], s['refusal_all']['of'])} | {s.get('forbidden_hits')} | "
                     f"{s.get('dup_pairs_trigram_over')} / {s.get('dup_pairs_5gram_over')} | {s['median_search_s']} | "
                     f"{s.get('p90_search_s')} | {p['run']} |")
    pick = choice["pick"]
    lines += ["", f"**Pick**: " + (f"FLOOR {pick['floor']}, MAX_PER_DOC {pick['max_per_doc']} (`{pick['run']}`)"
                                    if pick else "none"), "", f"Reason: {choice['reason']}"]
    for name, reasons in choice["not_eligible"].items():
        lines.append(f"- not eligible {name}: {'; '.join(reasons)}")
    (out_dir / "grid.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"grid: pick {pick} ({choice['reason']}) -> {out_dir / 'grid.md'}")
    return choice


def cpu_text() -> str:
    ort = sys.modules.get("onnxruntime")
    return (f"{platform.processor() or platform.machine()}, {os.cpu_count()} logical CPUs, {platform.system()}"
            + (f", onnxruntime {ort.__version__}" if ort is not None and hasattr(ort, "__version__") else ""))


def run_bank(args, bank, keys, corpus, subs, base, real, retrieval_mode, search, resolve, run_id, snapshot,
             warmup_s, doc_dates, plan_question, rules_plan, planner_version) -> tuple[list[dict], dict]:
    from cee.config import settings
    from cee.retrieve import fts
    from cee.retrieve.fts import PoolTrace, budget, budget_tokens
    records = []
    for q in bank:
        query = resolve(q["text"], today=args.as_of)  # retrieval and scoring share one window end
        # #213: without --k, search() takes the app's rule (passages, or tokens with TOKEN_BUDGET);
        # an explicit k is the passage rule. budget() includes the peers' slots (#205).
        # On exp/hybrid only fts takes the token budget; the hybrid modes keep the passage budget.
        b_tokens = budget_tokens(query) if args.k is None and retrieval_mode == "fts" else None
        k = args.k if args.k is not None else (budget(query) if b_tokens is None else None)
        trace = PoolTrace()  # #210: the candidate pools before select(), recording only
        # #214 (ADR-020): token mode without --k searches the question's plan (the rule plan on mock,
        # one planner call with --real); passage mode is one whole-question search, no planner.
        # On exp/hybrid b_tokens is None in the hybrid modes, so they never plan (cee.retrieve.modes).
        plan, pools, capped = None, {}, False
        if args.k is None and b_tokens is not None:
            plan = real.plan(q, query) if real else plan_question(query, "mock")
            if plan is None:   # the planner call would pass --max-calls: rule plan, no answer call
                plan, capped = rules_plan(query), True
        t0 = time.perf_counter()
        # k None: the app's rule (#213); fts with a plan = planner.search_parts, as on main
        hits = search(query, k=args.k, mode=retrieval_mode, trace=trace, plan=plan, part_pools=pools)
        search_s = round(time.perf_counter() - t0, 3)
        r = evaluate(q, query, hits, corpus, subs, args.min_coverage, key_for(q, keys), args.as_of, doc_dates,
                     trace.ids())
        r |= prompt_size(k, hits, b_tokens, trace.peers)
        r |= {"search_s": search_s, "unattached": list(trace.unattached)}
        research = [h for h in hits if h.part_id == "research"]
        r |= {"plan": plan.to_log() if plan else None, "parts": len(plan.parts) if plan else 1,
              "research_passages": len(research), "research_tokens": round(sum(len(h.text) for h in research) / 4),
              "llm_calls": {"planner": plan.calls if plan else 0, "answer": 0}}
        part_stages(r["recall"], hits, {**pools, "research": set(trace.research), "peers": set(trace.peers)})
        if real:
            # exp/hybrid: the hybrid modes answer with the one-part whole-question plan, as the app does
            # (cee.ask -> modes.plan_for; no planner call); fts keeps main's rule (plan or none)
            if retrieval_mode != "fts" and plan is None:
                from cee.retrieve.modes import plan_for
                plan = plan_for(query, mode=retrieval_mode)
            answer, how = (None, "cap") if capped else real.answer(q, query, hits, plan)
            r = apply_real(r, answer, how, real.last_file if not capped else None)
            if answer is not None and plan is not None:   # #215: how each part was covered
                from cee.answer.schema import Answer
                from cee.answer.validate import part_coverage
                r["part_coverage"] = part_coverage(Answer(**answer), plan, hits)
            r["llm_calls"]["answer"] = int(how in ("called", "cached", "invalid"))
            r["stop_reason"], r["output_tokens"] = real.last_stop if not capped else (None, None)   # #230
        if args.baseline:
            r["change"] = compare(r, base.get(q["id"]))
        records.append(r)
        print(f"{q['id']:>4} {r['status']:<13} coverage {r['coverage']} forbidden {len(r['forbidden'])}"
              + (f" recall {r['doc_recall']} refusal {_refusal(r)}" if r["recall"] else "")
              + (f" recall@pool {r['recall_pool']} recall@final {r['recall_final']}"
                 if r["recall_pool"] is not None else "")
              + f" passages {r['passages']} tokens~{r['tokens_est']} parts {r['parts']}"
              + (f" change {r['change']}" if args.baseline else "") + (f" model {r['model']}" if real else ""))

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    meta = {"run_id": run_id, "snapshot": snapshot, "commit": commit,
            "k": "by question" if args.k is None else args.k, "min_coverage": args.min_coverage,
            "pool_per_group": fts.POOL_PER_GROUP, "token_budget": fts.TOKEN_BUDGET if args.k is None and retrieval_mode == "fts" else None,
            "planner": settings().planner, "max_parts": settings().planner_max_parts,
            "planner_version": planner_version,
            "mode": "real" if real else "mock", "retrieval_mode": retrieval_mode, "warmup_s": warmup_s,
            "baseline": args.baseline, "as_of": args.as_of.isoformat(), "cpu": cpu_text(),
            "real_calls": real.calls if real else 0, "reused": real.reused if real else 0, "max_calls": args.max_calls}
    return records, meta


if __name__ == "__main__":
    sys.exit(main())
