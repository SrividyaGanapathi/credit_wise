#!/bin/sh
set -eu

python -m alembic upgrade head
# Seed reference data only when explicitly requested for a controlled deploy.
if [ "${RUN_SEED_ON_STARTUP:-false}" = "true" ]; then
  python -m data.seed
fi
exec uvicorn app:app --host "${APP_HOST:-0.0.0.0}" --port "${PORT:-8000}"
