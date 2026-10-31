#!/usr/bin/env bash
# Evaluación de conectividad del Fixture 2030 (Hito 11), desde la notebook donde corre la API.
#
#   bash scripts/evaluar_conectividad.sh [--modo completo|tcp|clientes|api] [--producto p1,p2]
#     --modo      completo (por defecto): configuración y TCP -> clientes (driver) -> API
#     --producto  mongodb, neo4j, cassandra, redis, influxdb, iris (por defecto, todos). En modo api
#                 también "api" (liveness y diagnóstico por dependencia).
#
# Guarda en docs/evidencia/: resultados_tcp.txt, resultados_clientes.txt, resultados_api.txt,
# resultados.jsonl y matriz.md. Al final verifica que ningún secreto de .env aparezca en la evidencia.
# SKIP = prueba no ejecutada por falta de herramienta o configuración; NO significa producto caído.
set -uo pipefail
cd "$(dirname "$0")/.."

MODO=completo
PRODUCTOS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --modo) MODO="$2"; shift 2 ;;
    --producto) PRODUCTOS="${2//,/ }"; shift 2 ;;
    *) echo "Opción desconocida: $1 (ver el encabezado del script)" >&2; exit 2 ;;
  esac
done
case "$MODO" in completo|tcp|clientes|api) ;; *) echo "Modo inválido: $MODO" >&2; exit 2 ;; esac

PY=../hito-10-api/.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "SKIP  todo: falta el entorno virtual de la API (../hito-10-api/.venv), que tiene los drivers." >&2
  echo "      Crearlo como indica el README del Hito 10; sin él no se puede ejecutar ninguna prueba." >&2
  exit 1
fi

EVID=docs/evidencia
mkdir -p "$EVID"
export RESULTADOS="$EVID/resultados.jsonl"
: > "$RESULTADOS"

encabezado() {
  local commit cambios docker
  commit=$(git rev-parse --short HEAD 2>/dev/null || echo "sin git")
  cambios=$(git status --porcelain --untracked-files=no 2>/dev/null | grep -q . && echo " + cambios sin commit" || true)
  docker=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "no disponible (SKIP)")
  echo "FIXTURE 2030 — HITO 11 — $1"
  echo "Fecha:    $(date '+%Y-%m-%d %H:%M:%S %Z') ($(date -u '+%Y-%m-%dT%H:%M:%SZ'))"
  echo "Commit:   $commit$cambios"
  echo "Entorno:  notebook $(uname -sm), $($PY --version), Docker $docker"
  echo "Origen:   las pruebas corren en la notebook, el mismo host que la API: localhost = la notebook"
  echo "Modo:     $MODO; productos: ${PRODUCTOS:-todos}; TIMEOUT_S de la configuración"
  echo "Columnas: resultado, producto, capa, duración, prueba: detalle"
  echo
}

correr() { # titulo archivo script productos...
  local titulo=$1 archivo=$2 script=$3; shift 3
  { encabezado "$titulo"; $PY "scripts/$script" "$@" 2>&1; } | tee "$EVID/$archivo"
  echo
}

# shellcheck disable=SC2086  # PRODUCTOS es una lista separada por espacios
if [ "$MODO" = completo ] || [ "$MODO" = tcp ]; then
  correr "Configuración, resolución y TCP" resultados_tcp.txt prueba_tcp.py $PRODUCTOS
fi
if [ "$MODO" = completo ] || [ "$MODO" = clientes ]; then
  correr "Clientes (protocolo, identidad, contexto, lectura)" resultados_clientes.txt prueba_clientes.py $PRODUCTOS
fi
if [ "$MODO" = completo ] || [ "$MODO" = api ]; then
  # Sin --producto, la prueba de la API incluye también liveness y el diagnóstico por dependencia.
  correr "API del Hito 10 (cadena completa)" resultados_api.txt prueba_api.py ${PRODUCTOS:-api mongodb neo4j cassandra redis influxdb iris}
fi

{ echo "# Matriz de conectividad — $(date '+%Y-%m-%d %H:%M %Z')"; echo
  echo "Commit $(git rev-parse --short HEAD 2>/dev/null)$(git status --porcelain --untracked-files=no 2>/dev/null | grep -q . && echo ' + cambios sin commit'); modo $MODO; productos: ${PRODUCTOS:-todos}; origen: notebook."
  echo; $PY scripts/resumen.py "$RESULTADOS"; } > "$EVID/matriz.md"
cat "$EVID/matriz.md"

# Ningún valor secreto de la configuración puede aparecer en la evidencia (RNF7, RNF8).
$PY -c "
import sys; sys.path.insert(0, 'scripts')
from comun import cargar_config, es_secreto
for clave, valor in cargar_config().items():
    if es_secreto(clave) and valor:
        print(valor)
" | while read -r secreto; do
  if grep -rqF --exclude=api.log -- "$secreto" "$EVID"; then echo "ALERTA: un secreto aparece en $EVID" >&2; exit 1; fi
done && echo && echo "Verificación de secretos: ningún secreto de la configuración aparece en $EVID."
