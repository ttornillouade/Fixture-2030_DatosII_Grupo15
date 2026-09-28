#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"

echo "=== CRUD Y RENOVACION DE SESION ==="
docker exec -i "$C" redis-cli < scripts/sesiones.redis
