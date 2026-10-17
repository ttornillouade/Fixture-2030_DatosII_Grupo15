#!/usr/bin/env bash
# Levanta las cuatro bases (Docker Compose), espera a que estén sanas y carga los datos que falten.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Falta .env: cp .env.example .env y definir NEO4J_PASSWORD" >&2; exit 1; }
mkdir -p ~/docker/data/{mongodb,redis,cassandra,neo4j}
docker compose up -d --wait
bash scripts/inicializar_datos.sh
bash scripts/verificar_conectividad.sh
echo; echo "Bases listas. Iniciar la API con: bash scripts/iniciar_api.sh  (http://localhost:8000/docs)"
