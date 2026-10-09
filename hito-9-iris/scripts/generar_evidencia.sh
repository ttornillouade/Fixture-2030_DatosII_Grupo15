#!/usr/bin/env bash
# Evidencia del Hito 9: versión de IRIS, compilación de scripts/Fixture y ejecución de
# scripts/demo_hito9.mac línea por línea en el Terminal (cada comando seguido de su salida).
# Uso: docker compose up -d && bash scripts/generar_evidencia.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="docs/evidencia/evidencia_hito9_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p docs/evidencia

{
  echo "EVIDENCIA HITO 9 — FIXTURE 2030 — ENTIDADES COMPLEJAS (InterSystems IRIS)"
  echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo
  docker compose ps
  docker image inspect intersystems/iris-community:latest-cd --format 'Imagen: {{index .RepoDigests 0}}'
  echo
  docker exec -i fixture2030-iris iris session IRIS <<'IRIS' | sed -e '/^Node: /d' -e '/^USER>$/d'
do ##class(%SYS.NLS.Device).SetIO("UTF8")
write !,"===== Versión =====",!,$zversion,!
write !,"===== Compilación: do $system.OBJ.LoadDir(""/scripts/Fixture"",""ck"") =====",!
do $system.OBJ.LoadDir("/scripts/Fixture", "ck", .err, 1)  write !,"Errores de compilación: ",+$get(err),!
write !,"===== Demo: scripts/demo_hito9.mac =====",!
set %f = ##class(%Stream.FileCharacter).%New(), %f.TranslateTable = "UTF8"  do %f.LinkToFile("/scripts/demo_hito9.mac")  while '%f.AtEnd { set %l = %f.ReadLine()  if %l = "" { write ! } elseif $extract(%l, 1, 2) = "//" { write %l, ! } else { write "USER> ", %l, !  try { xecute %l } catch %e { write "ERROR: ", %e.DisplayString() }  write ! } }
halt
IRIS
} 2>&1 | tee "$OUT"

echo
echo "Evidencia guardada en $OUT"
