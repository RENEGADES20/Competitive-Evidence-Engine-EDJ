#!/usr/bin/env bash
# #250 (plans/0250-final-runs.md): macOS / Linux twin of seed-cache.ps1. Builds a run cache from the committed record
# folders (+ extra folders). With an allow list, a map / remap record is copied only if its name is in it (C3).
#   bash seed-cache.sh <new cache dir> <worktree> [allow-list file or ""] [extra dir ...]
set -u
CACHE="$1"; WT="$2"; ALLOW="${3:-}"; shift 3 2>/dev/null || shift $#
[ -e "$CACHE" ] && { echo "STOP: $CACHE exists"; exit 3; }
mkdir -p "$CACHE"; n=0; left=0
for d in "$WT"/docs/results/{0242-deepseek-raw,0245-planner-raw,0246-map-raw,0247-raw,0247b-raw,0247d-raw} "$@"; do
  while IFS= read -r -d '' f; do
    b="$(basename "$f")"
    if [ -n "$ALLOW" ] && [[ "$b" =~ ^Q[0-9]+-(re)?map\. ]] && ! grep -qxF "$b" "$ALLOW"; then left=$((left+1)); continue; fi
    if [ -e "$CACHE/$b" ]; then cmp -s "$f" "$CACHE/$b" || { echo "STOP: $b differs between sources"; exit 3; }; continue; fi
    cp "$f" "$CACHE/$b"; n=$((n+1))
  done < <(find "$d" -type f -name 'Q*.json' -print0)
done
echo "seeded $n records into $CACHE; map records left out (not allowed): $left"
