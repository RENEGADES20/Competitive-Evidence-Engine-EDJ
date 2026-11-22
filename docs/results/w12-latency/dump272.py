"""#250: dump a run's 30 answers for blind scoring (no model calls; from ev247d/dump247b.py). The retrieved set of
an answer is the retrieval hits plus the corrective re-search hits (#247 B1). No mode, run or verdict is written.
  python -B dump250.py <report.json> <out.txt>      (cwd = a worktree root, PYTHONPATH=<wt>/src)"""
import json, re, sys
from pathlib import Path
import yaml
from cee.db import connect

rep = json.load(open(sys.argv[1], encoding="utf-8"))
qs = {q["id"]: q for q in yaml.safe_load(Path("evals/questions.yaml").read_text(encoding="utf-8"))["questions"]}
sup = {s["id"]: s["expected_behavior"] for s in
       (yaml.safe_load(Path("evals/behavior_supersede.yaml").read_text(encoding="utf-8")) or {}).get("supersedes", [])}
cur = connect().cursor()

def chunk(cid):
    cur.execute("SELECT c.text, d.doc_type, d.published_at, d.entity_id, c.segment FROM chunks c "
                "JOIN documents d USING (doc_id) WHERE c.chunk_id = %s", (cid,))
    r = cur.fetchone()
    return tuple(r.values()) if isinstance(r, dict) else r

def ex(t, n=450):
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n] + ("..." if len(t) > n else "")

out = []
for r in sorted(rep["questions"], key=lambda x: int(x["id"][1:])):
    qid = r["id"]; q = qs[qid]; a = r.get("answer") or {}
    retrieved = set(r.get("chunk_ids") or []) | set(r.get("corrective_chunk_ids") or [])
    exp = sup.get(qid, q["expected_behavior"])
    out += ["", "=" * 100, f"{qid} tier {q['tier']} trap {q.get('trap')} | {q['text']}",
            f"EXPECTED {exp}" + (f" (superseded; bank {q['expected_behavior']})" if qid in sup else "")
            + f" | GOT {a.get('behavior')} answerable={a.get('answerable')} | model output: "
            + ("none" if not a else "valid") + f" | reduce: {(r.get('reduce') or {}).get('how')}",
            f"PASSES_IF: {re.sub(chr(10), ' ', q['passes_if'])}",
            f"passages {r.get('passages')} tokens~{r.get('tokens_est')} sub-questions {r.get('subquestions')}"]
    plan = r.get("plan") or {}
    for asp in plan.get("aspects") or []:
        out.append(f"  ASPECT {asp.get('id')} kind={asp.get('kind')} metric={asp.get('metric')} firms={asp.get('firms')} text={asp.get('text')}")
    subs = plan.get("subquestions") or []
    out.append("  SUB-QUESTIONS " + ", ".join(f"{s['id']}({s.get('role')})" for s in subs))
    if plan.get("source") and plan.get("source") != "planner":
        out.append(f"  plan source: {plan.get('source')} error={plan.get('error')}")
    if not a:
        out.append("  NO ANSWER RECORD: " + json.dumps({k: r.get(k) for k in ("model", "how", "invalid", "error")}))
        continue
    for sect in ("claims", "adjacent"):
        for i, c in enumerate(a.get(sect) or [], 1):
            out.append(f"{sect[0].upper()}{i} [{c.get('part_id')}] {c['text']}  flags={c.get('flags')}")
            if c.get("differs_because"):
                out.append(f"    differs: {c['differs_because']}")
            for cid in c.get("chunk_ids", []):
                row = chunk(cid); inret = "" if cid in retrieved else " NOT-IN-RETRIEVED"
                out.append(f"    - {cid} ({row[1]}, {row[2]}, {row[3]}/{row[4]}){inret}: {ex(row[0])}" if row
                           else f"    - {cid} NOT IN DB{inret}")
    for g in a.get("gaps") or []:
        out.append(f"G [{g.get('part_id')}] {g.get('what')} | {g.get('suggested_source')} flags={g.get('flags')}")
    for c in a.get("caveats") or []:
        out.append(f"CAVEAT {c}")
    for k in ("coverage_note", "incomplete_note", "withheld"):
        if a.get(k):
            out.append(f"{k.upper()} {a[k]}")
Path(sys.argv[2]).write_text("\n".join(out) + "\n", encoding="utf-8")
print("written", sys.argv[2], len(rep["questions"]), "questions")
