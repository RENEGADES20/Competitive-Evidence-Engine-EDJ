"""Five-second health check: python -m cee.smoke  -> prints PASS or what is broken.

Skeleton placeholder, owner: TL (Yueyang Du). Offline: always uses the mock provider.
"""
from __future__ import annotations

import sys

TABLES = {"entities", "documents", "chunks", "topics", "chunk_topics", "source_registry",
          "query_log", "query_feedback"}
QUESTION = "What does Edward Jones's 10-K say about its number of financial advisors?"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as e:  # report, keep going
            ok, detail = False, f"{type(e).__name__}: {e}"
        checks.append((name, ok, detail))
        print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}")
        return ok

    from cee.db import connect

    def db():
        with connect() as c:
            snap = c.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
        return True, f"connected (snapshot: {snap or 'none, built locally'})"

    def tables():
        with connect() as c:
            have = {r["tablename"] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        missing = TABLES - have
        return not missing, "all present" if not missing else f"missing {sorted(missing)}"

    def chunks():
        with connect() as c:
            n = c.execute("SELECT count(*) AS n FROM chunks").fetchone()["n"]
        return n > 0, f"{n} chunks (run scripts\\restore.ps1 if 0)"

    def fts():
        from cee.retrieve.fts import resolve, search
        hits = search(resolve(QUESTION))
        return bool(hits), f"{len(hits)} hits for the EDJ acceptance question"

    def answer():
        from cee.ask import ask
        a = ask(QUESTION, provider="mock", log=False).answer
        cited = a.claims and all(c.chunk_ids and not c.flags for c in a.claims)
        return bool(cited), f"behavior={a.behavior}, {len(a.claims)} cited claims"

    if check("database", db):
        check("tables", tables)
        check("chunks", chunks)
        check("search", fts)
        check("answer (mock)", answer)

    passed = all(ok for _, ok, _ in checks) and len(checks) == 5
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
