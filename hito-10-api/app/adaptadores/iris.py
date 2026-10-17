"""Adaptador de InterSystems IRIS (Hito 9): detalle y transición de estado del partido.

Lectura: proyección SQL (consulta tabular acotada). Escritura: método de clase
Fixture.Partido.CambiarEstado, que usa Iniciar/Finalizar; nunca un UPDATE directo sobre el estado.
"""
import logging
import threading

import iris

from app.config import config
from app.errores import Conflicto, DependenciaNoDisponible, NoEncontrado, Validacion

log = logging.getLogger("api.iris")
_lock = threading.Lock()  # la conexión de IRIS no es segura entre hilos
_estado: dict = {}

_DETALLE = """
SELECT p.Codigo, p.Estado, p.FechaHora, p.Sede->Estadio, p.Sede->Ubicacion_Ciudad,
       p.EquipoLocal->Codigo, p.EquipoVisitante->Codigo,
       (SELECT COUNT(*) FROM Fixture.Evento e WHERE e.Partido = p.ID)
FROM Fixture.Partido p WHERE p.Codigo = ?
"""


def _conexion():
    if "conexion" not in _estado:
        _estado["conexion"] = iris.connect(config.iris_host, config.iris_port, config.iris_namespace,
                                           config.iris_usuario, config.iris_password,
                                           timeout=int(config.timeout_s * 1000))
    return _estado["conexion"]


def _ejecutar(operacion):
    with _lock:
        try:
            return operacion(_conexion())
        except (RuntimeError, OSError, ConnectionError) as e:
            log.warning("IRIS no disponible: %s", type(e).__name__)
            _estado.clear()
            raise DependenciaNoDisponible("IRIS")


def detalle(codigo: str) -> dict:
    def leer(conexion):
        cursor = conexion.cursor()
        cursor.execute(_DETALLE, [codigo])
        return cursor.fetchone()

    fila = _ejecutar(leer)
    if not fila:
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    return {"codigo": fila[0], "estado": fila[1], "fechaHora": str(fila[2]), "sede": fila[3], "ciudad": fila[4],
            "equipoLocal": fila[5], "equipoVisitante": fila[6], "cantidadEventos": int(fila[7])}


def cambiar_estado(codigo: str, estado: str) -> None:
    resultado = _ejecutar(lambda conexion: iris.createIRIS(conexion).classMethodValue(
        "Fixture.Partido", "CambiarEstado", codigo, estado))
    if resultado == "NOT_FOUND":
        raise NoEncontrado(f"No existe el partido {codigo}", "MATCH_NOT_FOUND")
    if resultado == "INVALID":
        raise Validacion(f"Estado no soportado: {estado}")
    if resultado.startswith("CONFLICT"):
        raise Conflicto(resultado.split(":", 1)[1].split(": ", 1)[-1], "ILLEGAL_TRANSITION")
