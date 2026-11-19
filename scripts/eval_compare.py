"""Three-mode comparison report for #126: fts, hybrid-norerank and hybrid, each at the constants the
selection rule picked and at its default before #126 (all numbers come from eval_run.py reports).

  python scripts/eval_compare.py \
      --chosen fts=<report.json> --chosen hybrid-norerank=<report.json> --chosen hybrid=<report.json> \
      --default fts=<report.json> --default hybrid-norerank=<report.json> --default hybrid=<report.json> \
      --grid fts=<grid.json> --grid hybrid-norerank=<grid.json> --grid hybrid=<grid.json> \
      --diag .eval-runs/p125r-diag/diag.json --notes <findings.md> --out evals/hybrid-eval/corpus-2026-10-29

#211 (fts vs hybrid-norerank, recall by stage, the #212 decision line):

  python scripts/eval_compare.py --run fts=<report.json> --run hybrid-norerank=<report.json> \
      [--run hybrid=<report.json>] --out evals/hybrid-eval/corpus-2026-11-17

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


def rerank_vs_norerank(norerank: dict, rerank: dict) -> tuple[list[str], dict]:
    """Per question, two runs with the same candidates and constants: RRF order vs cross-encoder order."""
    a = {q["id"]: q for q in norerank["questions"]}
    b = {q["id"]: q for q in rerank["questions"]}
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


def ablation_grid(grids: dict[str, dict]) -> list[str]:
    """Every grid point both hybrid modes ran: same candidates and constants, only the order differs."""
    if "hybrid" not in grids or "hybrid-norerank" not in grids:
        return []
    plain = {(p["floor"], p["max_per_doc"]): p["summary"] for p in grids["hybrid-norerank"]["points"]}
    lines = ["| FLOOR | MAX_PER_DOC | PASS (RRF / rerank) | Tier-1 docs (RRF / rerank) | Tier-1 passages (RRF / "
             "rerank) | Median search s (RRF / rerank) |", "|---|---|---|---|---|---|"]
    for p in grids["hybrid"]["points"]:
        a, b = plain.get((p["floor"], p["max_per_doc"])), p["summary"]
        if a is None:
            continue
        lines.append(f"| {p['floor']} | {p['max_per_doc']} | {a.get('pass')} / {b.get('pass')} | "
                     f"{a['tier1_doc_recall']} / {b['tier1_doc_recall']} | {a['tier1_passage_recall']} / "
                     f"{b['tier1_passage_recall']} | {a['median_search_s']} / {b['median_search_s']} |")
    return lines


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
        lines += ["", "Cross-encoder scores in the #125 diagnosis (`p125r-diag`, committed as `inputs/p125r-diag.json`; `hybrid`, "
                  "50-candidate pool, MiniLM-L-12, sigmoid):", ""]
        lines.append("- top 5 of the pool: " + ", ".join(f"`{c}` {s}" for c, s in d.get("top5", [])))
        for w in d.get("watch", []):
            if w.get("in_pool") and w.get("role") in ("must_return", "must_not"):
                lines.append(f"- `{w['chunk']}` ({w['role']}): keyword rank {w['kw_rank_in_firm']}, vector rank "
                             f"{w['vec_rank_in_firm']}, sigmoid {w['sigmoid']}, pool rank {w['pool_rank']} of "
                             f"{d.get('pool_size')}, returned {w['in_hybrid_hits']}")
    lines += ["", f"`{Q29_WATCH}` (a guarantee note: \"likelihood of any payment by the Firm under these "
              "arrangements is remote\") is not on Q29's `must_not_return` list in `evals/expected_chunks.yaml`, so "
              "it counts as neither forbidden nor misleading: extending the key (C1's call) would change only those "
              "counts, never PASS, which depends on coverage. No answer-key change and no Q29-specific rule here."]
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
          notes: str | None, same_constants: dict | None = None, command: str | None = None) -> tuple[str, dict]:
    """same_constants: a hybrid-norerank run at the constants hybrid picked (same candidates, RRF order).
    command: the eval_compare.py call that rebuilds this report, printed in it."""
    rows = [mode_row(m, chosen[m]) for m in MODES]
    drows = [mode_row(m, defaults[m]) for m in MODES if m in defaults]
    meta = chosen["fts"]["meta"]
    plain = same_constants or chosen["hybrid-norerank"]
    rr_lines, rr = rerank_vs_norerank(plain, chosen["hybrid"])
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
              "Both hybrid modes at every grid point (same candidates and constants; only the final order "
              "differs: RRF score vs cross-encoder):", ""] + ablation_grid(grids) + [
              "", f"Per question at `hybrid`'s picked constants ({_const(chosen['hybrid']['meta'])}), "
              f"`hybrid-norerank` run with the same constants: the cross-encoder finds more answer passages on "
              f"{rr['rerank_more_passages']} questions, fewer on {rr['rerank_fewer_passages']}, the same on "
              f"{rr['same_passages']}. Questions where status or passages differ:", ""] + rr_lines
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
    if command:
        lines += ["", "## How this report was built", "",
                  "From the repo root, from committed inputs only (no database, no model):", "",
                  "```", command, "```"]
    summary = {"chosen": rows, "default": drows, "rerank_vs_norerank": rr, "rule": rule,
               "picks": {m: grids[m]["choice"] for m in grids},
               "per_question": {m: {q["id"]: q["status"] for q in chosen[m]["questions"]} for m in MODES}}
    return "\n".join(lines) + "\n", summary


# --- #211: fts vs hybrid-norerank on corpus-2026-11-17, recall by stage, decision on #212 ----------

# The decision rule, fixed in plans/0211-hybrid-retest.md (step 5) before any run.
DECISION_MARGIN = 0.03
DECISION_RULE = (
    "hybrid-norerank tier-1 passage recall >= fts + 0.03 (3 decimals), refusal 5/5 on Q24, Q25, Q28, "
    "Q29, Q30, refusal correct on every keyed question (the issue's \"10/10 keyed\": every keyed question "
    "on today's key) and 0 forbidden hits -> #212 runs; otherwise #212 is closed as not planned. hybrid "
    "(with the reranker) is a reference only; recall@pool is reported, not decided on.")
WEAK_EVIDENCE = ("0.03 of tier-1 passage recall is about 1-2 passages on this bank; tuned and scored on the "
                 "same 30 questions with no held-out set (ADR-010), so a difference this size is weak evidence.")
NOT_LIKE_FOR_LIKE = ("recall@pool is not like-for-like: fts pools 15 per (firm, document type) with no total "
                     "cap, hybrid pools RERANK_N candidates per part (50 x k / 20).")
# The passages Gate 4 named as missed (PR #218, "Known gaps"); 7 of 8 were "not in pool" for fts.
GATE4_MISSED = [("Q7", ["MS-10K-2025#153"]), ("Q15", ["SCHW-10K-2025#27"]), ("Q17", ["BAC-TR-2026Q2#21"]),
                ("Q19", ["EDJ-10K-2025#88"]), ("Q20", ["FIDELITY-III-2025#0"]),
                ("Q20", ["UBS-NEXTGEN-2026#119", "UBS-NEXTGEN-2026#13"]), ("Q25", ["MS-10K-2025#153"]),
                ("Q25", ["RJF-PR-web-affiliation-options#1"])]
STAGE_TEXT = {"final": "retrieved", "pool": "in pool, lost in select", "none": "not in pool", None: "-"}


def run_row(mode: str, report: dict) -> dict:
    s, m, qs = report["summary"], report["meta"], report["questions"]
    pools = [q["pool_size"] for q in qs if q.get("pool_size") is not None]
    return {**mode_row(mode, report),
            "recall_pool": s.get("recall_pool"), "recall_final": s.get("recall_final"),
            "tier1_recall_pool": s.get("tier1_recall_pool"), "tier1_recall_final": s.get("tier1_recall_final"),
            "with_rows": s.get("with_rows"), "tier1_with_rows": s.get("tier1_with_rows"),
            "mean_pool_size": round(sum(pools) / len(pools), 1) if pools else None,
            "passages": s.get("passages"), "tokens_est": s.get("tokens_est"), "as_of": m.get("as_of"),
            "snapshot": m.get("snapshot")}


def decide(fts_row: dict, hyb_row: dict) -> dict:
    """The #212 decision from the fts and hybrid-norerank rows (DECISION_RULE)."""
    a_fts = round(fts_row["tier1_passage_recall"] or 0.0, 3)
    a_hyb = round(hyb_row["tier1_passage_recall"] or 0.0, 3)
    need = round(a_fts + DECISION_MARGIN, 3)
    gap, keyed = hyb_row["refusal_gap"], hyb_row["refusal_all"]
    checks = {
        "A": (a_hyb >= need, f"tier-1 passage recall {a_hyb} vs fts {a_fts} + {DECISION_MARGIN} = {need}"),
        "B": (gap["of"] == len(REFUSAL_IDS) and gap["ok"] == gap["of"],
              f"refusal on Q24, Q25, Q28-Q30 {gap['ok']}/{gap['of']}"),
        "C": (keyed["of"] > 0 and keyed["ok"] == keyed["of"],
              f"refusal on every keyed question {keyed['ok']}/{keyed['of']}"),
        "D": (hyb_row["forbidden_hits"] == 0, f"forbidden hits {hyb_row['forbidden_hits']}"),
    }
    go = all(ok for ok, _ in checks.values())
    failed = [k for k, (ok, _) in checks.items() if not ok]
    line = ("**Decision: #212 runs** (all four conditions hold)." if go else
            f"**Decision: #212 is closed as not planned** (condition{'s' if len(failed) > 1 else ''} "
            f"{', '.join(failed)} not met).")
    return {"runs_212": go, "line": line, "checks": {k: {"ok": ok, "text": t} for k, (ok, t) in checks.items()}}


def _stage(report: dict, qid: str, ids: list[str]) -> str:
    q = next((x for x in report["questions"] if x["id"] == qid), None)
    rows = ((q or {}).get("recall") or {}).get("rows") or []
    row = next((r for r in rows if set(r["ids"]) & set(ids)), None)
    return STAGE_TEXT.get(row.get("stage") if row else None, "-")


def build_retest(runs: dict[str, dict], command: str | None = None, pool_note: str | None = None,
                 decision_line: bool = True, title: str | None = None) -> tuple[str, dict]:
    """pool_note (#240): the recall@pool comparability note (default the #211 text, so #211's report
    rebuilds unchanged); decision_line False: no #212 decision section (#240 compares, decides nothing);
    title: the report's first heading."""
    pool_note = NOT_LIKE_FOR_LIKE if pool_note is None else pool_note
    rows = {m: run_row(m, r) for m, r in runs.items()}
    order = [m for m in MODES if m in rows]
    decision = decide(rows["fts"], rows["hybrid-norerank"])
    f = rows["fts"]
    lines = [title or f"# fts vs hybrid-norerank on {f['snapshot']} (#211)", "",
             f"Snapshot `{f['snapshot']}`, as of {f['as_of']}, k by question (`fts.budget`), mock provider, "
             f"{sum(r['real_calls'] or 0 for r in rows.values())} real calls. CPU: {f['cpu']}. Commits: "
             + ", ".join(f"{m} `{rows[m]['commit']}`" for m in order) + ".", "",
             "Modes: `fts` = keyword search (equals `main`). `hybrid-norerank` = keyword + vector legs fused by RRF "
             "per quota firm, with every rule of `main`'s `fts.search()` (plans/0211-hybrid-retest.md R1-R11), "
             "final order by RRF score. `hybrid` = the same candidates ordered by the local cross-encoder; a "
             "reference only, it does not decide.", "",
             ]
    if decision_line:
        lines += ["## Decision", "", decision["line"], "", f"Rule (fixed before any run): {DECISION_RULE}", ""]
        lines += [f"- {k}: {'met' if c['ok'] else 'NOT met'} ({c['text']})" for k, c in decision["checks"].items()]
        lines += [""]
    lines += [WEAK_EVIDENCE, "", "## Summary", "",
              "| Mode | PASS / FAIL | Tier-1 docs | Tier-1 passages | Tier-1 recall@pool | Tier-1 recall@final "
              "| recall@pool / @final (all rows) | Mean pool size | Refusal Q24, Q25, Q28-Q30 | Refusal all keyed "
              "| Forbidden | Passages | Search s median / p90 / max (warm-up) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in order:
        r = rows[m]
        lines.append(f"| `{m}` | {r['pass']} / {r['fail']} | {r['tier1_doc_recall']} | {r['tier1_passage_recall']} | "
                     f"{r['tier1_recall_pool']} | {r['tier1_recall_final']} | {r['recall_pool']} / {r['recall_final']} | "
                     f"{r['mean_pool_size']} | {_frac(r['refusal_gap'])} | {_frac(r['refusal_all'])} | "
                     f"{r['forbidden_hits']} | {r['passages']} | {r['median_search_s']} / {r['p90_search_s']} / "
                     f"{r['max_search_s']} ({r['warmup_s']}) |")
    lines += ["", "Recall@pool: expected passages with a chunk in a candidate pool before any floor or "
              f"`select()`; recall@final: in the retrieved set (#210). {pool_note} Tier 1: "
              f"{f['tier1_with_rows']} questions with expected passages; all rows: {f['with_rows']} questions.", "",
              "## Passages Gate 4 named as missed (stage per mode)", "",
              "| Q | Passage | " + " | ".join(f"`{m}`" for m in order) + " |", "|---|---|" + "---|" * len(order)]
    gate4 = []
    for qid, ids in GATE4_MISSED:
        st = {m: _stage(runs[m], qid, ids) for m in order}
        gate4.append({"q": qid, "ids": ids, "stage": st})
        lines.append(f"| {qid} | {' / '.join(f'`{i}`' for i in ids)} | " + " | ".join(st[m] for m in order) + " |")
    lines += ["", "## Per question", "",
              "Cells: status / recall@pool / recall@final / passages found.", "",
              "| Q | " + " | ".join(f"`{m}`" for m in order) + " |", "|---|" + "---|" * len(order)]
    by_mode = {m: {q["id"]: q for q in runs[m]["questions"]} for m in order}
    diffs = []
    for qid in by_mode["fts"]:
        cells, vals = [], {}
        for m in order:
            q = by_mode[m].get(qid) or {}
            vals[m] = (q.get("status"), q.get("recall_pool"), q.get("recall_final"), q.get("passage_recall"))
            cells.append(f"{q.get('status')} / {q.get('recall_pool', '-')} / {q.get('recall_final', '-')} / "
                         f"{_passages(q) if q else '-'}")
        if vals["fts"] != vals["hybrid-norerank"]:
            diffs.append(qid)
        lines.append(f"| {'**' + qid + '**' if qid in diffs else qid} | " + " | ".join(cells) + " |")
    lines += ["", "Bold: `fts` and `hybrid-norerank` differ in status, recall@pool, recall@final or passage "
              f"recall ({len(diffs)} questions: {', '.join(diffs) or 'none'}).", ""]
    if command:
        lines += [f"Rebuilt with: `{command}`", ""]
    summary = {"rule": DECISION_RULE, "decision": decision if decision_line else None, "modes": rows,
               "gate4_missed": gate4, "differs": diffs, "weak_evidence": WEAK_EVIDENCE, "pool_note": pool_note}
    return "\n".join(lines), summary


def write_out(out: Path, text: str, summary: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_bytes(text.encode("utf-8"))  # LF on every OS
    (out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--chosen", action="append", help="MODE=report.json at the picked constants (#126)")
    ap.add_argument("--run", action="append",
                    help="#211: MODE=report.json for fts and hybrid-norerank (hybrid optional); writes the "
                         "recall-by-stage comparison and the #212 decision instead of the #126 report")
    ap.add_argument("--default", action="append", help="MODE=report.json at the mode's default before #126")
    ap.add_argument("--grid", action="append", help="MODE=grid.json")
    ap.add_argument("--diag", type=Path, help="#125 diagnosis (diag.json)")
    ap.add_argument("--notes", type=Path, help="findings (markdown) placed after the summary")
    ap.add_argument("--same-constants", type=Path,
                    help="hybrid-norerank report.json at the constants hybrid picked (reranker ablation)")
    ap.add_argument("--no-decision", action="store_true",
                    help="#240: --run without the #212 decision section (the tables only)")
    ap.add_argument("--pool-note", help="#240: the recall@pool comparability note (default: the #211 text)")
    ap.add_argument("--title", help="#240: the report's first heading (default: the #211 one)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    raw = sys.argv[1:] if argv is None else argv
    command = "python scripts/eval_compare.py " + " ".join(a.replace("\\", "/") for a in raw)
    if args.run:
        runs = {m: _load(p) for m, p in _pairs(args.run, "run").items()}
        missing = {"fts", "hybrid-norerank"} - set(runs)
        if missing:
            ap.error(f"--run is missing {', '.join(sorted(missing))}")
        text, summary = build_retest(runs, command, pool_note=args.pool_note, decision_line=not args.no_decision,
                                     title=args.title)
        write_out(args.out, text, summary)
        print(f"{summary['decision']['line'] if summary['decision'] else '(no decision line)'}\nreport: "
              f"{args.out / 'report.md'}")
        return 0
    if not args.chosen:
        ap.error("give --chosen (the #126 report) or --run (the #211 comparison)")
    chosen = {m: _load(p) for m, p in _pairs(args.chosen, "chosen").items()}
    missing = set(MODES) - set(chosen)
    if missing:
        ap.error(f"--chosen is missing {', '.join(sorted(missing))}")
    defaults = {m: _load(p) for m, p in _pairs(args.default, "default").items()}
    grids = {m: _load(p) for m, p in _pairs(args.grid, "grid").items()}
    diag = _load(args.diag) if args.diag else None
    notes = args.notes.read_text(encoding="utf-8") if args.notes else None
    same = _load(args.same_constants) if args.same_constants else None
    text, summary = build(chosen, defaults, grids, diag, notes, same, command)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_bytes(text.encode("utf-8"))  # LF on every OS
    (args.out / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print(f"report: {args.out / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
