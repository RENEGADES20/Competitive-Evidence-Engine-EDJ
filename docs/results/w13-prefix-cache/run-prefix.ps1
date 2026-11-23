# #283 (plans/0283-prefix-cache.md): one phase (count | run) of the map prefix-cache run on DeepSeek, every setting
# pinned; copied from w12-latency/run-latency.ps1 (#272) plus the #283 settings -PrefixTokens (MAP_PREFIX_TOKENS),
# -PrefixGate (MAP_PREFIX_GATE, pinned from the Q10 probe) and -WaitS (MAP_PREFIX_WAIT_S). Test A comments below are #272's.
# Test A configs: C1 = -EffortPlan off -EffortMap low -EffortReduce low; C2 = C1 with -EffortMap off; C3 = C1 with
# -MapModel deepseek-flash. The key comes from -EnvFile (the main repo's .env), copied into the worktree inside try and
# removed in finally; never read or printed here. Run from a clean worktree at the gate commit.
#   powershell -File run-latency.ps1 -Wt <worktree> -Out <name> -Cache <dir> -MaxCalls <n> -Phase plan|count|run `
#     -GateSha <sha> [-EffortPlan off] [-EffortMap low] [-EffortReduce low] [-MapModel <model>] [-Stream on] `
#     [-Questions Q5,Q10] [-Mode hybrid-norerank] [-ReusePlans] [-PlanVersion <request version>] [-FastembedPath <dir>]
#     [-IdleS 120] [-ReducePrompt v5.2|v5.3] [-EvDir <dir>] [-PrefixTokens 150000] [-PrefixGate first_chunk|done|off] [-WaitS 5]
# #275: -IdleS pins DEEPSEEK_IDLE_S (a stalled stream fails, no retry), -ReducePrompt pins REDUCE_PROMPT, and
# PYTHONHASHSEED=0 is pinned so set iteration order is the same in every process (reduce message stability).
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][string]$Out, [Parameter(Mandatory)][string]$Cache,
      [Parameter(Mandatory)][int]$MaxCalls, [Parameter(Mandatory)][ValidateSet('plan', 'count', 'run')][string]$Phase,
      [Parameter(Mandatory)][string]$GateSha,
      [ValidateSet('off', 'low', 'high', 'max')][string]$EffortPlan = 'off',
      [ValidateSet('off', 'low', 'high', 'max')][string]$EffortMap = 'low',
      [ValidateSet('off', 'low', 'high', 'max')][string]$EffortReduce = 'low',
      [string]$MapModel = '', [ValidateSet('on', 'off', 'nothink')][string]$Stream = 'on',
      [string]$Model = 'deepseek-v4-pro', [string]$Mode = '', [switch]$ReusePlans, [string]$PlanVersion = '',
      [string]$FastembedPath = '', [string]$EnvFile = 'D:\ALLPROJECTS\EDJ\repo\.env',
      [double]$IdleS = 120, [ValidateSet('v5.2', 'v5.3')][string]$ReducePrompt = 'v5.2',
      [string]$Questions = ((1..30 | ForEach-Object { "Q$_" }) -join ','), [int]$Concurrency = 24,
      [int]$PrefixTokens = 150000, [ValidateSet('first_chunk', 'done', 'off')][string]$PrefixGate = 'first_chunk',
      [double]$WaitS = 5,
      [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev283', [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
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
        'DEEPSEEK_EFFORT_PLAN', 'DEEPSEEK_EFFORT_MAP', 'DEEPSEEK_EFFORT_REDUCE', 'DEEPSEEK_STREAM', 'PLANNER',
        'SUBQUESTION_TOKENS', 'MAP', 'MAP_CONCURRENCY', 'MAP_CALL_TOKENS', 'PYTHONPATH', 'CEE_VECTORS',
        'FASTEMBED_CACHE_PATH', 'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_IDLE_S', 'REDUCE_PROMPT', 'PYTHONHASHSEED',
        'MAP_PREFIX_TOKENS', 'MAP_PREFIX_GATE', 'MAP_PREFIX_WAIT_S'
$a = @('--real', '--max-calls', "$MaxCalls", '--naive-tz', 'America/Chicago', '--cache', $Cache, '--questions', $Questions,
       '--as-of', '2026-11-17', '--baseline', 'evals\baselines\corpus-2026-11-19\report.json', '--out', $outDir)
if ($Phase -eq 'plan') { $a += '--plan-only' }
if ($Mode) { $a += @('--mode', $Mode) }
if ($ReusePlans) { $a += @('--reuse-plans', "deepseek:$Model$(if ($PlanVersion) { "@$PlanVersion" })") }
try {
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  $env:LLM_PROVIDER = 'deepseek'; $env:PLANNER = 'on'; $env:SUBQUESTION_TOKENS = '40000'; $env:MAP = 'on'
  $env:MAP_CONCURRENCY = "$Concurrency"; $env:MAP_CALL_TOKENS = '60000'; $env:PYTHONPATH = "$Wt\src"
  $env:DEEPSEEK_MODEL = $Model; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com/beta'
  $env:DEEPSEEK_EFFORT_PLAN = $EffortPlan; $env:DEEPSEEK_EFFORT_MAP = $EffortMap; $env:DEEPSEEK_EFFORT_REDUCE = $EffortReduce
  $env:DEEPSEEK_STREAM = $Stream; if ($MapModel) { $env:DEEPSEEK_MODEL_MAP = $MapModel }
  $env:DEEPSEEK_IDLE_S = "$IdleS"; $env:REDUCE_PROMPT = $ReducePrompt; $env:PYTHONHASHSEED = '0'
  $env:MAP_PREFIX_TOKENS = "$PrefixTokens"; $env:MAP_PREFIX_GATE = $PrefixGate; $env:MAP_PREFIX_WAIT_S = "$WaitS"
  if ($Mode -and $Mode -ne 'fts') { $env:CEE_VECTORS = 'on'; if ($FastembedPath) { $env:FASTEMBED_CACHE_PATH = $FastembedPath } }
  $mm = if ($MapModel) { $MapModel } else { $Model }; $md = if ($Mode) { $Mode } else { 'fts' }
  "settings: model $Model map model $mm effort plan $EffortPlan map $EffortMap reduce $EffortReduce stream $Stream idle $IdleS reduce prompt $ReducePrompt PYTHONHASHSEED=0 mode $md PLANNER=on SUBQUESTION_TOKENS=40000 MAP=on MAP_CONCURRENCY=$Concurrency MAP_CALL_TOKENS=60000 MAP_PREFIX_TOKENS=$PrefixTokens MAP_PREFIX_GATE=$PrefixGate MAP_PREFIX_WAIT_S=$WaitS; args $($a -join ' ')" | Add-Content $h
  if ($Phase -eq 'count') {
    $env:DEEPSEEK_API_KEY = ''
    & $Py -B scripts\eval_run.py @a *> "$outDir.log"
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
