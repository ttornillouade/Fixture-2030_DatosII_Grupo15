#!/usr/bin/env bash
# 5.3 — Ejecuta scripts/iris/bloque_5_3.txt línea por línea en la terminal de IRIS y muestra
# cada comando antes de su resultado, como en una sesión interactiva.
# Requiere haber corrido scripts/cargar_clases.sh (copia scripts/iris/ al contenedor).
. "$(dirname "$0")/comun.sh"
requiere_contenedor
docker cp scripts/iris/bloque_5_3.txt "$C":/tmp/fixture/iris/bloque_5_3.txt

iris_terminal <<'EOF' | sed -e '/^Node: /d' -e '/^USER>$/d'
do ##class(%SYS.NLS.Device).SetIO("UTF8")
set %f = ##class(%Stream.FileCharacter).%New(), %f.TranslateTable = "UTF8"  do %f.LinkToFile("/tmp/fixture/iris/bloque_5_3.txt")  while '%f.AtEnd { set %l = %f.ReadLine()  if %l = "" { write ! } elseif $EXTRACT(%l, 1, 2) = "//" { write %l, ! } else { write "USER> ", %l, !  try { xecute %l } catch %e { write "ERROR: ", %e.DisplayString() }  write ! } }
halt
EOF
