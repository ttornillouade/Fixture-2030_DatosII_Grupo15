#!/usr/bin/env bash
# RF10 — Resumen a 1 minuto de la base en vivo hacia la base histórica.
. "$(dirname "$0")/comun.sh"
requiere_token
"$PY" scripts/downsampling.py "$@"
