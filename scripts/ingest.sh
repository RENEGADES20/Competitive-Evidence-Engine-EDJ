#!/usr/bin/env bash
# Load every document in data/manifest.csv into your local database (adds or replaces rows).
# Needs the raw files: in CORPUS_SHARE_PATH/raw (Box Drive) or in ./data/raw. macOS twin of ingest.ps1.
#
#   bash scripts/ingest.sh
#   bash scripts/ingest.sh --doc EDJ-10K-2025
. "$(dirname "$0")/_common.sh"

DOC=""
while [ $# -gt 0 ]; do
    case "$1" in
        --doc) DOC="${2:?--doc needs a doc_id}"; shift 2 ;;
        *) die "Unknown argument: $1 (use --doc <doc_id>)" ;;
    esac
done

start_database
if [ -n "$DOC" ]; then run "Ingestion" "$PYTHON" -m cee.ingest.load --doc "$DOC"
else run "Ingestion" "$PYTHON" -m cee.ingest.load; fi
echo "Row counts: $(table_counts)"
