#!/usr/bin/env bash
# Limpieza OPCIONAL. Nada se borra sin confirmación.
#   --datos        borra los objetos de la demo (las clases quedan compiladas)
#   --reset-total  docker compose down + indica cómo borrar ~/docker/data/iris
. "$(dirname "$0")/comun.sh"

confirmar() { read -r -p "$1 Escribí SI para confirmar: " r; [ "$r" = "SI" ]; }

case "${1:-}" in
  --datos)
    requiere_contenedor
    confirmar "Se borrarán sedes, equipos, personas, partidos y eventos." || exit 0
    iris_ejecutar '##class(Fixture.Demo).Limpiar()' && echo "Listo." ;;
  --reset-total)
    confirmar "Se detendrá el contenedor." || exit 0
    docker compose down
    echo "Para empezar de cero (borra bases, configuración y usuarios de IRIS):"
    echo "  rm -rf \"$DATA_DIR\""
    echo "y luego: bash scripts/inicializacion.sh" ;;
  *)
    echo "Uso: bash scripts/limpieza.sh --datos | --reset-total" ;;
esac
