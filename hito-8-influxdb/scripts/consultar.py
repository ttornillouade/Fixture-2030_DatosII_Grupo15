#!/usr/bin/env python3
"""Ejecuta archivos .sql contra InfluxDB 3 y muestra resultado + tiempo — Hito 8.

Los .sql usan variables {{PARTIDO}}, {{VENTANA_DESDE}}, ... que se resuelven desde
el manifiesto de la última corrida (ver influx_comun.variables_sql). Así las
consultas siempre acotan rango temporal y dimensiones (RNF8).

Directivas opcionales en la cabecera del .sql:
    -- titulo: Texto
    -- db: historico            (por defecto: vivo)
    -- interpretacion: Texto que explica cómo leer el resultado
    -- opcional: si             (si falla, se informa y se continúa)

Uso:
    python3 scripts/consultar.py sql/consultas            # todos los .sql de la carpeta
    python3 scripts/consultar.py sql/agregaciones/a02_pases_por_intervalo.sql
    python3 scripts/consultar.py sql/consultas --repeticiones 5 --guardar docs/evidencia/x.json
    python3 scripts/consultar.py --sql "SELECT COUNT(*) FROM eventos_partido WHERE time >= now() - INTERVAL '1 day'"
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import influx_comun as ic  # noqa: E402


def leer_sql(ruta: Path) -> tuple[dict, str]:
    meta, cuerpo = {}, []
    for ln in ruta.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("--") and ":" in s and not cuerpo:
            k, v = s[2:].split(":", 1)
            k = k.strip().lower()
            if k in ("titulo", "db", "interpretacion", "opcional", "patron"):
                meta[k] = (meta.get(k, "") + " " + v.strip()).strip()
                continue
        if s.startswith("--") and not cuerpo:
            continue
        cuerpo.append(ln)
    return meta, "\n".join(cuerpo).strip().rstrip(";")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rutas", nargs="*")
    ap.add_argument("--sql", help="consulta directa")
    ap.add_argument("--db", help="forzar base (fixture2030_vivo / fixture2030_historico)")
    ap.add_argument("--corrida")
    ap.add_argument("--repeticiones", type=int, default=1, help="ejecuciones para medir latencia")
    ap.add_argument("--max-filas", type=int, default=25)
    ap.add_argument("--guardar", help="guardar tiempos y cantidad de filas en JSON")
    a = ap.parse_args()

    man = ic.cargar_manifiesto(a.corrida)
    variables = ic.variables_sql(man)

    trabajos = []
    if a.sql:
        trabajos.append(("(directa)", {}, a.sql))
    for r in a.rutas:
        p = Path(r)
        for f in (sorted(p.glob("*.sql")) if p.is_dir() else [p]):
            meta, sql = leer_sql(f)
            trabajos.append((f.name, meta, sql))
    if not trabajos:
        ap.error("indicar archivos/carpetas .sql o --sql")

    print(f"Corrida: {man['corrida']} | partido de referencia {variables['PARTIDO']} "
          f"({variables['EQUIPO_LOCAL']} vs {variables['EQUIPO_VISITANTE']}, sede {variables['SEDE']})")
    resultados, fallidas = [], 0
    for nombre, meta, sql in trabajos:
        db = a.db or (ic.DB_HISTORICO if meta.get("db", "").startswith("hist") else ic.DB_VIVO)
        sql_final = ic.sustituir(sql, variables)
        print("\n" + "=" * 100)
        print(f"{nombre} — {meta.get('titulo', '')}")
        if meta.get("patron"):
            print(f"Patrón de acceso: {meta['patron']}")
        print(f"db: {db}")
        print("-" * 100)
        print(sql_final)
        print("-" * 100)
        tiempos, filas = [], []
        try:
            for _ in range(max(1, a.repeticiones)):
                t0 = time.perf_counter()
                filas = ic.consultar(db, sql_final)
                tiempos.append((time.perf_counter() - t0) * 1000)
        except Exception as e:  # noqa: BLE001
            msg = str(e)[:400]
            if meta.get("opcional", "").lower().startswith("s"):
                print(f"(consulta opcional no disponible: {msg})")
            else:
                print(f"ERROR: {msg}")
                fallidas += 1
            resultados.append({"archivo": nombre, "error": msg})
            continue
        print(ic.tabla_texto(filas, a.max_filas))
        med = statistics.median(tiempos)
        print(f"Tiempo (cliente HTTP, {len(tiempos)} ejec.): mediana {med:.1f} ms | "
              f"min {min(tiempos):.1f} | max {max(tiempos):.1f}")
        if meta.get("interpretacion"):
            print(f"Interpretación: {meta['interpretacion']}")
        resultados.append({"archivo": nombre, "titulo": meta.get("titulo", ""), "db": db,
                           "filas": len(filas), "ms_mediana": round(med, 2),
                           "ms_min": round(min(tiempos), 2), "ms_max": round(max(tiempos), 2),
                           "repeticiones": len(tiempos)})
    if a.guardar:
        Path(a.guardar).parent.mkdir(parents=True, exist_ok=True)
        Path(a.guardar).write_text(json.dumps({"fecha_utc": ic.ahora_iso(), "corrida": man["corrida"],
                                               "resultados": resultados}, indent=1, ensure_ascii=False))
        print(f"\nTiempos guardados en {a.guardar}")
    sys.exit(1 if fallidas else 0)


if __name__ == "__main__":
    main()
