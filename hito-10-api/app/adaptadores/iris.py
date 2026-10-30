"""Adaptador de InterSystems IRIS (clases del Hito 9): detalle y transición de estado del partido.

Lectura: proyección SQL de Fixture.Partido y Fixture.Evento, navegando Evento -> Jugador con `->`.
Escritura: un único UPDATE condicionado al estado de origen; si otro proceso cambió el estado en el
medio, no coincide ninguna fila y no se modifica nada (no hay lectura-y-escritura).
"""
import logging
import threading

import iris
from iris.dbapi import InterfaceError, OperationalError

from app.config import config
from app.errores import Conflicto, DependenciaNoDisponible, NoEncontrado

log = logging.getLogger("api.iris")
_lock = threading.Lock()  # la conexión de IRIS no es segura entre hilos
_estado: dict = {}
# Transiciones válidas: estado nuevo -> estado del que tiene que partir.
_DESDE = {"EN_JUEGO": "PROGRAMADO", "FINALIZADO": "EN_JUEGO"}

_PARTIDO = "SELECT ID, Codigo, Estado FROM Fixture.Partido WHERE Codigo = ?"
_EVENTOS = """
SELECT e.Minuto, e.Tipo, e.Jugador->Nombre, e.Jugador->Apellido, e.Jugador->Dorsal
FROM Fixture.Evento e WHERE e.Partido = ? ORDER BY e.Minuto
"""
_TRANSICION = "UPDATE Fixture.Partido SET Estado = ? WHERE Codigo = ? AND Estado = ?"


def _conexion():
    if "conexion" not in _estado:
        _estado["conexion"] = iris.connect(config.iris_host, config.iris_port, config.iris_namespace,
                                           config.iris_usuario, config.iris_password,
                                           timeout=int(config.timeout_s * 1000))
    return _estado["conexion"]


def _ejecutar(operacion):
    with _lock:
        try:
            return operacion(_conexion().cursor())
        # RuntimeError al conectar; OperationalError/InterfaceError si se corta una conexión abierta.
        except (RuntimeError, OSError, ConnectionError, OperationalError, InterfaceError) as e:
            log.warning("IRIS no disponible: %s", type(e).__name__)
            _estado.clear()
            raise DependenciaNoDisponible("IRIS")


def _partido(cursor, codigo: str):
    cursor.execute(_PARTIDO, [codigo])
    fila = cursor.fetchone()
    if not fila:
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    return fila


def detalle(codigo: str) -> dict:
    def leer(cursor):
        partido_id, codigo_, estado = _partido(cursor, codigo)
        cursor.execute(_EVENTOS, [partido_id])
        return codigo_, estado, cursor.fetchall()

    codigo_, estado, eventos = _ejecutar(leer)
    return {"codigo": codigo_, "estado": estado,
            "eventos": [{"minuto": e[0], "tipo": e[1], "jugador": f"{e[2]} {e[3]}", "dorsal": e[4]} for e in eventos]}


def cambiar_estado(codigo: str, nuevo: str) -> None:
    def actualizar(cursor):
        cursor.execute(_TRANSICION, [nuevo, codigo, _DESDE[nuevo]])
        if cursor.rowcount == 0:
            actual = _partido(cursor, codigo)[2]
            raise Conflicto(f"Transición ilegal: {actual} -> {nuevo}", "ILLEGAL_TRANSITION")

    _ejecutar(actualizar)
