#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${POSTGRES_DB:-cadora}"
DB_USER="${POSTGRES_USER:-postgres}"

mkdir -p "$BACKUP_DIR"

pg_dump -h db -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"

# Keep only last 30 backups
ls -t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n +31 | xargs -r rm

echo "Backup complete: ${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
