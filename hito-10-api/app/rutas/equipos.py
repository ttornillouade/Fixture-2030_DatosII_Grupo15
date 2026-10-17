from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app import servicios
from app.esquemas import Equipo, PaginaJugadores
from app.rutas.parametros import errores, fuente

router = APIRouter(tags=["MongoDB"], dependencies=[Depends(fuente("MongoDB"))])
EquipoCodigo = Annotated[str, Path(pattern=r"^E[0-9]{3}$", description="Código de equipo", examples=["E010"])]


@router.get("/equipos/{codigo}", response_model=Equipo, responses=errores(400, 404, 503),
            summary="Ficha de un equipo")
def obtener_equipo(codigo: EquipoCodigo):
    return servicios.equipo(codigo)


@router.get("/jugadores", response_model=PaginaJugadores, responses=errores(400, 503),
            summary="Plantel de un equipo, filtrado por posición y paginado por dorsal")
def listar_jugadores(equipoCodigo: Annotated[str, Query(pattern=r"^E[0-9]{3}$", examples=["E010"])],
                     posicion: Literal["Arquero", "Defensor", "Mediocampista", "Delantero"] | None = None,
                     limit: Annotated[int, Query(ge=1, le=100)] = 20,
                     cursor: Annotated[str | None, Query(description="nextCursor de la página anterior")] = None):
    """equipoCodigo es obligatorio: la consulta usa el índice {equipoId, posicion, dorsal} del Hito 4.
    Un equipo inexistente devuelve una página vacía (el filtro es válido, no hay jugadores)."""
    return servicios.jugadores(equipoCodigo, posicion, limit, cursor)
