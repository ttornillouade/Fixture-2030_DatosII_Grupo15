#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${CASSANDRA_CONTAINER_NAME:-fixture2030-cassandra}"
until docker exec "$C" cqlsh -e "SELECT release_version FROM system.local;" >/dev/null 2>&1; do sleep 3; done
docker exec -i "$C" cqlsh < scripts/esquema.cql
docker exec -i "$C" cqlsh < scripts/carga_muestra.cql
echo "Esquema y muestra cargados."
