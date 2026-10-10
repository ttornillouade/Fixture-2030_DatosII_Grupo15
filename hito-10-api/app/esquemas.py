"""DTOs de entrada y salida. La API devuelve vistas acotadas, no los registros completos de cada base."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Error(BaseModel):
    code: str = Field(examples=["NOT_FOUND"])
    message: str
    requestId: str | None = None


# --- MongoDB ----------------------------------------------------------------------------
class Equipo(BaseModel):
    codigo: str = Field(examples=["E010"])
    nombre: str
    pais: str
    confederacion: str
    grupo: str


class Jugador(BaseModel):
    codigo: str = Field(examples=["E010-J09"])
    equipoCodigo: str
    nombre: str
    apellido: str
    posicion: str
    dorsal: int


class PaginaJugadores(BaseModel):
    equipoCodigo: str
    items: list[Jugador]
    limit: int
    nextCursor: str | None = None


# --- Cassandra ---------------------------------------------------------------------------
class ComentarioEntrada(BaseModel):
    usuarioId: str = Field(pattern=r"^U[0-9]{6}$", examples=["U000042"])
    texto: str = Field(min_length=1, max_length=500, examples=["Gran jugada en el minuto 15"])


class Comentario(BaseModel):
    comentarioId: str
    partidoCodigo: str
    usuarioId: str
    texto: str
    creadoEn: datetime
    estadoModeracion: str
    reacciones: int


class PaginaComentarios(BaseModel):
    partidoCodigo: str
    bucket: datetime
    items: list[Comentario]
    limit: int
    nextCursor: str | None = None


# --- Redis -------------------------------------------------------------------------------
class SesionEntrada(BaseModel):
    usuarioId: str = Field(pattern=r"^U[0-9]{6}$", examples=["U000042"])
    locale: str = Field(default="es-AR", pattern=r"^[a-z]{2}-[A-Z]{2}$")


class Sesion(BaseModel):
    sesionId: str
    usuarioId: str
    estado: str
    locale: str | None = None
    creadaEn: str | None = None
    expiraEnSegundos: int


# --- InfluxDB ----------------------------------------------------------------------------
class PuntoEstadistica(BaseModel):
    time: datetime
    equipoId: str
    posesionPct: float | None = None
    pasesCompletados: int | None = None
    tiros: int | None = None


class Estadisticas(BaseModel):
    partidoCodigo: str
    desde: datetime
    hasta: datetime
    agregacion: Literal["raw", "minuto"]
    puntos: list[PuntoEstadistica]


# --- Neo4j -------------------------------------------------------------------------------
class EventoGrafo(BaseModel):
    tipo: str
    minuto: int
    jugadorCodigo: str | None = None


class EventosPartido(BaseModel):
    partidoCodigo: str
    eventos: list[EventoGrafo]


# --- IRIS --------------------------------------------------------------------------------
class PartidoDetalle(BaseModel):
    codigo: str
    estado: str
    fechaHora: str
    sede: str
    ciudad: str
    equipoLocal: str
    equipoVisitante: str
    cantidadEventos: int


class CambioEstado(BaseModel):
    estado: Literal["EN_JUEGO", "FINALIZADO"]
