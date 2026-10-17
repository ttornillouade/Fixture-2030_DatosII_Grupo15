#!/usr/bin/env bash
# Carga los datos que falten en cada base (es idempotente: lo que ya está no se vuelve a cargar).
#   MongoDB:   equipos y jugadores (Hito 4) + partidos, eventos y estadísticas (scripts/cargar_datos.sh)
#   Neo4j:     grafo del Hito 5 (estructura.cypher + carga.cypher)
#   Cassandra: esquema del Hito 6 + carga de muestra (64 comentarios) si la tabla está vacía
#   Redis:     no necesita datos iniciales
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

echo "== MongoDB"
if [ "$(docker exec fixture2030-mongodb mongosh --quiet --eval 'db.getSiblingDB("fixture2030").equipos.estimatedDocumentCount()')" = 0 ]; then
  docker exec fixture2030-mongodb mongosh --quiet /scripts/01_validacion.js
  docker exec fixture2030-mongodb mongosh --quiet /scripts/02_carga.js
  docker exec fixture2030-mongodb mongosh --quiet /scripts/05_indices_rendimiento.js > /dev/null
else
  echo "equipos y jugadores ya cargados"
fi
bash scripts/cargar_datos.sh

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

bash scripts/preparar_datos_demo.sh
