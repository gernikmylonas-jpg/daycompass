# Puts a backup file back into the database. THIS REPLACES the current data in that database.
#   powershell -ExecutionPolicy Bypass -File scripts\restore-db.ps1 -File backups\daycompass-2026-11-19-2100.sql
#   (add -Database daycompass_check to try a backup in a separate, throw-away database first)
param([Parameter(Mandatory = $true)][string]$File, [string]$Container = 'daycompass-db', [string]$Database = 'daycompass')
if (-not (Test-Path $File)) { Write-Error "File not found: $File"; exit 1 }
if ($Database -ne 'daycompass') { docker exec $Container psql -U postgres -c "CREATE DATABASE $Database" 2>$null | Out-Null }
Get-Content $File -Raw -Encoding utf8 | docker exec -i $Container psql -U postgres -d $Database -v ON_ERROR_STOP=0 -q | Out-Null
Write-Host "Restored $File into database '$Database'."
