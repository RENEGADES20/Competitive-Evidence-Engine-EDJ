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

function Get-TableCounts {
    $sql = "SELECT 'documents', count(*) FROM documents UNION ALL SELECT 'chunks', count(*) FROM chunks UNION ALL SELECT 'entities', count(*) FROM entities ORDER BY 1;"
    $out = docker exec $Container psql -At -F "=" -U cee -d cee -c $sql
    if ($LASTEXITCODE -ne 0) { throw "Counting rows failed" }
    return ($out -join ", ")
}
