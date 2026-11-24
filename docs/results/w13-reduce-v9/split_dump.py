"""#297 step 6: split the dump (dump295.py output) into the four scorer parts (0 calls). Q26 and Q27 are left out: they
reuse the identical #272 v5.2 records and carry #272's adjudicated verdicts (plan step 6).
  python split_dump.py <answers-dump.txt> <out dir>"""
import re
import sys
from pathlib import Path

PARTS = {"A": range(1, 11), "B": range(11, 17), "C": range(17, 22), "D": [22, 23, 24, 25, 28, 29, 30]}
text = Path(sys.argv[1]).read_text(encoding="utf-8")
sep = "=" * 100
blocks = {}
for b in text.split(sep):
    m = re.match(r"\s*Q(\d+) ", b)
    if m:
        blocks[int(m.group(1))] = sep + b
out = Path(sys.argv[2])
for name, qs in PARTS.items():
    body = "".join(blocks[q] for q in qs)
    (out / f"answers-part{name}.txt").write_text(body.rstrip("\n") + "\n", encoding="utf-8")
    print(name, [f"Q{q}" for q in qs], len(body))
