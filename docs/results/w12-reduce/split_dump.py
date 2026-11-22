"""#275 test B: split a blind answers dump (dump272.py output) into the four scoring parts by question range, the
#272 ranges (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30). 0 calls.
  python split_dump.py <answers-dump.txt> <out dir>"""
import re
import sys
from pathlib import Path

RANGES = {"A": (1, 10), "B": (11, 16), "C": (17, 21), "D": (22, 30)}
text = Path(sys.argv[1]).read_text(encoding="utf-8")
blocks = re.split(r"\n(?==+\nQ\d+ tier )", "\n" + text)
out = Path(sys.argv[2])
for name, (lo, hi) in RANGES.items():
    keep = []
    for b in blocks:
        m = re.search(r"^Q(\d+) tier ", b.lstrip("=\n"), re.M)
        if m and lo <= int(m.group(1)) <= hi:
            keep.append(b)
    (out / f"answers-part{name}.txt").write_text("\n".join(keep).strip() + "\n", encoding="utf-8")
    print(name, len(keep), "questions")
