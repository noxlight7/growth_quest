#!/bin/sh
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
DB_HOST=${POSTGRES_HOST:-db}
DB_PORT=${POSTGRES_PORT:-5432}
DB_NAME=${POSTGRES_DB:-app_db}
DB_USER=${POSTGRES_USER:-app_user}

mkdir -p "$BACKUP_DIR"

timestamp=$(date +"%Y%m%d_%H%M%S")
backup_file="$BACKUP_DIR/${DB_NAME}_${timestamp}.sql.gz"

export PGPASSWORD=${POSTGRES_PASSWORD:-}
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip -c > "$backup_file"

# Keep only the 7 newest backups.
old_backups=$(ls -1t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -n +8 || true)
if [ -n "$old_backups" ]; then
  echo "$old_backups" | xargs rm -f --
fi
