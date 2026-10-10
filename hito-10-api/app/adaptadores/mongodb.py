"""Adaptador de MongoDB (Hito 4): equipos y jugadores de la base fixture2030.

Cada consulta usa un patrón con índice del Hito 4 y proyecta solo los campos del contrato.
La lista de jugadores exige el equipo (índice {equipoId, posicion, dorsal}): no hay listados globales.
"""
import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import config
from app.errores import DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.mongodb")
_ms = int(config.timeout_s * 1000)
_db = MongoClient(config.mongodb_uri, serverSelectionTimeoutMS=_ms, connectTimeoutMS=_ms,
                  socketTimeoutMS=_ms)[config.mongodb_database]

_CAMPOS_EQUIPO = {"_id": 1, "nombre": 1, "pais": 1, "confederacion": 1, "grupo": 1}
_CAMPOS_JUGADOR = {"_id": 1, "equipoId": 1, "nombre": 1, "apellido": 1, "posicion": 1, "dorsal": 1}


def _no_disponible(e: Exception):
    log.warning("MongoDB no disponible: %s", type(e).__name__)
    return DependenciaNoDisponible("MongoDB")


def equipo(codigo: str) -> dict:
    try:
        doc = _db.equipos.find_one({"_id": codigo}, _CAMPOS_EQUIPO)
    except PyMongoError as e:
        raise _no_disponible(e)
    if not doc:
        raise NoEncontrado(f"No existe el equipo {codigo}", "TEAM_NOT_FOUND")
    return {"codigo": doc["_id"], "nombre": doc["nombre"], "pais": doc["pais"],
            "confederacion": doc["confederacion"], "grupo": doc["grupo"]}


def jugadores(equipo_codigo: str, posicion: str | None, limit: int, despues_de_dorsal: int | None) -> tuple[list[dict], bool]:
    """Plantel ordenado por dorsal. Paginación por clave (dorsal > cursor), sin skip."""
    filtro = {"equipoId": equipo_codigo}
    if posicion:
        filtro["posicion"] = posicion
    if despues_de_dorsal is not None:
        filtro["dorsal"] = {"$gt": despues_de_dorsal}
    try:
        docs = list(_db.jugadores.find(filtro, _CAMPOS_JUGADOR).sort("dorsal", 1).limit(limit + 1))
    except PyMongoError as e:
        raise _no_disponible(e)
    items = [{"codigo": d["_id"], "equipoCodigo": d["equipoId"], "nombre": d["nombre"], "apellido": d["apellido"],
              "posicion": d["posicion"], "dorsal": d["dorsal"]} for d in docs[:limit]]
    return items, len(docs) > limit
