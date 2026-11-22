"""#272 step 7: mock run after the change vs before (clean main): per question status, behavior, answer claims
and their chunk ids, cell labels. Call ids / counts are expected to change (one call per cell)."""
import json, sys
def L(p): return {r["id"]: r for r in json.load(open(p, encoding="utf-8"))["questions"]}
def cells(r):
    m = r.get("matrix") or {}
    cs = m.get("cells") or {}
    return {k: (v.get("label"), v.get("effective_label")) if isinstance(v, dict) else v for k, v in cs.items()} if isinstance(cs, dict) else cs
def claims(r):
    a = r.get("answer") or {}
    return [(c.get("text"), c.get("chunk_ids")) for c in (a.get("claims") or []) + (a.get("adjacent") or [])]
new, old = L(sys.argv[1]), L(sys.argv[2])
same = 0
for q in old:
    A, B = new[q], old[q]
    d = {k: (A.get(k), B.get(k)) for k in ("status", "chunk_ids", "map_behavior", "answer_behavior") if A.get(k) != B.get(k)}
    if cells(A) != cells(B): d["cells"] = "differ"
    if claims(A) != claims(B): d["claims"] = "differ"
    if d: print(q, {k: (v if k in ("cells", "claims") else "differ") for k, v in d.items()})
    else: same += 1
print(f"identical {same}/{len(old)}; map calls before {sum(len(r.get('map_calls') or []) if isinstance(r.get('map_calls'), list) else (r.get('map_calls') or 0) for r in old.values())} after {sum(len(r.get('map_calls') or []) if isinstance(r.get('map_calls'), list) else (r.get('map_calls') or 0) for r in new.values())}")
