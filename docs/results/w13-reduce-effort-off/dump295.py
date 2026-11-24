"""#295: dump a run's answers for blind scoring (no model calls). dump272.py (the #250 / #272 dump) plus, per the plan
review (issue comment 7120735225):
- the Computability box (answer.computations, written by code) listed WITH the answer, as answer content;
- the evidence list shown under the answer on the Ask page (#291: every item of the matrix's fact cells, the rule of
  cee.ask.evidence_lines), in a separate block marked "context only, not answer content".
No mode, run, prompt version or verdict is written.
  python -B dump295.py <report.json> <out.txt> [--no-evidence]   (cwd = a worktree root, PYTHONPATH=<wt>/src)
--no-evidence leaves the context block out (the side check: the same answers with and without it)."""
import json
import re
import sys
from pathlib import Path

import yaml
from cee.db import connect

args = [a for a in sys.argv[1:] if not a.startswith("--")]
no_evidence = "--no-evidence" in sys.argv
rep = json.load(open(args[0], encoding="utf-8"))
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


def cites(out, ids, retrieved, n=450, pad="    "):
    for cid in ids:
        row = chunk(cid)
        inret = "" if cid in retrieved else " NOT-IN-RETRIEVED"
        out.append(f"{pad}- {cid} ({row[1]}, {row[2]}, {row[3]}/{row[4]}){inret}: {ex(row[0], n)}" if row
                   else f"{pad}- {cid} NOT IN DB{inret}")


def cells_of(matrix):
    cells = (matrix or {}).get("cells") or []
    return list(cells.values()) if isinstance(cells, dict) else cells


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
    out.append("ANSWER (what the answer asserts: claims, adjacent items, gaps, caveats, Computability box)")
    for sect in ("claims", "adjacent"):
        for i, c in enumerate(a.get(sect) or [], 1):
            out.append(f"{sect[0].upper()}{i} [{c.get('part_id')}] {c['text']}  flags={c.get('flags')}")
            if c.get("differs_because"):
                out.append(f"    differs: {c['differs_because']}")
            cites(out, c.get("chunk_ids", []), retrieved)
    for i, c in enumerate(a.get("computations") or [], 1):
        out.append(f"COMPUTABILITY{i} (box written by code) [{c.get('part_id')}] {c['text']}  flags={c.get('flags')}")
        cites(out, c.get("chunk_ids", []), retrieved)
    for g in a.get("gaps") or []:
        out.append(f"G [{g.get('part_id')}] {g.get('what')} | {g.get('suggested_source')} flags={g.get('flags')}")
    for c in a.get("caveats") or []:
        out.append(f"CAVEAT {c}")
    for k in ("coverage_note", "incomplete_note", "withheld"):
        if a.get(k):
            out.append(f"{k.upper()} {a[k]}")
    if no_evidence:
        continue
    lines = []
    for c in cells_of(r.get("matrix")):
        if c.get("effective_label", c.get("label")) != "fact":
            continue
        for it in c.get("items") or []:
            ids = list(it.get("chunk_ids") or [])   # kept by the map's code check (rejected ids are elsewhere)
            if not ids:
                continue
            lines.append((c["id"], " ".join(str(it.get("text") or it.get("quote") or "").split()), it.get("value"), ids))
    if lines:
        out.append(f"EVIDENCE LIST (context only, not answer content: the {len(lines)} evidence lines the page shows "
                   "under the answer, one per item of each fact cell)")
        for n, (cid, text, value, ids) in enumerate(lines, 1):
            out.append(f"  E{n} [{cid}] {text}" + (f" (value {value})" if value else ""))
            cites(out, ids, retrieved, n=200, pad="      ")
Path(args[1]).write_text("\n".join(out) + "\n", encoding="utf-8")
print("written", args[1], len(rep["questions"]), "questions", "(no evidence block)" if no_evidence else "")
