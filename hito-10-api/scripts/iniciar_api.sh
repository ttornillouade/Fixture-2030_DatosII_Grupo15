#!/usr/bin/env bash
# Inicia la API en http://localhost:8000 (Swagger UI en /docs). Detener con Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Falta .env: cp .env.example .env y completar los valores locales" >&2; exit 1; }
[ -x .venv/bin/uvicorn ] || { echo "Falta el entorno: python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2; exit 1; }
# --no-access-log: el log propio de la API ya registra método, ruta, fuente, estado, duración y requestId,
# sin query strings ni cuerpos.
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT:-8000}" --no-access-log
