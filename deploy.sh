#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/cadora"
BRANCH="${1:-main}"

echo "→ Pulling latest code ($BRANCH)..."
cd "$APP_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

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
