#!/usr/bin/env bash
# Detiene Prometheus, Grafana y los exporters. NO toca las seis bases ni sus datos.
#   bash scripts/limpiar_entorno.sh            -> detiene y elimina los contenedores de monitoreo
#   bash scripts/limpiar_entorno.sh --datos    -> además borra los volúmenes de Prometheus y Grafana
#                                                (solo series y estado de Grafana; se pierde el historial)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${1:-}" = "--datos" ]; then
  docker compose down --volumes
else
  docker compose down
fi
