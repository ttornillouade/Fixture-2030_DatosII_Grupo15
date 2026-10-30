#!/usr/bin/env bash
# Prepara datos de prueba para la API. Se ejecuta a mano, nunca al arrancar la API.
#   - IRIS: deja el partido de prueba P128 en PROGRAMADO y sin eventos, para probar las transiciones
#     de estado. Los 127 partidos del Hito 5 están FINALIZADOS.
#   - Redis: crea la sesión de prueba s-demo-001 con el TTL del Hito 7 (30 minutos).
# Requiere haber ejecutado scripts/inicializar_datos.sh.
set -euo pipefail
docker exec -i fixture2030-iris iris session IRIS <<'IRIS' | grep -E "^(OK|ERROR)"
do ##class(%SQL.Statement).%ExecDirect(, "DELETE FROM Fixture.Partido WHERE Codigo = 'P128'")
set p = ##class(Fixture.Partido).%New(), p.Codigo = "P128", sc = p.%Save()
write $select(sc: "OK P128 en PROGRAMADO, sin eventos", 1: "ERROR "_$system.Status.GetErrorText(sc)), !
halt
IRIS
docker exec fixture2030-redis redis-cli HSET fixture2030:session:s-demo-001 session_id s-demo-001 user_id U000042 \
  created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" access_status AUTHENTICATED locale es-AR > /dev/null
docker exec fixture2030-redis redis-cli EXPIRE fixture2030:session:s-demo-001 1800 > /dev/null
echo "OK sesión s-demo-001 vigente por 30 minutos"
