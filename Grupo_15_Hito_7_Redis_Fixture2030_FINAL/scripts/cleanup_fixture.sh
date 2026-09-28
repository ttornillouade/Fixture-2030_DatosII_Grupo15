#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"

echo "Eliminando solo claves fixture2030:* mediante SCAN + UNLINK..."
docker exec "$C" sh -c '
  redis-cli --scan --pattern "fixture2030:*" |
  while IFS= read -r key; do
    redis-cli UNLINK "$key" >/dev/null
  done
'
echo "Limpieza terminada."
