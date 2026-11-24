#!/usr/bin/env bash
# #295 (plans/0295-reduce-effort-off.md): macOS / Linux twin of run-gate3.ps1. One phase (count | run) of the Gate 3
# run on DeepSeek, fts Q1-Q30, every setting pinned to the #272 test B run plus REDUCE_PROMPT=v8 and
# DEEPSEEK_EFFORT_REDUCE_BRIEF. The key comes from ENV_FILE
# (the main repo's .env), copied into the worktree for the run and removed after; never read or printed here.
#   WT=<worktree> OUT=<name> CACHE=<dir> PHASE=count|run GATE=<sha> [MAX_CALLS=N] [QUESTIONS=Q1,...,Q30]
#     [EFFORT_REDUCE_BRIEF=off|low] [ENV_FILE=<repo>/.env] [EV=$HOME/cee-ev295] [PY=python3] bash run-gate3.sh
set -u
: "${WT:?}" "${OUT:?}" "${CACHE:?}" "${PHASE:?}" "${GATE:?}"
EV="${EV:-$HOME/cee-ev295}"; PY="${PY:-python3}"; MAX_CALLS="${MAX_CALLS:-0}"
QUESTIONS="${QUESTIONS:-$(printf 'Q%s,' $(seq 1 30) | sed 's/,$//')}"
ENV_FILE="${ENV_FILE:-$WT/../repo/.env}"; REDUCE="${REDUCE:-v8}"; EFFORT_REDUCE="${EFFORT_REDUCE:-low}"
EFFORT_REDUCE_BRIEF="${EFFORT_REDUCE_BRIEF:-off}"
[ "$PHASE" = count ] && MAX_CALLS=0
H="$EV/$OUT.head-log.txt"; OUTDIR="$EV/$OUT"; mkdir -p "$EV"; cd "$WT" || exit 3
GATE_DIFF="$(git diff "$GATE" HEAD --stat -- src scripts config evals)"; ST="$(git status --short)"
echo "$PHASE $OUT before $(date -Iseconds) HEAD $(git rev-parse HEAD) gate $GATE [$GATE_DIFF] status [$ST] env-file $([ -e .env ] && echo True || echo False)" >> "$H"
if [ -n "$ST" ] || [ -n "$GATE_DIFF" ] || [ -e .env ] || [ -e "$OUTDIR" ]; then
  echo "STOP: dirty tree, code gate, .env present or out dir exists; nothing run" >> "$H"; tail -2 "$H"; exit 3
fi
A=(--real --max-calls "$MAX_CALLS" --naive-tz America/Chicago --cache "$CACHE" --questions "$QUESTIONS" --as-of 2026-11-17
   --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUTDIR")
cleanup() { rm -f "$WT/.env"; echo "$PHASE $OUT after $(date -Iseconds) HEAD $(git rev-parse HEAD) status [$(git status --short)]" >> "$H"; }
trap cleanup EXIT
(
  unset LLM_MODEL DEEPSEEK_MODEL_MAP DEEPSEEK_THINKING CEE_VECTORS FASTEMBED_CACHE_PATH ANTHROPIC_API_KEY FACTS
  export LLM_PROVIDER=deepseek PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=24 MAP_CALL_TOKENS=60000
  export PYTHONPATH="$WT/src" DEEPSEEK_MODEL=deepseek-v4-pro DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
  export DEEPSEEK_EFFORT_PLAN=off DEEPSEEK_EFFORT_MAP=low DEEPSEEK_EFFORT_REDUCE="$EFFORT_REDUCE" DEEPSEEK_EFFORT_REDUCE_BRIEF="$EFFORT_REDUCE_BRIEF" DEEPSEEK_STREAM=on DEEPSEEK_IDLE_S=120
  export REDUCE_PROMPT="$REDUCE" PYTHONHASHSEED=0 MAP_PREFIX=off
  echo "settings: model deepseek-v4-pro effort plan off map low reduce $EFFORT_REDUCE brief $EFFORT_REDUCE_BRIEF stream on idle 120 reduce prompt $REDUCE PYTHONHASHSEED=0 mode fts; args ${A[*]}" >> "$H"
  if [ "$PHASE" = count ]; then export DEEPSEEK_API_KEY=; else unset DEEPSEEK_API_KEY; cp "$ENV_FILE" "$WT/.env"; fi
  "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
  echo "$PHASE $OUT exit $?" >> "$H"
)
tail -2 "$OUTDIR.log"
