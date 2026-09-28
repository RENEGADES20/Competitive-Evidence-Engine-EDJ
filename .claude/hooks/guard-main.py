"""PreToolUse hook: block git commit/push on main and pushes that target main or force."""
import json, re, subprocess, sys

MSG = "Blocked: never commit or push to main. Create a branch: git switch -c <role>/<issue#>-<slug>"

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "") or ""
    commit, push = re.search(r"\bgit\s+commit\b", cmd), re.search(r"\bgit\s+push\b", cmd)
    if commit or push:
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        bad = branch in ("main", "master")
        if push and re.search(r"(\s|:|/)(main|master)\b|\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S", cmd):
            bad = True
        if bad:
            print(MSG, file=sys.stderr)
            sys.exit(2)
except SystemExit:
    raise
except Exception:
    pass
sys.exit(0)
