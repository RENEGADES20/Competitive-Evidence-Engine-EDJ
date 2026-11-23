"""Run the question bank against the loaded snapshot and write a per-question report (#43).

Default is mock: retrieval only, no model call, free. For each question it records the resolved
entities, the retrieved chunk IDs, which `expected_sources` patterns were hit, forbidden hits
(another firm's chunks; BAC chunks outside GWIM for Merrill questions) and a status.

  python scripts/eval_run.py                          # all 30, mock
  python scripts/eval_run.py --questions Q1,Q4 --k 20   # fixed k (default: the app's budget by question)
  python scripts/eval_run.py --baseline .eval-runs/<run>/report.json
  python scripts/eval_run.py --real --max-calls 5 --questions Q28,Q29,Q30

--real calls the configured provider (LLM_PROVIDER: anthropic, openai or deepseek), at most --max-calls times, and saves every
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

Cache, cost and plan reuse (#248): every call of the flow (plan, map per firm, re-extraction, reduce;
the legacy answer) has its own cache key and file; a resumed run reuses every saved call and never pays
twice. Each question's `cost` in report.json: calls by type, new and reused, tokens (with the
provider's cache-hit tokens), `usd` (every call the answer used, reused ones at what they cost when
made), `usd_new` (spent in this run), `usd_peak` and peak / off-peak calls, priced with
config/pricing.yaml (cee.answer.cost); `summary.cost` and `meta.cost` hold the run totals. Records
written before #248 have a naive `at` (written in America/Chicago): a real run over a cache holding
them needs `--naive-tz America/Chicago` when the provider has a peak window (deepseek).
  python scripts/eval_run.py --real --max-calls 0 --naive-tz America/Chicago --cache <folder>   # replay
  python scripts/eval_run.py --reuse-plans deepseek:deepseek-v4-pro      # plans only from saved records

Recall by stage (#210): search() fills a PoolTrace with the chunk ids of every candidate pool
before select(); recall@pool = expected passages with a chunk in a pool, recall@final = in the
retrieved set. Each expected row is `final`, `pool` (lost in select) or `none` (never a candidate).
Estimated tokens = characters / 4.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from cee.config import entities_config  # noqa: E402
from cee.retrieve.fts import theme_gaps  # noqa: E402

RUNS = REPO / ".eval-runs"
CACHE = RUNS / "cache"
QUESTIONS = REPO / "evals" / "questions.yaml"
KEYS = REPO / "evals" / "expected_chunks.yaml"
STATUSES = ("PASS", "FAIL", "NOT_EVALUATED", "INVALID_OUTPUT")
GAP_BEHAVIORS = ("gap_with_adjacent", "refuse")


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
    return {"tier1_doc_recall": mean([r["doc_recall"] for r in with_key]),
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
            "refusal_all": accuracy(keyed),
            "cost": run_cost(records)}


def run_cost(records: list[dict]) -> dict:
    """#248: the run's totals over every question's cost rows (no rows in a mock run: 0)."""
    from cee.answer.cost import summarize
    return summarize([row for r in records for row in (r.get("cost") or {}).get("rows") or []])


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
            "patterns": rows, "available_patterns": len(avail), "hit_patterns": len(hit),
            "coverage": coverage, "forbidden": bad,
            "doc_recall": recall["doc_recall"] if recall else None,
            "passage_recall": recall["passage_recall"] if recall else None,
            "recall_pool": recall["recall_pool"] if recall else None,
            "recall_final": recall["recall_final"] if recall else None,
            "pool_size": len(set(pool_ids or ()) | {h.chunk_id for h in hits}) if pool_ids is not None else None,
            "refusal_ok": recall["refusal_ok"] if recall else None,
            "misleading": recall["misleading"] if recall else [], "recall": recall, "status": status}


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
              max_tokens: int = 8000, plan_parts: list | None = None, window=None,
              request: str | None = None) -> str:
    """max_tokens (#213) joins the key only when it is not 8000: outputs saved so far keep their
    key, and a run with another output cap never reuses one made under 8000. The window (#230)
    joins it only when the question has one (the v4.1 user message names it; --as-of moves it).
    The request version (#232, llm.request_version: "strict-1" for anthropic) joins it only when
    given, so a strict Anthropic request never reuses a non-strict output; other keys unchanged."""
    parts = [q["id"], q["text"], prompt_version, snapshot, provider, model, chunk_ids]
    if max_tokens != 8000:
        parts = [*parts, {"max_tokens": max_tokens}]
    if plan_parts is not None:   # #215: the v4 user message lists the plan's parts
        parts = [*parts, {"parts": plan_parts}]
    if window:
        parts = [*parts, {"window": [str(window[0]), str(window[1])]}]
    if request:
        parts = [*parts, {"request": request}]

    blob = json.dumps(parts)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def now_iso() -> str:
    """#248: record times carry this machine's UTC offset, so pricing by period needs no assumed zone."""
    return dt.datetime.now().astimezone().isoformat()


def stage_version(provider: str, stage: str) -> str | None:
    """#272: the request version of one W11 stage (plan, map, reduce): deepseek's names that stage's effort,
    cap and streaming; anthropic / openai have one version for every call."""
    from cee.answer import llm
    return llm.request_version(provider, stage) if provider == "deepseek" else llm.request_version(provider)


def idle_fields(e: BaseException) -> dict:
    """#275: a stalled stream (llm.StreamIdle) is saved as a failed call with its partial output, whether any output
    arrived, and the time to it; never re-called, never retried automatically."""
    from cee.answer import llm
    if not isinstance(e, llm.StreamIdle):
        return {}
    return {"idle_timeout": True, "idle_s": e.idle_s, "output_seen": e.output_seen, "ttft_s": e.ttft_s,
            "partial": e.partial}


def timing(t0: float, usage: dict | None) -> dict:
    """#242: wall time of one paid call and its output tokens per second (None when unknown)."""
    wall = round(time.monotonic() - t0, 2)
    out = (usage or {}).get("output_tokens")
    out_t = {"wall_s": wall, "tokens_per_s": round(out / wall, 2) if out and wall > 0 else None}
    if usage and usage.get("ttft_s") is not None:   # #272: streamed calls, time to first token
        out_t["ttft_s"] = usage["ttft_s"]
    return out_t


def parts_of(plan) -> list | None:
    """The plan's parts as the answer cache key sees them (#215): [[id, text, firms], ...]."""
    return None if plan is None else [[p.id, p.text, list(p.firms)] for p in plan.parts]


def plan_cache_key(q: dict, snapshot: str, provider: str, model: str, query: dict,
                   request: str | None = None) -> str:
    """Planner outputs (#214) are cached apart from answers: question, planner version, snapshot,
    provider, model, the planner's output cap, the registered metric keys (the schema's enum, #245)
    and the resolved query; the request version (#232) only when given. No part cap since plan-v3."""
    from cee.retrieve.planner import PLANNER_MAX_TOKENS, PLANNER_VERSION, metric_keys
    # PLANNER_MAX_TOKENS is the anthropic / openai cap; the DeepSeek planner cap (by thinking mode,
    # #242) is kept apart through the request version (llm.request_version).
    # #247 part 2: the retrieval-only Query fields (period_range, exclude_ids) join the key only when
    # set, so plans saved before them keep their key (they are never set on the question's own query)
    query = {k: v for k, v in query.items() if not (k in ("period_range", "exclude_ids") and not v)}
    parts = [q["id"], q["text"], PLANNER_VERSION, snapshot, provider, model, PLANNER_MAX_TOKENS,
             list(metric_keys()), query]
    if request:
        parts = [*parts, {"request": request}]
    return hashlib.sha256(json.dumps(parts, default=str, sort_keys=True).encode()).hexdigest()[:24]


def plans_wanted(query, k: int | None = None) -> bool:
    """True when a run plans this question with a planner call (#214): planner on, the question is
    searched, token mode and no explicit k. False: plan_question's rule plan, no call, no file."""
    from cee.config import settings
    from cee.retrieve import fts
    return k is None and settings().planner and fts.searchable(query) and fts.budget_tokens(query) is not None


def plan_path(cache_dir: Path, q: dict, query, snapshot: str, provider: str, model: str,
              request: str | None) -> Path:
    """Where a question's planner output is saved (#214); one function for RealRunner.plan and
    --reuse-plans (#240, #248), so both read the same file. The retrieval mode is not part of it."""
    from dataclasses import asdict
    key = plan_cache_key(q, snapshot, provider, model, asdict(query), request)
    return cache_dir / f"{q['id']}-plan-{key}.json"


class PlanMissing(RuntimeError):
    """--reuse-plans: a question's saved planner output is not in the cache (#240)."""


def missing_plans(bank: list[dict], resolve, as_of, snapshot: str, provider: str, model: str,
                  request: str | None, k: int | None = None, cache_dir: Path | None = None) -> list[str]:
    """Question IDs whose saved plan --reuse-plans would need but cannot find (0 calls)."""
    cache_dir = cache_dir or CACHE
    out = []
    for q in bank:
        query = resolve(q["text"], today=as_of)
        if plans_wanted(query, k) and not plan_path(cache_dir, q, query, snapshot, provider, model,
                                                    request).is_file():
            out.append(q["id"])
    return out


def plan_from_record(saved: dict, query, provider: str):
    """(Plan, parse flags, origin note) of a saved planner record: valid, invalid (re-parsed when only
    stray closing braces broke it, #246) or a failed call (the rule plan with its error)."""
    from cee.retrieve import planner
    if saved.get("invalid"):
        payload = saved.get("raw_payload")
        if isinstance(payload, str) and str(saved.get("error", "")).startswith(
                ("planner arguments are not a JSON object", "planner output is not JSON")):
            from cee.answer.llm import loads_object
            flags: list = []
            try:   # #246 TL decision: stray closing braces after a complete object (0 calls)
                plan = planner.from_output(query, loads_object(payload, flags), provider)
                flags = [*flags, "rechecked"]   # #247 (PR #256 review note 2)
                return plan, flags, f"; re-parsed, flags {', '.join(flags)}"
            except (TypeError, ValueError):
                pass
        return planner.from_output(query, payload, provider, error=saved["error"]), [], ""
    return planner.from_output(query, saved["raw"], provider), list(saved.get("parse_flags") or []), ""


class SavedPlans:
    """--reuse-plans in a mock run (#240, #248): each plan from the planner output a real run with this
    provider / model / request version saved; the planner is never called (no client is built)."""

    def __init__(self, provider: str, model: str, snapshot: str, cache_dir: Path | None = None,
                 request: str | None = None):
        self.provider, self.model, self.snapshot, self.cache_dir = provider, model, snapshot, cache_dir or CACHE
        # #272: the planner stage's version, or the one named in --reuse-plans PROVIDER:MODEL@VERSION
        self.request_version = request or stage_version(provider, "plan")

    def plan(self, q: dict, query):
        from cee.retrieve import planner
        if not plans_wanted(query):
            return planner.plan_question(query, "mock")
        path = plan_path(self.cache_dir, q, query, self.snapshot, self.provider, self.model, self.request_version)
        if not path.is_file():
            raise PlanMissing(f"{q['id']}: no saved plan {path.name}")
        plan, _, _ = plan_from_record(json.loads(path.read_text(encoding="utf-8")), query, self.provider)
        plan.calls = 0   # read from a file in a mock run: no call was made here
        return plan


def call_type(name: str) -> str:
    """plan | map | remap | reduce | answer, from a cache file name (#248)."""
    if "-plan-" in name:
        return "plan"
    if "-reduce-" in name:
        return "reduce"
    if "-remap." in name:
        return "remap"
    if "-map." in name:
        return "map"
    return "answer"


def naive_records(cache_dir: Path) -> list[str]:
    """Cache files whose `at` has no UTC offset (every record written before #248)."""
    from cee.answer.cost import is_naive
    out = []
    for f in sorted(cache_dir.glob("*.json")) if cache_dir.is_dir() else []:
        try:
            if is_naive(json.loads(f.read_text(encoding="utf-8")).get("at")):
                out.append(f.name)
        except (ValueError, OSError):
            continue
    return out


def price_rows(ledger: list[dict], naive_tz: str | None) -> list[dict]:
    """Ledger entries -> cost rows {type, file, new, cost} (cee.answer.cost; a price that cannot be
    computed is status `error` with the reason, never a guess)."""
    from cee.answer import cost as C
    rows = []
    for e in ledger:
        try:
            c = C.price_call(e["provider"], e["model"], e["usage"], at=e["at"], wall_s=e["wall_s"],
                             finished_at=e.get("finished_at"), naive_tz=naive_tz)
        except C.CostError as err:
            c = {**C.price_call(e["provider"], e["model"], None), "status": "error", "error": str(err)}
        rows.append({"type": e["type"], "file": e["file"], "new": e["new"], "cost": c})
    return rows


def question_cost(rows: list[dict]) -> dict:
    from cee.answer.cost import summarize
    return {**summarize(rows), "rows": rows}


def map_cache_key(q: dict, snapshot: str, provider: str, model: str, max_tokens: int,
                  request: str | None, spec, window=None) -> str:
    """#246: one extraction call: question, extract version, snapshot, provider, model, the map cap,
    the request version (thinking mode), the call id, its cells (id, text, kind, metric, proxy), the
    input chunk ids in order and the window; #283: a shared-prefix call adds its firm block (cells, chunk ids)."""
    from cee.answer.extract import extract_version
    cells = [[c.id, c.text, c.aspect.kind, c.aspect.metric, bool(getattr(c.aspect, "proxy", False))]
             for c in spec.cells]
    parts = [q["id"], q["text"], extract_version(), snapshot, provider, model, max_tokens, request, spec.id,
             cells, [h.chunk_id for h in spec.hits], [str(w) for w in window] if window else None]
    prefix = getattr(spec, "prefix", None)
    if prefix is not None:   # #283: the shared firm block (its sub-questions and passages) is part of the request
        parts.append([[c.id, c.text] for c in prefix.cells] + [h.chunk_id for h in prefix.hits])
    return hashlib.sha256(json.dumps(parts, default=str).encode()).hexdigest()[:24]


def reduce_cache_key(q: dict, snapshot: str, provider: str, model: str, max_tokens: int,
                     request: str | None, matrix, query) -> str:
    """#247: one reduce call: question, reduce version, snapshot, provider, model, the cap, the request
    version (thinking mode), a sha256 of the v5 system prompt (a wording edit never reuses an output,
    review note 6), of the rendered user message (behavior, window, every cell, mark, gap and source)
    and of the schema (its enums)."""
    from cee.answer import prompt as P
    from cee.answer import reduce as R

    def sha(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    schema, _ = R.reduce_schema(matrix)
    # #275: the prompt version and system text in use (REDUCE_PROMPT); v5.2 gives the #272 keys unchanged
    parts = [q["id"], q["text"], R.prompt_version(), snapshot, provider, model, max_tokens, request,
             sha(R.system_prompt()), sha(R.reduce_message(q["text"], matrix, query)),
             sha(json.dumps(schema, sort_keys=True))]
    return hashlib.sha256(json.dumps(parts, default=str).encode()).hexdigest()[:24]


def reduce_version() -> str:
    from cee.answer.reduce import prompt_version
    return prompt_version()


def extract_version() -> str:
    from cee.answer.extract import extract_version as v
    return v()


def effective_behaviors() -> dict[str, str]:
    """evals/behavior_supersede.yaml (ADR-021 rule 8): informational here; the scorer is #248's."""
    path = REPO / "evals" / "behavior_supersede.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {e["id"]: e["expected_behavior"] for e in data.get("supersedes") or []}


def map_must_not(matrix, key: dict | None) -> list[dict]:
    """#246: every must_not_return chunk the matrix cites (items, and the inputs behind an accepted
    derivation), with its cell and label; as_fact = cited for a cell that holds the asked quantity."""
    bad = set((key or {}).get("must_not_return") or [])
    if matrix is None or not bad:
        return []
    from cee.answer.matrix import holds
    out = []
    for c in matrix.cells.values():
        for i in c.items:
            for cid in i.chunk_ids:
                if cid in bad:
                    out.append({"chunk_id": cid, "cell": c.id, "label": c.effective_label,
                                "as_fact": c.effective_label == "fact", "via": "item"})
        d = c.derivation or {}
        if d.get("ok"):
            for cid in d.get("input_chunk_ids") or []:
                if cid in bad:
                    out.append({"chunk_id": cid, "cell": c.id, "label": c.label, "as_fact": holds(c),
                                "via": "derivation input"})
    return out


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
            raise SystemExit("--real needs LLM_PROVIDER=anthropic, openai or deepseek; it is mock.")
        self.provider, self.max_calls, self.snapshot = provider, max_calls, snapshot
        self.model, self.prompt_version = model_name(provider), PROMPT_VERSION
        self.max_tokens = llm.answer_max_tokens(provider)   # #242: deepseek by thinking mode
        self.request_version = llm.request_version(provider)   # #232: "strict-1" for anthropic
        # #272: each W11 stage's own request version and the map's model (DEEPSEEK_MODEL_MAP)
        self.plan_version = stage_version(provider, "plan")
        self.map_version = stage_version(provider, "map")
        self.reduce_version = stage_version(provider, "reduce")
        from cee.retrieve.planner import model_for
        self.map_model = model_for(provider, "map") if provider == "deepseek" else self.model
        self.calls, self.reused, self.last_file = 0, 0, None
        self.last_stop: tuple[str | None, int | None] = (None, None)   # stop_reason, output tokens (#230)
        self.cache_dir, self.raw_dir = cache_dir, run_dir / "raw"
        # #246: `calls` counts reservations (the --max-calls cap, exact under parallel map calls);
        # `made` counts calls actually sent (a reservation cancelled after a ProviderStop is not made)
        import threading
        self.made, self.lock = 0, threading.Lock()
        self.map_max_tokens = None
        self.last_plan_origin: str | None = None
        self.map_capped: list[str] = []
        self.map_stopped: list[str] = []
        self.bad_request: str | None = None
        self.last_plan_flags: list[str] = []
        # #248: one entry per call served (new or reused from the cache), for the cost per question
        self.ledger: list[dict] = []
        # #240 / #248 --reuse-plans: plans only from the cache, never a planner call (an attribute, not a
        # constructor argument, so tests that patch __init__'s defaults keep working)
        self.plans_only = False

    def answer(self, q: dict, query, hits, plan=None) -> tuple[dict | None, str]:
        """The legacy single answer call (prompt v4.1, `--legacy`, MAP off).
        (answer dict or None, how): how = no_call | cached | called | cap | invalid.
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
                        [h.chunk_id for h in hits], self.max_tokens, parts_of(plan), answer_window(query),
                        self.request_version)
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
        self.made += 1
        meta = {"question_id": q["id"], "question": q["text"], "prompt_version": self.prompt_version,
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model,
                "max_tokens": self.max_tokens, "request_version": self.request_version,
                "chunk_ids": [h.chunk_id for h in hits], "at": now_iso()}
        from cee.answer.llm import ProviderStop

        t0 = time.monotonic()
        try:
            answer, raw = answer_for(q["text"], query, hits, self.provider, plan=plan)
        except ProviderStop as e:   # #242: refused before any output: nothing to save, the run stops
            raise SystemExit(f"stopped: {e}") from e
        except ModelOutputError as e:   # paid output that is not a valid Answer: keep it (#187)
            usage = getattr(e, "usage", None) or {}
            self.last_stop = (getattr(e, "stop_reason", None), usage.get("output_tokens"))
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                              "stop_reason": getattr(e, "stop_reason", None), "usage": usage,
                              **timing(t0, usage)})
            return None, "invalid"
        # Any other error (timeout, 400 / 500 / 503) propagates: nothing saved, the call counted.
        self.last_stop = (raw.stop_reason or None, raw.usage.get("output_tokens"))
        extra = {}
        payload = getattr(raw, "_provider_payload", None)
        if payload:   # #242: DeepSeek's reasoning, kept in the record only (never in the Answer dump)
            extra["reasoning_content"] = payload.get("reasoning_content")
        self._save(path, {**meta, "stop_reason": raw.stop_reason, "usage": raw.usage, **timing(t0, raw.usage),
                          **extra, "raw": raw.model_dump()})
        return answer.model_dump(), "called"

    def reduce(self, q: dict, query, plan, hits, matrix) -> tuple[dict | None, str, dict]:
        """#247: the reduce call, cached like a map call and never re-called (valid, invalid or failed).
        (answer dict or None, how, info): how = no_call | code_built | cached | called | cap | invalid |
        failed | stopped. `hits` = retrieval + corrective re-search hits (B1). A 400 sets bad_request
        (the run stops after this question, every record saved)."""
        from cee.answer import llm
        from cee.answer import reduce as R
        from cee.ask import answer_for

        self.last_file, self.last_stop = None, (None, None)
        info: dict = {}
        if not hits:
            answer, _ = answer_for(q["text"], query, hits, self.provider)
            return answer.model_dump(), "no_call", info
        if not R.needs_call(matrix):
            answer, _ = answer_for(q["text"], query, hits, self.provider, plan=plan, matrix=matrix, info=info)
            return answer.model_dump(), "code_built", info
        key = reduce_cache_key(q, self.snapshot, self.provider, self.model, R.max_tokens(self.provider),
                               self.reduce_version, matrix, query)
        path = self.cache_dir / f"{q['id']}-reduce-{key}.json"
        self.last_file = path.name
        # #275: the reduce record's file and a sha of its rendered message, in the report even when the call is
        # capped (count phase), so a reduce-only re-run can show which reduce keys are new and why
        info["file"] = path.name
        info["message_sha"] = hashlib.sha256(R.reduce_message(q["text"], matrix, query).encode()).hexdigest()[:16]

        def finish(raw_answer):
            answer, _ = answer_for(q["text"], query, hits, self.provider, raw=raw_answer, plan=plan,
                                   matrix=matrix, info=info)
            info.update(stop_reason=raw_answer.stop_reason, usage=raw_answer.usage)
            return answer.model_dump()

        if path.is_file():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.reused += 1
            self._copy(path)
            self.last_stop = (saved.get("stop_reason"), (saved.get("usage") or {}).get("output_tokens"))
            if saved.get("failed_call"):
                return None, "failed", {"error": saved.get("error")}
            meta = {"stop_reason": saved.get("stop_reason"), "usage": saved.get("usage"),
                    "parse_flags": saved.get("parse_flags")}
            raw = saved.get("raw")
            if saved.get("invalid"):
                payload = saved.get("raw_payload")
                if not (isinstance(payload, str) and str(saved.get("error", "")).startswith(R.ARGUMENT_ERRORS)):
                    return None, "invalid", {"error": saved.get("error")}
                flags: list = []
                try:   # the #246 rule: stray closing braces after a complete object (0 calls)
                    raw = llm.loads_object(payload, flags)
                except (TypeError, ValueError):
                    return None, "invalid", {"error": saved.get("error")}
                meta["parse_flags"] = [*flags, "rechecked"]
            try:
                return finish(R.to_answer(raw, self.provider, meta, matrix)), "cached", info
            except llm.ModelOutputError as e:
                return None, "invalid", {"error": str(e)}
        if self.bad_request:
            return None, "stopped", {"error": "not run: the run stopped after a 400"}
        if self.calls >= self.max_calls:
            return None, "cap", info
        self.calls += 1   # reserved and counted before the call: a failed call still cost money
        self.made += 1
        schema, fallback = R.reduce_schema(matrix)
        meta = {"question_id": q["id"], "question": q["text"], "reduce_version": R.prompt_version(),
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model,
                "max_tokens": R.max_tokens(self.provider), "request_version": self.reduce_version,
                "behavior": matrix.behavior, "chunk_ids": R.citable(matrix), "schema_fallback": fallback,
                "enum_values": R.enum_values(schema), "at": now_iso()}
        got: dict = {}
        t0 = time.monotonic()
        early = R.EarlyClaims(matrix, query)   # #275: what the Ask page would show before the final answer
        try:
            out = R.call_reduce(q["text"], matrix, query, self.provider, meta=got, on_item=early)
        except llm.ProviderStop as e:   # refused before any output: nothing to save, the run stops
            raise SystemExit(f"stopped: {e}") from e
        except llm.ModelOutputError as e:   # paid output that is not a valid Answer: keep it (#187)
            usage = e.usage or got.get("usage") or {}
            self.last_stop = (e.stop_reason, usage.get("output_tokens"))
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                              "stop_reason": e.stop_reason, "usage": usage, **timing(t0, usage),
                              **self._reasoning(got)})
            return None, "invalid", {"error": str(e)}
        except Exception as e:   # timeout, 5xx, connection, a 400: counted, saved, never re-called
            err = f"{type(e).__name__}: {e}"
            bad = getattr(e, "status_code", None) == 400
            self._save(path, {**meta, "invalid": True, "failed_call": True, "error": err, "raw_payload": None,
                              "bad_request": bad, **timing(t0, None), **idle_fields(e),
                              "stream_items": early.stats()})
            if bad:
                self.bad_request = err
            return None, "failed", {"error": err}
        flags = list(got.get("parse_flags") or [])
        self.last_stop = (got.get("stop_reason"), (got.get("usage") or {}).get("output_tokens"))
        stream = early.stats()
        self._save(path, {**meta, "stop_reason": got.get("stop_reason"), "usage": got.get("usage"),
                          **timing(t0, got.get("usage")), **self._reasoning(got),
                          **({"parse_flags": flags} if flags else {}), "first_claim_s": stream["first_claim_s"],
                          "stream_items": stream, "raw": out})
        answer = finish(R.to_answer(out, self.provider, got, matrix))
        final = {c.get("text") for c in answer.get("claims") or []}
        info["stream_items"] = {**stream, "shown_not_final": sum(c.text not in final for c in early.shown)}
        return answer, "called", info
    def plan(self, q: dict, query):
        """The question's plan (#214, ADR-020) from one planner call, cached like an answer: a saved
        plan (valid, invalid or a failed call) is always reused, so a re-run never calls the planner
        again. None when the call would pass --max-calls. No call when the planner is off, the
        question is not searched, or passage mode (planner.plan_question decides)."""
        from dataclasses import asdict

        from cee.config import settings
        from cee.retrieve import fts, planner

        self.last_plan_origin, self.last_plan_flags = None, []
        if not settings().planner or not fts.searchable(query) or fts.budget_tokens(query) is None:
            self.last_plan_origin = "no planner call (rules or passage plan)"
            return planner.plan_question(query, self.provider)
        path = plan_path(self.cache_dir, q, query, self.snapshot, self.provider, self.model, self.plan_version)
        if path.is_file():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.reused += 1
            self._copy(path)
            # #246: where the plan came from, in every record
            self.last_plan_origin = (f"cached: {path.name} ({saved.get('planner_version')}, request_version "
                                     f"{saved.get('request_version')}, made {saved.get('at')}); no new planner call")
            plan, self.last_plan_flags, note = plan_from_record(saved, query, self.provider)
            self.last_plan_origin += note
            return plan
        if self.plans_only:   # #240 / #248 --reuse-plans: never a planner call
            raise PlanMissing(f"{q['id']}: no saved plan {path.name} (--reuse-plans); no call made")
        if self.calls >= self.max_calls:
            return None
        self.calls += 1   # counted before the call: a failed call still cost money
        self.made += 1
        self.last_plan_origin = (f"new planner call: {path.name} ({planner.PLANNER_VERSION}, request_version "
                                 f"{self.plan_version})")
        meta = {"question_id": q["id"], "question": q["text"], "planner_version": planner.PLANNER_VERSION,
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model,
                "max_tokens": planner.planner_max_tokens(self.provider), "request_version": self.plan_version,
                "query": asdict(query),
                "at": now_iso()}
        from cee.answer.llm import ProviderStop

        call: dict = {}   # #230: stop_reason and usage of the call, saved with every plan record
        t0 = time.monotonic()
        try:
            raw = planner.call_planner(query, self.provider, meta=call)
        except ProviderStop as e:   # #242: refused before any output: nothing to save, the run stops
            raise SystemExit(f"stopped: {e}") from e
        except planner.PlannerOutputError as e:
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                              "stop_reason": e.stop_reason, "usage": call.get("usage"),
                              **timing(t0, call.get("usage")), **self._reasoning(call)})
            return planner.from_output(query, e.raw, self.provider, error=str(e))
        except Exception as e:   # API / network: the rule plan, the call counted, never re-called
            err = f"{type(e).__name__}: {e}"
            bad_request = getattr(e, "status_code", None) == 400
            self._save(path, {**meta, "invalid": True, "failed_call": True, "error": err, "raw_payload": None,
                              "bad_request": bad_request, **timing(t0, None), **idle_fields(e)})
            if bad_request:   # #245: the provider rejected the request itself (e.g. the schema);
                # every planned call would fail the same way, so the run stops (saved, counted once)
                raise SystemExit(f"stopped: planner request rejected with 400 ({err})") from e
            return planner.from_output(query, None, self.provider, error=err)
        self._save(path, {**meta, "stop_reason": call.get("stop_reason"), "usage": call.get("usage"),
                          **timing(t0, call.get("usage")), **self._reasoning(call),
                          **({"parse_flags": call["parse_flags"]} if call.get("parse_flags") else {}), "raw": raw})
        self.last_plan_flags = list(call.get("parse_flags") or [])
        return planner.from_output(query, raw, self.provider)

    def map(self, q: dict, query, plan, hits, as_of=None):
        """#246: the map step with every extraction call cached and saved (valid, invalid or failed),
        never re-called. Calls are reserved here, in the main thread, before each parallel round, so
        --max-calls is exact; a call over the cap is not made and writes no cache file. A 400 stops
        the run after the round is saved."""
        from cee.answer import extract, llm
        from cee.answer.extract import CallResult

        self.map_capped, self.map_stopped = [], []
        self.map_max_tokens = extract.extract_max_tokens(self.provider)
        window = extract.query_window(query)
        paths: dict[str, Path] = {}

        def path_of(spec) -> Path:
            if spec.id not in paths:
                key = map_cache_key(q, self.snapshot, self.provider, self.map_model, self.map_max_tokens,
                                    self.map_version, spec, window)
                paths[spec.id] = self.cache_dir / f"{q['id']}-{spec.id}-{key}.json"
            return paths[spec.id]

        def allow(spec):   # main thread: True, or the reason the call is not made (#247)
            if self.bad_request:   # PR #256 review note 1: after a 400 no further call (round 2 included)
                self.map_stopped.append(spec.id)
                return "not run: the run stopped after a 400"
            if path_of(spec).is_file():
                return True
            if self.calls >= self.max_calls:
                self.map_capped.append(spec.id)
                return False
            self.calls += 1        # reserved: counted before the call
            return True

        def call(spec, question, win, firms) -> CallResult:
            path = path_of(spec)
            if path.is_file():
                saved = json.loads(path.read_text(encoding="utf-8"))
                with self.lock:
                    self.reused += 1
                self._copy(path)
                if saved.get("invalid"):
                    again = extract.recheck_invalid(saved, self.provider)   # #246 TL: stray closing braces
                    if again is not None:
                        return again
                    return CallResult(invalid=not saved.get("failed_call"), failed_call=bool(saved.get("failed_call")),
                                      error=saved.get("error"), stop_reason=saved.get("stop_reason"),
                                      usage=saved.get("usage"), cached=True)
                try:
                    extract.validate_output(saved["raw"], self.provider)
                except llm.ModelOutputError as e:
                    return CallResult(invalid=True, error=str(e), cached=True)
                return CallResult(raw=saved["raw"], stop_reason=saved.get("stop_reason"), usage=saved.get("usage"),
                                  cached=True, flags=list(saved.get("parse_flags") or []))
            with self.lock:
                self.made += 1
            meta = {"question_id": q["id"], "question": q["text"], "extract_version": extract.extract_version(),
                    "call_id": spec.id, "round": spec.round, "entity": spec.entity, "cells": spec.cell_ids,
                    "snapshot": self.snapshot, "provider": self.provider, "model": self.map_model,
                    "max_tokens": self.map_max_tokens, "request_version": self.map_version,
                    "chunk_ids": [h.chunk_id for h in spec.hits], "at": now_iso(),
                    # #283: prefix_group, prefix_role, gate_wait_s, prefix_chars, request_chars (run_round)
                    **(extract.PREFIX_INFO.get() or {})}
            got: dict = {}
            t0 = time.monotonic()
            try:
                raw = extract.call_extract(question, spec, self.provider, win, firms, meta=got)
            except llm.ProviderStop:
                raise   # refused before any output: nothing to save, the run stops
            except llm.ModelOutputError as e:
                usage = e.usage or got.get("usage") or {}
                self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw,
                                  "stop_reason": e.stop_reason, "usage": usage, **timing(t0, usage),
                                  **self._reasoning(got)})
                return CallResult(invalid=True, error=str(e), stop_reason=e.stop_reason, usage=usage)
            except Exception as e:   # B3: timeout, 5xx, connection, 401 / 429 outside ProviderStop, 400
                err = f"{type(e).__name__}: {e}"
                bad = getattr(e, "status_code", None) == 400
                self._save(path, {**meta, "invalid": True, "failed_call": True, "error": err, "raw_payload": None,
                                  "bad_request": bad, **timing(t0, None), **idle_fields(e)})
                if bad:
                    self.bad_request = err
                return CallResult(failed_call=True, error=err, bad_request=bad)
            flags = list(got.get("parse_flags") or [])
            self._save(path, {**meta, "stop_reason": got.get("stop_reason"), "usage": got.get("usage"),
                              **timing(t0, got.get("usage")), **self._reasoning(got),
                              **({"parse_flags": flags} if flags else {}), "raw": raw})
            return CallResult(raw=raw, stop_reason=got.get("stop_reason"), usage=got.get("usage"), flags=flags)

        try:
            return extract.run_map(query, plan, hits, self.provider, call=call, as_of=as_of, allow=allow)
        except llm.ProviderStop as e:
            raise SystemExit(f"stopped: {e}") from e

    @staticmethod
    def _reasoning(call: dict) -> dict:
        """#242: the planner's reasoning text, when the provider returned one (deepseek)."""
        return {"reasoning_content": call["reasoning_content"]} if "reasoning_content" in call else {}

    def _save(self, path: Path, record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # default=str: an unexpected payload type must never cost the paid output (#187)
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
        self._copy(path, new=True)

    def _copy(self, path: Path, new: bool = False) -> None:
        """Copy a record to the run's raw/ folder and enter it in the ledger (#248): new = made in this
        run, else reused from the cache."""
        text = path.read_text(encoding="utf-8")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / path.name).write_text(text, encoding="utf-8")
        try:
            rec = json.loads(text)
        except ValueError:
            rec = {}
        with self.lock:
            self.ledger.append({"type": call_type(path.name), "file": path.name, "new": new,
                                "provider": rec.get("provider", self.provider), "model": rec.get("model", self.model),
                                "usage": rec.get("usage"), "at": rec.get("at"), "wall_s": rec.get("wall_s"),
                                "finished_at": rec.get("finished_at")})


def apply_real(record: dict, answer: dict | None, how: str, raw_file: str | None = None) -> dict:
    record["model"] = how
    if how == "invalid":   # the retrieval status is kept in the note (#187)
        record["note"] = (f"retrieval {record['status']}; model output invalid, see raw/{raw_file}"
                          if raw_file else f"retrieval {record['status']}; model output invalid")
        record["status"], record["behavior"] = "INVALID_OUTPUT", None
        return record
    if answer is None:
        record["status"], record["behavior"] = "NOT_EVALUATED", None
        record["note"] = {"failed": "reduce call failed (saved, never re-called)",
                          "stopped": "not run: the run stopped after a 400"}.get(how, "not run: --max-calls reached")
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


def _usd(v) -> str:
    return "-" if v is None else f"{v:.3f}"


def cost_line(c: dict | None) -> str:
    """#248: one line of calls, tokens and dollars (report header and each question)."""
    if not c:
        return "**Cost** (#248): 0 calls, $0"
    types = ", ".join(f"{k} {v}" for k, v in c["by_type"].items() if v)
    extra = [f"{c[k]} {k.replace('_calls', '').replace('_', ' ')}" for k in ("unpriced_calls", "no_usage_calls")
             if c.get(k)]
    return (f"**Cost** (#248): {c['calls']} calls ({types or 'none'}; new {c['new']}, reused {c['reused']}); "
            f"tokens in {c['input_tokens']:,} (cache hit {c['cache_hit_tokens']:,}), out {c['output_tokens']:,} "
            f"(reasoning {c['reasoning_tokens']:,}); ${c['usd']:.3f} (new in this run ${c['usd_new']:.3f}, all at "
            f"peak ${c['usd_peak']:.3f}); off-peak {c['off_peak_calls']}, peak {c['peak_calls']}"
            + (f"; {', '.join(extra)}" if extra else "")
            + (f"; naive times read as {c['naive_tz']}" if c.get("naive_tz") else ""))


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
             cost_line(meta.get("cost")), "",
             "Status: FAIL on any forbidden hit or refusal failure; NOT_EVALUATED when no expected source is in the "
             "corpus; PASS when coverage of the available patterns >= min coverage"
             + ("; real mode also needs behavior == expected." if meta["mode"] == "real" else "."), "",
             "Recall: expected documents (passages) from `evals/expected_chunks.yaml` with at least one retrieved "
             "chunk. Refusal: no must-not chunk, no forbidden hit, nothing outside the time window. "
             "Recall@pool: expected passages with a chunk in any candidate pool before select(); recall@final: "
             "in the retrieved set (= Passages). Tokens: characters / 4.", "",
             "| Q | Tier | Use case | Expected | Firms (mode) | k | Hits | Chars | Tokens | Coverage | Recall docs"
             " | Passages (final) | Pool | Refusal | Forbidden | Status" + (" | Change" if meta.get("baseline") else "")
             + (" | Behavior | Cost (USD)" if meta["mode"] == "real" else "") + " |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---" + ("|---" if meta.get("baseline") else "")
             + ("|---|---" if meta["mode"] == "real" else "") + "|"]
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
                     + (f" | {r.get('behavior') or r.get('note', '')} | {_usd((r.get('cost') or {}).get('usd'))}"
                        if meta["mode"] == "real" else "") + " |")
    lines.append(f"| **All** | | | | | | {summary['passages']} | {sum(r.get('chars', 0) for r in records)} | "
                 f"{summary['tokens_est']} | | | {summary['recall_final']} (mean) | {summary['recall_pool']} (mean) | "
                 f"{_frac(ra['ok'], ra['of'])} | {sum(len(r['forbidden']) for r in records)} | "
                 f"PASS {counts['PASS']}" + (" | " if meta.get("baseline") else "")
                 + (f" | | {_usd((meta.get('cost') or {}).get('usd'))}" if meta["mode"] == "real" else "") + " |")
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
        if "map_behavior" in r:   # #246: the evidence matrix
            m = r["matrix"]
            lines.append(f"- Map: behavior by code {r['map_behavior'] or 'undecided'} (effective expected "
                         f"{r.get('expected_behavior_effective')}); {r['map_calls']} map + {r['remap_calls']} "
                         f"re-extraction calls; labels {m['counts']['labels']}; {len(m['research'])} re-searched"
                         + (f"; capped: {', '.join(r['map_capped_calls'])}" if r.get("map_capped_calls") else "")
                         + (f"; parse flags: {r['map_call_flags']}" if r.get("map_call_flags") else ""))
            lines += [f"  - {g}" for g in m["grid"]]
            for hit in r.get("map_must_not") or []:
                lines.append(f"  - must-not `{hit['chunk_id']}` in {hit['cell']} ({hit['label']}, {hit['via']})"
                             + (" **as fact**" if hit["as_fact"] else ""))
        if r.get("reduce"):   # #247: the reduce step
            red, ans = r["reduce"], r.get("answer") or {}
            lines.append(f"- Reduce ({red.get('version')}, {'code-built' if red.get('code_built') else red.get('how')}): "
                         f"behavior {r.get('behavior') or r.get('answer_behavior')} (map {r.get('map_behavior') or 'undecided'}, effective "
                         f"expected {r.get('expected_behavior_effective')}); {len(ans.get('claims') or [])} claims, "
                         f"{len(ans.get('adjacent') or [])} adjacent, {len(ans.get('gaps') or [])} gaps; flags "
                         f"{red.get('flags') or {}}; comparison missing {red.get('comparison_missing') or []}; "
                         f"why-lines missing {red.get('why_line_missing', 0)}; outside matrix "
                         f"{red.get('outside_matrix', 0)}; reordered {red.get('reordered', 0)}; part gaps "
                         f"{red.get('part_gaps', 0)}; code computability {red.get('code_computability') or []}; "
                         f"why-lines removed {red.get('why_line_removed', 0)} / restated "
                         f"{red.get('why_line_restated', 0)}; duplicates removed "
                         f"{len(red.get('duplicates_removed') or [])}; basis breaks {red.get('basis_breaks') or []}")
        if r.get("added_chunk_ids") and any(r["added_chunk_ids"].values()):
            lines.append(f"- Added passages: {r['added_chunk_ids']}")
        if r.get("plan_origin"):
            lines.append(f"- Plan: {r['plan_origin']}")
        if (r.get("cost") or {}).get("calls"):
            lines.append("- " + cost_line(r["cost"]).replace("**Cost** (#248): ", "Cost: "))
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
    ap.add_argument("--plan-only", action="store_true",
                    help="with --real: planner calls only, then the 0-call search of each plan; no answer call (#245)")
    ap.add_argument("--map", action="store_true",
                    help="accepted for #246's commands; since #247 the map and reduce run unless --legacy")
    ap.add_argument("--legacy", action="store_true",
                    help="#247: the legacy single answer call (prompt v4.1), no map and no reduce")
    ap.add_argument("--map-only", action="store_true",
                    help="with --real: plan, search and the map step; no answer call (#246; implies --map)")
    ap.add_argument("--out", help="run folder (default .eval-runs/<snapshot>-<time>)")
    ap.add_argument("--as-of", type=dt.date.fromisoformat, default=dt.date.today(),
                    help="day the time windows end, YYYY-MM-DD (default today)")
    ap.add_argument("--keys", type=Path, default=KEYS, help="answer key (default evals/expected_chunks.yaml)")
    ap.add_argument("--reuse-plans", metavar="PROVIDER:MODEL",
                    help="#240 / #248: every plan from a saved planner output in the cache, never a planner call; "
                         "a missing plan stops the run before any search (exit 2). Mock or --real.")
    ap.add_argument("--cache", type=Path, help="cache folder (default .eval-runs/cache), e.g. a copied record folder")
    ap.add_argument("--naive-tz", help="#248: the zone of saved records whose `at` has no UTC offset (every record "
                                       "before #248: America/Chicago); an IANA name or a fixed offset like -06:00")
    args = ap.parse_args(argv)
    if args.real and (args.max_calls is None or args.max_calls < 0):
        ap.error("--real needs --max-calls N (CLAUDE.md 'Paid API calls'); nothing was called")
    if args.plan_only and not args.real:
        ap.error("--plan-only needs --real (the mock planner makes no call)")
    if args.map_only and not args.real:
        ap.error("--map-only needs --real (use --map for a mock run)")
    if args.map_only and args.plan_only:
        ap.error("--map-only and --plan-only exclude each other")
    if args.legacy and args.map_only:
        ap.error("--legacy and --map-only exclude each other")
    run_map_step = not args.legacy   # #247 (review note 1): the eval maps unless --legacy, whatever MAP says
    from cee.answer import cost as C
    try:
        C.parse_tz(args.naive_tz)
    except C.CostError as e:
        ap.error(str(e))
    if args.max_calls is not None and args.max_calls > 10:
        print("Note: more than 10 calls needs the user's OK first (CLAUDE.md 'Paid API calls').")

    from cee.config import settings
    from cee.retrieve import fts
    from cee.retrieve.fts import PoolTrace, budget, budget_tokens, resolve, search
    from cee.ask import answer_for, union_hits
    from cee.retrieve.planner import PLANNER_VERSION, plan_question, rules_plan, search_subquestions

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
    run_dir = Path(args.out) if args.out else RUNS / run_id
    base = {}
    if args.baseline:
        base = {r["id"]: r for r in json.loads(Path(args.baseline).read_text(encoding="utf-8"))["questions"]}
    subs = substitutes()
    supersede = effective_behaviors()
    cache_dir = args.cache or CACHE
    saved_plans = None
    if args.reuse_plans:  # #240 / #248: plans only from saved planner outputs, checked before any search
        from cee.ask import model_name
        provider, _, model = args.reuse_plans.partition(":")
        # #272: PROVIDER:MODEL@VERSION reads plans saved under another planner request version (e.g. the #250
        # plans, ds-strict-1-think-on-a64000-p64000); without @ the planner stage's current version
        model, _, plan_request = model.partition("@")
        if not provider or not model:
            ap.error("--reuse-plans takes PROVIDER:MODEL[@REQUEST_VERSION], e.g. deepseek:deepseek-v4-pro")
        if args.real and (provider != settings().llm_provider or model != model_name(provider)):
            ap.error(f"--reuse-plans {args.reuse_plans} is not this run's provider and model "
                     f"({settings().llm_provider}:{model_name(settings().llm_provider)}); nothing was called")
        plan_request = plan_request or stage_version(provider, "plan")
        missing = missing_plans(bank, resolve, args.as_of, snapshot, provider, model,
                                plan_request, args.k, cache_dir)
        if missing:
            print(f"--reuse-plans: no saved plan for {', '.join(missing)}; nothing was searched or called.")
            return 2
        if not args.real:
            saved_plans = SavedPlans(provider, model, snapshot, cache_dir, request=plan_request)
    if args.real and not args.naive_tz and C.needs_time(settings().llm_provider):
        naive = naive_records(cache_dir)   # #248: priced by period, so their zone must be given
        if naive:
            print(f"{len(naive)} saved records in {cache_dir} have a time without a UTC offset (e.g. {naive[0]}); "
                  f"pass the zone they were written in, e.g. --naive-tz America/Chicago. Nothing was called.")
            return 2
    if args.real:
        real = (RealRunner(settings().llm_provider, args.max_calls, snapshot, run_dir, cache_dir=args.cache)
                if args.cache else RealRunner(settings().llm_provider, args.max_calls, snapshot, run_dir))
        real.plans_only = bool(args.reuse_plans)
        if args.reuse_plans:   # #272: the plans' request version (@VERSION or the planner stage's)
            real.plan_version = plan_request
    else:
        real = None
    if args.naive_tz:
        print(f"Naive record times are read as {args.naive_tz} (--naive-tz).")

    records = []
    for q in bank:
        start = len(real.ledger) if real else 0   # #248: this question's calls in the ledger
        query = resolve(q["text"], today=args.as_of)  # retrieval and scoring share one window end
        # #213: without --k, search() takes the app's rule (passages, or tokens with TOKEN_BUDGET);
        # an explicit k is the passage rule. budget() includes the peers' slots (#205).
        b_tokens = budget_tokens(query) if args.k is None else None
        k = args.k if args.k is not None else (budget(query) if b_tokens is None else None)
        trace = PoolTrace()  # #210: the candidate pools before select(), recording only
        # #214 (ADR-020): token mode without --k searches the question's plan (the rule plan on mock,
        # one planner call with --real); passage mode is one whole-question search, no planner.
        plan, pools, capped = None, {}, False
        if args.k is None and b_tokens is not None:
            plan = (real.plan(q, query) if real else saved_plans.plan(q, query) if saved_plans
                    else plan_question(query, "mock"))
            if plan is None:   # the planner call would pass --max-calls: rule plan, no answer call
                plan, capped = rules_plan(query), True
        t0 = time.perf_counter()
        if plan is not None:
            hits = search_subquestions(query, plan, trace=trace, part_pools=pools, as_of=args.as_of)
        else:
            hits = search(query, trace=trace) if args.k is None else search(query, k=args.k, trace=trace)
        search_s = round(time.perf_counter() - t0, 3)
        r = evaluate(q, query, hits, corpus, subs, args.min_coverage, key_for(q, keys), args.as_of, doc_dates,
                     trace.ids())
        r |= prompt_size(k, hits, b_tokens, trace.peers)
        r |= {"search_s": search_s, "unattached": list(trace.unattached),
              # #247 part 2: the passages the per-period and pin passes added, by origin
              "added_chunk_ids": {o: [h.chunk_id for h in hits if getattr(h, "origin", "search") == o]
                                  for o in ("period", "pinned")}}
        research = [h for h in hits if h.part_id == "research"]
        r |= {"plan": plan.to_log() if plan else None, "parts": len(plan.parts) if plan else 1,
              "aspects": len(plan.aspects) if plan else 1, "subquestions": len(plan.subquestions) if plan else 1,
              "research_passages": len(research), "research_tokens": round(sum(len(h.text) for h in research) / 4),
              "llm_calls": {"planner": plan.calls if plan else 0, "answer": 0}}
        if plan is not None and plan.searched:   # #245: the budget is per sub-question
            sub_budget = sum(s["budget"] for s in plan.searched)
            sub_tokens = sum(s.get("tokens", 0) for s in plan.searched)
            r |= {"budget_tokens": sub_budget, "subquestion_tokens": sub_tokens,
                  "fill": round(sub_tokens / sub_budget, 3) if sub_budget else None}

        part_stages(r["recall"], hits, {**pools, "research": set(trace.research), "peers": set(trace.peers)})
        if real:
            r["plan_origin"] = real.last_plan_origin if not capped else "not planned: --max-calls reached"
            r["plan_parse_flags"] = list(real.last_plan_flags) if not capped else []
        matrix = None
        if run_map_step and plan is not None and hits and not capped and not (real and args.plan_only):
            from cee.answer.extract import EXTRACT_VERSION, run_map
            matrix = (real.map(q, query, plan, hits, as_of=args.as_of) if real
                      else run_map(query, plan, hits, "mock", as_of=args.as_of))
            made = [c for c in matrix.calls if not c.get("skipped")]
            r |= {"matrix": matrix.to_log(), "map_behavior": matrix.behavior,
                  "map_behavior_reason": matrix.behavior_reason,
                  "expected_behavior_effective": supersede.get(q["id"], q.get("expected_behavior")),
                  "map_calls": sum(c["round"] == 1 for c in made), "remap_calls": sum(c["round"] == 2 for c in made),
                  "map_must_not": map_must_not(matrix, key_for(q, keys)), "map_research": matrix.research,
                  "map_capped_calls": list(real.map_capped) if real else [],
                  "map_call_flags": {c["id"]: c["flags"] for c in matrix.calls if c.get("flags")},
                  "corrective_chunk_ids": [h.chunk_id for h in matrix.corrective],   # #247 B1
                  "map_breaks": matrix.breaks}
            r["llm_calls"] |= {"map": r["map_calls"], "remap": r["remap_calls"]}
            if real and real.bad_request:   # a 400: every planned call would fail the same way
                r["cost"] = question_cost(price_rows(real.ledger[start:], args.naive_tz))
                records.append(r)
                write_reports(run_dir, {"run_id": run_id, "snapshot": snapshot, "mode": "real", "commit": "",
                                        "k": "-", "min_coverage": args.min_coverage, "as_of": args.as_of.isoformat(),
                                        "real_calls": real.made, "max_calls": args.max_calls, "reused": real.reused,
                                        "stopped": real.bad_request}, records)
                raise SystemExit(f"stopped: a map request was rejected with 400 ({real.bad_request})")
        if real and args.plan_only:
            r["model"] = "plan_only"
        elif real and args.map_only:
            r["model"] = "map_only"
        elif real:
            every = union_hits(hits, matrix)   # #247 B1: retrieval + corrective re-search hits
            if capped:
                answer, how, info = None, "cap", {}
            elif matrix is not None:
                answer, how, info = real.reduce(q, query, plan, every, matrix)
            else:
                (answer, how), info = real.answer(q, query, hits, plan), {}
            r = apply_real(r, answer, how, real.last_file if not capped else None)
            if matrix is not None:
                r["reduce"] = {**info, "how": how}
            if answer is not None and plan is not None:   # #215: how each part was covered (on the union)
                from cee.answer.schema import Answer
                from cee.answer.validate import part_coverage
                r["part_coverage"] = part_coverage(Answer(**answer), plan, every, matrix)
            r["llm_calls"]["answer"] = int(how in ("called", "cached", "invalid", "failed"))
            r["stop_reason"], r["output_tokens"] = real.last_stop if not capped else (None, None)   # #230
            if real.bad_request:   # #247: a 400 on the reduce call: the run stops, every record saved
                r["cost"] = question_cost(price_rows(real.ledger[start:], args.naive_tz))
                records.append(r)
                write_reports(run_dir, {"run_id": run_id, "snapshot": snapshot, "mode": "real", "commit": "",
                                        "k": "-", "min_coverage": args.min_coverage, "as_of": args.as_of.isoformat(),
                                        "real_calls": real.made, "max_calls": args.max_calls, "reused": real.reused,
                                        "stopped": real.bad_request}, records)
                raise SystemExit(f"stopped: a reduce request was rejected with 400 ({real.bad_request})")
        elif matrix is not None:   # #247: the mock reduce (0 calls); retrieval status unchanged
            info: dict = {}
            every = union_hits(hits, matrix)
            a, _ = answer_for(q["text"], query, every, "mock", plan=plan, matrix=matrix, info=info)
            from cee.answer.validate import part_coverage
            r["reduce"] = {**info, "how": "code_built" if info.get("code_built") else "mock"}
            r["answer"], r["answer_behavior"] = a.model_dump(), a.behavior
            r["part_coverage"] = part_coverage(a, plan, every, matrix)
        if args.baseline:
            r["change"] = compare(r, base.get(q["id"]))
        r["cost"] = question_cost(price_rows(real.ledger[start:], args.naive_tz) if real else [])
        records.append(r)
        print(f"{q['id']:>4} {r['status']:<13} coverage {r['coverage']} forbidden {len(r['forbidden'])}"
              + (f" recall {r['doc_recall']} refusal {_refusal(r)}" if r["recall"] else "")
              + (f" recall@pool {r['recall_pool']} recall@final {r['recall_final']}"
                 if r["recall_pool"] is not None else "")
              + f" passages {r['passages']} tokens~{r['tokens_est']} sub-questions {r['subquestions']}"
              + (f" change {r['change']}" if args.baseline else "") + (f" model {r['model']}" if real else ""))

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    meta = {"run_id": run_id, "snapshot": snapshot, "commit": commit,
            "k": "by question" if args.k is None else args.k, "min_coverage": args.min_coverage,
            "pool_per_group": fts.POOL_PER_GROUP, "token_budget": fts.TOKEN_BUDGET if args.k is None else None,
            "planner": settings().planner, "subquestion_tokens": settings().subquestion_tokens,
            "planner_version": PLANNER_VERSION, "plan_only": args.plan_only,
            "map_setting": settings().map_on, "legacy": args.legacy,
            "mode": "real" if real else "mock", "baseline": args.baseline, "as_of": args.as_of.isoformat(),
            "real_calls": real.made if real else 0, "calls_reserved": real.calls if real else 0,
            "reused": real.reused if real else 0, "max_calls": args.max_calls,
            "map": run_map_step, "map_only": args.map_only, "extract_version": extract_version(),
            "map_concurrency": settings().map_concurrency, "reduce_version": reduce_version(),
            "map_max_tokens": real.map_max_tokens if real else None,
            "reuse_plans": args.reuse_plans, "cache": str(cache_dir),
            "cost": {**run_cost(records), "naive_tz": args.naive_tz,
                     "prices": "config/pricing.yaml"}}
    write_reports(run_dir, meta, records)
    counts = {s: sum(r["status"] == s for r in records) for s in STATUSES}
    summary = summarize(records)
    print(f"\n{counts} | tier-1 recall {summary['tier1_doc_recall']} | refusal gap {summary['refusal_gap']['ok']}/"
          f"{summary['refusal_gap']['of']} | recall@pool {summary['recall_pool']} recall@final "
          f"{summary['recall_final']} (tier 1: {summary['tier1_recall_pool']} / {summary['tier1_recall_final']})"
          f" | passages {summary['passages']} tokens~{summary['tokens_est']}"
          f" | real calls {meta['real_calls']} | ${meta['cost']['usd']:.3f} (new ${meta['cost']['usd_new']:.3f})"
          f" | report: {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
