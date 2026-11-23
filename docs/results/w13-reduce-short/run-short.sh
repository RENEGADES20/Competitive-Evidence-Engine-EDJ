#!/usr/bin/env bash
# #284 (plans/0284-reduce-short.md): copy of w13-prefix-cache/run-prefix.sh with REDUCE_PROMPT=v6 allowed, EV ev284. #283: macOS / Linux twin of run-prefix.ps1 (copied from w12-latency/run-latency.sh, #272,
# plus PREFIX_TOKENS=150000, PREFIX_GATE=first_chunk|done|off pinned from the Q10 probe, WAIT_S=5). One phase (plan | count | run) of a W12 latency
# run on DeepSeek, every setting pinned. Test A: C1 = EFFORT_PLAN=off EFFORT_MAP=low EFFORT_REDUCE=low; C2 = C1 with
# EFFORT_MAP=off; C3 = C1 with MAP_MODEL=deepseek-flash. The key file is copied in and removed by a trap; never read or
# printed here. Options as environment variables:
#   WT OUT CACHE MAXCALLS PHASE GATE_SHA [EFFORT_PLAN] [EFFORT_MAP] [EFFORT_REDUCE] [MAP_MODEL] [STREAM] [MODEL]
#   [MODE] [REUSE_PLANS=1] [PLAN_VERSION] [FASTEMBED_PATH] [ENV_FILE] [QUESTIONS] [CONCURRENCY] [EV] [PY]
#   [IDLE_S=120] [REDUCE_PROMPT=v5.2|v5.3|v6] [MAP_PREFIX=off|firm] [PREFIX_TOKENS=150000] [PREFIX_GATE=first_chunk] [WAIT_S=5]   (#275; PYTHONHASHSEED=0 is pinned, like run-latency.ps1)
set -u
: "${WT:?}" "${OUT:?}" "${CACHE:?}" "${MAXCALLS:?}" "${PHASE:?}" "${GATE_SHA:?}"
EFFORT_PLAN="${EFFORT_PLAN:-off}"; EFFORT_MAP="${EFFORT_MAP:-low}"; EFFORT_REDUCE="${EFFORT_REDUCE:-low}"
STREAM="${STREAM:-on}"; MODEL="${MODEL:-deepseek-v4-pro}"; CONCURRENCY="${CONCURRENCY:-24}"
IDLE_S="${IDLE_S:-120}"; REDUCE_PROMPT="${REDUCE_PROMPT:-v5.2}"
MAP_PREFIX="${MAP_PREFIX:-off}"; PREFIX_TOKENS="${PREFIX_TOKENS:-150000}"; PREFIX_GATE="${PREFIX_GATE:-first_chunk}"; WAIT_S="${WAIT_S:-5}"
EV="${EV:-$HOME/cee-ev284}"; PY="${PY:-python3}"
QUESTIONS="${QUESTIONS:-$(seq -s, -f 'Q%g' 1 30)}"; OUTDIR="$EV/$OUT"; H="$EV/$OUT.head-log.txt"
[ "$PHASE" = count ] && MAXCALLS=0
mkdir -p "$EV"; cd "$WT" || exit 3
GATE="$(git diff "$GATE_SHA" HEAD --stat -- src scripts config evals)"; ST="$(git status --short)"
echo "$PHASE $OUT before $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD) gate $GATE_SHA [$GATE] status [$ST] env-file $([ -f .env ] && echo True || echo False)" >> "$H"
if [ -n "$ST" ] || [ -n "$GATE" ] || [ -f .env ] || [ -e "$OUTDIR" ]; then
  echo "STOP: dirty tree, code gate, .env present or out dir exists; nothing run" >> "$H"; tail -1 "$H"; exit 3; fi
A=(--real --max-calls "$MAXCALLS" --naive-tz America/Chicago --cache "$CACHE" --questions "$QUESTIONS" --as-of 2026-11-17
   --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUTDIR")
[ "$PHASE" = plan ] && A+=(--plan-only); [ -n "${MODE:-}" ] && A+=(--mode "$MODE")
[ -n "${REUSE_PLANS:-}" ] && A+=(--reuse-plans "deepseek:$MODEL${PLAN_VERSION:+@$PLAN_VERSION}")
trap 'rm -f "$WT/.env"; echo "$PHASE $OUT after $(date -u +%FT%TZ) HEAD $(git -C "$WT" rev-parse HEAD) env-file $([ -f "$WT/.env" ] && echo True || echo False)" >> "$H"' EXIT
(
  unset DEEPSEEK_API_KEY ANTHROPIC_API_KEY LLM_MODEL DEEPSEEK_MODEL DEEPSEEK_MODEL_MAP DEEPSEEK_THINKING CEE_VECTORS FASTEMBED_CACHE_PATH
  export LLM_PROVIDER=deepseek PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY="$CONCURRENCY" MAP_CALL_TOKENS=60000
  export PYTHONPATH="$WT/src" DEEPSEEK_MODEL="$MODEL" DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
  export DEEPSEEK_EFFORT_PLAN="$EFFORT_PLAN" DEEPSEEK_EFFORT_MAP="$EFFORT_MAP" DEEPSEEK_EFFORT_REDUCE="$EFFORT_REDUCE" DEEPSEEK_STREAM="$STREAM"
  export DEEPSEEK_IDLE_S="$IDLE_S" REDUCE_PROMPT="$REDUCE_PROMPT" PYTHONHASHSEED=0
  export MAP_PREFIX="$MAP_PREFIX" MAP_PREFIX_TOKENS="$PREFIX_TOKENS" MAP_PREFIX_GATE="$PREFIX_GATE" MAP_PREFIX_WAIT_S="$WAIT_S"
  [ -n "${MAP_MODEL:-}" ] && export DEEPSEEK_MODEL_MAP="$MAP_MODEL"
  if [ -n "${MODE:-}" ] && [ "$MODE" != fts ]; then export CEE_VECTORS=on; [ -n "${FASTEMBED_PATH:-}" ] && export FASTEMBED_CACHE_PATH="$FASTEMBED_PATH"; fi
  echo "settings: model $MODEL map model ${MAP_MODEL:-$MODEL} effort plan $EFFORT_PLAN map $EFFORT_MAP reduce $EFFORT_REDUCE stream $STREAM idle $IDLE_S reduce prompt $REDUCE_PROMPT PYTHONHASHSEED=0 mode ${MODE:-fts} MAP_CONCURRENCY=$CONCURRENCY MAP_CALL_TOKENS=60000 MAP_PREFIX=$MAP_PREFIX MAP_PREFIX_TOKENS=$PREFIX_TOKENS MAP_PREFIX_GATE=$PREFIX_GATE MAP_PREFIX_WAIT_S=$WAIT_S; args ${A[*]}" >> "$H"
  if [ "$PHASE" = count ]; then
    export DEEPSEEK_API_KEY=
    "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
  else
    cp "${ENV_FILE:?ENV_FILE (the main repo .env path) is needed for plan / run}" "$WT/.env"
    "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
  fi
  echo "$PHASE $OUT exit $?" >> "$H"
)
tail -2 "$OUTDIR.log"
