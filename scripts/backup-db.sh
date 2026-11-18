#!/bin/sh
# Same as backup-db.ps1, for a Linux server: ./scripts/backup-db.sh  (cron it daily, e.g. 0 3 * * *)
set -e
cd "$(dirname "$0")/.."
mkdir -p backups
file="backups/daycompass-$(date +%Y-%m-%d-%H%M).sql"
docker exec "${DB_CONTAINER:-daycompass-db}" pg_dump -U postgres --clean --if-exists daycompass > "$file"
# keep the 14 newest, delete older ones
ls -1t backups/daycompass-*.sql | tail -n +15 | xargs -r rm --
echo "Backup saved: $file"
