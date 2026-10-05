#!/usr/bin/env bash
# Autorización local: crea el token de administrador (operator token) y lo guarda
# SOLO en .env (archivo ignorado por git). Nunca se imprime completo.
. "$(dirname "$0")/comun.sh"

[ -f .env ] || { cp .env.example .env; echo "Se creó .env a partir de .env.example"; }
chmod 600 .env

if [ -n "${INFLUX_TOKEN:-}" ] && influx_auth show databases >/dev/null 2>&1; then
  echo "El token de .env es válido (${INFLUX_TOKEN:0:10}****). No se crea uno nuevo."
  exit 0
fi

echo "Creando token de administrador con: influxdb3 create token --admin"
salida=$(influx create token --admin 2>&1 || true)
nuevo=$(printf '%s' "$salida" | grep -oE 'apiv3_[A-Za-z0-9_-]+' | head -1 || true)

if [ -z "$nuevo" ]; then
  echo "No se pudo crear el token. Respuesta del servidor (enmascarada):"
  printf '%s\n' "$salida" | enmascarar
  cat <<'MSG'

Causa habitual: ya existe un token de administrador en esta instancia.
  a) Si lo tenés, pegalo en .env como INFLUX_TOKEN=... y volvé a ejecutar este script.
  b) Si lo tenés pero querés rotarlo:
       INFLUXDB3_AUTH_TOKEN=<token_actual> docker exec -e INFLUXDB3_AUTH_TOKEN \
         fixture2030-influxdb influxdb3 create token --admin --regenerate
  c) Si se perdió y es un laboratorio descartable: bash scripts/limpieza.sh --reset-total
MSG
  exit 1
fi

"$PY" - "$nuevo" <<'PYEOF'
import re, sys
tok = sys.argv[1]
txt = open(".env", encoding="utf-8").read()
if re.search(r"^INFLUX_TOKEN=.*$", txt, flags=re.M):
    txt = re.sub(r"^INFLUX_TOKEN=.*$", "INFLUX_TOKEN=" + tok, txt, flags=re.M)
else:
    txt = txt.rstrip("\n") + "\nINFLUX_TOKEN=" + tok + "\n"
open(".env", "w", encoding="utf-8").write(txt)
PYEOF
chmod 600 .env
echo "Token creado y guardado en .env (${nuevo:0:10}****). .env está en .gitignore."

export INFLUX_TOKEN="$nuevo"
influx_auth show databases >/dev/null && echo "Verificación OK: el token autentica contra el servidor."
echo "Siguiente paso: bash scripts/crear_bases.sh"
