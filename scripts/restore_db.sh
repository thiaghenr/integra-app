#!/usr/bin/env bash
# Restores integra_db from a backup produced by backup_db.sh.
# Usage: ./scripts/restore_db.sh [path/to/backup.sql.gz]
# With no argument, restores the most recent file in backups/.
#
# WARNING: this overwrites all current data in the dev database.
set -euo pipefail

cd "$(dirname "$0")/.."

set -a
source .env
set +a

FILE="${1:-}"
if [ -z "$FILE" ]; then
  FILE=$(ls -1t backups/"${POSTGRES_DB}"_*.sql.gz 2>/dev/null | head -1)
fi

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "No backup file found. Usage: $0 [path/to/backup.sql.gz]" >&2
  exit 1
fi

echo "About to restore '$FILE' into '$POSTGRES_DB', overwriting all current data."
read -r -p "Type 'yes' to continue: " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

gunzip -c "$FILE" | docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "Restore complete from $FILE."
