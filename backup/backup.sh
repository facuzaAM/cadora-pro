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

# ── Encryption (optional) ────────────────────────────────────────────────
FINAL_FILE="$DUMP_FILE"
if [ -n "${BACKUP_GPG_PASSPHRASE:-}" ]; then
    ENCRYPTED_FILE="${DUMP_FILE}.gpg"
    gpg --batch --yes --pinentry-mode loopback \
        --passphrase "$BACKUP_GPG_PASSPHRASE" \
        --symmetric --cipher-algo AES256 -o "$ENCRYPTED_FILE" "$DUMP_FILE"
    rm -f "$DUMP_FILE"
    FINAL_FILE="$ENCRYPTED_FILE"
    echo "Backup encriptado: $FINAL_FILE"
fi

# ── Offsite upload (optional, Supabase Storage) ──────────────────────────
if [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_KEY:-}" ] && [ -n "${BACKUP_BUCKET:-}" ]; then
    OBJECT_NAME="$(basename "$FINAL_FILE")"
    if curl -sf -X POST \
        -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
        -H "Content-Type: application/octet-stream" \
        --data-binary "@$FINAL_FILE" \
        "$SUPABASE_URL/storage/v1/object/$BACKUP_BUCKET/$OBJECT_NAME"; then
        echo "Backup subido offsite: $BACKUP_BUCKET/$OBJECT_NAME"
    else
        echo "ERROR: falló la subida offsite de $OBJECT_NAME" >&2
    fi

    # Prune remote backups older than BACKUP_KEEP_DAYS (default 30).
    KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
    EXPIRED=$(date -d "-${KEEP_DAYS} days" +%Y%m%d_%H%M%S)
    LIST=$(curl -sf -X GET \
        -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
        "$SUPABASE_URL/storage/v1/object/list/$BACKUP_BUCKET" || true)
    if [ -n "$LIST" ]; then
        for NAME in $(echo "$LIST" | grep -oE '"name":"[^"]+"' | sed 's/"name":"//;s/"$//'); do
            TS=$(echo "$NAME" | sed 's/\.dump.*//' | tr -d '.')
            if [ -n "$TS" ] && [ "$TS" -lt "$EXPIRED" ]; then
                curl -sf -X DELETE \
                    -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
                    "$SUPABASE_URL/storage/v1/object/$BACKUP_BUCKET/$NAME" || true
                echo "Backup remoto antiguo eliminado: $NAME"
            fi
        done
    fi
fi

# Keep only last 30 local backups
ls -t "$BACKUP_DIR"/*.dump "$BACKUP_DIR"/*.dump.gpg 2>/dev/null | tail -n +31 | xargs -r rm

echo "Backup complete: $FINAL_FILE"
