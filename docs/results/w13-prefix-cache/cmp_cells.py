"""#283 TL condition B3 (plans/0283-prefix-cache.md): the shared-prefix layout against #272 test B, cell by cell, 0 calls.

Both runs use the same plans, so the same cells. For every cell of the matrix (model cells: source model or
reextract, in both runs): label changed, items lost or gained (by cited chunk ids), and per item the rates of
unmatched_citation, quote_not_found and number_not_found; also the #283 cell flags (foreign_cell, unknown_cell,
unknown_ref). Trigger (fixed in the plan before any call): the unmatched_citation rate per item more than 2x #272,
or more than 10% of model cells change label -> the results doc names the layout as the suspected cause before any
score is read.
  python cmp_cells.py <new report.json> [<old report.json>] [--json out.json]
  (old default: docs/results/w12-latency/b-fts/report.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

OLD = Path(__file__).resolve().parents[1] / "w12-latency" / "b-fts" / "report.json"
ITEM_FLAGS = ("unmatched_citation", "quote_not_found", "number_not_found")
CELL_FLAGS = ("foreign_cell", "unknown_cell", "unknown_ref", "missing_cell")
MODEL = ("model", "reextract")


def cells_of(report: Path) -> dict[tuple[str, str], dict]:
    out = {}
    for q in json.loads(report.read_text(encoding="utf-8"))["questions"]:
        cs = (q.get("matrix") or {}).get("cells") or {}
        for cid, c in (cs.items() if isinstance(cs, dict) else []):
            out[(q["id"], cid)] = c
    return out


def item_keys(c: dict) -> set[tuple]:
    return {tuple(i.get("chunk_ids") or []) for i in c.get("items") or []}


def rates(cells: list[dict]) -> dict:
    items = [i for c in cells for i in c.get("items") or []]
    out = {"cells": len(cells), "items": len(items)}
    for f in ITEM_FLAGS:
        n = sum(f in (i.get("flags") or []) for i in items)
        out[f] = n
        out[f + "_rate"] = round(n / len(items), 4) if items else None
    for f in CELL_FLAGS:
        out[f] = sum(f in (c.get("flags") or []) for c in cells)
    return out


def compare(new: dict, old: dict) -> dict:
    both = [k for k in old if k in new and new[k].get("source") in MODEL and old[k].get("source") in MODEL]
    changed = [k for k in both if (new[k].get("label"), new[k].get("effective_label"))
               != (old[k].get("label"), old[k].get("effective_label"))]
    lost = [k for k in both if item_keys(old[k]) - item_keys(new[k])]
    gained = [k for k in both if item_keys(new[k]) - item_keys(old[k])]
    r_new, r_old = rates([new[k] for k in both]), rates([old[k] for k in both])
    share = round(len(changed) / len(both), 4) if both else None
    u_new, u_old = r_new["unmatched_citation_rate"], r_old["unmatched_citation_rate"]
    citation_trigger = bool(u_new and (u_old == 0 or (u_old and u_new > 2 * u_old)))
    label_trigger = bool(share is not None and share > 0.10)
    return {"model_cells_compared": len(both), "only_new": len([k for k in new if k not in old]),
            "only_old": len([k for k in old if k not in new]), "label_changed": len(changed),
            "label_changed_share": share, "items_lost": len(lost), "items_gained": len(gained),
            "new": r_new, "old": r_old, "trigger_citations": citation_trigger, "trigger_labels": label_trigger,
            "trigger": citation_trigger or label_trigger,
            "changed": [{"q": q, "cell": c, "old": old[(q, c)].get("effective_label"),
                         "new": new[(q, c)].get("effective_label")} for q, c in changed]}


def markdown(r: dict) -> str:
    n, o = r["new"], r["old"]
    lines = [f"Model cells compared: {r['model_cells_compared']} (only new {r['only_new']}, only #272 {r['only_old']}); "
             f"label changed {r['label_changed']} ({r['label_changed_share']}); items lost in {r['items_lost']} cells, "
             f"gained in {r['items_gained']}.", "",
             "| Rate per item | #272 test B | #283 |", "|---|---|---|"]
    for f in ITEM_FLAGS:
        lines.append(f"| {f} | {o[f]} / {o['items']} ({o[f + '_rate']}) | {n[f]} / {n['items']} ({n[f + '_rate']}) |")
    for f in CELL_FLAGS:
        lines.append(f"| cells with {f} | {o[f]} | {n[f]} |")
    lines += ["", f"Trigger (unmatched_citation > 2x, or > 10% labels changed): "
                  f"{'YES - name the layout as the suspected cause' if r['trigger'] else 'no'} "
                  f"(citations {r['trigger_citations']}, labels {r['trigger_labels']})."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    out_json = argv[argv.index("--json") + 1] if "--json" in argv else None
    if out_json:
        args.remove(out_json)
    new = Path(args[0])
    old = Path(args[1]) if len(args) > 1 else OLD
    r = compare(cells_of(new), cells_of(old))
    sys.stdout.write(markdown(r))
    if out_json:
        Path(out_json).write_text(json.dumps(r, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
