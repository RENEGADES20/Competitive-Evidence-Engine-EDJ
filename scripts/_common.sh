# Shared helpers for the bash scripts (macOS twins of the .ps1 scripts). Owner: TL (Yueyang Du).
# Source it: . "$(dirname "$0")/_common.sh"
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash on Windows: keep /snapshots/... as container paths

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then PYTHON="$REPO_ROOT/.venv/bin/python"
else PYTHON="$REPO_ROOT/.venv/Scripts/python.exe"; fi   # Git Bash on Windows
CONTAINER="cee-db"

die() { echo "ERROR: $*" >&2; exit 1; }

dotenv_value() {
    # A process environment variable wins over .env (same rule as python-dotenv).
    local name="$1"
    if [ -n "${!name:-}" ]; then printf '%s' "${!name}"; return; fi
    local env_file="$REPO_ROOT/.env"
    [ -f "$env_file" ] || return 0
    sed -n "s/^[[:space:]]*$name[[:space:]]*=[[:space:]]*//p" "$env_file" | tail -1 | tr -d '\r' \
        | sed 's/[[:space:]]*$//; s/^"//; s/"$//'
}

run() {
    # run "<what>" cmd args...: fail with a readable message, judged by the exit code only.
    local what="$1"; shift
    "$@" || die "$what failed (exit code $?)"
}

start_database() {
    mkdir -p "$REPO_ROOT/snapshots"
    (cd "$REPO_ROOT" && docker compose up -d --wait) \
        || die "Starting the database failed (is Docker Desktop running?)"
}

reset_database() {
    run "Dropping the database" docker exec "$CONTAINER" psql -q -U cee -d postgres \
        -c "DROP DATABASE IF EXISTS cee WITH (FORCE);" -c "CREATE DATABASE cee;"
}

upgrade_schema() {
    # db/upgrade.sql: idempotent additions (pgvector column, #123), so older snapshots gain them.
    run "Upgrading the schema (did you pull the new database image? docker compose up -d)" \
        docker exec "$CONTAINER" psql -q -U cee -d cee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/02-upgrade.sql
}

table_counts() {
    docker exec "$CONTAINER" psql -At -F "=" -U cee -d cee -c \
        "SELECT 'documents', count(*) FROM documents UNION ALL SELECT 'chunks', count(*) FROM chunks UNION ALL SELECT 'entities', count(*) FROM entities ORDER BY 1;" \
        | tr -d '\r' | paste -sd ',' - | sed 's/,/, /g' || die "Counting rows failed"
}
