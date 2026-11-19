"""Identity check for the parse cache (#82): are the chunks the same as before?

  python scripts/chunk_dump.py dump OUT.json          every PDF chunk in the local DB
  python scripts/chunk_dump.py dump --all OUT.json    every chunk (HTML, text, PDF)
  python scripts/chunk_dump.py compare A.json B.json  exit 1 if any chunk differs
  python scripts/chunk_dump.py remap OLD.json NEW.json ID [ID ...]
                                                      new ID(s) of old chunks after a re-parse (#84)

A chunk is compared on chunk_id, section, page and text. Owner: TL (Yueyang Du).
"""
from __future__ import annotations

import argparse
import json
import re
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


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def remap_ids(old: dict, new: dict, ids: list[str]) -> dict[str, list[str]]:
    """{old ID: new IDs}. The new chunk of the same document with identical text; else the first
    new chunk that contains the old text; else the parts of a chunk split at a page break: new chunks
    of that document made mostly (>= 80%) of the old chunk's words and holding >= 10% of them, best
    first; [] when nothing matches. Check the result against the passage's quote."""
    out = {}
    for old_id in ids:
        doc = old_id.split("#")[0]
        text = old[old_id]["text"]
        same_doc = {k: v for k, v in new.items() if k.split("#")[0] == doc}
        exact = [k for k, v in same_doc.items() if v["text"] == text]
        if exact:
            out[old_id] = exact[:1]
            continue
        # The old text plus a part that moved in from another page (SCHW-DECK-2026Q3#7).
        holding = sorted((k for k, v in same_doc.items() if text in v["text"]),
                         key=lambda k: int(k.split("#")[1]))
        if holding:
            out[old_id] = holding[:1]
            continue
        # Split: the parts are new chunks made mostly of the old chunk's words.
        words, old_set = _words(text), set(_words(text))
        scored = []
        for k, v in same_doc.items():
            new_words = _words(v["text"])
            have = set(new_words)
            hit = sum(w in have for w in words) / max(len(words), 1)
            from_old = sum(w in old_set for w in new_words) / max(len(new_words), 1)
            if hit >= 0.1 and from_old >= 0.8:
                scored.append((hit, k))
        out[old_id] = [k for _, k in sorted(scored, key=lambda x: (-x[0], x[1]))]
    return out


def remap(a: str, b: str, ids: list[str]) -> int:
    with open(a, encoding="utf-8") as f:
        old = json.load(f)
    with open(b, encoding="utf-8") as f:
        new = json.load(f)
    missing = [i for i in ids if i not in old]
    for old_id, new_ids in remap_ids(old, new, [i for i in ids if i not in missing]).items():
        first = new[new_ids[0]]["text"] if new_ids else ""
        how = ("" if not new_ids else
               (" (unchanged)" if new_ids == [old_id] else " (same text)") if first == old[old_id]["text"]
               else " (contains the old text)" if old[old_id]["text"] in first else " (split: parts)")
        pages = ", ".join(f"p{new[k]['page']}" for k in new_ids)
        print(f"{old_id} p{old[old_id]['page']} -> {', '.join(new_ids) or 'NO MATCH'}{how}"
              + (f" [{pages}]" if new_ids else ""))
    for i in missing:
        print(f"{i} -> not in {a}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--all", action="store_true", help="every chunk, not only PDF chunks")
    d.add_argument("out")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    r = sub.add_parser("remap")
    r.add_argument("a")
    r.add_argument("b")
    r.add_argument("ids", nargs="+")
    args = ap.parse_args()
    if args.cmd == "remap":
        sys.exit(remap(args.a, args.b, args.ids))
    sys.exit(dump(args.out, args.all) if args.cmd == "dump" else compare(args.a, args.b))
