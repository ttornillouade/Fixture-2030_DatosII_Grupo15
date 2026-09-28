#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${CASSANDRA_CONTAINER_NAME:-fixture2030-cassandra}"; mkdir -p docs/evidencia; OUT="docs/evidencia/evidencia_hito6_$(date +%Y%m%d_%H%M%S).txt"
{
 echo "EVIDENCIA HITO 6"; echo "Fecha: $(date)"; docker compose ps
 docker exec "$C" cqlsh -e "SHOW VERSION"; docker exec "$C" nodetool status
 docker exec "$C" cqlsh -e "DESCRIBE KEYSPACE fixture2030_comments"
 echo "=== RE-CARGA IDEMPOTENTE ==="; docker exec -i "$C" cqlsh < scripts/carga_muestra.cql; docker exec -i "$C" cqlsh < scripts/carga_muestra.cql
 echo "=== CONSULTAS ==="; docker exec -i "$C" cqlsh < scripts/consultas.cql
 echo "=== CRUD ==="; docker exec -i "$C" cqlsh < scripts/crud.cql
} | tee "$OUT"
echo "Evidencia: $OUT"
