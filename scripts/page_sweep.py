"""Page sweep (#84): is each PDF chunk on the page it says it is on?

  python scripts/page_sweep.py                     every PDF chunk in the DB (DATABASE_URL)
  python scripts/page_sweep.py --doc SCHW-DECK-2026Q1

For each PDF chunk, the share of its word tokens found in the stated page's text (pymupdf). A token
counts when it occurs in the page text with all spaces and punctuation removed, because some PDFs
fuse words ("requirewealthmanagersto") or footnote numbers ("Lending1"). A chunk is
- OK             >= 90% of its tokens on the stated page;
- PASS-SAMEPAGE  below 90%, but no other page holds more of its tokens (the page is right, the text
                 differs: docling reads text pymupdf does not, or the other way round);
- MISPLACED      another page holds more of its tokens.
Prints every chunk below 90% and a table per group (all PDFs; the 16 PDFs from #77/#78). A report:
exit 0 always. Raw files are found like the app finds them (CORPUS_SHARE_PATH, then data/).
Owner: TL (Yueyang Du).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

THRESHOLD = 0.9
TOKEN = re.compile(r"[a-z0-9]+")
# The decks and supplements the issue was written for (#77, #78): 0 chunks below 90% expected.
GROUP_77_78 = {f"{e}-SUPP-2026Q{q}" for e in ("BAC", "MS") for q in (1, 2, 3)} | {
    "RJF-SUPP-2026Q1", "RJF-SUPP-2026Q2", "BAC-DECK-2026Q1", "BAC-DECK-2026Q2", "BAC-DECK-2026Q3",
    "RJF-DECK-2026Q1", "RJF-DECK-2026Q2", "SCHW-DECK-2026Q1", "SCHW-DECK-2026Q2", "SCHW-DECK-2026Q3"}


def compact(page_text: str) -> str:
    return "".join(TOKEN.findall(page_text.lower()))


def share(tokens: list[str], page: str) -> float:
    return sum(t in page for t in tokens) / len(tokens) if tokens else 1.0


def score(text: str, stated: int | None, pages: dict[int, str]) -> tuple[str, float, int | None]:
    """(status, share on the stated page, page holding most tokens). `pages` are compact()ed.
    A tie with the stated page counts for the stated page."""
    tokens = TOKEN.findall(text.lower())
    own = share(tokens, pages.get(stated, ""))
    if own >= THRESHOLD:
        return "OK", own, stated
    best = max(pages, key=lambda p: (share(tokens, pages[p]), p == stated), default=stated)
    if best == stated or share(tokens, pages[best]) <= own:
        return "PASS-SAMEPAGE", own, stated
    return "MISPLACED", own, best


def page_texts(path: Path) -> dict[int, str]:
    import pymupdf

    with pymupdf.open(path) as doc:
        return {i: compact(page.get_text("text")) for i, page in enumerate(doc, start=1)}


def main(doc_filter: str | None = None) -> None:
    from cee.config import resolve_path
    from cee.db import connect

    with connect() as conn:
        rows = conn.execute(
            """SELECT c.chunk_id, c.doc_id, c.page, c.text, d.storage_path FROM chunks c
               JOIN documents d USING (doc_id)
               WHERE lower(d.storage_path) LIKE '%%.pdf' AND (%s::text IS NULL OR c.doc_id = %s)
               ORDER BY c.doc_id, c.seq""", (doc_filter, doc_filter)).fetchall()
    groups = {"all PDFs": Counter(), "16 PDFs of #77/#78": Counter()}
    below, docs, pages, current = [], Counter(), {}, None
    for r in rows:
        if r["doc_id"] != current:
            current, pages = r["doc_id"], page_texts(resolve_path(r["storage_path"]))
        status, own, best = score(r["text"], r["page"], pages)
        for name in groups:
            if name == "all PDFs" or r["doc_id"] in GROUP_77_78:
                groups[name][status] += 1
                groups[name]["chunks"] += 1
                groups[name]["docs " + r["doc_id"]] = 1
        docs[r["doc_id"], status] += 1
        if status != "OK":
            below.append((r["chunk_id"], r["page"], own, status, best))
    for doc_id in dict.fromkeys(r["doc_id"] for r in rows):
        n = sum(docs[doc_id, s] for s in ("OK", "PASS-SAMEPAGE", "MISPLACED"))
        print(f"{doc_id}: {docs[doc_id, 'OK']}/{n} >= 90%; PASS-SAMEPAGE {docs[doc_id, 'PASS-SAMEPAGE']}; "
              f"MISPLACED {docs[doc_id, 'MISPLACED']}")
    print("\nBelow 90% (chunk_id, stated page, share on it, status, page holding most tokens):")
    for chunk_id, page, own, status, best in below:
        print(f"  {chunk_id}  p{page}  {own:.2f}  {status}" + (f" -> p{best}" if status == "MISPLACED" else ""))
    print("\n| group | PDFs | chunks | >= 90% | below 90% | PASS-SAMEPAGE | MISPLACED |")
    print("|---|---|---|---|---|---|---|")
    for name, c in groups.items():
        ndocs = sum(1 for k in c if k.startswith("docs "))
        print(f"| {name} | {ndocs} | {c['chunks']} | {c['OK']} | {c['PASS-SAMEPAGE'] + c['MISPLACED']} | "
              f"{c['PASS-SAMEPAGE']} | {c['MISPLACED']} |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="only this doc_id")
    main(ap.parse_args().doc)
