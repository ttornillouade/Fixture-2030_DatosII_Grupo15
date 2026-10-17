"""Adaptador de MongoDB, database fixture2030.

- equipos / jugadores (Hito 4): fichas por _id y plantel por el índice {equipoId, posicion, dorsal}.
- partidos (Hito 9): documento con los eventos embebidos. Las transiciones de estado son
  updates condicionados al estado actual: atómicos en un único documento.
- estadisticas (Hito 8): colección time series con índice {meta, ts}.
Cada consulta proyecta solo los campos del contrato.
"""
import logging
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import config
from app.errores import Conflicto, DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.mongodb")
_ms = int(config.timeout_s * 1000)
_db = MongoClient(config.mongodb_uri, serverSelectionTimeoutMS=_ms, connectTimeoutMS=_ms,
                  socketTimeoutMS=_ms)[config.mongodb_database]

_CAMPOS_EQUIPO = {"_id": 1, "nombre": 1, "pais": 1, "confederacion": 1, "grupo": 1}
_CAMPOS_JUGADOR = {"_id": 1, "equipoId": 1, "nombre": 1, "apellido": 1, "posicion": 1, "dorsal": 1}
# Transiciones válidas: estado nuevo -> estado del que tiene que partir.
_DESDE = {"EN_JUEGO": "PROGRAMADO", "FINALIZADO": "EN_JUEGO"}


def _no_disponible(e: Exception):
    log.warning("MongoDB no disponible: %s", type(e).__name__)
    return DependenciaNoDisponible("MongoDB")


# --- Equipos y jugadores (Hito 4) --------------------------------------------------------
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


# --- Partidos y eventos (Hito 9) ---------------------------------------------------------
def detalle_partido(codigo: str) -> dict:
    try:
        docs = list(_db.partidos.aggregate([
            {"$match": {"_id": codigo}},
            {"$project": {"fechaHora": 1, "fase": 1, "sede": 1, "equipoLocalId": 1, "equipoVisitanteId": 1,
                          "estado": 1, "cantidadEventos": {"$size": "$eventos"}}}]))
    except PyMongoError as e:
        raise _no_disponible(e)
    if not docs:
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    d = docs[0]
    return {"codigo": d["_id"], "estado": d["estado"], "fechaHora": d["fechaHora"].replace(tzinfo=timezone.utc),
            "fase": d["fase"], "sede": d["sede"]["nombre"], "ciudad": d["sede"]["ciudad"],
            "equipoLocal": d["equipoLocalId"], "equipoVisitante": d["equipoVisitanteId"],
            "cantidadEventos": d["cantidadEventos"]}


def _estado_actual(codigo: str) -> str:
    doc = _db.partidos.find_one({"_id": codigo}, {"estado": 1})
    if not doc:
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    return doc["estado"]


def cambiar_estado(codigo: str, nuevo: str) -> None:
    """La transición es un único update condicionado al estado de origen: si otro proceso cambió el
    estado en el medio, el filtro no coincide y no se modifica nada (no hay lectura-y-escritura)."""
    desde = _DESDE[nuevo]
    try:
        r = _db.partidos.update_one({"_id": codigo, "estado": desde},
                                    {"$set": {"estado": nuevo, "updatedAt": datetime.now(timezone.utc)}})
        if r.matched_count == 0:
            actual = _estado_actual(codigo)
            raise Conflicto(f"Transición ilegal: {actual} -> {nuevo}", "ILLEGAL_TRANSITION")
    except PyMongoError as e:
        raise _no_disponible(e)


# --- Estadísticas temporales (Hito 8) ----------------------------------------------------
def estadisticas(partido: str, desde: datetime, hasta: datetime, agregacion: str) -> list[dict]:
    filtro = {"meta.partidoId": partido, "ts": {"$gte": desde, "$lt": hasta}}
    try:
        if agregacion == "raw":
            docs = _db.estadisticas.find(filtro, {"_id": 0}).sort([("ts", 1), ("meta.equipoId", 1)])
            return [{"time": d["ts"].replace(tzinfo=timezone.utc), "equipoId": d["meta"]["equipoId"],
                     "posesionPct": d["posesionPct"], "pasesCompletados": d["pasesCompletados"],
                     "tiros": d["tiros"]} for d in docs]
        # posesión es un valor de muestra -> promedio; pases y tiros son acumulados -> máximo del minuto.
        docs = _db.estadisticas.aggregate([
            {"$match": filtro},
            {"$group": {"_id": {"t": {"$dateTrunc": {"date": "$ts", "unit": "minute"}}, "e": "$meta.equipoId"},
                        "posesion": {"$avg": "$posesionPct"}, "pases": {"$max": "$pasesCompletados"},
                        "tiros": {"$max": "$tiros"}}},
            {"$sort": {"_id.t": 1, "_id.e": 1}}])
        return [{"time": d["_id"]["t"].replace(tzinfo=timezone.utc), "equipoId": d["_id"]["e"],
                 "posesionPct": round(d["posesion"], 2), "pasesCompletados": d["pases"], "tiros": d["tiros"]}
                for d in docs]
    except PyMongoError as e:
        raise _no_disponible(e)
