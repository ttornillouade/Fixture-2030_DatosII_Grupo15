#!/usr/bin/env bash
# PRUEBA OPTIMIZADA: el mismo escenario (config/escenario.json) y los mismos datos que la línea base,
# cambiando solo la configuración de la API. Cada configuración se repite N veces (por defecto 3).
#   cache          Optimización 1: micro-caché en Redis de la primera página (TTL 1000 ms), 1 proceso
#   workers        Optimización 2 sola: 3 procesos uvicorn, sin caché (para separar el efecto de cada cambio)
#   cache_workers  Optimizaciones 1 + 2: caché + 3 procesos (configuración final propuesta)
# Uso: bash scripts/ejecutar_prueba_optimizada.sh [cache|workers|cache_workers|todas]
set -euo pipefail
cd "$(dirname "$0")/.."
CUAL=${1:-todas}
correr() { # nombre workers ttl_ms
  for i in $(seq 1 "${REPETICIONES:-3}"); do
    bash scripts/correr_escenario.sh "optimizada_$1_r$i" "$2" "$3"
  done
}
case "$CUAL" in
  cache)         correr cache 1 1000 ;;
  workers)       correr workers 3 0 ;;
  cache_workers) correr cache_workers 3 1000 ;;
  todas)         correr cache 1 1000; correr workers 3 0; correr cache_workers 3 1000 ;;
  *) echo "Uso: $0 [cache|workers|cache_workers|todas]" >&2; exit 1 ;;
esac
