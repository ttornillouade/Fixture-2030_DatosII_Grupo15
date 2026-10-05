#!/usr/bin/env python3
"""Validación de la carga — Fixture 2030, Hito 8.

SOLO consulta: compara lo que hay en InfluxDB con lo declarado en manifest.json.

Verificaciones (todas con rango temporal acotado por partido, RNF8):
  V1  cantidad de puntos por tabla y partido == manifiesto (incluye tardíos)
  V2  cantidad de series por tabla y partido == manifiesto (cardinalidad real)
  V3  distribución: 60 puntos por equipo y minuto de juego (frecuencia 1 Hz)
      y 0 puntos en el entretiempo
  V4  coherencia entre tablas: MAX(pases_intentados) == cantidad de eventos 'pase'
  V5  tipos de columnas (tags = Dictionary/Utf8, fields con el tipo declarado)

Uso:  python3 scripts/validacion.py [--corrida NOMBRE] [--db fixture2030_vivo]
Sale con código 1 si alguna verificación falla.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import influx_comun as ic  # noqa: E402

CLAVE_SERIE = {
    "estadisticas_equipo": ["equipo_id"],
    "rendimiento_jugador": ["jugador_id"],
    "eventos_partido": ["equipo_id", "tipo_evento"],
    "actividad_usuarios": ["plataforma"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corrida")
    ap.add_argument("--db", default=ic.DB_VIVO)
    ap.add_argument("--json", help="guardar el resultado en este archivo")
    a = ap.parse_args()
    man = ic.cargar_manifiesto(a.corrida)

    fallas: list[str] = []
    filas_resumen = []
    tot_obs = {t: 0 for t in man["esquema"]}

    for p in man["partidos"]:
        pid = p["partido_id"]
        desde, hasta = ic.ms_a_iso(p["previa_ms"]), ic.ms_a_iso(p["post_ms"] + 1000)
        rango = f"partido_id = '{pid}' AND time >= '{desde}' AND time < '{hasta}'"
        fila = {"partido": pid}
        for tabla, claves in CLAVE_SERIE.items():
            g = ", ".join(claves)
            r = ic.consultar(a.db, f"SELECT {g}, COUNT(*) AS puntos FROM {tabla} WHERE {rango} GROUP BY {g}")
            puntos = sum(int(x["puntos"]) for x in r)
            series = len(r)
            tot_obs[tabla] += puntos
            esp_p, esp_s = p["conteos"][tabla], p["series"][tabla]
            fila[tabla] = f"{puntos}/{esp_p}"
            if puntos != esp_p:
                fallas.append(f"V1 {pid} {tabla}: {puntos} puntos, se esperaban {esp_p}")
            if series != esp_s:
                fallas.append(f"V2 {pid} {tabla}: {series} series, se esperaban {esp_s}")

        # V3 distribución 1 Hz por minuto de juego
        juego = (f"partido_id = '{pid}' AND time >= '{ic.ms_a_iso(p['inicio_ms'])}' "
                 f"AND time < '{ic.ms_a_iso(p['fin_ms'])}'")
        r = ic.consultar(a.db,
            "SELECT equipo_id, date_bin(INTERVAL '1 minute', time) AS time, COUNT(*) AS n "
            f"FROM estadisticas_equipo WHERE {juego} GROUP BY 1, 2")
        minutos_esperados = 90 + p["adicion_1t"] + p["adicion_2t"]
        por_equipo: dict = {}
        for x in r:
            por_equipo.setdefault(x["equipo_id"], []).append(int(x["n"]))
        for eq, ns in por_equipo.items():
            if len(ns) != minutos_esperados or any(n != 60 for n in ns):
                fallas.append(f"V3 {pid} {eq}: {len(ns)} minutos con datos (esperados {minutos_esperados}), "
                              f"puntos/minuto min={min(ns)} max={max(ns)} (esperado 60)")
        ht = (f"partido_id = '{pid}' AND time >= '{ic.ms_a_iso(p['pt_fin_ms'] + 1000)}' "
              f"AND time < '{ic.ms_a_iso(p['st_inicio_ms'])}'")
        r = ic.consultar(a.db, f"SELECT COUNT(*) AS n FROM estadisticas_equipo WHERE {ht}")
        n_ht = int(r[0]["n"]) if r else 0
        if n_ht != 0:
            fallas.append(f"V3 {pid}: {n_ht} puntos en el entretiempo (esperado 0)")

        # V4 coherencia contador acumulado vs eventos
        r1 = ic.consultar(a.db, f"SELECT equipo_id, MAX(pases_intentados) AS v FROM estadisticas_equipo "
                                f"WHERE {rango} GROUP BY equipo_id")
        r2 = ic.consultar(a.db, f"SELECT equipo_id, COUNT(*) AS v FROM eventos_partido "
                                f"WHERE {rango} AND tipo_evento = 'pase' GROUP BY equipo_id")
        m1 = {x["equipo_id"]: int(x["v"]) for x in r1}
        m2 = {x["equipo_id"]: int(x["v"]) for x in r2}
        for eq, cons in p["consistencia"].items():
            if not (m1.get(eq) == m2.get(eq) == cons["pases_intentados"]):
                fallas.append(f"V4 {pid} {eq}: max(pases_intentados)={m1.get(eq)} "
                              f"eventos pase={m2.get(eq)} manifiesto={cons['pases_intentados']}")
        fila["pases_ok"] = "si" if not any(f.startswith(f"V4 {pid}") for f in fallas) else "NO"
        filas_resumen.append(fila)

    # V5 tipos
    r = ic.consultar(a.db, "SELECT table_name, column_name, data_type FROM information_schema.columns "
                           "WHERE table_schema = 'iox'")
    tipos = {(x["table_name"], x["column_name"]): x["data_type"] for x in r}
    filas_tipos = []
    for tabla, esq in man["esquema"].items():
        for tag in esq["tags"]:
            dt = tipos.get((tabla, tag), "AUSENTE")
            filas_tipos.append({"tabla": tabla, "columna": tag, "rol": "tag", "tipo": dt})
            if "Utf8" not in dt:
                fallas.append(f"V5 {tabla}.{tag}: tipo {dt}, se esperaba Dictionary(Int32, Utf8)")
        for campo, tipo in esq["fields"].items():
            dt = tipos.get((tabla, campo), "AUSENTE")
            filas_tipos.append({"tabla": tabla, "columna": campo, "rol": "field", "tipo": dt})
            if dt != tipo:
                fallas.append(f"V5 {tabla}.{campo}: tipo {dt}, se esperaba {tipo}")
        dt = tipos.get((tabla, "time"), "AUSENTE")
        filas_tipos.append({"tabla": tabla, "columna": "time", "rol": "timestamp", "tipo": dt})
        if not dt.startswith("Timestamp"):
            fallas.append(f"V5 {tabla}.time: tipo {dt}")

    print(f"Corrida: {man['corrida']}  ({len(man['partidos'])} partidos)  db={a.db}")
    print("\nV1/V2/V4 — puntos observados/esperados por partido")
    print(ic.tabla_texto(filas_resumen, 120))
    print("\nTotales por tabla (observado vs esperado)")
    print(ic.tabla_texto([{"tabla": t, "observado": tot_obs[t], "esperado": man["totales"][t],
                           "ok": "si" if tot_obs[t] == man["totales"][t] else "NO"} for t in tot_obs]))
    print("\nV5 — tipos de columnas en InfluxDB")
    print(ic.tabla_texto(filas_tipos, 200))
    total_obs = sum(tot_obs.values())
    print(f"\nTOTAL puntos: observado {total_obs:,} / esperado {man['total_puntos']:,}")
    if fallas:
        print(f"\nVALIDACION CON {len(fallas)} FALLA(S):")
        for f in fallas[:50]:
            print("  -", f)
    else:
        print("\nVALIDACION OK: cantidades, series, distribución 1 Hz, coherencia y tipos coinciden.")
    if a.json:
        Path(a.json).write_text(json.dumps({"fecha_utc": ic.ahora_iso(), "corrida": man["corrida"],
                                            "total_observado": total_obs, "total_esperado": man["total_puntos"],
                                            "fallas": fallas}, indent=1, ensure_ascii=False))
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
