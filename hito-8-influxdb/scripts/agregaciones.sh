#!/usr/bin/env bash
# RF9 — Agregaciones temporales justificadas por la semántica de cada medida.
. "$(dirname "$0")/comun.sh"
requiere_token
"$PY" scripts/consultar.py sql/agregaciones "$@"
