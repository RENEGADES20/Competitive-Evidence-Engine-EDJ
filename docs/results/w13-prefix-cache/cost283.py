"""#283: cost of a run's 30 answers, like for like, from the raw records' usage (0 calls).

For each run: every call record the answers used (plan, map, re-map, reduce), priced three ways from
config/pricing.yaml: as billed (each call at its own period, the cee.answer.cost rule: completion time in UTC),
all off-peak, all peak. Broken down by stage, the map split into input cache-hit, input cache-miss and output.
  python cost283.py <run raw dir> [<run raw dir> ...]      (PYTHONPATH=<repo>/src)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from cee.answer import cost

NAME = re.compile(r"^(Q\d+)-(plan|reduce|map\.[^-]+|remap\.[^-]+)-[0-9a-f]+\.json$")


def rates(model: str) -> dict:
    return cost.load_prices()["providers"]["deepseek"]["models"][model]


def run(raw: Path) -> dict:
    parts: dict[str, dict[str, float]] = {}
    tot = {"billed": 0.0, "off_peak": 0.0, "peak": 0.0, "peak_calls": 0, "off_peak_calls": 0, "calls": 0}
    for p in sorted(raw.glob("Q*.json")):
        m = NAME.match(p.name)
        if not m:
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        u = rec.get("usage") or {}
        stage = m.group(2).split(".", 1)[0]
        model = rec.get("model") or "deepseek-v4-pro"
        priced = cost.price_call("deepseek", model, u, at=rec.get("at"), wall_s=rec.get("wall_s"),
                                 finished_at=rec.get("finished_at"), naive_tz="America/Chicago")
        t = cost.tokens(u)
        r = rates(model)
        tot["calls"] += 1
        tot["billed"] += priced["usd"] or 0.0
        tot["peak_calls" if priced.get("period") == "peak" else "off_peak_calls"] += 1
        for tier in ("off_peak", "peak"):
            k = r[tier]
            pieces = {"input_hit": t["cache_hit_tokens"] * k["input_cache_hit"] / 1e6,
                      "input_miss": t["cache_miss_tokens"] * k["input_cache_miss"] / 1e6,
                      "output": t["output_tokens"] * k["output"] / 1e6}
            for name, usd in pieces.items():
                key = f"{stage} {name}"
                parts.setdefault(key, {"off_peak": 0.0, "peak": 0.0, "tokens": 0})
                parts[key][tier] += usd
                tot[tier] += usd
            if tier == "off_peak":
                for name, n in (("input_hit", t["cache_hit_tokens"]), ("input_miss", t["cache_miss_tokens"]),
                                ("output", t["output_tokens"])):
                    parts[f"{stage} {name}"]["tokens"] += n
    return {"total": tot, "parts": parts}


def main(argv: list[str]) -> int:
    for a in argv:
        r = run(Path(a))
        t = r["total"]
        print(f"## {a}\n{t['calls']} calls ({t['off_peak_calls']} off-peak, {t['peak_calls']} peak as billed): "
              f"billed ${t['billed']:.2f} (${t['billed'] / 30:.3f}/q); all off-peak ${t['off_peak']:.2f} "
              f"(${t['off_peak'] / 30:.3f}/q); all peak ${t['peak']:.2f} (${t['peak'] / 30:.3f}/q)")
        print("| part | tokens | off-peak $ | peak $ |\n|---|---|---|---|")
        for k, v in sorted(r["parts"].items()):
            print(f"| {k} | {v['tokens']:,} | {v['off_peak']:.2f} | {v['peak']:.2f} |")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
