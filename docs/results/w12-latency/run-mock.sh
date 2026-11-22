#!/usr/bin/env bash
# #272 (plans/0272-latency.md step 7): macOS / Linux twin of run-mock.ps1. Mock eval, 0 calls. Options as environment
# variables: WT OUT [MODE] [REUSE_PLANS=1 CACHE [PLAN_VERSION]] [QUESTIONS] [FASTEMBED_PATH] [EV] [PY]
set -u
: "${WT:?}" "${OUT:?}"
EV="${EV:-$HOME/cee-ev272}"; PY="${PY:-python3}"; QUESTIONS="${QUESTIONS:-$(seq -s, -f 'Q%g' 1 30)}"; OUTDIR="$EV/$OUT"
[ -e "$OUTDIR" ] && { echo "STOP: $OUTDIR exists"; exit 3; }
mkdir -p "$EV"; cd "$WT" || exit 3
A=(--as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUTDIR" --questions "$QUESTIONS")
[ -n "${MODE:-}" ] && A+=(--mode "$MODE")
[ -n "${REUSE_PLANS:-}" ] && A+=(--reuse-plans "deepseek:deepseek-v4-pro${PLAN_VERSION:+@$PLAN_VERSION}" --cache "${CACHE:?}")
(
  unset CEE_VECTORS FASTEMBED_CACHE_PATH DEEPSEEK_THINKING
  export LLM_PROVIDER=mock PYTHONPATH="$WT/src" PLANNER=on MAP=on DEEPSEEK_API_KEY=
  if [ -n "${MODE:-}" ] && [ "$MODE" != fts ]; then export CEE_VECTORS=on; [ -n "${FASTEMBED_PATH:-}" ] && export FASTEMBED_CACHE_PATH="$FASTEMBED_PATH"; fi
  echo "mock $OUT HEAD $(git rev-parse HEAD) args ${A[*]}" > "$OUTDIR.cmd.txt"
  "$PY" -B scripts/eval_run.py "${A[@]}" > "$OUTDIR.log" 2>&1
)
tail -1 "$OUTDIR.log"
