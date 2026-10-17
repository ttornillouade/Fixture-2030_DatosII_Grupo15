#!/usr/bin/env bash
# Prepara datos de prueba para la API. Se ejecuta a mano, nunca al arrancar la API.
#   - MongoDB: deja el partido de prueba P128 (E063 vs E064) en PROGRAMADO, para probar las
#     transiciones de estado. Los 127 partidos del Hito 5 están FINALIZADOS.
#   - Redis: crea la sesión de prueba s-demo-001 con el TTL del Hito 7 (30 minutos).
# Requiere haber ejecutado scripts/cargar_datos.sh.
set -euo pipefail
docker exec fixture2030-mongodb mongosh --quiet --eval '
const db2 = db.getSiblingDB("fixture2030");
const base = db2.partidos.findOne({ _id: "P127" });
if (!base) { print("ERROR falta cargar los partidos: scripts/cargar_datos.sh"); quit(1); }
db2.partidos.replaceOne({ _id: "P128" }, {
  fechaHora: new Date("2030-07-25T16:00:00Z"), fase: "Prueba", sede: base.sede,
  equipoLocalId: "E063", equipoVisitanteId: "E064", estado: "PROGRAMADO", eventos: [], updatedAt: new Date()
}, { upsert: true });
print("OK P128 en PROGRAMADO, sin eventos");'
docker exec fixture2030-redis redis-cli HSET fixture2030:session:s-demo-001 session_id s-demo-001 user_id U000042 \
  created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" access_status AUTHENTICATED locale es-AR > /dev/null
docker exec fixture2030-redis redis-cli EXPIRE fixture2030:session:s-demo-001 1800 > /dev/null
echo "OK sesión s-demo-001 vigente por 30 minutos"
