"""Estadísticas temporales por equipo en InfluxDB (tabla estadisticas_equipo del Hito 8).

Genera 1 punto por segundo y equipo para P001-P004 (95 minutos desde las 16:00 UTC de la fecha del
partido), de forma determinística, y los escribe en line protocol. Las fechas son del torneo (2030):
la retención de 14 días de fixture2030_vivo no los borra. Es repetible: un punto con la misma serie
y el mismo instante reemplaza al anterior.
Uso (con .env cargado): .venv/bin/python scripts/influx/estadisticas.py ../hito-5-neo4j/import/partidos.csv
"""
import csv
import os
import random
import sys
from datetime import datetime, timezone

import httpx

PARTIDOS = {"P001", "P002", "P003", "P004"}
LOTE = 10_000

cliente = httpx.Client(base_url=os.environ["INFLUX_URL"], timeout=30,
                       headers={"Authorization": f"Bearer {os.environ['INFLUX_TOKEN']}"})
azar = random.Random(2030)

with open(sys.argv[1], newline="", encoding="utf-8") as f:
    partidos = [p for p in csv.DictReader(f) if p["id"] in PARTIDOS]

for p in sorted(partidos, key=lambda p: p["id"]):
    inicio = int(datetime.fromisoformat(p["fecha"] + "T16:00:00").replace(tzinfo=timezone.utc).timestamp())
    equipos = (p["local_id"], p["visitante_id"])
    pases, tiros, posesion_local, lineas = [0, 0], [0, 0], 50.0, []
    for s in range(95 * 60):
        posesion_local = min(80, max(20, posesion_local + (azar.random() - 0.5) * 2))
        for i in (0, 1):
            pases[i] += azar.random() < 0.08
            tiros[i] += azar.random() < 0.002
            posesion = posesion_local if i == 0 else 100 - posesion_local
            lineas.append(f"estadisticas_equipo,partido_id={p['id']},equipo_id={equipos[i]} "
                          f"posesion_pct={posesion:.2f},pases_completados={pases[i]}i,tiros={tiros[i]}i {inicio + s}")
    for desde in range(0, len(lineas), LOTE):
        r = cliente.post("/api/v3/write_lp", params={"db": os.environ["INFLUX_DATABASE"], "precision": "second"},
                         content="\n".join(lineas[desde:desde + LOTE]))
        r.raise_for_status()
    print(f"{p['id']}: {len(lineas)} puntos desde {datetime.fromtimestamp(inicio, timezone.utc).isoformat()}")
