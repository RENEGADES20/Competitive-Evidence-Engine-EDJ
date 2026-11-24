"""#295 step 5: read a count-phase report (--max-calls 0): records reused, plan / map / re-map calls the cap held back,
new reduce keys (0 calls).   python count.py <report.json>"""
import json
import sys
from collections import Counter

r = json.load(open(sys.argv[1], encoding="utf-8"))
qs = r["questions"]


def n(v):
    return v if isinstance(v, int) else len(v or [])


how = Counter((q.get("reduce") or {}).get("how") for q in qs)
new_reduce = [q["id"] for q in qs if (q.get("reduce") or {}).get("how") == "cap"]
print("meta: reused", r["meta"].get("reused"), "| real_calls", r["meta"].get("real_calls"),
      "| calls_reserved", r["meta"].get("calls_reserved"))
print("map calls served", sum(n(q.get("map_calls")) for q in qs), "| re-maps", sum(n(q.get("remap_calls")) for q in qs),
      "| map calls held by the cap", sum(n(q.get("map_capped_calls")) for q in qs),
      "| plans not from the cache", [q["id"] for q in qs if (q.get("plan") or {}).get("source") not in ("model",)])
print("reduce how", dict(how))
print("new reduce keys (held by the cap):", len(new_reduce), " ".join(new_reduce))
print("reduce reused:", " ".join(q["id"] for q in qs if (q.get("reduce") or {}).get("how") == "cached"))
