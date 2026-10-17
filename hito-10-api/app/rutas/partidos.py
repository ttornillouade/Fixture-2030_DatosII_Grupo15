from fastapi import APIRouter, Depends

from app import servicios
from app.esquemas import CambioEstado, EventosPartido, PartidoDetalle
from app.rutas.parametros import PartidoCodigo, errores, fuente

router = APIRouter()


@router.get("/partidos/{codigo}/eventos", response_model=EventosPartido, tags=["Neo4j"], dependencies=[Depends(fuente("Neo4j"))],
            responses=errores(400, 404, 503), summary="Eventos conectados con un partido en el grafo")
def eventos(codigo: PartidoCodigo):
    return servicios.eventos(codigo)


@router.get("/partidos/{codigo}/detalle", response_model=PartidoDetalle, tags=["IRIS"],
            dependencies=[Depends(fuente("IRIS"))],
            responses=errores(400, 404, 503), summary="Detalle del partido (entidad compleja)")
def detalle(codigo: PartidoCodigo):
    return servicios.detalle(codigo)


@router.patch("/partidos/{codigo}/estado", response_model=PartidoDetalle, tags=["IRIS"],
              dependencies=[Depends(fuente("IRIS"))],
              responses=errores(400, 404, 409, 503), summary="Transición validada del estado del partido")
def cambiar_estado(codigo: PartidoCodigo, cambio: CambioEstado):
    """Invoca Fixture.Partido.CambiarEstado (Iniciar/Finalizar): una transición ilegal devuelve 409."""
    return servicios.cambiar_estado(codigo, cambio.estado)
