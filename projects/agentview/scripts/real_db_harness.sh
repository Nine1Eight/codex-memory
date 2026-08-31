#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
COMPOSE_FILE="$ROOT_DIR/compose.yaml"

docker compose -f "$COMPOSE_FILE" up -d postgres
trap 'docker compose -f "$COMPOSE_FILE" down -v --remove-orphans' EXIT INT TERM

for _ in $(seq 1 60); do
  if docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U agentview -d agentview >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U agentview -d agentview -v ON_ERROR_STOP=1 -f /workspace/migrations/0001_initial.sql

