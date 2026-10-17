"""Adaptador de Cassandra (Hito 6): comentarios por partido.

La partición es (partido_id, bucket_5m, shard): una página de comentarios de un partido se arma
leyendo los 8 shards del bucket pedido y fusionándolos por fecha. Nunca se lee sin la clave de
partición completa (no hay ALLOW FILTERING ni escaneos).
"""
import logging
import threading
import uuid
import zlib
from datetime import datetime, timezone

from cassandra import OperationTimedOut, ReadTimeout, Unavailable, WriteTimeout
from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.query import BatchStatement, BatchType

from app.config import config
from app.errores import DependenciaNoDisponible

log = logging.getLogger("api.cassandra")
SHARDS = 8
_ERRORES = (NoHostAvailable, OperationTimedOut, ReadTimeout, WriteTimeout, Unavailable)
_lock = threading.Lock()
_estado: dict = {}

_COLUMNAS = "creado_en, comentario_id, autor_id, contenido, estado_moderacion, reacciones"


def _sesion():
    with _lock:
        if "sesion" not in _estado:
            cluster = Cluster([config.cassandra_host], port=config.cassandra_port,
                              connect_timeout=config.timeout_s)
            sesion = cluster.connect(config.cassandra_keyspace)
            sesion.default_timeout = config.timeout_s
            _estado["pagina"] = sesion.prepare(
                f"SELECT {_COLUMNAS} FROM comentarios_por_partido "
                "WHERE partido_id = ? AND bucket_5m = ? AND shard = ? LIMIT ?")
            _estado["pagina_cursor"] = sesion.prepare(
                f"SELECT {_COLUMNAS} FROM comentarios_por_partido "
                "WHERE partido_id = ? AND bucket_5m = ? AND shard = ? "
                "AND (creado_en, comentario_id) < (?, ?) LIMIT ?")
            _estado["insert_partido"] = sesion.prepare(
                "INSERT INTO comentarios_por_partido (partido_id, bucket_5m, shard, creado_en, "
                "comentario_id, autor_id, contenido, estado_moderacion, reacciones) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
            _estado["insert_usuario"] = sesion.prepare(
                "INSERT INTO comentarios_por_usuario (autor_id, dia_bucket, creado_en, comentario_id, "
                "partido_id, bucket_5m, shard, contenido, estado_moderacion, reacciones) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
            _estado["sesion"] = sesion
        return _estado["sesion"]


def _fila(partido: str, f) -> dict:
    return {"comentarioId": f.comentario_id, "partidoCodigo": partido, "usuarioId": f.autor_id,
            "texto": f.contenido, "creadoEn": f.creado_en.replace(tzinfo=timezone.utc),
            "estadoModeracion": f.estado_moderacion, "reacciones": f.reacciones or 0}


def leer_pagina(partido: str, bucket: datetime, limit: int,
                cursor: tuple[datetime, str] | None) -> tuple[list[dict], bool]:
    """Devuelve hasta `limit` comentarios del bucket (más recientes primero) y si quedan más."""
    try:
        sesion = _sesion()
        # Se pide limit+1 por shard para saber si queda algo después de la página.
        futuros = []
        for shard in range(SHARDS):
            if cursor:
                params = (partido, bucket, shard, cursor[0], cursor[1], limit + 1)
                futuros.append(sesion.execute_async(_estado["pagina_cursor"], params))
            else:
                futuros.append(sesion.execute_async(_estado["pagina"], (partido, bucket, shard, limit + 1)))
        filas = []
        for futuro in futuros:
            filas.extend(futuro.result())
    except _ERRORES as e:
        log.warning("Cassandra no disponible: %s", type(e).__name__)
        _estado.clear()
        raise DependenciaNoDisponible("Cassandra")
    filas.sort(key=lambda f: (f.creado_en, f.comentario_id), reverse=True)
    return [_fila(partido, f) for f in filas[:limit]], len(filas) > limit


def insertar(partido: str, usuario: str, texto: str) -> dict:
    """Escribe el comentario en las dos tablas del Hito 6 en un batch LOGGED: o quedan las dos o ninguna."""
    ahora = datetime.now(timezone.utc).replace(microsecond=0)
    bucket = ahora.replace(minute=ahora.minute - ahora.minute % 5, second=0)
    comentario_id = "C-" + uuid.uuid4().hex[:12].upper()
    shard = zlib.crc32(comentario_id.encode()) % SHARDS
    try:
        sesion = _sesion()
        batch = BatchStatement(batch_type=BatchType.LOGGED)
        batch.add(_estado["insert_partido"],
                  (partido, bucket, shard, ahora, comentario_id, usuario, texto, "VISIBLE", 0))
        batch.add(_estado["insert_usuario"],
                  (usuario, ahora.date(), ahora, comentario_id, partido, bucket, shard, texto, "VISIBLE", 0))
        sesion.execute(batch)
    except _ERRORES as e:
        log.warning("Cassandra no disponible: %s", type(e).__name__)
        _estado.clear()
        raise DependenciaNoDisponible("Cassandra")
    return {"comentarioId": comentario_id, "partidoCodigo": partido, "usuarioId": usuario, "texto": texto,
            "creadoEn": ahora, "estadoModeracion": "VISIBLE", "reacciones": 0}
