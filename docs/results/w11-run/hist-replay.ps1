# #250 (plans/0250-final-runs.md, condition C2): 0-call replay at a record's producing commit, with that commit's
# own CLI and the seed in <wt>\.eval-runs\cache, under diag\map_msg_hash.py (message hashes then).
#   powershell -File hist-replay.ps1 -Wt <detached worktree at the commit> -Seed <cache dir> -Questions Q1,Q3 -Out <name>
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Seed, [Parameter(Mandatory)][string]$Questions,
      [Parameter(Mandatory)][string]$Out, [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev250',
      [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$h = Join-Path $EvDir "$Out.head-log.txt"; $outDir = Join-Path $EvDir $Out; $cache = "$Wt\.eval-runs\cache"
Set-Location $Wt
"hist $Out before $(Get-Date -Format o) HEAD $(git rev-parse HEAD) env-file $(Test-Path "$Wt\.env")" | Add-Content $h
if ((Test-Path "$Wt\.env") -or (Test-Path $outDir) -or (Test-Path $cache)) { "STOP: .env, out dir or cache exists" | Add-Content $h; exit 3 }
New-Item -ItemType Directory -Force $cache | Out-Null
Copy-Item "$Seed\*.json" $cache
$a = @('--real', '--max-calls', '0', '--questions', $Questions, '--as-of', '2026-11-17', '--out', $outDir)
if (Select-String -Path scripts\eval_run.py -Pattern '"--naive-tz"' -Quiet) { $a += @('--naive-tz', 'America/Chicago') }
$vars = 'LLM_PROVIDER', 'DEEPSEEK_MODEL', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_THINKING', 'PLANNER', 'SUBQUESTION_TOKENS',
        'MAP', 'MAP_CONCURRENCY', 'PYTHONPATH', 'DEEPSEEK_API_KEY'
try {
  $env:LLM_PROVIDER = 'deepseek'; $env:DEEPSEEK_MODEL = 'deepseek-v4-pro'; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com/beta'
  $env:DEEPSEEK_THINKING = 'on'; $env:PLANNER = 'on'; $env:SUBQUESTION_TOKENS = '40000'; $env:MAP = 'on'
  $env:MAP_CONCURRENCY = '6'; $env:PYTHONPATH = "$Wt\src"; $env:DEEPSEEK_API_KEY = ''
  & $Py -B "$here\diag\map_msg_hash.py" --wt $Wt --tsv "$outDir.tsv" -- @a *> "$outDir.log"
  "hist $Out exit $LASTEXITCODE" | Add-Content $h
} finally {
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  Remove-Item -Recurse -Force $cache -ErrorAction SilentlyContinue
  "hist $Out after $(Get-Date -Format o) env-file $(Test-Path "$Wt\.env")" | Add-Content $h
}
Get-Content "$outDir.log" -Tail 2
