# Not runnable after #289: the code it drives or imports was removed; kept as the record of how the evidence was made.
# #285 (plans/0285-facts.md): the facts extraction on DeepSeek (map-stage settings pinned), one phase: count (0 calls) |
# run (paid, planned) | write (0 calls: saved records -> config/facts.jsonl). The key comes from -EnvFile (the main repo's
# .env), copied into the worktree inside try and removed in finally; never read or printed here. Run from a clean
# worktree at the gate commit (write may leave config/facts.jsonl changed: that is its output).
#   powershell -File run-extract.ps1 -Wt <worktree> -Phase count|run|write -GateSha <sha> [-MaxCalls 76] [-MaxUsd 3]
param([Parameter(Mandatory)][string]$Wt, [Parameter(Mandatory)][ValidateSet('count', 'run', 'write')][string]$Phase,
      [Parameter(Mandatory)][string]$GateSha, [int]$MaxCalls = 76, [double]$MaxUsd = 3, [int]$Concurrency = 8,
      [string]$EnvFile = 'D:\ALLPROJECTS\EDJ\repo\.env', [string]$EvDir = 'D:\ALLPROJECTS\EDJ\cache\ev285',
      [string]$Py = 'D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe')
$h = Join-Path $EvDir "extract.head-log.txt"; $outDir = Join-Path $EvDir "extract"
New-Item -ItemType Directory -Force $EvDir | Out-Null
Set-Location $Wt
$gate = git diff $GateSha HEAD --stat -- src scripts config
$st = git status --short
"$Phase before $(Get-Date -Format o) HEAD $(git rev-parse HEAD) gate $GateSha [$gate] status [$st] env-file $(Test-Path "$Wt\.env")" | Add-Content $h
if (($Phase -ne 'write' -and $st) -or $gate -or (Test-Path "$Wt\.env")) {
  "STOP: dirty tree, code gate or .env present; nothing run" | Add-Content $h; Get-Content $h -Tail 2; exit 3
}
$vars = 'LLM_PROVIDER', 'DEEPSEEK_MODEL', 'DEEPSEEK_MODEL_MAP', 'DEEPSEEK_BASE_URL', 'DEEPSEEK_THINKING',
        'DEEPSEEK_EFFORT_MAP', 'DEEPSEEK_STREAM', 'DEEPSEEK_IDLE_S', 'PYTHONPATH', 'DEEPSEEK_API_KEY', 'PYTHONHASHSEED'
try {
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  $env:LLM_PROVIDER = 'deepseek'; $env:DEEPSEEK_MODEL = 'deepseek-v4-pro'; $env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com/beta'
  $env:DEEPSEEK_EFFORT_MAP = 'low'; $env:DEEPSEEK_STREAM = 'on'; $env:DEEPSEEK_IDLE_S = '120'
  $env:PYTHONPATH = "$Wt\src"; $env:PYTHONHASHSEED = '0'
  "settings: deepseek-v4-pro map effort low stream on idle 120; max-calls $MaxCalls max-usd $MaxUsd concurrency $Concurrency" | Add-Content $h
  if ($Phase -eq 'count') {
    $env:DEEPSEEK_API_KEY = ''
    & $Py -B scripts\extract_facts.py --out $outDir --count *> "$outDir-count.log"
  } elseif ($Phase -eq 'write') {
    $env:DEEPSEEK_API_KEY = ''
    & $Py -B scripts\extract_facts.py --out $outDir --write *> "$outDir-write.log"
  } else {
    Copy-Item $EnvFile "$Wt\.env"
    & $Py -B scripts\extract_facts.py --out $outDir --real --max-calls $MaxCalls --max-usd $MaxUsd --concurrency $Concurrency *> "$outDir-run.log"
  }
  "$Phase exit $LASTEXITCODE" | Add-Content $h
} finally {
  Remove-Item "$Wt\.env" -Force -ErrorAction SilentlyContinue
  $vars | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
  "$Phase after $(Get-Date -Format o) HEAD $(git rev-parse HEAD) env-file $(Test-Path "$Wt\.env") status [$(git status --short)]" | Add-Content $h
}
Get-Content $h -Tail 3
