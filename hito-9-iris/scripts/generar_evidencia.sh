#!/usr/bin/env bash
# Evidencia de ejecución del Hito 9: ambiente, compilación, bloque de terminal (5.3),
# demostración completa (RF5–RF9), consultas SQL (RF8) y persistencia tras reiniciar (RF1).
# Uso: bash scripts/generar_evidencia.sh   -> docs/evidencia/evidencia_hito9_<fecha>.txt
. "$(dirname "$0")/comun.sh"
requiere_env

OUT="docs/evidencia/evidencia_hito9_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p docs/evidencia

esperar_iris() {
  for i in $(seq 1 60); do
    echo 'halt' | docker exec -i "$C" iris session IRIS -U "$NS" >/dev/null 2>&1 && return 0
    sleep 3
  done
  echo "ERROR: IRIS no respondió" >&2; return 1
}

{
  echo "EVIDENCIA HITO 9 — FIXTURE 2030 — ENTIDADES COMPLEJAS (InterSystems IRIS)"

  titulo "0. Ambiente"
  echo "Fecha local:  $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "Fecha UTC:    $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "SO:           $(uname -srm)"
  echo "Docker:       $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '?')"
  docker image inspect intersystems/iris-community:latest-cd \
    --format 'Imagen:       intersystems/iris-community:latest-cd {{index .RepoDigests 0}}' 2>/dev/null || true

  titulo "1. Servicio y persistencia (RF1, RNF1)"
  bash scripts/inicializacion.sh
  echo
  echo "Contenido de ~/docker/data/iris (Durable %SYS):"
  ls "$DATA_DIR/iris" | sed 's/^/  /'

  titulo "2. Bloque de comandos en la terminal de IRIS (5.3)"
  bash scripts/bloque_terminal.sh

  titulo "3. Demostración completa: do ##class(Fixture.Demo).Ejecutar() (RF5–RF9, RNF3)"
  bash scripts/demo.sh

  titulo "4. Consultas SQL relacionales en el shell SQL (RF8)"
  bash scripts/consultas_sql.sh | sed -e '/^Node: /d' -e '/^USER>$/d' -e '/prepare time/d' -e '/execute time/d' -e '/query class/d'

  titulo "5. Persistencia: docker compose down + up (RF1)"
  echo "Antes del reinicio:"
  iris_ejecutar '##class(Fixture.Demo).MostrarConteos()'
  docker compose down
  docker compose up -d
  esperar_iris
  echo "Después del reinicio (contenedor nuevo, mismos datos y clases compiladas):"
  iris_ejecutar '##class(Fixture.Demo).MostrarConteos()'
  iris_ejecutar '##class(Fixture.Demo).Navegar()' | sed -n '1,14p'
} 2>&1 | enmascarar | tee "$OUT"

echo
echo "Evidencia guardada en $OUT"
