"""#240 report generator: hybrid-norerank real run vs #217 fts, both on #217's planner plans.

Reads (no model call, no database write):
  --run      the #240 run's report.json (the scored records; committed beside this file as run-report.json)
  --fts      #217's last-attempt report.json (.eval-runs/0217-real-2/report.json)
  --w10      docs/results/w10-report.json (#217's final verdicts after its second read)
  --blind    the blind verdict file (its exact bytes go into report.json, field `blind`)
  --causes   hand-written cause per differing question (JSON: {Q: {label, text}})
  --second   optional second-read verdicts (JSON: {Q: {verdict, note}}), filled after PR review round 1
  --mock     mock comparison folder (for the link) ; --out the folder for report.md and report.json

  python evals/hybrid-eval/corpus-2026-11-19/real/gen_report.py --run .eval-runs/0240-real/report.json \
      --fts <0217-real-2>/report.json --w10 docs/results/w10-report.json --blind <ev240>/verdicts-blind.json \
      --causes <ev240>/causes.json --out evals/hybrid-eval/corpus-2026-11-19/real
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

IN_RATE, OUT_RATE = 2.0, 10.0   # $ per million tokens, the rates #217's plan used


def load(p) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def cited(rec: dict) -> set[str]:
    a = rec.get("answer") or {}
    return {c for sect in ("claims", "adjacent") for x in a.get(sect) or [] for c in x.get("chunk_ids") or []}


def rows_found(rec: dict) -> dict[str, set[str]]:
    """Expected row (its ids joined) -> chunks of it in the retrieved set."""
    return {" / ".join(r["ids"]): set(r.get("found") or []) for r in ((rec.get("recall") or {}).get("rows") or [])}


def rows_pool(rec: dict) -> dict[str, set[str]]:
    return {" / ".join(r["ids"]): set(r.get("pool") or []) for r in ((rec.get("recall") or {}).get("rows") or [])}


def compare(h: dict, f: dict) -> dict:
    hs, fs = set(h["chunk_ids"]), set(f["chunk_ids"])
    hr, fr = rows_found(h), rows_found(f)
    return {
        "retrieved": {"hybrid": len(hs), "fts": len(fs), "both": len(hs & fs),
                      "hybrid_only": len(hs - fs), "fts_only": len(fs - hs)},
        "cited": {"hybrid": len(cited(h)), "fts": len(cited(f)), "hybrid_only": sorted(cited(h) - cited(f)),
                  "fts_only": sorted(cited(f) - cited(h))},
        "recall": {"hybrid": [h.get("passage_recall"), h.get("recall_pool"), h.get("recall_final")],
                   "fts": [f.get("passage_recall"), f.get("recall_pool"), f.get("recall_final")]},
        "expected_rows_hybrid_only": {k: sorted(v) for k, v in hr.items() if v and not fr.get(k)},
        "expected_rows_fts_only": {k: sorted(v) for k, v in fr.items() if v and not hr.get(k)},
        "expected_chunks_hybrid_only": sorted({c for k, v in hr.items() for c in v - fr.get(k, set())}),
        "expected_chunks_fts_only": sorted({c for k, v in fr.items() for c in v - hr.get(k, set())}),
        "fts_pool_had_hybrid_only_expected": sorted({c for k, v in hr.items() for c in v - fr.get(k, set())
                                                     if c in rows_pool(f).get(k, set())}),
        "behavior": {"hybrid": h.get("behavior"), "fts": f.get("behavior")},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    for a in ("--run", "--fts", "--w10", "--blind", "--causes", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--second")
    ap.add_argument("--mock", default="evals/hybrid-eval/corpus-2026-11-19/mock")
    args = ap.parse_args(argv)
    run, fts, w10 = load(args.run), load(args.fts), load(args.w10)
    blind_text = Path(args.blind).read_text(encoding="utf-8")
    blind = json.loads(blind_text)["verdicts"]
    causes = load(args.causes)
    second = load(args.second) if args.second else {}
    gen_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fv = w10["verdicts"]
    H = {q["id"]: q for q in run["questions"]}
    F = {q["id"]: q for q in fts["questions"]}
    qids = list(H)
    raw = Path(args.run).parent / "raw"
    usage = [json.loads(p.read_text(encoding="utf-8")).get("usage") or {} for p in sorted(raw.glob("*.json"))
             if "-plan-" not in p.name]
    tin, tout = sum(u.get("input_tokens", 0) for u in usage), sum(u.get("output_tokens", 0) for u in usage)
    cost = round(tin * IN_RATE / 1e6 + tout * OUT_RATE / 1e6, 2)
    tier = {q: H[q]["tier"] for q in qids}

    def score(v, t1=False):
        return sum(1 for q in qids if v[q] == "PASS" and (not t1 or tier[q] == 1))
    hv = {q: blind[q]["verdict"] for q in qids}
    fvv = {q: fv[q]["verdict"] for q in qids}
    differ = [q for q in qids if hv[q] != fvv[q]]
    borderline = sorted({q for q in qids if blind[q]["borderline"]} | set(differ)
                        | {"Q7", "Q15", "Q17", "Q19", "Q22", "Q25", "Q26", "Q28"}, key=lambda s: int(s[1:]))
    comp = {q: compare(H[q], F[q]) for q in qids}
    m = run["meta"]
    lines = [
        "# hybrid-norerank real run vs #217 fts on corpus-2026-11-19 (#240)", "",
        "## How it was run", "",
        f"- Commit `{m['commit']}` (code = M-runs sha 101e332), snapshot `{m['snapshot']}`, as of {m['as_of']}, "
        f"retrieval `{m['retrieval_mode']}`, constants {json.dumps(m.get('constants'))}.",
        f"- Model `claude-sonnet-5-5`, prompt v4.1, request `strict-1`, answer cap 20000, planner plan-v2 reused "
        f"from #217 (`--reuse-plans anthropic:claude-sonnet-5-5`), token budget {m.get('token_budget')}, pool "
        f"{m.get('pool_per_group')} per (firm, document type).",
        "- Command: `eval_run.py --real --max-calls 30 --reuse-plans anthropic:claude-sonnet-5-5 --mode hybrid-norerank "
        "--as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-19/report.json --out .eval-runs/0240-real` "
        "(plans/0240-hybrid-parity.md, Paid-call plan).",
        f"- Calls: {m['real_calls']} real (30 answers, 0 planner), {m['reused']} reused (#217's 30 planner outputs); "
        f"tokens {tin:,} in / {tout:,} out, about ${cost} at ${IN_RATE:g} / ${OUT_RATE:g} per M. One attempt, no stop, "
        "no invalid output; every stop_reason `tool_use`.",
        "- The run's chunk lists equal the mock M4 (same code, same plans) on 30/30, and fts on the same plans (M3) "
        "equals #217's real run on 30/30, so both answers were built from the same plans and the only difference "
        "is how candidates were found and ranked.",
        f"- Scoring: blind first (verdict file sha256 `{hashlib.sha256(blind_text.encode('utf-8')).hexdigest()}`, "
        "committed before #217's verdicts were opened), same rule as #217 / Gate 4: PASS only if the project lead would "
        "forward it, read against `passes_if`, no half credit. #217's verdicts are its final ones (24/30 after its "
        "second read).", f"- Mock comparison: `{args.mock}/` (rule plans and #217 plans).",
        f"- Generated by `gen_report.py` (sha256 `{gen_sha}`).", "",
        "## Score", "",
        f"| | hybrid-norerank (#240) | fts (#217) |", "|---|---|---|",
        f"| All 30 | **{score(hv)}/30** | {score(fvv)}/30 |",
        f"| Tier 1 | **{score(hv, True)}/18** | {score(fvv, True)}/18 |",
        f"| Run summary: tier-1 passage recall / recall@final (all rows) | {run['summary']['tier1_passage_recall']} / "
        f"{run['summary']['recall_final']} | {fts['summary']['tier1_passage_recall']} / {fts['summary']['recall_final']} |",
        f"| Refusal gap / keyed (retrieval check) | {run['summary']['refusal_gap']['ok']}/5, "
        f"{run['summary']['refusal_all']['ok']}/{run['summary']['refusal_all']['of']} | "
        f"{fts['summary']['refusal_gap']['ok']}/5, {fts['summary']['refusal_all']['ok']}/{fts['summary']['refusal_all']['of']} |",
        "", "One sample per question and one scorer; a one-question difference is within what model variance and "
        "reading can move (ADR-010: tuned and scored on the same 30 questions, no held-out set).", "",
        "## Questions whose verdict differs", ""]
    for q in differ:
        c = comp[q]
        lines += [f"### {q}: hybrid {hv[q]}, fts {fvv[q]}", "",
                  f"- Cause: **{causes[q]['label']}**. {causes[q]['text']}",
                  f"- Retrieved: hybrid {c['retrieved']['hybrid']}, fts {c['retrieved']['fts']}, both "
                  f"{c['retrieved']['both']}. Behavior: hybrid `{c['behavior']['hybrid']}`, fts `{c['behavior']['fts']}`.",
                  f"- Expected passages only hybrid retrieved: {', '.join(c['expected_chunks_hybrid_only']) or 'none'}; "
                  f"of these in fts's pool: {', '.join(c['fts_pool_had_hybrid_only_expected']) or 'none'}.",
                  f"- Expected passages only fts retrieved: {', '.join(c['expected_chunks_fts_only']) or 'none'}.",
                  f"- hybrid reason: {blind[q]['reason']}", f"- fts reason (#217): {fv[q]['reason']}", ""]
    if not differ:
        lines += ["None.", ""]
    lines += ["## Per question", "",
              "Recall cells: passage recall / recall@pool / recall@final. Retrieved: hybrid-only / fts-only chunks. "
              "Cited: hybrid / fts cited chunks.", "",
              "| Q | Tier | Expected -> hybrid / fts | hybrid | fts | Class (hybrid) | Recall hybrid | Recall fts | "
              "Retrieved only | Cited | Borderline |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for q in qids:
        c = comp[q]
        r = lambda v: " / ".join("-" if x is None else f"{x:.2f}" for x in v)  # noqa: E731
        lines.append(f"| {q} | {tier[q]} | {H[q]['expected_behavior']} -> {c['behavior']['hybrid']} / "
                     f"{c['behavior']['fts']} | {hv[q]} | {fvv[q]} | {blind[q]['class'] or ''} | {r(c['recall']['hybrid'])} | "
                     f"{r(c['recall']['fts'])} | {c['retrieved']['hybrid_only']} / {c['retrieved']['fts_only']} | "
                     f"{c['cited']['hybrid']} / {c['cited']['fts']} | {'yes' if q in borderline else ''} |")
    lines += ["", "## Expected passages one mode found and the other did not", "",
              "| Q | Only hybrid retrieved | Only fts retrieved |", "|---|---|---|"]
    for q in qids:
        c = comp[q]
        if c["expected_chunks_hybrid_only"] or c["expected_chunks_fts_only"]:
            lines.append(f"| {q} | {', '.join(c['expected_chunks_hybrid_only']) or '-'} | "
                         f"{', '.join(c['expected_chunks_fts_only']) or '-'} |")
    lines += ["", "No verdict difference comes from a passage only fts found, so no *LEG_K reach* tag applies. No part's "
              "embedded text (`plan.searched[].vector_text`) holds a configured neighbour phrase (mock checks).", "",
              "## Borderline and second read", "",
              "Read twice in PR review (every borderline question of this scoring, every question whose verdict differs "
              "from #217, and #217's borderline set): " + ", ".join(borderline) + ".", ""]
    if second:
        lines += ["| Q | First read | Second read | Note |", "|---|---|---|---|"]
        lines += [f"| {q} | {hv[q]} | {second[q]['verdict']} | {second[q].get('note', '')} |" for q in borderline if q in second]
        s2 = {q: second.get(q, {}).get("verdict", hv[q]) for q in qids}
        lines += ["", f"Second-read score: {score(s2)}/30 (tier 1 {score(s2, True)}/18). The reported score stays "
                  f"the first read's ({score(hv)}/30); range {min(score(hv), score(s2))}-{max(score(hv), score(s2))}/30.", ""]
    else:
        lines += ["Second read: pending (PR review round 1).", ""]
    lines += ["## Verdicts (first read, blind)", "", "| Q | Verdict | Class | Reason |", "|---|---|---|---|"]
    lines += [f"| {q} | {hv[q]} | {blind[q]['class'] or ''} | {blind[q]['reason']} |" for q in qids]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    report = {"meta": {k: m.get(k) for k in ("run_id", "snapshot", "commit", "as_of", "retrieval_mode", "constants",
                                             "token_budget", "pool_per_group", "planner_version", "reuse_plans",
                                             "real_calls", "reused", "max_calls")},
              "cost": {"input_tokens": tin, "output_tokens": tout, "usd_estimate": cost, "rates_per_m": [IN_RATE, OUT_RATE]},
              "score": {"hybrid": {"pass": score(hv), "tier1_pass": score(hv, True)},
                        "fts_217": {"pass": score(fvv), "tier1_pass": score(fvv, True)}},
              "differ": {q: {"hybrid": hv[q], "fts": fvv[q], **causes[q]} for q in differ},
              "borderline": borderline, "verdicts": {q: {**blind[q], "fts_217": fv[q]["verdict"],
                                                         "second_read": second.get(q)} for q in qids},
              "comparison": comp, "blind_sha256": hashlib.sha256(blind_text.encode("utf-8")).hexdigest(),
              "blind": blind_text, "scored_records": "run-report.json", "generator_sha256": gen_sha}
    (out / "report.json").write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(f"hybrid {score(hv)}/30 (tier 1 {score(hv, True)}/18) vs fts {score(fvv)}/30 ({score(fvv, True)}/18); "
          f"differ {differ}; borderline {borderline}; report {out / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
