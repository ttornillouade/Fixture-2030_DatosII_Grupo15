#!/usr/bin/env bash
# Carga en MongoDB (contenedor del Hito 4) los partidos con sus eventos y las estadísticas
# temporales. Es repetible. Requiere haber cargado antes equipos y jugadores (hito-4-mongodb).
set -euo pipefail
cd "$(dirname "$0")/.."
C=fixture2030-mongodb
docker exec -u root "$C" sh -c 'rm -rf /tmp/fixture10 && mkdir -p /tmp/fixture10'
docker cp datos/. "$C":/tmp/fixture10/
docker cp scripts/mongo/. "$C":/tmp/fixture10/
echo "== Partidos y eventos (Hito 9)"
docker exec "$C" mongosh --quiet /tmp/fixture10/partidos.js
echo "== Estadísticas temporales (Hito 8)"
docker exec "$C" mongosh --quiet /tmp/fixture10/estadisticas.js
