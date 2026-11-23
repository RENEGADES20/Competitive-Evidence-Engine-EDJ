#!/usr/bin/env bash
# #285 (plans/0285-facts.md): the facts extraction on DeepSeek (map-stage settings pinned), one phase: count (0 calls) |
# run (paid, planned) | write (0 calls: saved records -> config/facts.jsonl). Mac / Linux twin of run-extract.ps1. The
# key comes from ENV_FILE (the main repo's .env), copied into the worktree and removed on exit; never read or printed.
#   bash run-extract.sh <worktree> count|run|write <gate sha> [max calls 76] [max usd 3]
set -uo pipefail
WT="$1"; PHASE="$2"; GATE="$3"; MAXCALLS="${4:-76}"; MAXUSD="${5:-3}"; CONC="${CONCURRENCY:-8}"
ENV_FILE="${ENV_FILE:-$HOME/EDJ/repo/.env}"; EVDIR="${EVDIR:-$HOME/EDJ/cache/ev285}"
if [ -x "$WT/.venv/bin/python" ]; then PY="${PY:-$WT/.venv/bin/python}"; else PY="${PY:-python3}"; fi
H="$EVDIR/extract.head-log.txt"; OUT="$EVDIR/extract"
mkdir -p "$EVDIR"; cd "$WT" || exit 3
gate="$(git diff "$GATE" HEAD --stat -- src scripts config)"; st="$(git status --short)"
echo "$PHASE before $(date -Iseconds) HEAD $(git rev-parse HEAD) gate $GATE [$gate] status [$st] env-file $([ -f "$WT/.env" ] && echo True || echo False)" >> "$H"
if { [ "$PHASE" != write ] && [ -n "$st" ]; } || [ -n "$gate" ] || [ -f "$WT/.env" ]; then
  echo "STOP: dirty tree, code gate or .env present; nothing run" >> "$H"; tail -2 "$H"; exit 3
fi
cleanup() { rm -f "$WT/.env"; echo "$PHASE after $(date -Iseconds) HEAD $(git rev-parse HEAD) env-file $([ -f "$WT/.env" ] && echo True || echo False) status [$(git status --short)]" >> "$H"; }
trap cleanup EXIT
unset DEEPSEEK_MODEL_MAP DEEPSEEK_THINKING DEEPSEEK_API_KEY
export LLM_PROVIDER=deepseek DEEPSEEK_MODEL=deepseek-v4-pro DEEPSEEK_BASE_URL=https://api.deepseek.com/beta
export DEEPSEEK_EFFORT_MAP=low DEEPSEEK_STREAM=on DEEPSEEK_IDLE_S=120 PYTHONPATH="$WT/src" PYTHONHASHSEED=0
echo "settings: deepseek-v4-pro map effort low stream on idle 120; max-calls $MAXCALLS max-usd $MAXUSD concurrency $CONC" >> "$H"
case "$PHASE" in
  count) DEEPSEEK_API_KEY='' "$PY" -B scripts/extract_facts.py --out "$OUT" --count > "$OUT-count.log" 2>&1 ;;
  write) DEEPSEEK_API_KEY='' "$PY" -B scripts/extract_facts.py --out "$OUT" --write > "$OUT-write.log" 2>&1 ;;
  run) cp "$ENV_FILE" "$WT/.env"
       "$PY" -B scripts/extract_facts.py --out "$OUT" --real --max-calls "$MAXCALLS" --max-usd "$MAXUSD" --concurrency "$CONC" > "$OUT-run.log" 2>&1 ;;
  *) echo "phase must be count, run or write"; exit 2 ;;
esac
echo "$PHASE exit $?" >> "$H"
