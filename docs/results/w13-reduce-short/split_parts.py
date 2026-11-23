"""#284: split an answers dump (w12-latency/dump272.py output) into the #272 scoring parts, 0 calls:
A Q1-Q10, B Q11-Q16, C Q17-Q21, D Q22-Q30. Each part is the dump's own text from the blank line before its first
question's separator to the one before the next part's (the #283 parts are byte-identical slices of their dump).
  python split_parts.py <answers-dump.txt> <out dir>"""
import re
import sys
from pathlib import Path

PARTS = [("A", 1), ("B", 11), ("C", 17), ("D", 22)]
SEP = "\n" + "=" * 100 + "\n"

text = Path(sys.argv[1]).read_text(encoding="utf-8")   # universal newlines: the parts are LF
starts = {int(m.group(1)): m.start() for m in re.finditer(re.escape(SEP) + r"Q(\d+) tier", text)}
cut = [starts[q] for _, q in PARTS] + [len(text)]
out = Path(sys.argv[2])
for k, (name, _) in enumerate(PARTS):
    (out / f"answers-part{name}.txt").write_bytes(text[cut[k]:cut[k + 1]].encode("utf-8"))
    print(name, sorted(q for q, s in starts.items() if cut[k] <= s < cut[k + 1]))
