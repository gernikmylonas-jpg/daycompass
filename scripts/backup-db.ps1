# Saves the whole DayCompass database (accounts, journal, recordings, pictures... everything) to one file.
#   powershell -ExecutionPolicy Bypass -File scripts\backup-db.ps1            -> backups\daycompass-YYYY-MM-DD-HHMM.sql
# Keep the file somewhere safe: it contains personal data (and the encrypted journal, which stays encrypted).
param([string]$Container = 'daycompass-db', [string]$Folder = (Join-Path (Split-Path -Parent $PSScriptRoot) 'backups'))
New-Item -ItemType Directory -Force $Folder | Out-Null
$file = Join-Path $Folder ("daycompass-{0:yyyy-MM-dd-HHmm}.sql" -f (Get-Date))
# --clean --if-exists makes the file safe to restore over an existing database
docker exec $Container pg_dump -U postgres --clean --if-exists daycompass | Out-File -Encoding utf8 $file
if ($LASTEXITCODE -ne 0 -or (Get-Item $file).Length -lt 1000) { Write-Error 'Backup failed (is the database container running?)'; exit 1 }
Write-Host "Backup saved: $file ($([math]::Round((Get-Item $file).Length / 1KB)) KB)"
