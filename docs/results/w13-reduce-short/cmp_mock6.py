"""#284 step 4: mock run with REDUCE_PROMPT=v6 vs clean main (v5.2): per question status, retrieved chunks, behavior,
cell labels, and per claim / adjacent item (part_id, chunk ids). The text differs by design (code renders it), so it is
not compared here; render_check.py checks it item by item.
  python cmp_mock6.py <new report.json> <main report.json>"""
import json
import sys


def load(p):
    return {r["id"]: r for r in json.load(open(p, encoding="utf-8"))["questions"]}


def cells(r):
    cs = (r.get("matrix") or {}).get("cells") or {}
    return {k: (v.get("label"), v.get("effective_label")) if isinstance(v, dict) else v
            for k, v in cs.items()} if isinstance(cs, dict) else cs


def items(r):
    a = r.get("answer") or {}
    return [(f, c.get("part_id"), tuple(c.get("chunk_ids") or [])) for f in ("claims", "adjacent")
            for c in a.get(f) or []]


new, old = load(sys.argv[1]), load(sys.argv[2])
same = 0
for q in old:
    A, B = new[q], old[q]
    d = [k for k in ("status", "chunk_ids", "map_behavior", "answer_behavior") if A.get(k) != B.get(k)]
    if cells(A) != cells(B):
        d.append("cells")
    if items(A) != items(B):
        d.append("claims (part, chunk ids)")
    if d:
        print(q, d)
    else:
        same += 1
print(f"equal (text not compared) {same}/{len(old)}")
