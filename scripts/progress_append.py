"""Append a merged PR's progress line to docs/PROGRESS.md. Run by .github/workflows/progress.yml.

  python scripts/progress_append.py <github-event.json>

Reads the merged pull_request event: the first line of the PR body's `## Progress line`
section ("What landed | Blockers | Next"), or the PR title when the section is missing.
The role comes from the branch prefix (c1/..., tl/...). The row goes to the end of that
role's `### <ROLE>` table under `## Status log`. A PR that is already logged is skipped.
The PR body is untrusted text: it is only read from the event file and written as a cell.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROGRESS = Path(__file__).resolve().parents[1] / "docs" / "PROGRESS.md"
ROLES = ["C1", "C2", "C3", "S1", "S2", "U1", "TL", "Other"]
HEADER = "| Date | What landed | Blockers | Next |\n|---|---|---|---|\n"


def cell(text: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", text or "", flags=re.S)
    text = " ".join(text.split()).replace("|", "/")
    return text[:400] or "-"


def progress_line(body: str) -> list[str] | None:
    m = re.search(r"^##\s*Progress line\s*$(.*?)(?=^##\s|\Z)", body or "", flags=re.M | re.S | re.I)
    if not m:
        return None
    section = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    for line in section.splitlines():
        line = line.strip().strip("`").lstrip("-* ").strip()
        if line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            landed = parts[0]
            blockers = parts[1] if len(parts) > 1 else "-"
            nxt = " / ".join(parts[2:]) if len(parts) > 2 else "-"
            return [landed, blockers, nxt]
    return None


def role_of(branch: str) -> str:
    prefix = branch.split("/", 1)[0].upper()
    return prefix if prefix in ROLES else "Other"


def build_row(pr: dict, date: str) -> str:
    parts = progress_line(pr.get("body") or "") or [pr["title"], "-", "-"]
    landed, blockers, nxt = (cell(p) for p in parts)
    return f"| {date} | {landed} (#{pr['number']}) | {blockers} | {nxt} |\n"


def insert(text: str, role: str, row: str, number: int) -> str:
    if re.search(rf"\(#{number}\) \|", text):
        return text
    heading = f"### {role}\n"
    if heading not in text:
        log = text.index("## Status log")
        nxt = re.search(r"^## ", text[log + 3:], flags=re.M)
        end = log + 3 + nxt.start() if nxt else len(text)
        text = text[:end].rstrip("\n") + f"\n\n{heading}\n{HEADER}" + "\n" + text[end:]
    start = text.index(heading) + len(heading)
    nxt = re.search(r"^#{2,3} ", text[start:], flags=re.M)
    end = start + nxt.start() if nxt else len(text)
    section = text[start:end].rstrip("\n") + "\n" + row
    return text[:start] + section + ("\n" if nxt else "") + text[end:]


def main() -> int:
    event = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pr = event["pull_request"]
    if not pr.get("merged"):
        print("Not merged; nothing to log.")
        return 0
    row = build_row(pr, pr["merged_at"][:10])
    text = PROGRESS.read_text(encoding="utf-8")
    new = insert(text, role_of(pr["head"]["ref"]), row, pr["number"])
    if new == text:
        print(f"#{pr['number']} already logged.")
        return 0
    PROGRESS.write_text(new, encoding="utf-8", newline="\n")
    print(f"Logged #{pr['number']}: {row.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
