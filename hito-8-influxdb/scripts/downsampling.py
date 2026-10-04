#!/usr/bin/env python3
"""Resumen a 1 minuto (downsampling) vivo -> histórico — Fixture 2030, Hito 8.

Lee la base de datos en vivo (retención corta, precisión original de ms) y escribe
en la base histórica (retención indefinida) tablas *_1m con agregaciones elegidas
según la semántica de cada medida (ver docs/retencion_y_granularidad.md):

  gauge (posesión, velocidad, usuarios)   -> avg / max (nunca suma en el tiempo)
  contador acumulado (pases, distancia)   -> max del minuto (= último valor)
  evento / delta (eventos, solicitudes)   -> count / sum
  percentil ya calculado (latencia p95)   -> max (no se promedian percentiles)

Es idempotente: re-ejecutarlo sobrescribe los mismos puntos (misma serie + mismo
timestamp), no duplica.

En producción esto correría como trigger programado del Processing Engine de
InfluxDB 3 (cada 1 min sobre la ventana cerrada). En el laboratorio se ejecuta a demanda.

Uso: python3 scripts/downsampling.py [--corrida NOMBRE] [--partido P001]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import influx_comun as ic  # noqa: E402

# tabla_destino: (sql, tags, {campo: tipo})   tipo: i=int, f=float
RESUMENES = {
    "estadisticas_equipo_1m": ("""
        SELECT date_bin(INTERVAL '1 minute', time) AS time,
               partido_id, equipo_id, condicion, fase, sede_id, pais_sede,
               avg(posesion_pct)        AS posesion_pct_avg,
               max(pases_intentados)    AS pases_intentados,
               max(pases_completados)   AS pases_completados,
               max(tiros)               AS tiros,
               max(tiros_al_arco)       AS tiros_al_arco,
               max(recuperaciones)      AS recuperaciones,
               max(goles)               AS goles,
               max(xg_acum)             AS xg_acum,
               count(*)                 AS muestras
        FROM estadisticas_equipo
        WHERE {rango}
        GROUP BY 1, partido_id, equipo_id, condicion, fase, sede_id, pais_sede""",
        ["partido_id", "equipo_id", "condicion", "fase", "sede_id", "pais_sede"],
        {"posesion_pct_avg": "f", "pases_intentados": "i", "pases_completados": "i", "tiros": "i",
         "tiros_al_arco": "i", "recuperaciones": "i", "goles": "i", "xg_acum": "f", "muestras": "i"}),

    "rendimiento_jugador_1m": ("""
        SELECT date_bin(INTERVAL '1 minute', time) AS time,
               partido_id, equipo_id, jugador_id,
               avg(velocidad_kmh) AS velocidad_avg_kmh,
               max(velocidad_kmh) AS velocidad_max_kmh,
               max(distancia_m)   AS distancia_m,
               max(sprints)       AS sprints,
               count(*)           AS muestras
        FROM rendimiento_jugador
        WHERE {rango}
        GROUP BY 1, partido_id, equipo_id, jugador_id""",
        ["partido_id", "equipo_id", "jugador_id"],
        {"velocidad_avg_kmh": "f", "velocidad_max_kmh": "f", "distancia_m": "f", "sprints": "i",
         "muestras": "i"}),

    "eventos_partido_1m": ("""
        SELECT date_bin(INTERVAL '1 minute', time) AS time,
               partido_id, equipo_id, tipo_evento,
               count(*)                                      AS cantidad,
               sum(CASE WHEN exitoso THEN 1 ELSE 0 END)      AS exitosos,
               sum(xg)                                       AS xg
        FROM eventos_partido
        WHERE {rango}
        GROUP BY 1, partido_id, equipo_id, tipo_evento""",
        ["partido_id", "equipo_id", "tipo_evento"],
        {"cantidad": "i", "exitosos": "i", "xg": "f"}),

    "actividad_usuarios_1m": ("""
        SELECT date_bin(INTERVAL '1 minute', time) AS time,
               partido_id, plataforma, fase, pais_sede,
               avg(usuarios_activos)  AS usuarios_avg,
               max(usuarios_activos)  AS usuarios_max,
               sum(solicitudes)       AS solicitudes,
               sum(errores)           AS errores,
               max(latencia_p95_ms)   AS latencia_p95_max_ms,
               count(*)               AS muestras
        FROM actividad_usuarios
        WHERE {rango}
        GROUP BY 1, partido_id, plataforma, fase, pais_sede""",
        ["partido_id", "plataforma", "fase", "pais_sede"],
        {"usuarios_avg": "f", "usuarios_max": "i", "solicitudes": "i", "errores": "i",
         "latencia_p95_max_ms": "f", "muestras": "i"}),
}


def a_lp(tabla: str, fila: dict, tags: list, campos: dict) -> str | None:
    tg = {t: fila[t] for t in tags if fila.get(t) not in (None, "")}
    cv = {}
    for c, tipo in campos.items():
        v = fila.get(c)
        if v is None:
            continue
        cv[c] = int(round(float(v))) if tipo == "i" else float(v)
    if not cv:
        return None
    return ic.linea_lp(tabla, tg, cv, ic.iso_a_ms(fila["time"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corrida")
    ap.add_argument("--partido", action="append", help="limitar a estos partidos")
    ap.add_argument("--origen", default=ic.DB_VIVO)
    ap.add_argument("--destino", default=ic.DB_HISTORICO)
    a = ap.parse_args()
    man = ic.cargar_manifiesto(a.corrida)
    partidos = [p for p in man["partidos"] if not a.partido or p["partido_id"] in a.partido]

    t0 = time.perf_counter()
    escritos_por_tabla = {t: 0 for t in RESUMENES}
    for p in partidos:
        # Ventana cerrada: minutos completos desde la previa hasta el final del partido.
        rango = (f"partido_id = '{p['partido_id']}' AND time >= '{ic.ms_a_iso(p['previa_ms'])}' "
                 f"AND time < '{ic.ms_a_iso(p['post_ms'] + 60_000)}'")
        for destino, (sql, tags, campos) in RESUMENES.items():
            filas = ic.consultar(a.origen, sql.format(rango=rango))
            lineas = [x for x in (a_lp(destino, f, tags, campos) for f in filas) if x]
            for i in range(0, len(lineas), 5000):
                r = ic.escribir_lp(a.destino, "\n".join(lineas[i:i + 5000]) + "\n")
                if not r["ok"]:
                    print(f"  rechazadas en {destino}: {r['rechazadas'][:3]}")
            escritos_por_tabla[destino] += len(lineas)
        print(f"  {p['partido_id']} resumido")
    seg = time.perf_counter() - t0

    print(f"\nDownsampling {a.origen} -> {a.destino}  ({len(partidos)} partidos, {seg:.1f} s)")
    filas = []
    for t in RESUMENES:
        orig = t.replace("_1m", "")
        crudos = sum(p["conteos"][orig] for p in partidos)
        filas.append({"tabla_resumen": t, "puntos_crudos": crudos, "puntos_1m": escritos_por_tabla[t],
                      "reduccion_x": round(crudos / max(1, escritos_por_tabla[t]), 1)})
    print(ic.tabla_texto(filas))


if __name__ == "__main__":
    main()
