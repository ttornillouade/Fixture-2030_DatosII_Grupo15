"""VALIDACIÓN: integridad de los datos después de una corrida de carga (RF15, RNF4).

Un 201 no garantiza que el dato quedó bien escrito. Para la corrida indicada verifica:
  1. Escrituras: cada comentario con 201 existe exactamente una vez en comentarios_por_partido Y en
     comentarios_por_usuario (lectura puntual por clave completa), con el mismo texto y autor.
  2. Sin escrituras fantasma ni duplicadas: en las particiones que tocó la corrida, la cantidad de
     filas con el texto "carga <etiqueta> ..." es igual a la cantidad de 201 (un POST que el cliente
     dio por fallido pero que la base escribió aparecería acá como sobrante).
  3. Ids únicos: ningún comentarioId repetido entre los 201.
  4. Datos precargados intactos: la cantidad de comentarios L-* por partido coincide con el manifiesto
     de scripts/preparar_datos.py.
  5. Consistencia de la caché (solo si la API la tiene activa): pasado el TTL, la primera página que
     devuelve la API coincide con la que se arma leyendo Cassandra directamente.

Uso: python scripts/validar_integridad.py --etiqueta linea_base   (usa la última corrida con esa etiqueta)
"""
import argparse
import json
import time
import zlib
from datetime import datetime, timedelta, timezone

import httpx
from cassandra.concurrent import execute_concurrent_with_args

import comun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", required=True)
    ap.add_argument("--cache-ttl-ms", type=int, default=0)
    args = ap.parse_args()
    carpeta = comun.EVIDENCIA / (comun.EVIDENCIA / f"ultima_{args.etiqueta}.txt").read_text().strip()
    resumen = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    manifiesto = json.loads((comun.EVIDENCIA / "datos_preparados.json").read_text(encoding="utf-8"))
    lineas = [l for l in (carpeta / "ids_creados.txt").read_text(encoding="utf-8").splitlines() if l]
    creados = [l.split(";", 4) for l in lineas]
    cluster, s = comun.sesion_cassandra()
    informe = {"corrida": carpeta.name, "validado_utc": comun.ahora()}

    # 1. Lectura puntual de cada 201 en las dos tablas -------------------------------------------
    q_p = s.prepare("SELECT autor_id, contenido FROM comentarios_por_partido WHERE partido_id=? AND bucket_5m=? "
                    "AND shard=? AND creado_en=? AND comentario_id=?")
    q_u = s.prepare("SELECT partido_id, contenido FROM comentarios_por_usuario WHERE autor_id=? AND dia_bucket=? "
                    "AND creado_en=? AND comentario_id=?")
    params_p, params_u = [], []
    for cid, partido, usuario, creado, _texto in creados:
        t = datetime.fromisoformat(creado.replace("Z", "+00:00")).astimezone(timezone.utc)
        params_p.append((partido, comun.bucket_de(t), zlib.crc32(cid.encode()) % comun.SHARDS, t, cid))
        params_u.append((usuario, t.date(), t, cid))
    res_p = execute_concurrent_with_args(s, q_p, params_p, concurrency=64, raise_on_first_error=False)
    res_u = execute_concurrent_with_args(s, q_u, params_u, concurrency=64, raise_on_first_error=False)
    faltan_p = faltan_u = distintos = 0
    for (cid, partido, usuario, _c, texto), (ok_p, rp), (ok_u, ru) in zip(creados, res_p, res_u):
        fp = list(rp) if ok_p else []
        fu = list(ru) if ok_u else []
        faltan_p += len(fp) != 1
        faltan_u += len(fu) != 1
        if fp and fu and (fp[0].contenido != texto or fp[0].autor_id != usuario or fu[0].partido_id != partido):
            distintos += 1
    informe["escrituras"] = {"enviadas": resumen["escrituras"]["enviadas_total"], "aceptadas_201": len(creados),
                             "rechazadas_o_fallidas": resumen["escrituras"]["enviadas_total"] - len(creados),
                             "faltan_en_por_partido": faltan_p, "faltan_en_por_usuario": faltan_u,
                             "contenido_distinto": distintos}

    # 2. Sin fantasmas ni duplicados en las particiones tocadas -----------------------------------
    marca = f"carga {args.etiqueta} "
    tiempos = [datetime.fromisoformat(c[3].replace("Z", "+00:00")) for c in creados]
    encontrados = 0
    if tiempos:
        b, fin = comun.bucket_de(min(tiempos)), comun.bucket_de(max(tiempos))
        buckets = []
        while b <= fin:
            buckets.append(b)
            b += timedelta(minutes=5)
        q_all = s.prepare("SELECT comentario_id, contenido FROM comentarios_por_partido "
                          "WHERE partido_id=? AND bucket_5m=? AND shard=?")
        claves = [(p, b, sh) for p in comun.PARTIDOS_LAB for b in buckets for sh in range(comun.SHARDS)]
        ids_vistos = []
        for ok, filas in execute_concurrent_with_args(s, q_all, claves, concurrency=32):
            ids_vistos += [f.comentario_id for f in filas if f.contenido.startswith(marca)]
        encontrados = len(ids_vistos)
        informe["particiones_revisadas"] = len(claves)
    informe["filas_de_la_corrida_en_cassandra"] = encontrados
    informe["sobrantes_vs_201"] = encontrados - len(creados)

    # 3. Ids únicos -------------------------------------------------------------------------------
    ids = [c[0] for c in creados]
    informe["ids_duplicados"] = len(ids) - len(set(ids))

    # 4. Datos precargados intactos ---------------------------------------------------------------
    q_ids = s.prepare("SELECT comentario_id FROM comentarios_por_partido WHERE partido_id=? AND bucket_5m=? AND shard=?")
    claves = []
    for clave in manifiesto["por_bucket_partido"]:
        p, b = clave.split("|")
        claves += [(p, datetime.fromisoformat(b), sh) for sh in range(comun.SHARDS)]
    conteo = {p: 0 for p in comun.PARTIDOS_LAB}
    for (p, _b, _sh), (ok, filas) in zip(claves, execute_concurrent_with_args(s, q_ids, claves, concurrency=64)):
        conteo[p] += sum(1 for f in filas if f.comentario_id.startswith("L-"))
    informe["precargados"] = {"esperado": manifiesto["por_partido"], "encontrado": conteo,
                              "coincide": conteo == manifiesto["por_partido"]}

    # 5. Consistencia caché vs fuente ---------------------------------------------------------------
    if args.cache_ttl_ms:
        time.sleep(args.cache_ttl_ms / 1000 + 0.5)
        bucket = comun.bucket_de(comun.ahora())
        q_pag = s.prepare("SELECT creado_en, comentario_id FROM comentarios_por_partido "
                          "WHERE partido_id=? AND bucket_5m=? AND shard=? LIMIT 21")
        iguales = {}
        for p in comun.PARTIDOS_LAB:
            api = httpx.get(f"{comun.API_URL}/partidos/{p}/comentarios",
                            params={"bucket": bucket.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": 20}).json()
            filas = []
            for sh in range(comun.SHARDS):
                filas += list(s.execute(q_pag, (p, bucket, sh)))
            filas.sort(key=lambda f: (f.creado_en, f.comentario_id), reverse=True)
            iguales[p] = [i["comentarioId"] for i in api["items"]] == [f.comentario_id for f in filas[:20]]
        informe["cache_vs_cassandra_primera_pagina"] = iguales
    cluster.shutdown()

    e = informe["escrituras"]
    informe["integridad_ok"] = (e["faltan_en_por_partido"] == 0 and e["faltan_en_por_usuario"] == 0
                                and e["contenido_distinto"] == 0 and informe["sobrantes_vs_201"] == 0
                                and informe["ids_duplicados"] == 0 and informe["precargados"]["coincide"]
                                and all(informe.get("cache_vs_cassandra_primera_pagina", {"-": True}).values()))
    comun.guardar_json(carpeta / "integridad.json", informe)
    print(json.dumps({k: v for k, v in informe.items() if k != "validado_utc"}, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
