#!/usr/bin/env bash
# RF13 — Medición de carga y consulta sobre un volumen acorde al hardware.
#
# Uso: bash scripts/prueba_rendimiento.sh [perfil] [lote] [hilos] [repeticiones]
#      perfil: demo (~0,33 M) | lab (~2 M, por defecto) | torneo (~17 M)
# Barrido opcional de configuraciones (recarga la misma corrida: escrituras idempotentes):
#      BARRIDO="1000x1 5000x4 10000x8" bash scripts/prueba_rendimiento.sh lab
. "$(dirname "$0")/comun.sh"
requiere_token

PERFIL="${1:-lab}"; LOTE="${2:-5000}"; HILOS="${3:-4}"; REPS="${4:-5}"
SELLO="$(date +%Y%m%d_%H%M%S)"
OUT="docs/evidencia/rendimiento_hito8_${SELLO}.txt"
mkdir -p docs/evidencia

{
  titulo "PRUEBA DE RENDIMIENTO HITO 8 — perfil=$PERFIL lote=$LOTE hilos=$HILOS"
  bash scripts/ambiente.sh

  titulo "1. Generación (fuera del tiempo de carga)"
  "$PY" scripts/generacion_puntos.py --perfil "$PERFIL"

  titulo "2. Carga por lotes"
  "$PY" scripts/carga_lotes.py --lote "$LOTE" --hilos "$HILOS" --etiqueta "rendimiento_${PERFIL}"

  if [ -n "${BARRIDO:-}" ]; then
    for conf in $BARRIDO; do
      titulo "2b. Barrido: recarga con lote=${conf%x*} hilos=${conf#*x}"
      "$PY" scripts/carga_lotes.py --lote "${conf%x*}" --hilos "${conf#*x}" --sin-tardios \
        --etiqueta "barrido_${PERFIL}_${conf}"
    done
  fi

  titulo "3. Recursos después de la carga"
  docker stats --no-stream "$C" || true
  echo "Disco usado por InfluxDB: $(du -sh "$HOME/docker/data/influxdb" 2>/dev/null | cut -f1)"

  titulo "4. Validación de lo cargado"
  "$PY" scripts/validacion.py || echo "(la validación informó diferencias)"

  titulo "5. Latencia de consultas (${REPS} repeticiones cada una)"
  "$PY" scripts/consultar.py sql/consultas sql/agregaciones --repeticiones "$REPS" --max-filas 5 \
    --guardar "docs/evidencia/tiempos_consultas_${SELLO}.json" || true
} 2>&1 | enmascarar | tee "$OUT"

echo
echo "Resultado guardado en $OUT"
echo "Métricas de carga en docs/evidencia/carga_*.json y tiempos en docs/evidencia/tiempos_consultas_${SELLO}.json"
