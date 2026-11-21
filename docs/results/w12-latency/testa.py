"""#272 step 10: test A summary per config (latency, cut / invalid, behaviors vs expected_behavior, cost) and the
fixed choice rule. python testa.py a-c1 a-c2 a-c3"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

EV = Path(__file__).parent
REPO = Path("D:/ALLPROJECTS/EDJ/repo")
SIX = ["Q5", "Q10", "Q19", "Q21", "Q24", "Q26"]
BASELINE_MATCH = 4   # #250 fts on the six: Q5, Q19, Q24, Q26 match expected_behavior (plan step 10)
bank = {q["id"]: q for q in yaml.safe_load(open(REPO / "evals/questions.yaml", encoding="utf-8"))["questions"]}
sys.path.insert(0, str(REPO / "scripts"))
import latency_report as L  # noqa: E402

out = {}
for name in sys.argv[1:]:
    rep = json.load(open(EV / name / "report.json", encoding="utf-8"))
    qs = {r["id"]: r for r in rep["questions"]}
    rows = L.load(EV / name / "raw", set(SIX))
    lat = {q["q"]: q for q in L.per_question(rows)}
    s = L.summary(list(lat.values()))
    beh = {}
    for q in SIX:
        r = qs.get(q, {})
        got = (r.get("answer") or {}).get("behavior") if isinstance(r.get("answer"), dict) else None
        want = r.get("expected_behavior_effective") or bank[q].get("expected_behavior")
        beh[q] = (got, want)
    match = sum(g == w for g, w in beh.values())
    usd = rep["meta"].get("cost", {}) if isinstance(rep["meta"].get("cost"), dict) else {}
    out[name] = {"summary": s, "match": match, "beh": beh, "meta_cost": rep["meta"].get("cost"),
                 "real_calls": rep["meta"].get("real_calls"), "reused": rep["meta"].get("reused")}
    print(f"== {name}: critical p50 {s['critical_p50']} p90 {s['critical_p90']} max {s['critical_max']}; first evidence "
          f"p50 {s['first_evidence_p50']}; cut {s['cut']} invalid {s['invalid']} failed {s['failed']}; behavior match "
          f"{match}/6; new calls {rep['meta'].get('real_calls')} reused {rep['meta'].get('reused')}; cost {rep['meta'].get('cost')}")
    for q in SIX:
        print(f"   {q} crit {lat.get(q, {}).get('critical_s')} first {lat.get(q, {}).get('first_evidence_s')} "
              f"behavior {beh[q][0]} (expected {beh[q][1]})")
elig = {n: o for n, o in out.items() if o["summary"]["cut"] == 0 and o["summary"]["invalid"] == 0
        and o["match"] >= BASELINE_MATCH}
print("eligible:", list(elig))
non_flash = {n: o for n, o in elig.items() if not n.endswith("c3")}
best = min(non_flash, key=lambda n: non_flash[n]["summary"]["critical_p50"]) if non_flash else None
c3 = next((n for n in elig if n.endswith("c3")), None)
if c3 and (best is None or elig[c3]["summary"]["critical_p50"] < elig[best]["summary"]["critical_p50"]):
    best = c3
print("chosen:", best)
