#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${POSTGRES_DB:-cadora}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

if [ -z "$PGPASSWORD" ]; then
    echo "ERROR: POSTGRES_PASSWORD no definido, no se puede realizar el backup" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

DUMP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -F c -f "$DUMP_FILE"

# Verify the dump is a readable, non-empty custom-format archive.
if [ ! -s "$DUMP_FILE" ]; then
    echo "ERROR: backup is empty or missing: $DUMP_FILE" >&2
    exit 1
fi
if ! pg_restore --list "$DUMP_FILE" >/dev/null 2>&1; then
    echo "ERROR: backup failed integrity check: $DUMP_FILE" >&2
    exit 1
fi

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n +31 | xargs -r rm

echo "Backup complete: $DUMP_FILE"
