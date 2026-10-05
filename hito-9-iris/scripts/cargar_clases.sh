#!/usr/bin/env bash
# RNF2 — Copia src/ al contenedor (docker cp) y carga y compila todas las clases.
# También aplica la contraseña local de .env. Se puede repetir después de editar un .cls.
. "$(dirname "$0")/comun.sh"
requiere_contenedor

titulo "Copia de src/ al contenedor"
# docker cp deja los archivos como root: se limpian como root y se entregan a irisowner.
docker exec -u root "$C" sh -c 'rm -rf /tmp/fixture && mkdir -p /tmp/fixture'
docker cp src "$C":/tmp/fixture/src
docker cp scripts/iris "$C":/tmp/fixture/iris
docker exec -u root "$C" chown -R irisowner:irisowner /tmp/fixture
docker exec "$C" sh -c 'find /tmp/fixture/src -name "*.cls" | sort'

titulo "Contraseña local de IRIS"
docker exec "$C" sh /tmp/fixture/iris/configurar_usuarios.sh | grep -v '^\s*$' | enmascarar

titulo "Carga y compilación (namespace $NS)"
docker exec -e IRIS_NAMESPACE="$NS" "$C" sh /tmp/fixture/iris/cargar_clases.sh
