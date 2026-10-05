#!/usr/bin/env bash
# Funciones comunes. Se incluye desde los demás scripts: . "$(dirname "$0")/comun.sh"
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; . ./.env; set +a; fi
C="${IRIS_CONTAINER:-fixture2030-iris}"
NS="${IRIS_NAMESPACE:-USER}"
DATA_DIR="$HOME/docker/data/iris"

titulo() { printf '\n========== %s ==========\n' "$1"; }

requiere_env() {
  if [ ! -f .env ]; then
    echo "Falta .env: ejecutar  cp .env.example .env  y cambiar IRIS_PASSWORD" >&2
    exit 1
  fi
}

requiere_contenedor() {
  if [ "$(docker inspect -f '{{.State.Running}}' "$C" 2>/dev/null)" != "true" ]; then
    echo "El contenedor $C no está corriendo: ejecutar  bash scripts/inicializacion.sh" >&2
    exit 1
  fi
}

# Ejecuta ObjectScript leído de stdin en la terminal de IRIS del contenedor.
iris_terminal() { docker exec -i "$C" iris session IRIS -U "$NS"; }

# Ejecuta un punto de entrada, por ejemplo: iris_ejecutar '##class(Fixture.Demo).Ejecutar()'
iris_ejecutar() { docker exec -i "$C" iris session IRIS -U "$NS" "$1"; }

# Oculta la contraseña local si llegara a aparecer en alguna salida.
enmascarar() {
  if [ -n "${IRIS_PASSWORD:-}" ]; then sed "s/${IRIS_PASSWORD//\//\\/}/****OCULTO****/g"; else cat; fi
}
