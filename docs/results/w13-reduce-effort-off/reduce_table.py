"""#295 step 8: reduce wall time, tokens, tokens/s and cost per question for three sets of saved reduce records (0 calls):
v8-off (this run's raw folder), v5.2 (#272 test B raw folder), v8-low (#292 g8-low raw folder, Q5 Q8 Q22 Q24).
  python reduce_table.py <v8-off raw dir> <v5.2 raw dir> <v8-low raw dir> > reduce-table.md   (PYTHONPATH=<wt>/src)"""
import json
import statistics
import sys
from pathlib import Path

from cee.answer import cost as C


def load(folder):
    out = {}
    for p in sorted(Path(folder).glob("*-reduce-*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        u = d.get("usage") or {}
        c = C.price_call(d.get("provider"), d.get("model"), u, at=d.get("at"), wall_s=d.get("wall_s"),
                         naive_tz="America/Chicago")
        out[d["question_id"]] = {"file": p.name, "version": d.get("reduce_version"), "req": d.get("request_version"),
                                 "wall": d.get("wall_s"), "tps": d.get("tokens_per_s"), "in": u.get("input_tokens"),
                                 "out": u.get("output_tokens"), "reason": u.get("reasoning_tokens"),
                                 "usd": c.get("usd"), "usd_peak": c.get("usd_peak"), "period": c.get("period"),
                                 "failed": bool(d.get("failed_call") or d.get("invalid"))}
    return out


def pct(xs, p):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 1)


def summary(name, rows, qids):
    rs = [rows[q] for q in qids if q in rows]
    walls = [r["wall"] for r in rs if not r["failed"]]
    usd = sum(r["usd"] or 0 for r in rs)
    peak = sum(r["usd_peak"] or 0 for r in rs)
    periods = sorted({r["period"] for r in rs if r["period"]})
    return (f"| {name} | {len(rs)} | {pct(walls, 0.5)} | {pct(walls, 0.9)} | {max(walls) if walls else '-'} | "
            f"{pct([r['tps'] for r in rs], 0.5)} | {sum(r['out'] or 0 for r in rs):,} | {usd:.3f} | {peak:.3f} | "
            f"{', '.join(periods)} | {sum(r['failed'] for r in rs)} |")


off, v52, low = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
all30 = [f"Q{i}" for i in range(1, 31)]
four = ["Q5", "Q8", "Q22", "Q24"]
print("| Set | Records | Wall p50 s | Wall p90 s | Max s | Tokens/s p50 | Output tokens | USD as run | USD at peak | Period | Failed |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
print(summary("v8-off (this run), Q1-Q30", off, all30))
print(summary("v5.2 (#272 test B), Q1-Q30", v52, all30))
print(summary("v8-off, Q5 Q8 Q22 Q24", off, four))
print(summary("v8-low (#292), Q5 Q8 Q22 Q24", low, four))
print(summary("v5.2 (#272), Q5 Q8 Q22 Q24", v52, four))
print()
print("| Q | v8-off version / request | wall s | out / reasoning | tok/s | USD (period) | v5.2 wall s | v5.2 out | v8-low wall s |")
print("|---|---|---|---|---|---|---|---|---|")
for q in all30:
    o, b, l = off.get(q, {}), v52.get(q, {}), low.get(q, {})
    print(f"| {q} | {o.get('version')} / {o.get('req')} | {o.get('wall')} | {o.get('out')} / {o.get('reason')} | "
          f"{o.get('tps')} | {o.get('usd') if o.get('usd') is None else round(o['usd'], 4)} ({o.get('period')})"
          f"{' FAILED' if o.get('failed') else ''} | {b.get('wall')} | {b.get('out')} | {l.get('wall', '-')} |")
