#!/usr/bin/env bash
# Bring your local database to the snapshot named in snapshots/LATEST.json (#129).
# macOS twin of sync-db.ps1. Teammates: in Claude Code type /sync-db, or run this script.
# Needs no embedding model.
#
#   bash scripts/sync-db.sh
#   bash scripts/sync-db.sh --check            # only compare, change nothing
#   --latest <file>   read another manifest instead of snapshots/LATEST.json (for tests)
#
# Steps: update the code (git pull on main, pip install, start the database); stop if the database
# already carries that snapshot; find <name>.dump in ./snapshots, CORPUS_SHARE_PATH/snapshots or
# Box Drive (~/Library/CloudStorage on a Mac, %USERPROFILE%/Box in Git Bash) and check its sha256;
# restore it; run python -m cee.smoke.
# Exit codes: 0 done or already up to date; 1 error; 2 the dump is missing or differs (download it),
# or with --check: the database is behind.
. "$(dirname "$0")/_common.sh"

LATEST="$REPO_ROOT/snapshots/LATEST.json"
CHECK=0
while [ $# -gt 0 ]; do
    case "$1" in
        --check) CHECK=1; shift ;;
        --latest) [ $# -ge 2 ] || die "--latest needs a file"; LATEST="$2"; shift 2 ;;
        *) die "Unknown argument: $1 (use --check or --latest <file>)" ;;
    esac
done
if [ -f "$LATEST" ]; then LATEST="$(cd "$(dirname "$LATEST")" && pwd)/$(basename "$LATEST")"; fi
HELPER="$(native_path "$REPO_ROOT/scripts/snapshot_latest.py")"
LATEST_PY="$(native_path "$LATEST")"

latest_field() {
    local out
    out="$("$PYTHON" "$HELPER" show --file "$LATEST_PY" --field "$1")" || die "Could not read $LATEST"
    printf '%s' "$out" | tr -d '\r'
}

current_snapshot() {
    # Empty when the database has no stamp or cannot be read (e.g. a database that is not a snapshot).
    snapshot_name 2>/dev/null || true
}

if [ "$CHECK" -eq 1 ]; then
    if [ ! -f "$LATEST" ]; then echo "No snapshots/LATEST.json yet; nothing to compare."; exit 0; fi
    name="$(latest_field name)"
    if ! current="$(snapshot_name 2>/dev/null)"; then
        echo "Cannot compare snapshots: the database is not running (start Docker Desktop, then run /sync-db)."
        exit 1
    fi
    if [ "$current" = "$name" ]; then echo "Database is up to date: $name."; exit 0; fi
    echo "Your database has ${current:-no snapshot}; the newest snapshot is $name. Run /sync-db."
    exit 2
fi

cd "$REPO_ROOT"
echo "1/4 Updating code..."
branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "main" ]; then
    git pull --ff-only 2>&1 | sed 's/^/   /' \
        || die "git pull failed: fix main first (or ask the tech lead), then run /sync-db again. The database was not changed."
else
    echo "WARNING: You are on '$branch': not pulling, and this sync uses this branch's snapshots/LATEST.json. Switch to main to get the newest one." >&2
fi
run "pip install -r requirements.txt" "$PYTHON" -m pip install -q --disable-pip-version-check -r requirements.txt
start_database

[ -f "$LATEST" ] || die "$LATEST not found. No snapshot has been published through the repo yet; use scripts/restore.sh (docs/RUN.md)."
name="$(latest_field name)"
current="$(current_snapshot)"
if [ "$current" = "$name" ]; then echo "Already up to date: $name. Nothing to do."; exit 0; fi
echo "   database has ${current:-no snapshot}; newest is $name"

echo "2/4 Finding $name.dump..."
search=("$REPO_ROOT/snapshots")
share="$(dotenv_value CORPUS_SHARE_PATH)"
[ -n "$share" ] && search+=("$share/snapshots")
case "${OSTYPE:-}" in
    msys*|cygwin*) [ -n "${USERPROFILE:-}" ] && search+=("$USERPROFILE/Box") ;;   # Git Bash on Windows
    *) search+=("$HOME/Library/CloudStorage") ;;
esac
py_search=()
for d in "${search[@]}"; do py_search+=("$(native_path "$d")"); done
set +e
found="$("$PYTHON" "$HELPER" locate --file "$LATEST_PY" --search "${py_search[@]}" 2>&1)"
code=$?
set -e
if [ "$code" -ne 0 ]; then
    printf '%s\n' "$found"
    if [ "$code" -eq 2 ]; then echo "The database was not changed."; exit 2; fi
    die "Looking for $name.dump failed"
fi
dump="$(posix_path "$(printf '%s' "$found" | tr -d '\r' | tail -1)")"
echo "   Using $dump (sha256 matches)"

echo "3/4 Restoring $name (replaces your local database)..."
bash "$REPO_ROOT/scripts/restore.sh" "$dump" \
    || die "Restore failed. Your local database may be incomplete; run /sync-db again."
now="$(current_snapshot)"
[ "$now" = "$name" ] || die "After the restore the database says '$now', not '$name'. Run /sync-db again."

echo "4/4 Smoke test..."
set +e
"$PYTHON" -m cee.smoke
smoke=$?
set -e
echo ""
echo "What is new in $name: $(latest_field notes)"
if [ "$smoke" -ne 0 ]; then echo "Synced to $name, but the smoke test FAILED (see the lines above)."; exit 1; fi
echo "Synced to $name ($(latest_field documents) documents, $(latest_field chunks) chunks). Smoke PASS."
if vectors_on; then echo "Vectors are on: run python -m cee.retrieve.embed --missing to embed the new chunks."; fi
