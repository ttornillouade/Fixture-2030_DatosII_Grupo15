"""Caché de la primera página de comentarios en Redis (Hito 12, optimización 1).

Problema (línea base del Hito 12): durante un partido en vivo casi todas las lecturas piden la MISMA
página (primera página de la ventana de 5 minutos actual de unos pocos partidos). Cada una cuesta 8
consultas a Cassandra (una por shard) y la fusión en Python, y con 60 usuarios virtuales la API
satura un núcleo.

Solución: micro-caché con TTL corto (CACHE_COMENTARIOS_TTL_MS, 0 = desactivada, que es el valor por
defecto: la API del Hito 10 se comporta igual que antes).
  - Clave: fixture2030:cache:comentarios:{partido}:{bucket ISO}:{limit}  (STRING con el JSON de la página)
  - Solo la primera página (sin cursor): las siguientes se piden poco y no se repiten.
  - Sin invalidación al publicar: con ~16 publicaciones/s repartidas en 4 partidos, borrar la clave en
    cada POST dejaría la caché casi siempre vacía. Se acepta una página desactualizada a lo sumo TTL
    milisegundos (frescura acotada). Quien publica ve su comentario por la respuesta del POST.
  - Si Redis falla o tarda más de 200 ms, se lee Cassandra como siempre: la caché nunca hace que una
    request falle (no se agrega una dependencia obligatoria al flujo).
"""
import json

import redis

from app.config import config

_TIMEOUT_S = 0.2
_cliente = redis.Redis.from_url(config.redis_url, decode_responses=True,
                                socket_timeout=_TIMEOUT_S, socket_connect_timeout=_TIMEOUT_S)


def _contar(resultado: str) -> None:
    try:
        from app.metricas import CACHE  # disponible desde el Hito 13
        CACHE.labels(resultado).inc()
    except ImportError:
        pass


def _clave(partido: str, bucket_iso: str, limit: int) -> str:
    return f"fixture2030:cache:comentarios:{partido}:{bucket_iso}:{limit}"


def activa() -> bool:
    return config.cache_comentarios_ttl_ms > 0


def leer(partido: str, bucket_iso: str, limit: int) -> dict | None:
    try:
        valor = _cliente.get(_clave(partido, bucket_iso, limit))
    except redis.RedisError:
        _contar("error")
        return None
    _contar("hit" if valor else "miss")
    return json.loads(valor) if valor else None


def guardar(partido: str, bucket_iso: str, limit: int, pagina: dict) -> None:
    try:
        _cliente.set(_clave(partido, bucket_iso, limit), json.dumps(pagina, default=str),
                     px=config.cache_comentarios_ttl_ms)
    except redis.RedisError:
        _contar("error")
