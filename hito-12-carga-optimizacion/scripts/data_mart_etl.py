"""DATA MART (prototipo): proyección analítica "actividad de comentarios por partido y minuto".

Pregunta analítica (docs/integracion_data_mart.md): ¿cómo evoluciona, minuto a minuto, la actividad de
comentarios de cada partido (volumen, autores distintos, moderación, reacciones)?

Extracción  : Cassandra fixture2030_comments.comentarios_por_partido, por partición completa
              (partido, bucket de 5 min, shard 0..7). Solo ventanas CERRADAS: bucket + 5 min + 2 min de
              tolerancia para datos tardíos (watermark) < ahora.
Transformación: agrupa por minuto (truncando creado_en), cuenta comentarios y ocultos, suma reacciones y
              cuenta autores distintos. Deduplica por comentario_id (si una fila aparece dos veces, cuenta una).
Carga       : keyspace fixture2030_mart, tabla actividad_partido_minuto ((partido_id), minuto). Upsert por
              clave: reprocesar una ventana reescribe las mismas filas (idempotente; sin duplicados).
Procedencia : cada fila guarda la fuente, la ventana de origen, la cantidad de filas leídas y la hora del ETL.

Uso:
  python scripts/data_mart_etl.py cargar   [--partidos P901,P902] [--desde-horas 4]
  python scripts/data_mart_etl.py validar                (conteos mart vs fuente)
  python scripts/data_mart_etl.py comparar               (misma pregunta: fuente vs proyección, tiempos)
"""
import argparse
import statistics
import time
from collections import defaultdict
from datetime import timedelta

from cassandra.concurrent import execute_concurrent_with_args

import comun

MART = "fixture2030_mart"
TOLERANCIA = timedelta(minutes=2)

DDL = [
    f"CREATE KEYSPACE IF NOT EXISTS {MART} WITH replication = {{'class':'NetworkTopologyStrategy','datacenter1':1}}",
    f"""CREATE TABLE IF NOT EXISTS {MART}.actividad_partido_minuto (
        partido_id text, minuto timestamp,
        comentarios int, ocultos int, reacciones int, autores_distintos int,
        fuente text, ventana_origen timestamp, filas_leidas int, etl_utc timestamp, version_etl text,
        PRIMARY KEY ((partido_id), minuto)
    ) WITH CLUSTERING ORDER BY (minuto ASC)""",
    f"""CREATE TABLE IF NOT EXISTS {MART}.etl_marcas (
        partido_id text, ventana timestamp, filas_leidas int, minutos_escritos int, etl_utc timestamp,
        PRIMARY KEY ((partido_id), ventana)
    )""",
]


def ventanas_cerradas(desde_horas: int):
    fin = comun.bucket_de(comun.ahora() - timedelta(minutes=5) - TOLERANCIA)
    b = fin - timedelta(hours=desde_horas)
    while b <= fin:
        yield b
        b += timedelta(minutes=5)


def leer_fuente(s, partidos, ventanas):
    """Lee las particiones completas de la fuente operacional. Devuelve {(partido, ventana): [filas]}."""
    q = s.prepare("SELECT comentario_id, creado_en, autor_id, estado_moderacion, reacciones "
                  "FROM fixture2030_comments.comentarios_por_partido WHERE partido_id=? AND bucket_5m=? AND shard=?")
    claves = [(p, v, sh) for p in partidos for v in ventanas for sh in range(comun.SHARDS)]
    filas = defaultdict(list)
    for (p, v, _), (ok, res) in zip(claves, execute_concurrent_with_args(s, q, claves, concurrency=64,
                                                                         raise_on_first_error=True)):
        filas[(p, v)].extend(res)
    return filas, len(claves)


def cargar(partidos, desde_horas):
    cluster, s = comun.sesion_cassandra()
    for ddl in DDL:
        s.execute(ddl)
    ventanas = list(ventanas_cerradas(desde_horas))
    t0 = time.perf_counter()
    fuente, particiones = leer_fuente(s, partidos, ventanas)
    t_ext = time.perf_counter() - t0
    ins = s.prepare(f"INSERT INTO {MART}.actividad_partido_minuto (partido_id, minuto, comentarios, ocultos, "
                    "reacciones, autores_distintos, fuente, ventana_origen, filas_leidas, etl_utc, version_etl) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    marca = s.prepare(f"INSERT INTO {MART}.etl_marcas (partido_id, ventana, filas_leidas, minutos_escritos, etl_utc) "
                      "VALUES (?, ?, ?, ?, ?)")
    ahora = comun.ahora()
    filas_mart, marcas, duplicadas = [], [], 0
    for (p, v), filas in fuente.items():
        vistos, por_min = set(), defaultdict(lambda: {"c": 0, "o": 0, "r": 0, "a": set()})
        for f in filas:
            if f.comentario_id in vistos:
                duplicadas += 1
                continue
            vistos.add(f.comentario_id)
            m = por_min[f.creado_en.replace(second=0, microsecond=0)]
            m["c"] += 1
            m["o"] += f.estado_moderacion != "VISIBLE"
            m["r"] += f.reacciones or 0
            m["a"].add(f.autor_id)
        for minuto, m in por_min.items():
            filas_mart.append((p, minuto, m["c"], m["o"], m["r"], len(m["a"]),
                               "cassandra:fixture2030_comments.comentarios_por_partido", v, len(filas), ahora, "v1"))
        marcas.append((p, v, len(filas), len(por_min), ahora))
    t1 = time.perf_counter()
    execute_concurrent_with_args(s, ins, filas_mart, concurrency=64, raise_on_first_error=True)
    execute_concurrent_with_args(s, marca, marcas, concurrency=64, raise_on_first_error=True)
    t_carga = time.perf_counter() - t1
    leidas = sum(len(f) for f in fuente.values())
    cluster.shutdown()
    resultado = {"etl_utc": ahora, "partidos": partidos, "ventanas": len(ventanas), "particiones_leidas": particiones,
                 "filas_leidas": leidas, "duplicadas_descartadas": duplicadas, "filas_mart_escritas": len(filas_mart),
                 "extraccion_s": round(t_ext, 2), "transformacion_y_carga_s": round(t_carga, 2),
                 "primera_ventana": ventanas[0], "ultima_ventana": ventanas[-1]}
    comun.guardar_json(comun.EVIDENCIA / "data_mart" / "etl_ultima_carga.json", resultado)
    print(resultado)


def validar():
    """Conteo por partido: suma del mart == filas únicas de la fuente en las mismas ventanas (etl_marcas)."""
    cluster, s = comun.sesion_cassandra()
    informe = {}
    for p in comun.PARTIDOS_LAB:
        marcas = list(s.execute(f"SELECT ventana, filas_leidas FROM {MART}.etl_marcas WHERE partido_id=%s", (p,)))
        if not marcas:
            continue
        ventanas = [m.ventana for m in marcas]
        fuente, _ = leer_fuente(s, [p], ventanas)
        unicos_fuente = sum(len({f.comentario_id for f in filas}) for filas in fuente.values())
        mart = list(s.execute(f"SELECT minuto, comentarios FROM {MART}.actividad_partido_minuto WHERE partido_id=%s", (p,)))
        suma_mart = sum(r.comentarios for r in mart)
        informe[p] = {"ventanas": len(ventanas), "comentarios_fuente": unicos_fuente, "suma_mart": suma_mart,
                      "minutos_mart": len(mart), "coincide": unicos_fuente == suma_mart}
    cluster.shutdown()
    comun.guardar_json(comun.EVIDENCIA / "data_mart" / "validacion.json", informe)
    for p, r in informe.items():
        print(p, r)


def comparar(repeticiones=10):
    """Misma pregunta ("comentarios por minuto de P901 en las ventanas cargadas") contra la fuente y el mart."""
    cluster, s = comun.sesion_cassandra()
    p = "P901"
    ventanas = [m.ventana for m in s.execute(f"SELECT ventana FROM {MART}.etl_marcas WHERE partido_id=%s", (p,))]
    q_mart = s.prepare(f"SELECT minuto, comentarios FROM {MART}.actividad_partido_minuto WHERE partido_id=?")
    t_fuente, t_mart, filas_fuente, filas_mart = [], [], 0, 0
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        fuente, particiones = leer_fuente(s, [p], ventanas)
        por_min = defaultdict(int)
        for filas in fuente.values():
            for f in filas:
                por_min[f.creado_en.replace(second=0, microsecond=0)] += 1
        t_fuente.append((time.perf_counter() - t0) * 1000)
        filas_fuente = sum(len(f) for f in fuente.values())
        t0 = time.perf_counter()
        mart = list(s.execute(q_mart, (p,)))
        t_mart.append((time.perf_counter() - t0) * 1000)
        filas_mart = len(mart)
    iguales = dict(por_min) == {r.minuto: r.comentarios for r in mart}
    cluster.shutdown()
    resultado = {
        "pregunta": f"comentarios por minuto de {p} en {len(ventanas)} ventanas de 5 min",
        "repeticiones": repeticiones, "medicion": "tiempo de cliente (driver Python) en ms, mediana y máximo",
        "fuente_operacional": {"particiones": particiones, "filas_transferidas": filas_fuente,
                               "mediana_ms": round(statistics.median(t_fuente), 1), "max_ms": round(max(t_fuente), 1)},
        "proyeccion_mart": {"particiones": 1, "filas_transferidas": filas_mart,
                            "mediana_ms": round(statistics.median(t_mart), 1), "max_ms": round(max(t_mart), 1)},
        "mismas_respuestas": iguales,
    }
    comun.guardar_json(comun.EVIDENCIA / "data_mart" / "comparacion_fuente_vs_mart.json", resultado)
    print(resultado)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["cargar", "validar", "comparar"])
    ap.add_argument("--partidos", default=",".join(comun.PARTIDOS_LAB))
    ap.add_argument("--desde-horas", type=int, default=4)
    a = ap.parse_args()
    {"cargar": lambda: cargar(a.partidos.split(","), a.desde_horas), "validar": validar, "comparar": comparar}[a.accion]()
