#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${REDIS_CONTAINER_NAME:-fixture2030-redis}"

mkdir -p docs/evidencia
OUT="docs/evidencia/evidencia_hito7_$(date +%Y%m%d_%H%M%S).txt"

{
  echo "EVIDENCIA HITO 7 - FIXTURE 2030"
  echo "Fecha: $(date)"
  echo

  echo "=== DOCKER ==="
  docker compose ps
  echo

  echo "=== REDIS VERSION ==="
  docker exec "$C" redis-server --version
  echo

  echo "=== DISPONIBILIDAD ==="
  docker exec "$C" redis-cli PING
  echo

  echo "=== CONFIGURACION DE MEMORIA ==="
  docker exec "$C" redis-cli CONFIG GET maxmemory
  docker exec "$C" redis-cli CONFIG GET maxmemory-policy
  echo

  echo "=== SESIONES ==="
  bash scripts/run_sesiones.sh
  echo

  echo "=== EXPIRACION NATIVA ==="
  bash scripts/demo_expiracion.sh
  echo

  echo "=== CACHE-ASIDE + INVALIDACION ==="
  bash scripts/demo_cache.sh
  echo

  echo "=== CONCURRENCIA + RANKING ==="
  bash scripts/prueba_concurrencia.sh 10000 50
  echo

  echo "=== METRICAS ==="
  docker exec -i "$C" redis-cli < scripts/metricas.redis
} | tee "$OUT"

echo
echo "Evidencia guardada en $OUT"
echo "Ejecutar además scripts/prueba_rendimiento.sh para RF12."
