#!/usr/bin/env bash
# Carga los datos que falten en cada base (es idempotente: lo que ya está no se vuelve a cargar).
#   MongoDB:   equipos y jugadores (Hito 4)
#   Neo4j:     grafo del Hito 5 (estructura.cypher + carga.cypher)
#   Cassandra: esquema del Hito 6 + carga de muestra (64 comentarios) si la tabla está vacía
#   Redis:     no necesita datos iniciales
#   InfluxDB:  token y base del Hito 8 + estadísticas de P001-P004 (scripts/influx/estadisticas.py)
#   IRIS:      clases del Hito 9 + partidos y eventos del Hito 5 (scripts/iris/partidos.py)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
DATOS=../hito-5-neo4j/import

echo "== MongoDB"
if [ "$(docker exec fixture2030-mongodb mongosh --quiet --eval 'db.getSiblingDB("fixture2030").equipos.estimatedDocumentCount()')" = 0 ]; then
  docker exec fixture2030-mongodb mongosh --quiet /scripts/01_validacion.js
  docker exec fixture2030-mongodb mongosh --quiet /scripts/02_carga.js
  docker exec fixture2030-mongodb mongosh --quiet /scripts/05_indices_rendimiento.js > /dev/null
else
  echo "equipos y jugadores ya cargados"
fi

echo "== Neo4j"
if [ "$(docker exec fixture2030-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format plain 'MATCH (j:Jugador) RETURN count(j)' | tail -1)" = 0 ]; then
  docker exec fixture2030-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f /queries/estructura.cypher
  docker exec fixture2030-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f /queries/carga.cypher
fi
docker exec fixture2030-neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format plain "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label"

echo "== Cassandra"
docker exec fixture2030-cassandra cqlsh -f /scripts/esquema.cql
if docker exec fixture2030-cassandra cqlsh -e "SELECT comentario_id FROM $CASSANDRA_KEYSPACE.comentarios_por_partido WHERE partido_id='P001' AND bucket_5m='2030-06-08 20:00:00+0000' AND shard=0 LIMIT 1" | grep -q "(0 rows)"; then
  docker exec fixture2030-cassandra cqlsh -f /scripts/carga_muestra.cql
  echo "carga de muestra del Hito 6 aplicada"
else
  echo "comentarios ya cargados"
fi

echo "== InfluxDB"
if [ -z "${INFLUX_TOKEN:-}" ]; then
  # El token se guarda solo en .env (no versionado) y nunca se imprime.
  INFLUX_TOKEN=$(docker exec fixture2030-influxdb influxdb3 create token --admin 2>&1 | grep -oE 'apiv3_[A-Za-z0-9_-]+' | head -1 || true)
  [ -n "$INFLUX_TOKEN" ] || { echo "No se pudo crear el token: ya existe uno. Copiarlo en .env (INFLUX_TOKEN)" >&2; exit 1; }
  { grep -v '^INFLUX_TOKEN=' .env; echo "INFLUX_TOKEN=$INFLUX_TOKEN"; } > .env.tmp && mv .env.tmp .env && chmod 600 .env
  echo "token de administrador creado y guardado en .env"
fi
influx() { INFLUXDB3_AUTH_TOKEN="$INFLUX_TOKEN" docker exec -e INFLUXDB3_AUTH_TOKEN fixture2030-influxdb influxdb3 "$@"; }
influx show databases --format csv | grep -qx "$INFLUX_DATABASE" || influx create database "$INFLUX_DATABASE" --retention-period 14d
.venv/bin/python scripts/influx/estadisticas.py "$DATOS/partidos.csv"

echo "== IRIS"
docker exec -i -e IRIS_PASSWORD fixture2030-iris iris session IRIS -U %SYS <<'IRIS' | grep -E "^(OK|ERROR)"
set p("Password") = $system.Util.GetEnviron("IRIS_PASSWORD"), p("ChangePassword") = 0
set sc = ##class(Security.Users).Modify("_SYSTEM", .p)  write $select(sc: "OK contraseña de _SYSTEM aplicada", 1: "ERROR "_$system.Status.GetErrorText(sc)), !
halt
IRIS
docker exec -i fixture2030-iris iris session IRIS <<'IRIS' | grep -E "^(OK|ERROR)"
set sc = $system.OBJ.LoadDir("/scripts/Fixture", "ck-d")  write $select(sc: "OK clases del Hito 9 compiladas", 1: "ERROR "_$system.Status.GetErrorText(sc)), !
halt
IRIS
.venv/bin/python scripts/iris/partidos.py "$DATOS"

bash scripts/preparar_datos_demo.sh
