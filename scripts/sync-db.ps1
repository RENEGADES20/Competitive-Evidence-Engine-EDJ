<#
Bring your local database to the snapshot named in snapshots/LATEST.json (#129).
Teammates: in Claude Code type /sync-db, or run this script. Needs no embedding model.

  powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1
  powershell -ExecutionPolicy Bypass -File scripts\sync-db.ps1 -Check     # only compare, change nothing
  -Latest <file>   read another manifest instead of snapshots\LATEST.json (for tests)

Steps: update the code (git pull on main, pip install, start the database); stop if the database
already carries that snapshot; find <name>.dump in .\snapshots, CORPUS_SHARE_PATH\snapshots or
Box Drive (%USERPROFILE%\Box) and check its sha256; restore it; run python -m cee.smoke.
Exit codes: 0 done or already up to date; 1 error; 2 the dump is missing or differs (download it),
or with -Check: the database is behind.
#>
param([string]$Latest, [switch]$Check)
. "$PSScriptRoot\_common.ps1"

if (-not $Latest) { $Latest = Join-Path $RepoRoot "snapshots\LATEST.json" }
elseif (Test-Path $Latest) { $Latest = (Resolve-Path $Latest).Path }
$Helper = Join-Path $RepoRoot "scripts\snapshot_latest.py"

function Get-LatestField([string]$Field) {
    $out = & $Python $Helper show --file $Latest --field $Field
    if ($LASTEXITCODE -ne 0) { throw "Could not read $Latest" }
    return ("$out").Trim()
}

function Get-CurrentSnapshot {
    # "" when the database has no stamp or cannot be read (e.g. a database that is not a snapshot).
    try { return Get-SnapshotName } catch { return "" }
}

if ($Check) {
    if (-not (Test-Path $Latest)) { Write-Host "No snapshots/LATEST.json yet; nothing to compare."; exit 0 }
    $name = Get-LatestField "name"
    try { $current = Get-SnapshotName }
    catch { Write-Host "Cannot compare snapshots: the database is not running (start Docker Desktop, then run /sync-db)."; exit 1 }
    if ($current -eq $name) { Write-Host "Database is up to date: $name."; exit 0 }
    $shown = if ($current) { $current } else { "no snapshot" }
    Write-Host "Your database has $shown; the newest snapshot is $name. Run /sync-db."
    exit 2
}

Push-Location $RepoRoot
try {
    Write-Host "1/4 Updating code..."
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($branch -eq "main") {
        $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        try { git pull --ff-only 2>&1 | ForEach-Object { "   $_" } } finally { $ErrorActionPreference = $old }
        if ($LASTEXITCODE -ne 0) { throw "git pull failed: fix main first (or ask the tech lead), then run /sync-db again. The database was not changed." }
    } else {
        Write-Warning "You are on '$branch': not pulling, and this sync uses this branch's snapshots/LATEST.json. Switch to main to get the newest one."
    }
    Invoke-Native { & $Python -m pip install -q --disable-pip-version-check -r requirements.txt } "pip install -r requirements.txt"
    Start-Database

    if (-not (Test-Path $Latest)) { throw "$Latest not found. No snapshot has been published through the repo yet; use scripts\restore.ps1 (docs/RUN.md)." }
    $name = Get-LatestField "name"
    $current = Get-CurrentSnapshot
    if ($current -eq $name) { Write-Host "Already up to date: $name. Nothing to do."; exit 0 }
    $shown = if ($current) { $current } else { "no snapshot" }
    Write-Host "   database has $shown; newest is $name"

    Write-Host "2/4 Finding $name.dump..."
    $search = @(Join-Path $RepoRoot "snapshots")
    $share = Get-DotEnvValue "CORPUS_SHARE_PATH"
    if ($share) { $search += (Join-Path $share "snapshots") }
    if ($env:USERPROFILE) { $search += (Join-Path $env:USERPROFILE "Box") }
    $old = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    try { $found = & $Python $Helper locate --file $Latest --search @search 2>&1 | ForEach-Object { "$_" } }
    finally { $ErrorActionPreference = $old }
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        $found | ForEach-Object { Write-Host $_ }
        if ($code -eq 2) { Write-Host "The database was not changed."; exit 2 }
        throw "Looking for $name.dump failed"
    }
    $dump = ($found | Select-Object -Last 1).Trim()
    Write-Host "   Using $dump (sha256 matches)"

    Write-Host "3/4 Restoring $name (replaces your local database)..."
    try { & "$PSScriptRoot\restore.ps1" $dump }
    catch { throw "Restore failed: $($_.Exception.Message). Your local database may be incomplete; run /sync-db again." }
    $now = Get-CurrentSnapshot
    if ($now -ne $name) { throw "After the restore the database says '$now', not '$name'. Run /sync-db again." }

    Write-Host "4/4 Smoke test..."
    & $Python -m cee.smoke
    $smoke = $LASTEXITCODE
    Write-Host ""
    Write-Host "What is new in ${name}: $(Get-LatestField 'notes')"
    if ($smoke -ne 0) { Write-Host "Synced to $name, but the smoke test FAILED (see the lines above)."; exit 1 }
    Write-Host "Synced to $name ($(Get-LatestField 'documents') documents, $(Get-LatestField 'chunks') chunks). Smoke PASS."
    if (Test-VectorsOn) { Write-Host "Vectors are on: run python -m cee.retrieve.embed --missing to embed the new chunks." }
} finally { Pop-Location }
