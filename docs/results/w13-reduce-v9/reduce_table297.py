"""#297 step 7: reduce wall time, tokens, tokens/s and cost per question for three sets of saved reduce records (0 calls):
v9-low (this run's raw folder, Q26 Q27 reused v5.2 records come from the #272 folder), v5.2 (#272 test B raw folder),
v8-off (#295 g3-run raw folder). From w13-reduce-effort-off/reduce_table.py.
  python reduce_table297.py <v9 raw dir> <v5.2 raw dir> <v8-off raw dir> > reduce-table.md   (PYTHONPATH=<wt>/src)"""
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


v9, v52, off = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
all30 = [f"Q{i}" for i in range(1, 31)]
new28 = [q for q in all30 if q not in ("Q26", "Q27")]
v9_30 = {**{q: v52[q] for q in ("Q26", "Q27") if q in v52}, **v9}   # Q26, Q27: the reused #272 v5.2-low records
print("| Set | Records | Wall p50 s | Wall p90 s | Max s | Tokens/s p50 | Output tokens | USD as run | USD at peak | Period | Failed |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
print(summary("v9-low (this run), 28 new calls", v9, new28))
print(summary("v9-low, Q1-Q30 (Q26, Q27 reused v5.2-low)", v9_30, all30))
print(summary("v5.2-low (#272 test B), Q1-Q30", v52, all30))
print(summary("v5.2-low (#272), the same 28", v52, new28))
print(summary("v8-off (#295), its 24 new calls", off, all30))
print()
print("| Q | v9 version / request | wall s | out / reasoning | tok/s | USD (period) | v5.2 wall s | v5.2 out / reasoning | v8-off wall s | v8-off out |")
print("|---|---|---|---|---|---|---|---|---|---|")
for q in all30:
    o, b, f = v9.get(q, {}), v52.get(q, {}), off.get(q, {})
    print(f"| {q} | {o.get('version')} / {o.get('req')} | {o.get('wall')} | {o.get('out')} / {o.get('reason')} | "
          f"{o.get('tps')} | {o.get('usd') if o.get('usd') is None else round(o['usd'], 4)} ({o.get('period')})"
          f"{' FAILED' if o.get('failed') else ''} | {b.get('wall')} | {b.get('out')} / {b.get('reason')} | "
          f"{f.get('wall', '-')} | {f.get('out', '-')} |")
