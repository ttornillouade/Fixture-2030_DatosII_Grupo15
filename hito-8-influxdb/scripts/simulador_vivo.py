#!/usr/bin/env python3
"""Simulador de partido EN VIVO — Fixture 2030, Hito 8.

Escribe en tiempo real (1 punto/s por equipo y por plataforma) un partido "en curso"
con timestamps = ahora, para demostrar:
  * la ventana reciente con now()  (sql/consultas/c06_ventana_reciente.sql)
  * la Last Value Cache             (sql/consultas/c07_ultimo_valor_cache.sql)
  * el corte de la fuente: --corte INICIO:DURACION deja de enviar N segundos
    (la consulta de ventana reciente muestra el hueco; la LVC conserva el último valor)

El partido simulado es el siguiente al último de la corrida generada (no altera
los conteos que verifica validacion.py).

Uso: python3 scripts/simulador_vivo.py --segundos 90 --corte 30:20
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import influx_comun as ic  # noqa: E402
from generacion_puntos import calendario, PLATAFORMAS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segundos", type=int, default=90)
    ap.add_argument("--corte", default="", help="INICIO:DURACION en segundos sin enviar datos")
    ap.add_argument("--corrida")
    a = ap.parse_args()

    man = ic.cargar_manifiesto(a.corrida)
    n = min(len(man["partidos"]) + 1, 104)
    p = calendario(man["semilla"])[n - 1]
    pid, eqs = p["partido_id"], [p["local"], p["visitante"]]
    corte = (0, 0)
    if a.corte:
        i, d = a.corte.split(":")
        corte = (int(i), int(d))
    rng = random.Random(7)
    acc = [{"pi": 0, "ti": 0, "gol": 0, "pos": 0} for _ in range(2)]
    print(f"Simulando {pid} ({eqs[0]} vs {eqs[1]}) en vivo durante {a.segundos} s -> {ic.DB_VIVO}")
    if corte[1]:
        print(f"Corte de fuente: sin datos entre el segundo {corte[0]} y {corte[0] + corte[1]}")
    t_ini = time.time()
    for s in range(a.segundos):
        dueno = 0 if rng.random() < 0.55 else 1
        acc[dueno]["pos"] += 1
        if rng.random() < 0.3:
            acc[dueno]["pi"] += 1
        if rng.random() < 0.02:
            acc[dueno]["ti"] += 1
        if rng.random() < 0.004:
            acc[dueno]["gol"] += 1
        if corte[0] <= s < corte[0] + corte[1]:
            if s == corte[0]:
                print(f"  [{s:>3}s] CORTE: la fuente deja de enviar")
        else:
            ts = int(time.time() * 1000)
            tot = acc[0]["pos"] + acc[1]["pos"]
            lineas = []
            for k in range(2):
                lineas.append(ic.linea_lp("estadisticas_equipo",
                    {"partido_id": pid, "equipo_id": eqs[k], "condicion": ["local", "visitante"][k],
                     "fase": p["fase"], "sede_id": p["sede_id"], "pais_sede": p["pais_sede"]},
                    {"minuto": s // 60 + 1, "posesion_pct": 100.0 * acc[k]["pos"] / tot,
                     "pases_intentados": acc[k]["pi"], "tiros": acc[k]["ti"], "goles": acc[k]["gol"]}, ts))
            for plat, share in PLATAFORMAS.items():
                u = int(500_000 * share * (1 + rng.gauss(0, 0.01)))
                lineas.append(ic.linea_lp("actividad_usuarios",
                    {"partido_id": pid, "plataforma": plat, "fase": p["fase"], "pais_sede": p["pais_sede"]},
                    {"usuarios_activos": u, "solicitudes": int(u * 0.02), "errores": 0,
                     "latencia_p95_ms": 85.0 + rng.gauss(0, 5)}, ts))
            r = ic.escribir_lp(ic.DB_VIVO, "\n".join(lineas) + "\n")
            if not r["ok"]:
                print("  rechazos:", r["rechazadas"][:2])
            if s % 10 == 0:
                print(f"  [{s:>3}s] {ic.ms_a_iso(ts)} pases {acc[0]['pi']}-{acc[1]['pi']} goles {acc[0]['gol']}-{acc[1]['gol']}")
        time.sleep(max(0.0, t_ini + s + 1 - time.time()))
    print("Fin de la simulación.")


if __name__ == "__main__":
    main()
