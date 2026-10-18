"""Identity check for the parse cache (#82): are the chunks the same as before?

  python scripts/chunk_dump.py dump OUT.json          every PDF chunk in the local DB
  python scripts/chunk_dump.py dump --all OUT.json    every chunk (HTML, text, PDF)
  python scripts/chunk_dump.py compare A.json B.json  exit 1 if any chunk differs

A chunk is compared on chunk_id, section, page and text. Owner: TL (Yueyang Du).
"""
from __future__ import annotations

import argparse
import json
import sys

from cee.db import connect


def dump(out: str, every: bool = False) -> None:
    with connect() as conn:
        rows = conn.execute(
            """SELECT c.chunk_id, c.section, c.page, c.text FROM chunks c
               JOIN documents d USING (doc_id)
               WHERE %s OR lower(d.storage_path) LIKE '%%.pdf' ORDER BY c.doc_id, c.seq""",
            (every,)).fetchall()
    data = {r["chunk_id"]: {"section": r["section"], "page": r["page"], "text": r["text"]} for r in rows}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f)
    docs = {k.split("#")[0] for k in data}
    print(f"{out}: {len(data)} {'' if every else 'PDF '}chunks from {len(docs)} documents")


def compare(a: str, b: str) -> int:
    with open(a, encoding="utf-8") as f:
        left = json.load(f)
    with open(b, encoding="utf-8") as f:
        right = json.load(f)
    only_a, only_b = left.keys() - right.keys(), right.keys() - left.keys()
    changed = [k for k in left.keys() & right.keys() if left[k] != right[k]]
    print(f"{a}: {len(left)} chunks; {b}: {len(right)} chunks")
    print(f"only in first: {len(only_a)}; only in second: {len(only_b)}; "
          f"section/page/text differs: {len(changed)}")
    for k in sorted(only_a | only_b | set(changed))[:10]:
        print(f"  {k}")
    same = not (only_a or only_b or changed)
    print("IDENTICAL" if same else "DIFFERENT")
    return 0 if same else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--all", action="store_true", help="every chunk, not only PDF chunks")
    d.add_argument("out")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = ap.parse_args()
    sys.exit(dump(args.out, args.all) if args.cmd == "dump" else compare(args.a, args.b))
