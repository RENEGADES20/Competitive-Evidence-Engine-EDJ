# Not runnable after #289: the code it drives or imports was removed; kept as the record of how the evidence was made.
"""#285 G0 (TL ruling): upper bound of map calls saved on the #272 test-B records under the tightened serving rules
(B3 positive rule on aspect text, sub-question text and question; metric tag and kind; B2 registry status quoted).
Every eligible cell is assumed fully covered by facts. 0 calls. Run with PYTHONPATH=<worktree>/src.
  python g0_upper_bound.py [cache-a dir]"""
import glob
import json
import os
import sys

import yaml

from cee import facts
from cee.retrieve.planner import Aspect, SubQuestion

CACHE = sys.argv[1] if len(sys.argv) > 1 else r"D:\ALLPROJECTS\EDJ\cache\ev272\cache-a"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
qs = yaml.safe_load(open(os.path.join(ROOT, "evals", "questions.yaml"), encoding="utf-8"))
qs = qs.get("questions", qs) if isinstance(qs, dict) else qs
text = {q["id"]: q["text"] for q in qs}
plans, calls = {}, {}
for f in glob.glob(os.path.join(CACHE, "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    if "-plan-" in f:
        plans[d["question_id"]] = d["raw"]["aspects"]
    elif ("-map." in f or "-remap." in f) and d.get("model") == "deepseek-v4-pro" \
            and d.get("request_version") == "ds-strict-2-map-low-c128000-s1":
        for c in d["cells"]:
            calls.setdefault((d["question_id"], c), []).append(d["call_id"])
total = sum(len({x for v in calls.values() for x in v if True}) for _ in [0])
n_calls = len({(q, cid) for (q, _), ids in calls.items() for cid in ids})
eligible, metric_named = [], []
for (q, cell), ids in sorted(calls.items(), key=lambda kv: (int(kv[0][0][1:]), kv[0][1])):
    aid, _, ent = cell.partition(".")
    a = plans[q][int(aid[1:]) - 1]
    asp = Aspect(aid, a["text"], a.get("keyword_query"), a.get("metric") or None, a.get("kind") or "fact",
                 proxy=bool(a.get("proxy")))
    role = "research" if ent == "research" else "all" if ent == "all" else "named"
    sq = SubQuestion(cell, None if role != "named" else ent, asp, role)
    ok, why = facts.eligible(sq, asp, text[q])
    if ok:
        phrases, why = facts.registered_basis(ent, asp.metric)
        ok = phrases is not None
    row = {"q": q, "cell": cell, "metric": asp.metric, "kind": asp.kind, "calls": len(set(ids)),
           "eligible": ok, "reason": "" if ok else why}
    if asp.metric:
        metric_named.append(row)
    if ok:
        eligible.append(row)
saved = sum(r["calls"] for r in eligible)
out = {"map_and_remap_calls": n_calls, "metric_tagged_cells": len(metric_named), "eligible_cells": len(eligible),
       "upper_bound_calls_saved": saved, "threshold": 15, "decision": "STOP" if saved < 15 else "GO",
       "eligible": eligible, "metric_tagged_not_eligible": [r for r in metric_named if not r["eligible"]]}
print(json.dumps(out, indent=1))
