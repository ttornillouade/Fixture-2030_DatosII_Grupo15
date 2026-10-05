#!/usr/bin/env bash
# Abre la terminal interactiva de IRIS en el namespace del proyecto (salir con: halt).
. "$(dirname "$0")/comun.sh"
requiere_contenedor
docker exec -it "$C" iris session IRIS -U "$NS"
