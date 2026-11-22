# #250 (plans/0250-final-runs.md): one phase of a scored run (plan | count | run), settings pinned by provider.
# Reused by #259 with -Provider anthropic -Model claude-sonnet-5-5. The key comes from -EnvFile (the main repo's
# .env), copied into the worktree inside try and removed in finally; never read or printed here.
#   powershell -File run-scored.ps1 -Wt <worktree> -Out <name> -Cache <dir> -MaxCalls <n> -Phase plan|count|run `
#     -Provider deepseek -Model deepseek-v4-pro -GateSha <sha> [-GateExclude <path>] [-Mode hybrid-norerank] `
#     [-ReusePlans] [-FastembedPath <dir>] [-EnvFile <path>] [-Diag]
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Out, [Parameter(Mandatory)][string]$Cache,
      [Parameter(Mandatory)][int]$MaxCalls, [Parameter(Mandatory)][ValidateSet('plan', 'count', 'run')][string]$Phase,
      [Parameter(Mandatory)][ValidateSet('deepseek', 'anthropic')][string]$Provider, [Parameter(Mandatory)][string]$Model,
      [Parameter(Mandatory)][string]$GateSha, [string]$GateExclude = '', [string]$Mode = '', [switch]$ReusePlans,
      [string]$FastembedPath = '', [string]$EnvFile = 'D:\ALLPROJECTS\EDJ\repo\.env', [switch]$Diag,
      [string]$Questions = ((1..30 | ForEach-Object { "Q$_" }) -join ','),
      [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev250', [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$h = Join-Path $EvDir "$Out.head-log.txt"; $outDir = Join-Path $EvDir $Out
if ($Phase -eq 'count') { $MaxCalls = 0 }
if ($Diag -and $Phase -ne 'count') { Write-Output 'STOP: -Diag only with -Phase count'; exit 3 }
Set-Location $Wt
$spec = @('--', 'src', 'scripts', 'config', 'evals') + $(if ($GateExclude) { ":(exclude)$GateExclude" } else { @() })
$gate = git diff $GateSha HEAD --stat @spec
$st = git status --short
"$Phase $Out before $(Get-Date -Format o) HEAD $(git rev-parse HEAD) branch $(git branch --show-current) gate $GateSha [$gate] status [$st] env-file $(Test-Path "$Wt\.env")" | Add-Content $h
if ($st -or $gate -or (Test-Path "$Wt\.env") -or (Test-Path $outDir)) {
  "STOP: dirty tree, code gate, .env present or out dir exists; nothing run" | Add-Content $h; Get-Content $h -Tail 2; exit 3
}
$vars = 'LLM_PROVIDER', 'LLM_MODEL', 'DEEPSEEK_MODEL', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_THINKING', 'PLANNER',
        'SUBQUESTION_TOKENS', 'MAP', 'MAP_CONCURRENCY', 'PYTHONPATH', 'CEE_VECTORS', 'FASTEMBED_CACHE_PATH',
        'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY'
$a = @('--real', '--max-calls', "$MaxCalls", '--naive-tz', 'America/Chicago', '--cache', $Cache, '--questions', $Questions,
       '--as-of', '2026-11-17', '--baseline', 'evals\baselines\corpus-2026-11-19\report.json', '--out', $outDir)
if ($Phase -eq 'plan') { $a += '--plan-only' }
if ($Mode) { $a += @('--mode', $Mode) }
if ($ReusePlans) { $a += @('--reuse-plans', "${Provider}:$Model") }
try {
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  $env:LLM_PROVIDER = $Provider; $env:PLANNER = 'on'; $env:SUBQUESTION_TOKENS = '40000'; $env:MAP = 'on'
  $env:MAP_CONCURRENCY = '6'; $env:PYTHONPATH = "$Wt\src"
  if ($Provider -eq 'deepseek') {
    $env:DEEPSEEK_MODEL = $Model; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com/beta'; $env:DEEPSEEK_THINKING = 'on'
  } else { $env:LLM_MODEL = $Model }
  if ($Mode -and $Mode -ne 'fts') { $env:CEE_VECTORS = 'on'; if ($FastembedPath) { $env:FASTEMBED_CACHE_PATH = $FastembedPath } }
  "settings: provider $Provider model $Model mode $(if ($Mode) { $Mode } else { 'default' }) PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=6 thinking on (deepseek); args $($a -join ' ')" | Add-Content $h
  if ($Phase -eq 'count') {
    $env:DEEPSEEK_API_KEY = ''; $env:ANTHROPIC_API_KEY = ''
    if ($Diag) { & $Py -B "$here\diag\map_msg_hash.py" --wt $Wt --tsv "$outDir.tsv" --provider $Provider -- @a *> "$outDir.log" }
    else { & $Py -B scripts\eval_run.py @a *> "$outDir.log" }
  } else {
    Copy-Item $EnvFile "$Wt\.env"
    & $Py -B scripts\eval_run.py @a *> "$outDir.log"
  }
  "$Phase $Out exit $LASTEXITCODE" | Add-Content $h
} finally {
  Remove-Item "$Wt\.env" -Force -ErrorAction SilentlyContinue
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  "$Phase $Out after $(Get-Date -Format o) HEAD $(git rev-parse HEAD) env-file $(Test-Path "$Wt\.env") status [$(git status --short)]" | Add-Content $h
}
Get-Content "$outDir.log" -Tail 2
