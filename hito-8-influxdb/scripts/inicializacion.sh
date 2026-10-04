#!/usr/bin/env bash
# RF1 — Levanta InfluxDB 3 con Docker Compose y verifica disponibilidad con el CLI del contenedor.
. "$(dirname "$0")/comun.sh"

command -v docker >/dev/null || { echo "ERROR: Docker no está instalado"; exit 1; }

titulo "Persistencia local"
mkdir -p "$HOME/docker/data/influxdb"
echo "Montaje: $HOME/docker/data/influxdb -> /var/lib/influxdb3"

titulo "docker compose up -d"
docker compose up -d
docker compose ps

titulo "Esperando al servidor HTTP (${URL})"
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "${URL}/health" || true)
  # 200 = OK; 401 = servidor arriba pero requiere token (esperado antes de autorizar)
  if [ "$code" = "200" ] || [ "$code" = "401" ]; then
    echo "Servidor disponible (GET /health -> HTTP $code) tras ${i} intento(s)"
    break
  fi
  [ "$i" = "60" ] && { echo "ERROR: el servidor no respondió. Ver: docker compose logs influxdb"; exit 1; }
  sleep 1
done

titulo "Versión observada (CLI dentro del contenedor)"
influx --version
docker image inspect influxdb:3-core --format 'Imagen influxdb:3-core  id={{.Id}}  creada={{.Created}}' 2>/dev/null || true
docker image inspect influxdb:3-core --format '{{range .RepoDigests}}digest={{.}}{{"\n"}}{{end}}' 2>/dev/null || true

titulo "Proceso del servidor"
docker exec "$C" ps -o pid,args 2>/dev/null | grep -i "influxdb3 serve" | grep -v grep || \
  docker inspect "$C" --format 'Comando: {{.Path}} {{join .Args " "}}'

echo
echo "Siguiente paso: bash scripts/autorizacion.sh"
