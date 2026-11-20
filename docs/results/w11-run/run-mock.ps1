# #250 (plans/0250-final-runs.md steps 3 and 5): mock run, 0 calls. Rule plans by default; with -ReusePlans the saved
# plans of PROVIDER:MODEL from -Cache (the real planner's plans, searched and mapped on the mock).
#   powershell -File run-mock.ps1 -Wt <worktree> -Out <name> [-Mode hybrid-norerank] [-ReusePlans deepseek:deepseek-v4-pro -Cache <dir>]
#     [-Questions Q1,...] [-FastembedPath <dir>]
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Out, [string]$Mode = '', [string]$ReusePlans = '',
      [string]$Cache = '', [string]$Questions = '', [string]$FastembedPath = '',
      [string]$Ev = 'D:\ALLPROJECTS\EDJ\cache\ev250', [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$outDir = Join-Path $Ev $Out
if (Test-Path $outDir) { Write-Output "STOP: $outDir exists"; exit 3 }
if (Test-Path "$Wt\.env") { Write-Output "STOP: $Wt\.env exists"; exit 3 }
Set-Location $Wt
$a = @('--as-of', '2026-11-17', '--baseline', 'evals\baselines\corpus-2026-11-19\report.json', '--out', $outDir)
if ($Questions) { $a += @('--questions', $Questions) }
if ($Mode) { $a += @('--mode', $Mode) }
if ($ReusePlans) { $a += @('--reuse-plans', $ReusePlans, '--cache', $Cache) }
$vars = 'LLM_PROVIDER', 'PYTHONPATH', 'CEE_VECTORS', 'FASTEMBED_CACHE_PATH', 'PLANNER', 'MAP', 'DEEPSEEK_THINKING', 'DEEPSEEK_API_KEY'
try {
  # DEEPSEEK_THINKING=on: the saved plans' key holds the DeepSeek request version (thinking on)
  $env:LLM_PROVIDER = 'mock'; $env:PYTHONPATH = "$Wt\src"; $env:PLANNER = 'on'; $env:MAP = 'on'
  $env:DEEPSEEK_THINKING = 'on'; $env:DEEPSEEK_API_KEY = ''
  if ($Mode -and $Mode -ne 'fts') { $env:CEE_VECTORS = 'on'; if ($FastembedPath) { $env:FASTEMBED_CACHE_PATH = $FastembedPath } }
  "mock $Out HEAD $(git rev-parse HEAD) args $($a -join ' ')" | Set-Content "$outDir.cmd.txt"
  & $Py -B scripts\eval_run.py @a *> "$outDir.log"
} finally { $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue } }
Get-Content "$outDir.log" -Tail 1
