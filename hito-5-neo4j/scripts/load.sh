#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

CONTAINER="${NEO4J_CONTAINER_NAME:-fixture2030-neo4j}"
USER_NAME="${NEO4J_USER:-neo4j}"
PASSWORD="${NEO4J_PASSWORD:-fixture2030}"

echo "Esperando a Neo4j..."
until docker exec "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD" "RETURN 1;" >/dev/null 2>&1; do
  sleep 2
done

echo "Aplicando restricciones e índices..."
docker exec -i "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD" < queries/estructura.cypher

echo "Cargando el grafo con MERGE..."
docker exec -i "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD" < queries/carga.cypher

echo "Ejecutando controles de integridad..."
docker exec -i "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD" < queries/integridad.cypher
