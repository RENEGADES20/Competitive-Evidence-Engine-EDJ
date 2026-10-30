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

MODEL_FOLDER="models--Qdrant--bge-small-en-v1.5-onnx-Q"   # fastembed cache folder of BAAI/bge-small-en-v1.5

model_cache_env() {
    # #124: the embedding model (about 70 MB) goes to FASTEMBED_CACHE_PATH (environment or .env),
    # else <repo>/.cache/fastembed; never a system temp folder. HF_HOME next to it if unset.
    local path
    path="$(dotenv_value FASTEMBED_CACHE_PATH)"
    [ -n "$path" ] || path="$REPO_ROOT/.cache/fastembed"
    export FASTEMBED_CACHE_PATH="$path"
    [ -n "${HF_HOME:-}" ] || export HF_HOME="$(dirname "$path")/huggingface"
}

copy_model_to_share() {
    # #124: keep a copy of the cached model in Box models/, for teammates without HuggingFace access.
    # Only refs/ and snapshots/ (what an offline load reads), symlinks resolved; skipped when Box has it.
    local share="$1" src dest
    model_cache_env
    src="$FASTEMBED_CACHE_PATH/$MODEL_FOLDER"
    dest="$share/models/$MODEL_FOLDER"
    if [ -f "$dest/refs/main" ]; then echo "   already in $dest"; return; fi
    [ -f "$src/refs/main" ] || die "Embedding model not found in $src"
    mkdir -p "$dest"
    cp -RL "$src/snapshots" "$dest/" || die "Copying the model to $dest failed"
    cp -RL "$src/refs" "$dest/" || die "Copying the model to $dest failed"   # refs last: its presence means "complete"
    echo "   copied to $dest"
}

table_counts() {
    docker exec "$CONTAINER" psql -At -F "=" -U cee -d cee -c \
        "SELECT 'documents', count(*) FROM documents UNION ALL SELECT 'chunks', count(*) FROM chunks UNION ALL SELECT 'entities', count(*) FROM entities ORDER BY 1;" \
        | tr -d '\r' | paste -sd ',' - | sed 's/,/, /g' || die "Counting rows failed"
}
