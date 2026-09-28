#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"
KEY="fixture2030:session:S-TTL-DEMO"

echo "La politica real es TTL deslizante de 1800 s."
echo "Para no esperar 30 minutos, esta clave de evidencia usa 5 s."

docker exec "$C" redis-cli DEL "$KEY" >/dev/null
docker exec "$C" redis-cli HSET "$KEY" \
  session_id S-TTL-DEMO \
  user_id U-TTL-DEMO \
  created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  last_activity "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  access_status AUTHENTICATED >/dev/null
docker exec "$C" redis-cli EXPIRE "$KEY" 5 >/dev/null

echo "TTL inicial:"
docker exec "$C" redis-cli TTL "$KEY"

sleep 2

echo "TTL luego de 2 segundos:"
docker exec "$C" redis-cli TTL "$KEY"

sleep 4

echo "EXISTS luego del vencimiento (esperado 0):"
docker exec "$C" redis-cli EXISTS "$KEY"
