"""#292: v5.2 vs v7, per question, from two eval reports (0 calls).
  python analyze.py <v7 report.json> <v5.2 report.json> [Q5,Q8,Q22,Q24] > compare.md
Per question and version: first sentence, sentence (claim) count, adjacent / gap counts, claims without a citation,
flags (final answer, after the code checks), part gaps, comparison_missing, reduce output / reasoning tokens, the
reduce call's cost (off-peak and peak, as priced by eval_run), wall time and tokens/s from the saved record."""
import json
import sys
from pathlib import Path

WATCH = ("part_gap", "comparison_missing", "number_not_found", "no_citation", "outside_matrix")


def load(p):
    return {r["id"]: r for r in json.load(open(p, encoding="utf-8"))["questions"]}


def reduce_row(r):
    rows = [x for x in (r.get("cost") or {}).get("rows") or [] if x.get("type") == "reduce"]
    return rows[0] if rows else {}


def record(report: Path, r):
    row = reduce_row(r)
    f = row.get("file")
    for d in (report.parent / "raw", report.parent / ".." / "raw"):
        if f and (d / f).is_file():
            return json.loads((d / f).read_text(encoding="utf-8"))
    return {}


def stats(report: Path, r) -> dict:
    a = r.get("answer") or {}
    claims = a.get("claims") or []
    flags: dict = {}
    for x in claims + (a.get("adjacent") or []) + (a.get("gaps") or []):
        for f in x.get("flags") or []:
            flags[f] = flags.get(f, 0) + 1
    red = r.get("reduce") or {}
    u = red.get("usage") or {}
    rec = record(report, r)
    cost = reduce_row(r).get("cost") or {}
    return {"version": red.get("version"), "first": claims[0]["text"] if claims else "(no claim)",
            "claims": len(claims), "adjacent": len(a.get("adjacent") or []), "gaps": len(a.get("gaps") or []),
            "uncited": sum(not x.get("chunk_ids") for x in claims),
            "multi_chunk": sum(len(x.get("chunk_ids") or []) > 1 for x in claims),
            "flags": flags, "watch": {k: flags.get(k, 0) for k in WATCH},
            "comparison_missing": len(red.get("comparison_missing") or []),
            "out": u.get("output_tokens"), "reasoning": u.get("reasoning_tokens"), "in": u.get("input_tokens"),
            "usd": cost.get("usd"), "usd_peak": cost.get("usd_peak"), "period": cost.get("period"),
            "wall": rec.get("wall_s"), "tps": rec.get("tokens_per_s"), "behavior": r.get("answer_behavior") or a.get("behavior"),
            "stop": red.get("stop_reason"), "how": red.get("how"), "texts": [x["text"] for x in claims]}


def main(new_p, old_p, qs):
    new, old = load(new_p), load(old_p)
    out = ["| Q | version | claims | multi-chunk | uncited | adjacent | gaps | part_gap | comparison_missing | "
           "number_not_found | outside_matrix | reduce in / out / reasoning | reduce $ (peak $) | wall s | tok/s |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    detail = []
    for q in qs:
        for p, rep in ((old_p, old), (new_p, new)):
            s = stats(Path(p), rep[q])
            w = s["watch"]
            out.append(f"| {q} | {s['version']} | {s['claims']} | {s['multi_chunk']} | {s['uncited']} | {s['adjacent']} | "
                       f"{s['gaps']} | {w['part_gap']} | {s['comparison_missing']} | {w['number_not_found']} | "
                       f"{w['outside_matrix']} | {s['in']} / {s['out']} / {s['reasoning']} | "
                       f"{s['usd']} ({s['usd_peak']}, {s['period']}) | {s['wall']} | {s['tps']} |")
            detail.append(f"\n### {q} {s['version']} ({s['behavior']}, stop {s['stop']}, {s['how']})\n"
                          f"Flags: {s['flags'] or 'none'}\n")
            detail += [f"{n + 1}. {t}" for n, t in enumerate(s["texts"])]
    print("\n".join(out + ["", "## Claims (final answer, after the code checks)"] + detail))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "Q5,Q8,Q22,Q24").split(","))
