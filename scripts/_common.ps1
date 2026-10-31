# Shared helpers for the PowerShell scripts. Owner: TL (Yueyang Du).
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Container = "cee-db"

function Get-DotEnvValue([string]$Name) {
    # A process environment variable wins over .env (same rule as python-dotenv).
    if (Test-Path "env:$Name") { return (Get-Item "env:$Name").Value.Trim().Trim('"') }
    $envFile = Join-Path $RepoRoot ".env"
    if (-not (Test-Path $envFile)) { return "" }
    foreach ($line in Get-Content $envFile) {
        if ($line -match "^\s*$Name\s*=\s*(.*)$") { return $Matches[1].Trim().Trim('"') }
    }
    return ""
}

function Invoke-Native([scriptblock]$Block, [string]$What) {
    # Docker writes progress to stderr; in Windows PowerShell 5.1 that must not count as an error.
    # Success is judged by the exit code only.
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $old }
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)" }
}

function Start-Database {
    Push-Location $RepoRoot
    try {
        New-Item -ItemType Directory -Force (Join-Path $RepoRoot "snapshots") | Out-Null
        Invoke-Native { docker compose up -d --wait } "Starting the database (is Docker Desktop running?)"
    } finally { Pop-Location }
}

function Reset-Database {
    Invoke-Native { docker exec $Container psql -q -U cee -d postgres -c "DROP DATABASE IF EXISTS cee WITH (FORCE);" -c "CREATE DATABASE cee;" } "Dropping the database"
}

function Update-Schema {
    # db/upgrade.sql: idempotent core additions (no extension, ADR-009), so older snapshots gain them.
    Invoke-Native { docker exec $Container psql -q -U cee -d cee -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/02-upgrade.sql } "Upgrading the schema"
}

function Test-VectorsOn {
    # CEE_VECTORS (environment or .env): the optional vectors module (ADR-009), off by default.
    # Same parsing as cee.config.vectors_enabled(): on|true|1|yes / empty, off|false|0|no.
    $v = (Get-DotEnvValue "CEE_VECTORS").ToLower()
    if (@("on", "true", "1", "yes") -contains $v) { return $true }
    if (@("", "off", "false", "0", "no") -contains $v) { return $false }
    throw "CEE_VECTORS='$v' is not understood; use on or off"
}

function Invoke-VectorsSql {
    # db/optional/vectors.sql (idempotent): pgvector, chunk_embeddings, one-time move of the old
    # chunks.embedding column. Not mounted in the container on purpose, so it goes in over stdin.
    $sql = Join-Path $RepoRoot "db/optional/vectors.sql"
    Invoke-Native { Get-Content -Raw $sql | docker exec -i $Container psql -q -U cee -d cee -v ON_ERROR_STOP=1 -f - } "Applying db/optional/vectors.sql (CEE_VECTORS=on)"
}

# Model helpers below: used only when CEE_VECTORS=on.
$ModelFolder = "models--Qdrant--bge-small-en-v1.5-onnx-Q"   # fastembed cache folder of BAAI/bge-small-en-v1.5

function Set-ModelCache {
    # #124: the embedding model (about 70 MB) goes to FASTEMBED_CACHE_PATH (environment or .env),
    # else <repo>\.cache\fastembed; never a system temp folder. HF_HOME next to it if unset.
    $path = Get-DotEnvValue "FASTEMBED_CACHE_PATH"
    if (-not $path) { $path = Join-Path $RepoRoot ".cache\fastembed" }
    $env:FASTEMBED_CACHE_PATH = $path
    if (-not $env:HF_HOME) { $env:HF_HOME = Join-Path (Split-Path -Parent $path) "huggingface" }
    return $path
}

function Copy-ModelToShare([string]$Share) {
    # #124: keep a copy of the cached model in Box models/, for teammates without HuggingFace access.
    # Only refs\ and snapshots\ (what an offline load reads); skipped when Box already has it.
    $src = Join-Path (Set-ModelCache) $ModelFolder
    $dest = Join-Path $Share "models\$ModelFolder"
    if (Test-Path (Join-Path $dest "refs\main")) { Write-Host "   already in $dest"; return }
    if (-not (Test-Path (Join-Path $src "refs\main"))) { throw "Embedding model not found in $src" }
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item (Join-Path $src "snapshots") $dest -Recurse -Force
    Copy-Item (Join-Path $src "refs") $dest -Recurse -Force   # refs last: its presence means "complete"
    Write-Host "   copied to $dest"
}

function Get-TableCounts {
    $sql = "SELECT 'documents', count(*) FROM documents UNION ALL SELECT 'chunks', count(*) FROM chunks UNION ALL SELECT 'entities', count(*) FROM entities ORDER BY 1;"
    $out = docker exec $Container psql -At -F "=" -U cee -d cee -c $sql
    if ($LASTEXITCODE -ne 0) { throw "Counting rows failed" }
    return ($out -join ", ")
}
