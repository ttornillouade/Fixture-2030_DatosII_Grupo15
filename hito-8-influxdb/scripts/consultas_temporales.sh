#!/usr/bin/env bash
# RF8 — Ventana temporal, filtros por dimensión, comparaciones y ventana reciente.
. "$(dirname "$0")/comun.sh"
requiere_token
"$PY" scripts/consultar.py sql/consultas "$@"
