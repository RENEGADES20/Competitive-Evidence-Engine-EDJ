"""#292 step 3: compare two mock eval runs (report.json), question by question.
  python cmp_mock.py <new report.json> <old report.json> [--identical]   # --identical: v5.2 vs main, every field
Prints, per question: identical answers (status, chunk ids, behavior, claims / adjacent / gaps with chunk ids,
part_id and flags), else the flag counts old -> new, the reduce version and the claim counts. Watched flags (plan
step 3): a higher count of part_gap, comparison_missing, outside_matrix, number_not_found or no_citation, or a flag
kind the old run lacks, is printed as WORSE."""
import json
import sys
from collections import Counter

WATCH = ("part_gap", "comparison_missing", "outside_matrix", "number_not_found", "no_citation")


def load(p):
    return {r["id"]: r for r in json.load(open(p, encoding="utf-8"))["questions"]}


def items(r):
    a = r.get("answer") or {}
    return [(k, x.get("text") or x.get("what"), x.get("chunk_ids"), x.get("part_id"), x.get("flags"))
            for k in ("claims", "adjacent", "gaps") for x in (a.get(k) or [])]


def flags(r):
    a = r.get("answer") or {}
    return Counter(f for k in ("claims", "adjacent", "gaps") for x in (a.get(k) or []) for f in (x.get("flags") or []))


def main(new_p, old_p, identical_only=False):
    new, old = load(new_p), load(old_p)
    same, worse = [], []
    for q in old:
        A, B = new[q], old[q]
        keys = ("status", "chunk_ids", "map_behavior", "answer_behavior")
        if all(A.get(k) == B.get(k) for k in keys) and items(A) == items(B):
            same.append(q)
            continue
        fa, fb = flags(A), flags(B)
        bad = sorted(f for f in set(fa) | set(fb) if (f in WATCH and fa[f] > fb[f]) or (f not in fb))
        if bad:
            worse.append(q)
        ver = ((A.get("reduce") or {}).get("version"), (B.get("reduce") or {}).get("version"))
        na, nb = len((A.get("answer") or {}).get("claims") or []), len((B.get("answer") or {}).get("claims") or [])
        print(f"{q}: differs; version {ver[1]} -> {ver[0]}; claims {nb} -> {na}; flags {dict(fb)} -> {dict(fa)}"
              + (f"; WORSE {bad}" if bad else ""))
    print(f"identical {len(same)}/{len(old)}: {' '.join(same)}")
    print(f"worse {len(worse)}: {' '.join(worse) or 'none'}")
    return 0 if (not worse and (not identical_only or len(same) == len(old))) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], "--identical" in sys.argv))
