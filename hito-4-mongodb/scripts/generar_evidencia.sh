#!/usr/bin/env bash
# Levanta MongoDB, ejecuta validación, carga (dos veces, para mostrar que es idempotente),
# operaciones, agregación, índices y controles de integridad. Guarda la salida en docs/evidencia/.
# Uso: bash scripts/generar_evidencia.sh [--desde-cero]
#   --desde-cero  borra la base fixture2030 antes de empezar, para mostrar la carga inicial completa.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="docs/evidencia/evidencia_hito4_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p docs/evidencia ~/docker/data/mongodb
correr() { echo; echo "========== $1 =========="; docker exec fixture2030-mongodb mongosh --quiet "/scripts/$2"; }

{
  echo "EVIDENCIA HITO 4 — FIXTURE 2030 — MÓDULO DOCUMENTAL (MongoDB)"
  echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  docker compose up -d 2>&1
  until docker exec fixture2030-mongodb mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1; do sleep 2; done
  docker compose ps
  echo "MongoDB: $(docker exec fixture2030-mongodb mongosh --quiet --eval 'db.version()')"
  if [ "${1:-}" = "--desde-cero" ]; then
    echo; echo "========== 0. Base fixture2030 borrada (--desde-cero) =========="
    docker exec fixture2030-mongodb mongosh --quiet --eval 'printjson(db.getSiblingDB("fixture2030").dropDatabase())'
  fi
  correr "1. Validación (RF7)" 01_validacion.js
  correr "2. Carga inicial (RF4, RF5, RF8)" 02_carga.js
  correr "2b. Segunda carga: no debe insertar nada (idempotencia)" 02_carga.js
  correr "3. Operaciones (RF9, RF10)" 03_operaciones.js
  correr "4. Agregación (RF11)" 04_agregacion.js
  correr "5. Índices y rendimiento (RF12, RF13)" 05_indices_rendimiento.js
  correr "6. Integridad (RNF2, RNF3)" 06_integridad.js
} 2>&1 | tee "$OUT"
echo; echo "Evidencia guardada en $OUT"
