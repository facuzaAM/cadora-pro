#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/cadora"
BRANCH="${1:-main}"

echo "→ Pulling latest code ($BRANCH)..."
cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

# Snapshot the DB before any schema migration runs (entrypoint runs
# `alembic upgrade head`). A raw pg_dump in the backups volume is the recovery
# point; the offsite/GPG parts of backup.sh aren't needed here and can fail
# for unrelated reasons, so we warn (not abort) on a failed snapshot. On a
# first deploy there is no container yet and the snapshot is skipped.
echo "→ Backing up database before deployment..."
if docker compose ps --format '{{.Service}}' 2>/dev/null | grep -q '^backup$'; then
  docker compose exec -T backup bash -c \
    'mkdir -p /backups && pg_dump -h "${POSTGRES_HOST:-db}" -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-cadora}" -F c -f "/backups/predeploy_$(date +%Y%m%d_%H%M%S).dump"' \
    && echo "  ✓ Pre-deploy DB snapshot created" \
    || echo "  ⚠ No se pudo crear el snapshot pre-deploy (deploy continúa)"
else
  echo "  ⚠ backup container no está corriendo — se omite snapshot pre-deploy"
fi

echo "→ Rebuilding and restarting services..."
docker compose up --build -d --remove-orphans

echo "→ Running health checks..."
sleep 5

SITE_URL="${SITE_URL:-https://cadora.pro}"

check() {
  local name=$1 url=$2 max=12
  for i in $(seq 1 $max); do
    if curl -sf "$url" > /dev/null 2>&1; then
      echo "  ✓ $name is healthy"
      return 0
    fi
    sleep 5
  done
  echo "  ✗ $name failed health check after $((max * 5))s"
  return 1
}

check "Frontend" "$SITE_URL/"
check "API" "$SITE_URL/api/v1/readyz"

echo "→ Pruning unused images..."
docker image prune -f

echo "✓ Deploy complete"
