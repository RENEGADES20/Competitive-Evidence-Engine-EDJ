#!/usr/bin/env bash
# #250 (C2): macOS / Linux twin of hist-replay.ps1. 0-call replay at a producing commit with that commit's own CLI,
# seed in <wt>/.eval-runs/cache, under diag/map_msg_hash.py.
#   EV=<evidence dir> PY=<python> bash hist-replay.sh <detached worktree> <seed dir> <questions> <out>
set -u
WT="$1"; SEED="$2"; QS="$3"; OUT="$4"; EV="${EV:-$HOME/cee-ev250}"; PY="${PY:-python3}"
HERE="$(cd "$(dirname "$0")" && pwd)"; H="$EV/$OUT.head-log.txt"; OUTDIR="$EV/$OUT"; CACHE="$WT/.eval-runs/cache"
cd "$WT" || exit 3
echo "hist $OUT before $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD)" >> "$H"
if [ -f .env ] || [ -e "$OUTDIR" ] || [ -e "$CACHE" ]; then echo "STOP: .env, out dir or cache exists" >> "$H"; exit 3; fi
mkdir -p "$CACHE"; cp "$SEED"/*.json "$CACHE"/
trap 'rm -rf "$CACHE"; echo "hist $OUT after $(date -u +%FT%TZ)" >> "$H"' EXIT
A=(--real --max-calls 0 --questions "$QS" --as-of 2026-11-17 --out "$OUTDIR")
grep -q '"--naive-tz"' scripts/eval_run.py && A+=(--naive-tz America/Chicago)
(
  export LLM_PROVIDER=deepseek DEEPSEEK_MODEL=deepseek-v4-pro DEEPSEEK_BASE_URL=https://api.deepseek.com/beta \
    DEEPSEEK_THINKING=on PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=6 PYTHONPATH="$WT/src" DEEPSEEK_API_KEY=
  "$PY" -B "$HERE/diag/map_msg_hash.py" --wt "$WT" --tsv "$OUTDIR.tsv" -- "${A[@]}" > "$OUTDIR.log" 2>&1
  echo "hist $OUT exit $?" >> "$H"
)
tail -2 "$OUTDIR.log"
