#!/usr/bin/env bash
# #250: macOS / Linux twin of run-mock.ps1 (mock, 0 calls).
#   EV=<evidence dir> PY=<python> bash run-mock.sh <worktree> <out> [mode] [PROVIDER:MODEL cache] [questions] [fastembed dir]
set -u
WT="$1"; OUT="$2"; MODE="${3:-}"; REUSE="${4:-}"; CACHE="${5:-}"; QS="${6:-}"; FE="${7:-}"
EV="${EV:-$HOME/cee-ev250}"; PY="${PY:-python3}"; OUTDIR="$EV/$OUT"
[ -e "$OUTDIR" ] && { echo "STOP: $OUTDIR exists"; exit 3; }
[ -f "$WT/.env" ] && { echo "STOP: $WT/.env exists"; exit 3; }
cd "$WT" || exit 3
A=(--as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUTDIR")
[ -n "$QS" ] && A+=(--questions "$QS"); [ -n "$MODE" ] && A+=(--mode "$MODE")
[ -n "$REUSE" ] && A+=(--reuse-plans "$REUSE" --cache "$CACHE")
(
  export LLM_PROVIDER=mock PYTHONPATH="$WT/src" PLANNER=on MAP=on DEEPSEEK_THINKING=on DEEPSEEK_API_KEY=
  if [ -n "$MODE" ] && [ "$MODE" != fts ]; then export CEE_VECTORS=on; [ -n "$FE" ] && export FASTEMBED_CACHE_PATH="$FE"; fi
  echo "mock $OUT HEAD $(git rev-parse HEAD) args ${A[*]}" > "$OUTDIR.cmd.txt"
  "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
)
tail -1 "$OUTDIR.log"
