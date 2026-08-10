#!/bin/sh
set -e

# ECS injeta usuario/senha do RDS via Secrets Manager (POSTGRES_USER /
# POSTGRES_PASSWORD) e host/port/db como env var comum (nao sao segredo) --
# nao existe uma DATABASE_URL pronta em lugar nenhum, entao montamos aqui.
# Se DATABASE_URL ja vier setada (dev local via .env), respeita e nao mexe.
if [ -z "$DATABASE_URL" ] && [ -n "$POSTGRES_HOST" ]; then
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec python -m app.main
