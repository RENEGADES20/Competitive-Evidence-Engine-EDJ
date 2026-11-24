"""#295 step 7: merge the four blind verdict parts, count blind and text-only PASSes, compare per question with the #272
test B adjudicated verdicts (blind file + PR #273 second read: Q8 and Q17 PASS). 0 calls.
  python merge_verdicts.py <dir with verdicts-blind-part{A,B,C,D}.json> <#272 verdicts-blind-full.json>"""
import hashlib
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
m = {}
for p in "ABCD":
    m.update(json.loads((d / f"verdicts-blind-part{p}.json").read_text(encoding="utf-8")))
assert list(m) == [f"Q{i}" for i in range(1, 31)], list(m)
out = d / "verdicts-blind-full.json"
out.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print("verdicts-blind-full.json sha256", hashlib.sha256(out.read_bytes()).hexdigest())
old = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
adj = {q: v["verdict"] for q, v in old.items()} | {"Q8": "PASS", "Q17": "PASS"}   # PR #273 second read
passes = [q for q, v in m.items() if v["verdict"] == "PASS"]
text_only = [q for q in passes if m[q].get("text_only")]
print(f"blind {len(passes)}/30, text-only {len(text_only)}/30; #272 adjudicated {sum(v == 'PASS' for v in adj.values())}/30, "
      f"#272 blind {sum(v['verdict'] == 'PASS' for v in old.values())}/30")
print("lost (#272 adjudicated PASS -> FAIL):", [q for q in m if adj[q] == "PASS" and m[q]["verdict"] == "FAIL"])
print("gained (FAIL -> PASS):", [q for q in m if adj[q] == "FAIL" and m[q]["verdict"] == "PASS"])
bl = [q for q, v in m.items() if v["verdict"] == "FAIL" and v.get("borderline")]
print("borderline FAILs (the most a second read could add):", len(bl), bl)
print("| Q | #272 adjudicated | #295 blind | text_only | class | borderline | reason |")
print("|---|---|---|---|---|---|---|")
for q, v in m.items():
    print(f"| {q} | {adj[q]} | **{v['verdict']}** | {v.get('text_only')} | {v.get('class')} | {v.get('borderline')} | "
          f"{v['reason']} |")
