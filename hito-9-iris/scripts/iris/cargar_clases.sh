#!/bin/sh
# Corre DENTRO del contenedor. Carga y compila todas las clases .cls de /tmp/fixture/src.
# Sale con código 1 si alguna clase no compila (RNF2).

iris session IRIS -U "${IRIS_NAMESPACE:-USER}" <<'EOF'
set sc = $SYSTEM.OBJ.LoadDir("/tmp/fixture/src", "ck", .errores, 1, .cargadas)
write !, "Clases cargadas: ", $GET(cargadas), !
write "Errores de compilación: ", +$GET(errores), !
if 'sc { do $SYSTEM.Status.DisplayError(sc)  write !  do $SYSTEM.Process.Terminate($JOB, 1) }
write "COMPILACION OK", !
halt
EOF
