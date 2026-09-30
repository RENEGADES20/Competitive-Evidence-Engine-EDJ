<#
Load a corpus snapshot into your local Docker Postgres (replaces what is there).

  powershell -ExecutionPolicy Bypass -File scripts\restore.ps1                 # newest snapshot
  powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 path\to\corpus-2026-10-05.dump

Without a path it looks in CORPUS_SHARE_PATH\snapshots (Box Drive), then in .\snapshots.
Teammates: download the newest .dump from the team Box link into .\snapshots first.
#>
param([string]$Dump)
. "$PSScriptRoot\_common.ps1"

if (-not $Dump) {
    $dirs = @()
    $share = Get-DotEnvValue "CORPUS_SHARE_PATH"
    if ($share) { $dirs += (Join-Path $share "snapshots") }
    $dirs += (Join-Path $RepoRoot "snapshots")
    foreach ($d in $dirs) {
        if (Test-Path $d) {
            # Newest official snapshot; -test builds are only restored when named explicitly.
            $f = Get-ChildItem $d -Filter "corpus-*.dump" | Where-Object { $_.Name -notlike "*-test.dump" } |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($f) { $Dump = $f.FullName; break }
        }
    }
    if (-not $Dump) { throw "No snapshot found. Download the newest corpus-YYYY-MM-DD.dump from the team Box link into $RepoRoot\snapshots and run this again." }
}
$Dump = (Resolve-Path $Dump).Path
$name = Split-Path $Dump -Leaf
Write-Host "Restoring $name"

Start-Database
$staged = Join-Path $RepoRoot "snapshots\$name"
if ($Dump -ne $staged) { Copy-Item $Dump $staged -Force }   # the container sees .\snapshots as /snapshots

Reset-Database
Invoke-Native { docker exec $Container pg_restore -U cee -d cee --no-owner "/snapshots/$name" } "pg_restore"
Write-Host "Done. Row counts: $(Get-TableCounts)"
