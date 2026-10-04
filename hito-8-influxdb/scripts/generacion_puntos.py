#!/usr/bin/env python3
"""Generación reproducible de puntos (line protocol) — Fixture 2030, Hito 8.

SOLO genera archivos; no escribe en InfluxDB (la carga es carga_lotes.py).

Salida: data/generated/<corrida>/
    P001.lp.gz ... Pnnn.lp.gz   puntos de cada partido, ordenados por timestamp
    tardios.lp.gz               eventos que "llegan tarde" (se cargan al final)
    manifest.json               calendario, conteos esperados, tipos y precisión

Precisión de timestamps: milisegundos (epoch ms), declarada en el manifiesto y
usada como precision=millisecond en la carga.

Tablas generadas (ver docs/modelo_multidimensional.md):
    estadisticas_equipo   1 punto/s por equipo     (contadores acumulados + posesión)
    rendimiento_jugador   1 punto/s por jugador    (velocidad, distancia, sprints)
    eventos_partido       irregular                (pase, tiro, gol, falta, ...)
    actividad_usuarios    1 punto/s por plataforma (audiencia y carga operativa)

Uso:
    python3 scripts/generacion_puntos.py --perfil demo     # 2 partidos  (~0,33 M puntos)
    python3 scripts/generacion_puntos.py --perfil lab      # 12 partidos (~2 M puntos)
    python3 scripts/generacion_puntos.py --perfil torneo   # 104 partidos (~17 M puntos)
    python3 scripts/generacion_puntos.py --partidos 6 --semilla 2030
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from influx_comun import DIR_GENERADOS, PRECISION_LP, ms_a_iso  # noqa: E402

PERFILES = {"demo": 2, "lab": 12, "torneo": 104}

MS_S = 1000
MS_MIN = 60_000
HORA = 3_600_000

PARTIDOS_SIMULTANEOS = 4          # partidos por "jornada" comprimida del laboratorio
SEPARACION_JORNADAS_MS = 3 * HORA

TIPOS_EVENTO = ["pase", "tiro", "gol", "recuperacion", "falta", "tarjeta", "corner", "sustitucion"]
PLATAFORMAS = {"web": 0.28, "ios": 0.34, "android": 0.38}
AUDIENCIA_FASE = {"grupos": 400_000, "dieciseisavos": 600_000, "octavos": 800_000,
                  "cuartos": 1_000_000, "semifinal": 1_500_000, "tercer_puesto": 900_000,
                  "final": 2_500_000}
# Sustituciones fijas: (minuto del 2T, sale, entra). J09 juega siempre (jugador de las consultas).
SUSTITUCIONES = [(15, "J11", "J12"), (25, "J10", "J13"), (35, "J08", "J14")]

TIPOS_CAMPOS = {
    "estadisticas_equipo": {
        "tags": ["partido_id", "equipo_id", "condicion", "fase", "sede_id", "pais_sede"],
        "fields": {"minuto": "Int64", "posesion_pct": "Float64", "pases_intentados": "Int64",
                   "pases_completados": "Int64", "tiros": "Int64", "tiros_al_arco": "Int64",
                   "recuperaciones": "Int64", "faltas": "Int64", "corners": "Int64",
                   "goles": "Int64", "xg_acum": "Float64"}},
    "rendimiento_jugador": {
        "tags": ["partido_id", "equipo_id", "jugador_id"],
        "fields": {"minuto": "Int64", "velocidad_kmh": "Float64", "distancia_m": "Float64",
                   "sprints": "Int64"}},
    "eventos_partido": {
        "tags": ["partido_id", "equipo_id", "tipo_evento"],
        "fields": {"jugador_id": "Utf8", "minuto": "Int64", "exitoso": "Boolean",
                   "x": "Float64", "y": "Float64", "xg": "Float64", "valor": "Int64"}},
    "actividad_usuarios": {
        "tags": ["partido_id", "plataforma", "fase", "pais_sede"],
        "fields": {"usuarios_activos": "Int64", "solicitudes": "Int64", "errores": "Int64",
                   "latencia_p95_ms": "Float64"}},
}


# --------------------------------------------------------------------------- #
# Calendario
# --------------------------------------------------------------------------- #
def sedes():
    # Centenario: 3 partidos inaugurales en Sudamérica; resto en España, Portugal y Marruecos.
    s = [("S01", "URY"), ("S02", "ARG"), ("S03", "PRY")]
    s += [(f"S{i:02d}", "ESP") for i in range(4, 15)]
    s += [(f"S{i:02d}", "PRT") for i in range(15, 18)]
    s += [(f"S{i:02d}", "MAR") for i in range(18, 24)]
    return s


def calendario(semilla: int) -> list[dict]:
    """104 partidos: 72 de grupos (12 grupos x 4 equipos) + 32 de eliminación."""
    rng = random.Random(semilla)
    equipos = [f"E{i:03d}" for i in range(1, 49)]
    grupos = [equipos[i * 4:(i + 1) * 4] for i in range(12)]
    pares_fecha = [[(0, 1), (2, 3)], [(0, 2), (1, 3)], [(0, 3), (1, 2)]]
    partidos = []
    for fecha in range(3):
        for g in grupos:
            for a, b in pares_fecha[fecha]:
                partidos.append(("grupos", g[a], g[b]))
    for fase, n in [("dieciseisavos", 16), ("octavos", 8), ("cuartos", 4),
                    ("semifinal", 2), ("tercer_puesto", 1), ("final", 1)]:
        pool = rng.sample(equipos, n * 2)
        for i in range(n):
            partidos.append((fase, pool[2 * i], pool[2 * i + 1]))
    lista_sedes = sedes()
    resto = lista_sedes[3:]
    out = []
    for i, (fase, loc, vis) in enumerate(partidos):
        sede_id, pais = lista_sedes[i] if i < 3 else resto[(i - 3) % len(resto)]
        out.append({"partido_id": f"P{i + 1:03d}", "fase": fase, "local": loc,
                    "visitante": vis, "sede_id": sede_id, "pais_sede": pais})
    return out


# --------------------------------------------------------------------------- #
# Simulación de un partido
# --------------------------------------------------------------------------- #
def simular_partido(args: tuple) -> dict:
    p, semilla, dir_salida, frac_tardios = args
    rng = random.Random(f"{semilla}-{p['partido_id']}")
    pid, fase, sede, pais = p["partido_id"], p["fase"], p["sede_id"], p["pais_sede"]
    equipos = [p["local"], p["visitante"]]
    condicion = ["local", "visitante"]

    add1, add2 = rng.randint(1, 4), rng.randint(2, 6)
    ini = p["inicio_ms"]
    pt_fin = ini + (45 + add1) * MS_MIN
    st_ini = pt_fin + 15 * MS_MIN
    fin = st_ini + (45 + add2) * MS_MIN
    previa, post = ini - 15 * MS_MIN, fin + 15 * MS_MIN
    p.update({"pt_fin_ms": pt_fin, "st_inicio_ms": st_ini, "fin_ms": fin,
              "previa_ms": previa, "post_ms": post, "adicion_1t": add1, "adicion_2t": add2})

    lineas: list[tuple[int, str]] = []
    tardios: list[str] = []
    cont = {t: 0 for t in TIPOS_CAMPOS}
    series = {t: set() for t in TIPOS_CAMPOS}

    # estado del juego
    fuerza = rng.uniform(0.38, 0.62)          # share de posesión esperado del local
    dueno = 0
    seg_pos = [0, 0]
    acc = [{"pi": 0, "pc": 0, "ti": 0, "ta": 0, "rec": 0, "fal": 0, "cor": 0, "gol": 0, "xg": 0.0}
           for _ in range(2)]
    goles_ms: list[int] = []
    ult_ts_evento: dict = {}
    jug = [{f"J{n:02d}": {"v": rng.uniform(5, 8), "d": 0.0, "s": 0, "sprint": False}
            for n in range(1, 12)} for _ in range(2)]

    tags_eq = [f"partido_id={pid},equipo_id={equipos[k]},condicion={condicion[k]},"
               f"fase={fase},sede_id={sede},pais_sede={pais}" for k in range(2)]

    def evento(k: int, tipo: str, seg_ms: int, minuto: int, jugador: str,
               exitoso: bool | None = None, xg: float | None = None):
        clave = (k, tipo)
        ts = seg_ms + rng.randint(0, 999)
        if ult_ts_evento.get(clave, -1) >= ts:       # evita colisión de timestamp en la serie
            ts = ult_ts_evento[clave] + 1
        ult_ts_evento[clave] = ts
        campos = [f'jugador_id="{jugador}"', f"minuto={minuto}i"]
        if exitoso is not None:
            campos.append("exitoso=" + ("true" if exitoso else "false"))
        campos.append(f"x={rng.uniform(0, 105):.2f}")
        campos.append(f"y={rng.uniform(0, 68):.2f}")
        if xg is not None:
            campos.append(f"xg={xg:.3f}")
        campos.append("valor=1i")
        ln = (f"eventos_partido,partido_id={pid},equipo_id={equipos[k]},tipo_evento={tipo} "
              + ",".join(campos) + f" {ts}")
        cont["eventos_partido"] += 1
        series["eventos_partido"].add((equipos[k], tipo))
        if rng.random() < frac_tardios:
            tardios.append(ln)
        else:
            lineas.append((ts, ln))

    def jugador_al_azar(k):
        return equipos[k] + rng.choice(list(jug[k].keys()))

    for mitad, (t0, dur_min) in enumerate([(ini, 45 + add1), (st_ini, 45 + add2)]):
        for s in range(dur_min * 60):
            seg_ms = t0 + s * MS_S
            minuto = s // 60 + 1 + 45 * mitad
            # sustituciones
            if mitad == 1 and s % 60 == 0:
                for min_st, sale, entra in SUSTITUCIONES:
                    if s // 60 == min_st:
                        for k in range(2):
                            jug[k].pop(sale, None)
                            jug[k][entra] = {"v": rng.uniform(6, 9), "d": 0.0, "s": 0, "sprint": False}
                            evento(k, "sustitucion", seg_ms, minuto, equipos[k] + entra)
            en_juego = rng.random() < 0.62
            if en_juego:
                seg_pos[dueno] += 1
                otro = 1 - dueno
                if rng.random() < 0.30:                          # pase
                    ok = rng.random() < 0.83
                    acc[dueno]["pi"] += 1
                    acc[dueno]["pc"] += ok
                    evento(dueno, "pase", seg_ms, minuto, jugador_al_azar(dueno), ok)
                    if not ok:
                        if rng.random() < 0.6:
                            acc[otro]["rec"] += 1
                            evento(otro, "recuperacion", seg_ms, minuto, jugador_al_azar(otro))
                        dueno = otro
                        otro = 1 - dueno
                if rng.random() < 0.004:                         # tiro
                    al_arco = rng.random() < 0.35
                    xg = rng.uniform(0.03, 0.45)
                    acc[dueno]["ti"] += 1
                    acc[dueno]["ta"] += al_arco
                    acc[dueno]["xg"] += xg
                    autor = jugador_al_azar(dueno)
                    evento(dueno, "tiro", seg_ms, minuto, autor, al_arco, xg)
                    if al_arco and rng.random() < 0.30:
                        acc[dueno]["gol"] += 1
                        goles_ms.append(seg_ms)
                        evento(dueno, "gol", seg_ms, minuto, autor, True)
                    dueno = 1 - dueno
                    otro = 1 - dueno
                if rng.random() < 0.0018:                        # corner
                    acc[dueno]["cor"] += 1
                    evento(dueno, "corner", seg_ms, minuto, jugador_al_azar(dueno))
                p_cambio = 0.06 * ((1 - fuerza) if dueno == 0 else fuerza) / 0.5
                if rng.random() < p_cambio:                      # pérdida/recuperación
                    if rng.random() < 0.5:
                        acc[otro]["rec"] += 1
                        evento(otro, "recuperacion", seg_ms, minuto, jugador_al_azar(otro))
                    dueno = otro
            if rng.random() < 0.0035:                            # falta
                k = rng.randint(0, 1)
                acc[k]["fal"] += 1
                evento(k, "falta", seg_ms, minuto, jugador_al_azar(k))
                if rng.random() < 0.15:
                    evento(k, "tarjeta", seg_ms, minuto, jugador_al_azar(k))

            total_pos = seg_pos[0] + seg_pos[1]
            for k in range(2):
                pos = 50.0 if total_pos == 0 else 100.0 * seg_pos[k] / total_pos
                a = acc[k]
                ts = seg_ms + rng.randint(0, 250)                # latencia del proveedor
                lineas.append((ts,
                    f"estadisticas_equipo,{tags_eq[k]} minuto={minuto}i,posesion_pct={pos:.2f},"
                    f"pases_intentados={a['pi']}i,pases_completados={a['pc']}i,tiros={a['ti']}i,"
                    f"tiros_al_arco={a['ta']}i,recuperaciones={a['rec']}i,faltas={a['fal']}i,"
                    f"corners={a['cor']}i,goles={a['gol']}i,xg_acum={a['xg']:.3f} {ts}"))
                cont["estadisticas_equipo"] += 1
                series["estadisticas_equipo"].add(equipos[k])
                for jid, st in jug[k].items():
                    v = st["v"]
                    if rng.random() < 0.004:                     # inicio de sprint
                        v = rng.uniform(25, 33)
                    else:                                        # caminar/trotar con inercia
                        v = v + 0.15 * (6.5 - v) + rng.gauss(0, 1.2)
                    v = min(max(v, 0.0), 34.0)
                    if v >= 25 and not st["sprint"]:
                        st["s"] += 1
                    st["sprint"] = v >= 25
                    st["v"] = v
                    st["d"] += v / 3.6
                    jfull = equipos[k] + jid
                    tsj = seg_ms + rng.randint(0, 250)
                    lineas.append((tsj,
                        f"rendimiento_jugador,partido_id={pid},equipo_id={equipos[k]},jugador_id={jfull} "
                        f"minuto={minuto}i,velocidad_kmh={v:.2f},distancia_m={st['d']:.1f},sprints={st['s']}i {tsj}"))
                    cont["rendimiento_jugador"] += 1
                    series["rendimiento_jugador"].add(jfull)

    # actividad de usuarios: desde 15 min antes hasta 15 min después del partido
    base = AUDIENCIA_FASE[fase] * rng.uniform(0.7, 1.3)
    for seg_ms in range(previa, post, MS_S):
        if seg_ms < ini:
            curva = 0.4 + 0.5 * (seg_ms - previa) / (ini - previa)
        elif pt_fin <= seg_ms < st_ini:
            curva = 0.85
        elif seg_ms >= fin:
            curva = 0.9 - 0.5 * (seg_ms - fin) / (post - fin)
        else:
            curva = 1.0
        pico = sum(0.35 * math.exp(-(seg_ms - g) / 90_000) for g in goles_ms if g <= seg_ms)
        for plat, share in PLATAFORMAS.items():
            usuarios = int(base * curva * share * (1 + pico) * (1 + rng.gauss(0, 0.01)))
            solicitudes = int(usuarios * 0.02 * (1 + 2 * pico) * (1 + rng.gauss(0, 0.05)))
            carga = solicitudes / 20_000
            errores = int(solicitudes * 0.001 * rng.random() * (1 + 3 * pico))
            lat = max(20.0, 80 + 120 * carga + rng.gauss(0, 8))
            ts = seg_ms + rng.randint(0, 50)
            lineas.append((ts,
                f"actividad_usuarios,partido_id={pid},plataforma={plat},fase={fase},pais_sede={pais} "
                f"usuarios_activos={usuarios}i,solicitudes={solicitudes}i,errores={errores}i,"
                f"latencia_p95_ms={lat:.1f} {ts}"))
            cont["actividad_usuarios"] += 1
            series["actividad_usuarios"].add(plat)

    lineas.sort(key=lambda x: x[0])
    ruta = Path(dir_salida) / f"{pid}.lp.gz"
    with gzip.open(ruta, "wt", encoding="utf-8", compresslevel=3) as f:
        for _, ln in lineas:
            f.write(ln)
            f.write("\n")

    p["conteos"] = cont
    p["series"] = {t: len(v) for t, v in series.items()}
    p["consistencia"] = {equipos[k]: {"pases_intentados": acc[k]["pi"], "goles": acc[k]["gol"],
                                      "posesion_final_pct": round(100.0 * seg_pos[k] / max(1, sum(seg_pos)), 2)}
                         for k in range(2)}
    p["archivo"] = ruta.name
    p["lineas_archivo"] = len(lineas)
    return {"partido": p, "tardios": tardios}


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", choices=PERFILES, default="demo")
    ap.add_argument("--partidos", type=int, help="cantidad de partidos (pisa al perfil)")
    ap.add_argument("--semilla", type=int, default=2030)
    ap.add_argument("--inicio", help="inicio del 1er partido, ISO UTC (ej 2030-06-13T16:00:00Z). "
                                     "Por defecto se ancla al pasado reciente para quedar dentro de la retención.")
    ap.add_argument("--tardios", type=float, default=0.02, help="fracción de eventos que llega tarde")
    ap.add_argument("--procesos", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--nombre", help="nombre de la corrida (default <perfil>_<semilla>)")
    a = ap.parse_args()

    n = a.partidos or PERFILES[a.perfil]
    if not 1 <= n <= 104:
        sys.exit("--partidos debe estar entre 1 y 104")
    jornadas = math.ceil(n / PARTIDOS_SIMULTANEOS)
    if a.inicio:
        inicio = int(datetime.fromisoformat(a.inicio.replace("Z", "+00:00")).timestamp() * 1000)
    else:
        # Calendario comprimido: la última jornada termina antes de "ahora".
        ahora_h = int(time.time() * 1000) // HORA * HORA
        inicio = ahora_h - jornadas * SEPARACION_JORNADAS_MS

    partidos = calendario(a.semilla)[:n]
    for i, p in enumerate(partidos):
        p["jornada"] = i // PARTIDOS_SIMULTANEOS + 1
        p["inicio_ms"] = inicio + (i // PARTIDOS_SIMULTANEOS) * SEPARACION_JORNADAS_MS

    nombre = a.nombre or f"{a.perfil if not a.partidos else 'p' + str(n)}_{a.semilla}"
    salida = DIR_GENERADOS / nombre
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("*.lp.gz"):
        viejo.unlink()

    t0 = time.perf_counter()
    trabajos = [(p, a.semilla, str(salida), a.tardios) for p in partidos]
    if a.procesos > 1 and n > 1:
        with ProcessPoolExecutor(max_workers=a.procesos) as ex:
            resultados = list(ex.map(simular_partido, trabajos))
    else:
        resultados = [simular_partido(t) for t in trabajos]
    tardios = [ln for r in resultados for ln in r["tardios"]]
    with gzip.open(salida / "tardios.lp.gz", "wt", encoding="utf-8") as f:
        for ln in tardios:
            f.write(ln + "\n")
    seg = time.perf_counter() - t0

    partidos = [r["partido"] for r in resultados]
    totales = {t: sum(p["conteos"][t] for p in partidos) for t in TIPOS_CAMPOS}
    man = {
        "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corrida": nombre,
        "perfil": a.perfil,
        "semilla": a.semilla,
        "precision": PRECISION_LP,
        "unidad_timestamp": "epoch milisegundos",
        "partidos_simultaneos": PARTIDOS_SIMULTANEOS,
        "separacion_jornadas_h": SEPARACION_JORNADAS_MS // HORA,
        "fraccion_tardios": a.tardios,
        "rango": {"desde_ms": min(p["previa_ms"] for p in partidos),
                  "hasta_ms": max(p["post_ms"] for p in partidos)},
        "esquema": TIPOS_CAMPOS,
        "totales": totales,
        "total_puntos": sum(totales.values()),
        "lineas_tardias": len(tardios),
        "archivos": [p["archivo"] for p in partidos] + ["tardios.lp.gz"],
        "segundos_generacion": round(seg, 2),
        "partidos": partidos,
    }
    man["rango"]["desde_iso"] = ms_a_iso(man["rango"]["desde_ms"])
    man["rango"]["hasta_iso"] = ms_a_iso(man["rango"]["hasta_ms"])
    (salida / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    (DIR_GENERADOS / "ULTIMA").write_text(nombre)

    print(f"Corrida:          {nombre}  ({salida})")
    print(f"Partidos:         {n}  en {jornadas} jornada(s) de hasta {PARTIDOS_SIMULTANEOS} simultáneos")
    print(f"Rango temporal:   {man['rango']['desde_iso']}  ->  {man['rango']['hasta_iso']}")
    print(f"Precisión:        {PRECISION_LP} (epoch ms)")
    for t, c in totales.items():
        print(f"  {t:<22}{c:>12,}")
    print(f"  {'TOTAL':<22}{man['total_puntos']:>12,}   (tardíos: {len(tardios):,})")
    print(f"Tiempo de generación: {seg:.1f} s  ({man['total_puntos'] / max(seg, 1e-9):,.0f} puntos/s, {a.procesos} procesos)")


if __name__ == "__main__":
    main()
