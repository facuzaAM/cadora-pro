#!/bin/sh
set -e

BACKUP_DIR="/backups"
RETENTION_DAYS=7

echo "$(date +%Y\-%m\-%d\ %H:%M:%S) — Starting PostgreSQL backup..."

FILENAME="cadora_$(date +%Y%m%d_%H%M%S).sql.gz"
pg_dump -h db -U "${POSTGRES_USER:-cadora}" -d "${POSTGRES_DB:-cadora}" | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "$(date +%Y\-%m\-%d\ %H:%M:%S) — Backup saved: ${FILENAME}"

# Remove backups older than retention period
find "${BACKUP_DIR}" -name "cadora_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "$(date +%Y\-%m\-%d\ %H:%M:%S) — Cleanup done. Backups remaining:"
ls -lh "${BACKUP_DIR}"/cadora_*.sql.gz 2>/dev/null || echo "  (none)"
