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

mkdir -p docs/evidencia
OUT="docs/evidencia/salida_hito5.txt"

{
  echo "EVIDENCIA HITO 5 - FIXTURE 2030"
  echo "Fecha de prueba: $(date)"
  echo

  echo "=== DOCKER ==="
  docker compose ps
  echo

  echo "=== CARGA 1 ==="
  bash scripts/load.sh
  echo

  echo "=== CARGA 2 - PRUEBA DE IDEMPOTENCIA ==="
  bash scripts/load.sh
  echo

  echo "=== CRUD, CONSULTAS Y ANALISIS ==="
  bash scripts/run_all.sh
  echo

  echo "=== RESTRICCIONES ==="
  docker exec "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD"     "SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;"
  echo

  echo "=== INDICES ==="
  docker exec "$CONTAINER" cypher-shell -u "$USER_NAME" -p "$PASSWORD"     "SHOW INDEXES YIELD name, type, labelsOrTypes, properties RETURN name, type, labelsOrTypes, properties;"
} | tee "$OUT"

echo
echo "Evidencia textual creada en $OUT"
echo "Completar además las capturas indicadas en docs/evidencia/README.md"
