"""0-call coverage estimate for #285 from the #272 test-B records (cache-a, C1 map records)."""
import json, glob, re, collections, subprocess, datetime as dt, os
PRICE = {"in_hit": 0.022, "in_miss": 0.66, "out": 1.98}   # deepseek-v4-pro off-peak, config/pricing.yaml
METRICS = {
    "advisor_headcount": re.compile(r"\badvisor headcount\b|\bnumber of (financial )?advisors\b|\badvisor count\b", re.I),
    "net_new_assets": re.compile(r"\bnet new (client )?assets\b|\bnet (client )?asset flows\b", re.I),
    "client_assets": re.compile(r"\b(total )?client assets\b|\bassets under (care|administration|management)\b", re.I),
}
NOT_FIGURE = re.compile(r"defin|includ|exclud|disclos|\bhow\b|\bwhy\b|strateg|attribut|recruit|retention|attrition|"
                        r"project|prepare|source|channel|\bmix\b|\bper\b|revenue|fee|rate|across|\bby (affiliation|channel|model|segment)", re.I)
KINDS = {"fact", "series", "recency"}

def eligible(a):
    if a.get("kind") not in KINDS or a.get("proxy"):
        return []
    t = a.get("text", "")
    if NOT_FIGURE.search(t):
        return []
    return [m for m, p in METRICS.items() if p.search(t)]

def names_metric(a):
    t = a.get("text", "") + " " + (a.get("keyword_query") or "")
    ms = {m for m, p in METRICS.items() if p.search(a.get("text", ""))}
    if a.get("metric"): ms.add(a["metric"])
    return ms

def cost(u):
    hit = u.get("cache_hit_tokens") or 0
    miss = u.get("cache_miss_tokens", u.get("input_tokens", 0) - hit)
    return (hit * PRICE["in_hit"] + miss * PRICE["in_miss"] + (u.get("output_tokens") or 0) * PRICE["out"]) / 1e6

sql = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidates.sql"), encoding="utf-8").read()
cand = set(subprocess.run(["docker", "exec", "-i", "cee-db", "psql", "-U", "cee", "-d", "cee", "-At"], input=sql,
                          capture_output=True, text=True).stdout.split())
print("candidate chunks", len(cand))
plans, recs = {}, []
for f in glob.glob(r"D:\ALLPROJECTS\EDJ\cache\ev272\cache-a\*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "-plan-" in f:
        plans[d["question_id"]] = {f"a{n}": a for n, a in enumerate(d["raw"]["aspects"], 1)}
    elif d.get("model") == "deepseek-v4-pro" and d.get("request_version") == "ds-strict-2-map-low-c128000-s1" \
            and ("-map." in f or "-remap." in f):
        recs.append(d)
calls_all = [r for r in recs if r["round"] == 1]
tot_cost = sum(cost(r["usage"]) for r in recs)
cells = collections.defaultdict(lambda: {"calls": [], "items": []})
for r in recs:
    raw = r.get("raw") if isinstance(r.get("raw"), dict) else {}
    for cid in r["cells"]:
        cells[(r["question_id"], cid)]["calls"].append(r)
    for c in raw.get("cells") or []:
        k = (r["question_id"], c.get("subquestion_id"))
        if k in cells:
            cells[k]["items"] += [i for i in c.get("items") or [] if str(i.get("value") or "").strip()]
out = []
for (q, cid), v in cells.items():
    aid, _, ent = cid.partition(".")
    a = plans[q][aid]
    out.append(dict(q=q, cell=cid, entity=ent, aspect=aid, text=a["text"], kind=a["kind"], proxy=a.get("proxy"),
                    named=sorted(names_metric(a)), eligible=[] if ent in ("research", "all") else eligible(a), figure=bool(v["items"]),
                    cand=any(set(i.get("chunk_ids") or []) & cand for i in v["items"]),
                    n_calls=len(v["calls"]), cost=sum(cost(c["usage"]) for c in v["calls"]),
                    wall=max(c["wall_s"] for c in v["calls"]),
                    values=[(i.get("value"), i.get("period"), (i.get("chunk_ids") or [""])[0]) for i in v["items"]][:6]))
json.dump(out, open(r"D:\ALLPROJECTS\EDJ\cache\ev285\coverage272.json", "w", encoding="utf-8"), indent=1)
metric_cells = [c for c in out if c["named"] and c["figure"]]
elig = [c for c in out if c["eligible"]]
cov = [c for c in elig if c["figure"] and c["cand"]]
print(f"map+remap records {len(recs)} (round 1: {len(calls_all)}), cost off-peak ${tot_cost:.2f}")
print(f"cells {len(out)}; metric cells (aspect names a target metric, map gave a figure) {len(metric_cells)}")
print(f"servable (eligible aspect) cells {len(elig)}; with a figure {sum(c['figure'] for c in elig)}; "
      f"figure cites a candidate chunk {len(cov)}")
print(f"estimated covered: {len(cov)}/{len(metric_cells)} metric cells; calls saved {sum(c['n_calls'] for c in cov)} "
      f"of {len(recs)}; $ saved {sum(c['cost'] for c in cov):.2f} of map ${tot_cost:.2f}")
for c in sorted(elig, key=lambda c: (int(c["q"][1:]), c["cell"])):
    print(c["q"], c["cell"], c["kind"], c["eligible"], "FIG" if c["figure"] else "-", "CAND" if c["cand"] else "-",
          c["n_calls"], f"{c['wall']:.0f}s", f"${c['cost']:.3f}", c["values"][:2])
qs = collections.Counter(c["q"] for c in cov)
print("questions touched", dict(qs))
