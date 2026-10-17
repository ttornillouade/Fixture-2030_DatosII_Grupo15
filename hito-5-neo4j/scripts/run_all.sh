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

run_file () {
  local file="$1"
  echo
  echo ">>> Ejecutando $file"
  docker exec -i "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD" < "$file"
}

run_file queries/crud.cypher
run_file queries/consultas_grafo.cypher
run_file queries/analisis_relacional.cypher
run_file queries/integridad.cypher
