#!/usr/bin/env bash
# PA1 — Last Value Cache: último estado por (partido, equipo) y por (partido, plataforma).
# Requiere que las tablas existan (ejecutar después de la primera carga).
. "$(dirname "$0")/comun.sh"
requiere_token

crear_lvc() {
  local tabla="$1" claves="$2" valores="$3" nombre="$4"
  if influx_auth create last_cache --database "$DB_VIVO" --table "$tabla" \
       --key-columns "$claves" --value-columns "$valores" --count 1 --ttl 4h "$nombre" 2>&1 | enmascarar; then
    echo "LVC $nombre creada"
  else
    echo "LVC $nombre no creada (si el mensaje indica que ya existe, no es un error)"
  fi
}

titulo "Last Value Caches"
crear_lvc estadisticas_equipo partido_id,equipo_id minuto,posesion_pct,pases_intentados,tiros,goles ultimo_estado_equipo
crear_lvc actividad_usuarios partido_id,plataforma usuarios_activos,solicitudes,latencia_p95_ms ultima_actividad
