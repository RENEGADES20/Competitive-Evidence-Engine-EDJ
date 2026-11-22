# #272 (plans/0272-latency.md step 7): mock eval, 0 calls. Rule plans by default; with -ReusePlans the saved plans of
# deepseek:deepseek-v4-pro from -Cache (with -PlanVersion: plans saved under that request version, e.g. the #250 plans,
# ds-strict-1-think-on-a64000-p64000), searched and mapped on the mock.
#   powershell -File run-mock.ps1 -Wt <worktree> -Out <name> [-Mode hybrid-norerank] [-ReusePlans -Cache <dir> [-PlanVersion <v>]]
#     [-Questions Q1,...] [-FastembedPath <dir>]
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Out, [string]$Mode = '', [switch]$ReusePlans,
      [string]$Cache = '', [string]$PlanVersion = '', [string]$Questions = ((1..30 | ForEach-Object { "Q$_" }) -join ','),
      [string]$FastembedPath = '', [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev272',
      [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$outDir = Join-Path $EvDir $Out
if (Test-Path $outDir) { Write-Output "STOP: $outDir exists"; exit 3 }
New-Item -ItemType Directory -Force $EvDir | Out-Null
Set-Location $Wt
$a = @('--as-of', '2026-11-17', '--baseline', 'evals\baselines\corpus-2026-11-19\report.json', '--out', $outDir, '--questions', $Questions)
if ($Mode) { $a += @('--mode', $Mode) }
if ($ReusePlans) { $a += @('--reuse-plans', "deepseek:deepseek-v4-pro$(if ($PlanVersion) { "@$PlanVersion" })", '--cache', $Cache) }
$vars = 'LLM_PROVIDER', 'PYTHONPATH', 'CEE_VECTORS', 'FASTEMBED_CACHE_PATH', 'PLANNER', 'MAP', 'DEEPSEEK_THINKING', 'DEEPSEEK_API_KEY'
try {
  $env:LLM_PROVIDER = 'mock'; $env:PYTHONPATH = "$Wt\src"; $env:PLANNER = 'on'; $env:MAP = 'on'; $env:DEEPSEEK_API_KEY = ''
  if ($Mode -and $Mode -ne 'fts') { $env:CEE_VECTORS = 'on'; if ($FastembedPath) { $env:FASTEMBED_CACHE_PATH = $FastembedPath } }
  "mock $Out HEAD $(git rev-parse HEAD) args $($a -join ' ')" | Set-Content "$outDir.cmd.txt"
  & $Py -B scripts\eval_run.py @a *> "$outDir.log"
} finally { $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue } }
Get-Content "$outDir.log" -Tail 1
