#!/usr/bin/env bash
# Rebuild the database from main + the stored raw files, and publish a snapshot (ADR-006).
# With CEE_VECTORS=on (environment or .env; off by default, ADR-009) it also embeds every chunk.
# Tech lead only; needs CORPUS_SHARE_PATH (Box Drive folder) in .env. macOS twin of build-snapshot.ps1.
#
#   bash scripts/build-snapshot.sh --notes "What changed (#108, #111)"
#   --notes "<text>"   required: what changed, with issue numbers; goes into snapshots/LATEST.json
#                      (#129). No links (the repo is public).
#   --allow-branch     skip the "clean main" check. For testing only; never publish a snapshot
#                      built this way.
. "$(dirname "$0")/_common.sh"

ALLOW_BRANCH=0
NOTES=""
while [ $# -gt 0 ]; do
    case "$1" in
        --allow-branch) ALLOW_BRANCH=1; shift ;;
        --notes) [ $# -ge 2 ] || die "--notes needs a text"; NOTES="$2"; shift 2 ;;
        *) die "Unknown argument: $1 (use --notes or --allow-branch)" ;;
    esac
done

# Checked first, before anything is touched (#129).
if [ "$ALLOW_BRANCH" -eq 0 ] && [ -z "$(printf '%s' "$NOTES" | tr -d '[:space:]')" ]; then
    die 'Pass --notes "<what changed, issue numbers>" (it goes into snapshots/LATEST.json).'
fi
[ -n "$(printf '%s' "$NOTES" | tr -d '[:space:]')" ] || NOTES="test build"

VECTORS=0
if vectors_on; then VECTORS=1; fi
share="$(dotenv_value CORPUS_SHARE_PATH)"
[ -n "$share" ] || die "CORPUS_SHARE_PATH is empty in .env. build-snapshot runs on the tech lead's machine (Box Drive)."

cd "$REPO_ROOT"
if [ "$ALLOW_BRANCH" -eq 0 ]; then
    branch="$(git rev-parse --abbrev-ref HEAD)"
    [ "$branch" = "main" ] || die "Check out main first (current branch: $branch)."
    [ -z "$(git status --porcelain --untracked-files=no)" ] || die "Working tree has uncommitted changes. Commit or stash them first."
    run "git pull" git pull --ff-only
else
    echo "WARNING: --allow-branch: test build, do not share this snapshot." >&2
fi

echo "1/7 Checking every manifest file in $share (exists, sha256 matches)..."
run "Manifest check" "$PYTHON" -c "from cee.ingest.manifest import check_files, read_manifest; r = check_files(read_manifest()); print(f'   {len(r)} files OK')"

echo "2/7 Recreating the database..."
start_database
reset_database
run "Applying schema" docker exec "$CONTAINER" psql -q -U cee -d cee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/01-schema.sql
upgrade_schema

echo "3/7 Re-ingesting from the manifest..."
run "Ingestion" "$PYTHON" -m cee.ingest.load

if [ "$VECTORS" -eq 1 ]; then
    model_cache_env
    echo "4/7 Embedding every chunk (CEE_VECTORS=on; model cache: $FASTEMBED_CACHE_PATH)..."
    apply_vectors_sql
    run "Embedding (a chunk without a vector stops the build)" "$PYTHON" -m cee.retrieve.embed --missing
else
    echo "4/7 Embedding skipped (CEE_VECTORS is off)"
fi

name="corpus-$(date +%Y-%m-%d)"
[ "$ALLOW_BRANCH" -eq 1 ] && name="$name-test"
run "Stamping snapshot name" docker exec "$CONTAINER" psql -q -U cee -d cee -c "COMMENT ON TABLE documents IS '$name';"

echo "5/7 Dumping $name.dump..."
run "pg_dump" docker exec "$CONTAINER" pg_dump -U cee -d cee -Fc -f "/snapshots/$name.dump"
# snapshots/LATEST.json names the dump for /sync-db (#129); a test build writes LATEST-test.json (git-ignored).
latest_name="LATEST.json"
[ "$ALLOW_BRANCH" -eq 1 ] && latest_name="LATEST-test.json"
docs="$(docker exec "$CONTAINER" psql -qtA -U cee -d cee -c "SELECT count(*) FROM documents" | tr -d '\r')" \
    || die "Counting documents failed"
chunks="$(docker exec "$CONTAINER" psql -qtA -U cee -d cee -c "SELECT count(*) FROM chunks" | tr -d '\r')" \
    || die "Counting chunks failed"
echo "   writing snapshots/$latest_name"
run "Writing snapshots/$latest_name" "$PYTHON" "$(native_path "$REPO_ROOT/scripts/snapshot_latest.py")" write \
    --out "$(native_path "$REPO_ROOT/snapshots/$latest_name")" \
    --dump "$(native_path "$REPO_ROOT/snapshots/$name.dump")" \
    --documents "$docs" --chunks "$chunks" --notes "$NOTES"

echo "6/7 Copying to Box..."
dest="$share/snapshots"
mkdir -p "$dest"
cp -f "$REPO_ROOT/snapshots/$name.dump" "$dest/"

if [ "$VECTORS" -eq 1 ]; then
    echo "7/7 Embedding model in Box models/..."
    copy_model_to_share "$share"
else
    echo "7/7 Embedding model skipped (CEE_VECTORS is off)"
fi

mb="$(du -k "$REPO_ROOT/snapshots/$name.dump" | awk '{printf "%.1f", $1/1024}')"
echo "Done: $dest/$name.dump ($mb MB)"
echo "Row counts: $(table_counts)"
if [ "$ALLOW_BRANCH" -eq 0 ]; then
    echo ""
    echo "Next: publish snapshots/LATEST.json through a PR (merging it tells the team to run /sync-db):"
    echo "  git switch -c tl/snapshot-$name"
    echo "  git add snapshots/LATEST.json"
    echo "  git commit -m \"Snapshot $name\""
    echo "  git push -u origin tl/snapshot-$name"
    echo "  gh pr create --fill"
fi
