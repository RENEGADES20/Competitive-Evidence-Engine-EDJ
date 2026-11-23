"""Facts extraction (#285, ADR-022): one model call per document that holds candidate chunks, every proposed row
code-checked, the passing rows written to config/facts.jsonl. Paid only with --real (a planned run: CLAUDE.md "Paid
API calls"); every raw output is saved and reused, never re-called.

  python scripts/extract_facts.py --out DIR --count                 # 0 calls: documents, chunks, estimated tokens
  python scripts/extract_facts.py --out DIR --real --max-calls 76   # the run (DeepSeek, map-stage settings)
  python scripts/extract_facts.py --out DIR --write                 # 0 calls: saved records -> config/facts.jsonl
  python scripts/extract_facts.py --verify                          # 0 calls: every stored row against the database
  python scripts/extract_facts.py --out DIR --audit 50 --seed 285   # 0 calls: a random sample for an auditor

Stop rules (plan TL non-blocking 2): no new call once more than 10% of the planned calls failed or came back invalid,
or once the run's cost passes --max-usd (default 3). Off-peak only unless --allow-peak.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import random
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cee import facts  # noqa: E402
from cee.config import settings  # noqa: E402


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def is_peak_now(prices=None) -> bool:
    from cee.answer import cost
    entry = ((prices or cost.load_prices()).get("providers") or {}).get("deepseek") or {}
    return cost.is_peak(_now(), entry)


def request_version() -> str:
    from cee.answer import llm
    return f"{llm.request_version('deepseek', 'map')}-{facts.extract_version()}"


def record_path(out: Path, doc_id: str) -> Path:
    return out / "raw" / f"{doc_id}.json"


def est_tokens(doc, chunks) -> int:
    return round((len(facts.system_prompt()) + len(json.dumps(facts.extract_schema()))
                  + len(facts.extract_message(doc, chunks))) / 4)


def _jsonable(v):
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    return v


def one_call(client, doc, chunks) -> dict:
    from cee.answer import llm
    meta: dict = {}
    t0, at = time.monotonic(), _now()
    rec = {"doc_id": doc["doc_id"], "extract_version": facts.extract_version(), "request_version": request_version(),
           "provider": "deepseek", "model": llm.stage_model("map"), "at": at.isoformat(),
           "chunk_ids": [c["chunk_id"] for c in chunks],
           "prompt_sha": hashlib.sha256((facts.system_prompt() + facts.extract_message(doc, chunks)).encode()).hexdigest()[:16],
           "est_input_tokens": est_tokens(doc, chunks), "raw": None, "error": None, "invalid": False, "failed_call": False}
    try:
        rec["raw"] = facts.call_extract(client, doc, chunks, meta)
    except llm.ProviderStop:
        raise
    except llm.ModelOutputError as e:
        rec["invalid"], rec["error"] = True, str(e)
    except Exception as e:   # saved as a failed call; never retried
        rec["failed_call"], rec["error"] = True, f"{type(e).__name__}: {e}"
    wall = round(time.monotonic() - t0, 2)
    usage = meta.get("usage") or {}
    ttft = usage.get("ttft_s")
    out_tok = usage.get("output_tokens") or 0
    rec.update({"finished_at": _now().isoformat(), "wall_s": wall, "ttft_s": ttft, "usage": usage,
                "stop_reason": meta.get("stop_reason"), "reasoning_content": meta.get("reasoning_content"),
                "parse_flags": meta.get("parse_flags") or [],
                "raw_payload": None if rec["raw"] is not None else meta.get("payload"),
                "tokens_per_s": round(out_tok / (wall - (ttft or 0)), 2) if out_tok and wall > (ttft or 0) else None})
    return rec


def price(rec: dict) -> dict:
    from cee.answer import cost
    return cost.price_call("deepseek", rec.get("model"), rec.get("usage"), finished_at=rec.get("finished_at"))


def off_peak_usd(rec: dict) -> float:
    from cee.answer import cost
    rates = cost.load_prices()["providers"]["deepseek"]["models"].get(rec.get("model") or "", {}).get("off_peak")
    t = cost.tokens(rec.get("usage"))
    if not rates:
        return 0.0
    return (t["cache_hit_tokens"] * rates["input_cache_hit"] + t["cache_miss_tokens"] * rates["input_cache_miss"]
            + t["output_tokens"] * rates["output"]) / 1e6


def run(args, docs) -> int:
    from cee.answer import llm
    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    todo = [d for d in docs if not record_path(out, d["doc"]["doc_id"]).exists()]
    print(f"{len(docs)} documents, {len(docs) - len(todo)} saved records reused, {len(todo)} calls to make")
    if not todo:
        return 0
    if len(todo) > args.max_calls:
        print(f"STOP: {len(todo)} calls needed, --max-calls {args.max_calls}")
        return 2
    if settings().llm_provider != "deepseek":
        print("STOP: LLM_PROVIDER must be deepseek for --real")
        return 2
    if is_peak_now() and not args.allow_peak:
        print("STOP: DeepSeek peak hours (UTC 01-04, 06-10 Mon-Fri); run off-peak or pass --allow-peak")
        return 2
    client = llm.deepseek_client()
    lock = threading.Lock()
    state = {"bad": 0, "usd": 0.0, "stopped": None, "done": 0}
    bad_max = int(0.10 * len(docs))

    def work(d):
        with lock:
            if state["stopped"]:
                return None
        rec = one_call(client, d["doc"], d["chunks"])
        record_path(out, d["doc"]["doc_id"]).write_text(json.dumps(rec, ensure_ascii=False, indent=1, default=_jsonable),
                                                        encoding="utf-8")
        with lock:
            state["done"] += 1
            state["usd"] += price(rec).get("usd") or 0.0
            if rec["invalid"] or rec["failed_call"]:
                state["bad"] += 1
            if state["bad"] > bad_max:
                state["stopped"] = f"more than 10% failed or invalid ({state['bad']} > {bad_max})"
            elif state["usd"] > args.max_usd:
                state["stopped"] = f"cost ${state['usd']:.2f} passed --max-usd {args.max_usd}"
            print(f"[{state['done']}/{len(todo)}] {d['doc']['doc_id']}: "
                  f"{'invalid' if rec['invalid'] else 'failed' if rec['failed_call'] else 'ok'} "
                  f"{rec['wall_s']} s, ${state['usd']:.3f}", flush=True)
        return rec

    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        list(ex.map(work, todo))
    if state["stopped"]:
        print(f"STOP rule: {state['stopped']}")
        return 3
    return 0


def saved_records(out: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "raw").glob("*.json"))]


def write(args, docs) -> dict:
    out = Path(args.out)
    by_doc = {d["doc"]["doc_id"]: d for d in docs}
    kept, rejected, summary = [], [], {"records": 0, "invalid": 0, "failed": 0, "proposed": 0, "kept": 0,
                                       "reasons": {}, "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0,
                                       "usd_billed": 0.0, "usd_off_peak": 0.0, "wall_s": [], "tokens_per_s": []}
    for rec in saved_records(out):
        summary["records"] += 1
        u = rec.get("usage") or {}
        for k in ("input_tokens", "output_tokens", "reasoning_tokens"):
            summary[k] += u.get(k) or 0
        summary["usd_billed"] += price(rec).get("usd") or 0.0
        summary["usd_off_peak"] += off_peak_usd(rec)
        summary["wall_s"].append(rec.get("wall_s"))
        if rec.get("tokens_per_s"):
            summary["tokens_per_s"].append(rec["tokens_per_s"])
        if rec.get("invalid"):
            summary["invalid"] += 1
            continue
        if rec.get("failed_call") or rec.get("raw") is None:
            summary["failed"] += 1
            continue
        d = by_doc.get(rec["doc_id"])
        if d is None:
            continue
        rows, rej = facts.check_output(rec["raw"], d["doc"], d["chunks"], rec.get("model") or "")
        summary["proposed"] += len(rows) + len(rej)
        kept += rows
        for r in rej:
            summary["reasons"][r["reject"]] = summary["reasons"].get(r["reject"], 0) + 1
            rejected.append({"doc_id": rec["doc_id"], **r})
    seen, uniq = set(), []
    for r in kept:
        if r["fact_id"] not in seen:
            seen.add(r["fact_id"])
            uniq.append(r)
    summary["kept"] = len(uniq)
    summary["pass_rate"] = round(len(uniq) / summary["proposed"], 4) if summary["proposed"] else None
    for k in ("usd_billed", "usd_off_peak"):
        summary[k] = round(summary[k], 4)
    w = sorted(x for x in summary.pop("wall_s") if x is not None)
    t = sorted(summary.pop("tokens_per_s"))
    summary["wall_p50"] = w[len(w) // 2] if w else None
    summary["wall_max"] = w[-1] if w else None
    summary["tokens_per_s_p50"] = t[len(t) // 2] if t else None
    summary["by_metric"] = {}
    for r in uniq:
        key = f"{r['entity_id']}:{r['metric']}"
        summary["by_metric"][key] = summary["by_metric"].get(key, 0) + 1
    facts.write_rows(uniq, Path(args.facts_file) if args.facts_file else None)
    (out / "rejected.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rejected),
                                        encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return summary


def verify(args) -> int:
    """Gate 5a: every stored row against the database: chunk exists, entity = the document's, segment = the chunk's,
    quote verbatim in the chunk text, value verbatim in the quote, period end not after publication."""
    from cee.db import connect
    rows = facts.read_rows(Path(args.facts_file) if args.facts_file else None)
    bad = []
    with connect() as conn:
        db = {r["chunk_id"]: r for r in conn.execute(
            "SELECT c.chunk_id, c.text, c.segment, d.entity_id, d.published_at FROM chunks c JOIN documents d "
            "USING (doc_id) WHERE c.chunk_id = ANY(%s)", ([r["chunk_id"] for r in rows],)).fetchall()}
    for r in rows:
        c = db.get(r["chunk_id"])
        why = None
        if c is None:
            why = "chunk missing"
        elif c["entity_id"] != r["entity_id"]:
            why = "entity differs"
        elif (c["segment"] or None) != (r["segment"] or None):
            why = "segment differs"
        elif facts.squash(r["quote"]) not in facts.squash(c["text"]):
            why = "quote not verbatim"
        elif not facts.value_in(r["value"], r["quote"]):
            why = "value not in quote"
        elif str(c["published_at"]) < r["period_end"]:
            why = "period after publication"
        if why:
            bad.append({"fact_id": r["fact_id"], "why": why})
    print(f"verify: {len(rows) - len(bad)}/{len(rows)} rows pass")
    for b in bad[:20]:
        print(" ", b)
    return 0 if not bad else 1


def audit(args) -> int:
    """A seeded random sample of stored rows, each with its chunk text and document header, for an auditor."""
    from cee.db import connect
    rows = facts.read_rows(Path(args.facts_file) if args.facts_file else None)
    sample = random.Random(args.seed).sample(rows, min(args.audit, len(rows)))
    with connect() as conn:
        db = {r["chunk_id"]: r for r in conn.execute(
            "SELECT c.chunk_id, c.text, c.prefix, c.segment, c.section, c.page, d.doc_id, d.entity_id, d.doc_type, "
            "d.published_at::text AS published_at, d.period_end::text AS period_end FROM chunks c JOIN documents d "
            "USING (doc_id) WHERE c.chunk_id = ANY(%s)", ([r["chunk_id"] for r in sample],)).fetchall()}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# Facts audit sample: {len(sample)} of {len(rows)} stored rows (seed {args.seed})", "",
             "For each fact, read the chunk text and judge whether value, unit, period (period_end and period_type) and "
             "entity are correct for the labelled metric. Verdict per fact: correct, or wrong with the field(s).", ""]
    for n, r in enumerate(sample, 1):
        c = db[r["chunk_id"]]
        lines += [f"## F{n:02d} {r['fact_id']}",
                  f"- metric: {r['metric']}", f"- entity: {r['entity_id']} (segment {r['segment'] or 'none'})",
                  f"- label: {r['label']}", f"- scope: {r['scope'] or '(whole)'}", f"- value: {r['value']}",
                  f"- unit: {r['unit']}", f"- period_type: {r['period_type']}", f"- period_end: {r['period_end']}",
                  f"- quote: {r['quote']}",
                  f"- source: {c['doc_id']} ({c['doc_type']}, published {c['published_at']}, document period end "
                  f"{c['period_end'] or 'not set'}), chunk {r['chunk_id']}, section {facts.squash(c['section'])}, "
                  f"page {c['page']}", "", "Chunk text:", "", "```", c["text"].strip(), "```", ""]
    (out / "audit-sample.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "audit-sample.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in sample),
                                            encoding="utf-8")
    print(f"audit sample: {out / 'audit-sample.md'} ({len(sample)} rows)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="evidence folder (raw records, summary, rejected rows, audit sample)")
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--audit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=285)
    ap.add_argument("--max-calls", type=int, default=0)
    ap.add_argument("--max-usd", type=float, default=3.0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--allow-peak", action="store_true")
    ap.add_argument("--facts-file", default="")
    args = ap.parse_args(argv)
    if args.verify:
        return verify(args)
    if args.audit:
        return audit(args)
    from cee.db import connect
    with connect() as conn:
        docs = facts.candidate_docs(conn)
    if args.count:
        toks = [est_tokens(d["doc"], d["chunks"]) for d in docs]
        print(json.dumps({"documents": len(docs), "chunks": sum(len(d["chunks"]) for d in docs),
                          "est_input_tokens": sum(toks), "max_call_tokens": max(toks) if toks else 0,
                          "request_version": request_version()}, indent=1))
        return 0
    if args.real:
        return run(args, docs)
    if args.write:
        write(args, docs)
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
