#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${CASSANDRA_CONTAINER_NAME:-fixture2030-cassandra}"
docker exec -i "$C" cqlsh < scripts/crud.cql
