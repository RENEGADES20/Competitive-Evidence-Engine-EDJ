# #250 (plans/0250-final-runs.md): build a run cache from the committed record folders (+ extra folders).
# With -AllowMaps, a map / remap record (`Q*-map.*` / `Q*-remap.*`) is copied only if its file name is in that
# list (condition C3: only hash-checked inherited map records); plans and reduces are always copied.
#   powershell -File seed-cache.ps1 -Cache <new dir> -Wt <worktree> [-Extra <dir>,<dir>] [-AllowMaps <file>]
param([Parameter(Mandatory)][string]$Cache, [Parameter(Mandatory)][string]$Wt,
      [string[]]$Extra = @(), [string]$AllowMaps = '')
$ErrorActionPreference = 'Stop'
if (Test-Path $Cache) { Write-Output "STOP: $Cache exists"; exit 3 }
$folders = '0242-deepseek-raw', '0245-planner-raw', '0246-map-raw', '0247-raw', '0247b-raw', '0247d-raw' |
  ForEach-Object { Join-Path $Wt "docs\results\$_" }
$files = @(Get-ChildItem ($folders + $Extra) -Recurse -File -Filter 'Q*.json')
$allow = $null
if ($AllowMaps) { $allow = @{}; Get-Content $AllowMaps | Where-Object { $_ } | ForEach-Object { $allow[$_.Trim()] = 1 } }
New-Item -ItemType Directory -Force $Cache | Out-Null
$seen = @{}; $left = 0
foreach ($f in $files) {
  $isMap = $f.Name -match '^Q\d+-(re)?map\.'
  if ($allow -and $isMap -and -not $allow.ContainsKey($f.Name)) { $left++; continue }
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
  if ($seen.ContainsKey($f.Name)) {
    if ($seen[$f.Name] -ne $h) { Write-Output "STOP: $($f.Name) differs between sources"; exit 3 }
    continue
  }
  $seen[$f.Name] = $h
  Copy-Item $f.FullName (Join-Path $Cache $f.Name)
}
Write-Output "seeded $($seen.Count) records into $Cache from $($files.Count) files; map records left out (not allowed): $left"
