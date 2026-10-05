#!/usr/bin/env bash
# RF1 — Levanta IRIS con persistencia durable en ~/docker/data/iris, espera a que acepte
# sesiones, aplica la contraseña local y compila las clases (scripts/cargar_clases.sh).
. "$(dirname "$0")/comun.sh"
requiere_env

titulo "Persistencia local (Durable %SYS)"
mkdir -p "$DATA_DIR"
echo "Montaje: ~/docker/data/iris -> /durable  (ISC_DATA_DIRECTORY=/durable/iris)"

titulo "docker compose up -d"
docker compose up -d
docker compose ps

titulo "Esperando a que IRIS acepte sesiones"
listo=0
for i in $(seq 1 60); do
  if echo 'halt' | docker exec -i "$C" iris session IRIS -U "$NS" >/dev/null 2>&1; then listo=1; break; fi
  sleep 3
done
if [ "$listo" != 1 ]; then echo "ERROR: IRIS no respondió. Ver: docker logs $C" >&2; exit 1; fi
echo "IRIS listo tras $i intento(s)"

bash scripts/cargar_clases.sh

titulo "Versión observada"
iris_terminal <<'EOF'
write $ZVERSION,!
write "Namespace: ",$NAMESPACE,"  Instancia: ",##class(%SYS.System).GetInstanceName(),!
halt
EOF
docker image inspect intersystems/iris-community:latest-cd \
  --format 'Imagen: intersystems/iris-community:latest-cd  {{index .RepoDigests 0}}' 2>/dev/null || true
