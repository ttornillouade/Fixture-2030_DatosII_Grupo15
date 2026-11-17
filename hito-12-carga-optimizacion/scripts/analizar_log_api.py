"""MEDICIÓN del lado del servidor: latencia según el log de la API (RF6).

La API registra en una línea por request la duración medida dentro del proceso (middleware de
hito-10-api/app/main.py). Comparar esa duración con la que ve el generador separa el tiempo de la API
(procesamiento + espera en el pool de hilos + base) del tiempo de red local, cola de conexiones y
del propio generador.

Uso: python scripts/analizar_log_api.py --etiqueta linea_base --log <log de la API de esa corrida>
"""
import argparse
import json
import re
from datetime import datetime, timedelta

import comun
from ejecutar_carga import percentil

LINEA = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ INFO api (\w+) (\S+) fuente=(\S+) status=(\d+) (\d+)ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--log", required=True)
    args = ap.parse_args()
    carpeta = comun.EVIDENCIA / (comun.EVIDENCIA / f"ultima_{args.etiqueta}.txt").read_text().strip()
    r = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    esc = r["escenario"]
    # El log está en hora local; el inicio de la corrida, en UTC.
    inicio = datetime.strptime(r["inicio_utc"], "%Y%m%dT%H%M%SZ").replace(tzinfo=__import__("datetime").timezone.utc)
    desde = (inicio + timedelta(seconds=2 + esc["calentamiento_s"] + esc["rampa_s"])).astimezone().replace(tzinfo=None)
    hasta = desde + timedelta(seconds=esc["sostenimiento_s"])
    por_op = {}
    for linea in open(args.log, encoding="utf-8", errors="replace"):
        m = LINEA.match(linea)
        if not m or "/comentarios" not in m.group(3):
            continue
        t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        if desde <= t < hasta:
            op = "publicar" if m.group(2) == "POST" else "leer"
            por_op.setdefault(op, []).append(float(m.group(6)))
    salida = {"ventana_local": [str(desde), str(hasta)],
              "nota": "duración medida dentro de la API (middleware), resolución 1 ms",
              **{op: {"requests": len(v), "p50": percentil(v, 50), "p95": percentil(v, 95),
                      "p99": percentil(v, 99), "max": max(v)} for op, v in por_op.items()}}
    comun.guardar_json(carpeta / "servidor.json", salida)
    print(json.dumps(salida, indent=1))


if __name__ == "__main__":
    main()
