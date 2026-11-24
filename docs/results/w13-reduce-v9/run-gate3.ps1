# #297 (plans/0297-reduce-v9.md): one phase (count | run) of the Gate 3 run on DeepSeek, fts Q1-Q30, every setting
# pinned to the #272 test B run (docs/results/w12-latency/b-fts.head-log.txt) plus REDUCE_PROMPT=v9 at reduce effort
# low. From w13-reduce-effort-off/run-gate3.ps1 (#295), without its per-form effort variable (not on main).
# count: --max-calls 0, no key (shows which records are reused and which are new).
# run: the key comes from -EnvFile (the main repo's .env), copied into the worktree inside try and removed in finally;
# never read or printed here. Run from a clean worktree at the gate commit.
#   powershell -File run-gate3.ps1 -Wt <worktree> -Out <name> -Cache <dir> -Phase count|run -GateSha <sha> [-MaxCalls N]
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Out, [Parameter(Mandatory)][string]$Cache,
      [Parameter(Mandatory)][ValidateSet('count', 'run')][string]$Phase, [Parameter(Mandatory)][string]$GateSha,
      [int]$MaxCalls = 0, [string]$Questions = ((1..30 | ForEach-Object { "Q$_" }) -join ','),
      [string]$EnvFile = 'D:\ALLPROJECTS\EDJ\repo\.env', [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev297',
      [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$h = Join-Path $EvDir "$Out.head-log.txt"; $outDir = Join-Path $EvDir $Out
if ($Phase -eq 'count') { $MaxCalls = 0 }
New-Item -ItemType Directory -Force $EvDir | Out-Null
Set-Location $Wt
$gate = git diff $GateSha HEAD --stat -- src scripts config evals
$st = git status --short
"$Phase $Out before $(Get-Date -Format o) HEAD $(git rev-parse HEAD) gate $GateSha [$gate] status [$st] env-file $(Test-Path "$Wt\.env")" | Add-Content $h
if ($st -or $gate -or (Test-Path "$Wt\.env") -or (Test-Path $outDir)) {
  "STOP: dirty tree, code gate, .env present or out dir exists; nothing run" | Add-Content $h; Get-Content $h -Tail 2; exit 3
}
$vars = 'LLM_PROVIDER', 'LLM_MODEL', 'DEEPSEEK_MODEL', 'DEEPSEEK_MODEL_MAP', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_THINKING',
        'DEEPSEEK_EFFORT_PLAN', 'DEEPSEEK_EFFORT_MAP', 'DEEPSEEK_EFFORT_REDUCE', 'DEEPSEEK_EFFORT_REDUCE_BRIEF', 'DEEPSEEK_STREAM',
        'PLANNER', 'SUBQUESTION_TOKENS', 'MAP', 'MAP_CONCURRENCY', 'MAP_CALL_TOKENS', 'PYTHONPATH', 'CEE_VECTORS',
        'FASTEMBED_CACHE_PATH', 'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_IDLE_S', 'REDUCE_PROMPT', 'PYTHONHASHSEED',
        'MAP_PREFIX', 'FACTS'
$a = @('--real', '--max-calls', "$MaxCalls", '--naive-tz', 'America/Chicago', '--cache', $Cache, '--questions', $Questions,
       '--as-of', '2026-11-17', '--baseline', 'evals\baselines\corpus-2026-11-19\report.json', '--out', $outDir)
try {
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  $env:LLM_PROVIDER = 'deepseek'; $env:PLANNER = 'on'; $env:SUBQUESTION_TOKENS = '40000'; $env:MAP = 'on'
  $env:MAP_CONCURRENCY = '24'; $env:MAP_CALL_TOKENS = '60000'; $env:PYTHONPATH = "$Wt\src"
  $env:DEEPSEEK_MODEL = 'deepseek-v4-pro'; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com/beta'
  $env:DEEPSEEK_EFFORT_PLAN = 'off'; $env:DEEPSEEK_EFFORT_MAP = 'low'; $env:DEEPSEEK_EFFORT_REDUCE = 'low'
  $env:DEEPSEEK_STREAM = 'on'; $env:DEEPSEEK_IDLE_S = '120'; $env:REDUCE_PROMPT = 'v9'; $env:PYTHONHASHSEED = '0'
  $env:MAP_PREFIX = 'off'
  "settings: model deepseek-v4-pro effort plan off map low reduce low stream on idle 120 reduce prompt v9 PYTHONHASHSEED=0 mode fts PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=24 MAP_CALL_TOKENS=60000 MAP_PREFIX=off; args $($a -join ' ')" | Add-Content $h
  if ($Phase -eq 'count') { $env:DEEPSEEK_API_KEY = '' } else { Copy-Item $EnvFile "$Wt\.env" }
  & $Py -B scripts\eval_run.py @a *> "$outDir.log"
  "$Phase $Out exit $LASTEXITCODE" | Add-Content $h
} finally {
  Remove-Item "$Wt\.env" -Force -ErrorAction SilentlyContinue
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  "$Phase $Out after $(Get-Date -Format o) HEAD $(git rev-parse HEAD) env-file $(Test-Path "$Wt\.env") status [$(git status --short)]" | Add-Content $h
}
Get-Content "$outDir.log" -Tail 2
