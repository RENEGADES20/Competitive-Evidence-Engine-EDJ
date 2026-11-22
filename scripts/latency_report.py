"""Answer latency from a run's raw call records (#272). 0 calls: reads files only.

Each record of an eval run's raw/ folder (scripts/eval_run.py) is one model call: Q<n>-plan-<key>.json,
Q<n>-map.<id>-<key>.json, Q<n>-remap.<id>-<key>.json, Q<n>-reduce-<key>.json, with `wall_s`, `usage`
(output_tokens, reasoning_tokens) and, for streamed calls (#272), `ttft_s`.

Per question:
- critical path = plan + slowest round-1 map call + slowest re-map call + reduce (the stages run in series,
  the calls of one map round in parallel);
- first evidence = plan + fastest round-1 map call (when the Ask page can show the first cited evidence);
- first claim (#275) = plan + slowest round-1 map + slowest re-map + the reduce's first_claim_s (when the Ask page
  shows the first checked claim of the final answer while the reduce streams); "-" for records without it.
Per stage: p50 / p90 / max of wall time, time to first token, output tokens and the reasoning share.
A record reused from an earlier run keeps the time it was made with.

With the run's report.json (--report; the run folder's own is read when present), each question also gets its
retrieval time (`search_s`: every sub-question search before the map) and, in the hybrid modes, the time spent
embedding the query texts (`embed_s`, exp/hybrid #272); "with retrieval" adds search_s to the critical path.

  python scripts/latency_report.py <run>/raw [--questions Q5,Q10] [--title "C1"] [--json out.json] [--report report.json]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

NAME = re.compile(r"^(Q\d+)-(plan|reduce|map\.[^-]+|remap\.[^-]+)-[0-9a-f]+\.json$")
STAGES = ("plan", "map", "remap", "reduce")


def stage_of(kind: str) -> str:
    return kind.split(".", 1)[0]


def load(raw_dir: Path, questions: set[str] | None = None) -> list[dict]:
    """One row per call record: question, stage, call id, wall_s, ttft_s, output and reasoning tokens."""
    rows = []
    for p in sorted(raw_dir.glob("Q*.json")):
        m = NAME.match(p.name)
        if not m or (questions and m.group(1) not in questions):
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        usage = rec.get("usage") or {}
        rows.append({"q": m.group(1), "stage": stage_of(m.group(2)), "id": m.group(2),
                     "wall_s": rec.get("wall_s"), "ttft_s": rec.get("ttft_s", usage.get("ttft_s")),
                     "out": usage.get("output_tokens"), "reasoning": usage.get("reasoning_tokens"),
                     "cut": rec.get("stop_reason") == "length", "invalid": bool(rec.get("invalid")),
                     "failed": bool(rec.get("failed_call")), "model": rec.get("model"),
                     "request_version": rec.get("request_version"), "first_claim_s": rec.get("first_claim_s")})
    return rows


def pct(xs: list[float], p: float) -> float | None:
    """Percentile with linear interpolation between ranks (p in 0..100; p50 = the median); None for no
    values."""
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 2)


def per_question(rows: list[dict], retrieval: dict | None = None) -> list[dict]:
    retrieval = retrieval or {}
    out = []
    for q in sorted({r["q"] for r in rows}, key=lambda x: int(x[1:])):
        rs = [r for r in rows if r["q"] == q]

        def walls(stage):
            return [r["wall_s"] or 0.0 for r in rs if r["stage"] == stage]
        plan, maps, remaps, reduce = sum(walls("plan")), walls("map"), walls("remap"), sum(walls("reduce"))
        crit = plan + (max(maps) if maps else 0) + (max(remaps) if remaps else 0) + reduce
        first = plan + min(maps) if maps else None
        fc = [r["first_claim_s"] for r in rs if r["stage"] == "reduce" and r.get("first_claim_s") is not None]
        first_claim = crit - reduce + fc[0] if fc else None
        out.append({"q": q, "plan_s": round(plan, 1), "map_calls": len(maps),
                    "map_max_s": round(max(maps), 1) if maps else None, "remap_calls": len(remaps),
                    "remap_max_s": round(max(remaps), 1) if remaps else None, "reduce_s": round(reduce, 1),
                    "critical_s": round(crit, 1), "first_evidence_s": round(first, 1) if first is not None else None,
                    "first_claim_s": round(first_claim, 1) if first_claim is not None else None,
                    "calls": len(rs), "cut": sum(r["cut"] for r in rs), "invalid": sum(r["invalid"] for r in rs),
                    "failed": sum(r["failed"] for r in rs)})
        rt = retrieval.get(q) or {}
        if rt.get("search_s") is not None:
            out[-1].update(search_s=rt["search_s"], embed_s=rt.get("embed_s"), embed_calls=rt.get("embed_calls"),
                           with_retrieval_s=round(crit + rt["search_s"], 1),
                           first_with_retrieval_s=round(first + rt["search_s"], 1) if first is not None else None)
    return out


def load_retrieval(report: Path) -> dict:
    """search_s / embed_s / embed_calls per question from an eval run's report.json."""
    rep = json.loads(report.read_text(encoding="utf-8"))
    return {r["id"]: {k: r.get(k) for k in ("search_s", "embed_s", "embed_calls")} for r in rep.get("questions", [])}


def per_stage(rows: list[dict]) -> list[dict]:
    out = []
    for st in STAGES:
        rs = [r for r in rows if r["stage"] == st]
        if not rs:
            continue
        outs = [r["out"] for r in rs if r["out"] is not None]
        reas = [r["reasoning"] for r in rs if r["reasoning"] is not None and r["out"]]
        share = (sum(reas) / sum(r["out"] for r in rs if r["reasoning"] is not None and r["out"])) if reas else None
        walls = [r["wall_s"] for r in rs]
        ttfts = [r["ttft_s"] for r in rs]
        out.append({"stage": st, "calls": len(rs), "wall_p50": pct(walls, 50), "wall_p90": pct(walls, 90),
                    "wall_max": pct(walls, 100), "ttft_p50": pct(ttfts, 50), "ttft_p90": pct(ttfts, 90),
                    "out_p50": pct(outs, 50), "out_max": pct(outs, 100),
                    "reasoning_share": round(share, 2) if share is not None else None})
    return out


def summary(qs: list[dict]) -> dict:
    crit = [q["critical_s"] for q in qs]
    first = [q["first_evidence_s"] for q in qs if q["first_evidence_s"] is not None]
    claim = [q["first_claim_s"] for q in qs if q.get("first_claim_s") is not None]
    search = [q["search_s"] for q in qs if q.get("search_s") is not None]
    embed = [q["embed_s"] for q in qs if q.get("embed_s") is not None]
    withr = [q["with_retrieval_s"] for q in qs if q.get("with_retrieval_s") is not None]
    extra = ({"search_p50": pct(search, 50), "search_p90": pct(search, 90), "search_max": pct(search, 100),
              "embed_p50": pct(embed, 50), "embed_p90": pct(embed, 90), "embed_max": pct(embed, 100),
              "with_retrieval_p50": pct(withr, 50), "with_retrieval_p90": pct(withr, 90),
              "with_retrieval_max": pct(withr, 100)} if search else {})
    return {**extra, "questions": len(qs), "critical_p50": pct(crit, 50), "critical_p90": pct(crit, 90),
            "critical_max": pct(crit, 100), "critical_min": min(crit) if crit else None,
            "first_evidence_p50": pct(first, 50), "first_evidence_p90": pct(first, 90),
            "first_claim_p50": pct(claim, 50), "first_claim_p90": pct(claim, 90),
            "calls": sum(q["calls"] for q in qs), "cut": sum(q["cut"] for q in qs),
            "invalid": sum(q["invalid"] for q in qs), "failed": sum(q["failed"] for q in qs)}


def _f(v) -> str:
    if v is None:
        return "-"
    return f"{v:,.0f}" if isinstance(v, (int, float)) and abs(v) >= 100 else (f"{v:g}" if isinstance(v, float) else str(v))


def markdown(title: str, qs: list[dict], stages: list[dict], s: dict) -> str:
    lines = [f"### {title}", "",
             f"{s['questions']} questions, {s['calls']} call records: critical path p50 {_f(s['critical_p50'])} s, "
             f"p90 {_f(s['critical_p90'])} s, max {_f(s['critical_max'])} s; first evidence p50 "
             f"{_f(s['first_evidence_p50'])} s, p90 {_f(s['first_evidence_p90'])} s; first claim p50 "
             f"{_f(s.get('first_claim_p50'))} s, p90 {_f(s.get('first_claim_p90'))} s; cut {s['cut']}, invalid "
             f"{s['invalid']}, failed {s['failed']}.", ""]
    if "search_p50" in s:
        lines += [f"Retrieval (search_s): p50 {_f(s['search_p50'])} s, p90 {_f(s['search_p90'])} s, max "
                  f"{_f(s['search_max'])} s; query embedding (embed_s): p50 {_f(s['embed_p50'])} s, p90 "
                  f"{_f(s['embed_p90'])} s, max {_f(s['embed_max'])} s; critical path with retrieval: p50 "
                  f"{_f(s['with_retrieval_p50'])} s, p90 {_f(s['with_retrieval_p90'])} s, max "
                  f"{_f(s['with_retrieval_max'])} s.", ""]
    ret = "search_p50" in s
    lines += [
             "| Q | " + ("retrieval s | embed s | " if ret else "") + "plan s | map calls | slowest map s | re-maps | "
             "slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |",
             "|---|" + ("---|---|" if ret else "") + "---|---|---|---|---|---|---|---|---|---|"]
    for q in qs:
        lines.append(f"| {q['q']} | " + (f"{_f(q.get('search_s'))} | {_f(q.get('embed_s'))} | " if ret else "")
                     + f"{_f(q['plan_s'])} | {q['map_calls']} | {_f(q['map_max_s'])} | {q['remap_calls']} | "
                     f"{_f(q['remap_max_s'])} | {_f(q['reduce_s'])} | {_f(q['critical_s'])} | "
                     f"{_f(q['first_evidence_s'])} | {_f(q.get('first_claim_s'))} | {q['cut']} |")
    lines += ["", "| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for st in stages:
        lines.append(f"| {st['stage']} | {st['calls']} | {_f(st['wall_p50'])} | {_f(st['wall_p90'])} | "
                     f"{_f(st['wall_max'])} | {_f(st['ttft_p50'])} | {_f(st['ttft_p90'])} | {_f(st['out_p50'])} | "
                     f"{_f(st['out_max'])} | {_f(st['reasoning_share'])} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw", type=Path, help="a run's raw/ folder (or the run folder)")
    ap.add_argument("--questions", default="", help="comma-separated IDs, e.g. Q5,Q10")
    ap.add_argument("--title", default="")
    ap.add_argument("--json", type=Path, default=None, help="also write the numbers as JSON here")
    ap.add_argument("--report", type=Path, default=None,
                    help="the run's report.json for retrieval times (default: the run folder's, when present)")
    a = ap.parse_args(argv)
    raw = a.raw / "raw" if (a.raw / "raw").is_dir() else a.raw
    report = a.report or (raw.parent / "report.json" if (raw.parent / "report.json").is_file() else None)
    wanted = {x.strip() for x in a.questions.split(",") if x.strip()} or None
    rows = load(raw, wanted)
    if not rows:
        print(f"No call records in {raw}")
        return 1
    qs, stages = per_question(rows, load_retrieval(report) if report else None), per_stage(rows)
    s = summary(qs)
    sys.stdout.write(markdown(a.title or str(raw), qs, stages, s))
    if a.json:
        a.json.write_text(json.dumps({"summary": s, "questions": qs, "stages": stages}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
