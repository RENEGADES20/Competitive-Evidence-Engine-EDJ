# Not runnable after #289: the code it drives or imports was removed; kept as the record of how the evidence was made.
"""#284 (plans/0284-reduce-short.md steps 4-5, TL B4): render-fidelity and rule checks for reduce v6, 0 calls.

Runs scripts/eval_run.py in this process with two hooks, then writes a summary JSON:
- every v6 output rendered (reduce.render_output) is re-checked item by item by the independent fidelity check of
  tests/test_reduce_v6.py (item text verbatim, firm prefix of the ref's cell, scope, source label and date of the
  item's first chunk id, derived formula and input ids, why-line once, chunk ids = refs' ids + extras);
- every final answer (reduce.finish_answer) is counted: claims / adjacent flagged no_citation, outside_matrix,
  number_not_found, unknown_ref, ref_part_mismatch; the render log counts.
- In a real-provider count phase (--real --max-calls 0, every plan and map from the cache), the reduce would be capped;
  the hook then runs the v6 mock reduce on that real matrix (rendering, finish_answer), so the #272 matrices are
  checked too, and records the v6 schema's enum count and fallback per question.
Run from the worktree root with PYTHONPATH=<worktree>/src and REDUCE_PROMPT=v6:
  python docs/results/w13-reduce-short/render_check.py <summary.json> <eval_run args...>
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())   # the worktree root: scripts/ and tests/

from cee.answer import reduce as R  # noqa: E402
from scripts import eval_run as er  # noqa: E402
from tests.test_reduce_v6 import fidelity  # noqa: E402

SUMMARY: dict = {"questions": {}, "fidelity_problems": [], "items_checked": 0}
CURRENT = {"q": None}
FLAGS = ("no_citation", "outside_matrix", "number_not_found", "unknown_ref", "ref_part_mismatch", "unmatched_citation")


def _q(question: str | None) -> dict:
    return SUMMARY["questions"].setdefault(CURRENT["q"] or question or "?", {})


_render_output = R.render_output


def render_output(raw, m):
    out, log = _render_output(raw, m)
    for f in R.STREAMED:
        for x in raw.get(f) or []:
            if isinstance(x, dict):
                SUMMARY["items_checked"] += 1
                for p in fidelity(x, R.render_one(x, m), m):
                    SUMMARY["fidelity_problems"].append({"q": CURRENT["q"], "part_id": x.get("part_id"), "problem": p})
    return out, log


_finish_answer = R.finish_answer


def finish_answer(answer, m, query, plan, hits, question, code_built=False):
    final, info = _finish_answer(answer, m, query, plan, hits, question, code_built=code_built)
    rec = _q(question)
    items = [*final.claims, *final.adjacent]
    rec["flags"] = {f: sum(f in x.flags for x in items) for f in FLAGS}
    rec["claims"] = len(final.claims)
    rec["uncited_shown"] = sum(not x.chunk_ids and x.text.strip() != R.P.BOUNDARY_HANDOFF for x in final.claims)
    if info.get("render"):
        rec["render"] = {k: v for k, v in info["render"].items() if k != "lists"}
        rec["render_lists"] = info["render"].get("lists", {})
    return final, info


_reduce = er.RealRunner.reduce


def reduce(self, q, query, plan, hits, matrix):
    CURRENT["q"] = q["id"]
    answer, how, info = _reduce(self, q, query, plan, hits, matrix)
    if how == "cap" and R.needs_call(matrix):   # the count phase: check the real matrix with the v6 mock
        schema, fallback = R.reduce_schema(matrix)
        rec = _q(q["id"])
        rec.update(enum_values=R.enum_values(schema), schema_fallback=fallback, refs=len(R.item_refs(matrix)),
                   message_sha=info.get("message_sha"), file=info.get("file"))
        a = R.to_answer(R.mock_reduce_v6(matrix, query), "mock", m=matrix)
        R.finish_answer(a, matrix, query, plan, hits, q["text"])
    return answer, how, info


def main() -> int:
    out, argv = sys.argv[1], sys.argv[2:]
    assert R.v6(), "set REDUCE_PROMPT=v6"
    R.render_output, R.finish_answer, er.RealRunner.reduce = render_output, finish_answer, reduce
    import yaml
    texts = {x["text"]: x["id"] for x in yaml.safe_load(open("evals/questions.yaml", encoding="utf-8"))["questions"]}
    orig = R.finish_answer

    def by_text(answer, m, query, plan, hits, question, code_built=False):   # the mock path: question id by text
        CURRENT["q"] = texts.get(question, CURRENT["q"])
        return orig(answer, m, query, plan, hits, question, code_built=code_built)
    R.finish_answer = by_text
    try:
        code = er.main(argv)
    finally:
        tot = {f: sum(r.get("flags", {}).get(f, 0) for r in SUMMARY["questions"].values()) for f in FLAGS}
        tot["uncited_shown"] = sum(r.get("uncited_shown", 0) for r in SUMMARY["questions"].values())
        for k in R.RENDER_COUNTS:
            tot[f"render_{k}"] = sum(r.get("render", {}).get(k, 0) for r in SUMMARY["questions"].values())
        tot["enum_fallback_questions"] = sorted(q for q, r in SUMMARY["questions"].items() if r.get("schema_fallback"))
        SUMMARY["totals"] = tot
        SUMMARY["fidelity_problem_count"] = len(SUMMARY["fidelity_problems"])
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(SUMMARY, fh, indent=1, sort_keys=True)
        print(json.dumps({"items_checked": SUMMARY["items_checked"],
                          "fidelity_problems": SUMMARY["fidelity_problem_count"], **tot}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
