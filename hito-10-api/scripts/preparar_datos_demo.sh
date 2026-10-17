#!/usr/bin/env bash
# Prepara datos de prueba para la API. Se ejecuta a mano, nunca al arrancar la API.
#   1. IRIS: aplica IRIS_PASSWORD de .env al usuario _SYSTEM (la imagen exige cambiar la de fábrica).
#   2. IRIS: deja el partido P003 en PROGRAMADO, para probar PATCH /partidos/P003/estado.
# Requiere el contenedor fixture2030-iris del Hito 9 con las clases compiladas.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

docker exec -i -e IRIS_PASSWORD="$IRIS_PASSWORD" fixture2030-iris iris session IRIS -U %SYS <<'IRIS' | grep -E "^(OK|ERROR)" || true
set p("Password") = $system.Util.GetEnviron("IRIS_PASSWORD"), p("ChangePassword") = 0
set sc = ##class(Security.Users).Modify("_SYSTEM", .p)  write $select(sc: "OK contraseña de _SYSTEM aplicada", 1: "ERROR "_$system.Status.GetErrorText(sc)), !
halt
IRIS

docker exec -i fixture2030-iris iris session IRIS <<'IRIS' | grep -E "^(OK|ERROR)" || true
set base = ##class(Fixture.Partido).CodigoIdxOpen("P001")
if '$isobject(base) write "ERROR falta P001: ejecutar la demo del Hito 9 (scripts/demo_hito9.mac)", !  halt
do ##class(Fixture.Partido).CodigoIdxDelete("P003")
set p = ##class(Fixture.Partido).%New(), p.Codigo = "P003", p.FechaHora = "2030-06-10 18:00:00", p.Sede = base.Sede, p.EquipoLocal = base.EquipoVisitante, p.EquipoVisitante = base.EquipoLocal, p.Arbitro = base.Arbitro
set sc = p.%Save()  write $select(sc: "OK P003 en PROGRAMADO", 1: "ERROR "_$system.Status.GetErrorText(sc)), !
halt
IRIS
