"""LIMPIEZA OPCIONAL: borra SOLO los datos de laboratorio del Hito 12 (RNF7, RNF11).

Qué borra (por clave de partición completa, sin escaneos ni TRUNCATE):
  - comentarios_por_partido: particiones (P901..P904, bucket, shard) desde el primer bucket precargado
    hasta la ventana actual;
  - comentarios_por_usuario: particiones (U900000..U909999, día) de esos mismos días;
  - el keyspace fixture2030_mart (prototipo del Data Mart), solo con --mart;
  - las claves de caché fixture2030:cache:comentarios:P90* en Redis.
Qué NO toca: los comentarios de P001..P128 (Hitos 6 y 10), otras tablas, volúmenes ni contenedores.
La evidencia en docs/evidencia/ se conserva.

Uso: python scripts/limpiar_datos_de_prueba.py --confirmar [--mart]
"""
import argparse
import json
from datetime import datetime, timedelta

import redis
from cassandra.concurrent import execute_concurrent_with_args

import comun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmar", action="store_true", help="sin esta opción solo muestra qué borraría")
    ap.add_argument("--mart", action="store_true")
    args = ap.parse_args()
    manifiesto = json.loads((comun.EVIDENCIA / "datos_preparados.json").read_text(encoding="utf-8"))
    desde = datetime.fromisoformat(manifiesto["primer_bucket"])
    hasta = comun.bucket_de(comun.ahora())
    buckets = []
    b = desde
    while b <= hasta:
        buckets.append(b)
        b += timedelta(minutes=5)
    dias = sorted({x.date() for x in buckets})
    claves_p = [(p, b, sh) for p in comun.PARTIDOS_LAB for b in buckets for sh in range(comun.SHARDS)]
    claves_u = [(comun.usuario(n), d) for n in range(comun.USUARIO_MAX - comun.USUARIO_MIN + 1) for d in dias]
    print(f"Particiones a borrar: {len(claves_p)} en comentarios_por_partido (P901-P904, "
          f"{buckets[0]:%Y-%m-%d %H:%M} .. {buckets[-1]:%H:%M} UTC), {len(claves_u)} en comentarios_por_usuario "
          f"(U900000-U909999, días {', '.join(map(str, dias))})" + (", keyspace fixture2030_mart" if args.mart else ""))
    if not args.confirmar:
        print("Modo simulación: agregar --confirmar para borrar")
        return
    cluster, s = comun.sesion_cassandra()
    dp = s.prepare("DELETE FROM comentarios_por_partido WHERE partido_id=? AND bucket_5m=? AND shard=?")
    du = s.prepare("DELETE FROM comentarios_por_usuario WHERE autor_id=? AND dia_bucket=?")
    execute_concurrent_with_args(s, dp, claves_p, concurrency=64)
    execute_concurrent_with_args(s, du, claves_u, concurrency=64)
    if args.mart:
        s.execute("DROP KEYSPACE IF EXISTS fixture2030_mart")
    cluster.shutdown()
    r = redis.Redis(host="127.0.0.1", port=6379)
    borradas = sum(r.delete(k) for k in r.scan_iter("fixture2030:cache:comentarios:P90*"))
    print(f"Listo. Claves de caché borradas: {borradas}. Para volver a probar: python scripts/preparar_datos.py")


if __name__ == "__main__":
    main()
