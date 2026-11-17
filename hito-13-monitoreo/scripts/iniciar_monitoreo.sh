#!/usr/bin/env bash
# Levanta Prometheus, Grafana y los exporters, y verifica los targets.
# Requiere: las seis bases del Hito 10 corriendo (crean la red hito-10-api_default) y, para las métricas
# de aplicación, la API iniciada (bash ../hito-10-api/scripts/iniciar_api.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Falta .env: cp .env.example .env y definir GRAFANA_ADMIN_PASSWORD" >&2; exit 1; }
docker network inspect hito-10-api_default > /dev/null 2>&1 || {
  echo "No existe la red hito-10-api_default: levantar primero las bases (bash ../hito-10-api/scripts/levantar_todo.sh)" >&2; exit 1; }
docker compose up -d --wait
echo
echo "Prometheus: http://localhost:9090/targets"
echo "Grafana:    http://localhost:3000/d/fixture2030   (lectura anónima; admin con la contraseña de .env)"
echo
sleep 6   # dos scrapes de 5 s antes de verificar
PY=../hito-10-api/.venv/bin/python
"$PY" scripts/verificar_targets.py
