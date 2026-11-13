#!/usr/bin/env bash
# Corre UNA vez el escenario de carga completo con una configuración de API dada:
#   preparación de la API -> carga y medición -> latencia del servidor -> validación de integridad -> detener API
# Uso: bash scripts/correr_escenario.sh <etiqueta> <workers> <cache_ttl_ms>
# Lo llaman ejecutar_linea_base.sh y ejecutar_prueba_optimizada.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
ETIQUETA=$1; WORKERS=${2:-1}; CACHE_TTL_MS=${3:-0}
PY=.venv/bin/python
[ -x "$PY" ] || [ -x "$PY.exe" ] || { echo "Falta el entorno: ver README (Preparación)" >&2; exit 1; }
LOG=config/api_${ETIQUETA}.log   # no versionado: el resumen del log queda en servidor.json
trap '$PY scripts/api_lab.py detener' EXIT

echo "== API: workers=$WORKERS cache_ttl_ms=$CACHE_TTL_MS"
PID=$($PY scripts/api_lab.py iniciar --log "$LOG" --workers "$WORKERS" --cache-ttl-ms "$CACHE_TTL_MS")
echo "== Carga ($ETIQUETA)"
$PY scripts/ejecutar_carga.py --etiqueta "$ETIQUETA" --api-pid "$PID"
echo "== Latencia del lado del servidor"
$PY scripts/analizar_log_api.py --etiqueta "$ETIQUETA" --log "$LOG" > /dev/null
echo "== Integridad"
$PY scripts/validar_integridad.py --etiqueta "$ETIQUETA" --cache-ttl-ms "$CACHE_TTL_MS" | grep -E '"(aceptadas_201|faltan_en_por_partido|faltan_en_por_usuario|sobrantes_vs_201|ids_duplicados|coincide|integridad_ok)"'
