"""#292: v5.2 vs v7 vs v8, per question, from eval reports (0 calls).
  python analyze.py <label>=<report.json> [<label>=<report.json> ...] [--q Q5,Q8,Q22,Q24] > compare.md
The first report is the baseline (v5.2) for the flag rules. Per question and report: sentence (claim) count, first
sentence cited, sentences over 45 words / list sentences (3+ items joined by ";" or 4+ figures), adjacent, gaps,
computability box entries, flags, reduce output / reasoning tokens, the reduce call's cost, wall time, tokens/s; then
the v8 pass rule (plan, "v8 amendment") and every claim and box text."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
WATCH = ("part_gap", "comparison_missing", "number_not_found")
FIG = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?\s*(?:%|percent|billion|million|trillion|bn)?", re.I)


def load(p):
    return {r["id"]: r for r in json.load(open(p, encoding="utf-8"))["questions"]}


def reduce_row(r):
    rows = [x for x in (r.get("cost") or {}).get("rows") or [] if x.get("type") == "reduce"]
    return rows[0] if rows else {}


def record(report: Path, r):
    f = reduce_row(r).get("file")
    d = report.parent / "raw"
    return json.loads((d / f).read_text(encoding="utf-8")) if f and (d / f).is_file() else {}


def figures(text: str) -> int:
    from cee.answer.validate import figures as figs
    return len(figs(text))


def is_list(text: str) -> bool:
    return text.count(";") >= 2 or figures(text) >= 4


def stats(report: Path, r) -> dict:
    a = r.get("answer") or {}
    claims = a.get("claims") or []
    box = a.get("computations") or []
    flags: dict = {}
    for x in claims + (a.get("adjacent") or []) + (a.get("gaps") or []) + box:
        for f in x.get("flags") or []:
            flags[f] = flags.get(f, 0) + 1
    red = r.get("reduce") or {}
    u = red.get("usage") or {}
    rec = record(report, r)
    cost = reduce_row(r).get("cost") or {}
    words = [len(c["text"].split()) for c in claims]
    return {"version": red.get("version"), "claims": len(claims), "first_cited": bool(claims and claims[0].get("chunk_ids")),
            "long": sum(w > 45 for w in words), "lists": sum(is_list(c["text"]) for c in claims),
            "max_words": max(words or [0]), "adjacent": len(a.get("adjacent") or []), "gaps": len(a.get("gaps") or []),
            "box": len(box), "flags": flags, "watch": {k: flags.get(k, 0) for k in WATCH},
            "comparison_missing": len(red.get("comparison_missing") or []),
            "out": u.get("output_tokens"), "reasoning": u.get("reasoning_tokens") or 0, "in": u.get("input_tokens"),
            "usd": cost.get("usd"), "usd_peak": cost.get("usd_peak"), "period": cost.get("period"),
            "wall": rec.get("wall_s"), "tps": rec.get("tokens_per_s"), "behavior": a.get("behavior"),
            "stop": red.get("stop_reason"), "how": red.get("how"),
            "texts": [c["text"] for c in claims], "box_texts": [(c["text"], c.get("chunk_ids")) for c in box]}


def verdict(s: dict, base: dict) -> str:
    why = []
    if not s["first_cited"]:
        why.append("sentence 1 uncited")
    if s["claims"] > 5:
        why.append(f"{s['claims']} sentences")
    if s["long"]:
        why.append(f"{s['long']} over 45 words")
    if s["lists"]:
        why.append(f"{s['lists']} list sentences")
    new = sorted(set(s["flags"]) - set(base["flags"]))
    if new:
        why.append(f"new flag kinds {new}")
    for k in WATCH:
        if s["watch"][k] > base["watch"][k]:
            why.append(f"{k} {base['watch'][k]} -> {s['watch'][k]}")
    if s["comparison_missing"] > base["comparison_missing"]:
        why.append("comparison_missing up")
    if s["stop"] not in ("tool_calls", "stop", None) or s["how"] in ("invalid", "failed", "cut"):
        why.append(f"output {s['how']} / {s['stop']}")
    return "pass" if not why else "fail: " + "; ".join(why)


def main(args):
    qs = "Q5,Q8,Q22,Q24".split(",")
    if "--q" in args:
        qs = args[args.index("--q") + 1].split(",")
        args = [a for a in args if a not in ("--q", ",".join(qs))]
    runs = [(lab, Path(p), load(p)) for lab, p in (a.split("=", 1) for a in args)]
    out = ["| Q | run | version | sentences | sentence 1 cited | >45 words | list sentences | box | adjacent | gaps | "
           "part_gap | comparison_missing | number_not_found | reduce out / reasoning | reduce $ (peak $) | wall s | tok/s | rule |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    detail = []
    for q in qs:
        base = stats(runs[0][1], runs[0][2][q])
        for lab, p, rep in runs:
            s = stats(p, rep[q])
            w = s["watch"]
            rule = "-" if lab == runs[0][0] else verdict(s, base)
            out.append(f"| {q} | {lab} | {s['version']} | {s['claims']} | {'yes' if s['first_cited'] else 'no'} | {s['long']} | "
                       f"{s['lists']} | {s['box']} | {s['adjacent']} | {s['gaps']} | {w['part_gap']} | {s['comparison_missing']} | "
                       f"{w['number_not_found']} | {s['out']} / {s['reasoning']} | {s['usd']} ({s['usd_peak']}, {s['period']}) | "
                       f"{s['wall']} | {s['tps']} | {rule} |")
            detail.append(f"\n### {q} {lab} ({s['version']}, {s['behavior']}, stop {s['stop']}, {s['how']})\n"
                          f"Flags: {s['flags'] or 'none'}\n")
            detail += [f"{n + 1}. {t}" for n, t in enumerate(s["texts"])]
            detail += [f"- Computability box: {t} (cites {', '.join(ids or [])})" for t, ids in s["box_texts"]]
    print("\n".join(out + ["", "## Claims (final answer, after the code checks)"] + detail))


if __name__ == "__main__":
    main(sys.argv[1:])
