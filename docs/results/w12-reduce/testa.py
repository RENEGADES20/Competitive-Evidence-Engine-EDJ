"""#275 test A (plans/0275-reduce-speed.md steps 10-11; 0 calls): compare reduce-only configs on the six questions
from their runs (report.json + raw/ reduce records), and apply the fixed choice rule.

  python testa.py C1=<run dir> R1=<run dir>[,<run dir>] R2=<run dir>     (C1 = the #272 baseline; a config may list
                                                                          several run dirs, e.g. the Q5 probe + the rest)
"""
import json
import statistics as st
import sys
from pathlib import Path

SIX = ["Q5", "Q10", "Q19", "Q21", "Q24", "Q26"]
FLAGS = ("part_gap", "comparison_missing", "why_line_missing", "number_not_found", "date_mismatch", "outside_matrix")
SUPERSEDE = {}


def load(dirs: list[Path]) -> tuple[dict, dict]:
    qs, recs = {}, {}
    for d in dirs:
        for q in json.loads((d / "report.json").read_text(encoding="utf-8"))["questions"]:
            if q["id"] in SIX and (q.get("answer") or q.get("reduce", {}).get("how") not in (None, "cap")):
                qs[q["id"]] = q
        for p in (d / "raw").glob("Q*-reduce-*.json"):
            r = json.loads(p.read_text(encoding="utf-8"))
            if r.get("question_id") in SIX:
                recs.setdefault(r["question_id"], []).append(r)
    return qs, recs


def crit(d: Path, qid: str) -> tuple[float, float]:
    """(critical path without the reduce, plan + slowest map + slowest re-map) from the run's raw records."""
    rs = [json.loads(p.read_text(encoding="utf-8")) | {"_n": p.name} for p in (d / "raw").glob(f"{qid}-*.json")]

    def w(kind):
        return [r.get("wall_s") or 0 for r in rs if f"{qid}-{kind}" in r["_n"]]
    plan, maps, remaps = sum(w("plan-")), w("map."), w("remap.")
    return plan + (max(maps) if maps else 0) + (max(remaps) if remaps else 0), plan


def flags(q: dict) -> dict:
    a = q.get("answer") or {}
    out = {f: 0 for f in FLAGS}
    for x in (a.get("claims") or []) + (a.get("adjacent") or []) + (a.get("gaps") or []):
        for f in x.get("flags") or []:
            if f in out:
                out[f] += 1
    return out


def summarize(name: str, dirs: list[Path]) -> dict:
    qs, recs = load(dirs)
    rows = []
    for qid in SIX:
        q, rec = qs.get(qid, {}), (recs.get(qid) or [{}])[-1]
        pre = max(crit(d, qid)[0] for d in dirs if (d / "raw").glob(f"{qid}-*.json"))
        u = rec.get("usage") or {}
        out, reas = u.get("output_tokens") or 0, u.get("reasoning_tokens") or 0
        wall = rec.get("wall_s")
        rows.append({"q": qid, "reduce_s": wall, "ttft_s": rec.get("ttft_s"), "first_claim_s": rec.get("first_claim_s"),
                     "end_s": round(pre + (wall or 0), 1), "claim_at_s": round(pre + rec["first_claim_s"], 1)
                     if rec.get("first_claim_s") is not None else None,
                     "answer_tokens": out - reas, "output": out, "cut": rec.get("stop_reason") == "length",
                     "invalid": bool(rec.get("invalid")) and not rec.get("failed_call"),
                     "failed": bool(rec.get("failed_call")), "behavior": q.get("behavior"),
                     "expected": q.get("expected_behavior_effective") or q.get("expected_behavior"),
                     "flags": flags(q), "shown_not_final": (q.get("reduce") or {}).get("stream_items", {}).get("shown_not_final"),
                     "request_version": rec.get("request_version"), "prompt": rec.get("reduce_version")})
    return {"name": name, "rows": rows}


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else None


def main() -> int:
    cfgs = []
    for arg in sys.argv[1:]:
        name, dirs = arg.split("=", 1)
        cfgs.append(summarize(name, [Path(d) for d in dirs.split(",")]))
    print("| Config | reduce wall p50 / max s | TTFT p50 s | first claim p50 s (from reduce start) | end to end p50 / max s | "
          "first claim on page p50 s | answer tokens p50 / sum | cut / invalid / failed | behavior = expected | "
          + " | ".join(FLAGS) + " |")
    print("|" + "---|" * (9 + len(FLAGS)))
    for c in cfgs:
        r = c["rows"]
        fl = {f: sum(x["flags"][f] for x in r) for f in FLAGS}
        c["fl"] = fl
        c["ok"] = sum(x["behavior"] == x["expected"] for x in r)
        c["bad"] = sum(x["cut"] for x in r), sum(x["invalid"] for x in r), sum(x["failed"] for x in r)
        c["wall_med"] = med([x["reduce_s"] for x in r])
        print(f"| {c['name']} | {c['wall_med']} / {max((x['reduce_s'] or 0) for x in r)} | {med([x['ttft_s'] for x in r])} | "
              f"{med([x['first_claim_s'] for x in r])} | {med([x['end_s'] for x in r])} / {max(x['end_s'] for x in r)} | "
              f"{med([x['claim_at_s'] for x in r])} | {med([x['answer_tokens'] for x in r])} / "
              f"{sum(x['answer_tokens'] for x in r):,} | {' / '.join(map(str, c['bad']))} | {c['ok']}/6 | "
              + " | ".join(str(fl[f]) for f in FLAGS) + " |")
    print()
    for c in cfgs:
        print(f"{c['name']} per question: " + "; ".join(
            f"{x['q']} reduce {x['reduce_s']} s, first claim {x['first_claim_s']}, answer {x['answer_tokens']}, "
            f"{x['behavior']}, shown_not_final {x['shown_not_final']}" for x in c["rows"]))
    base = next((c for c in cfgs if c["name"] == "C1"), None)
    if base is None:
        return 0
    eligible = {}
    for c in cfgs:
        if c is base:
            continue
        why = []
        if any(c["bad"]):
            why.append(f"cut/invalid/failed {c['bad']}")
        if c["ok"] < base["ok"]:
            why.append(f"behavior {c['ok']}/6 < C1 {base['ok']}/6")
        for f in FLAGS:
            if c["fl"][f] > base["fl"][f]:
                why.append(f"{f} {c['fl'][f]} > C1 {base['fl'][f]}")
        snf = [x["shown_not_final"] for x in c["rows"] if x["shown_not_final"]]
        if snf:
            why.append(f"shown_not_final {snf} (check: dedupe only)")
        eligible[c["name"]] = not [w for w in why if not w.startswith("shown_not_final")]
        print(f"{c['name']}: {'ELIGIBLE' if eligible[c['name']] else 'NOT eligible'}" + (f" ({'; '.join(why)})" if why else ""))
    r1 = next((c for c in cfgs if c["name"] == "R1"), None)
    r2 = next((c for c in cfgs if c["name"] == "R2"), None)
    if r2 and eligible.get("R2") and r1 and r2["wall_med"] <= 0.9 * r1["wall_med"]:
        choice = "R2"
    elif r1 and eligible.get("R1"):
        choice = "R1"
    elif r2 and eligible.get("R2") and not eligible.get("R1"):
        choice = "R2"
    else:
        choice = None
    print(f"rule (step 11): R2 needs eligible and median reduce wall <= 0.9 x R1 "
          f"({r2['wall_med'] if r2 else '-'} vs 0.9 x {r1['wall_med'] if r1 else '-'}); chosen: {choice or 'none (keep low)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
