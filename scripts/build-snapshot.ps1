<#
Rebuild the database from main + the stored raw files, embed every chunk (#124), and publish a
snapshot (ADR-006).
Tech lead only; needs CORPUS_SHARE_PATH (Box Drive folder) in .env.

  powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1
  -AllowBranch   skip the "clean main" check. For testing only; never publish a snapshot built this way.
#>
param([switch]$AllowBranch)
. "$PSScriptRoot\_common.ps1"

$share = Get-DotEnvValue "CORPUS_SHARE_PATH"
if (-not $share) { throw "CORPUS_SHARE_PATH is empty in .env. build-snapshot runs on the tech lead's machine (Box Drive)." }

Push-Location $RepoRoot
try {
    if (-not $AllowBranch) {
        $branch = (git rev-parse --abbrev-ref HEAD).Trim()
        if ($branch -ne "main") { throw "Check out main first (current branch: $branch)." }
        if (git status --porcelain --untracked-files=no) { throw "Working tree has uncommitted changes. Commit or stash them first." }
        Invoke-Native { git pull --ff-only } "git pull"
    } else {
        Write-Warning "-AllowBranch: test build, do not share this snapshot."
    }

    Write-Host "1/7 Checking every manifest file in $share (exists, sha256 matches)..."
    Invoke-Native { & $Python -c "from cee.ingest.manifest import check_files, read_manifest; r = check_files(read_manifest()); print(f'   {len(r)} files OK')" } "Manifest check"

    Write-Host "2/7 Recreating the database..."
    Start-Database
    Reset-Database
    Invoke-Native { docker exec $Container psql -q -U cee -d cee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/01-schema.sql } "Applying schema"
    Update-Schema

    Write-Host "3/7 Re-ingesting from the manifest..."
    Invoke-Native { & $Python -m cee.ingest.load } "Ingestion"

    Write-Host "4/7 Embedding every chunk (#124; model cache: $(Set-ModelCache))..."
    Invoke-Native { & $Python -m cee.retrieve.embed --missing } "Embedding (a chunk without a vector stops the build)"

    $name = "corpus-" + (Get-Date -Format "yyyy-MM-dd")
    if ($AllowBranch) { $name += "-test" }
    Invoke-Native { docker exec $Container psql -q -U cee -d cee -c "COMMENT ON TABLE documents IS '$name';" } "Stamping snapshot name"

    Write-Host "5/7 Dumping $name.dump..."
    Invoke-Native { docker exec $Container pg_dump -U cee -d cee -Fc -f "/snapshots/$name.dump" } "pg_dump"

    Write-Host "6/7 Copying to Box..."
    $dest = Join-Path $share "snapshots"
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item (Join-Path $RepoRoot "snapshots\$name.dump") $dest -Force

    Write-Host "7/7 Embedding model in Box models/..."
    Copy-ModelToShare $share

    $mb = [math]::Round((Get-Item (Join-Path $RepoRoot "snapshots\$name.dump")).Length / 1MB, 1)
    Write-Host "Done: $dest\$name.dump ($mb MB)"
    Write-Host "Row counts: $(Get-TableCounts)"
} finally { Pop-Location }
