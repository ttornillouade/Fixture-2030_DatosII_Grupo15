#!/usr/bin/env bash
# RF14 — Corrida completa y verificable: ambiente, autorización, bases, carga, validación,
# consultas, agregaciones, retención/downsampling, errores y ventana en vivo.
# Uso: bash scripts/generar_evidencia.sh [perfil]   (por defecto: demo)
. "$(dirname "$0")/comun.sh"

PERFIL="${1:-demo}"
OUT="docs/evidencia/evidencia_hito8_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p docs/evidencia

{
  echo "EVIDENCIA HITO 8 — FIXTURE 2030 — SERIES TEMPORALES (InfluxDB)"
  titulo "0. Ambiente"
  bash scripts/ambiente.sh
  docker compose ps

  titulo "1. Disponibilidad (RF1)"
  bash scripts/inicializacion.sh

  titulo "2. Autorización local (token enmascarado)"
  bash scripts/autorizacion.sh
  [ -f .env ] && { set -a; . ./.env; set +a; }

  titulo "3. Bases y retención (RF10)"
  bash scripts/crear_bases.sh

  titulo "4. Generación reproducible (RF7)"
  "$PY" scripts/generacion_puntos.py --perfil "$PERFIL"

  titulo "5. Carga por lotes (RF7, RF12)"
  "$PY" scripts/carga_lotes.py --etiqueta "evidencia_${PERFIL}"

  titulo "6. Manejo de errores de carga (RF12)"
  "$PY" scripts/carga_lotes.py --demo-errores

  titulo "7. Validación de cantidades, series, distribución y tipos (RF11, RNF6)"
  "$PY" scripts/validacion.py || echo "(la validación informó diferencias)"

  titulo "8. Consultas temporales (RF8)"
  "$PY" scripts/consultar.py sql/consultas --max-filas 12 || true

  titulo "9. Agregaciones (RF9)"
  bash scripts/downsampling.sh
  "$PY" scripts/consultar.py sql/agregaciones --max-filas 12 || true

  titulo "10. Ventana en vivo + Last Value Cache + corte de fuente (PA1)"
  bash scripts/caches_ultimo_valor.sh
  "$PY" scripts/simulador_vivo.py --segundos 45 --corte 20:15
  "$PY" scripts/consultar.py sql/consultas/c06_ventana_reciente.sql sql/consultas/c07_ultimo_valor_cache.sql || true
} 2>&1 | enmascarar | tee "$OUT"

echo
echo "Evidencia guardada en $OUT"
echo "Para RF13 ejecutar además: bash scripts/prueba_rendimiento.sh lab"
