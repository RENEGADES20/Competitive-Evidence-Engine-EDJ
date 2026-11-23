"""#284: reduce-only run tables and the fixed checks (plans/0284-reduce-short.md, TL conditions B1 / B3), 0 calls.

  python analyze.py <run dir> <baseline report.json> <baseline raw dir>[,<raw dir> ...] [--stage1] [--md <out.md>]

Per question: reduce how, output / reasoning / answer tokens, wall, TTFT, first claim, price tier, render counts
(refs, unknown_ref, ref_part_mismatch, dropped, uncited, text claims, figures outside the matrix and number_not_found
split into rendered and model text), final flags (outside_matrix, number_not_found), shown claims without a citation.
Baseline (#272) per question from its report.json (flags) and raw reduce records (tokens, wall); a question's baseline
record is the newest valid v5.2 reduce record found in the raw dirs, in the order given (the six test-A questions:
pass ev272/a-c1/raw first). --stage1: the B1 rule on the questions of the run. Every number comes from the files.
"""
from __future__ import annotations

import glob
import json
import os
import statistics as st
import sys

SIX = ["Q5", "Q10", "Q19", "Q21", "Q24", "Q26"]


def p(vals, q):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return None
    if q == 50:
        return st.median(vals)
    k = max(0, min(len(vals) - 1, round(q / 100 * (len(vals) - 1))))
    return vals[k]


def reduce_records(dirs):
    out = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*-reduce-*.json"))):
            r = json.load(open(f, encoding="utf-8"))
            q = r.get("question_id")
            if q and q not in out:
                out[q] = r
    return out


def report(path):
    return {r["id"]: r for r in json.load(open(path, encoding="utf-8"))["questions"]}


def row(qid, rep, rec):
    red = (rep or {}).get("reduce") or {}
    u = (rec or {}).get("usage") or red.get("usage") or {}
    out, rea = u.get("output_tokens"), u.get("reasoning_tokens")
    render = red.get("render") or {}
    ans = (rep or {}).get("answer") or {}
    flags = red.get("flags") or {}
    claims = ans.get("claims") or []
    cost = next((x.get("cost") or {} for x in ((rep or {}).get("cost") or {}).get("rows") or []
                 if x.get("type") == "reduce"), {})
    return {"period": cost.get("period"), "usd": cost.get("usd"), "usd_peak": cost.get("usd_peak"),"q": qid, "how": red.get("how"), "stop": (rec or {}).get("stop_reason"),
            "failed": bool((rec or {}).get("failed_call") or (rec or {}).get("invalid")),
            "out": out, "reasoning": rea, "answer_tokens": (out - rea) if out is not None and rea is not None else None,
            "wall": (rec or {}).get("wall_s"), "ttft": (rec or {}).get("ttft_s"),
            "first_claim": (rec or {}).get("first_claim_s"), "fallback": (rec or {}).get("schema_fallback"),
            "nnf": flags.get("number_not_found", 0), "outside_matrix": red.get("outside_matrix", 0),
            "uncited_shown": sum(not c.get("chunk_ids") for c in claims if "Whether or how" not in c.get("text", "")),
            **{f"r_{k}": render.get(k) for k in ("refs", "unknown_ref", "ref_part_mismatch", "dropped", "uncited",
                                                 "text_claims", "rendered_outside", "model_outside",
                                                 "rendered_number_not_found", "model_number_not_found")},
            "model_outside_list": (render.get("lists") or {}).get("model_outside", [])}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    run_dir, base_report, base_raw = args[0], args[1], args[2].split(",")
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    rep = report(os.path.join(run_dir, "report.json"))
    recs = reduce_records([os.path.join(run_dir, "raw")])
    brep, brecs = report(base_report), reduce_records(base_raw)
    qs = [q for q in rep if (rep[q].get("reduce") or {}).get("how") not in (None, "no_call", "code_built")]
    rows = [row(q, rep[q], recs.get(q)) for q in qs]
    base = [row(q, brep.get(q), brecs.get(q)) for q in qs]
    lines = ["| Q | how | out (#272) | reasoning (#272) | answer tok (#272) | wall s (#272) | first claim s | refs | "
             "unknown / mismatch / dropped | text claims | nnf model / rendered (#272 final) | outside matrix | "
             "model-text figures outside matrix |", "|" + "---|" * 13]
    for a, b in zip(rows, base):
        lines.append(f"| {a['q']} | {a['how']} | {a['out']} ({b['out']}) | {a['reasoning']} ({b['reasoning']}) | "
                     f"{a['answer_tokens']} ({b['answer_tokens']}) | {a['wall']} ({b['wall']}) | {a['first_claim']} | "
                     f"{a['r_refs']} | {a['r_unknown_ref']} / {a['r_ref_part_mismatch']} / {a['r_dropped']} | "
                     f"{a['r_text_claims']} | {a['r_model_number_not_found']} / {a['r_rendered_number_not_found']} "
                     f"({b['nnf']}) | {a['outside_matrix']} | "
                     f"{', '.join(x['figure'] for x in a['model_outside_list']) or '-'} |")
    summ = {}
    for name, rs in (("v6", rows), ("272", base)):
        for k in ("out", "reasoning", "answer_tokens", "wall", "ttft", "first_claim"):
            vals = [r[k] for r in rs]
            summ[f"{name}_{k}"] = (p(vals, 50), p(vals, 90), max([v for v in vals if v is not None], default=None))
        for k in ("nnf", "outside_matrix", "uncited_shown", "r_unknown_ref", "r_ref_part_mismatch", "r_dropped",
                  "r_uncited", "r_rendered_outside", "r_model_outside", "r_rendered_number_not_found",
                  "r_model_number_not_found", "r_text_claims", "r_refs"):
            summ[f"{name}_{k}_sum"] = sum(r[k] or 0 for r in rs)
        summ[f"{name}_reduce_usd"] = round(sum(r["usd"] or 0 for r in rs), 4)
        summ[f"{name}_reduce_usd_at_peak"] = round(sum(r["usd_peak"] or 0 for r in rs), 4)
        summ[f"{name}_periods"] = {k: sum(r["period"] == k for r in rs) for k in {r["period"] for r in rs}}
        summ[f"{name}_cut_invalid_failed"] = sum(r["failed"] or r["stop"] == "length" or r["how"] in ("invalid", "failed")
                                                 for r in rs)
        summ[f"{name}_fallback_questions"] = [r["q"] for r in rs if r["fallback"]]
    out = {"questions": qs, "summary": summ, "rows": rows, "baseline_rows": base}
    if "--stage1" in sys.argv:
        b_out, b_wall = p([r["out"] for r in base], 50), p([r["wall"] for r in base], 50)
        checks = {
            "unknown_ref == 0": summ["v6_r_unknown_ref_sum"] == 0,
            "ref_part_mismatch == 0": summ["v6_r_ref_part_mismatch_sum"] == 0,
            "no_citation before the move == 0": summ["v6_r_uncited_sum"] == 0,
            "outside_matrix == 0": summ["v6_outside_matrix_sum"] == 0,
            "cut / invalid / failed == 0": summ["v6_cut_invalid_failed"] == 0,
            "number_not_found in model text <= 8": summ["v6_r_model_number_not_found_sum"] <= 8,
            "number_not_found in rendered text == 0": summ["v6_r_rendered_number_not_found_sum"] == 0,
            f"output p50 <= 0.60 x {b_out} = {0.6 * b_out:.0f}": summ["v6_out"][0] <= 0.6 * b_out,
            f"wall p50 <= 0.70 x {b_wall} = {0.7 * b_wall:.1f}": summ["v6_wall"][0] <= 0.7 * b_wall,
        }
        out["stage1"] = {"checks": checks, "continue": all(checks.values())}
    text = "\n".join(lines) + "\n\n```json\n" + json.dumps({k: v for k, v in out.items() if k not in ("rows", "baseline_rows")},
                                                           indent=1) + "\n```\n"
    if md:
        open(md, "w", encoding="utf-8").write(text)
        json.dump(out, open(md.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), indent=1)
    print(text)


if __name__ == "__main__":
    main()
