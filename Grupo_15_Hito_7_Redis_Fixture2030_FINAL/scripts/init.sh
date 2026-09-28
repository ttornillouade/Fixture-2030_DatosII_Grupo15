#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a

C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"

echo "Esperando Redis..."
until docker exec "$C" redis-cli PING 2>/dev/null | grep -q PONG; do
  sleep 1
done

echo "Inicializando metadatos..."
docker exec -i "$C" redis-cli < scripts/inicializacion.redis

echo "Cargando muestra reproducible..."
docker exec -i "$C" redis-cli < scripts/carga_muestra.redis

echo "Redis listo."
