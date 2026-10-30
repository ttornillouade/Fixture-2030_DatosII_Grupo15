"""Partidos con sus eventos en IRIS, con las clases del Hito 9 (Fixture.Partido, Evento, Jugador).

Fuente: los CSV del Hito 5 (mismos códigos que Neo4j y MongoDB). Los eventos se agregan con
Partido.RegistrarEvento y cada partido se guarda con un solo %Save, que guarda también sus eventos
y los jugadores nuevos. Los partidos jugados quedan FINALIZADOS después de registrar sus eventos.
Si los partidos ya están cargados no hace nada; si no, vacía las clases (como la demo del Hito 9) y carga.
Uso (con .env cargado): .venv/bin/python scripts/iris/partidos.py ../hito-5-neo4j/import
"""
import csv
import os
import sys
from collections import defaultdict

import iris


def leer(nombre: str) -> list[dict]:
    with open(os.path.join(sys.argv[1], nombre), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verificar(sc, contexto: str):
    if sc != 1 and str(sc) != "1":
        sys.exit(f"ERROR {contexto}: {nativo.classMethodValue('%SYSTEM.Status', 'GetErrorText', sc)}")


conexion = iris.connect(os.environ["IRIS_HOST"], int(os.environ["IRIS_PORT"]), os.environ["IRIS_NAMESPACE"],
                        os.environ["IRIS_USUARIO"], os.environ["IRIS_PASSWORD"])
nativo = iris.createIRIS(conexion)
cursor = conexion.cursor()
partidos = leer("partidos.csv")

cursor.execute("SELECT COUNT(*) FROM Fixture.Partido WHERE Codigo = ?", [partidos[-1]["id"]])
if cursor.fetchone()[0]:
    print("partidos ya cargados")
    sys.exit(0)

for clase in ("Fixture.Evento", "Fixture.Partido", "Fixture.Persona"):
    nativo.classMethodVoid(clase, "%KillExtent")

fichas = {j["id"]: j for j in leer("jugadores.csv")}
eventos = defaultdict(list)
for e in leer("eventos.csv"):
    eventos[e["partido_id"]].append(e)

jugadores = {}
for p in partidos:
    partido = nativo.classMethodObject("Fixture.Partido", "%New")
    partido.set("Codigo", p["id"])
    for e in sorted(eventos[p["id"]], key=lambda e: int(e["minuto"])):
        if e["jugador_id"] not in jugadores:
            ficha, jugador = fichas[e["jugador_id"]], nativo.classMethodObject("Fixture.Jugador", "%New")
            for propiedad, campo in (("Nombre", "nombre"), ("Apellido", "apellido"), ("Nacionalidad", "nacionalidad")):
                jugador.set(propiedad, ficha[campo])
            jugador.set("Dorsal", int(ficha["dorsal"]))
            jugadores[e["jugador_id"]] = jugador
        verificar(partido.invoke("RegistrarEvento", e["tipo"], int(e["minuto"]), jugadores[e["jugador_id"]]),
                  f"evento {e['id']}")
    if p["estado"].strip() == "Finalizado":
        partido.set("Estado", "FINALIZADO")
    verificar(partido.invoke("%Save"), f"partido {p['id']}")

cursor.execute("SELECT COUNT(*) FROM Fixture.Partido")
n_partidos = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM Fixture.Evento")
print(f"Total: {n_partidos} partidos, {cursor.fetchone()[0]} eventos, {len(jugadores)} jugadores")
