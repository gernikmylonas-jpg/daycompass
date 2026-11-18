#!/bin/sh
# Restores a backup into the database (REPLACES current data): ./scripts/restore-db.sh backups/daycompass-....sql
set -e
[ -f "$1" ] || { echo "Usage: $0 backups/daycompass-....sql"; exit 1; }
docker exec -i "${DB_CONTAINER:-daycompass-db}" psql -U postgres -d "${DB_NAME:-daycompass}" -q < "$1" > /dev/null
echo "Restored $1"
