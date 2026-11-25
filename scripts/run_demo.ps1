# Start the app in demo mode (#299): the Ask page replays prepared answers for the 30 eval questions.
# No model is called (LLM_PROVIDER=mock for anything outside the demo); the database must be running
# (citations open the stored passage). Mac twin: scripts/run_demo.sh.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\run_demo.ps1 -Port 8502
param([int]$Port = 8501)
. "$PSScriptRoot\_common.ps1"

$env:CEE_DEMO = "1"
$env:LLM_PROVIDER = "mock"
Write-Host "Demo mode: open http://localhost:$Port (the Demo toggle sits at the bottom of the sidebar)."
& $Python -m streamlit run (Join-Path $RepoRoot "src\cee\app\streamlit_app.py") --server.port $Port
