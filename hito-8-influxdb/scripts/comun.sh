#!/usr/bin/env bash
# Funciones y variables comunes a todos los scripts del Hito 8.
set -euo pipefail

DIR_RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR_RAIZ"

if [ -f .env ]; then set -a; . ./.env; set +a; fi

C="${INFLUX_CONTAINER:-fixture2030-influxdb}"
PORT="${INFLUX_PORT:-8181}"
URL="${INFLUX_URL:-http://localhost:${PORT}}"
DB_VIVO="${INFLUX_DB_VIVO:-fixture2030_vivo}"
DB_HIST="${INFLUX_DB_HISTORICO:-fixture2030_historico}"
RET_VIVO="${INFLUX_RETENCION_VIVO:-14d}"
RET_HIST="${INFLUX_RETENCION_HISTORICO:-none}"
PY="${PYTHON:-python3}"

# CLI incluido en el contenedor, sin token (version, ayuda, crear el primer token).
influx() { docker exec "$C" influxdb3 "$@"; }

# CLI incluido en el contenedor, autenticado. El token viaja como variable de
# entorno (INFLUXDB3_AUTH_TOKEN) y no aparece en la línea de comandos.
influx_auth() {
  requiere_token
  INFLUXDB3_AUTH_TOKEN="$INFLUX_TOKEN" docker exec -e INFLUXDB3_AUTH_TOKEN "$C" influxdb3 "$@"
}

requiere_token() {
  if [ -z "${INFLUX_TOKEN:-}" ]; then
    echo "ERROR: falta INFLUX_TOKEN en .env. Ejecutar: bash scripts/autorizacion.sh" >&2
    exit 1
  fi
}

# Oculta cualquier token en la salida (evidencia sin secretos, RNF7).
enmascarar() { sed -E 's/apiv3_[A-Za-z0-9_-]+/apiv3_****OCULTO****/g'; }

titulo() { printf '\n========== %s ==========\n' "$*"; }
