#!/usr/bin/env bash
# Ejecuta todas las pruebas con la API corriendo (scripts/iniciar_api.sh) y guarda la salida en docs/evidencia/.
#   1. Conectividad de cada base.            4. Contraste: respuesta de la API vs. cliente nativo.
#   2. Contrato: OpenAPI == código.          5. Dependencia caída (Neo4j se detiene y se vuelve a levantar).
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
  echo "Entorno: API en la notebook ($(uname -sm)), bases en Docker $(docker version --format '{{.Server.Version}}'), TIMEOUT_S=$TIMEOUT_S"

  titulo "1. Conectividad"
  bash scripts/verificar_conectividad.sh

  titulo "2. Contrato OpenAPI vs. código"
  .venv/bin/python scripts/exportar_openapi.py --verificar

  titulo "3. Colección Bruno"
  bash scripts/preparar_datos_demo.sh
  (cd bruno && npx -y @usebruno/cli@latest run --env local 2>&1 | grep -v "^npm notice")

  titulo "4. Contraste con el cliente nativo de cada base"
  echo "--- MongoDB: GET /equipos/E010"; api /equipos/E010
  docker exec fixture2030-mongodb mongosh --quiet --eval 'printjson(db.getSiblingDB("fixture2030").equipos.findOne({_id:"E010"},{_id:1,nombre:1,confederacion:1,grupo:1}))'
  echo "--- Neo4j: GET /partidos/P001/eventos"; api /partidos/P001/eventos
  docker exec fixture2030-neo4j cypher-shell -u "$NEO4J_USUARIO" -p "$NEO4J_PASSWORD" \
    "MATCH (e:Evento)-[:OCURRE_EN]->(:Partido {id:'P001'}) OPTIONAL MATCH (j:Jugador)-[:PROTAGONIZA]->(e) RETURN e.tipo, e.minuto, j.id ORDER BY e.minuto"
  echo "--- Cassandra: GET /partidos/P001/comentarios (limit=2)"; api "/partidos/P001/comentarios?bucket=2030-06-08T20:00:00Z&limit=2"
  docker exec fixture2030-cassandra cqlsh -e "PAGING OFF; SELECT comentario_id, creado_en FROM fixture2030_comments.comentarios_por_partido WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:00:00+0000' AND shard IN (0,1,2,3,4,5,6,7) ORDER BY creado_en DESC LIMIT 2"
  echo "--- Redis: sesión creada por la API, leída con redis-cli"
  S=$(curl -s -X POST -H "Content-Type: application/json" -d '{"usuarioId":"U000042"}' "$B/sesiones" | .venv/bin/python -c "import sys,json;print(json.load(sys.stdin)['sesionId'])")
  api "/sesiones/$S"
  docker exec fixture2030-redis redis-cli HGET "fixture2030:session:$S" user_id
  docker exec fixture2030-redis redis-cli TTL "fixture2030:session:$S"
  curl -s -o /dev/null -X DELETE "$B/sesiones/$S"
  echo "--- InfluxDB: GET /partidos/P001/estadisticas (3 s)"; api "/partidos/P001/estadisticas?desde=2026-10-04T14:00:00Z&hasta=2026-10-04T14:00:03Z"
  curl -s -G -H "Authorization: Bearer $INFLUX_TOKEN" "$INFLUX_URL/api/v3/query_sql" --data-urlencode "db=$INFLUX_DATABASE" --data-urlencode "format=pretty" \
    --data-urlencode "q=SELECT time, equipo_id, posesion_pct FROM estadisticas_equipo WHERE partido_id='P001' AND time >= '2026-10-04T14:00:00Z' AND time < '2026-10-04T14:00:03Z' ORDER BY time, equipo_id"
  echo; echo "--- IRIS: GET /partidos/P003/detalle"; api /partidos/P003/detalle
  docker exec fixture2030-iris sh -c 'echo "do ##class(%SQL.Statement).%ExecDirect(,\"SELECT Codigo, Estado FROM Fixture.Partido WHERE Codigo = '"'"'P003'"'"'\").%Display()
halt" | iris session IRIS' | grep -v "^USER>\|^Node\|^$"

  titulo "5. Dependencia caída (Neo4j detenido; sus datos están en un volumen)"
  docker stop fixture2030-neo4j >/dev/null
  curl -s -w "\n-> HTTP %{http_code} en %{time_total}s\n" "$B/partidos/P001/eventos"
  echo "Otra fuente durante la caída: $(curl -s -o /dev/null -w 'GET /equipos/E010 -> HTTP %{http_code}' "$B/equipos/E010")"
  docker start fixture2030-neo4j >/dev/null
  for i in $(seq 1 40); do sleep 2; c=$(curl -s -o /dev/null -w "%{http_code}" "$B/partidos/P001/eventos"); [ "$c" = 200 ] && break; done
  echo "Neo4j levantado de nuevo -> HTTP $c, sin reiniciar la API"

  titulo "6. Latencia básica (20 requests secuenciales por endpoint, cliente curl en la misma notebook)"
  for ruta in "/equipos/E010" "/jugadores?equipoCodigo=E010&posicion=Delantero" "/partidos/P001/eventos" \
              "/partidos/P001/comentarios?bucket=2030-06-08T20:00:00Z&limit=20" \
              "/partidos/P001/estadisticas?desde=2026-10-04T14:00:00Z&hasta=2026-10-04T14:10:00Z&agregacion=minuto" \
              "/partidos/P003/detalle"; do
    for i in $(seq 1 20); do curl -s -o /dev/null -w "%{time_total}\n" "$B$ruta"; done | sort -n | awk -v r="$ruta" \
      '{v[NR]=$1*1000} END {printf "%-95s mediana=%5.1f ms  p95=%5.1f ms  max=%5.1f ms\n", r, v[int(NR/2)+1], v[int(NR*0.95)], v[NR]}'
  done
} 2>&1 | tee "$OUT"
echo; echo "Salida guardada en $OUT"
