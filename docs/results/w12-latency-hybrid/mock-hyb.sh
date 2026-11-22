#!/usr/bin/env bash
# #272 step 13: mock hybrid-norerank Q1-Q30 with the #250 plans (0 calls). $1 worktree, $2 out name, $3 plan request suffix
set -e
WT=$1; OUT=/d/ALLPROJECTS/EDJ/cache/ev272/$2
Q=$(python -c "print(','.join(f'Q{i}' for i in range(1,31)))")
cd "$WT"
unset DEEPSEEK_API_KEY
export LLM_PROVIDER=mock PYTHONPATH="$WT/src" PLANNER=on MAP=on DEEPSEEK_THINKING=on DEEPSEEK_API_KEY= CEE_VECTORS=on
export FASTEMBED_CACHE_PATH='D:\ALLPROJECTS\EDJ\cache\fastembed'
/d/ALLPROJECTS/EDJ/repo/.venv/Scripts/python.exe -B scripts/eval_run.py --as-of 2026-11-17 \
  --baseline evals/baselines/corpus-2026-11-19/report.json --out "$OUT" --questions "$Q" --mode hybrid-norerank \
  --reuse-plans "deepseek:deepseek-v4-pro${3:-}" --cache /d/ALLPROJECTS/EDJ/cache/ev272/plans250 > "$OUT.log" 2>&1
tail -1 "$OUT.log"
