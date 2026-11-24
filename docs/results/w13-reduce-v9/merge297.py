"""#297 step 6: merge the four blind verdict parts (Q1-Q25, Q28-Q30), add Q26 and Q27 with #272's adjudicated verdicts
(identical records, not re-scored), count blind and text-only PASSes, compare per question with #272 adjudicated
(blind file + PR #273 second read: Q8 and Q17 PASS) and #295 blind. 0 calls.
  python merge297.py <dir with verdicts-blind-part{A,B,C,D}.json> <#272 verdicts-blind-full.json> <#295 verdicts-blind-full.json>"""
import hashlib
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
old = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
v295 = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
adj = {q: v["verdict"] for q, v in old.items()} | {"Q8": "PASS", "Q17": "PASS"}   # PR #273 second read
got = {}
for p in "ABCD":
    got.update(json.loads((d / f"verdicts-blind-part{p}.json").read_text(encoding="utf-8")))
m = {}
for i in range(1, 31):
    q = f"Q{i}"
    if q in ("Q26", "Q27"):
        m[q] = {"verdict": adj[q], "class": "", "borderline": False, "text_only": None,
                "reason": "carried: identical #272 v5.2 record, #272 adjudicated verdict (plan step 6)", "carried": True}
    else:
        m[q] = got[q]
assert set(got) == {f"Q{i}" for i in range(1, 31)} - {"Q26", "Q27"}, sorted(got)
out = d / "verdicts-blind-full.json"
out.write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print("verdicts-blind-full.json sha256", hashlib.sha256(out.read_bytes()).hexdigest())
passes = [q for q, v in m.items() if v["verdict"] == "PASS"]
text_only = [q for q in passes if m[q].get("text_only") or m[q].get("carried")]
print(f"blind {len(passes)}/30, text-only {len(text_only)}/30 (Q26, Q27 carried from #272 adjudicated); "
      f"#272 adjudicated {sum(v == 'PASS' for v in adj.values())}/30; #295 blind "
      f"{sum(v['verdict'] == 'PASS' for v in v295.values())}/30")
print("lost vs #272 adjudicated (PASS -> FAIL):", [q for q in m if adj[q] == "PASS" and m[q]["verdict"] == "FAIL"])
print("gained vs #272 adjudicated (FAIL -> PASS):", [q for q in m if adj[q] == "FAIL" and m[q]["verdict"] == "PASS"])
print("vs #295 blind, FAIL -> PASS:", [q for q in m if v295[q]["verdict"] == "FAIL" and m[q]["verdict"] == "PASS"],
      "| PASS -> FAIL:", [q for q in m if v295[q]["verdict"] == "PASS" and m[q]["verdict"] == "FAIL"])
pass_not_text = [q for q in passes if q not in text_only]
print("PASS but not text_only:", pass_not_text)
bl = [q for q, v in m.items() if v["verdict"] == "FAIL" and v.get("borderline")]
print("borderline FAILs (for the PR reviewer's second read):", len(bl), bl)
print("| Q | #272 adjudicated | #295 blind | #297 blind | text_only | class | borderline | reason |")
print("|---|---|---|---|---|---|---|---|")
for q, v in m.items():
    print(f"| {q} | {adj[q]} | {v295[q]['verdict']} | **{v['verdict']}** | {v.get('text_only')} | {v.get('class')} | "
          f"{v.get('borderline')} | {v.get('reason')} |")
