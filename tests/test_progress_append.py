"""scripts/progress_append.py: parse the PR's progress line and log it in the right role table."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "progress_append.py"
spec = importlib.util.spec_from_file_location("progress_append", SCRIPT)
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)

DOC = """# Progress

## Status log

### C1

| Date | What landed | Blockers | Next |
|---|---|---|---|

### TL

| Date | What landed | Blockers | Next |
|---|---|---|---|
| 2026-10-10 | Old row (#22): x | - | - |

## Weekly score (from W6)

| Date | Snapshot | X/30 | Failing IDs |
"""


def pr(number=21, body="", title="Map expansion eleven", ref="c1/2-expansion-registry"):
    return {"number": number, "body": body, "title": title, "head": {"ref": ref},
            "merged": True, "merged_at": "2026-10-14T12:00:00Z"}


def test_reads_progress_section_and_ignores_template_comment():
    body = ("## What changed\n- x\n\n## Progress line\n<!-- What landed | Blockers | Next -->\n"
            "Registry CSV, 49 rows | loader not written | TL loads it\n\n## Spec\nspecs/filings.md\n")
    assert pa.progress_line(body) == ["Registry CSV, 49 rows", "loader not written", "TL loads it"]


def test_title_fallback_and_cell_escaping():
    row = pa.build_row(pr(body="no section here", title="Fix a | b\nnow"), "2026-10-14")
    assert row == "| 2026-10-14 | Fix a / b now (#21) | - | - |\n"


def test_inserts_at_end_of_role_table_only():
    row = pa.build_row(pr(body="## Progress line\nC1 thing | - | next"), "2026-10-14")
    out = pa.insert(DOC, "C1", row, 21)
    c1 = out.split("### C1")[1].split("### TL")[0]
    assert c1.rstrip().endswith("| 2026-10-14 | C1 thing (#21) | - | next |")
    assert out.split("### TL")[1] == DOC.split("### TL")[1]


def test_idempotent_and_role_from_branch():
    row = pa.build_row(pr(), "2026-10-14")
    once = pa.insert(DOC, "C1", row, 21)
    assert pa.insert(once, "C1", row, 21) == once
    assert pa.role_of("s2/10-prompt-v0") == "S2" and pa.role_of("feature/x") == "Other"


def test_unknown_role_gets_its_own_section_before_next_h2():
    out = pa.insert(DOC, "Other", "| d | x (#5) | - | - |\n", 5)
    assert out.index("### Other") < out.index("## Weekly score")
    assert "| d | x (#5) | - | - |" in out.split("### Other")[1].split("## Weekly")[0]


def test_main_writes_file(tmp_path, monkeypatch):
    doc = tmp_path / "PROGRESS.md"
    doc.write_text(DOC, encoding="utf-8")
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": pr(number=28, ref="tl/28-progress-bot",
                                                    body="## Progress line\nBot logs PROGRESS | - | -")}), encoding="utf-8")
    monkeypatch.setattr(pa, "PROGRESS", doc)
    monkeypatch.setattr("sys.argv", ["progress_append.py", str(event)])
    assert pa.main() == 0
    assert "| 2026-10-14 | Bot logs PROGRESS (#28) | - | - |" in doc.read_text(encoding="utf-8").split("### TL")[1]
