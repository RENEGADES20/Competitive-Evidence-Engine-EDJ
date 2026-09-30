<#
Load every document in data\manifest.csv into your local database (adds or replaces rows).
Needs the raw files: in CORPUS_SHARE_PATH\raw (Box Drive) or in .\data\raw.

  powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1
  powershell -ExecutionPolicy Bypass -File scripts\ingest.ps1 -Doc EDJ-10K-2025
#>
param([string]$Doc)
. "$PSScriptRoot\_common.ps1"

Start-Database
if ($Doc) { Invoke-Native { & $Python -m cee.ingest.load --doc $Doc } "Ingestion" }
else { Invoke-Native { & $Python -m cee.ingest.load } "Ingestion" }
Write-Host "Row counts: $(Get-TableCounts)"
