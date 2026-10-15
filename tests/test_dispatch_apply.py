"""dispatch_apply with a fake `gh`: validation, ordering, issue links, resumable re-runs."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dispatch_apply.py"

BODY = """### Why
w
### Goal
g
### Inputs
i
### Deliverable
d
### Acceptance
- [ ] a
### Verification
v
### Out of scope
see {issue:%s}
"""


def load(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("dispatch_apply", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "STATE", tmp_path / "state.json")
    calls, created = [], [100]
    fail = {"on": None}

    def gh(args, input_text=None):
        calls.append((args, input_text))
        if fail["on"] and any(fail["on"] in a for a in args):
            raise RuntimeError("boom")
        if args[:2] == ["label", "list"]:
            return json.dumps([{"name": n} for n in ("role:c1", "role:u1", "type:corpus")])
        if args[:2] == ["repo", "view"]:
            return "o/r"
        if args[:2] == ["issue", "create"]:
            created[0] += 1
            return f"https://github.com/o/r/issues/{created[0]}"
        if args[:2] == ["project", "item-add"]:
            return json.dumps({"id": "ITEM"})
        if args[0] == "api" and args[1].startswith("repos/o/r/issues/") and "-X" not in args and "comments" not in args[1]:
            return json.dumps({"id": 9000 + int(args[1].rsplit("/", 1)[1])})
        return ""

    monkeypatch.setattr(mod, "gh", gh)
    monkeypatch.setattr(mod, "board_fields", lambda: ("PROJ", {
        "Week": {"id": "FW", "configuration": {"iterations": [{"id": "it4", "title": "W4"}]}},
        "Role": {"id": "FR", "options": [{"id": "oc1", "name": "C1"}, {"id": "ou1", "name": "U1"}]},
        "Size": {"id": "FS", "options": [{"id": "om", "name": "M"}]},
        "Eval Qs": {"id": "FE"}}))
    return mod, calls, fail


def draft(tmp_path, **over):
    d = {"mode": "week W4", "state_time": "2026-10-11T00:00:00+00:00", "issues": [
        {"key": "a", "decision": "assign", "title": "[W4][C1] A", "role": "C1", "week": "W4",
         "size": "M", "labels": ["type:corpus"], "eval_qs": "Q1", "body": BODY % "b"},
        {"key": "b", "decision": "assign", "title": "[W4][U1] B", "role": "U1", "week": "W4",
         "size": "M", "blocked_by": [20, "key:a"], "body": BODY % "a"},
        {"key": "c", "decision": "defer", "title": "[W4][S1] C", "role": "S1", "reason": "busy"},
    ], "replies": [{"number": 12, "body": "see {issue:b}"}]}
    d.update(over)
    path = tmp_path / "draft.yaml"
    path.write_text(yaml.safe_dump(d), encoding="utf-8")
    return path


def run(mod, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["dispatch_apply.py", *map(str, argv)])
    return mod.main()


def test_check_only_changes_nothing(tmp_path, monkeypatch):
    mod, calls, _ = load(tmp_path, monkeypatch)
    assert run(mod, monkeypatch, draft(tmp_path)) == 0
    assert not [c for c in calls if c[0][:2] in (["issue", "create"], ["issue", "edit"])]
    assert not (tmp_path / "state.json").exists()


def test_rejects_vague_or_unordered_drafts(tmp_path, monkeypatch):
    mod, calls, _ = load(tmp_path, monkeypatch)
    bad = draft(tmp_path, issues=[
        {"key": "b", "decision": "assign", "title": "[W4][U1] B", "role": "U1", "week": "W4", "size": "L",
         "blocked_by": ["key:a"], "body": "### Goal\nno acceptance"},
        {"key": "a", "decision": "defer", "title": "x", "role": "C1"}])
    assert run(mod, monkeypatch, bad, "--apply") == 1
    assert not [c for c in calls if c[0][:2] == ["issue", "create"]]


def test_apply_links_and_resumes(tmp_path, monkeypatch):
    mod, calls, fail = load(tmp_path, monkeypatch)
    path = draft(tmp_path)
    fail["on"] = "comments"  # stop before the reply
    with pytest.raises(RuntimeError):
        run(mod, monkeypatch, path, "--apply")
    creates = [c for c in calls if c[0][:2] == ["issue", "create"]]
    assert len(creates) == 2 and "--assignee" in creates[0][0] and "fjingran" in creates[0][0]
    edits = {c[0][2]: c[1] for c in calls if c[0][:2] == ["issue", "edit"]}
    assert "see #102" in edits["101"] and "see #101" in edits["102"]   # forward and backward links
    deps = [c[0][3] for c in calls if "-X" in c[0]]
    assert deps == ["repos/o/r/issues/102/dependencies/blocked_by"] * 2
    week = [c for c in calls if "--iteration-id" in c[0]]
    assert week and week[0][0][-1] == "it4"

    calls.clear()
    fail["on"] = None
    assert run(mod, monkeypatch, path, "--apply") == 0
    assert not [c for c in calls if c[0][:2] in (["issue", "create"], ["issue", "edit"], ["project", "item-add"])]
    reply = [c for c in calls if "comments" in c[0][1]]
    assert reply and reply[0][1] == "see #102"
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["last_run"] == "2026-10-11T00:00:00+00:00"


def test_board_auto_add_race_uses_existing_item(tmp_path, monkeypatch):
    mod, calls, _ = load(tmp_path, monkeypatch)
    inner = mod.gh

    def gh(args, input_text=None):
        if args[:2] == ["project", "item-add"]:
            calls.append((args, input_text))
            raise RuntimeError("gh project item-add 3 failed: GraphQL: Content already exists in this project")
        if args[:2] == ["api", "graphql"]:
            calls.append((args, input_text))
            return json.dumps({"data": {"repository": {"issue": {"projectItems": {"nodes": [
                {"id": "OTHER", "project": {"id": "ELSEWHERE"}}, {"id": "FOUND", "project": {"id": "PROJ"}}]}}}}})
        return inner(args, input_text)

    monkeypatch.setattr(mod, "gh", gh)
    assert run(mod, monkeypatch, draft(tmp_path), "--apply") == 0
    edits = [c[0] for c in calls if c[0][:2] == ["project", "item-edit"]]
    assert edits and all(e[e.index("--id") + 1] == "FOUND" for e in edits)
