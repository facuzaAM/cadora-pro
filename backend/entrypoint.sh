#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16'
