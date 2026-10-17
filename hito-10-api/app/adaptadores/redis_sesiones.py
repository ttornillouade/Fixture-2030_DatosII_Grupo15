"""Adaptador de Redis (Hito 7): sesiones con TTL en la clave fixture2030:session:{id} (HASH)."""
import logging

import redis

from app.config import config
from app.errores import DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.redis")
_cliente = redis.Redis.from_url(config.redis_url, decode_responses=True,
                                socket_timeout=config.timeout_s, socket_connect_timeout=config.timeout_s)


def _clave(sesion_id: str) -> str:
    return f"fixture2030:session:{sesion_id}"


def _no_disponible(e: Exception):
    log.warning("Redis no disponible: %s", type(e).__name__)
    return DependenciaNoDisponible("Redis")


def obtener(sesion_id: str) -> dict:
    try:
        datos = _cliente.hgetall(_clave(sesion_id))
        ttl = _cliente.ttl(_clave(sesion_id)) if datos else -2
    except redis.RedisError as e:
        raise _no_disponible(e)
    if not datos:
        # La clave no existe o expiró: es ausencia, no un error del servidor.
        raise NoEncontrado("La sesión no existe o expiró", "SESSION_EXPIRED_OR_NOT_FOUND")
    return {"sesionId": sesion_id, "usuarioId": datos.get("user_id"), "estado": datos.get("access_status"),
            "locale": datos.get("locale"), "creadaEn": datos.get("created_at"), "expiraEnSegundos": ttl}


def eliminar(sesion_id: str) -> None:
    try:
        borradas = _cliente.delete(_clave(sesion_id))
    except redis.RedisError as e:
        raise _no_disponible(e)
    if borradas == 0:
        raise NoEncontrado("La sesión no existe o expiró", "SESSION_EXPIRED_OR_NOT_FOUND")
