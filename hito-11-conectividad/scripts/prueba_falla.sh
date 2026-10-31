#!/usr/bin/env bash
# Falla controlada y reversible de una dependencia (5.7, RF20, RF21). No borra datos ni volúmenes.
#
#   bash scripts/prueba_falla.sh detener <producto>   docker stop:  el puerto deja de aceptar (caída)
#   bash scripts/prueba_falla.sh pausar  <producto>   docker pause: acepta TCP pero no responde (colgada)
#
# Registra condición inicial, cambio, respuesta de la API y su log, estado en /salud/dependencias,
# prueba TCP, recuperación y una huella de los datos antes y después. Requiere la API corriendo con
# su salida en API_LOG. Guarda la salida en docs/evidencia/falla_<accion>_<producto>.txt.
set -uo pipefail
cd "$(dirname "$0")/.."
ACCION=${1:-}; PRODUCTO=${2:-}
PY=../hito-10-api/.venv/bin/python
API=$(grep -E '^API_URL=' config/configuracion-ejemplo.env | cut -d= -f2)
API_LOG=$(grep -E '^API_LOG=' config/configuracion-ejemplo.env | cut -d= -f2)
[ -f config/local.env ] && . config/local.env

case "$PRODUCTO" in
  mongodb)   RUTA="/equipos/E010";                 OTRA="/partidos/P001/detalle" ;;
  neo4j)     RUTA="/jugadores/E001-J09/partidos";  OTRA="/equipos/E010" ;;
  cassandra) RUTA="/partidos/P001/comentarios?bucket=2030-06-08T20:00:00Z&limit=2"; OTRA="/equipos/E010" ;;
  redis)     RUTA="/sesiones/s-demo-001";          OTRA="/equipos/E010" ;;
  influxdb)  RUTA="/partidos/P001/estadisticas?desde=2030-06-08T16:00:00Z&hasta=2030-06-08T16:00:02Z"; OTRA="/partidos/P001/detalle" ;;
  iris)      RUTA="/partidos/P001/detalle";        OTRA="/equipos/E010" ;;
  *) echo "Uso: bash scripts/prueba_falla.sh detener|pausar mongodb|neo4j|cassandra|redis|influxdb|iris" >&2; exit 2 ;;
esac
case "$ACCION" in
  detener) APLICAR=stop;  RECUPERAR=start ;;
  pausar)  APLICAR=pause; RECUPERAR=unpause ;;
  *) echo "Acción inválida: $ACCION (detener o pausar)" >&2; exit 2 ;;
esac
command -v docker >/dev/null || { echo "SKIP: docker no está disponible en este entorno" >&2; exit 1; }
C="fixture2030-$PRODUCTO"
OUT="docs/evidencia/falla_${ACCION}_${PRODUCTO}.txt"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

pedir() { # ruta -> "status ms requestId cuerpo"
  curl -s -m 15 -D $TMP/headers -o $TMP/cuerpo -w "%{http_code} %{time_total}" "$API$1" \
    | awk '{printf "HTTP %s en %.0f ms", $1, $2*1000}'
  printf " | %s | %s\n" "$(grep -i '^x-request-id' $TMP/headers | tr -d '\r' | cut -d' ' -f2)" \
    "$(head -c 160 $TMP/cuerpo)"
}
log_de() { sleep 0.2; grep -F "$(grep -i '^x-request-id' $TMP/headers | tr -d '\r' | cut -d' ' -f2)" "$API_LOG" \
  | sed -E 's/^[0-9-]+ [0-9:,]+ //' | tail -2; }
huella() { # el cuerpo sin campos que cambian solos (requestId, TTL), resumido en un hash
  curl -s -m 15 "$API$RUTA" | $PY -c "
import hashlib, json, sys
d = json.load(sys.stdin); [d.pop(k, None) for k in ('requestId', 'expiraEnSegundos')]
print(hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16])"; }
estado_salud() { curl -s -m 15 "$API/salud/dependencias" | $PY -c "
import json, sys
d = json.load(sys.stdin); x = {e['nombre'].lower(): e for e in d['dependencias']}['$PRODUCTO']
print(f\"global={d['estado']}; $PRODUCTO={x['estado']} codigo={x['codigo']} ms={x['ms']}\")"; }
# Solo los montajes de datos (no los scripts de inicialización), con ~ en lugar de la ruta personal.
montajes() { docker inspect "$C" --format '{{range .Mounts}}{{.Source}}->{{.Destination}} {{end}}' | tr ' ' '\n' \
  | grep -E '/docker/data/' | sed "s|$HOME|~|" | tr '\n' ' '; }

{
  echo "FIXTURE 2030 — HITO 11 — Falla controlada: $ACCION $PRODUCTO ($C)"
  echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S %Z') | Commit: $(git rev-parse --short HEAD) | Origen: notebook | API: $API"
  echo; echo "== 1. Condición inicial"
  echo "Contenedor: $(docker inspect "$C" --format '{{.State.Status}} ({{.State.Health.Status}})' 2>/dev/null)"
  echo "GET $RUTA -> $(pedir "$RUTA")"
  H0=$(huella); M0=$(montajes)
  echo "Huella de los datos: $H0 | volúmenes: $M0"
  echo "Salud: $(estado_salud)"

  echo; echo "== 2. Cambio aplicado: docker $APLICAR $C ($(date '+%H:%M:%S'))"
  docker "$APLICAR" "$C" >/dev/null

  echo; echo "== 3. Durante la falla"
  echo "GET $RUTA -> $(pedir "$RUTA")"
  echo "Log de la API:"; log_de | sed 's/^/  /'
  echo "Otra fuente: GET $OTRA -> $(pedir "$OTRA" | cut -d'|' -f1)"
  echo "Salud: $(estado_salud)"
  echo "TCP desde la notebook:"; $PY scripts/prueba_tcp.py "$PRODUCTO" 2>&1 | grep " tcp " | head -1 | sed 's/^/  /'

  echo; echo "== 4. Recuperación: docker $RECUPERAR $C ($(date '+%H:%M:%S'))"
  docker "$RECUPERAR" "$C" >/dev/null
  inicio=$(date +%s)
  for i in $(seq 1 180); do
    [ "$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$API$RUTA")" = 200 ] && break; sleep 1
  done
  echo "La ruta volvió a responder 200 a los $(( $(date +%s) - inicio )) s, sin reiniciar la API"

  echo; echo "== 5. Después de recuperar (se repite la prueba)"
  echo "GET $RUTA -> $(pedir "$RUTA")"
  H1=$(huella); M1=$(montajes)
  echo "Huella de los datos: $H1 ($([ "$H0" = "$H1" ] && echo 'igual a la inicial: datos conservados' || echo 'DISTINTA a la inicial'))"
  echo "Volúmenes: $([ "$M0" = "$M1" ] && echo 'los mismos montajes, no se borró nada' || echo "CAMBIARON: $M1")"
  echo "Salud: $(estado_salud)"
} 2>&1 | sed "s|$HOME|~|g" | tee "$OUT"
