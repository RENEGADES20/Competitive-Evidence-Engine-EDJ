"""#275 (plans/0275-reduce-speed.md section 6, TL condition 4; 0 calls): read a count phase's report.json and show,
per question, whether every plan / map / re-map record was reused and what the reduce would do.

  python countcheck.py <count run dir> [<second count run dir>]   (two dirs: compare reduce files and map lists)

A count phase runs with --max-calls 0, so any call that is not saved shows as capped: the plan as a non-"cached"
plan_origin, a map or re-map call in map_capped_calls, the reduce as how == "cap" (with its file and message sha).
"""
import json
import sys
from pathlib import Path


def load(run: Path) -> dict:
    rep = json.loads((run / "report.json").read_text(encoding="utf-8"))
    return {q["id"]: q for q in rep["questions"]}


def maps(run: Path, qid: str) -> list[str]:
    return sorted(p.name for p in (run / "raw").glob(f"{qid}-*map.*.json"))


def main() -> int:
    runs = [Path(a) for a in sys.argv[1:]]
    qs = load(runs[0])
    bad, reduce_new, reduce_cached, other = [], [], [], []
    for qid, q in qs.items():
        origin = str(q.get("plan_origin") or "")
        capped = q.get("map_capped_calls") or []
        red = q.get("reduce") or {}
        if not (origin.startswith("cached") or origin.startswith("no planner call")) or capped:
            bad.append((qid, origin[:60], capped))
        how = red.get("how")
        (reduce_new if how == "cap" else reduce_cached if how == "cached" else other).append(
            (qid, how, red.get("file"), red.get("message_sha")))
    print(f"{runs[0].name}: {len(qs)} questions; plan / map / re-map not reused: {len(bad)} {bad}")
    print(f"reduce new (capped in count): {len(reduce_new)}; reduce reused: {len(reduce_cached)}; other: {other}")
    for r in reduce_new:
        print("  new reduce", *r)
    if len(runs) == 2:
        qs2 = load(runs[1])
        for qid in qs:
            a, b = qs[qid].get("reduce") or {}, qs2.get(qid, {}).get("reduce") or {}
            m1, m2 = maps(runs[0], qid), maps(runs[1], qid)
            print(f"{qid}: reduce file {a.get('file')} vs {b.get('file')} (same {a.get('file') == b.get('file')}); "
                  f"message sha {a.get('message_sha')} vs {b.get('message_sha')}; map files {len(m1)} vs {len(m2)} "
                  f"(same {m1 == m2})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
