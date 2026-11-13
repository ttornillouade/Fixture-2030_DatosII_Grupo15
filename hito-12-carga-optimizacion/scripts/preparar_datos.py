"""PREPARACIÓN: carga el historial de comentarios de los partidos de laboratorio P901-P904.

Datos sintéticos y reproducibles (semilla fija). Para cada partido se generan comentarios en las
ventanas de 5 minutos de las últimas H horas (hasta la ventana actual, que es la que lee la prueba), con:
  - distribución desigual entre partidos (P901 es el partido "caliente": 55 % de los comentarios);
  - más actividad en las ventanas recientes (rampa lineal), como un partido que se calienta;
  - shard = crc32(comentario_id) % 8, igual que la API.
Se escriben las dos tablas del Hito 6 (por partido y por usuario), como hace la API.

Es idempotente: los ids son deterministas (L-<partido>-<n>), así que repetir la carga reescribe
las mismas filas (upsert de Cassandra) y no duplica. Deja un manifiesto con los conteos esperados.

Uso:  python scripts/preparar_datos.py [--total 200000] [--horas 3]
"""
import argparse
import random
import time
import zlib
from datetime import timedelta

from cassandra.concurrent import execute_concurrent_with_args

import comun

PESOS = {"P901": 0.55, "P902": 0.20, "P903": 0.15, "P904": 0.10}
FRASES = ["Golazo!", "Qué atajada", "Penal clarísimo", "Vamos que se puede", "Fuera de juego",
          "Tarjeta amarilla", "Gran jugada por la banda", "El VAR lo revisa", "Cambio táctico", "Final emocionante"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=200_000)
    ap.add_argument("--horas", type=int, default=3)
    ap.add_argument("--concurrencia", type=int, default=64)
    args = ap.parse_args()

    rnd = random.Random(2030)
    fin = comun.bucket_de(comun.ahora())               # ventana actual
    inicio = fin - timedelta(hours=args.horas) + timedelta(minutes=5)
    buckets = comun.ventana_historica(inicio, args.horas)
    pesos_bucket = [i + 1 for i in range(len(buckets))]  # rampa: más comentarios en ventanas recientes

    cluster, s = comun.sesion_cassandra()
    ins_p = s.prepare("INSERT INTO comentarios_por_partido (partido_id, bucket_5m, shard, creado_en, comentario_id, "
                      "autor_id, contenido, estado_moderacion, reacciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
    ins_u = s.prepare("INSERT INTO comentarios_por_usuario (autor_id, dia_bucket, creado_en, comentario_id, partido_id, "
                      "bucket_5m, shard, contenido, estado_moderacion, reacciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")

    filas_p, filas_u = [], []
    por_partido = {p: 0 for p in PESOS}
    por_bucket_partido = {}
    usuarios_dias = set()
    for n in range(args.total):
        partido = rnd.choices(list(PESOS), weights=list(PESOS.values()))[0]
        bucket = rnd.choices(buckets, weights=pesos_bucket)[0]
        creado = bucket + timedelta(seconds=rnd.randrange(300), milliseconds=rnd.randrange(1000))
        cid = f"L-{partido}-{n:07d}"
        shard = zlib.crc32(cid.encode()) % comun.SHARDS
        autor = comun.usuario(rnd.randrange(10_000))
        texto = rnd.choice(FRASES)
        estado = "VISIBLE" if rnd.random() > 0.02 else "OCULTO"
        reac = int(rnd.paretovariate(1.5)) - 1
        filas_p.append((partido, bucket, shard, creado, cid, autor, texto, estado, reac))
        filas_u.append((autor, creado.date(), creado, cid, partido, bucket, shard, texto, estado, reac))
        por_partido[partido] += 1
        clave = f"{partido}|{bucket.isoformat()}"
        por_bucket_partido[clave] = por_bucket_partido.get(clave, 0) + 1
        usuarios_dias.add((autor, creado.date().isoformat()))

    t0 = time.perf_counter()
    errores = 0
    for tabla, stmt, filas in (("comentarios_por_partido", ins_p, filas_p), ("comentarios_por_usuario", ins_u, filas_u)):
        res = execute_concurrent_with_args(s, stmt, filas, concurrency=args.concurrencia, raise_on_first_error=False)
        e = sum(1 for ok, _ in res if not ok)
        errores += e
        print(f"{tabla}: {len(filas)} filas escritas, {e} errores")
    dur = time.perf_counter() - t0
    cluster.shutdown()

    manifiesto = {
        "generado": comun.ahora(), "semilla": 2030, "total": args.total, "horas": args.horas,
        "primer_bucket": buckets[0], "ultimo_bucket": buckets[-1], "buckets": len(buckets),
        "por_partido": por_partido, "por_bucket_partido": por_bucket_partido,
        "particiones_usuario": sorted(f"{u}|{d}" for u, d in usuarios_dias),
        "duracion_carga_s": round(dur, 1), "filas_por_s": round(2 * args.total / dur), "errores": errores,
    }
    comun.guardar_json(comun.EVIDENCIA / "datos_preparados.json", manifiesto)
    print(f"Carga: {2 * args.total} filas en {dur:.1f} s ({manifiesto['filas_por_s']} filas/s), errores={errores}")
    print(f"Por partido: {por_partido}")
    print(f"Ventanas: {buckets[0]:%Y-%m-%d %H:%M} .. {buckets[-1]:%H:%M} UTC ({len(buckets)} buckets de 5 min)")


if __name__ == "__main__":
    main()
