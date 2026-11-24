"""#297 step 2 (plan review finding 3): Q19's matrix roles from a run report (0 calls). Lists each aspect (kind,
asked_firms) and its holding cells with role and whether the v9 rule (cee.answer.validate.asked_cell) asks for them.
Exit 1 when a competitor cell of the competitor aspect (passes_if "competitor moves") holds a fact and is not asked.
  python q19_roles.py <report.json> [Q19]"""
import json
import sys

rep = json.load(open(sys.argv[1], encoding="utf-8"))
qid = sys.argv[2] if len(sys.argv) > 2 else "Q19"
q = next(x for x in rep["questions"] if x["id"] == qid)
m = q["matrix"]
aspects = {a["id"]: a for a in m["aspects"]}


def holds(c):
    return c.get("effective_label") == "fact" or (c.get("label") == "derived" and bool((c.get("derivation") or {}).get("ok")))


def asked(c):   # mirrors cee.answer.validate.asked_cell
    a = aspects[c["aspect_id"]]
    if not holds(c) or a.get("kind") == "comparison" or a.get("proxy"):
        return False
    return c["role"] in ("named", "all", "research") or (c["role"] == "competitor" and c.get("entity") in (a.get("asked_firms") or []))


bad = []
for aid, a in aspects.items():
    cells = [c for c in m["cells"].values() if c["aspect_id"] == aid and holds(c)]
    print(f"{aid} {a.get('kind')} asked_firms={a.get('asked_firms') or []} | {a.get('text')}")
    for c in cells:
        print(f"    {c['id']:<14} {c['role']:<11} asked={asked(c)}")
        competitor_aspect = "competitor" in (a.get("text") or "").lower() and a.get("kind") != "comparison"
        if competitor_aspect and c["role"] == "competitor" and not asked(c):
            bad.append(c["id"])
print("competitor-aspect cells holding a fact but not asked:", bad or "none")
sys.exit(1 if bad else 0)
