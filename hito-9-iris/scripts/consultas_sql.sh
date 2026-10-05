#!/usr/bin/env bash
# RF8 — Ejecuta sql/consultas.sql en el shell SQL de IRIS ($SYSTEM.SQL.Shell()).
# Son consultas relacionales clásicas, sin ObjectScript, sobre las tablas proyectadas.
. "$(dirname "$0")/comun.sh"
requiere_contenedor

{
  echo 'do ##class(%SYS.NLS.Device).SetIO("UTF8")'
  echo 'do $SYSTEM.SQL.Shell()'
  # Los comentarios numerados (-- 1. ...) se muestran como títulos; el resto de los comentarios se omite.
  while IFS= read -r linea; do
    case "$linea" in
      "-- "[0-9]*) printf "SELECT '%s' AS Consulta\n" "$(echo "${linea#-- }" | sed "s/'/''/g")" ;;
      ""|--*) ;;
      *) echo "$linea" ;;
    esac
  done < sql/consultas.sql
  echo 'quit'
  echo 'halt'
} | iris_terminal
