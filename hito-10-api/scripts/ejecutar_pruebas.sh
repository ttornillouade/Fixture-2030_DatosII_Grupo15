#!/usr/bin/env bash
# Ejecuta todas las pruebas con la API corriendo (scripts/iniciar_api.sh) y guarda la salida en docs/evidencia/.
#   1. Conectividad de las seis bases.       4. Contraste: respuesta de la API vs. cliente nativo.
#   2. Contrato: OpenAPI == código.          5. Dependencias caídas: Neo4j, Redis, IRIS e InfluxDB (503 y recuperación).
#   3. Colección Bruno (válidos, inválidos,  6. Latencia básica por endpoint.
#      inexistentes, vacíos, repetidos).
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
export PATH="/opt/homebrew/bin:$PATH"
B=http://localhost:8000
OUT="docs/evidencia/pruebas_$(date +%Y%m%d_%H%M%S).txt"
titulo() { printf '\n========== %s ==========\n' "$1"; }
api() { curl -s "$B$1"; echo; }

{
  echo "PRUEBAS API REST INTEGRADA — FIXTURE 2030 — $(date '+%Y-%m-%d %H:%M:%S %Z')"
  donde=$(docker ps --filter name=fixture2030-api --filter status=running -q | grep -q . && echo "contenedor fixture2030-api" || echo "notebook")
  echo "Entorno: API en $donde ($(uname -sm)), bases en Docker $(docker version --format '{{.Server.Version}}'), TIMEOUT_S=$TIMEOUT_S"

  titulo "1. Conectividad"
  bash scripts/verificar_conectividad.sh

  titulo "2. Contrato OpenAPI vs. código"
  .venv/bin/python scripts/exportar_openapi.py --verificar

  titulo "3. Colección Bruno"
  bash scripts/preparar_datos_demo.sh
  (cd bruno && npx -y @usebruno/cli@latest run --env local 2>&1 | grep -v "^npm notice")

  titulo "4. Contraste con el cliente nativo de cada base"
  mongo() { docker exec fixture2030-mongodb mongosh --quiet --eval "$1"; }
  echo "--- MongoDB: GET /equipos/E010"; api /equipos/E010
  mongo 'printjson(db.getSiblingDB("fixture2030").equipos.findOne({_id:"E010"},{nombre:1,confederacion:1,grupo:1}))'
  echo "--- IRIS: GET /partidos/P001/detalle"; api /partidos/P001/detalle
  docker exec -i fixture2030-iris iris session IRIS <<'IRIS' | grep -vE "^(USER>|$)"
do ##class(%SQL.Statement).%ExecDirect(, "SELECT p.Codigo, p.Estado, e.Minuto, e.Tipo, e.Jugador->Nombre, e.Jugador->Apellido, e.Jugador->Dorsal FROM Fixture.Evento e JOIN Fixture.Partido p ON e.Partido = p.ID WHERE p.Codigo = 'P001' ORDER BY e.Minuto").%Display()
halt
IRIS
  echo "--- InfluxDB: GET /partidos/P001/estadisticas (2 s)"; api "/partidos/P001/estadisticas?desde=2030-06-08T16:00:00Z&hasta=2030-06-08T16:00:02Z"
  INFLUXDB3_AUTH_TOKEN="$INFLUX_TOKEN" docker exec -e INFLUXDB3_AUTH_TOKEN fixture2030-influxdb influxdb3 query -d "$INFLUX_DATABASE" \
    "SELECT time, equipo_id, posesion_pct, pases_completados, tiros FROM estadisticas_equipo WHERE partido_id = 'P001' AND time >= '2030-06-08T16:00:00Z' AND time < '2030-06-08T16:00:02Z' ORDER BY time, equipo_id"
  echo "--- Neo4j: GET /jugadores/E001-J09/partidos"; api /jugadores/E001-J09/partidos
  docker exec fixture2030-neo4j cypher-shell -u "$NEO4J_USUARIO" -p "$NEO4J_PASSWORD" \
    "MATCH (j:Jugador {id:'E001-J09'})-[:PARTICIPA_EN]->(p:Partido)<-[:DISPUTA]-(rival:Equipo) WHERE NOT (j)-[:PERTENECE_A]->(rival) RETURN p.id, p.fecha, rival.id ORDER BY p.fecha, p.id"
  echo "--- Cassandra: GET /partidos/P001/comentarios (limit=2)"; api "/partidos/P001/comentarios?bucket=2030-06-08T20:00:00Z&limit=2"
  docker exec fixture2030-cassandra cqlsh -e "PAGING OFF; SELECT comentario_id, creado_en FROM fixture2030_comments.comentarios_por_partido WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:00:00+0000' AND shard IN (0,1,2,3,4,5,6,7) ORDER BY creado_en DESC LIMIT 2"
  echo "--- Redis: GET /sesiones/s-demo-001 (la colección Bruno la invalidó: se vuelve a crear)"
  bash scripts/preparar_datos_demo.sh > /dev/null
  api /sesiones/s-demo-001
  docker exec fixture2030-redis redis-cli HGET fixture2030:session:s-demo-001 user_id
  docker exec fixture2030-redis redis-cli TTL fixture2030:session:s-demo-001

  titulo "5. Dependencias caídas (se detienen y se vuelven a levantar; sus datos persisten en disco)"
  esperar_200() { for i in $(seq 1 40); do sleep 2; c=$(curl -s -o /dev/null -w "%{http_code}" "$B$1"); [ "$c" = 200 ] && break; done; echo "$c"; }
  echo "--- Neo4j detenido"
  docker stop fixture2030-neo4j >/dev/null
  curl -s -w "\n-> HTTP %{http_code} en %{time_total}s\n" "$B/jugadores/E001-J09/partidos"
  echo "Otra fuente durante la caída: $(curl -s -o /dev/null -w 'GET /partidos/P001/detalle -> HTTP %{http_code}' "$B/partidos/P001/detalle")"
  docker start fixture2030-neo4j >/dev/null
  echo "Neo4j levantado de nuevo -> HTTP $(esperar_200 /jugadores/E001-J09/partidos), sin reiniciar la API"
  echo "--- Redis detenido"
  docker stop fixture2030-redis >/dev/null
  curl -s -w "\n-> HTTP %{http_code} en %{time_total}s\n" "$B/sesiones/s-demo-001"
  echo "Otra fuente durante la caída: $(curl -s -o /dev/null -w 'GET /equipos/E011 -> HTTP %{http_code}' "$B/equipos/E011")"
  docker start fixture2030-redis >/dev/null
  sleep 2; echo "Redis levantado de nuevo -> GET /sesiones/s-demo-001 HTTP $(esperar_200 /sesiones/s-demo-001), sin reiniciar la API"
  echo "--- IRIS detenido"
  docker stop fixture2030-iris >/dev/null
  curl -s -w "\n-> HTTP %{http_code} en %{time_total}s\n" "$B/partidos/P001/detalle"
  echo "Otra fuente durante la caída: $(curl -s -o /dev/null -w 'GET /equipos/E011 -> HTTP %{http_code}' "$B/equipos/E011")"
  docker start fixture2030-iris >/dev/null
  echo "IRIS levantado de nuevo -> HTTP $(esperar_200 /partidos/P001/detalle), sin reiniciar la API"
  echo "--- InfluxDB detenido"
  E="/partidos/P001/estadisticas?desde=2030-06-08T16:00:00Z&hasta=2030-06-08T16:00:02Z"
  docker stop fixture2030-influxdb >/dev/null
  curl -s -w "\n-> HTTP %{http_code} en %{time_total}s\n" "$B$E"
  echo "Otra fuente durante la caída: $(curl -s -o /dev/null -w 'GET /partidos/P001/detalle -> HTTP %{http_code}' "$B/partidos/P001/detalle")"
  docker start fixture2030-influxdb >/dev/null
  echo "InfluxDB levantado de nuevo -> HTTP $(esperar_200 "$E"), sin reiniciar la API"

  titulo "6. Latencia básica (20 requests secuenciales por endpoint, cliente curl en la misma notebook)"
  for ruta in "/equipos/E010" "/jugadores?equipoCodigo=E010&posicion=Delantero" "/partidos/P001/detalle" \
              "/partidos/P001/estadisticas?desde=2030-06-08T16:00:00Z&hasta=2030-06-08T17:00:00Z&agregacion=minuto" \
              "/jugadores/E001-J09/partidos" "/partidos/P001/comentarios?bucket=2030-06-08T20:00:00Z&limit=20"; do
    for i in $(seq 1 20); do curl -s -o /dev/null -w "%{time_total}\n" "$B$ruta"; done | sort -n | awk -v r="$ruta" \
      '{v[NR]=$1*1000} END {printf "%-92s mediana=%5.1f ms  p95=%5.1f ms  max=%5.1f ms\n", r, v[int(NR/2)+1], v[int(NR*0.95)], v[NR]}'
  done
} 2>&1 | tee "$OUT"
echo; echo "Salida guardada en $OUT"
