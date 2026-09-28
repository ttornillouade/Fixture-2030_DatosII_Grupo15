#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"
KEY="fixture2030:ranking:partidos:concurrencia:test"
OPS="${1:-10000}"
CLIENTS="${2:-50}"

docker exec "$C" redis-cli DEL "$KEY" >/dev/null

echo "Ejecutando $OPS ZINCRBY con $CLIENTS clientes concurrentes..."
docker exec "$C" redis-benchmark -q -n "$OPS" -c "$CLIENTS" \
  ZINCRBY "$KEY" 1 P001

docker exec "$C" redis-cli ZADD "$KEY" 250 P002 175 P003 >/dev/null
docker exec "$C" redis-cli EXPIRE "$KEY" 172800 >/dev/null

echo
echo "Score final de P001 (esperado: $OPS):"
docker exec "$C" redis-cli ZSCORE "$KEY" P001

echo
echo "Ranking temporal:"
docker exec "$C" redis-cli ZREVRANGE "$KEY" 0 9 WITHSCORES
