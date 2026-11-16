<#
Rebuild the database from main + the stored raw files, and publish a snapshot (ADR-006).
With CEE_VECTORS=on (environment or .env; off by default, ADR-009) it also embeds every chunk.
Tech lead only; needs CORPUS_SHARE_PATH (Box Drive folder) in .env.

  powershell -ExecutionPolicy Bypass -File scripts\build-snapshot.ps1 -Notes "What changed (#108, #111)"
  -Notes         required: what changed, with issue numbers; goes into snapshots\LATEST.json (#129).
                 No links (the repo is public).
  -AllowBranch   skip the "clean main" check. For testing only; never publish a snapshot built this way.
#>
param([switch]$AllowBranch, [string]$Notes)
. "$PSScriptRoot\_common.ps1"

# Checked first, before anything is touched (#129).
if (-not $AllowBranch -and -not "$Notes".Trim()) { throw 'Pass -Notes "<what changed, issue numbers>" (it goes into snapshots\LATEST.json).' }
if (-not "$Notes".Trim()) { $Notes = "test build" }

$vectors = Test-VectorsOn
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

    if ($vectors) {
        Write-Host "4/7 Embedding every chunk (CEE_VECTORS=on; model cache: $(Set-ModelCache))..."
        Invoke-VectorsSql
        Invoke-Native { & $Python -m cee.retrieve.embed --missing } "Embedding (a chunk without a vector stops the build)"
    } else {
        Write-Host "4/7 Embedding skipped (CEE_VECTORS is off)"
    }

    $name = "corpus-" + (Get-Date -Format "yyyy-MM-dd")
    if ($AllowBranch) { $name += "-test" }
    Invoke-Native { docker exec $Container psql -q -U cee -d cee -c "COMMENT ON TABLE documents IS '$name';" } "Stamping snapshot name"

    Write-Host "5/7 Dumping $name.dump..."
    Invoke-Native { docker exec $Container pg_dump -U cee -d cee -Fc -f "/snapshots/$name.dump" } "pg_dump"
    # snapshots\LATEST.json names the dump for /sync-db (#129); a test build writes LATEST-test.json (git-ignored).
    $latestName = if ($AllowBranch) { "LATEST-test.json" } else { "LATEST.json" }
    $latestFile = Join-Path $RepoRoot "snapshots\$latestName"
    $docs = (docker exec $Container psql -qtA -U cee -d cee -c "SELECT count(*) FROM documents" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Counting documents failed" }
    $chunks = (docker exec $Container psql -qtA -U cee -d cee -c "SELECT count(*) FROM chunks" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Counting chunks failed" }
    Write-Host "   writing snapshots\$latestName"
    Invoke-Native { & $Python (Join-Path $RepoRoot "scripts\snapshot_latest.py") write --out $latestFile --dump (Join-Path $RepoRoot "snapshots\$name.dump") --documents $docs --chunks $chunks --notes $Notes } "Writing $latestFile"

    Write-Host "6/7 Copying to Box..."
    $dest = Join-Path $share "snapshots"
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item (Join-Path $RepoRoot "snapshots\$name.dump") $dest -Force

    if ($vectors) {
        Write-Host "7/7 Embedding model in Box models/..."
        Copy-ModelToShare $share
    } else {
        Write-Host "7/7 Embedding model skipped (CEE_VECTORS is off)"
    }

    $mb = [math]::Round((Get-Item (Join-Path $RepoRoot "snapshots\$name.dump")).Length / 1MB, 1)
    Write-Host "Done: $dest\$name.dump ($mb MB)"
    Write-Host "Row counts: $(Get-TableCounts)"
    if (-not $AllowBranch) {
        Write-Host ""
        Write-Host "Next: publish snapshots\LATEST.json through a PR (merging it tells the team to run /sync-db):"
        Write-Host "  git switch -c tl/snapshot-$name"
        Write-Host "  git add snapshots/LATEST.json"
        Write-Host "  git commit -m `"Snapshot $name`""
        Write-Host "  git push -u origin tl/snapshot-$name"
        Write-Host "  gh pr create --fill"
    }
} finally { Pop-Location }
