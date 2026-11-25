#!/usr/bin/env bash
# Start the app in demo mode (#299): the Ask page replays prepared answers for the 30 eval questions.
# No model is called (LLM_PROVIDER=mock for anything outside the demo); the database must be running
# (citations open the stored passage). Windows twin: scripts/run_demo.ps1.
#
#   bash scripts/run_demo.sh            # port 8501
#   bash scripts/run_demo.sh 8502
. "$(dirname "$0")/_common.sh"

PORT="${1:-8501}"
export CEE_DEMO=1
export LLM_PROVIDER=mock
echo "Demo mode: open http://localhost:$PORT (the Demo toggle sits at the bottom of the sidebar)."
exec "$PYTHON" -m streamlit run "$(native_path "$REPO_ROOT/src/cee/app/streamlit_app.py")" --server.port "$PORT"
