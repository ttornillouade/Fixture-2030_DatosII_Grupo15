#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"
N="${1:-50000}"
CLIENTS="${2:-50}"

mkdir -p docs/evidencia
OUT="docs/evidencia/rendimiento_hito7_$(date +%Y%m%d_%H%M%S).txt"

{
  echo "RENDIMIENTO HITO 7 - REDIS"
  echo "Fecha: $(date)"
  echo "Operaciones por prueba: $N"
  echo "Clientes concurrentes: $CLIENTS"
  echo

  echo "=== VERSION ==="
  docker exec "$C" redis-server --version
  echo

  echo "=== RECURSOS DEL CONTENEDOR ==="
  docker stats "$C" --no-stream
  echo

  echo "=== SET CON TTL ==="
  docker exec "$C" redis-benchmark -q -n "$N" -c "$CLIENTS" -r 100000 \
    SET fixture2030:bench:cache:__rand_int__ value EX 300
  echo

  echo "=== GET ==="
  docker exec "$C" redis-benchmark -q -n "$N" -c "$CLIENTS" -r 100000 \
    GET fixture2030:bench:cache:__rand_int__
  echo

  echo "=== HSET SESION ==="
  docker exec "$C" redis-benchmark -q -n "$N" -c "$CLIENTS" -r 100000 \
    HSET fixture2030:bench:session:__rand_int__ user_id U-BENCH access_status AUTHENTICATED
  echo

  echo "=== MEMORIA ==="
  docker exec "$C" redis-cli INFO memory
} | tee "$OUT"

echo
echo "Resultado guardado en $OUT"
echo "Las claves benchmark son temporales o de prueba; no se usan como evidencia funcional."
