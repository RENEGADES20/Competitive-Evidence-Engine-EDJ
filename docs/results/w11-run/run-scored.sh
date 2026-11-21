#!/usr/bin/env bash
# #250 (plans/0250-final-runs.md): macOS / Linux twin of run-scored.ps1. One phase (plan | count | run) of a scored run,
# settings pinned by provider (deepseek, or anthropic for #259). The key file is copied in and removed by a trap;
# never read or printed here. Options as environment variables:
#   WT OUT CACHE MAXCALLS PHASE PROVIDER MODEL GATE_SHA [GATE_EXCLUDE] [MODE] [REUSE_PLANS=1] [FASTEMBED_PATH]
#   [ENV_FILE] [DIAG=1] [QUESTIONS] [EV] [PY]        e.g.  WT=~/wt OUT=fts-run ... bash run-scored.sh
set -u
: "${WT:?}" "${OUT:?}" "${CACHE:?}" "${MAXCALLS:?}" "${PHASE:?}" "${PROVIDER:?}" "${MODEL:?}" "${GATE_SHA:?}"
EV="${EV:-$HOME/cee-ev250}"; PY="${PY:-python3}"; HERE="$(cd "$(dirname "$0")" && pwd)"
QUESTIONS="${QUESTIONS:-$(seq -s, -f 'Q%g' 1 30)}"; OUTDIR="$EV/$OUT"; H="$EV/$OUT.head-log.txt"
[ "$PHASE" = count ] && MAXCALLS=0
[ -n "${DIAG:-}" ] && [ "$PHASE" != count ] && { echo "STOP: DIAG only with PHASE=count"; exit 3; }
cd "$WT" || exit 3
SPEC=(-- src scripts config evals); [ -n "${GATE_EXCLUDE:-}" ] && SPEC+=(":(exclude)$GATE_EXCLUDE")
GATE="$(git diff "$GATE_SHA" HEAD --stat "${SPEC[@]}")"; ST="$(git status --short)"
echo "$PHASE $OUT before $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD) gate $GATE_SHA [$GATE] status [$ST] env-file $([ -f .env ] && echo True || echo False)" >> "$H"
if [ -n "$ST" ] || [ -n "$GATE" ] || [ -f .env ] || [ -e "$OUTDIR" ]; then
  echo "STOP: dirty tree, code gate, .env present or out dir exists; nothing run" >> "$H"; tail -1 "$H"; exit 3; fi
A=(--real --max-calls "$MAXCALLS" --naive-tz America/Chicago --cache "$CACHE" --questions "$QUESTIONS" --as-of 2026-11-17
   --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUTDIR")
[ "$PHASE" = plan ] && A+=(--plan-only); [ -n "${MODE:-}" ] && A+=(--mode "$MODE")
[ -n "${REUSE_PLANS:-}" ] && A+=(--reuse-plans "$PROVIDER:$MODEL")
trap 'rm -f "$WT/.env"; echo "$PHASE $OUT after $(date -u +%FT%TZ) HEAD $(git -C "$WT" rev-parse HEAD) env-file $([ -f "$WT/.env" ] && echo True || echo False)" >> "$H"' EXIT
(
  unset DEEPSEEK_API_KEY ANTHROPIC_API_KEY LLM_MODEL DEEPSEEK_MODEL CEE_VECTORS FASTEMBED_CACHE_PATH
  export LLM_PROVIDER="$PROVIDER" PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=6 PYTHONPATH="$WT/src"
  if [ "$PROVIDER" = deepseek ]; then export DEEPSEEK_MODEL="$MODEL" DEEPSEEK_BASE_URL=https://api.deepseek.com/beta DEEPSEEK_THINKING=on
  else export LLM_MODEL="$MODEL"; fi
  if [ -n "${MODE:-}" ] && [ "$MODE" != fts ]; then export CEE_VECTORS=on; [ -n "${FASTEMBED_PATH:-}" ] && export FASTEMBED_CACHE_PATH="$FASTEMBED_PATH"; fi
  echo "settings: provider $PROVIDER model $MODEL mode ${MODE:-default}; args ${A[*]}" >> "$H"
  if [ "$PHASE" = count ]; then
    export DEEPSEEK_API_KEY= ANTHROPIC_API_KEY=
    if [ -n "${DIAG:-}" ]; then "$PY" -B "$HERE/diag/map_msg_hash.py" --wt "$WT" --tsv "$OUTDIR.tsv" --provider "$PROVIDER" -- "${A[@]}" > "$OUTDIR.log" 2>&1
    else "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1; fi
  else
    cp "${ENV_FILE:?ENV_FILE (the main repo .env path) is needed for plan / run}" "$WT/.env"
    "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
  fi
  echo "$PHASE $OUT exit $?" >> "$H"
)
tail -2 "$OUTDIR.log"
