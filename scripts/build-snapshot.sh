#!/usr/bin/env bash
# Rebuild the database from main + the stored raw files, embed every chunk (#124), and publish a
# snapshot (ADR-006).
# Tech lead only; needs CORPUS_SHARE_PATH (Box Drive folder) in .env. macOS twin of build-snapshot.ps1.
#
#   bash scripts/build-snapshot.sh
#   bash scripts/build-snapshot.sh --allow-branch   skip the "clean main" check. For testing only;
#                                                   never publish a snapshot built this way.
. "$(dirname "$0")/_common.sh"

ALLOW_BRANCH=0
while [ $# -gt 0 ]; do
    case "$1" in
        --allow-branch) ALLOW_BRANCH=1; shift ;;
        *) die "Unknown argument: $1 (use --allow-branch)" ;;
    esac
done

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

model_cache_env
echo "4/7 Embedding every chunk (#124; model cache: $FASTEMBED_CACHE_PATH)..."
run "Embedding (a chunk without a vector stops the build)" "$PYTHON" -m cee.retrieve.embed --missing

name="corpus-$(date +%Y-%m-%d)"
[ "$ALLOW_BRANCH" -eq 1 ] && name="$name-test"
run "Stamping snapshot name" docker exec "$CONTAINER" psql -q -U cee -d cee -c "COMMENT ON TABLE documents IS '$name';"

echo "5/7 Dumping $name.dump..."
run "pg_dump" docker exec "$CONTAINER" pg_dump -U cee -d cee -Fc -f "/snapshots/$name.dump"

echo "6/7 Copying to Box..."
dest="$share/snapshots"
mkdir -p "$dest"
cp -f "$REPO_ROOT/snapshots/$name.dump" "$dest/"

echo "7/7 Embedding model in Box models/..."
copy_model_to_share "$share"

mb="$(du -k "$REPO_ROOT/snapshots/$name.dump" | awk '{printf "%.1f", $1/1024}')"
echo "Done: $dest/$name.dump ($mb MB)"
echo "Row counts: $(table_counts)"
