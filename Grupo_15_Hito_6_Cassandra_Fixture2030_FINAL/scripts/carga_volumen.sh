#!/usr/bin/env bash
set -euo pipefail
[ -f .env ] && set -a && source .env && set +a
C="${CASSANDRA_CONTAINER_NAME:-fixture2030-cassandra}"; TOTAL="${1:-1100000}"
[ -f data/comentarios_por_partido.csv ] || python3 scripts/generar_volumen.py "$TOTAL"
ROWS=$(( $(wc -l < data/comentarios_por_partido.csv)-1 ))
mkdir -p docs/evidencia
OUT="docs/evidencia/carga_volumen_$(date +%Y%m%d_%H%M%S).txt"
{
 echo "PRUEBA DE CARGA - HITO 6"; echo "Fecha: $(date)"; echo "Filas tabla principal: $ROWS"
 docker stats "$C" --no-stream || true
 docker exec "$C" cqlsh -e "SHOW VERSION"
 START=$(date +%s)
 docker exec "$C" cqlsh -e "COPY fixture2030_comments.comentarios_por_partido (partido_id,bucket_5m,shard,creado_en,comentario_id,autor_id,contenido,estado_moderacion,reacciones) FROM '/import/comentarios_por_partido.csv' WITH HEADER=TRUE AND NUMPROCESSES=4 AND CHUNKSIZE=5000;"
 END=$(date +%s); ELAPSED=$((END-START)); [ "$ELAPSED" -eq 0 ] && ELAPSED=1; RATE=$((ROWS/ELAPSED))
 echo "Tiempo tabla principal (s): $ELAPSED"; echo "Tasa aproximada observada (filas/s): $RATE"
 echo "Luego cargar la tabla secundaria si se desea medir el costo total de duplicación."
} | tee "$OUT"
echo "Resultado guardado en $OUT"
