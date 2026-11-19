"""Run the question bank against the loaded snapshot and write a per-question report (#43).

Default is mock: retrieval only, no model call, free. For each question it records the resolved
entities, the retrieved chunk IDs, which `expected_sources` patterns were hit, forbidden hits
(another firm's chunks; BAC chunks outside GWIM for Merrill questions) and a status.

  python scripts/eval_run.py                          # all 30, mock
  python scripts/eval_run.py --questions Q1,Q4 --k 20   # fixed k (default: the app's budget by question)
  python scripts/eval_run.py --baseline .eval-runs/<run>/report.json
  python scripts/eval_run.py --real --max-calls 5 --questions Q28,Q29,Q30

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
import json
import subprocess
import sys
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
            "patterns": rows, "available_patterns": len(avail), "hit_patterns": len(hit),
            "coverage": coverage, "forbidden": bad,
            "doc_recall": recall["doc_recall"] if recall else None,
            "passage_recall": recall["passage_recall"] if recall else None,
            "recall_pool": recall["recall_pool"] if recall else None,
            "recall_final": recall["recall_final"] if recall else None,
            "pool_size": len(set(pool_ids or ()) | {h.chunk_id for h in hits}) if pool_ids is not None else None,
            "refusal_ok": recall["refusal_ok"] if recall else None,
            "misleading": recall["misleading"] if recall else [], "recall": recall, "status": status}


def prompt_size(k: int, hits) -> dict:
    """What the model is handed (#181): the budget k, passages retrieved, their characters and the
    estimated tokens, characters / 4 (#210)."""
    chars = sum(len(h.text) for h in hits)
    return {"k": k, "passages": len(hits), "chars": chars, "tokens_est": round(chars / 4)}


def _score(r: dict) -> tuple:
    return (r["status"] == "PASS", r.get("refusal_ok") is not False, r.get("doc_recall") or 0.0,
            r.get("passage_recall") or 0.0, r["coverage"] or 0.0, -len(r["forbidden"]))


def compare(record: dict, base: dict | None) -> str:
    if base is None:
        return "NEW"
    a, b = _score(record), _score(base)
    return "IMPROVED" if a > b else "REGRESSED" if a < b else "UNCHANGED"


def cache_key(q: dict, prompt_version: str, snapshot: str, provider: str, model: str, chunk_ids: list) -> str:
    blob = json.dumps([q["id"], q["text"], prompt_version, snapshot, provider, model, chunk_ids])
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


class RealRunner:
    """Model answers with a hard call cap; every output cached and reused (never re-rolled)."""

    def __init__(self, provider: str, max_calls: int, snapshot: str, run_dir: Path, cache_dir: Path = CACHE):
        from cee.answer.prompt import PROMPT_VERSION
        from cee.ask import model_name

        if provider == "mock":
            raise SystemExit("--real needs LLM_PROVIDER=anthropic or openai; it is mock.")
        self.provider, self.max_calls, self.snapshot = provider, max_calls, snapshot
        self.model, self.prompt_version = model_name(provider), PROMPT_VERSION
        self.calls, self.reused, self.last_file = 0, 0, None
        self.cache_dir, self.raw_dir = cache_dir, run_dir / "raw"

    def answer(self, q: dict, query, hits) -> tuple[dict | None, str]:
        """(answer dict or None, how): how = no_call | cached | called | cap | invalid.
        invalid: the model output (new or cached) is not a valid Answer; its raw payload is in
        raw/<self.last_file> and the call still counts (#187)."""
        from cee.answer.llm import ModelOutputError
        from cee.answer.schema import Answer
        from cee.ask import answer_for

        self.last_file = None
        if not hits:
            answer, _ = answer_for(q["text"], query, hits, self.provider)
            return answer.model_dump(), "no_call"
        key = cache_key(q, self.prompt_version, self.snapshot, self.provider, self.model,
                        [h.chunk_id for h in hits])
        path = self.cache_dir / f"{q['id']}-{key}.json"
        self.last_file = path.name
        if path.is_file():
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.reused += 1
            self._copy(path)
            if saved.get("invalid"):    # a wrong output is a finding: never re-called (CLAUDE.md)
                return None, "invalid"
            answer, _ = answer_for(q["text"], query, hits, self.provider, raw=Answer(**saved["raw"]))
            return answer.model_dump(), "cached"
        if self.calls >= self.max_calls:
            return None, "cap"
        self.calls += 1   # counted before the call: a failed call still cost money
        meta = {"question_id": q["id"], "question": q["text"], "prompt_version": self.prompt_version,
                "snapshot": self.snapshot, "provider": self.provider, "model": self.model,
                "chunk_ids": [h.chunk_id for h in hits], "at": dt.datetime.now().isoformat()}
        try:
            answer, raw = answer_for(q["text"], query, hits, self.provider)
        except ModelOutputError as e:   # paid output that is not a valid Answer: keep it (#187)
            self._save(path, {**meta, "invalid": True, "error": str(e), "raw_payload": e.raw})
            return None, "invalid"
        self._save(path, {**meta, "raw": raw.model_dump()})
        return answer.model_dump(), "called"

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
             f"over {len(records)} questions  ",
             f"**Refusal accuracy**: gap questions ({gap_ids or 'none'}) {_frac(rg['ok'], rg['of'])}; "
             f"all questions with a key {_frac(ra['ok'], ra['of'])}", "",
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
    args = ap.parse_args(argv)
    if args.real and (args.max_calls is None or args.max_calls < 0):
        ap.error("--real needs --max-calls N (CLAUDE.md 'Paid API calls'); nothing was called")
    if args.max_calls is not None and args.max_calls > 10:
        print("Note: more than 10 calls needs the user's OK first (CLAUDE.md 'Paid API calls').")

    from cee.config import settings
    from cee.retrieve.fts import PoolTrace, budget, peer_slots, resolve, search

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
    real = RealRunner(settings().llm_provider, args.max_calls, snapshot, run_dir) if args.real else None

    records = []
    for q in bank:
        query = resolve(q["text"], today=args.as_of)  # retrieval and scoring share one window end
        k = budget(query) if args.k is None else args.k  # budget() includes the peers' slots (#205)
        # search() adds the theme peers' slots on top of the k it is given, as the app does
        trace = PoolTrace()  # #210: the candidate pools before select(), recording only
        hits = search(query, k=budget(query) - peer_slots(query) if args.k is None else args.k, trace=trace)
        r = evaluate(q, query, hits, corpus, subs, args.min_coverage, key_for(q, keys), args.as_of, doc_dates,
                     trace.ids())
        r |= prompt_size(k, hits)
        if real:
            r = apply_real(r, *real.answer(q, query, hits), real.last_file)
        if args.baseline:
            r["change"] = compare(r, base.get(q["id"]))
        records.append(r)
        print(f"{q['id']:>4} {r['status']:<13} coverage {r['coverage']} forbidden {len(r['forbidden'])}"
              + (f" recall {r['doc_recall']} refusal {_refusal(r)}" if r["recall"] else "")
              + (f" recall@pool {r['recall_pool']} recall@final {r['recall_final']}"
                 if r["recall_pool"] is not None else "")
              + f" passages {r['passages']} tokens~{r['tokens_est']}"
              + (f" change {r['change']}" if args.baseline else "") + (f" model {r['model']}" if real else ""))

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    meta = {"run_id": run_id, "snapshot": snapshot, "commit": commit,
            "k": "by question" if args.k is None else args.k, "min_coverage": args.min_coverage,
            "mode": "real" if real else "mock", "baseline": args.baseline, "as_of": args.as_of.isoformat(),
            "real_calls": real.calls if real else 0, "reused": real.reused if real else 0, "max_calls": args.max_calls}
    write_reports(run_dir, meta, records)
    counts = {s: sum(r["status"] == s for r in records) for s in STATUSES}
    summary = summarize(records)
    print(f"\n{counts} | tier-1 recall {summary['tier1_doc_recall']} | refusal gap {summary['refusal_gap']['ok']}/"
          f"{summary['refusal_gap']['of']} | recall@pool {summary['recall_pool']} recall@final "
          f"{summary['recall_final']} (tier 1: {summary['tier1_recall_pool']} / {summary['tier1_recall_final']})"
          f" | passages {summary['passages']} tokens~{summary['tokens_est']}"
          f" | real calls {meta['real_calls']} | report: {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
