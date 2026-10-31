"""Adaptador de MongoDB, database fixture2030 (Hito 4).

Fichas de equipo por _id y plantel por el índice {equipoId, posicion, dorsal}.
Cada consulta proyecta solo los campos del contrato.
"""
from pymongo import MongoClient
from pymongo.errors import NetworkTimeout, PyMongoError, ServerSelectionTimeoutError

from app.config import config
from app.errores import DependenciaNoDisponible, DependenciaTimeout, NoEncontrado

_ms = int(config.timeout_s * 1000)
# timeoutMS limita la operación completa (selección de servidor + red + ejecución): sin él, una base
# que no responde sumaba los timeouts de cada etapa (8,6 s medidos en el Hito 11).
_db = MongoClient(config.mongodb_uri, timeoutMS=_ms, serverSelectionTimeoutMS=_ms,
                  connectTimeoutMS=_ms)[config.mongodb_database]

_CAMPOS_EQUIPO = {"_id": 1, "nombre": 1, "pais": 1, "confederacion": 1, "grupo": 1}
_CAMPOS_JUGADOR = {"_id": 1, "equipoId": 1, "nombre": 1, "apellido": 1, "posicion": 1, "dorsal": 1}


def _rechazada() -> bool:
    """Con la base detenida el driver reintenta hasta agotar timeoutMS y lanza un error de timeout;
    el último error de conexión dice si la base rechazó la conexión (caída) o no respondió (lenta)."""
    errores = [d.error for d in _db.client.topology_description.server_descriptions().values() if d.error]
    return bool(errores) and not any(isinstance(error, NetworkTimeout) for error in errores)


def _no_disponible(e: PyMongoError):
    if e.timeout and not (isinstance(e, ServerSelectionTimeoutError) and _rechazada()):
        return DependenciaTimeout("MongoDB", type(e).__name__)
    rechazo = " (conexión rechazada)" if isinstance(e, ServerSelectionTimeoutError) else ""
    return DependenciaNoDisponible("MongoDB", type(e).__name__ + rechazo)


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



def ping() -> None:
    """Además del ping, verifica el contexto: MongoDB no da error con una database mal escrita (la crea
    vacía al escribir y la lee vacía), así que sin este control la API respondería 404 a todo."""
    try:
        _db.command("ping")
        existe = _db.list_collection_names(filter={"name": "equipos"})
    except PyMongoError as e:
        raise _no_disponible(e)
    if not existe:
        raise DependenciaNoDisponible("MongoDB", f"sin la colección equipos en la database {config.mongodb_database}")
