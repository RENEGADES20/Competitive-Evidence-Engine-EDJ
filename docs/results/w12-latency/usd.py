"""#272: USD ceiling of a paid run from its 0-call count report (plans/0272-latency.md "USD ceiling").
Round-1 map calls the count capped (input_tokens_est each) + one re-map per round-1 cell (ceiling) + one reduce per
question that reached a reduce. Peak rates from config/pricing.yaml. Hard ceiling = every call at its output cap;
expected = output at a per-call guess (map 6k, reduce 20k; low effort, one cell per call).
  python usd.py <count report.json> <map model> [map cap] [reduce cap]"""
import json
import sys

RATES = {"deepseek-v4-pro": (1.32, 3.96), "deepseek-flash": (0.30, 1.20)}   # peak miss input, output per 1M
rep = json.load(open(sys.argv[1], encoding="utf-8"))
map_model = sys.argv[2]
map_cap = int(sys.argv[3]) if len(sys.argv) > 3 else 128000
red_cap = int(sys.argv[4]) if len(sys.argv) > 4 else 128000
mi, mo = RATES[map_model]
pi, po = RATES["deepseek-v4-pro"]
n_map = n_red = 0
inp = 0
rows = []
for q in rep["questions"]:
    m = q.get("matrix") or {}
    calls = [c for c in m.get("calls") or [] if c.get("skipped") and "--max-calls" in str(c.get("error"))]
    est = sum(c.get("input_tokens_est") or 0 for c in calls)
    n_map += len(calls)
    inp += est
    red = 1 if calls or q.get("reduce") else 0
    n_red += red
    rows.append((q["id"], len(calls), est))
remap = n_map   # ceiling: one re-map per round-1 cell, input at most its own new chunks (taken as the same size)
hard = (inp * 2 * mi + (n_map + remap) * map_cap * mo + n_red * (60000 * pi + red_cap * po)) / 1e6
expected = (inp * mi + n_map * 6000 * mo + n_red * (30000 * pi + 20000 * po)) / 1e6
for r in rows:
    print(*r)
print(f"round-1 map calls {n_map} (input est {inp:,} tokens), re-map ceiling {remap}, reduces <= {n_red}; "
      f"max-calls = {n_map + remap + n_red}; USD hard ceiling {hard:.2f}, expected about {expected:.2f} (peak rates)")
