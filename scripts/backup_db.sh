#!/usr/bin/env bash
# Dumps the local dev Postgres DB (docker compose "db" service) to backups/,
# gzip'd and timestamped. Keeps the most recent 14 dumps, prunes older ones.
#
# Run manually:      ./scripts/backup_db.sh
# Run automatically:  ./scripts/install_backup_schedule.sh  (macOS launchd, every 6h)
set -euo pipefail

# launchd runs this with a minimal PATH that doesn't include where Docker's
# CLI lives, which silently no-ops every check below — force it explicitly.
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

cd "$(dirname "$0")/.."

set -a
source .env
set +a

BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

if ! docker compose ps db --status running --format '{{.Name}}' 2>/dev/null | grep -q .; then
  echo "backup_db.sh: 'db' service is not running, skipping backup." >&2
  exit 0
fi

docker compose exec -T db pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$OUT_FILE"
echo "Backup written to $OUT_FILE"

# Prune: keep only the 14 most recent backups.
ls -1t "$BACKUP_DIR"/"${POSTGRES_DB}"_*.sql.gz 2>/dev/null | tail -n +15 | while IFS= read -r f; do
  rm -f -- "$f"
done
