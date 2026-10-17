"""Servicios: validan la request y aplican las reglas de cada caso de uso antes de llamar al adaptador."""
import base64
import binascii
from datetime import datetime, timedelta, timezone

from app.adaptadores import cassandra, mongodb, neo4j_grafo, redis_sesiones
from app.errores import Validacion

# Ventana máxima por consulta temporal: evita traer el histórico completo del partido.
VENTANA_MAXIMA = {"raw": timedelta(minutes=15), "minuto": timedelta(hours=3)}
_VENTANA_TEXTO = {"raw": "15 minutos", "minuto": "3 horas"}


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=timezone.utc) if valor.tzinfo is None else valor.astimezone(timezone.utc)


# --- MongoDB: partidos -------------------------------------------------------------------
def detalle(partido: str) -> dict:
    return mongodb.detalle_partido(partido)


def cambiar_estado(partido: str, estado: str) -> dict:
    mongodb.cambiar_estado(partido, estado)
    return mongodb.detalle_partido(partido)


# --- MongoDB: equipos y jugadores --------------------------------------------------------
def equipo(codigo: str) -> dict:
    return mongodb.equipo(codigo)


def jugadores(equipo_codigo: str, posicion: str | None, limit: int, cursor: str | None) -> dict:
    despues_de = None
    if cursor is not None:
        if not cursor.isdigit() or not 1 <= int(cursor) <= 99:
            raise Validacion("El cursor no es válido: usar el nextCursor de la página anterior")
        despues_de = int(cursor)
    items, hay_mas = mongodb.jugadores(equipo_codigo, posicion, limit, despues_de)
    return {"equipoCodigo": equipo_codigo, "items": items, "limit": limit,
            "nextCursor": str(items[-1]["dorsal"]) if hay_mas and items else None}


# --- MongoDB: estadísticas temporales ----------------------------------------------------
def estadisticas(partido: str, desde: datetime, hasta: datetime, agregacion: str) -> dict:
    desde, hasta = _utc(desde), _utc(hasta)
    if desde >= hasta:
        raise Validacion("desde debe ser anterior a hasta")
    if hasta - desde > VENTANA_MAXIMA[agregacion]:
        raise Validacion(f"La ventana máxima para agregacion={agregacion} es de {_VENTANA_TEXTO[agregacion]}")
    return {"partidoCodigo": partido, "desde": desde, "hasta": hasta, "agregacion": agregacion,
            "puntos": mongodb.estadisticas(partido, desde, hasta, agregacion)}


# --- Neo4j: recorridos -------------------------------------------------------------------
def partidos_de_jugador(jugador: str) -> dict:
    return {"jugadorCodigo": jugador, "partidos": neo4j_grafo.partidos_de_jugador(jugador)}


# --- Cassandra ---------------------------------------------------------------------------
def _codificar_cursor(comentario: dict) -> str:
    texto = f"{comentario['creadoEn'].isoformat()}|{comentario['comentarioId']}"
    return base64.urlsafe_b64encode(texto.encode()).decode()


def _decodificar_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        creado, comentario_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
        return _utc(datetime.fromisoformat(creado)), comentario_id
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise Validacion("El cursor no es válido: usar el nextCursor de la página anterior")


def comentarios(partido: str, bucket: datetime, limit: int, cursor: str | None) -> dict:
    bucket = _utc(bucket)
    if bucket.minute % 5 or bucket.second or bucket.microsecond:
        raise Validacion("bucket debe ser el inicio de una ventana de 5 minutos (por ejemplo 2030-06-08T20:00:00Z)")
    items, hay_mas = cassandra.leer_pagina(partido, bucket, limit, _decodificar_cursor(cursor) if cursor else None)
    return {"partidoCodigo": partido, "bucket": bucket, "items": items, "limit": limit,
            "nextCursor": _codificar_cursor(items[-1]) if hay_mas and items else None}


def crear_comentario(partido: str, usuario: str, texto: str) -> dict:
    return cassandra.insertar(partido, usuario, texto.strip())


# --- Redis: sesiones ---------------------------------------------------------------------
def sesion(sesion_id: str) -> dict:
    return redis_sesiones.obtener(sesion_id)


def eliminar_sesion(sesion_id: str) -> None:
    redis_sesiones.eliminar(sesion_id)
