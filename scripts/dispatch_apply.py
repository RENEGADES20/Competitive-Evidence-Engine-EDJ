"""Apply a dispatch draft that the tech lead approved. Windows and macOS.

  python scripts/dispatch_apply.py .dispatch/draft-<...>.yaml           # check and show, change nothing
  python scripts/dispatch_apply.py .dispatch/draft-<...>.yaml --apply   # create issues, post replies

Only entries with `decision: assign` become issues. For each: create the issue (labels,
assignee from config/team.yaml), add it to the board with Week/Role/Size/Eval Qs/Firm, and
record "blocked by" links (an issue number, or `key:<key>` for an issue created earlier in
the same draft). `{issue:<key>}` in any body becomes `#N` once that issue exists. Replies are posted as issue/PR comments. Safe to re-run:
finished steps are recorded in <draft>.applied.json and skipped. Finally the time the draft's
state snapshot was taken becomes the new "last dispatch run" (.dispatch/state.json).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TEAM = yaml.safe_load((REPO / "config/team.yaml").read_text(encoding="utf-8"))
STATE = REPO / ".dispatch" / "state.json"
ROLES = set(TEAM["roles"])
SECTIONS = ["Why", "Goal", "Inputs", "Deliverable", "Acceptance", "Verification", "Out of scope"]
SIZES = {"S", "M"}


def gh(args: list[str], input_text: str | None = None) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", cwd=REPO,
                       input=input_text)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} failed: {r.stderr.strip()[:400]}")
    return r.stdout.strip()


def repo_name() -> str:
    return gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])


def board_fields() -> tuple[str, dict]:
    p = TEAM["project"]
    q = """query($owner:String!,$n:Int!){ user(login:$owner){ projectV2(number:$n){ id
      fields(first:30){ nodes{
        ... on ProjectV2Field{ id name }
        ... on ProjectV2SingleSelectField{ id name options{ id name } }
        ... on ProjectV2IterationField{ id name configuration{ iterations{ id title } } } } } } } }"""
    data = json.loads(gh(["api", "graphql", "-f", f"query={q}", "-f", f"owner={p['owner']}", "-F", f"n={p['number']}"]))
    proj = data["data"]["user"]["projectV2"]
    return proj["id"], {f["name"]: f for f in proj["fields"]["nodes"] if f}


def check(draft: dict) -> list[str]:
    errors = []
    labels = {l["name"] for l in json.loads(gh(["label", "list", "--limit", "200", "--json", "name"]))}
    for i, e in enumerate(draft.get("issues", [])):
        where = f"issues[{i}] {e.get('key', '?')}"
        if e.get("decision") not in {"assign", "defer", "ask"}:
            errors.append(f"{where}: decision must be assign, defer or ask")
        if e.get("decision") != "assign":
            if not e.get("reason"):
                errors.append(f"{where}: defer/ask needs a reason")
            continue
        if e.get("role") not in ROLES:
            errors.append(f"{where}: unknown role {e.get('role')}")
        if not re.fullmatch(r"W([2-9]|1[0-2])", str(e.get("week", ""))):
            errors.append(f"{where}: week must be W2..W12")
        if e.get("size") not in SIZES:
            errors.append(f"{where}: size must be S or M (split anything larger)")
        if not str(e.get("title", "")).startswith(f"[{e.get('week')}][{e.get('role')}] "):
            errors.append(f"{where}: title must start with [{e.get('week')}][{e.get('role')}] ")
        body = e.get("body", "")
        missing = [s for s in SECTIONS if f"### {s}" not in body]
        if missing:
            errors.append(f"{where}: body is missing sections {missing}")
        if "- [ ]" not in body:
            errors.append(f"{where}: Acceptance needs checkbox items")
        for l in e.get("labels", []):
            if l not in labels:
                errors.append(f"{where}: label {l!r} does not exist")
    assign_keys, seen = {e.get("key") for e in draft.get("issues", []) if e.get("decision") == "assign"}, set()
    for e in draft.get("issues", []):
        for b in e.get("blocked_by", []) if e.get("decision") == "assign" else []:
            if isinstance(b, str) and b.startswith("key:") and b[4:] not in seen:
                errors.append(f"{e.get('key')}: blocked_by {b} must name an assign entry listed earlier")
        if e.get("decision") == "assign":
            seen.add(e.get("key"))
    texts = [e.get("body", "") for e in draft.get("issues", [])] + [r.get("body", "") for r in draft.get("replies", [])]
    for ref in set(re.findall(r"\{issue:([\w-]+)\}", "\n".join(texts))):
        if ref not in assign_keys:
            errors.append(f"{{issue:{ref}}} does not name an assign entry")
    for r in draft.get("replies", []):
        if not r.get("number") or not r.get("body"):
            errors.append(f"reply {r}: needs number and body")
    return errors


FOOTER = "\n\nStart with `/start-task <this issue #>` in Claude Code.\n"


def fill(text: str, done: dict, strict: bool = True) -> str:
    """Replace {issue:<key>} with #N. Not strict: leave refs to issues not created yet."""
    def sub(m):
        hit = done.get(m.group(1))
        if not hit:
            if strict:
                raise RuntimeError(f"{m.group(0)} is not created yet")
            return m.group(0)
        return f"#{hit['number']}"
    return re.sub(r"\{issue:([\w-]+)\}", sub, text)


def issue_body(e: dict, done: dict, strict: bool) -> str:
    return fill(e["body"], done, strict).rstrip() + FOOTER


def reply_key(r: dict) -> str:
    return f"reply-{r['number']}-{hashlib.sha256(r['body'].encode()).hexdigest()[:10]}"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    path = Path(sys.argv[1])
    apply = "--apply" in sys.argv
    draft = yaml.safe_load(path.read_text(encoding="utf-8"))
    done_path = path.with_suffix(".applied.json")
    done = json.loads(done_path.read_text(encoding="utf-8")) if done_path.exists() else {}

    errors = check(draft)
    if errors:
        print("Draft has problems; nothing was changed:")
        for e in errors:
            print(f"  - {e}")
        return 1

    issues = draft.get("issues", [])
    for e in issues:
        tag = "ASSIGN" if e["decision"] == "assign" else e["decision"].upper()
        state = f" (done: #{done[e['key']]['number']})" if e.get("key") in done else ""
        print(f"[{tag}] {e.get('title') or e.get('key')}{state}")
        if e["decision"] != "assign":
            print(f"        reason: {e['reason']} | revisit: {e.get('revisit_when', '-')}")
        else:
            print(f"        {e['role']} -> {TEAM['roles'][e['role']]}, {e['week']}, size {e['size']}, "
                  f"labels {e.get('labels', [])}, blocked by {e.get('blocked_by', [])}")
    for r in draft.get("replies", []):
        state = " (done)" if reply_key(r) in done else ""
        print(f"[REPLY] #{r['number']}{state}: {r['body'][:100]!r}")
    if not apply:
        print("\nCheck only. Run again with --apply to create the issues and post the replies.")
        return 0

    repo = repo_name()
    project_id, fields = board_fields()

    def save():
        done_path.write_text(json.dumps(done, indent=2), encoding="utf-8")

    def board_item(number: int, url: str) -> dict:
        """Add the issue to the board, or find its item when the board's auto-add got there first."""
        p = TEAM["project"]
        try:
            return json.loads(gh(["project", "item-add", str(p["number"]), "--owner", p["owner"],
                                  "--url", url, "--format", "json"]))
        except RuntimeError as err:
            if "already exists" not in str(err):
                raise
        owner, name = repo.split("/")
        q = """query($o:String!,$r:String!,$n:Int!){ repository(owner:$o,name:$r){ issue(number:$n){
          projectItems(first:20){ nodes{ id project{ id } } } } } }"""
        data = json.loads(gh(["api", "graphql", "-f", f"query={q}", "-f", f"o={owner}", "-f", f"r={name}",
                              "-F", f"n={number}"]))
        for node in data["data"]["repository"]["issue"]["projectItems"]["nodes"]:
            if node["project"]["id"] == project_id:
                return {"id": node["id"]}
        raise RuntimeError(f"#{number} is neither added nor found on the board")

    def set_field(item_id: str, name: str, value: str):
        f = fields.get(name)
        if not f or not value:
            return
        args = ["project", "item-edit", "--id", item_id, "--project-id", project_id, "--field-id", f["id"]]
        if "options" in f:
            opt = next((o["id"] for o in f["options"] if o["name"] == value), None)
            if not opt:
                print(f"    ! {name}={value} is not an option on the board; skipped")
                return
            args += ["--single-select-option-id", opt]
        elif "configuration" in f:
            it = next((i["id"] for i in f["configuration"]["iterations"] if i["title"] == value), None)
            if not it:
                print(f"    ! {name}={value} is not an open iteration; skipped")
                return
            args += ["--iteration-id", it]
        else:
            args += ["--text", value]
        gh(args)

    for e in issues:
        if e["decision"] != "assign":
            continue
        rec = done.get(e["key"])
        if not rec:
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tf:
                tf.write(issue_body(e, done, strict=False))
            args = ["issue", "create", "--title", e["title"], "--body-file", tf.name,
                    "--assignee", TEAM["roles"][e["role"]]]
            for l in [f"role:{e['role'].lower()}", *e.get("labels", [])]:
                args += ["--label", l]
            url = gh(args)
            Path(tf.name).unlink(missing_ok=True)
            rec = done[e["key"]] = {"number": int(url.rstrip("/").rsplit("/", 1)[1]), "url": url}
            save()
            print(f"Created #{rec['number']} {url}")
        if not rec.get("board"):
            p = TEAM["project"]
            item = board_item(rec["number"], rec["url"])
            for name, value in (("Week", e["week"]), ("Role", e["role"]), ("Size", e["size"]),
                                ("Eval Qs", e.get("eval_qs", "")), ("Firm", e.get("firm", ""))):
                set_field(item["id"], name, value)
            rec["board"] = True
            save()
        for b in e.get("blocked_by", []):
            num = done[b[4:]]["number"] if isinstance(b, str) and b.startswith("key:") else int(b)
            if num in rec.setdefault("blocked_by", []):
                continue
            blocker_id = json.loads(gh(["api", f"repos/{repo}/issues/{num}"]))["id"]
            gh(["api", "-X", "POST", f"repos/{repo}/issues/{rec['number']}/dependencies/blocked_by",
                "-F", f"issue_id={blocker_id}"])
            rec["blocked_by"].append(num)
            save()
            print(f"    #{rec['number']} blocked by #{num}")

    # Second pass: bodies that named an issue created later in this run.
    for e in issues:
        if e["decision"] != "assign" or "{issue:" not in e["body"] or done[e["key"]].get("filled"):
            continue
        gh(["issue", "edit", str(done[e["key"]]["number"]), "--body-file", "-"],
           input_text=issue_body(e, done, strict=True))
        done[e["key"]]["filled"] = True
        save()
        print(f"Linked issue numbers in #{done[e['key']]['number']}")

    for r in draft.get("replies", []):
        key = reply_key(r)
        if key in done:
            continue
        gh(["api", f"repos/{repo}/issues/{r['number']}/comments", "-F", "body=@-"], input_text=fill(r["body"], done))
        done[key] = {"number": r["number"]}
        save()
        print(f"Replied on #{r['number']}")

    snapshot_time = draft.get("state_time") or datetime.now(timezone.utc).isoformat()
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps({"last_run": snapshot_time, "last_draft": path.name}, indent=2), encoding="utf-8")
    print(f"\nDone. Last dispatch run set to {snapshot_time}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
