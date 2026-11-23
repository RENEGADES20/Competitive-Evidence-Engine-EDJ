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
#283: a map call's time is gate_wait_s (waiting for its prefix leader) + wall_s, in the critical path and first
evidence. Cache table: input tokens and the DeepSeek cache-hit share per stage and per map prefix role (leader,
follower, solo, cell), and the probe metric of plans/0283-prefix-cache.md (TL condition B4): follower share =
sum(cache_hit_tokens) / sum(input_tokens x prefix_chars / request_chars) over followers whose leader was not reused;
>= 0.50 -> first_chunk, < 0.50 -> done, fewer than 5 such followers -> done (inconclusive).

  python scripts/latency_report.py <run>/raw [--questions Q5,Q10] [--title "C1"] [--json out.json]
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
                     "request_version": rec.get("request_version"), "first_claim_s": rec.get("first_claim_s"),
                     "input": usage.get("input_tokens"), "hit": usage.get("cache_hit_tokens"),
                     "role": rec.get("prefix_role"), "gate_wait_s": rec.get("gate_wait_s"),
                     "leader_cached": rec.get("leader_cached"), "prefix_chars": rec.get("prefix_chars"),
                     "request_chars": rec.get("request_chars")})
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


def per_question(rows: list[dict]) -> list[dict]:
    out = []
    for q in sorted({r["q"] for r in rows}, key=lambda x: int(x[1:])):
        rs = [r for r in rows if r["q"] == q]

        def walls(stage):   # #283: a map call waits for its prefix leader's gate first
            return [(r["wall_s"] or 0.0) + (r.get("gate_wait_s") or 0.0) for r in rs if r["stage"] == stage]
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
    return out


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


def _share(hit: int, total: float) -> float | None:
    return round(hit / total, 3) if total else None


def cache_table(rows: list[dict]) -> list[dict]:
    """#283: input tokens, cache-hit tokens and share per stage, then per map prefix role (round 1)."""
    out = []
    groups = [(st, [r for r in rows if r["stage"] == st]) for st in STAGES]
    groups.append(("all", list(rows)))
    roles = sorted({r.get("role") for r in rows if r["stage"] == "map" and r.get("role")})
    groups += [(f"map {role}", [r for r in rows if r["stage"] == "map" and r.get("role") == role]) for role in roles]
    for name, rs in groups:
        if not rs:
            continue
        inp = sum(r.get("input") or 0 for r in rs)
        hit = sum(r.get("hit") or 0 for r in rs)
        waits = [r["gate_wait_s"] for r in rs if r.get("gate_wait_s") is not None]
        out.append({"group": name, "calls": len(rs), "input": inp, "hit": hit, "share": _share(hit, inp),
                    "gate_wait_p50": pct(waits, 50), "gate_wait_max": pct(waits, 100)})
    return out


PROBE_MIN_FOLLOWERS = 5
PROBE_SHARE = 0.50


def probe_rule(rows: list[dict]) -> dict:
    """#283 (TL condition B4): the follower share of the prefix and the gate it decides."""
    fs = [r for r in rows if r["stage"] == "map" and r.get("role") == "follower" and not r.get("leader_cached")
          and r.get("input") and r.get("prefix_chars") and r.get("request_chars")]
    prefix = sum(r["input"] * r["prefix_chars"] / r["request_chars"] for r in fs)
    hit = sum(r.get("hit") or 0 for r in fs)
    share = _share(hit, prefix)
    if len(fs) < PROBE_MIN_FOLLOWERS or share is None:
        gate, why = "done", f"inconclusive: {len(fs)} followers (< {PROBE_MIN_FOLLOWERS})"
    elif share >= PROBE_SHARE:
        gate, why = "first_chunk", f"share {share} >= {PROBE_SHARE}"
    else:
        gate, why = "done", f"share {share} < {PROBE_SHARE}"
    return {"followers": len(fs), "prefix_tokens": round(prefix), "hit_tokens": hit, "share": share,
            "gate": gate, "why": why}


def summary(qs: list[dict]) -> dict:
    crit = [q["critical_s"] for q in qs]
    first = [q["first_evidence_s"] for q in qs if q["first_evidence_s"] is not None]
    claim = [q["first_claim_s"] for q in qs if q.get("first_claim_s") is not None]
    return {"questions": len(qs), "critical_p50": pct(crit, 50), "critical_p90": pct(crit, 90),
            "critical_max": pct(crit, 100), "critical_min": min(crit) if crit else None,
            "first_evidence_p50": pct(first, 50), "first_evidence_p90": pct(first, 90),
            "first_claim_p50": pct(claim, 50), "first_claim_p90": pct(claim, 90),
            "calls": sum(q["calls"] for q in qs), "cut": sum(q["cut"] for q in qs),
            "invalid": sum(q["invalid"] for q in qs), "failed": sum(q["failed"] for q in qs)}


def _f(v) -> str:
    if v is None:
        return "-"
    return f"{v:,.0f}" if isinstance(v, (int, float)) and abs(v) >= 100 else (f"{v:g}" if isinstance(v, float) else str(v))


def markdown(title: str, qs: list[dict], stages: list[dict], s: dict, cache: list[dict] | None = None,
             probe: dict | None = None) -> str:
    lines = [f"### {title}", "",
             f"{s['questions']} questions, {s['calls']} call records: critical path p50 {_f(s['critical_p50'])} s, "
             f"p90 {_f(s['critical_p90'])} s, max {_f(s['critical_max'])} s; first evidence p50 "
             f"{_f(s['first_evidence_p50'])} s, p90 {_f(s['first_evidence_p90'])} s; first claim p50 "
             f"{_f(s.get('first_claim_p50'))} s, p90 {_f(s.get('first_claim_p90'))} s; cut {s['cut']}, invalid "
             f"{s['invalid']}, failed {s['failed']}.", "",
             "| Q | plan s | map calls | slowest map s | re-maps | slowest re-map s | reduce s | critical path s | first evidence s | first claim s | cut |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for q in qs:
        lines.append(f"| {q['q']} | {_f(q['plan_s'])} | {q['map_calls']} | {_f(q['map_max_s'])} | {q['remap_calls']} | "
                     f"{_f(q['remap_max_s'])} | {_f(q['reduce_s'])} | {_f(q['critical_s'])} | "
                     f"{_f(q['first_evidence_s'])} | {_f(q.get('first_claim_s'))} | {q['cut']} |")
    lines += ["", "| Stage | calls | wall p50 s | wall p90 s | wall max s | TTFT p50 s | TTFT p90 s | output p50 | output max | reasoning share |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for st in stages:
        lines.append(f"| {st['stage']} | {st['calls']} | {_f(st['wall_p50'])} | {_f(st['wall_p90'])} | "
                     f"{_f(st['wall_max'])} | {_f(st['ttft_p50'])} | {_f(st['ttft_p90'])} | {_f(st['out_p50'])} | "
                     f"{_f(st['out_max'])} | {_f(st['reasoning_share'])} |")
    if cache:
        lines += ["", "| Calls | n | input tokens | cache-hit tokens | hit share | gate wait p50 s | gate wait max s |",
                  "|---|---|---|---|---|---|---|"]
        for c in cache:
            lines.append(f"| {c['group']} | {c['calls']} | {_f(c['input'])} | {_f(c['hit'])} | {_f(c['share'])} | "
                         f"{_f(c['gate_wait_p50'])} | {_f(c['gate_wait_max'])} |")
    if probe:
        lines += ["", f"Probe rule (plans/0283-prefix-cache.md, B4): {probe['followers']} followers, prefix tokens "
                      f"{_f(probe['prefix_tokens'])}, cache-hit tokens {_f(probe['hit_tokens'])}, share "
                      f"{_f(probe['share'])} -> MAP_PREFIX_GATE={probe['gate']} ({probe['why']})."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("raw", type=Path, help="a run's raw/ folder (or the run folder)")
    ap.add_argument("--questions", default="", help="comma-separated IDs, e.g. Q5,Q10")
    ap.add_argument("--title", default="")
    ap.add_argument("--json", type=Path, default=None, help="also write the numbers as JSON here")
    a = ap.parse_args(argv)
    raw = a.raw / "raw" if (a.raw / "raw").is_dir() else a.raw
    wanted = {x.strip() for x in a.questions.split(",") if x.strip()} or None
    rows = load(raw, wanted)
    if not rows:
        print(f"No call records in {raw}")
        return 1
    qs, stages = per_question(rows), per_stage(rows)
    s = summary(qs)
    cache = cache_table(rows)
    probe = probe_rule(rows) if any(r.get("role") for r in rows) else None
    sys.stdout.write(markdown(a.title or str(raw), qs, stages, s, cache, probe))
    if a.json:
        a.json.write_text(json.dumps({"summary": s, "questions": qs, "stages": stages, "cache": cache,
                                      "probe": probe}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
