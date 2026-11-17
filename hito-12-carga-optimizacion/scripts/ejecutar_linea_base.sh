#!/usr/bin/env bash
# LÍNEA BASE: la API del Hito 10 tal como estaba (1 proceso uvicorn, sin caché).
# Repite el escenario N veces (por defecto 3) para ver la variación entre corridas.
set -euo pipefail
cd "$(dirname "$0")/.."
for i in $(seq 1 "${REPETICIONES:-3}"); do
  bash scripts/correr_escenario.sh "linea_base_r$i" 1 0
done
