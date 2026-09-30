"""Load entities, documents and chunks into Postgres from data/manifest.csv.

Skeleton placeholder, owner: TL (Yueyang Du).
Usage: python -m cee.ingest.load            (re-ingest every manifest row)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from cee.config import entities_config
from cee.db import connect
from cee.ingest.chunk import chunk_sections, split_10k_sections
from cee.ingest.manifest import check_files, read_manifest


def seed_entities(conn) -> None:
    ents = entities_config()["entities"]
    # parents first so the foreign key holds
    for e in sorted(ents, key=lambda e: e.get("parent") is not None):
        conn.execute(
            """INSERT INTO entities (entity_id, name, parent_id, reported_as, equivalence, caveat)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (entity_id) DO UPDATE SET name = EXCLUDED.name,
                 parent_id = EXCLUDED.parent_id, reported_as = EXCLUDED.reported_as,
                 equivalence = EXCLUDED.equivalence, caveat = EXCLUDED.caveat""",
            (e["id"], e["name"], e.get("parent"), e.get("reported_as"),
             e.get("equivalence"), e.get("caveat")))


def parse_file(row: dict, path: Path) -> list[tuple[str, str, int | None]]:
    suffix = path.suffix.lower()
    if suffix in (".htm", ".html"):
        from edgar.documents import parse_html

        text = parse_html(path.read_text(encoding="utf-8")).text()
        if row["doc_type"] in ("10-K", "10-Q"):
            return [(s, b, None) for s, b in split_10k_sections(text)]
        return [("Document", text, None)]
    if suffix == ".pdf":
        from cee.ingest.pdf import parse_pdf

        return [(s, t, p) for s, p, t in parse_pdf(path)]
    if suffix in (".txt", ".md"):
        return [("Document", path.read_text(encoding="utf-8"), None)]
    raise ValueError(f"{row['doc_id']}: no parser for {suffix}")


def load_document(conn, row: dict, path: Path) -> int:
    sections = parse_file(row, path)
    chunks = chunk_sections(row["doc_id"], row["entity_id"] or "", row["doc_type"],
                            row["period_end"] or row["published_at"], sections)
    conn.execute("DELETE FROM documents WHERE doc_id = %s", (row["doc_id"],))
    conn.execute(
        """INSERT INTO documents (doc_id, entity_id, doc_type, source_tier, published_at,
                                  period_end, url, storage_path, sha256)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (row["doc_id"], row["entity_id"] or None, row["doc_type"], int(row["source_tier"]),
         row["published_at"], row["period_end"] or None, row["url"] or None,
         row["storage_path"], row["sha256"]))
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO chunks (chunk_id, doc_id, seq, section, segment, page, prefix, text)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            [(c.chunk_id, row["doc_id"], c.seq, c.section, c.segment, c.page, c.prefix, c.text)
             for c in chunks])
    return len(chunks)


def load_all(only: str | None = None) -> dict[str, int]:
    rows = [r for r in read_manifest() if not only or r["doc_id"] == only]
    resolved = check_files(rows)  # stop before touching the DB if any file is missing/bad
    counts = {}
    with connect() as conn:
        seed_entities(conn)
        for row, path in resolved:
            counts[row["doc_id"]] = load_document(conn, row, path)
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="load only this doc_id")
    args = ap.parse_args()
    for doc_id, n in load_all(args.doc).items():
        print(f"{doc_id}: {n} chunks")
