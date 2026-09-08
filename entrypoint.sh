#!/bin/sh
set -e

# ECS injeta usuario/senha do RDS via Secrets Manager (POSTGRES_USER /
# POSTGRES_PASSWORD) e host/port/db como env var comum (nao sao segredo) --
# nao existe uma DATABASE_URL pronta em lugar nenhum, entao montamos aqui.
# Se DATABASE_URL ja vier setada (dev local via .env), respeita e nao mexe.
if [ -z "$DATABASE_URL" ] && [ -n "$POSTGRES_HOST" ]; then
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

# Se um comando explicito for passado (ex.: override de task do ECS pra
# rodar "alembic stamp X" manualmente), roda ele em vez do fluxo padrao --
# usado so pra diagnostico/correcao manual do estado do banco. Sem args
# (caso normal do service), segue o fluxo de sempre.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec python -m app.main
