#!/usr/bin/env bash
# Limpieza OPCIONAL. Nada se borra sin confirmación.
#   --datos-generados   borra data/generated/ (se reconstruye con generacion_puntos.py)
#   --bases             borra las bases fixture2030_vivo y fixture2030_historico (API DELETE)
#   --reset-total       docker compose down + indica cómo borrar ~/docker/data/influxdb
. "$(dirname "$0")/comun.sh"

confirmar() { read -r -p "$1 Escribí SI para confirmar: " r; [ "$r" = "SI" ]; }

case "${1:-}" in
  --datos-generados)
    confirmar "Se borrará data/generated/." && rm -rf data/generated && echo "Listo." ;;
  --bases)
    requiere_token
    confirmar "Se borrarán $DB_VIVO y $DB_HIST (todos sus puntos)." || exit 0
    for db in "$DB_VIVO" "$DB_HIST"; do
      code=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
        -H "Authorization: Bearer ${INFLUX_TOKEN}" "${URL}/api/v3/configure/database?db=${db}")
      echo "DELETE $db -> HTTP $code"
    done ;;
  --reset-total)
    confirmar "Se detendrá el contenedor." || exit 0
    docker compose down
    echo "Para empezar de cero (borra datos, catálogo y tokens):"
    echo "  rm -rf \"$HOME/docker/data/influxdb\""
    echo "y luego: bash scripts/inicializacion.sh && bash scripts/autorizacion.sh" ;;
  *)
    echo "Uso: bash scripts/limpieza.sh --datos-generados | --bases | --reset-total" ;;
esac
