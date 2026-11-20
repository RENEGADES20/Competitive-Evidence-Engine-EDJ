"""Price a folder of saved model-call records (#248): an eval run's raw/ folder, the cache, or a
results folder such as docs/results/0242-deepseek-raw. 0 calls; prices from config/pricing.yaml.

  python scripts/eval_cost.py docs/results/0242-deepseek-raw --naive-tz America/Chicago
  python scripts/eval_cost.py .eval-runs/<run>/raw --json cost.json

Each record is priced from its `usage` and completion time (`at` + `wall_s`, or `finished_at`), peak or
off-peak in UTC for providers with a peak window (deepseek). A record whose `at` has no UTC offset
(every record written before #248; they were written in America/Chicago) needs --naive-tz; without it
the script names the file and exits 2. Prints one line per call and the totals: the cost at the time
each call ran and the full (peak) price.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cee.answer import cost as C  # noqa: E402


def call_type(name: str) -> str:
    for key, kind in (("-plan-", "plan"), ("-reduce-", "reduce"), ("-remap.", "remap"), ("-map.", "map")):
        if key in name:
            return kind
    return "answer"


def records(folder: Path) -> list[tuple[Path, dict]]:
    out = []
    for f in sorted(folder.rglob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(rec, dict) and "provider" in rec and ("usage" in rec or rec.get("failed_call")):
            out.append((f, rec))
    return out


def price(folder: Path, naive_tz: str | None) -> tuple[list[dict], dict]:
    rows = []
    for f, rec in records(folder):
        c = C.price_call(rec["provider"], rec.get("model"), rec.get("usage"), at=rec.get("at"),
                         wall_s=rec.get("wall_s"), finished_at=rec.get("finished_at"), naive_tz=naive_tz)
        rows.append({"type": call_type(f.name), "file": str(f.relative_to(folder)), "new": True, "cost": c})
    return rows, C.summarize(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", type=Path, help="folder of saved records (searched recursively)")
    ap.add_argument("--naive-tz", help="zone of records whose `at` has no UTC offset, e.g. America/Chicago or -06:00")
    ap.add_argument("--json", type=Path, help="also write the rows and totals to this file")
    args = ap.parse_args(argv)
    try:
        C.parse_tz(args.naive_tz)
        rows, total = price(args.folder, args.naive_tz)
    except C.CostError as e:
        naive = [str(f.relative_to(args.folder)) for f, r in records(args.folder) if C.is_naive(r.get("at"))]
        print(f"{e}" + (f" (first such record: {naive[0]})" if naive else ""), file=sys.stderr)
        return 2
    if args.naive_tz:
        print(f"Naive record times read as {args.naive_tz}.")
    for r in rows:
        c = r["cost"]
        usd = "-" if c["usd"] is None else f"{c['usd']:.4f}"
        print(f"{r['file']:<60} {r['type']:<7} {c['status']:<9} {c['period'] or '-':<9} in {c['input_tokens']:>8} "
              f"out {c['output_tokens']:>7} ${usd}")
    print(f"\n{total['calls']} calls; tokens in {total['input_tokens']:,} (cache hit {total['cache_hit_tokens']:,}), "
          f"out {total['output_tokens']:,}; ${total['usd']:.4f} as run (off-peak {total['off_peak_calls']}, peak "
          f"{total['peak_calls']}); ${total['usd_peak']:.4f} at full (peak) price; unpriced {total['unpriced_calls']}, "
          f"no usage {total['no_usage_calls']}")
    if args.json:
        args.json.write_text(json.dumps({"folder": str(args.folder), "naive_tz": args.naive_tz, "total": total,
                                         "rows": rows}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
