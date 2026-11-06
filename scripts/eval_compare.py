"""Three-mode comparison report for #126: fts, hybrid-norerank and hybrid, each at the constants the
selection rule picked and at its default before #126 (all numbers come from eval_run.py reports).

  python scripts/eval_compare.py \
      --chosen fts=<report.json> --chosen hybrid-norerank=<report.json> --chosen hybrid=<report.json> \
      --default fts=<report.json> --default hybrid-norerank=<report.json> --default hybrid=<report.json> \
      --grid fts=<grid.json> --grid hybrid-norerank=<grid.json> --grid hybrid=<grid.json> \
      --diag .eval-runs/p125r-diag/diag.json --notes <findings.md> --out evals/hybrid-eval/corpus-2026-10-29

Writes report.md and summary.json in --out. No database, no model, no network.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODES = ("fts", "hybrid-norerank", "hybrid")
REFUSAL_IDS = ("Q24", "Q25", "Q28", "Q29", "Q30")
Q29_WATCH = "MS-10K-2025#702"


def _pairs(values: list[str] | None, what: str) -> dict[str, Path]:
    out = {}
    for v in values or []:
        mode, _, path = v.partition("=")
        if mode not in MODES or not path:
            raise SystemExit(f"--{what} takes MODE=PATH with MODE in {', '.join(MODES)}; got {v!r}")
        out[mode] = Path(path)
    return out


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _frac(block: dict | None) -> str:
    return f"{block['ok']}/{block['of']}" if block and block.get("of") else "-"


def _const(meta: dict) -> str:
    c = meta.get("constants") or {}
    return f"FLOOR {c.get('FLOOR')}, MAX_PER_DOC {c.get('MAX_PER_DOC')}, DUP_JACCARD {c.get('DUP_JACCARD')}"


def mode_row(mode: str, report: dict) -> dict:
    s, m, qs = report["summary"], report["meta"], report["questions"]
    return {"mode": mode, "constants": m.get("constants"), "commit": m.get("commit"), "run_id": m.get("run_id"),
            "pass": sum(q["status"] == "PASS" for q in qs), "fail": sum(q["status"] == "FAIL" for q in qs),
            "tier1_doc_recall": s["tier1_doc_recall"], "tier1_passage_recall": s["tier1_passage_recall"],
            "refusal_gap": s["refusal_gap"], "refusal_all": s["refusal_all"],
            "refusal_by_question": {q["id"]: q.get("refusal_ok") for q in qs if q["id"] in REFUSAL_IDS},
            "forbidden_hits": sum(len(q["forbidden"]) for q in qs),
            "dup_pairs_trigram_over": s.get("dup_pairs_trigram_over"), "dup_max_trigram": s.get("dup_max_trigram"),
            "dup_pairs_5gram_over": s.get("dup_pairs_5gram_over"), "dup_max_5gram": s.get("dup_max_5gram"),
            "median_search_s": s.get("median_search_s"), "p90_search_s": s.get("p90_search_s"),
            "max_search_s": s.get("max_search_s"), "warmup_s": m.get("warmup_s"), "cpu": m.get("cpu"),
            "real_calls": m.get("real_calls"), "provider_mode": m.get("mode")}


def summary_table(rows: list[dict]) -> list[str]:
    lines = ["| Mode | Constants | PASS / FAIL | Tier-1 docs | Tier-1 passages | Refusal Q24, Q25, Q28-Q30 | "
             "Refusal all keyed | Forbidden hits | Dup pairs > 0.9 (trigram / 5-gram; max trigram) | "
             "Search s median / p90 / max (warm-up) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["constants"] or {}
        lines.append(f"| `{r['mode']}` | FLOOR {c.get('FLOOR')}, MAX_PER_DOC {c.get('MAX_PER_DOC')}, DUP_JACCARD "
                     f"{c.get('DUP_JACCARD')} | {r['pass']} / {r['fail']} | {r['tier1_doc_recall']} | "
                     f"{r['tier1_passage_recall']} | {_frac(r['refusal_gap'])} | {_frac(r['refusal_all'])} | "
                     f"{r['forbidden_hits']} | {r['dup_pairs_trigram_over']} / {r['dup_pairs_5gram_over']}; "
                     f"{r['dup_max_trigram']} | {r['median_search_s']} / {r['p90_search_s']} / {r['max_search_s']} "
                     f"({r['warmup_s']}) |")
    return lines


def _passages(q: dict) -> str:
    rec = q.get("recall") or {}
    return f"{rec['passages_found']}/{rec['passages']}" if rec.get("passages") else "-"


def per_question(chosen: dict[str, dict]) -> list[str]:
    ids = [q["id"] for q in chosen["fts"]["questions"]]
    by = {m: {q["id"]: q for q in chosen[m]["questions"]} for m in chosen}
    head = "| Q | Expected | " + " | ".join(f"`{m}` status (passages, coverage)" for m in MODES) + " | Change vs fts |"
    lines = [head, "|---|---|" + "---|" * len(MODES) + "---|"]
    for qid in ids:
        cells, changes = [], []
        for m in MODES:
            q = by[m][qid]
            cov = "-" if q["coverage"] is None else f"{q['hit_patterns']}/{q['available_patterns']}"
            cells.append(f"{q['status']} ({_passages(q)}, {cov})")
            if m != "fts" and q["status"] != by["fts"][qid]["status"]:
                changes.append(f"{m}: {by['fts'][qid]['status']} -> {q['status']}")
        lines.append(f"| {qid} | {by['fts'][qid]['expected_behavior']} | " + " | ".join(cells)
                     + f" | {'; '.join(changes) or '-'} |")
    return lines


def refusal_table(chosen: dict[str, dict]) -> list[str]:
    lines = ["| Q | " + " | ".join(f"`{m}`" for m in MODES) + " |", "|---|" + "---|" * len(MODES)]
    for qid in REFUSAL_IDS:
        cells = []
        for m in MODES:
            q = next((q for q in chosen[m]["questions"] if q["id"] == qid), None)
            if q is None:
                cells.append("not run")
                continue
            bad = q.get("misleading") or []
            cells.append("-" if q.get("refusal_ok") is None else "ok" if q["refusal_ok"] else f"FAIL ({', '.join(bad)})")
        lines.append(f"| {qid} | " + " | ".join(cells) + " |")
    return lines


def rerank_vs_norerank(chosen: dict[str, dict]) -> tuple[list[str], dict]:
    a = {q["id"]: q for q in chosen["hybrid-norerank"]["questions"]}
    b = {q["id"]: q for q in chosen["hybrid"]["questions"]}
    better = worse = same = 0
    lines = ["| Q | `hybrid-norerank` status, passages | `hybrid` status, passages | Shared hits |",
             "|---|---|---|---|"]
    for qid, qa in a.items():
        qb = b[qid]
        pa = (qa.get("recall") or {}).get("passages_found") or 0
        pb = (qb.get("recall") or {}).get("passages_found") or 0
        better += pb > pa
        worse += pb < pa
        same += pb == pa
        if qa["status"] != qb["status"] or pa != pb:
            shared = len(set(qa["chunk_ids"]) & set(qb["chunk_ids"]))
            lines.append(f"| {qid} | {qa['status']}, {_passages(qa)} | {qb['status']}, {_passages(qb)} | "
                         f"{shared} of {len(qb['chunk_ids'])} |")
    return lines, {"rerank_more_passages": better, "rerank_fewer_passages": worse, "same_passages": same}


def q29_section(chosen: dict[str, dict], diag: dict | None) -> list[str]:
    lines = ["MS 10-K chunks each mode returns for Q29 (score = the mode's `Hit.rank`: ts_rank, RRF, or "
             "cross-encoder sigmoid):", ""]
    for m in MODES:
        q = next((q for q in chosen[m]["questions"] if q["id"] == "Q29"), None)
        if q is None:
            lines.append(f"- `{m}`: Q29 not run")
            continue
        ms10k = [f"`{c}` ({r})" for c, r in zip(q["chunk_ids"], q.get("ranks") or [None] * len(q["chunk_ids"]))
                 if c.startswith("MS-10K-2025#")]
        lines.append(f"- `{m}`: {q['status']}, coverage {q['coverage']}; MS 10-K: {', '.join(ms10k) or 'none'}; "
                     f"`{Q29_WATCH}` {'returned' if Q29_WATCH in q['chunk_ids'] else 'not returned'}")
    if diag and diag.get("Q29"):
        d = diag["Q29"]
        lines += ["", "Cross-encoder scores in the #125 diagnosis (`.eval-runs/p125r-diag/diag.json`, `hybrid`, "
                  "50-candidate pool, MiniLM-L-12, sigmoid):", ""]
        lines.append("- top 5 of the pool: " + ", ".join(f"`{c}` {s}" for c, s in d.get("top5", [])))
        for w in d.get("watch", []):
            if w.get("in_pool"):
                lines.append(f"- `{w['chunk']}` ({w['role']}): keyword rank {w['kw_rank_in_firm']}, vector rank "
                             f"{w['vec_rank_in_firm']}, sigmoid {w['sigmoid']}, pool rank {w['pool_rank']} of "
                             f"{d.get('pool_size')}, returned {w['in_hybrid_hits']}")
    lines += ["", f"`{Q29_WATCH}` is not on Q29's `must_not_return` list in `evals/expected_chunks.yaml`, so it "
              "counts as neither forbidden nor misleading: it changes only those counts if the key were extended "
              "(C1's call), never PASS. Q29 fails in `hybrid` on coverage (no Wealth Management 10-K chunk), not on "
              "refusal. No answer-key change and no Q29-specific rule here."]
    return lines


def grid_section(mode: str, grid: dict) -> list[str]:
    lines = [f"### `{mode}`", "", "| FLOOR | MAX_PER_DOC | PASS | Tier-1 docs | Passages | Refusal gap | "
             "Refusal all | Forbidden | Dup > 0.9 (trigram / 5-gram) | Median s |", "|---|---|---|---|---|---|---|---|---|---|"]
    for p in grid["points"]:
        s = p["summary"]
        lines.append(f"| {p['floor']} | {p['max_per_doc']} | {s.get('pass')} | {s['tier1_doc_recall']} | "
                     f"{s['tier1_passage_recall']} | {_frac(s['refusal_gap'])} | {_frac(s['refusal_all'])} | "
                     f"{s.get('forbidden_hits')} | {s.get('dup_pairs_trigram_over')} / {s.get('dup_pairs_5gram_over')} | "
                     f"{s['median_search_s']} |")
    pick = grid["choice"]["pick"]
    lines += ["", "Pick: " + (f"FLOOR {pick['floor']}, MAX_PER_DOC {pick['max_per_doc']}" if pick else "none")
              + f". {grid['choice']['reason']}.", ""]
    for name, reasons in grid["choice"].get("not_eligible", {}).items():
        lines.append(f"- not eligible {name}: {'; '.join(reasons)}")
    return lines + [""]


def latency_table(chosen: dict[str, dict]) -> list[str]:
    lines = ["| Q | " + " | ".join(f"`{m}` s" for m in MODES) + " |", "|---|" + "---|" * len(MODES)]
    by = {m: {q["id"]: q for q in chosen[m]["questions"]} for m in MODES}
    for qid in by["fts"]:
        lines.append(f"| {qid} | " + " | ".join(str(by[m][qid].get("search_s")) for m in MODES) + " |")
    return lines


def build(chosen: dict[str, dict], defaults: dict[str, dict], grids: dict[str, dict], diag: dict | None,
          notes: str | None) -> tuple[str, dict]:
    rows = [mode_row(m, chosen[m]) for m in MODES]
    drows = [mode_row(m, defaults[m]) for m in MODES if m in defaults]
    meta = chosen["fts"]["meta"]
    rr_lines, rr = rerank_vs_norerank(chosen)
    rule = next(iter(grids.values()))["rule"] if grids else "-"
    lines = ["# Retrieval modes compared: fts, hybrid-norerank, hybrid (#126)", "",
             f"Snapshot `{meta['snapshot']}`, as of {meta['as_of']}, k={meta['k']}, min coverage "
             f"{meta['min_coverage']}, mock provider, {sum(r['real_calls'] or 0 for r in rows)} real calls. "
             f"CPU: {rows[-1]['cpu']}. Commits: " + ", ".join(f"{r['mode']} `{r['commit']}`" for r in rows) + ".", "",
             "Modes: `fts` = keyword search (`main`'s mode). `hybrid-norerank` = keyword + vector legs fused by RRF "
             "per firm, 50-candidate pool by (firm, document type), final order by RRF score. `hybrid` = the same "
             "candidates, final order by the local cross-encoder (Xenova/ms-marco-MiniLM-L-12-v2). FLOOR is "
             "relative: fts on ts_rank, both hybrid modes on the RRF score before any rerank (the cross-encoder "
             "sigmoid is not a ratio scale). Time-window questions have no floor in any mode; the window cap (8) "
             "and the research cap (2) are not tuned. fts's DUP_JACCARD is measured, never changed.", "",
             "This report gives numbers; the decision on the default mode is #127.", "",
             "## At the constants the selection rule picked", ""] + summary_table(rows) + [
             "", "## At each mode's default before #126", ""] + summary_table(drows) + [
             "", f"## Selection rule (fixed in `plans/0126-hybrid-eval.md` before any grid run)", "", rule, "",
             "Tuned and scored on the same 30 questions (no held-out set): one passage is about 0.02 of tier-1 "
             "passage recall, so small differences are weak evidence.", ""]
    if notes:
        lines += ["## Findings", "", notes.strip(), ""]
    lines += ["## PASS / FAIL per question (chosen constants)", "", "Status, passages found / expected "
              "(answer key), expected-source coverage.", ""] + per_question(chosen)
    lines += ["", "## Refusal questions", ""] + refusal_table(chosen)
    lines += ["", "## Is the cross-encoder reliable on this financial text? (input for #127)", "",
              f"Same candidates, different order: across the 30 questions the cross-encoder finds more answer "
              f"passages than RRF order on {rr['rerank_more_passages']}, fewer on {rr['rerank_fewer_passages']}, the "
              f"same on {rr['same_passages']}. Questions where status or passages differ:", ""] + rr_lines
    lines += ["", "### Q29 (what Morgan Stanley pays its advisors)", ""] + q29_section(chosen, diag)
    lines += ["", "## Duplicate measure", "",
              "Every pair of final hits per question: (a) character trigram similarity computed like pg_trgm's "
              "`similarity()` (Python re-implementation: pg_trgm is not installed in `cee-db`; lower case, words = "
              "runs of letters and digits, each padded with two spaces in front and one behind, shared trigrams / "
              "all distinct trigrams); (b) word 5-gram Jaccard, the measure `select()` dedupes with (DUP_JACCARD). "
              "Spec: no two hits > 0.9 similar. Counts are in the tables above.", ""]
    lines += ["## Grid (appendix)", ""]
    for m in MODES:
        if m in grids:
            lines += grid_section(m, grids[m])
    lines += ["## Search time per question, chosen constants (appendix)", "",
              "Seconds per `search()`; the first, untimed warm-up search (model loading) is excluded."
              " fts from its chosen grid point; the hybrid modes from their confirmation runs.", ""] + latency_table(chosen)
    summary = {"chosen": rows, "default": drows, "rerank_vs_norerank": rr, "rule": rule,
               "picks": {m: grids[m]["choice"] for m in grids},
               "per_question": {m: {q["id"]: q["status"] for q in chosen[m]["questions"]} for m in MODES}}
    return "\n".join(lines) + "\n", summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--chosen", action="append", required=True, help="MODE=report.json at the picked constants")
    ap.add_argument("--default", action="append", help="MODE=report.json at the mode's default before #126")
    ap.add_argument("--grid", action="append", help="MODE=grid.json")
    ap.add_argument("--diag", type=Path, help="#125 diagnosis (diag.json)")
    ap.add_argument("--notes", type=Path, help="findings (markdown) placed after the summary")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    chosen = {m: _load(p) for m, p in _pairs(args.chosen, "chosen").items()}
    missing = set(MODES) - set(chosen)
    if missing:
        ap.error(f"--chosen is missing {', '.join(sorted(missing))}")
    defaults = {m: _load(p) for m, p in _pairs(args.default, "default").items()}
    grids = {m: _load(p) for m, p in _pairs(args.grid, "grid").items()}
    diag = _load(args.diag) if args.diag else None
    notes = args.notes.read_text(encoding="utf-8") if args.notes else None
    text, summary = build(chosen, defaults, grids, diag, notes)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_text(text, encoding="utf-8")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"report: {args.out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
