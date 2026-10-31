#!/usr/bin/env bash
# Load a corpus snapshot into your local Docker Postgres (replaces what is there).
# macOS twin of restore.ps1.
#
#   bash scripts/restore.sh                                  # newest snapshot
#   bash scripts/restore.sh path/to/corpus-2026-10-05.dump
#
# Without a path it looks in CORPUS_SHARE_PATH/snapshots (Box Drive), then in ./snapshots.
# Teammates: download the newest .dump from the team Box link into ./snapshots first.
. "$(dirname "$0")/_common.sh"

DUMP="${1:-}"
if [ -z "$DUMP" ]; then
    dirs=()
    share="$(dotenv_value CORPUS_SHARE_PATH)"
    [ -n "$share" ] && dirs+=("$share/snapshots")
    dirs+=("$REPO_ROOT/snapshots")
    for d in "${dirs[@]}"; do
        [ -d "$d" ] || continue
        # Newest official snapshot by modified time; -test builds are only restored when named explicitly.
        f="$(ls -t "$d"/corpus-*.dump 2>/dev/null | grep -v -- '-test\.dump$' | head -1 || true)"
        if [ -n "$f" ]; then DUMP="$f"; break; fi
    done
    [ -n "$DUMP" ] || die "No snapshot found. Download the newest corpus-YYYY-MM-DD.dump from the team Box link into $REPO_ROOT/snapshots and run this again."
fi
[ -f "$DUMP" ] || die "File not found: $DUMP"
DUMP="$(cd "$(dirname "$DUMP")" && pwd)/$(basename "$DUMP")"
NAME="$(basename "$DUMP")"
echo "Restoring $NAME"

start_database
STAGED="$REPO_ROOT/snapshots/$NAME"
[ "$DUMP" -ef "$STAGED" ] || cp -f "$DUMP" "$STAGED"   # the container sees ./snapshots as /snapshots

reset_database
run "pg_restore" docker exec "$CONTAINER" pg_restore -U cee -d cee --no-owner "/snapshots/$NAME"
upgrade_schema
if vectors_on; then
    echo "Applying db/optional/vectors.sql (CEE_VECTORS=on)..."
    apply_vectors_sql
else
    echo "Vectors module skipped (CEE_VECTORS is off)"
fi
echo "Done. Row counts: $(table_counts)"
