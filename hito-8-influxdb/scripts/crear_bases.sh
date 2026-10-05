#!/usr/bin/env bash
# Crea las bases con su política de retención (RF10):
#   fixture2030_vivo       14d   precisión original (ms), consultas en vivo y post-partido
#   fixture2030_historico  none  resúmenes de 1 minuto (downsampling), análisis histórico
. "$(dirname "$0")/comun.sh"
requiere_token

crear() {
  local db="$1" ret="$2"
  if influx_auth show databases 2>/dev/null | grep -qw "$db"; then
    echo "La base $db ya existe (no se modifica)."
    return
  fi
  # InfluxDB 3 Core no acepta "none" en --retention-period: sin el parámetro la retención es indefinida.
  if [ "$ret" = "none" ]; then
    influx_auth create database "$db" && echo "Base $db creada sin retención (indefinida)"
    return
  fi
  if influx_auth create database --retention-period "$ret" "$db"; then
    echo "Base $db creada con retención $ret"
  else
    echo "AVISO: esta versión no aceptó --retention-period; se crea $db sin retención." >&2
    echo "       Registrar la versión observada y aplicar la política documentada manualmente." >&2
    influx_auth create database "$db"
  fi
}

titulo "Bases de datos"
crear "$DB_VIVO" "$RET_VIVO"
crear "$DB_HIST" "$RET_HIST"

titulo "influxdb3 show databases"
influx_auth show databases
titulo "influxdb3 show databases --format json (incluye retención si la versión la informa)"
influx_auth show databases --format json || true
