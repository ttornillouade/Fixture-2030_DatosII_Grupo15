#!/usr/bin/env bash
# Verifica cada base con su cliente nativo, usando la configuración de .env (no imprime secretos).
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
chequear() { # nombre comando...
  if salida=$("${@:2}" 2>&1); then echo "OK     $1: $(echo "$salida" | tail -1 | cut -c1-80)"; else echo "FALLA  $1: $(echo "$salida" | tail -1 | cut -c1-120)"; fi
}
chequear "MongoDB   (fixture2030-mongodb, $MONGODB_DATABASE)" docker exec fixture2030-mongodb mongosh --quiet --eval \
  "const d = db.getSiblingDB('$MONGODB_DATABASE'); ['equipos','jugadores','partidos','estadisticas'].map(c => c + '=' + d[c].estimatedDocumentCount()).join(' ')"
chequear "Redis     (fixture2030-redis)" docker exec fixture2030-redis redis-cli PING
chequear "Cassandra (fixture2030-cassandra, $CASSANDRA_KEYSPACE)" docker exec fixture2030-cassandra cqlsh -e "SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name='$CASSANDRA_KEYSPACE'"
chequear "Neo4j     (fixture2030-neo4j)" docker exec fixture2030-neo4j cypher-shell -u "$NEO4J_USUARIO" -p "$NEO4J_PASSWORD" "MATCH (j:Jugador) RETURN count(j) AS jugadores"
